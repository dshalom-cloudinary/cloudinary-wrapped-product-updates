import type {VideoData} from './types';

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

// Dynamic durations based on data
export const getFunFactsDuration = (funFactsCount: number): number => {
  return FUN_FACT_SLIDE_DURATION * Math.min(funFactsCount, 5);
};

export const getBigRocksDuration = (bigRocksCount: number): number => {
  return BIG_ROCK_SLIDE_DURATION * Math.min(bigRocksCount, 5);
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
