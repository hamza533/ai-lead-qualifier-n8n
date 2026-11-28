// Shots 2 / 6 / 9 — paper-title-card (demos/typography/paper-title-card/PaperTitleCard.tsx)
// Kept: word i delay = 4 + 4i, 9f, bezier(0.2,0.75,0.3,1), scale 1.28→1 + blur 7→0 + opacity
// (the letterpress recipe), exactly one accent group, accent underline 220×6 scaleX 16→34f,
// whole card fades out over the last 8f, optional small sub line (static: the results shot
// owns the digit rolls; a rolling digit here sat low and left a remnant).
// Re-skinned: surface background with a white centre glow instead of paper + warm light,
// Inter 700 instead of serif, accent = primary #630ed4 italic, sub line in Inter caps.
import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion';
import { C, INTER } from '../theme';

export const parseWords = (text: string): { text: string; accent: boolean }[] => {
  const out: { text: string; accent: boolean }[] = [];
  let inAccent = false;
  for (const raw of text.split(/\s+/).filter(Boolean)) {
    let w = raw;
    const open = w.startsWith('*');
    if (open) {
      inAccent = true;
      w = w.slice(1);
    }
    const close = w.endsWith('*');
    if (close) w = w.slice(0, -1);
    out.push({ text: w, accent: inAccent });
    if (close) inAccent = false;
  }
  return out;
};

export const TitleCard: React.FC<{ text: string; sub?: string; duration: number }> = ({ text, sub, duration }) => {
  const frame = useCurrentFrame();
  const words = parseWords(text);
  const fadeOut = interpolate(frame, [duration - 8, duration], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const underline = interpolate(frame, [16, 34], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.3, 0, 0.2, 1),
  });
  const subT = interpolate(frame, [12, 24], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const subDigit = sub?.match(/^(\d+)\s(.*)$/);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: C.surface,
        backgroundImage: `radial-gradient(1100px 750px at 50% 42%, rgba(255,255,255,0.95), rgba(255,255,255,0) 65%), radial-gradient(900px 500px at 50% 110%, rgba(210,187,255,0.25), rgba(210,187,255,0) 70%)`,
        justifyContent: 'center',
        alignItems: 'center',
        opacity: fadeOut,
        fontFamily: INTER,
      }}
    >
      <div style={{ textAlign: 'center', maxWidth: 1600 }}>
        <div
          style={{
            fontSize: 112,
            fontWeight: 700,
            lineHeight: 1.12,
            color: C.onSurface,
            letterSpacing: '-0.035em',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            columnGap: '0.24em',
          }}
        >
          {words.map((w, i) => {
            const delay = 4 + i * 4;
            const t = interpolate(frame, [delay, delay + 9], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
              easing: Easing.bezier(0.2, 0.75, 0.3, 1),
            });
            return (
              <span
                key={i}
                style={{
                  opacity: t,
                  transform: `scale(${1.28 - 0.28 * t})`,
                  filter: t < 0.999 ? `blur(${(1 - t) * 7}px)` : undefined,
                  display: 'inline-block',
                  fontStyle: w.accent ? 'italic' : 'normal',
                  color: w.accent ? C.primary : undefined,
                  paddingRight: w.accent ? '0.04em' : 0,
                }}
              >
                {w.text}
              </span>
            );
          })}
        </div>
        <div
          style={{
            height: 6,
            width: 220,
            margin: '40px auto 0',
            borderRadius: 3,
            background: C.primary,
            transform: `scaleX(${underline})`,
          }}
        />
        {sub ? (
          <div
            style={{
              fontSize: 34,
              fontWeight: 600,
              letterSpacing: '0.08em',
              color: C.onSurfaceVariant,
              marginTop: 34,
              opacity: subT,
              textTransform: 'uppercase',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'baseline',
              gap: '0.4em',
            }}
          >
            {subDigit ? (
              <>
                <span style={{ color: C.primary, fontWeight: 700 }}>{subDigit[1]}</span>
                <span>{subDigit[2]}</span>
              </>
            ) : (
              <span>{sub}</span>
            )}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
