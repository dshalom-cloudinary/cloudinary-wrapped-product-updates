import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import {loadFont} from '@remotion/google-fonts/Poppins';
import type {QuarterActivity} from '../types';

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type SlackQuarterlySceneProps = {
  quarters: QuarterActivity[];
};

export const SlackQuarterlyScene: React.FC<SlackQuarterlySceneProps> = ({quarters}) => {
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

  // Use messages field, fallback to prs for backward compatibility
  const getMessageCount = (q: QuarterActivity) => q.messages ?? q.prs ?? 0;

  // Find max messages for bar scaling
  const maxMessages = Math.max(...quarters.map(getMessageCount));

  // Find quarter with highest messages
  const maxQuarterIndex = quarters.findIndex(
    (q) => getMessageCount(q) === maxMessages
  );

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(180deg, #0c0c1d 0%, #1a1a3e 100%)',
        fontFamily,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 80,
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
          Your Year, Quarter by Quarter
        </h2>
        <div
          style={{
            width: 120,
            height: 4,
            background: 'linear-gradient(90deg, #06b6d4, #8b5cf6)',
            borderRadius: 2,
            margin: '20px auto 0',
          }}
        />
      </div>

      {/* Chart */}
      <div
        style={{
          display: 'flex',
          gap: 40,
          marginTop: 60,
        }}
      >
        {quarters.map((quarter, index) => {
          const barProgress = spring({
            frame: frame - 20 - index * 15,
            fps,
            config: {damping: 80, stiffness: 120},
          });

          const messageCount = getMessageCount(quarter);
          const maxBarHeight = 300;
          const barHeight = (messageCount / maxMessages) * maxBarHeight;
          const animatedHeight = interpolate(barProgress, [0, 1], [0, barHeight]);

          const isHighest = index === maxQuarterIndex;

          const colors = [
            {bar: 'linear-gradient(180deg, #22d3ee 0%, #0891b2 100%)', glow: '#22d3ee'},
            {bar: 'linear-gradient(180deg, #a78bfa 0%, #7c3aed 100%)', glow: '#a78bfa'},
            {bar: 'linear-gradient(180deg, #4ade80 0%, #16a34a 100%)', glow: '#4ade80'},
            {bar: 'linear-gradient(180deg, #fb923c 0%, #ea580c 100%)', glow: '#fb923c'},
          ];

          const color = colors[index % colors.length];

          return (
            <div
              key={quarter.quarter}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 16,
              }}
            >
              {/* Highest badge */}
              {isHighest && (
                <div
                  style={{
                    opacity: barProgress,
                    transform: `translateY(${interpolate(barProgress, [0, 1], [-20, 0])}px)`,
                    background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
                    padding: '4px 12px',
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 700,
                    color: '#1a1a2e',
                    marginBottom: -8,
                  }}
                >
                  🔥 PEAK
                </div>
              )}

              {/* Message count */}
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 800,
                  color: isHighest ? '#fbbf24' : 'white',
                  opacity: barProgress,
                  transform: `translateY(${interpolate(barProgress, [0, 1], [20, 0])}px)`,
                }}
              >
                {Math.floor(interpolate(barProgress, [0, 1], [0, messageCount]))}
              </div>

              {/* Bar container - fixed height to align all bars at the bottom */}
              <div
                style={{
                  width: 120,
                  height: maxBarHeight,
                  display: 'flex',
                  alignItems: 'flex-end',
                }}
              >
                {/* Bar */}
                <div
                  style={{
                    width: '100%',
                    height: animatedHeight,
                    background: color.bar,
                    borderRadius: '16px 16px 8px 8px',
                    boxShadow: isHighest
                      ? `0 0 60px ${color.glow}60`
                      : `0 0 40px ${color.glow}40`,
                    border: isHighest ? '2px solid #fbbf24' : 'none',
                  }}
                />
              </div>

              {/* Quarter label */}
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  color: isHighest ? '#fbbf24' : 'rgba(255, 255, 255, 0.9)',
                  opacity: barProgress,
                }}
              >
                {quarter.quarter}
              </div>

              {/* Highlight text */}
              {quarter.highlights && (
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 400,
                    color: 'rgba(255, 255, 255, 0.5)',
                    maxWidth: 180,
                    textAlign: 'center',
                    opacity: barProgress,
                    transform: `translateY(${interpolate(barProgress, [0, 1], [10, 0])}px)`,
                    height: 60,
                  }}
                >
                  {Array.isArray(quarter.highlights)
                    ? quarter.highlights[0]
                    : String(quarter.highlights).split(':')[0]}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Total badge */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          opacity: spring({
            frame: frame - 80,
            fps,
            config: {damping: 100},
          }),
        }}
      >
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(20px)',
            borderRadius: 20,
            padding: '16px 40px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <span style={{fontSize: 24}}>💬</span>
          <span
            style={{
              fontSize: 24,
              fontWeight: 600,
              color: 'white',
            }}
          >
            Total: {quarters.reduce((sum, q) => sum + getMessageCount(q), 0).toLocaleString()} Messages
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
