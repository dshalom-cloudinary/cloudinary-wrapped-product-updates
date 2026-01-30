import React from 'react';
import {Composition} from 'remotion';
import {WrappedVideo} from './WrappedVideo';
import {SlackWrappedVideo} from './SlackWrappedVideo';
import type {VideoData, SlackVideoData} from './types';
import videoData from './video-data.json';
import {calculateTotalDuration, calculateSlackTotalDuration} from './durations';

// Type guard to check if data is SlackVideoData
const isSlackVideoData = (data: VideoData | SlackVideoData): data is SlackVideoData => {
  return 'channelStats' in data && 'topContributors' in data;
};

export const RemotionRoot: React.FC = () => {
  // Type assertion to unknown first to avoid overlap errors
  const rawData = videoData as unknown;
  
  // Check if this is Slack data or GitHub data
  if (isSlackVideoData(rawData as VideoData | SlackVideoData)) {
    const slackData = rawData as SlackVideoData;
    const totalDuration = calculateSlackTotalDuration(slackData);
    
    return (
      <>
        <Composition
          id="SlackWrappedVideo"
          component={SlackWrappedVideo}
          durationInFrames={totalDuration}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            data: slackData,
          }}
        />
      </>
    );
  }
  
  // Legacy GitHub data
  const data = rawData as VideoData;
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
