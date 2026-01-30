import type {VideoData, SlackVideoData, ContentAnalysis} from './types';

// Transition settings
export const TRANSITION_DURATION = 20;
export const NUM_TRANSITIONS = 6;

// Scene durations in frames (at 30fps)
export const INTRO_DURATION = 150; // 5 seconds
export const HERO_STATS_DURATION = 240; // 8 seconds
export const QUARTERLY_DURATION = 240; // 8 seconds
export const TOP_REPOS_DURATION = 240; // 8 seconds
export const OUTRO_DURATION = 210; // 7 seconds

// Per-slide durations
export const FUN_FACT_SLIDE_DURATION = 240; // 8 seconds per fact at 30fps
export const BIG_ROCK_SLIDE_DURATION = 210; // 7 seconds per rock at 30fps

// Content Analysis scene durations (at 30fps)
export const YEAR_STORY_PART_DURATION = 120; // 4 seconds per story part
export const QUOTE_DURATION = 120; // 4 seconds per quote
export const TOPIC_DURATION = 150; // 5 seconds per topic

// Dynamic durations based on data
export const getFunFactsDuration = (funFactsCount: number): number => {
  return FUN_FACT_SLIDE_DURATION * Math.min(funFactsCount, 5);
};

export const getBigRocksDuration = (bigRocksCount: number): number => {
  return BIG_ROCK_SLIDE_DURATION * Math.min(bigRocksCount, 5);
};

// Content Analysis scene durations
export const getYearStoryDuration = (): number => {
  // 4 parts: opening, arc, climax, closing
  return YEAR_STORY_PART_DURATION * 4;
};

export const getBestQuotesDuration = (quotesCount: number): number => {
  return QUOTE_DURATION * Math.min(quotesCount, 4);
};

export const getTopicHighlightsDuration = (topicsCount: number): number => {
  return TOPIC_DURATION * Math.min(topicsCount, 5);
};

export const getContentAnalysisDuration = (contentAnalysis?: ContentAnalysis): number => {
  if (!contentAnalysis) return 0;
  
  let duration = 0;
  
  // Year story
  if (contentAnalysis.yearStory) {
    duration += getYearStoryDuration();
  }
  
  // Topic highlights
  if (contentAnalysis.topicHighlights.length > 0) {
    duration += getTopicHighlightsDuration(contentAnalysis.topicHighlights.length);
  }
  
  // Best quotes
  if (contentAnalysis.bestQuotes.length > 0) {
    duration += getBestQuotesDuration(contentAnalysis.bestQuotes.length);
  }
  
  return duration;
};

// Calculate total duration based on video data
export const calculateTotalDuration = (data: VideoData): number => {
  const FUN_FACTS_DURATION = getFunFactsDuration(data.funFacts.length);
  const BIG_ROCKS_DURATION = getBigRocksDuration(data.bigRocks.length);

  const totalSceneDuration = 
    INTRO_DURATION + 
    HERO_STATS_DURATION + 
    FUN_FACTS_DURATION + 
    BIG_ROCKS_DURATION + 
    QUARTERLY_DURATION + 
    TOP_REPOS_DURATION + 
    OUTRO_DURATION;

  // Subtract overlap from transitions
  return totalSceneDuration - (TRANSITION_DURATION * NUM_TRANSITIONS);
};

// Calculate total duration for Slack video with content analysis
export const calculateSlackTotalDuration = (data: SlackVideoData): number => {
  const FUN_FACTS_DURATION = getFunFactsDuration(data.funFacts.length);
  const CONTENT_ANALYSIS_DURATION = getContentAnalysisDuration(data.contentAnalysis);
  
  // Base transitions: Intro -> Hero -> FunFacts -> Quarterly -> TopRepos -> Outro = 5 transitions
  // With content analysis, add transitions for each enabled scene:
  // - yearStory adds 1 transition
  // - topicHighlights adds 1 transition  
  // - bestQuotes adds 1 transition
  let numTransitions = 5; // Base transitions between core scenes
  
  if (data.contentAnalysis) {
    if (data.contentAnalysis.yearStory) {
      numTransitions += 1;
    }
    if (data.contentAnalysis.topicHighlights.length > 0) {
      numTransitions += 1;
    }
    if (data.contentAnalysis.bestQuotes.length > 0) {
      numTransitions += 1;
    }
  }

  const totalSceneDuration = 
    INTRO_DURATION + 
    HERO_STATS_DURATION + 
    CONTENT_ANALYSIS_DURATION +  // New content scenes
    FUN_FACTS_DURATION + 
    QUARTERLY_DURATION + 
    TOP_REPOS_DURATION + 
    OUTRO_DURATION;

  // Subtract overlap from transitions
  return totalSceneDuration - (TRANSITION_DURATION * numTransitions);
};
