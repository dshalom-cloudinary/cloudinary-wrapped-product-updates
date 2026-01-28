# GitHub Wrapped - Performance Review Tool

A CLI tool that fetches your GitHub contributions and generates a markdown report structured around your performance review framework, highlighting big rocks and providing evidence for Execution and Culture competencies.

## Setup

1. Clone this repository
2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your GitHub Personal Access Token:

```bash
cp .env.example .env
```

4. Create a GitHub PAT at https://github.com/settings/tokens with these scopes:
   - `repo` - Full control of private repositories
   - `read:org` - Read org membership
   - `read:user` - Read user profile data

## Usage

```bash
# Generate report for specific organizations
python -m github_wrapped --orgs cloudinary --year 2025

# Multiple organizations
python -m github_wrapped --orgs cloudinary,other-org --year 2025

# Output will be saved to: output/performance-review-2025.md
```

## Report Structure

The generated report includes:

1. **Big Rocks Summary** - Major accomplishments grouped by project
2. **Execution Evidence** - Quality, Time, Focus, Impact
3. **Culture Evidence** - Helpful, Healthy Growth, Efficient
4. **Raw Data** - All PRs with descriptions for reference

## How It Works

The tool fetches:
- Pull Requests you created and merged
- Code reviews you gave to teammates
- Commit activity by repository

PRs are categorized as:
- `feature` - New functionality → Impact
- `bugfix` - Bug fixes → Quality
- `infrastructure` - Platform/tooling → Healthy Growth
- `documentation` - Docs → Helpful
- `refactor` - Code improvements → Quality
- `test` - Test coverage → Quality
