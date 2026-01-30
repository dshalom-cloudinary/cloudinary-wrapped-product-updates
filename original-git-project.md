# Original Git Project Documentation

## Cloudinary-Wrapped: GitHub Wrapped Video Generator

**Repository**: `cloudinary-hackathons/cloudinary-wrapped`  
**Documentation Date**: January 30, 2026  
**Purpose**: A "Spotify Wrapped"-style video generator for GitHub contributions that fetches GitHub data, analyzes it with OpenAI, and renders an animated video using Remotion.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Python Backend (github_wrapped)](#3-python-backend-github_wrapped)
4. [Video Frontend (wrapped-video)](#4-video-frontend-wrapped-video)
5. [AI Skills](#5-ai-skills)
6. [Data Structures](#6-data-structures)
7. [Environment Configuration](#7-environment-configuration)
8. [Build Commands](#8-build-commands)
9. [Dependencies](#9-dependencies)
10. [File Structure](#10-file-structure)

---

## 1. Project Overview

### What It Does

This project creates personalized "GitHub Wrapped" videos that summarize a user's GitHub contributions for a given year. The workflow is:

1. **Collect** - Fetches GitHub contribution data (PRs, reviews, commits)
2. **Analyze** - Categorizes contributions and generates insights using OpenAI
3. **Prepare** - Transforms data into video-compatible format
4. **Render** - Creates an animated MP4 video using Remotion

### Key Features

- OAuth Device Flow authentication (no token required)
- GraphQL-based GitHub data fetching with pagination
- Rule-based PR categorization (features, bugfixes, infrastructure, etc.)
- "Big rocks" identification (major achievements)
- LLM-powered narrative report generation
- Animated video with 7 scenes and transitions
- Background music with fade effects

---

## 2. Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA COLLECTION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   GitHub API (GraphQL/REST)                                                  │
│         │                                                                    │
│         ▼                                                                    │
│   GitHubClient ──► DataFetcher ──► ContributionData                         │
│         │                              │                                     │
│   DeviceAuth                           │                                     │
│   (OAuth fallback)                     ▼                                     │
│                              ┌─────────┴─────────┐                          │
│                              │                   │                          │
│                              ▼                   ▼                          │
│                        Categorizer        LLMReportGenerator                │
│                              │                   │                          │
│                              ▼                   ▼                          │
│                      CategorizedData      ContributionSummary               │
│                              │                   │                          │
│                              ▼                   ▼                          │
│                      ReportGenerator      OpenAI API                        │
│                              │                   │                          │
│                              ▼                   ▼                          │
│                      Markdown Report     Markdown Report                    │
│                                          + Video Data JSON                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              VIDEO RENDERING                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   video-data.json ──► prepare-video-data.js ──► src/video-data.json        │
│                                                        │                    │
│                                                        ▼                    │
│                                                    Root.tsx                 │
│                                                        │                    │
│                                                        ▼                    │
│                                                WrappedVideo.tsx             │
│                                                        │                    │
│                    ┌───────────┬───────────┬──────────┼──────────┐         │
│                    ▼           ▼           ▼          ▼          ▼         │
│              IntroScene  HeroStats  FunFacts  BigRocks  Quarterly ...      │
│                                                                              │
│                                         │                                    │
│                                         ▼                                    │
│                                  render.js ──► MP4 Video                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Module Dependencies

```
cli.py (entry point)
├── github_client.py (GitHubClient)
│   └── device_auth.py (authenticate_with_device_flow)
├── data_fetcher.py (DataFetcher, ContributionData)
│   └── github_client.py (GitHubClient)
├── categorizer.py (Categorizer, CategorizedData)
│   └── data_fetcher.py (ContributionData, PullRequestData)
├── report_generator.py (ReportGenerator)
│   ├── categorizer.py (CategorizedData)
│   └── data_fetcher.py (ContributionData, ReviewData)
└── llm_report_generator.py (LLMReportGenerator)
    └── data_fetcher.py (ContributionData, PullRequestData)
```

---

## 3. Python Backend (github_wrapped)

### 3.1 Package Structure

```
github_wrapped/
├── __init__.py          # Package init, version "0.1.0"
├── __main__.py          # Entry point for python -m github_wrapped
├── cli.py               # CLI using Typer
├── github_client.py     # GitHub API wrapper
├── device_auth.py       # OAuth Device Flow
├── data_fetcher.py      # Data collection
├── categorizer.py       # PR categorization
├── report_generator.py  # Template-based reports
└── llm_report_generator.py  # LLM-powered reports
```

### 3.2 Module Details

#### `cli.py` - Command Line Interface

Main entry point using Typer framework.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `orgs` | str | Required | Comma-separated organization names |
| `repos` | str | None | Comma-separated repository names (optional filter) |
| `year` | int | Current year | Year for the report |
| `output_dir` | str | "output" | Output directory path |
| `token` | str | None | GitHub token (env: GITHUB_TOKEN) |
| `use_ai` | bool | True | Use AI report generation |
| `openai_key` | str | None | OpenAI API key (env: OPENAI_API_KEY) |
| `openai_model` | str | "gpt-5.2" | OpenAI model to use |
| `fetch_commits` | bool | False | Fetch individual commits |
| `from_file` | str | None | Load from existing JSON file |
| `save_data` | bool | True | Save fetched data to JSON |
| `github_username` | str | None | GitHub username to display |

**Usage:**
```bash
python -m github_wrapped --orgs cloudinary --year 2025 --use-ai
```

---

#### `github_client.py` - GitHub API Client

Wrapper around PyGithub with GraphQL support.

**Class: `GitHubClient`**

```python
class GitHubClient:
    def __init__(self, token: str | None = None, console: Console | None = None)
    
    @property
    def user(self) -> AuthenticatedUser  # Cached authenticated user
    
    @property
    def username(self) -> str  # User's login name
    
    def get_org_repos(self, org_name: str) -> list  # All repos in org
    def get_repo(self, org_name: str, repo_name: str)  # Specific repo
    def verify_connection(self) -> bool  # Test connection
    def execute_graphql(self, query: str, variables: dict | None = None) -> dict
    def close(self)  # Close connection
    
    # Context manager support
    def __enter__(self)
    def __exit__(self, ...)
```

**Features:**
- Automatic token detection from environment
- Falls back to Device Flow OAuth if no token
- GraphQL execution with retry logic
- Rate limit handling

---

#### `device_auth.py` - OAuth Device Flow

Browser-based authentication without storing tokens.

**Functions:**
```python
def request_device_code(client_id: str = GITHUB_CLIENT_ID) -> dict
def poll_for_token(device_code: str, interval: int, expires_in: int, ...) -> str
def authenticate_with_device_flow(console: Console | None = None, ...) -> str
```

**Flow:**
1. Request device code from GitHub
2. Display URL and code to user
3. User opens browser and enters code
4. Poll until user authorizes
5. Return access token

---

#### `data_fetcher.py` - Data Collection

Fetches GitHub contribution data.

**Data Classes:**

```python
@dataclass
class PullRequestData:
    number: int
    title: str
    body: str
    repo: str
    created_at: datetime
    merged_at: datetime | None
    state: str
    additions: int
    deletions: int
    labels: list[str]
    is_author: bool

@dataclass
class ReviewData:
    pr_number: int
    pr_title: str
    pr_repo: str
    submitted_at: datetime
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED
    author: str

@dataclass
class CommitData:
    sha: str
    message: str
    repo: str
    date: datetime
    additions: int
    deletions: int
```

**Class: `ContributionData`**

Container for all fetched data with serialization support.

```python
class ContributionData:
    username: str
    year: int
    pull_requests: list[PullRequestData]
    reviews: list[ReviewData]
    commits: list[CommitData]
    
    @property
    def authored_prs(self) -> list[PullRequestData]  # PRs by user
    
    @property
    def merged_prs(self) -> list[PullRequestData]  # Merged PRs by user
    
    def to_dict(self) -> dict  # JSON-serializable
    def save(self, output_dir: str = "output") -> str  # Save to file
    
    @classmethod
    def from_dict(cls, data: dict) -> "ContributionData"
    
    @classmethod
    def load(cls, filepath: str) -> "ContributionData"
```

**Class: `DataFetcher`**

```python
class DataFetcher:
    def __init__(self, client: GitHubClient, year: int, orgs: list[str], 
                 repos: list[str] | None = None, target_username: str | None = None)
    
    def fetch_all(self, progress: Progress | None = None, 
                  console: Console | None = None,
                  fetch_commits: bool = False) -> ContributionData
```

**GraphQL Queries Used:**
- `AUTHORED_PRS_GRAPHQL` - Fetch PRs authored by user
- `REVIEWS_GRAPHQL` - Fetch code reviews
- `TOP_REPOS_GRAPHQL` - Discover top contributed repos

---

#### `categorizer.py` - PR Categorization

Rule-based categorization of pull requests.

**Enum: `PRCategory`**
```python
class PRCategory(Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    INFRASTRUCTURE = "infrastructure"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    TEST = "test"
    OTHER = "other"
```

**Data Classes:**

```python
@dataclass
class CategorizedPR:
    pr: PullRequestData
    category: PRCategory
    is_big_rock: bool
    big_rock_reason: str | None

@dataclass
class CategorizedData:
    data: ContributionData
    categorized_prs: list[CategorizedPR]
    
    @property
    def big_rocks(self) -> list[CategorizedPR]
    
    @property
    def features(self) -> list[CategorizedPR]
    # ... properties for each category
    
    def by_repo(self) -> dict[str, list[CategorizedPR]]
    def by_quarter(self) -> dict[str, list[CategorizedPR]]
```

**Categorization Rules:**

| Category | Keywords |
|----------|----------|
| FEATURE | feat, feature, add, new, implement |
| BUGFIX | fix, bug, patch, resolve, issue |
| INFRASTRUCTURE | infra, ci, cd, deploy, config, build |
| DOCUMENTATION | doc, readme, comment |
| REFACTOR | refactor, cleanup, clean up, reorganize |
| TEST | test, spec, coverage |

**Big Rock Detection:**
- Lines changed > 500
- Title keywords: "major", "redesign", "rewrite", "migration"
- Labels: "big-rock", "major", "epic"

---

#### `report_generator.py` - Template-Based Reports

Generates markdown reports using templates.

**Class: `ReportGenerator`**

```python
class ReportGenerator:
    def __init__(self, categorized_data: CategorizedData)
    
    def generate(self) -> str  # Full markdown report
    def save(self, output_dir: str = "output") -> Path
```

**Report Sections:**
1. **Header** - Title, date range, summary
2. **Summary Stats** - Total PRs, reviews, commits
3. **Big Rocks** - Major achievements
4. **Execution** - Quality, Time, Focus, Impact evidence
5. **Culture** - Humble/Helpful/Proud, Healthy Growth, Efficient/Impactful
6. **Raw Data** - Reference to JSON file

---

#### `llm_report_generator.py` - AI-Powered Reports

Uses OpenAI to generate narrative reports.

**Data Class:**
```python
@dataclass
class ContributionSummary:
    username: str
    year: int
    total_prs: int
    merged_prs: int
    reviews_given: int
    total_additions: int
    total_deletions: int
    top_repos: list[tuple[str, int]]
    categories: dict[str, int]
    quarterly_distribution: dict[str, int]
    big_rocks: list[dict]
    
    def to_prompt_data(self) -> str  # Formatted for LLM
```

**Class: `LLMReportGenerator`**

```python
class LLMReportGenerator:
    def __init__(self, data: ContributionData, api_key: str | None = None, 
                 model: str = "gpt-5.2")
    
    def generate(self) -> str  # AI-generated markdown report
    def generate_video_data(self) -> dict  # Video-compatible JSON
    def save(self, output_dir: str = "output") -> Path
    def save_video_data(self, output_dir: str = "output") -> Path
```

**Video Data JSON Structure:**
```json
{
  "heroStats": {
    "prsMerged": 42,
    "linesAdded": 15000,
    "linesRemoved": 8000,
    "reviewsGiven": 25,
    "reposContributed": 5
  },
  "funFacts": [
    { "label": "Most Active Day", "value": "Tuesday", "detail": "..." }
  ],
  "bigRocks": [
    { "title": "...", "repo": "...", "impact": "...", "linesChanged": 1200 }
  ],
  "quarterlyActivity": [
    { "quarter": "Q1", "prs": 10, "highlights": ["..."] }
  ],
  "topRepos": [
    { "name": "repo-name", "prs": 15, "funFact": "..." }
  ],
  "yearInReview": {
    "headline": "A Year of Impact",
    "tagline": "..."
  },
  "meta": {
    "username": "user",
    "year": 2025,
    "generatedAt": "2025-01-30T..."
  }
}
```

---

## 4. Video Frontend (wrapped-video)

### 4.1 Project Structure

```
wrapped-video/
├── package.json           # Dependencies and scripts
├── tsconfig.json          # TypeScript config
├── remotion.config.ts     # Remotion settings
├── prepare-video-data.js  # Data validation
├── render.js              # Render script
├── public/                # Static assets
│   ├── intro-bg.png
│   ├── hero-stats-bg.png
│   ├── fun-facts-bg.png
│   ├── big-rocks-achievement.png
│   ├── async-capsule.png
│   ├── captain-crash.png
│   └── background-music.mp3
└── src/
    ├── index.ts           # Remotion entry
    ├── Root.tsx           # Composition definition
    ├── WrappedVideo.tsx   # Main video component
    ├── types.ts           # TypeScript interfaces
    ├── durations.ts       # Timing constants
    ├── video-data.json    # Video data (generated)
    └── scenes/
        ├── IntroScene.tsx
        ├── HeroStatsScene.tsx
        ├── FunFactsScene.tsx
        ├── BigRocksScene.tsx
        ├── QuarterlyScene.tsx
        ├── TopReposScene.tsx
        └── OutroScene.tsx
```

### 4.2 Dependencies

**Key Packages:**
- `remotion@4.0.0` - Video framework
- `@remotion/cli` - CLI tools
- `@remotion/google-fonts` - Font loading
- `@remotion/media` - Audio support
- `@remotion/transitions` - Scene transitions
- `react@18.2.0` - UI framework

### 4.3 Video Specifications

| Property | Value |
|----------|-------|
| Resolution | 1920 × 1080 (Full HD) |
| Frame Rate | 30 FPS |
| Format | MP4 |
| Font | Poppins (400, 600, 700, 800) |
| Audio | Looping background music |

### 4.4 Scene Structure

| # | Scene | Duration | Description |
|---|-------|----------|-------------|
| 1 | IntroScene | 150 frames (5s) | Year badge, title, username |
| 2 | HeroStatsScene | 240 frames (8s) | 5 stat cards with count-up |
| 3 | FunFactsScene | 240 × N frames | Slideshow of facts (max 5) |
| 4 | BigRocksScene | 210 × N frames | Major achievements (max 5) |
| 5 | QuarterlyScene | 240 frames (8s) | Bar chart by quarter |
| 6 | TopReposScene | 240 frames (8s) | Top 3 repositories |
| 7 | OutroScene | 210 frames (7s) | Summary and sign-off |

**Transitions:**
- 6 transitions between scenes (20 frames each)
- Types: fade, slide (from-right, from-bottom, from-left)

### 4.5 Timing System (`durations.ts`)

```typescript
export const TRANSITION_DURATION = 20;  // frames
export const INTRO_DURATION = 150;      // 5 seconds
export const HERO_STATS_DURATION = 240; // 8 seconds
export const QUARTERLY_DURATION = 240;  // 8 seconds
export const TOP_REPOS_DURATION = 240;  // 8 seconds
export const OUTRO_DURATION = 210;      // 7 seconds
export const FUN_FACT_SLIDE_DURATION = 240;  // per fact
export const BIG_ROCK_SLIDE_DURATION = 210;  // per rock

export function getFunFactsDuration(count: number): number;
export function getBigRocksDuration(count: number): number;
export function calculateTotalDuration(data: VideoData): number;
```

### 4.6 Type Definitions (`types.ts`)

```typescript
interface HeroStats {
  prsMerged: number;
  linesAdded: number;
  linesRemoved: number;
  reviewsGiven: number;
  reposContributed: number;
}

interface FunFact {
  label: string;
  value: string | number;
  detail: string;
}

interface BigRock {
  title: string;
  repo: string;
  impact: string;
  linesChanged: number;
}

interface QuarterActivity {
  quarter: string;  // "Q1", "Q2", "Q3", "Q4"
  prs: number;
  highlights: string[];
}

interface TopRepo {
  name: string;
  prs: number;
  funFact: string;
}

interface YearInReview {
  headline: string;
  tagline: string;
}

interface Meta {
  username: string;
  year: number;
  generatedAt: string;
}

interface VideoData {
  heroStats: HeroStats;
  funFacts: FunFact[];
  bigRocks: BigRock[];
  quarterlyActivity: QuarterActivity[];
  topRepos: TopRepo[];
  yearInReview: YearInReview;
  meta: Meta;
}
```

### 4.7 Scene Components

#### IntroScene
- **Props**: `{ username: string, year: number }`
- **Animations**: Spring-based title entry, year badge, username, subtitle
- **Background**: `intro-bg.png` with zoom effect (1.1 → 1.0)

#### HeroStatsScene
- **Props**: `{ stats: HeroStats }`
- **Sub-component**: `StatCard` with count-up animation
- **Layout**: 5 stat cards in grid
- **Background**: `hero-stats-bg.png`

#### FunFactsScene
- **Props**: `{ funFacts: FunFact[] }`
- **Features**: Slideshow, color-coded badges, progress dots
- **Limit**: Maximum 5 facts displayed
- **Background**: `fun-facts-bg.png`

#### BigRocksScene
- **Props**: `{ bigRocks: BigRock[] }`
- **Features**: Slideshow, dynamic backgrounds based on title
- **Limit**: Maximum 5 rocks displayed
- **Backgrounds**: `async-capsule.png` or `big-rocks-achievement.png`

#### QuarterlyScene
- **Props**: `{ quarters: QuarterActivity[] }`
- **Features**: Animated bar chart, color-coded quarters, total badge
- **Background**: Gradient

#### TopReposScene
- **Props**: `{ repos: TopRepo[] }`
- **Features**: Top 3 repos, #1 crown highlight, staggered animations
- **Background**: `hero-stats-bg.png` (blurred)

#### OutroScene
- **Props**: `{ yearInReview, stats, username, year }`
- **Features**: Headline, tagline, mini stats recap, sign-off
- **Background**: `intro-bg.png` (blurred)

### 4.8 Animation Techniques

**Spring Animations:**
```typescript
spring({
  frame,
  fps: 30,
  config: { damping: 100, stiffness: 200 }
})
```

**Interpolation:**
```typescript
interpolate(frame, [0, 30], [0, 1], {
  extrapolateLeft: 'clamp',
  extrapolateRight: 'clamp'
})
```

**Common Patterns:**
- Entry: Scale (0 → 1) + TranslateY (50 → 0) + Opacity (0 → 1)
- Count-up: Interpolate from 0 to target value
- Fade-out: Opacity interpolation at scene end
- Background zoom: Scale 1.1 → 1.0 over scene duration

### 4.9 Rendering Pipeline

**Development:**
```bash
npm start  # Opens Remotion Studio
```

**Production:**
```bash
npm run build  # Runs render.js
```

**render.js workflow:**
1. Read `src/video-data.json` for username
2. Generate filename: `wrapped-2025-{username}-{timestamp}.mp4`
3. Create `out/` directory
4. Execute: `npx remotion render src/index.ts WrappedVideo {output}`

**Data Validation (prepare-video-data.js):**
- Validates required fields
- Checks data types
- Ensures 4 quarters in `quarterlyActivity`
- Copies validated data to `src/video-data.json`

---

## 5. AI Skills

### 5.1 gpt-image-1-5

**Location**: `.agents/skills/gpt-image-1-5/`

**Purpose**: Generate and edit images using OpenAI's GPT Image model.

**Capabilities:**
- Text-to-image generation
- Image editing with optional masks
- Quality: low, medium, high
- Sizes: 1024x1024, 1024x1536, 1536x1024, auto
- Transparent or opaque backgrounds

**Usage:**
```bash
python generate_image.py "Description of image" --size 1024x1024 --quality high
```

### 5.2 remotion-best-practices

**Location**: `.agents/skills/remotion-best-practices/`

**Purpose**: Domain knowledge for Remotion video creation.

**30+ Rule Files:**
| Category | Files |
|----------|-------|
| Core | compositions, animations, timing, sequencing, transitions |
| Media | assets, images, videos, audio, gifs, lottie |
| Advanced | charts, 3d, maps, text-animations, captions |
| Utilities | get-video-duration, get-audio-duration, measuring-text |
| Config | parameters, calculate-metadata, fonts, tailwind |

---

## 6. Data Structures

### 6.1 Complete Data Flow

```
GitHub API
    │
    ├─► PullRequestData (number, title, body, repo, dates, stats, labels)
    ├─► ReviewData (pr_number, pr_title, submitted_at, state, author)
    └─► CommitData (sha, message, repo, date, additions, deletions)
           │
           ▼
    ContributionData (container)
           │
           ├─► Categorizer ─► CategorizedData ─► ReportGenerator ─► Markdown
           │
           └─► LLMReportGenerator
                    │
                    ├─► ContributionSummary ─► OpenAI ─► Markdown
                    │
                    └─► VideoData JSON
                              │
                              ▼
                    prepare-video-data.js
                              │
                              ▼
                    src/video-data.json
                              │
                              ▼
                    Remotion ─► MP4 Video
```

### 6.2 JSON Schema: Video Data

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["heroStats", "funFacts", "bigRocks", "quarterlyActivity", "topRepos", "yearInReview", "meta"],
  "properties": {
    "heroStats": {
      "type": "object",
      "required": ["prsMerged", "linesAdded", "linesRemoved", "reviewsGiven", "reposContributed"],
      "properties": {
        "prsMerged": { "type": "integer" },
        "linesAdded": { "type": "integer" },
        "linesRemoved": { "type": "integer" },
        "reviewsGiven": { "type": "integer" },
        "reposContributed": { "type": "integer" }
      }
    },
    "funFacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["label", "value", "detail"],
        "properties": {
          "label": { "type": "string" },
          "value": { "type": ["string", "number"] },
          "detail": { "type": "string" }
        }
      }
    },
    "bigRocks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "repo", "impact", "linesChanged"],
        "properties": {
          "title": { "type": "string" },
          "repo": { "type": "string" },
          "impact": { "type": "string" },
          "linesChanged": { "type": "integer" }
        }
      }
    },
    "quarterlyActivity": {
      "type": "array",
      "minItems": 4,
      "maxItems": 4,
      "items": {
        "type": "object",
        "required": ["quarter", "prs", "highlights"],
        "properties": {
          "quarter": { "type": "string", "enum": ["Q1", "Q2", "Q3", "Q4"] },
          "prs": { "type": "integer" },
          "highlights": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "topRepos": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "prs", "funFact"],
        "properties": {
          "name": { "type": "string" },
          "prs": { "type": "integer" },
          "funFact": { "type": "string" }
        }
      }
    },
    "yearInReview": {
      "type": "object",
      "required": ["headline", "tagline"],
      "properties": {
        "headline": { "type": "string" },
        "tagline": { "type": "string" }
      }
    },
    "meta": {
      "type": "object",
      "required": ["username", "year", "generatedAt"],
      "properties": {
        "username": { "type": "string" },
        "year": { "type": "integer" },
        "generatedAt": { "type": "string", "format": "date-time" }
      }
    }
  }
}
```

---

## 7. Environment Configuration

### 7.1 Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI reports |
| `GITHUB_TOKEN` | No | GitHub PAT (uses Device Flow if not set) |

### 7.2 GitHub Token Scopes

If using `GITHUB_TOKEN`, required scopes:
- `repo` - Full repository access
- `read:org` - Read organization data
- `read:user` - Read user profile

### 7.3 .env.example

```bash
# OpenAI API Key (required for AI-generated reports)
# Get at: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-...

# GitHub Personal Access Token (optional)
# If not provided, uses OAuth Device Flow for authentication
# Required scopes: repo, read:org, read:user
# Get at: https://github.com/settings/tokens
GITHUB_TOKEN=ghp_...
```

---

## 8. Build Commands

### 8.1 Makefile Targets

| Command | Description |
|---------|-------------|
| `make run username=<user>` | Full pipeline: collect → prepare → render |
| `make collect username=<user>` | Collect GitHub data and generate AI analysis |
| `make prepare file=<path>` | Prepare video data from JSON |
| `make render` | Render final video |

### 8.2 NPM Scripts (wrapped-video)

| Command | Description |
|---------|-------------|
| `npm start` | Open Remotion Studio for preview |
| `npm run build` | Render video (runs render.js) |
| `npm run prepare-data` | Validate and copy video data |

### 8.3 Python CLI

```bash
# Full command with all options
python -m github_wrapped \
    --orgs cloudinary \
    --repos optional-filter \
    --year 2025 \
    --output-dir output \
    --use-ai \
    --openai-model gpt-5.2 \
    --fetch-commits \
    --save-data \
    --github-username display-name
```

---

## 9. Dependencies

### 9.1 Python (requirements.txt)

```
PyGithub>=2.1.1
typer>=0.9.0
python-dotenv>=1.0.0
rich>=13.7.0
requests>=2.31.0
openai>=1.0.0
```

### 9.2 Node.js (package.json)

```json
{
  "dependencies": {
    "@remotion/cli": "4.0.0",
    "@remotion/google-fonts": "4.0.0",
    "@remotion/media": "4.0.0",
    "@remotion/transitions": "4.0.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "remotion": "4.0.0"
  },
  "devDependencies": {
    "@types/react": "18.2.0",
    "typescript": "5.2.2"
  }
}
```

---

## 10. File Structure

```
cloudinary-wrapped/
├── .agents/
│   └── skills/
│       ├── gpt-image-1-5/
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       └── generate_image.py
│       └── remotion-best-practices/
│           ├── SKILL.md
│           └── rules/
│               ├── 3d.md
│               ├── animations.md
│               ├── assets.md
│               ├── audio.md
│               ├── calculate-metadata.md
│               ├── can-decode.md
│               ├── charts.md
│               ├── compositions.md
│               ├── display-captions.md
│               ├── extract-frames.md
│               ├── fonts.md
│               ├── get-audio-duration.md
│               ├── get-video-dimensions.md
│               ├── get-video-duration.md
│               ├── gifs.md
│               ├── images.md
│               ├── import-srt-captions.md
│               ├── lottie.md
│               ├── maps.md
│               ├── measuring-dom-nodes.md
│               ├── measuring-text.md
│               ├── parameters.md
│               ├── sequencing.md
│               ├── tailwind.md
│               ├── text-animations.md
│               ├── timing.md
│               ├── transcribe-captions.md
│               ├── transitions.md
│               ├── trimming.md
│               └── videos.md
├── .env.example
├── .gitignore
├── github_wrapped/
│   ├── __init__.py
│   ├── __main__.py
│   ├── categorizer.py
│   ├── cli.py
│   ├── data_fetcher.py
│   ├── device_auth.py
│   ├── github_client.py
│   ├── llm_report_generator.py
│   └── report_generator.py
├── Makefile
├── output/
│   └── .gitkeep
├── README.md
├── requirements.txt
└── wrapped-video/
    ├── package.json
    ├── package-lock.json
    ├── prepare-video-data.js
    ├── public/
    │   ├── async-capsule.png
    │   ├── background-music.mp3
    │   ├── big-rocks-achievement.png
    │   ├── captain-crash.png
    │   ├── fun-facts-bg.png
    │   ├── hero-stats-bg.png
    │   └── intro-bg.png
    ├── remotion.config.ts
    ├── render.js
    ├── src/
    │   ├── durations.ts
    │   ├── index.ts
    │   ├── Root.tsx
    │   ├── scenes/
    │   │   ├── BigRocksScene.tsx
    │   │   ├── FunFactsScene.tsx
    │   │   ├── HeroStatsScene.tsx
    │   │   ├── IntroScene.tsx
    │   │   ├── OutroScene.tsx
    │   │   ├── QuarterlyScene.tsx
    │   │   └── TopReposScene.tsx
    │   ├── types.ts
    │   ├── video-data.json
    │   └── WrappedVideo.tsx
    └── tsconfig.json
```

---

## Summary

The cloudinary-wrapped project is a comprehensive GitHub contribution visualization tool that:

1. **Collects** GitHub data via GraphQL API with OAuth Device Flow support
2. **Categorizes** pull requests using keyword-based rules
3. **Identifies** major achievements ("big rocks")
4. **Generates** narrative reports using OpenAI
5. **Renders** animated videos using Remotion

The architecture cleanly separates:
- **Data layer**: Python backend for fetching and processing
- **Presentation layer**: React/Remotion frontend for visualization
- **AI layer**: OpenAI integration for insights and narratives

This documentation serves as the baseline for understanding the original project before modifications.
