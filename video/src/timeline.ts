// Single source of truth for the cut: shot table, captions, flash cuts and the SFX pin table.
// Everything downstream is derived from SHOTS, so changing a shot's length moves its captions
// and sound with it (sound-design 4.5: SFX are pinned relative to shot starts, never as bare
// absolute frames).

const DURATIONS = {
  open: 170, // orbit-ring-title-open: screens on a ring around the LeadPilot title
  tcArrive: 60, // paper-title-card: "A new lead arrives."
  form: 190, // PageCam push-in on the hosted lead form
  research: 195, // row-embed: sourced company-profile rows land in the card
  score: 225, // spotlight-hero-card: the computed score box
  tcHuman: 75, // paper-title-card: "A human approves every email."
  approval: 255, // cursor-flyover over the Slack approval request, ends on Approve
  crm: 215, // document-typewriter-reveal: email writes itself, HubSpot cards drop in
  tcReal: 95, // paper-title-card: "Tested on real keys." + sub line
  results: 250, // PageCam + DigitRoll on the spot-check KPIs, then the cost banner
  outro: 185, // outro-group-photo-launch: screens assemble around the wordmark
} as const;

export type ShotId = keyof typeof DURATIONS;

export const SHOTS = (() => {
  let from = 0;
  const out = {} as Record<ShotId, { from: number; duration: number }>;
  for (const id of Object.keys(DURATIONS) as ShotId[]) {
    out[id] = { from, duration: DURATIONS[id] };
    from += DURATIONS[id];
  }
  return out;
})();

export const TOTAL = Object.values(DURATIONS).reduce((a, b) => a + b, 0);

// Title-card copy: `*…*` marks the single accent group (primary colour, italic).
export const TITLE_CARDS = {
  tcArrive: { text: 'A new lead *arrives.*' },
  tcHuman: { text: 'A *human* approves every email.' },
  tcReal: { text: 'Tested on *real keys.*', sub: '5 hot leads · real Tavily and Gemini' },
} as const;

// Narration captions (relative to the shot start; `until` defaults to the shot end). Each shot's
// camera keeps the caption band (y ≥ ~880) clear of page content while its caption is up.
// Outro stays clean (C1 exception).
export const CAPTIONS: { shot: ShotId; at: number; until?: number; main: string; sub?: string }[] = [
  { shot: 'form', at: 34, main: 'Hosted form or any form tool.', sub: 'Spam and duplicates are stopped at the door.' },
  { shot: 'research', at: 60, main: 'Researched on the web.', sub: 'Every fact cites a page it actually read.' },
  { shot: 'score', at: 10, main: 'The model rates each criterion.', sub: 'Code computes the score.' },
  { shot: 'approval', at: 40, until: 140, main: 'An approval request lands in Slack.' },
  { shot: 'approval', at: 168, main: 'Approve, edit or reject in Slack.' },
  { shot: 'crm', at: 98, main: 'Email sent. HubSpot updated:', sub: 'contact, company, score, note and follow-up task.' },
  // only once the camera is on the cost banner, so no counter is ever mid-roll beside it
  { shot: 'results', at: 162, main: 'Median 81 s from form to approval request', sub: '≈ $0.03 per lead' },
];

// Lavender bloom over the hard cuts between two product screens (from = cut − 5, 10f long).
export const FLASH_CUTS = [SHOTS.research.from, SHOTS.score.from, SHOTS.crm.from, SHOTS.outro.from];

// ---------------------------------------------------------------------------------------------
// Sound. Peak lags measured on the files (RMS envelope, frames @30fps); the output-track offset
// is the AAC encoder priming measured on this render pipeline (4 probes, 1.27–1.29 f; README).
export const OUTPUT_AUDIO_OFFSET_F = 1.28;
const PEAK_F: Record<string, number> = {
  'transition-soft.mp3': 13,
  'swoosh-quick.mp3': 9,
  'whoosh-fast.mp3': 22,
  'sweep-short.mp3': 15,
  'air-woosh-deep.mp3': 15,
  'transition-snap.mp3': 3,
  'wind-swoosh-short.mp3': 5,
  'sparkle-touch.mp3': 16,
  'shimmer-sparkle-sweep.mp3': 28,
  'click-camera.mp3': 6,
  'camera-shutter-hard.mp3': 4,
  'paper-slide.mp3': 11,
  'paper-move-quick.mp3': 9,
  'impact-deep-whoosh.mp3': 17,
  'swoosh-slow.mp3': 64,
};
/** Sequence start so the sample's own peak lands on `targetPeakF` in the rendered file. */
export const sfxFrom = (targetPeakF: number, src: string) =>
  Math.max(0, Math.round(targetPeakF - (PEAK_F[src] ?? 0) - OUTPUT_AUDIO_OFFSET_F));

export type Sfx = { from: number; src: string; volume: number; duration?: number; note: string };
const S = SHOTS;
const pin = (target: number, src: string, volume: number, note: string, duration?: number): Sfx => ({
  from: sfxFrom(target, src),
  src,
  volume,
  duration,
  note,
});

// Frame offsets used below mirror the shot components' own constants (see each shot file).
export const SFX: Sfx[] = [
  // 1 open — the ring opens out; the marker swipes under "within minutes"
  pin(S.open.from + 14, 'transition-soft.mp3', 0.35, 'ring expands from the centre'),
  pin(S.open.from + 58, 'sweep-short.mp3', 0.5, 'marker swipe under "within minutes"'),
  // title cards share one swoosh (paper-title-card: same element, same sound)
  pin(S.tcArrive.from + 10, 'swoosh-quick.mp3', 0.4, 'title card: words press in'),
  pin(S.tcHuman.from + 10, 'swoosh-quick.mp3', 0.4, 'title card: words press in'),
  pin(S.tcReal.from + 10, 'swoosh-quick.mp3', 0.4, 'title card: words press in'),
  // 3 form — camera push-in on the form card
  pin(S.form.from + 38, 'whoosh-fast.mp3', 0.4, 'push-in to the form (mid-move)'),
  // 4 research — one soft transition for the whole row rain (no per-row pop: row-embed card)
  pin(S.research.from + 16, 'transition-soft.mp3', 0.4, 'first fact row drops in'),
  // 5 score — rise, beam scan, reseat (spotlight-hero-card: one sound per beat)
  pin(S.score.from + 80, 'air-woosh-deep.mp3', 0.45, 'score box lifts off its slot', 50),
  pin(S.score.from + 92, 'sparkle-touch.mp3', 0.6, 'perimeter beam lap 1'),
  pin(S.score.from + 158, 'transition-snap.mp3', 0.6, 'score box reseats'),
  // 7 approval — cursor taps at each stop (real switch clicks, alternating, stepping down),
  // then the Approve click: a hard camera shutter, the loudest UI sound in the film
  pin(S.approval.from + 62, 'switch-tap.mp3', 0.2, 'cursor taps the 82 · HOT badge'),
  pin(S.approval.from + 114, 'switch-click-quick.mp3', 0.17, 'cursor taps "2 sources attached"'),
  pin(S.approval.from + 166, 'switch-tap.mp3', 0.15, 'cursor points at the drafted email'),
  pin(S.approval.from + 218, 'camera-shutter-hard.mp3', 1.0, 'Approve is clicked'),
  // 8 crm — typing under the line-by-line writing (two passes, trimmed), paper landings
  { from: S.crm.from + 8, src: 'typewriter-digital.mp3', volume: 0.9, duration: 54, note: 'email writes itself (1/2)' },
  { from: S.crm.from + 62, src: 'typewriter-digital.mp3', volume: 0.9, duration: 30, note: 'email writes itself (2/2, trimmed)' },
  pin(S.crm.from + 108, 'paper-slide.mp3', 0.45, 'contact + properties card lands'),
  pin(S.crm.from + 118, 'paper-move-quick.mp3', 0.8, 'note card lands'),
  pin(S.crm.from + 128, 'paper-slide.mp3', 0.36, 'follow-up task card lands'),
  // 10 results — mechanical counter under the rolls, a click as the last one settles, a glide
  { from: S.results.from + 36, src: 'clock-mech-retract.mp3', volume: 0.55, duration: 42, note: 'KPI digits roll' },
  pin(S.results.from + 78, 'click-camera.mp3', 1.0, 'last KPI settles'),
  pin(S.results.from + 142, 'wind-swoosh-short.mp3', 0.3, 'camera glides down to the cost banner'),
  // 11 outro — swell -> impact (wordmark stamp, loudest SFX) -> sparkle (rule)
  pin(S.outro.from + 42, 'swoosh-slow.mp3', 0.6, 'slow swell under the fly-in, peaks into the stamp', 70),
  pin(S.outro.from + 44, 'impact-deep-whoosh.mp3', 0.7, 'LeadPilot wordmark stamps in'),
  pin(S.outro.from + 66, 'shimmer-sparkle-sweep.mp3', 0.32, 'rule grows under the wordmark'),
];

export const BGM = { src: 'house-vibez.mp3', volume: 0.34, fadeIn: 30, fadeOut: 50 };
