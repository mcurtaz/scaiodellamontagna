# Step 3 — Shared atoms: SectionHeader, SageBand, DifficultyBadge, PageHeader

Part of `FRONTEND_BUILD_PLAN.md`. These are small, presentational,
data-agnostic components — built and checked with hardcoded props before any
page uses them for real. Depends on Step 1 (tokens) and Step 2 (they don't
depend on Nav/Footer directly, but reuse the same tokens/fonts).

## `SectionHeader.astro`

The recurring "LABEL ————— action" divider used above almost every section
(IL SITO, ULTIMI ARTICOLI, FILTRI, DATI, TRACCIA, DESCRIZIONE, GALLERIA, SI
COLLEGA CON, ARTICOLI, ARTICOLO, TESTO, ALTRI ARTICOLI, and the small eyebrow
line above the `<h1>` on Itinerario/Articolo detail pages and the Articoli
listing).

```ts
interface Props {
  label: string;
  tone?: "onCrema" | "onSage"; // default "onCrema"
  action?: { label: string; href: string };
}
```

Color rule observed consistently in the mockup: label is `verde` when the
section sits on the crema background, `terra` when it sits inside a
`SageBand`. The action link/text (e.g. "Tutti gli articoli →", "Azzera") is
always `terra`, regardless of tone.

Layout: `flex flex-wrap items-center gap-3` — label (uppercase,
`font-mono-data text-xs tracking-widest`), a horizontal rule that grows to
fill remaining space (`flex-1 h-px bg-current/20 min-w-6`), then the optional
action. `flex-wrap` means on very narrow screens the action drops to its own
line rather than clipping — no special mobile markup needed.

## `SageBand.astro`

Plain wrapper for the one salvia-colored section per page. No props beyond a
default slot.

```astro
<div class="bg-salvia px-4 py-8 sm:px-8 sm:py-10 md:px-14 md:py-12">
  <slot />
</div>
```

Padding scales up at wider breakpoints instead of the mockup's fixed 56px —
mobile-first.

## `DifficultyBadge.astro`

```ts
interface Props {
  level: "T" | "E" | "EE" | "EEA" | "OFA";
  withLabel?: boolean; // also render " — nome esteso", e.g. "E — escursionistico"
}
```

Renders the code in `font-mono-data font-medium text-terra`. The full-name
mapping (`T` → Turistico, `E` → Escursionistico, `EE` → Escursionisti Esperti,
`EEA` → Escursionisti Esperti con Attrezzatura, `OFA` → Occorrono Fune e/o
Attrezzatura Alpinistica) lives in a small shared constant, **not** inside
this component, so other places (e.g. a future filter UI) can reuse the
labels without importing the badge:

`src/lib/difficolta.ts`:
```ts
export const DIFFICOLTA_LABELS: Record<string, string> = {
  T: "Turistico",
  E: "Escursionistico",
  EE: "Escursionisti Esperti",
  EEA: "Escursionisti Esperti con Attrezzatura",
  OFA: "Occorrono Fune e/o Attrezzatura Alpinistica",
};
```

The mockup doesn't color-code different difficulty levels differently (every
level uses the same `terra` treatment) — we're keeping that; no per-level
color scheme is being invented.

## `PageHeader.astro`

The recurring `<h1>` + supporting content pattern reused at the top of every
page (Home's tagline, Itinerari listing, Itinerario detail, Articoli listing,
Articolo detail). Note this does **not** include the small eyebrow line above
it (that's just a `SectionHeader`, composed separately by each page) or the
sage-band background (that's `SageBand`, wrapped around this by pages that
need it — Itinerario/Articolo detail headers sit directly on crema).

```ts
interface Props {
  title: string;
}
```

Content next to the title varies per page (a plain paragraph on Itinerari
listing, a paragraph with an inline `DifficultyBadge` on Itinerario detail,
etc.) — too varied for a single string prop, so it's a **default slot**:

```astro
<PageHeader title="Gita al Rifugio Curò">
  <p>Difficoltà <DifficultyBadge level="E" withLabel /> , andata e ritorno sullo stesso sentiero.</p>
</PageHeader>
```

Layout: mobile-first single column (title, then slot content below); at
`md:` and up, switch to the mockup's 1.5fr/1fr grid with items aligned to the
baseline/end:

```
grid grid-cols-1 gap-4 md:grid-cols-[1.5fr_1fr] md:gap-12 md:items-end
```

## Placeholder media pattern (small addition to `global.css`)

Every list/detail piece still needs a placeholder box (no real images until
Directus is wired in Step 5+). Add two small reusable utility classes to
`global.css` rather than repeating inline `background-image` gradients in
every component:

```css
.media-placeholder {
  @apply bg-pietra rounded-lg;
}
.media-placeholder-diagonal {
  background-image: repeating-linear-gradient(135deg, rgb(27 42 37 / 0.06) 0 6px, transparent 6px 12px);
}
.media-placeholder-grid {
  background-image:
    repeating-linear-gradient(0deg, rgb(27 42 37 / 0.07) 0 1px, transparent 1px 22px),
    repeating-linear-gradient(90deg, rgb(27 42 37 / 0.07) 0 1px, transparent 1px 22px);
}
```

(`diagonal` for article/gallery thumbnails, `grid` for route/map thumbnails —
matching the two patterns used in the mockup.) These get swapped for real
`<img>`/map output later without changing the components that use them.

## What "done" looks like

- `src/components/SectionHeader.astro`, `SageBand.astro`,
  `DifficultyBadge.astro`, `PageHeader.astro` exist; `src/lib/difficolta.ts`
  exists; `global.css` has the placeholder utility classes.
- Dropped into a throwaway page with hardcoded props, each renders correctly
  at mobile width and desktop width, matching the mockup's visual language
  (colors, type, spacing rhythm) without needing to match its exact pixels.
- `npm run build` succeeds.

## Open questions

None — component boundaries and props above are implementation calls within
the strategy already agreed; flag here only if building one of these reveals
a case the mockup doesn't cover.
