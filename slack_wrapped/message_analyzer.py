"""Message analyzer for Slack Wrapped interactive setup.

Analyzes raw Slack messages using LLM to extract context-aware insights
and generate smart questions for the user.
"""

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .llm_client import LLMClient, LLMError
from .models import SlackMessage
from .parser import SlackParser

logger = logging.getLogger(__name__)


# System prompt for message analysis
ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing Slack channel data for a "Wrapped" video generator.

Your job is to:
1. Identify patterns and themes in the messages
2. Understand the channel's purpose and culture
3. Recognize key achievements and milestones
4. Suggest team groupings based on interaction patterns
5. Generate smart questions to fill in missing context

Be insightful and observant. Look for:
- Recurring topics and keywords
- Celebration patterns (shipped, released, deployed, etc.)
- Team dynamics and collaboration
- Milestone moments worth highlighting
"""

# Prompt template for message analysis
ANALYSIS_PROMPT_TEMPLATE = """Analyze these Slack channel messages and provide insights.

═══════════════════════════════════════════════════════════════════════════════
                         MESSAGE DATA
═══════════════════════════════════════════════════════════════════════════════

BASIC STATS:
- Total Messages: {total_messages}
- Date Range: {date_range}
- Unique Contributors: {contributor_count}

CONTRIBUTORS (by message count):
{contributors_list}

SAMPLE MESSAGES (first 50):
{sample_messages}

═══════════════════════════════════════════════════════════════════════════════
                         ANALYSIS REQUEST
═══════════════════════════════════════════════════════════════════════════════

Analyze these messages and return a JSON object with:

{{
  "channel_analysis": {{
    "likely_name": "suggested channel name based on content",
    "purpose": "what this channel is primarily used for",
    "tone": "formal|casual|celebratory|technical|mixed",
    "main_topics": ["topic1", "topic2", "topic3"],
    "key_milestones": ["milestone1", "milestone2"],
    "notable_patterns": ["pattern observed in the messages"]
  }},
  "team_suggestions": [
    {{
      "name": "Suggested Team Name",
      "members": ["username1", "username2"],
      "reasoning": "why these users seem to form a team"
    }}
  ],
  "user_display_names": [
    {{
      "username": "david.shalom",
      "suggested_name": "David Shalom",
      "confidence": "high|medium|low"
    }}
  ],
  "highlights": [
    {{
      "type": "achievement|milestone|celebration|funny",
      "description": "what happened",
      "quote": "relevant quote from messages",
      "contributor": "username"
    }}
  ],
  "questions_for_user": [
    {{
      "id": "channel_name",
      "question": "What is the name of this Slack channel?",
      "suggestion": "product-updates",
      "required": true
    }},
    {{
      "id": "confirm_teams",
      "question": "I noticed these potential teams. Is this grouping correct?",
      "suggestion": "Based on interaction patterns...",
      "required": false
    }}
  ]
}}

Focus on being helpful and asking the right questions to create an accurate config.
"""


@dataclass
class UserSuggestion:
    """Suggested display name for a username."""
    
    username: str
    suggested_name: str
    message_count: int
    confidence: str = "medium"


@dataclass
class TeamSuggestion:
    """Suggested team grouping."""
    
    name: str
    members: list[str]
    reasoning: str = ""


@dataclass
class Highlight:
    """Notable moment from the messages."""
    
    type: str  # achievement, milestone, celebration, funny
    description: str
    quote: str = ""
    contributor: str = ""


@dataclass
class Question:
    """Question to ask the user."""
    
    id: str
    question: str
    suggestion: str = ""
    required: bool = False
    type: str = "text"  # text, confirm, select, multi_select
    options: list[str] = field(default_factory=list)


@dataclass
class ChannelAnalysis:
    """LLM-generated analysis of the channel."""
    
    likely_name: str = ""
    purpose: str = ""
    tone: str = ""
    main_topics: list[str] = field(default_factory=list)
    key_milestones: list[str] = field(default_factory=list)
    notable_patterns: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete analysis result from MessageAnalyzer."""
    
    # Basic stats (extracted directly from messages)
    total_messages: int
    date_range: tuple[datetime, datetime]
    usernames: list[str]
    message_counts: dict[str, int]
    
    # LLM-generated insights
    channel_analysis: ChannelAnalysis
    team_suggestions: list[TeamSuggestion]
    user_suggestions: list[UserSuggestion]
    highlights: list[Highlight]
    questions: list[Question]
    
    # Raw messages for later use
    messages: list[SlackMessage] = field(default_factory=list)
    
    @property
    def year(self) -> int:
        """Get the year from messages."""
        if self.date_range[0]:
            return self.date_range[0].year
        return datetime.now().year


class MessageAnalyzer:
    """Analyzes Slack messages to extract insights and generate questions."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize message analyzer.
        
        Args:
            llm_client: LLM client for AI analysis
        """
        self.llm = llm_client
    
    def analyze(
        self,
        messages: list[SlackMessage],
        sample_size: int = 50,
    ) -> AnalysisResult:
        """
        Analyze messages and generate insights.
        
        Args:
            messages: Parsed Slack messages
            sample_size: Number of messages to include in LLM prompt
            
        Returns:
            AnalysisResult with stats, insights, and questions
        """
        # Extract basic stats
        basic_stats = self._extract_basic_stats(messages)
        
        # Prepare sample messages for LLM
        sample_messages = self._format_sample_messages(messages, sample_size)
        
        # Format contributors list
        contributors_list = self._format_contributors(basic_stats["message_counts"])
        
        # Format date range
        date_range = basic_stats["date_range"]
        date_range_str = f"{date_range[0].strftime('%Y-%m-%d')} to {date_range[1].strftime('%Y-%m-%d')}"
        
        # Build prompt
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            total_messages=len(messages),
            date_range=date_range_str,
            contributor_count=len(basic_stats["usernames"]),
            contributors_list=contributors_list,
            sample_messages=sample_messages,
        )
        
        # Get LLM analysis
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                system_prompt=ANALYSIS_SYSTEM_PROMPT,
                temperature=0.6,
                max_tokens=3000,
            )
            
            llm_result = self._parse_llm_response(response)
        except (LLMError, json.JSONDecodeError) as e:
            logger.warning(f"LLM analysis failed, using fallback: {e}")
            llm_result = self._generate_fallback_analysis(basic_stats)
        
        # Build user suggestions with message counts
        user_suggestions = []
        for username in basic_stats["usernames"]:
            suggested = self._suggest_display_name(username)
            # Check if LLM had a suggestion
            llm_suggestion = next(
                (u for u in llm_result.get("user_suggestions", [])
                 if u.get("username") == username),
                None
            )
            if llm_suggestion:
                suggested = llm_suggestion.get("suggested_name", suggested)
                confidence = llm_suggestion.get("confidence", "medium")
            else:
                confidence = "low"
            
            user_suggestions.append(UserSuggestion(
                username=username,
                suggested_name=suggested,
                message_count=basic_stats["message_counts"][username],
                confidence=confidence,
            ))
        
        # Sort by message count
        user_suggestions.sort(key=lambda x: x.message_count, reverse=True)
        
        # Build team suggestions
        team_suggestions = [
            TeamSuggestion(
                name=t.get("name", "Team"),
                members=t.get("members", []),
                reasoning=t.get("reasoning", ""),
            )
            for t in llm_result.get("team_suggestions", [])
        ]
        
        # Build highlights
        highlights = [
            Highlight(
                type=h.get("type", "achievement"),
                description=h.get("description", ""),
                quote=h.get("quote", ""),
                contributor=h.get("contributor", ""),
            )
            for h in llm_result.get("highlights", [])
        ]
        
        # Build questions
        questions = self._build_questions(llm_result, basic_stats)
        
        # Build channel analysis
        ca = llm_result.get("channel_analysis", {})
        channel_analysis = ChannelAnalysis(
            likely_name=ca.get("likely_name", ""),
            purpose=ca.get("purpose", ""),
            tone=ca.get("tone", ""),
            main_topics=ca.get("main_topics", []),
            key_milestones=ca.get("key_milestones", []),
            notable_patterns=ca.get("notable_patterns", []),
        )
        
        return AnalysisResult(
            total_messages=len(messages),
            date_range=date_range,
            usernames=basic_stats["usernames"],
            message_counts=basic_stats["message_counts"],
            channel_analysis=channel_analysis,
            team_suggestions=team_suggestions,
            user_suggestions=user_suggestions,
            highlights=highlights,
            questions=questions,
            messages=messages,
        )
    
    def analyze_file(self, filepath: str) -> AnalysisResult:
        """
        Analyze messages from a file.
        
        Args:
            filepath: Path to raw messages file
            
        Returns:
            AnalysisResult with stats, insights, and questions
        """
        parser = SlackParser()
        messages = parser.parse_file(filepath)
        return self.analyze(messages)
    
    def _extract_basic_stats(self, messages: list[SlackMessage]) -> dict:
        """Extract basic statistics from messages."""
        usernames = set()
        message_counts = Counter()
        
        min_date = None
        max_date = None
        
        for msg in messages:
            usernames.add(msg.username)
            message_counts[msg.username] += 1
            
            if min_date is None or msg.timestamp < min_date:
                min_date = msg.timestamp
            if max_date is None or msg.timestamp > max_date:
                max_date = msg.timestamp
        
        return {
            "usernames": sorted(usernames),
            "message_counts": dict(message_counts),
            "date_range": (min_date, max_date),
        }
    
    def _format_sample_messages(
        self,
        messages: list[SlackMessage],
        sample_size: int,
    ) -> str:
        """Format sample messages for the LLM prompt."""
        # Take evenly distributed samples
        if len(messages) <= sample_size:
            sample = messages
        else:
            step = len(messages) // sample_size
            sample = [messages[i] for i in range(0, len(messages), step)][:sample_size]
        
        lines = []
        for msg in sample:
            date_str = msg.timestamp.strftime("%Y-%m-%d")
            lines.append(f"[{date_str}] {msg.username}: {msg.message}")
        
        return "\n".join(lines)
    
    def _format_contributors(self, message_counts: dict[str, int]) -> str:
        """Format contributors list for prompt."""
        sorted_users = sorted(
            message_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        lines = []
        for username, count in sorted_users:
            lines.append(f"- {username}: {count} messages")
        
        return "\n".join(lines)
    
    def _parse_llm_response(self, response: str) -> dict:
        """Parse JSON response from LLM."""
        # Strip markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)
        
        return json.loads(response)
    
    def _suggest_display_name(self, username: str) -> str:
        """Generate a display name suggestion from username."""
        # Handle common patterns
        # david.shalom -> David Shalom
        # david_shalom -> David Shalom
        # davidshalom -> Davidshalom (can't split)
        
        parts = username.replace("_", ".").split(".")
        return " ".join(part.capitalize() for part in parts)
    
    def _build_questions(self, llm_result: dict, basic_stats: dict) -> list[Question]:
        """Build the list of questions to ask the user."""
        questions = []
        
        # Get LLM-generated questions
        for q in llm_result.get("questions_for_user", []):
            questions.append(Question(
                id=q.get("id", f"q_{len(questions)}"),
                question=q.get("question", ""),
                suggestion=q.get("suggestion", ""),
                required=q.get("required", False),
                type=q.get("type", "text"),
                options=q.get("options", []),
            ))
        
        # Ensure we have essential questions
        question_ids = {q.id for q in questions}
        
        # Channel name (required)
        if "channel_name" not in question_ids:
            ca = llm_result.get("channel_analysis", {})
            questions.insert(0, Question(
                id="channel_name",
                question="What is the name of this Slack channel?",
                suggestion=ca.get("likely_name", ""),
                required=True,
                type="text",
            ))
        
        # Year (required)
        if "year" not in question_ids:
            year = basic_stats["date_range"][0].year if basic_stats["date_range"][0] else datetime.now().year
            questions.insert(1, Question(
                id="year",
                question="What year is this Wrapped for?",
                suggestion=str(year),
                required=True,
                type="text",
            ))
        
        # Include roasts preference
        if "include_roasts" not in question_ids:
            questions.append(Question(
                id="include_roasts",
                question="Include gentle roasts and playful humor in the video?",
                suggestion="yes",
                required=False,
                type="confirm",
            ))
        
        # Top contributors count
        if "top_contributors_count" not in question_ids:
            questions.append(Question(
                id="top_contributors_count",
                question="How many top contributors should be highlighted?",
                suggestion="5",
                required=False,
                type="text",
            ))
        
        return questions
    
    def _generate_fallback_analysis(self, basic_stats: dict) -> dict:
        """Generate fallback analysis without LLM."""
        usernames = basic_stats["usernames"]
        
        return {
            "channel_analysis": {
                "likely_name": "channel",
                "purpose": "Team communication and updates",
                "tone": "casual",
                "main_topics": [],
                "key_milestones": [],
                "notable_patterns": [],
            },
            "team_suggestions": [],
            "user_suggestions": [
                {
                    "username": u,
                    "suggested_name": self._suggest_display_name(u),
                    "confidence": "low",
                }
                for u in usernames
            ],
            "highlights": [],
            "questions_for_user": [],
        }


def analyze_messages(
    filepath: str,
    llm_client: LLMClient,
) -> AnalysisResult:
    """
    Convenience function to analyze messages from a file.
    
    Args:
        filepath: Path to raw messages file
        llm_client: LLM client for AI analysis
        
    Returns:
        AnalysisResult with stats, insights, and questions
    """
    analyzer = MessageAnalyzer(llm_client)
    return analyzer.analyze_file(filepath)
