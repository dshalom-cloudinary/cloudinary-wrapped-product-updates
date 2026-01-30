"""Insight Synthesizer for Slack Wrapped.

Implements Pass 2 of two-pass content analysis: synthesizes content summaries
with statistics to generate context-aware, story-driven insights.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal

from .llm_client import LLMClient, LLMError
from .models import ChannelStats, ContributorStats
from .content_analyzer import ContentChunkSummary

logger = logging.getLogger(__name__)

__all__ = [
    "InsightSynthesizer",
    "VideoDataInsights",
    "YearStory",
    "TopicHighlight",
    "Quote",
    "PersonalityAssignment",
    "SYNTHESIS_SYSTEM_PROMPT",
    "SYNTHESIS_PROMPT_TEMPLATE",
]


@dataclass
class YearStory:
    """Narrative arc of the year."""
    
    opening: str  # How the year began
    arc: str  # The journey through the year
    climax: str  # The defining moment
    closing: str  # How the year ended
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class TopicHighlight:
    """A topic with synthesized insight."""
    
    topic: str
    insight: str  # e.g., "47% of Q4 messages were about AI"
    best_quote: str
    period: str  # Which period this topic dominated
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class Quote:
    """A quote with full context."""
    
    text: str
    author: str
    context: str  # Why this quote matters in the year story
    period: str  # When it was said
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class PersonalityAssignment:
    """A personality type with evidence from content analysis."""
    
    username: str
    display_name: str
    personality_type: str  # e.g., "The Launcher"
    evidence: str  # Specific evidence from content
    fun_fact: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "username": self.username,
            "displayName": self.display_name,
            "personalityType": self.personality_type,
            "evidence": self.evidence,
            "funFact": self.fun_fact,
        }


@dataclass
class VideoDataInsights:
    """Complete insights from two-pass analysis."""
    
    year_story: YearStory
    topic_highlights: list[TopicHighlight] = field(default_factory=list)
    best_quotes: list[Quote] = field(default_factory=list)
    stats_highlights: list[str] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)
    competitions: list[dict] = field(default_factory=list)
    superlatives: list[dict] = field(default_factory=list)
    personality_types: list[PersonalityAssignment] = field(default_factory=list)
    roasts: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "yearStory": self.year_story.to_dict(),
            "topicHighlights": [t.to_dict() for t in self.topic_highlights],
            "bestQuotes": [q.to_dict() for q in self.best_quotes],
            "statsHighlights": self.stats_highlights,
            "records": self.records,
            "competitions": self.competitions,
            "superlatives": self.superlatives,
            "personalityTypes": [p.to_dict() for p in self.personality_types],
            "roasts": self.roasts,
        }


class InsightSynthesizer:
    """Synthesizes content analysis with statistics for final insights."""
    
    def __init__(
        self,
        llm_client: LLMClient,
        include_roasts: bool = True,
    ):
        """
        Initialize insight synthesizer.
        
        Args:
            llm_client: LLM client for synthesis
            include_roasts: Whether to generate roasts
        """
        self.llm = llm_client
        self.include_roasts = include_roasts
    
    def synthesize(
        self,
        content_summaries: list[ContentChunkSummary],
        stats: ChannelStats,
        contributors: list[ContributorStats],
        channel_name: str,
        year: int,
    ) -> VideoDataInsights:
        """
        Synthesize all inputs into final video insights.
        
        Args:
            content_summaries: Content extraction results from Pass 1
            stats: Channel statistics
            contributors: Top contributor stats
            channel_name: Name of the channel
            year: Year being analyzed
            
        Returns:
            VideoDataInsights with all synthesized content
        """
        if not content_summaries:
            logger.warning("No content summaries provided, using fallback")
            return self._generate_fallback_insights(stats, contributors, channel_name, year)
        
        # Format inputs for prompt
        formatted_content = self._format_content_summaries(content_summaries)
        formatted_stats = self._format_channel_stats(stats)
        formatted_contributors = self._format_contributors(contributors)
        
        # Build and execute prompt
        prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
            channel_name=channel_name,
            year=year,
            content_summaries=formatted_content,
            channel_stats=formatted_stats,
            contributors=formatted_contributors,
            include_roasts="YES - generate 2-3 gentle roasts" if self.include_roasts else "NO - skip roasts",
        )
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                system_prompt=SYNTHESIS_SYSTEM_PROMPT,
                temperature=0.7,  # Higher for more creative synthesis
                max_tokens=3000,
            )
            
            return self._parse_synthesis_response(response, content_summaries, contributors)
            
        except (LLMError, Exception) as e:
            logger.warning(f"Failed to synthesize insights: {e}")
            return self._generate_fallback_insights(stats, contributors, channel_name, year)
    
    def _format_content_summaries(
        self,
        summaries: list[ContentChunkSummary],
    ) -> str:
        """Format content summaries for the prompt."""
        lines = []
        
        for summary in summaries:
            lines.append(f"\n═══ {summary.period} ({summary.message_count} messages) ═══")
            
            # Topics
            if summary.topics:
                lines.append("\nTOPICS:")
                for topic in summary.topics:
                    lines.append(f"  • {topic.name} ({topic.frequency}): \"{topic.sample_quote}\"")
            
            # Achievements
            if summary.achievements:
                lines.append("\nACHIEVEMENTS:")
                for ach in summary.achievements:
                    lines.append(f"  • {ach.description} ({ach.who}, {ach.date})")
            
            # Sentiment
            if summary.sentiment:
                lines.append(f"\nSENTIMENT: {summary.sentiment.overall} (trend: {summary.sentiment.trend})")
                if summary.sentiment.notable_moods:
                    lines.append(f"  Moods: {', '.join(summary.sentiment.notable_moods)}")
            
            # Notable quotes
            if summary.notable_quotes:
                lines.append("\nNOTABLE QUOTES:")
                for quote in summary.notable_quotes:
                    lines.append(f"  • \"{quote.text}\" - {quote.author} ({quote.why_notable})")
            
            # Patterns
            if summary.recurring_patterns:
                lines.append("\nPATTERNS:")
                for pattern in summary.recurring_patterns:
                    lines.append(f"  • {pattern.name}: {pattern.description}")
        
        return "\n".join(lines)
    
    def _format_channel_stats(self, stats: ChannelStats) -> str:
        """Format channel stats for the prompt."""
        lines = [
            f"Total Messages: {stats.total_messages:,}",
            f"Total Words: {stats.total_words:,}",
            f"Contributors: {stats.total_contributors}",
            f"Active Days: {stats.active_days}",
            f"Avg Message Length: {stats.average_message_length:.1f} words",
            f"Peak Hour: {stats.peak_hour}:00",
            f"Peak Day: {stats.peak_day}",
        ]
        
        if stats.messages_by_quarter:
            lines.append("\nQuarterly Activity:")
            for q, count in stats.messages_by_quarter.items():
                lines.append(f"  {q}: {count:,} messages")
        
        return "\n".join(lines)
    
    def _format_contributors(self, contributors: list[ContributorStats]) -> str:
        """Format contributors for the prompt."""
        lines = []
        
        for i, c in enumerate(contributors[:10], 1):
            rank = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
            lines.append(
                f"{rank} {c.display_name} ({c.username}): "
                f"{c.message_count} msgs ({c.contribution_percent:.1f}%), "
                f"avg {c.average_message_length:.1f} words/msg, "
                f"team: {c.team or 'N/A'}"
            )
            if c.favorite_words:
                words = ", ".join(c.favorite_words[:3])
                lines.append(f"    Favorite words: {words}")
        
        return "\n".join(lines)
    
    def _parse_synthesis_response(
        self,
        response: str,
        content_summaries: list[ContentChunkSummary],
        contributors: list[ContributorStats],
    ) -> VideoDataInsights:
        """Parse the LLM synthesis response."""
        # Strip markdown code blocks
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        data = json.loads(response)
        
        # Parse year story
        year_story_data = data.get("yearStory", data.get("year_story", {}))
        year_story = YearStory(
            opening=year_story_data.get("opening", ""),
            arc=year_story_data.get("arc", ""),
            climax=year_story_data.get("climax", ""),
            closing=year_story_data.get("closing", ""),
        )
        
        # Parse topic highlights
        topic_highlights = []
        for t in data.get("topicHighlights", data.get("topic_highlights", [])):
            topic_highlights.append(TopicHighlight(
                topic=t.get("topic", ""),
                insight=t.get("insight", ""),
                best_quote=t.get("bestQuote", t.get("best_quote", "")),
                period=t.get("period", ""),
            ))
        
        # Parse best quotes
        best_quotes = []
        for q in data.get("bestQuotes", data.get("best_quotes", [])):
            best_quotes.append(Quote(
                text=q.get("text", ""),
                author=q.get("author", ""),
                context=q.get("context", ""),
                period=q.get("period", ""),
            ))
        
        # Parse personality assignments
        personality_types = []
        for p in data.get("personalityTypes", data.get("personality_types", [])):
            # Find display name from contributors
            username = p.get("username", "")
            display_name = username
            for c in contributors:
                if c.username == username:
                    display_name = c.display_name
                    break
            
            personality_types.append(PersonalityAssignment(
                username=username,
                display_name=display_name,
                personality_type=p.get("personalityType", p.get("personality_type", p.get("type", ""))),
                evidence=p.get("evidence", ""),
                fun_fact=p.get("funFact", p.get("fun_fact", "")),
            ))
        
        return VideoDataInsights(
            year_story=year_story,
            topic_highlights=topic_highlights,
            best_quotes=best_quotes,
            stats_highlights=data.get("statsHighlights", data.get("stats_highlights", [])),
            records=data.get("records", []),
            competitions=data.get("competitions", []),
            superlatives=data.get("superlatives", []),
            personality_types=personality_types,
            roasts=data.get("roasts", []),
        )
    
    def _generate_fallback_insights(
        self,
        stats: ChannelStats,
        contributors: list[ContributorStats],
        channel_name: str,
        year: int,
    ) -> VideoDataInsights:
        """Generate basic insights without LLM."""
        # Create basic year story
        year_story = YearStory(
            opening=f"The #{channel_name} channel kicked off {year} with energy.",
            arc=f"Throughout the year, {stats.total_contributors} contributors shared {stats.total_messages:,} messages.",
            climax=f"The channel peaked with activity on {stats.peak_day}s at {stats.peak_hour}:00.",
            closing=f"Together, the team wrote {stats.total_words:,} words across {stats.active_days} active days.",
        )
        
        # Create basic personality types
        personality_types = []
        titles = ["The Champion", "The Contributor", "The Voice", "The Collaborator", "The Team Player"]
        for i, c in enumerate(contributors[:5]):
            personality_types.append(PersonalityAssignment(
                username=c.username,
                display_name=c.display_name,
                personality_type=titles[i] if i < len(titles) else "The Contributor",
                evidence=f"Sent {c.message_count} messages",
                fun_fact=f"Contributed {c.contribution_percent:.1f}% of all messages!",
            ))
        
        return VideoDataInsights(
            year_story=year_story,
            personality_types=personality_types,
            stats_highlights=[
                f"{stats.total_messages:,} messages exchanged",
                f"{stats.total_words:,} words written",
                f"{stats.total_contributors} contributors participated",
            ],
        )


# System prompt for synthesis
SYNTHESIS_SYSTEM_PROMPT = """You are a creative writer synthesizing a "Slack Wrapped" year-end retrospective video.

Your job is to weave together:
1. Content analysis (what was discussed, achieved, celebrated)
2. Statistics (who contributed, when, how much)
3. Contributors (who made an impact)

Into a compelling, data-driven STORY that celebrates the channel's year.

TONE: Celebratory, fun, like a team yearbook crossed with Spotify Wrapped
STYLE: Specific references to real events, real quotes, real people
HUMOR: Gentle, positive - never mean or embarrassing

KEY OUTPUTS:
1. YEAR STORY - Narrative arc (opening → arc → climax → closing)
2. TOPIC HIGHLIGHTS - Key topics with insights and best quotes  
3. BEST QUOTES - Most memorable quotes with context
4. PERSONALITY TYPES - Fun titles based on EVIDENCE from content
5. ROASTS - Gentle, loving teases based on real patterns

CRITICAL RULES:
- Reference ACTUAL content from summaries (don't make things up)
- Use REAL quotes provided in the content analysis
- Base personality types on EVIDENCE (not generic traits)
- Keep roasts positive and based on real behaviors
- Make it feel personal and specific to this channel

OUTPUT: Valid JSON only. No markdown, no explanation."""


# Prompt template for synthesis
SYNTHESIS_PROMPT_TEMPLATE = """Create a compelling "Wrapped" narrative for #{channel_name} in {year}.

═══════════════════════════════════════════════════════════════════════════════
                            CONTENT ANALYSIS (Pass 1 Results)
═══════════════════════════════════════════════════════════════════════════════
{content_summaries}

═══════════════════════════════════════════════════════════════════════════════
                            CHANNEL STATISTICS
═══════════════════════════════════════════════════════════════════════════════
{channel_stats}

═══════════════════════════════════════════════════════════════════════════════
                            TOP CONTRIBUTORS
═══════════════════════════════════════════════════════════════════════════════
{contributors}

═══════════════════════════════════════════════════════════════════════════════
                            SYNTHESIS TASK
═══════════════════════════════════════════════════════════════════════════════

Create a JSON response with the following structure:

{{
  "yearStory": {{
    "opening": "How the year began (reference Q1 topics/achievements)",
    "arc": "The journey through the year (major themes, shifts, progress)",
    "climax": "The defining moment (biggest achievement or turning point)",
    "closing": "How the year ended (Q4 sentiment, looking ahead)"
  }},
  "topicHighlights": [
    {{
      "topic": "Topic name from content analysis",
      "insight": "Data-driven observation (e.g., '47% of Q4 messages')",
      "bestQuote": "Actual quote about this topic",
      "period": "When this topic peaked"
    }}
  ],
  "bestQuotes": [
    {{
      "text": "Exact quote from content analysis",
      "author": "Who said it",
      "context": "Why this quote matters in the year's story",
      "period": "When it was said"
    }}
  ],
  "personalityTypes": [
    {{
      "username": "exact_username",
      "personalityType": "Creative Title (e.g., 'The Launcher')",
      "evidence": "Specific evidence from content (e.g., 'Announced 5 launches')",
      "funFact": "Personalized, data-driven fun fact"
    }}
  ],
  "statsHighlights": [
    "Data-driven highlight 1",
    "Data-driven highlight 2"
  ],
  "roasts": [
    "Gentle, loving roast based on real behavior"
  ]
}}

INCLUDE ROASTS: {include_roasts}

REQUIREMENTS:
1. Year Story: Reference ACTUAL topics and achievements from each quarter
2. Topic Highlights: Include 3-5 key topics with real quotes
3. Best Quotes: Select 3-5 most memorable quotes with context
4. Personality Types: Assign to top contributors with EVIDENCE from content
5. Stats Highlights: 3-5 interesting statistics
6. Roasts: Only if enabled, keep gentle and based on real patterns

Make it feel like a celebration of what this team accomplished together!"""
