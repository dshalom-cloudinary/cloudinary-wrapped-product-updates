"""Interactive CLI for Slack Wrapped setup.

Provides terminal-based Q&A using rich prompts for collecting user input.
"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.syntax import Syntax
from rich.markdown import Markdown

from .message_analyzer import AnalysisResult, Question, UserSuggestion, TeamSuggestion


console = Console()


class InteractiveSetup:
    """Interactive CLI setup wizard for Slack Wrapped."""
    
    def __init__(self, analysis: AnalysisResult):
        """
        Initialize interactive setup.
        
        Args:
            analysis: Analysis result from MessageAnalyzer
        """
        self.analysis = analysis
        self.answers: dict = {}
    
    def run(self) -> dict:
        """
        Run the interactive setup wizard.
        
        Returns:
            Dictionary of user answers ready for config generation
        """
        self._show_welcome()
        self._show_analysis_summary()
        self._collect_basic_info()
        self._collect_user_mappings()
        self._collect_team_info()
        self._collect_preferences()
        
        return self.answers
    
    def _show_welcome(self):
        """Display welcome message."""
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Slack Wrapped[/bold cyan] - Interactive Setup\n\n"
            "I'll analyze your messages and ask a few questions to create\n"
            "a personalized Wrapped video for your team.",
            border_style="cyan",
        ))
        console.print()
    
    def _show_analysis_summary(self):
        """Display summary of message analysis."""
        a = self.analysis
        ca = a.channel_analysis
        
        # Basic stats table
        stats_table = Table(title="Message Analysis", show_header=False, box=None)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")
        
        stats_table.add_row("Total Messages", f"{a.total_messages:,}")
        stats_table.add_row(
            "Date Range",
            f"{a.date_range[0].strftime('%Y-%m-%d')} to {a.date_range[1].strftime('%Y-%m-%d')}"
        )
        stats_table.add_row("Contributors", str(len(a.usernames)))
        
        if ca.purpose:
            stats_table.add_row("Detected Purpose", ca.purpose)
        if ca.tone:
            stats_table.add_row("Detected Tone", ca.tone.capitalize())
        if ca.main_topics:
            stats_table.add_row("Main Topics", ", ".join(ca.main_topics[:3]))
        
        console.print(stats_table)
        console.print()
        
        # Top contributors
        console.print("[bold]Top Contributors:[/bold]")
        for i, user in enumerate(a.user_suggestions[:5], 1):
            console.print(f"  {i}. {user.username} ({user.message_count} messages)")
        console.print()
        
        # Key milestones if detected
        if ca.key_milestones:
            console.print("[bold]Key Milestones Detected:[/bold]")
            for milestone in ca.key_milestones[:3]:
                console.print(f"  - {milestone}")
            console.print()
        
        # Highlights if detected
        if a.highlights:
            console.print("[bold]Notable Moments:[/bold]")
            for h in a.highlights[:3]:
                console.print(f"  [{h.type}] {h.description}")
                if h.quote:
                    console.print(f"    \"{h.quote}\"")
            console.print()
    
    def _collect_basic_info(self):
        """Collect basic channel information."""
        console.print(Panel("[bold]Step 1:[/bold] Basic Information", style="blue"))
        
        # Channel name
        ca = self.analysis.channel_analysis
        default_name = ca.likely_name or "channel"
        
        channel_name = Prompt.ask(
            "Channel name",
            default=default_name,
        )
        self.answers["channel_name"] = channel_name
        
        # Year
        default_year = str(self.analysis.year)
        year = Prompt.ask(
            "Year for this Wrapped",
            default=default_year,
        )
        self.answers["year"] = int(year)
        
        # Channel description (optional)
        description = Prompt.ask(
            "Brief channel description (optional)",
            default=ca.purpose or "",
        )
        self.answers["channel_description"] = description
        
        console.print()
    
    def _collect_user_mappings(self):
        """Collect display name mappings for users."""
        console.print(Panel("[bold]Step 2:[/bold] User Display Names", style="blue"))
        console.print(
            "I'll suggest display names for each contributor. "
            "Press Enter to accept or type a new name.\n"
        )
        
        user_mappings = []
        
        for user in self.analysis.user_suggestions:
            display_name = Prompt.ask(
                f"  {user.username}",
                default=user.suggested_name,
            )
            user_mappings.append({
                "slack_username": user.username,
                "display_name": display_name,
            })
        
        self.answers["user_mappings"] = user_mappings
        console.print()
    
    def _collect_team_info(self):
        """Collect team structure information."""
        console.print(Panel("[bold]Step 3:[/bold] Team Structure", style="blue"))
        
        # Show suggested teams if any
        if self.analysis.team_suggestions:
            console.print("Based on the messages, I detected these potential teams:\n")
            
            for i, team in enumerate(self.analysis.team_suggestions, 1):
                console.print(f"  {i}. [cyan]{team.name}[/cyan]: {', '.join(team.members)}")
                if team.reasoning:
                    console.print(f"     ({team.reasoning})")
            console.print()
            
            use_suggestions = Confirm.ask(
                "Use these team groupings?",
                default=True,
            )
            
            if use_suggestions:
                self.answers["teams"] = [
                    {"name": t.name, "members": t.members}
                    for t in self.analysis.team_suggestions
                ]
                self._assign_teams_to_users()
                console.print()
                return
        
        # Manual team setup
        create_teams = Confirm.ask(
            "Would you like to define teams?",
            default=True,
        )
        
        if not create_teams:
            self.answers["teams"] = []
            console.print()
            return
        
        teams = []
        console.print("\nDefine your teams (enter empty name when done):\n")
        
        while True:
            team_name = Prompt.ask("  Team name (or empty to finish)", default="")
            if not team_name:
                break
            
            # Show available users
            assigned = set()
            for team in teams:
                assigned.update(team["members"])
            
            available = [u for u in self.analysis.usernames if u not in assigned]
            
            if available:
                console.print(f"  Available members: {', '.join(available)}")
                members_str = Prompt.ask(
                    "  Members (comma-separated usernames)",
                    default="",
                )
                members = [m.strip() for m in members_str.split(",") if m.strip()]
            else:
                members = []
            
            teams.append({"name": team_name, "members": members})
        
        self.answers["teams"] = teams
        self._assign_teams_to_users()
        console.print()
    
    def _assign_teams_to_users(self):
        """Assign team names to user mappings."""
        # Build username -> team lookup
        team_lookup = {}
        for team in self.answers.get("teams", []):
            for member in team.get("members", []):
                team_lookup[member] = team["name"]
        
        # Update user mappings
        for mapping in self.answers.get("user_mappings", []):
            username = mapping["slack_username"]
            if username in team_lookup:
                mapping["team"] = team_lookup[username]
    
    def _collect_preferences(self):
        """Collect user preferences."""
        console.print(Panel("[bold]Step 4:[/bold] Preferences", style="blue"))
        
        # Include roasts
        include_roasts = Confirm.ask(
            "Include gentle roasts and playful humor?",
            default=True,
        )
        self.answers["include_roasts"] = include_roasts
        
        # Top contributors count
        top_count = IntPrompt.ask(
            "Number of top contributors to highlight",
            default=5,
        )
        self.answers["top_contributors_count"] = top_count
        
        console.print()


def review_config(config_dict: dict) -> dict:
    """
    Display config for review and allow editing.
    
    Args:
        config_dict: Generated configuration dictionary
        
    Returns:
        Possibly modified configuration dictionary
    """
    console.print(Panel("[bold]Configuration Review[/bold]", style="green"))
    console.print("Here's the generated configuration:\n")
    
    # Display formatted JSON
    json_str = json.dumps(config_dict, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(syntax)
    console.print()
    
    # Ask if user wants to edit
    is_correct = Confirm.ask(
        "Does this configuration look correct?",
        default=True,
    )
    
    if is_correct:
        return config_dict
    
    # Offer editing options
    console.print("\n[yellow]Editing options:[/yellow]")
    console.print("  1. Edit channel info")
    console.print("  2. Edit user mappings")
    console.print("  3. Edit teams")
    console.print("  4. Edit preferences")
    console.print("  5. Edit raw JSON")
    console.print("  6. Accept as-is")
    
    choice = Prompt.ask(
        "Select option",
        choices=["1", "2", "3", "4", "5", "6"],
        default="6",
    )
    
    if choice == "1":
        config_dict = _edit_channel_info(config_dict)
    elif choice == "2":
        config_dict = _edit_user_mappings(config_dict)
    elif choice == "3":
        config_dict = _edit_teams(config_dict)
    elif choice == "4":
        config_dict = _edit_preferences(config_dict)
    elif choice == "5":
        config_dict = _edit_raw_json(config_dict)
    
    return config_dict


def _edit_channel_info(config: dict) -> dict:
    """Edit channel information."""
    channel = config.get("channel", {})
    
    channel["name"] = Prompt.ask(
        "Channel name",
        default=channel.get("name", ""),
    )
    channel["year"] = int(Prompt.ask(
        "Year",
        default=str(channel.get("year", 2025)),
    ))
    channel["description"] = Prompt.ask(
        "Description",
        default=channel.get("description", ""),
    )
    
    config["channel"] = channel
    return config


def _edit_user_mappings(config: dict) -> dict:
    """Edit user mappings."""
    mappings = config.get("userMappings", [])
    
    console.print("\nCurrent user mappings:")
    for i, m in enumerate(mappings):
        console.print(f"  {i+1}. {m.get('slackUsername')} -> {m.get('displayName')}")
    
    # Simple edit - just allow changing display names
    for m in mappings:
        m["displayName"] = Prompt.ask(
            f"  {m.get('slackUsername')}",
            default=m.get("displayName", ""),
        )
    
    config["userMappings"] = mappings
    return config


def _edit_teams(config: dict) -> dict:
    """Edit team structure."""
    console.print("\n[yellow]Team editing - redefine teams:[/yellow]")
    
    teams = []
    while True:
        team_name = Prompt.ask("Team name (empty to finish)", default="")
        if not team_name:
            break
        
        members_str = Prompt.ask("Members (comma-separated)", default="")
        members = [m.strip() for m in members_str.split(",") if m.strip()]
        teams.append({"name": team_name, "members": members})
    
    config["teams"] = teams
    return config


def _edit_preferences(config: dict) -> dict:
    """Edit preferences."""
    prefs = config.get("preferences", {})
    
    prefs["includeRoasts"] = Confirm.ask(
        "Include roasts?",
        default=prefs.get("includeRoasts", True),
    )
    prefs["topContributorsCount"] = IntPrompt.ask(
        "Top contributors count",
        default=prefs.get("topContributorsCount", 5),
    )
    
    config["preferences"] = prefs
    return config


def _edit_raw_json(config: dict) -> dict:
    """Allow editing raw JSON (basic version)."""
    console.print(
        "\n[yellow]Paste your edited JSON below (end with an empty line):[/yellow]\n"
    )
    
    lines = []
    while True:
        try:
            line = input()
            if not line:
                break
            lines.append(line)
        except EOFError:
            break
    
    if lines:
        try:
            new_config = json.loads("\n".join(lines))
            console.print("[green]JSON parsed successfully![/green]")
            return new_config
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON: {e}[/red]")
            console.print("Keeping original config.")
    
    return config


def save_config(config_dict: dict, output_path: str) -> Path:
    """
    Save configuration to a JSON file.
    
    Args:
        config_dict: Configuration dictionary
        output_path: Path to save the config
        
    Returns:
        Path to saved config file
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(config_dict, f, indent=2)
    
    console.print(f"\n[green]Configuration saved to:[/green] {path}")
    return path


def confirm_proceed() -> bool:
    """Ask user if they want to proceed with video generation."""
    console.print()
    return Confirm.ask(
        "[bold cyan]Proceed with video generation?[/bold cyan]",
        default=True,
    )


def run_interactive_setup(analysis: AnalysisResult) -> dict:
    """
    Run the full interactive setup flow.
    
    Args:
        analysis: Analysis result from MessageAnalyzer
        
    Returns:
        Dictionary of user answers
    """
    setup = InteractiveSetup(analysis)
    return setup.run()
