"""Tests for video_data_generator module."""

import json
from pathlib import Path
import tempfile

import pytest

from slack_wrapped.video_data_generator import (
    VideoDataGenerator,
    SlackVideoData,
    generate_video_data,
)
from slack_wrapped.models import (
    ChannelStats,
    ContributorStats,
    FunFact,
    QuarterActivity,
    Insights,
    ContentAnalysis,
    ContentAnalysisYearStory,
    ContentAnalysisTopicHighlight,
    ContentAnalysisQuote,
    ContentAnalysisPersonality,
)


@pytest.fixture
def sample_channel_stats():
    """Create sample channel stats."""
    return ChannelStats(
        total_messages=1000,
        total_words=25000,
        total_contributors=15,
        active_days=150,
        messages_by_user={"alice": 200, "bob": 150, "carol": 100},
        messages_by_quarter={"Q1": 250, "Q2": 300, "Q3": 250, "Q4": 200},
        peak_hour=14,
        peak_day="Tuesday",
    )


@pytest.fixture
def sample_quarterly_activity():
    """Create sample quarterly activity."""
    return [
        QuarterActivity(quarter="Q1", messages=250, highlights=["Product launch"]),
        QuarterActivity(quarter="Q2", messages=300, highlights=["Team growth"]),
        QuarterActivity(quarter="Q3", messages=250, highlights=["Feature sprint"]),
        QuarterActivity(quarter="Q4", messages=200, highlights=["Year wrap up"]),
    ]


@pytest.fixture
def sample_contributors():
    """Create sample contributor stats."""
    return [
        ContributorStats(
            username="alice",
            display_name="Alice Chen",
            team="Engineering",
            message_count=200,
            word_count=5000,
            contribution_percent=20.0,
            personality_type="The Leader",
            fun_fact="Most active at 9am",
        ),
        ContributorStats(
            username="bob",
            display_name="Bob Wilson",
            team="Product",
            message_count=150,
            word_count=3750,
            contribution_percent=15.0,
            personality_type="The Thinker",
            fun_fact="Loves emojis",
        ),
        ContributorStats(
            username="carol",
            display_name="Carol Martinez",
            team="Design",
            message_count=100,
            word_count=2500,
            contribution_percent=10.0,
            personality_type="The Creator",
            fun_fact="Early morning poster",
        ),
    ]


@pytest.fixture
def sample_fun_facts():
    """Create sample fun facts."""
    return [
        FunFact(label="Peak Hour", value="2pm", detail="Most messages sent after lunch"),
        FunFact(label="Busiest Day", value="Tuesday", detail="Tuesdays are 30% busier"),
        FunFact(label="Favorite Emoji", value="🚀", detail="Used 156 times"),
    ]


@pytest.fixture
def sample_insights():
    """Create sample insights."""
    return Insights(
        interesting=["Q2 was the most active quarter", "15 contributors this year"],
        funny=["'ASAP' was used 47 times - none were actually ASAP"],
        roasts=["Bob's 'quick updates' averaged 200 words each"],
    )


@pytest.fixture
def sample_content_analysis():
    """Create sample content analysis."""
    return ContentAnalysis(
        year_story=ContentAnalysisYearStory(
            opening="The year began with ambitious goals",
            arc="The team rallied around the product launch",
            climax="September marked the biggest release",
            closing="The year ended with a stronger team",
        ),
        topic_highlights=[
            ContentAnalysisTopicHighlight(
                topic="Product Launch",
                insight="47% of Q2 messages",
                best_quote="We did it!",
                period="Q2 2025",
            ),
        ],
        best_quotes=[
            ContentAnalysisQuote(
                text="Biggest launch ever!",
                author="Alice Chen",
                context="After release",
                period="Q3 2025",
            ),
        ],
        personality_types=[
            ContentAnalysisPersonality(
                username="alice",
                display_name="Alice Chen",
                personality_type="The Launcher",
                evidence="47 'shipped' mentions",
                fun_fact="Never missed a deadline",
            ),
        ],
    )


class TestVideoDataGenerator:
    """Tests for VideoDataGenerator class."""

    def test_init(self):
        """Test generator initialization."""
        generator = VideoDataGenerator("test-channel", 2025)
        assert generator.channel_name == "test-channel"
        assert generator.year == 2025

    def test_generate_basic(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_contributors,
        sample_fun_facts,
    ):
        """Test basic video data generation."""
        generator = VideoDataGenerator("test-channel", 2025)
        
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=sample_contributors,
            fun_facts=sample_fun_facts,
        )
        
        assert isinstance(video_data, SlackVideoData)
        assert video_data.channelStats.totalMessages == 1000
        assert video_data.channelStats.totalWords == 25000
        assert len(video_data.quarterlyActivity) == 4
        assert len(video_data.topContributors) == 3
        assert len(video_data.funFacts) == 3
        assert video_data.meta.channelName == "test-channel"
        assert video_data.meta.year == 2025

    def test_generate_with_insights(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_contributors,
        sample_fun_facts,
        sample_insights,
    ):
        """Test video data generation with insights."""
        generator = VideoDataGenerator("test-channel", 2025)
        
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=sample_contributors,
            fun_facts=sample_fun_facts,
            insights=sample_insights,
        )
        
        assert len(video_data.insights.interesting) == 2
        assert len(video_data.insights.roasts) == 1

    def test_generate_with_content_analysis(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_contributors,
        sample_fun_facts,
        sample_content_analysis,
    ):
        """Test video data generation with content analysis."""
        generator = VideoDataGenerator("test-channel", 2025)
        
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=sample_contributors,
            fun_facts=sample_fun_facts,
            content_analysis=sample_content_analysis,
        )
        
        assert video_data.contentAnalysis is not None
        assert video_data.contentAnalysis.yearStory is not None
        assert len(video_data.contentAnalysis.topicHighlights) == 1
        assert len(video_data.contentAnalysis.bestQuotes) == 1

    def test_top_contributors_limit(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_fun_facts,
    ):
        """Test that only top 5 contributors are included."""
        # Create 10 contributors
        contributors = [
            ContributorStats(
                username=f"user{i}",
                display_name=f"User {i}",
                team="Team",
                message_count=100 - i * 10,
                word_count=2500,
                contribution_percent=10.0 - i,
            )
            for i in range(10)
        ]
        
        generator = VideoDataGenerator("test-channel", 2025)
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=contributors,
            fun_facts=sample_fun_facts,
        )
        
        assert len(video_data.topContributors) == 5
        assert video_data.topContributors[0].username == "user0"

    def test_to_dict(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_contributors,
        sample_fun_facts,
    ):
        """Test conversion to dictionary."""
        generator = VideoDataGenerator("test-channel", 2025)
        
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=sample_contributors,
            fun_facts=sample_fun_facts,
        )
        
        result = video_data.to_dict()
        
        assert "channelStats" in result
        assert "quarterlyActivity" in result
        assert "topContributors" in result
        assert "funFacts" in result
        assert "insights" in result
        assert "meta" in result
        
        # Verify it's JSON serializable
        json_str = json.dumps(result)
        assert len(json_str) > 0

    def test_save(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_contributors,
        sample_fun_facts,
    ):
        """Test saving video data to file."""
        generator = VideoDataGenerator("test-channel", 2025)
        
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=sample_contributors,
            fun_facts=sample_fun_facts,
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video-data.json"
            saved_path = generator.save(video_data, output_path)
            
            assert saved_path.exists()
            
            with open(saved_path) as f:
                loaded = json.load(f)
            
            assert loaded["meta"]["channelName"] == "test-channel"
            assert loaded["channelStats"]["totalMessages"] == 1000

    def test_validate_valid_data(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_contributors,
        sample_fun_facts,
    ):
        """Test validation of valid data."""
        generator = VideoDataGenerator("test-channel", 2025)
        
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=sample_contributors,
            fun_facts=sample_fun_facts,
        )
        
        is_valid, errors = generator.validate(video_data)
        
        assert is_valid
        assert len(errors) == 0

    def test_validate_empty_contributors(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_fun_facts,
    ):
        """Test validation catches empty contributors."""
        generator = VideoDataGenerator("test-channel", 2025)
        
        video_data = generator.generate(
            channel_stats=sample_channel_stats,
            quarterly_activity=sample_quarterly_activity,
            contributors=[],  # Empty
            fun_facts=sample_fun_facts,
        )
        
        is_valid, errors = generator.validate(video_data)
        
        assert not is_valid
        assert "topContributors is empty" in errors


class TestGenerateVideoData:
    """Tests for convenience function."""

    def test_generate_and_save(
        self,
        sample_channel_stats,
        sample_quarterly_activity,
        sample_contributors,
        sample_fun_facts,
    ):
        """Test convenience function with save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video-data.json"
            
            video_data = generate_video_data(
                channel_name="test-channel",
                year=2025,
                channel_stats=sample_channel_stats,
                quarterly_activity=sample_quarterly_activity,
                contributors=sample_contributors,
                fun_facts=sample_fun_facts,
                output_path=output_path,
            )
            
            assert output_path.exists()
            assert video_data.meta.channelName == "test-channel"
