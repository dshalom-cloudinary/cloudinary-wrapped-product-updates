"""Categorizer for classifying PRs and identifying big rocks."""

import re
from dataclasses import dataclass
from enum import Enum

from .data_fetcher import PullRequestData, ContributionData


class PRCategory(Enum):
    """Categories for pull requests."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    TEST = "test"
    OTHER = "other"


@dataclass
class CategorizedPR:
    """A pull request with its category and big rock status."""

    pr: PullRequestData
    category: PRCategory
    is_big_rock: bool
    big_rock_reason: str | None = None


@dataclass
class CategorizedData:
    """Contribution data with categorization applied."""

    raw_data: ContributionData
    categorized_prs: list[CategorizedPR]

    @property
    def big_rocks(self) -> list[CategorizedPR]:
        """Get all big rock PRs."""
        return [cp for cp in self.categorized_prs if cp.is_big_rock]

    @property
    def features(self) -> list[CategorizedPR]:
        """Get feature PRs."""
        return [cp for cp in self.categorized_prs if cp.category == PRCategory.FEATURE]

    @property
    def bugfixes(self) -> list[CategorizedPR]:
        """Get bugfix PRs."""
        return [cp for cp in self.categorized_prs if cp.category == PRCategory.BUGFIX]

    @property
    def infrastructure(self) -> list[CategorizedPR]:
        """Get infrastructure PRs."""
        return [cp for cp in self.categorized_prs if cp.category == PRCategory.INFRASTRUCTURE]

    @property
    def documentation(self) -> list[CategorizedPR]:
        """Get documentation PRs."""
        return [cp for cp in self.categorized_prs if cp.category == PRCategory.DOCUMENTATION]

    @property
    def refactors(self) -> list[CategorizedPR]:
        """Get refactor PRs."""
        return [cp for cp in self.categorized_prs if cp.category == PRCategory.REFACTOR]

    @property
    def tests(self) -> list[CategorizedPR]:
        """Get test PRs."""
        return [cp for cp in self.categorized_prs if cp.category == PRCategory.TEST]

    def by_repo(self) -> dict[str, list[CategorizedPR]]:
        """Group categorized PRs by repository."""
        repos: dict[str, list[CategorizedPR]] = {}
        for cp in self.categorized_prs:
            repo = cp.pr.repo_name
            if repo not in repos:
                repos[repo] = []
            repos[repo].append(cp)
        return repos

    def by_quarter(self) -> dict[str, list[CategorizedPR]]:
        """Group categorized PRs by quarter."""
        quarters: dict[str, list[CategorizedPR]] = {}
        for cp in self.categorized_prs:
            date = cp.pr.merged_at or cp.pr.created_at
            quarter = f"Q{(date.month - 1) // 3 + 1}"
            if quarter not in quarters:
                quarters[quarter] = []
            quarters[quarter].append(cp)
        return quarters


class Categorizer:
    """Categorizes PRs and identifies big rocks."""

    # Thresholds for big rocks
    BIG_ROCK_FILES_THRESHOLD = 10
    BIG_ROCK_LINES_THRESHOLD = 500

    # Keywords for categorization
    FEATURE_KEYWORDS = [
        r"\bfeat\b", r"\bfeature\b", r"\badd\b", r"\bnew\b", r"\bimplement\b",
        r"\bsupport\b", r"\benable\b", r"\bintroduce\b",
    ]
    BUGFIX_KEYWORDS = [
        r"\bfix\b", r"\bbug\b", r"\bhotfix\b", r"\bpatch\b", r"\bresolve\b",
        r"\bcorrect\b", r"\brepair\b",
    ]
    INFRA_KEYWORDS = [
        r"\binfra\b", r"\bci\b", r"\bcd\b", r"\bpipeline\b", r"\bdeploy\b",
        r"\bconfig\b", r"\bsetup\b", r"\bdevops\b", r"\bterraform\b",
        r"\bkubernetes\b", r"\bk8s\b", r"\bdocker\b", r"\bhelm\b",
        r"\bautomation\b", r"\bscript\b", r"\btooling\b",
    ]
    DOC_KEYWORDS = [
        r"\bdoc\b", r"\bdocs\b", r"\breadme\b", r"\bchangelog\b",
        r"\bcomment\b", r"\bjsdoc\b", r"\btypedoc\b",
    ]
    REFACTOR_KEYWORDS = [
        r"\brefactor\b", r"\bcleanup\b", r"\bclean up\b", r"\brestructure\b",
        r"\breorganize\b", r"\bsimplify\b", r"\bimprove\b", r"\boptimize\b",
    ]
    TEST_KEYWORDS = [
        r"\btest\b", r"\btests\b", r"\bspec\b", r"\bcoverage\b",
        r"\bunit\b", r"\bintegration\b", r"\be2e\b",
    ]

    # Keywords that indicate big rocks
    BIG_ROCK_KEYWORDS = [
        r"\bmajor\b", r"\blaunch\b", r"\bmigration\b", r"\bredesign\b",
        r"\boverhaul\b", r"\bv\d+\b", r"\brelease\b", r"\bepic\b",
        r"\bbreaking\b", r"\bcore\b", r"\bplatform\b", r"\barchitecture\b",
        r"\bfoundation\b", r"\bframework\b", r"\bsystem\b", r"\bengine\b",
    ]

    # Labels that indicate big rocks
    BIG_ROCK_LABELS = [
        "epic", "major", "breaking-change", "feature", "release",
        "milestone", "important", "priority", "p0", "p1",
    ]

    def categorize(self, data: ContributionData) -> CategorizedData:
        """
        Categorize all PRs and identify big rocks.

        Args:
            data: Raw contribution data.

        Returns:
            CategorizedData with all PRs categorized.
        """
        categorized_prs = []

        for pr in data.merged_prs:
            category = self._categorize_pr(pr)
            is_big_rock, reason = self._is_big_rock(pr)

            categorized_prs.append(
                CategorizedPR(
                    pr=pr,
                    category=category,
                    is_big_rock=is_big_rock,
                    big_rock_reason=reason,
                )
            )

        # Sort by date (newest first)
        categorized_prs.sort(
            key=lambda cp: cp.pr.merged_at or cp.pr.created_at,
            reverse=True,
        )

        return CategorizedData(raw_data=data, categorized_prs=categorized_prs)

    def _categorize_pr(self, pr: PullRequestData) -> PRCategory:
        """Determine the category of a PR based on title, body, and labels."""
        text = f"{pr.title} {pr.body or ''} {' '.join(pr.labels)}".lower()

        # Check in order of specificity
        if self._matches_keywords(text, self.TEST_KEYWORDS):
            return PRCategory.TEST
        if self._matches_keywords(text, self.DOC_KEYWORDS):
            return PRCategory.DOCUMENTATION
        if self._matches_keywords(text, self.INFRA_KEYWORDS):
            return PRCategory.INFRASTRUCTURE
        if self._matches_keywords(text, self.REFACTOR_KEYWORDS):
            return PRCategory.REFACTOR
        if self._matches_keywords(text, self.BUGFIX_KEYWORDS):
            return PRCategory.BUGFIX
        if self._matches_keywords(text, self.FEATURE_KEYWORDS):
            return PRCategory.FEATURE

        return PRCategory.OTHER

    def _is_big_rock(self, pr: PullRequestData) -> tuple[bool, str | None]:
        """
        Determine if a PR is a big rock.

        Returns:
            Tuple of (is_big_rock, reason).
        """
        text = f"{pr.title} {pr.body or ''}".lower()
        label_text = " ".join(pr.labels).lower()

        # Check size thresholds
        if pr.changed_files >= self.BIG_ROCK_FILES_THRESHOLD:
            return True, f"Large scope: {pr.changed_files} files changed"

        total_lines = pr.additions + pr.deletions
        if total_lines >= self.BIG_ROCK_LINES_THRESHOLD:
            return True, f"Significant changes: {total_lines} lines"

        # Check keywords in title/body
        if self._matches_keywords(text, self.BIG_ROCK_KEYWORDS):
            return True, "Keywords indicate major work"

        # Check labels
        for label in pr.labels:
            if label.lower() in self.BIG_ROCK_LABELS:
                return True, f"Label: {label}"

        return False, None

    def _matches_keywords(self, text: str, keywords: list[str]) -> bool:
        """Check if text matches any of the keyword patterns."""
        for pattern in keywords:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
