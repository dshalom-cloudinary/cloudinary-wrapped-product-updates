"""Insights generator for Slack Wrapped.

Generates AI-powered insights, fun facts, and personality types using OpenAI.
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass

from .llm_client import LLMClient, LLMError
from .models import (
    ChannelStats,
    ContributorStats,
    Insights,
    FunFact,
)
from .config import Config

logger = logging.getLogger(__name__)


# System prompt for insights generation
INSIGHTS_SYSTEM_PROMPT = """You are a creative analyst for a "Slack Wrapped" video generator.
Your job is to analyze channel statistics and generate engaging, positive insights.

RULES:
- Always be positive and celebratory
- Never embarrassing or mean
- Focus on achievements and interesting patterns
- Keep roasts gentle and fun (like Spotify Wrapped style)
- Reference specific data points
- Be creative but data-driven
"""

# Prompt template for generating insights
INSIGHTS_PROMPT_TEMPLATE = """Analyze these Slack channel statistics and generate insights.

CHANNEL: {channel_name}
YEAR: {year}

STATISTICS:
- Total messages: {total_messages:,}
- Total words: {total_words:,}
- Total contributors: {total_contributors}
- Active days: {active_days}
- Average message length: {avg_length:.1f} words
- Peak hour: {peak_hour}:00 ({peak_day}s are busiest)

QUARTERLY DISTRIBUTION:
{quarterly_breakdown}

TOP CONTRIBUTORS:
{top_contributors}

MOST USED WORDS: {top_words}
TOP EMOJI: {top_emoji}

Generate a JSON response with this exact structure:
{{
  "interesting": [
    "First interesting insight about the data...",
    "Second insight...",
    "Third insight..."
  ],
  "funny": [
    "First gentle roast or funny observation...",
    "Second fun observation..."
  ]
}}

Generate 3-5 interesting insights and 2-3 funny observations.
Focus on patterns, achievements, and communication style."""


# Prompt for personality type assignment
PERSONALITY_PROMPT_TEMPLATE = """Assign fun personality types to these Slack channel contributors.

CHANNEL: {channel_name}

CONTRIBUTORS:
{contributors_data}

For each contributor, assign:
1. A fun title (like "The Announcer", "The Emoji Master", "The Novelist", "The Early Bird")
2. A personalized fun fact based on their stats

Generate a JSON response with this exact structure:
{{
  "personalities": [
    {{
      "username": "contributor1",
      "title": "The Title",
      "funFact": "Personalized fun fact referencing their actual data"
    }}
  ]
}}

RULES:
- Titles should be unique for each person
- Be positive and celebratory
- Reference actual data points (message count, favorite words, etc.)
- Keep it fun and professional"""


@dataclass
class InsightsResult:
    """Result from insights generation."""
    
    insights: Insights
    personalities: dict[str, tuple[str, str]]  # username -> (title, fun_fact)
    raw_response: Optional[str] = None


class InsightsGenerator:
    """Generates AI-powered insights using OpenAI."""
    
    def __init__(
        self,
        llm_client: LLMClient,
        config: Config,
    ):
        """
        Initialize insights generator.
        
        Args:
            llm_client: LLM client for API calls
            config: Channel configuration
        """
        self.llm = llm_client
        self.config = config
    
    def generate_insights(
        self,
        stats: ChannelStats,
        contributors: list[ContributorStats],
        top_words: list[tuple[str, int]],
        top_emoji: list[tuple[str, int]],
    ) -> Insights:
        """
        Generate interesting insights about the channel.
        
        Args:
            stats: Channel statistics
            contributors: List of top contributors
            top_words: Most used words
            top_emoji: Most used emoji
            
        Returns:
            Insights object with interesting and funny observations
        """
        # Build quarterly breakdown
        quarterly_lines = []
        for quarter, count in stats.messages_by_quarter.items():
            quarterly_lines.append(f"- {quarter}: {count:,} messages")
        quarterly_breakdown = "\n".join(quarterly_lines)
        
        # Build contributors list
        contrib_lines = []
        for c in contributors[:5]:
            contrib_lines.append(
                f"- {c.display_name} ({c.username}): {c.message_count} messages "
                f"({c.contribution_percent:.1f}%), {c.word_count} words"
            )
        top_contributors_str = "\n".join(contrib_lines)
        
        # Format words and emoji
        words_str = ", ".join(f"{w} ({c}x)" for w, c in top_words[:5])
        emoji_str = "".join(e for e, _ in top_emoji[:5]) if top_emoji else "None"
        
        prompt = INSIGHTS_PROMPT_TEMPLATE.format(
            channel_name=self.config.channel.name,
            year=self.config.channel.year,
            total_messages=stats.total_messages,
            total_words=stats.total_words,
            total_contributors=stats.total_contributors,
            active_days=stats.active_days,
            avg_length=stats.average_message_length,
            peak_hour=stats.peak_hour,
            peak_day=stats.peak_day,
            quarterly_breakdown=quarterly_breakdown,
            top_contributors=top_contributors_str,
            top_words=words_str,
            top_emoji=emoji_str,
        )
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                system_prompt=INSIGHTS_SYSTEM_PROMPT,
                temperature=0.7,
            )
            
            # Parse JSON response
            data = self._parse_json_response(response)
            
            return Insights(
                interesting=data.get("interesting", []),
                funny=data.get("funny", []) if self.config.preferences.include_roasts else [],
            )
            
        except (LLMError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to generate insights: {e}")
            return self._generate_fallback_insights(stats)
    
    def assign_personalities(
        self,
        contributors: list[ContributorStats],
        favorite_words: dict[str, list[tuple[str, int]]],
    ) -> list[ContributorStats]:
        """
        Assign fun personality types to contributors.
        
        Args:
            contributors: List of contributors to update
            favorite_words: Favorite words by username
            
        Returns:
            Updated contributors with personality types
        """
        if not contributors:
            return contributors
        
        # Build contributor data for prompt
        contrib_lines = []
        for c in contributors:
            words = favorite_words.get(c.username, [])
            words_str = ", ".join(w for w, _ in words[:3]) if words else "N/A"
            contrib_lines.append(
                f"- {c.display_name} ({c.username}): "
                f"{c.message_count} messages, "
                f"{c.average_message_length:.1f} avg words/msg, "
                f"favorite words: {words_str}"
            )
        
        prompt = PERSONALITY_PROMPT_TEMPLATE.format(
            channel_name=self.config.channel.name,
            contributors_data="\n".join(contrib_lines),
        )
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                system_prompt=INSIGHTS_SYSTEM_PROMPT,
                temperature=0.8,
            )
            
            # Parse JSON response
            data = self._parse_json_response(response)
            personalities = data.get("personalities", [])
            
            # Create lookup
            personality_map = {
                p["username"]: (p.get("title", ""), p.get("funFact", ""))
                for p in personalities
            }
            
            # Update contributors
            for c in contributors:
                if c.username in personality_map:
                    c.personality_type, c.fun_fact = personality_map[c.username]
            
            return contributors
            
        except (LLMError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to assign personalities: {e}")
            return self._assign_fallback_personalities(contributors)
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Strip markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            # Remove first line (```json) and last line (```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        return json.loads(response)
    
    def _generate_fallback_insights(self, stats: ChannelStats) -> Insights:
        """Generate basic insights without LLM."""
        interesting = [
            f"The channel had {stats.total_messages:,} messages across {stats.active_days} active days.",
            f"Peak activity was at {stats.peak_hour}:00, with {stats.peak_day} being the busiest day.",
        ]
        
        if stats.total_contributors > 1:
            interesting.append(
                f"{stats.total_contributors} team members contributed to the conversation."
            )
        
        return Insights(interesting=interesting, funny=[])
    
    def _assign_fallback_personalities(
        self,
        contributors: list[ContributorStats],
    ) -> list[ContributorStats]:
        """Assign basic personality types without LLM."""
        fallback_titles = [
            "The Communicator",
            "The Contributor",
            "The Collaborator",
            "The Team Player",
            "The Active Voice",
        ]
        
        for i, c in enumerate(contributors):
            if not c.personality_type:
                c.personality_type = fallback_titles[i % len(fallback_titles)]
                c.fun_fact = f"Sent {c.message_count} messages this year!"
        
        return contributors


def generate_all_insights(
    llm_client: LLMClient,
    config: Config,
    stats: ChannelStats,
    contributors: list[ContributorStats],
    top_words: list[tuple[str, int]],
    top_emoji: list[tuple[str, int]],
    favorite_words: dict[str, list[tuple[str, int]]],
) -> tuple[Insights, list[ContributorStats]]:
    """
    Generate all insights and personality types.
    
    Convenience function that runs the full insights pipeline.
    
    Args:
        llm_client: LLM client
        config: Channel configuration
        stats: Channel statistics
        contributors: Top contributors
        top_words: Most used words
        top_emoji: Most used emoji
        favorite_words: Favorite words by username
        
    Returns:
        Tuple of (Insights, updated contributors with personalities)
    """
    generator = InsightsGenerator(llm_client, config)
    
    # Generate insights
    insights = generator.generate_insights(stats, contributors, top_words, top_emoji)
    
    # Assign personality types
    updated_contributors = generator.assign_personalities(contributors, favorite_words)
    
    return insights, updated_contributors
