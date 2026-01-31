#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// ============================================
// LEGACY GITHUB SCHEMA
// ============================================

const GITHUB_REQUIRED_FIELDS = [
  'heroStats',
  'funFacts',
  'bigRocks',
  'quarterlyActivity',
  'topRepos',
  'yearInReview',
  'meta'
];

const HERO_STATS_FIELDS = [
  'prsMerged',
  'linesAdded',
  'linesRemoved',
  'reviewsGiven',
  'repositoriesContributed'
];

const GITHUB_META_FIELDS = ['username', 'year', 'generatedAt'];

// ============================================
// SLACK WRAPPED SCHEMA
// ============================================

const SLACK_REQUIRED_FIELDS = [
  'channelStats',
  'quarterlyActivity',
  'topContributors',
  'funFacts',
  'insights',
  'meta'
];

const CHANNEL_STATS_FIELDS = [
  'totalMessages',
  'totalWords',
  'totalContributors',
  'activeDays'
];

const SLACK_META_FIELDS = ['channelName', 'year', 'generatedAt'];

// ============================================
// DETECT DATA TYPE
// ============================================

function isSlackData(data) {
  return 'channelStats' in data && 'topContributors' in data;
}

// ============================================
// SLACK VALIDATION
// ============================================

function validateSlackVideoData(data) {
  const errors = [];

  // Check top-level required fields
  for (const field of SLACK_REQUIRED_FIELDS) {
    if (!(field in data)) {
      errors.push(`Missing required field: ${field}`);
    }
  }

  // Validate channelStats
  if (data.channelStats) {
    for (const field of CHANNEL_STATS_FIELDS) {
      if (!(field in data.channelStats)) {
        errors.push(`Missing channelStats.${field}`);
      }
    }
  }

  // Validate funFacts is an array with items
  if (data.funFacts) {
    if (!Array.isArray(data.funFacts)) {
      errors.push('funFacts must be an array');
    } else {
      data.funFacts.forEach((fact, i) => {
        if (!fact.label) errors.push(`funFacts[${i}] missing label`);
        if (fact.value === undefined) errors.push(`funFacts[${i}] missing value`);
        if (!fact.detail) errors.push(`funFacts[${i}] missing detail`);
      });
    }
  }

  // Validate quarterlyActivity
  if (data.quarterlyActivity) {
    if (!Array.isArray(data.quarterlyActivity)) {
      errors.push('quarterlyActivity must be an array');
    } else if (data.quarterlyActivity.length !== 4) {
      errors.push(`quarterlyActivity should have 4 quarters, found ${data.quarterlyActivity.length}`);
    } else {
      data.quarterlyActivity.forEach((q, i) => {
        if (!q.quarter) errors.push(`quarterlyActivity[${i}] missing quarter`);
        if (q.messages === undefined && q.prs === undefined) {
          errors.push(`quarterlyActivity[${i}] missing messages`);
        }
        if (!q.highlights) errors.push(`quarterlyActivity[${i}] missing highlights`);
      });
    }
  }

  // Validate topContributors
  if (data.topContributors) {
    if (!Array.isArray(data.topContributors)) {
      errors.push('topContributors must be an array');
    } else if (data.topContributors.length === 0) {
      errors.push('topContributors array is empty');
    } else {
      data.topContributors.forEach((c, i) => {
        if (!c.username) errors.push(`topContributors[${i}] missing username`);
        if (!c.displayName) errors.push(`topContributors[${i}] missing displayName`);
        if (c.messageCount === undefined) errors.push(`topContributors[${i}] missing messageCount`);
        if (c.contributionPercent === undefined) errors.push(`topContributors[${i}] missing contributionPercent`);
      });
    }
  }

  // Validate insights
  if (data.insights) {
    if (typeof data.insights !== 'object') {
      errors.push('insights must be an object');
    }
  }

  // Validate meta
  if (data.meta) {
    for (const field of SLACK_META_FIELDS) {
      if (!(field in data.meta)) {
        errors.push(`Missing meta.${field}`);
      }
    }
  }

  // Validate contentAnalysis (optional)
  if (data.contentAnalysis) {
    if (data.contentAnalysis.topicHighlights && !Array.isArray(data.contentAnalysis.topicHighlights)) {
      errors.push('contentAnalysis.topicHighlights must be an array');
    }
    if (data.contentAnalysis.bestQuotes && !Array.isArray(data.contentAnalysis.bestQuotes)) {
      errors.push('contentAnalysis.bestQuotes must be an array');
    }
    if (data.contentAnalysis.personalityTypes && !Array.isArray(data.contentAnalysis.personalityTypes)) {
      errors.push('contentAnalysis.personalityTypes must be an array');
    }
  }

  return errors;
}

// ============================================
// GITHUB VALIDATION (Legacy)
// ============================================

function validateGitHubVideoData(data) {
  const errors = [];

  // Check top-level required fields
  for (const field of GITHUB_REQUIRED_FIELDS) {
    if (!(field in data)) {
      errors.push(`Missing required field: ${field}`);
    }
  }

  // Validate heroStats
  if (data.heroStats) {
    for (const field of HERO_STATS_FIELDS) {
      if (!(field in data.heroStats)) {
        errors.push(`Missing heroStats.${field}`);
      }
    }
  }

  // Validate funFacts is an array with items
  if (data.funFacts) {
    if (!Array.isArray(data.funFacts)) {
      errors.push('funFacts must be an array');
    } else if (data.funFacts.length === 0) {
      errors.push('funFacts array is empty');
    } else {
      data.funFacts.forEach((fact, i) => {
        if (!fact.label) errors.push(`funFacts[${i}] missing label`);
        if (fact.value === undefined) errors.push(`funFacts[${i}] missing value`);
        if (!fact.detail) errors.push(`funFacts[${i}] missing detail`);
      });
    }
  }

  // Validate bigRocks is an array with items
  if (data.bigRocks) {
    if (!Array.isArray(data.bigRocks)) {
      errors.push('bigRocks must be an array');
    } else if (data.bigRocks.length === 0) {
      errors.push('bigRocks array is empty');
    } else {
      data.bigRocks.forEach((rock, i) => {
        if (!rock.title) errors.push(`bigRocks[${i}] missing title`);
        if (!rock.repo) errors.push(`bigRocks[${i}] missing repo`);
        if (!rock.impact) errors.push(`bigRocks[${i}] missing impact`);
        if (rock.linesChanged === undefined) errors.push(`bigRocks[${i}] missing linesChanged`);
      });
    }
  }

  // Validate quarterlyActivity
  if (data.quarterlyActivity) {
    if (!Array.isArray(data.quarterlyActivity)) {
      errors.push('quarterlyActivity must be an array');
    } else if (data.quarterlyActivity.length !== 4) {
      errors.push(`quarterlyActivity should have 4 quarters, found ${data.quarterlyActivity.length}`);
    } else {
      data.quarterlyActivity.forEach((q, i) => {
        if (!q.quarter) errors.push(`quarterlyActivity[${i}] missing quarter`);
        if (q.prs === undefined) errors.push(`quarterlyActivity[${i}] missing prs`);
        if (!q.highlights) errors.push(`quarterlyActivity[${i}] missing highlights`);
      });
    }
  }

  // Validate topRepos
  if (data.topRepos) {
    if (!Array.isArray(data.topRepos)) {
      errors.push('topRepos must be an array');
    } else if (data.topRepos.length === 0) {
      errors.push('topRepos array is empty');
    } else {
      data.topRepos.forEach((repo, i) => {
        if (!repo.name) errors.push(`topRepos[${i}] missing name`);
        if (repo.prs === undefined) errors.push(`topRepos[${i}] missing prs`);
        if (!repo.funFact) errors.push(`topRepos[${i}] missing funFact`);
      });
    }
  }

  // Validate yearInReview
  if (data.yearInReview) {
    if (!data.yearInReview.headline) errors.push('yearInReview missing headline');
    if (!data.yearInReview.tagline) errors.push('yearInReview missing tagline');
  }

  // Validate meta
  if (data.meta) {
    for (const field of GITHUB_META_FIELDS) {
      if (!(field in data.meta)) {
        errors.push(`Missing meta.${field}`);
      }
    }
  }

  return errors;
}

// ============================================
// UNIFIED VALIDATION
// ============================================

function validateVideoData(data) {
  if (isSlackData(data)) {
    return validateSlackVideoData(data);
  }
  return validateGitHubVideoData(data);
}

function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.error('Usage: npm run prepare-data <path-to-video-data.json>');
    console.error('Example: npm run prepare-data ../output/video-data-2025-1769602059.json');
    process.exit(1);
  }

  const inputPath = args[0];
  const outputPath = path.join(__dirname, 'src', 'video-data.json');

  // Check if input file exists
  if (!fs.existsSync(inputPath)) {
    console.error(`Error: Input file not found: ${inputPath}`);
    process.exit(1);
  }

  // Read and parse the JSON
  let data;
  try {
    const content = fs.readFileSync(inputPath, 'utf-8');
    data = JSON.parse(content);
  } catch (err) {
    console.error(`Error: Failed to parse JSON: ${err.message}`);
    process.exit(1);
  }

  // Validate the data
  const errors = validateVideoData(data);
  if (errors.length > 0) {
    console.error('Validation failed with the following errors:');
    errors.forEach(err => console.error(`  - ${err}`));
    process.exit(1);
  }

  // Copy to destination
  try {
    fs.writeFileSync(outputPath, JSON.stringify(data, null, 2));
    // Handle both Slack and GitHub data types
    const identifier = isSlackData(data) 
      ? `#${data.meta.channelName}` 
      : data.meta.username;
    const dataType = isSlackData(data) ? 'Slack' : 'GitHub';
    console.log(`✓ Validated and copied ${dataType} video data for ${identifier} (${data.meta.year})`);
    console.log(`  → ${outputPath}`);
  } catch (err) {
    console.error(`Error: Failed to write output file: ${err.message}`);
    process.exit(1);
  }
}

main();
