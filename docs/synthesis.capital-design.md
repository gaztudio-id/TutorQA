---
version: alpha
name: Synthesis Capital
description: A minimalist, editorial investment brand with a bold indigo accent, large typography, and airy white space.
colors:
  primary: "#120A59"
  secondary: "#E5E7EB"
  tertiary: "#D8F500"
  neutral: "#FFFFFF"
  surface: "#FFFFFF"
  on-surface: "#120A59"
  error: "#D92D20"
  primary-60: "#5B5490"
  primary-70: "#7B74A8"
  primary-90: "#E7E5F2"
typography:
  headline-display:
    fontFamily: "syntheSans"
    fontSize: "57px"
    fontWeight: 700
    lineHeight: "57px"
    letterSpacing: "0px"
  headline-lg:
    fontFamily: "syntheSans"
    fontSize: "48px"
    fontWeight: 700
    lineHeight: "57px"
    letterSpacing: "0px"
  headline-md:
    fontFamily: "syntheSans"
    fontSize: "40px"
    fontWeight: 700
    lineHeight: "48px"
    letterSpacing: "0px"
  headline-sm:
    fontFamily: "syntheSans"
    fontSize: "33px"
    fontWeight: 700
    lineHeight: "40px"
    letterSpacing: "0px"
  body-lg:
    fontFamily: "syntheSans"
    fontSize: "28px"
    fontWeight: 400
    lineHeight: "42px"
    letterSpacing: "0px"
  body-md:
    fontFamily: "syntheSans"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "24px"
    letterSpacing: "0px"
  body-sm:
    fontFamily: "syntheSans"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "20px"
    letterSpacing: "0px"
  label-lg:
    fontFamily: "syntheSans"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "24px"
    letterSpacing: "0px"
  label-md:
    fontFamily: "syntheSans"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "20px"
    letterSpacing: "0px"
  label-sm:
    fontFamily: "syntheSans"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: "16px"
    letterSpacing: "0px"
  link:
    fontFamily: "syntheSans"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: "24px"
    letterSpacing: "0px"
rounded:
  none: "0px"
  sm: "4px"
  md: "8px"
  lg: "16px"
  xl: "24px"
  full: "9999px"
spacing:
  xs: "8px"
  sm: "16px"
  md: "32px"
  lg: "60px"
  xl: "100px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral}"
    typography: "{typography.body-md}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
    size: "120px"
    height: "40px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.neutral}"
    typography: "{typography.body-md}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
    size: "120px"
    height: "40px"
  button-link:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.body-md}"
    rounded: "{rounded.none}"
    padding: "0px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.sm}"
    padding: "16px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.full}"
    padding: "8px 16px"
## Overview

Synthesis Capital feels refined, calm, and purpose-driven, with a strong editorial presence rather than a corporate fintech tone. The page uses expansive white space, oversized typography, and a single deep indigo accent to communicate clarity and confidence. It appeals to an audience of founders, investors, and partners who expect sophistication, restraint, and a premium visual language.

## Colors

- **Primary (#120A59):** A deep indigo used for headlines, navigation, links, and core brand accents. It carries the entire visual identity and provides the strongest contrast against the white canvas.
- **Secondary (#E5E7EB):** A light neutral border tone for subtle separation when needed. It should stay quiet and never compete with the primary ink color.
- **Tertiary (#D8F500):** A high-energy lime accent reserved for attention-grabbing actions such as the strongest CTA. It adds a modern, slightly unexpected note to the otherwise restrained palette.
- **Neutral (#FFFFFF):** The dominant background color, creating a gallery-like, open environment. It supports the brand’s airy, editorial feel.
- **Surface (#FFFFFF):** Used for cards and elevated UI surfaces when a distinct container is needed without adding visual weight.
- **On-surface (#120A59):** The default readable text color on white surfaces, matching the brand ink.
- **Error (#D92D20):** Reserved for failure states, validation messages, and destructive feedback; keep usage minimal so it does not dilute the brand palette.
- **Primary scale variants (#5B5490, #7B74A8, #E7E5F2):** Softened or diluted versions of the indigo for hover states, subtle links, decorative overlays, or inactive treatments.

## Typography

The system is built around Synthe Sans, a clean custom grotesk with a modern, slightly architectural feel. Headlines are bold and compact, with tight line heights and no added letter spacing, which keeps the hero statement feeling crisp and assertive. Body text remains lightweight and readable, while labels and navigation use the same family to preserve consistency across the page.

Use the large headline tiers for hero statements and section titles, with `headline-display` and `headline-lg` doing most of the brand work. `body-lg` is intentionally generous and editorial, suitable for supporting copy and mission statements. `body-md`, `body-sm`, `label-md`, and `label-sm` should be used for utility text, nav, small UI labels, and cookie or legal text without changing the voice. Links and nav items should remain sentence case rather than all caps; the source does not rely on uppercase tracking for emphasis.

## Layout

The layout is highly spacious and asymmetric, with a strong left-aligned text block and a vertically stacked visual collage on the right. It behaves like a wide, fluid desktop composition rather than a tightly constrained card grid. The spacing rhythm follows a simple jump from `8px` up to `100px`, which creates generous breathing room between large sections and smaller UI elements.

Use broad horizontal padding around the page edges and keep content aligned to a clear left edge for the headline and supporting copy. Sections should feel open, with large intentional gaps between hero, supporting text, and imagery. Cards and smaller containers should use modest internal padding, while the overall page should remain visually uncluttered.

## Elevation & Depth

Depth is understated and mostly expressed through layering imagery rather than heavy UI shadowing. The site avoids strong shadows and instead uses overlap, slight rotations, and stacking to create momentum and visual interest. Flat surfaces dominate, with borders and contrast doing more work than elevation.

When depth is needed, keep it soft and minimal, as seen in card borders and subtle image overlap. Avoid glossy effects, dramatic blur, or pronounced drop shadows. The brand should feel editorial and composed, not glossy or materially heavy.

## Shapes

The shape language is rounded but restrained. Buttons use a full pill radius, giving them an approachable, contemporary feel, while cards and containers stay softly squared with `8px` corners. Overall, the geometry balances friendliness with precision.

Avoid sharp, angular UI unless it is a deliberate structural choice. Reuse the pill shape for primary actions and the small-radius card shape for informational containers. The combination should feel smooth, polished, and unobtrusive.

## Components

Buttons should be simple and clear. `button-primary` uses the indigo background with white text and pill rounding for the strongest call to action. `button-secondary` should be transparent with a white outline when placed on dark backgrounds, while `button-link` should remain text-only, using the primary color and no container chrome. Keep padding compact at `8px 16px`, and preserve the minimum `40px` height for accessibility.

Cards should stay minimal, with a white surface, subtle `1px` border, and `rounded.sm`. They should not rely on shadow for separation; use whitespace, borders, and content hierarchy instead. Internal padding should stay at `16px` unless the card is used for denser content.

Inputs should mirror the pill-like button geometry where appropriate, staying calm and low-contrast. Use white surfaces, indigo text, and moderate padding for comfortable typing targets. States should be communicated through border and text color rather than decorative fills.

Navigation links should be lightweight and understated, matching the brand ink color and avoiding heavy emphasis. Cookie consent actions demonstrate the hierarchy well: a filled primary action, a secondary outlined action, and a quiet supporting link. Image tiles or collage elements should be allowed to overlap and tilt slightly to keep the composition lively.

## Do's and Don'ts

- Do keep layouts spacious and asymmetrical, with strong left alignment and large negative space.
- Do use Synthe Sans consistently for headlines, body copy, labels, and links.
- Do favor indigo for nearly all text and UI chrome on light backgrounds.
- Do reserve the lime tertiary color for the highest-priority action only.
- Do keep shadows minimal and let borders, overlap, and whitespace create hierarchy.
- Don't introduce dense grids, loud gradients, or heavy material-style elevation.
- Don't use all-caps navigation or aggressive tracking; the voice is calm and editorial.
- Don't over-round cards or use sharp corners on primary controls; maintain the pill-and-soft-square contrast.