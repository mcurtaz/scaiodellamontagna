# Step 2 — Chrome: Layout, Nav, Footer

Part of `FRONTEND_BUILD_PLAN.md`. Builds the shell every page sits inside.
Depends on Step 1's tokens/fonts.

## Decision: one Nav bar on every page, including Home

The mockup shows Home with a big centered title + links (no bar) and every
other page with a slim bar (links left, small logo right, active underline).
We're **not** replicating that split. Instead:

- `Nav.astro` renders the **same slim bar on every page**, Home included.
- Home's large "Scaio della Montagna" heading + intro text becomes part of
  Home's own hero content (built in Step 4's `PageHeader`), not part of the
  nav/chrome.

This keeps navigation consistent across the whole site and is simpler to make
work well on mobile than maintaining two structurally different nav layouts.

## Site config

Small config module so the site name and contact address exist in one place
rather than being repeated in Nav/Footer:

`src/lib/site.ts`:
```ts
export const SITE_NAME = "Scaio della Montagna";
export const CONTACT_EMAIL = "mcurtaz@gmail.com";
```

## `Nav.astro`

Props:
```ts
interface Props {
  active?: "articoli" | "itinerari"; // omitted on Home and any other page with no matching link
}
```

Content: `SITE_NAME` (links to `/`) + three links — Articoli (`/articoli`),
Itinerari (`/itinerari`), Contatti (`mailto:${CONTACT_EMAIL}`). The link
matching `active` gets the underline/accent-color treatment from the mockup
(`terra` underline, `verde`/medium-weight text); the rest stay in the plain
inline text color.

Mobile-first layout: a single flex row (`flex flex-wrap items-baseline
justify-between gap-x-6 gap-y-2`) holding the site name and the links group.
With only four short text items total, this wraps cleanly at narrow widths
without needing a hamburger menu or any JS — verify by resizing down to
~320px in `astro dev` and confirming nothing clips or overlaps. Padding scales
up at wider breakpoints (e.g. `px-4 py-3 sm:px-8 md:px-14`) rather than using
the mockup's fixed `56px`.

## `Footer.astro`

No props. Static content: `SITE_NAME` on the left, "Contatti"
(`mailto:${CONTACT_EMAIL}`) on the right, thin top border — same flex-wrap
approach as Nav so it degrades gracefully on narrow screens.

## `Layout.astro`

Props:
```ts
interface Props {
  title: string;         // used as `${title} · ${SITE_NAME}` in <title>, except Home which is just SITE_NAME
  description?: string;  // <meta name="description">
  active?: "articoli" | "itinerari"; // forwarded to Nav
}
```

Structure: standard Astro page shell (`<html lang="it">`, charset, viewport,
favicon, generator meta, `<title>`, optional description meta) importing
`../styles/global.css`, rendering `<Nav active={active} />`, then `<slot />`
for page content, then `<Footer />`.

Every page built from Step 4 onward wraps its content in this Layout instead
of hand-rolling `<html>`; `src/pages/index.astro`'s current placeholder
markup gets replaced when Home is actually built (Step 4), not in this step.

## What "done" looks like

- `src/lib/site.ts`, `src/components/Nav.astro`, `src/components/Footer.astro`,
  `src/layouts/Layout.astro` exist.
- A throwaway page wrapped in `<Layout title="Test" active="itinerari">` shows
  the nav bar with "Itinerari" visually marked active, and the footer at the
  bottom, both readable and non-overlapping from ~320px viewport width up
  through desktop.
- `npm run build` succeeds.

## Open questions

None outstanding — Nav structure and contact email were resolved above.
