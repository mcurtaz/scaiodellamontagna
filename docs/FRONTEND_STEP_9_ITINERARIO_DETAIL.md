# Step 9 — Itinerario detail

Part of `FRONTEND_BUILD_PLAN.md`. Adds `/itinerari/[slug]`, the last route
and the most complex page in the build plan: a stats table, a track section
(GPX download + map), a description with a caratteristiche sidebar, an
image gallery, and related-routes ("si collega con"). Every `RouteListItem`
on Home and on `/itinerari` (Steps 5, 7) already links to
`/itinerari/${slug}` — this step fills in that currently-404ing route.

**Status: the junction-permissions blocker that used to gate this step is
fixed (2026-09-09).** API Reader now has Read access on both
`itinerari_galleria` and `itinerari_correlati`, verified directly against
the live instance while writing this revision (see "Schema facts" below for
what that verification turned up). The only section that still ships as a
placeholder is the map image itself — that's a separate, still-open research
question (`PROJECT_SPEC.md`'s "Map rendering" section), unrelated to
permissions.

| Section | Status this step |
|---|---|
| DATI (stats table) | ✅ fully buildable |
| DESCRIZIONE + caratteristiche sidebar | ✅ fully buildable |
| TRACCIA (GPX download + map) | ⚠️ GPX download ships; the map image itself stays a placeholder — see below |
| GALLERIA | ✅ fully buildable (permissions fixed) |
| SI COLLEGA CON | ✅ fully buildable (permissions fixed, symmetric-query shape confirmed) |

## Schema facts

- `itinerari` fields already in `types.ts`/fetched elsewhere: `id`,
  `titolo`, `slug`, `dislivello_positivo`, `dislivello_negativo`,
  `tempo_medio_ore` (string), `distanza_km` (string), `difficolta`,
  `is_child_friendly`, `is_winter_friendly`, `is_loop`, `punto_partenza`,
  `punto_arrivo`, `traccia_gpx` (file id, nullable), `descrizione`,
  `autore` (m2o).
- **Two mockup formatting conventions for the same value, in different
  contexts — confirmed against the mockup source, not assumed.** The DATI
  table shows tempo medio as decimal hours (`3,5 h`), while `RouteListItem`
  everywhere else shows it as hours+minutes (`3 h 30`). These are two
  different helpers, not one reused: `formatTimeLabel()` (existing, h/min)
  stays only for list/badge contexts; DATI needs a new
  `formatHoursDecimal()`.
- **Coordinates need reformatting for display.** `punto_partenza`/
  `punto_arrivo` are GeoJSON `{ coordinates: [lon, lat] }` — the DATI table
  shows `lat, lon` (e.g. `46.0090, 9.9520`), reversed from storage order,
  to 4 decimal places.
- **"arrivo" collapses to "stesso punto" when start and end coincide** —
  same coordinate-equality check `getTypeLabel()` (`src/lib/format.ts`)
  already does for the loop/andata-e-ritorno/traversata distinction; reused
  here rather than re-derived.
- **`descrizione` has the same markdown-rendering situation `articoli.testo`
  had in Step 6**: no simple "string in, HTML out" renderer wired up
  (`@astrojs/markdown-satteri` isn't meant for ad hoc use — see Step 6's
  doc for the full explanation). Same decision here: render as plain
  paragraphs split on blank lines, not parsed HTML.
- **Caratteristiche sidebar phrasing flips per boolean, confirmed against
  the mockup**: a route with all three booleans false renders "Non adatto
  ai bambini. / Non adatto in inverno. / Non ad anello." — the *positive*
  phrasing ("Adatto ai bambini.", "Ad anello.") is implied for the `true`
  case, though no mockup instance shows it. A small formatter handles both
  directions per field rather than hardcoding the negative case only.
- **Traccia GPX** is a plain file, downloadable via the same `/assets/{id}`
  endpoint already used for images (`assetUrl()` in `directus.ts`) — no new
  endpoint needed, just called without `width`/`quality` params since it's
  not an image transform.
- **`galleria`** — m2m via junction `itinerari_galleria`, confirmed live:
  `{ itinerari_id, directus_files_id, sort, didascalia }`. Querying
  `itinerari.galleria` with `fields: ["directus_files_id", "didascalia",
  "sort"]` returns the expected array (verified against item id 1: one
  image, `sort: 1`, `didascalia: null`). Not a blocker.
- **`correlati`** — self-referencing m2m via junction `itinerari_correlati`,
  confirmed live: `{ itinerari_id, itinerario_correlato, tipo }`
  (`itinerari_id` is the second foreign-key field the earlier draft of this
  doc left as an open question — now confirmed by querying the junction
  collection directly).
- **Important, confirmed empirically**: querying the auto-generated
  `itinerari.correlati` m2m field returns **only one direction** of the
  relation. With the one seeded link (item 1 `itinerari_id` → item 2
  `itinerario_correlato`, `tipo: "prosecuzione"`), fetching item 1's
  `correlati` returns that row, but fetching item 2's `correlati` returns
  `[]` — even though `PROJECT_SPEC.md` specifies the relation is
  **symmetric with no stored direction** (linking A→B once should surface
  on both A's and B's pages). **Decision, confirmed working**: don't query
  `itinerari.correlati` at all for this page. Query the
  `itinerari_correlati` junction collection directly, filtered with an
  `_or` across both foreign-key fields:
  ```
  filter: { _or: [{ itinerari_id: { _eq: id } }, { itinerario_correlato: { _eq: id } }] }
  ```
  Verified against both directions (id 1 and id 2) — both return the same
  single junction row, as expected for a symmetric relation. See
  `getCorrelati()` below.

## Decisions for this step

### `src/lib/types.ts` — add gallery/correlati types, extend `Schema`

```ts
export interface GalleriaImage {
  directus_files_id: string;
  didascalia: string | null;
  sort: number | null;
}

export interface ItinerarioCorrelatoJunction {
  id: number;
  tipo: "prosecuzione" | "variante" | "nella_zona";
  itinerari_id: number | Itinerario;
  itinerario_correlato: number | Itinerario;
}
```

Add `galleria?: GalleriaImage[]` to the `Itinerario` interface (optional —
Home's and the listing's queries, Steps 5/7/8, don't request it, so it's
`undefined` there, not an empty array). `correlati` is deliberately **not**
added to `Itinerario` — per the schema fact above, that auto-generated field
is one-directional and this step bypasses it entirely, so there's no reason
to type it.

Extend `Schema` with the new junction collection so `readItems`/`readItem`
type-check against it:

```ts
export interface Schema {
  articoli: Articolo[];
  itinerari: Itinerario[];
  itinerari_correlati: ItinerarioCorrelatoJunction[];
  autori: Autore[];
}
```

(`itinerari_galleria` doesn't need its own `Schema` entry — it's only ever
queried through the `galleria` m2m alias field on `itinerari`, never
directly, unlike `itinerari_correlati`.)

### `src/lib/format.ts` — add detail-page-only formatters

```ts
import type { Itinerario, GeoPoint } from "./types";

export function formatHoursDecimal(hours: number | string): string {
  return `${Number(hours).toLocaleString("it-IT", { maximumFractionDigits: 1 })} h`;
}

export function formatCoordinates(point: GeoPoint): string {
  const [lon, lat] = point.coordinates;
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

export function sameCoordinates(a: GeoPoint, b: GeoPoint): boolean {
  return a.coordinates[0] === b.coordinates[0] && a.coordinates[1] === b.coordinates[1];
}

export function caratteristicheLines(it: Pick<Itinerario, "is_child_friendly" | "is_winter_friendly" | "is_loop">): string[] {
  return [
    it.is_child_friendly ? "Adatto ai bambini." : "Non adatto ai bambini.",
    it.is_winter_friendly ? "Adatto in inverno." : "Non adatto in inverno.",
    it.is_loop ? "Ad anello." : "Non ad anello.",
  ];
}
```

`getTypeLabel()` (existing) could be refactored to use the new
`sameCoordinates()` instead of its own inline comparison, but that's an
optional cleanup, not required by this step — noted so it doesn't get
"discovered" later as unexplained duplication.

### `src/lib/directus.ts` — add `getItinerariDetail()` and `getCorrelati()`

```ts
export function getItinerariDetail() {
  return client.request(
    readItems("itinerari", {
      fields: [
        "id", "titolo", "slug", "difficolta", "distanza_km", "dislivello_positivo",
        "dislivello_negativo", "tempo_medio_ore", "is_loop", "is_child_friendly",
        "is_winter_friendly", "punto_partenza", "punto_arrivo", "traccia_gpx", "descrizione",
        { autore: ["nome"] },
        { galleria: ["directus_files_id", "didascalia", "sort"] },
      ],
    }),
  );
}

export async function getCorrelati(id: number) {
  const junctions = await client.request(
    readItems("itinerari_correlati", {
      filter: { _or: [{ itinerari_id: { _eq: id } }, { itinerario_correlato: { _eq: id } }] },
      fields: [
        "tipo",
        { itinerari_id: ["id", "titolo", "slug", "difficolta", "distanza_km", "dislivello_positivo", "dislivello_negativo", "tempo_medio_ore", "is_loop", "punto_partenza", "punto_arrivo"] },
        { itinerario_correlato: ["id", "titolo", "slug", "difficolta", "distanza_km", "dislivello_positivo", "dislivello_negativo", "tempo_medio_ore", "is_loop", "punto_partenza", "punto_arrivo"] },
      ],
    }),
  );

  return junctions.map((j) => ({
    tipo: j.tipo,
    itinerario: (typeof j.itinerari_id === "object" && j.itinerari_id.id === id ? j.itinerario_correlato : j.itinerari_id) as Itinerario,
  }));
}
```

`getItinerariDetail()` is a separate function from Step 7/8's
`getItinerari()`, not an extension of it — the listing query deliberately
only fetches what it renders (`FRONTEND_STEP_7`'s stated principle), and
`autore`/`galleria`/`traccia_gpx` would be dead weight on every listing row.
Two functions, two purposes.

`getCorrelati()` normalizes the junction's two possible "which side is the
current item" shapes into one `{ tipo, itinerario }` shape regardless of
which side the link was created from — this is what makes the relation
actually behave symmetrically on both routes' pages, matching
`PROJECT_SPEC.md`'s intent despite the underlying m2m field not doing that
for free.

**N+1 accepted here, deliberately**: `getStaticPaths` below calls
`getCorrelati()` once per itinerario. At "tens of routes" volume
(`PROJECT_SPEC.md`'s stated scale) this is a handful of extra build-time
requests, not a real cost, and it's simpler than one aggregate query that'd
need post-processing to regroup by itinerario anyway. This only runs at
build time, never per-request, consistent with the project's "static as
possible" goal.

### `src/components/DataTable.astro` (new)

```astro
---
interface Row {
  label: string;
  value: string;
}

interface Props {
  rows: Row[];
}

const { rows } = Astro.props;
const lastRowStart = Math.floor((rows.length - 1) / 3) * 3;
---

<div class="grid grid-cols-1 gap-x-11 sm:grid-cols-3">
  {rows.map((row, i) => (
    <div class={`flex justify-between py-3 font-mono-data text-[13px] border-b border-inchiostro/18 last:border-0 ${i < lastRowStart ? "sm:border-b" : "sm:border-0"}`}>
      <span class="text-inchiostro/82">{row.label}</span>
      <span>{row.value}</span>
    </div>
  ))}
</div>
```

Single column (every row bordered except the last) below `sm`, a 3-column
grid matching the mockup's DATI table above it — border-bottom applies only
to rows that aren't in the final visual row of the grid. Generic over row
count, but written and checked against the itinerario stats' fixed 6 rows.

### `src/components/MapThumbnail.astro` (new — placeholder only)

```astro
---
interface Props {
  imageUrl?: string;
}

const { imageUrl } = Astro.props;
---

{imageUrl ? (
  <img src={imageUrl} alt="Mappa della traccia" class="h-[300px] w-full rounded-lg object-cover" />
) : (
  <div class="media-placeholder media-placeholder-grid h-[300px] w-full flex items-end p-4">
    <span class="font-mono-data text-[10px] tracking-widest uppercase text-inchiostro/80">Mappa statica</span>
  </div>
)}
```

**Why this ships as a placeholder rather than a real rendered map**: per
`PROJECT_SPEC.md`'s "Map rendering" section, the *generation mechanism* —
which static-map provider or self-hosted renderer, GPX-parsing approach,
whether it happens at Astro build time or is pre-generated on the Directus
side — is explicitly still open research, unrelated to the junction
permissions fixed for this step. `FRONTEND_BUILD_PLAN.md`'s Decision #7
locks in *that* the final result is a static `<img>` (not a client-side map
library), which is exactly why `MapThumbnail` takes an `imageUrl?` prop
shaped to accept that `<img>` src the moment it exists — swapping in a real
map later is a prop change on the call site, not a component rewrite.

### `src/components/Gallery.astro` (new)

```astro
---
interface GalleryImage {
  url: string;
  caption: string | null;
}

interface Props {
  cover: GalleryImage;
  images: GalleryImage[];
}

const { cover, images } = Astro.props;
---

<div>
  <img src={cover.url} alt={cover.caption ?? ""} class="h-[260px] w-full rounded-lg object-cover" />
  {cover.caption && <p class="mt-3 text-sm text-inchiostro/82">{cover.caption}</p>}

  {images.length > 0 && (
    <div class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
      {images.map((img) => (
        <div>
          <img src={img.url} alt={img.caption ?? ""} class="aspect-[3/2] w-full rounded-lg object-cover" />
          <p class="mt-2.5 text-[12.5px] text-inchiostro/82">{img.caption ?? "Didascalia immagine"}</p>
        </div>
      ))}
    </div>
  )}
</div>
```

Matches the mockup exactly: cover image + caption below, then a 3-up grid
of the rest, each with its own caption (a generic "Didascalia immagine"
placeholder when `didascalia` is empty, same spirit as the mockup's own
placeholder captions). Not rendered at all when an itinerario has zero
gallery images — see the page code below.

### `src/components/SectionHeader.astro` — add optional `badge` prop

```astro
---
interface Props {
  label: string;
  tone?: "onCrema" | "onSage";
  action?: { label: string; href: string };
  meta?: string;
  badge?: string;
}

const { label, tone = "onCrema", action, meta, badge } = Astro.props;
const labelColor = tone === "onSage" ? "text-terra" : "text-verde";
---

<div class="flex flex-wrap items-center gap-3">
  <span class={`font-mono-data text-xs tracking-widest uppercase ${labelColor}`}>{label}</span>
  <span class="flex-1 h-px bg-current/20 min-w-6"></span>
  {action && (
    <a href={action.href} class="text-terra">{action.label}</a>
  )}
  {meta && (
    <span class="font-mono-data text-xs text-inchiostro/82">{meta}</span>
  )}
  {badge && (
    <span class="font-mono-data text-[11.5px] tracking-wider font-medium text-terra">{badge}</span>
  )}
</div>
```

Only addition is `badge` — bold uppercase mono/terra, distinct from
`meta`'s plain-weight text, matching the mockup's "PROSECUZIONE" treatment
next to the "SI COLLEGA CON" label. Every existing call site is unaffected
(prop not passed, nothing renders).

### `src/pages/itinerari/[slug].astro` (new)

```astro
---
import Layout from "../../layouts/Layout.astro";
import SageBand from "../../components/SageBand.astro";
import SectionHeader from "../../components/SectionHeader.astro";
import PageHeader from "../../components/PageHeader.astro";
import DataTable from "../../components/DataTable.astro";
import MapThumbnail from "../../components/MapThumbnail.astro";
import Gallery from "../../components/Gallery.astro";
import RouteListItem from "../../components/RouteListItem.astro";
import { getItinerariDetail, getCorrelati, assetUrl } from "../../lib/directus";
import {
  formatHoursDecimal, formatCoordinates, sameCoordinates, caratteristicheLines,
  formatTimeLabel, getTypeLabel,
} from "../../lib/format";
import { DIFFICOLTA_LABELS } from "../../lib/difficolta";
import type { Itinerario, Autore } from "../../lib/types";

const TIPO_LABELS = { prosecuzione: "PROSECUZIONE", variante: "VARIANTE", nella_zona: "NELLA ZONA" } as const;
const TIPO_ORDER = ["prosecuzione", "variante", "nella_zona"] as const;

export async function getStaticPaths() {
  const itinerari = await getItinerariDetail();
  const correlati = await Promise.all(itinerari.map((it) => getCorrelati(it.id)));
  return itinerari.map((itinerario, i) => ({
    params: { slug: itinerario.slug },
    props: { itinerario, correlati: correlati[i] },
  }));
}

interface Props {
  itinerario: Itinerario & { autore: Autore };
  correlati: { tipo: "prosecuzione" | "variante" | "nella_zona"; itinerario: Itinerario }[];
}

const { itinerario: it, correlati } = Astro.props;

const rows = [
  { label: "distanza", value: `${Number(it.distanza_km).toLocaleString("it-IT")} km` },
  { label: "dislivello +", value: `${it.dislivello_positivo} m` },
  { label: "dislivello −", value: `${it.dislivello_negativo} m` },
  { label: "tempo medio", value: formatHoursDecimal(it.tempo_medio_ore) },
  { label: "partenza", value: formatCoordinates(it.punto_partenza) },
  {
    label: "arrivo",
    value: sameCoordinates(it.punto_partenza, it.punto_arrivo) ? "stesso punto" : formatCoordinates(it.punto_arrivo),
  },
];

const paragraphs = it.descrizione.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
const caratteristiche = caratteristicheLines(it);

const sortedGalleria = [...(it.galleria ?? [])].sort((a, b) => (a.sort ?? 0) - (b.sort ?? 0));
const [coverImg, ...restImg] = sortedGalleria;
const cover = coverImg && {
  url: assetUrl(coverImg.directus_files_id, { width: 1200, quality: 80 }),
  caption: coverImg.didascalia,
};
const galleryRest = restImg.map((img) => ({
  url: assetUrl(img.directus_files_id, { width: 500, quality: 80 }),
  caption: img.didascalia,
}));

const correlatiGroups = TIPO_ORDER
  .map((tipo) => ({ tipo, items: correlati.filter((c) => c.tipo === tipo) }))
  .filter((g) => g.items.length > 0);
---

<Layout title={it.titolo} active="itinerari">
  <div class="px-4 pt-8 sm:px-8 md:px-14">
    <SectionHeader label="ITINERARIO" meta={it.autore.nome} />
    <div class="mt-8">
      <PageHeader title={it.titolo}>
        <p class="text-inchiostro/82">
          Difficoltà <span class="font-semibold text-verde">{it.difficolta} — {DIFFICOLTA_LABELS[it.difficolta].toLowerCase()}</span>,
          {" "}{getTypeLabel(it)}.
        </p>
      </PageHeader>
    </div>
  </div>

  <SageBand>
    <SectionHeader label="DATI" tone="onSage" />
    <div class="mt-6">
      <DataTable rows={rows} />
    </div>
  </SageBand>

  <section class="px-4 py-8 sm:px-8 md:px-14">
    <SectionHeader
      label="TRACCIA"
      action={it.traccia_gpx ? { label: "Scarica GPX ↓", href: assetUrl(it.traccia_gpx) } : undefined}
    />
    <div class="mt-6">
      <MapThumbnail />
    </div>
  </section>

  <section class="px-4 pb-8 sm:px-8 md:px-14">
    <SectionHeader label="DESCRIZIONE" />
    <div class="mt-8 grid grid-cols-1 gap-4 md:grid-cols-[1.5fr_1fr] md:gap-12">
      <div class="space-y-5">
        {paragraphs.map((p) => (
          <p class="text-[17.5px] leading-[1.72] text-inchiostro">{p}</p>
        ))}
      </div>
      <div class="border-l-2 border-terra pl-5 text-sm leading-loose text-inchiostro/82">
        {caratteristiche.map((line) => <>{line}<br /></>)}
      </div>
    </div>
  </section>

  {cover && (
    <section class="px-4 pb-8 sm:px-8 md:px-14">
      <SectionHeader label="GALLERIA" meta={`${sortedGalleria.length} ${sortedGalleria.length === 1 ? "immagine" : "immagini"}`} />
      <div class="mt-6">
        <Gallery cover={cover} images={galleryRest} />
      </div>
    </section>
  )}

  {correlatiGroups.map((group) => (
    <SageBand>
      <SectionHeader label="SI COLLEGA CON" tone="onSage" badge={TIPO_LABELS[group.tipo]} />
      <div class="mt-8 divide-y divide-inchiostro/14">
        {group.items.map((c) => (
          <RouteListItem
            title={c.itinerario.titolo}
            href={`/itinerari/${c.itinerario.slug}`}
            difficulty={c.itinerario.difficolta}
            distanceKm={Number(c.itinerario.distanza_km)}
            elevationGainM={c.itinerario.dislivello_positivo}
            timeLabel={formatTimeLabel(c.itinerario.tempo_medio_ore)}
            typeLabel={getTypeLabel(c.itinerario)}
          />
        ))}
      </div>
    </SageBand>
  ))}
</Layout>
```

Notes on decisions folded into this page code:

- `SectionHeader`'s existing `action` prop already supports an optional
  `href`-only action, so "Scarica GPX ↓" reuses it as-is; when
  `traccia_gpx` is null the action is simply omitted (`undefined`), no new
  prop needed.
- The GALLERIA section is wrapped in `{cover && (...)}` and skipped
  entirely for any itinerario with an empty `galleria` array — no empty
  "0 immagini" section ever renders.
- Related routes ("si collega con") reuse `RouteListItem` **without** the
  `elevationLossM`/`excerpt` props from Step 7, i.e. its original
  two-line compact stat block. The mockup actually shows a third, slightly
  different stat-line combination for this specific row (km alone / D+ and
  time on one line / type alone) — a one-off variant not worth a third prop
  combination for a single low-traffic section. Per
  `FRONTEND_BUILD_PLAN.md`'s own framing ("the mockup is a starting point,
  not a pixel spec"), reusing the existing compact rendering here is a
  deliberate simplification, not an oversight.
- `TIPO_LABELS`'s exact Italian wording (`"VARIANTE"`, `"NELLA ZONA"`) is a
  reasonable guess for the two tipos the mockup doesn't show an example
  of (only `"prosecuzione"` → `"PROSECUZIONE"` is confirmed against the
  mockup) — revisit copy once a `variante`/`nella_zona` example actually
  exists to check against.

## What "done" looks like

- `types.ts` has `GalleriaImage`, `ItinerarioCorrelatoJunction`, extends
  `Schema` with `itinerari_correlati`, and adds optional `galleria?` to
  `Itinerario`.
- `format.ts` has `formatHoursDecimal()`, `formatCoordinates()`,
  `sameCoordinates()`, `caratteristicheLines()`.
- `directus.ts` has `getItinerariDetail()` and `getCorrelati()`; the latter
  returns the same relation regardless of which itinerario in the pair it's
  called for (verify against two linked itinerari, both directions).
- `DataTable.astro`, `MapThumbnail.astro`, `Gallery.astro` exist and match
  the shapes above; `SectionHeader.astro` has the optional `badge` prop.
- `src/pages/itinerari/[slug].astro` exists; `getStaticPaths` returns one
  path per itinerario; each page renders real title, difficulty, author,
  the six-row DATI table, a GPX download link (when `traccia_gpx` is set),
  the placeholder map, description paragraphs, the caratteristiche sidebar
  with correctly-flipped phrasing, a GALLERIA section when images exist
  (skipped otherwise), and a SI COLLEGA CON band per non-empty `tipo` group
  — confirmed showing up on **both** sides of a linked pair.
- Every `RouteListItem` linking to `/itinerari/${slug}` (Home, the
  listing) resolves instead of 404ing.
- `npm run build` succeeds against the live local Directus instance.
- Checked at mobile width first, then wider viewports.

## Open questions

- **Static map generation mechanism** — provider vs. self-hosted, GPX
  parsing approach, build-time vs. pre-generated-on-Directus — genuinely
  unresolved; see `PROJECT_SPEC.md`'s "Map rendering" section. This step
  deliberately ships the placeholder rather than guessing at a provider.
- **Elevation profile image** — `PROJECT_SPEC.md` floats this as a possible
  addition alongside the map on this same page section; not designed here
  at all, fully deferred.
- **`variante`/`nella_zona` badge copy is unverified against a real
  example** — only `prosecuzione` → "PROSECUZIONE" is confirmed against the
  mockup; the other two labels are a reasonable guess, not a checked fact.
- **N+1 `getCorrelati()` calls in `getStaticPaths`** — accepted as fine at
  current/expected data volume (see "Decisions" above); revisit only if
  itinerari count grows far beyond "tens per year."
