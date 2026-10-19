---
name: Asphalt & Signal
colors:
  surface: '#f7f9fd'
  surface-dim: '#d8dade'
  surface-bright: '#f7f9fd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f8'
  surface-container: '#eceef2'
  surface-container-high: '#e6e8ec'
  surface-container-highest: '#e0e3e6'
  on-surface: '#191c1f'
  on-surface-variant: '#44474d'
  inverse-surface: '#2d3134'
  inverse-on-surface: '#eff1f5'
  outline: '#75777e'
  outline-variant: '#c5c6ce'
  surface-tint: '#505f7a'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#0c1c34'
  on-primary-container: '#7684a1'
  inverse-primary: '#b8c7e6'
  secondary: '#795900'
  on-secondary: '#ffffff'
  secondary-container: '#fcc01d'
  on-secondary-container: '#6c5000'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#001453'
  on-tertiary-container: '#5679ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d6e3ff'
  primary-fixed-dim: '#b8c7e6'
  on-primary-fixed: '#0c1c34'
  on-primary-fixed-variant: '#394761'
  secondary-fixed: '#ffdf9f'
  secondary-fixed-dim: '#f9bd19'
  on-secondary-fixed: '#261a00'
  on-secondary-fixed-variant: '#5b4300'
  tertiary-fixed: '#dde1ff'
  tertiary-fixed-dim: '#b8c4ff'
  on-tertiary-fixed: '#001453'
  on-tertiary-fixed-variant: '#0037b9'
  background: '#f7f9fd'
  on-background: '#191c1f'
  surface-variant: '#e0e3e6'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-caps:
    fontFamily: Manrope
    fontSize: 11px
    fontWeight: '800'
    lineHeight: 16px
    letterSpacing: 0.08em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system drives a modern, high-focus exam preparation platform tailored for Uzbekistan’s drivers. The visual identity merges the structural rigor of road engineering with high-velocity SaaS refinement. It captures the energy of high-contrast signage against dark tarmac—authoritative, legible at speed, and encouraging.

The aesthetic blends Modern SaaS product clarity (precision typography, functional density, muted control borders) with gamified learning motifs (punchy rewards, distinct status signaling, deliberate tactile interaction). The interface must instill calm confidence during stressful test simulations while preserving high operational speed across low-end mobile devices and high-resolution desktop environments.

## Colors

The palette relies on deliberate contrast hierarchies derived from transport navigation and civic regulatory design:

- **Deep Navy-Ink (`#0B1B33`):** The primary anchor. Serves as high-contrast structural framing, hero sections, primary typography, and dark surfaces.
- **Signal Amber Yellow (`#FFC220`):** The dominant action accent. Reserved for conversion anchors, active drill triggers, dynamic progress metrics, and road-caution signifiers. Pair with `#0B1B33` text to maintain WCAG AAA compliance.
- **SaaS Hyper Blue (`#2457F5`):** Secondary interactive engine. Powers links, systematic tooltips, functional badges, and focus rings.
- **System States:**
  - Success Green: `#14A44D` (Correct test answers, passed milestones, readiness scores).
  - Hazard Red: `#E5383B` (Mistakes, critical test failure, timed expiration warnings).
- **Surfaces & Boundaries:**
  - Base Canvas: `#F4F6FA` (Soft cool grey-blue preventing eye fatigue).
  - Raised Cards: `#FFFFFF` (Pure white containers).
  - Hairline Separators: `#E6EAF0` (Structural definition without heavy cognitive weight).

## Typography

The type system balances high-energy geometric display cuts with legible body setting:

- **Headings (Manrope):** Display and headline weights use Extra Bold (`800`) and Bold (`700`) with negative letter-tracking. This mirrors technical automotive dials and highway signage, giving prompts and scores an authoritative cadence.
- **Body & Controls (Inter):** Regular (`400`) and Semi-Bold (`600`) weights preserve clarity for complex Uzbek legal clauses, traffic law nuances, and localized Latin orthography (including frequent apostrophes, `o‘`, and `g‘`).
- **Data & Micro-Labels:** `label-caps` in Manrope uppercase acts as category delimiters, section kickers, and countdown indicators.

## Layout & Spacing

The layout model runs on a 12-column responsive grid with an 8px base rhythm:

- **Mobile (< 768px):** 4-column fluid system. Gutter is `1rem` (16px), margin is `1rem` (16px). All quiz elements, road situation imagery, and multi-choice selections collapse to 100% container width. Action bars pin to bottom safe areas.
- **Tablet (768px – 1023px):** 8-column layout. Gutter is `1.25rem` (20px), margin is `2rem` (32px). Quiz interactions sit side-by-side with situational diagrams where height permits.
- **Desktop (1024px+):** 12-column fixed-max layout (`max-w-7xl` / 1280px). Gutter is `1.5rem` (24px), margins expand automatically. Split panes prioritize the test questionnaire on the left (7 columns) and metadata/sign inspection/shortcuts on the right (5 columns).
- **Rhythm Guidelines:** Card interiors leverage `space-lg` (24px) for desktop and `space-md` (16px) for mobile. Gaps between multiple-choice options adhere strictly to `space-sm` (8px) or `space-md` (12px) to guarantee generous touch targets.

## Elevation & Depth

Visual hierarchy uses ambient diffusion rather than harsh shadows, pairing crisp borders with layered depth:

- **Surface Level 0 (Canvas):** `#F4F6FA` flat base. Used for page viewports and secondary panels.
- **Surface Level 1 (Default Containers):** `#FFFFFF` paired with a 1px border of `#E6EAF0` and ambient shadow: `0 2px 8px -2px rgba(11, 27, 51, 0.04), 0 1px 3px -1px rgba(11, 27, 51, 0.02)`.
- **Surface Level 2 (Interactive Floating / Active Question):** Raised white containers with enhanced elevation: `0 12px 24px -6px rgba(11, 27, 51, 0.08), 0 4px 8px -2px rgba(11, 27, 51, 0.03)`.
- **Surface Level 3 (Modals, Overlays, Floating HUD):** High-diffusion elevation: `0 24px 48px -12px rgba(11, 27, 51, 0.16)`.
- **Active State Depth:** Buttons and quiz options deploy a subtle 2px solid offset border effect along the bottom (`box-shadow: inset 0 -2px 0 0 rgba(11, 27, 51, 0.12)`) to give interactive surfaces a physical, responsive key-stroke feel.

## Shapes

The interface balances soft industrial geometry with high-utility containers:

- **Primary Cards & Containers:** Standardized at `16px` (`rounded-2xl` on mobile) scaling up to `20px` for hero dashboard widgets, creating friendly, approachable surfaces.
- **Buttons & Action Controls:** Formed with `12px` to `16px` radius depending on scale, matching container softness while preserving geometric punch.
- **Badges, Tags, and Question Indicators:** Styled as pill shapes (`9999px`) to immediately distinguish regulatory classification tags and question sequence counters from interactive rectangular cards.
- **Road Sign Visual Frames:** Padded internally with matching corner radiuses to simulate physical street infrastructure.

## Components

### Buttons
- **Primary Action (Signal CTA):** Background `#FFC220`, text `#0B1B33`, font `Manrope` 700. Inset bottom shadow (`rgba(0,0,0,0.15) 2px`) for tactile compression on `:active`. Hover: `#F0B418`.
- **Secondary / Tech CTA:** Background `#2457F5`, text `#FFFFFF`, font `Inter` 600. Hover: `#1B45C8`.
- **Ghost / Tertiary:** Background transparent, text `#0B1B33`, border 1px solid `#E6EAF0`. Hover: background `#FFFFFF`, border-color `#CBD5E1`.
- **Disabled:** Background `#E6EAF0`, text `#94A3B8`, border none.

### Option Cards (Multiple Choice Answers)
- Neutral: Background `#FFFFFF`, border 2px solid `#E6EAF0`, text `#0B1B33`. Includes a rounded-lg index key (A, B, C, D) in `#F4F6FA` with `#0B1B33` text.
- Focused / Selected: Border 2px solid `#2457F5`, background `rgba(36, 87, 245, 0.04)`.
- Correct Submission: Border 2px solid `#14A44D`, background `rgba(20, 164, 77, 0.06)`, index key turns `#14A44D` with white text.
- Incorrect Submission: Border 2px solid `#E5383B`, background `rgba(229, 56, 59, 0.06)`, index key turns `#E5383B` with white text.

### Progress & Metric Gauges
- **Exam Progress Bar:** Height 8px, track background `#E6EAF0`, active fill transitioning dynamically from `#2457F5` to `#FFC220` with pill ends. Segmented tick marks indicate mandatory passing thresholds (e.g., 18/20 correct).
- **Readiness Meter:** Circular dial or dense badge utilizing `#0B1B33` backdrop with glowing `#FFC220` or `#14A44D` progress arcs.

### Input Fields
- White fill, 1.5px border `#E6EAF0`, text `#0B1B33`, placeholder `#94A3B8`.
- Focus ring: 3px semi-transparent `#2457F5` spread (`rgba(36, 87, 245, 0.15)`), border color `#2457F5`.

### Chips & Badges
- **Category Chips (e.g., "Yo‘l belgilari", "Chorrahalar"):** Pill-shaped, background `#F4F6FA`, text `#0B1B33`, border 1px solid `#E6EAF0`.
- **Live Ticket Tracker:** Pill badge showing question index `14 / 20`, with deep navy surface and white monospace numbers.

### Question Illustration Canvas
- Container holding traffic scenarios and signs: pure white background framed in `16px` radius, subtle `#E6EAF0` border, centered imagery with internal aspect ratio lock (16:9 or 4:3), avoiding distortion across viewport resizes.