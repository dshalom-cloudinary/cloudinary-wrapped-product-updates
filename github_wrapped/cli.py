"""CLI entry point for GitHub Wrapped."""

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .github_client import GitHubClient
from .data_fetcher import DataFetcher
from .categorizer import Categorizer
from .report_generator import ReportGenerator

app = typer.Typer(
    name="github-wrapped",
    help="Generate a performance review report from your GitHub contributions.",
)
console = Console()


@app.command()
def main(
    orgs: str = typer.Option(
        ...,
        "--orgs",
        "-o",
        help="Comma-separated list of GitHub organizations to fetch from.",
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
):
    """
    Generate a GitHub Wrapped performance review report.

    Fetches your contributions from specified organizations for a given year
    and generates a markdown report aligned to the Execution/Culture review framework.
    """
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

            # Fetch data with progress
            console.print("[cyan]Fetching contribution data...[/cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                fetcher = DataFetcher(client, year, org_list, repos=repo_list)
                data = fetcher.fetch_all(progress, console=console)

            console.print("")
            console.print(f"[green]✓[/green] Found {len(data.merged_prs)} merged PRs")
            console.print(f"[green]✓[/green] Found {len(data.reviews)} code reviews")
            console.print(f"[green]✓[/green] Found {len(data.commits)} commits")

            if not data.merged_prs:
                console.print("\n[yellow]Warning:[/yellow] No merged PRs found for the specified criteria.")
                console.print("This could mean:")
                console.print("  - No PRs merged in the specified year")
                console.print("  - Token doesn't have access to the organizations")
                console.print("  - Organization names are incorrect")
                raise typer.Exit(0)

            # Categorize
            console.print("\n[cyan]Analyzing contributions...[/cyan]")
            categorizer = Categorizer()
            categorized = categorizer.categorize(data)

            console.print(f"[green]✓[/green] Identified {len(categorized.big_rocks)} big rocks")

            # Generate report
            console.print("\n[cyan]Generating report...[/cyan]")
            generator = ReportGenerator(categorized)
            filepath = generator.save(output_dir)

            console.print(f"\n[bold green]✓ Report saved to:[/bold green] {filepath}")
            console.print("\nUse this report to help fill out your performance review!")

    except typer.Exit:
        raise  # Re-raise typer.Exit to allow clean exits
    except ValueError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
