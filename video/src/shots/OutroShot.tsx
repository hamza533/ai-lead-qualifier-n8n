// Shot 11 — outro-group-photo-launch (demos/outro/outro-group-photo-launch/OutroGroupPhotoLaunch.tsx)
// Kept: 9 elements fly in from all sides (cue 4 + 3i, 12f each, offsets ±360–500px) on
// bezier(0.34,1.4,0.44,1) (y1 > 1: real overshoot, the landing metaphor), rotation ×2 → settled
// (±5°), scale ×1.12 → 1, 8%-lagging blurred ghost, 6f accent glow on landing; render order =
// cue order; everyone recedes (opacity −12%, saturate −8%) when the wordmark arrives; wordmark
// letterpress letters (delay 42 + 1.8i, 8f), rule 58→70f with 190px extension lines, one
// letter-spacing breath; crane: perspective(1400px) rotateX(4°→0) scale(1.06→1) over 40f then
// a slow +0.035 push; light band 2–14f, stage light 0→0.5→0.25 behind the wordmark, 20
// index-derived dust motes; background page blurs 0→14px over 24f; 12f fade at the end.
// Adapted: elements = one representative crop from every screen shown in the film; colours =
// lavender/primary instead of amber/gold; wordmark = bolt mark + "LeadPilot" in Inter 700;
// sign-off line = "Built in n8n · github.com/…" at 36px (Q11: the URL is not the smallest line).
import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion';
import { PageCam } from '../lib/PageCam';
import { C, INTER } from '../theme';
import { BoltMark } from './OrbitOpen';
import { Box, PageName, R_XL, TexCrop, layout, pageH, tex } from './common';

const FLY_EASE = Easing.bezier(0.34, 1.4, 0.44, 1);
const CRANE_EASE = Easing.bezier(0.3, 0, 0.2, 1);
const LETTERS = 'LeadPilot'.split('');
export const WORDMARK_AT = 42;

type FlyEl = { key: string; page: PageName; box: Box; cx: number; cy: number; scale: number; rot: number; dx: number; dy: number; radius: number; cue: number };
const crop = (b: Box, h?: number): Box => ({ x: b.x, y: b.y, w: b.w, h: h ?? b.h });

const ELS: FlyEl[] = [
  { key: 'nav', page: 'landing', box: { x: 0, y: 0, w: 1920, h: 92 }, cx: 960, cy: 62, scale: 0.6, rot: 0, dx: 0, dy: -120, radius: 10, cue: 4 },
  { key: 'form', page: 'form', box: crop(layout.form.formCard), cx: 300, cy: 380, scale: 0.34, rot: -5, dx: -500, dy: 0, radius: R_XL, cue: 7 },
  { key: 'research', page: 'research', box: crop(layout.research.profileCard), cx: 1630, cy: 400, scale: 0.32, rot: 4, dx: 500, dy: 0, radius: R_XL, cue: 10 },
  { key: 'criteria', page: 'score', box: { x: layout.score.rows[0].x, y: layout.score.rows[0].y, w: layout.score.rows[0].w, h: layout.score.rows[2].y + layout.score.rows[2].h - layout.score.rows[0].y }, cx: 1400, cy: 770, scale: 0.4, rot: -3, dx: 450, dy: 260, radius: R_XL, cue: 13 },
  { key: 'scoreBox', page: 'score', box: crop(layout.score.scoreBox), cx: 320, cy: 770, scale: 0.78, rot: 3, dx: -400, dy: 300, radius: R_XL, cue: 16 },
  { key: 'approval', page: 'approval', box: crop(layout.approval.message, 380), cx: 650, cy: 935, scale: 0.42, rot: 2, dx: 0, dy: 320, radius: R_XL, cue: 19 },
  { key: 'email', page: 'crm', box: crop(layout.crm.emailCard, 520), cx: 720, cy: 205, scale: 0.36, rot: -1.5, dx: 0, dy: -240, radius: R_XL, cue: 22 },
  { key: 'kpi', page: 'results', box: crop(layout.results.kpiCards[2]), cx: 1330, cy: 930, scale: 0.7, rot: -2, dx: 380, dy: 0, radius: R_XL, cue: 25 },
  { key: 'lead', page: 'landing', box: crop(layout.landing.heroCard), cx: 1225, cy: 205, scale: 0.45, rot: 2.5, dx: 360, dy: -200, radius: R_XL, cue: 28 },
];

const DUST = Array.from({ length: 20 }, (_, i) => ({
  x: (i * 439 + 137) % 1920,
  y0: (i * 613 + 271) % 1080,
  rise: 0.3 + (i % 5) * 0.11,
  swayAmp: 9 + (i % 4) * 5,
  swayFreq: 0.022 + (i % 3) * 0.008,
  phase: (i * 0.83) % (Math.PI * 2),
  size: 2.5 + (i % 3) * 0.6,
  opacity: 0.25 + ((i * 7) % 5) * 0.06,
}));

export const OutroShot: React.FC<{ duration: number }> = ({ duration }) => {
  const frame = useCurrentFrame();

  const blur = interpolate(frame, [0, 24], [0, 14], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.4, 0, 0.4, 1) });
  const rule = interpolate(frame, [58, 70], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.2, 1) });
  const tag = interpolate(frame, [68, 80], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const fadeOut = interpolate(frame, [duration - 12, duration], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const recede = interpolate(frame, [42, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const craneT = interpolate(frame, [0, 40], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: CRANE_EASE });
  const pushT = interpolate(frame, [40, duration], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const camScale = 1.06 - 0.06 * craneT + 0.035 * pushT;
  const camTilt = 4 * (1 - craneT);

  const sweepX = interpolate(frame, [2, 14], [-700, 2020], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.4, 0, 0.6, 1) });
  const sweepOpacity = interpolate(frame, [2, 5, 11, 14], [0, 0.12, 0.12, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const stageLight = interpolate(frame, [42, 50, 58], [0, 0.5, 0.25], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const vignette = interpolate(frame, [42, 54], [0, 0.1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const ruleExt = interpolate(frame, [58, 66], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.2, 1) });
  const ruleExtFade = interpolate(frame, [66, 72], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const wordSpacing = interpolate(frame, [62, 66], [-0.05, -0.035], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.2, 1) });

  const letter = (i: number) => {
    const delay = Math.round(WORDMARK_AT + i * 1.8);
    const t = interpolate(frame, [delay, delay + 8], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.2, 0.75, 0.3, 1) });
    return {
      opacity: t,
      transform: `translateY(${(1 - t) * 28}px) scale(${1.35 - 0.35 * t})`,
      filter: t < 0.999 ? `blur(${(1 - t) * 8}px)` : undefined,
      display: 'inline-block',
      whiteSpace: 'pre' as const,
    };
  };

  return (
    <AbsoluteFill style={{ opacity: fadeOut, backgroundColor: C.surface, fontFamily: INTER }}>
      <AbsoluteFill style={{ transform: `perspective(1400px) rotateX(${camTilt}deg) scale(${camScale})`, transformOrigin: '50% 45%' }}>
        {/* blur only the background page; the group-photo elements sit in an unfiltered sibling */}
        <PageCam src={tex('landing')} pageH={pageH('landing')} keys={[{ frame: 0, cx: 960, cy: 620, zoom: 0.8 }]} blur={blur} />
        <AbsoluteFill
          style={{ background: 'radial-gradient(1200px 800px at 50% 48%, rgba(250,248,255,0.85), rgba(250,248,255,0.6) 60%, rgba(250,248,255,0.4))' }}
        />
        <AbsoluteFill>
          {ELS.map((el) => {
            if (frame < el.cue) return null;
            const t = interpolate(frame, [el.cue, el.cue + 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: FLY_EASE });
            const opacity = interpolate(frame, [el.cue, el.cue + 3], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
            const x = el.dx * (1 - t);
            const y = el.dy * (1 - t);
            const rot = el.rot * (2 - t);
            const scale = el.scale * (1.12 - 0.12 * t);
            const air = Math.max(0, 1 - t);
            // shadow scaled up by 1/scale so it reads the same size on screen
            const k = 1 / el.scale;
            const shadow =
              air > 0.01
                ? `0 ${(10 + 26 * air) * k}px ${(24 + 46 * air) * k}px rgba(19,27,46,${0.16 + 0.1 * air}), 0 ${2 * k}px ${6 * k}px rgba(19,27,46,.08)`
                : `0 ${10 * k}px ${24 * k}px rgba(19,27,46,.16), 0 ${2 * k}px ${6 * k}px rgba(19,27,46,.08)`;
            const linT = interpolate(frame, [el.cue, el.cue + 12], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
            const showGhost = linT > 0.05 && linT < 0.95;
            const glow = interpolate(frame, [el.cue + 12, el.cue + 18], [0.35, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
            const showGlow = frame >= el.cue + 12 && frame < el.cue + 18;
            const glowR = Math.min(el.box.w * el.scale, 420) * 0.5;
            const place: React.CSSProperties = {
              position: 'absolute',
              left: el.cx - el.box.w / 2,
              top: el.cy - el.box.h / 2,
              transformOrigin: 'center center',
            };
            return (
              <div key={el.key}>
                {showGhost ? (
                  <div
                    style={{
                      ...place,
                      transform: `translate(${x + el.dx * 0.08}px, ${y + el.dy * 0.08}px) rotate(${rot}deg) scale(${scale})`,
                      opacity: 0.2 * Math.max(0, 1 - linT),
                      filter: 'blur(8px)',
                    }}
                  >
                    <TexCrop page={el.page} box={el.box} radius={el.radius} />
                  </div>
                ) : null}
                <div
                  style={{
                    ...place,
                    transform: `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${scale})`,
                    opacity: opacity * (1 - 0.12 * recede),
                    filter: `saturate(${1 - 0.08 * recede})`,
                  }}
                >
                  <TexCrop page={el.page} box={el.box} radius={el.radius} style={{ boxShadow: shadow }} />
                </div>
                {showGlow ? (
                  <div
                    style={{
                      position: 'absolute',
                      left: el.cx - glowR,
                      top: el.cy - glowR,
                      width: glowR * 2,
                      height: glowR * 2,
                      borderRadius: '50%',
                      background: 'radial-gradient(circle, rgba(196,167,255,0.9), rgba(196,167,255,0) 70%)',
                      opacity: glow,
                      mixBlendMode: 'multiply',
                    }}
                  />
                ) : null}
              </div>
            );
          })}
        </AbsoluteFill>
      </AbsoluteFill>

      {/* lavender dust drifting up */}
      <AbsoluteFill>
        {DUST.map((d, i) => {
          const y = (((d.y0 - frame * d.rise) % 1080) + 1080) % 1080;
          const x = d.x + Math.sin(frame * d.swayFreq + d.phase) * d.swayAmp;
          return (
            <div key={i} style={{ position: 'absolute', left: x, top: y, width: d.size, height: d.size, borderRadius: '50%', background: C.primaryFixedDim, opacity: d.opacity }} />
          );
        })}
      </AbsoluteFill>

      {sweepOpacity > 0 ? (
        <AbsoluteFill style={{ mixBlendMode: 'overlay' }}>
          <div
            style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              left: sweepX - 300,
              width: 600,
              background: 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,1) 50%, rgba(255,255,255,0))',
              opacity: sweepOpacity,
            }}
          />
        </AbsoluteFill>
      ) : null}

      {stageLight > 0 ? (
        <AbsoluteFill
          style={{
            background: 'radial-gradient(760px 380px at 960px 500px, rgba(255,255,255,0.98), rgba(250,248,255,0.5) 55%, rgba(250,248,255,0) 75%)',
            opacity: stageLight,
          }}
        />
      ) : null}
      {vignette > 0 ? (
        <AbsoluteFill style={{ background: 'radial-gradient(1400px 900px at 50% 50%, rgba(19,27,46,0) 55%, rgba(19,27,46,0.6) 100%)', opacity: vignette }} />
      ) : null}

      {/* wordmark sign-off */}
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ textAlign: 'center', marginTop: -40 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 30 }}>
            <span style={letter(-1)}>
              <BoltMark size={124} />
            </span>
            <div style={{ fontSize: 148, fontWeight: 700, color: C.onSurface, letterSpacing: `${wordSpacing}em`, display: 'flex', lineHeight: 1.05 }}>
              {LETTERS.map((ch, i) => (
                <span key={i} style={letter(i)}>
                  {ch}
                </span>
              ))}
            </div>
          </div>
          <div style={{ position: 'relative', height: 6, width: 260, margin: '34px auto 0' }}>
            <div style={{ position: 'absolute', inset: 0, borderRadius: 3, background: C.primary, transform: `scaleX(${rule})` }} />
            {ruleExt > 0 && ruleExtFade > 0 ? (
              <>
                <div style={{ position: 'absolute', top: 2.5, height: 1, right: '100%', width: 190 * ruleExt, background: C.primary, opacity: ruleExtFade }} />
                <div style={{ position: 'absolute', top: 2.5, height: 1, left: '100%', width: 190 * ruleExt, background: C.primary, opacity: ruleExtFade }} />
              </>
            ) : null}
          </div>
          <div style={{ fontSize: 38, fontWeight: 500, letterSpacing: '-0.01em', color: C.onSurfaceVariant, marginTop: 30, opacity: tag }}>
            Built in n8n <span style={{ color: C.outlineVariant, margin: '0 0.35em' }}>·</span>
            <span style={{ color: C.primary, fontWeight: 600 }}>github.com/hamza533/ai-lead-qualifier-n8n</span>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
