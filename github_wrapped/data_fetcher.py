"""Data fetcher for GitHub contributions."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import os
import sys
from pathlib import Path

from github.Issue import Issue
from github.PullRequest import PullRequest as GHPullRequest
from github.Repository import Repository
from rich.progress import Progress, TaskID
from rich.console import Console

from .github_client import GitHubClient

# Number of concurrent API requests for fetching PR details
MAX_WORKERS = 10


@dataclass
class PullRequestData:
    """Data class for pull request information."""

    number: int
    title: str
    body: str | None
    repo_name: str
    repo_full_name: str
    url: str
    state: str
    merged: bool
    created_at: datetime
    merged_at: datetime | None
    additions: int
    deletions: int
    changed_files: int
    labels: list[str]
    is_author: bool  # True if user authored, False if user reviewed


@dataclass
class ReviewData:
    """Data class for code review information."""

    pr_number: int
    pr_title: str
    repo_name: str
    repo_full_name: str
    pr_url: str
    submitted_at: datetime
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED
    author: str  # PR author (who you reviewed)


@dataclass
class CommitData:
    """Data class for commit information."""

    sha: str
    message: str
    repo_name: str
    repo_full_name: str
    url: str
    date: datetime
    additions: int
    deletions: int


@dataclass
class ContributionData:
    """Container for all fetched contribution data."""

    username: str
    year: int
    orgs: list[str]
    pull_requests: list[PullRequestData] = field(default_factory=list)
    reviews: list[ReviewData] = field(default_factory=list)
    commits: list[CommitData] = field(default_factory=list)

    @property
    def authored_prs(self) -> list[PullRequestData]:
        """Get PRs authored by the user."""
        return [pr for pr in self.pull_requests if pr.is_author]

    @property
    def merged_prs(self) -> list[PullRequestData]:
        """Get merged PRs authored by the user."""
        return [pr for pr in self.authored_prs if pr.merged]

    def to_dict(self) -> dict:
        """Convert ContributionData to a JSON-serializable dictionary."""
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        def serialize_dataclass(obj):
            result = {}
            for key, value in asdict(obj).items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, list):
                    result[key] = [serialize_datetime(item) for item in value]
                else:
                    result[key] = value
            return result

        return {
            "username": self.username,
            "year": self.year,
            "orgs": self.orgs,
            "pull_requests": [serialize_dataclass(pr) for pr in self.pull_requests],
            "reviews": [serialize_dataclass(r) for r in self.reviews],
            "commits": [serialize_dataclass(c) for c in self.commits],
        }

    def save(self, output_dir: str = "output") -> str:
        """
        Save contribution data to a JSON file.

        Args:
            output_dir: Directory to save the data file.

        Returns:
            The path to the saved file.
        """
        os.makedirs(output_dir, exist_ok=True)
        filename = f"github_data_{self.username}_{self.year}_{int(datetime.now().timestamp())}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        return filepath

    @classmethod
    def from_dict(cls, data: dict) -> "ContributionData":
        """Create ContributionData from a dictionary (e.g., loaded from JSON)."""
        def parse_datetime(dt_str: str | None) -> datetime | None:
            if dt_str is None:
                return None
            return datetime.fromisoformat(dt_str)

        pull_requests = [
            PullRequestData(
                number=pr["number"],
                title=pr["title"],
                body=pr["body"],
                repo_name=pr["repo_name"],
                repo_full_name=pr["repo_full_name"],
                url=pr["url"],
                state=pr["state"],
                merged=pr["merged"],
                created_at=parse_datetime(pr["created_at"]),
                merged_at=parse_datetime(pr["merged_at"]),
                additions=pr["additions"],
                deletions=pr["deletions"],
                changed_files=pr["changed_files"],
                labels=pr["labels"],
                is_author=pr["is_author"],
            )
            for pr in data["pull_requests"]
        ]

        reviews = [
            ReviewData(
                pr_number=r["pr_number"],
                pr_title=r["pr_title"],
                repo_name=r["repo_name"],
                repo_full_name=r["repo_full_name"],
                pr_url=r["pr_url"],
                submitted_at=parse_datetime(r["submitted_at"]),
                state=r["state"],
                author=r["author"],
            )
            for r in data["reviews"]
        ]

        commits = [
            CommitData(
                sha=c["sha"],
                message=c["message"],
                repo_name=c["repo_name"],
                repo_full_name=c["repo_full_name"],
                url=c["url"],
                date=parse_datetime(c["date"]),
                additions=c["additions"],
                deletions=c["deletions"],
            )
            for c in data["commits"]
        ]

        return cls(
            username=data["username"],
            year=data["year"],
            orgs=data["orgs"],
            pull_requests=pull_requests,
            reviews=reviews,
            commits=commits,
        )

    @classmethod
    def load(cls, filepath: str) -> "ContributionData":
        """
        Load contribution data from a JSON file.

        Args:
            filepath: Path to the JSON data file.

        Returns:
            ContributionData loaded from the file.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


class DataFetcher:
    """Fetches contribution data from GitHub.

    Uses GitHub's Search API for efficient filtering by author/reviewer,
    avoiding the need to fetch all PRs and filter locally.
    """

    def __init__(
        self,
        client: GitHubClient,
        year: int,
        orgs: list[str],
        repos: list[str] | None = None,
    ):
        """
        Initialize the data fetcher.

        Args:
            client: Authenticated GitHub client.
            year: The year to fetch data for.
            orgs: List of organization names to fetch from.
            repos: Optional list of specific repository names to fetch from.
                   If None, fetches from all repos in the organizations.
        """
        self.client = client
        self.year = year
        self.orgs = orgs
        self.repos = repos  # Keep as list for search queries
        self.start_date = datetime(year, 1, 1)
        self.end_date = datetime(year, 12, 31, 23, 59, 59)
        self.start_date_str = f"{year}-01-01"
        self.end_date_str = f"{year}-12-31"

    def _build_scope_query(self) -> str:
        """Build the scope portion of search queries (org/repo filters)."""
        if self.repos:
            # Specific repos: use repo:org/repo for each combination
            repo_queries = []
            for org in self.orgs:
                for repo in self.repos:
                    repo_queries.append(f"repo:{org}/{repo}")
            return " ".join(repo_queries)
        else:
            # All repos in orgs: use org:name for each
            return " ".join(f"org:{org}" for org in self.orgs)

    def fetch_all(
        self, progress: Progress | None = None, console: Console | None = None, fetch_commits: bool = False
    ) -> ContributionData:
        """
        Fetch all contribution data using GitHub Search API.

        This is much more efficient than iterating through all PRs in each repo,
        as the Search API filters by author/reviewer on the server side.

        Args:
            progress: Optional Rich progress bar.
            console: Optional Rich console for status updates.

        Returns:
            ContributionData containing all fetched data.
        """
        data = ContributionData(
            username=self.client.username,
            year=self.year,
            orgs=self.orgs,
        )

        username = self.client.username
        scope_query = self._build_scope_query()

        if console:
            if self.repos:
                console.print(f"  [dim]Searching in {len(self.repos)} repo(s) across {len(self.orgs)} org(s)[/dim]")
            else:
                console.print(f"  [dim]Searching across all repos in {len(self.orgs)} org(s)[/dim]")
            console.print("")

        # Create progress task if provided - we have 2 or 3 phases depending on fetch_commits
        task: TaskID | None = None
        if progress:
            total_phases = 3 if fetch_commits else 2
            task = progress.add_task("[cyan]Fetching contributions...", total=total_phases)

        # Phase 1: Fetch authored PRs using Search API
        if progress and task is not None:
            progress.update(task, description="[cyan]Searching for your PRs...")
        self._fetch_authored_prs_search(username, scope_query, data, console)
        if progress and task is not None:
            progress.update(task, advance=1)

        # Phase 2: Fetch reviews using Search API
        if progress and task is not None:
            progress.update(
                task,
                description=f"[cyan]Searching for your reviews... [dim]({len(data.pull_requests)} PRs found)[/dim]",
            )
        self._fetch_reviews_search(username, scope_query, data, console)
        if progress and task is not None:
            progress.update(task, advance=1)

        # Phase 3: Fetch commits (optional, disabled by default)
        if fetch_commits:
            if progress and task is not None:
                progress.update(
                    task,
                    description=f"[cyan]Fetching commits... [dim]({len(data.pull_requests)} PRs, {len(data.reviews)} reviews)[/dim]",
                )
            self._fetch_commits_search(username, scope_query, data, console)
            if progress and task is not None:
                progress.update(task, advance=1)

        if console:
            if fetch_commits:
                console.print(
                    f"  [dim]Found {len(data.pull_requests)} PRs, "
                    f"{len(data.reviews)} reviews, {len(data.commits)} commits[/dim]"
                )
            else:
                console.print(
                    f"  [dim]Found {len(data.pull_requests)} PRs, "
                    f"{len(data.reviews)} reviews[/dim]"
                )

        return data

    def _fetch_authored_prs_search(
        self, username: str, scope_query: str, data: ContributionData, console: Console | None = None
    ):
        """Fetch pull requests authored by the user using Search API."""
        # Search for merged PRs by this author in the date range
        # Using merged: for merged PRs gives us accurate date filtering
        query = (
            f"type:pr author:{username} is:merged "
            f"merged:{self.start_date_str}..{self.end_date_str} {scope_query}"
        )

        try:
            # Fetch merged PRs only
            if console:
                console.print(f"  [dim]Query: {query}[/dim]")
                console.print(f"  [dim]Searching for merged PRs...[/dim]")
            merged_issues = self.client.client.search_issues(query)
            total_count = merged_issues.totalCount
            if console:
                console.print(f"  [dim]Found {total_count} merged PRs, fetching details...[/dim]")
            
            # Collect issues first, then fetch PR details in parallel
            issues_list = list(merged_issues)
            pr_results = self._fetch_pr_details_parallel(issues_list, is_author=True, console=console)
            data.pull_requests.extend(pr_results)
            
            if console:
                console.print(f"  [dim]Processed {len(pr_results)} merged PRs                    [/dim]")

        except Exception as e:
            print(f"Warning: Could not search for authored PRs: {e}", file=sys.stderr)

    def _fetch_reviews_search(
        self, username: str, scope_query: str, data: ContributionData, console: Console | None = None
    ):
        """Fetch code reviews given by the user using Search API."""
        # Search for PRs reviewed by this user
        # Note: reviewed-by finds PRs where user submitted a review
        # We search for PRs updated in our date range, then filter reviews by date
        query = (
            f"type:pr reviewed-by:{username} -author:{username} "
            f"updated:{self.start_date_str}..{self.end_date_str} {scope_query}"
        )

        try:
            issues = self.client.client.search_issues(query)
            pr_count = 0
            for issue in issues:
                pr_count += 1
                if console:
                    console.print(f"  [dim]Processing review PR {pr_count}...[/dim]", end="\r")
                # Need to get the full PR to access reviews
                try:
                    pr = issue.as_pull_request()
                    repo_full_name = issue.repository.full_name
                    repo_name = issue.repository.name

                    # Get reviews and filter by user and date
                    reviews = pr.get_reviews()
                    for review in reviews:
                        if review.user and review.user.login == username:
                            if review.submitted_at and self._in_date_range(review.submitted_at):
                                review_data = ReviewData(
                                    pr_number=pr.number,
                                    pr_title=pr.title,
                                    repo_name=repo_name,
                                    repo_full_name=repo_full_name,
                                    pr_url=pr.html_url,
                                    submitted_at=review.submitted_at,
                                    state=review.state,
                                    author=pr.user.login if pr.user else "unknown",
                                )
                                data.reviews.append(review_data)
                except Exception:
                    # Skip if we can't get the PR details
                    continue
            if console and pr_count > 0:
                console.print(f"  [dim]Processed {pr_count} reviewed PRs                    [/dim]")

        except Exception as e:
            print(f"Warning: Could not search for reviews: {e}", file=sys.stderr)

    def _fetch_commits_search(
        self, username: str, scope_query: str, data: ContributionData, console: Console | None = None
    ):
        """Fetch commits made by the user using Search API."""
        # The commits search API has different syntax
        # committer-date for date range, author for the user
        query = (
            f"author:{username} "
            f"committer-date:{self.start_date_str}..{self.end_date_str} {scope_query}"
        )

        try:
            commits = self.client.client.search_commits(query)
            commit_count = 0
            for commit in commits:
                commit_count += 1
                if console and commit_count % 10 == 0:
                    console.print(f"  [dim]Processing commit {commit_count}...[/dim]", end="\r")
                try:
                    repo = commit.repository
                    commit_data = CommitData(
                        sha=commit.sha[:7],
                        message=commit.commit.message.split("\n")[0],  # First line only
                        repo_name=repo.name,
                        repo_full_name=repo.full_name,
                        url=commit.html_url,
                        date=commit.commit.author.date,
                        additions=commit.stats.additions if commit.stats else 0,
                        deletions=commit.stats.deletions if commit.stats else 0,
                    )
                    data.commits.append(commit_data)
                except Exception:
                    # Skip commits we can't process
                    continue
            if console and commit_count > 0:
                console.print(f"  [dim]Processed {commit_count} commits                    [/dim]")

        except Exception as e:
            print(f"Warning: Could not search for commits: {e}", file=sys.stderr)

    def _fetch_pr_details_parallel(
        self, issues: list[Issue], is_author: bool, console: Console | None = None
    ) -> list[PullRequestData]:
        """Fetch PR details for multiple issues in parallel.
        
        This is much faster than fetching sequentially since we can make
        multiple API calls concurrently.
        """
        results: list[PullRequestData] = []
        total = len(issues)
        
        if total == 0:
            return results
        
        completed = 0
        
        def fetch_one(issue: Issue) -> PullRequestData | None:
            return self._create_pr_data_from_issue(issue, is_author=is_author, fetch_details=True)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_one, issue): issue for issue in issues}
            
            for future in as_completed(futures):
                completed += 1
                if console:
                    console.print(f"  [dim]Fetching PR details: {completed}/{total}...[/dim]", end="\r")
                try:
                    pr_data = future.result()
                    if pr_data:
                        results.append(pr_data)
                except Exception:
                    # Skip PRs that fail to fetch
                    pass
        
        return results

    def _in_date_range(self, dt: datetime) -> bool:
        """Check if a datetime is within the target year."""
        # Handle timezone-aware datetimes
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return self.start_date <= dt <= self.end_date

    def _create_pr_data_from_issue(
        self, issue: Issue, is_author: bool, fetch_details: bool = False
    ) -> PullRequestData | None:
        """Create a PullRequestData object from a GitHub Issue (search result).

        Search API returns Issues, which need to be converted to PRs for full data.
        If fetch_details is False, we use issue data directly (faster, no extra API call)
        but won't have additions/deletions/changed_files stats.
        """
        try:
            repo = issue.repository
            
            if fetch_details:
                # Convert issue to PR to get PR-specific fields (slow - extra API call)
                pr = issue.as_pull_request()
                return PullRequestData(
                    number=pr.number,
                    title=pr.title,
                    body=pr.body,
                    repo_name=repo.name,
                    repo_full_name=repo.full_name,
                    url=pr.html_url,
                    state=pr.state,
                    merged=pr.merged,
                    created_at=pr.created_at,
                    merged_at=pr.merged_at,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    changed_files=pr.changed_files,
                    labels=[label.name for label in pr.labels],
                    is_author=is_author,
                )
            else:
                # Use issue data directly (fast - no extra API call)
                # We infer merged status from the search query context
                # Note: additions/deletions/changed_files not available from issue
                return PullRequestData(
                    number=issue.number,
                    title=issue.title,
                    body=issue.body,
                    repo_name=repo.name,
                    repo_full_name=repo.full_name,
                    url=issue.html_url,
                    state=issue.state,
                    merged=issue.state == "closed" and issue.pull_request is not None,
                    created_at=issue.created_at,
                    merged_at=issue.closed_at,  # Best approximation from issue data
                    additions=0,  # Not available without fetching PR details
                    deletions=0,
                    changed_files=0,
                    labels=[label.name for label in issue.labels],
                    is_author=is_author,
                )
        except Exception:
            # If we can't process the issue, skip it
            return None

    def _create_pr_data(
        self, pr: GHPullRequest, repo: Repository, is_author: bool
    ) -> PullRequestData:
        """Create a PullRequestData object from a GitHub PR."""
        return PullRequestData(
            number=pr.number,
            title=pr.title,
            body=pr.body,
            repo_name=repo.name,
            repo_full_name=repo.full_name,
            url=pr.html_url,
            state=pr.state,
            merged=pr.merged,
            created_at=pr.created_at,
            merged_at=pr.merged_at,
            additions=pr.additions,
            deletions=pr.deletions,
            changed_files=pr.changed_files,
            labels=[label.name for label in pr.labels],
            is_author=is_author,
        )
