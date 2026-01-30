#!/usr/bin/env python3
"""
Interactive test script for Slack Wrapped backend.

Usage:
    python3 test_my_data.py --data messages.txt --config config.json
    python3 test_my_data.py  # Uses sample data
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from slack_wrapped.parser import SlackParser
from slack_wrapped.analyzer import ChannelAnalyzer, ContributorAnalyzer, WordAnalyzer, generate_fun_facts
from slack_wrapped.config import Config
from slack_wrapped.llm_client import create_llm_client
from slack_wrapped.insights_generator import InsightsGenerator


def print_section(title: str):
    """Print a section header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_parsing(data_path: str) -> list:
    """Test message parsing."""
    print_section("1. MESSAGE PARSING")
    
    parser = SlackParser()
    try:
        messages = parser.parse_file(data_path)
        print(f"✓ Parsed {len(messages)} messages from {data_path}")
        
        # Show sample
        print(f"\nFirst 3 messages:")
        for msg in messages[:3]:
            preview = msg.message[:50] + "..." if len(msg.message) > 50 else msg.message
            print(f"  [{msg.timestamp.strftime('%Y-%m-%d')}] {msg.username}: {preview}")
        
        return messages
    except Exception as e:
        print(f"✗ Parsing failed: {e}")
        return []


def test_config(config_path: str) -> Config:
    """Test config loading."""
    print_section("2. CONFIG VALIDATION")
    
    try:
        config = Config.load(config_path)
        print(f"✓ Config loaded: channel='{config.channel.name}', year={config.channel.year}")
        print(f"  Teams: {[t.name for t in config.teams]}")
        print(f"  User mappings: {len(config.user_mappings)}")
        return config
    except Exception as e:
        print(f"✗ Config failed: {e}")
        return None


def test_analysis(messages: list, config: Config):
    """Test message analysis."""
    print_section("3. CHANNEL ANALYSIS")
    
    channel = ChannelAnalyzer(messages, config)
    stats = channel.calculate_stats()
    
    print(f"Total messages: {stats.total_messages}")
    print(f"Total contributors: {stats.total_contributors}")
    print(f"Total words: {stats.total_words}")
    print(f"Peak hour: {stats.peak_hour}:00")
    print(f"Peak day: {stats.peak_day}")
    
    print(f"\nQuarterly breakdown:")
    quarterly = channel.get_quarterly_activity()
    for q in quarterly:
        bar = "█" * (q.messages // 2) if q.messages > 0 else "▒"
        print(f"  {q.quarter}: {bar} {q.messages}")
    
    return stats


def test_contributors(messages: list, config: Config):
    """Test contributor analysis."""
    print_section("4. TOP CONTRIBUTORS")
    
    contrib = ContributorAnalyzer(messages, config)
    contributors = contrib.rank_contributors()
    
    for i, c in enumerate(contributors[:5], 1):
        team_str = f" ({c.team})" if c.team else ""
        print(f"  {i}. {c.display_name}{team_str}: {c.message_count} msgs ({c.contribution_percent:.1f}%)")
    
    return contributors


def test_words(messages: list):
    """Test word analysis."""
    print_section("5. WORD ANALYSIS")
    
    words = WordAnalyzer(messages)
    
    top_words = words.get_most_used_words(top_n=10)
    print(f"Top words: {', '.join(w for w, _ in top_words[:5])}")
    
    top_emoji = words.get_most_used_emoji(top_n=5)
    if top_emoji:
        print(f"Top emoji: {''.join(e for e, _ in top_emoji)}")
    else:
        print("Top emoji: (none found)")
    
    longest = words.get_longest_message()
    if longest:
        preview = longest.message[:60] + "..." if len(longest.message) > 60 else longest.message
        print(f"Longest message: {longest.username}: \"{preview}\"")
    
    return words


def test_llm(stats, contributors, words, config):
    """Test LLM insights (optional)."""
    print_section("6. LLM INSIGHTS")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ OPENAI_API_KEY not set - skipping LLM test")
        print("  Set it in .env or environment to enable AI insights")
        return None
    
    try:
        client = create_llm_client(model="gpt-4o-mini")
        generator = InsightsGenerator(client, config)
        
        top_words = words.get_most_used_words(top_n=10)
        top_emoji = words.get_most_used_emoji(top_n=5)
        
        print("Generating AI insights...")
        insights = generator.generate_insights(stats, contributors, top_words, top_emoji)
        
        print(f"\n✓ Generated {len(insights.interesting)} insights:")
        for i, insight in enumerate(insights.interesting, 1):
            print(f"  {i}. {insight}")
        
        return insights
    except Exception as e:
        print(f"✗ LLM failed: {e}")
        return None


def test_fun_facts(stats, contributors, words):
    """Test fun facts generation."""
    print_section("7. FUN FACTS (Non-LLM)")
    
    fun_facts = generate_fun_facts(stats, contributors, words)
    
    for fact in fun_facts:
        print(f"  • {fact.label}: {fact.value}")
        if fact.detail:
            print(f"    {fact.detail}")
    
    return fun_facts


def main():
    parser = argparse.ArgumentParser(description="Test Slack Wrapped backend with your data")
    parser.add_argument("--data", "-d", default="tests/fixtures/sample_messages.txt",
                        help="Path to messages file")
    parser.add_argument("--config", "-c", default="tests/fixtures/sample_config.json",
                        help="Path to config file")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip LLM insights test")
    args = parser.parse_args()
    
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           SLACK WRAPPED - BACKEND TEST                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\nData file: {args.data}")
    print(f"Config file: {args.config}")
    
    # Run tests
    messages = test_parsing(args.data)
    if not messages:
        print("\n✗ Cannot continue without messages")
        sys.exit(1)
    
    config = test_config(args.config)
    if not config:
        print("\n✗ Cannot continue without config")
        sys.exit(1)
    
    stats = test_analysis(messages, config)
    contributors = test_contributors(messages, config)
    words = test_words(messages)
    fun_facts = test_fun_facts(stats, contributors, words)
    
    if not args.skip_llm:
        test_llm(stats, contributors, words, config)
    
    print_section("SUMMARY")
    print(f"✓ Messages parsed: {len(messages)}")
    print(f"✓ Contributors found: {len(contributors)}")
    print(f"✓ Fun facts generated: {len(fun_facts)}")
    print(f"✓ Backend test complete!")
    print()


if __name__ == "__main__":
    main()
