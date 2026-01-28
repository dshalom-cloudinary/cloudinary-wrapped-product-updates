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

const {fontFamily} = loadFont('normal', {
  weights: ['400', '600', '700', '800'],
  subsets: ['latin'],
});

type IntroSceneProps = {
  username: string;
  year: number;
};

export const IntroScene: React.FC<IntroSceneProps> = ({username, year}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Background zoom animation
  const bgScale = interpolate(frame, [0, durationInFrames], [1.1, 1.0], {
    extrapolateRight: 'clamp',
  });

  // Title animations with spring
  const titleProgress = spring({
    frame: frame - 10,
    fps,
    config: {damping: 100},
  });

  const yearProgress = spring({
    frame: frame - 25,
    fps,
    config: {damping: 80, stiffness: 150},
  });

  const usernameProgress = spring({
    frame: frame - 40,
    fps,
    config: {damping: 100},
  });

  const subtitleProgress = spring({
    frame: frame - 55,
    fps,
    config: {damping: 100},
  });

  // Fade out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 15, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  return (
    <AbsoluteFill style={{backgroundColor: '#0d0d1a'}}>
      {/* Background Image */}
      <AbsoluteFill
        style={{
          transform: `scale(${bgScale})`,
          opacity: fadeOut,
        }}
      >
        <Img
          src={staticFile('intro-bg.png')}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
        {/* Overlay gradient */}
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(ellipse at center, transparent 30%, rgba(13, 13, 26, 0.8) 100%)',
          }}
        />
      </AbsoluteFill>

      {/* Content */}
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          fontFamily,
          opacity: fadeOut,
        }}
      >
        {/* Year Badge */}
        <div
          style={{
            position: 'absolute',
            top: 100,
            transform: `translateY(${interpolate(yearProgress, [0, 1], [50, 0])}px)`,
            opacity: yearProgress,
          }}
        >
          <div
            style={{
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
              padding: '12px 40px',
              borderRadius: 50,
              fontSize: 28,
              fontWeight: 700,
              color: 'white',
              letterSpacing: 4,
            }}
          >
            {year} WRAPPED
          </div>
        </div>

        {/* Main Title */}
        <div
          style={{
            transform: `scale(${titleProgress})`,
            opacity: titleProgress,
            textAlign: 'center',
          }}
        >
          <h1
            style={{
              fontSize: 120,
              fontWeight: 800,
              margin: 0,
              background: 'linear-gradient(180deg, #ffffff 0%, #a5b4fc 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              color: 'transparent',
              textShadow: '0 0 80px rgba(139, 92, 246, 0.5)',
            }}
          >
            GitHub
          </h1>
          <h1
            style={{
              fontSize: 100,
              fontWeight: 700,
              margin: '-20px 0 0 0',
              background: 'linear-gradient(180deg, #c084fc 0%, #6366f1 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              color: 'transparent',
            }}
          >
            Wrapped
          </h1>
        </div>

        {/* Username */}
        <div
          style={{
            marginTop: 60,
            transform: `translateY(${interpolate(usernameProgress, [0, 1], [30, 0])}px)`,
            opacity: usernameProgress,
          }}
        >
          <span
            style={{
              fontSize: 48,
              fontWeight: 600,
              color: '#e0e7ff',
            }}
          >
            @{username}
          </span>
        </div>

        {/* Subtitle */}
        <div
          style={{
            position: 'absolute',
            bottom: 120,
            transform: `translateY(${interpolate(subtitleProgress, [0, 1], [20, 0])}px)`,
            opacity: subtitleProgress,
          }}
        >
          <span
            style={{
              fontSize: 28,
              fontWeight: 400,
              color: 'rgba(255, 255, 255, 0.6)',
              letterSpacing: 2,
            }}
          >
            YOUR YEAR IN CODE
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
