import React from 'react';
import {Composition} from 'remotion';
import {WrappedVideo} from './WrappedVideo';
import type {VideoData} from './types';
import videoData from './video-data.json';
import {calculateTotalDuration} from './durations';

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
