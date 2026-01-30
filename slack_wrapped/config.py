"""Configuration schema and validation for Slack Wrapped."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ChannelConfig:
    """Channel configuration."""
    
    name: str
    year: int
    description: str = ""


@dataclass
class TeamConfig:
    """Team configuration."""
    
    name: str
    members: list[str] = field(default_factory=list)


@dataclass
class UserMapping:
    """User display name mapping."""
    
    slack_username: str
    display_name: str
    team: str = ""


@dataclass
class Preferences:
    """User preferences for generation."""
    
    include_roasts: bool = True
    top_contributors_count: int = 5


@dataclass
class ChannelContext:
    """Contextual information about the channel content."""
    
    purpose: str = ""  # What this channel is used for
    major_themes: list[str] = field(default_factory=list)  # Main topics discussed
    key_milestones: list[str] = field(default_factory=list)  # Important events/achievements
    tone: str = ""  # casual, formal, celebratory, technical
    highlights: list[str] = field(default_factory=list)  # Notable quotes or messages


@dataclass
class Config:
    """Complete configuration for Slack Wrapped."""
    
    channel: ChannelConfig
    teams: list[TeamConfig] = field(default_factory=list)
    user_mappings: list[UserMapping] = field(default_factory=list)
    preferences: Preferences = field(default_factory=Preferences)
    context: ChannelContext = field(default_factory=ChannelContext)
    
    def get_display_name(self, username: str) -> str:
        """Get display name for a username, or return username if not mapped."""
        for mapping in self.user_mappings:
            if mapping.slack_username == username:
                return mapping.display_name
        return username
    
    def get_team(self, username: str) -> str:
        """Get team for a username."""
        # Check user mappings first
        for mapping in self.user_mappings:
            if mapping.slack_username == username and mapping.team:
                return mapping.team
        
        # Check team memberships
        for team in self.teams:
            if username in team.members:
                return team.name
        
        return ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary."""
        # Parse channel (required)
        channel_data = data.get("channel", {})
        if not channel_data.get("name"):
            raise ValueError("Config missing required field: channel.name")
        if not channel_data.get("year"):
            raise ValueError("Config missing required field: channel.year")
        
        channel = ChannelConfig(
            name=channel_data["name"],
            year=int(channel_data["year"]),
            description=channel_data.get("description", ""),
        )
        
        # Parse teams (optional)
        teams = []
        for team_data in data.get("teams", []):
            teams.append(TeamConfig(
                name=team_data.get("name", ""),
                members=team_data.get("members", []),
            ))
        
        # Parse user mappings (optional)
        user_mappings = []
        for mapping_data in data.get("userMappings", []):
            user_mappings.append(UserMapping(
                slack_username=mapping_data.get("slackUsername", ""),
                display_name=mapping_data.get("displayName", ""),
                team=mapping_data.get("team", ""),
            ))
        
        # Parse preferences (optional)
        prefs_data = data.get("preferences", {})
        preferences = Preferences(
            include_roasts=prefs_data.get("includeRoasts", True),
            top_contributors_count=prefs_data.get("topContributorsCount", 5),
        )
        
        # Parse context (optional) - semantic understanding of the channel
        context_data = data.get("context", {})
        context = ChannelContext(
            purpose=context_data.get("channelPurpose", context_data.get("purpose", "")),
            major_themes=context_data.get("majorThemes", context_data.get("major_themes", [])),
            key_milestones=context_data.get("keyMilestones", context_data.get("key_milestones", [])),
            tone=context_data.get("tone", ""),
            highlights=context_data.get("highlights", []),
        )
        
        return cls(
            channel=channel,
            teams=teams,
            user_mappings=user_mappings,
            preferences=preferences,
            context=context,
        )
    
    @classmethod
    def load(cls, filepath: str) -> "Config":
        """Load configuration from JSON file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")
        
        with open(path, "r") as f:
            data = json.load(f)
        
        return cls.from_dict(data)


class ConfigValidator:
    """Validates configuration files."""
    
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    def validate(self, config_path: str) -> tuple[bool, list[str], list[str]]:
        """
        Validate a config file.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        path = Path(config_path)
        
        # Check file exists
        if not path.exists():
            self.errors.append(f"Config file not found: {config_path}")
            return False, self.errors, self.warnings
        
        # Check file is valid JSON
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False, self.errors, self.warnings
        
        # Validate required fields
        if "channel" not in data:
            self.errors.append("Missing required field: channel")
        else:
            channel = data["channel"]
            if not channel.get("name"):
                self.errors.append("Missing required field: channel.name")
            if not channel.get("year"):
                self.errors.append("Missing required field: channel.year")
            elif not isinstance(channel.get("year"), int):
                try:
                    int(channel["year"])
                except (ValueError, TypeError):
                    self.errors.append("channel.year must be a valid integer")
        
        # Validate teams structure
        if "teams" in data:
            if not isinstance(data["teams"], list):
                self.errors.append("teams must be an array")
            else:
                for i, team in enumerate(data["teams"]):
                    if not isinstance(team, dict):
                        self.errors.append(f"teams[{i}] must be an object")
                    elif not team.get("name"):
                        self.warnings.append(f"teams[{i}] missing name field")
        
        # Validate userMappings structure
        if "userMappings" in data:
            if not isinstance(data["userMappings"], list):
                self.errors.append("userMappings must be an array")
            else:
                for i, mapping in enumerate(data["userMappings"]):
                    if not isinstance(mapping, dict):
                        self.errors.append(f"userMappings[{i}] must be an object")
                    elif not mapping.get("slackUsername"):
                        self.warnings.append(f"userMappings[{i}] missing slackUsername")
        
        # Validate preferences
        if "preferences" in data:
            prefs = data["preferences"]
            if not isinstance(prefs, dict):
                self.errors.append("preferences must be an object")
            else:
                if "includeRoasts" in prefs and not isinstance(prefs["includeRoasts"], bool):
                    self.warnings.append("preferences.includeRoasts should be a boolean")
                if "topContributorsCount" in prefs:
                    try:
                        count = int(prefs["topContributorsCount"])
                        if count < 1 or count > 20:
                            self.warnings.append("preferences.topContributorsCount should be between 1 and 20")
                    except (ValueError, TypeError):
                        self.errors.append("preferences.topContributorsCount must be a number")
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings


# Sample config for documentation
SAMPLE_CONFIG = {
    "channel": {
        "name": "product-updates",
        "description": "Product announcements and updates",
        "year": 2025
    },
    "teams": [
        {
            "name": "Backend",
            "members": ["david.shalom", "alice.smith"]
        },
        {
            "name": "Frontend",
            "members": ["bob.jones", "carol.white"]
        }
    ],
    "userMappings": [
        {
            "slackUsername": "david.shalom",
            "displayName": "David Shalom",
            "team": "Backend"
        },
        {
            "slackUsername": "alice.smith",
            "displayName": "Alice Smith",
            "team": "Backend"
        }
    ],
    "preferences": {
        "includeRoasts": True,
        "topContributorsCount": 5
    }
}


def generate_sample_config(output_path: str = "docs/sample-config.json") -> Path:
    """Generate a sample config file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w") as f:
        json.dump(SAMPLE_CONFIG, f, indent=2)
    
    return path
