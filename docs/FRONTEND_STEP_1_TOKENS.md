# Step 1 — Design tokens & fonts

Part of `FRONTEND_BUILD_PLAN.md`. This is the foundation every later component
depends on: nothing else should hardcode a hex value or a font stack once this
step is done.

## 1. Palette → Tailwind v4 theme tokens

Astro's Tailwind setup already exists (`astro/astro.config.mjs` has the
`@tailwindcss/vite` plugin, `astro/src/styles/global.css` has
`@import "tailwindcss";`). Tailwind v4 takes theme config as CSS, so add an
`@theme` block to `global.css`:

```css
@import "tailwindcss";

@theme {
  --color-crema: #F4EEE1;
  --color-inchiostro: #1B2A25;
  --color-salvia: #A9C1B0;
  --color-verde: #3B5C4B;
  --color-terra: #6E3A08;
  --color-pietra: #DCD9C6;

  --font-display: "Epilogue", system-ui, sans-serif;
  --font-mono-data: "IBM Plex Mono", ui-monospace, monospace;
}
```

This makes `bg-crema`, `text-inchiostro`, `border-salvia`, `text-verde`,
`text-terra`, `bg-pietra`, `font-display`, `font-mono-data` available as
Tailwind utilities everywhere, matching the token names already used in
`PROJECT_SPEC.md` and the mockup's own design note.

Also set the page-level defaults (body background/text/font) in the same
file, below the `@theme` block:

```css
body {
  @apply bg-crema text-inchiostro font-display;
}
```

## 2. Fonts → self-hosted via `@fontsource`

Install:

```
npm install @fontsource/epilogue @fontsource/ibm-plex-mono
```

Import the weights actually used by the mockup — 400, 500, 600 for both
families — in the base layout (`Layout.astro`, built in Step 2) or at the top
of `global.css`:

```css
@import "@fontsource/epilogue/400.css";
@import "@fontsource/epilogue/500.css";
@import "@fontsource/epilogue/600.css";
@import "@fontsource/ibm-plex-mono/400.css";
@import "@fontsource/ibm-plex-mono/500.css";
@import "@fontsource/ibm-plex-mono/600.css";
```

No `<link>` tags to Google Fonts, no `preconnect` needed — everything ships
from the Astro build.

## 3. What "done" looks like

- `astro/src/styles/global.css` contains the `@theme` block above plus the
  font imports.
- `npm run build` succeeds.
- A throwaway element using `bg-salvia text-terra font-mono-data` (or similar)
  renders with the right color/font when checked in `astro dev` — same
  smoke test already used to verify Tailwind installed correctly.
- No component built after this step should contain a raw hex color or a
  `font-family` declaration — if one needs a color/font not in this table,
  that's a signal to come back and extend the token list, not to hardcode.

## Open question

None for this step — palette/fonts/naming were already settled in
`FRONTEND_BUILD_PLAN.md`.
