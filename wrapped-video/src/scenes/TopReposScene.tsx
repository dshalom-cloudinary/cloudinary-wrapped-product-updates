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
import type {TopRepo} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type TopReposSceneProps = {
  repos: TopRepo[];
};

export const TopReposScene: React.FC<TopReposSceneProps> = ({repos}) => {
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
          Your Home Turf
        </h2>
        <p
          style={{
            fontSize: 24,
            fontWeight: 400,
            color: 'rgba(255, 255, 255, 0.6)',
            marginTop: 16,
          }}
        >
          The repositories where you made the biggest impact
        </p>
      </div>

      {/* Repos */}
      <div
        style={{
          display: 'flex',
          gap: 48,
          marginTop: 60,
        }}
      >
        {repos.map((repo, index) => {
          const cardProgress = spring({
            frame: frame - 20 - index * 20,
            fps,
            config: {damping: 80},
          });

          const isFirst = index === 0;

          return (
            <div
              key={repo.name}
              style={{
                transform: `translateY(${interpolate(cardProgress, [0, 1], [80, 0])}px) scale(${interpolate(cardProgress, [0, 1], [0.9, 1])})`,
                opacity: cardProgress,
                background: isFirst
                  ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%)'
                  : 'rgba(255, 255, 255, 0.05)',
                backdropFilter: 'blur(20px)',
                borderRadius: 32,
                padding: 48,
                width: 400,
                border: isFirst
                  ? '2px solid rgba(139, 92, 246, 0.4)'
                  : '1px solid rgba(255, 255, 255, 0.1)',
                textAlign: 'center',
              }}
            >
              {/* Rank badge */}
              {isFirst && (
                <div
                  style={{
                    position: 'absolute',
                    top: -20,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                    padding: '8px 24px',
                    borderRadius: 20,
                    fontSize: 16,
                    fontWeight: 700,
                    color: '#1a1a2e',
                  }}
                >
                  👑 #1 REPO
                </div>
              )}

              {/* Repo icon */}
              <div
                style={{
                  fontSize: 64,
                  marginBottom: 24,
                }}
              >
                {isFirst ? '🏆' : '📦'}
              </div>

              {/* Repo name */}
              <h3
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: 'white',
                  margin: '0 0 16px 0',
                }}
              >
                {repo.name}
              </h3>

              {/* PR count */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 24,
                }}
              >
                <span
                  style={{
                    fontSize: 56,
                    fontWeight: 800,
                    background: isFirst
                      ? 'linear-gradient(180deg, #c4b5fd 0%, #a78bfa 100%)'
                      : 'linear-gradient(180deg, #22d3ee 0%, #06b6d4 100%)',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    color: 'transparent',
                  }}
                >
                  {repo.prs}
                </span>
                <span
                  style={{
                    fontSize: 20,
                    fontWeight: 500,
                    color: 'rgba(255, 255, 255, 0.6)',
                  }}
                >
                  PRs
                </span>
              </div>

              {/* Fun fact */}
              <p
                style={{
                  fontSize: 16,
                  fontWeight: 400,
                  color: 'rgba(255, 255, 255, 0.7)',
                  lineHeight: 1.5,
                  margin: 0,
                }}
              >
                {repo.funFact}
              </p>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
