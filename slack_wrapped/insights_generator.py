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
    StatHighlight,
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
INSIGHTS_PROMPT_TEMPLATE = """Create a DATA-DRIVEN "Wrapped" analysis. Every output MUST include specific numbers.

CHANNEL: {channel_name} | YEAR: {year}

══════════════════════════════════════════════════════════════════════
                         RAW DATA
══════════════════════════════════════════════════════════════════════

CHANNEL TOTALS:
  Messages: {total_messages:,} | Words: {total_words:,} | Contributors: {total_contributors}
  Active Days: {active_days} | Avg Msg Length: {avg_length:.1f} words
  Peak: {peak_hour}:00 on {peak_day}s

QUARTERLY BREAKDOWN:
{quarterly_breakdown}

TEAM COMPARISON:
{team_breakdown}

LEADERBOARD:
{top_contributors}

TOP WORDS: {top_words}
TOP EMOJI: {top_emoji}

══════════════════════════════════════════════════════════════════════
                      REQUIRED OUTPUT FORMAT
══════════════════════════════════════════════════════════════════════

Generate JSON with NUMBERS IN EVERY FIELD:

{{
  "stats": [
    {{
      "label": "Messages Per Active Day",
      "value": 1.12,
      "unit": "messages/day",
      "context": "That's 1 message every 7.1 hours of active time"
    }},
    {{
      "label": "Words Written",
      "value": 269,
      "unit": "words",
      "context": "Equivalent to 1 page of a novel"
    }},
    {{
      "label": "Team Participation Rate",
      "value": 100,
      "unit": "%",
      "context": "All 4 contributors posted at least once"
    }}
  ],
  "records": [
    {{
      "title": "Message Champion",
      "winner": "David Shalom",
      "value": 16,
      "unit": "messages",
      "comparison": "34% of total, 1.5x the runner-up",
      "quip": "Carried the channel harder than Atlas carried the world"
    }}
  ],
  "competitions": [
    {{
      "category": "Total Messages",
      "participants": ["Backend", "Frontend"],
      "scores": [26, 21],
      "winner": "Backend",
      "margin": "+5 messages (24% more)",
      "quip": "Backend wins quantity. Frontend claims quality. The debate continues."
    }}
  ],
  "superlatives": [
    {{
      "title": "The Novelist",
      "winner": "david.shalom",
      "value": 6.8,
      "unit": "words/msg",
      "percentile": "#1 of 4",
      "quip": "Uses 26% more words per message than the team average"
    }}
  ],
  "insights": [
    "Q1 dominated with 16 messages (34% of yearly total) - the team peaked early",
    "Peak hour 9:00 AM saw 12 messages (26% of total) - morning productivity confirmed"
  ],
  "roasts": [
    "With only 1.1 messages per active day, the channel embraced the art of quality silence"
  ]
}}

══════════════════════════════════════════════════════════════════════
                        STATISTICS TO CALCULATE
══════════════════════════════════════════════════════════════════════

MUST INCLUDE these calculated stats:
1. Messages per day (total_messages / active_days)
2. Words per message (total_words / total_messages)
3. Contribution distribution (top person % vs rest)
4. Quarter comparison (best vs worst quarter, % difference)
5. Team comparison (if teams exist) with margin

RECORDS to identify:
- Message Champion (most messages)
- Wordsmith (most words)
- Consistent Contributor (most even distribution across quarters)
- Most Active Quarter

SUPERLATIVES with data:
- Use actual numbers: "6.8 words/msg", "34% contribution", "#1 of 4"
- Include percentiles or rankings
- Show how they compare to average

══════════════════════════════════════════════════════════════════════

Generate 4-5 stats, 2-3 records, 1-2 competitions, 3-4 superlatives, 3-5 insights, 2-3 roasts.
EVERY item must reference specific numbers from the data!"""


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
            
            # Parse stats (new data-driven highlights)
            stat_highlights = []
            for s in data.get("stats", []):
                stat_highlights.append(StatHighlight(
                    label=s.get("label", ""),
                    value=float(s.get("value", 0)),
                    unit=s.get("unit", ""),
                    context=s.get("context", ""),
                    trend=s.get("trend", ""),
                ))
            
            # Parse records with numeric values
            records = []
            for r in data.get("records", []):
                records.append(Record(
                    title=r.get("title", ""),
                    winner=r.get("winner", ""),
                    value=int(r.get("value", 0)),
                    unit=r.get("unit", ""),
                    comparison=r.get("comparison", r.get("stat", "")),  # Fallback to stat
                    quip=r.get("quip", ""),
                ))
            
            # Parse competitions with category and margin
            competitions = []
            for c in data.get("competitions", []):
                competitions.append(Competition(
                    category=c.get("category", c.get("type", "")),
                    participants=c.get("participants", c.get("teams", [])),
                    scores=c.get("scores", []),
                    winner=c.get("winner", ""),
                    margin=c.get("margin", ""),
                    quip=c.get("quip", ""),
                ))
            
            # Parse superlatives with numeric values
            superlatives = []
            for s in data.get("superlatives", []):
                superlatives.append(Superlative(
                    title=s.get("title", ""),
                    winner=s.get("winner", ""),
                    value=float(s.get("value", 0)),
                    unit=s.get("unit", s.get("stat", "")),  # Fallback to stat
                    percentile=s.get("percentile", ""),
                    quip=s.get("quip", ""),
                ))
            
            # Get roasts (only if enabled)
            roasts = data.get("roasts", []) if self.config.preferences.include_roasts else []
            
            return Insights(
                interesting=data.get("insights", []),
                funny=roasts,  # Keep backward compatibility
                stats=stat_highlights,
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
