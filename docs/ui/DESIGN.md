---
name: LeadPilot
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#4a4455'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#7b7487'
  outline-variant: '#ccc3d8'
  surface-tint: '#732ee4'
  primary: '#630ed4'
  on-primary: '#ffffff'
  primary-container: '#7c3aed'
  on-primary-container: '#ede0ff'
  inverse-primary: '#d2bbff'
  secondary: '#6a4fa0'
  on-secondary: '#ffffff'
  secondary-container: '#c4a7ff'
  on-secondary-container: '#523787'
  tertiary: '#7d3d00'
  on-tertiary: '#ffffff'
  tertiary-container: '#a15100'
  on-tertiary-container: '#ffe0cd'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d2bbff'
  on-primary-fixed: '#25005a'
  on-primary-fixed-variant: '#5a00c6'
  secondary-fixed: '#eaddff'
  secondary-fixed-dim: '#d2bbff'
  on-secondary-fixed: '#25005a'
  on-secondary-fixed-variant: '#523787'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb784'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#713700'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  margin: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes a confident, modern B2B SaaS aesthetic tailored for revenue operations, sales leaders, and SDR teams. The interface evokes clarity, speed, and analytical trust—transforming complex AI lead-qualification signals into scannable, decisive workflows.

The visual language blends **Corporate / Modern** precision with **Minimalist** restraint:
- **Clean, airy surfaces:** Generous whitespace and crisp neutral slate backgrounds keep cognitive load low during high-volume lead triage.
- **Purposeful color:** A single crisp violet accent directs attention to primary actions and AI-driven insights, while semantic tier colors communicate lead temperature at a glance.
- **Structured hierarchy:** Subtle borders, soft ambient shadows, and disciplined typography create a dependable, high-contrast workspace.

## Colors

The palette pairs a cool, neutral slate foundation with a single crisp violet accent and high-contrast semantic tier colors.

### Surface & Neutral Palette
- **Canvas Background:** `#F8FAFC` (Slate 50) for the main application backdrop.
- **Card & Elevated Surface:** `#FFFFFF` for cards, modals, and data tables.
- **Borders & Dividers:** `#E2E8F0` (Slate 200) for crisp, low-contrast structural separation.
- **Primary Text:** `#0F172A` (Slate 900) for headings, key metrics, and primary labels.
- **Secondary Text:** `#475569` (Slate 600) for supporting copy, metadata, and table headers.

### Brand Accent
- **Primary Violet:** `#7C3AED` for primary buttons, active tabs, and focus rings.
- **Primary Hover / Active:** `#6D28D9` for interactive hover and pressed states.

### Semantic & Lead Tier Colors
- **Hot Lead:** `#EA580C` foreground/icon on `#FFF7ED` background tint.
- **Warm Lead:** `#D97706` foreground/icon on `#FFFBEB` background tint.
- **Cold Lead:** `#64748B` foreground/icon on `#F1F5F9` background tint.
- **Success / Qualified:** `#16A34A` foreground/icon on `#F0FDF4` background tint.

All text and interactive pairings must maintain WCAG AA contrast (at least 4.5:1 for body text and 3:1 for large text and UI controls).

## Typography

The design system uses **Inter** across all typographic roles to ensure maximum legibility, clean tabular alignment in data tables, and a cohesive modern SaaS feel.

- **Readable Body Scale:** Default body copy sits at `14px` (`body-md`) to `15px` (`body-lg`) with generous line heights (`22px`–`24px`) for comfortable scanning of lead summaries and AI qualification notes.
- **Tabular Numerals:** Enable `tabular-nums` on all scores, percentages, timestamps, and table columns so numbers align cleanly.
- **Responsive Scaling:** Display headings scale down on mobile viewports (`display-lg-mobile` at `28px`) to prevent awkward wrapping while preserving hierarchy.

## Layout & Spacing

The layout uses a **12-column fluid grid** that adapts smoothly across screen sizes, prioritizing generous breathing room around cards, tables, and timelines.

- **Desktop (`>= 1024px`):** 12-column grid with `1.5rem` (`24px`) gutters and `2rem` (`32px`) outer canvas margins. Dashboards typically pair a fixed `240px`–`260px` sidebar with a fluid main content area.
- **Tablet (`768px`–`1023px`):** 8-column grid with `1.25rem` (`20px`) gutters and `1.5rem` (`24px`) margins. Multi-column metric cards reflow into 2-column rows.
- **Mobile (`< 768px`):** 4-column grid with `1rem` (`16px`) gutters and `1rem` (`16px`) margins. Side-by-side detail panels stack vertically, and data tables scroll horizontally within their card container.

## Elevation & Depth

Visual hierarchy is achieved through a combination of **low-contrast `#E2E8F0` borders** and **soft, subtle ambient shadows**—characteristic of modern Tailwind and shadcn/ui interfaces.

- **Base Cards & Tables:** Rest on `#FFFFFF` surfaces with a `1px solid #E2E8F0` border and a whisper-soft shadow (`0 1px 2px 0 rgba(15, 23, 42, 0.05)`).
- **Interactive Hover & Popovers:** Elevated menus, dropdowns, and hovered cards use a slightly deeper, diffused shadow (`0 4px 12px -2px rgba(15, 23, 42, 0.08)`) while retaining their crisp `#E2E8F0` border.
- **Modals & Drawers:** Use a subtle backdrop scrim (`rgba(15, 23, 42, 0.4)`) with a clean `0 12px 24px -4px rgba(15, 23, 42, 0.12)` shadow.

## Shapes

The design system uses a **Rounded** shape language (`8px`–`12px` radii) that feels approachable yet structured and precise.

- **Controls & Inputs (`8px` / `0.5rem`):** Buttons, text inputs, select dropdowns, and table cells use `8px` (`rounded-lg` in Tailwind) for a crisp, tactile feel.
- **Cards & Containers (`12px` / `0.75rem`):** Dashboard cards, modals, and data table wrappers use `12px` (`rounded-xl`) to soften large rectangular surfaces.
- **Badges & Avatars (`9999px`):** Status pills, lead tier badges, and user avatars use full pill rounding.

## Components

All components follow shadcn/ui conventions built with Tailwind CSS, paired with simple `1.5px`–`2px` stroke line icons (such as Lucide).

### Buttons
- **Primary:** `#7C3AED` background, `#FFFFFF` text, `8px` radius, `0.5rem 1rem` padding, `#6D28D9` hover state.
- **Secondary / Outline:** `#FFFFFF` background, `1px solid #E2E8F0` border, `#0F172A` text, `#F8FAFC` hover background.
- **Ghost:** Transparent background, `#475569` text, `#F1F5F9` hover background.

### Badges & Chips
- Compact pill-shaped indicators (`9999px` radius, `12px` medium text) for lead qualification tiers:
  - **Hot:** `#FFF7ED` fill, `#EA580C` text.
  - **Warm:** `#FFFBEB` fill, `#D97706` text.
  - **Cold:** `#F1F5F9` fill, `#64748B` text.
  - **Qualified / Success:** `#F0FDF4` fill, `#16A34A` text.

### Cards
- `#FFFFFF` surface, `1px solid #E2E8F0` border, `12px` radius, `1.5rem` (`24px`) internal padding, and subtle `0 1px 2px rgba(15, 23, 42, 0.05)` shadow.

### Input Fields, Checkboxes & Radio Buttons
- **Inputs:** `#FFFFFF` background, `1px solid #E2E8F0` border, `8px` radius, `14px` text. Focus states apply a `2px` `#7C3AED` ring with `2px` offset.
- **Checkboxes & Radios:** `1px solid #E2E8F0` border, `#7C3AED` fill with `#FFFFFF` checkmark/dot when selected.

### Tables
- Clean horizontal dividers (`1px solid #E2E8F0`) with `#F8FAFC` header backgrounds, `12px`–`13px` `#475569` medium header labels, and `14px` `#0F172A` row text. Hovering a row applies a subtle `#F8FAFC` highlight.

### Tabs
- Segmented or underlined navigation using `#475569` inactive text and `#0F172A` active text with a `#7C3AED` bottom indicator or `#FFFFFF` active pill.

### Progress Bars
- `8px` height, `9999px` radius, `#F1F5F9` track, and `#7C3AED` (or semantic tier color) fill to visualize AI qualification confidence scores.

### Avatars with Initials
- Circular (`9999px` radius) `32px`–`40px` containers with `#F1F5F9` or soft violet-tinted backgrounds and `#0F172A` / `#7C3AED` medium-weight initials.

### Vertical & Horizontal Timelines
- Used for lead activity history and qualification stages. Features `2px` `#E2E8F0` connector lines, `10px`–`12px` circular status nodes (`#7C3AED` for active/AI steps, `#16A34A` for completed), and `14px` event descriptions with `12px` `#475569` timestamps.