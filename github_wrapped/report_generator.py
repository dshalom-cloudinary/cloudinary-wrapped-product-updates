"""Markdown report generator aligned to performance review framework."""

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .categorizer import CategorizedData, CategorizedPR, PRCategory
from .data_fetcher import ContributionData, ReviewData


class ReportGenerator:
    """Generates a markdown report for performance review."""

    def __init__(self, categorized_data: CategorizedData):
        """
        Initialize the report generator.

        Args:
            categorized_data: Categorized contribution data.
        """
        self.data = categorized_data
        self.raw = categorized_data.raw_data

    def generate(self) -> str:
        """Generate the full markdown report."""
        sections = [
            self._header(),
            self._summary_stats(),
            self._big_rocks_section(),
            self._execution_section(),
            self._culture_section(),
            self._raw_data_section(),
        ]
        return "\n\n".join(sections)

    def save(self, output_dir: str = "output") -> Path:
        """
        Save the report to a file.

        Args:
            output_dir: Directory to save the report.

        Returns:
            Path to the saved file.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"performance-review-{self.raw.year}.md"
        filepath = output_path / filename

        report = self.generate()
        filepath.write_text(report)

        return filepath

    def _header(self) -> str:
        """Generate the report header."""
        return f"""# GitHub Wrapped - {self.raw.year} Performance Review

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**User:** {self.raw.username}
**Organizations:** {", ".join(self.raw.orgs)}

---

Use this report to help fill out your performance review. The sections below are organized around the Execution and Culture framework."""

    def _summary_stats(self) -> str:
        """Generate summary statistics."""
        total_prs = len(self.data.categorized_prs)
        big_rocks = len(self.data.big_rocks)
        reviews = len(self.raw.reviews)
        commits = len(self.raw.commits)

        # Calculate lines changed
        total_additions = sum(cp.pr.additions for cp in self.data.categorized_prs)
        total_deletions = sum(cp.pr.deletions for cp in self.data.categorized_prs)

        # Count repos
        repos = set(cp.pr.repo_name for cp in self.data.categorized_prs)

        return f"""## Overview

| Metric | Count |
|--------|-------|
| Pull Requests Merged | {total_prs} |
| Big Rock Contributions | {big_rocks} |
| Code Reviews Given | {reviews} |
| Commits | {commits} |
| Lines Added | {total_additions:,} |
| Lines Removed | {total_deletions:,} |
| Repositories | {len(repos)} |"""

    def _big_rocks_section(self) -> str:
        """Generate the big rocks section."""
        big_rocks = self.data.big_rocks

        if not big_rocks:
            return """## Big Rocks (Major Accomplishments)

No big rock contributions identified based on size/keyword thresholds. Consider lowering thresholds or manually reviewing the raw data section."""

        lines = ["## Big Rocks (Major Accomplishments)", ""]
        lines.append("These are your most significant contributions, identified by scope, impact keywords, or labels.")
        lines.append("")

        # Group by repository
        by_repo: dict[str, list[CategorizedPR]] = defaultdict(list)
        for cp in big_rocks:
            by_repo[cp.pr.repo_name].append(cp)

        for repo, prs in sorted(by_repo.items()):
            lines.append(f"### {repo}")
            lines.append("")
            for cp in prs:
                date = (cp.pr.merged_at or cp.pr.created_at).strftime("%Y-%m-%d")
                reason = f" *({cp.big_rock_reason})*" if cp.big_rock_reason else ""
                lines.append(f"- **[{cp.pr.title}]({cp.pr.url})**{reason}")
                lines.append(f"  - {date} | +{cp.pr.additions}/-{cp.pr.deletions} | {cp.pr.changed_files} files")
                if cp.pr.body:
                    # Include first 200 chars of description
                    desc = cp.pr.body.replace("\n", " ").strip()[:200]
                    if len(cp.pr.body) > 200:
                        desc += "..."
                    lines.append(f"  - {desc}")
                lines.append("")

        return "\n".join(lines)

    def _execution_section(self) -> str:
        """Generate the Execution evidence section."""
        lines = ["## Execution Evidence", ""]

        # Quality section
        lines.extend(self._quality_subsection())
        lines.append("")

        # Time section
        lines.extend(self._time_subsection())
        lines.append("")

        # Focus section
        lines.extend(self._focus_subsection())
        lines.append("")

        # Impact section
        lines.extend(self._impact_subsection())

        return "\n".join(lines)

    def _quality_subsection(self) -> list[str]:
        """Generate Quality evidence."""
        lines = ["### Quality"]
        lines.append("")
        lines.append("*Level of quality at which tasks were performed.*")
        lines.append("")

        # Bugfixes and refactors indicate quality focus
        bugfixes = self.data.bugfixes
        refactors = self.data.refactors
        tests = self.data.tests

        if bugfixes or refactors or tests:
            lines.append("**Evidence of quality focus:**")
            lines.append("")
            if bugfixes:
                lines.append(f"- Fixed {len(bugfixes)} bugs")
            if refactors:
                lines.append(f"- {len(refactors)} refactoring/improvement PRs")
            if tests:
                lines.append(f"- {len(tests)} test-related PRs")
            lines.append("")

            # Show top examples
            quality_prs = bugfixes[:3] + refactors[:3] + tests[:3]
            if quality_prs:
                lines.append("**Examples:**")
                for cp in quality_prs[:5]:
                    lines.append(f"- [{cp.pr.title}]({cp.pr.url}) ({cp.pr.repo_name})")
        else:
            lines.append("*No specific quality-focused PRs identified. Review raw data for examples.*")

        return lines

    def _time_subsection(self) -> list[str]:
        """Generate Time evidence."""
        lines = ["### Time"]
        lines.append("")
        lines.append("*Meeting predefined timelines and milestones.*")
        lines.append("")
        lines.append("**Quarterly delivery cadence:**")
        lines.append("")

        quarters = self.data.by_quarter()
        for q in ["Q1", "Q2", "Q3", "Q4"]:
            count = len(quarters.get(q, []))
            lines.append(f"- {q}: {count} PRs merged")

        lines.append("")
        lines.append("*Note: GitHub data doesn't track sprint commitments. Add context about deadline achievements manually.*")

        return lines

    def _focus_subsection(self) -> list[str]:
        """Generate Focus evidence."""
        lines = ["### Focus"]
        lines.append("")
        lines.append("*Focus on goals, initiatives and tasks that create most value.*")
        lines.append("")

        # Show where effort was concentrated
        by_repo = self.data.by_repo()
        sorted_repos = sorted(by_repo.items(), key=lambda x: len(x[1]), reverse=True)

        lines.append("**Work concentration by repository:**")
        lines.append("")
        for repo, prs in sorted_repos[:10]:
            lines.append(f"- **{repo}**: {len(prs)} PRs")

        return lines

    def _impact_subsection(self) -> list[str]:
        """Generate Impact evidence."""
        lines = ["### Impact"]
        lines.append("")
        lines.append("*Actual value delivered to customers (internal and external).*")
        lines.append("")

        features = self.data.features
        big_rocks = self.data.big_rocks

        if features or big_rocks:
            lines.append("**Customer-facing and high-impact work:**")
            lines.append("")

            # Combine features and big rocks, dedupe
            impact_prs = {cp.pr.url: cp for cp in features + big_rocks}
            for cp in list(impact_prs.values())[:10]:
                date = (cp.pr.merged_at or cp.pr.created_at).strftime("%Y-%m-%d")
                lines.append(f"- [{cp.pr.title}]({cp.pr.url}) - {date}")
        else:
            lines.append("*Review big rocks section and raw data for impact examples.*")

        return lines

    def _culture_section(self) -> str:
        """Generate the Culture evidence section."""
        lines = ["## Culture Evidence", ""]

        # Humble, Helpful, Proud
        lines.extend(self._helpful_subsection())
        lines.append("")

        # Healthy Growth
        lines.extend(self._healthy_growth_subsection())
        lines.append("")

        # Efficient and Impactful
        lines.extend(self._efficient_subsection())

        return "\n".join(lines)

    def _helpful_subsection(self) -> list[str]:
        """Generate Humble, Helpful, Proud evidence."""
        lines = ["### Humble, Helpful, and Proud"]
        lines.append("")
        lines.append("*Growth mindset, helping others, accountability.*")
        lines.append("")

        reviews = self.raw.reviews

        if reviews:
            lines.append(f"**Code reviews given:** {len(reviews)}")
            lines.append("")

            # Group by who was helped
            by_author: dict[str, list[ReviewData]] = defaultdict(list)
            for review in reviews:
                by_author[review.author].append(review)

            lines.append("**Teammates supported:**")
            lines.append("")
            sorted_authors = sorted(by_author.items(), key=lambda x: len(x[1]), reverse=True)
            for author, author_reviews in sorted_authors[:10]:
                lines.append(f"- @{author}: {len(author_reviews)} reviews")

            lines.append("")
            lines.append("**Recent review examples:**")
            lines.append("")
            for review in reviews[:5]:
                lines.append(f"- [{review.pr_title}]({review.pr_url}) for @{review.author}")
        else:
            lines.append("*No code review data found. This may indicate private repos or API limitations.*")

        return lines

    def _healthy_growth_subsection(self) -> list[str]:
        """Generate Healthy Growth evidence."""
        lines = ["### Healthy Growth"]
        lines.append("")
        lines.append("*Balance between immediate results and long-term investment.*")
        lines.append("")

        infra = self.data.infrastructure
        docs = self.data.documentation
        refactors = self.data.refactors

        investment_prs = infra + docs + refactors

        if investment_prs:
            lines.append("**Investment in long-term improvements:**")
            lines.append("")
            if infra:
                lines.append(f"- Infrastructure/tooling: {len(infra)} PRs")
            if docs:
                lines.append(f"- Documentation: {len(docs)} PRs")
            if refactors:
                lines.append(f"- Refactoring: {len(refactors)} PRs")

            lines.append("")
            lines.append("**Examples:**")
            lines.append("")
            for cp in investment_prs[:5]:
                lines.append(f"- [{cp.pr.title}]({cp.pr.url}) ({cp.category.value})")
        else:
            lines.append("*No infrastructure/documentation PRs identified. Review raw data for examples.*")

        return lines

    def _efficient_subsection(self) -> list[str]:
        """Generate Efficient and Impactful evidence."""
        lines = ["### Efficient and Impactful"]
        lines.append("")
        lines.append("*Focus on high-value work, break down to small impactful steps.*")
        lines.append("")

        # Calculate average PR size
        if self.data.categorized_prs:
            avg_files = sum(cp.pr.changed_files for cp in self.data.categorized_prs) / len(self.data.categorized_prs)
            avg_lines = sum(cp.pr.additions + cp.pr.deletions for cp in self.data.categorized_prs) / len(self.data.categorized_prs)

            lines.append("**PR size metrics (smaller = more focused):**")
            lines.append("")
            lines.append(f"- Average files per PR: {avg_files:.1f}")
            lines.append(f"- Average lines per PR: {avg_lines:.0f}")
        else:
            lines.append("*No PR data available.*")

        return lines

    def _raw_data_section(self) -> str:
        """Generate the raw data reference section."""
        lines = ["## Raw Data Reference", ""]
        lines.append("Complete list of merged PRs for cherry-picking examples.")
        lines.append("")

        quarters = self.data.by_quarter()

        for q in ["Q1", "Q2", "Q3", "Q4"]:
            q_prs = quarters.get(q, [])
            if not q_prs:
                continue

            lines.append(f"### {q} {self.raw.year}")
            lines.append("")

            for cp in q_prs:
                date = (cp.pr.merged_at or cp.pr.created_at).strftime("%m-%d")
                category = cp.category.value
                rock = " 🪨" if cp.is_big_rock else ""
                lines.append(f"- `{date}` [{cp.pr.title}]({cp.pr.url}) *{cp.pr.repo_name}* ({category}){rock}")

            lines.append("")

        return "\n".join(lines)
