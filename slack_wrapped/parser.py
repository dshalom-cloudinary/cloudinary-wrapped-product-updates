"""Message parser for Slack Wrapped.

Parses various Slack message formats into structured SlackMessage objects.
"""

import re
import json
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from .models import SlackMessage

logger = logging.getLogger(__name__)


# Known JSON/structured data field names that should NOT be treated as usernames
# These are common in Cloudinary, Jira, and other API exports
KNOWN_FIELD_NAMES = {
    # Cloudinary fields
    'publicId', 'cloudName', 'resourceType', 'assetType', 'secureUrl', 'url',
    'format', 'width', 'height', 'bytes', 'duration', 'createdAt', 'updatedAt',
    'privateCdn', 'secureDistribution', 'sourceTypes', 'adaptiveStreaming',
    'textTracks', 'subtitles', 'chapters', 'videoSources', 'profile',
    # Jira/project management fields
    'Assignee', 'Priority', 'Status', 'Type', 'Motivation', 'Note',
    'Description', 'Reporter', 'Creator', 'Labels', 'Sprint', 'Epic',
    # Generic JSON fields
    'id', 'name', 'value', 'type', 'data', 'config', 'options', 'settings',
    'title', 'description', 'label', 'download', 'strategy',
}


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
    
    # Pattern 6: Slack copy-paste format - "David Shalom  10:23 AM" followed by message on next line
    # This is handled specially in multi-line mode
    PATTERN_SLACK_HEADER = re.compile(
        r'^([A-Za-z][A-Za-z0-9\s\.\-_]+?)\s{2,}(\d{1,2}:\d{2}\s*[AP]M|\d{1,2}:\d{2})$',
        re.IGNORECASE
    )
    
    # Pattern 7: Discord-like format - "username — Today at 10:23 AM" or "username — 01/15/2025 10:23 AM"
    PATTERN_DISCORD = re.compile(
        r'^([A-Za-z][A-Za-z0-9\s\.\-_]+?)\s*[—–-]\s*(?:Today at\s+)?(\d{1,2}:\d{2}\s*[AP]M|\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*[AP]M?)$',
        re.IGNORECASE
    )
    
    # Pattern 8: Simple username: message (no timestamp) - "david.shalom: Hello everyone"
    PATTERN_NO_TIMESTAMP = re.compile(
        r'^([A-Za-z][A-Za-z0-9\.\-_]{2,}):\s+(.+)$'
    )
    
    # Pattern 9: Slack export JSON-style - will be handled separately
    # Pattern 10: Name with spaces and colon - "David Shalom: Hello everyone"
    PATTERN_NAME_COLON = re.compile(
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+):\s+(.+)$'
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
        self.failed_lines: list[str] = []  # Store sample of failed lines for debugging
        self.debug_mode = False
    
    def parse(self, raw_text: str, debug: bool = False) -> list[SlackMessage]:
        """
        Parse raw text into SlackMessage objects.
        
        Args:
            raw_text: Raw message text, one message per line
            debug: If True, log detailed parsing information
            
        Returns:
            List of parsed SlackMessage objects
            
        Raises:
            ParserError: If no messages could be parsed
        """
        self.debug_mode = debug
        self.stats = {
            "total_lines": 0,
            "parsed_messages": 0,
            "skipped_empty": 0,
            "skipped_system": 0,
            "skipped_json_fields": 0,
            "parse_errors": 0,
        }
        self.failed_lines = []
        
        # Check if input looks like JSON
        stripped = raw_text.strip()
        if self._looks_like_json(stripped):
            raise ParserError(
                "Input appears to be JSON data, not Slack messages.\n\n"
                "Expected formats:\n"
                "  - 2025-01-15T09:30:00Z username: message\n"
                "  - [1/15/2025 9:30 AM] username: message\n"
                "  - David Shalom: message\n\n"
                "If you have a Slack JSON export, you need to convert it to text format first.\n"
                "See the documentation for supported message formats."
            )
        
        messages = []
        lines = stripped.split('\n')
        self.stats["total_lines"] = len(lines)
        
        logger.info(f"Starting to parse {len(lines)} lines")
        
        # First, try to detect the format from sample lines
        detected_format = self._detect_format(lines[:50])
        if detected_format:
            logger.info(f"Detected message format: {detected_format}")
        
        # Try multi-line parsing for Slack copy-paste format
        if detected_format == "slack_multiline":
            messages = self._parse_multiline_slack(lines)
            if messages:
                self.stats["parsed_messages"] = len(messages)
                logger.info(f"Parsed {len(messages)} messages using multi-line Slack format")
                return messages
        
        # Standard line-by-line parsing
        prev_json_fields = 0
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                self.stats["skipped_empty"] += 1
                continue
            
            # Track JSON field count before parsing
            prev_json_fields = self.stats["skipped_json_fields"]
            
            # Try to parse the line
            message = self._parse_line(line)
            
            if message:
                # Check if it's a system message
                if self._is_system_message(message.message):
                    self.stats["skipped_system"] += 1
                    if self.debug_mode:
                        logger.debug(f"Line {i+1}: Skipped system message: {line[:80]}")
                    continue
                    
                messages.append(message)
                self.stats["parsed_messages"] += 1
                if self.debug_mode and self.stats["parsed_messages"] <= 3:
                    logger.debug(f"Line {i+1}: Successfully parsed: {line[:80]}")
            else:
                # Check if it was skipped as a JSON field (don't count as parse error)
                if self.stats["skipped_json_fields"] > prev_json_fields:
                    if self.debug_mode:
                        logger.debug(f"Line {i+1}: Skipped as JSON field: {line[:80]}")
                    continue
                
                self.stats["parse_errors"] += 1
                # Store sample of failed lines (up to 10)
                if len(self.failed_lines) < 10:
                    self.failed_lines.append(line[:200])
                if self.debug_mode and self.stats["parse_errors"] <= 5:
                    logger.debug(f"Line {i+1}: Failed to parse: {line[:80]}")
        
        # Log parsing summary
        logger.info(
            f"Parsing complete: {self.stats['parsed_messages']} messages parsed, "
            f"{self.stats['parse_errors']} failed, "
            f"{self.stats['skipped_empty']} empty, "
            f"{self.stats['skipped_system']} system, "
            f"{self.stats['skipped_json_fields']} JSON fields skipped"
        )
        
        if not messages:
            # Build detailed error with sample failed lines
            error_msg = (
                f"No messages could be parsed. "
                f"Total lines: {self.stats['total_lines']}, "
                f"Empty: {self.stats['skipped_empty']}, "
                f"System: {self.stats['skipped_system']}, "
                f"JSON fields skipped: {self.stats['skipped_json_fields']}, "
                f"Parse errors: {self.stats['parse_errors']}."
            )
            
            # Check if many lines looked like JSON fields
            if self.stats['skipped_json_fields'] > 5:
                error_msg += (
                    "\n\n⚠️  Many lines looked like JSON field names (publicId, cloudName, etc.).\n"
                    "This suggests you may be providing structured data instead of Slack messages.\n"
                    "Make sure your input file contains actual Slack messages, not JSON exports."
                )
            
            if self.failed_lines:
                error_msg += "\n\nSample lines that failed to parse:\n"
                for i, line in enumerate(self.failed_lines[:5], 1):
                    error_msg += f"  {i}. {line}\n"
                error_msg += "\nExpected formats:\n"
                error_msg += "  - 2025-01-15T09:30:00Z username: message\n"
                error_msg += "  - [1/15/2025 9:30 AM] username: message\n"
                error_msg += "  - username [09:30]: message\n"
                error_msg += "  - David Shalom: message\n"
            
            logger.error(error_msg)
            raise ParserError(error_msg)
        
        return messages
    
    def _looks_like_json(self, text: str) -> bool:
        """
        Check if the input text looks like JSON data.
        
        Returns True if:
        - Text starts with { or [
        - Text contains many JSON-like patterns
        """
        text = text.strip()
        
        # Direct JSON detection
        if text.startswith('{') or text.startswith('['):
            try:
                json.loads(text)
                return True
            except json.JSONDecodeError:
                pass
        
        # Check for JSON-like patterns in first 50 lines
        lines = text.split('\n')[:50]
        json_indicators = 0
        
        for line in lines:
            line = line.strip()
            # Count JSON structure indicators
            if line in ('{', '}', '[', ']', '{,', '},', '[,', '],'):
                json_indicators += 1
            # Count lines with quoted keys: "key": value
            elif re.match(r'^\s*"[^"]+"\s*:', line):
                json_indicators += 1
            # Count lines ending with comma after value
            elif re.match(r'^\s*"[^"]+"\s*:\s*.+,$', line):
                json_indicators += 1
        
        # If more than 30% of lines look like JSON, it's probably JSON
        if len(lines) > 0 and json_indicators / len(lines) > 0.3:
            return True
        
        return False
    
    def _is_known_field_name(self, name: str) -> bool:
        """
        Check if a name looks like a JSON/structured data field name.
        
        Returns True for:
        - Known field names (publicId, cloudName, Assignee, etc.)
        - camelCase patterns that are typical of code/JSON
        """
        # Check against known field names (case-insensitive)
        if name in KNOWN_FIELD_NAMES or name.lower() in {n.lower() for n in KNOWN_FIELD_NAMES}:
            return True
        
        # Detect camelCase patterns (lowercase followed by uppercase)
        # e.g., publicId, cloudName, secureUrl - these are NOT usernames
        if re.match(r'^[a-z]+[A-Z][a-zA-Z]*$', name):
            return True
        
        # Single lowercase words that are too short or look like field names
        if len(name) <= 4 and name.islower() and name in {'id', 'url', 'key', 'name', 'type', 'data'}:
            return True
        
        return False
    
    def _detect_format(self, sample_lines: list[str]) -> Optional[str]:
        """Detect the message format from sample lines."""
        iso_count = 0
        us_count = 0
        simple_count = 0
        slack_header_count = 0
        name_colon_count = 0
        no_timestamp_count = 0
        
        for line in sample_lines:
            line = line.strip()
            if not line:
                continue
            
            if self.PATTERN_ISO.match(line):
                iso_count += 1
            elif self.PATTERN_US.match(line):
                us_count += 1
            elif self.PATTERN_SIMPLE.match(line):
                simple_count += 1
            elif self.PATTERN_SLACK_HEADER.match(line):
                slack_header_count += 1
            elif self.PATTERN_NAME_COLON.match(line):
                name_colon_count += 1
            elif self.PATTERN_NO_TIMESTAMP.match(line):
                no_timestamp_count += 1
        
        # Determine dominant format
        counts = {
            "iso": iso_count,
            "us": us_count,
            "simple": simple_count,
            "slack_multiline": slack_header_count,
            "name_colon": name_colon_count,
            "no_timestamp": no_timestamp_count,
        }
        
        max_format = max(counts, key=counts.get)
        if counts[max_format] > 2:
            logger.debug(f"Format detection counts: {counts}")
            return max_format
        
        return None
    
    def _parse_multiline_slack(self, lines: list[str]) -> list[SlackMessage]:
        """
        Parse Slack copy-paste format where header and message are on separate lines.
        
        Format:
        David Shalom  10:23 AM
        Hello everyone, this is my message
        
        Alice Smith  10:25 AM
        Thanks for sharing!
        """
        messages = []
        current_header = None
        current_message_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this is a header line
            header_match = self.PATTERN_SLACK_HEADER.match(line_stripped)
            
            if header_match:
                # Save previous message if exists
                if current_header and current_message_lines:
                    username, time_str = current_header
                    message_text = " ".join(current_message_lines)
                    if message_text:
                        timestamp = self._parse_slack_time(time_str)
                        # Convert display name to username format
                        username_clean = username.strip().lower().replace(" ", ".")
                        messages.append(SlackMessage(
                            timestamp=timestamp,
                            username=username_clean,
                            message=message_text,
                        ))
                
                # Start new message
                current_header = header_match.groups()
                current_message_lines = []
            elif line_stripped and current_header:
                # This is message content
                current_message_lines.append(line_stripped)
            elif not line_stripped and current_header and current_message_lines:
                # Empty line after message - save and reset
                username, time_str = current_header
                message_text = " ".join(current_message_lines)
                if message_text:
                    timestamp = self._parse_slack_time(time_str)
                    username_clean = username.strip().lower().replace(" ", ".")
                    messages.append(SlackMessage(
                        timestamp=timestamp,
                        username=username_clean,
                        message=message_text,
                    ))
                current_header = None
                current_message_lines = []
        
        # Don't forget the last message
        if current_header and current_message_lines:
            username, time_str = current_header
            message_text = " ".join(current_message_lines)
            if message_text:
                timestamp = self._parse_slack_time(time_str)
                username_clean = username.strip().lower().replace(" ", ".")
                messages.append(SlackMessage(
                    timestamp=timestamp,
                    username=username_clean,
                    message=message_text,
                ))
        
        return messages
    
    def _parse_slack_time(self, time_str: str) -> datetime:
        """Parse Slack-style time (10:23 AM or 10:23)."""
        time_str = time_str.strip()
        try:
            if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                time_obj = datetime.strptime(time_str.upper(), "%I:%M %p")
            else:
                time_obj = datetime.strptime(time_str, "%H:%M")
            
            return datetime(
                self.default_year, 1, 1,
                time_obj.hour, time_obj.minute, 0
            )
        except ValueError:
            return datetime(self.default_year, 1, 1, 12, 0, 0)
    
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
        
        # Try Pattern 10: Name with colon (e.g., "David Shalom: Hello")
        match = self.PATTERN_NAME_COLON.match(line)
        if match:
            display_name, message = match.groups()
            # Check if this looks like a known field name
            if self._is_known_field_name(display_name.replace(" ", "")):
                if self.debug_mode:
                    logger.debug(f"Skipped known field name: {display_name}")
                self.stats["skipped_json_fields"] += 1
                return None
            # Convert display name to username format
            username = display_name.strip().lower().replace(" ", ".")
            timestamp = datetime(self.default_year, 1, 1, 12, 0, 0)
            return SlackMessage(timestamp=timestamp, username=username, message=message)
        
        # Try Pattern 8: Simple username: message (no timestamp)
        match = self.PATTERN_NO_TIMESTAMP.match(line)
        if match:
            username, message = match.groups()
            # Filter out known field names (JSON, API fields, etc.)
            if self._is_known_field_name(username):
                if self.debug_mode:
                    logger.debug(f"Skipped known field name: {username}")
                self.stats["skipped_json_fields"] += 1
                return None
            timestamp = datetime(self.default_year, 1, 1, 12, 0, 0)
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
