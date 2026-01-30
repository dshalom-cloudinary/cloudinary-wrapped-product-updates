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
    Record,
    Competition,
    Superlative,
)
from .config import Config

logger = logging.getLogger(__name__)


# System prompt for insights generation
INSIGHTS_SYSTEM_PROMPT = """You are a witty analyst creating a "Slack Wrapped" video - think Spotify Wrapped meets office comedy.

TONE: Celebratory, fun, slightly competitive (like fantasy sports stats)
STYLE: Data-driven observations with punchy, memorable delivery
HUMOR: Gentle teasing, superlatives, fun comparisons - never mean or embarrassing

CATEGORIES TO EXPLORE:
1. RECORDS & ACHIEVEMENTS - Who holds the records? Crown the champions!
2. TEAM COMPETITION - How do teams stack up? Create friendly rivalry!
3. BEHAVIORAL PATTERNS - What quirks emerge? Early birds vs night owls?
4. TIME PATTERNS - When is the team most alive? Any dead zones?
5. COMMUNICATION STYLE - Emoji lovers vs minimalists? Novelists vs snipers?

FUN COMPARISON IDEAS:
- "If your messages were tweets..." 
- "Your team wrote enough words to fill X books"
- "That's X messages per working day"
- Sports metaphors: "carried the team", "MVP", "rookie of the year"

SUPERLATIVE TITLES TO ASSIGN:
- "The Novelist" - longest average messages
- "The Sniper" - short but frequent
- "The Emoji Artist" - highest emoji usage
- "The Early Bird" - most messages before 9am
- "The Night Owl" - most messages after 6pm
- "The Announcer" - always sharing updates
- "The Cheerleader" - most positive/encouraging
- "The Champion" - #1 contributor

RULES:
- Always reference specific numbers from the data
- Make it feel like a celebration, not a report
- Create friendly competition between users/teams
- Keep roasts gentle - the kind you'd say to a friend
"""

# Prompt template for generating insights
INSIGHTS_PROMPT_TEMPLATE = """Analyze these Slack channel statistics and create engaging, fun insights for a "Wrapped" video.

CHANNEL: {channel_name}
YEAR: {year}

═══════════════════════════════════════════════════
CHANNEL STATISTICS
═══════════════════════════════════════════════════
- Total messages: {total_messages:,}
- Total words: {total_words:,}
- Total contributors: {total_contributors}
- Active days: {active_days}
- Average message length: {avg_length:.1f} words
- Peak hour: {peak_hour}:00 ({peak_day}s are busiest)

═══════════════════════════════════════════════════
QUARTERLY ACTIVITY
═══════════════════════════════════════════════════
{quarterly_breakdown}

═══════════════════════════════════════════════════
TEAM BREAKDOWN
═══════════════════════════════════════════════════
{team_breakdown}

═══════════════════════════════════════════════════
TOP CONTRIBUTORS (The Leaderboard)
═══════════════════════════════════════════════════
{top_contributors}

═══════════════════════════════════════════════════
VOCABULARY
═══════════════════════════════════════════════════
Most used words: {top_words}
Favorite emoji: {top_emoji}

═══════════════════════════════════════════════════
EXAMPLE OUTPUTS (for style reference)
═══════════════════════════════════════════════════

Example 1 - Quarterly comparison:
INPUT: Q2 had 312 messages, Q4 had 89
OUTPUT: "Q2 was ON FIRE with 312 messages - someone discovered coffee! Q4? The team was 'conserving energy' with just 89. Holiday mode activated early."

Example 2 - Top contributor celebration:
INPUT: david.shalom sent 34% of messages
OUTPUT: "David Shalom carried the conversation harder than a group project partner - 34% of all messages! The rest of you owe him a coffee. ☕"

Example 3 - Team competition:
INPUT: Backend: 450 msgs, Frontend: 380 msgs
OUTPUT: "Backend vs Frontend: The eternal rivalry! Backend takes the trophy with 450 messages. Frontend's response? 'We were too busy shipping pixels.' 🏆"

Example 4 - Time pattern insight:
INPUT: Peak hour 9:00, Monday busiest
OUTPUT: "Monday mornings at 9am - when the team collectively remembers Slack exists. 47% of messages happened before lunch. Afternoon? Apparently coding time."

Example 5 - Fun comparison:
INPUT: 1,247 total messages, 45,678 words
OUTPUT: "With 45,678 words exchanged, the team wrote the equivalent of a short novel. Working title: 'The Chronicles of Shipped Features' 📚"

═══════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════

Generate a JSON response with this structure:

{{
  "records": [
    {{"title": "Message Champion", "winner": "username", "stat": "156 messages", "quip": "Fun one-liner about this achievement"}}
  ],
  "competitions": [
    {{"type": "team_vs_team", "teams": ["Backend", "Frontend"], "scores": [450, 380], "quip": "Witty comparison"}}
  ],
  "superlatives": [
    {{"title": "The Novelist", "winner": "username", "stat": "42 avg words/msg", "quip": "They never met a message they couldn't elaborate on"}}
  ],
  "insights": [
    "Interesting pattern or achievement with specific numbers...",
    "Another data-driven observation with a fun spin..."
  ],
  "roasts": [
    "Gentle, funny observation about the data (not targeting individuals negatively)..."
  ]
}}

Generate:
- 2-3 records (achievements with clear winners)
- 1-2 team competitions (if multiple teams exist)
- 3-4 superlatives (fun titles for contributors)
- 3-5 insights (interesting patterns)
- 2-3 roasts (gentle, data-based humor)

Make it feel like a sports broadcast meets year-end celebration!"""


# Prompt for personality type assignment
PERSONALITY_PROMPT_TEMPLATE = """Assign fun, memorable personality types to these Slack channel contributors.
Think yearbook superlatives meets sports MVP awards!

CHANNEL: {channel_name}

═══════════════════════════════════════════════════
CONTRIBUTOR DATA
═══════════════════════════════════════════════════
{contributors_data}

═══════════════════════════════════════════════════
TITLE IDEAS (use these or create similar ones)
═══════════════════════════════════════════════════
- "The Announcer" - always sharing updates
- "The Novelist" - writes detailed, long messages  
- "The Sniper" - short, precise, frequent messages
- "The Emoji Artist" - expresses everything with emoji
- "The Early Bird" - online before everyone else
- "The Night Owl" - burning the midnight oil
- "The Cheerleader" - encouraging and positive
- "The Champion" - highest contributor
- "The Consistent One" - steady contributor throughout
- "The Q[X] MVP" - dominated a specific quarter
- "The Wordsmith" - great vocabulary variety
- "The Topic Starter" - initiates conversations

═══════════════════════════════════════════════════
EXAMPLE OUTPUT
═══════════════════════════════════════════════════
{{
  "personalities": [
    {{
      "username": "david.shalom",
      "title": "The Announcer",
      "funFact": "Shipped 47 updates and said 'shipped' so many times it became a catchphrase. Legend has it, he ships in his sleep. 🚢"
    }},
    {{
      "username": "alice.smith", 
      "title": "The Novelist",
      "funFact": "Average message: 42 words. Most people tweet. Alice writes essays. Quality over quantity! 📝"
    }}
  ]
}}

═══════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════

Generate a JSON response with this exact structure:
{{
  "personalities": [
    {{
      "username": "exact_username_from_data",
      "title": "Creative Title",
      "funFact": "Personalized, data-driven fun fact with a witty spin and relevant emoji"
    }}
  ]
}}

RULES:
- Each person gets a UNIQUE title (no duplicates!)
- Reference their ACTUAL stats (message count, words, favorite words)
- Keep it celebratory and fun - like roasting a friend lovingly
- Add a relevant emoji to each fun fact
- Make them feel like superstars, not just statistics"""


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
        team_stats: Optional[dict[str, dict]] = None,
    ) -> Insights:
        """
        Generate interesting insights about the channel.
        
        Args:
            stats: Channel statistics
            contributors: List of top contributors
            top_words: Most used words
            top_emoji: Most used emoji
            team_stats: Optional dict of team -> {messages, members, avg_per_person}
            
        Returns:
            Insights object with records, competitions, superlatives, and roasts
        """
        # Build quarterly breakdown
        quarterly_lines = []
        for quarter, count in stats.messages_by_quarter.items():
            quarterly_lines.append(f"- {quarter}: {count:,} messages")
        quarterly_breakdown = "\n".join(quarterly_lines)
        
        # Build team breakdown
        team_lines = []
        if team_stats:
            for team_name, team_data in team_stats.items():
                team_lines.append(
                    f"- {team_name}: {team_data['messages']} messages, "
                    f"{team_data['members']} members, "
                    f"{team_data['avg_per_person']:.1f} avg/person"
                )
        team_breakdown = "\n".join(team_lines) if team_lines else "No team data available"
        
        # Build contributors list with rankings
        contrib_lines = []
        for i, c in enumerate(contributors[:5], 1):
            rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
            contrib_lines.append(
                f"{rank_emoji} {c.display_name} ({c.username}): {c.message_count} messages "
                f"({c.contribution_percent:.1f}%), {c.word_count} words, "
                f"avg {c.average_message_length:.1f} words/msg, team: {c.team or 'N/A'}"
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
            team_breakdown=team_breakdown,
            top_contributors=top_contributors_str,
            top_words=words_str,
            top_emoji=emoji_str,
        )
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                system_prompt=INSIGHTS_SYSTEM_PROMPT,
                temperature=0.8,  # Slightly higher for more creative outputs
            )
            
            # Parse JSON response
            data = self._parse_json_response(response)
            
            # Parse records
            records = []
            for r in data.get("records", []):
                records.append(Record(
                    title=r.get("title", ""),
                    winner=r.get("winner", ""),
                    stat=r.get("stat", ""),
                    quip=r.get("quip", ""),
                ))
            
            # Parse competitions
            competitions = []
            for c in data.get("competitions", []):
                competitions.append(Competition(
                    type=c.get("type", ""),
                    participants=c.get("teams", c.get("participants", [])),
                    scores=c.get("scores", []),
                    quip=c.get("quip", ""),
                ))
            
            # Parse superlatives
            superlatives = []
            for s in data.get("superlatives", []):
                superlatives.append(Superlative(
                    title=s.get("title", ""),
                    winner=s.get("winner", ""),
                    stat=s.get("stat", ""),
                    quip=s.get("quip", ""),
                ))
            
            # Get roasts (only if enabled)
            roasts = data.get("roasts", []) if self.config.preferences.include_roasts else []
            
            return Insights(
                interesting=data.get("insights", []),
                funny=roasts,  # Keep backward compatibility
                records=records,
                competitions=competitions,
                superlatives=superlatives,
                roasts=roasts,
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
    team_stats: Optional[dict[str, dict]] = None,
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
        team_stats: Optional team comparison statistics
        
    Returns:
        Tuple of (Insights, updated contributors with personalities)
    """
    generator = InsightsGenerator(llm_client, config)
    
    # Generate insights with team stats
    insights = generator.generate_insights(
        stats, contributors, top_words, top_emoji, team_stats
    )
    
    # Assign personality types
    updated_contributors = generator.assign_personalities(contributors, favorite_words)
    
    return insights, updated_contributors
