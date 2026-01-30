"""Content Analyzer for Slack Wrapped.

Implements two-pass content analysis using GPT-5.2 Thinking for 
semantic understanding of message content.

Pass 1: Extracts topics, achievements, sentiment, notable quotes, patterns
Pass 2: Synthesizes findings into coherent insights (handled by insight_synthesizer.py)
"""

import logging

__all__ = [
    "ContentAnalyzer",
    "ContentChunkSummary",
    "MessageChunk",
    "TopicExtraction",
    "Achievement",
    "SentimentAnalysis",
    "NotableQuote",
    "Pattern",
    "MAX_MESSAGES_PER_CHUNK",
    "CONTENT_EXTRACTION_SYSTEM_PROMPT",
    "CONTENT_EXTRACTION_PROMPT_TEMPLATE",
]
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional
from collections import defaultdict

from .llm_client import LLMClient, LLMError
from .models import SlackMessage

logger = logging.getLogger(__name__)


# Maximum messages per chunk to stay within context window limits
MAX_MESSAGES_PER_CHUNK = 100


@dataclass
class TopicExtraction:
    """A topic identified in the messages."""
    
    name: str
    frequency: Literal["high", "medium", "low"]
    sample_quote: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class Achievement:
    """An achievement or milestone identified in the messages."""
    
    description: str
    who: str  # "team", specific username, or "channel"
    date: str  # Approximate date or period
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class SentimentAnalysis:
    """Sentiment analysis for a period."""
    
    overall: Literal["excited", "neutral", "stressed", "mixed", "celebratory"]
    trend: Literal["improving", "stable", "declining", "variable"]
    notable_moods: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class NotableQuote:
    """A notable or memorable quote from the messages."""
    
    text: str
    author: str
    why_notable: str
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class Pattern:
    """A recurring pattern identified in the messages."""
    
    name: str
    description: str
    frequency: str  # e.g., "daily", "weekly", "throughout Q1"
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class ContentChunkSummary:
    """Summary of content extracted from a chunk of messages."""
    
    period: str  # e.g., "Q1 2025", "January 2025"
    message_count: int
    topics: list[TopicExtraction] = field(default_factory=list)
    achievements: list[Achievement] = field(default_factory=list)
    sentiment: Optional[SentimentAnalysis] = None
    notable_quotes: list[NotableQuote] = field(default_factory=list)
    recurring_patterns: list[Pattern] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "period": self.period,
            "messageCount": self.message_count,
            "topics": [t.to_dict() for t in self.topics],
            "achievements": [a.to_dict() for a in self.achievements],
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
            "notableQuotes": [q.to_dict() for q in self.notable_quotes],
            "recurringPatterns": [p.to_dict() for p in self.recurring_patterns],
        }


@dataclass
class MessageChunk:
    """A chunk of messages for analysis."""
    
    period: str
    messages: list[SlackMessage]
    
    @property
    def message_count(self) -> int:
        return len(self.messages)


class ContentAnalyzer:
    """Analyzes message content for semantic meaning using GPT-5.2 Thinking."""
    
    # Default model for content analysis
    DEFAULT_MODEL = "gpt-4o"
    
    def __init__(
        self,
        llm_client: LLMClient,
        model: Optional[str] = None,
    ):
        """
        Initialize content analyzer.
        
        Args:
            llm_client: LLM client for API calls
            model: Optional model override (defaults to o3-mini)
        """
        self.llm = llm_client
        self.model = model or self.DEFAULT_MODEL
    
    def chunk_messages(
        self,
        messages: list[SlackMessage],
        year: int,
    ) -> list[MessageChunk]:
        """
        Split messages into chunks by quarter or month.
        
        For smaller datasets (<400 messages), groups by quarter.
        For larger datasets, groups by month to respect context limits.
        
        Args:
            messages: List of messages to chunk
            year: Year to filter messages for
            
        Returns:
            List of MessageChunk objects
        """
        if not messages:
            return []
        
        # Filter to the specified year
        year_messages = [m for m in messages if m.timestamp.year == year]
        
        if not year_messages:
            return []
        
        # Decide chunking strategy based on volume
        total = len(year_messages)
        use_monthly = total > MAX_MESSAGES_PER_CHUNK * 4  # More than 400 messages
        
        if use_monthly:
            return self._chunk_by_month(year_messages, year)
        else:
            return self._chunk_by_quarter(year_messages, year)
    
    def _chunk_by_quarter(
        self,
        messages: list[SlackMessage],
        year: int,
    ) -> list[MessageChunk]:
        """Group messages by quarter."""
        quarters: dict[str, list[SlackMessage]] = defaultdict(list)
        
        for msg in messages:
            quarter = (msg.timestamp.month - 1) // 3 + 1
            period = f"Q{quarter} {year}"
            quarters[period].append(msg)
        
        # Create chunks in chronological order
        chunks = []
        for q in range(1, 5):
            period = f"Q{q} {year}"
            if period in quarters:
                chunk_messages = quarters[period]
                # Further split if chunk is too large
                if len(chunk_messages) > MAX_MESSAGES_PER_CHUNK:
                    sub_chunks = self._split_large_chunk(chunk_messages, period)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(MessageChunk(period=period, messages=chunk_messages))
        
        return chunks
    
    def _chunk_by_month(
        self,
        messages: list[SlackMessage],
        year: int,
    ) -> list[MessageChunk]:
        """Group messages by month."""
        months: dict[str, list[SlackMessage]] = defaultdict(list)
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        for msg in messages:
            period = f"{month_names[msg.timestamp.month - 1]} {year}"
            months[period].append(msg)
        
        # Create chunks in chronological order
        chunks = []
        for month_idx, month_name in enumerate(month_names, 1):
            period = f"{month_name} {year}"
            if period in months:
                chunk_messages = months[period]
                # Further split if chunk is too large
                if len(chunk_messages) > MAX_MESSAGES_PER_CHUNK:
                    sub_chunks = self._split_large_chunk(chunk_messages, period)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(MessageChunk(period=period, messages=chunk_messages))
        
        return chunks
    
    def _split_large_chunk(
        self,
        messages: list[SlackMessage],
        base_period: str,
    ) -> list[MessageChunk]:
        """Split a large chunk into smaller sub-chunks."""
        chunks = []
        for i in range(0, len(messages), MAX_MESSAGES_PER_CHUNK):
            sub_messages = messages[i:i + MAX_MESSAGES_PER_CHUNK]
            part = i // MAX_MESSAGES_PER_CHUNK + 1
            total_parts = (len(messages) + MAX_MESSAGES_PER_CHUNK - 1) // MAX_MESSAGES_PER_CHUNK
            period = f"{base_period} (Part {part}/{total_parts})"
            chunks.append(MessageChunk(period=period, messages=sub_messages))
        return chunks
    
    def extract_content(
        self,
        chunk: MessageChunk,
    ) -> ContentChunkSummary:
        """
        Extract semantic content from a message chunk.
        
        Uses LLM to identify topics, achievements, sentiment, quotes, and patterns.
        
        Args:
            chunk: MessageChunk to analyze
            
        Returns:
            ContentChunkSummary with extracted information
        """
        if not chunk.messages:
            return ContentChunkSummary(
                period=chunk.period,
                message_count=0,
                sentiment=SentimentAnalysis(
                    overall="neutral",
                    trend="stable",
                ),
            )
        
        # Format messages for LLM
        formatted_messages = self._format_messages_for_llm(chunk.messages)
        
        # Build prompt
        prompt = self._build_extraction_prompt(chunk.period, formatted_messages)
        
        # Store and restore model safely using try/finally for thread safety
        original_model = self.llm.model
        try:
            # Use the content analysis model
            self.llm.model = self.model
            
            response = self.llm.generate_json(
                prompt=prompt,
                system_prompt=CONTENT_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=2000,
            )
            
            # Parse response
            return self._parse_extraction_response(response, chunk)
            
        except (LLMError, Exception) as e:
            logger.warning(f"Failed to extract content for {chunk.period}: {e}")
            return self._generate_fallback_summary(chunk)
        finally:
            # Always restore original model
            self.llm.model = original_model
    
    def analyze_all_content(
        self,
        messages: list[SlackMessage],
        year: int,
    ) -> list[ContentChunkSummary]:
        """
        Analyze all messages and return content summaries.
        
        This is the main entry point for Pass 1 of two-pass analysis.
        
        Args:
            messages: All messages to analyze
            year: Year to analyze
            
        Returns:
            List of ContentChunkSummary objects, one per chunk
        """
        # Split into chunks
        chunks = self.chunk_messages(messages, year)
        
        if not chunks:
            logger.warning(f"No messages found for year {year}")
            return []
        
        logger.info(f"Analyzing {len(chunks)} chunks for {year}")
        
        # Extract content from each chunk
        summaries = []
        for chunk in chunks:
            logger.info(f"Extracting content for {chunk.period} ({chunk.message_count} messages)")
            summary = self.extract_content(chunk)
            summaries.append(summary)
        
        return summaries
    
    # Maximum characters for formatted messages to avoid exceeding context limits
    MAX_FORMATTED_CHARS = 50000  # ~12,500 tokens at 4 chars/token
    
    def _format_messages_for_llm(
        self,
        messages: list[SlackMessage],
    ) -> str:
        """Format messages for LLM input.
        
        Truncates output if it exceeds MAX_FORMATTED_CHARS to avoid
        exceeding model context limits.
        """
        lines = []
        total_chars = 0
        truncated = False
        
        for msg in messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            line = f"[{timestamp}] {msg.username}: {msg.message}"
            
            # Check if adding this line would exceed limit
            if total_chars + len(line) + 1 > self.MAX_FORMATTED_CHARS:
                truncated = True
                break
            
            lines.append(line)
            total_chars += len(line) + 1  # +1 for newline
        
        if truncated:
            logger.warning(
                f"Truncated messages from {len(messages)} to {len(lines)} "
                f"to stay within {self.MAX_FORMATTED_CHARS} char limit"
            )
        
        return "\n".join(lines)
    
    def _build_extraction_prompt(
        self,
        period: str,
        formatted_messages: str,
    ) -> str:
        """Build the content extraction prompt."""
        return CONTENT_EXTRACTION_PROMPT_TEMPLATE.format(
            period=period,
            messages=formatted_messages,
        )
    
    def _parse_extraction_response(
        self,
        response: str,
        chunk: MessageChunk,
    ) -> ContentChunkSummary:
        """Parse the LLM response into a ContentChunkSummary."""
        import json
        
        # Strip markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        data = json.loads(response)
        
        # Parse topics
        topics = []
        for t in data.get("topics", []):
            topics.append(TopicExtraction(
                name=t.get("name", ""),
                frequency=t.get("frequency", "low"),
                sample_quote=t.get("sample_quote", t.get("sampleQuote", "")),
            ))
        
        # Parse achievements
        achievements = []
        for a in data.get("achievements", []):
            achievements.append(Achievement(
                description=a.get("description", ""),
                who=a.get("who", "team"),
                date=a.get("date", chunk.period),
            ))
        
        # Parse sentiment
        sentiment_data = data.get("sentiment", {})
        sentiment = SentimentAnalysis(
            overall=sentiment_data.get("overall", "neutral"),
            trend=sentiment_data.get("trend", "stable"),
            notable_moods=sentiment_data.get("notable_moods", 
                           sentiment_data.get("notableMoods", [])),
        )
        
        # Parse notable quotes
        notable_quotes = []
        for q in data.get("notable_quotes", data.get("notableQuotes", [])):
            notable_quotes.append(NotableQuote(
                text=q.get("text", ""),
                author=q.get("author", ""),
                why_notable=q.get("why_notable", q.get("whyNotable", "")),
            ))
        
        # Parse recurring patterns
        patterns = []
        for p in data.get("recurring_patterns", data.get("recurringPatterns", [])):
            patterns.append(Pattern(
                name=p.get("name", ""),
                description=p.get("description", ""),
                frequency=p.get("frequency", ""),
            ))
        
        return ContentChunkSummary(
            period=chunk.period,
            message_count=chunk.message_count,
            topics=topics,
            achievements=achievements,
            sentiment=sentiment,
            notable_quotes=notable_quotes,
            recurring_patterns=patterns,
        )
    
    def _generate_fallback_summary(
        self,
        chunk: MessageChunk,
    ) -> ContentChunkSummary:
        """Generate a basic summary without LLM."""
        return ContentChunkSummary(
            period=chunk.period,
            message_count=chunk.message_count,
            sentiment=SentimentAnalysis(
                overall="neutral",
                trend="stable",
            ),
        )


# System prompt for content extraction
CONTENT_EXTRACTION_SYSTEM_PROMPT = """You are an expert content analyst examining Slack channel messages for a "Year in Review" video.

Your task is to extract meaningful SEMANTIC information - understanding WHAT was discussed, not just counting words:

1. TOPICS - Major subjects, projects, initiatives discussed
   - Look for project names, product features, team initiatives
   - Note frequency: high (mentioned 10+ times), medium (5-9), low (2-4)
   - Always include a representative sample quote

2. ACHIEVEMENTS - Milestones, launches, completions, celebrations
   - Shipped features, launches, releases, go-lives
   - Met goals, hit targets, closed deals
   - Team wins, individual accomplishments
   - Include WHO achieved it and approximate WHEN

3. SENTIMENT - Emotional tone and energy of the period
   - excited: high energy, enthusiasm, anticipation
   - celebratory: victories, wins, celebrations
   - stressed: deadlines, crunch, pressure
   - neutral: routine, business as usual
   - mixed: combination of highs and lows
   - Track if mood is improving, stable, or declining

4. NOTABLE QUOTES - Memorable, funny, or significant statements
   - Announcements, celebrations, memorable one-liners
   - Inside jokes that capture team culture
   - Statements that mark important moments
   - Include WHY the quote is notable

5. RECURRING PATTERNS - Behaviors, habits, inside jokes
   - Regular rituals (standups, celebrations, traditions)
   - Running jokes, catchphrases, memes
   - Communication patterns unique to this team

══════════════════════════════════════════════════════════════════════════════
PRIVACY & SAFETY GUARDRAILS
══════════════════════════════════════════════════════════════════════════════

🔒 NEVER extract or include:
- Personal identifiable information (PII): phone numbers, addresses, SSN
- Credentials: passwords, API keys, tokens, secrets
- Private matters: health, finances, personal relationships
- Confidential business data: revenue numbers, customer names, salaries
- Anything that could embarrass someone if shown publicly

✅ SAFE to include:
- Project names and feature descriptions
- Public achievement celebrations
- Team dynamics and culture
- Work-related humor and quotes
- General sentiment about work

OUTPUT: Valid JSON only. No markdown code blocks, no explanation text.
If unsure about privacy, err on the side of exclusion."""


# Few-shot example for content extraction
CONTENT_EXTRACTION_EXAMPLE_INPUT = """[2025-01-15 09:30] david.shalom: Good morning team! Starting Q1 with fresh energy 🚀
[2025-01-15 10:15] bob.jones: Just deployed the new authentication module
[2025-01-15 10:17] david.shalom: Great work Bob! That was a big rock 💪
[2025-01-15 14:23] carol.white: PR merged for the user dashboard redesign
[2025-01-16 11:00] alice.smith: Finished the API refactoring, 500 lines cleaned up!
[2025-01-16 11:05] david.shalom: Shipped! Thanks Alice, great cleanup
[2025-01-20 09:00] bob.jones: Starting work on the caching layer today
[2025-01-25 16:30] carol.white: Database migration complete 🎉"""

# Note: Curly braces are escaped for string formatting compatibility
CONTENT_EXTRACTION_EXAMPLE_OUTPUT = """{{
  "period": "Q1 2025",
  "topics": [
    {{
      "name": "Infrastructure & Security",
      "frequency": "high",
      "sample_quote": "Just deployed the new authentication module"
    }},
    {{
      "name": "Code Quality & Refactoring",
      "frequency": "medium",
      "sample_quote": "Finished the API refactoring, 500 lines cleaned up!"
    }},
    {{
      "name": "UI/UX Improvements",
      "frequency": "low",
      "sample_quote": "PR merged for the user dashboard redesign"
    }}
  ],
  "achievements": [
    {{
      "description": "Deployed new authentication module",
      "who": "bob.jones",
      "date": "January 15, 2025"
    }},
    {{
      "description": "Completed API refactoring (500 lines cleaned up)",
      "who": "alice.smith",
      "date": "January 16, 2025"
    }},
    {{
      "description": "Database migration completed",
      "who": "carol.white",
      "date": "January 25, 2025"
    }}
  ],
  "sentiment": {{
    "overall": "excited",
    "trend": "improving",
    "notable_moods": ["high energy", "celebration", "momentum"]
  }},
  "notable_quotes": [
    {{
      "text": "Starting Q1 with fresh energy 🚀",
      "author": "david.shalom",
      "why_notable": "Sets the energetic tone for the quarter"
    }},
    {{
      "text": "500 lines cleaned up!",
      "author": "alice.smith",
      "why_notable": "Impressive refactoring accomplishment"
    }},
    {{
      "text": "Database migration complete 🎉",
      "author": "carol.white",
      "why_notable": "Major infrastructure milestone"
    }}
  ],
  "recurring_patterns": [
    {{
      "name": "Shipped! Celebrations",
      "description": "Team lead celebrates each completion with 'Shipped!'",
      "frequency": "after each feature completion"
    }},
    {{
      "name": "Emoji Usage for Milestones",
      "description": "Team uses 🚀 🎉 💪 to celebrate wins",
      "frequency": "with every major announcement"
    }}
  ]
}}"""


# Prompt template for content extraction
CONTENT_EXTRACTION_PROMPT_TEMPLATE = """Analyze these Slack messages from {period} and extract semantic content for a year-end video.

═══════════════════════════════════════════════════════════════════════════════
                                    EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

**Example Messages:**
""" + CONTENT_EXTRACTION_EXAMPLE_INPUT + """

**Example Output:**
""" + CONTENT_EXTRACTION_EXAMPLE_OUTPUT + """

═══════════════════════════════════════════════════════════════════════════════
                              MESSAGES TO ANALYZE
═══════════════════════════════════════════════════════════════════════════════

{messages}

═══════════════════════════════════════════════════════════════════════════════
                            EXTRACTION INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

Read through ALL messages and identify:

1. TOPICS (3-7 items)
   - What subjects come up repeatedly?
   - What projects or features are discussed?
   - Frequency guide: high (10+ mentions), medium (5-9), low (2-4)

2. ACHIEVEMENTS (1-5 items)
   - What was shipped, launched, or completed?
   - What milestones were reached?
   - Who was involved and when?

3. SENTIMENT (1 analysis)
   - What's the overall emotional tone?
   - Is the mood improving, stable, or declining?
   - What notable moods are present?

4. NOTABLE QUOTES (2-5 items)
   - What statements are memorable or significant?
   - What captures the team spirit?
   - Why is each quote notable?

5. RECURRING PATTERNS (1-4 items)
   - What behaviors repeat?
   - Any inside jokes or catchphrases?
   - Team rituals or habits?

═══════════════════════════════════════════════════════════════════════════════
                            REQUIRED JSON OUTPUT
═══════════════════════════════════════════════════════════════════════════════

{{
  "period": "{period}",
  "topics": [
    {{
      "name": "Topic Name (e.g., 'AI Feature Launch')",
      "frequency": "high",
      "sample_quote": "Exact quote from messages mentioning this topic"
    }}
  ],
  "achievements": [
    {{
      "description": "What was achieved (e.g., 'Launched v2.0 to production')",
      "who": "team or specific username",
      "date": "When - month or specific date from messages"
    }}
  ],
  "sentiment": {{
    "overall": "excited|neutral|stressed|mixed|celebratory",
    "trend": "improving|stable|declining|variable",
    "notable_moods": ["specific moods detected like 'anticipation', 'relief', 'pride'"]
  }},
  "notable_quotes": [
    {{
      "text": "The exact quote from messages",
      "author": "username who said it",
      "why_notable": "Why this quote matters (e.g., 'Marked the launch moment')"
    }}
  ],
  "recurring_patterns": [
    {{
      "name": "Pattern name (e.g., 'Friday Celebrations')",
      "description": "What the pattern is",
      "frequency": "How often (e.g., 'weekly', 'every release')"
    }}
  ]
}}

IMPORTANT:
- Extract ONLY from the messages provided
- Use EXACT quotes from messages (don't paraphrase)
- If a category has no clear examples, return an empty array
- Prioritize positive, celebration-worthy content
- Remember: This is for a fun year-end video, not an audit"""
