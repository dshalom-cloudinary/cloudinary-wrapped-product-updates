import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Poppins';
import type {YearStory} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type StoryPartProps = {
  part: string;
  label: string;
  emoji: string;
  color: string;
};

const StoryPart: React.FC<StoryPartProps> = ({part, label, emoji, color}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: {damping: 80, stiffness: 100},
  });

  // Text reveal
  const textReveal = interpolate(
    frame,
    [15, 45],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  // Fade out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily,
        opacity: fadeOut,
      }}
    >
      {/* Background gradient */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(135deg, #0f0f23 0%, ${color}20 50%, #1a1a2e 100%)`,
        }}
      />

      {/* Floating emoji */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          fontSize: 80,
          transform: `scale(${entryProgress}) rotate(${interpolate(frame, [0, 120], [0, 10])}deg)`,
          opacity: entryProgress * 0.5,
        }}
      >
        {emoji}
      </div>

      {/* Content card */}
      <div
        style={{
          transform: `translateY(${interpolate(entryProgress, [0, 1], [60, 0])}px)`,
          opacity: entryProgress,
          maxWidth: 1000,
          textAlign: 'center',
          padding: 60,
        }}
      >
        {/* Label badge */}
        <div
          style={{
            display: 'inline-block',
            background: `linear-gradient(135deg, ${color} 0%, ${color}cc 100%)`,
            padding: '12px 36px',
            borderRadius: 30,
            fontSize: 20,
            fontWeight: 700,
            color: 'white',
            marginBottom: 40,
            letterSpacing: 2,
            textTransform: 'uppercase',
          }}
        >
          {label}
        </div>

        {/* Story text */}
        <p
          style={{
            fontSize: 48,
            fontWeight: 600,
            color: 'white',
            lineHeight: 1.4,
            margin: 0,
            opacity: textReveal,
            transform: `translateY(${interpolate(textReveal, [0, 1], [20, 0])}px)`,
            textShadow: '0 4px 20px rgba(0, 0, 0, 0.5)',
          }}
        >
          "{part}"
        </p>
      </div>

      {/* Story arc indicator */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          display: 'flex',
          gap: 24,
          alignItems: 'center',
        }}
      >
        {[
          {step: 'Opening', matches: ['Opening']},
          {step: 'Journey', matches: ['Journey', 'The Journey']},
          {step: 'Climax', matches: ['Climax']},
          {step: 'Closing', matches: ['Closing']},
        ].map(({step, matches}) => {
          const isActive = matches.some(m => m.toLowerCase() === label.toLowerCase());
          return (
            <div
              key={step}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <div
                style={{
                  width: isActive ? 16 : 10,
                  height: isActive ? 16 : 10,
                  borderRadius: '50%',
                  background: isActive ? 'white' : 'rgba(255, 255, 255, 0.3)',
                  boxShadow: isActive ? '0 0 20px white' : 'none',
                }}
              />
              <span
                style={{
                  fontSize: 14,
                  color: isActive ? 'white' : 'rgba(255, 255, 255, 0.4)',
                  fontWeight: isActive ? 600 : 400,
                }}
              >
                {step}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

type YearStorySceneProps = {
  yearStory: YearStory;
  channelName: string;
};

export const YEAR_STORY_PART_DURATION = 120; // 4 seconds per part at 30fps

export const YearStoryScene: React.FC<YearStorySceneProps> = ({yearStory, channelName}) => {
  const parts = [
    {part: yearStory.opening, label: 'Opening', emoji: '🌅', color: '#6366f1'},
    {part: yearStory.arc, label: 'The Journey', emoji: '🚀', color: '#f97316'},
    {part: yearStory.climax, label: 'Climax', emoji: '⭐', color: '#ec4899'},
    {part: yearStory.closing, label: 'Closing', emoji: '🎉', color: '#10b981'},
  ];

  return (
    <AbsoluteFill>
      {parts.map((p, index) => (
        <Sequence
          key={p.label}
          from={index * YEAR_STORY_PART_DURATION}
          durationInFrames={YEAR_STORY_PART_DURATION}
          premountFor={30}
        >
          <StoryPart {...p} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
