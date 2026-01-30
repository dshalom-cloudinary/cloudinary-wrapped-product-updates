"""CLI entry point for Slack Wrapped."""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from .config import Config, ConfigValidator

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    name="slack-wrapped",
    help="Generate a Wrapped-style summary video from Slack channel activity.",
)
console = Console()


@app.command()
def generate(
    data: str = typer.Option(
        ...,
        "--data",
        "-d",
        help="Path to raw Slack messages text file.",
    ),
    config: str = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to config.json file with channel info and user mappings.",
    ),
    output: str = typer.Option(
        "output",
        "--output",
        "-o",
        help="Directory to save output files.",
    ),
    openai_key: Optional[str] = typer.Option(
        None,
        "--openai-key",
        envvar="OPENAI_API_KEY",
        help="OpenAI API key for AI-powered insights.",
    ),
    openai_model: str = typer.Option(
        "gpt-5.2",
        "--model",
        "-m",
        help="OpenAI model to use for insights generation.",
    ),
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="Skip LLM insights generation (basic stats only).",
    ),
    skip_content_analysis: bool = typer.Option(
        False,
        "--skip-content-analysis",
        help="Skip two-pass content analysis (faster, less semantic insight).",
    ),
    content_model: str = typer.Option(
        "o3-mini",
        "--content-model",
        help="Model for content analysis pass (default: o3-mini/GPT-5.2 Thinking).",
    ),
):
    """
    Generate a Slack Wrapped video from channel messages.

    Takes raw Slack messages and a config file, generates insights using AI,
    and produces video-data.json for Remotion rendering.
    
    By default, uses two-pass content analysis for deeper semantic insights.
    Use --skip-content-analysis for faster single-pass mode.
    """
    console.print(f"\n[bold]Slack Wrapped[/bold] - Video Generator\n")
    
    # Validate input files exist
    data_path = Path(data)
    config_path = Path(config)
    
    if not data_path.exists():
        console.print(f"[red]Error:[/red] Data file not found: {data}")
        raise typer.Exit(1)
    
    if not config_path.exists():
        console.print(f"[red]Error:[/red] Config file not found: {config}")
        raise typer.Exit(2)
    
    # Create output directory
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[green]✓[/green] Data file: {data_path}")
    console.print(f"[green]✓[/green] Config file: {config_path}")
    console.print(f"[green]✓[/green] Output directory: {output_path}")
    
    # Display mode info
    if skip_llm:
        console.print("[yellow]Mode:[/yellow] Basic stats only (--skip-llm)")
    elif skip_content_analysis:
        console.print(f"[cyan]Mode:[/cyan] Single-pass insights ({openai_model})")
    else:
        console.print(f"[cyan]Mode:[/cyan] Two-pass content analysis")
        console.print(f"  Pass 1: Content extraction ({content_model})")
        console.print(f"  Pass 2: Insight synthesis ({openai_model})")
    
    # Check for OpenAI API key
    if not skip_llm and not openai_key:
        console.print("\n[yellow]Warning:[/yellow] No OpenAI API key provided.")
        console.print("Set OPENAI_API_KEY environment variable or use --openai-key option.")
        console.print("Use --skip-llm to generate basic stats without AI insights.\n")
        raise typer.Exit(3)
    
    # Pipeline components implemented:
    # 1. Parse messages (Story 2.1) ✅
    # 2. Calculate statistics (Story 2.2) ✅
    # 3. Rank contributors (Story 2.3) ✅
    # 4. Analyze words (Story 2.4) ✅
    # 5. Generate LLM insights (Story 3.1, 3.2, 3.3) ✅
    # 6. Content analysis (Story 6.1-6.5) ✅
    # 7. Generate video data (Story 5.1) - pending integration
    
    console.print("\n[cyan]Backend pipeline ready[/cyan]")
    console.print("[green]✓[/green] Message parsing and analysis")
    console.print("[green]✓[/green] LLM insights generation")
    console.print("[green]✓[/green] Two-pass content analysis")
    console.print("[yellow]→[/yellow] Video data generation (Epic 5 pending)")


@app.command()
def validate(
    data: str = typer.Option(
        ...,
        "--data",
        "-d",
        help="Path to raw Slack messages text file.",
    ),
    config: str = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to config.json file with channel info and user mappings.",
    ),
):
    """
    Validate input data and config files without generating output.

    Checks that the message file can be parsed and the config is valid.
    """
    console.print(f"\n[bold]Slack Wrapped[/bold] - Validation\n")
    
    data_path = Path(data)
    config_path = Path(config)
    
    all_errors = []
    all_warnings = []
    
    # Validate data file
    if not data_path.exists():
        all_errors.append(f"Data file not found: {data}")
    else:
        console.print(f"[green]✓[/green] Data file exists: {data_path}")
        # TODO: Validate message format (Story 2.1)
    
    # Validate config file
    if not config_path.exists():
        all_errors.append(f"Config file not found: {config}")
    else:
        console.print(f"[green]✓[/green] Config file exists: {config_path}")
        
        # Validate config schema
        validator = ConfigValidator()
        is_valid, errors, warnings = validator.validate(config)
        
        if errors:
            all_errors.extend(errors)
        if warnings:
            all_warnings.extend(warnings)
        
        if is_valid:
            # Try to load the config to verify it works
            try:
                cfg = Config.load(config)
                console.print(f"[green]✓[/green] Config valid: channel '{cfg.channel.name}' ({cfg.channel.year})")
                console.print(f"[green]✓[/green] Teams defined: {len(cfg.teams)}")
                console.print(f"[green]✓[/green] User mappings: {len(cfg.user_mappings)}")
            except Exception as e:
                all_errors.append(f"Failed to load config: {e}")
    
    # Display warnings
    if all_warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in all_warnings:
            console.print(f"  ⚠ {warning}")
    
    # Display errors and exit
    if all_errors:
        console.print("\n[red]Validation failed:[/red]")
        for error in all_errors:
            console.print(f"  ✗ {error}")
        raise typer.Exit(1)
    
    console.print("\n[bold green]✓ Validation passed[/bold green]")


@app.command()
def preview(
    data: str = typer.Option(
        ...,
        "--data",
        "-d",
        help="Path to raw Slack messages text file.",
    ),
    config: str = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to config.json file with channel info and user mappings.",
    ),
):
    """
    Generate video data and open Remotion Studio for preview.

    Generates video-data.json and launches the Remotion preview server.
    """
    console.print(f"\n[bold]Slack Wrapped[/bold] - Preview Mode\n")
    
    # Validate inputs
    data_path = Path(data)
    config_path = Path(config)
    
    if not data_path.exists():
        console.print(f"[red]Error:[/red] Data file not found: {data}")
        raise typer.Exit(1)
    
    if not config_path.exists():
        console.print(f"[red]Error:[/red] Config file not found: {config}")
        raise typer.Exit(2)
    
    console.print(f"[green]✓[/green] Inputs validated")
    console.print("[cyan]Generating preview data...[/cyan]")
    
    # TODO: Generate video data and launch Remotion Studio
    console.print("\n[yellow]Preview mode implementation pending[/yellow]")
    console.print("Run 'cd wrapped-video && npm start' to open Remotion Studio")


if __name__ == "__main__":
    app()
