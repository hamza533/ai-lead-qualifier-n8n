// Inter (OFL), bundled from @fontsource/inter. Loaded from inside the rendered component (see
// useInter) rather than at module scope: a module-scope delayRender() also runs in Remotion's
// idle helper pages, whose timers are frozen, and timed the whole render out.
import { useEffect, useState } from 'react';
import { continueRender, delayRender } from 'remotion';
import w400 from '@fontsource/inter/files/inter-latin-400-normal.woff2';
import w500 from '@fontsource/inter/files/inter-latin-500-normal.woff2';
import w600 from '@fontsource/inter/files/inter-latin-600-normal.woff2';
import w700 from '@fontsource/inter/files/inter-latin-700-normal.woff2';
import w700i from '@fontsource/inter/files/inter-latin-700-italic.woff2';

const FACES: { url: string; weight: string; style: string }[] = [
  { url: w400, weight: '400', style: 'normal' },
  { url: w500, weight: '500', style: 'normal' },
  { url: w600, weight: '600', style: 'normal' },
  { url: w700, weight: '700', style: 'normal' },
  { url: w700i, weight: '700', style: 'italic' },
];

let loading: Promise<void> | null = null;
const loadInter = () => {
  if (!loading) {
    loading = Promise.all(
      FACES.map(async (f) => {
        const face = new FontFace('Inter', `url(${f.url}) format('woff2')`, { weight: f.weight, style: f.style });
        await face.load();
        document.fonts.add(face);
      }),
    ).then(() => undefined);
  }
  return loading;
};

/** Holds the frame until Inter is registered (once per page). */
export const useInter = () => {
  const [handle] = useState(() => delayRender('Loading Inter'));
  useEffect(() => {
    loadInter()
      .catch((err) => console.error(err))
      .finally(() => continueRender(handle));
  }, [handle]);
};
