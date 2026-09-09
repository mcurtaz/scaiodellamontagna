# Map & Elevation Profile — Plan B: No static images, interactive map + chart

Status: **candidate plan, not decided** — see `MAP_PROFILE_PLAN_A_STATIC.md` for the
alternative. `PROJECT_SPEC.md`'s "Map rendering" / "Elevation profile" sections link here;
a decision between A and B must be made before implementation starts.

## Summary

Generate no images at all. The itinerario **list** thumbnail reuses an existing gallery
image instead of a rendered map. The detail page's track section ships an interactive
MapTiler map and a Chart.js elevation-profile chart, both driven by a small JSON file of
track points computed at Astro build time from the GPX — with hovering the chart moving a
marker on the map, and vice versa. This reverses `PROJECT_SPEC.md`'s original "static
image, not interactive" decision for the map, in exchange for zero new backend
infrastructure and a materially better track-exploration UX.

## Attribution requirement (handled automatically here)

Using MapTiler's map data/styles requires visibly crediting them (their ToS's attribution
clause) — this is the same category of legal requirement as OpenStreetMap's own attribution
condition in Plan A, just for a different provider. Unlike Plan A's static image, though,
this is essentially a non-issue here: MapLibre GL JS/the MapTiler SDK render a small
attribution control in the map's corner automatically, on by default. No implementation
work needed — just don't remove or hide that control.

## Comparison with Plan A

| Dimension | Plan A (static) | Plan B (this plan) |
|---|---|---|
| Code complexity | New Python service + Directus Flow + schema + token — backend/ops complexity, front-loaded, then invisible | No new backend; real frontend complexity (build-time parsing, interactive island, two-way hover glue) that must keep working correctly indefinitely |
| Site appeal | Consistent but plain; no pan/zoom or per-point elevation readout | Nicer map styles, pan/zoom, linked hover — but the hover payoff is desktop-only until touch is designed in |
| Site performance | No extra runtime JS; cacheable images; best for slow connections/older phones | MapLibre GL JS + a chart library + extra network round-trips, landing on the detail page specifically |
| Build time/complexity | `astro build` unaffected — generation fully decoupled from the build | Adds a GPX fetch+parse per route on every build, plus a new build-time failure mode (a malformed GPX can fail the whole build) |
| GDPR / third-party requests | None — all assets served from your own infrastructure | Visitor's browser talks directly to MapTiler on every page view — a consent/privacy consideration for an EU audience |
| Editorial control | Editor can see and manually override a bad render in Directus | No per-route override without a code change |
| Social sharing (OG image) | `mappa_statica` doubles as a ready-made link-preview image | No natural OG image; needs a separate solution (e.g. fall back to a gallery photo) |
| Accessibility | Plain `<img alt="...">`, screen-reader compatible | WebGL/canvas content is invisible to screen readers by default; needs extra work (hidden data table, ARIA) to not regress |
| Offline / printable | Trivially save-able/printable — useful for low-signal mountain use | A WebGL map isn't reliably printable and needs connectivity to load at all |
| Attribution | Must be composited into the static image itself (no live UI to attach a control to) | Just a small on-page MapTiler control — simpler to satisfy |
| Future optionality | Doesn't block future map features, but shares no code with them | Lays groundwork reusable for a future "all routes on one map" view (ties to the spec's planned "near me" search) |
| Elevation data noise | Shared concern, not yet designed in either plan — see below | Same |

## Architecture

```
Astro build (per Itinerario with a traccia_gpx), e.g. in getStaticPaths:
  1. Fetch the raw GPX from Directus (assetUrl(traccia_gpx))
  2. Parse it (src/lib/gpx.ts) → [{lat, lon, ele, dist}, ...]
     (dist = cumulative distance via Haversine between consecutive points;
      dense tracks decimated to keep payload small)
  3. Emit as a prerendered static JSON file via
     src/pages/itinerari/[slug]/track.json.ts
     → physically lands in dist/itinerari/<slug>/track.json, served as a
       plain static asset, no server involved at runtime

Detail page (client-side, in the visitor's browser):
  TrackExplorer island (client:visible)
    fetch('./track.json')
      → MapLibre GL JS / MapTiler SDK: fit bounds, draw the track as a
        GeoJSON line, start/end markers + one movable cursor marker
      → Chart.js: distance (x) vs elevation (y) line chart, plotted from
        a smoothed/filtered elevation series (raw GPS/barometric elevation
        is often jittery; unsmoothed data looks jagged and can visually
        overstate small climbs)
      → two-way hover:
          chart hover  → nearest point index → move map cursor marker
          map mousemove → nearest point (linear scan over the array)
                        → move chart's active tooltip/crosshair to that index
          on touch devices, hover doesn't exist — needs a tap-and-drag or
          tap-to-select equivalent, otherwise the linked-hover feature is
          invisible on mobile
```

This computation is pure, fast, local math over the GPX's XML (no external API, no cost),
so — unlike the map/elevation *images* in Plan A — it's fine to just recompute it on every
Astro build. No "only regenerate when the GPX changes" caching problem to solve.

## List thumbnail

Use the first (or a designated "cover") image from `galleria` instead of any generated map
— same image-handling pattern already used elsewhere (e.g. `ArticleListItem`). No map
rendering of any kind happens for the list.

## New dependencies

- `maplibre-gl` (or `@maptiler/sdk`, MapTiler's thin wrapper with simpler style URLs).
- `chart.js`.
- A GPX-parsing utility for the Node build step — either a small library (e.g.
  `gpxparser`, `@we-gold/gpxjs`) or hand-rolled parsing, since only `trkpt` lat/lon/ele is
  needed.
- No UI framework is strictly required: `TrackExplorer` can be a vanilla-JS `<script>`
  inside an `.astro` component (`client:visible`), keeping the project's current
  zero-framework dependency footprint. If a component-based approach is preferred instead,
  this would be the first thing to add `@astrojs/react` (or Preact) for — worth deciding
  explicitly rather than defaulting into it.

## Directus schema

None. No new fields — `traccia_gpx` (already existing) is the only dependency.

## Env / config changes

- `MAPTILER_KEY` in `.env.example` needs to become a `PUBLIC_`-prefixed var (e.g.
  `PUBLIC_MAPTILER_KEY`), since Astro only exposes `PUBLIC_`-prefixed env vars to
  client-side bundles, and the map runs in the browser here.
- Restrict that key to the site's domain in the MapTiler dashboard (standard practice for a
  publicly-shipped browser key, same as a Google Maps browser key).

## Implementation steps

1. Rename `MAPTILER_KEY` → `PUBLIC_MAPTILER_KEY` in `.env.example`; restrict it by domain
   in MapTiler's dashboard.
2. Write `src/lib/gpx.ts`: `parseTrack(gpxText) → {lat, lon, ele, dist}[]`, with a
   decimation step for dense tracks.
3. In the detail page's `getStaticPaths` (or a shared build-time helper), fetch + parse each
   itinerario's GPX once (cache by file id if it's needed in more than one place, to avoid
   downloading/parsing the same file twice).
4. Add `src/pages/itinerari/[slug]/track.json.ts`, returning the parsed points, prerendered.
5. Build the `TrackExplorer` island: map init + GeoJSON line + markers, chart init, and the
   two-way hover wiring; a loading state while `track.json` fetches.
6. Replace `MapThumbnail.astro` usage on the detail page with `TrackExplorer`.
7. Update the itinerari list item component to show a `galleria` image instead of a map
   thumbnail.
8. Decide the decimation approach/threshold for dense GPX tracks (start with a naive "cap to
   ~500 points"; revisit a proper simplification algorithm like Douglas-Peucker only if
   visual quality suffers).
9. Smooth/filter the raw elevation series before charting (e.g. a simple moving average) so
   GPS/barometric noise doesn't make the chart look jagged or overstate small climbs.
10. Design a touch/tap equivalent for the linked hover interaction, or the feature is
    effectively invisible to mobile visitors.
11. Add an accessible fallback for the map/chart (e.g. a visually-hidden data table of
    distance/elevation), since WebGL/canvas content isn't screen-reader visible by default.
12. Decide an Open Graph / social-preview image strategy for route pages (e.g. fall back to
    the first `galleria` image), since this plan produces no map/elevation image to reuse.

## Pros

- Zero new backend infrastructure: no Python service, no Directus Flow, no automation
  credential to create/manage, no new Directus schema.
- Materially better UX: pan/zoom on the map, plus the linked map↔chart hover interaction
  that a static image fundamentally cannot offer.
- Track JSON generation is cheap, pure, build-time computation — no invalidation/caching
  problem, since it costs nothing to just redo it every build.
- Lays groundwork reusable for a future "all routes on one map" overview page — the spec
  already plans a client-side "near me" search feature that a live map would pair well with.

## Cons / costs

- Reverses the spec's original "static as possible" map decision — ships real client-side
  JS on every itinerario detail page (MapLibre GL JS + Chart.js).
- Creates a real dependency on MapTiler's account/free-tier terms: 100,000 requests/mo,
  5,000 sessions/mo, **non-commercial-only** clause, attribution requirement — free at this
  project's scale, but a live external dependency and ToS to keep an eye on (unlike Plan A,
  which has none).
- No offline/no-JS fallback: if MapTiler is unreachable or the visitor has JS disabled, the
  entire track section shows nothing, versus Plan A's `<img>` which degrades gracefully.
- If a UI framework gets added for `TrackExplorer` instead of vanilla JS, that's a new
  category of dependency for a project that's currently plain Astro throughout.
- MapTiler tiles/style/fonts load directly from MapTiler's servers in the visitor's
  browser on every page view — a third-party data-processing relationship, and a
  consent/privacy consideration for an EU (Italian) audience that Plan A doesn't have.
- WebGL/canvas content (the map and the chart) is invisible to screen readers by default;
  needs a hidden data table and/or ARIA live region to not regress accessibility.
- No natural social-sharing (Open Graph) image — a route link shared on WhatsApp/Instagram
  needs a separate image strategy (e.g. falling back to a gallery photo).
- No per-route manual override: if a specific route's auto-framed map or noisy elevation
  chart looks bad, fixing it means a code/algorithm change affecting every route, not a
  one-off edit in Directus.
- Not naturally offline/printable — a WebGL map generally can't be saved or printed
  reliably, and needs connectivity to load at all, unlike a plain image.

## Open questions

- Vanilla-JS island vs. adding a UI framework for `TrackExplorer` — leaning vanilla, to
  keep the project's current zero-framework footprint, not decided.
- Decimation threshold/algorithm for dense tracks.
- Whether a static `<img>` fallback is worth keeping for no-JS visitors, given it adds back
  some of the complexity this plan is trying to avoid.
- Touch/tap interaction design for the linked hover on mobile — not yet designed.
- How much accessibility work (data table, ARIA) is worth doing for v1 vs. deferring.
- Open Graph image source for route pages, since there's no generated map/elevation image
  to fall back on.
