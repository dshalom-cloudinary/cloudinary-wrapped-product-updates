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
import type {FunFact} from '../types';
import {FUN_FACT_SLIDE_DURATION} from '../durations';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type FunFactCardProps = {
  fact: FunFact;
  index: number;
};

const FunFactCard: React.FC<FunFactCardProps> = ({fact, index}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: {damping: 100},
  });

  // Highlight animation for value
  const pulseScale = interpolate(
    frame % 60,
    [0, 30, 60],
    [1, 1.03, 1],
    {extrapolateRight: 'clamp'}
  );

  // Fade out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 10, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const colors = [
    {bg: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', accent: '#c4b5fd'},
    {bg: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)', accent: '#fed7aa'},
    {bg: 'linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%)', accent: '#a5f3fc'},
    {bg: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)', accent: '#a7f3d0'},
    {bg: 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)', accent: '#fbcfe8'},
  ];

  const color = colors[index % colors.length];

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily,
        opacity: fadeOut,
      }}
    >
      {/* Background */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(180deg, #0f0f23 0%, #1a1a2e 100%)',
        }}
      >
        <Img
          src={staticFile('fun-facts-bg.png')}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            opacity: 0.3,
          }}
        />
      </AbsoluteFill>

      {/* Card */}
      <div
        style={{
          transform: `scale(${entryProgress}) translateY(${interpolate(entryProgress, [0, 1], [100, 0])}px)`,
          opacity: entryProgress,
          background: 'rgba(255, 255, 255, 0.05)',
          backdropFilter: 'blur(40px)',
          borderRadius: 40,
          padding: 60,
          maxWidth: 900,
          textAlign: 'center',
          border: '2px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 40px 80px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Label Badge */}
        <div
          style={{
            display: 'inline-block',
            background: color.bg,
            padding: '12px 32px',
            borderRadius: 30,
            fontSize: 22,
            fontWeight: 700,
            color: 'white',
            marginBottom: 32,
            letterSpacing: 1,
          }}
        >
          {fact.label}
        </div>

        {/* Value */}
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            color: color.accent,
            marginBottom: 24,
            transform: `scale(${pulseScale})`,
            textShadow: `0 0 40px ${color.accent}40`,
          }}
        >
          {fact.value}
        </div>

        {/* Detail */}
        <p
          style={{
            fontSize: 28,
            fontWeight: 400,
            color: 'rgba(255, 255, 255, 0.8)',
            lineHeight: 1.6,
            margin: 0,
            maxWidth: 700,
          }}
        >
          {fact.detail}
        </p>
      </div>

      {/* Progress dots */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          display: 'flex',
          gap: 16,
        }}
      >
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            style={{
              width: i === index ? 40 : 12,
              height: 12,
              borderRadius: 6,
              background: i === index ? 'white' : 'rgba(255, 255, 255, 0.3)',
              transition: 'all 0.3s',
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

type FunFactsSceneProps = {
  funFacts: FunFact[];
};

export const FunFactsScene: React.FC<FunFactsSceneProps> = ({funFacts}) => {
  return (
    <AbsoluteFill>
      {funFacts.slice(0, 5).map((fact, index) => (
        <Sequence
          key={index}
          from={index * FUN_FACT_SLIDE_DURATION}
          durationInFrames={FUN_FACT_SLIDE_DURATION}
          premountFor={30}
        >
          <FunFactCard fact={fact} index={index} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
