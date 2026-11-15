---
name: Flame in Freefall Editorial System
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e4e2e1'
  on-surface: '#1b1c1c'
  on-surface-variant: '#434651'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0ef'
  outline: '#747782'
  outline-variant: '#c4c6d3'
  surface-tint: '#395ba9'
  primary: '#163f8b'
  on-primary: '#ffffff'
  primary-container: '#3457a4'
  on-primary-container: '#c2d1ff'
  inverse-primary: '#b1c5ff'
  secondary: '#9c440d'
  on-secondary: '#ffffff'
  secondary-container: '#fc8e53'
  on-secondary-container: '#6e2b00'
  tertiary: '#374455'
  on-tertiary: '#ffffff'
  tertiary-container: '#4e5b6d'
  on-tertiary-container: '#c6d3e8'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b1c5ff'
  on-primary-fixed: '#001946'
  on-primary-fixed-variant: '#1c438f'
  secondary-fixed: '#ffdbcb'
  secondary-fixed-dim: '#ffb692'
  on-secondary-fixed: '#341100'
  on-secondary-fixed-variant: '#793000'
  tertiary-fixed: '#d6e3f9'
  tertiary-fixed-dim: '#bac7dc'
  on-tertiary-fixed: '#0f1c2c'
  on-tertiary-fixed-variant: '#3b4859'
  background: '#fcf9f8'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e1'
typography:
  headline-xl:
    fontFamily: Geist
    fontSize: 4rem
    fontWeight: '700'
    lineHeight: 4.25rem
    letterSpacing: -0.03em
  headline-xl-mobile:
    fontFamily: Geist
    fontSize: 2.25rem
    fontWeight: '700'
    lineHeight: 2.5rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 2.5rem
    fontWeight: '600'
    lineHeight: 2.875rem
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: 2.125rem
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 1.75rem
    fontWeight: '500'
    lineHeight: 2.125rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Geist
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.625rem
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist
    fontSize: 1.125rem
    fontWeight: '400'
    lineHeight: 1.75rem
    letterSpacing: -0.005em
  body-md:
    fontFamily: Geist
    fontSize: 0.9375rem
    fontWeight: '400'
    lineHeight: 1.5rem
    letterSpacing: 0em
  body-sm:
    fontFamily: Geist
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.25rem
    letterSpacing: 0.005em
  label-caps:
    fontFamily: Geist
    fontSize: 0.6875rem
    fontWeight: '700'
    lineHeight: 0.875rem
    letterSpacing: 0.1em
  scientific-code:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: 1.125rem
    letterSpacing: 0.02em
  stat-numeral:
    fontFamily: Geist
    fontSize: 3.5rem
    fontWeight: '300'
    lineHeight: 3.75rem
    letterSpacing: -0.03em
spacing:
  gutter: 1.5rem
  gutter-desktop: 2rem
  margin: 1.25rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system embodies the rigorous discipline of Swiss International Typographic Style fused with archival scientific documentation. Designed for astrophysical research, orbital mechanics, and microgravity combustion investigation, the interface prioritizes absolute clarity, informational density, and typometric tension over decorative ornamentation.

The visual style rejects ephemeral consumer UI trends: there are zero bento boxes, zero drop-shadow cards, and zero floating rounded panels. The layout operates like a living broadsheet monograph—defined by razor-sharp hairline borders, asymmetric column splits, generous negative margins, and authoritative typographic hierarchy. The emotional response is one of academic gravitas, empirical objectivity, and focused intellectual discovery.

## Colors
The palette evokes archival research documents, laboratory paper, and high-contrast analytical instrumentation. Pure optical white (#FFFFFF) is strictly forbidden; interfaces build upon tactile, warm-tinted paper substrates.

- **Background Canvas (`#EDECE6`):** The foundational warm archival paper ground, providing low eye-strain for extensive observational reading.
- **Secondary Surface (`#F7F6F0`):** Elevated analytical panes, data table headers, and focused observation frames.
- **Primary Text (`#242424`):** Deep graphite ink tone for uncompromising legibility and sharp ink-on-paper contrast.
- **Secondary Text (`#74746C`):** Warm editorial gray for metadata, figure captions, running heads, and tabular axes.
- **Cobalt Blue (`#3457A4`):** Primary functional active hue. Designates observational facts, confirmed experimental readings, interactive states, and active text underlines.
- **Burnt Orange (`#E47B42`):** Alert and projection accent. Reserved strictly for predictive models, target thresholds, anomalies, and active input carets.
- **Dusty Blue (`#B7C4D9`):** Secondary data series, error bands, uncertainty intervals, and passive structural brackets.
- **Hairline Divider (`#D4D2C9`):** 1px structural grid lines and rule dividers creating visual scaffolding without physical weight.

## Typography
Typography is the primary architecture of the interface. We apply a strict Swiss hierarchy anchored by **Geist** for crisp structural reading and **JetBrains Mono** for empirical data streams.

- **Editorial Headings:** Displayed with high contrast and tight tracking. Numeric identifiers preceding section titles (e.g., `01 / QUENCH ANALYSIS`) must use `label-caps`.
- **Scientific Monospace:** `JetBrains Mono` is deployed selectively—never for continuous prose. Use strictly for SI units, mission timestamps, DOI citations, hardware IDs, and tabular figures requiring tabular lining alignment.
- **Large Scientific Numerals:** Formatted with `stat-numeral` using clean geometric weights, pairing directly with small, uppercase tracked labels pinned to the top-right or baseline.
- **Editorial Microcopy:** All category tags, indices, and column labels are set in uppercase `label-caps` with `0.1em` letter spacing for immediate scanning.

## Layout & Spacing
The layout model is an asymmetric 12-column Swiss broadsheet grid that enforces deliberate negative space and distinct horizontal datum lines.

- **The Masthead:** A slender, fixed top horizontal masthead spanning all 12 columns. It contains mission parameters, breadcrumbs, and live telemetry status. Primary sections are separated by `1px solid #D4D2C9` and navigate via minimal, low-profile text buttons with high-contrast active cobalt underlines. Sidebars are eliminated to preserve maximum horizontal canvas for multi-axis plots.
- **Column Asymmetry:** Editorial layouts employ a 4/8 or 3/9 column split. The narrower column serves as an archival margin containing section titles, abstract metadata, and variable legends. The wider column houses primary data visualizers and continuous scientific text.
- **Horizontal Datum Rules:** Layout divisions avoid background cards; instead, sections terminate with a continuous horizontal hairline rule (`1px solid #D4D2C9`). Spacing above and below rules adheres strictly to `space-lg` and `space-xl`.
- **Breakpoints & Reflow:**
  - **Desktop (≥ 1024px):** 12 columns, 2rem gutters, 3rem exterior margin.
  - **Tablet (768px – 1023px):** 6 columns, 1.5rem gutters, 2rem exterior margin. Asymmetric side margins collapse into stacked analytical blocks.
  - **Mobile (< 768px):** Single-column vertical stream, 1.25rem exterior margin. The masthead switches to a compact horizontal rail with horizontal scroll indicators.

## Elevation & Depth
In adherence to Swiss Modernism, three-dimensional depth, drop shadows, and faux skeuomorphic elevations are strictly prohibited. The system is resolutely flat and textural.

- **Planar Hierarchy:** Visual separation is achieved exclusively through tonal contrast between the `#EDECE6` canvas and `#F7F6F0` editorial surfaces, bordered by sharp `#D4D2C9` hairline rules.
- **Hairline Framing:** All containers, data cells, and workspace frames utilize razor-sharp 1px border lines. No box shadows are permitted on modals, sheets, or popovers.
- **Floating Overlays & Tooltips:** Where informational popovers or tooltips appear on experimental plots, they must be rendered with a solid `#F7F6F0` surface, a crisp `1px solid #242424` outline, and zero blur or shadow.
- **Z-Index Layering:** Scrims for transient dialogs use a flat `#242424` with 25% opacity, preserving the legibility of the background technical data.

## Shapes
The shape language is uncompromisingly architectural, sharp, and orthogonal (`roundedness: 0`). 

- **Absolute Rectilinearity:** Every button, input field, tab, split-pane, and tag features 90-degree squared corners (`border-radius: 0px`).
- **Data Scaffolding:** Graphical indicators, plot bounds, and selection brackets use straight segments and crosshairs reminiscent of technical drafting instruments.

## Components

### Action Elements (Buttons & Links)
- **Primary Action:** Solid `#242424` rectangular block with `#EDECE6` text, 0px border-radius, padded with `0.5rem 1.25rem`. Hover state transitions to `#3457A4`.
- **Secondary Action:** Transparent background with `1px solid #242424` border and `#242424` text. Hover state inverts background to `#242424` and text to `#EDECE6`.
- **Editorial Text Action:** Bare typographic link with an active underline. Normal state: `1px solid transparent`. Hover or active state: `2px solid #3457A4` offset by `4px`.
- **Destructive/Alert Action:** `1px solid #E47B42` with `#E47B42` text.

### Navigation Masthead
- **Structure:** Slim, 48px high single-row masthead anchored to the top of the canvas, resting on a `1px solid #D4D2C9` baseline.
- **Links:** Upper-case `label-caps` typography in `#74746C`. Active link transitions to `#242424` with an immediate `2px solid #3457A4` bottom underline positioned flush against the masthead baseline.

### Data Cells & Analytical Blocks (Replacement for Cards)
- Conventional rounded cards with drop shadows are disallowed.
- Structured content is enclosed in full-width or column-spanning data blocks bounded by `1px solid #D4D2C9` borders on the top and bottom.
- Backgrounds remain `#EDECE6` or alternate subtly to `#F7F6F0` for active observation viewports.
- Headers inside data blocks feature a compact metadata row (e.g., `FIG. 04A // FLAME FRONT SPREAD`) set in `label-caps` and colored `#74746C`.

### Form Controls & Inputs
- **Text Inputs:** Transparent background with a single bottom rule (`1px solid #74746C`) or a complete rectangular outline (`1px solid #D4D2C9`). When focused, border changes to `1px solid #3457A4` with a `#E47B42` blinking bar caret.
- **Checkboxes & Radios:** Sharp, square 14px indicators with `1px solid #242424`. Check state is represented by a solid 8px `#3457A4` square fill inside (no curved checkmark vector).
- **Unit Tags / Chips:** Flat rectangular tags, `#F7F6F0` fill, `1px solid #D4D2C9`, containing `JetBrains Mono` unit descriptors (`0.25rem 0.5rem` padding).

### Data Tables
- Continuous horizontal grid layout with `#D4D2C9` hairlines separating records; vertical borders are omitted.
- Header row styled in `#74746C` uppercase `label-caps`, pinned on scroll.
- Numeric columns right-aligned using `JetBrains Mono` with identical column widths.
- Active or hover row marked with a `#3457A4` left-edge 2px rule indicator and a slight tint of `#F7F6F0`.