"""Unit tests for LLM Direct Analyzer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from slack_wrapped.llm_direct_analyzer import (
    LLMDirectAnalyzer,
    UserContext,
    DirectAnalysisResult,
    analyze_raw_slack,
    MAX_CHUNK_SIZE,
    DIRECT_ANALYSIS_SYSTEM_PROMPT,
    DIRECT_ANALYSIS_EXAMPLE_INPUT,
    DIRECT_ANALYSIS_EXAMPLE_OUTPUT,
)
from slack_wrapped.llm_client import LLMClient


# Sample Slack messages in various formats
SAMPLE_SLACK_COPY_PASTE = """
Raz Konforti  [6:08 PM]
replied to a thread:
Thank you all for your valuable feedback! We're actively processing your input.

Liat Perlmutter  [7:18 PM]
Heads Up: Upcoming Redesign to the Media Library "Share" Modal
We're excited to announce improvements to the sharing experience.

Sharon Benasus Nathan  [11:23 AM]
New in Assets - External approvers in Creative Approval flows
Support adding external approvers to any approval flow.

Dan Siedner  [11:55 AM]
Update: Gen Fill 2z is Here
We're excited to announce the launch of Gen Fill 2z!
"""

SAMPLE_SLACK_ISO = """
2025-01-15T09:30:00Z david.shalom: Good morning team! Starting Q1 with fresh energy 🚀
2025-01-15T10:15:00Z bob.jones: Just deployed the new authentication module
2025-01-15T14:23:00Z carol.white: PR merged for the user dashboard redesign
"""


class TestUserContext:
    """Tests for UserContext dataclass."""
    
    def test_create_minimal_context(self):
        """Test creating context with required fields only."""
        context = UserContext(
            channel_name="product-updates",
            year=2025,
        )
        
        assert context.channel_name == "product-updates"
        assert context.year == 2025
        assert context.channel_description == ""
        assert context.team_info == ""
        assert context.include_roasts is True
        assert context.top_contributors_count == 5
    
    def test_create_full_context(self):
        """Test creating context with all fields."""
        context = UserContext(
            channel_name="product-updates",
            year=2025,
            channel_description="Product announcements and updates",
            team_info="Backend: David, Bob; Frontend: Alice, Carol",
            include_roasts=False,
            top_contributors_count=10,
        )
        
        assert context.channel_name == "product-updates"
        assert context.channel_description == "Product announcements and updates"
        assert context.team_info == "Backend: David, Bob; Frontend: Alice, Carol"
        assert context.include_roasts is False
        assert context.top_contributors_count == 10


class TestDirectAnalysisResult:
    """Tests for DirectAnalysisResult dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        result = DirectAnalysisResult()
        
        assert result.contributors == []
        assert result.total_messages == 0
        assert result.messages_by_month == {}
        assert result.messages_by_quarter == {}
        assert result.topics == []
        assert result.achievements == []
        assert result.notable_quotes == []
        assert result.personalities == []
        assert result.insights == []
        assert result.roasts == []
        assert result.year_story is None
        assert result.sentiment == "positive"
    
    def test_with_data(self):
        """Test result with actual data."""
        result = DirectAnalysisResult(
            contributors=[
                {"username": "david.shalom", "displayName": "David Shalom", "messageCount": 10}
            ],
            total_messages=10,
            messages_by_quarter={"Q1": 10},
            topics=[{"name": "Feature Launch", "frequency": "high"}],
            sentiment="celebratory",
        )
        
        assert len(result.contributors) == 1
        assert result.contributors[0]["username"] == "david.shalom"
        assert result.total_messages == 10
        assert result.sentiment == "celebratory"


class TestLLMDirectAnalyzer:
    """Tests for LLMDirectAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock(spec=LLMClient)
        self.analyzer = LLMDirectAnalyzer(self.mock_llm)
        self.context = UserContext(
            channel_name="product-updates",
            year=2025,
            channel_description="Team updates",
            team_info="Backend: David, Bob",
        )
    
    def test_chunk_text_small(self):
        """Test that small text is not chunked."""
        small_text = "This is a small message"
        chunks = self.analyzer._chunk_text(small_text)
        
        assert len(chunks) == 1
        assert chunks[0] == small_text
    
    def test_chunk_text_large(self):
        """Test that large text is chunked correctly."""
        # Create text larger than MAX_CHUNK_SIZE
        line = "This is a test message line\n"
        large_text = line * (MAX_CHUNK_SIZE // len(line) + 100)
        
        chunks = self.analyzer._chunk_text(large_text)
        
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= MAX_CHUNK_SIZE
    
    def test_parse_json_response_clean(self):
        """Test parsing clean JSON response."""
        response = '{"contributors": [], "totalMessages": 0}'
        
        result = self.analyzer._parse_json_response(response)
        
        assert result == {"contributors": [], "totalMessages": 0}
    
    def test_parse_json_response_with_markdown(self):
        """Test parsing JSON with markdown code blocks."""
        response = '''```json
{"contributors": [], "totalMessages": 0}
```'''
        
        result = self.analyzer._parse_json_response(response)
        
        assert result == {"contributors": [], "totalMessages": 0}
    
    def test_parse_json_response_with_markdown_no_language(self):
        """Test parsing JSON with markdown code blocks without language tag."""
        response = '''```
{"contributors": [], "totalMessages": 0}
```'''
        
        result = self.analyzer._parse_json_response(response)
        
        assert result == {"contributors": [], "totalMessages": 0}
    
    def test_analyze_chunk(self):
        """Test analyzing a single chunk."""
        # Mock LLM response
        mock_response = json.dumps({
            "contributors": [
                {"username": "david.shalom", "displayName": "David Shalom", "messageCount": 5}
            ],
            "totalMessages": 5,
            "messagesByMonth": {"January": 5},
            "messagesByQuarter": {"Q1": 5},
            "topics": [{"name": "Updates", "frequency": "high", "examples": []}],
            "achievements": [],
            "notableQuotes": [],
            "personalities": [],
            "insights": ["Team is active"],
            "roasts": [],
            "yearStory": None,
            "sentiment": "positive",
        })
        self.mock_llm.generate_json.return_value = mock_response
        
        result = self.analyzer._analyze_chunk(SAMPLE_SLACK_ISO, self.context, 0.5)
        
        assert isinstance(result, DirectAnalysisResult)
        assert len(result.contributors) == 1
        assert result.total_messages == 5
        self.mock_llm.generate_json.assert_called_once()
    
    def test_merge_results(self):
        """Test merging multiple analysis results."""
        result1 = DirectAnalysisResult(
            contributors=[{"username": "david", "displayName": "David", "messageCount": 5}],
            total_messages=5,
            messages_by_quarter={"Q1": 5},
            topics=[{"name": "Topic A"}],
            insights=["Insight 1"],
        )
        result2 = DirectAnalysisResult(
            contributors=[
                {"username": "david", "displayName": "David", "messageCount": 3},
                {"username": "alice", "displayName": "Alice", "messageCount": 4},
            ],
            total_messages=7,
            messages_by_quarter={"Q2": 7},
            topics=[{"name": "Topic B"}],
            insights=["Insight 2"],
        )
        
        merged = self.analyzer._merge_results([result1, result2], self.context)
        
        # Check merged contributors
        assert merged.total_messages == 12
        
        # David's count should be combined
        david = next((c for c in merged.contributors if c.get("username") == "david"), None)
        assert david is not None
        assert david["messageCount"] == 8  # 5 + 3
        
        # Alice should be present
        alice = next((c for c in merged.contributors if c.get("username") == "alice"), None)
        assert alice is not None
        assert alice["messageCount"] == 4
        
        # Quarters merged
        assert merged.messages_by_quarter == {"Q1": 5, "Q2": 7}
        
        # Topics combined
        assert len(merged.topics) == 2
        
        # Insights combined
        assert len(merged.insights) == 2
    
    def test_to_video_data(self):
        """Test converting DirectAnalysisResult to VideoData."""
        result = DirectAnalysisResult(
            contributors=[
                {"username": "david.shalom", "displayName": "David Shalom", "messageCount": 10, "team": "Backend"}
            ],
            total_messages=10,
            messages_by_quarter={"Q1": 10},
            topics=[{"name": "Updates", "frequency": "high", "examples": ["example"]}],
            achievements=[{"title": "Launched v2", "who": "Team", "when": "Q1"}],
            notable_quotes=[{"text": "Great work!", "author": "david.shalom", "context": "Celebration"}],
            personalities=[{"username": "david.shalom", "title": "The Leader", "funFact": "Led 10 updates"}],
            insights=["Team shipped fast"],
            roasts=["David never sleeps"],
            year_story={
                "opening": "Year started strong",
                "arc": "Shipped features",
                "climax": "Launched v2",
                "closing": "Great year",
            },
        )
        
        video_data = self.analyzer.to_video_data(result, self.context)
        
        # Check channel stats
        assert video_data.channel_stats.total_messages == 10
        assert video_data.channel_stats.total_contributors == 1
        
        # Check quarterly activity
        assert len(video_data.quarterly_activity) == 4
        q1 = next(q for q in video_data.quarterly_activity if q.quarter == "Q1")
        assert q1.messages == 10
        
        # Check top contributors
        assert len(video_data.top_contributors) == 1
        assert video_data.top_contributors[0].username == "david.shalom"
        assert video_data.top_contributors[0].personality_type == "The Leader"
        
        # Check content analysis
        assert video_data.content_analysis is not None
        assert video_data.content_analysis.year_story is not None
        assert video_data.content_analysis.year_story.opening == "Year started strong"
        
        # Check meta
        assert video_data.meta.channel_name == "product-updates"
        assert video_data.meta.year == 2025


class TestAnalyzeRawSlack:
    """Tests for the analyze_raw_slack convenience function."""
    
    def test_analyze_raw_slack_creates_context(self):
        """Test that analyze_raw_slack creates proper context."""
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate_json.return_value = json.dumps({
            "contributors": [],
            "totalMessages": 0,
            "messagesByMonth": {},
            "messagesByQuarter": {},
            "topics": [],
            "achievements": [],
            "notableQuotes": [],
            "personalities": [],
            "insights": [],
            "roasts": [],
            "yearStory": None,
            "sentiment": "neutral",
        })
        
        with patch.object(LLMDirectAnalyzer, 'analyze') as mock_analyze:
            mock_analyze.return_value = DirectAnalysisResult()
            
            analyze_raw_slack(
                raw_text="test",
                channel_name="test-channel",
                year=2025,
                llm_client=mock_llm,
                team_info="Test Team",
                include_roasts=False,
            )
            
            # Check that analyze was called with proper context
            mock_analyze.assert_called_once()
            call_args = mock_analyze.call_args
            context = call_args[0][1]  # Second positional arg is context
            
            assert context.channel_name == "test-channel"
            assert context.year == 2025
            assert context.team_info == "Test Team"
            assert context.include_roasts is False


class TestPromptContent:
    """Tests for prompt content and examples."""
    
    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        assert DIRECT_ANALYSIS_SYSTEM_PROMPT
        assert len(DIRECT_ANALYSIS_SYSTEM_PROMPT) > 100
    
    def test_example_input_exists(self):
        """Test that example input is defined."""
        assert DIRECT_ANALYSIS_EXAMPLE_INPUT
        assert "david.shalom" in DIRECT_ANALYSIS_EXAMPLE_INPUT.lower() or "David Shalom" in DIRECT_ANALYSIS_EXAMPLE_INPUT
    
    def test_example_output_is_valid_json(self):
        """Test that example output is valid JSON."""
        example_json = json.loads(DIRECT_ANALYSIS_EXAMPLE_OUTPUT)
        
        assert "contributors" in example_json
        assert "totalMessages" in example_json
        assert "topics" in example_json
        assert "personalities" in example_json
    
    def test_example_output_has_required_fields(self):
        """Test that example output has all required fields."""
        example_json = json.loads(DIRECT_ANALYSIS_EXAMPLE_OUTPUT)
        
        required_fields = [
            "contributors",
            "totalMessages",
            "messagesByMonth",
            "messagesByQuarter",
            "topics",
            "achievements",
            "notableQuotes",
            "personalities",
            "insights",
            "roasts",
            "yearStory",
            "sentiment",
        ]
        
        for field in required_fields:
            assert field in example_json, f"Missing required field: {field}"


class TestSlackFormatHandling:
    """Tests for handling various Slack message formats."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = Mock(spec=LLMClient)
        self.mock_llm.generate_json.return_value = json.dumps({
            "contributors": [{"username": "test", "displayName": "Test", "messageCount": 1}],
            "totalMessages": 1,
            "messagesByMonth": {},
            "messagesByQuarter": {},
            "topics": [],
            "achievements": [],
            "notableQuotes": [],
            "personalities": [],
            "insights": [],
            "roasts": [],
            "yearStory": None,
            "sentiment": "positive",
        })
        self.analyzer = LLMDirectAnalyzer(self.mock_llm)
        self.context = UserContext(channel_name="test", year=2025)
    
    def test_handles_copy_paste_format(self):
        """Test that copy-paste format is passed to LLM."""
        self.analyzer._analyze_chunk(SAMPLE_SLACK_COPY_PASTE, self.context, 0.5)
        
        # Verify the raw text was included in the prompt
        call_args = self.mock_llm.generate_json.call_args
        prompt = call_args.kwargs.get("prompt", "")
        if not prompt and call_args.args:
            prompt = call_args.args[0]
        assert "Raz Konforti" in prompt or "raz" in prompt.lower()
    
    def test_handles_iso_format(self):
        """Test that ISO timestamp format is passed to LLM."""
        self.analyzer._analyze_chunk(SAMPLE_SLACK_ISO, self.context, 0.5)
        
        # Verify the raw text was included in the prompt
        call_args = self.mock_llm.generate_json.call_args
        prompt = call_args.kwargs.get("prompt", "")
        if not prompt and call_args.args:
            prompt = call_args.args[0]
        assert "david.shalom" in prompt or "David" in prompt
