import React from 'react';
import { staticFile } from 'remotion';
import layoutJson from '../layout.json';

export type Box = { x: number; y: number; w: number; h: number };
export const layout = layoutJson as any;

export const PAGES = ['landing', 'form', 'research', 'score', 'approval', 'crm', 'results'] as const;
export type PageName = (typeof PAGES)[number];
export const tex = (page: PageName) => `textures/${page}-full.png`;
export const pageH = (page: PageName): number => layout[page].pageH;

/** A rectangle cut out of a full-page texture (no re-drawing of product UI: Q1). */
export const TexCrop: React.FC<{
  page: PageName;
  box: Box;
  radius?: number;
  style?: React.CSSProperties;
}> = ({ page, box, radius = 0, style }) => (
  <div
    style={{
      width: box.w,
      height: box.h,
      borderRadius: radius,
      overflow: 'hidden',
      backgroundColor: '#fff',
      backgroundImage: `url(${staticFile(tex(page))})`,
      backgroundSize: `1920px ${pageH(page)}px`,
      backgroundPosition: `${-box.x}px ${-box.y}px`,
      backgroundRepeat: 'no-repeat',
      ...style,
    }}
  />
);

// rounded-xl in the screens = 0.75rem = 12 CSS px = 14.4 page px
export const R_XL = 14.4;
export const R_LG = 9.6;

/** Covers the page's copyright footer (page space) so it never peeks around the caption. */
export const FooterCover: React.FC<{ page: PageName; color: string }> = ({ page, color }) => {
  const f: Box = layout[page].footer;
  return <div style={{ position: 'absolute', left: -3000, width: 7920, top: f.y, height: pageH(page) - f.y + 3000, background: color }} />;
};
