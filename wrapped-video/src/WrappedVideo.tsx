import React from 'react';
import {AbsoluteFill, staticFile, useVideoConfig, interpolate} from 'remotion';
import {Audio} from '@remotion/media';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';

import {IntroScene} from './scenes/IntroScene';
import {HeroStatsScene} from './scenes/HeroStatsScene';
import {FunFactsScene} from './scenes/FunFactsScene';
import {BigRocksScene} from './scenes/BigRocksScene';
import {QuarterlyScene} from './scenes/QuarterlyScene';
import {TopReposScene} from './scenes/TopReposScene';
import {OutroScene} from './scenes/OutroScene';
import type {VideoData} from './types';
import {
  TRANSITION_DURATION,
  INTRO_DURATION,
  HERO_STATS_DURATION,
  QUARTERLY_DURATION,
  TOP_REPOS_DURATION,
  OUTRO_DURATION,
  getFunFactsDuration,
  getBigRocksDuration,
} from './durations';

type WrappedVideoProps = {
  data: VideoData;
};

export const WrappedVideo: React.FC<WrappedVideoProps> = ({data}) => {
  const {fps, durationInFrames} = useVideoConfig();
  
  // Dynamic durations based on data
  const FUN_FACTS_DURATION = getFunFactsDuration(data.funFacts.length);
  const BIG_ROCKS_DURATION = getBigRocksDuration(data.bigRocks.length);

  // Volume control for background music with fade in/out
  const volumeCallback = (frame: number) => {
    const fadeInDuration = fps * 2; // 2 second fade in
    const fadeOutStart = durationInFrames - fps * 3; // Start fade out 3 seconds before end
    
    // Fade in at the start
    if (frame < fadeInDuration) {
      return interpolate(frame, [0, fadeInDuration], [0, 0.4], {
        extrapolateRight: 'clamp',
      });
    }
    
    // Fade out at the end
    if (frame > fadeOutStart) {
      return interpolate(frame, [fadeOutStart, durationInFrames], [0.4, 0], {
        extrapolateLeft: 'clamp',
      });
    }
    
    // Normal volume
    return 0.4;
  };

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a1a'}}>
      {/* Background Music */}
      <Audio
        src={staticFile('background-music.mp3')}
        volume={volumeCallback}
        loop
      />
      <TransitionSeries>
        {/* Intro */}
        <TransitionSeries.Sequence durationInFrames={INTRO_DURATION}>
          <IntroScene 
            username={data.meta.username ?? 'user'} 
            year={data.meta.year} 
          />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Hero Stats */}
        <TransitionSeries.Sequence durationInFrames={HERO_STATS_DURATION}>
          <HeroStatsScene stats={data.heroStats} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({direction: 'from-right'})}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Fun Facts */}
        <TransitionSeries.Sequence durationInFrames={FUN_FACTS_DURATION}>
          <FunFactsScene funFacts={data.funFacts} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Big Rocks */}
        <TransitionSeries.Sequence durationInFrames={BIG_ROCKS_DURATION}>
          <BigRocksScene bigRocks={data.bigRocks} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({direction: 'from-bottom'})}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Quarterly Activity */}
        <TransitionSeries.Sequence durationInFrames={QUARTERLY_DURATION}>
          <QuarterlyScene quarters={data.quarterlyActivity} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({direction: 'from-left'})}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Top Repos */}
        <TransitionSeries.Sequence durationInFrames={TOP_REPOS_DURATION}>
          <TopReposScene repos={data.topRepos} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Outro */}
        <TransitionSeries.Sequence durationInFrames={OUTRO_DURATION}>
          <OutroScene
            yearInReview={data.yearInReview}
            stats={data.heroStats}
            username={data.meta.username ?? 'user'}
            year={data.meta.year}
          />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
