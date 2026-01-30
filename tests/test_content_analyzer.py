"""Tests for Content Analyzer module."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import json

from slack_wrapped.content_analyzer import (
    ContentAnalyzer,
    ContentChunkSummary,
    MessageChunk,
    TopicExtraction,
    Achievement,
    SentimentAnalysis,
    NotableQuote,
    Pattern,
    MAX_MESSAGES_PER_CHUNK,
    CONTENT_EXTRACTION_SYSTEM_PROMPT,
)
from slack_wrapped.models import SlackMessage
from slack_wrapped.llm_client import LLMClient, LLMError


class TestTopicExtraction:
    """Tests for TopicExtraction dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        topic = TopicExtraction(
            name="AI Launch",
            frequency="high",
            sample_quote="The AI feature is live!"
        )
        result = topic.to_dict()
        
        assert result == {
            "name": "AI Launch",
            "frequency": "high",
            "sample_quote": "The AI feature is live!"
        }


class TestAchievement:
    """Tests for Achievement dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        achievement = Achievement(
            description="Hit 1M users",
            who="team",
            date="March 2025"
        )
        result = achievement.to_dict()
        
        assert result == {
            "description": "Hit 1M users",
            "who": "team",
            "date": "March 2025"
        }


class TestSentimentAnalysis:
    """Tests for SentimentAnalysis dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        sentiment = SentimentAnalysis(
            overall="excited",
            trend="improving",
            notable_moods=["celebratory", "high-energy"]
        )
        result = sentiment.to_dict()
        
        assert result == {
            "overall": "excited",
            "trend": "improving",
            "notable_moods": ["celebratory", "high-energy"]
        }
    
    def test_default_moods(self):
        """Test default empty moods list."""
        sentiment = SentimentAnalysis(
            overall="neutral",
            trend="stable"
        )
        assert sentiment.notable_moods == []


class TestNotableQuote:
    """Tests for NotableQuote dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        quote = NotableQuote(
            text="We shipped it!",
            author="david",
            why_notable="Marked major launch"
        )
        result = quote.to_dict()
        
        assert result == {
            "text": "We shipped it!",
            "author": "david",
            "why_notable": "Marked major launch"
        }


class TestPattern:
    """Tests for Pattern dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        pattern = Pattern(
            name="Daily standups",
            description="Team shares daily updates",
            frequency="daily"
        )
        result = pattern.to_dict()
        
        assert result == {
            "name": "Daily standups",
            "description": "Team shares daily updates",
            "frequency": "daily"
        }


class TestContentChunkSummary:
    """Tests for ContentChunkSummary dataclass."""
    
    def test_to_dict_complete(self):
        """Test full conversion to dictionary."""
        summary = ContentChunkSummary(
            period="Q1 2025",
            message_count=150,
            topics=[TopicExtraction(
                name="Product Launch",
                frequency="high",
                sample_quote="Launching next week!"
            )],
            achievements=[Achievement(
                description="Released v2.0",
                who="team",
                date="February 2025"
            )],
            sentiment=SentimentAnalysis(
                overall="excited",
                trend="improving",
                notable_moods=["busy", "enthusiastic"]
            ),
            notable_quotes=[NotableQuote(
                text="Best quarter ever!",
                author="alice",
                why_notable="Captured team spirit"
            )],
            recurring_patterns=[Pattern(
                name="Celebrations",
                description="Team celebrates wins",
                frequency="weekly"
            )]
        )
        
        result = summary.to_dict()
        
        assert result["period"] == "Q1 2025"
        assert result["messageCount"] == 150
        assert len(result["topics"]) == 1
        assert result["topics"][0]["name"] == "Product Launch"
        assert len(result["achievements"]) == 1
        assert result["sentiment"]["overall"] == "excited"
        assert len(result["notableQuotes"]) == 1
        assert len(result["recurringPatterns"]) == 1
    
    def test_to_dict_empty(self):
        """Test conversion with minimal data."""
        summary = ContentChunkSummary(
            period="Q2 2025",
            message_count=0
        )
        
        result = summary.to_dict()
        
        assert result["period"] == "Q2 2025"
        assert result["messageCount"] == 0
        assert result["topics"] == []
        assert result["sentiment"] is None


class TestMessageChunk:
    """Tests for MessageChunk dataclass."""
    
    def test_message_count(self):
        """Test message count property."""
        messages = [
            SlackMessage(
                timestamp=datetime(2025, 3, 15, 14, 0),
                username="alice",
                message="Hello"
            ),
            SlackMessage(
                timestamp=datetime(2025, 3, 15, 15, 0),
                username="bob",
                message="Hi there"
            )
        ]
        
        chunk = MessageChunk(period="Q1 2025", messages=messages)
        
        assert chunk.message_count == 2


class TestContentAnalyzer:
    """Tests for ContentAnalyzer class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock(spec=LLMClient)
        client.model = "gpt-5.2"
        return client
    
    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        return [
            SlackMessage(
                timestamp=datetime(2025, 1, 15, 10, 0),
                username="david",
                message="Shipped the new feature!"
            ),
            SlackMessage(
                timestamp=datetime(2025, 2, 20, 14, 0),
                username="alice",
                message="Great work team!"
            ),
            SlackMessage(
                timestamp=datetime(2025, 4, 10, 9, 0),
                username="bob",
                message="Q2 planning started"
            ),
            SlackMessage(
                timestamp=datetime(2025, 5, 5, 11, 0),
                username="david",
                message="Hit our milestone!"
            ),
            SlackMessage(
                timestamp=datetime(2025, 7, 15, 16, 0),
                username="alice",
                message="Summer release complete"
            ),
            SlackMessage(
                timestamp=datetime(2025, 10, 1, 10, 0),
                username="bob",
                message="Q4 goals defined"
            ),
        ]
    
    def test_init_default_model(self, mock_llm_client):
        """Test initialization with default model."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        assert analyzer.model == "gpt-5.2-thinking"
        assert analyzer.llm == mock_llm_client
    
    def test_init_custom_model(self, mock_llm_client):
        """Test initialization with custom model."""
        analyzer = ContentAnalyzer(mock_llm_client, model="gpt-4")
        
        assert analyzer.model == "gpt-4"
    
    def test_chunk_messages_empty(self, mock_llm_client):
        """Test chunking with no messages."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        result = analyzer.chunk_messages([], 2025)
        
        assert result == []
    
    def test_chunk_messages_no_matching_year(self, mock_llm_client, sample_messages):
        """Test chunking with no messages in the target year."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        result = analyzer.chunk_messages(sample_messages, 2024)
        
        assert result == []
    
    def test_chunk_messages_by_quarter(self, mock_llm_client, sample_messages):
        """Test chunking by quarter for small datasets."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        chunks = analyzer.chunk_messages(sample_messages, 2025)
        
        # Should have Q1, Q2, Q3, Q4 chunks
        periods = [c.period for c in chunks]
        assert "Q1 2025" in periods
        assert "Q2 2025" in periods
        assert "Q3 2025" in periods
        assert "Q4 2025" in periods
    
    def test_chunk_messages_by_month_large_dataset(self, mock_llm_client):
        """Test chunking by month for large datasets."""
        # Create more than 400 messages (triggers monthly chunking)
        messages = []
        for i in range(450):
            month = (i % 12) + 1
            messages.append(SlackMessage(
                timestamp=datetime(2025, month, 15, 10, 0),
                username=f"user{i % 5}",
                message=f"Message {i}"
            ))
        
        analyzer = ContentAnalyzer(mock_llm_client)
        chunks = analyzer.chunk_messages(messages, 2025)
        
        # Should have monthly chunks
        periods = [c.period for c in chunks]
        assert any("January" in p for p in periods)
        assert any("July" in p for p in periods)
    
    def test_chunk_messages_splits_large_chunks(self, mock_llm_client):
        """Test that large chunks are split."""
        # Create 150 messages all in Q1 (exceeds MAX_MESSAGES_PER_CHUNK)
        messages = []
        for i in range(150):
            messages.append(SlackMessage(
                timestamp=datetime(2025, 2, 15, 10, i % 60),
                username=f"user{i % 5}",
                message=f"Message {i}"
            ))
        
        analyzer = ContentAnalyzer(mock_llm_client)
        chunks = analyzer.chunk_messages(messages, 2025)
        
        # Q1 should be split into parts
        q1_chunks = [c for c in chunks if "Q1" in c.period]
        assert len(q1_chunks) == 2
        assert "Part 1/2" in q1_chunks[0].period
        assert "Part 2/2" in q1_chunks[1].period
    
    def test_extract_content_empty_chunk(self, mock_llm_client):
        """Test extraction from empty chunk."""
        analyzer = ContentAnalyzer(mock_llm_client)
        chunk = MessageChunk(period="Q1 2025", messages=[])
        
        result = analyzer.extract_content(chunk)
        
        assert result.period == "Q1 2025"
        assert result.message_count == 0
        assert result.sentiment.overall == "neutral"
    
    def test_extract_content_success(self, mock_llm_client):
        """Test successful content extraction."""
        # Mock LLM response
        mock_response = json.dumps({
            "period": "Q1 2025",
            "topics": [
                {
                    "name": "Product Launch",
                    "frequency": "high",
                    "sample_quote": "Shipped the feature!"
                }
            ],
            "achievements": [
                {
                    "description": "Launched v2.0",
                    "who": "team",
                    "date": "February 2025"
                }
            ],
            "sentiment": {
                "overall": "excited",
                "trend": "improving",
                "notable_moods": ["celebratory"]
            },
            "notable_quotes": [
                {
                    "text": "Great work team!",
                    "author": "david",
                    "why_notable": "Team celebration"
                }
            ],
            "recurring_patterns": [
                {
                    "name": "Shipping updates",
                    "description": "Regular ship announcements",
                    "frequency": "weekly"
                }
            ]
        })
        mock_llm_client.generate_json.return_value = mock_response
        
        analyzer = ContentAnalyzer(mock_llm_client)
        messages = [
            SlackMessage(
                timestamp=datetime(2025, 2, 15, 10, 0),
                username="david",
                message="Shipped the feature!"
            )
        ]
        chunk = MessageChunk(period="Q1 2025", messages=messages)
        
        result = analyzer.extract_content(chunk)
        
        assert result.period == "Q1 2025"
        assert result.message_count == 1
        assert len(result.topics) == 1
        assert result.topics[0].name == "Product Launch"
        assert result.sentiment.overall == "excited"
        assert len(result.notable_quotes) == 1
    
    def test_extract_content_handles_llm_error(self, mock_llm_client):
        """Test fallback when LLM fails."""
        mock_llm_client.generate_json.side_effect = LLMError("API error")
        
        analyzer = ContentAnalyzer(mock_llm_client)
        messages = [
            SlackMessage(
                timestamp=datetime(2025, 2, 15, 10, 0),
                username="david",
                message="Test message"
            )
        ]
        chunk = MessageChunk(period="Q1 2025", messages=messages)
        
        result = analyzer.extract_content(chunk)
        
        # Should return fallback summary
        assert result.period == "Q1 2025"
        assert result.message_count == 1
        assert result.sentiment.overall == "neutral"
    
    def test_extract_content_handles_json_error(self, mock_llm_client):
        """Test fallback when JSON parsing fails."""
        mock_llm_client.generate_json.return_value = "invalid json"
        
        analyzer = ContentAnalyzer(mock_llm_client)
        messages = [
            SlackMessage(
                timestamp=datetime(2025, 2, 15, 10, 0),
                username="david",
                message="Test message"
            )
        ]
        chunk = MessageChunk(period="Q1 2025", messages=messages)
        
        result = analyzer.extract_content(chunk)
        
        # Should return fallback summary
        assert result.period == "Q1 2025"
        assert result.sentiment.overall == "neutral"
    
    def test_extract_content_uses_correct_model(self, mock_llm_client):
        """Test that extraction uses the content analysis model."""
        mock_response = json.dumps({
            "topics": [],
            "achievements": [],
            "sentiment": {"overall": "neutral", "trend": "stable"},
            "notable_quotes": [],
            "recurring_patterns": []
        })
        mock_llm_client.generate_json.return_value = mock_response
        
        analyzer = ContentAnalyzer(mock_llm_client, model="o3-mini")
        messages = [
            SlackMessage(
                timestamp=datetime(2025, 2, 15, 10, 0),
                username="david",
                message="Test"
            )
        ]
        chunk = MessageChunk(period="Q1 2025", messages=messages)
        
        analyzer.extract_content(chunk)
        
        # Model should be temporarily changed then restored
        mock_llm_client.generate_json.assert_called_once()
    
    def test_analyze_all_content(self, mock_llm_client, sample_messages):
        """Test analyzing all content."""
        mock_response = json.dumps({
            "topics": [{"name": "Topic", "frequency": "high", "sample_quote": "Quote"}],
            "achievements": [],
            "sentiment": {"overall": "excited", "trend": "stable"},
            "notable_quotes": [],
            "recurring_patterns": []
        })
        mock_llm_client.generate_json.return_value = mock_response
        
        analyzer = ContentAnalyzer(mock_llm_client)
        
        results = analyzer.analyze_all_content(sample_messages, 2025)
        
        # Should have summaries for each quarter with messages
        assert len(results) == 4  # Q1, Q2, Q3, Q4
        for summary in results:
            assert isinstance(summary, ContentChunkSummary)
    
    def test_analyze_all_content_empty(self, mock_llm_client):
        """Test analyzing empty message list."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        results = analyzer.analyze_all_content([], 2025)
        
        assert results == []
    
    def test_format_messages_for_llm(self, mock_llm_client):
        """Test message formatting for LLM."""
        analyzer = ContentAnalyzer(mock_llm_client)
        messages = [
            SlackMessage(
                timestamp=datetime(2025, 3, 15, 14, 30),
                username="david",
                message="Hello team!"
            )
        ]
        
        result = analyzer._format_messages_for_llm(messages)
        
        assert "[2025-03-15 14:30] david: Hello team!" in result
    
    def test_parse_extraction_response_with_code_blocks(self, mock_llm_client):
        """Test parsing response with markdown code blocks."""
        response = '''```json
{
    "topics": [{"name": "Test", "frequency": "low", "sample_quote": "Test"}],
    "achievements": [],
    "sentiment": {"overall": "neutral", "trend": "stable"},
    "notable_quotes": [],
    "recurring_patterns": []
}
```'''
        
        analyzer = ContentAnalyzer(mock_llm_client)
        chunk = MessageChunk(period="Q1 2025", messages=[])
        
        result = analyzer._parse_extraction_response(response, chunk)
        
        assert result.topics[0].name == "Test"
    
    def test_parse_extraction_response_camelcase(self, mock_llm_client):
        """Test parsing response with camelCase keys."""
        response = json.dumps({
            "topics": [],
            "achievements": [],
            "sentiment": {"overall": "excited", "trend": "improving", "notableMoods": ["happy"]},
            "notableQuotes": [{"text": "Quote", "author": "user", "whyNotable": "Important"}],
            "recurringPatterns": []
        })
        
        analyzer = ContentAnalyzer(mock_llm_client)
        messages = [SlackMessage(
            timestamp=datetime(2025, 1, 1, 10, 0),
            username="user",
            message="test"
        )]
        chunk = MessageChunk(period="Q1 2025", messages=messages)
        
        result = analyzer._parse_extraction_response(response, chunk)
        
        assert result.sentiment.notable_moods == ["happy"]
        assert len(result.notable_quotes) == 1
        assert result.notable_quotes[0].why_notable == "Important"


class TestContentExtractionPrompts:
    """Tests for prompt templates."""
    
    def test_system_prompt_contains_extraction_categories(self):
        """Test that system prompt contains all extraction categories."""
        assert "TOPICS" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "ACHIEVEMENTS" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "SENTIMENT" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "NOTABLE QUOTES" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "RECURRING PATTERNS" in CONTENT_EXTRACTION_SYSTEM_PROMPT
    
    def test_system_prompt_contains_privacy_guardrails(self):
        """Test that system prompt contains privacy guardrails."""
        assert "PRIVACY" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "PII" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "NEVER extract" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "passwords" in CONTENT_EXTRACTION_SYSTEM_PROMPT.lower()
        assert "API keys" in CONTENT_EXTRACTION_SYSTEM_PROMPT
    
    def test_system_prompt_contains_sentiment_types(self):
        """Test that system prompt documents sentiment types."""
        assert "excited" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "celebratory" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "stressed" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "neutral" in CONTENT_EXTRACTION_SYSTEM_PROMPT
    
    def test_system_prompt_contains_frequency_guide(self):
        """Test that system prompt contains frequency guide."""
        assert "high" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "medium" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "low" in CONTENT_EXTRACTION_SYSTEM_PROMPT
    
    def test_system_prompt_requests_json_output(self):
        """Test that system prompt requests JSON output."""
        assert "JSON" in CONTENT_EXTRACTION_SYSTEM_PROMPT
        assert "Valid JSON only" in CONTENT_EXTRACTION_SYSTEM_PROMPT
    
    def test_prompt_template_contains_placeholders(self):
        """Test that prompt template has required placeholders."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        assert "{period}" in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert "{messages}" in CONTENT_EXTRACTION_PROMPT_TEMPLATE
    
    def test_prompt_template_contains_output_structure(self):
        """Test that prompt template shows expected JSON structure."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        # Check for all required fields in the JSON template
        assert '"topics"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"achievements"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"sentiment"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"notable_quotes"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"recurring_patterns"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
    
    def test_prompt_template_contains_topic_structure(self):
        """Test that prompt template shows topic extraction structure."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        assert '"name"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"frequency"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"sample_quote"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
    
    def test_prompt_template_contains_achievement_structure(self):
        """Test that prompt template shows achievement structure."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        assert '"description"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"who"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"date"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
    
    def test_prompt_template_contains_sentiment_structure(self):
        """Test that prompt template shows sentiment structure."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        assert '"overall"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"trend"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"notable_moods"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
    
    def test_prompt_template_contains_quote_structure(self):
        """Test that prompt template shows quote structure."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        assert '"text"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"author"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"why_notable"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
    
    def test_prompt_template_contains_pattern_structure(self):
        """Test that prompt template shows pattern structure."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        assert '"name"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"description"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        assert '"frequency"' in CONTENT_EXTRACTION_PROMPT_TEMPLATE
    
    def test_prompt_template_provides_guidance_counts(self):
        """Test that prompt template suggests extraction counts."""
        from slack_wrapped.content_analyzer import CONTENT_EXTRACTION_PROMPT_TEMPLATE
        
        # Should suggest 3-7 topics
        assert "3-7" in CONTENT_EXTRACTION_PROMPT_TEMPLATE
        # Should suggest 2-5 quotes
        assert "2-5" in CONTENT_EXTRACTION_PROMPT_TEMPLATE


class TestContentAnalyzerPromptIntegration:
    """Tests for prompt generation and formatting."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock(spec=LLMClient)
        client.model = "gpt-5.2"
        return client
    
    def test_build_extraction_prompt_formats_correctly(self, mock_llm_client):
        """Test that extraction prompt is formatted correctly."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        messages = "[2025-01-15 10:00] david: Hello team!"
        prompt = analyzer._build_extraction_prompt("Q1 2025", messages)
        
        assert "Q1 2025" in prompt
        assert "Hello team!" in prompt
        assert "david" in prompt
    
    def test_build_extraction_prompt_includes_all_sections(self, mock_llm_client):
        """Test that prompt includes all required sections."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        prompt = analyzer._build_extraction_prompt("Q1 2025", "test message")
        
        assert "MESSAGES TO ANALYZE" in prompt
        assert "EXTRACTION INSTRUCTIONS" in prompt
        assert "REQUIRED JSON OUTPUT" in prompt
    
    def test_format_messages_includes_timestamp_and_author(self, mock_llm_client):
        """Test message formatting includes all parts."""
        analyzer = ContentAnalyzer(mock_llm_client)
        
        messages = [
            SlackMessage(
                timestamp=datetime(2025, 3, 15, 14, 30, 0),
                username="alice.smith",
                message="Great job everyone!"
            )
        ]
        
        formatted = analyzer._format_messages_for_llm(messages)
        
        assert "2025-03-15" in formatted
        assert "14:30" in formatted
        assert "alice.smith" in formatted
        assert "Great job everyone!" in formatted
