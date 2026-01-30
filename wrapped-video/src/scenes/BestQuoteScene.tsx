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
import type {Quote} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type QuoteCardProps = {
  quote: Quote;
  index: number;
  isMain?: boolean;
};

const QuoteCard: React.FC<QuoteCardProps> = ({quote, index, isMain = false}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Entry animation
  const entryProgress = spring({
    frame,
    fps,
    config: {damping: 80, stiffness: 120},
  });

  // Quote mark animation
  const quoteMarkScale = spring({
    frame: frame - 10,
    fps,
    config: {damping: 60, stiffness: 100},
  });

  // Fade out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  const gradients = [
    'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
    'linear-gradient(135deg, #f97316 0%, #fb923c 100%)',
    'linear-gradient(135deg, #06b6d4 0%, #22d3ee 100%)',
    'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
    'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)',
  ];

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
      />

      {/* Decorative quote marks */}
      <div
        style={{
          position: 'absolute',
          top: 150,
          left: 100,
          fontSize: 200,
          color: 'rgba(255, 255, 255, 0.05)',
          fontWeight: 800,
          transform: `scale(${quoteMarkScale})`,
        }}
      >
        "
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: 150,
          right: 100,
          fontSize: 200,
          color: 'rgba(255, 255, 255, 0.05)',
          fontWeight: 800,
          transform: `scale(${quoteMarkScale}) rotate(180deg)`,
        }}
      >
        "
      </div>

      {/* Main content */}
      <div
        style={{
          transform: `translateY(${interpolate(entryProgress, [0, 1], [80, 0])}px)`,
          opacity: entryProgress,
          maxWidth: 1000,
          textAlign: 'center',
          padding: 60,
        }}
      >
        {/* Badge */}
        {isMain && (
          <div
            style={{
              display: 'inline-block',
              background: gradients[index % gradients.length],
              padding: '10px 28px',
              borderRadius: 25,
              fontSize: 18,
              fontWeight: 700,
              color: 'white',
              marginBottom: 40,
              letterSpacing: 2,
              textTransform: 'uppercase',
            }}
          >
            ⭐ Quote of the Year
          </div>
        )}

        {!isMain && (
          <div
            style={{
              display: 'inline-block',
              background: 'rgba(255, 255, 255, 0.1)',
              padding: '8px 24px',
              borderRadius: 20,
              fontSize: 16,
              fontWeight: 600,
              color: 'rgba(255, 255, 255, 0.8)',
              marginBottom: 40,
            }}
          >
            {quote.period}
          </div>
        )}

        {/* Quote text */}
        <p
          style={{
            fontSize: isMain ? 56 : 44,
            fontWeight: 700,
            color: 'white',
            lineHeight: 1.3,
            margin: 0,
            marginBottom: 40,
            fontStyle: 'italic',
            textShadow: '0 4px 30px rgba(0, 0, 0, 0.5)',
          }}
        >
          "{quote.text}"
        </p>

        {/* Author */}
        <div
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: 'rgba(255, 255, 255, 0.9)',
            marginBottom: 20,
          }}
        >
          — {quote.author}
        </div>

        {/* Context */}
        <p
          style={{
            fontSize: 22,
            fontWeight: 400,
            color: 'rgba(255, 255, 255, 0.6)',
            margin: 0,
            maxWidth: 600,
            marginLeft: 'auto',
            marginRight: 'auto',
          }}
        >
          {quote.context}
        </p>
      </div>
    </AbsoluteFill>
  );
};

type BestQuoteSceneProps = {
  quotes: Quote[];
};

export const QUOTE_DURATION = 120; // 4 seconds per quote at 30fps

export const BestQuoteScene: React.FC<BestQuoteSceneProps> = ({quotes}) => {
  // Return empty fragment instead of null to maintain composition structure
  if (!quotes || quotes.length === 0) {
    return <></>;
  }

  // First quote is the "Quote of the Year" (safe access after length check)
  const mainQuote = quotes[0];
  const otherQuotes = quotes.slice(1, 4); // Max 3 additional quotes

  return (
    <AbsoluteFill>
      {/* Main quote */}
      <Sequence from={0} durationInFrames={QUOTE_DURATION} premountFor={30}>
        <QuoteCard quote={mainQuote} index={0} isMain />
      </Sequence>

      {/* Additional quotes */}
      {otherQuotes.map((quote, index) => (
        <Sequence
          key={index}
          from={(index + 1) * QUOTE_DURATION}
          durationInFrames={QUOTE_DURATION}
          premountFor={30}
        >
          <QuoteCard quote={quote} index={index + 1} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
