"""Unit tests for SlackParser."""

import pytest
from datetime import datetime

from slack_wrapped.parser import SlackParser, ParserError
from slack_wrapped.models import SlackMessage


class TestSlackParser:
    """Tests for SlackParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SlackParser(default_year=2025)
    
    # ==================== Format Tests ====================
    
    def test_parse_iso_format(self):
        """Test parsing ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ username: message"""
        raw = "2025-03-15T14:23:00Z david.shalom: Shipped the new feature!"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        msg = messages[0]
        assert msg.username == "david.shalom"
        assert msg.message == "Shipped the new feature!"
        assert msg.timestamp.year == 2025
        assert msg.timestamp.month == 3
        assert msg.timestamp.day == 15
        assert msg.timestamp.hour == 14
        assert msg.timestamp.minute == 23
    
    def test_parse_iso_format_with_microseconds(self):
        """Test parsing ISO format with microseconds."""
        raw = "2025-03-15T14:23:00.123456Z david.shalom: Test message"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].username == "david.shalom"
    
    def test_parse_us_format(self):
        """Test parsing US format: [M/D/YYYY H:MM PM] username: message"""
        raw = "[3/15/2025 2:23 PM] david.shalom: Shipped the new feature!"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        msg = messages[0]
        assert msg.username == "david.shalom"
        assert msg.message == "Shipped the new feature!"
        assert msg.timestamp.hour == 14  # 2 PM = 14
        assert msg.timestamp.minute == 23
    
    def test_parse_us_format_am(self):
        """Test parsing US format with AM."""
        raw = "[3/15/2025 9:30 AM] alice.smith: Good morning!"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].timestamp.hour == 9
    
    def test_parse_simple_format(self):
        """Test parsing simple format: username [HH:MM]: message"""
        raw = "david.shalom [14:23]: Shipped the new feature!"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        msg = messages[0]
        assert msg.username == "david.shalom"
        assert msg.message == "Shipped the new feature!"
        assert msg.timestamp.hour == 14
        assert msg.timestamp.minute == 23
    
    def test_parse_time_first_format(self):
        """Test parsing time-first format: HH:MM username: message"""
        raw = "14:23 david.shalom: Quick update"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].username == "david.shalom"
        assert messages[0].message == "Quick update"
    
    def test_parse_date_space_format(self):
        """Test parsing date-space format: YYYY-MM-DD HH:MM username: message"""
        raw = "2025-03-15 14:23 david.shalom: Test message"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].username == "david.shalom"
        assert messages[0].timestamp.year == 2025
        assert messages[0].timestamp.month == 3
    
    # ==================== Multiple Messages ====================
    
    def test_parse_multiple_messages(self):
        """Test parsing multiple messages."""
        raw = """2025-03-15T14:23:00Z david.shalom: First message
2025-03-15T14:24:00Z alice.smith: Second message
2025-03-15T14:25:00Z bob.jones: Third message"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 3
        assert messages[0].username == "david.shalom"
        assert messages[1].username == "alice.smith"
        assert messages[2].username == "bob.jones"
    
    def test_parse_mixed_formats(self):
        """Test parsing messages with different formats."""
        raw = """2025-03-15T14:23:00Z david.shalom: ISO format
[3/15/2025 2:24 PM] alice.smith: US format
bob.jones [14:25]: Simple format"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 3
        assert messages[0].username == "david.shalom"
        assert messages[1].username == "alice.smith"
        assert messages[2].username == "bob.jones"
    
    # ==================== Skip Handling ====================
    
    def test_skip_empty_lines(self):
        """Test that empty lines are skipped."""
        raw = """2025-03-15T14:23:00Z david.shalom: First

2025-03-15T14:24:00Z alice.smith: Second

"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 2
        stats = self.parser.get_stats()
        assert stats["skipped_empty"] >= 1  # At least one empty line skipped
    
    def test_skip_system_messages_joined(self):
        """Test that 'joined the channel' messages are skipped."""
        raw = """2025-03-15T14:23:00Z david.shalom: Real message
2025-03-15T14:24:00Z bot: joined the channel
2025-03-15T14:25:00Z alice.smith: Another message"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 2
        usernames = [m.username for m in messages]
        assert "bot" not in usernames
    
    def test_skip_system_messages_left(self):
        """Test that 'left the channel' messages are skipped."""
        raw = """2025-03-15T14:23:00Z david.shalom: Real message
2025-03-15T14:24:00Z bot: has left the channel"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
    
    # ==================== Error Handling ====================
    
    def test_parse_empty_raises_error(self):
        """Test that parsing empty content raises ParserError."""
        with pytest.raises(ParserError) as excinfo:
            self.parser.parse("")
        
        assert "No messages could be parsed" in str(excinfo.value)
    
    def test_parse_only_empty_lines_raises_error(self):
        """Test that parsing only empty lines raises ParserError."""
        with pytest.raises(ParserError):
            self.parser.parse("\n\n\n")
    
    def test_parse_invalid_format_raises_error(self):
        """Test that completely invalid format raises ParserError."""
        raw = """This is not a valid message format
Neither is this one
No timestamps or usernames here"""
        
        with pytest.raises(ParserError):
            self.parser.parse(raw)
    
    # ==================== Statistics ====================
    
    def test_parse_stats(self):
        """Test that parsing statistics are tracked."""
        raw = """2025-03-15T14:23:00Z david.shalom: Message 1

2025-03-15T14:24:00Z bot: joined the channel
2025-03-15T14:25:00Z alice.smith: Message 2
invalid line here"""
        
        messages = self.parser.parse(raw)
        stats = self.parser.get_stats()
        
        assert stats["parsed_messages"] == 2
        assert stats["skipped_empty"] >= 1
        assert stats["skipped_system"] >= 1
        assert stats["parse_errors"] >= 1
    
    # ==================== Edge Cases ====================
    
    def test_parse_message_with_colons(self):
        """Test parsing messages that contain colons."""
        raw = "2025-03-15T14:23:00Z david.shalom: Check this URL: https://example.com"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert "https://example.com" in messages[0].message
    
    def test_parse_message_with_emoji(self):
        """Test parsing messages with emoji."""
        raw = "2025-03-15T14:23:00Z david.shalom: Great work! 🎉🚀"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert "🎉" in messages[0].message
    
    def test_parse_username_with_dots(self):
        """Test parsing usernames with multiple dots."""
        raw = "2025-03-15T14:23:00Z david.john.shalom: Hello"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].username == "david.john.shalom"
    
    def test_parse_username_with_underscore(self):
        """Test parsing usernames with underscores."""
        raw = "2025-03-15T14:23:00Z david_shalom: Hello"
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].username == "david_shalom"


class TestSlackParserJsonFieldDetection:
    """Tests for JSON/structured data field detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SlackParser(default_year=2025)
    
    def test_skip_camelcase_field_names(self):
        """Test that camelCase field names are skipped (not treated as usernames)."""
        raw = """publicId: some-video-id
cloudName: my-cloud
2025-03-15T14:23:00Z david.shalom: This is a real message"""
        
        messages = self.parser.parse(raw)
        
        # Only the real message should be parsed
        assert len(messages) == 1
        assert messages[0].username == "david.shalom"
        
        # Check that JSON fields were tracked
        stats = self.parser.get_stats()
        assert stats["skipped_json_fields"] == 2
    
    def test_skip_known_field_names(self):
        """Test that known field names (Assignee, Priority, etc.) are skipped."""
        raw = """Assignee: John Doe
Priority: High
Status: In Progress
2025-03-15T14:23:00Z david.shalom: Real Slack message here"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].username == "david.shalom"
        
        stats = self.parser.get_stats()
        assert stats["skipped_json_fields"] >= 2
    
    def test_cloudinary_field_names_skipped(self):
        """Test that Cloudinary-specific field names are not treated as users."""
        raw = """secureDistribution: example.cloudinary.com
adaptiveStreaming: true
videoSources: mp4,webm
2025-03-15T14:23:00Z david.shalom: Shipped the video feature"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 1
        assert messages[0].username == "david.shalom"
    
    def test_json_input_detected(self):
        """Test that pure JSON input raises a helpful error."""
        raw = """{
  "publicId": "video123",
  "cloudName": "my-cloud",
  "resourceType": "video"
}"""
        
        with pytest.raises(ParserError) as excinfo:
            self.parser.parse(raw)
        
        assert "JSON data" in str(excinfo.value)
    
    def test_json_array_detected(self):
        """Test that JSON array input raises an error."""
        raw = """[
  {"username": "david", "message": "hello"},
  {"username": "alice", "message": "hi"}
]"""
        
        with pytest.raises(ParserError) as excinfo:
            self.parser.parse(raw)
        
        assert "JSON" in str(excinfo.value)
    
    def test_real_usernames_not_filtered(self):
        """Test that real usernames are NOT incorrectly filtered."""
        raw = """2025-03-15T14:23:00Z david.shalom: First message
2025-03-15T14:24:00Z alice.smith: Second message
2025-03-15T14:25:00Z bob.jones: Third message
2025-03-15T14:26:00Z carol.white: Fourth message"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 4
        usernames = [m.username for m in messages]
        assert "david.shalom" in usernames
        assert "alice.smith" in usernames
        assert "bob.jones" in usernames
        assert "carol.white" in usernames
    
    def test_name_colon_format_not_filtered(self):
        """Test that 'Name Colon: message' format works for real names."""
        raw = """David Shalom: Hello everyone!
Alice Smith: Hi David!
Bob Jones: Great to see you all"""
        
        messages = self.parser.parse(raw)
        
        assert len(messages) == 3
        # Names should be converted to username format
        usernames = [m.username for m in messages]
        assert "david.shalom" in usernames
        assert "alice.smith" in usernames
        assert "bob.jones" in usernames
    
    def test_many_json_fields_warning(self):
        """Test that many JSON-like fields produces a warning in error message."""
        raw = """publicId: id1
cloudName: name1
resourceType: type1
secureUrl: url1
format: fmt1
width: 100
height: 200"""
        
        with pytest.raises(ParserError) as excinfo:
            self.parser.parse(raw)
        
        # Should mention structured data
        error_msg = str(excinfo.value)
        assert "JSON" in error_msg or "structured data" in error_msg


class TestSlackParserFile:
    """Tests for file parsing functionality."""
    
    def test_parse_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for missing file."""
        parser = SlackParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/messages.txt")
    
    def test_parse_file_success(self, tmp_path):
        """Test parsing from a file."""
        parser = SlackParser()
        
        # Create test file
        test_file = tmp_path / "messages.txt"
        test_file.write_text("""2025-03-15T14:23:00Z david.shalom: Message 1
2025-03-15T14:24:00Z alice.smith: Message 2""")
        
        messages = parser.parse_file(str(test_file))
        
        assert len(messages) == 2
        assert messages[0].username == "david.shalom"
        assert messages[1].username == "alice.smith"
