"""Tests for Insight Synthesizer module."""

import pytest
from unittest.mock import Mock
import json

from slack_wrapped.insight_synthesizer import (
    InsightSynthesizer,
    VideoDataInsights,
    YearStory,
    TopicHighlight,
    Quote,
    PersonalityAssignment,
    SYNTHESIS_SYSTEM_PROMPT,
    SYNTHESIS_PROMPT_TEMPLATE,
)
from slack_wrapped.content_analyzer import (
    ContentChunkSummary,
    TopicExtraction,
    Achievement,
    SentimentAnalysis,
    NotableQuote,
    Pattern,
)
from slack_wrapped.models import ChannelStats, ContributorStats
from slack_wrapped.llm_client import LLMClient, LLMError


class TestYearStory:
    """Tests for YearStory dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        story = YearStory(
            opening="The year began with infrastructure work.",
            arc="By Q2, the team pivoted to AI features.",
            climax="September's launch was the defining moment.",
            closing="Q4 was celebration territory."
        )
        result = story.to_dict()
        
        assert result["opening"] == "The year began with infrastructure work."
        assert result["arc"] == "By Q2, the team pivoted to AI features."
        assert result["climax"] == "September's launch was the defining moment."
        assert result["closing"] == "Q4 was celebration territory."


class TestTopicHighlight:
    """Tests for TopicHighlight dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        highlight = TopicHighlight(
            topic="AI Launch",
            insight="47% of Q4 messages",
            best_quote="The AI is live!",
            period="Q4 2025"
        )
        result = highlight.to_dict()
        
        assert result["topic"] == "AI Launch"
        assert result["insight"] == "47% of Q4 messages"
        assert result["best_quote"] == "The AI is live!"
        assert result["period"] == "Q4 2025"


class TestQuote:
    """Tests for Quote dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        quote = Quote(
            text="We shipped it!",
            author="david",
            context="Marked the major launch",
            period="Q3 2025"
        )
        result = quote.to_dict()
        
        assert result["text"] == "We shipped it!"
        assert result["author"] == "david"
        assert result["context"] == "Marked the major launch"
        assert result["period"] == "Q3 2025"


class TestPersonalityAssignment:
    """Tests for PersonalityAssignment dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary with camelCase."""
        assignment = PersonalityAssignment(
            username="david.shalom",
            display_name="David Shalom",
            personality_type="The Launcher",
            evidence="Announced 5 product launches",
            fun_fact="If shipping were a sport, David would be an Olympian!"
        )
        result = assignment.to_dict()
        
        assert result["username"] == "david.shalom"
        assert result["displayName"] == "David Shalom"
        assert result["personalityType"] == "The Launcher"
        assert result["evidence"] == "Announced 5 product launches"
        assert result["funFact"] == "If shipping were a sport, David would be an Olympian!"


class TestVideoDataInsights:
    """Tests for VideoDataInsights dataclass."""
    
    def test_to_dict_complete(self):
        """Test full conversion to dictionary."""
        insights = VideoDataInsights(
            year_story=YearStory(
                opening="Opening",
                arc="Arc",
                climax="Climax",
                closing="Closing"
            ),
            topic_highlights=[TopicHighlight(
                topic="AI",
                insight="50% of messages",
                best_quote="Quote",
                period="Q4"
            )],
            best_quotes=[Quote(
                text="Quote text",
                author="author",
                context="Context",
                period="Q3"
            )],
            stats_highlights=["Stat 1", "Stat 2"],
            records=[{"title": "Champion", "winner": "david"}],
            competitions=[{"category": "Messages", "winner": "TeamA"}],
            superlatives=[{"title": "The Novelist", "winner": "alice"}],
            personality_types=[PersonalityAssignment(
                username="david",
                display_name="David",
                personality_type="The Champion",
                evidence="Most messages",
                fun_fact="Fun fact"
            )],
            roasts=["Gentle roast"]
        )
        
        result = insights.to_dict()
        
        assert "yearStory" in result
        assert result["yearStory"]["opening"] == "Opening"
        assert len(result["topicHighlights"]) == 1
        assert len(result["bestQuotes"]) == 1
        assert result["statsHighlights"] == ["Stat 1", "Stat 2"]
        assert len(result["records"]) == 1
        assert len(result["personalityTypes"]) == 1
        assert result["roasts"] == ["Gentle roast"]
    
    def test_to_dict_empty_lists(self):
        """Test with minimal data."""
        insights = VideoDataInsights(
            year_story=YearStory(
                opening="",
                arc="",
                climax="",
                closing=""
            )
        )
        
        result = insights.to_dict()
        
        assert result["topicHighlights"] == []
        assert result["bestQuotes"] == []
        assert result["roasts"] == []


class TestInsightSynthesizer:
    """Tests for InsightSynthesizer class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock(spec=LLMClient)
        client.model = "gpt-5.2"
        return client
    
    @pytest.fixture
    def sample_stats(self):
        """Create sample channel stats."""
        return ChannelStats(
            total_messages=500,
            total_words=5000,
            total_contributors=10,
            active_days=100,
            messages_by_user={"david": 100, "alice": 80},
            messages_by_quarter={"Q1": 100, "Q2": 120, "Q3": 150, "Q4": 130},
            peak_hour=10,
            peak_day="Tuesday",
            average_message_length=10.0
        )
    
    @pytest.fixture
    def sample_contributors(self):
        """Create sample contributors."""
        return [
            ContributorStats(
                username="david",
                display_name="David Shalom",
                team="Backend",
                message_count=100,
                word_count=1000,
                contribution_percent=20.0,
                average_message_length=10.0,
                favorite_words=["shipped", "launch", "done"]
            ),
            ContributorStats(
                username="alice",
                display_name="Alice Smith",
                team="Frontend",
                message_count=80,
                word_count=800,
                contribution_percent=16.0,
                average_message_length=10.0,
                favorite_words=["design", "component", "style"]
            )
        ]
    
    @pytest.fixture
    def sample_content_summaries(self):
        """Create sample content summaries."""
        return [
            ContentChunkSummary(
                period="Q1 2025",
                message_count=100,
                topics=[TopicExtraction(
                    name="Infrastructure",
                    frequency="high",
                    sample_quote="Building the foundation"
                )],
                achievements=[Achievement(
                    description="Set up CI/CD",
                    who="team",
                    date="February 2025"
                )],
                sentiment=SentimentAnalysis(
                    overall="excited",
                    trend="improving",
                    notable_moods=["optimistic"]
                ),
                notable_quotes=[NotableQuote(
                    text="Let's build this right!",
                    author="david",
                    why_notable="Set the tone for the year"
                )],
                recurring_patterns=[Pattern(
                    name="Daily standups",
                    description="Team syncs every morning",
                    frequency="daily"
                )]
            ),
            ContentChunkSummary(
                period="Q3 2025",
                message_count=150,
                topics=[TopicExtraction(
                    name="AI Launch",
                    frequency="high",
                    sample_quote="The AI feature is live!"
                )],
                achievements=[Achievement(
                    description="Launched AI feature",
                    who="team",
                    date="September 2025"
                )],
                sentiment=SentimentAnalysis(
                    overall="celebratory",
                    trend="stable",
                    notable_moods=["excited", "proud"]
                ),
                notable_quotes=[NotableQuote(
                    text="We did it!",
                    author="alice",
                    why_notable="Launch celebration"
                )]
            )
        ]
    
    def test_init_with_roasts(self, mock_llm_client):
        """Test initialization with roasts enabled."""
        synthesizer = InsightSynthesizer(mock_llm_client, include_roasts=True)
        
        assert synthesizer.include_roasts is True
        assert synthesizer.llm == mock_llm_client
    
    def test_init_without_roasts(self, mock_llm_client):
        """Test initialization with roasts disabled."""
        synthesizer = InsightSynthesizer(mock_llm_client, include_roasts=False)
        
        assert synthesizer.include_roasts is False
    
    def test_synthesize_success(
        self,
        mock_llm_client,
        sample_stats,
        sample_contributors,
        sample_content_summaries
    ):
        """Test successful synthesis."""
        mock_response = json.dumps({
            "yearStory": {
                "opening": "The year began with infrastructure work.",
                "arc": "The team built strong foundations.",
                "climax": "September's AI launch was the peak.",
                "closing": "Q4 was celebration time."
            },
            "topicHighlights": [
                {
                    "topic": "AI Launch",
                    "insight": "30% of Q3 messages",
                    "bestQuote": "The AI feature is live!",
                    "period": "Q3 2025"
                }
            ],
            "bestQuotes": [
                {
                    "text": "We did it!",
                    "author": "alice",
                    "context": "Launch celebration",
                    "period": "Q3 2025"
                }
            ],
            "personalityTypes": [
                {
                    "username": "david",
                    "personalityType": "The Builder",
                    "evidence": "Led infrastructure work",
                    "funFact": "Shipped 10 features!"
                }
            ],
            "statsHighlights": ["500 messages exchanged"],
            "roasts": ["The team loves shipping so much they forgot weekends exist"]
        })
        mock_llm_client.generate_json.return_value = mock_response
        
        synthesizer = InsightSynthesizer(mock_llm_client)
        result = synthesizer.synthesize(
            sample_content_summaries,
            sample_stats,
            sample_contributors,
            "product",
            2025
        )
        
        assert result.year_story.opening == "The year began with infrastructure work."
        assert len(result.topic_highlights) == 1
        assert result.topic_highlights[0].topic == "AI Launch"
        assert len(result.best_quotes) == 1
        assert len(result.personality_types) == 1
        assert result.personality_types[0].personality_type == "The Builder"
        assert len(result.roasts) == 1
    
    def test_synthesize_empty_content(
        self,
        mock_llm_client,
        sample_stats,
        sample_contributors
    ):
        """Test synthesis with no content summaries."""
        synthesizer = InsightSynthesizer(mock_llm_client)
        
        result = synthesizer.synthesize(
            [],  # Empty content
            sample_stats,
            sample_contributors,
            "product",
            2025
        )
        
        # Should return fallback insights
        assert result.year_story.opening != ""
        assert len(result.personality_types) > 0
        mock_llm_client.generate_json.assert_not_called()
    
    def test_synthesize_handles_llm_error(
        self,
        mock_llm_client,
        sample_stats,
        sample_contributors,
        sample_content_summaries
    ):
        """Test fallback when LLM fails."""
        mock_llm_client.generate_json.side_effect = LLMError("API error")
        
        synthesizer = InsightSynthesizer(mock_llm_client)
        result = synthesizer.synthesize(
            sample_content_summaries,
            sample_stats,
            sample_contributors,
            "product",
            2025
        )
        
        # Should return fallback
        assert result.year_story.opening != ""
        assert "product" in result.year_story.opening.lower()
    
    def test_synthesize_handles_json_error(
        self,
        mock_llm_client,
        sample_stats,
        sample_contributors,
        sample_content_summaries
    ):
        """Test fallback when JSON parsing fails."""
        mock_llm_client.generate_json.return_value = "invalid json"
        
        synthesizer = InsightSynthesizer(mock_llm_client)
        result = synthesizer.synthesize(
            sample_content_summaries,
            sample_stats,
            sample_contributors,
            "product",
            2025
        )
        
        # Should return fallback
        assert result.year_story.opening != ""
    
    def test_format_content_summaries(
        self,
        mock_llm_client,
        sample_content_summaries
    ):
        """Test content summary formatting."""
        synthesizer = InsightSynthesizer(mock_llm_client)
        
        result = synthesizer._format_content_summaries(sample_content_summaries)
        
        assert "Q1 2025" in result
        assert "Q3 2025" in result
        assert "Infrastructure" in result
        assert "AI Launch" in result
        assert "Building the foundation" in result
        assert "excited" in result
    
    def test_format_channel_stats(self, mock_llm_client, sample_stats):
        """Test channel stats formatting."""
        synthesizer = InsightSynthesizer(mock_llm_client)
        
        result = synthesizer._format_channel_stats(sample_stats)
        
        assert "500" in result
        assert "5,000" in result
        assert "10" in result
        assert "Tuesday" in result
    
    def test_format_contributors(self, mock_llm_client, sample_contributors):
        """Test contributor formatting."""
        synthesizer = InsightSynthesizer(mock_llm_client)
        
        result = synthesizer._format_contributors(sample_contributors)
        
        assert "David Shalom" in result
        assert "david" in result
        assert "100 msgs" in result
        assert "shipped" in result
    
    def test_parse_response_with_code_blocks(
        self,
        mock_llm_client,
        sample_contributors
    ):
        """Test parsing response with markdown code blocks."""
        response = '''```json
{
    "yearStory": {"opening": "Test", "arc": "Arc", "climax": "Climax", "closing": "Closing"},
    "topicHighlights": [],
    "bestQuotes": [],
    "personalityTypes": [],
    "statsHighlights": [],
    "roasts": []
}
```'''
        
        synthesizer = InsightSynthesizer(mock_llm_client)
        result = synthesizer._parse_synthesis_response(response, [], sample_contributors)
        
        assert result.year_story.opening == "Test"
    
    def test_parse_response_snake_case(
        self,
        mock_llm_client,
        sample_contributors
    ):
        """Test parsing response with snake_case keys."""
        response = json.dumps({
            "year_story": {"opening": "Test", "arc": "Arc", "climax": "Climax", "closing": "Closing"},
            "topic_highlights": [{"topic": "AI", "insight": "50%", "best_quote": "Quote", "period": "Q1"}],
            "best_quotes": [{"text": "Text", "author": "david", "context": "Context", "period": "Q1"}],
            "personality_types": [{"username": "david", "personality_type": "Champion", "evidence": "E", "fun_fact": "F"}],
            "stats_highlights": ["Stat"],
            "roasts": ["Roast"]
        })
        
        synthesizer = InsightSynthesizer(mock_llm_client)
        result = synthesizer._parse_synthesis_response(response, [], sample_contributors)
        
        assert result.year_story.opening == "Test"
        assert len(result.topic_highlights) == 1
        assert len(result.best_quotes) == 1
        assert len(result.personality_types) == 1
    
    def test_personality_gets_display_name(
        self,
        mock_llm_client,
        sample_contributors
    ):
        """Test that personality assignment gets display name from contributors."""
        response = json.dumps({
            "yearStory": {"opening": "", "arc": "", "climax": "", "closing": ""},
            "topicHighlights": [],
            "bestQuotes": [],
            "personalityTypes": [
                {"username": "david", "personalityType": "Champion", "evidence": "E", "funFact": "F"}
            ],
            "statsHighlights": [],
            "roasts": []
        })
        
        synthesizer = InsightSynthesizer(mock_llm_client)
        result = synthesizer._parse_synthesis_response(response, [], sample_contributors)
        
        assert result.personality_types[0].display_name == "David Shalom"
    
    def test_fallback_includes_channel_name(
        self,
        mock_llm_client,
        sample_stats,
        sample_contributors
    ):
        """Test that fallback includes channel name."""
        synthesizer = InsightSynthesizer(mock_llm_client)
        
        result = synthesizer._generate_fallback_insights(
            sample_stats,
            sample_contributors,
            "engineering",
            2025
        )
        
        assert "engineering" in result.year_story.opening.lower()
    
    def test_fallback_personality_types(
        self,
        mock_llm_client,
        sample_stats,
        sample_contributors
    ):
        """Test that fallback generates personality types."""
        synthesizer = InsightSynthesizer(mock_llm_client)
        
        result = synthesizer._generate_fallback_insights(
            sample_stats,
            sample_contributors,
            "channel",
            2025
        )
        
        assert len(result.personality_types) == 2
        assert result.personality_types[0].personality_type == "The Champion"
        assert result.personality_types[0].username == "david"


class TestSynthesisPrompts:
    """Tests for synthesis prompt templates."""
    
    def test_system_prompt_contains_key_sections(self):
        """Test that system prompt has key sections."""
        assert "YEAR STORY" in SYNTHESIS_SYSTEM_PROMPT
        assert "TOPIC HIGHLIGHTS" in SYNTHESIS_SYSTEM_PROMPT
        assert "BEST QUOTES" in SYNTHESIS_SYSTEM_PROMPT
        assert "PERSONALITY TYPES" in SYNTHESIS_SYSTEM_PROMPT
        assert "ROASTS" in SYNTHESIS_SYSTEM_PROMPT
    
    def test_system_prompt_has_tone_guidance(self):
        """Test that system prompt sets tone."""
        assert "Celebratory" in SYNTHESIS_SYSTEM_PROMPT
        assert "fun" in SYNTHESIS_SYSTEM_PROMPT.lower()
        assert "never mean" in SYNTHESIS_SYSTEM_PROMPT.lower()
    
    def test_system_prompt_requests_json(self):
        """Test that system prompt requests JSON."""
        assert "JSON" in SYNTHESIS_SYSTEM_PROMPT
    
    def test_prompt_template_has_placeholders(self):
        """Test that prompt template has all placeholders."""
        assert "{channel_name}" in SYNTHESIS_PROMPT_TEMPLATE
        assert "{year}" in SYNTHESIS_PROMPT_TEMPLATE
        assert "{content_summaries}" in SYNTHESIS_PROMPT_TEMPLATE
        assert "{channel_stats}" in SYNTHESIS_PROMPT_TEMPLATE
        assert "{contributors}" in SYNTHESIS_PROMPT_TEMPLATE
        assert "{include_roasts}" in SYNTHESIS_PROMPT_TEMPLATE
    
    def test_prompt_template_has_output_structure(self):
        """Test that prompt template shows output structure."""
        assert '"yearStory"' in SYNTHESIS_PROMPT_TEMPLATE
        assert '"topicHighlights"' in SYNTHESIS_PROMPT_TEMPLATE
        assert '"bestQuotes"' in SYNTHESIS_PROMPT_TEMPLATE
        assert '"personalityTypes"' in SYNTHESIS_PROMPT_TEMPLATE
