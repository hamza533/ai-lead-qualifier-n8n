// Shot 10 — spot-check results. PageCam (assets/lib/PageCam.tsx) settles on the KPI row, then
// DigitRoll (assets/lib/DigitRoll.tsx) rolls each KPI value in (patch over the baked-in number,
// same Inter weight/size/tracking as the screen: display-lg 36px → 43.2 page px, 700, −0.025em).
// Rules (review round 2):
// - rolls start only after the camera has settled (push ends at f34, first roll f36);
// - only the significant digits roll, from blank (no "000%", "00 s"); "/ 5", "s", "%" are static;
// - the settled values hold ≥ 1.5 s before the camera moves on (last settles f78, pan at f125);
// - the cost banner's "$0.03" is the page's own static text (never "$0.00" on screen), and the
//   caption that states 81 s / $0.03 only appears once the banner is framed (timeline.ts).
// Values are exactly the screen's (eval/results-spotcheck.md): 5 / 5, 100%, 81 s, 100%, ≈ $0.03.
import React from 'react';
import { PageCam, CamKey } from '../lib/PageCam';
import { DigitRoll } from '../lib/DigitRoll';
import { C, EASE_CAM, INTER } from '../theme';
import { FooterCover, layout, pageH, tex } from './common';

const L = layout.results;
const PAGE_H = pageH('results');
export const ROLL_AT = [36, 40, 44, 48];
export const PAN = [125, 160] as const;

const KEYS: CamKey[] = [
  { frame: 0, cx: 960, cy: 560, zoom: 1 },
  { frame: 8, cx: 960, cy: 560, zoom: 1 },
  { frame: 34, cx: 960, cy: 410, zoom: 1.25 },
  { frame: PAN[0], cx: 960, cy: 410, zoom: 1.25 },
  // cost banner at y≈685–856, footer covered: the caption band below is empty page
  { frame: PAN[1], cx: 960, cy: 1120, zoom: 1.25 },
];

type Num = { text: string; x: number; y: number; w: number; h: number };

// which part of each KPI rolls; the rest is static text
const split = (text: string) => {
  const m = text.match(/^(\d+)(.*)$/);
  return m ? { roll: m[1], rest: m[2] } : { roll: '', rest: text };
};

const Roll: React.FC<{ n: Num; delay: number }> = ({ n, delay }) => {
  const size = 43.2;
  const lineH = size * 1.15;
  const { roll, rest } = split(n.text);
  const font: React.CSSProperties = { fontFamily: INTER, fontSize: size, fontWeight: 700, letterSpacing: '-0.025em', color: C.onSurface, lineHeight: `${lineH}px`, whiteSpace: 'pre' };
  return (
    <>
      <div style={{ position: 'absolute', left: n.x - 3, top: n.y - 1, width: n.w + 6, height: n.h + 2, background: C.surfaceLowest }} />
      <div style={{ position: 'absolute', left: n.x, top: n.y + (n.h - lineH) / 2, height: lineH, display: 'flex', alignItems: 'flex-start' }}>
        <DigitRoll value={roll} delay={delay} fontSize={size} fontWeight={700} letterSpacing="-0.025em" color={C.onSurface} blankStart />
        <span style={font}>{rest}</span>
      </div>
    </>
  );
};

export const ResultsShot: React.FC = () => {
  const nums: Num[] = L.kpiNums;
  return (
    <PageCam src={tex('results')} pageH={PAGE_H} keys={KEYS} ease={EASE_CAM}>
      <FooterCover page="results" color={C.surface} />
      {nums.map((n, i) => (
        <Roll key={i} n={n} delay={ROLL_AT[i]} />
      ))}
    </PageCam>
  );
};
