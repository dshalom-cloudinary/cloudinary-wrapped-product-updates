"""Statistics analyzer for Slack Wrapped.

Calculates channel and contributor statistics from parsed messages.
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional
import re

from .models import (
    SlackMessage,
    ChannelStats,
    ContributorStats,
    QuarterActivity,
    FunFact,
)
from .config import Config


# Common English stop words to exclude from word analysis
# Note: Using a set automatically handles any duplicates
STOP_WORDS = {
    # Articles, conjunctions, prepositions
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under',
    # Verbs (be, have, do, modals)
    'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
    'must', 'shall', 'can', 'need', 'dare', 'ought', 'used',
    # Pronouns
    'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
    'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
    'his', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
    # Question words and determiners
    'what', 'which', 'who', 'whom', 'when', 'where', 'why', 'how', 'all',
    'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such',
    # Adverbs and misc
    'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'just', 'also', 'now', 'here', 'there', 'then', 'if', 'because', 'about',
    'again', 'further', 'once',
    # Contractions (positive)
    "i'm", "i've", "i'll", "i'd", "we're", "we've", "we'll", "we'd",
    "you're", "you've", "you'll", "you'd", "he's", "he'll", "he'd",
    "she's", "she'll", "she'd", "it's", "it'll", "they're", "they've",
    "they'll", "they'd", "that's", "that'll", "who's", "who'll", "who'd",
    "what's", "what'll", "where's", "when's", "why's", "how's",
    "here's", "there's", "let's",
    # Contractions (negative)
    "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't", "hadn't",
    "doesn't", "don't", "didn't", "won't", "wouldn't", "shan't", "shouldn't",
    "can't", "cannot", "couldn't", "mustn't",
    # Common casual words
    'yeah', 'yes', 'ok', 'okay', 'hi', 'hey', 'hello', 'thanks',
    'thank', 'please', 'sorry', 'got', 'get', 'going', 'go', 'know',
    'like', 'think', 'see', 'look', 'make', 'want', 'give', 'take',
}

# Day names constant - used for day of week calculations
DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# Emoji pattern for extraction
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U00002600-\U000026FF"  # misc symbols
    "]+",
    flags=re.UNICODE
)


class ChannelAnalyzer:
    """Analyzes channel statistics from parsed messages."""
    
    def __init__(self, messages: list[SlackMessage], config: Optional[Config] = None):
        """
        Initialize analyzer.
        
        Args:
            messages: List of parsed SlackMessage objects
            config: Optional configuration for user mappings
        """
        self.messages = messages
        self.config = config
    
    def calculate_stats(self) -> ChannelStats:
        """
        Calculate comprehensive channel statistics.
        
        Returns:
            ChannelStats object with all metrics
        """
        if not self.messages:
            return ChannelStats(
                total_messages=0,
                total_words=0,
                total_contributors=0,
                active_days=0,
            )
        
        # Basic counts
        total_messages = len(self.messages)
        
        # Count words
        total_words = sum(len(msg.message.split()) for msg in self.messages)
        
        # Unique contributors
        contributors = set(msg.username for msg in self.messages)
        total_contributors = len(contributors)
        
        # Messages by user
        messages_by_user = Counter(msg.username for msg in self.messages)
        
        # Messages by quarter
        messages_by_quarter = self._calculate_quarterly_distribution()
        
        # Messages by day of week
        messages_by_day = self._calculate_day_distribution()
        
        # Active days
        active_dates = set(msg.timestamp.date() for msg in self.messages)
        active_days = len(active_dates)
        
        # Peak hour
        hour_counts = Counter(msg.timestamp.hour for msg in self.messages)
        peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 12
        
        # Peak day (empty string if no messages)
        peak_day = max(messages_by_day.items(), key=lambda x: x[1])[0] if messages_by_day else ''
        
        # Average message length
        avg_length = total_words / total_messages if total_messages > 0 else 0
        
        # Most active date
        date_counts = Counter(msg.timestamp.date() for msg in self.messages)
        most_active = date_counts.most_common(1)[0][0] if date_counts else None
        most_active_date = most_active.isoformat() if most_active else None
        
        return ChannelStats(
            total_messages=total_messages,
            total_words=total_words,
            total_contributors=total_contributors,
            active_days=active_days,
            messages_by_user=dict(messages_by_user),
            messages_by_quarter=messages_by_quarter,
            messages_by_day_of_week=messages_by_day,
            peak_hour=peak_hour,
            peak_day=peak_day,
            average_message_length=round(avg_length, 2),
            most_active_date=most_active_date,
        )
    
    def _calculate_quarterly_distribution(self) -> dict[str, int]:
        """Calculate message distribution by quarter."""
        quarters = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
        
        for msg in self.messages:
            month = msg.timestamp.month
            if month <= 3:
                quarters["Q1"] += 1
            elif month <= 6:
                quarters["Q2"] += 1
            elif month <= 9:
                quarters["Q3"] += 1
            else:
                quarters["Q4"] += 1
        
        return quarters
    
    def _calculate_day_distribution(self) -> dict[str, int]:
        """Calculate message distribution by day of week."""
        day_counts = Counter(msg.timestamp.weekday() for msg in self.messages)
        
        return {DAY_NAMES[i]: day_counts.get(i, 0) for i in range(7)}
    
    def get_quarterly_activity(self) -> list[QuarterActivity]:
        """
        Get quarterly activity data for video.
        
        Returns:
            List of QuarterActivity objects
        """
        quarters_data = self._calculate_quarterly_distribution()
        
        result = []
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:
            result.append(QuarterActivity(
                quarter=quarter,
                messages=quarters_data.get(quarter, 0),
                highlights=[],  # Will be filled by LLM
            ))
        
        return result


class ContributorAnalyzer:
    """Analyzes individual contributor statistics."""
    
    def __init__(
        self,
        messages: list[SlackMessage],
        config: Optional[Config] = None,
        top_n: int = 5,
    ):
        """
        Initialize analyzer.
        
        Args:
            messages: List of parsed SlackMessage objects
            config: Optional configuration for user mappings
            top_n: Number of top contributors to return
        """
        self.messages = messages
        self.config = config
        self.top_n = top_n
    
    def rank_contributors(self) -> list[ContributorStats]:
        """
        Rank and return top contributors.
        
        Returns:
            List of ContributorStats sorted by message count (descending)
        """
        if not self.messages:
            return []
        
        # Group messages by user
        user_messages: dict[str, list[SlackMessage]] = defaultdict(list)
        for msg in self.messages:
            user_messages[msg.username].append(msg)
        
        total_messages = len(self.messages)
        contributors = []
        
        for username, msgs in user_messages.items():
            message_count = len(msgs)
            word_count = sum(len(m.message.split()) for m in msgs)
            contribution_percent = (message_count / total_messages) * 100 if total_messages > 0 else 0
            avg_length = word_count / message_count if message_count > 0 else 0
            
            # Get display name and team from config
            display_name = username
            team = ""
            if self.config:
                display_name = self.config.get_display_name(username)
                team = self.config.get_team(username)
            
            contributors.append(ContributorStats(
                username=username,
                display_name=display_name,
                team=team,
                message_count=message_count,
                word_count=word_count,
                contribution_percent=round(contribution_percent, 2),
                average_message_length=round(avg_length, 2),
            ))
        
        # Sort by message count descending
        contributors.sort(key=lambda c: c.message_count, reverse=True)
        
        # Return top N
        return contributors[:self.top_n]
    
    def get_team_stats(self) -> dict[str, dict]:
        """
        Calculate statistics by team.
        
        Returns:
            Dict of team_name -> {messages, members, avg_per_person, words, top_contributor}
        """
        if not self.messages or not self.config:
            return {}
        
        # Group messages by team
        team_messages: dict[str, list[SlackMessage]] = defaultdict(list)
        team_members: dict[str, set] = defaultdict(set)
        
        for msg in self.messages:
            team = self.config.get_team(msg.username)
            if team:
                team_messages[team].append(msg)
                team_members[team].add(msg.username)
        
        team_stats = {}
        for team_name in team_messages:
            msgs = team_messages[team_name]
            members = team_members[team_name]
            message_count = len(msgs)
            member_count = len(members)
            word_count = sum(len(m.message.split()) for m in msgs)
            
            # Find top contributor for this team
            user_counts = Counter(m.username for m in msgs)
            top_user = user_counts.most_common(1)[0][0] if user_counts else ""
            top_user_display = self.config.get_display_name(top_user) if top_user else ""
            
            team_stats[team_name] = {
                "messages": message_count,
                "members": member_count,
                "avg_per_person": round(message_count / member_count, 1) if member_count > 0 else 0,
                "words": word_count,
                "top_contributor": top_user_display,
                "top_contributor_count": user_counts.get(top_user, 0) if top_user else 0,
            }
        
        return team_stats
    
    def get_all_contributors(self) -> list[ContributorStats]:
        """
        Get all contributors (not just top N).
        
        Returns:
            List of all ContributorStats sorted by message count
        """
        if not self.messages:
            return []
        
        # Group messages by user
        user_messages: dict[str, list[SlackMessage]] = defaultdict(list)
        for msg in self.messages:
            user_messages[msg.username].append(msg)
        
        total_messages = len(self.messages)
        contributors = []
        
        for username, msgs in user_messages.items():
            message_count = len(msgs)
            word_count = sum(len(m.message.split()) for m in msgs)
            contribution_percent = (message_count / total_messages) * 100 if total_messages > 0 else 0
            avg_length = word_count / message_count if message_count > 0 else 0
            
            # Get display name and team from config
            display_name = username
            team = ""
            if self.config:
                display_name = self.config.get_display_name(username)
                team = self.config.get_team(username)
            
            contributors.append(ContributorStats(
                username=username,
                display_name=display_name,
                team=team,
                message_count=message_count,
                word_count=word_count,
                contribution_percent=round(contribution_percent, 2),
                average_message_length=round(avg_length, 2),
            ))
        
        # Sort by message count descending
        contributors.sort(key=lambda c: c.message_count, reverse=True)
        return contributors


class WordAnalyzer:
    """Analyzes word patterns and favorites."""
    
    def __init__(self, messages: list[SlackMessage]):
        """
        Initialize analyzer.
        
        Args:
            messages: List of parsed SlackMessage objects
        """
        self.messages = messages
    
    def get_most_used_words(self, top_n: int = 10) -> list[tuple[str, int]]:
        """
        Get most frequently used words (excluding stop words).
        
        Args:
            top_n: Number of top words to return
            
        Returns:
            List of (word, count) tuples
        """
        words = []
        for msg in self.messages:
            # Tokenize and clean
            tokens = re.findall(r'\b[a-zA-Z]{3,}\b', msg.message.lower())
            words.extend(t for t in tokens if t not in STOP_WORDS)
        
        return Counter(words).most_common(top_n)
    
    def get_most_used_emoji(self, top_n: int = 5) -> list[tuple[str, int]]:
        """
        Get most frequently used emoji.
        
        Args:
            top_n: Number of top emoji to return
            
        Returns:
            List of (emoji, count) tuples
        """
        emoji_counts: Counter = Counter()
        
        for msg in self.messages:
            emojis = EMOJI_PATTERN.findall(msg.message)
            for emoji_group in emojis:
                # Split emoji cluster into individual emoji
                for emoji in emoji_group:
                    emoji_counts[emoji] += 1
        
        return emoji_counts.most_common(top_n)
    
    def get_favorite_words_by_user(
        self,
        top_n_users: int = 5,
        top_n_words: int = 3,
    ) -> dict[str, list[tuple[str, int]]]:
        """
        Get favorite words for each top user.
        
        Args:
            top_n_users: Number of users to analyze
            top_n_words: Number of words per user
            
        Returns:
            Dict mapping username to list of (word, count) tuples
        """
        # Group messages by user
        user_messages: dict[str, list[str]] = defaultdict(list)
        for msg in self.messages:
            user_messages[msg.username].append(msg.message)
        
        # Sort users by message count
        sorted_users = sorted(
            user_messages.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:top_n_users]
        
        result = {}
        for username, msgs in sorted_users:
            words = []
            for message in msgs:
                tokens = re.findall(r'\b[a-zA-Z]{3,}\b', message.lower())
                words.extend(t for t in tokens if t not in STOP_WORDS)
            
            result[username] = Counter(words).most_common(top_n_words)
        
        return result
    
    def get_longest_message(self) -> Optional[SlackMessage]:
        """
        Get the longest message by word count.
        
        Returns:
            SlackMessage with most words, or None if no messages
        """
        if not self.messages:
            return None
        
        return max(self.messages, key=lambda m: len(m.message.split()))
    
    def get_word_frequency_by_quarter(self) -> dict[str, Counter]:
        """
        Get word frequency distribution by quarter.
        
        Returns:
            Dict mapping quarter to Counter of words
        """
        quarters: dict[str, list[str]] = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
        
        for msg in self.messages:
            month = msg.timestamp.month
            if month <= 3:
                quarter = "Q1"
            elif month <= 6:
                quarter = "Q2"
            elif month <= 9:
                quarter = "Q3"
            else:
                quarter = "Q4"
            
            tokens = re.findall(r'\b[a-zA-Z]{3,}\b', msg.message.lower())
            quarters[quarter].extend(t for t in tokens if t not in STOP_WORDS)
        
        return {q: Counter(words) for q, words in quarters.items()}


def generate_fun_facts(
    stats: ChannelStats,
    contributors: list[ContributorStats],
    word_analyzer: WordAnalyzer,
) -> list[FunFact]:
    """
    Generate fun facts from statistics.
    
    Args:
        stats: Channel statistics
        contributors: List of top contributors
        word_analyzer: WordAnalyzer instance
        
    Returns:
        List of FunFact objects
    """
    facts = []
    
    # Peak hour fact
    hour = stats.peak_hour
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    
    # Build detail text, handling empty peak_day
    if stats.peak_day:
        detail = f"{stats.peak_day}s are the busiest day"
    else:
        detail = "Based on channel activity"
    
    facts.append(FunFact(
        label="Peak Hour",
        value=f"{display_hour}:00 {period}",
        detail=detail,
    ))
    
    # Average message length
    facts.append(FunFact(
        label="Avg Message",
        value=f"{stats.average_message_length:.1f} words",
        detail=f"Across {stats.total_messages:,} messages",
    ))
    
    # Most used words
    top_words = word_analyzer.get_most_used_words(3)
    if top_words:
        word_list = ", ".join(w for w, _ in top_words)
        facts.append(FunFact(
            label="Favorite Words",
            value=word_list,
            detail=f"Used {top_words[0][1]:,} times combined",
        ))
    
    # Top emoji
    top_emoji = word_analyzer.get_most_used_emoji(3)
    if top_emoji:
        emoji_list = "".join(e for e, _ in top_emoji)
        facts.append(FunFact(
            label="Top Emoji",
            value=emoji_list,
            detail=f"{top_emoji[0][0]} used {top_emoji[0][1]} times",
        ))
    
    # Most active date
    if stats.most_active_date:
        facts.append(FunFact(
            label="Busiest Day",
            value=stats.most_active_date,
            detail="The most messages in a single day",
        ))
    
    return facts[:5]  # Limit to 5 facts
