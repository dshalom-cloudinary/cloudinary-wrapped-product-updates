import React from 'react';
import {AbsoluteFill, staticFile, useVideoConfig, interpolate} from 'remotion';
import {Audio} from '@remotion/media';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';

import {SlackIntroScene} from './scenes/SlackIntroScene';
import {ChannelStatsScene} from './scenes/ChannelStatsScene';
import {FunFactsScene} from './scenes/FunFactsScene';
import {SlackQuarterlyScene} from './scenes/SlackQuarterlyScene';
import {TopContributorsScene} from './scenes/TopContributorsScene';
import {SpotlightScene} from './scenes/SpotlightScene';
import {SlackOutroScene} from './scenes/SlackOutroScene';
import {YearStoryScene} from './scenes/YearStoryScene';
import {TopicHighlightsScene} from './scenes/TopicHighlightsScene';
import {BestQuoteScene} from './scenes/BestQuoteScene';
import type {SlackVideoData} from './types';
import {
  TRANSITION_DURATION,
  INTRO_DURATION,
  CHANNEL_STATS_DURATION,
  QUARTERLY_DURATION,
  TOP_CONTRIBUTORS_DURATION,
  OUTRO_DURATION,
  getFunFactsDuration,
  getSpotlightDuration,
  getYearStoryDuration,
  getTopicHighlightsDuration,
  getBestQuotesDuration,
} from './durations';

type SlackWrappedVideoProps = {
  data: SlackVideoData;
};

export const SlackWrappedVideo: React.FC<SlackWrappedVideoProps> = ({data}) => {
  const {fps, durationInFrames} = useVideoConfig();
  
  // Dynamic durations based on data
  const FUN_FACTS_DURATION = getFunFactsDuration(data.funFacts.length);
  const SPOTLIGHT_DURATION = data.topContributors 
    ? getSpotlightDuration(data.topContributors.length) 
    : 0;

  // Content analysis durations
  const hasYearStory = data.contentAnalysis?.yearStory;
  const hasTopics = data.contentAnalysis?.topicHighlights && data.contentAnalysis.topicHighlights.length > 0;
  const hasQuotes = data.contentAnalysis?.bestQuotes && data.contentAnalysis.bestQuotes.length > 0;
  
  const YEAR_STORY_DURATION = hasYearStory ? getYearStoryDuration() : 0;
  const TOPICS_DURATION = hasTopics ? getTopicHighlightsDuration(data.contentAnalysis!.topicHighlights.length) : 0;
  const QUOTES_DURATION = hasQuotes ? getBestQuotesDuration(data.contentAnalysis!.bestQuotes.length) : 0;

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
          <SlackIntroScene 
            channelName={data.meta.channelName} 
            year={data.meta.year} 
          />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Channel Stats */}
        <TransitionSeries.Sequence durationInFrames={CHANNEL_STATS_DURATION}>
          <ChannelStatsScene stats={data.channelStats} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({direction: 'from-right'})}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Year Story (if available) */}
        {hasYearStory && (
          <>
            <TransitionSeries.Sequence durationInFrames={YEAR_STORY_DURATION}>
              <YearStoryScene yearStory={data.contentAnalysis!.yearStory!} />
            </TransitionSeries.Sequence>

            <TransitionSeries.Transition
              presentation={fade()}
              timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
            />
          </>
        )}

        {/* Topic Highlights (if available) */}
        {hasTopics && (
          <>
            <TransitionSeries.Sequence durationInFrames={TOPICS_DURATION}>
              <TopicHighlightsScene topics={data.contentAnalysis!.topicHighlights} />
            </TransitionSeries.Sequence>

            <TransitionSeries.Transition
              presentation={slide({direction: 'from-bottom'})}
              timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
            />
          </>
        )}

        {/* Best Quotes (if available) */}
        {hasQuotes && (
          <>
            <TransitionSeries.Sequence durationInFrames={QUOTES_DURATION}>
              <BestQuoteScene quotes={data.contentAnalysis!.bestQuotes} />
            </TransitionSeries.Sequence>

            <TransitionSeries.Transition
              presentation={fade()}
              timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
            />
          </>
        )}

        {/* Fun Facts */}
        <TransitionSeries.Sequence durationInFrames={FUN_FACTS_DURATION}>
          <FunFactsScene funFacts={data.funFacts} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Quarterly Activity */}
        <TransitionSeries.Sequence durationInFrames={QUARTERLY_DURATION}>
          <SlackQuarterlyScene quarters={data.quarterlyActivity} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={slide({direction: 'from-left'})}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Top Contributors */}
        <TransitionSeries.Sequence durationInFrames={TOP_CONTRIBUTORS_DURATION}>
          <TopContributorsScene contributors={data.topContributors} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
        />

        {/* Contributor Spotlights */}
        {SPOTLIGHT_DURATION > 0 && (
          <>
            <TransitionSeries.Sequence durationInFrames={SPOTLIGHT_DURATION}>
              <SpotlightScene contributors={data.topContributors} />
            </TransitionSeries.Sequence>

            <TransitionSeries.Transition
              presentation={fade()}
              timing={linearTiming({durationInFrames: TRANSITION_DURATION})}
            />
          </>
        )}

        {/* Outro */}
        <TransitionSeries.Sequence durationInFrames={OUTRO_DURATION}>
          <SlackOutroScene
            channelName={data.meta.channelName}
            year={data.meta.year}
            stats={data.channelStats}
          />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
