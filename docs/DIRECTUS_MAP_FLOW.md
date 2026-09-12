# Directus Setup — Map/Elevation Generation Flow

Do this **after** [`DIRECTUS_SETUP.md`](./DIRECTUS_SETUP.md) section 6 (the `mappa_statica` /
`profilo_altimetrico` fields must exist) and [`DIRECTUS_USERS.md`](./DIRECTUS_USERS.md) section 3
(the `Map Generator` role/token must exist). Implements the Flow described in
[`MAP_PROFILE_PLAN_A_STATIC.md`](./MAP_PROFILE_PLAN_A_STATIC.md): whenever an editor
uploads/changes `traccia_gpx` on an `itinerari` record, call the `map-generator` service so it
(re)generates the map and elevation images.

## Why the id needs a branch

A single Event Hook trigger can be scoped to both `items.create` and `items.update` at once, but
those two events expose the saved item's id differently:

- On `items.create`, the primary key is at `$trigger.key` (singular — a create always makes
  exactly one row).
- On `items.update`, it's at `$trigger.keys` (plural — an **array**, since Directus allows bulk
  edits of multiple rows at once), even when the admin UI only ever edits one row through the form.

So the Flow branches once on `$trigger.event` to pick the right reference before calling the
webhook.

## Flow — "Genera mappa"

Settings → **Flows** → **Create Flow**.

1. Name: `Genera mappa`.
2. Trigger: **Event Hook** → type **Action** (non-blocking — the record should save immediately;
   generation can happen a moment later) → Scope: check **both** `items.create` and
   `items.update` → Collection: `itinerari`.
3. Add a **Condition** operation, "GPX presente": `{{$trigger.payload.traccia_gpx}}` is set (not
   empty). This reliably detects "GPX was touched" on both create (present in the full payload)
   and update (Directus's `items.update` trigger payload only includes the fields that were
   actually changed).
4. On the **true** branch of that condition, add a second **Condition** operation, "È una
   modifica?": `{{$trigger.event}}` equals `items.update`.
5. On the **true** branch of the second condition (it's an update), add a **Webhook / Request
   URL** operation:
   - Method: `POST`
   - URL: `http://map-generator:8000/generate`
   - Body: `{ "item_id": {{$trigger.keys[0]}} }`
6. On the **false** branch of the second condition (it's a create), add another **Webhook /
   Request URL** operation with the same method/URL but:
   - Body: `{ "item_id": {{$trigger.key}} }`
7. Save.

```
Trigger (items.create + items.update on itinerari)
        │
        ▼
Condition: traccia_gpx presente?
   │ false            │ true
   ▼                   ▼
 (stop)      Condition: è una modifica?
                  │ true             │ false
                  ▼                   ▼
        Webhook → item_id:     Webhook → item_id:
        {{$trigger.keys[0]}}   {{$trigger.key}}
```

## Optional: failure visibility

A failed webhook call (bad GPX, Directus write error inside the service) shows up in the Flow's run
log (open the Flow → **Logs**) but doesn't otherwise notify anyone. If silent failures become a
problem in practice, add a further operation on either webhook's error branch (e.g. **Send
Email**) — skipped for v1 since editors can simply re-save the record to retry once a bad GPX is
fixed.

## Verifying it works

1. Upload a `.gpx` file to a test `itinerari` record's `traccia_gpx` field and save (try both
   creating a new record and editing an existing one, to exercise both webhook branches).
2. Open the Flow → **Logs** and confirm a successful run.
3. Reopen the `itinerari` record — `mappa_statica` and `profilo_altimetrico` should now be
   populated.
4. Open `mappa_statica` at full size and confirm "© OpenStreetMap contributors" is legible in a
   corner of the image — this is a hard legal requirement (see `MAP_PROFILE_PLAN_A_STATIC.md`),
   not optional polish.
