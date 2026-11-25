// Render the Stitch showcase HTML (docs/ui/html/*.html) to
//   docs/ui/NN-name.png       1920x1080 frames for the demo video and Upwork cover
//   docs/ui/full/NN-name.png  full-page images (1600 px wide) for the README
//
// Runs inside the official Playwright image so nothing is installed locally:
//   docker run --rm -v "$PWD:/repo" -w /repo mcr.microsoft.com/playwright:v1.49.1-noble \
//     sh -c "npm i --no-save --prefix /tmp/pw playwright@1.49.1 >/dev/null && \
//            NODE_PATH=/tmp/pw/node_modules node scripts/render_ui_frames.mjs"
import { readdirSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const htmlDir = path.resolve("docs/ui/html");
const outDir = path.resolve("docs/ui");
// 1600x900 CSS pixels at 1.2x = 1920x1080 PNG
const viewport = { width: 1600, height: 900 };

const renders = [
  { dir: outDir, viewport, deviceScaleFactor: 1.2, fullPage: false },
  // 1280 CSS px (Stitch's design width) at 1.25x = 1600 px wide, like Stitch's own export
  { dir: path.join(outDir, "full"), viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1.25, fullPage: true },
];

const browser = await chromium.launch();
for (const r of renders) {
  const page = await browser.newPage({ viewport: r.viewport, deviceScaleFactor: r.deviceScaleFactor });
  for (const file of readdirSync(htmlDir).filter((f) => f.endsWith(".html")).sort()) {
    await page.goto(`file://${path.join(htmlDir, file)}`, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(500); // let the Tailwind CDN finish applying styles
    const out = path.join(r.dir, file.replace(/\.html$/, ".png"));
    await page.screenshot({ path: out, fullPage: r.fullPage });
    console.log(`rendered ${path.relative(process.cwd(), out)}`);
  }
  await page.close();
}
await browser.close();
