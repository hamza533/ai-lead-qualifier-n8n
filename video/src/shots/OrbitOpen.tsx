// Shot 1 — orbit-ring-title-open (demos/opening/orbit-ring-title-open/OrbitRingTitleOpen.tsx)
// Kept from the card: 8 cards at 45° on a 700×375 ellipse, 0.3 rad/s, cards never tilt, depth
// only via sin θ (±9% scale + z order from the same value), ring opens 0.62→1 over 0.7s with the
// per-card fade windows [0.06+0.05i, 0.42+0.05i]s, card content frozen until PLAY_START=24f,
// blur-slide title (blur走满 0.9s / travel 0.3s / 1f stagger / bezier(.22,1,.36,1)), marker
// sweep by spring(damping 14) under the key phrase, whole-line defocus exit (blur 0→6.5px),
// then the ring keeps turning alone as the hand-off.
// Adapted: the cards are the seven LeadPilot screens (+ the landing pipeline) and "play" by
// slowly scrolling their own page once unfrozen; title = LeadPilot wordmark + the tagline, the
// marker is primary-fixed lavender; the shot is 170f so the title holds > 2s.
import React from 'react';
import { AbsoluteFill, Easing, Freeze, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, INTER } from '../theme';
import { PageName, pageH, tex } from './common';

export const RX = 700;
export const RY = 375;
const CW = 380;
const CH = 214;
const N = 8;
const ROT_SPEED = 0.3;
const RING_IN = 0.7;
const RING_SCALE_FROM = 0.62;
const PLAY_START = 24;
const DEPTH_SCALE = 0.09;

const H_LEAD = 0.35;
const H_DUR = 0.9;
const H_TRAVEL = 0.3;
const H_STAGGER = 1 / 30;
const H_EASE = Easing.bezier(0.22, 1, 0.36, 1);

const WORDMARK = 'LeadPilot';
const W_SIZE = 150;
const TAG_SIZE = 48;
const TAG_LEAD = 0.8; // s: tagline words start once the wordmark is mostly in
const TAG_STAGGER = 2 / 30; // per word
const TAG_LINES: { text: string; hl?: boolean }[][] = [
  [{ text: 'Every' }, { text: 'new' }, { text: 'lead' }, { text: 'researched,' }, { text: 'scored' }],
  [{ text: 'and' }, { text: 'answered' }, { text: 'within', hl: true }, { text: 'minutes.', hl: true }],
];
const MARKER_AT_F = 60; // last tagline word's ease ≈ 0.95 — "words in place, then sweep"
const EXIT_AT = 140 / 30;
const EXIT_DUR = 0.34;
const EXIT_BLUR = 6.5;

const MESH_BG =
  'radial-gradient(52% 44% at 18% 22%, rgba(124,58,237,0.12) 0%, rgba(124,58,237,0) 70%),' +
  'radial-gradient(46% 42% at 84% 18%, rgba(196,167,255,0.22) 0%, rgba(196,167,255,0) 70%),' +
  'radial-gradient(58% 50% at 78% 84%, rgba(99,14,212,0.08) 0%, rgba(99,14,212,0) 70%),' +
  'radial-gradient(50% 46% at 24% 88%, rgba(210,187,255,0.22) 0%, rgba(210,187,255,0) 70%),' +
  `linear-gradient(180deg, ${C.surface} 0%, #f3f1fd 100%)`;

// one card = the top of a screen; once unfrozen it scrolls its own page a little ("playing")
const CARDS: { page: PageName; y0: number; scroll: number }[] = [
  { page: 'landing', y0: 0, scroll: 140 },
  { page: 'form', y0: 0, scroll: 90 },
  { page: 'research', y0: 0, scroll: 95 },
  { page: 'score', y0: 0, scroll: 160 },
  { page: 'approval', y0: 0, scroll: 150 },
  { page: 'crm', y0: 0, scroll: 160 },
  { page: 'results', y0: 0, scroll: 170 },
  { page: 'landing', y0: 300, scroll: 140 },
];

const ScreenTile: React.FC<{ page: PageName; y0: number; scroll: number }> = ({ page, y0, scroll }) => {
  const f = useCurrentFrame();
  const y = y0 + scroll * interpolate(f, [0, 140], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad) });
  // 960×540 tile = the 1920×1080 viewport of the page at half size
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: `url(${staticFile(tex(page))})`,
        backgroundSize: `960px ${pageH(page) / 2}px`,
        backgroundPosition: `0px ${-y / 2}px`,
        backgroundColor: C.surface,
        backgroundRepeat: 'no-repeat',
      }}
    />
  );
};

export const BoltMark: React.FC<{ size: number; style?: React.CSSProperties }> = ({ size, style }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.25,
      background: C.primary,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: `0 ${size * 0.08}px ${size * 0.3}px rgba(99,14,212,0.28)`,
      ...style,
    }}
  >
    <svg viewBox="0 0 24 24" width={size * 0.6} height={size * 0.6}>
      <path
        fill="#fff"
        d="M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z"
      />
    </svg>
  </div>
);

export const OrbitOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const ringIn = interpolate(t, [0, RING_IN], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const ringScale = RING_SCALE_FROM + (1 - RING_SCALE_FROM) * ringIn;
  const rot = t * ROT_SPEED;
  const markerScale = spring({ frame: frame - MARKER_AT_F, fps, config: { damping: 14 } });
  const exitQ = interpolate(t, [EXIT_AT, EXIT_AT + EXIT_DUR], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const blurSlide = (at: number, size: number): React.CSSProperties => {
    const pMain = interpolate(t, [at, at + H_DUR], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: H_EASE });
    const pTravel = interpolate(t, [at, at + H_TRAVEL], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: H_EASE });
    return {
      display: 'inline-block',
      whiteSpace: 'pre',
      position: 'relative',
      zIndex: 1,
      transformOrigin: '50% 55%',
      opacity: pMain,
      filter: pMain < 0.999 ? `blur(${(1 - pMain) * (size / 6)}px)` : undefined,
      transform: `translateY(${(1 - pTravel) * size * 0.22}px)`,
    };
  };

  const exitStyle: React.CSSProperties = {
    opacity: 1 - exitQ,
    filter: exitQ > 0.01 ? `blur(${exitQ * EXIT_BLUR}px)` : undefined,
  };

  let wordIdx = 0;
  return (
    <AbsoluteFill style={{ background: MESH_BG, fontFamily: INTER }}>
      {CARDS.map((card, i) => {
        const theta = -Math.PI / 2 + (i * Math.PI * 2) / N + rot;
        const x = 960 + Math.cos(theta) * RX * ringScale;
        const y = 540 + Math.sin(theta) * RY * ringScale;
        const depth = Math.sin(theta);
        const s = 1 + DEPTH_SCALE * depth;
        const op = interpolate(t, [0.06 + i * 0.05, 0.42 + i * 0.05], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x - (CW * s) / 2,
              top: y - (CH * s) / 2,
              width: CW * s,
              height: CH * s,
              borderRadius: 12,
              overflow: 'hidden',
              background: C.surface,
              opacity: op,
              zIndex: 10 + Math.round(depth * 5),
              boxShadow: `0 0 0 1px rgba(19,27,46,0.08), 0 14px 34px rgba(19,27,46,0.13)`,
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                width: 960,
                height: 540,
                transform: `scale(${(CW * s) / 960})`,
                transformOrigin: 'top left',
              }}
            >
              <Freeze frame={Math.max(0, frame - PLAY_START)}>
                <ScreenTile {...card} />
              </Freeze>
            </div>
          </div>
        );
      })}

      {/* static soft surface pool behind the title (not a second moving element) */}
      <AbsoluteFill
        style={{
          zIndex: 25,
          background: `radial-gradient(640px 300px at 50% 50%, rgba(250,248,255,0.92) 0%, rgba(250,248,255,0.75) 55%, rgba(250,248,255,0) 100%)`,
          opacity: ringIn * (1 - exitQ * 0.6),
        }}
      />

      <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', zIndex: 30 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: -30 }}>
          {/* wordmark */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 34, ...exitStyle }}>
            <div style={blurSlide(H_LEAD - H_STAGGER, W_SIZE)}>
              <BoltMark size={128} />
            </div>
            <div
              style={{
                fontSize: W_SIZE,
                fontWeight: 700,
                letterSpacing: '-0.045em',
                color: C.onSurface,
                whiteSpace: 'nowrap',
                lineHeight: 1.05,
              }}
            >
              {Array.from(WORDMARK).map((ch, i) => (
                <span key={i} style={blurSlide(H_LEAD + i * H_STAGGER, W_SIZE)}>
                  {ch}
                </span>
              ))}
            </div>
          </div>
          {/* tagline, two lines, marker under the key phrase */}
          <div style={{ marginTop: 34, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, ...exitStyle }}>
            {TAG_LINES.map((line, li) => {
              const plain = line.filter((w) => !w.hl);
              const hl = line.filter((w) => w.hl);
              const word = (w: { text: string }, k: number) => {
                const at = TAG_LEAD + wordIdx++ * TAG_STAGGER;
                return (
                  <span key={k} style={blurSlide(at, TAG_SIZE)}>
                    {w.text}
                  </span>
                );
              };
              return (
                <div
                  key={li}
                  style={{
                    fontSize: TAG_SIZE,
                    fontWeight: 600,
                    letterSpacing: '-0.02em',
                    color: C.onSurface,
                    whiteSpace: 'nowrap',
                    display: 'flex',
                    columnGap: '0.26em',
                    lineHeight: 1.22,
                  }}
                >
                  {plain.map(word)}
                  {hl.length ? (
                    <span style={{ position: 'relative', display: 'inline-flex', columnGap: '0.26em' }}>
                      <span
                        aria-hidden
                        style={{
                          position: 'absolute',
                          inset: '0.08em -0.14em 0.02em',
                          background: C.primaryFixed,
                          transformOrigin: 'left center',
                          transform: `scaleX(${markerScale})`,
                          borderRadius: 8,
                          zIndex: 0,
                        }}
                      />
                      {hl.map((w, k) => (
                        <span key={k} style={{ ...blurSlide(TAG_LEAD + wordIdx++ * TAG_STAGGER, TAG_SIZE), color: C.primary }}>
                          {w.text}
                        </span>
                      ))}
                    </span>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
