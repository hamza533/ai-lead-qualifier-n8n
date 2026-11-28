// Shot 8 — document-typewriter-reveal (demos/ui-entrance/document-typewriter-reveal/DocumentTypewriterReveal.tsx)
// Kept: blocks are written on a cue grid (each wipe a background mask that shrinks
// right-anchored, bezier(0.4,0,0.6,1)); a single 2px accent caret rides the newest
// block's reveal edge and fades 2f after it finishes (never two "pen tips"); camera starts on a
// close-up of the title and pulls back until both columns are in frame, then only breathes;
// the "history items" drop into the side rail one by one from −44px on bezier(0.2,1.15,0.3,1)
// (8f, light bounce, shadow while airborne), each landing exactly on its slot in the layout.
// Adapted: blocks = the sent email's rendered text lines, written one line at a time (7f wipe,
// next line starts as the previous ends; the demo's pairs read as two lines typing at once),
// the booking button fades in at its turn; caret = primary; the rail = the HubSpot column —
// contact & AI properties, note, follow-up task — which drop in after the email is written.
// The @-mention wash is not used (no names to mark in this document).
import React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';
import { PageCam, CamKey } from '../lib/PageCam';
import { C } from '../theme';
import { Box, FooterCover, R_XL, TexCrop, layout, pageH, tex } from './common';

const L = layout.crm;
const PAGE_H = pageH('crm');
type Line = Box & { tag: string };
// in reading order; the booking button fades in at its turn instead of being wiped
const blocks: Line[] = [...(L.lines as Line[]), { ...L.cta, tag: 'a' }].sort((a, b) => a.y - b.y);

const CUE0 = 8;
// one line at a time (STEP = WIPE): never two pen tips, never two lines appearing together
const STEP = 7;
const WIPE = 7;
const cueFor = (i: number) => CUE0 + i * STEP;
const REVEAL_EASE = Easing.bezier(0.4, 0, 0.6, 1);

export const RAIL_CUE = (i: number) => 100 + i * 10;
const RAIL_DROP = Easing.bezier(0.2, 1.15, 0.3, 1);
const railCards: Box[] = L.leftCards;

const CAM_KEYS: CamKey[] = [
  { frame: 0, cx: 1270, cy: 440, zoom: 1.25 },
  { frame: 22, cx: 1262, cy: 452, zoom: 1.21 },
  // both columns in frame, the follow-up task card ends at y≈859, above the caption band
  { frame: 96, cx: 960, cy: 849, zoom: 0.78 },
  { frame: 130, cx: 960, cy: 849, zoom: 0.782 },
  { frame: 180, cx: 960, cy: 849, zoom: 0.778 },
];

export const CrmShot: React.FC = () => {
  const frame = useCurrentFrame();
  let caretIdx = -1;
  blocks.forEach((_, i) => {
    if (frame >= cueFor(i) && frame <= cueFor(i) + WIPE + 2) caretIdx = i;
  });

  return (
    <PageCam src={tex('crm')} pageH={PAGE_H} keys={CAM_KEYS}>
      <FooterCover page="crm" color={C.surface} />
      {blocks.map((p, i) => {
        const cue = cueFor(i);
        const coverT = interpolate(frame, [cue, cue + WIPE], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: REVEAL_EASE });
        if (p.tag === 'a') {
          // button: fade the cover out (a wiped button reads as a sliver)
          return coverT > 0 ? (
            <div key={i} style={{ position: 'absolute', left: p.x - 4, top: p.y - 4, width: p.w + 8, height: p.h + 8, background: C.surfaceLowest, opacity: coverT }} />
          ) : null;
        }
        const bg = p.tag === 'div' ? C.surfaceLow : C.surfaceLowest;
        const bx = p.x - 4;
        const by = p.y - 3;
        const bw = p.w + 10;
        const bh = p.h + 6;
        const caretX = bx + bw * (1 - coverT);
        const caretH = Math.min(30, p.h - 2);
        return (
          <div key={i}>
            {coverT > 0 ? (
              <div style={{ position: 'absolute', left: bx, top: by, width: bw, height: bh, overflow: 'hidden' }}>
                <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: `${coverT * 100}%`, background: bg }} />
              </div>
            ) : null}
            {i === caretIdx ? (
              <div
                style={{
                  position: 'absolute',
                  left: caretX,
                  top: p.y + (p.h - caretH) / 2,
                  width: 2.5,
                  height: caretH,
                  background: C.primary,
                  opacity: coverT > 0 ? 1 : interpolate(frame, [cue + WIPE, cue + WIPE + 2], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
                }}
              />
            ) : null}
          </div>
        );
      })}

      {/* HubSpot column: each record card drops into its own slot */}
      {railCards.map((b, i) => {
        const cue = RAIL_CUE(i);
        const land = cue + 8;
        const patch = frame < land ? (
          <div key={`p${i}`} style={{ position: 'absolute', left: b.x - 6, top: b.y - 6, width: b.w + 12, height: b.h + 14, background: C.surface }} />
        ) : null;
        if (frame < cue) return patch;
        const t = interpolate(frame, [cue, land], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: RAIL_DROP });
        const appear = interpolate(frame, [cue, cue + 3], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        const air = Math.max(0, 1 - t);
        return (
          <React.Fragment key={i}>
            {patch}
            <div
              style={{
                position: 'absolute',
                left: b.x,
                top: b.y,
                transform: `translateY(${-44 * air}px)`,
                opacity: appear,
                borderRadius: R_XL,
                boxShadow: air > 0.02 ? `0 ${10 * air}px ${20 * air}px rgba(19,27,46,${0.16 * air})` : 'none',
              }}
            >
              <TexCrop page="crm" box={b} radius={R_XL} style={{ backgroundColor: C.surface }} />
            </div>
          </React.Fragment>
        );
      })}
    </PageCam>
  );
};
