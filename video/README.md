# LeadPilot demo video

A 64 s product demo (1920×1080, 30 fps) and the README GIF, built with
[Remotion](https://www.remotion.dev/) from the Stitch showcase screens in `docs/ui/html/`.
This folder is a dev-only tool: nothing in n8n, CI or the deployment depends on it
(DECISIONS 64).

Outputs:

| File | What |
|---|---|
| `out/leadpilot-demo.mp4` | the demo with music |
| `out/leadpilot-demo-nobgm.mp4` | same timeline, sound effects only (for adding your own music) |
| `../docs/media/demo.gif` | 960 px README cut: form → score → approval → results |

## Requirements

Node 20+ and Docker (the screen capture runs Playwright in its official image, nothing
installed locally). Remotion downloads its own headless Chrome and ships `ffmpeg`/`ffprobe`
(`npx remotion ffmpeg …`), so no system ffmpeg is needed.

```bash
cd video
npm ci
```

## 1. Capture the screens

The textures (`public/textures/`, git-ignored) and `src/layout.json` (element boxes) are
regenerated from `docs/ui/html/*.html`. Run from the **repo root** (the HTML loads Tailwind and
the Inter font from CDNs, so it needs network):

```bash
docker run --rm -v "$PWD:/repo" -w /repo mcr.microsoft.com/playwright:v1.49.1-noble \
  sh -c "npm i --no-save --prefix /tmp/pw playwright@1.49.1 >/dev/null && \
         NODE_PATH=/tmp/pw/node_modules node video/scripts/capture.mjs"
```

Git Bash on Windows: prefix with `MSYS_NO_PATHCONV=1` and use `$(pwd -W)` instead of `$PWD`.

Each screen is laid out at 1600×900 CSS px (like `docs/ui/*.png`) and captured at 2.4×, so the
1920-px-wide video shows it at 2× texture density; the score box the camera pushes in on is
also cut out at 4×. Re-run the capture after any change to the showcase HTML.

## 2. Preview

```bash
npm run dev            # Remotion Studio
npm run stills         # QA stills: node scripts/stills.mjs out/qa <frame> [frame...]
```

## 3. Render

```bash
npm run render         # out/leadpilot-demo.mp4
npm run render:nobgm   # out/leadpilot-demo-nobgm.mp4 (uses props-nobgm.json: {"bgm":false})
```

The no-music version is the same composition with the `bgm` input prop off; pass props through
the JSON file, because Windows shells strip the quotes from inline `--props='{"bgm":false}'`.

## 4. README GIF

A ~15.7 s, 960 px, 12 fps cut of six moments, in pipeline order: form push-in (7.87–9.87 s),
research rows landing (14.33–16.83 s), score spotlight (22.5–25.0 s), Slack approval up to the
Approve click and its approved state (35.5–38.5 s), email written and HubSpot cards landing
(41.0–43.5 s) and the KPIs rolling and then held settled for 1.5 s (50.33–53.5 s). Two-pass
palette, from the no-music render (Remotion's bundled ffmpeg has `trim`/`concat`/`palettegen`
but no `fps` filter, so the frame rate is set with `-r`). Run from `video/`:

```bash
SRC=out/leadpilot-demo-nobgm.mp4
CUT="-ss 7.867 -t 2.0 -i $SRC -ss 14.333 -t 2.5 -i $SRC -ss 22.5 -t 2.5 -i $SRC -ss 35.5 -t 3.0 -i $SRC -ss 41.0 -t 2.5 -i $SRC -ss 50.333 -t 3.167 -i $SRC"
JOIN="[0:v][1:v][2:v][3:v][4:v][5:v]concat=n=6:v=1:a=0,scale=960:-1:flags=lanczos"
npx remotion ffmpeg -y $CUT -filter_complex "$JOIN,palettegen=stats_mode=diff" -frames:v 1 -update 1 out/palette.png
mkdir -p ../docs/media
npx remotion ffmpeg -y $CUT -i out/palette.png \
  -filter_complex "$JOIN[v];[v][6:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  -r 12 ../docs/media/demo.gif
```

The shot boundaries come from `src/timeline.ts` (frame ÷ 30); if you retime a shot, move the
`-ss` values with it.

## How it is put together

- `src/timeline.ts` is the single source of truth: shot table, title-card copy, captions,
  flash cuts and the SFX table. Captions and sound are pinned relative to shot starts, so a
  shot can change length without re-pinning anything after it.
- `src/shots/*` one file per shot; each header says which video-shotcraft shot card it adapts
  and which of the card's tuned parameters it keeps.
- `src/lib/*` components copied from the video-shotcraft skill (`PageCam`, `Caption`,
  `DigitRoll`, `FlashCut`), re-skinned to the LeadPilot design tokens (`src/theme.ts`, from
  `docs/ui/DESIGN.md`).
- Rendering is deterministic (no `Date.now()` / `Math.random()`; the outro's dust motes are
  derived from their index).

## Licenses and credits

- **Remotion** is not MIT: it is free for individuals and for companies of up to three people;
  larger companies need a company license. See https://www.remotion.dev/license.
- **Inter** (SIL Open Font License) via `@fontsource/inter`.
- **Music and sound effects** are from Mixkit (free license, no attribution required); every
  file and its original Mixkit item URL is listed in `public/audio/ATTRIBUTION.md`.
- Motion recipes: the video-shotcraft skill's shot cards (orbit-ring-title-open,
  paper-title-card, row-embed, spotlight-hero-card, cursor-flyover,
  document-typewriter-reveal, outro-group-photo-launch).
- All data on screen is the synthetic showcase data (example domains); the spot-check numbers
  are from `eval/results-spotcheck.md`.
