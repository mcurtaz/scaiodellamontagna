# Directus Setup — Collections & Fields

Step-by-step instructions to build the Directus data model described in [`PROJECT_SPEC.md`](./PROJECT_SPEC.md). Follow this once against a fresh local instance (`docker compose up -d`, then open `http://localhost:8055`, log in with `DIRECTUS_ADMIN_EMAIL` / `DIRECTUS_ADMIN_PASSWORD` from `.env`).

The `punto_partenza` / `punto_arrivo` Geometry fields in `itinerari` (section 3) need the PostGIS extension — plain Postgres has no `geometry` type. `docker-compose.yml` uses `postgis/postgis:16-3.4` for this reason. On a fresh volume the image bootstraps the extension itself; if you're migrating an existing database, enable it once with `docker compose exec postgres psql -U directus -d directus -c "CREATE EXTENSION IF NOT EXISTS postgis;"`.

Do these in order: **Autori → Articoli → Itinerari → Itinerari correlati (junction) → Galleria immagini (junction)**. Later collections reference earlier ones.

Field "key" names below are the machine names to type in Directus — use them exactly so later docs (permissions, mock data) line up. The "Note" is optional but recommended for future-you.

---

## 1. Collection: `autori`

Settings → Data Model → **Create Collection**.

- Name: `autori`
- Primary key: **Auto-increment integer** (default) — fine, not exposed publicly in URLs.
- Leave "Optional Fields" (archived, sort, date_created, ...) **unchecked** — this collection doesn't need them yet.

Add fields (Data Model → `autori` → **Create Field**):

| Key | Type | Interface | Required | Notes |
|---|---|---|---|---|
| `nome` | String | Input | ✅ | Full name of the author |
| `bio` | Text | Textarea | — | Short bio, plain text is enough for v1 |
| `foto` | File (single image) | Image | — | Optional headshot |

Save. Autori section stays unlinked from navigation/frontend per spec (hidden for now) — this is just a Directus content collection, no extra config needed for "hiding" it since there's no public listing yet.

---

## 2. Collection: `articoli`

**Create Collection** → name `articoli`.

- Primary key: Auto-increment integer.
- Optional system fields: check **Archived** — this Directus version doesn't offer a draft/published/archived Status field, just a boolean `archived` field auto-added to the collection.

Fields:

| Key | Type | Interface | Required | Notes |
|---|---|---|---|---|
| `titolo` | String | Input | ✅ | Article title |
| `slug` | String | Input | ✅ | Unique, lowercase-hyphenated. There's no separate "Slug" interface — use **Input** and enable its **Slug** option (in the interface's field options) so Directus auto-formats it and offers a "populate from `titolo`" button. Add a **Unique** validation. |
| `immagine` | File (single image) | Image | ✅ | Cover image |
| `testo` | Text | **Markdown** | ✅ | Body content, stored as raw Markdown (keeps Astro rendering simple — no HTML sanitization needed) |
| `autore` | Many to One → `autori` | Dropdown (M2O) | ✅ | Single author per article |

Order the fields in this table order in the Directus form for a natural editing flow (drag to reorder in the Data Model screen).

---

## 3. Collection: `itinerari`

**Create Collection** → name `itinerari`.

- Primary key: Auto-increment integer.
- Optional system fields: check **Archived** (same boolean pattern as `articoli` — no draft/published Status field in this Directus version).

Fields — create in this order:

| Key | Type | Interface | Required | Notes |
|---|---|---|---|---|
| `titolo` | String | Input | ✅ | Route title, e.g. "Gita al Rifugio Curò" |
| `slug` | String | Input | ✅ | Unique, derived from `titolo`. Use **Input** with its **Slug** option enabled — no separate "Slug" interface, see note on `articoli` above. |
| `dislivello_positivo` | Integer | Input | ✅ | Meters, D+ |
| `dislivello_negativo` | Integer | Input | ✅ | Meters, D- |
| `tempo_medio_ore` | Decimal | Input | ✅ | Hours, e.g. `3.5` |
| `distanza_km` | Decimal | Input | ✅ | Km, e.g. `8.2` |
| `difficolta` | String | **Dropdown (Select)** | ✅ | Choices — set exactly these key/value pairs: `T: Turistico`, `E: Escursionistico`, `EE: Escursionisti Esperti`, `EEA: Escursionisti Esperti con Attrezzatura`, `OFA: Occorrono Fune e/o Attrezzatura Alpinistica` |
| `is_child_friendly` | Boolean | Toggle | — | Default `false` |
| `is_winter_friendly` | Boolean | Toggle | — | Default `false` |
| `is_loop` | Boolean | Toggle | — | Default `false`. See `PROJECT_SPEC.md` for exact semantics (true only if return path ≠ outbound path). |
| `punto_partenza` | **Geometry (Point)** | Map | ✅ | Directus native geo field — gives you a map picker in the UI and stores real lat/lon, needed later for "near me" search |
| `punto_arrivo` | **Geometry (Point)** | Map | ✅ | Same as above. Coincides with `punto_partenza` for anello/andata-e-ritorno routes. |
| `traccia_gpx` | File (single) | File | ✅ | Upload the `.gpx` track. Directus doesn't restrict by extension in the UI — just a convention, put a note on the field reminding editors "GPX only". |
| `descrizione` | Text | Markdown | ✅ | Route description |
| `autore` | Many to One → `autori` | Dropdown (M2O) | ✅ | |

Don't add `galleria` or `itinerari_correlati` yet — those need extra collections, done in the next two sections.

---

## 4. Field: `galleria` (ordered image gallery with captions)

This needs a **Many to Many** field pointing at `directus_files`, because we need an extra `didascalia` (caption) field per image — a plain "Files" multi-select doesn't give you that.

1. Go to `itinerari` → **Create Field** → type **Many to Many**.
2. Key: `galleria`.
3. Related collection: pick **Directus Files** (this is the built-in files table — Directus offers this directly in the M2M wizard as a special case, sometimes labeled "Files" instead of a normal M2M).
4. Let Directus auto-create the junction collection — accept the default name (something like `itinerari_files`) or rename it to `itinerari_galleria` for clarity.
5. After the field is created, open the auto-created junction collection (`itinerari_galleria`) in Data Model and add one more field to it:
   - Key: `didascalia`, Type: String, Interface: Input — the per-image caption.
6. Back on `itinerari`, edit the `galleria` field again and switch to its **Relationship** tab (not Interface) — set **Sort Field** to `sort` (the field Directus auto-added to the junction collection). This is what turns on drag-to-reorder in the M2M interface; there's no separate "Enable Sorting" toggle in the interface options. This gives editors manual ordering + a caption per photo, per spec.

---

## 5. Collection: `itinerari_correlati` (typed relation between routes)

This is the "itinerari correlati" relation from `PROJECT_SPEC.md` — a self-referencing many-to-many on `itinerari`, qualified with a `tipo` field. Build it as an explicit junction collection rather than the M2M wizard, it's clearer for a self-relation:

1. **Create Collection** → name `itinerari_correlati`.
   - Primary key: Auto-increment integer.
   - No optional system fields needed.
2. Add field `itinerario_da`: **Many to One** → related collection `itinerari`. Required.
3. Add field `itinerario_a`: **Many to One** → related collection `itinerari`. Required.
4. Add field `tipo`: **String**, interface **Dropdown**, required. Choices: `prosecuzione: Prosecuzione`, `variante: Variante`, `nella_zona: Nella stessa zona`.
5. Go back to `itinerari` → **Create Field** → type **One to Many** → related collection `itinerari_correlati`, foreign key field `itinerario_da`. Key this field e.g. `itinerari_correlati_da_qui` — this is what shows up on a route's edit page as "the list of relations where this route is the starting point."

This is enough for v1 (manual selection, per spec). Editors create a row in `itinerari_correlati` picking the two routes and the relation type; the Astro build later reads this table to render "puoi proseguire fino a..." / "varianti" / "nella zona" sections. (A frontend detail — not needed to decide now — is whether to also show the *inverse* direction, e.g. showing the link on Lago Gelt's page pointing back to Rifugio Curò. That's a query-time decision in Astro, not a schema decision.)

---

## Recap of collections created

- `autori`
- `articoli`
- `itinerari`
- `itinerari_correlati` (junction: `itinerario_da`, `itinerario_a`, `tipo`)
- `itinerari_galleria` (auto-created junction for the `galleria` M2M: file, `didascalia`, `sort`)

Next: [`DIRECTUS_USERS.md`](./DIRECTUS_USERS.md) for roles and permissions, then [`MOCK_DATA.md`](./MOCK_DATA.md) to populate content for the Astro build.
