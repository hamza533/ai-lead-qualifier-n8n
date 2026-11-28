// origin: video-shotcraft assets/lib/FlashCut.tsx (template/src/aifl/FlashCut.tsx).
// Bright-field cut over a hard cut; the warm-white bloom is re-tinted to LeadPilot's
// surface / primary-fixed lavender.
import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';

export const FlashCut: React.FC<{ duration?: number }> = ({ duration = 10 }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, duration * 0.4, duration], [0, 0.85, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill
      style={{
        pointerEvents: 'none',
        opacity: o,
        background:
          'radial-gradient(ellipse at 50% 45%, rgba(250,248,255,0.98), rgba(234,221,255,0.55) 55%, transparent 80%)',
      }}
    />
  );
};
