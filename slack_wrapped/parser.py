"""Message parser for Slack Wrapped.

Parses various Slack message formats into structured SlackMessage objects.
"""

import re
from datetime import datetime
from typing import Optional
from pathlib import Path

from .models import SlackMessage


class ParserError(Exception):
    """Raised when message parsing fails."""
    pass


class SlackParser:
    """Parses raw Slack messages from various formats."""
    
    # Pattern 1: ISO format - "2025-03-15T14:23:00Z david.shalom: Message"
    PATTERN_ISO = re.compile(
        r'^(\d{4}-\d{2}-\d{2}T[\d:]+(?:\.\d+)?Z?)\s+(\S+):\s*(.+)$'
    )
    
    # Pattern 2: US format - "[3/15/2025 2:23 PM] david.shalom: Message"
    PATTERN_US = re.compile(
        r'^\[(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)\]\s+(\S+):\s*(.+)$',
        re.IGNORECASE
    )
    
    # Pattern 3: Simple format - "david.shalom [14:23]: Message"
    PATTERN_SIMPLE = re.compile(
        r'^(\S+)\s+\[(\d{2}:\d{2}(?::\d{2})?)\]:\s*(.+)$'
    )
    
    # Pattern 4: Timestamp + username - "14:23 david.shalom: Message"
    PATTERN_TIME_FIRST = re.compile(
        r'^(\d{2}:\d{2}(?::\d{2})?)\s+(\S+):\s*(.+)$'
    )
    
    # Pattern 5: Date prefix - "2025-03-15 14:23 david.shalom: Message"
    PATTERN_DATE_SPACE = re.compile(
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s+(\S+):\s*(.+)$'
    )
    
    # System message patterns to skip
    SYSTEM_PATTERNS = [
        re.compile(r'^(joined|left)\s+the\s+channel', re.IGNORECASE),
        re.compile(r'^(has\s+joined|has\s+left)', re.IGNORECASE),
        re.compile(r'^This\s+channel\s+was\s+created', re.IGNORECASE),
        re.compile(r'^Channel\s+(created|archived)', re.IGNORECASE),
        re.compile(r'^set\s+the\s+channel\s+(topic|purpose|description)', re.IGNORECASE),
    ]
    
    def __init__(self, default_year: int = 2025):
        """
        Initialize parser.
        
        Args:
            default_year: Year to use when parsing time-only formats
        """
        self.default_year = default_year
        self.stats = {
            "total_lines": 0,
            "parsed_messages": 0,
            "skipped_empty": 0,
            "skipped_system": 0,
            "parse_errors": 0,
        }
    
    def parse(self, raw_text: str) -> list[SlackMessage]:
        """
        Parse raw text into SlackMessage objects.
        
        Args:
            raw_text: Raw message text, one message per line
            
        Returns:
            List of parsed SlackMessage objects
            
        Raises:
            ParserError: If no messages could be parsed
        """
        self.stats = {
            "total_lines": 0,
            "parsed_messages": 0,
            "skipped_empty": 0,
            "skipped_system": 0,
            "parse_errors": 0,
        }
        
        messages = []
        lines = raw_text.strip().split('\n')
        self.stats["total_lines"] = len(lines)
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                self.stats["skipped_empty"] += 1
                continue
            
            # Try to parse the line
            message = self._parse_line(line)
            
            if message:
                # Check if it's a system message
                if self._is_system_message(message.message):
                    self.stats["skipped_system"] += 1
                    continue
                    
                messages.append(message)
                self.stats["parsed_messages"] += 1
            else:
                self.stats["parse_errors"] += 1
        
        if not messages:
            raise ParserError(
                f"No messages could be parsed. "
                f"Total lines: {self.stats['total_lines']}, "
                f"Empty: {self.stats['skipped_empty']}, "
                f"System: {self.stats['skipped_system']}, "
                f"Parse errors: {self.stats['parse_errors']}. "
                f"Expected format: '[timestamp] username: message' or 'username [time]: message'"
            )
        
        return messages
    
    def _parse_line(self, line: str) -> Optional[SlackMessage]:
        """Try to parse a single line using all known patterns."""
        
        # Try Pattern 1: ISO format
        match = self.PATTERN_ISO.match(line)
        if match:
            timestamp_str, username, message = match.groups()
            timestamp = self._parse_iso_timestamp(timestamp_str)
            if timestamp:
                return SlackMessage(timestamp=timestamp, username=username, message=message)
        
        # Try Pattern 2: US format
        match = self.PATTERN_US.match(line)
        if match:
            timestamp_str, username, message = match.groups()
            timestamp = self._parse_us_timestamp(timestamp_str)
            if timestamp:
                return SlackMessage(timestamp=timestamp, username=username, message=message)
        
        # Try Pattern 3: Simple format (username first)
        match = self.PATTERN_SIMPLE.match(line)
        if match:
            username, time_str, message = match.groups()
            timestamp = self._parse_time_only(time_str)
            return SlackMessage(timestamp=timestamp, username=username, message=message)
        
        # Try Pattern 4: Time first
        match = self.PATTERN_TIME_FIRST.match(line)
        if match:
            time_str, username, message = match.groups()
            timestamp = self._parse_time_only(time_str)
            return SlackMessage(timestamp=timestamp, username=username, message=message)
        
        # Try Pattern 5: Date with space
        match = self.PATTERN_DATE_SPACE.match(line)
        if match:
            timestamp_str, username, message = match.groups()
            timestamp = self._parse_date_space_timestamp(timestamp_str)
            if timestamp:
                return SlackMessage(timestamp=timestamp, username=username, message=message)
        
        return None
    
    def _parse_iso_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse ISO 8601 timestamp."""
        try:
            # Remove trailing Z and handle microseconds
            ts = timestamp_str.rstrip('Z')
            if '.' in ts:
                return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    
    def _parse_us_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse US format timestamp (M/D/YYYY H:MM AM/PM)."""
        try:
            # Try with seconds
            try:
                return datetime.strptime(timestamp_str.strip(), "%m/%d/%Y %I:%M:%S %p")
            except ValueError:
                pass
            
            # Try without seconds
            return datetime.strptime(timestamp_str.strip(), "%m/%d/%Y %I:%M %p")
        except ValueError:
            return None
    
    def _parse_time_only(self, time_str: str) -> datetime:
        """Parse time-only format, using default year."""
        try:
            # Try with seconds
            try:
                time_obj = datetime.strptime(time_str, "%H:%M:%S")
            except ValueError:
                time_obj = datetime.strptime(time_str, "%H:%M")
            
            # Use default date with parsed time
            return datetime(
                self.default_year, 1, 1,
                time_obj.hour, time_obj.minute, time_obj.second
            )
        except ValueError:
            return datetime(self.default_year, 1, 1, 12, 0, 0)
    
    def _parse_date_space_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse date-space-time format (YYYY-MM-DD HH:MM:SS)."""
        try:
            # Try with seconds
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
            
            # Try without seconds
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    
    def _is_system_message(self, message: str) -> bool:
        """Check if message is a system message."""
        for pattern in self.SYSTEM_PATTERNS:
            if pattern.search(message):
                return True
        return False
    
    def parse_file(self, filepath: str) -> list[SlackMessage]:
        """
        Parse messages from a file.
        
        Args:
            filepath: Path to the raw messages file
            
        Returns:
            List of parsed SlackMessage objects
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Message file not found: {filepath}")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return self.parse(content)
    
    def get_stats(self) -> dict:
        """Get parsing statistics."""
        return self.stats.copy()
