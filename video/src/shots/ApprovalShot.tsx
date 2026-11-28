// Shot 7 — cursor-flyover (demos/camera/cursor-flyover/CursorFlyover.tsx)
// Kept: camera = lookup table of steps (overview + 4 close-ups), five channels tx/ty/s/cx/cy
// accumulated with `acc` + inOutCubic; equal move/hold rhythm; the cursor's coordinates come
// from the SAME table and interpolation as the camera (one system), with scale(1/s) so it keeps
// its screen size; a click ripple (ring 0.3→1.9×, fading) and a cursor-tip flash at the start of
// each hold; the page fades in from a 5px blur during the overview.
// Adapted: world = the Slack approval screen in page px (1920 wide) instead of a 480×270 mock;
// stops = lead header + HOT badge → reasons + sources → drafted email → actions, the last click
// lands on Approve (the button darkens, then cross-fades to the page's own "✓ Approved by you · email
// sent · CRM updated" state, captured by clicking it). Holds are longer than the demo's
// (30f vs ~14f) so each stop can be read; overview scale 0.8, close-ups 1.5–1.62 (≤2.2, card).
import React from 'react';
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { PageEdges } from '../lib/PageCam';
import { C } from '../theme';
import { Box, R_LG, layout, pageH, tex } from './common';

const L = layout.approval;
const PAGE_H = pageH('approval');
const ctr = (b: Box) => [b.x + b.w / 2, b.y + b.h / 2];

type Step = { tx: number; ty: number; s: number; cx: number; cy: number };
const CAM: Step[] = [
  { tx: 960, ty: 690, s: 0.8, cx: 1250, cy: 560 },
  // 1: lead header + 82 · HOT
  { tx: 1180, ty: 362, s: 1.5, cx: ctr(L.hotBadge)[0] - 6, cy: ctr(L.hotBadge)[1] + 2 },
  // 2: top 3 reasons + "2 sources attached"
  { tx: 1179, ty: 440, s: 1.6, cx: ctr(L.sources)[0] + 30, cy: ctr(L.sources)[1] + 2 },
  // 3: drafted email
  { tx: 1180, ty: 680, s: 1.5, cx: 1180, cy: 662 },
  // 4: actions — click Approve
  { tx: 1179, ty: 770, s: 1.6, cx: ctr(L.approve)[0] - 4, cy: ctr(L.approve)[1] + 2 },
];
export const FLY_WIN: [number, number][] = [
  [40, 62],
  [92, 114],
  [144, 166],
  [196, 218],
];
const KEY: (keyof Step)[] = ['tx', 'ty', 's', 'cx', 'cy'];
// union of the button row (before) and the banner (after), padded, in page space
const AFTER = (() => {
  const a = L.after as Box;
  const b = L.approve as Box;
  const y0 = Math.min(a.y, b.y) - 4;
  const y1 = Math.max(a.y + a.h, b.y + b.h) + 4;
  return { x: a.x - 4, y: y0, w: a.w + 8, h: y1 - y0 };
})();
const RIPPLE = 14; // frames (demo: 0.055 of 180f ≈ 10f)

const inOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const seg = (t: number, a: number, b: number) => Math.min(1, Math.max(0, (t - a) / (b - a)));
const acc = (frame: number): Step => {
  const out = { ...CAM[0] };
  let prev = CAM[0];
  FLY_WIN.forEach((w, i) => {
    const u = inOutCubic(seg(frame, w[0], w[1]));
    const to = CAM[i + 1];
    for (const k of KEY) out[k] += u * (to[k] - prev[k]);
    prev = to;
  });
  return out;
};

export const ApprovalShot: React.FC = () => {
  const frame = useCurrentFrame();
  const v = acc(frame);
  const fade = interpolate(frame, [0, 24], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });

  let click = 0;
  let hold = 0;
  let clickIdx = -1;
  FLY_WIN.forEach((w, i) => {
    const c = interpolate(frame, [w[1], w[1] + RIPPLE], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
    const next = FLY_WIN[i + 1] ? FLY_WIN[i + 1][0] : 1e9;
    if (frame >= w[1] && frame < next) {
      click = c;
      hold = 1;
      clickIdx = i;
    }
  });
  const ripple = hold && click < 1 ? click : 1;
  const approved = interpolate(frame, [FLY_WIN[3][1] + 4, FLY_WIN[3][1] + 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const pressing = clickIdx === 3 ? interpolate(frame, [FLY_WIN[3][1], FLY_WIN[3][1] + 2, FLY_WIN[3][1] + 8], [0, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) : 0;

  return (
    <AbsoluteFill style={{ background: C.surface, overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: 1920,
          height: PAGE_H,
          transformOrigin: '0 0',
          transform: `translate(${960 - v.tx * v.s}px, ${540 - v.ty * v.s}px) scale(${v.s})`,
          opacity: fade,
        }}
      >
        <div style={{ position: 'absolute', inset: 0, filter: fade < 0.999 ? `blur(${(1 - fade) * 5}px)` : undefined }}>
          <PageEdges src={tex('approval')} pageH={PAGE_H} />
          <Img src={staticFile(tex('approval'))} style={{ position: 'absolute', width: 1920, height: PAGE_H }} />
          {/* Approve press: the button darkens for a few frames under the click */}
          {pressing > 0 ? (
            <div
              style={{
                position: 'absolute',
                left: L.approve.x,
                top: L.approve.y,
                width: L.approve.w,
                height: L.approve.h,
                borderRadius: R_LG,
                background: 'rgba(37,0,90,0.35)',
                opacity: pressing,
              }}
            />
          ) : null}
          {/* the page's own after-click state (captured by clicking #btn-approve): the action
              row becomes "✓ Approved by you · email sent · CRM updated" */}
          {approved > 0 ? (
            <div style={{ position: 'absolute', left: AFTER.x, top: AFTER.y, width: AFTER.w, height: AFTER.h, overflow: 'hidden', opacity: approved }}>
              <Img src={staticFile('textures/approval-after-full.png')} style={{ position: 'absolute', left: -AFTER.x, top: -AFTER.y, width: 1920 }} />
            </div>
          ) : null}
        </div>

        {/* click ripple (world-anchored, counter-scaled to keep its screen size) */}
        <div
          style={{
            position: 'absolute',
            left: v.cx,
            top: v.cy,
            width: 56,
            height: 56,
            borderRadius: '50%',
            border: `3px solid ${C.primaryContainer}`,
            boxSizing: 'border-box',
            opacity: hold ? (1 - ripple) * 0.9 : 0,
            transform: `translate(-50%,-50%) scale(${(0.3 + ripple * 1.6) / v.s})`,
          }}
        />
        {/* cursor */}
        <svg
          viewBox="0 0 24 24"
          style={{
            position: 'absolute',
            left: v.cx,
            top: v.cy,
            width: 44,
            height: 44,
            transformOrigin: '0 0',
            transform: `scale(${1 / v.s}) translate(-7.3px,-3.7px)`,
            filter: 'drop-shadow(0 4px 6px rgba(19,27,46,0.45))',
            opacity: fade,
          }}
        >
          <path
            d="M4 2 L4 19 L9 14.4 L12.2 21.5 L15.4 20 L12.2 13 L19 12.6 Z"
            fill={hold && click > 0 && click < 0.4 ? C.primaryFixed : '#fff'}
            stroke={C.onSurface}
            strokeWidth={1.2}
            strokeLinejoin="round"
          />
        </svg>
      </div>
    </AbsoluteFill>
  );
};
