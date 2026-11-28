// origin: video-shotcraft assets/lib/Caption.tsx (template/src/aifl/Caption.tsx).
// Same mechanics (screen-space narration strip, 8f fade/rise in, 8f fade out, small accent
// square), re-skinned to LeadPilot tokens and raised to the Q11 readable sizes: the main line
// is 56 px (>= 5.2% of frame height), the optional second line 36 px (>= 3%). It sits on an
// opaque white surface card; the shots keep page content out of its band while it is up.
import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { C, EASE_OUT, INTER, shadow } from '../theme';

export const Caption: React.FC<{ main: string; sub?: string; duration: number; bottom?: number }> = ({
  main,
  sub,
  duration,
  bottom = 40,
}) => {
  const frame = useCurrentFrame();
  const inT = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE_OUT,
  });
  const outT = interpolate(frame, [duration - 8, duration], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom,
        display: 'flex',
        justifyContent: 'center',
        pointerEvents: 'none',
        opacity: inT * outT,
        transform: `translateY(${(1 - inT) * 10}px)`,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 22,
          padding: sub ? '18px 40px 20px 34px' : '18px 40px 18px 34px',
          borderRadius: 24,
          background: C.surfaceLowest, // fully opaque: nothing behind may show through
          boxShadow: `0 0 0 1.5px ${C.primaryFixed}, 0 18px 48px ${shadow(0.16)}, 0 2px 6px ${shadow(0.06)}`,
          fontFamily: INTER,
          maxWidth: 1680,
        }}
      >
        <span
          style={{
            width: 14,
            height: 14,
            borderRadius: 4,
            background: C.primary,
            flex: '0 0 auto',
            marginTop: 25,
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span
            style={{
              fontSize: 56,
              lineHeight: 1.14,
              fontWeight: 600,
              letterSpacing: '-0.02em',
              color: C.onSurface,
              whiteSpace: 'nowrap',
            }}
          >
            {main}
          </span>
          {sub ? (
            <span
              style={{
                fontSize: 36,
                lineHeight: 1.25,
                fontWeight: 500,
                letterSpacing: '-0.01em',
                color: C.onSurfaceVariant,
                whiteSpace: 'nowrap',
              }}
            >
              {sub}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
};
