"""Unit tests for analyzer module."""

import pytest
from datetime import datetime

from slack_wrapped.analyzer import (
    ChannelAnalyzer,
    ContributorAnalyzer,
    WordAnalyzer,
    generate_fun_facts,
)
from slack_wrapped.models import SlackMessage
from slack_wrapped.config import Config, ChannelConfig, UserMapping


def create_message(
    timestamp: str,
    username: str,
    message: str,
) -> SlackMessage:
    """Helper to create test messages."""
    return SlackMessage(
        timestamp=datetime.fromisoformat(timestamp),
        username=username,
        message=message,
    )


class TestChannelAnalyzer:
    """Tests for ChannelAnalyzer class."""
    
    def test_calculate_stats_empty(self):
        """Test stats calculation with no messages."""
        analyzer = ChannelAnalyzer([])
        stats = analyzer.calculate_stats()
        
        assert stats.total_messages == 0
        assert stats.total_words == 0
        assert stats.total_contributors == 0
        assert stats.active_days == 0
    
    def test_calculate_stats_basic(self):
        """Test basic stats calculation."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "Hello world"),
            create_message("2025-03-15T15:00:00", "bob", "Hi there friend"),
            create_message("2025-03-16T10:00:00", "alice", "Another message here"),
        ]
        
        analyzer = ChannelAnalyzer(messages)
        stats = analyzer.calculate_stats()
        
        assert stats.total_messages == 3
        assert stats.total_words == 8  # 2 + 3 + 3
        assert stats.total_contributors == 2
        assert stats.active_days == 2  # March 15 and 16
    
    def test_messages_by_user(self):
        """Test message count per user."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "One"),
            create_message("2025-03-15T15:00:00", "alice", "Two"),
            create_message("2025-03-15T16:00:00", "bob", "Three"),
        ]
        
        analyzer = ChannelAnalyzer(messages)
        stats = analyzer.calculate_stats()
        
        assert stats.messages_by_user["alice"] == 2
        assert stats.messages_by_user["bob"] == 1
    
    def test_messages_by_quarter(self):
        """Test quarterly distribution."""
        messages = [
            create_message("2025-01-15T14:00:00", "alice", "Q1 message"),
            create_message("2025-02-15T14:00:00", "alice", "Q1 message"),
            create_message("2025-04-15T14:00:00", "bob", "Q2 message"),
            create_message("2025-07-15T14:00:00", "alice", "Q3 message"),
            create_message("2025-10-15T14:00:00", "bob", "Q4 message"),
            create_message("2025-12-15T14:00:00", "bob", "Q4 message"),
        ]
        
        analyzer = ChannelAnalyzer(messages)
        stats = analyzer.calculate_stats()
        
        assert stats.messages_by_quarter["Q1"] == 2
        assert stats.messages_by_quarter["Q2"] == 1
        assert stats.messages_by_quarter["Q3"] == 1
        assert stats.messages_by_quarter["Q4"] == 2
    
    def test_peak_hour(self):
        """Test peak hour calculation."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "Msg"),
            create_message("2025-03-15T14:30:00", "bob", "Msg"),
            create_message("2025-03-15T14:45:00", "alice", "Msg"),
            create_message("2025-03-15T10:00:00", "bob", "Msg"),
        ]
        
        analyzer = ChannelAnalyzer(messages)
        stats = analyzer.calculate_stats()
        
        assert stats.peak_hour == 14  # 3 messages at 14:xx
    
    def test_peak_day(self):
        """Test peak day calculation."""
        # March 2025: 15 = Saturday, 17 = Monday, 18 = Tuesday
        messages = [
            create_message("2025-03-17T14:00:00", "alice", "Monday"),
            create_message("2025-03-18T14:00:00", "bob", "Tuesday"),
            create_message("2025-03-18T15:00:00", "alice", "Tuesday"),
            create_message("2025-03-18T16:00:00", "bob", "Tuesday"),
        ]
        
        analyzer = ChannelAnalyzer(messages)
        stats = analyzer.calculate_stats()
        
        assert stats.peak_day == "Tuesday"
    
    def test_get_quarterly_activity(self):
        """Test quarterly activity list generation."""
        messages = [
            create_message("2025-01-15T14:00:00", "alice", "Q1"),
            create_message("2025-04-15T14:00:00", "bob", "Q2"),
        ]
        
        analyzer = ChannelAnalyzer(messages)
        activity = analyzer.get_quarterly_activity()
        
        assert len(activity) == 4
        assert activity[0].quarter == "Q1"
        assert activity[0].messages == 1
        assert activity[1].quarter == "Q2"
        assert activity[1].messages == 1
        assert activity[2].quarter == "Q3"
        assert activity[2].messages == 0


class TestContributorAnalyzer:
    """Tests for ContributorAnalyzer class."""
    
    def test_rank_contributors_empty(self):
        """Test with no messages."""
        analyzer = ContributorAnalyzer([])
        contributors = analyzer.rank_contributors()
        
        assert len(contributors) == 0
    
    def test_rank_contributors_basic(self):
        """Test basic contributor ranking."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "Message one"),
            create_message("2025-03-15T15:00:00", "alice", "Message two"),
            create_message("2025-03-15T16:00:00", "bob", "Single message"),
        ]
        
        analyzer = ContributorAnalyzer(messages)
        contributors = analyzer.rank_contributors()
        
        assert len(contributors) == 2
        assert contributors[0].username == "alice"
        assert contributors[0].message_count == 2
        assert contributors[1].username == "bob"
        assert contributors[1].message_count == 1
    
    def test_contribution_percent(self):
        """Test contribution percentage calculation."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "One"),
            create_message("2025-03-15T15:00:00", "alice", "Two"),
            create_message("2025-03-15T16:00:00", "alice", "Three"),
            create_message("2025-03-15T17:00:00", "bob", "Four"),
        ]
        
        analyzer = ContributorAnalyzer(messages)
        contributors = analyzer.rank_contributors()
        
        assert contributors[0].contribution_percent == 75.0
        assert contributors[1].contribution_percent == 25.0
    
    def test_word_count(self):
        """Test word count calculation."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "One two three"),
            create_message("2025-03-15T15:00:00", "alice", "Four five"),
        ]
        
        analyzer = ContributorAnalyzer(messages)
        contributors = analyzer.rank_contributors()
        
        assert contributors[0].word_count == 5
    
    def test_top_n_limit(self):
        """Test top N limiting."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "Msg"),
            create_message("2025-03-15T15:00:00", "bob", "Msg"),
            create_message("2025-03-15T16:00:00", "carol", "Msg"),
            create_message("2025-03-15T17:00:00", "dave", "Msg"),
            create_message("2025-03-15T18:00:00", "eve", "Msg"),
        ]
        
        analyzer = ContributorAnalyzer(messages, top_n=3)
        contributors = analyzer.rank_contributors()
        
        assert len(contributors) == 3
    
    def test_config_display_names(self):
        """Test display name from config."""
        messages = [
            create_message("2025-03-15T14:00:00", "david.shalom", "Hello"),
        ]
        
        config = Config(
            channel=ChannelConfig(name="test", year=2025),
            user_mappings=[
                UserMapping(
                    slack_username="david.shalom",
                    display_name="David Shalom",
                    team="Backend",
                )
            ],
        )
        
        analyzer = ContributorAnalyzer(messages, config=config)
        contributors = analyzer.rank_contributors()
        
        assert contributors[0].display_name == "David Shalom"
        assert contributors[0].team == "Backend"


class TestWordAnalyzer:
    """Tests for WordAnalyzer class."""
    
    def test_most_used_words(self):
        """Test most used words extraction."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "shipped the feature shipped"),
            create_message("2025-03-15T15:00:00", "bob", "shipped another update"),
        ]
        
        analyzer = WordAnalyzer(messages)
        words = analyzer.get_most_used_words(top_n=3)
        
        assert len(words) <= 3
        assert words[0][0] == "shipped"
        assert words[0][1] == 3
    
    def test_stop_words_excluded(self):
        """Test that stop words are excluded."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "the the the is is and"),
            create_message("2025-03-15T15:00:00", "bob", "feature release deploy"),
        ]
        
        analyzer = WordAnalyzer(messages)
        words = analyzer.get_most_used_words(top_n=5)
        
        word_list = [w for w, _ in words]
        assert "the" not in word_list
        assert "is" not in word_list
        assert "and" not in word_list
    
    def test_emoji_extraction(self):
        """Test emoji extraction."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "Great work! 🎉🎉🎉"),
            create_message("2025-03-15T15:00:00", "bob", "Awesome 🚀🎉"),
        ]
        
        analyzer = WordAnalyzer(messages)
        emoji = analyzer.get_most_used_emoji(top_n=3)
        
        assert len(emoji) == 2
        assert emoji[0][0] == "🎉"
        assert emoji[0][1] == 4
    
    def test_favorite_words_by_user(self):
        """Test favorite words per user."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "shipped shipped deployed"),
            create_message("2025-03-15T15:00:00", "alice", "shipped feature"),
            create_message("2025-03-15T16:00:00", "bob", "reviewed tested merged"),
        ]
        
        analyzer = WordAnalyzer(messages)
        favorites = analyzer.get_favorite_words_by_user(top_n_users=2, top_n_words=2)
        
        assert "alice" in favorites
        assert favorites["alice"][0][0] == "shipped"
    
    def test_longest_message(self):
        """Test longest message detection."""
        messages = [
            create_message("2025-03-15T14:00:00", "alice", "Short"),
            create_message("2025-03-15T15:00:00", "bob", "This is a much longer message with many words"),
            create_message("2025-03-15T16:00:00", "alice", "Medium length message"),
        ]
        
        analyzer = WordAnalyzer(messages)
        longest = analyzer.get_longest_message()
        
        assert longest.username == "bob"
    
    def test_word_frequency_by_quarter(self):
        """Test word frequency by quarter."""
        messages = [
            create_message("2025-01-15T14:00:00", "alice", "planning planning"),
            create_message("2025-07-15T14:00:00", "bob", "shipping releasing"),
        ]
        
        analyzer = WordAnalyzer(messages)
        quarterly = analyzer.get_word_frequency_by_quarter()
        
        assert quarterly["Q1"]["planning"] == 2
        assert quarterly["Q3"]["shipping"] == 1


class TestGenerateFunFacts:
    """Tests for fun facts generation."""
    
    def test_generate_fun_facts(self):
        """Test fun facts generation."""
        messages = [
            create_message("2025-03-18T14:00:00", "alice", "Hello world shipped 🎉"),
            create_message("2025-03-18T14:30:00", "bob", "Great work shipped!"),
        ]
        
        channel_analyzer = ChannelAnalyzer(messages)
        contributor_analyzer = ContributorAnalyzer(messages)
        word_analyzer = WordAnalyzer(messages)
        
        stats = channel_analyzer.calculate_stats()
        contributors = contributor_analyzer.rank_contributors()
        
        facts = generate_fun_facts(stats, contributors, word_analyzer)
        
        assert len(facts) >= 1
        assert len(facts) <= 5
        
        # Check peak hour fact exists
        labels = [f.label for f in facts]
        assert "Peak Hour" in labels
