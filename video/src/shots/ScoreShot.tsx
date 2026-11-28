// Shot 5 — spotlight-hero-card (demos/opening/spotlight-hero-card/SpotlightHeroCard.tsx)
// Kept (all times are the demo's, shifted by OFF=28f for a longer roving phase over the
// criterion rows): spotlight with intermediate stations then lock + 6% pulse, pool radius
// 620→420→360, vignette 0.16→0.42; static full page zoom 0.78, 16f push to zoom 2.6 with
// rotY 34° (left camera) + rotX 8° + rotZ 2°, persp 1200, focus 30px left of the hero centre;
// rise 10f on bezier(0.2,1.25,0.3,1) (landing metaphor → overshoot), 54f hover with a 4px sin
// bob (40f period, z = 110·lift), 18f reseat with a 0.997 press; two perimeter-beam laps
// (lap1 14f bright 5+2.5px, lap2 20f at 0.62 opacity 3.5+1.75px), "0.14 1" dash; vacated-slot
// patch + breathing outline; 4x hi-res cutout cross-fades in during the push (6f); camera fully
// locked after the reseat (no tail drift).
// Adapted: hero = the TOTAL SCORE box (82 / 100) on the scorecard; colours = primary beam with
// a white core, lavender-white light pool, a light violet vignette (max 0.12, not the card's 0.42 dark wash); the optional 3D annotation is left
// out (the caption carries the line).
import React from 'react';
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { PageCam, CamKey } from '../lib/PageCam';
import { C } from '../theme';
import { R_XL, layout, pageH, tex } from './common';

const PAGE_H = pageH('score');
const CARD = layout.score.scoreBox;
const MCX = CARD.x + CARD.w / 2;
const MCY = CARD.y + CARD.h / 2;
const RADIUS = R_XL;
const OFF = 28; // longer roving phase over the criteria rows

const PRIMARY = C.primary;
const BEAM_CORE = 'rgba(255,255,255,0.98)';
const PATCH = '#fbfaff';

// overview: the whole criteria table sits above the caption band (rows end at y≈874)
const OV = { cx: 960, cy: 640, zoom: 0.8 };
// close-up focus sits 40 page px above the box centre: the box lands a little lower, the
// "81 seconds" pill is fully in frame at the top and the table header drops out of the bottom
const FOCUS_DY = -40;
const CAM_KEYS: CamKey[] = [
  { frame: 0, ...OV, rotX: 0, rotY: 0, rotZ: 0, persp: 1200 },
  { frame: OFF + 32, ...OV, rotX: 0, rotY: 0, rotZ: 0, persp: 1200 },
  { frame: OFF + 48, cx: MCX - 30, cy: MCY + FOCUS_DY, zoom: 2.6, rotX: 8, rotY: 34, rotZ: 2, persp: 1200 },
  { frame: 400, cx: MCX - 30, cy: MCY + FOCUS_DY, zoom: 2.6, rotX: 8, rotY: 34, rotZ: 2, persp: 1200 },
];
const PUSH_EASE = Easing.bezier(0.35, 0, 0.2, 1);
const POP_EASE = Easing.bezier(0.2, 1.25, 0.3, 1);
const RESEAT_EASE = Easing.bezier(0.4, 0, 0.3, 1.05);

// screen-space % of a page point in the overview framing
const scr = (px: number, py: number) => [
  ((960 + (px - OV.cx) * OV.zoom) / 1920) * 100,
  ((540 + (py - OV.cy) * OV.zoom) / 1080) * 100,
];
const rows = layout.score.rows;
const rowY = (i: number) => rows[i].y + rows[i].h / 2;
const [lockX, lockY] = scr(MCX, MCY);
// stations: rating dots of row 1 → points of row 2 → reason of row 3 → rating of row 4 → lock
const ST = [scr(560, rowY(0)), scr(560, rowY(0)), scr(1030, rowY(1)), scr(760, rowY(2)), scr(1200, rowY(3)), [lockX, lockY], [51, 59]];
const ST_F = [4, 10, 22, 34, 46, OFF + 28, OFF + 48];

export const SCORE_TIMES = { rise: OFF + 48, beam1: OFF + 60, reseatEnd: OFF + 130 };

export const ScoreShot: React.FC = () => {
  const frame = useCurrentFrame();
  const f = frame - OFF; // demo-relative clock for the hero arc

  const macroIn = interpolate(frame, [0, 8], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.3, 0, 0.2, 1) });

  const spotEase = Easing.bezier(0.4, 0, 0.3, 1);
  const spotX = interpolate(frame, ST_F, ST.map((s) => s[0]), { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: spotEase });
  const spotY = interpolate(frame, ST_F, ST.map((s) => s[1]), { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: spotEase });
  const spotOn = interpolate(frame, [2, 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const poolBase = interpolate(f, [22, 32, 48], [620, 420, 360], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.4, 0, 0.3, 1) });
  const poolPulse = interpolate(f, [32, 36, 41], [0, 0.06, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const poolRx = poolBase * (1 + poolPulse);
  const poolRy = poolBase * 0.8 * (1 + poolPulse);
  // card value 0.16→0.34→0.42 lowered to ≤0.12: the light DESIGN.md surface must stay light
  const vignette = interpolate(f, [22, 32, 48], [0.06, 0.1, 0.12], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const rise = interpolate(f, [48, 58], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: POP_EASE });
  const reseat = interpolate(f, [112, 130], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: RESEAT_EASE });
  const lift = rise * (1 - reseat);
  const bob = Math.sin(((f - 58) / 40) * Math.PI * 2) * 4 * lift;
  const z = 110 * lift + bob;
  const landed = f >= 130;
  const press = interpolate(f, [126, 129, 130], [1, 0.997, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const shadow = `0 ${8 * lift}px ${10 + 12 * lift}px rgba(19,27,46,${0.16 * lift}), 0 ${46 * lift}px ${90 * lift}px rgba(19,27,46,${0.2 * lift})`;

  const slotVis = Math.min(1, rise * 2) * (1 - reseat);
  const landPulse = interpolate(f, [126, 130, 134], [0, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const slotEdge = Math.min(1, 0.4 * (1 - reseat)) + landPulse * 0.6;

  const beam1Prog = interpolate(f, [60, 74], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.linear });
  const beam1On = f >= 59 && f <= 75;
  const beam2Prog = interpolate(f, [80, 100], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(0.4, 0, 0.4, 1) });
  const beam2On = f >= 79 && f <= 101;
  const beamTrail = interpolate(f, [100, 112], [0.35, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const bw = CARD.w + 6;
  const bh = CARD.h + 6;

  const hiresIn = interpolate(f, [32, 38], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ backgroundColor: C.surface }}>
      <AbsoluteFill style={{ opacity: macroIn }}>
        <PageCam src={tex('score')} pageH={PAGE_H} keys={CAM_KEYS} ease={PUSH_EASE}>
          <div style={{ transformStyle: 'preserve-3d' }}>
            {slotVis > 0.02 ? (
              <div
                style={{
                  position: 'absolute',
                  left: CARD.x - 2,
                  top: CARD.y - 2,
                  width: CARD.w + 4,
                  height: CARD.h + 4,
                  background: PATCH,
                  borderRadius: RADIUS,
                  boxShadow: `inset 0 0 26px rgba(99,14,212,${0.1 * slotEdge})`,
                  opacity: slotVis,
                }}
              >
                <div style={{ position: 'absolute', inset: 0, borderRadius: RADIUS, border: `1.5px solid ${C.primaryContainer}`, opacity: slotEdge }} />
              </div>
            ) : null}

            <div
              style={{
                position: 'absolute',
                left: CARD.x,
                top: CARD.y,
                width: CARD.w,
                height: CARD.h,
                transform: `translateZ(${z}px) scale(${press})`,
                transformOrigin: 'center center',
                transformStyle: 'preserve-3d',
              }}
            >
              <div style={{ position: 'absolute', inset: 0, borderRadius: RADIUS, overflow: 'hidden', boxShadow: landed ? 'none' : shadow }}>
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    backgroundImage: `url(${staticFile(tex('score'))})`,
                    backgroundSize: `1920px ${PAGE_H}px`,
                    backgroundPosition: `-${CARD.x}px -${CARD.y}px`,
                  }}
                />
                <Img
                  src={staticFile('textures/score-scoreBox@4x.png')}
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block', opacity: hiresIn }}
                />
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'linear-gradient(160deg, rgba(255,255,255,0.45), transparent 40%)',
                    opacity: lift,
                  }}
                />
              </div>
              <div style={{ position: 'absolute', inset: 0, borderRadius: RADIUS, boxShadow: `inset 0 0 0 1px rgba(255,255,255,${0.7 * lift})` }} />

              {(beam1On || beam2On) && lift > 0.4 ? (
                <svg
                  width={bw}
                  height={bh}
                  viewBox={`0 0 ${bw} ${bh}`}
                  style={{
                    position: 'absolute',
                    left: -3,
                    top: -3,
                    overflow: 'visible',
                    opacity: beam1On ? 1 : 0.62,
                    filter: `drop-shadow(0 0 6px ${C.primaryContainer}) drop-shadow(0 0 18px rgba(210,187,255,0.7))`,
                  }}
                >
                  <rect x={2} y={2} width={bw - 4} height={bh - 4} rx={RADIUS} fill="none" stroke={PRIMARY} strokeWidth={beam1On ? 5 : 3.5} strokeLinecap="round" pathLength={1} strokeDasharray="0.14 1" strokeDashoffset={-(beam1On ? beam1Prog : beam2Prog)} />
                  <rect x={2} y={2} width={bw - 4} height={bh - 4} rx={RADIUS} fill="none" stroke={BEAM_CORE} strokeWidth={beam1On ? 2.5 : 1.75} strokeLinecap="round" pathLength={1} strokeDasharray="0.14 1" strokeDashoffset={-(beam1On ? beam1Prog : beam2Prog)} />
                </svg>
              ) : null}

              {beamTrail > 0.01 ? (
                <div style={{ position: 'absolute', inset: -3, borderRadius: RADIUS + 3, border: `1.5px solid ${C.primaryContainer}`, opacity: beamTrail }} />
              ) : null}
            </div>
          </div>
        </PageCam>

        {/* roving / locking spotlight: lavender-white pool + navy falloff outside */}
        <AbsoluteFill
          style={{
            background: `radial-gradient(${poolRx}px ${poolRy}px at ${spotX}% ${spotY}%, rgba(255,255,255,0.40), rgba(246,242,255,0.10) 45%, rgba(37,0,90,${vignette * spotOn}) 100%)`,
            opacity: spotOn,
          }}
        />
        <AbsoluteFill
          style={{
            background: `radial-gradient(300px 220px at ${spotX - 6}% ${spotY + 10}%, rgba(255,255,255,0.16), transparent 70%)`,
            opacity: spotOn * 0.7,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
