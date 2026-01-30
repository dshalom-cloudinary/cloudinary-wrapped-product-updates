"""
Video Data Generator - Assembles all analysis data into video-data.json format.

Story 5.1: Combine stats, insights, contributors into single JSON for Remotion rendering.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union, List

from .models import (
    ChannelStats,
    ContributorStats,
    FunFact,
    QuarterActivity,
    Insights,
    ContentAnalysis,
    ContentAnalysisYearStory as YearStory,
    ContentAnalysisTopicHighlight as TopicHighlight,
    ContentAnalysisQuote as Quote,
    ContentAnalysisPersonality as PersonalityType,
)

logger = logging.getLogger(__name__)


@dataclass
class VideoMeta:
    """Metadata for the video."""
    channelName: str
    year: int
    generatedAt: str


@dataclass
class TopContributor:
    """Top contributor data for video scene."""
    username: str
    displayName: str
    team: str
    messageCount: int
    contributionPercent: float
    funTitle: str
    funFact: str


@dataclass
class VideoQuarterActivity:
    """Quarter activity data for video scene."""
    quarter: str
    messages: int
    highlights: list[str]


@dataclass
class VideoFunFact:
    """Fun fact data for video scene."""
    label: str
    value: Union[str, int]
    detail: str


@dataclass
class VideoChannelStats:
    """Channel stats for video scene."""
    totalMessages: int
    totalWords: int
    totalContributors: int
    activeDays: int


@dataclass
class VideoInsights:
    """Insights data for video scene."""
    interesting: list[str]
    funny: list[str]
    stats: list[dict]
    records: list[dict]
    competitions: list[dict]
    superlatives: list[dict]
    roasts: list[str]


@dataclass
class VideoContentAnalysis:
    """Content analysis data for video scene."""
    yearStory: Optional[dict]
    topicHighlights: list[dict]
    bestQuotes: list[dict]
    personalityTypes: list[dict]


@dataclass
class SlackVideoData:
    """Complete video data structure for Slack Wrapped."""
    channelStats: VideoChannelStats
    quarterlyActivity: list[VideoQuarterActivity]
    topContributors: list[TopContributor]
    funFacts: list[VideoFunFact]
    insights: VideoInsights
    meta: VideoMeta
    contentAnalysis: Optional[VideoContentAnalysis] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "channelStats": asdict(self.channelStats),
            "quarterlyActivity": [asdict(q) for q in self.quarterlyActivity],
            "topContributors": [asdict(c) for c in self.topContributors],
            "funFacts": [asdict(f) for f in self.funFacts],
            "insights": asdict(self.insights),
            "meta": asdict(self.meta),
        }
        if self.contentAnalysis:
            result["contentAnalysis"] = asdict(self.contentAnalysis)
        return result


class VideoDataGenerator:
    """
    Generates video-data.json from analysis results.
    
    Combines:
    - Channel statistics
    - Quarterly activity
    - Top contributors with personality types
    - Fun facts
    - LLM insights
    - Content analysis (if available)
    """

    def __init__(
        self,
        channel_name: str,
        year: int,
    ):
        """
        Initialize the video data generator.
        
        Args:
            channel_name: Name of the Slack channel
            year: Year being analyzed
        """
        self.channel_name = channel_name
        self.year = year
        logger.info(f"VideoDataGenerator initialized for #{channel_name} ({year})")

    def generate(
        self,
        channel_stats: ChannelStats,
        quarterly_activity: list[QuarterActivity],
        contributors: list[ContributorStats],
        fun_facts: list[FunFact],
        insights: Optional[Insights] = None,
        content_analysis: Optional[ContentAnalysis] = None,
    ) -> SlackVideoData:
        """
        Generate complete video data from analysis results.
        
        Args:
            channel_stats: Overall channel statistics
            quarterly_activity: Activity by quarter
            contributors: List of contributor stats
            fun_facts: List of fun facts
            insights: LLM-generated insights (optional)
            content_analysis: Two-pass content analysis (optional)
            
        Returns:
            SlackVideoData ready for JSON serialization
        """
        logger.info("Generating video data...")
        
        # Convert channel stats
        video_channel_stats = VideoChannelStats(
            totalMessages=channel_stats.total_messages,
            totalWords=channel_stats.total_words,
            totalContributors=channel_stats.total_contributors,
            activeDays=channel_stats.active_days,
        )
        logger.debug(f"Channel stats: {channel_stats.total_messages} messages")
        
        # Convert quarterly activity
        video_quarterly = [
            VideoQuarterActivity(
                quarter=q.quarter,
                messages=q.messages,
                highlights=q.highlights if isinstance(q.highlights, list) else [q.highlights],
            )
            for q in quarterly_activity
        ]
        logger.debug(f"Quarterly activity: {len(video_quarterly)} quarters")
        
        # Convert top contributors
        video_contributors = self._convert_contributors(contributors, content_analysis)
        logger.debug(f"Top contributors: {len(video_contributors)}")
        
        # Convert fun facts
        video_fun_facts = [
            VideoFunFact(
                label=f.label,
                value=f.value,
                detail=f.detail,
            )
            for f in fun_facts
        ]
        logger.debug(f"Fun facts: {len(video_fun_facts)}")
        
        # Convert insights
        video_insights = self._convert_insights(insights)
        
        # Convert content analysis
        video_content = self._convert_content_analysis(content_analysis) if content_analysis else None
        
        # Build metadata
        meta = VideoMeta(
            channelName=self.channel_name,
            year=self.year,
            generatedAt=datetime.now().isoformat(),
        )
        
        video_data = SlackVideoData(
            channelStats=video_channel_stats,
            quarterlyActivity=video_quarterly,
            topContributors=video_contributors,
            funFacts=video_fun_facts,
            insights=video_insights,
            meta=meta,
            contentAnalysis=video_content,
        )
        
        logger.info("Video data generation complete")
        return video_data

    def _convert_contributors(
        self,
        contributors: list[ContributorStats],
        content_analysis: Optional[ContentAnalysis],
    ) -> list[TopContributor]:
        """Convert contributor stats to video format."""
        # Get personality types from content analysis if available
        personality_map = {}
        if content_analysis and content_analysis.personality_types:
            for pt in content_analysis.personality_types:
                personality_map[pt.username] = pt
        
        result = []
        for c in contributors[:5]:  # Top 5 contributors
            # Get personality type from content analysis or use default
            pt = personality_map.get(c.username)
            fun_title = pt.personality_type if pt else c.personality_type or "Active Contributor"
            fun_fact = pt.fun_fact if pt else c.fun_fact or f"Sent {c.message_count} messages"
            
            result.append(TopContributor(
                username=c.username,
                displayName=c.display_name,
                team=c.team or "Team",
                messageCount=c.message_count,
                contributionPercent=round(c.contribution_percent, 1),
                funTitle=fun_title,
                funFact=fun_fact,
            ))
        
        return result

    def _convert_insights(self, insights: Optional[Insights]) -> VideoInsights:
        """Convert insights to video format."""
        if not insights:
            return VideoInsights(
                interesting=[],
                funny=[],
                stats=[],
                records=[],
                competitions=[],
                superlatives=[],
                roasts=[],
            )
        
        return VideoInsights(
            interesting=insights.interesting or [],
            funny=insights.funny or [],
            stats=[asdict(s) for s in (insights.stats or [])],
            records=[asdict(r) for r in (insights.records or [])],
            competitions=[asdict(c) for c in (insights.competitions or [])],
            superlatives=[asdict(s) for s in (insights.superlatives or [])],
            roasts=insights.roasts or [],
        )

    def _convert_content_analysis(self, content: ContentAnalysis) -> VideoContentAnalysis:
        """Convert content analysis to video format."""
        # Convert year story
        year_story = None
        if content.year_story:
            year_story = {
                "opening": content.year_story.opening,
                "arc": content.year_story.arc,
                "climax": content.year_story.climax,
                "closing": content.year_story.closing,
            }
        
        # Convert topic highlights
        topics = [
            {
                "topic": t.topic,
                "insight": t.insight,
                "bestQuote": t.best_quote,
                "period": t.period,
            }
            for t in (content.topic_highlights or [])
        ]
        
        # Convert best quotes
        quotes = [
            {
                "text": q.text,
                "author": q.author,
                "context": q.context,
                "period": q.period,
            }
            for q in (content.best_quotes or [])
        ]
        
        # Convert personality types
        personalities = [
            {
                "username": p.username,
                "displayName": p.display_name,
                "personalityType": p.personality_type,
                "evidence": p.evidence,
                "funFact": p.fun_fact,
            }
            for p in (content.personality_types or [])
        ]
        
        return VideoContentAnalysis(
            yearStory=year_story,
            topicHighlights=topics,
            bestQuotes=quotes,
            personalityTypes=personalities,
        )

    def save(self, video_data: SlackVideoData, output_path: Union[Path, str]) -> Path:
        """
        Save video data to JSON file.
        
        Args:
            video_data: The video data to save
            output_path: Path to save the JSON file
            
        Returns:
            Path to the saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(video_data.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Video data saved to: {output_path}")
        return output_path

    def validate(self, video_data: SlackVideoData) -> tuple[bool, list[str]]:
        """
        Validate video data against required schema.
        
        Args:
            video_data: The video data to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check required fields
        if not video_data.meta.channelName:
            errors.append("Missing channelName in meta")
        
        if video_data.meta.year < 2000 or video_data.meta.year > 2100:
            errors.append(f"Invalid year: {video_data.meta.year}")
        
        if video_data.channelStats.totalMessages <= 0:
            errors.append("totalMessages must be positive")
        
        if len(video_data.quarterlyActivity) == 0:
            errors.append("quarterlyActivity is empty")
        
        if len(video_data.topContributors) == 0:
            errors.append("topContributors is empty")
        
        # Validate quarterly activity sums
        quarterly_sum = sum(q.messages for q in video_data.quarterlyActivity)
        if quarterly_sum > video_data.channelStats.totalMessages * 1.1:  # Allow 10% tolerance
            errors.append(
                f"Quarterly message sum ({quarterly_sum}) exceeds total ({video_data.channelStats.totalMessages})"
            )
        
        is_valid = len(errors) == 0
        if is_valid:
            logger.info("Video data validation passed")
        else:
            logger.warning(f"Video data validation failed: {errors}")
        
        return is_valid, errors


def generate_video_data(
    channel_name: str,
    year: int,
    channel_stats: ChannelStats,
    quarterly_activity: list[QuarterActivity],
    contributors: list[ContributorStats],
    fun_facts: list[FunFact],
    insights: Optional[Insights] = None,
    content_analysis: Optional[ContentAnalysis] = None,
    output_path: Optional[Union[Path, str]] = None,
) -> SlackVideoData:
    """
    Convenience function to generate and optionally save video data.
    
    Args:
        channel_name: Name of the Slack channel
        year: Year being analyzed
        channel_stats: Overall channel statistics
        quarterly_activity: Activity by quarter
        contributors: List of contributor stats
        fun_facts: List of fun facts
        insights: LLM-generated insights (optional)
        content_analysis: Two-pass content analysis (optional)
        output_path: Path to save JSON file (optional)
        
    Returns:
        SlackVideoData ready for Remotion
    """
    generator = VideoDataGenerator(channel_name, year)
    
    video_data = generator.generate(
        channel_stats=channel_stats,
        quarterly_activity=quarterly_activity,
        contributors=contributors,
        fun_facts=fun_facts,
        insights=insights,
        content_analysis=content_analysis,
    )
    
    # Validate
    is_valid, errors = generator.validate(video_data)
    if not is_valid:
        logger.warning(f"Video data validation warnings: {errors}")
    
    # Save if output path provided
    if output_path:
        generator.save(video_data, output_path)
    
    return video_data
