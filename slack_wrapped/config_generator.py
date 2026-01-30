"""Config generator for Slack Wrapped.

Generates config.json from analysis results and user answers.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from .message_analyzer import AnalysisResult
from .config import Config, ChannelConfig, TeamConfig, UserMapping, Preferences, ChannelContext


class ConfigGenerator:
    """Generates configuration from analysis and user answers."""
    
    def __init__(self, analysis: AnalysisResult, answers: dict):
        """
        Initialize config generator.
        
        Args:
            analysis: Analysis result from MessageAnalyzer
            answers: User answers from interactive setup
        """
        self.analysis = analysis
        self.answers = answers
    
    def generate(self) -> dict:
        """
        Generate configuration dictionary.
        
        Returns:
            Configuration dictionary ready for JSON serialization
        """
        config = {
            "channel": self._build_channel(),
            "teams": self._build_teams(),
            "userMappings": self._build_user_mappings(),
            "preferences": self._build_preferences(),
            "context": self._build_context(),
        }
        
        return config
    
    def generate_config_object(self) -> Config:
        """
        Generate a Config object.
        
        Returns:
            Config instance
        """
        config_dict = self.generate()
        return Config.from_dict(config_dict)
    
    def _build_channel(self) -> dict:
        """Build channel configuration."""
        return {
            "name": self.answers.get("channel_name", "channel"),
            "year": self.answers.get("year", self.analysis.year),
            "description": self.answers.get(
                "channel_description",
                self.analysis.channel_analysis.purpose,
            ),
        }
    
    def _build_teams(self) -> list[dict]:
        """Build teams configuration."""
        teams = self.answers.get("teams", [])
        
        # If no teams from answers, try suggestions
        if not teams and self.analysis.team_suggestions:
            teams = [
                {"name": t.name, "members": t.members}
                for t in self.analysis.team_suggestions
            ]
        
        return teams
    
    def _build_user_mappings(self) -> list[dict]:
        """Build user mappings configuration."""
        mappings = self.answers.get("user_mappings", [])
        
        # Convert to expected format
        result = []
        for m in mappings:
            result.append({
                "slackUsername": m.get("slack_username", m.get("slackUsername", "")),
                "displayName": m.get("display_name", m.get("displayName", "")),
                "team": m.get("team", ""),
            })
        
        # If no mappings from answers, use suggestions
        if not result:
            for user in self.analysis.user_suggestions:
                # Find team for this user
                team = ""
                for t in self.answers.get("teams", []):
                    if user.username in t.get("members", []):
                        team = t.get("name", "")
                        break
                
                result.append({
                    "slackUsername": user.username,
                    "displayName": user.suggested_name,
                    "team": team,
                })
        
        return result
    
    def _build_preferences(self) -> dict:
        """Build preferences configuration."""
        return {
            "includeRoasts": self.answers.get("include_roasts", True),
            "topContributorsCount": self.answers.get("top_contributors_count", 5),
        }
    
    def _build_context(self) -> dict:
        """Build channel context configuration."""
        ca = self.analysis.channel_analysis
        
        # Safely get highlights (handle None or empty list)
        highlights = self.analysis.highlights or []
        
        return {
            "channelPurpose": ca.purpose or self.answers.get("channel_description", ""),
            "majorThemes": ca.main_topics or [],
            "keyMilestones": ca.key_milestones or [],
            "tone": ca.tone or "",
            "highlights": [h.description for h in highlights[:5]],
        }
    
    def save(self, output_path: str) -> Path:
        """
        Save configuration to a JSON file.
        
        Args:
            output_path: Path to save the config
            
        Returns:
            Path to saved config file
        """
        config = self.generate()
        
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(config, f, indent=2)
        
        return path


def generate_config(analysis: AnalysisResult, answers: dict) -> dict:
    """
    Convenience function to generate config from analysis and answers.
    
    Args:
        analysis: Analysis result from MessageAnalyzer
        answers: User answers from interactive setup
        
    Returns:
        Configuration dictionary
    """
    generator = ConfigGenerator(analysis, answers)
    return generator.generate()


def save_config(
    analysis: AnalysisResult,
    answers: dict,
    output_path: str,
) -> Path:
    """
    Generate and save configuration.
    
    Args:
        analysis: Analysis result from MessageAnalyzer
        answers: User answers from interactive setup
        output_path: Path to save the config
        
    Returns:
        Path to saved config file
    """
    generator = ConfigGenerator(analysis, answers)
    return generator.save(output_path)


def merge_analysis_with_config(analysis: AnalysisResult, existing_config: dict) -> dict:
    """
    Merge analysis insights into an existing config.
    
    Useful for enhancing a manually created config with LLM-detected context.
    
    Args:
        analysis: Analysis result from MessageAnalyzer
        existing_config: Existing configuration dictionary
        
    Returns:
        Enhanced configuration dictionary
    """
    config = existing_config.copy()
    
    # Add/enhance context if not present
    if "context" not in config or not config["context"]:
        ca = analysis.channel_analysis
        highlights = analysis.highlights or []
        config["context"] = {
            "channelPurpose": ca.purpose or "",
            "majorThemes": ca.main_topics or [],
            "keyMilestones": ca.key_milestones or [],
            "tone": ca.tone or "",
            "highlights": [h.description for h in highlights[:5]],
        }
    else:
        # Merge with existing context
        ctx = config["context"]
        ca = analysis.channel_analysis
        
        if not ctx.get("channelPurpose") and ca.purpose:
            ctx["channelPurpose"] = ca.purpose
        if not ctx.get("majorThemes") and ca.main_topics:
            ctx["majorThemes"] = ca.main_topics
        if not ctx.get("keyMilestones") and ca.key_milestones:
            ctx["keyMilestones"] = ca.key_milestones
        if not ctx.get("tone") and ca.tone:
            ctx["tone"] = ca.tone
        highlights = analysis.highlights or []
        if not ctx.get("highlights") and highlights:
            ctx["highlights"] = [h.description for h in highlights[:5]]
    
    return config
