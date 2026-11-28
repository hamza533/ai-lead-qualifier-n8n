// Shot 4 — row-embed (demos/ui-entrance/row-embed/RowEmbed.tsx)
// Kept: each row drops from the air as a crop of the page texture (no re-drawing, Q1):
// perspective(900px) translateY(−120·air) rotateX(16°·air), scale 1.06→0.995 then a 4f press
// back to 1, 3f appear, 12f flight on bezier(0.3,0,0.25,1); the empty slot is covered by a
// background patch that disappears 2f after touchdown; a 2px accent seam opens from the centre
// of the row's bottom edge over 5f (out-cubic) and fades by 8f; the camera pans steadily down
// while the rows rain in.
// Adapted: rows = the five sourced company-profile facts; cue spacing 12f (demo 9f) so each
// fact is readable; seam = primary with a violet glow, clipped to the row's rounded corners
// (Q4); patch = the card's white.
import React from 'react';
import { Easing, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { PageCam, CamKey } from '../lib/PageCam';
import { C } from '../theme';
import { Box, FooterCover, R_XL, layout, pageH, tex } from './common';

const rows: Box[] = layout.research.factRows;
const PAGE_H = pageH('research');
export const ROW_CUE0 = 14;
export const ROW_STEP = 16; // next row enters only after the previous one has landed and its seam faded
const FLY = 12;
const lastLand = ROW_CUE0 + (rows.length - 1) * ROW_STEP + FLY;

const KEYS: CamKey[] = [
  { frame: 0, cx: 1060, cy: 491, zoom: 1.1 }, // page top exactly at the frame top
  // both cards centred, profile card bottom at y≈844: the caption band below stays empty page
  { frame: lastLand + 10, cx: 960, cy: 687, zoom: 1 },
];

const FLY_EASE = Easing.bezier(0.3, 0, 0.25, 1);
const src = staticFile(tex('research'));

export const ResearchShot: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <PageCam src={tex('research')} pageH={PAGE_H} keys={KEYS} ease={Easing.linear}>
      <FooterCover page="research" color={C.surface} />
      {rows.map((r, i) => {
        const cue = ROW_CUE0 + i * ROW_STEP;
        const land = cue + FLY;
        const patchOpacity = interpolate(frame, [land, land + 2], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

        let flyer: React.ReactNode = null;
        if (frame >= cue && frame < cue + 16) {
          const p = interpolate(frame, [cue, cue + FLY], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: FLY_EASE });
          const appear = interpolate(frame, [cue, cue + 2], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          const scale =
            frame < land
              ? 1.06 - 0.065 * p
              : interpolate(frame, [land, land + 4], [0.995, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad) });
          const air = 1 - p;
          flyer = (
            <div
              style={{
                position: 'absolute',
                left: r.x,
                top: r.y,
                width: r.w,
                height: r.h,
                borderRadius: R_XL,
                backgroundColor: C.surfaceLow,
                backgroundImage: `url(${src})`,
                backgroundSize: `1920px ${PAGE_H}px`,
                backgroundPosition: `-${r.x}px -${r.y}px`,
                opacity: appear,
                transform: `perspective(900px) translateY(${-120 * air}px) rotateX(${16 * air}deg) scale(${scale})`,
                boxShadow: `0 ${30 * air}px ${60 * air}px rgba(19,27,46,${0.2 * air}), 0 ${8 * air}px ${16 * air}px rgba(19,27,46,${0.1 * air})`,
                zIndex: 3,
              }}
            />
          );
        }

        let seam: React.ReactNode = null;
        if (frame >= land && frame < land + 8) {
          const spread = interpolate(frame, [land, land + 5], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
          const seamOpacity = interpolate(frame, [land, land + 2, land + 8], [1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          const seamW = r.w * spread;
          seam = (
            // clip box = the row's own rounded rect, so the seam never spills past the corners
            <div
              style={{
                position: 'absolute',
                left: r.x,
                top: r.y,
                width: r.w,
                height: r.h,
                borderRadius: R_XL,
                overflow: 'hidden',
                zIndex: 4,
                opacity: seamOpacity,
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  left: (r.w - seamW) / 2,
                  top: r.h - 2.5,
                  width: seamW,
                  height: 2.5,
                  background: C.primary,
                  boxShadow: '0 0 7px rgba(124,58,237,0.55)',
                }}
              />
            </div>
          );
        }

        return (
          <React.Fragment key={i}>
            {patchOpacity > 0 ? (
              <div
                style={{
                  position: 'absolute',
                  left: r.x - 2,
                  top: r.y - 2,
                  width: r.w + 4,
                  height: r.h + 4,
                  background: C.surfaceLowest,
                  opacity: patchOpacity,
                  zIndex: 1,
                }}
              />
            ) : null}
            {flyer}
            {seam}
          </React.Fragment>
        );
      })}
    </PageCam>
  );
};
