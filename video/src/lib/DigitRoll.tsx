// origin: video-shotcraft assets/lib/DigitRoll.tsx (template/src/aifl/DigitRoll.tsx).
// Same odometer mechanics (roll one full strip, land on the target, 22f per column, 4f column
// stagger, bezier(0.25,0.8,0.25,1)). LeadPilot: Inter instead of mono, configurable weight /
// tracking, non-digit characters (spaces, %, /, s, .) stay static, and `blankStart` puts an
// empty cell at the head of each strip so a value rolls in from blank instead of from "000".
import React from 'react';
import { interpolate, useCurrentFrame, Easing } from 'remotion';
import { C, INTER } from '../theme';

const DIGITS = '0123456789';

export const DigitRoll: React.FC<{
  value: string;
  delay?: number;
  fontSize?: number;
  fontWeight?: number;
  letterSpacing?: string;
  color?: string;
  blankStart?: boolean;
}> = ({ value, delay = 0, fontSize = 30, fontWeight = 700, letterSpacing = '0em', color = C.onSurface, blankStart = false }) => {
  const frame = useCurrentFrame();
  const lineH = fontSize * 1.15;
  let col = 0;
  return (
    <span
      style={{
        display: 'inline-flex',
        overflow: 'hidden',
        height: lineH,
        verticalAlign: 'bottom',
        fontFamily: INTER,
        fontWeight,
        letterSpacing,
        whiteSpace: 'pre',
      }}
    >
      {value.split('').map((ch, i) => {
        const target = DIGITS.indexOf(ch);
        if (target < 0) {
          return (
            <span key={i} style={{ fontSize, lineHeight: `${lineH}px`, color }}>
              {ch}
            </span>
          );
        }
        const c = col++;
        const t = interpolate(frame, [delay + c * 4, delay + c * 4 + 22], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
          easing: Easing.bezier(0.25, 0.8, 0.25, 1),
        });
        // roll through one full strip then land on the target digit
        const lead = blankStart ? 1 : 0;
        const offset = (lead + 10 + target) * t * lineH;
        return (
          <span key={i} style={{ display: 'inline-block', height: lineH }}>
            <span style={{ display: 'block', transform: `translateY(${-offset}px)` }}>
              {((blankStart ? ' ' : '') + DIGITS + DIGITS).split('').map((d, j) => (
                <span
                  key={j}
                  style={{ display: 'block', fontSize, lineHeight: `${lineH}px`, color, fontVariantNumeric: 'tabular-nums' }}
                >
                  {d}
                </span>
              ))}
            </span>
          </span>
        );
      })}
    </span>
  );
};
