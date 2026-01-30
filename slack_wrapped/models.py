"""Data models for Slack Wrapped."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json
from pathlib import Path


@dataclass
class SlackMessage:
    """Represents a single Slack message."""
    
    timestamp: datetime
    username: str
    message: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "username": self.username,
            "message": self.message,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SlackMessage":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            username=data["username"],
            message=data["message"],
        )


@dataclass
class ChannelStats:
    """Aggregate statistics for a Slack channel."""
    
    total_messages: int
    total_words: int
    total_contributors: int
    active_days: int
    messages_by_user: dict[str, int] = field(default_factory=dict)
    messages_by_quarter: dict[str, int] = field(default_factory=dict)
    messages_by_day_of_week: dict[str, int] = field(default_factory=dict)
    peak_hour: int = 12
    peak_day: str = "Tuesday"
    average_message_length: float = 0.0
    most_active_date: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChannelStats":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ContributorStats:
    """Statistics for an individual contributor."""
    
    username: str
    display_name: str
    team: str
    message_count: int
    word_count: int
    contribution_percent: float
    average_message_length: float = 0.0
    personality_type: str = ""
    fun_fact: str = ""
    favorite_words: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ContributorStats":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class QuarterActivity:
    """Activity data for a single quarter."""
    
    quarter: str  # "Q1", "Q2", "Q3", "Q4"
    messages: int
    highlights: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class FunFact:
    """A fun fact about the channel."""
    
    label: str
    value: str
    detail: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class Insights:
    """AI-generated insights about the channel."""
    
    interesting: list[str] = field(default_factory=list)
    funny: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class VideoDataMeta:
    """Metadata for the video data."""
    
    channel_name: str
    year: int
    generated_at: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "channelName": self.channel_name,
            "year": self.year,
            "generatedAt": self.generated_at,
        }


@dataclass
class VideoData:
    """Complete data structure for video rendering."""
    
    channel_stats: ChannelStats
    quarterly_activity: list[QuarterActivity]
    top_contributors: list[ContributorStats]
    fun_facts: list[FunFact]
    insights: Insights
    meta: VideoDataMeta
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary matching Remotion schema."""
        return {
            "channelStats": {
                "totalMessages": self.channel_stats.total_messages,
                "totalWords": self.channel_stats.total_words,
                "totalContributors": self.channel_stats.total_contributors,
                "activeDays": self.channel_stats.active_days,
            },
            "quarterlyActivity": [
                {
                    "quarter": q.quarter,
                    "messages": q.messages,
                    "highlights": q.highlights,
                }
                for q in self.quarterly_activity
            ],
            "topContributors": [
                {
                    "username": c.username,
                    "displayName": c.display_name,
                    "team": c.team,
                    "messageCount": c.message_count,
                    "contributionPercent": c.contribution_percent,
                    "funTitle": c.personality_type,
                    "funFact": c.fun_fact,
                }
                for c in self.top_contributors
            ],
            "funFacts": [f.to_dict() for f in self.fun_facts],
            "insights": self.insights.to_dict(),
            "meta": self.meta.to_dict(),
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, output_dir: str = "output") -> Path:
        """Save video data to file."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"video-data-{self.meta.channel_name}-{timestamp}.json"
        filepath = output_path / filename
        
        with open(filepath, "w") as f:
            f.write(self.to_json())
        
        return filepath
