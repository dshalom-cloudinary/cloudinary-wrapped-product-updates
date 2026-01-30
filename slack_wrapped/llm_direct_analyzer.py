"""LLM Direct Analyzer for Slack Wrapped.

Bypasses regex-based parsing entirely and uses GPT to directly analyze
raw Slack messages and extract all information needed for video generation.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .llm_client import LLMClient, LLMError
from .models import (
    ChannelStats,
    ContributorStats,
    QuarterActivity,
    FunFact,
    Insights,
    VideoDataMeta,
    ContentAnalysis,
    ContentAnalysisYearStory,
    ContentAnalysisTopicHighlight,
    ContentAnalysisQuote,
    ContentAnalysisPersonality,
    VideoData,
    Record,
    Superlative,
    StatHighlight,
)

logger = logging.getLogger(__name__)

# Maximum characters per chunk (approximately 12,500 tokens)
MAX_CHUNK_SIZE = 50000


@dataclass
class UserContext:
    """User-provided context for the analysis."""
    
    channel_name: str
    year: int
    channel_description: str = ""
    team_info: str = ""  # Free-form team/contributor info
    include_roasts: bool = True
    top_contributors_count: int = 5


@dataclass 
class DirectAnalysisResult:
    """Result from LLM direct analysis."""
    
    contributors: list[dict] = field(default_factory=list)
    total_messages: int = 0
    messages_by_month: dict[str, int] = field(default_factory=dict)
    messages_by_quarter: dict[str, int] = field(default_factory=dict)
    topics: list[dict] = field(default_factory=list)
    achievements: list[dict] = field(default_factory=list)
    notable_quotes: list[dict] = field(default_factory=list)
    personalities: list[dict] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    roasts: list[str] = field(default_factory=list)
    year_story: Optional[dict] = None
    sentiment: str = "positive"
    

# System prompt for direct analysis
DIRECT_ANALYSIS_SYSTEM_PROMPT = """You are an expert Slack channel analyst creating a "Wrapped" video summary (like Spotify Wrapped).

Your task is to analyze raw Slack messages and extract ALL information needed to create an engaging year-end video.

## What You Must Extract

1. **Contributors**: List of all people who posted, with message counts
2. **Message Statistics**: Total messages, messages by month/quarter
3. **Topics**: Major themes discussed (3-7 topics)
4. **Achievements**: Notable milestones, releases, accomplishments
5. **Notable Quotes**: Memorable or funny quotes (3-5 quotes)
6. **Personalities**: Fun personality types for top contributors
7. **Insights**: Interesting observations about the channel
8. **Roasts**: Playful, work-appropriate roasts for contributors (if enabled)
9. **Year Story**: A narrative arc of the year

## Important Guidelines

- Extract REAL data from the messages - use actual names, quotes, and numbers
- Be accurate with counts - actually count the messages per contributor
- Keep tone celebratory, fun, and team-building
- Roasts should be playful and never mean-spirited
- Quotes must be REAL quotes from the messages (you may shorten them)
- Use the user-provided context to understand team structure

## Output Format

You MUST respond with valid JSON only. No markdown, no explanation."""


# Few-shot example for the direct analysis
DIRECT_ANALYSIS_EXAMPLE_INPUT = """
Channel: product-updates
Year: 2025
Context: Engineering team product updates. Teams: Backend (David, Bob), Frontend (Alice, Carol).

RAW MESSAGES:
David Shalom  [9:30 AM]
Good morning team! Starting Q1 with fresh energy 🚀

Alice Smith  [9:32 AM]
Morning David! Ready to ship some features

Bob Jones  [10:15 AM]
Just deployed the new authentication module

David Shalom  [10:17 AM]
Great work Bob! That was a big rock 💪

Carol White  [2:23 PM]
PR merged for the user dashboard redesign

Alice Smith  [11:00 AM]
Finished the API refactoring, 500 lines cleaned up

David Shalom  [11:05 AM]
Shipped! Thanks Alice, great cleanup
"""

DIRECT_ANALYSIS_EXAMPLE_OUTPUT = """{
  "contributors": [
    {"username": "david.shalom", "displayName": "David Shalom", "messageCount": 3, "team": "Backend"},
    {"username": "alice.smith", "displayName": "Alice Smith", "messageCount": 2, "team": "Frontend"},
    {"username": "bob.jones", "displayName": "Bob Jones", "messageCount": 1, "team": "Backend"},
    {"username": "carol.white", "displayName": "Carol White", "messageCount": 1, "team": "Frontend"}
  ],
  "totalMessages": 7,
  "messagesByMonth": {"January": 7},
  "messagesByQuarter": {"Q1": 7},
  "topics": [
    {"name": "Feature Releases", "frequency": "high", "examples": ["authentication module", "dashboard redesign"]},
    {"name": "Code Quality", "frequency": "medium", "examples": ["API refactoring", "500 lines cleaned up"]}
  ],
  "achievements": [
    {"title": "Authentication Module Launch", "who": "Bob Jones", "when": "Q1"},
    {"title": "Dashboard Redesign", "who": "Carol White", "when": "Q1"},
    {"title": "Major Refactoring", "who": "Alice Smith", "when": "Q1", "details": "500 lines cleaned up"}
  ],
  "notableQuotes": [
    {"text": "Starting Q1 with fresh energy 🚀", "author": "David Shalom", "context": "Kickoff energy"},
    {"text": "500 lines cleaned up", "author": "Alice Smith", "context": "Impressive refactoring"}
  ],
  "personalities": [
    {"username": "david.shalom", "title": "The Hype Master", "funFact": "Said 'Shipped!' 2 times - keeps the team motivated!"},
    {"username": "alice.smith", "title": "The Refactorer", "funFact": "Cleaned up 500 lines in one go. Code quality champion!"},
    {"username": "bob.jones", "title": "The Auth Guardian", "funFact": "Deployed the authentication module - security first!"},
    {"username": "carol.white", "title": "The Designer", "funFact": "Merged the dashboard redesign PR. Making things pretty!"}
  ],
  "insights": [
    "This team ships fast - 4 major features in just these few messages!",
    "Strong culture of recognition - teammates regularly celebrate each other's wins",
    "Backend and Frontend teams work closely together"
  ],
  "roasts": [
    "David might as well change his Slack status to 'Shipped!' permanently 🚢",
    "Alice refactored 500 lines. The other 500 are scheduled for 2026.",
    "Bob deployed auth and immediately went back to lurking"
  ],
  "yearStory": {
    "opening": "The year started with fresh energy and ambitious goals",
    "arc": "The team dove into major infrastructure improvements - auth, dashboards, and code quality",
    "climax": "Multiple major features shipped in quick succession",
    "closing": "A testament to strong teamwork and shipping culture"
  },
  "sentiment": "celebratory"
}"""


# User prompt template
DIRECT_ANALYSIS_PROMPT_TEMPLATE = """## Channel Context
- **Channel Name**: {channel_name}
- **Year**: {year}
- **Description**: {channel_description}
- **Team Info**: {team_info}
- **Include Roasts**: {include_roasts}

## Example

**Input:**
{example_input}

**Expected Output:**
{example_output}

---

## Your Task

Analyze the following raw Slack messages and extract all information needed for the Wrapped video.

**RAW SLACK MESSAGES:**

{raw_messages}

---

**IMPORTANT**: 
- Count messages accurately for each contributor
- Extract REAL quotes from the messages above
- Use the team info provided to assign people to teams
- Generate {top_n} personality entries for top contributors
- Output ONLY valid JSON matching the example structure above"""


class LLMDirectAnalyzer:
    """Analyzes raw Slack messages directly using LLM without parsing."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the direct analyzer.
        
        Args:
            llm_client: Configured LLM client
        """
        self.llm = llm_client
    
    def analyze(
        self,
        raw_text: str,
        context: UserContext,
        temperature: float = 0.5,
    ) -> DirectAnalysisResult:
        """
        Analyze raw Slack messages directly.
        
        Args:
            raw_text: Raw Slack message text (any format)
            context: User-provided context
            temperature: LLM temperature for generation
            
        Returns:
            DirectAnalysisResult with extracted information
        """
        logger.info(f"Starting direct analysis of {len(raw_text)} characters")
        
        # Chunk the text if too large
        chunks = self._chunk_text(raw_text)
        logger.info(f"Split into {len(chunks)} chunks")
        
        if len(chunks) == 1:
            # Single chunk - analyze directly
            return self._analyze_chunk(chunks[0], context, temperature)
        else:
            # Multiple chunks - analyze each and merge
            chunk_results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Analyzing chunk {i+1}/{len(chunks)}")
                result = self._analyze_chunk(chunk, context, temperature)
                chunk_results.append(result)
            
            return self._merge_results(chunk_results, context)
    
    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks that fit within context limits."""
        if len(text) <= MAX_CHUNK_SIZE:
            return [text]
        
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > MAX_CHUNK_SIZE:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _analyze_chunk(
        self,
        chunk: str,
        context: UserContext,
        temperature: float,
    ) -> DirectAnalysisResult:
        """Analyze a single chunk of messages."""
        
        prompt = DIRECT_ANALYSIS_PROMPT_TEMPLATE.format(
            channel_name=context.channel_name,
            year=context.year,
            channel_description=context.channel_description or "Team communication channel",
            team_info=context.team_info or "No specific team info provided",
            include_roasts="Yes" if context.include_roasts else "No",
            example_input=DIRECT_ANALYSIS_EXAMPLE_INPUT.strip(),
            example_output=DIRECT_ANALYSIS_EXAMPLE_OUTPUT.strip(),
            raw_messages=chunk,
            top_n=context.top_contributors_count,
        )
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                system_prompt=DIRECT_ANALYSIS_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=4000,
            )
            
            # Parse JSON response
            data = self._parse_json_response(response)
            
            return DirectAnalysisResult(
                contributors=data.get("contributors", []),
                total_messages=data.get("totalMessages", 0),
                messages_by_month=data.get("messagesByMonth", {}),
                messages_by_quarter=data.get("messagesByQuarter", {}),
                topics=data.get("topics", []),
                achievements=data.get("achievements", []),
                notable_quotes=data.get("notableQuotes", []),
                personalities=data.get("personalities", []),
                insights=data.get("insights", []),
                roasts=data.get("roasts", []) if context.include_roasts else [],
                year_story=data.get("yearStory"),
                sentiment=data.get("sentiment", "positive"),
            )
            
        except Exception as e:
            logger.error(f"Error analyzing chunk: {e}")
            raise LLMError(f"Failed to analyze messages: {e}")
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response, handling common issues."""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            # Try to extract JSON from response
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise LLMError(f"Failed to parse JSON response: {e}")
    
    def _merge_results(
        self,
        results: list[DirectAnalysisResult],
        context: UserContext,
    ) -> DirectAnalysisResult:
        """Merge results from multiple chunks."""
        
        # Merge contributors (combine counts for same username)
        contributors_map: dict[str, dict] = {}
        for result in results:
            for contrib in result.contributors:
                username = contrib.get("username", "")
                if username in contributors_map:
                    contributors_map[username]["messageCount"] += contrib.get("messageCount", 0)
                else:
                    contributors_map[username] = contrib.copy()
        
        # Sort by message count
        merged_contributors = sorted(
            contributors_map.values(),
            key=lambda x: x.get("messageCount", 0),
            reverse=True,
        )
        
        # Merge message counts
        total_messages = sum(r.total_messages for r in results)
        
        # Merge monthly counts
        messages_by_month: dict[str, int] = {}
        for result in results:
            for month, count in result.messages_by_month.items():
                messages_by_month[month] = messages_by_month.get(month, 0) + count
        
        # Merge quarterly counts
        messages_by_quarter: dict[str, int] = {}
        for result in results:
            for quarter, count in result.messages_by_quarter.items():
                messages_by_quarter[quarter] = messages_by_quarter.get(quarter, 0) + count
        
        # Combine unique topics
        all_topics = []
        seen_topics = set()
        for result in results:
            for topic in result.topics:
                name = topic.get("name", "")
                if name and name not in seen_topics:
                    all_topics.append(topic)
                    seen_topics.add(name)
        
        # Combine achievements (take unique ones)
        all_achievements = []
        seen_achievements = set()
        for result in results:
            for achievement in result.achievements:
                title = achievement.get("title", "")
                if title and title not in seen_achievements:
                    all_achievements.append(achievement)
                    seen_achievements.add(title)
        
        # Combine notable quotes (limit to best ones)
        all_quotes = []
        for result in results:
            all_quotes.extend(result.notable_quotes)
        all_quotes = all_quotes[:5]  # Keep top 5
        
        # Keep personalities from first chunk that found them
        personalities = []
        seen_usernames = set()
        for result in results:
            for p in result.personalities:
                username = p.get("username", "")
                if username and username not in seen_usernames:
                    personalities.append(p)
                    seen_usernames.add(username)
        personalities = personalities[:context.top_contributors_count]
        
        # Combine insights (unique)
        all_insights = []
        seen_insights = set()
        for result in results:
            for insight in result.insights:
                if insight not in seen_insights:
                    all_insights.append(insight)
                    seen_insights.add(insight)
        all_insights = all_insights[:8]  # Limit
        
        # Combine roasts
        all_roasts = []
        for result in results:
            all_roasts.extend(result.roasts)
        all_roasts = all_roasts[:5]  # Limit
        
        # Use first year story found
        year_story = None
        for result in results:
            if result.year_story:
                year_story = result.year_story
                break
        
        return DirectAnalysisResult(
            contributors=merged_contributors,
            total_messages=total_messages,
            messages_by_month=messages_by_month,
            messages_by_quarter=messages_by_quarter,
            topics=all_topics[:7],
            achievements=all_achievements[:10],
            notable_quotes=all_quotes,
            personalities=personalities,
            insights=all_insights,
            roasts=all_roasts,
            year_story=year_story,
            sentiment=results[0].sentiment if results else "positive",
        )
    
    def to_video_data(
        self,
        result: DirectAnalysisResult,
        context: UserContext,
    ) -> VideoData:
        """Convert DirectAnalysisResult to VideoData for rendering."""
        
        # Build channel stats
        channel_stats = ChannelStats(
            total_messages=result.total_messages,
            total_words=result.total_messages * 15,  # Estimate
            total_contributors=len(result.contributors),
            active_days=len(result.messages_by_month) * 20,  # Estimate
            messages_by_user={
                c.get("username", ""): c.get("messageCount", 0)
                for c in result.contributors
            },
            messages_by_quarter=result.messages_by_quarter,
            messages_by_day_of_week={},
            peak_hour=10,  # Default
            peak_day="Wednesday",  # Default
        )
        
        # Build quarterly activity
        quarterly_activity = []
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:
            count = result.messages_by_quarter.get(quarter, 0)
            # Find achievements for this quarter
            highlights = [
                a.get("title", "")
                for a in result.achievements
                if a.get("when", "") == quarter
            ]
            quarterly_activity.append(QuarterActivity(
                quarter=quarter,
                messages=count,
                highlights=highlights[:3],
            ))
        
        # Build top contributors
        top_contributors = []
        personality_map = {
            p.get("username", ""): p
            for p in result.personalities
        }
        
        for contrib in result.contributors[:context.top_contributors_count]:
            username = contrib.get("username", "")
            personality = personality_map.get(username, {})
            
            total = result.total_messages or 1
            contribution_percent = (contrib.get("messageCount", 0) / total) * 100
            
            top_contributors.append(ContributorStats(
                username=username,
                display_name=contrib.get("displayName", username),
                team=contrib.get("team", ""),
                message_count=contrib.get("messageCount", 0),
                word_count=contrib.get("messageCount", 0) * 15,  # Estimate
                contribution_percent=round(contribution_percent, 1),
                personality_type=personality.get("title", ""),
                fun_fact=personality.get("funFact", ""),
            ))
        
        # Build fun facts
        fun_facts = []
        if result.topics:
            fun_facts.append(FunFact(
                label="Top Topic",
                value=result.topics[0].get("name", "Shipping"),
                detail="The most discussed topic this year",
            ))
        if result.contributors:
            top = result.contributors[0]
            fun_facts.append(FunFact(
                label="Most Active",
                value=top.get("displayName", ""),
                detail=f"{top.get('messageCount', 0)} messages",
            ))
        fun_facts.append(FunFact(
            label="Total Messages",
            value=str(result.total_messages),
            detail=f"From {len(result.contributors)} contributors",
        ))
        
        # Build insights
        stats_highlights = []
        for i, insight in enumerate(result.insights[:3]):
            stats_highlights.append(StatHighlight(
                label=f"Insight {i+1}",
                value=0,
                unit="",
                context=insight,
                trend="stable",
            ))
        
        records = []
        for achievement in result.achievements[:3]:
            records.append(Record(
                title=achievement.get("title", ""),
                winner=achievement.get("who", ""),
                value=1,
                unit="achievement",
                comparison=achievement.get("when", ""),
                quip=achievement.get("details", "Great work!"),
            ))
        
        superlatives = []
        for personality in result.personalities[:3]:
            superlatives.append(Superlative(
                title=personality.get("title", ""),
                winner=personality.get("username", ""),
                value=0,
                unit="",
                percentile="Top contributor",
                quip=personality.get("funFact", ""),
            ))
        
        insights = Insights(
            interesting=result.insights,
            funny=result.roasts[:3] if result.roasts else [],
            stats=stats_highlights,
            records=records,
            competitions=[],
            superlatives=superlatives,
            roasts=result.roasts,
        )
        
        # Build content analysis
        year_story_obj = None
        if result.year_story:
            year_story_obj = ContentAnalysisYearStory(
                opening=result.year_story.get("opening", ""),
                arc=result.year_story.get("arc", ""),
                climax=result.year_story.get("climax", ""),
                closing=result.year_story.get("closing", ""),
            )
        
        topic_highlights = []
        for topic in result.topics[:5]:
            examples = topic.get("examples", [])
            topic_highlights.append(ContentAnalysisTopicHighlight(
                topic=topic.get("name", ""),
                insight=f"Frequency: {topic.get('frequency', 'medium')}",
                best_quote=examples[0] if examples else "",
                period=context.year,
            ))
        
        best_quotes = []
        for quote in result.notable_quotes[:5]:
            best_quotes.append(ContentAnalysisQuote(
                text=quote.get("text", ""),
                author=quote.get("author", ""),
                context=quote.get("context", ""),
                period=str(context.year),
            ))
        
        personality_types = []
        for p in result.personalities:
            personality_types.append(ContentAnalysisPersonality(
                username=p.get("username", ""),
                display_name=p.get("username", "").replace(".", " ").title(),
                personality_type=p.get("title", ""),
                evidence="",
                fun_fact=p.get("funFact", ""),
            ))
        
        content_analysis = ContentAnalysis(
            year_story=year_story_obj,
            topic_highlights=topic_highlights,
            best_quotes=best_quotes,
            personality_types=personality_types,
        )
        
        # Build meta
        meta = VideoDataMeta(
            channel_name=context.channel_name,
            year=context.year,
            generated_at=datetime.now().isoformat(),
        )
        
        return VideoData(
            channel_stats=channel_stats,
            quarterly_activity=quarterly_activity,
            top_contributors=top_contributors,
            fun_facts=fun_facts,
            insights=insights,
            meta=meta,
            content_analysis=content_analysis,
        )


def analyze_raw_slack(
    raw_text: str,
    channel_name: str,
    year: int,
    llm_client: LLMClient,
    channel_description: str = "",
    team_info: str = "",
    include_roasts: bool = True,
    top_contributors_count: int = 5,
) -> VideoData:
    """
    Convenience function to analyze raw Slack messages directly.
    
    Args:
        raw_text: Raw Slack message text (any format)
        channel_name: Name of the Slack channel
        year: Year to analyze
        llm_client: Configured LLM client
        channel_description: Optional channel description
        team_info: Optional team/contributor info
        include_roasts: Whether to generate roasts
        top_contributors_count: Number of top contributors to highlight
        
    Returns:
        VideoData ready for rendering
    """
    context = UserContext(
        channel_name=channel_name,
        year=year,
        channel_description=channel_description,
        team_info=team_info,
        include_roasts=include_roasts,
        top_contributors_count=top_contributors_count,
    )
    
    analyzer = LLMDirectAnalyzer(llm_client)
    result = analyzer.analyze(raw_text, context)
    return analyzer.to_video_data(result, context)
