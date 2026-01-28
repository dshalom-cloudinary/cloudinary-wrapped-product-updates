"""LLM-powered report generator for performance reviews."""

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from .data_fetcher import ContributionData, PullRequestData


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
- Pull requests authored (with titles, descriptions, size, and labels)
- Code reviews given to teammates
- Commits made
- Repository and project distribution

Your task is to analyze the contributions, understand what's important, and write a compelling, evidence-based performance review that addresses both Execution and Culture aspects of the performance framework.

{execution_framework}

{culture_framework}

## How to Analyze the Data

As you read through the PRs, internally consider:
- What type of work each PR represents (features, bug fixes, infrastructure, documentation, refactoring, tests, etc.)
- Which contributions are "big rocks" - major accomplishments with significant impact (large scope, strategic importance, or notable complexity)
- What themes and patterns emerge across the work
- How the work demonstrates the Execution and Culture framework values

Use this understanding to write the review, but DO NOT output your categorization or analysis. The review should read naturally, highlighting the most impactful work without explicitly labeling PRs by category.

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
    
    # All PRs (uncategorized - LLM will categorize)
    pull_requests: list[dict]
    
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
        
        # All pull requests
        lines.append("## Pull Requests")
        lines.append("")
        
        for i, pr in enumerate(self.pull_requests, 1):
            lines.append(f"### PR {i}: {pr['title']}")
            lines.append(f"- Repository: {pr['repo']}")
            lines.append(f"- Date: {pr['date']}")
            lines.append(f"- Size: +{pr['additions']}/-{pr['deletions']} in {pr['changed_files']} files")
            if pr.get('labels'):
                lines.append(f"- Labels: {', '.join(pr['labels'])}")
            if pr.get('description'):
                # Truncate very long descriptions
                desc = pr['description'][:500]
                if len(pr['description']) > 500:
                    desc += "..."
                lines.append(f"- Description: {desc}")
            lines.append(f"- URL: {pr['url']}")
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
    """Generates performance review reports using OpenAI.
    
    The LLM handles both categorization and report generation, providing
    better contextual understanding than rule-based categorization.
    """
    
    def __init__(
        self,
        data: ContributionData,
        api_key: str | None = None,
        model: str = "gpt-5.2",
    ):
        """
        Initialize the LLM report generator.
        
        Args:
            data: Raw contribution data (uncategorized).
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: OpenAI model to use.
        """
        self.data = data
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
        merged_prs = self.data.merged_prs
        
        def pr_to_dict(pr: PullRequestData) -> dict:
            """Convert a PR to a dictionary for the LLM."""
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
            }
        
        # Calculate quarterly distribution
        quarterly_prs: dict[str, int] = defaultdict(int)
        for pr in merged_prs:
            date = pr.merged_at or pr.created_at
            quarter = f"Q{(date.month - 1) // 3 + 1}"
            quarterly_prs[quarter] += 1
        
        # Teammates reviewed
        teammates_reviewed: dict[str, int] = defaultdict(int)
        for review in self.data.reviews:
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
            for r in self.data.reviews
        ]
        
        return ContributionSummary(
            username=self.data.username,
            year=self.data.year,
            organizations=self.data.orgs,
            total_prs_merged=len(merged_prs),
            total_reviews_given=len(self.data.reviews),
            total_commits=len(self.data.commits),
            total_additions=sum(pr.additions for pr in merged_prs),
            total_deletions=sum(pr.deletions for pr in merged_prs),
            repositories_contributed_to=list(set(pr.repo_name for pr in merged_prs)),
            pull_requests=[pr_to_dict(pr) for pr in merged_prs],
            teammates_reviewed=dict(teammates_reviewed),
            review_details=review_details,
            quarterly_prs=dict(quarterly_prs),
        )
    
    def generate(self) -> str:
        """Generate the performance review report using the LLM.
        
        The LLM will analyze and categorize the PRs, identify major accomplishments,
        and write a comprehensive performance review.
        """
        # Prepare the data summary
        summary = self._prepare_summary()
        prompt_data = summary.to_prompt_data()
        
        # Build the user message
        user_message = f"""Based on the following GitHub contribution data, write a comprehensive performance review self-assessment for {self.data.year}.

The review should address the question:
"Please share your main accomplishments throughout {self.data.year} in the aspects of execution and culture."

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
            max_completion_tokens=10000,
        )
        
        # Check for valid response
        if not response.choices:
            raise ValueError(
                f"OpenAI returned no choices. "
                f"Finish reason: {getattr(response, 'finish_reason', 'unknown')}"
            )
        
        choice = response.choices[0]
        report_content = choice.message.content
        
        # Check for empty content and provide helpful error
        if not report_content:
            finish_reason = getattr(choice, 'finish_reason', 'unknown')
            refusal = getattr(choice.message, 'refusal', None)
            
            error_details = [f"Finish reason: {finish_reason}"]
            if refusal:
                error_details.append(f"Refusal: {refusal}")
            
            raise ValueError(
                f"OpenAI returned empty content. {'; '.join(error_details)}. "
                f"This may indicate the model refused the request, hit a content filter, "
                f"or the request was too large. Try a different model or reduce the data."
            )
        
        # Add header and metadata
        header = self._generate_header()
        footer = self._generate_footer()
        
        return f"{header}\n\n{report_content}\n\n{footer}"
    
    def _generate_header(self) -> str:
        """Generate the report header."""
        return f"""# Performance Review Self-Assessment - {self.data.year}

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**User:** {self.data.username}
**Organizations:** {", ".join(self.data.orgs)}

---

*This report was generated using AI based on your GitHub contributions. The AI analyzed and categorized your PRs to identify themes and major accomplishments. Please review and customize it to accurately reflect your accomplishments and add context that may not be visible in the code.*

---"""

    def _generate_footer(self) -> str:
        """Generate the report footer with raw data reference."""
        merged_prs = self.data.merged_prs
        
        lines = ["---", "", "## Appendix: Raw Data Summary", ""]
        lines.append("| Metric | Count |")
        lines.append("|--------|-------|")
        lines.append(f"| Pull Requests Merged | {len(merged_prs)} |")
        lines.append(f"| Code Reviews Given | {len(self.data.reviews)} |")
        lines.append(f"| Commits | {len(self.data.commits)} |")
        
        total_additions = sum(pr.additions for pr in merged_prs)
        total_deletions = sum(pr.deletions for pr in merged_prs)
        lines.append(f"| Lines Added | {total_additions:,} |")
        lines.append(f"| Lines Removed | {total_deletions:,} |")
        
        repos = set(pr.repo_name for pr in merged_prs)
        lines.append(f"| Repositories | {len(repos)} |")
        
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
        
        timestamp = int(datetime.now().timestamp())
        filename = f"performance-review-{self.data.year}-ai-{timestamp}.md"
        filepath = output_path / filename
        
        report = self.generate()
        filepath.write_text(report)
        
        return filepath
