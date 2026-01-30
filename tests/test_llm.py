"""Unit tests for LLM client and insights generator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from slack_wrapped.llm_client import LLMClient, LLMError, LLMUsage, create_llm_client
from slack_wrapped.insights_generator import (
    InsightsGenerator,
    generate_all_insights,
)
from slack_wrapped.models import ChannelStats, ContributorStats, Insights
from slack_wrapped.config import Config, ChannelConfig, Preferences


class TestLLMUsage:
    """Tests for LLMUsage class."""
    
    def test_initial_values(self):
        """Test initial zero values."""
        usage = LLMUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
    
    def test_add_usage(self):
        """Test adding usage."""
        usage = LLMUsage()
        usage.add(100, 50)
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
    
    def test_add_multiple(self):
        """Test adding multiple usages."""
        usage = LLMUsage()
        usage.add(100, 50)
        usage.add(200, 100)
        
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 150
        assert usage.total_tokens == 450


class TestLLMClient:
    """Tests for LLMClient class."""
    
    def test_init_without_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        # Explicitly remove OPENAI_API_KEY to test error handling
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            # Also need to clear the key if it exists
            import os
            original_key = os.environ.pop('OPENAI_API_KEY', None)
            try:
                with pytest.raises(ValueError) as excinfo:
                    LLMClient()
                
                assert "OpenAI API key required" in str(excinfo.value)
            finally:
                # Restore original key if it existed
                if original_key:
                    os.environ['OPENAI_API_KEY'] = original_key
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = LLMClient(api_key="test-key")
        assert client.model == LLMClient.DEFAULT_MODEL
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        client = LLMClient(api_key="test-key", model="gpt-5-mini")
        assert client.model == "gpt-5-mini"
    
    @patch('slack_wrapped.llm_client.OpenAI')
    def test_generate_success(self, mock_openai_class):
        """Test successful generation."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        mock_client.chat.completions.create.return_value = mock_response
        
        client = LLMClient(api_key="test-key")
        result = client.generate("Test prompt")
        
        assert result == "Test response"
        assert client.usage.prompt_tokens == 10
        assert client.usage.completion_tokens == 5
    
    def test_retry_wait_exponential(self):
        """Test exponential backoff calculation."""
        client = LLMClient(api_key="test-key")
        
        assert client._get_retry_wait(0) == 1
        assert client._get_retry_wait(1) == 2
        assert client._get_retry_wait(2) == 4
        assert client._get_retry_wait(3) == 8
        assert client._get_retry_wait(10) == 30  # Capped at 30
    
    def test_estimated_cost_calculation(self):
        """Test cost estimation."""
        client = LLMClient(api_key="test-key")
        client.usage.prompt_tokens = 1_000_000
        client.usage.completion_tokens = 100_000
        
        cost = client.get_estimated_cost()
        
        # Should use default model rates
        assert cost > 0


class TestCreateLLMClient:
    """Tests for create_llm_client factory."""
    
    def test_default_model(self):
        """Test default model selection."""
        client = create_llm_client(api_key="test-key")
        assert client.model == LLMClient.DEFAULT_MODEL
    
    def test_dev_model(self):
        """Test dev model selection."""
        client = create_llm_client(api_key="test-key", use_dev_model=True)
        assert client.model == LLMClient.DEV_MODEL
    
    def test_custom_model(self):
        """Test custom model override."""
        client = create_llm_client(api_key="test-key", model="custom-model")
        assert client.model == "custom-model"


class TestInsightsGenerator:
    """Tests for InsightsGenerator class."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        llm = Mock(spec=LLMClient)
        return llm
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            channel=ChannelConfig(name="test-channel", year=2025),
            preferences=Preferences(include_roasts=True),
        )
    
    @pytest.fixture
    def stats(self):
        """Create test stats."""
        return ChannelStats(
            total_messages=100,
            total_words=500,
            total_contributors=5,
            active_days=30,
            messages_by_quarter={"Q1": 25, "Q2": 25, "Q3": 25, "Q4": 25},
            peak_hour=14,
            peak_day="Tuesday",
            average_message_length=5.0,
        )
    
    @pytest.fixture
    def contributors(self):
        """Create test contributors."""
        return [
            ContributorStats(
                username="alice",
                display_name="Alice",
                team="Backend",
                message_count=50,
                word_count=250,
                contribution_percent=50.0,
                average_message_length=5.0,
            ),
            ContributorStats(
                username="bob",
                display_name="Bob",
                team="Frontend",
                message_count=30,
                word_count=150,
                contribution_percent=30.0,
                average_message_length=5.0,
            ),
        ]
    
    def test_generate_insights_success(self, mock_llm, config, stats, contributors):
        """Test successful insights generation."""
        # Setup mock response with new data-driven format
        mock_llm.generate_json.return_value = json.dumps({
            "insights": ["Insight 1", "Insight 2"],
            "roasts": ["Roast 1"],
            "stats": [{"label": "Msg/Day", "value": 1.5, "unit": "messages", "context": "test"}],
            "records": [{"title": "Champion", "winner": "alice", "value": 100, "unit": "messages", "comparison": "50%", "quip": "Nice!"}],
            "competitions": [{"category": "Messages", "participants": ["A", "B"], "scores": [10, 5], "winner": "A", "margin": "+5", "quip": "Win!"}],
            "superlatives": [{"title": "The Pro", "winner": "bob", "value": 50.0, "unit": "words", "percentile": "#1", "quip": "Wow!"}],
        })
        
        generator = InsightsGenerator(mock_llm, config)
        insights = generator.generate_insights(
            stats, contributors,
            top_words=[("shipped", 10)],
            top_emoji=[("🎉", 5)],
        )
        
        assert len(insights.interesting) == 2
        assert len(insights.roasts) == 1
        assert len(insights.stats) == 1
        assert len(insights.records) == 1
        assert len(insights.superlatives) == 1
        assert len(insights.competitions) == 1
        assert insights.records[0].value == 100
        assert insights.superlatives[0].value == 50.0
    
    def test_generate_insights_no_roasts(self, mock_llm, stats, contributors):
        """Test insights without roasts when disabled."""
        config = Config(
            channel=ChannelConfig(name="test", year=2025),
            preferences=Preferences(include_roasts=False),
        )
        
        mock_llm.generate_json.return_value = json.dumps({
            "insights": ["Insight 1"],
            "roasts": ["Roast 1"],  # Should be excluded
            "stats": [],
            "records": [],
            "competitions": [],
            "superlatives": [],
        })
        
        generator = InsightsGenerator(mock_llm, config)
        insights = generator.generate_insights(
            stats, contributors, [], [],
        )
        
        assert len(insights.interesting) == 1
        assert len(insights.roasts) == 0  # Excluded when include_roasts=False
    
    def test_generate_insights_fallback_on_error(self, mock_llm, config, stats, contributors):
        """Test fallback when LLM fails."""
        mock_llm.generate_json.side_effect = LLMError("API error")
        
        generator = InsightsGenerator(mock_llm, config)
        insights = generator.generate_insights(
            stats, contributors, [], [],
        )
        
        # Should get fallback insights
        assert len(insights.interesting) >= 1
        assert "100" in insights.interesting[0] or "messages" in insights.interesting[0]
    
    def test_assign_personalities_success(self, mock_llm, config, contributors):
        """Test successful personality assignment."""
        mock_llm.generate_json.return_value = json.dumps({
            "personalities": [
                {"username": "alice", "title": "The Leader", "funFact": "Sent 50 messages!"},
                {"username": "bob", "title": "The Helper", "funFact": "Always there!"},
            ]
        })
        
        generator = InsightsGenerator(mock_llm, config)
        updated = generator.assign_personalities(
            contributors,
            favorite_words={"alice": [("shipped", 5)], "bob": [("merged", 3)]},
        )
        
        assert updated[0].personality_type == "The Leader"
        assert updated[0].fun_fact == "Sent 50 messages!"
        assert updated[1].personality_type == "The Helper"
    
    def test_assign_personalities_fallback_on_error(self, mock_llm, config, contributors):
        """Test fallback personality assignment on error."""
        mock_llm.generate_json.side_effect = LLMError("API error")
        
        generator = InsightsGenerator(mock_llm, config)
        updated = generator.assign_personalities(contributors, {})
        
        # Should have fallback personalities
        assert updated[0].personality_type != ""
        assert updated[0].fun_fact != ""
    
    def test_parse_json_with_markdown(self, mock_llm, config):
        """Test JSON parsing with markdown code blocks."""
        generator = InsightsGenerator(mock_llm, config)
        
        # Simulate response with markdown
        response = '''```json
{"interesting": ["Test"]}
```'''
        
        result = generator._parse_json_response(response)
        assert result["interesting"] == ["Test"]
    
    def test_parse_json_plain(self, mock_llm, config):
        """Test JSON parsing without markdown."""
        generator = InsightsGenerator(mock_llm, config)
        
        response = '{"interesting": ["Test"]}'
        result = generator._parse_json_response(response)
        assert result["interesting"] == ["Test"]


class TestTwoPassInsights:
    """Tests for two-pass content analysis integration."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM client."""
        mock = Mock(spec=LLMClient)
        mock.model = "gpt-5.2"
        mock.usage = LLMUsage()
        return mock
    
    @pytest.fixture
    def config(self):
        """Create a test config."""
        return Config(
            channel=ChannelConfig(name="test-channel", year=2025),
            teams=[],
            user_mappings=[],
            preferences=Preferences(include_roasts=True, top_contributors_count=5),
        )
    
    @pytest.fixture
    def sample_messages(self):
        """Create sample messages."""
        from datetime import datetime
        from slack_wrapped.models import SlackMessage
        
        return [
            SlackMessage(
                timestamp=datetime(2025, 2, 15, 10, 0),
                username="david",
                message="Shipped the new feature!"
            ),
            SlackMessage(
                timestamp=datetime(2025, 5, 10, 14, 0),
                username="alice",
                message="Great work team!"
            ),
            SlackMessage(
                timestamp=datetime(2025, 9, 1, 9, 0),
                username="david",
                message="AI launch complete!"
            ),
        ]
    
    @pytest.fixture
    def sample_stats(self):
        """Create sample channel stats."""
        return ChannelStats(
            total_messages=100,
            total_words=1000,
            total_contributors=5,
            active_days=50,
            messages_by_quarter={"Q1": 25, "Q2": 25, "Q3": 30, "Q4": 20},
            peak_hour=10,
            peak_day="Tuesday",
            average_message_length=10.0,
        )
    
    @pytest.fixture
    def sample_contributors(self):
        """Create sample contributors."""
        return [
            ContributorStats(
                username="david",
                display_name="David",
                team="Backend",
                message_count=50,
                word_count=500,
                contribution_percent=50.0,
                favorite_words=["shipped"]
            ),
            ContributorStats(
                username="alice",
                display_name="Alice",
                team="Frontend",
                message_count=30,
                word_count=300,
                contribution_percent=30.0,
                favorite_words=["design"]
            ),
        ]
    
    def test_generate_two_pass_insights_success(
        self,
        mock_llm,
        config,
        sample_messages,
        sample_stats,
        sample_contributors
    ):
        """Test successful two-pass insights generation."""
        from slack_wrapped.insights_generator import generate_two_pass_insights
        
        # Mock Pass 1 response (content extraction)
        pass1_response = json.dumps({
            "topics": [{"name": "AI Launch", "frequency": "high", "sample_quote": "AI launch!"}],
            "achievements": [{"description": "Launched AI", "who": "team", "date": "September"}],
            "sentiment": {"overall": "excited", "trend": "improving"},
            "notable_quotes": [],
            "recurring_patterns": []
        })
        
        # Mock Pass 2 response (synthesis)
        pass2_response = json.dumps({
            "yearStory": {
                "opening": "The year began with infrastructure.",
                "arc": "Progress through the quarters.",
                "climax": "AI launch was the peak.",
                "closing": "Celebrated successes."
            },
            "topicHighlights": [
                {"topic": "AI", "insight": "50% of Q3", "bestQuote": "AI launch!", "period": "Q3"}
            ],
            "bestQuotes": [],
            "personalityTypes": [
                {"username": "david", "personalityType": "The Launcher", "evidence": "Shipped AI", "funFact": "Fun!"}
            ],
            "statsHighlights": ["100 messages"],
            "roasts": ["Gentle roast"]
        })
        
        # Set up mock to return different responses
        mock_llm.generate_json.side_effect = [pass1_response, pass1_response, pass1_response, pass2_response]
        
        result = generate_two_pass_insights(
            llm_client=mock_llm,
            config=config,
            messages=sample_messages,
            stats=sample_stats,
            contributors=sample_contributors,
            top_words=[("shipped", 10)],
            top_emoji=[],
            favorite_words={"david": [("shipped", 5)]},
        )
        
        assert len(result.content_summaries) > 0
        assert result.video_insights is not None
        assert result.video_insights.year_story.opening != ""
        assert result.insights is not None
    
    def test_two_pass_result_token_tracking(
        self,
        mock_llm,
        config,
        sample_messages,
        sample_stats,
        sample_contributors
    ):
        """Test that token usage is tracked across passes."""
        from slack_wrapped.insights_generator import generate_two_pass_insights, TwoPassResult
        
        # Mock responses
        mock_response = json.dumps({
            "topics": [],
            "achievements": [],
            "sentiment": {"overall": "neutral", "trend": "stable"},
            "notable_quotes": [],
            "recurring_patterns": [],
            "yearStory": {"opening": "", "arc": "", "climax": "", "closing": ""},
            "topicHighlights": [],
            "bestQuotes": [],
            "personalityTypes": [],
            "statsHighlights": [],
            "roasts": []
        })
        mock_llm.generate_json.return_value = mock_response
        
        result = generate_two_pass_insights(
            llm_client=mock_llm,
            config=config,
            messages=sample_messages,
            stats=sample_stats,
            contributors=sample_contributors,
            top_words=[],
            top_emoji=[],
            favorite_words={},
        )
        
        assert isinstance(result, TwoPassResult)
        assert result.total_tokens == result.pass1_tokens + result.pass2_tokens
    
    def test_convert_to_legacy_insights(self):
        """Test conversion from VideoDataInsights to legacy Insights."""
        from slack_wrapped.insights_generator import _convert_to_legacy_insights
        from slack_wrapped.insight_synthesizer import (
            VideoDataInsights,
            YearStory,
            TopicHighlight,
        )
        
        video_insights = VideoDataInsights(
            year_story=YearStory(
                opening="Opening",
                arc="Arc",
                climax="The big moment!",
                closing="Closing"
            ),
            topic_highlights=[
                TopicHighlight(topic="AI", insight="50% of msgs", best_quote="Quote", period="Q3")
            ],
            roasts=["Gentle roast"],
            stats_highlights=["Stat 1"],
        )
        
        result = _convert_to_legacy_insights(video_insights)
        
        assert isinstance(result, Insights)
        assert "The big moment!" in result.interesting
        assert result.roasts == ["Gentle roast"]
    
    def test_apply_personality_types(self):
        """Test applying personality types to contributors."""
        from slack_wrapped.insights_generator import _apply_personality_types
        from slack_wrapped.insight_synthesizer import PersonalityAssignment
        
        contributors = [
            ContributorStats(
                username="david",
                display_name="David",
                team="Backend",
                message_count=50,
                word_count=500,
                contribution_percent=50.0,
            )
        ]
        
        personalities = [
            PersonalityAssignment(
                username="david",
                display_name="David",
                personality_type="The Champion",
                evidence="Most messages",
                fun_fact="Shipped 10 features!"
            )
        ]
        
        result = _apply_personality_types(contributors, personalities)
        
        assert result[0].personality_type == "The Champion"
        assert result[0].fun_fact == "Shipped 10 features!"
