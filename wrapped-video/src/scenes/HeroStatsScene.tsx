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
import type {HeroStats} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type HeroStatsSceneProps = {
  stats: HeroStats;
};

const StatCard: React.FC<{
  label: string;
  value: number | string;
  delay: number;
  color: string;
  icon: string;
}> = ({label, value, delay, color, icon}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const progress = spring({
    frame: frame - delay,
    fps,
    config: {damping: 100, stiffness: 200},
  });

  const countUp = typeof value === 'number'
    ? Math.floor(interpolate(progress, [0, 1], [0, value]))
    : value;

  return (
    <div
      style={{
        transform: `translateY(${interpolate(progress, [0, 1], [60, 0])}px) scale(${interpolate(progress, [0, 1], [0.8, 1])})`,
        opacity: progress,
        background: 'rgba(255, 255, 255, 0.05)',
        backdropFilter: 'blur(20px)',
        borderRadius: 24,
        padding: '32px 40px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        minWidth: 280,
        textAlign: 'center',
      }}
    >
      <div style={{fontSize: 48, marginBottom: 12}}>{icon}</div>
      <div
        style={{
          fontSize: 64,
          fontWeight: 800,
          color,
          marginBottom: 8,
        }}
      >
        {typeof value === 'number' ? countUp.toLocaleString() : value}
      </div>
      <div
        style={{
          fontSize: 20,
          fontWeight: 500,
          color: 'rgba(255, 255, 255, 0.7)',
          textTransform: 'uppercase',
          letterSpacing: 2,
        }}
      >
        {label}
      </div>
    </div>
  );
};

export const HeroStatsScene: React.FC<HeroStatsSceneProps> = ({stats}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Background animation
  const bgScale = interpolate(frame, [0, durationInFrames], [1.05, 1.0], {
    extrapolateRight: 'clamp',
  });

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

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a1a', fontFamily}}>
      {/* Background */}
      <AbsoluteFill style={{transform: `scale(${bgScale})`, opacity: 0.4 * fadeOut}}>
        <Img
          src={staticFile('hero-stats-bg.png')}
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
        />
      </AbsoluteFill>

      {/* Gradient overlay */}
      <AbsoluteFill
        style={{
          background: 'radial-gradient(ellipse at center, transparent 0%, rgba(10, 10, 26, 0.9) 80%)',
          opacity: fadeOut,
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          padding: 60,
          opacity: fadeOut,
        }}
      >
        {/* Title */}
        <div
          style={{
            position: 'absolute',
            top: 80,
            transform: `translateY(${interpolate(titleProgress, [0, 1], [-30, 0])}px)`,
            opacity: titleProgress,
          }}
        >
          <h2
            style={{
              fontSize: 56,
              fontWeight: 700,
              color: 'white',
              margin: 0,
              textAlign: 'center',
            }}
          >
            Your Numbers This Year
          </h2>
          <div
            style={{
              width: 120,
              height: 4,
              background: 'linear-gradient(90deg, #6366f1, #a855f7)',
              borderRadius: 2,
              margin: '20px auto 0',
            }}
          />
        </div>

        {/* Stats Grid */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 32,
            justifyContent: 'center',
            maxWidth: 1200,
            marginTop: 40,
          }}
        >
          <StatCard
            icon="🚀"
            label="PRs Merged"
            value={stats.prsMerged}
            delay={15}
            color="#22d3ee"
          />
          <StatCard
            icon="➕"
            label="Lines Added"
            value={stats.linesAdded}
            delay={25}
            color="#4ade80"
          />
          <StatCard
            icon="➖"
            label="Lines Removed"
            value={stats.linesRemoved}
            delay={35}
            color="#f87171"
          />
          <StatCard
            icon="👀"
            label="Reviews Given"
            value={stats.reviewsGiven}
            delay={45}
            color="#fbbf24"
          />
          <StatCard
            icon="📦"
            label="Repos"
            value={stats.repositoriesContributed}
            delay={55}
            color="#c084fc"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
