import React from 'react';
import {
  AbsoluteFill,
  Img,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Poppins';
import type {BigRock} from '../types';
import {BIG_ROCK_SLIDE_DURATION} from '../durations';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type BigRockCardProps = {
  rock: BigRock;
  index: number;
  total: number;
};

const BigRockCard: React.FC<BigRockCardProps> = ({rock, index, total}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: {damping: 80},
  });

  const titleProgress = spring({
    frame: frame - 15,
    fps,
    config: {damping: 100},
  });

  const detailsProgress = spring({
    frame: frame - 30,
    fps,
    config: {damping: 100},
  });

  // Fade out
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  // Select image based on project
  const bgImage = rock.title.toLowerCase().includes('async') || rock.title.toLowerCase().includes('capsule')
    ? 'async-capsule.png'
    : 'big-rocks-achievement.png';

  return (
    <AbsoluteFill
      style={{
        fontFamily,
        background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
        opacity: fadeOut,
      }}
    >
      {/* Background Image */}
      <AbsoluteFill style={{opacity: 0.25}}>
        <Img
          src={staticFile(bgImage)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'blur(2px)',
          }}
        />
      </AbsoluteFill>

      {/* Gradient overlay */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.7) 0%, rgba(30, 27, 75, 0.9) 100%)',
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          padding: 80,
        }}
      >
        {/* Project number badge */}
        <div
          style={{
            position: 'absolute',
            top: 60,
            left: 80,
            transform: `translateX(${interpolate(entryProgress, [0, 1], [-100, 0])}px)`,
            opacity: entryProgress,
          }}
        >
          <span
            style={{
              fontSize: 24,
              fontWeight: 600,
              color: 'rgba(255, 255, 255, 0.5)',
              letterSpacing: 3,
            }}
          >
            BIG ROCK {index + 1} OF {total}
          </span>
        </div>

        {/* Main content card */}
        <div
          style={{
            transform: `scale(${entryProgress})`,
            opacity: entryProgress,
            background: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(30px)',
            borderRadius: 32,
            padding: 60,
            maxWidth: 1000,
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          {/* Repo badge */}
          <div
            style={{
              display: 'inline-block',
              background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
              padding: '8px 24px',
              borderRadius: 20,
              fontSize: 18,
              fontWeight: 600,
              color: 'white',
              marginBottom: 24,
              transform: `translateY(${interpolate(titleProgress, [0, 1], [20, 0])}px)`,
              opacity: titleProgress,
            }}
          >
            📦 {rock.repo}
          </div>

          {/* Title */}
          <h2
            style={{
              fontSize: 56,
              fontWeight: 800,
              color: 'white',
              margin: '0 0 24px 0',
              lineHeight: 1.2,
              transform: `translateY(${interpolate(titleProgress, [0, 1], [30, 0])}px)`,
              opacity: titleProgress,
            }}
          >
            {rock.title}
          </h2>

          {/* Impact description */}
          <p
            style={{
              fontSize: 26,
              fontWeight: 400,
              color: 'rgba(255, 255, 255, 0.8)',
              margin: '0 0 32px 0',
              lineHeight: 1.6,
              transform: `translateY(${interpolate(detailsProgress, [0, 1], [20, 0])}px)`,
              opacity: detailsProgress,
            }}
          >
            {rock.impact}
          </p>

          {/* Lines changed stat */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              transform: `translateY(${interpolate(detailsProgress, [0, 1], [20, 0])}px)`,
              opacity: detailsProgress,
            }}
          >
            <div
              style={{
                background: 'rgba(34, 197, 94, 0.2)',
                border: '1px solid rgba(34, 197, 94, 0.4)',
                borderRadius: 12,
                padding: '12px 24px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <span style={{fontSize: 24}}>📊</span>
              <span
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  color: '#4ade80',
                }}
              >
                {rock.linesChanged.toLocaleString()}
              </span>
              <span
                style={{
                  fontSize: 18,
                  fontWeight: 500,
                  color: 'rgba(255, 255, 255, 0.6)',
                }}
              >
                lines changed
              </span>
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

type BigRocksSceneProps = {
  bigRocks: BigRock[];
};

export const BigRocksScene: React.FC<BigRocksSceneProps> = ({bigRocks}) => {
  return (
    <AbsoluteFill>
      {bigRocks.slice(0, 5).map((rock, index) => (
        <Sequence
          key={index}
          from={index * BIG_ROCK_SLIDE_DURATION}
          durationInFrames={BIG_ROCK_SLIDE_DURATION}
          premountFor={30}
        >
          <BigRockCard rock={rock} index={index} total={Math.min(bigRocks.length, 5)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
