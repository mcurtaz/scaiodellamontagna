# Scaio della Montagna — Project Specification

Personal side project: a hiking blog/site. Content managed in Directus, frontend built with Astro, rendered as static as possible. This document is the reference for scope and content-model decisions; revisit and update it as decisions change.

Status: v1 draft — 2026-09-06.

## Language

Italian only. No i18n/translation fields needed in Directus, no Astro i18n routing.

## Site sections

1. **About** — brief static page describing the site.
2. **Autori** (Authors) — list of authors. Data model exists now; the page/listing stays hidden (unpublished/unlinked) until we decide to expose it.
3. **Articoli** (Articles/Guides) — short educational articles about hiking (e.g. what to pack, how to plan a hike, difficulty ratings explained, winter hiking basics).
4. **Itinerari** (Routes) — a searchable collection of hiking routes.

## Content model

### Autore (Author)
- Fields: TBD in detail during Directus schema design (name, bio, etc.) — not urgent since hidden for now.
- One author can be linked to many Articoli and many Itinerari.

### Articolo (Article/Guide)
- Immagine (image)
- Testo (markdown/rich text body)
- Autore (single author, required)
- No categories/tags for v1 — flat list is enough.

### Itinerario (Route)
- Dislivello positivo (elevation gain, D+)
- Dislivello negativo (elevation loss, D-)
- Tempo medio (average time, hours) — single figure, not a range
- Distanza totale (total distance, km)
- Difficoltà — full CAI (Club Alpino Italiano) scale:
  - **T** – Turistico (Touristic): easy, well-marked paths/tracks, suitable for most people.
  - **E** – Escursionistico (Hiking): mountain trails, uneven terrain, requires some experience and basic fitness.
  - **EE** – Escursionisti Esperti (Expert hikers): exposed terrain, steep/unmarked sections, requires experience, sure-footedness, no vertigo.
  - **EEA** – Escursionisti Esperti con Attrezzatura (Expert hikers, equipped): via ferrata / equipped trails requiring harness, helmet, lanyard.
  - **OFA** – Occorrono Fune e/o Attrezzatura Alpinistica (Alpine equipment required): glacier/alpinistic terrain, rope and mountaineering gear.
- È adatto ai bambini (is_child_friendly, boolean)
- È adatto in inverno (is_winter_friendly, boolean)
- È ad anello (is_loop, boolean) — true only when the return path differs from the outbound path (a true loop shape). An out-and-back hike that retraces the same trail is **not** a loop, even though it returns to the starting point: `is_loop = false` in that case too. Three real cases: (1) *anello* — start = end, outbound ≠ return path → `is_loop = true`; (2) *andata e ritorno* — start = end, same path both ways → `is_loop = false`; (3) *traversata* (point-to-point) — start ≠ end → `is_loop = false`.
- Punto di partenza (start point coordinates)
- Punto di arrivo (end point coordinates) — coincides with the start point for cases (1) and (2) above; differs only for a point-to-point traversata
- Traccia GPS: **GPX format only** (open standard for tracks; supported by all hiking apps/devices — Wikiloc, Komoot, AllTrails, Garmin, OsmAnd, Strava — no need for KML/TCX)
- Descrizione (markdown/rich text)
- Galleria immagini (ordered list of images, each with a caption)
- Itinerari correlati (related routes) — **manual selection for v1**, not auto-computed. Modeled as a typed relation (see "Modeling philosophy" below), not a plain M2M. Revisit auto-suggestion (by proximity/difficulty) later if useful.
- Link to related Articoli — **not needed now**, add later if useful.
- Autore (single author, required)

### Modeling philosophy: an Itinerario is a real recorded outing, not a composable segment

Early design question: should routes be split into atomic point-to-point "tratte" (segments) that get automatically composed into full trips (e.g. summing elevation/time, reversing a segment for the return leg)? **Decision: no.** That's route-planning-engine complexity (merging GPX tracks, inverting D+/D- on reversal, summing times) for a personal blog with a few dozen routes a year — not worth it.

Instead:
- **Every Itinerario record corresponds to a GPX track actually recorded during a real outing.** Nothing is derived or computed from other records.
- Example: "Gita al Rifugio Curò" (parcheggio → rifugio → parcheggio, a loop/out-and-back with its own full GPX, D+/D-, and total time) is one Itinerario. If a later outing continues from the rifugio to Lago Gelt, that continuation is recorded as a **separate, independent Itinerario** ("Rifugio Curò → Lago Gelt", point-to-point, `is_loop = false`, its own GPX/D+/D-/time for just that stretch).
- These are linked via **itinerari correlati**, qualified with a relation type (e.g. `prosecuzione` / `variante` / `nella zona`) so the frontend can distinguish "puoi proseguire fino a..." from "itinerari nella stessa zona". In Directus this needs a junction collection with an extra `tipo` field (M2M with metadata), not a plain M2M relation.
- Extending a chain further (lago → passo → ...) costs one new independent record + one new link each time — no cumulative recalculation, no combinatorial complexity.

### Map rendering (decide later, two options on the table)
- **Static-first (preferred direction for v1)**: render a map image (track + start/end markers) at build time and ship it as a plain `<img>` — keeps the route page fully static, no client-side map JS.
- **Interactive**: client-side Leaflet + OpenStreetMap tiles, loading the GPX live. More flexible (zoom/pan) but adds JS and a runtime dependency on tile servers.

## Search

Expected volume: tens of routes per year (low total volume). Decision: **fully client-side search**.
- At build time, export all Itinerari data into a static JSON index.
- Filter entirely in the browser: numeric range filters (distanza, dislivello, tempo), boolean filters (bambini, inverno), and "near me" via a Haversine distance calculation against a user-supplied GPS point — all trivial in plain JS at this data scale.
- No Directus API calls needed at request time for search; Directus is only a build-time data source.
- If full-text search over Articoli is wanted later, consider a client-side index tool (e.g. Pagefind) rather than a server-side search API — keeps the "static as possible" goal intact.

## Users & permissions (Directus)

Multiple contributors, one administrator (the site owner).

- **v1 (start simple)**: two roles.
  - **Administrator**: full access — schema, settings, users, all content.
  - **Contributor**: CRUD access to Articoli and Itinerari collections only; no access to schema, settings, or user management. Any contributor can create/edit any article or route.
- **Upgrade path (not built yet, easy to add later)**: restrict Contributors to editing only content they created, using a Directus permission rule such as `user_created equals $CURRENT_USER` on the update permission for Articoli/Itinerari. This is a permissions config change, not a schema/rebuild change, so it can be introduced later without disruption.

## Deployment & rebuild pipeline

Goal: automated deploy triggered by content changes.
- **Preferred**: Directus webhook fires on publish/update → triggers an Astro rebuild + redeploy.
- **Fallback (simpler, keeps project easy to reason about)**: manual rebuild trigger.
- Decide the exact webhook target (CI job, build server, etc.) once hosting is set up.

## Infrastructure (future discussion, notes only — not decided)

- Direction: containers on a single EC2 instance (Directus + Postgres via docker-compose, as already started locally) rather than a separate managed RDS instance — avoids the cost/complexity of a second managed service for a personal project.
- Also planned: Route53, S3, CloudFront for static asset hosting/CDN in front of the Astro output.
- **Backups are a hard requirement, schedule/retention TBD**: both the Postgres database (e.g. scheduled `pg_dump` to S3) and uploaded files (Directus uploads folder / S3 storage) need a backup strategy before going to production.
- Full production architecture to be revisited in a dedicated discussion.

## Analytics (future discussion, not decided)

- Candidate: Umami. Deferred until the rest of the site is in place.

## Open items / explicitly deferred

- Autori page: unhide and design listing (later).
- Auto-suggested related routes (later, if manual curation proves limiting).
- Articolo ↔ Itinerario cross-linking (later, if useful).
- Interactive vs static map rendering: final call pending.
- Backup schedule/retention specifics.
- Production infra details (EC2 sizing, CloudFront config, DNS, TLS).
- Umami setup and metrics of interest.
