"""CLI entry point for GitHub Wrapped."""

import os
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Load environment variables from .env file
load_dotenv()

from .github_client import GitHubClient
from .data_fetcher import DataFetcher, ContributionData
from .categorizer import Categorizer
from .report_generator import ReportGenerator
from .llm_report_generator import LLMReportGenerator

app = typer.Typer(
    name="github-wrapped",
    help="Generate a performance review report from your GitHub contributions.",
)
console = Console()


@app.command()
def main(
    orgs: str = typer.Option(
        None,
        "--orgs",
        "-o",
        help="Comma-separated list of GitHub organizations to fetch from. Required unless using --from-file.",
    ),
    repos: str = typer.Option(
        None,
        "--repos",
        "-r",
        help="Comma-separated list of specific repository names to fetch from. If not specified, fetches from all repos in the organizations.",
    ),
    year: int = typer.Option(
        2025,
        "--year",
        "-y",
        help="The year to generate the report for.",
    ),
    output_dir: str = typer.Option(
        "output",
        "--output",
        "-O",
        help="Directory to save the report.",
    ),
    token: str = typer.Option(
        None,
        "--token",
        "-t",
        envvar="GITHUB_TOKEN",
        help="GitHub Personal Access Token. If not provided, will use OAuth Device Flow for one-time authentication.",
    ),
    use_ai: bool = typer.Option(
        True,
        "--ai/--no-ai",
        help="Use AI (OpenAI) to generate a narrative performance review. Requires OPENAI_API_KEY.",
    ),
    openai_key: str = typer.Option(
        None,
        "--openai-key",
        envvar="OPENAI_API_KEY",
        help="OpenAI API key for AI-powered report generation.",
    ),
    openai_model: str = typer.Option(
        "gpt-5.2",
        "--model",
        "-m",
        help="OpenAI model to use for report generation.",
    ),
    fetch_commits: bool = typer.Option(
        False,
        "--commits/--no-commits",
        help="Fetch individual commits. Disabled by default since PR data already includes line counts.",
    ),
    from_file: str = typer.Option(
        None,
        "--from-file",
        "-f",
        help="Load contribution data from a previously saved JSON file instead of fetching from GitHub.",
    ),
    save_data: bool = typer.Option(
        True,
        "--save-data/--no-save-data",
        help="Save fetched data to a JSON file for later reuse.",
    ),
    github_username: str = typer.Option(
        None,
        "--github-username",
        "-u",
        help="GitHub username to display in the video (defaults to authenticated user).",
    ),
):
    """
    Generate a GitHub Wrapped performance review report.

    Fetches your contributions from specified organizations for a given year
    and generates a markdown report aligned to the Execution/Culture review framework.
    You can also load previously saved data using --from-file to skip fetching.
    """
    # If loading from file, skip fetching entirely
    if from_file:
        console.print(f"\n[bold]GitHub Wrapped[/bold] - Loading from file\n")
        try:
            console.print(f"[cyan]Loading data from:[/cyan] {from_file}")
            data = ContributionData.load(from_file)
            
            # Override username if provided
            if github_username:
                data.username = github_username
                console.print(f"[green]✓[/green] Using username: [bold]{github_username}[/bold]")
            else:
                console.print(f"[green]✓[/green] Loaded data for [bold]{data.username}[/bold] ({data.year})")
            
            console.print(f"[green]✓[/green] Organizations: {', '.join(data.orgs)}")
            console.print(f"[green]✓[/green] Found {len(data.merged_prs)} merged PRs")
            console.print(f"[green]✓[/green] Found {len(data.reviews)} code reviews")
            if data.commits:
                console.print(f"[green]✓[/green] Found {len(data.commits)} commits")
        except FileNotFoundError:
            console.print(f"[red]Error:[/red] File not found: {from_file}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to load data file: {e}")
            raise typer.Exit(1)
    else:
        # Fetch from GitHub - orgs is required
        if not orgs:
            console.print("[red]Error:[/red] --orgs is required when not using --from-file.")
            raise typer.Exit(1)

        org_list = [o.strip() for o in orgs.split(",") if o.strip()]
        repo_list = [r.strip() for r in repos.split(",") if r.strip()] if repos else None

        if not org_list:
            console.print("[red]Error:[/red] At least one organization is required.")
            raise typer.Exit(1)

        console.print(f"\n[bold]GitHub Wrapped[/bold] - {year} Performance Review\n")
        console.print(f"Organizations: {', '.join(org_list)}")
        if repo_list:
            console.print(f"Repositories: {', '.join(repo_list)}")
        else:
            console.print("Repositories: all")
        console.print("")

        try:
            with GitHubClient(token=token, console=console) as client:
                # Verify connection
                console.print(f"[green]✓[/green] Authenticated as [bold]{client.username}[/bold]")
                
                # Determine target username (use provided or authenticated user)
                target_user = github_username or client.username
                if github_username and github_username != client.username:
                    console.print(f"[cyan]→[/cyan] Fetching data for [bold]{github_username}[/bold]")

                # Fetch data with progress
                console.print("[cyan]Fetching contribution data...[/cyan]")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    fetcher = DataFetcher(client, year, org_list, repos=repo_list, target_username=target_user)
                    data = fetcher.fetch_all(progress, console=console, fetch_commits=fetch_commits)

                console.print("")
                console.print(f"[green]✓[/green] Found {len(data.merged_prs)} merged PRs")
                console.print(f"[green]✓[/green] Found {len(data.reviews)} code reviews")
                if fetch_commits:
                    console.print(f"[green]✓[/green] Found {len(data.commits)} commits")

                # Save data to file if requested
                if save_data:
                    data_filepath = data.save(output_dir)
                    console.print(f"[green]✓[/green] Data saved to: {data_filepath}")

                if not data.merged_prs:
                    console.print("\n[yellow]Warning:[/yellow] No merged PRs found for the specified criteria.")
                    console.print("This could mean:")
                    console.print("  - No PRs merged in the specified year")
                    console.print("  - Token doesn't have access to the organizations")
                    console.print("  - Organization names are incorrect")
                    raise typer.Exit(0)
        except typer.Exit:
            raise  # Re-raise typer.Exit to allow clean exits
        except ValueError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[red]Unexpected error:[/red] {e}")
            raise typer.Exit(1)

    # Check for empty data (applies to both loaded and fetched data)
    if not data.merged_prs:
        console.print("\n[yellow]Warning:[/yellow] No merged PRs found in the data.")
        raise typer.Exit(0)

    # Generate report
    if use_ai:
        # Check for OpenAI API key
        if not openai_key:
            console.print("\n[yellow]Warning:[/yellow] No OpenAI API key provided.")
            console.print("Set OPENAI_API_KEY environment variable or use --openai-key option.")
            console.print("Falling back to template-based report...\n")
            use_ai = False
        else:
            console.print(f"\n[cyan]Generating AI-powered report using {openai_model}...[/cyan]")
            console.print("[dim]The AI will analyze and categorize your contributions.[/dim]")
            try:
                llm_generator = LLMReportGenerator(
                    data,
                    api_key=openai_key,
                    model=openai_model,
                )
                filepath = llm_generator.save(output_dir)
                console.print(f"\n[bold green]✓ AI-powered report saved to:[/bold green] {filepath}")
                
                # Generate video data JSON
                console.print("\n[cyan]Generating video data...[/cyan]")
                video_filepath = llm_generator.save_video_data(output_dir)
                console.print(f"[bold green]✓ Video data saved to:[/bold green] {video_filepath}")
                
                console.print("\n[dim]Review and customize the report to add context from your work.[/dim]")
            except Exception as e:
                console.print(f"\n[red]Error:[/red] AI report generation failed: {e}")
                raise typer.Exit(1)

    if not use_ai:
        # Use template-based report with rule-based categorization
        console.print("\n[cyan]Analyzing contributions...[/cyan]")
        categorizer = Categorizer()
        categorized = categorizer.categorize(data)
        console.print(f"[green]✓[/green] Identified {len(categorized.big_rocks)} big rocks")
        
        console.print("\n[cyan]Generating template-based report...[/cyan]")
        generator = ReportGenerator(categorized)
        filepath = generator.save(output_dir)
        console.print(f"\n[bold green]✓ Report saved to:[/bold green] {filepath}")

    console.print("\nUse this report to help fill out your performance review!")


if __name__ == "__main__":
    app()
