# Step 7 — Itinerari listing (static/non-interactive filters)

Part of `FRONTEND_BUILD_PLAN.md`. Adds `/itinerari`, wired to Directus using
the same fetch pattern proved in Steps 5–6. The route already has live links
pointing at it — Nav's "Itinerari" item (`src/components/Nav.astro`) and
Home's "Tutti gli itinerari →" action (`src/pages/index.astro`) both target
`/itinerari`, and every `RouteListItem` on Home already links to
`/itinerari/${slug}` — so this step fills in a currently-404ing route.

**Scope boundary for this step**: the FILTRI band gets its full visual
markup (sliders, difficulty toggles, caratteristiche checkboxes, "Azzera"),
but none of it filters anything yet — the list always shows every
itinerario. That's Step 8. This step is about proving the listing renders
real data correctly and giving Step 8 real DOM/markup to attach behavior to,
without writing throwaway HTML now.

## Goal

- `npm run build` succeeds against the live local Directus instance.
- `/itinerari` lists every `itinerari` row with real data (title, difficulty,
  excerpt, distance, D+/D−, time, type).
- The FILTRI band renders (sliders, difficulty chips, caratteristiche
  checkboxes, Azzera) but is inert — dragging a slider or checking a box
  does not change the list.
- Nav's "Itinerari" link and Home's "Tutti gli itinerari →" link resolve
  instead of 404ing.

## Schema facts

- `itinerari` fields in scope for this step: `titolo`, `slug`, `difficolta`,
  `distanza_km` (string), `dislivello_positivo`, `dislivello_negativo`,
  `tempo_medio_ore` (string), `is_loop`, `punto_partenza`, `punto_arrivo`,
  `descrizione` (markdown, used for a one-line excerpt only — see below).
  `is_child_friendly` / `is_winter_friendly` aren't needed yet: nothing
  renders them until Step 8's caratteristiche filters actually read them, so
  they're left out of this step's query rather than fetched unused.
- **No cover image for the listing thumbnail.** Unlike `articoli`, itinerari
  have no direct image field — the only images live behind the `galleria`
  m2m relation, and per `FRONTEND_BUILD_PLAN.md`'s schema note, **both
  `itinerari_galleria` and `itinerari_correlati` junction collections
  currently have zero permission rows for the API Reader policy** — not
  fixed yet. This step doesn't touch that; it isn't needed here either.
  Listing thumbnails stay `media-placeholder-grid` placeholders, same as
  Home's `RouteListItem` usage. Real thumbnails (from `galleria`) are a
  Step 9 concern, gated on that permissions fix.
- **Mockup shows a per-row excerpt on the full listing that Home's compact
  rows don't have** (e.g. "Salita classica dall'alta Val Seriana, sentiero
  ben segnalato su fondo misto."). No dedicated dek field exists (unlike a
  CMS excerpt field), but `descrizione` does — **decision: derive the
  excerpt from `descrizione`'s first paragraph, truncated to ~140 chars at a
  word boundary.** This is the same "no excerpt field, reuse the body text"
  situation Step 6 hit with `articoli.testo`, except here a defensible
  source field exists, so nothing gets dropped.
- **Mockup shows three stat lines on the full listing vs. two on Home's
  compact rows**: `9,2 km` / `850 m D+ · 850 m D−` / `3 h 30 · andata e
  ritorno` — Home's compact variant only shows `9,2 km · 850 m D+` /
  `3 h 30 · andata e ritorno` (no D−). `RouteListItem` needs an optional
  `elevationLossM` prop to switch between the two layouts.
- **The FILTRI band is the page's one salvia band — not the page header.**
  Checked directly against the mockup (`Scaio della Montagna.dc.html` lines
  78–96): the H1 + intro paragraph sit in a plain crema section *above* the
  salvia band, and the salvia band contains only FILTRI. This differs from
  Home and Articoli, where `PageHeader` sits *inside* `SageBand`. Follow the
  mockup's hierarchy here rather than copying the Home/Articoli pattern.
- **No "ARTICOLI"-style label above the H1.** The mockup's Itinerari header
  section has no small mono label line before "Itinerari" — go straight from
  Nav to H1. Confirmed by inspecting the mockup source directly (nothing
  between the nav's closing tag and the H1's grid).
- Decimal fields (`distanza_km`, `tempo_medio_ore`) come back from the API as
  strings, same wrinkle already handled on Home (Step 5) — `Number(...)`
  before use, same as `index.astro` already does.

## Decisions for this step

### `src/lib/directus.ts` — add `getItinerari()`

```ts
export function getItinerari() {
  return client.request(
    readItems("itinerari", {
      fields: [
        "titolo", "slug", "difficolta", "distanza_km", "dislivello_positivo",
        "dislivello_negativo", "tempo_medio_ore", "is_loop", "punto_partenza",
        "punto_arrivo", "descrizione",
      ],
      sort: ["-date_created"],
    }),
  );
}
```

No `limit`, same shape as `getArticoli()` — fetches every route. Sort order
barely matters here: the mockup's "Ordina per distanza" control is inert
this step (rendered as static `meta` text, see below) and becomes a real
client-side re-sort in Step 8, which will reorder DOM rows regardless of
the order they were server-rendered in.

### `src/lib/format.ts` — add `formatExcerpt()`

```ts
export function formatExcerpt(markdown: string, maxLength = 140): string {
  const firstParagraph = markdown.split(/\n\s*\n/)[0].trim();
  if (firstParagraph.length <= maxLength) return firstParagraph;
  const truncated = firstParagraph.slice(0, maxLength);
  return `${truncated.slice(0, truncated.lastIndexOf(" "))}…`;
}
```

Same "split on blank lines" approach Step 6 used for `testo`, plus a
word-boundary truncation `articoli` never needed (its excerpt requirement
was dropped entirely rather than derived).

### `src/components/RouteListItem.astro` — add optional `elevationLossM` and `excerpt` props

```astro
---
import DifficultyBadge from "./DifficultyBadge.astro";

interface Props {
  title: string;
  href: string;
  difficulty: "T" | "E" | "EE" | "EEA" | "OFA";
  distanceKm: number;
  elevationGainM: number;
  elevationLossM?: number;
  timeLabel: string;
  typeLabel: string;
  excerpt?: string;
}

const {
  title, href, difficulty, distanceKm, elevationGainM, elevationLossM,
  timeLabel, typeLabel, excerpt,
} = Astro.props;
---

<div class={`grid grid-cols-[64px_1fr] sm:grid-cols-[96px_1fr_210px] gap-4 sm:gap-6 py-5 ${excerpt ? "items-start" : "items-center"}`}>
  <a href={href} class="media-placeholder media-placeholder-grid h-16 sm:h-[72px] row-span-2 sm:row-span-1"></a>
  <div>
    <div class="flex items-baseline gap-3.5">
      <h3 class="text-xl sm:text-2xl font-normal tracking-tight leading-snug">
        <a href={href} class="hover:text-terra">{title}</a>
      </h3>
      <DifficultyBadge level={difficulty} />
    </div>
    {excerpt && <p class="mt-2 text-sm text-inchiostro/82">{excerpt}</p>}
  </div>
  <div class="col-start-2 sm:col-start-3 font-mono-data text-xs text-inchiostro/80 leading-loose sm:text-right">
    {elevationLossM !== undefined ? (
      <>{distanceKm} km<br />{elevationGainM} m D+ · {elevationLossM} m D−<br /></>
    ) : (
      <>{distanceKm} km · {elevationGainM} m D+<br /></>
    )}
    {timeLabel} · {typeLabel}
  </div>
</div>
```

Home's existing usage (no `elevationLossM`, no `excerpt`) renders identically
to today: same two-line stat block, same `items-center` alignment, no
excerpt paragraph. Both new props are additive.

### `src/components/FilterPanel.astro` (new — inert this step)

```astro
---
interface Props {
  maxDistanzaKm: number;
  maxDislivelloM: number;
  maxTempoOre: number;
}

const { maxDistanzaKm, maxDislivelloM, maxTempoOre } = Astro.props;
const difficolta = ["T", "E", "EE", "EEA", "OFA"] as const;
---

<div>
  <div class="flex items-center gap-4 mb-6">
    <span class="font-mono-data text-xs tracking-widest uppercase text-terra">FILTRI</span>
    <span class="flex-1 h-px bg-inchiostro/22"></span>
    <button type="button" id="filtri-azzera" class="text-terra">Azzera</button>
  </div>

  <div class="grid grid-cols-1 gap-8 sm:grid-cols-3 sm:gap-9">
    <label class="block">
      <div class="flex justify-between font-mono-data text-[13px] mb-3.5">
        <span class="text-inchiostro/82">distanza</span>
        <span id="distanza-value">0 – {maxDistanzaKm} km</span>
      </div>
      <input type="range" id="filtro-distanza" min="0" max={maxDistanzaKm} value={maxDistanzaKm} step="0.5" class="w-full accent-verde" />
    </label>
    <label class="block">
      <div class="flex justify-between font-mono-data text-[13px] mb-3.5">
        <span class="text-inchiostro/82">dislivello +</span>
        <span id="dislivello-value">0 – {maxDislivelloM} m</span>
      </div>
      <input type="range" id="filtro-dislivello" min="0" max={maxDislivelloM} value={maxDislivelloM} step="10" class="w-full accent-verde" />
    </label>
    <label class="block">
      <div class="flex justify-between font-mono-data text-[13px] mb-3.5">
        <span class="text-inchiostro/82">tempo medio</span>
        <span id="tempo-value">fino a {maxTempoOre} h</span>
      </div>
      <input type="range" id="filtro-tempo" min="0" max={maxTempoOre} value={maxTempoOre} step="0.5" class="w-full accent-verde" />
    </label>
  </div>

  <div class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-3 sm:items-start">
    <div>
      <div class="font-mono-data text-[13px] text-inchiostro/82 mb-4">difficoltà</div>
      <div class="flex gap-5 font-mono-data text-sm">
        {difficolta.map((level) => (
          <label class="cursor-pointer">
            <input type="checkbox" name="difficolta" value={level} checked class="peer sr-only" />
            <span class="text-inchiostro/82 border-b-2 border-transparent pb-1 peer-checked:text-inchiostro peer-checked:font-medium peer-checked:border-terra">{level}</span>
          </label>
        ))}
      </div>
    </div>
    <div class="sm:col-span-2">
      <div class="font-mono-data text-[13px] text-inchiostro/82 mb-4">caratteristiche</div>
      <div class="flex flex-wrap gap-6 text-sm">
        <label class="flex items-center gap-2"><input type="checkbox" id="filtro-bambini" class="accent-verde" /> Adatto ai bambini</label>
        <label class="flex items-center gap-2"><input type="checkbox" id="filtro-inverno" class="accent-verde" /> Adatto in inverno</label>
        <label class="flex items-center gap-2"><input type="checkbox" id="filtro-anello" class="accent-verde" /> Ad anello</label>
        <label class="flex items-center gap-2"><input type="checkbox" id="filtro-vicino" class="accent-verde" /> Vicino a me</label>
      </div>
    </div>
  </div>
</div>
```

**Why real `<input type="range">`/`checkbox` elements instead of the
mockup's hand-drawn slider divs**: the mockup fakes sliders with absolutely
positioned `<span>`s because it's a static design comp, not a page. Using
real form controls now means Step 8 only adds a `<script>` with event
listeners and comparison logic — it doesn't have to rewrite this markup to
make it interactive. `id`s are chosen to be the attachment points Step 8
will use (`filtro-distanza`, `filtro-bambini`, `filtri-azzera`, etc.).
Values default to "no filter applied" (sliders at max, checkboxes
unchecked, all difficulty chips checked) since that's the correct rest
state for an inert panel — the mockup's own slider positions (e.g. 60%) are
just illustrative of the interaction, not a real default.

The difficulty chips are plain checkboxes visually styled as toggle chips
(`peer` + `peer-checked`), not a reuse of `DifficultyBadge` — that component
is a read-only display badge (used inside `RouteListItem`), not an
interactive control; reusing it here would conflate two different roles.

"Vicino a me" is a plain checkbox like the others in this step. It needs
`navigator.geolocation` in Step 8 to mean anything — see that step's doc.

### `src/pages/itinerari/index.astro` (new)

```astro
---
import Layout from "../../layouts/Layout.astro";
import SageBand from "../../components/SageBand.astro";
import SectionHeader from "../../components/SectionHeader.astro";
import PageHeader from "../../components/PageHeader.astro";
import RouteListItem from "../../components/RouteListItem.astro";
import FilterPanel from "../../components/FilterPanel.astro";
import { getItinerari } from "../../lib/directus";
import { formatTimeLabel, getTypeLabel, formatExcerpt } from "../../lib/format";

const itinerari = await getItinerari();

const maxDistanzaKm = Math.ceil(Math.max(...itinerari.map((r) => Number(r.distanza_km))));
const maxDislivelloM = Math.ceil(Math.max(...itinerari.map((r) => r.dislivello_positivo)) / 50) * 50;
const maxTempoOre = Math.ceil(Math.max(...itinerari.map((r) => Number(r.tempo_medio_ore))));

const countLabel = `${itinerari.length} ${itinerari.length === 1 ? "ITINERARIO" : "ITINERARI"}`;
---

<Layout title="Itinerari" active="itinerari">
  <div class="px-4 pt-8 sm:px-8 md:px-14">
    <PageHeader title="Itinerari">
      <p class="text-inchiostro/82">
        Muovi i valori e l'elenco si aggiorna subito: i filtri lavorano nel browser.
      </p>
    </PageHeader>
  </div>

  <SageBand>
    <FilterPanel maxDistanzaKm={maxDistanzaKm} maxDislivelloM={maxDislivelloM} maxTempoOre={maxTempoOre} />
  </SageBand>

  <section class="px-4 py-8 sm:px-8 md:px-14">
    <SectionHeader label={countLabel} meta="Ordina per distanza" />
    <div class="mt-6 divide-y divide-inchiostro/14">
      {itinerari.map((r) => (
        <RouteListItem
          title={r.titolo}
          href={`/itinerari/${r.slug}`}
          difficulty={r.difficolta}
          distanceKm={Number(r.distanza_km)}
          elevationGainM={r.dislivello_positivo}
          elevationLossM={r.dislivello_negativo}
          timeLabel={formatTimeLabel(r.tempo_medio_ore)}
          typeLabel={getTypeLabel(r)}
          excerpt={formatExcerpt(r.descrizione)}
        />
      ))}
    </div>
  </section>
</Layout>
```

`meta="Ordina per distanza"` reuses `SectionHeader`'s existing plain-text
slot (no new prop needed) to match the mockup's sort-control text; it's
non-interactive this step, same "azzera"/sliders-do-nothing scope boundary.
`countLabel` is computed once at build time and isn't kept live — Step 8's
script updates the DOM text node directly as filters run, since the count
has to reflect the *filtered* set once filtering is real.

## What "done" looks like

- `directus.ts` has `getItinerari()` — no `limit`, matches `getArticoli()`'s
  shape.
- `format.ts` has `formatExcerpt()`.
- `RouteListItem.astro` has optional `elevationLossM` and `excerpt` props;
  Home's rendered output is byte-for-byte unchanged (neither prop passed
  there).
- `FilterPanel.astro` exists, renders sliders/chips/checkboxes/Azzera with
  the `id`s listed above, and is inert — no `<script>` in this step.
- `src/pages/itinerari/index.astro` exists, lists every real itinerario with
  title, difficulty badge, excerpt, and full three-line stats.
- Nav's "Itinerari" link and Home's "Tutti gli itinerari →" link resolve
  instead of 404ing.
- `npm run build` succeeds against the live local Directus instance.
- Checked at mobile width first, then wider viewports.

## Open questions

- **Thumbnails stay placeholders.** Real per-route thumbnails would come
  from `galleria`, which is blocked on the junction-permissions fix noted in
  `FRONTEND_BUILD_PLAN.md`. Not this step's problem to solve — tracked
  against Step 9.
- **`maxDislivelloM`'s rounding (`/50 → *50`) and the range steps
  (`step="0.5"` for km/ore, `step="10"` for meters) are reasonable
  placeholders**, not measured against real data volume. Revisit once real
  itinerari exist across a wider spread of values than the current handful.
- **Sort control is decorative this step.** Step 8 replaces the static
  `meta="Ordina per distanza"` text with a real control (a `<select>` most
  likely) — not decided yet whether it stays inside `SectionHeader` or sits
  beside it; see Step 8's doc.
