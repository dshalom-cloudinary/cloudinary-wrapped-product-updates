"""LLM-powered report generator for performance reviews."""

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from .categorizer import CategorizedData, CategorizedPR, PRCategory
from .data_fetcher import ContributionData, ReviewData


# Performance review framework definitions
EXECUTION_FRAMEWORK = """
## Execution Framework

### Quality
Level of quality at which tasks were performed.

### Time
Meeting predefined timelines and milestones of the tasks/projects/processes you own.

### Focus
Focus on goals, initiatives and tasks that create most value and move the needle.

### Impact
The actual value you have contributed that was delivered to customers (internal and external), affected our goals or way of work, quarter after quarter (consistent bottom-line results).
"""

CULTURE_FRAMEWORK = """
## Culture Framework

### We Are All People
Consider other perspectives while making decisions; Give others the benefit of the doubt; Contribute to creating respectful and empathic environment.

### Customer Value First
Serve customers and maximize value for them; Perceive customers' success as your own success.

### Healthy Growth
Balance between delivering immediate results to investing in long-term goals (infrastructure, automation, process improvement, innovation, professional development).

### Efficient and Impactful
Focus on goals, initiatives and tasks that create most value and moves the needle. Break down projects/tasks to small, impactful steps.

### Humble, Helpful and Proud
Growth mindset - ability to gain new knowledge, learn from others, ask for help when needed; Accountability on development of self and others; Ownership - meet commitments, raise flags on time, resolve problems proactively; Contribute to achievement of team goals and challenges. Work proactively to assist others.

### Life & Work
Keep balance between high work ethics and personal life.
"""

SYSTEM_PROMPT = """You are an expert performance review writer helping an engineer prepare their annual performance review self-assessment.

You will be given detailed GitHub contribution data for a year, including:
- Pull requests authored (with descriptions, size, and impact indicators)
- Code reviews given to teammates
- Commits made
- Repository and project distribution

Your task is to write a compelling, evidence-based performance review that addresses both Execution and Culture aspects of the performance framework.

{execution_framework}

{culture_framework}

## Guidelines for Writing

1. **Be specific and evidence-based**: Reference actual PRs, projects, and metrics from the data
2. **Quantify achievements**: Use numbers for PRs merged, reviews given, lines of code, projects contributed to
3. **Highlight impact**: Focus on customer and business value, not just technical work
4. **Balance execution and culture**: Address all framework areas with relevant examples
5. **Be honest but positive**: Present achievements confidently without exaggeration
6. **Use concrete examples**: Quote PR titles and descriptions when they demonstrate value
7. **Identify themes**: Group related work to show strategic focus and consistency
8. **Show growth**: Highlight areas where skills were developed or expanded

## Output Format

Write a structured self-assessment in markdown format with these sections:
1. Executive Summary (2-3 sentences)
2. Key Accomplishments (3-5 major achievements with evidence)
3. Execution (Quality, Time, Focus, Impact - with specific examples)
4. Culture (address relevant aspects with evidence from code reviews, collaboration, etc.)
5. Growth Areas (areas of development demonstrated this year)

Be concise but comprehensive. Each point should be backed by data from the contributions.""".format(
    execution_framework=EXECUTION_FRAMEWORK,
    culture_framework=CULTURE_FRAMEWORK
)


@dataclass
class ContributionSummary:
    """Structured summary of contributions for LLM consumption."""
    
    username: str
    year: int
    organizations: list[str]
    
    # High-level metrics
    total_prs_merged: int
    total_reviews_given: int
    total_commits: int
    total_additions: int
    total_deletions: int
    repositories_contributed_to: list[str]
    
    # Categorized work
    features: list[dict]
    bugfixes: list[dict]
    infrastructure: list[dict]
    documentation: list[dict]
    refactors: list[dict]
    tests: list[dict]
    
    # High-impact work
    big_rocks: list[dict]
    
    # Collaboration metrics
    teammates_reviewed: dict[str, int]  # teammate -> review count
    review_details: list[dict]
    
    # Quarterly distribution
    quarterly_prs: dict[str, int]
    
    def to_prompt_data(self) -> str:
        """Convert to a structured string for the LLM prompt."""
        lines = []
        
        lines.append(f"# GitHub Contributions for {self.username} in {self.year}")
        lines.append(f"\nOrganizations: {', '.join(self.organizations)}")
        lines.append("")
        
        # High-level metrics
        lines.append("## Summary Metrics")
        lines.append(f"- Pull Requests Merged: {self.total_prs_merged}")
        lines.append(f"- Code Reviews Given: {self.total_reviews_given}")
        lines.append(f"- Commits: {self.total_commits}")
        lines.append(f"- Lines Added: {self.total_additions:,}")
        lines.append(f"- Lines Removed: {self.total_deletions:,}")
        lines.append(f"- Repositories: {len(self.repositories_contributed_to)}")
        lines.append("")
        
        # Quarterly distribution
        lines.append("## Quarterly Distribution")
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:
            count = self.quarterly_prs.get(quarter, 0)
            lines.append(f"- {quarter}: {count} PRs")
        lines.append("")
        
        # Repository focus
        lines.append("## Repositories Contributed To")
        for repo in self.repositories_contributed_to[:10]:
            lines.append(f"- {repo}")
        if len(self.repositories_contributed_to) > 10:
            lines.append(f"- ... and {len(self.repositories_contributed_to) - 10} more")
        lines.append("")
        
        # Big rocks / major accomplishments
        if self.big_rocks:
            lines.append("## Major Accomplishments (Big Rocks)")
            for pr in self.big_rocks:
                lines.append(f"\n### {pr['title']}")
                lines.append(f"- Repository: {pr['repo']}")
                lines.append(f"- Date: {pr['date']}")
                lines.append(f"- Size: +{pr['additions']}/-{pr['deletions']} in {pr['changed_files']} files")
                lines.append(f"- Impact Reason: {pr['big_rock_reason']}")
                if pr.get('description'):
                    # Truncate very long descriptions
                    desc = pr['description'][:500]
                    if len(pr['description']) > 500:
                        desc += "..."
                    lines.append(f"- Description: {desc}")
                lines.append(f"- URL: {pr['url']}")
            lines.append("")
        
        # Features
        if self.features:
            lines.append("## Features Delivered")
            for pr in self.features[:15]:  # Limit to avoid token overflow
                lines.append(f"- [{pr['date']}] {pr['title']} ({pr['repo']}) - +{pr['additions']}/-{pr['deletions']}")
                if pr.get('description'):
                    desc = pr['description'][:200]
                    lines.append(f"  Description: {desc}")
            if len(self.features) > 15:
                lines.append(f"- ... and {len(self.features) - 15} more features")
            lines.append("")
        
        # Bugfixes
        if self.bugfixes:
            lines.append("## Bug Fixes")
            for pr in self.bugfixes[:10]:
                lines.append(f"- [{pr['date']}] {pr['title']} ({pr['repo']})")
            if len(self.bugfixes) > 10:
                lines.append(f"- ... and {len(self.bugfixes) - 10} more bug fixes")
            lines.append("")
        
        # Infrastructure
        if self.infrastructure:
            lines.append("## Infrastructure & DevOps")
            for pr in self.infrastructure[:10]:
                lines.append(f"- [{pr['date']}] {pr['title']} ({pr['repo']})")
                if pr.get('description'):
                    desc = pr['description'][:150]
                    lines.append(f"  Description: {desc}")
            if len(self.infrastructure) > 10:
                lines.append(f"- ... and {len(self.infrastructure) - 10} more")
            lines.append("")
        
        # Refactors and quality improvements
        if self.refactors:
            lines.append("## Refactoring & Quality Improvements")
            for pr in self.refactors[:10]:
                lines.append(f"- [{pr['date']}] {pr['title']} ({pr['repo']})")
            if len(self.refactors) > 10:
                lines.append(f"- ... and {len(self.refactors) - 10} more")
            lines.append("")
        
        # Tests
        if self.tests:
            lines.append("## Testing")
            for pr in self.tests[:10]:
                lines.append(f"- [{pr['date']}] {pr['title']} ({pr['repo']})")
            if len(self.tests) > 10:
                lines.append(f"- ... and {len(self.tests) - 10} more")
            lines.append("")
        
        # Documentation
        if self.documentation:
            lines.append("## Documentation")
            for pr in self.documentation[:10]:
                lines.append(f"- [{pr['date']}] {pr['title']} ({pr['repo']})")
            if len(self.documentation) > 10:
                lines.append(f"- ... and {len(self.documentation) - 10} more")
            lines.append("")
        
        # Code reviews / collaboration
        if self.teammates_reviewed:
            lines.append("## Code Reviews & Collaboration")
            lines.append(f"\nTotal reviews given: {self.total_reviews_given}")
            lines.append("\nTeammates supported:")
            sorted_teammates = sorted(self.teammates_reviewed.items(), key=lambda x: x[1], reverse=True)
            for teammate, count in sorted_teammates[:15]:
                lines.append(f"- @{teammate}: {count} reviews")
            if len(sorted_teammates) > 15:
                lines.append(f"- ... and {len(sorted_teammates) - 15} more teammates")
            lines.append("")
            
            # Sample review details
            if self.review_details:
                lines.append("Sample reviews (showing collaboration):")
                for review in self.review_details[:10]:
                    lines.append(f"- Reviewed '{review['pr_title']}' for @{review['author']} ({review['state']})")
            lines.append("")
        
        return "\n".join(lines)


class LLMReportGenerator:
    """Generates performance review reports using OpenAI."""
    
    def __init__(
        self,
        categorized_data: CategorizedData,
        api_key: str | None = None,
        model: str = "gpt-5.2",
    ):
        """
        Initialize the LLM report generator.
        
        Args:
            categorized_data: Categorized contribution data.
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: OpenAI model to use.
        """
        self.data = categorized_data
        self.raw = categorized_data.raw_data
        self.model = model
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
        if not self.client.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
    
    def _prepare_summary(self) -> ContributionSummary:
        """Prepare a structured summary of contributions for the LLM."""
        
        def pr_to_dict(cp: CategorizedPR) -> dict:
            """Convert a categorized PR to a dictionary."""
            pr = cp.pr
            return {
                "title": pr.title,
                "description": pr.body,
                "repo": pr.repo_name,
                "url": pr.url,
                "date": (pr.merged_at or pr.created_at).strftime("%Y-%m-%d"),
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "labels": pr.labels,
                "category": cp.category.value,
                "is_big_rock": cp.is_big_rock,
                "big_rock_reason": cp.big_rock_reason,
            }
        
        # Calculate quarterly distribution
        quarters = self.data.by_quarter()
        quarterly_prs = {q: len(prs) for q, prs in quarters.items()}
        
        # Teammates reviewed
        teammates_reviewed: dict[str, int] = defaultdict(int)
        for review in self.raw.reviews:
            teammates_reviewed[review.author] += 1
        
        # Review details
        review_details = [
            {
                "pr_title": r.pr_title,
                "author": r.author,
                "repo": r.repo_name,
                "state": r.state,
                "date": r.submitted_at.strftime("%Y-%m-%d"),
            }
            for r in self.raw.reviews
        ]
        
        return ContributionSummary(
            username=self.raw.username,
            year=self.raw.year,
            organizations=self.raw.orgs,
            total_prs_merged=len(self.data.categorized_prs),
            total_reviews_given=len(self.raw.reviews),
            total_commits=len(self.raw.commits),
            total_additions=sum(cp.pr.additions for cp in self.data.categorized_prs),
            total_deletions=sum(cp.pr.deletions for cp in self.data.categorized_prs),
            repositories_contributed_to=list(set(cp.pr.repo_name for cp in self.data.categorized_prs)),
            features=[pr_to_dict(cp) for cp in self.data.features],
            bugfixes=[pr_to_dict(cp) for cp in self.data.bugfixes],
            infrastructure=[pr_to_dict(cp) for cp in self.data.infrastructure],
            documentation=[pr_to_dict(cp) for cp in self.data.documentation],
            refactors=[pr_to_dict(cp) for cp in self.data.refactors],
            tests=[pr_to_dict(cp) for cp in self.data.tests],
            big_rocks=[pr_to_dict(cp) for cp in self.data.big_rocks],
            teammates_reviewed=dict(teammates_reviewed),
            review_details=review_details,
            quarterly_prs=quarterly_prs,
        )
    
    def generate(self) -> str:
        """Generate the performance review report using the LLM."""
        
        # Prepare the data summary
        summary = self._prepare_summary()
        prompt_data = summary.to_prompt_data()
        
        # Build the user message
        user_message = f"""Based on the following GitHub contribution data, write a comprehensive performance review self-assessment for {self.raw.year}.

The review should address the question:
"Please share your main accomplishments throughout {self.raw.year} in the aspects of execution and culture."

Here is my GitHub contribution data:

{prompt_data}

Write a compelling, evidence-based performance review that I can use as a starting point for my self-assessment. Be specific, reference actual work, and quantify achievements where possible."""
        
        # Call OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        
        report_content = response.choices[0].message.content or ""
        
        # Add header and metadata
        header = self._generate_header()
        footer = self._generate_footer()
        
        return f"{header}\n\n{report_content}\n\n{footer}"
    
    def _generate_header(self) -> str:
        """Generate the report header."""
        return f"""# Performance Review Self-Assessment - {self.raw.year}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**User:** {self.raw.username}
**Organizations:** {", ".join(self.raw.orgs)}

---

*This report was generated using AI based on your GitHub contributions. Please review and customize it to accurately reflect your accomplishments and add context that may not be visible in the code.*

---"""

    def _generate_footer(self) -> str:
        """Generate the report footer with raw data reference."""
        lines = ["---", "", "## Appendix: Raw Data Summary", ""]
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| Pull Requests Merged | {len(self.data.categorized_prs)} |")
        lines.append(f"| Big Rock Contributions | {len(self.data.big_rocks)} |")
        lines.append(f"| Code Reviews Given | {len(self.raw.reviews)} |")
        lines.append(f"| Commits | {len(self.raw.commits)} |")
        
        total_additions = sum(cp.pr.additions for cp in self.data.categorized_prs)
        total_deletions = sum(cp.pr.deletions for cp in self.data.categorized_prs)
        lines.append(f"| Lines Added | {total_additions:,} |")
        lines.append(f"| Lines Removed | {total_deletions:,} |")
        
        repos = set(cp.pr.repo_name for cp in self.data.categorized_prs)
        lines.append(f"| Repositories | {len(repos)} |")
        
        # List big rocks for reference
        if self.data.big_rocks:
            lines.append("")
            lines.append("### Major Contributions (Big Rocks)")
            lines.append("")
            for cp in self.data.big_rocks:
                date = (cp.pr.merged_at or cp.pr.created_at).strftime("%Y-%m-%d")
                lines.append(f"- [{cp.pr.title}]({cp.pr.url}) - {date} ({cp.pr.repo_name})")
        
        return "\n".join(lines)
    
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
        
        filename = f"performance-review-{self.raw.year}-ai.md"
        filepath = output_path / filename
        
        report = self.generate()
        filepath.write_text(report)
        
        return filepath
