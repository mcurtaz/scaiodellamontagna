# Step 4 — Home page, hardcoded content

Part of `FRONTEND_BUILD_PLAN.md`. First full page assembled from Steps 1–3's
pieces, with the two sample articles/routes typed directly into the page
(copied from the mockup's placeholder content). **No Directus involved yet** —
that's Step 5, once this page's composition and styling are validated.

Replaces the current placeholder `src/pages/index.astro`.

## New components built in this step

Home needs two more composite pieces that don't exist yet. Both are built
**compact-variant only** here — the "full" listing variant (used later by the
Articoli/Itinerari listing pages) is a Step 6/7 decision, not designed yet.
Avoid adding a `variant` prop pre-emptively; add it when the second variant
is actually built.

### `ArticleListItem.astro` (compact)

```ts
interface Props {
  title: string;
  href: string;
  author: string;
}
```

Layout: mobile-first — a two-column row (`grid grid-cols-[64px_1fr] gap-4
items-center`) with a small `media-placeholder media-placeholder-diagonal`
square and the title next to it; author name moves below the title on
mobile. At `sm:`/`md:` and up, switch to the mockup's three-column layout
(thumbnail | title | author, author right-aligned) — e.g.
`sm:grid-cols-[96px_1fr_150px]`.

### `RouteListItem.astro` (compact)

```ts
interface Props {
  title: string;
  href: string;
  difficulty: "T" | "E" | "EE" | "EEA" | "OFA";
  distanceKm: number;
  elevationGainM: number;
  timeLabel: string;   // e.g. "3 h 30"
  typeLabel: string;   // e.g. "andata e ritorno" / "traversata"
}
```

Same mobile-first two-column-then-three-column approach as
`ArticleListItem`, using a `media-placeholder-grid` thumbnail, title next to
a `DifficultyBadge`, and a mono stats line (`{distanceKm} km · {elevationGainM} m D+`
/ `{timeLabel} · {typeLabel}`).

## Assembling `src/pages/index.astro`

```astro
<Layout title="Scaio della Montagna">
  <SageBand>
    <SectionHeader label="IL SITO" tone="onSage" />
    <PageHeader title="Un archivio personale di uscite in montagna, camminate e misurate sul posto.">
      <p>Ogni itinerario nasce da una traccia GPX registrata durante l'uscita. Gli articoli sono appunti sparsi: attrezzatura, letture della difficoltà, cose imparate sbagliando.</p>
      <p class="font-mono-data text-sm mt-4">
        itinerari · 2 &nbsp; articoli · 2<br>
        zona · orobie &nbsp; contatti · <a href={`mailto:${CONTACT_EMAIL}`}>email</a>
      </p>
    </PageHeader>
  </SageBand>

  <section>
    <SectionHeader label="ULTIMI ARTICOLI" action={{ label: "Tutti gli articoli →", href: "/articoli" }} />
    <ArticleListItem title="Cosa mettere nello zaino per un'escursione di giornata" href="/articoli/cosa-mettere-nello-zaino" author="michele curtaz" />
    <ArticleListItem title="Come leggere la scala di difficoltà CAI" href="/articoli/scala-difficolta-cai" author="sara bonetti" />
  </section>

  <section>
    <SectionHeader label="ULTIMI ITINERARI" action={{ label: "Tutti gli itinerari →", href: "/itinerari" }} />
    <RouteListItem title="Gita al Rifugio Curò" href="/itinerari/gita-al-rifugio-curo" difficulty="E" distanceKm={9.2} elevationGainM={850} timeLabel="3 h 30" typeLabel="andata e ritorno" />
    <RouteListItem title="Da Rifugio Curò a Lago Gelt" href="/itinerari/rifugio-curo-lago-gelt" difficulty="E" distanceKm={2.4} elevationGainM={180} timeLabel="1 h" typeLabel="traversata" />
  </section>
</Layout>
```

Notes:
- Titles/slugs above come from the **real Directus data** already in the
  local instance (checked directly against the API), not the mockup's
  slightly different wording — e.g. the mockup says "Rifugio Curò → Lago
  Gelt" but the actual `itinerari` record's `titolo` is "Da Rifugio Curò a
  Lago Gelt", slug `rifugio-curo-lago-gelt". Hardcoding it now means Step 5
  (wiring to Directus) should produce visually identical output, which is
  the point of the exercise — a good end-to-end check that the fetch layer
  is right.
- "itinerari · 2" / "articoli · 2" counts are hardcoded here; Step 5 replaces
  them with real counts from the fetched data.
- No image URLs yet — thumbnails stay as placeholders until Step 5+ adds
  `<img>` tags built from `${DIRECTUS_URL}/assets/{id}?width=...`.

## What "done" looks like

- `src/components/ArticleListItem.astro`, `RouteListItem.astro` exist.
- `src/pages/index.astro` renders the full Home page using `Layout`,
  `SageBand`, `SectionHeader`, `PageHeader`, `ArticleListItem`,
  `RouteListItem` — no raw HTML/CSS copy-pasted from the mockup.
- Checked in `astro dev` from mobile width up: nav, hero, both list sections,
  and footer all read cleanly with no overlap/clipping, and content matches
  the real Directus records' titles/slugs (not the mockup's placeholder
  text).
- `npm run build` succeeds.

## Open questions

None for this step — all content/behavior above follows directly from
decisions already made in Steps 1–3 and the real Directus data inspected
earlier.
