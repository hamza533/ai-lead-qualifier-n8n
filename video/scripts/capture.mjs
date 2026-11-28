// capture.mjs — turn the Stitch showcase screens (docs/ui/html/*.html) into video textures.
//
// Adapted from video-shotcraft assets/scripts/capture-template.mjs (pipeline stage 4):
//   1. full-page 2x textures   -> public/textures/<name>-full.png
//   2. 4x element cutouts      -> public/textures/<name>-<key>@4x.png (hero elements under push-ins)
//   3. layout.json             -> src/layout.json (element boxes in page space)
//
// Coordinate system: the screens are laid out at 1600x900 CSS px (like docs/ui/*.png) and every
// texture is shown 1920 px wide in the video, so ONE page-space unit = 1.2 CSS px. Full pages are
// captured at deviceScaleFactor 2.4 (= 2x the 1920 video width); cutouts at 4.8 (= 4x).
//
// Runs inside the official Playwright image, nothing installed locally (run from the repo root):
//   docker run --rm -v "$PWD:/repo" -w /repo mcr.microsoft.com/playwright:v1.49.1-noble \
//     sh -c "npm i --no-save --prefix /tmp/pw playwright@1.49.1 >/dev/null && \
//            NODE_PATH=/tmp/pw/node_modules node video/scripts/capture.mjs"
// The HTML pulls Tailwind and the Inter / Material Symbols fonts from CDNs, so it needs network.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
const htmlDir = path.join(repo, 'docs/ui/html');
const outDir = path.join(repo, 'video/public/textures');
const layoutPath = path.join(repo, 'video/src/layout.json');
fs.mkdirSync(outDir, { recursive: true });

const VIEWPORT = { width: 1600, height: 900 };
const UNIT = 1.2; // page-space px per CSS px
const SETTLE_MS = 900;

// Freeze CSS animations (pulse/spin) so every capture is deterministic.
const FREEZE_CSS = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';

// In-page helpers: boxes in CSS px (page coordinates) -> scaled by UNIT in node.
const HELPERS = () => {
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
  };
  const q = (sel, root = document) => root.querySelector(sel);
  const qa = (sel, root = document) => [...root.querySelectorAll(sel)];
  // smallest element whose text contains `text`, then climb to `closest`
  const byText = (text, closest) => {
    const all = qa('body *').filter((e) => e.textContent && e.textContent.includes(text));
    all.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length);
    const hit = all[0];
    return hit ? (closest ? hit.closest(closest) : hit) : null;
  };
  // tight text-line boxes of an element (one rect per rendered line)
  const lines = (el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    const rects = [...range.getClientRects()].filter((r) => r.width > 1 && r.height > 1);
    const out = [];
    for (const r of rects) {
      const prev = out.find((o) => Math.abs(o.top - r.top) < 6 || Math.abs(o.bottom - r.bottom) < 6);
      if (prev) {
        prev.left = Math.min(prev.left, r.left);
        prev.right = Math.max(prev.right, r.right);
        prev.top = Math.min(prev.top, r.top);
        prev.bottom = Math.max(prev.bottom, r.bottom);
      } else out.push({ left: r.left, right: r.right, top: r.top, bottom: r.bottom });
    }
    out.sort((a, b) => a.top - b.top);
    return out.map((o) => ({ x: o.left + scrollX, y: o.top + scrollY, w: o.right - o.left, h: o.bottom - o.top }));
  };
  window.__cap = { box, q, qa, byText, lines };
};

// Per-page element specs, evaluated in the page. Each returns { key: box | box[] | null }.
const PAGES = [
  {
    name: 'landing',
    file: '01-landing.html',
    spec: () => {
      const { box, byText, qa } = window.__cap;
      return {
        heroCard: box(byText('Draft ready for approval', 'div.shadow-xl')),
        headline: box(qa('h1')[0]),
        pipeline: box(document.querySelector('#workflow')),
      };
    },
  },
  {
    name: 'form',
    file: '02-lead-form.html',
    spec: () => {
      const { box, q, qa, byText } = window.__cap;
      const card = byText('Contact us', 'div.relative.rounded-xl');
      return {
        formCard: box(card),
        fields: qa('input, select, textarea', card).map(box),
        send: box(qa('button', card).find((b) => b.textContent.includes('Send'))),
        headline: box(q('h1')),
      };
    },
  },
  {
    name: 'research',
    file: '03-research.html',
    spec: () => {
      const { box, q, qa } = window.__cap;
      const left = q('[class~="lg:col-span-5"]');
      const right = q('[class~="lg:col-span-7"]');
      return {
        stepsCard: box(left),
        steps: qa(':scope > div.relative > div.relative', left).map(box),
        profileCard: box(right),
        factRows: qa('div.bg-surface-container-low.rounded-xl', right).filter((e) => e.querySelector('p')).map(box),
      };
    },
  },
  {
    name: 'score',
    file: '04-scorecard.html',
    spec: () => {
      const { box, q, qa } = window.__cap;
      const hero = q('div.relative.overflow-hidden.rounded-xl.bg-surface-container-lowest.shadow-md');
      const scoreBox = q('div.bg-surface-container-low.rounded-xl', hero);
      return {
        heroCard: box(hero),
        scoreBox: box(scoreBox),
        title: box(q('h1')),
        rows: qa('div[class*="md:grid-cols-12"][class*="items-center"]').map(box),
      };
    },
  },
  {
    name: 'approval',
    file: '05-approval.html',
    // the film clicks Approve on this request, so the later 10:21 outcome message for the same
    // lead is removed from the 'before' capture (it would read as already approved)
    prepare: () => document.querySelectorAll('section article')[1]?.remove(),
    // the page's own after-click state: actions row replaced by the 'Approved' banner
    after: { click: '#btn-approve', box: '#approval-actions' },
    spec: () => {
      const { box, q, qa, byText } = window.__cap;
      const msg = q('div.bg-surface-container-low.rounded-xl.p-space-lg');
      return {
        aside: box(q('aside')),
        panel: box(q('section[class~="lg:col-span-9"]')),
        message: box(msg),
        header: box(byText('Inbound demo request', 'div.flex.items-start') ?? byText('Inbound demo request')),
        hotBadge: box(qa('span', msg).find((s) => s.textContent.trim() === '82 · HOT')),
        reasons: box(byText('Top 3 reasons', 'div.flex.flex-col')),
        sources: box(q('#sources-toggle')),
        draft: box(byText('Drafted email', 'div.bg-surface-container-lowest')),
        approve: box(q('#btn-approve')),
        edit: box(q('#btn-edit')),
        reject: box(q('#btn-reject')),
      };
    },
  },
  {
    name: 'crm',
    file: '06-crm-email.html',
    spec: () => {
      const { box, q, qa, lines } = window.__cap;
      const email = q('div.bg-surface-container-lowest.rounded-xl.shadow-md.p-8');
      const leftCol = email.parentElement.parentElement.firstElementChild;
      const leftCards = [...leftCol.children].filter((e) => e.getBoundingClientRect().height > 40);
      // typewriter blocks: one per rendered text line, in reading order
      const textEls = [
        q('h1', email),
        ...qa('div.bg-surface-container-low.rounded-xl > div', email),
        ...qa(':scope > div.flex.flex-col.gap-space-md > p', email),
      ];
      const blockLines = [];
      for (const el of textEls) for (const l of lines(el)) blockLines.push({ ...l, tag: el.tagName.toLowerCase() });
      blockLines.sort((a, b) => a.y - b.y || a.x - b.x);
      const cta = q('a[href*="northwind"]', email);
      return {
        emailCard: box(email),
        sentBadge: box(qa('span', email).find((s) => s.textContent.trim() === 'Sent')),
        lines: blockLines,
        cta: box(cta),
        leftCol: box(leftCol),
        leftCards: leftCards.map(box),
      };
    },
  },
  {
    name: 'results',
    file: '07-results.html',
    spec: () => {
      const { box, q, qa, lines } = window.__cap;
      const grid = q('section[class*="lg:grid-cols-4"]');
      const nums = qa('span.font-display-lg', grid);
      const cost = qa('h3').find((h) => h.textContent.includes('0.03'));
      // tight box of just the "0.03" glyphs (the DigitRoll overlay replaces only those)
      const tn = [...cost.childNodes].find((n) => n.nodeType === 3 && n.textContent.includes('0.03'));
      const at = tn.textContent.indexOf('0.03');
      const rg = document.createRange();
      rg.setStart(tn, at);
      rg.setEnd(tn, at + 4);
      const rr = rg.getBoundingClientRect();
      return {
        costDigits: { text: '0.03', x: rr.x + scrollX, y: rr.y + scrollY, w: rr.width, h: rr.height },
        title: box(q('h1')),
        kpiCards: qa(':scope > div', grid).map(box),
        kpiNums: nums.map((n) => ({ text: n.textContent.trim(), ...lines(n)[0] })),
        costCard: box(cost.closest('section')),
        costTitle: { text: cost.textContent.trim(), ...lines(cost)[0] },
        matrix: box(q('section[class*="lg:grid-cols-12"] > div')),
      };
    },
  },
];

// 4x cutouts for elements the camera pushes in on.
const CUTOUTS = [
  { page: 'score', key: 'scoreBox', selector: 'div.relative.overflow-hidden.rounded-xl.bg-surface-container-lowest.shadow-md div.bg-surface-container-low.rounded-xl' },
];

const scaleBox = (b) => {
  if (b == null) return b;
  if (Array.isArray(b)) return b.map(scaleBox);
  const out = { ...b };
  for (const k of ['x', 'y', 'w', 'h']) if (typeof out[k] === 'number') out[k] = Math.round(out[k] * UNIT * 10) / 10;
  return out;
};

const browser = await chromium.launch();
const layout = { unit: UNIT, pageW: VIEWPORT.width * UNIT };

const open = async (dsf, file) => {
  const page = await browser.newPage({ viewport: VIEWPORT, deviceScaleFactor: dsf });
  await page.goto(`file://${path.join(htmlDir, file)}`, { waitUntil: 'networkidle' });
  await page.addStyleTag({ content: FREEZE_CSS });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(SETTLE_MS);
  await page.evaluate(HELPERS);
  return page;
};

for (const pg of PAGES) {
  const page = await open(2.4, pg.file);
  if (pg.prepare) await page.evaluate(pg.prepare);
  const pageH = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.screenshot({ path: path.join(outDir, `${pg.name}-full.png`), fullPage: true });
  // 2 CSS px strips of the outer page margin, stretched sideways by PageEdges so zoomed-out
  // shots continue the full-width header/footer bands instead of ending at the texture edge
  for (const [side, x] of [['l', 0], ['r', VIEWPORT.width - 2]]) {
    await page.screenshot({ path: path.join(outDir, `${pg.name}-edge-${side}.png`), fullPage: true, clip: { x, y: 0, width: 2, height: pageH } });
  }
  // the strip as colour bands (page units): PageEdges paints these as plain divs, which also
  // behave under the 3D/CSS-zoom camera path (a stretched 5 px image did not)
  const edgePng = fs.readFileSync(path.join(outDir, `${pg.name}-edge-l.png`)).toString('base64');
  const edgeBands = await page.evaluate(async ({ b64, unit, dsf }) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = img.width;
    cv.height = img.height;
    const ctx = cv.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const px = ctx.getImageData(0, 0, 1, img.height).data;
    const bands = [];
    for (let y = 0; y < img.height; y++) {
      const c = [px[y * 4], px[y * 4 + 1], px[y * 4 + 2]];
      const last = bands[bands.length - 1];
      if (last && Math.max(...c.map((v, i) => Math.abs(v - last.c[i]))) <= 2) last.h++;
      else bands.push({ y, h: 1, c });
    }
    const k = unit / dsf; // image px -> page units
    return bands.map((b) => ({ y: +(b.y * k).toFixed(2), h: +(b.h * k).toFixed(2), color: `rgb(${b.c.join(',')})` }));
  }, { b64: edgePng, unit: UNIT, dsf: 2.4 });
  const boxes = await page.evaluate(pg.spec);
  const footer = await page.evaluate(() => window.__cap.box(document.querySelector('footer')));
  const entry = { pageH: Math.round(pageH * UNIT), footer: scaleBox(footer), edgeBands };
  for (const [k, v] of Object.entries(boxes)) entry[k] = scaleBox(v);
  if (pg.after) {
    await page.click(pg.after.click);
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(outDir, `${pg.name}-after-full.png`), fullPage: true });
    entry.after = scaleBox(await page.evaluate((sel) => window.__cap.box(document.querySelector(sel)), pg.after.box));
  }
  layout[pg.name] = entry;
  console.log(`captured ${pg.name}-full (pageH ${entry.pageH})`);
  await page.close();
}

for (const c of CUTOUTS) {
  const file = PAGES.find((p) => p.name === c.page).file;
  const page = await open(4.8, file);
  const el = await page.$(c.selector);
  const out = `${c.page}-${c.key}@4x.png`;
  await el.screenshot({ path: path.join(outDir, out) });
  console.log(`captured ${out}`);
  await page.close();
}

await browser.close();
fs.writeFileSync(layoutPath, JSON.stringify(layout, null, 1) + '\n');
console.log('wrote', path.relative(repo, layoutPath));
