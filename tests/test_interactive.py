"""Tests for interactive setup functionality."""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from slack_wrapped.parser import SlackParser
from slack_wrapped.message_analyzer import (
    MessageAnalyzer,
    AnalysisResult,
    ChannelAnalysis,
    UserSuggestion,
    TeamSuggestion,
    Highlight,
    Question,
)
from slack_wrapped.config_generator import ConfigGenerator, generate_config
from slack_wrapped.interactive import InteractiveSetup


# Sample messages for testing
SAMPLE_MESSAGES = """2025-01-15T09:30:00Z david.shalom: Good morning team! Starting Q1 with fresh energy
2025-01-15T09:32:00Z alice.smith: Morning David! Ready to ship some features
2025-01-15T10:15:00Z bob.jones: Just deployed the new authentication module
2025-01-15T10:17:00Z david.shalom: Great work Bob! That was a big rock
2025-01-15T14:23:00Z carol.white: PR merged for the user dashboard redesign
"""


class TestMessageAnalyzerBasic:
    """Test MessageAnalyzer basic functionality without LLM."""
    
    def test_basic_stats_extraction(self):
        """Test that basic stats are extracted correctly."""
        parser = SlackParser()
        messages = parser.parse(SAMPLE_MESSAGES)
        
        # Create mock LLM client
        mock_llm = Mock()
        mock_llm.generate_json.return_value = json.dumps({
            "channel_analysis": {
                "likely_name": "product-updates",
                "purpose": "Team updates and announcements",
                "tone": "casual",
                "main_topics": ["shipping", "features"],
                "key_milestones": ["authentication module"],
                "notable_patterns": []
            },
            "team_suggestions": [],
            "user_suggestions": [],
            "highlights": [],
            "questions_for_user": []
        })
        
        analyzer = MessageAnalyzer(mock_llm)
        result = analyzer.analyze(messages)
        
        assert result.total_messages == 5
        assert len(result.usernames) == 4
        assert "david.shalom" in result.usernames
        assert result.message_counts["david.shalom"] == 2
        assert result.year == 2025
    
    def test_user_suggestions_generated(self):
        """Test that user display name suggestions are created."""
        parser = SlackParser()
        messages = parser.parse(SAMPLE_MESSAGES)
        
        mock_llm = Mock()
        mock_llm.generate_json.return_value = json.dumps({
            "channel_analysis": {},
            "team_suggestions": [],
            "user_suggestions": [],
            "highlights": [],
            "questions_for_user": []
        })
        
        analyzer = MessageAnalyzer(mock_llm)
        result = analyzer.analyze(messages)
        
        # Check suggestions are generated
        assert len(result.user_suggestions) == 4
        
        # Check format is correct
        david = next(u for u in result.user_suggestions if u.username == "david.shalom")
        assert david.suggested_name == "David Shalom"
        assert david.message_count == 2


class TestConfigGenerator:
    """Test ConfigGenerator functionality."""
    
    def create_mock_analysis(self) -> AnalysisResult:
        """Create a mock analysis result for testing."""
        return AnalysisResult(
            total_messages=100,
            date_range=(datetime(2025, 1, 1), datetime(2025, 12, 31)),
            usernames=["david.shalom", "alice.smith", "bob.jones"],
            message_counts={
                "david.shalom": 50,
                "alice.smith": 30,
                "bob.jones": 20,
            },
            channel_analysis=ChannelAnalysis(
                likely_name="product-updates",
                purpose="Product announcements",
                tone="casual",
                main_topics=["shipping", "releases"],
                key_milestones=["v2.0 launch"],
            ),
            team_suggestions=[
                TeamSuggestion(
                    name="Backend",
                    members=["david.shalom", "bob.jones"],
                    reasoning="Work on backend features",
                ),
            ],
            user_suggestions=[
                UserSuggestion("david.shalom", "David Shalom", 50, "high"),
                UserSuggestion("alice.smith", "Alice Smith", 30, "high"),
                UserSuggestion("bob.jones", "Bob Jones", 20, "high"),
            ],
            highlights=[
                Highlight("achievement", "Shipped v2.0", "We did it!", "david.shalom"),
            ],
            questions=[],
            messages=[],
        )
    
    def test_generate_config_basic(self):
        """Test basic config generation."""
        analysis = self.create_mock_analysis()
        
        answers = {
            "channel_name": "product-updates",
            "year": 2025,
            "channel_description": "Product announcements",
            "user_mappings": [
                {"slack_username": "david.shalom", "display_name": "David Shalom"},
                {"slack_username": "alice.smith", "display_name": "Alice Smith"},
            ],
            "teams": [{"name": "Backend", "members": ["david.shalom"]}],
            "include_roasts": True,
            "top_contributors_count": 5,
        }
        
        generator = ConfigGenerator(analysis, answers)
        config = generator.generate()
        
        assert config["channel"]["name"] == "product-updates"
        assert config["channel"]["year"] == 2025
        assert len(config["userMappings"]) == 2
        assert config["preferences"]["includeRoasts"] is True
    
    def test_generate_config_with_context(self):
        """Test that context from analysis is included."""
        analysis = self.create_mock_analysis()
        
        answers = {
            "channel_name": "product-updates",
            "year": 2025,
        }
        
        generator = ConfigGenerator(analysis, answers)
        config = generator.generate()
        
        assert config["context"]["channelPurpose"] == "Product announcements"
        assert "shipping" in config["context"]["majorThemes"]
        assert config["context"]["tone"] == "casual"


class TestInteractiveSetup:
    """Test InteractiveSetup class."""
    
    def test_init(self):
        """Test InteractiveSetup initialization."""
        analysis = AnalysisResult(
            total_messages=10,
            date_range=(datetime(2025, 1, 1), datetime(2025, 12, 31)),
            usernames=["user1"],
            message_counts={"user1": 10},
            channel_analysis=ChannelAnalysis(),
            team_suggestions=[],
            user_suggestions=[UserSuggestion("user1", "User One", 10)],
            highlights=[],
            questions=[],
            messages=[],
        )
        
        setup = InteractiveSetup(analysis)
        assert setup.analysis == analysis
        assert setup.answers == {}


class TestWebServerEndpoints:
    """Test web server API endpoints."""
    
    def test_basic_analysis_function(self):
        """Test the basic analysis fallback."""
        from slack_wrapped.web_server import _basic_analysis
        from slack_wrapped.models import SlackMessage
        
        messages = [
            SlackMessage(datetime(2025, 1, 1), "user1", "Hello"),
            SlackMessage(datetime(2025, 1, 2), "user1", "World"),
            SlackMessage(datetime(2025, 1, 3), "user2", "Hi there"),
        ]
        
        result = _basic_analysis(messages)
        
        assert result["total_messages"] == 3
        assert len(result["usernames"]) == 2
        assert result["year"] == 2025
        assert result["message_counts"]["user1"] == 2
        assert result["message_counts"]["user2"] == 1


class TestCLIImports:
    """Test that CLI commands can be imported."""
    
    def test_cli_app_importable(self):
        """Test that CLI app can be imported."""
        from slack_wrapped.cli import app
        assert app is not None
    
    def test_setup_command_exists(self):
        """Test that setup command is registered."""
        from slack_wrapped.cli import setup
        assert setup is not None
        assert callable(setup)
    
    def test_serve_command_exists(self):
        """Test that serve command is registered."""
        from slack_wrapped.cli import serve
        assert serve is not None
        assert callable(serve)
    
    def test_generate_command_exists(self):
        """Test that generate command is registered."""
        from slack_wrapped.cli import generate
        assert generate is not None
        assert callable(generate)


class TestModuleImports:
    """Test that all new modules can be imported."""
    
    def test_message_analyzer_import(self):
        """Test message_analyzer module imports."""
        from slack_wrapped.message_analyzer import (
            MessageAnalyzer,
            AnalysisResult,
            ChannelAnalysis,
            UserSuggestion,
            TeamSuggestion,
            Highlight,
            Question,
            analyze_messages,
        )
        assert MessageAnalyzer is not None
    
    def test_interactive_import(self):
        """Test interactive module imports."""
        from slack_wrapped.interactive import (
            InteractiveSetup,
            review_config,
            save_config,
            confirm_proceed,
            run_interactive_setup,
        )
        assert InteractiveSetup is not None
    
    def test_config_generator_import(self):
        """Test config_generator module imports."""
        from slack_wrapped.config_generator import (
            ConfigGenerator,
            generate_config,
            save_config,
            merge_analysis_with_config,
        )
        assert ConfigGenerator is not None
    
    def test_web_server_import(self):
        """Test web_server module imports."""
        from slack_wrapped.web_server import (
            app,
            run_server,
        )
        assert app is not None
