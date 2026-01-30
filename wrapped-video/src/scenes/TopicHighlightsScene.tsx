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
import type {TopicHighlight} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type TopicCardProps = {
  topic: TopicHighlight;
  index: number;
  totalCount: number;
};

const TopicCard: React.FC<TopicCardProps> = ({topic, index, totalCount}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: {damping: 80, stiffness: 100},
  });

  // Insight reveal
  const insightReveal = spring({
    frame: frame - 30,
    fps,
    config: {damping: 100, stiffness: 80},
  });

  // Quote reveal
  const quoteReveal = spring({
    frame: frame - 60,
    fps,
    config: {damping: 100, stiffness: 80},
  });

  // Fade out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const colors = [
    {gradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', accent: '#c4b5fd', bg: '#6366f1'},
    {gradient: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)', accent: '#fed7aa', bg: '#f97316'},
    {gradient: 'linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%)', accent: '#a5f3fc', bg: '#06b6d4'},
    {gradient: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)', accent: '#a7f3d0', bg: '#10b981'},
    {gradient: 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)', accent: '#fbcfe8', bg: '#ec4899'},
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
      {/* Background gradient */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, #0f0f23 0%, ${color.bg}15 50%, #1a1a2e 100%)`,
        }}
      />

      {/* Decorative circles */}
      <div
        style={{
          position: 'absolute',
          top: -100,
          right: -100,
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: `${color.bg}20`,
          transform: `scale(${entryProgress})`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -150,
          left: -150,
          width: 500,
          height: 500,
          borderRadius: '50%',
          background: `${color.bg}10`,
          transform: `scale(${entryProgress})`,
        }}
      />

      {/* Content */}
      <div
        style={{
          transform: `translateY(${interpolate(entryProgress, [0, 1], [60, 0])}px)`,
          opacity: entryProgress,
          maxWidth: 1000,
          textAlign: 'center',
          padding: 60,
        }}
      >
        {/* Topic badge */}
        <div
          style={{
            display: 'inline-block',
            background: color.gradient,
            padding: '16px 40px',
            borderRadius: 40,
            fontSize: 32,
            fontWeight: 800,
            color: 'white',
            marginBottom: 40,
            boxShadow: `0 10px 40px ${color.bg}50`,
          }}
        >
          📊 {topic.topic}
        </div>

        {/* Insight */}
        <div
          style={{
            opacity: insightReveal,
            transform: `translateY(${interpolate(insightReveal, [0, 1], [20, 0])}px)`,
          }}
        >
          <p
            style={{
              fontSize: 56,
              fontWeight: 700,
              color: color.accent,
              margin: 0,
              marginBottom: 20,
              textShadow: `0 0 40px ${color.accent}40`,
            }}
          >
            {topic.insight}
          </p>
          <p
            style={{
              fontSize: 24,
              fontWeight: 400,
              color: 'rgba(255, 255, 255, 0.6)',
              margin: 0,
              marginBottom: 50,
            }}
          >
            {topic.period}
          </p>
        </div>

        {/* Best quote */}
        <div
          style={{
            opacity: quoteReveal,
            transform: `translateY(${interpolate(quoteReveal, [0, 1], [20, 0])}px)`,
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: 24,
            padding: 32,
            borderLeft: `4px solid ${color.accent}`,
          }}
        >
          <p
            style={{
              fontSize: 28,
              fontWeight: 500,
              color: 'white',
              margin: 0,
              fontStyle: 'italic',
              lineHeight: 1.5,
            }}
          >
            "{topic.bestQuote}"
          </p>
        </div>
      </div>

      {/* Progress indicator - dynamic based on actual topic count */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          display: 'flex',
          gap: 12,
        }}
      >
        {Array.from({length: totalCount}, (_, i) => (
          <div
            key={i}
            style={{
              width: i === index ? 40 : 10,
              height: 10,
              borderRadius: 5,
              background: i === index ? 'white' : 'rgba(255, 255, 255, 0.3)',
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

type TopicHighlightsSceneProps = {
  topics: TopicHighlight[];
};

export const TOPIC_DURATION = 150; // 5 seconds per topic at 30fps

export const TopicHighlightsScene: React.FC<TopicHighlightsSceneProps> = ({topics}) => {
  // Return empty fragment instead of null to maintain composition structure
  if (!topics || topics.length === 0) {
    return <></>;
  }

  const displayTopics = topics.slice(0, 5); // Max 5 topics
  const totalCount = displayTopics.length;

  return (
    <AbsoluteFill>
      {displayTopics.map((topic, index) => (
        <Sequence
          key={index}
          from={index * TOPIC_DURATION}
          durationInFrames={TOPIC_DURATION}
          premountFor={30}
        >
          <TopicCard topic={topic} index={index} totalCount={totalCount} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
