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
import type {TopContributor} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type SpotlightSceneProps = {
  contributors: TopContributor[];
  durationPerContributor?: number; // frames per contributor
};

const FRAMES_PER_CONTRIBUTOR = 90; // 3 seconds at 30fps

const ContributorSpotlight: React.FC<{
  contributor: TopContributor;
  index: number;
}> = ({contributor, index}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: {damping: 80, stiffness: 150},
  });

  // Exit animation (fade out in last 15 frames)
  const exitProgress = interpolate(
    frame,
    [FRAMES_PER_CONTRIBUTOR - 20, FRAMES_PER_CONTRIBUTOR - 5],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const colors = ['#fbbf24', '#94a3b8', '#cd7f32', '#6366f1', '#a855f7'];
  const color = colors[index % colors.length];

  // Get initials
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
        background: `linear-gradient(135deg, #0f172a 0%, #1e293b 100%)`,
        fontFamily,
        justifyContent: 'center',
        alignItems: 'center',
        opacity: exitProgress,
      }}
    >
      {/* Glow effect behind avatar */}
      <div
        style={{
          position: 'absolute',
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${color}30 0%, transparent 70%)`,
          filter: 'blur(60px)',
          opacity: entryProgress,
        }}
      />

      {/* Content */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          transform: `translateY(${interpolate(entryProgress, [0, 1], [50, 0])}px)`,
          opacity: entryProgress,
        }}
      >
        {/* Avatar */}
        <div
          style={{
            width: 160,
            height: 160,
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${color} 0%, ${color}80 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 56,
            fontWeight: 700,
            color: 'white',
            marginBottom: 32,
            boxShadow: `0 0 60px ${color}40`,
          }}
        >
          {getInitials(contributor.displayName)}
        </div>

        {/* Name */}
        <h2
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: 'white',
            margin: 0,
            textAlign: 'center',
          }}
        >
          {contributor.displayName}
        </h2>

        {/* Team */}
        <div
          style={{
            fontSize: 24,
            fontWeight: 500,
            color: 'rgba(255, 255, 255, 0.5)',
            marginTop: 8,
          }}
        >
          {contributor.team}
        </div>

        {/* Fun Title Badge */}
        <div
          style={{
            background: `linear-gradient(135deg, ${color}20 0%, ${color}10 100%)`,
            border: `2px solid ${color}`,
            padding: '12px 32px',
            borderRadius: 30,
            marginTop: 32,
            fontSize: 28,
            fontWeight: 700,
            color,
          }}
        >
          {contributor.funTitle}
        </div>

        {/* Stats Row */}
        <div
          style={{
            display: 'flex',
            gap: 48,
            marginTop: 40,
          }}
        >
          {/* Message Count */}
          <div style={{textAlign: 'center'}}>
            <div
              style={{
                fontSize: 48,
                fontWeight: 800,
                color: 'white',
              }}
            >
              {contributor.messageCount.toLocaleString()}
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 500,
                color: 'rgba(255, 255, 255, 0.5)',
                textTransform: 'uppercase',
                letterSpacing: 2,
              }}
            >
              Messages
            </div>
          </div>

          {/* Contribution Percent */}
          <div style={{textAlign: 'center'}}>
            <div
              style={{
                fontSize: 48,
                fontWeight: 800,
                color,
              }}
            >
              {contributor.contributionPercent}%
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 500,
                color: 'rgba(255, 255, 255, 0.5)',
                textTransform: 'uppercase',
                letterSpacing: 2,
              }}
            >
              Of Total
            </div>
          </div>
        </div>

        {/* Fun Fact */}
        <div
          style={{
            marginTop: 40,
            padding: '16px 32px',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: 16,
            maxWidth: 600,
          }}
        >
          <p
            style={{
              fontSize: 22,
              fontWeight: 500,
              color: 'rgba(255, 255, 255, 0.85)',
              margin: 0,
              textAlign: 'center',
              lineHeight: 1.5,
            }}
          >
            "{contributor.funFact}"
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const SpotlightScene: React.FC<SpotlightSceneProps> = ({
  contributors,
  durationPerContributor = FRAMES_PER_CONTRIBUTOR,
}) => {
  return (
    <AbsoluteFill>
      {contributors.slice(0, 5).map((contributor, index) => (
        <Sequence
          key={contributor.username}
          from={index * durationPerContributor}
          durationInFrames={durationPerContributor}
        >
          <ContributorSpotlight contributor={contributor} index={index} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
