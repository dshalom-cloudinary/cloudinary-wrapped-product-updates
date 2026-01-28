"""Data fetcher for GitHub contributions."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator

from github.PullRequest import PullRequest as GHPullRequest
from github.Repository import Repository
from rich.progress import Progress, TaskID

from .github_client import GitHubClient


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


class DataFetcher:
    """Fetches contribution data from GitHub."""

    def __init__(self, client: GitHubClient, year: int, orgs: list[str]):
        """
        Initialize the data fetcher.

        Args:
            client: Authenticated GitHub client.
            year: The year to fetch data for.
            orgs: List of organization names to fetch from.
        """
        self.client = client
        self.year = year
        self.orgs = orgs
        self.start_date = datetime(year, 1, 1)
        self.end_date = datetime(year, 12, 31, 23, 59, 59)

    def fetch_all(self, progress: Progress | None = None) -> ContributionData:
        """
        Fetch all contribution data.

        Args:
            progress: Optional Rich progress bar.

        Returns:
            ContributionData containing all fetched data.
        """
        data = ContributionData(
            username=self.client.username,
            year=self.year,
            orgs=self.orgs,
        )

        # Collect all repos from all orgs
        all_repos: list[Repository] = []
        for org_name in self.orgs:
            repos = self.client.get_org_repos(org_name)
            all_repos.extend(repos)

        if not all_repos:
            return data

        # Create progress task if provided
        task: TaskID | None = None
        if progress:
            task = progress.add_task(
                f"[cyan]Fetching data from {len(all_repos)} repos...",
                total=len(all_repos),
            )

        for repo in all_repos:
            self._fetch_repo_data(repo, data)
            if progress and task is not None:
                progress.update(task, advance=1)

        return data

    def _fetch_repo_data(self, repo: Repository, data: ContributionData):
        """Fetch all contribution data from a single repository."""
        username = self.client.username

        # Fetch PRs authored by user
        self._fetch_authored_prs(repo, username, data)

        # Fetch PRs reviewed by user
        self._fetch_reviews(repo, username, data)

        # Fetch commits by user
        self._fetch_commits(repo, username, data)

    def _fetch_authored_prs(
        self, repo: Repository, username: str, data: ContributionData
    ):
        """Fetch pull requests authored by the user."""
        try:
            # Get all closed PRs (which includes merged)
            prs = repo.get_pulls(state="closed", sort="updated", direction="desc")

            for pr in self._filter_prs_by_date(prs):
                if pr.user and pr.user.login == username:
                    pr_data = self._create_pr_data(pr, repo, is_author=True)
                    data.pull_requests.append(pr_data)
        except Exception:
            # Skip repos we can't access
            pass

    def _fetch_reviews(self, repo: Repository, username: str, data: ContributionData):
        """Fetch code reviews given by the user."""
        try:
            # Get closed PRs to find reviews
            prs = repo.get_pulls(state="closed", sort="updated", direction="desc")

            for pr in self._filter_prs_by_date(prs):
                # Skip own PRs
                if pr.user and pr.user.login == username:
                    continue

                reviews = pr.get_reviews()
                for review in reviews:
                    if review.user and review.user.login == username:
                        if review.submitted_at and self._in_date_range(review.submitted_at):
                            review_data = ReviewData(
                                pr_number=pr.number,
                                pr_title=pr.title,
                                repo_name=repo.name,
                                repo_full_name=repo.full_name,
                                pr_url=pr.html_url,
                                submitted_at=review.submitted_at,
                                state=review.state,
                                author=pr.user.login if pr.user else "unknown",
                            )
                            data.reviews.append(review_data)
        except Exception:
            # Skip repos we can't access
            pass

    def _fetch_commits(self, repo: Repository, username: str, data: ContributionData):
        """Fetch commits made by the user."""
        try:
            commits = repo.get_commits(
                author=username,
                since=self.start_date,
                until=self.end_date,
            )

            for commit in commits:
                if commit.commit.author and commit.commit.author.date:
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
            # Skip repos we can't access
            pass

    def _filter_prs_by_date(
        self, prs: Iterator[GHPullRequest]
    ) -> Iterator[GHPullRequest]:
        """Filter PRs to only those within the target year."""
        for pr in prs:
            # Use merged_at for merged PRs, created_at otherwise
            check_date = pr.merged_at if pr.merged_at else pr.created_at
            if check_date and self._in_date_range(check_date):
                yield pr
            # Stop if we've gone past our date range (PRs are sorted by updated desc)
            elif check_date and check_date < self.start_date:
                # Could be updated recently but created before - continue checking
                continue

    def _in_date_range(self, dt: datetime) -> bool:
        """Check if a datetime is within the target year."""
        # Handle timezone-aware datetimes
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return self.start_date <= dt <= self.end_date

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
