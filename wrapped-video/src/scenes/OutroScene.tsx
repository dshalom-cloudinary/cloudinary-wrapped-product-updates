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
import type {YearInReview, HeroStats} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type OutroSceneProps = {
  yearInReview: YearInReview;
  stats: HeroStats;
  username: string;
  year: number;
};

export const OutroScene: React.FC<OutroSceneProps> = ({
  yearInReview,
  stats,
  username,
  year,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Animations
  const headlineProgress = spring({
    frame: frame - 10,
    fps,
    config: {damping: 80},
  });

  const taglineProgress = spring({
    frame: frame - 30,
    fps,
    config: {damping: 100},
  });

  const statsProgress = spring({
    frame: frame - 50,
    fps,
    config: {damping: 100},
  });

  const signoffProgress = spring({
    frame: frame - 70,
    fps,
    config: {damping: 100},
  });

  // Shimmer effect
  const shimmer = interpolate(frame % 90, [0, 90], [0, 360]);

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0f0f23 0%, #1a1a3e 50%, #2e1065 100%)',
        fontFamily,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 80,
      }}
    >
      {/* Animated background */}
      <AbsoluteFill style={{opacity: 0.3}}>
        <Img
          src={staticFile('intro-bg.png')}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'blur(8px)',
          }}
        />
      </AbsoluteFill>

      {/* Radial gradient overlay */}
      <AbsoluteFill
        style={{
          background: 'radial-gradient(circle at center, transparent 0%, rgba(15, 15, 35, 0.95) 70%)',
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        {/* Headline */}
        <div
          style={{
            transform: `scale(${headlineProgress})`,
            opacity: headlineProgress,
            textAlign: 'center',
            marginBottom: 32,
          }}
        >
          <h1
            style={{
              fontSize: 64,
              fontWeight: 800,
              margin: 0,
              background: `linear-gradient(${shimmer}deg, #c4b5fd, #f0abfc, #fde047, #c4b5fd)`,
              backgroundSize: '300% 300%',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              color: 'transparent',
            }}
          >
            {yearInReview.headline}
          </h1>
        </div>

        {/* Tagline */}
        <div
          style={{
            transform: `translateY(${interpolate(taglineProgress, [0, 1], [30, 0])}px)`,
            opacity: taglineProgress,
            textAlign: 'center',
            maxWidth: 900,
            marginBottom: 48,
          }}
        >
          <p
            style={{
              fontSize: 26,
              fontWeight: 400,
              color: 'rgba(255, 255, 255, 0.8)',
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            {yearInReview.tagline}
          </p>
        </div>

        {/* Mini stats row */}
        <div
          style={{
            display: 'flex',
            gap: 32,
            opacity: statsProgress,
            transform: `translateY(${interpolate(statsProgress, [0, 1], [20, 0])}px)`,
          }}
        >
          {[
            {label: 'PRs', value: stats.prsMerged, icon: '🚀'},
            {label: 'Lines+', value: stats.linesAdded, icon: '➕'},
            {label: 'Reviews', value: stats.reviewsGiven, icon: '👀'},
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                backdropFilter: 'blur(20px)',
                borderRadius: 16,
                padding: '16px 32px',
                textAlign: 'center',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <div style={{fontSize: 28}}>{stat.icon}</div>
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: 'white',
                }}
              >
                {stat.value.toLocaleString()}
              </div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'rgba(255, 255, 255, 0.5)',
                  textTransform: 'uppercase',
                  letterSpacing: 1,
                }}
              >
                {stat.label}
              </div>
            </div>
          ))}
        </div>

        {/* Sign off */}
        <div
          style={{
            position: 'absolute',
            bottom: 80,
            opacity: signoffProgress,
            transform: `translateY(${interpolate(signoffProgress, [0, 1], [20, 0])}px)`,
            textAlign: 'center',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                width: 60,
                height: 60,
                borderRadius: 30,
                background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                fontSize: 28,
              }}
            >
              👨‍💻
            </div>
            <div>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: 'white',
                }}
              >
                @{username}
              </div>
              <div
                style={{
                  fontSize: 16,
                  color: 'rgba(255, 255, 255, 0.5)',
                }}
              >
                {year} Wrapped
              </div>
            </div>
          </div>
          <div
            style={{
              fontSize: 18,
              color: 'rgba(255, 255, 255, 0.4)',
              letterSpacing: 2,
            }}
          >
            SEE YOU NEXT YEAR 🎉
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
