# Map & Elevation Profile — Plan A: Static images via a Python generator container

Status: **candidate plan, not decided** — see `MAP_PROFILE_PLAN_B_INTERACTIVE.md` for the
alternative. `PROJECT_SPEC.md`'s "Map rendering" / "Elevation profile" sections link here;
a decision between A and B must be made before implementation starts.

## Summary

Generate two PNGs per Itinerario — a static map (track + start/end markers) and a static
elevation-profile chart — once, whenever `traccia_gpx` is uploaded/changed, via a small
self-hosted Python service triggered by a Directus Flow. Store the results as new Directus
file fields. The Astro frontend never renders a map or chart itself: both images are plain
`<img>` tags, fetched like any other Directus asset. This matches `PROJECT_SPEC.md`'s
original "static as possible" decision and its "leading candidate" generation mechanism.

## Comparison with Plan B

| Dimension | Plan A (this plan) | Plan B (interactive) |
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
Editor uploads/changes traccia_gpx on an Itinerario
        │
        ▼
Directus Flow (trigger: items.create/items.update on `itinerari`)
        │  Condition: $trigger.payload.traccia_gpx is present
        ▼
Webhook operation → POST http://map-generator:8000/generate
                     body: { item_id }
        │
        ▼
map-generator (Python container, internal docker network only)
  1. GET the GPX from Directus (/assets/{traccia_gpx})
  2. Parse with gpxpy → [{lat, lon, ele}, ...]
  3. Compute cumulative distance (Haversine) for the elevation profile
  4. Render map PNG: staticmap (Komoot) or py-staticmaps, OSM tiles,
     bounding box fit to track + padding, polyline + start/end markers,
     with OSM copyright attribution composited onto the image itself
     (required by OSM's tile usage policy — there's no live UI to attach
     a control to, unlike an interactive map)
  5. Render elevation PNG: matplotlib, distance (x) vs elevation (y),
     smoothing/filtering the raw elevation series first (GPS/barometric
     elevation is often jittery; an unsmoothed chart looks jagged and can
     visually overstate small climbs)
  6. Delete the item's previous mappa_statica/profilo_altimetrico files (if any)
  7. POST new files to Directus /files, then PATCH /items/itinerari/{id}
     to link mappa_statica + profilo_altimetrico
        │
        ▼
Astro build fetches itinerari including the two new file fields,
renders plain <img> via the existing assetUrl() helper — no new
frontend rendering logic, no client-side JS for maps/charts.
```

The itinerario **list** thumbnail reuses the same `mappa_statica` asset at a smaller
width via Directus's existing on-the-fly resize (`?width=...`), so only one map image is
ever generated per route.

## New Directus schema

- `itinerari.mappa_statica` — file (M2O to `directus_files`), nullable.
- `itinerari.profilo_altimetrico` — file (M2O to `directus_files`), nullable.

## New infrastructure

- New docker-compose service, e.g. `map-generator`:
  - Python (FastAPI + uvicorn, or bare `http.server` — FastAPI recommended for minimal
    boilerplate), no port exposed externally (internal docker network only).
  - Dependencies: `gpxpy`, `staticmap` (or `py-staticmaps`), `matplotlib`, `Pillow`,
    `requests`.
  - Env: `DIRECTUS_URL`, `DIRECTUS_TOKEN` (a **dedicated, scoped Directus role/token** —
    read on `itinerari`/`directus_files`, update on `itinerari`, create/update/delete on
    `directus_files`. Do **not** reuse the frontend's read-only public token.)
- A Directus Flow (configured in the admin UI, documented in `DIRECTUS_SETUP.md` once built):
  - Trigger: Event Hook, `items.create` + `items.update` on `itinerari`.
  - Condition: `$trigger.payload.traccia_gpx` is set (Directus's `items.update` trigger
    payload only includes changed fields, so this reliably detects "GPX was touched").
  - Operation: Webhook (POST) to the generator's internal URL.
  - Optional: a failure-notification operation (e.g. log or email) so a broken flow
    doesn't fail silently.

## Frontend changes (Astro)

- `src/lib/directus.ts`: add `mappa_statica`, `profilo_altimetrico` to the field lists in
  `getItinerariDetail()` and the listing query.
- `MapThumbnail.astro`: drop the "always placeholder" state — render the real `<img>` once
  `mappa_statica` exists; keep the placeholder branch only for the case
  `traccia_gpx` exists but the Flow hasn't produced an image yet (or there's no GPX at all).
- New `ElevationProfile.astro` (same shape as `MapThumbnail.astro`) for
  `profilo_altimetrico`, placed on the detail page's track section alongside the map.
- Itinerari list item component: use `mappa_statica` at a small width as the route thumbnail.

## Implementation steps

1. Add the two file fields to the `itinerari` collection in Directus.
2. Create the `map-generator` service (Dockerfile, `requirements.txt`, app code implementing
   the flow described above).
3. Add the service to `docker-compose.yml`; add its Directus token to `.env.example`.
4. Create the dedicated Directus automation role/token for the service.
5. Configure the Directus Flow (trigger, condition, webhook); document it in
   `DIRECTUS_SETUP.md`.
6. Update `lib/directus.ts` queries, `MapThumbnail.astro`, add `ElevationProfile.astro`,
   wire both into the detail page and the list item component.

No backfill step needed — the site isn't live yet, so there's no existing content with a
`traccia_gpx` predating the Flow. (If content does get added to Directus before this ships,
re-saving each such record once would trigger the Flow retroactively.)

## Pros

- No client-side map/chart JS shipped to visitors at all — smallest possible page weight,
  fully consistent with "static as possible."
- No third-party map API account, cost, or ToS exposure: OSM tiles are free at this
  project's volume (tens of renders/year), with attribution.
- Reuses the storage/asset-cache/CDN pipeline already planned for every other image in the
  project — one Directus file field, resized via query params for both the list thumbnail
  and the detail page.
- Regeneration is automatic and tied to content changes, not to Astro rebuilds.
- Degrades gracefully: a plain `<img>` still works with JS disabled or a slow connection.
- No third-party runtime requests — nothing about this feature triggers a GDPR/consent
  consideration, unlike loading a live map from an external provider.
- `mappa_statica` doubles as a ready-made social-sharing (Open Graph) image for the route.
- An editor can see the generated image in Directus and manually replace it if a specific
  route renders badly (bad auto-zoom, self-crossing line, noisy elevation) — no code change
  needed for a one-off fix.
- Naturally offline-friendly: a plain image can be saved or printed before heading out with
  no signal, unlike an interactive map that needs connectivity to load at all.

## Cons / costs

- Real new infrastructure: a Python service to write, containerize, deploy, and monitor
  alongside Postgres/Directus in docker-compose — one more thing that can silently break.
- Needs a scoped Directus automation credential to create and manage.
- No pan/zoom or hover interactivity — inherent to a static image, not a bug, but a real
  UX ceiling compared to Plan B.
- A Flow failure (bad GPX, Directus write error) leaves a stale/placeholder image with no
  obvious signal unless failure notifications are wired up.

## Open questions

- FastAPI vs. something even smaller for the generator — leaning FastAPI, not decided.
- Any visual/branding requirements for the map or chart styling (colors, markers), or is a
  sensible default fine for v1?
- Retry/error-handling story for a corrupt GPX or a transient Directus write failure.
