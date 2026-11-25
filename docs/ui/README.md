# docs/ui – showcase visuals

Designed in Google Stitch from [`STITCH_PROMPT.md`](STITCH_PROMPT.md) (project "LeadPilot UI Showcase"). These are **showcase visuals** for the demo video, the README and the Upwork cover. They are not built as an app; the real product runs in n8n, Slack and HubSpot.

| Frame (1920×1080) | Full page | Source |
|---|---|---|
| `01-landing.png` | `full/01-landing.png` | `html/01-landing.html` |
| `02-lead-form.png` | `full/02-lead-form.png` | `html/02-lead-form.html` |
| `03-research.png` | `full/03-research.png` | `html/03-research.html` |
| `04-scorecard.png` | `full/04-scorecard.png` | `html/04-scorecard.html` |
| `05-approval.png` | `full/05-approval.png` | `html/05-approval.html` |
| `06-crm-email.png` | `full/06-crm-email.png` | `html/06-crm-email.html` |
| `07-results.png` | `full/07-results.png` | `html/07-results.html` |

`DESIGN.md` holds the Stitch design tokens (colours, type scale, spacing).

## Edits made after the Stitch export
The HTML was corrected so the visuals don't contradict the product's "no invented claims" promise or point at real domains:
- Screen 5's draft no longer claims "cut shipment status inquiries by 40%"; it only uses facts from Daniel's message and the research.
- `harborlogistics.com` / `.io` and a stray `sarah.chen@` address became `daniel.reyes@harborlogistics.example`.
- LinkedIn sources (the workflow doesn't use LinkedIn) became the company website and `news.example`.
- "Zero hallucinations" and "cached domain lookups" wording removed.

**The numbers on `07-results` (90 %, 48 s, cost) and the 48 s on screens 1 and 4 are placeholders.** Replace them with the real values from `eval/results.md` after M7, then re-render.

## Re-render
```
docker run --rm -v "$PWD:/repo" -w /repo mcr.microsoft.com/playwright:v1.49.1-noble \
  sh -c "npm i --no-save --prefix /tmp/pw playwright@1.49.1 >/dev/null && NODE_PATH=/tmp/pw/node_modules node scripts/render_ui_frames.mjs"
```
The HTML loads Tailwind and fonts from public CDNs, so rendering needs internet access.
