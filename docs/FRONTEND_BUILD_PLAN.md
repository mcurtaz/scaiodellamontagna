# Frontend build plan — from mockup to Astro site

Status: v1 draft — 2026-09-08.

This document is the reference for how we go from the Claude Design mockup
(`Scaio della Montagna.dc.html`, project root) to the real Astro frontend. It
complements `PROJECT_SPEC.md` (content model, deployment) with the
implementation strategy: which pieces we're building, in what order, and what
had to be decided up front vs. deferred.

**The mockup is a starting point, not a pixel spec.** It fixes the palette,
type pairing, and content hierarchy (which sections exist, in what order, what
data each shows) — not exact widths, spacing, or breakpoints. It's a single
1000px desktop card with no mobile treatment. We build **mobile-first and
responsive from the start**: the mockup's structure and visual language are
the reference, but every component gets designed to look appealing at phone
width first, then adapted upward — not "matched on desktop, patched for
mobile."

## Directus schema (as it actually exists today)

Inspected directly against the local instance (read-only API token) so
component props are grounded in real field names, not guesses:

- **itinerari**: `titolo`, `slug`, `dislivello_positivo`, `dislivello_negativo`,
  `tempo_medio_ore` (decimal, comes back from the API as a `string`),
  `distanza_km` (decimal, also a `string`), `difficolta` (`T`/`E`/`EE`/`EEA`/`OFA`),
  `is_child_friendly`, `is_winter_friendly`, `is_loop`, `punto_partenza` /
  `punto_arrivo` (GeoJSON Point), `traccia_gpx` (file id), `descrizione`,
  `autore` (m2o → autori). Two m2m relations, re-verified against the live
  instance (field names corrected from an earlier draft of this doc):
  `galleria` (→ `directus_files`, junction collection `itinerari_galleria`
  with `directus_files_id`, `sort`, `didascalia` caption) and `correlati`
  (self-referencing, junction collection `itinerari_correlati` with
  `itinerario_correlato`, `tipo`). **Both junction collections currently have
  zero permission rows for the API Reader policy** — needs a permissions fix
  before Step 9 can fetch either.
- **articoli**: `titolo`, `slug`, `immagine` (file id), `testo` (markdown),
  `autore` (m2o → autori).
- **autori**: `nome`, `bio`, `foto` (file id).
- Both `itinerari` and `articoli` already have populated `slug` fields, so
  `/itinerari/[slug]` and `/articoli/[slug]` routing is unblocked.

## Decisions locked in

1. **Directus client**: `@directus/sdk`, typed against the schema above.
2. **Images**: plain `<img>` tags, URLs built as
   `${DIRECTUS_URL}/assets/{id}?width=...&quality=...` — Directus resizes
   server-side. No Astro image pipeline / `remotePatterns` config.
3. **Fonts**: self-hosted via `@fontsource/epilogue` and
   `@fontsource/ibm-plex-mono` (no Google Fonts CDN request at runtime).
4. **Contatti**: a `mailto:` link in Nav/Footer, not a route/page.
5. **Itinerari filters**: plain vanilla JS against a build-time JSON index,
   per `PROJECT_SPEC.md`'s client-side search decision — no UI framework or
   Astro island library gets introduced for this.
6. **Responsiveness**: mobile-first, designed for real (not just "doesn't
   break") from the very first component.
7. **Map rendering**: static image — a track + start/end markers rendered to
   a plain `<img>` at build time, no client-side map JS/tile-server runtime
   dependency. Only affects the last piece (Itinerario detail's track
   section, Step 9); the "decide right before that piece" placeholder from
   `PROJECT_SPEC.md` is resolved.

## Design tokens

Palette and type pairing from the mockup, encoded once as Tailwind v4 theme
tokens (`@theme` block in `astro/src/styles/global.css`) so components use
`bg-crema`, `text-terra`, etc. instead of repeating hex values:

| token | hex | use |
|---|---|---|
| `crema` | `#F4EEE1` | page background |
| `inchiostro` | `#1B2A25` | body text / ink |
| `salvia` | `#A9C1B0` | accent band background (one per page) |
| `verde` | `#3B5C4B` | section labels on crema |
| `terra` | `#6E3A08` | links, accents, section labels on salvia |
| `pietra` | `#DCD9C6` | placeholder / thumbnail fill |

Fonts: **Epilogue** (body/display, weights 400/500/600) and **IBM Plex Mono**
(data, labels, stats, weights 400/500/600).

## Component inventory

**Chrome** (every page depends on these):
- `Layout.astro` — HTML shell, fonts, meta, imports `global.css`.
- `Nav.astro` — one component, two visual arrangements (centered for Home,
  inline with active-state underline for inner pages), responsive down to
  mobile.
- `Footer.astro` — site name + Contatti `mailto:` link, identical everywhere.

**Shared atoms:**
- `SectionHeader.astro` — the recurring "LABEL ————— action" pattern (IL
  SITO, ULTIMI ARTICOLI, FILTRI, DATI, TRACCIA, DESCRIZIONE, GALLERIA, SI
  COLLEGA CON, ARTICOLI, ARTICOLO, TESTO, ALTRI ARTICOLI...).
- `SageBand.astro` — the one salvia-colored section per page.
- `DifficultyBadge.astro` — T/E/EE/EEA/OFA label.
- `PageHeader.astro` — title + intro/meta pattern reused at the top of every
  page.

**Composite list/detail pieces** (built per-page, in the order below):
- `ArticleListItem.astro` — compact (Home) / full (Articoli listing) variants.
- `RouteListItem.astro` — compact (Home) / full (Itinerari listing) variants,
  reused again for "si collega con" with a relation-type badge.
- `MapThumbnail.astro` — placeholder now, swapped for a real static map later.
- `DataTable.astro` — the itinerario stats grid.
- `Gallery.astro` — cover image + caption, then a grid of image+caption.
- `FilterPanel.astro` — sliders + toggle groups for Itinerari; the one
  genuinely interactive piece, built last among the Itinerari pieces.

**Data layer:**
- `src/lib/directus.ts` — `@directus/sdk` client + typed query functions.
- `src/lib/types.ts` — TS interfaces mirroring the schema above.

## Build order

Detailed, executable specs exist for steps 1–5 (see below); later steps stay
at the strategy level until we get there.

1. **Design tokens + fonts** → `docs/FRONTEND_STEP_1_TOKENS.md`
2. **Chrome: Layout, Nav, Footer** → `docs/FRONTEND_STEP_2_CHROME.md`
3. **Shared atoms: SectionHeader, SageBand, DifficultyBadge, PageHeader** →
   `docs/FRONTEND_STEP_3_ATOMS.md`
4. **Home page, hardcoded content** → `docs/FRONTEND_STEP_4_HOME_STATIC.md`
5. **Wire Home to Directus** (`@directus/sdk`, `src/lib/directus.ts`) —
   proves the data-fetching architecture on the lowest-risk page →
   `docs/FRONTEND_STEP_5_DIRECTUS_WIRING.md`
6. **Articoli listing + Articolo detail**, wired to Directus immediately
   (pattern already proven in step 5) →
   `docs/FRONTEND_STEP_6_ARTICOLI.md`
7. **Itinerari listing**, static/non-interactive filters first.
8. **Itinerari filters**, made interactive with vanilla JS.
9. **Itinerario detail** — last and most complex: data table, gallery (needs
   `galleria_immagini` shape inspected), related routes (needs the
   `itinerari_correlati` junction permission/shape sorted out), and the
   static-vs-interactive map decision made right before this step.

## Verification per step

- Steps 1–4 (no data): visual check via `astro dev`, no build errors, checked
  at mobile width first and then wider viewports.
- Steps 5–9 (data-wired): `npm run build` succeeds against the live local
  Directus instance, and rendered content matches the real items currently in
  Directus rather than placeholder text.
