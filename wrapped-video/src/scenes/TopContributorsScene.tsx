import React from 'react';
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Poppins';
import type {TopContributor} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type TopContributorsSceneProps = {
  contributors: TopContributor[];
};

export const TopContributorsScene: React.FC<TopContributorsSceneProps> = ({contributors}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Title animation
  const titleProgress = spring({
    frame,
    fps,
    config: {damping: 100},
  });

  // Fade out
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  // Get initials from display name
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        fontFamily,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 80,
        opacity: fadeOut,
      }}
    >
      {/* Background pattern */}
      <AbsoluteFill style={{opacity: 0.1}}>
        <Img
          src={staticFile('hero-stats-bg.png')}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'blur(4px)',
          }}
        />
      </AbsoluteFill>

      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          transform: `translateY(${interpolate(titleProgress, [0, 1], [-30, 0])}px)`,
          opacity: titleProgress,
          textAlign: 'center',
        }}
      >
        <h2
          style={{
            fontSize: 52,
            fontWeight: 700,
            color: 'white',
            margin: 0,
          }}
        >
          Top Contributors
        </h2>
        <p
          style={{
            fontSize: 24,
            fontWeight: 400,
            color: 'rgba(255, 255, 255, 0.6)',
            marginTop: 16,
          }}
        >
          The voices that shaped this channel
        </p>
      </div>

      {/* Contributors */}
      <div
        style={{
          display: 'flex',
          gap: 32,
          marginTop: 60,
          flexWrap: 'wrap',
          justifyContent: 'center',
          maxWidth: 1400,
        }}
      >
        {contributors.slice(0, 5).map((contributor, index) => {
          const cardProgress = spring({
            frame: frame - 20 - index * 15,
            fps,
            config: {damping: 80},
          });

          const isFirst = index === 0;
          const colors = ['#fbbf24', '#94a3b8', '#cd7f32', '#6366f1', '#a855f7'];

          return (
            <div
              key={contributor.username}
              style={{
                position: 'relative',
                transform: `translateY(${interpolate(cardProgress, [0, 1], [80, 0])}px) scale(${interpolate(cardProgress, [0, 1], [0.9, 1])})`,
                opacity: cardProgress,
                background: isFirst
                  ? 'linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(245, 158, 11, 0.15) 100%)'
                  : 'rgba(255, 255, 255, 0.05)',
                backdropFilter: 'blur(20px)',
                borderRadius: 24,
                padding: 32,
                width: 240,
                border: isFirst
                  ? '2px solid rgba(251, 191, 36, 0.4)'
                  : '1px solid rgba(255, 255, 255, 0.1)',
                textAlign: 'center',
              }}
            >
              {/* Rank badge */}
              {isFirst && (
                <div
                  style={{
                    position: 'absolute',
                    top: -16,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                    padding: '6px 16px',
                    borderRadius: 16,
                    fontSize: 14,
                    fontWeight: 700,
                    color: '#1a1a2e',
                  }}
                >
                  👑 MVP
                </div>
              )}

              {/* Avatar placeholder with initials */}
              <div
                style={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: `linear-gradient(135deg, ${colors[index]} 0%, ${colors[index]}80 100%)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                  fontSize: 28,
                  fontWeight: 700,
                  color: 'white',
                }}
              >
                {getInitials(contributor.displayName)}
              </div>

              {/* Display name */}
              <h3
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  color: 'white',
                  margin: '0 0 4px 0',
                }}
              >
                {contributor.displayName}
              </h3>

              {/* Team */}
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'rgba(255, 255, 255, 0.5)',
                  marginBottom: 16,
                }}
              >
                {contributor.team}
              </div>

              {/* Fun title */}
              <div
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  padding: '6px 12px',
                  borderRadius: 12,
                  fontSize: 14,
                  fontWeight: 600,
                  color: colors[index],
                  marginBottom: 16,
                }}
              >
                {contributor.funTitle}
              </div>

              {/* Message count */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'baseline',
                  gap: 4,
                }}
              >
                <span
                  style={{
                    fontSize: 36,
                    fontWeight: 800,
                    color: 'white',
                  }}
                >
                  {contributor.messageCount}
                </span>
                <span
                  style={{
                    fontSize: 16,
                    fontWeight: 500,
                    color: 'rgba(255, 255, 255, 0.6)',
                  }}
                >
                  msgs
                </span>
              </div>

              {/* Contribution percent */}
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'rgba(255, 255, 255, 0.4)',
                  marginTop: 4,
                }}
              >
                {contributor.contributionPercent}% of total
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
