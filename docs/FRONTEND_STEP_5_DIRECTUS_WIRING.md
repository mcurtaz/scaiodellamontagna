# Step 5 — Wire Home to Directus

Part of `FRONTEND_BUILD_PLAN.md`. Replaces Step 4's hardcoded Home content
with real data fetched from Directus at build time. This is the first piece
of the data layer (`@directus/sdk`, `src/lib/directus.ts`, `src/lib/types.ts`)
and is deliberately scoped to the lowest-risk page — Home only needs two
articoli, two itinerari, and two counts, none of the harder relations
(galleria, correlati) that later steps need.

**Goal:** after this step, `astro dev`/`npm run build` render Home from live
Directus data, and the output is **visually identical** to Step 4's hardcoded
version — same titles, same numbers, same formatted strings. That equivalence
is the proof that the fetch layer is correct.

## Schema facts checked directly against the local instance

Re-verified against the running local Directus (`docker compose ps` showed
`scaio_directus`/`scaio_postgres` up) rather than assumed from
`PROJECT_SPEC.md`, since a couple of field names in `FRONTEND_BUILD_PLAN.md`
turned out to be wrong:

- Decimal fields (`tempo_medio_ore`, `distanza_km`) come back from the API as
  **strings** (`"3.50000"`, `"9.20000"`), not numbers — Directus does this for
  all `decimal`-type fields to avoid float precision loss. Integer fields
  (`dislivello_positivo`, `dislivello_negativo`) come back as plain numbers.
  **This step's fetch layer must `Number(...)` the decimal fields before
  handing them to components** — `RouteListItem`'s props are typed `number`.
- `punto_partenza` / `punto_arrivo` are GeoJSON `Point` objects:
  `{ type: "Point", coordinates: [lon, lat] }`.
- The two fields the build plan flagged as unresolved — the gallery and the
  related-routes junction — actually exist under different names than
  documented, and are **not needed by this step** (Home doesn't touch either):
  `itinerari.galleria` (m2m → `directus_files`, junction collection
  `itinerari_galleria` with `directus_files_id`, `sort`, `didascalia`) and
  `itinerari.correlati` (self-referencing m2m, junction collection
  `itinerari_correlati` with `itinerario_correlato`, `tipo`). See
  "Corrections carried back into the build plan" below — this matters for
  Steps 6–9, not this one.

## Decisions for this step

### Env vars: point Astro at the existing root `.env`, don't duplicate it

`DIRECTUS_URL` and `DIRECTUS_TOKEN` already exist in the repo-root `.env`
(used today for schema inspection). Astro by default only reads `.env` from
its own project root (`astro/`), so add:

```js
// astro.config.mjs
export default defineConfig({
  envDir: "../", // read the repo-root .env instead of astro/.env
  vite: { plugins: [tailwindcss()] },
});
```

One `.env`, one source of truth, instead of copying values into a second
`astro/.env`. This does mean `DIRECTUS_ADMIN_EMAIL`/`DIRECTUS_ADMIN_PASSWORD`
are technically loadable via `import.meta.env` during the build — harmless as
long as nothing in `src/` references them (nothing should; only
`DIRECTUS_URL`/`DIRECTUS_TOKEN` are used). Not `PUBLIC_`-prefixed: both vars
are only read in `.astro` frontmatter, which runs at build time for a fully
static site — the values get inlined into the output HTML (as asset URLs) or
used server-side to call the API, never shipped as client JS reading
`import.meta.env` at runtime, so the `PUBLIC_` convention doesn't apply here.

### `src/lib/types.ts`

TS interfaces mirroring the schema, decimal fields typed as they actually
arrive over the wire (`string`), converted at the call site:

```ts
export interface Autore {
  id: number;
  nome: string;
  bio: string;
  foto: string | null;
}

export interface GeoPoint {
  type: "Point";
  coordinates: [number, number]; // [lon, lat]
}

export interface Articolo {
  id: number;
  titolo: string;
  slug: string;
  immagine: string | null;
  testo: string;
  autore: number | Autore;
}

export interface Itinerario {
  id: number;
  titolo: string;
  slug: string;
  dislivello_positivo: number;
  dislivello_negativo: number;
  tempo_medio_ore: string;
  distanza_km: string;
  difficolta: "T" | "E" | "EE" | "EEA" | "OFA";
  is_child_friendly: boolean;
  is_winter_friendly: boolean;
  is_loop: boolean;
  punto_partenza: GeoPoint;
  punto_arrivo: GeoPoint;
  traccia_gpx: string | null;
  descrizione: string;
  autore: number | Autore;
}

export interface Schema {
  articoli: Articolo[];
  itinerari: Itinerario[];
  autori: Autore[];
}
```

### `src/lib/directus.ts`

```ts
import { createDirectus, rest, staticToken, readItems, aggregate } from "@directus/sdk";
import type { Schema } from "./types";

const client = createDirectus<Schema>(import.meta.env.DIRECTUS_URL)
  .with(staticToken(import.meta.env.DIRECTUS_TOKEN))
  .with(rest());

export function assetUrl(fileId: string, params?: { width?: number; quality?: number }) {
  const url = new URL(`/assets/${fileId}`, import.meta.env.DIRECTUS_URL);
  if (params?.width) url.searchParams.set("width", String(params.width));
  if (params?.quality) url.searchParams.set("quality", String(params.quality));
  return url.toString();
}

export function getHomeArticoli() {
  return client.request(
    readItems("articoli", {
      fields: ["titolo", "slug", "immagine", { autore: ["nome"] }],
      sort: ["-date_created"],
      limit: 2,
    }),
  );
}

export function getHomeItinerari() {
  return client.request(
    readItems("itinerari", {
      fields: [
        "titolo", "slug", "difficolta", "distanza_km", "dislivello_positivo",
        "tempo_medio_ore", "is_loop", "punto_partenza", "punto_arrivo",
      ],
      sort: ["-date_created"],
      limit: 2,
    }),
  );
}

export async function getCounts() {
  const [articoli, itinerari] = await Promise.all([
    client.request(aggregate("articoli", { aggregate: { count: "*" } })),
    client.request(aggregate("itinerari", { aggregate: { count: "*" } })),
  ]);
  return { articoli: Number(articoli[0].count), itinerari: Number(itinerari[0].count) };
}
```

`sort: ["-date_created"]` gives "latest first" for both — matches the
sections' "ULTIMI ARTICOLI"/"ULTIMI ITINERARI" (most recent) labels. Directus
aggregate `count` also comes back as a string, hence the `Number(...)`.

### `src/lib/format.ts` — small formatting helpers, not Directus-specific

```ts
export function formatTimeLabel(hours: number | string): string {
  const h = Number(hours);
  const wholeHours = Math.floor(h);
  const minutes = Math.round((h - wholeHours) * 60);
  return minutes === 0 ? `${wholeHours} h` : `${wholeHours} h ${minutes}`;
}

export function getTypeLabel(it: Pick<Itinerario, "is_loop" | "punto_partenza" | "punto_arrivo">): string {
  if (it.is_loop) return "anello";
  const [lonA, latA] = it.punto_partenza.coordinates;
  const [lonB, latB] = it.punto_arrivo.coordinates;
  return lonA === lonB && latA === latB ? "andata e ritorno" : "traversata";
}
```

`getTypeLabel` is a direct implementation of `PROJECT_SPEC.md`'s three cases
(anello / andata e ritorno / traversata) — the only field-derived display
logic Home needs. `formatTimeLabel(3.5)` → `"3 h 30"`, `formatTimeLabel(1)` →
`"1 h"`, matching Step 4's hardcoded strings exactly.

### `ArticleListItem.astro` — add an optional `imageUrl` prop

The only component change this step needs. `RouteListItem`'s thumbnail stays
a placeholder — it's a **map** thumbnail (`MapThumbnail.astro`, static image
per the decision below), and building that is Step 9's job, not this one's.
`immagine` on `articoli` is a plain single file id with no such dependency,
so it's low-risk to wire now:

```ts
interface Props {
  title: string;
  href: string;
  author: string;
  imageUrl?: string;
}
```

```astro
{imageUrl ? (
  <a href={href} class="block h-16 sm:h-[72px] row-span-2 sm:row-span-1 overflow-hidden">
    <img src={imageUrl} alt="" class="h-full w-full object-cover" />
  </a>
) : (
  <a href={href} class="media-placeholder media-placeholder-diagonal h-16 sm:h-[72px] row-span-2 sm:row-span-1"></a>
)}
```

Kept optional (falls back to the existing placeholder) rather than required,
since not every `articoli` record is guaranteed to have `immagine` set.

### `src/pages/index.astro`

```astro
---
import Layout from "../layouts/Layout.astro";
import SageBand from "../components/SageBand.astro";
import SectionHeader from "../components/SectionHeader.astro";
import PageHeader from "../components/PageHeader.astro";
import ArticleListItem from "../components/ArticleListItem.astro";
import RouteListItem from "../components/RouteListItem.astro";
import { CONTACT_EMAIL } from "../lib/site";
import { getHomeArticoli, getHomeItinerari, getCounts, assetUrl } from "../lib/directus";
import { formatTimeLabel, getTypeLabel } from "../lib/format";

const [articoli, itinerari, counts] = await Promise.all([
  getHomeArticoli(),
  getHomeItinerari(),
  getCounts(),
]);
---

<Layout title="Scaio della Montagna">
  <SageBand>
    <SectionHeader label="IL SITO" tone="onSage" />
    <PageHeader title="Scaio della Montagna">
      <p class="text-inchiostro/82">…</p>
      <p class="font-mono-data text-sm text-inchiostro/82 mt-5">
        itinerari · {counts.itinerari} &nbsp; articoli · {counts.articoli}<br />
        zona · orobie &nbsp; contatti · <a href={`mailto:${CONTACT_EMAIL}`} class="hover:text-terra">email</a>
      </p>
    </PageHeader>
  </SageBand>

  <section class="px-4 py-8 sm:px-8 md:px-14">
    <SectionHeader label="ULTIMI ARTICOLI" action={{ label: "Tutti gli articoli →", href: "/articoli" }} />
    <div class="divide-y divide-inchiostro/14">
      {articoli.map((a) => (
        <ArticleListItem
          title={a.titolo}
          href={`/articoli/${a.slug}`}
          author={a.autore.nome}
          imageUrl={a.immagine ? assetUrl(a.immagine, { width: 192, quality: 80 }) : undefined}
        />
      ))}
    </div>
  </section>

  <section class="px-4 pb-8 sm:px-8 md:px-14">
    <SectionHeader label="ULTIMI ITINERARI" action={{ label: "Tutti gli itinerari →", href: "/itinerari" }} />
    <div class="divide-y divide-inchiostro/14">
      {itinerari.map((r) => (
        <RouteListItem
          title={r.titolo}
          href={`/itinerari/${r.slug}`}
          difficulty={r.difficolta}
          distanceKm={Number(r.distanza_km)}
          elevationGainM={r.dislivello_positivo}
          timeLabel={formatTimeLabel(r.tempo_medio_ore)}
          typeLabel={getTypeLabel(r)}
        />
      ))}
    </div>
  </section>
</Layout>
```

`/articoli`, `/itinerari`, and the two detail routes remain 404s — expected,
unbuilt until Steps 6/7/9. Not a regression introduced by this step.

## Corrections carried back into `FRONTEND_BUILD_PLAN.md`

Applied directly to that file as part of this step, since they were checked
against the live instance while doing this step's own schema verification:

- The Directus schema section's `galleria_immagini` and `itinerari_correlati`
  **field** names are wrong — see "Schema facts" above for the real field and
  junction names.
- The `itinerari_correlati` permissions gap is confirmed and is broader than
  the build plan suggested: the API Reader policy currently has **zero**
  permission rows on either junction collection (`itinerari_galleria` and
  `itinerari_correlati`), not just missing rows on one. Both need read
  permissions added before Step 9 can fetch either.
- Map rendering (build order item 7 / Step 9): decided **static image**
  (track + start/end markers rendered to a plain `<img>` at build time, no
  client-side map JS) — recorded as locked in, no longer open.

## What "done" looks like

- `astro/astro.config.mjs` has `envDir: "../"`.
- `src/lib/types.ts`, `src/lib/directus.ts`, `src/lib/format.ts` exist.
- `ArticleListItem.astro` has the optional `imageUrl` prop.
- `src/pages/index.astro` fetches from Directus instead of hardcoding —  no
  literal titles/slugs/numbers left in the file.
- `astro dev` renders Home matching Step 4's output exactly: same two
  article titles/authors, same two route titles/stats/labels, same counts
  (2/2), article thumbnails now real images instead of placeholders.
- `npm run build` succeeds against the live local Directus instance.

## Open questions

None — schema shape, env wiring, and formatting logic above were all
verified directly against the running local instance and existing decisions
(`PROJECT_SPEC.md`'s type-label cases, the build plan's asset-URL decision)
rather than assumed.
