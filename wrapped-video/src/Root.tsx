import React from 'react';
import {Composition} from 'remotion';
import {WrappedVideo} from './WrappedVideo';
import type {VideoData} from './types';
import videoData from './video-data.json';

// Calculate total duration based on video data
const calculateTotalDuration = (data: VideoData): number => {
  const TRANSITION_DURATION = 20;
  const NUM_TRANSITIONS = 6;
  
  const INTRO_DURATION = 120;
  const HERO_STATS_DURATION = 180;
  const FUN_FACTS_DURATION = 120 * Math.min(data.funFacts.length, 5);
  const BIG_ROCKS_DURATION = 150 * Math.min(data.bigRocks.length, 5);
  const QUARTERLY_DURATION = 180;
  const TOP_REPOS_DURATION = 180;
  const OUTRO_DURATION = 180;
  
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

export const RemotionRoot: React.FC = () => {
  const data = videoData as VideoData;
  const totalDuration = calculateTotalDuration(data);

  return (
    <>
      <Composition
        id="WrappedVideo"
        component={WrappedVideo}
        durationInFrames={totalDuration}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          data,
        }}
      />
    </>
  );
};
