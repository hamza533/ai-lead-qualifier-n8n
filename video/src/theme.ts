// LeadPilot design tokens (docs/ui/DESIGN.md) + motion personality.
// Every title card, caption, transition and light effect in the video is skinned from these,
// not from the skill template's paper/amber look.
import { Easing } from 'remotion';

export const C = {
  surface: '#faf8ff',
  surfaceLowest: '#ffffff',
  surfaceLow: '#f2f3ff',
  surfaceContainer: '#eaedff',
  surfaceHigh: '#e2e7ff',
  onSurface: '#131b2e',
  onSurfaceVariant: '#4a4455',
  outline: '#7b7487',
  outlineVariant: '#ccc3d8',
  primary: '#630ed4',
  primaryContainer: '#7c3aed',
  primaryFixed: '#eaddff',
  primaryFixedDim: '#d2bbff',
  onPrimaryFixed: '#25005a',
  secondaryContainer: '#c4a7ff',
  inverseSurface: '#283044',
} as const;

export const INTER = 'Inter, ui-sans-serif, system-ui, sans-serif';

// "Professional trust (B2B)" preset: ~21f main duration, decelerate curve, no overshoot
// (overshoot only where a card's landing metaphor needs it).
export const MAIN_F = 21;
export const EASE_OUT = Easing.bezier(0, 0, 0.2, 1);
export const EASE_CAM = Easing.bezier(0.4, 0, 0.2, 1);

// navy-tinted shadows (on-surface #131b2e) instead of the template's warm brown
export const shadow = (a: number) => `rgba(19,27,46,${a})`;
