"""Tests for Content Analysis models."""

import pytest
from datetime import datetime
import json

from slack_wrapped.models import (
    ContentAnalysis,
    ContentAnalysisYearStory,
    ContentAnalysisTopicHighlight,
    ContentAnalysisQuote,
    ContentAnalysisPersonality,
    VideoData,
    ChannelStats,
    QuarterActivity,
    ContributorStats,
    FunFact,
    Insights,
    VideoDataMeta,
)


class TestContentAnalysisYearStory:
    """Tests for ContentAnalysisYearStory dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        story = ContentAnalysisYearStory(
            opening="The year began with infrastructure challenges.",
            arc="By Q2, the team pivoted hard to AI.",
            climax="September's launch was the defining moment.",
            closing="Q4 was victory lap territory."
        )
        
        result = story.to_dict()
        
        assert result["opening"] == "The year began with infrastructure challenges."
        assert result["arc"] == "By Q2, the team pivoted hard to AI."
        assert result["climax"] == "September's launch was the defining moment."
        assert result["closing"] == "Q4 was victory lap territory."


class TestContentAnalysisTopicHighlight:
    """Tests for ContentAnalysisTopicHighlight dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary with camelCase."""
        highlight = ContentAnalysisTopicHighlight(
            topic="AI Launch",
            insight="47% of Q4 messages",
            best_quote="The AI is live!",
            period="Q4 2025"
        )
        
        result = highlight.to_dict()
        
        assert result["topic"] == "AI Launch"
        assert result["insight"] == "47% of Q4 messages"
        assert result["bestQuote"] == "The AI is live!"
        assert result["period"] == "Q4 2025"


class TestContentAnalysisQuote:
    """Tests for ContentAnalysisQuote dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        quote = ContentAnalysisQuote(
            text="We shipped it!",
            author="david",
            context="This marked the launch moment",
            period="Q3 2025"
        )
        
        result = quote.to_dict()
        
        assert result["text"] == "We shipped it!"
        assert result["author"] == "david"
        assert result["context"] == "This marked the launch moment"
        assert result["period"] == "Q3 2025"


class TestContentAnalysisPersonality:
    """Tests for ContentAnalysisPersonality dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary with camelCase."""
        personality = ContentAnalysisPersonality(
            username="david.shalom",
            display_name="David Shalom",
            personality_type="The Launcher",
            evidence="Announced 5 product launches throughout the year",
            fun_fact="If shipping were a sport, David would be an Olympian!"
        )
        
        result = personality.to_dict()
        
        assert result["username"] == "david.shalom"
        assert result["displayName"] == "David Shalom"
        assert result["personalityType"] == "The Launcher"
        assert result["evidence"] == "Announced 5 product launches throughout the year"
        assert result["funFact"] == "If shipping were a sport, David would be an Olympian!"


class TestContentAnalysis:
    """Tests for ContentAnalysis dataclass."""
    
    def test_to_dict_complete(self):
        """Test complete conversion to dictionary."""
        content = ContentAnalysis(
            year_story=ContentAnalysisYearStory(
                opening="Opening",
                arc="Arc",
                climax="Climax",
                closing="Closing"
            ),
            topic_highlights=[
                ContentAnalysisTopicHighlight(
                    topic="AI",
                    insight="50%",
                    best_quote="Quote",
                    period="Q4"
                )
            ],
            best_quotes=[
                ContentAnalysisQuote(
                    text="Text",
                    author="author",
                    context="Context",
                    period="Q3"
                )
            ],
            personality_types=[
                ContentAnalysisPersonality(
                    username="david",
                    display_name="David",
                    personality_type="Champion",
                    evidence="Evidence",
                    fun_fact="Fun fact"
                )
            ]
        )
        
        result = content.to_dict()
        
        assert result["yearStory"]["opening"] == "Opening"
        assert len(result["topicHighlights"]) == 1
        assert result["topicHighlights"][0]["topic"] == "AI"
        assert len(result["bestQuotes"]) == 1
        assert len(result["personalityTypes"]) == 1
    
    def test_to_dict_empty(self):
        """Test conversion with minimal data."""
        content = ContentAnalysis()
        
        result = content.to_dict()
        
        assert result["yearStory"] is None
        assert result["topicHighlights"] == []
        assert result["bestQuotes"] == []
        assert result["personalityTypes"] == []
    
    def test_to_dict_no_year_story(self):
        """Test conversion without year story."""
        content = ContentAnalysis(
            topic_highlights=[
                ContentAnalysisTopicHighlight(
                    topic="Topic",
                    insight="Insight",
                    best_quote="Quote",
                    period="Q1"
                )
            ]
        )
        
        result = content.to_dict()
        
        assert result["yearStory"] is None
        assert len(result["topicHighlights"]) == 1


class TestVideoDataWithContentAnalysis:
    """Tests for VideoData with content analysis."""
    
    @pytest.fixture
    def sample_video_data(self):
        """Create sample video data."""
        return VideoData(
            channel_stats=ChannelStats(
                total_messages=100,
                total_words=1000,
                total_contributors=5,
                active_days=50,
                messages_by_user={"david": 50},
                messages_by_quarter={"Q1": 25, "Q2": 25, "Q3": 25, "Q4": 25},
                peak_hour=10,
                peak_day="Tuesday",
                average_message_length=10.0,
            ),
            quarterly_activity=[
                QuarterActivity(quarter="Q1", messages=25),
                QuarterActivity(quarter="Q2", messages=25),
            ],
            top_contributors=[
                ContributorStats(
                    username="david",
                    display_name="David",
                    team="Backend",
                    message_count=50,
                    word_count=500,
                    contribution_percent=50.0,
                    personality_type="Champion",
                    fun_fact="Fun fact!"
                )
            ],
            fun_facts=[
                FunFact(label="Total", value="100", detail="messages")
            ],
            insights=Insights(interesting=["Insight 1"]),
            meta=VideoDataMeta(
                channel_name="product",
                year=2025,
                generated_at="2025-01-30T12:00:00"
            ),
        )
    
    def test_to_dict_without_content_analysis(self, sample_video_data):
        """Test VideoData without content analysis."""
        result = sample_video_data.to_dict()
        
        assert "channelStats" in result
        assert "quarterlyActivity" in result
        assert "topContributors" in result
        assert "contentAnalysis" not in result
    
    def test_to_dict_with_content_analysis(self, sample_video_data):
        """Test VideoData with content analysis."""
        sample_video_data.content_analysis = ContentAnalysis(
            year_story=ContentAnalysisYearStory(
                opening="Opening",
                arc="Arc",
                climax="Climax",
                closing="Closing"
            ),
            topic_highlights=[
                ContentAnalysisTopicHighlight(
                    topic="AI Launch",
                    insight="Big insight",
                    best_quote="Great quote",
                    period="Q3"
                )
            ]
        )
        
        result = sample_video_data.to_dict()
        
        assert "contentAnalysis" in result
        assert result["contentAnalysis"]["yearStory"]["opening"] == "Opening"
        assert len(result["contentAnalysis"]["topicHighlights"]) == 1
    
    def test_to_json_with_content_analysis(self, sample_video_data):
        """Test JSON serialization with content analysis."""
        sample_video_data.content_analysis = ContentAnalysis(
            year_story=ContentAnalysisYearStory(
                opening="Test",
                arc="Arc",
                climax="Climax",
                closing="End"
            )
        )
        
        json_str = sample_video_data.to_json()
        parsed = json.loads(json_str)
        
        assert "contentAnalysis" in parsed
        assert parsed["contentAnalysis"]["yearStory"]["opening"] == "Test"
    
    def test_json_schema_matches_typescript(self, sample_video_data):
        """Test that JSON output matches TypeScript SlackVideoData schema."""
        sample_video_data.content_analysis = ContentAnalysis(
            year_story=ContentAnalysisYearStory(
                opening="O", arc="A", climax="C", closing="E"
            ),
            topic_highlights=[
                ContentAnalysisTopicHighlight(
                    topic="T", insight="I", best_quote="Q", period="P"
                )
            ],
            best_quotes=[
                ContentAnalysisQuote(
                    text="Text", author="Author", context="Context", period="Period"
                )
            ],
            personality_types=[
                ContentAnalysisPersonality(
                    username="user",
                    display_name="User",
                    personality_type="Type",
                    evidence="Evidence",
                    fun_fact="Fact"
                )
            ]
        )
        
        result = sample_video_data.to_dict()
        
        # Check camelCase keys match TypeScript interface
        ca = result["contentAnalysis"]
        assert "yearStory" in ca  # YearStory
        assert "topicHighlights" in ca  # TopicHighlight[]
        assert "bestQuotes" in ca  # Quote[]
        assert "personalityTypes" in ca  # PersonalityType[]
        
        # Check nested camelCase
        assert "bestQuote" in ca["topicHighlights"][0]  # not best_quote
        assert "displayName" in ca["personalityTypes"][0]  # not display_name
        assert "personalityType" in ca["personalityTypes"][0]  # not personality_type
        assert "funFact" in ca["personalityTypes"][0]  # not fun_fact
