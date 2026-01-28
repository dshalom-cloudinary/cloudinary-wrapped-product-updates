"""Data fetcher for GitHub contributions."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import os
import sys

from rich.progress import Progress, TaskID
from rich.console import Console

from .github_client import GitHubClient

# Branches to exclude from PR fetching (e.g., auto-merge PRs to production)
EXCLUDED_BASE_BRANCHES = {"production"}

# GraphQL query for fetching authored PRs with all required fields in one request
# Using first: 50 to avoid timeout issues with large responses
AUTHORED_PRS_GRAPHQL = """
query($searchQuery: String!, $cursor: String) {
  search(query: $searchQuery, type: ISSUE, first: 50, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        body
        url
        state
        merged
        createdAt
        mergedAt
        additions
        deletions
        changedFiles
        baseRefName
        labels(first: 10) {
          nodes {
            name
          }
        }
        repository {
          name
          nameWithOwner
        }
      }
    }
  }
}
"""

# GraphQL query for fetching reviews - gets PRs reviewed by user with review details
# Using first: 30 to avoid timeout issues
REVIEWS_GRAPHQL = """
query($searchQuery: String!, $username: String!, $cursor: String) {
  search(query: $searchQuery, type: ISSUE, first: 30, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        url
        author {
          login
        }
        repository {
          name
          nameWithOwner
        }
        reviews(first: 10, author: $username) {
          nodes {
            submittedAt
            state
          }
        }
      }
    }
  }
}
"""

# GraphQL query for fetching top repositories a user contributed to
# Returns repos with merged PR counts for ranking
TOP_REPOS_GRAPHQL = """
query($searchQuery: String!, $cursor: String) {
  search(query: $searchQuery, type: ISSUE, first: 100, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        repository {
          name
          nameWithOwner
          owner {
            login
          }
        }
      }
    }
  }
}
"""


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

    # Number of top repos to fetch when no specific repos are provided
    DEFAULT_TOP_REPOS_COUNT = 5

    def __init__(
        self,
        client: GitHubClient,
        year: int,
        orgs: list[str],
        repos: list[str] | None = None,
        target_username: str | None = None,
    ):
        """
        Initialize the data fetcher.

        Args:
            client: Authenticated GitHub client.
            year: The year to fetch data for.
            orgs: List of organization names to fetch from.
            repos: Optional list of specific repository names to fetch from.
                   If None, automatically discovers the top 5 repos the user
                   contributed to in the specified organizations.
            target_username: GitHub username to fetch data for. If None, uses
                   the authenticated user's username.
        """
        self.client = client
        self.year = year
        self.orgs = orgs
        self.repos = repos  # Keep as list for search queries
        self._discovered_repos: list[str] | None = None  # Cache for auto-discovered repos
        self.target_username = target_username or client.username
        self.start_date = datetime(year, 1, 1)
        self.end_date = datetime(year, 12, 31, 23, 59, 59)
        self.start_date_str = f"{year}-01-01"
        self.end_date_str = f"{year}-12-31"

    def _build_scope_query(self) -> str:
        """Build the scope portion of search queries (org/repo filters)."""
        # Use discovered repos if available, otherwise use provided repos
        repos_to_use = self._discovered_repos or self.repos
        
        if repos_to_use:
            # Specific repos: use repo:org/repo for each combination
            repo_queries = []
            for org in self.orgs:
                for repo in repos_to_use:
                    repo_queries.append(f"repo:{org}/{repo}")
            return " ".join(repo_queries)
        else:
            # All repos in orgs: use org:name for each
            return " ".join(f"org:{org}" for org in self.orgs)

    def _discover_top_repos(
        self, username: str, console: Console | None = None
    ) -> list[str]:
        """
        Discover the top repositories the user contributed to using GraphQL.
        
        Fetches merged PRs authored by the user in the specified orgs and year,
        then ranks repositories by contribution count.
        
        Args:
            username: GitHub username to find contributions for.
            console: Optional Rich console for status updates.
            
        Returns:
            List of repository names (without org prefix) sorted by contribution count.
        """
        from collections import Counter
        
        if console:
            console.print(f"  [dim]Discovering top repositories for {username}...[/dim]")
        
        # Build org scope for the search
        org_scope = " ".join(f"org:{org}" for org in self.orgs)
        
        # Search for all merged PRs by this user in the orgs for the year
        search_query = (
            f"type:pr author:{username} is:merged "
            f"merged:{self.start_date_str}..{self.end_date_str} {org_scope}"
        )
        
        repo_contributions: Counter = Counter()
        cursor = None
        total_prs = 0
        
        while True:
            result = self.client.execute_graphql(
                TOP_REPOS_GRAPHQL,
                variables={"searchQuery": search_query, "cursor": cursor}
            )
            
            search_data = result.get("search", {})
            nodes = search_data.get("nodes", [])
            page_info = search_data.get("pageInfo", {})
            
            for node in nodes:
                if not node:
                    continue
                
                repo = node.get("repository", {})
                repo_name = repo.get("name", "")
                owner = repo.get("owner", {}).get("login", "")
                
                # Only count repos from our target orgs
                if owner in self.orgs and repo_name:
                    repo_contributions[repo_name] += 1
                    total_prs += 1
            
            if console:
                console.print(f"  [dim]Processed {total_prs} PRs...[/dim]", end="\r")
            
            # Check for more pages
            if page_info.get("hasNextPage"):
                cursor = page_info.get("endCursor")
            else:
                break
        
        # Get top N repos by contribution count
        top_repos = [repo for repo, _ in repo_contributions.most_common(self.DEFAULT_TOP_REPOS_COUNT)]
        
        if console:
            if top_repos:
                console.print(f"  [dim]Found top {len(top_repos)} repos from {total_prs} PRs: {', '.join(top_repos)}[/dim]")
            else:
                console.print(f"  [dim]No contributions found in specified organizations[/dim]")
        
        return top_repos

    def fetch_all(
        self, progress: Progress | None = None, console: Console | None = None, fetch_commits: bool = False
    ) -> ContributionData:
        """
        Fetch all contribution data using GitHub GraphQL API.

        Args:
            progress: Optional Rich progress bar.
            console: Optional Rich console for status updates.
            fetch_commits: Whether to fetch commit data (slower, disabled by default).

        Returns:
            ContributionData containing all fetched data.
        """
        data = ContributionData(
            username=self.target_username,
            year=self.year,
            orgs=self.orgs,
        )

        username = self.target_username

        # If no specific repos provided, discover top repos the user contributed to
        if not self.repos:
            if console:
                console.print(f"  [dim]No specific repos provided, discovering top {self.DEFAULT_TOP_REPOS_COUNT} repos...[/dim]")
            self._discovered_repos = self._discover_top_repos(username, console)
            if not self._discovered_repos:
                if console:
                    console.print(f"  [yellow]Warning:[/yellow] No contributions found in the specified organizations for {self.year}")
                return data

        if console:
            repos_to_show = self._discovered_repos or self.repos
            if repos_to_show:
                console.print(f"  [dim]Searching in {len(repos_to_show)} repo(s) across {len(self.orgs)} org(s)[/dim]")
            else:
                console.print(f"  [dim]Searching across all repos in {len(self.orgs)} org(s)[/dim]")
            console.print(f"  [dim]Using GraphQL API for efficient fetching[/dim]")
            console.print("")

        # Create progress task if provided - we have 2 or 3 phases depending on fetch_commits
        task: TaskID | None = None
        if progress:
            total_phases = 3 if fetch_commits else 2
            task = progress.add_task("[cyan]Fetching contributions...", total=total_phases)

        # Phase 1: Fetch authored PRs
        if progress and task is not None:
            progress.update(task, description="[cyan]Searching for your PRs...")
        
        self._fetch_authored_prs_graphql(username, data, console)
        
        if progress and task is not None:
            progress.update(task, advance=1)

        # Phase 2: Fetch reviews
        if progress and task is not None:
            progress.update(
                task,
                description=f"[cyan]Searching for your reviews... [dim]({len(data.pull_requests)} PRs found)[/dim]",
            )
        
        self._fetch_reviews_graphql(username, data, console)
        
        if progress and task is not None:
            progress.update(task, advance=1)

        # Phase 3: Fetch commits (optional, disabled by default)
        # Note: Commits use REST as GraphQL commit search is limited
        if fetch_commits:
            if progress and task is not None:
                progress.update(
                    task,
                    description=f"[cyan]Fetching commits... [dim]({len(data.pull_requests)} PRs, {len(data.reviews)} reviews)[/dim]",
                )
            self._fetch_commits_search(username, self._build_scope_query(), data, console)
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

    # =========================================================================
    # GraphQL-based fetch methods (much more efficient than REST)
    # =========================================================================

    def _get_graphql_scopes(self) -> list[str]:
        """
        Get list of scope queries for GraphQL.
        
        When specific repos are requested (or discovered), returns one scope per repo to query separately.
        When fetching all repos in orgs, returns one scope per org.
        """
        # Use discovered repos if available, otherwise use provided repos
        repos_to_use = self._discovered_repos or self.repos
        
        if repos_to_use:
            # Query each repo separately to avoid query length issues
            scopes = []
            for org in self.orgs:
                for repo in repos_to_use:
                    scopes.append(f"repo:{org}/{repo}")
            return scopes
        else:
            # Query each org
            return [f"org:{org}" for org in self.orgs]

    def _fetch_authored_prs_graphql(
        self, username: str, data: ContributionData, console: Console | None = None
    ) -> None:
        """
        Fetch pull requests authored by the user using GraphQL API.
        
        This is much more efficient than REST as it fetches all PR data
        (including additions, deletions, changedFiles) in a single request per page.
        
        When specific repos are requested, queries each repo separately to avoid
        query length issues with GitHub's GraphQL API.
        """
        scopes = self._get_graphql_scopes()
        
        if console:
            console.print(f"  [dim]Fetching merged PRs via GraphQL ({len(scopes)} scope(s))...[/dim]")
        
        total_fetched = 0
        
        for scope_idx, scope in enumerate(scopes):
            # Build the search query for this scope
            search_query = (
                f"type:pr author:{username} is:merged "
                f"merged:{self.start_date_str}..{self.end_date_str} {scope}"
            )
            
            cursor = None
            
            while True:
                result = self.client.execute_graphql(
                    AUTHORED_PRS_GRAPHQL,
                    variables={"searchQuery": search_query, "cursor": cursor}
                )
                
                search_data = result.get("search", {})
                nodes = search_data.get("nodes", [])
                page_info = search_data.get("pageInfo", {})
                
                for node in nodes:
                    if not node:  # Skip null nodes
                        continue
                    
                    # Skip PRs targeting excluded branches (e.g., production)
                    base_ref = node.get("baseRefName", "")
                    if base_ref in EXCLUDED_BASE_BRANCHES:
                        continue
                    
                    pr_data = self._parse_graphql_pr(node, is_author=True)
                    if pr_data:
                        data.pull_requests.append(pr_data)
                        total_fetched += 1
                
                if console:
                    console.print(f"  [dim]Fetched {total_fetched} PRs (scope {scope_idx + 1}/{len(scopes)})...[/dim]", end="\r")
                
                # Check for more pages
                if page_info.get("hasNextPage"):
                    cursor = page_info.get("endCursor")
                else:
                    break
        
        if console:
            console.print(f"  [dim]Processed {total_fetched} merged PRs via GraphQL          [/dim]")

    def _fetch_reviews_graphql(
        self, username: str, data: ContributionData, console: Console | None = None
    ) -> None:
        """
        Fetch code reviews given by the user using GraphQL API.
        
        This fetches PRs reviewed by the user along with their review details
        in a single request per page, avoiding the N+1 problem of REST.
        
        When specific repos are requested, queries each repo separately to avoid
        query length issues with GitHub's GraphQL API.
        """
        scopes = self._get_graphql_scopes()
        
        if console:
            console.print(f"  [dim]Fetching reviews via GraphQL ({len(scopes)} scope(s))...[/dim]")
        
        total_reviews = 0
        prs_processed = 0
        
        for scope_idx, scope in enumerate(scopes):
            # Build the search query for this scope
            search_query = (
                f"type:pr reviewed-by:{username} -author:{username} "
                f"updated:{self.start_date_str}..{self.end_date_str} {scope}"
            )
            
            cursor = None
            
            while True:
                result = self.client.execute_graphql(
                    REVIEWS_GRAPHQL,
                    variables={
                        "searchQuery": search_query,
                        "username": username,
                        "cursor": cursor,
                    }
                )
                
                search_data = result.get("search", {})
                nodes = search_data.get("nodes", [])
                page_info = search_data.get("pageInfo", {})
                
                for node in nodes:
                    if not node:  # Skip null nodes
                        continue
                    
                    prs_processed += 1
                    reviews = self._parse_graphql_reviews(node, username)
                    for review_data in reviews:
                        # Filter by date range
                        if self._in_date_range(review_data.submitted_at):
                            data.reviews.append(review_data)
                            total_reviews += 1
                
                if console:
                    console.print(f"  [dim]Processed {prs_processed} PRs, found {total_reviews} reviews (scope {scope_idx + 1}/{len(scopes)})...[/dim]", end="\r")
                
                # Check for more pages
                if page_info.get("hasNextPage"):
                    cursor = page_info.get("endCursor")
                else:
                    break
        
        if console:
            console.print(f"  [dim]Processed {prs_processed} reviewed PRs, found {total_reviews} reviews via GraphQL          [/dim]")

    def _parse_graphql_pr(self, node: dict, is_author: bool) -> PullRequestData | None:
        """Parse a GraphQL PR node into PullRequestData."""
        try:
            repo = node.get("repository", {})
            labels_data = node.get("labels", {}).get("nodes", [])
            
            # Parse dates
            created_at = self._parse_iso_datetime(node.get("createdAt"))
            merged_at = self._parse_iso_datetime(node.get("mergedAt"))
            
            return PullRequestData(
                number=node.get("number", 0),
                title=node.get("title", ""),
                body=node.get("body"),
                repo_name=repo.get("name", ""),
                repo_full_name=repo.get("nameWithOwner", ""),
                url=node.get("url", ""),
                state=node.get("state", "").lower(),
                merged=node.get("merged", False),
                created_at=created_at,
                merged_at=merged_at,
                additions=node.get("additions", 0),
                deletions=node.get("deletions", 0),
                changed_files=node.get("changedFiles", 0),
                labels=[label.get("name", "") for label in labels_data if label],
                is_author=is_author,
            )
        except Exception:
            return None

    def _parse_graphql_reviews(self, node: dict, username: str) -> list[ReviewData]:
        """Parse GraphQL PR node with reviews into list of ReviewData."""
        results = []
        try:
            repo = node.get("repository", {})
            author_data = node.get("author", {})
            reviews_data = node.get("reviews", {}).get("nodes", [])
            
            pr_number = node.get("number", 0)
            pr_title = node.get("title", "")
            repo_name = repo.get("name", "")
            repo_full_name = repo.get("nameWithOwner", "")
            pr_url = node.get("url", "")
            pr_author = author_data.get("login", "unknown") if author_data else "unknown"
            
            for review in reviews_data:
                if not review:
                    continue
                
                submitted_at = self._parse_iso_datetime(review.get("submittedAt"))
                if not submitted_at:
                    continue
                
                results.append(ReviewData(
                    pr_number=pr_number,
                    pr_title=pr_title,
                    repo_name=repo_name,
                    repo_full_name=repo_full_name,
                    pr_url=pr_url,
                    submitted_at=submitted_at,
                    state=review.get("state", ""),
                    author=pr_author,
                ))
        except Exception:
            pass
        
        return results

    def _parse_iso_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse an ISO datetime string from GraphQL."""
        if not dt_str:
            return None
        try:
            # Handle ISO format with Z suffix
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(dt_str)
            # Remove timezone info to match existing behavior
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        except Exception:
            return None

    def _in_date_range(self, dt: datetime) -> bool:
        """Check if a datetime is within the target year."""
        # Handle timezone-aware datetimes
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return self.start_date <= dt <= self.end_date

