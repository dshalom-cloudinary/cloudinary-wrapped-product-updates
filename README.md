# GitHub Wrapped - Performance Review Tool

A CLI tool that fetches your GitHub contributions and generates an **AI-powered performance review** structured around your Execution and Culture framework. Uses OpenAI to create a narrative self-assessment based on your actual work.

## Features

- **AI-Powered Reports**: Uses OpenAI to generate compelling, evidence-based performance reviews
- **Framework Aligned**: Addresses Execution (Quality, Time, Focus, Impact) and Culture (Helpful, Customer Value, Healthy Growth, etc.)
- **Data-Driven**: Backs up claims with real metrics and PR references
- **Fallback Mode**: Can generate template-based reports without AI

## Setup

1. Clone this repository
2. Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

4. Configure your `.env` file:
   - **GitHub Token**: Create a PAT at https://github.com/settings/tokens with scopes:
     - `repo` - Full control of private repositories
     - `read:org` - Read org membership
     - `read:user` - Read user profile data
   - **OpenAI API Key**: Create one at https://platform.openai.com/api-keys

## Usage

```bash
# Generate AI-powered report (default)
python -m github_wrapped --orgs cloudinary --year 2025

# Multiple organizations
python -m github_wrapped --orgs cloudinary,other-org --year 2025

# Specific repositories only
python -m github_wrapped --orgs cloudinary --repos repo1,repo2 --year 2025

# Use a specific OpenAI model
python -m github_wrapped --orgs cloudinary --model gpt-4o-mini

# Generate template-based report (no AI)
python -m github_wrapped --orgs cloudinary --no-ai

# Output will be saved to: output/performance-review-2025-ai.md
```

### CLI Options

| Option | Description |
|--------|-------------|
| `--orgs`, `-o` | Comma-separated list of GitHub organizations (required) |
| `--repos`, `-r` | Specific repository names to include |
| `--year`, `-y` | Year to generate report for (default: 2025) |
| `--output`, `-O` | Output directory (default: output) |
| `--ai/--no-ai` | Use AI for report generation (default: --ai) |
| `--model`, `-m` | OpenAI model to use (default: gpt-4o) |
| `--token`, `-t` | GitHub token (or set GITHUB_TOKEN env var) |
| `--openai-key` | OpenAI API key (or set OPENAI_API_KEY env var) |

## Report Structure

The AI-generated report addresses:

### Execution
- **Quality**: Bug fixes, refactoring, test coverage
- **Time**: Quarterly delivery cadence, consistent output
- **Focus**: Work concentration across repositories/projects
- **Impact**: Customer-facing features, major accomplishments

### Culture
- **We Are All People**: Code reviews, collaboration with teammates
- **Customer Value First**: Features and improvements delivered
- **Healthy Growth**: Infrastructure, documentation, automation
- **Efficient and Impactful**: PR size metrics, focused work
- **Humble, Helpful, Proud**: Helping others, knowledge sharing
- **Life & Work**: Sustainable pace indicators

## How It Works

1. **Fetches** your GitHub contributions (PRs, reviews, commits)
2. **Categorizes** work by type (feature, bugfix, infrastructure, etc.)
3. **Identifies** major accomplishments ("big rocks")
4. **Sends** structured data to OpenAI with the performance framework
5. **Generates** a narrative self-assessment with evidence

## Data Collected

- Pull Requests you authored (with descriptions, size, labels)
- Code reviews you gave to teammates
- Commit activity by repository
- Quarterly distribution of work

## Privacy

- All data stays between you and GitHub/OpenAI
- No data is stored or sent elsewhere
- You can use `--no-ai` to avoid sending data to OpenAI
