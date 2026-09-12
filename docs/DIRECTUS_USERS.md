# Directus Setup — Roles, Users & Permissions

Do this **after** [`DIRECTUS_SETUP.md`](./DIRECTUS_SETUP.md) (permissions are set per-collection, so the collections must exist first).

Four roles, per `PROJECT_SPEC.md` plus the map/elevation generator from `MAP_PROFILE_PLAN_A_STATIC.md`:

1. **Administrator** — you. Already exists by default in Directus, full access. Nothing to configure.
2. **Contributor** — other people who write articles/routes.
3. **API Reader** — not a human role. A machine role used by the Astro build to pull published content via a static token, kept separate from the public "Public" role so access can be locked down precisely and rotated independently.
4. **Map Generator** — not a human role. A machine role used by the `map-generator` service to read `traccia_gpx` and write back `mappa_statica`/`profilo_altimetrico`. Kept separate from `API Reader` so this service's write access can't be reached with the frontend's read-only token.

---

## 1. Role: Contributor

Settings → **Access Control** → **Create Role**.

- Name: `Contributor`
- App Access: **on** (they need to log into the Studio to write content)
- Admin Access: **off**

Set permissions (click into the role, then per-collection):

| Collection | Create | Read | Update | Delete |
|---|---|---|---|---|
| `articoli` | ✅ All | ✅ All | ✅ All | ✅ All |
| `itinerari` | ✅ All | ✅ All | ✅ All | ✅ All |
| `itinerari_correlati` | ✅ All | ✅ All | ✅ All | ✅ All |
| `itinerari_galleria` | ✅ All | ✅ All | ✅ All | ✅ All |
| `autori` | ❌ | ✅ All | ❌ | ❌ |
| `directus_files` | ✅ All | ✅ All | ✅ All (own uploads is enough, but "All" is simpler for v1) | ❌ |

Everything else (Settings, Data Model, Users, Roles, Webhooks, Flows, ...) stays with **no access** — Contributors simply won't see those modules in the Studio sidebar.

Rationale for `autori` being read-only for Contributors: they need to *pick* an author when writing an article/route, but per spec author management isn't a Contributor concern for v1. If a Contributor is also going to be an author, you (Administrator) create their `autori` record for them.

> **Upgrade path noted in `PROJECT_SPEC.md`**: to later restrict Contributors to editing only their own `articoli`/`itinerari`, edit the **Update** and **Delete** permission rows above from "All" to a custom rule: `user_created equals $CURRENT_USER`. Everything else stays the same.

### Create Contributor users

Settings → **Users** → **Create User**, assign role `Contributor`. Repeat per person.

---

## 2. Role: API Reader (for the Astro build)

This is the role behind `DIRECTUS_TOKEN` in `.env` — Astro's build step calls the Directus REST/GraphQL API with this token to fetch content at build time. Keep it read-only.

Settings → **Access Control** → **Create Role**.

- Name: `API Reader`
- App Access: **off** (never logs into the Studio, API-only)
- Admin Access: **off**

Permissions — **Read only, all records**:

> **Note**: ideally `articoli`/`itinerari` reads would be filtered with a Custom permission (`archived equals false`), so the Astro build never sees archived content. Custom field-level filters require a **Custom policy**, which is a premium (paid) Directus Cloud/Enterprise feature — this project doesn't have a premium instance yet. Until then, grant **All** and filter out `archived` records at query time in the Astro build instead. Revisit this once a premium instance is available (see `PROJECT_SPEC.md` upgrade notes).

| Collection | Read |
|---|---|
| `articoli` | ✅ All (filter `archived equals false` at query time in Astro — see note above) |
| `itinerari` | ✅ All (filter `archived equals false` at query time in Astro — see note above) |
| `itinerari_correlati` | ✅ All (no archived field on this junction; it's just structural data) |
| `itinerari_galleria` | ✅ All |
| `autori` | ✅ All (no archived concept for authors) |
| `directus_files` | ✅ All (needed to resolve image/GPX URLs) |

Everything else: no access.

### Generate the static token

1. Settings → Users → **Create User** (yes, a token needs a user account to attach to, even for a role with App Access off).
   - Name: e.g. `astro-build`
   - Email: any placeholder, e.g. `astro-build@scaiodellamontagna.local` (doesn't need to be real, it's not used for login)
   - Role: `API Reader`
   - Status: **Active**
2. Open that user → scroll to **Token** field → generate a static access token.
3. Copy it into `.env` as `DIRECTUS_TOKEN`.

This matches what `.env.example` already expects: `DIRECTUS_TOKEN=your-static-token-here`.

---

## 3. Role: Map Generator (for the `map-generator` service)

This is the role behind `DIRECTUS_TOKEN_MAP_GENERATOR` in `.env` — the `map-generator` container
calls the Directus REST API with this token to read GPX tracks and write back the generated
map/elevation images. **Do not reuse `DIRECTUS_TOKEN`** (the frontend's read-only token) for this —
this role needs write access, which the frontend's token must never have.

Settings → **Access Control** → **Create Role**.

- Name: `Map Generator`
- App Access: **off** (API-only, never logs into the Studio)
- Admin Access: **off**

Permissions:

| Collection | Create | Read | Update | Delete |
|---|---|---|---|---|
| `itinerari` | ❌ | ✅ All | ✅ All | ❌ |
| `directus_files` | ✅ All | ✅ All | ✅ All | ✅ All |

- `itinerari` read is needed to fetch `traccia_gpx`; update is needed to set
  `mappa_statica`/`profilo_altimetrico` after generating them.
- `directus_files` needs full CRUD: create for the new PNGs, read to fetch the GPX asset, delete to
  remove the previous generation's files before replacing them.

Everything else: no access.

### Generate the static token

1. Settings → Users → **Create User**.
   - Name: e.g. `map-generator`
   - Email: any placeholder, e.g. `map-generator@scaiodellamontagna.local`
   - Role: `Map Generator`
   - Status: **Active**
2. Open that user → scroll to **Token** field → generate a static access token.
3. Copy it into `.env` as `DIRECTUS_TOKEN_MAP_GENERATOR`.
4. Optional: open the `Itinerari / Generati` folder (created in `DIRECTUS_SETUP.md` section 0),
   copy its id from the URL, and set it in `.env` as `DIRECTUS_MAP_GENERATOR_FOLDER_ID` so generated
   files are filed there instead of the File Library root.

Next: [`DIRECTUS_MAP_FLOW.md`](./DIRECTUS_MAP_FLOW.md) to wire up the Flow that calls this service.

---

## Recap

| Role | Who | App Access | Scope |
|---|---|---|---|
| Administrator | you (`michele.curtaz@libemax.com`) | ✅ | everything |
| Contributor | other writers | ✅ | full CRUD on `articoli`/`itinerari`(+junctions), read-only `autori` |
| API Reader | `astro-build` service user, static token | ❌ | read-only, all content (archived filtering done at query time until a premium instance enables Custom policies) |
| Map Generator | `map-generator` service user, static token | ❌ | read `itinerari`, update `itinerari`, full CRUD on `directus_files` |

Next: [`MOCK_DATA.md`](./MOCK_DATA.md) to populate mock content for local Astro development.
