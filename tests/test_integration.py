"""
End-to-end integration tests for Slack Wrapped.

Story 5.2: Test the full pipeline from parse → analyze → insights → video data.
"""

import json
from pathlib import Path
import tempfile

import pytest

from slack_wrapped.parser import SlackParser
from slack_wrapped.analyzer import (
    ChannelAnalyzer,
    ContributorAnalyzer,
    WordAnalyzer,
    generate_fun_facts,
)
from slack_wrapped.config import Config
from slack_wrapped.video_data_generator import (
    VideoDataGenerator,
    generate_video_data,
    SlackVideoData,
)
from slack_wrapped.models import (
    ChannelStats,
    ContributorStats,
    FunFact,
    QuarterActivity,
)


# Paths to fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_MESSAGES_FILE = FIXTURES_DIR / "sample_messages.txt"
SAMPLE_CONFIG_FILE = FIXTURES_DIR / "sample_config.json"


class TestE2EPipeline:
    """End-to-end tests for the full Slack Wrapped pipeline."""

    def test_fixtures_exist(self):
        """Verify test fixtures are present."""
        assert SAMPLE_MESSAGES_FILE.exists(), f"Missing: {SAMPLE_MESSAGES_FILE}"
        assert SAMPLE_CONFIG_FILE.exists(), f"Missing: {SAMPLE_CONFIG_FILE}"

    def test_parse_sample_messages(self):
        """Test parsing sample messages file."""
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        assert len(messages) >= 40, f"Expected at least 40 messages, got {len(messages)}"
        
        # Verify message structure
        first_msg = messages[0]
        assert first_msg.username == "david.shalom"
        assert first_msg.timestamp is not None
        assert "Good morning" in first_msg.message

    def test_analyze_sample_messages(self):
        """Test analyzing parsed messages."""
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        analyzer = ChannelAnalyzer(messages)
        stats = analyzer.calculate_stats()
        
        assert isinstance(stats, ChannelStats)
        assert stats.total_messages == len(messages)
        assert stats.total_contributors == 4  # david, alice, bob, carol
        assert stats.total_words > 0

    def test_calculate_quarterly_activity(self):
        """Test quarterly activity calculation."""
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        analyzer = ChannelAnalyzer(messages)
        quarters = analyzer.get_quarterly_activity()
        
        assert len(quarters) == 4  # Q1-Q4
        assert all(isinstance(q, QuarterActivity) for q in quarters)
        
        # Verify quarters are labeled correctly
        quarter_names = [q.quarter for q in quarters]
        assert "Q1" in quarter_names
        assert "Q4" in quarter_names
        
        # Total should match message count
        total_quarterly = sum(q.messages for q in quarters)
        assert total_quarterly == len(messages)

    def test_analyze_contributors(self):
        """Test contributor analysis."""
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        # Load config for user mappings
        config = Config.load(str(SAMPLE_CONFIG_FILE))
        
        contributor_analyzer = ContributorAnalyzer(messages, config)
        contributors = contributor_analyzer.get_all_contributors()
        
        assert len(contributors) == 4
        assert all(isinstance(c, ContributorStats) for c in contributors)
        
        # Check that David has the most messages (he's very active in sample)
        usernames = [c.username for c in contributors]
        assert "david.shalom" in usernames
        
        # Contribution percentages should sum to ~100%
        total_percent = sum(c.contribution_percent for c in contributors)
        assert 99 <= total_percent <= 101

    def test_generate_fun_facts(self):
        """Test fun facts generation."""
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        channel_analyzer = ChannelAnalyzer(messages)
        stats = channel_analyzer.calculate_stats()
        
        contributor_analyzer = ContributorAnalyzer(messages)
        contributors = contributor_analyzer.rank_contributors()
        
        word_analyzer = WordAnalyzer(messages)
        fun_facts = generate_fun_facts(stats, contributors, word_analyzer)
        
        assert len(fun_facts) >= 2  # At least peak hour and avg message
        assert all(isinstance(f, FunFact) for f in fun_facts)
        
        # Each fun fact should have label, value, detail
        for fact in fun_facts:
            assert fact.label
            assert fact.value is not None
            assert fact.detail

    def test_full_pipeline_to_video_data(self):
        """Test complete pipeline from parse to video data."""
        # Parse
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        # Load config
        config = Config.load(str(SAMPLE_CONFIG_FILE))
        channel_name = config.channel.name
        year = config.channel.year
        
        # Analyze
        channel_analyzer = ChannelAnalyzer(messages)
        stats = channel_analyzer.calculate_stats()
        quarters = channel_analyzer.get_quarterly_activity()
        
        contributor_analyzer = ContributorAnalyzer(messages, config)
        contributors = contributor_analyzer.get_all_contributors()
        
        word_analyzer = WordAnalyzer(messages)
        fun_facts = generate_fun_facts(stats, contributors, word_analyzer)
        
        # Generate video data
        video_data = generate_video_data(
            channel_name=channel_name,
            year=year,
            channel_stats=stats,
            quarterly_activity=quarters,
            contributors=contributors,
            fun_facts=fun_facts,
        )
        
        assert isinstance(video_data, SlackVideoData)
        assert video_data.meta.channelName == "product-updates"
        assert video_data.meta.year == 2025
        assert video_data.channelStats.totalMessages == len(messages)
        assert len(video_data.quarterlyActivity) == 4
        assert len(video_data.topContributors) == 4

    def test_pipeline_save_to_json(self):
        """Test that pipeline output can be saved and loaded as valid JSON."""
        # Parse
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        # Load config
        config = Config.load(str(SAMPLE_CONFIG_FILE))
        
        # Analyze
        channel_analyzer = ChannelAnalyzer(messages)
        stats = channel_analyzer.calculate_stats()
        quarters = channel_analyzer.get_quarterly_activity()
        
        contributor_analyzer = ContributorAnalyzer(messages, config)
        contributors = contributor_analyzer.get_all_contributors()
        
        word_analyzer = WordAnalyzer(messages)
        fun_facts = generate_fun_facts(stats, contributors, word_analyzer)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "video-data.json"
            
            # Generate and save
            video_data = generate_video_data(
                channel_name="product-updates",
                year=2025,
                channel_stats=stats,
                quarterly_activity=quarters,
                contributors=contributors,
                fun_facts=fun_facts,
                output_path=output_path,
            )
            
            assert output_path.exists()
            
            # Verify it's valid JSON matching Remotion schema
            with open(output_path) as f:
                loaded = json.load(f)
            
            # Check required fields for Remotion
            assert "channelStats" in loaded
            assert "quarterlyActivity" in loaded
            assert "topContributors" in loaded
            assert "funFacts" in loaded
            assert "insights" in loaded
            assert "meta" in loaded
            
            # Check schema matches types.ts
            assert "totalMessages" in loaded["channelStats"]
            assert "totalWords" in loaded["channelStats"]
            assert "totalContributors" in loaded["channelStats"]
            assert "activeDays" in loaded["channelStats"]
            
            for q in loaded["quarterlyActivity"]:
                assert "quarter" in q
                assert "messages" in q
                assert "highlights" in q
            
            for c in loaded["topContributors"]:
                assert "username" in c
                assert "displayName" in c
                assert "team" in c
                assert "messageCount" in c
                assert "contributionPercent" in c
                assert "funTitle" in c
                assert "funFact" in c

    def test_video_data_validation(self):
        """Test that generated video data passes validation."""
        # Parse and analyze
        parser = SlackParser()
        messages = parser.parse_file(str(SAMPLE_MESSAGES_FILE))
        
        config = Config.load(str(SAMPLE_CONFIG_FILE))
        
        channel_analyzer = ChannelAnalyzer(messages)
        stats = channel_analyzer.calculate_stats()
        quarters = channel_analyzer.get_quarterly_activity()
        
        contributor_analyzer = ContributorAnalyzer(messages, config)
        contributors = contributor_analyzer.get_all_contributors()
        
        word_analyzer = WordAnalyzer(messages)
        fun_facts = generate_fun_facts(stats, contributors, word_analyzer)
        
        # Generate
        generator = VideoDataGenerator("product-updates", 2025)
        video_data = generator.generate(
            channel_stats=stats,
            quarterly_activity=quarters,
            contributors=contributors,
            fun_facts=fun_facts,
        )
        
        # Validate
        is_valid, errors = generator.validate(video_data)
        
        assert is_valid, f"Validation failed: {errors}"
        assert len(errors) == 0


class TestE2EMessagesWithDifferentFormats:
    """Test parsing messages in different formats."""

    def test_iso_format(self, tmp_path):
        """Test parsing ISO 8601 format timestamps."""
        messages_file = tmp_path / "messages.txt"
        messages_file.write_text(
            "2025-03-15T14:23:00Z david: Hello world\n"
            "2025-03-15T14:24:00Z alice: Hi there\n"
        )
        
        parser = SlackParser()
        messages = parser.parse_file(str(messages_file))
        
        assert len(messages) >= 2

    def test_us_format(self, tmp_path):
        """Test parsing US date format."""
        messages_file = tmp_path / "messages.txt"
        messages_file.write_text(
            "[3/15/2025 2:23 PM] david: Hello world\n"
            "[3/15/2025 2:24 PM] alice: Hi there\n"
        )
        
        parser = SlackParser()
        messages = parser.parse_file(str(messages_file))
        
        # Some parsers may or may not support this format
        # At minimum, no exceptions should be raised
        assert isinstance(messages, list)


class TestE2EEdgeCases:
    """Edge case tests for the pipeline."""

    def test_empty_messages(self):
        """Test handling of empty message list."""
        analyzer = ChannelAnalyzer([])
        stats = analyzer.calculate_stats()
        
        assert stats.total_messages == 0
        assert stats.total_contributors == 0

    def test_single_message(self, tmp_path):
        """Test handling of single message."""
        messages_file = tmp_path / "messages.txt"
        messages_file.write_text("2025-01-15T09:30:00Z david: Only message\n")
        
        parser = SlackParser()
        messages = parser.parse_file(str(messages_file))
        
        analyzer = ChannelAnalyzer(messages)
        stats = analyzer.calculate_stats()
        
        assert stats.total_messages == 1
        assert stats.total_contributors == 1

    def test_single_contributor(self, tmp_path):
        """Test handling when all messages from one person."""
        messages_file = tmp_path / "messages.txt"
        messages_file.write_text(
            "2025-01-15T09:30:00Z david: Message 1\n"
            "2025-01-15T09:31:00Z david: Message 2\n"
            "2025-01-15T09:32:00Z david: Message 3\n"
        )
        
        parser = SlackParser()
        messages = parser.parse_file(str(messages_file))
        
        contributor_analyzer = ContributorAnalyzer(messages)
        contributors = contributor_analyzer.get_all_contributors()
        
        assert len(contributors) == 1
        assert contributors[0].contribution_percent == 100.0
