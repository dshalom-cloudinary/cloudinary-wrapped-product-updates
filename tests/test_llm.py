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
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as excinfo:
                LLMClient()
            
            assert "OpenAI API key required" in str(excinfo.value)
    
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
        # Setup mock response with new enhanced format
        mock_llm.generate_json.return_value = json.dumps({
            "insights": ["Insight 1", "Insight 2"],
            "roasts": ["Roast 1"],
            "records": [{"title": "Champion", "winner": "alice", "stat": "100 msgs", "quip": "Nice!"}],
            "competitions": [],
            "superlatives": [{"title": "The Pro", "winner": "bob", "stat": "50 avg", "quip": "Wow!"}],
        })
        
        generator = InsightsGenerator(mock_llm, config)
        insights = generator.generate_insights(
            stats, contributors,
            top_words=[("shipped", 10)],
            top_emoji=[("🎉", 5)],
        )
        
        assert len(insights.interesting) == 2
        assert len(insights.roasts) == 1
        assert len(insights.records) == 1
        assert len(insights.superlatives) == 1
    
    def test_generate_insights_no_roasts(self, mock_llm, stats, contributors):
        """Test insights without roasts when disabled."""
        config = Config(
            channel=ChannelConfig(name="test", year=2025),
            preferences=Preferences(include_roasts=False),
        )
        
        mock_llm.generate_json.return_value = json.dumps({
            "insights": ["Insight 1"],
            "roasts": ["Roast 1"],  # Should be excluded
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
