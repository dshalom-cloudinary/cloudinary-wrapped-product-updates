# GitHub Wrapped

Generate a personalized "Spotify Wrapped"-style video from your GitHub contributions. Fetches your GitHub data, creates an AI-powered analysis, and renders an animated video showcasing your year in code.

## Features

- **GitHub Data Collection**: Fetches PRs, reviews, commits, and contribution patterns
- **AI-Powered Analysis**: Uses OpenAI to identify your "big rocks" (major accomplishments) and generate insights
- **Animated Video**: Renders a Remotion-powered video with stats, charts, and achievements
- **Customizable**: Personalized with your name, avatar, and actual contribution data

## Quick Start

```bash
# 1. Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd wrapped-video && npm install && cd ..
cp .env.example .env  # Add your GITHUB_TOKEN and OPENAI_API_KEY

# 2. Generate everything (collect data + render video)
make run username=your-github-username

# Video output: wrapped-video/out/wrapped-video.mp4
```

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- OpenAI API Key
- GitHub Personal Access Token (optional - will use device auth flow if not provided)

### Installation

1. Clone and install Python dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Install video dependencies:
   ```bash
   cd wrapped-video && npm install
   ```

3. Configure `.env`:
   ```bash
   cp .env.example .env
   # Edit .env with your OPENAI_API_KEY (required)
   # GITHUB_TOKEN is optional - if not set, you'll authenticate via browser
   ```

## Usage

### Full Pipeline (Recommended)

```bash
make run username=your-github-username
```

This runs the complete pipeline: collect GitHub data → prepare video data → render video.

### Individual Steps

```bash
# Step 1: Collect GitHub data and generate AI analysis
make collect username=your-github-username

# Step 2: Prepare data for video rendering
make prepare file=output/video-data-2025-01-29.json

# Step 3: Render the video
make render
```

### Preview in Browser

```bash
cd wrapped-video && npm start
```

Opens Remotion Studio to preview and edit scenes before rendering.

## Project Structure

```
├── github_wrapped/      # Python CLI for data collection
│   ├── data_fetcher.py  # GitHub API integration
│   ├── categorizer.py   # PR categorization logic
│   └── llm_report_generator.py  # AI analysis
├── wrapped-video/       # Remotion video project
│   ├── src/scenes/      # Video scene components
│   └── public/          # Static assets (images, audio)
├── output/              # Generated data files
└── Makefile             # Build automation
```

## Privacy

- All data stays between you, GitHub, and OpenAI
- No data is stored or sent elsewhere
- Generated videos are saved locally
