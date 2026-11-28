// Shot 3 — lead form. PageCam (assets/lib/PageCam.tsx) push-in from the full screen onto the
// hosted form card; one move, then a true static hold for the caption (no tail drift, R1).
import React from 'react';
import { PageCam, CamKey } from '../lib/PageCam';
import { EASE_CAM } from '../theme';
import { layout, pageH, tex } from './common';

const card = layout.form.formCard;
// the whole card (incl. Send and the reply note) stays above the caption band (y < 860)
const Z = 1.12;
const TOP_MARGIN = 30; // card top lands 30px under the frame edge
export const FORM_PUSH = [22, 62] as const;

const KEYS: CamKey[] = [
  { frame: 0, cx: 960, cy: 540, zoom: 1 },
  { frame: FORM_PUSH[0], cx: 960, cy: 540, zoom: 1 },
  {
    frame: FORM_PUSH[1],
    cx: card.x + card.w / 2,
    cy: card.y - (TOP_MARGIN - 540) / Z,
    zoom: Z,
  },
];

export const FormShot: React.FC = () => <PageCam src={tex('form')} pageH={pageH('form')} keys={KEYS} ease={EASE_CAM} />;
