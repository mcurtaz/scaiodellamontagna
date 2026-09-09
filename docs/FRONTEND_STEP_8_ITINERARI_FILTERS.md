# Step 8 — Itinerari filters made interactive

Part of `FRONTEND_BUILD_PLAN.md`. Wires the FILTRI band built inert in
Step 7 (`src/components/FilterPanel.astro`, `src/pages/itinerari/index.astro`)
to actually filter and sort the listing, entirely client-side — no
framework, no build-time search index file, per `PROJECT_SPEC.md`'s
"fully client-side search" decision and `FRONTEND_BUILD_PLAN.md` Decision
#5 ("plain vanilla JS ... no UI framework or Astro island library").

## Goal

- Dragging a slider, checking a caratteristiche box, toggling a difficulty
  chip, or clicking "Vicino a me" narrows the visible list immediately, with
  no page reload and no network request.
- The result count label (`"N ITINERARI"`) updates live to match what's
  actually visible.
- "Azzera" resets every control to its rest state and re-shows the full
  list.
- "Ordina per..." becomes a real sort control, re-ordering visible rows.
- Everything still works with JS disabled in the sense that matters: the
  full, correct list still server-renders and is fully readable/linkable —
  only the *filtering* is JS-dependent, matching a search/filter UI's usual
  progressive-enhancement expectations (not a hard requirement anyone asked
  for here, just a side effect of doing this with real form controls).

## Decisions for this step

### Data lives in the DOM, not a separate JSON file

`PROJECT_SPEC.md`'s "Search" section describes exporting itinerari into "a
static JSON index" and filtering against it. Taken literally that suggests
a separate `itinerari.json` asset fetched by the client. **Decision: don't
build a separate JSON file or endpoint.** `src/pages/itinerari/index.astro`
already server-renders one `RouteListItem` row per itinerario with real
data (Step 7) — that markup *is* the index. Each row gets `data-*`
attributes carrying the raw filterable values, and the client script reads
those directly off the DOM instead of re-fetching or re-templating
anything:

```astro
<div
  data-itinerario
  data-distanza={r.distanza_km}
  data-dislivello={r.dislivello_positivo}
  data-tempo={r.tempo_medio_ore}
  data-difficolta={r.difficolta}
  data-bambini={r.is_child_friendly}
  data-inverno={r.is_winter_friendly}
  data-anello={r.is_loop}
  data-lat={r.punto_partenza.coordinates[1]}
  data-lon={r.punto_partenza.coordinates[0]}
>
  <RouteListItem ... />
</div>
```

This needs `getItinerari()` (`src/lib/directus.ts`, added in Step 7) to
fetch two more fields it didn't need before: `is_child_friendly` and
`is_winter_friendly`. Extend its `fields` array with both — everything else
about the function is unchanged.

**Why DOM data attributes over a JSON index + client-side templating**: at
this data volume (tens of routes), re-implementing `RouteListItem`'s markup
in JS to render from JSON would be strictly more code than filtering rows
that already exist. Filtering becomes "toggle a `hidden` attribute per
row"; sorting becomes "reorder existing DOM nodes" (`node.parentElement
.append(node)` on the already-rendered element, not a re-render). If a
future step needs the itinerari data as JSON for something else (an
external search tool, an RSS-like feed), export it separately then —
nothing here blocks that.

### `src/pages/itinerari/index.astro` — wrap each row, add the sort control, add the script

```astro
---
// ...same imports and data-fetching as Step 7, plus:
import { formatTimeLabel, getTypeLabel, formatExcerpt } from "../../lib/format";
---

<!-- FilterPanel and PageHeader unchanged from Step 7 -->

<section class="px-4 py-8 sm:px-8 md:px-14">
  <div class="flex flex-wrap items-center gap-3">
    <span id="itinerari-count" class="font-mono-data text-xs tracking-widest uppercase text-verde">{countLabel}</span>
    <span class="flex-1 h-px bg-inchiostro/20 min-w-6"></span>
    <label class="font-mono-data text-xs text-inchiostro/82">
      Ordina per
      <select id="itinerari-sort" class="ml-1 bg-transparent underline">
        <option value="distanza">distanza</option>
        <option value="dislivello">dislivello +</option>
        <option value="tempo">tempo medio</option>
      </select>
    </label>
  </div>

  <div id="itinerari-list" class="mt-6 divide-y divide-inchiostro/14">
    {itinerari.map((r) => (
      <div
        data-itinerario
        data-distanza={r.distanza_km}
        data-dislivello={r.dislivello_positivo}
        data-tempo={r.tempo_medio_ore}
        data-difficolta={r.difficolta}
        data-bambini={r.is_child_friendly}
        data-inverno={r.is_winter_friendly}
        data-anello={r.is_loop}
        data-lat={r.punto_partenza.coordinates[1]}
        data-lon={r.punto_partenza.coordinates[0]}
      >
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
      </div>
    ))}
  </div>
</section>

<script>
  const list = document.getElementById("itinerari-list")!;
  const rows = Array.from(list.querySelectorAll<HTMLElement>("[data-itinerario]"));
  const countEl = document.getElementById("itinerari-count")!;

  const distanza = document.getElementById("filtro-distanza") as HTMLInputElement;
  const dislivello = document.getElementById("filtro-dislivello") as HTMLInputElement;
  const tempo = document.getElementById("filtro-tempo") as HTMLInputElement;
  const distanzaLabel = document.getElementById("distanza-value")!;
  const dislivelloLabel = document.getElementById("dislivello-value")!;
  const tempoLabel = document.getElementById("tempo-value")!;
  const bambini = document.getElementById("filtro-bambini") as HTMLInputElement;
  const inverno = document.getElementById("filtro-inverno") as HTMLInputElement;
  const anello = document.getElementById("filtro-anello") as HTMLInputElement;
  const vicino = document.getElementById("filtro-vicino") as HTMLInputElement;
  const difficoltaBoxes = Array.from(document.querySelectorAll<HTMLInputElement>('input[name="difficolta"]'));
  const azzera = document.getElementById("filtri-azzera")!;
  const sort = document.getElementById("itinerari-sort") as HTMLSelectElement;

  const distanzaMax = Number(distanza.max);
  const dislivelloMax = Number(dislivello.max);
  const tempoMax = Number(tempo.max);

  const RAGGIO_VICINO_KM = 30; // placeholder threshold — see Open questions
  let userCoords: { lat: number; lon: number } | null = null;

  function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number) {
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function applyFilters() {
    const activeDifficolta = new Set(difficoltaBoxes.filter((b) => b.checked).map((b) => b.value));
    let visible = 0;

    for (const row of rows) {
      const d = Number(row.dataset.distanza);
      const el = Number(row.dataset.dislivello);
      const t = Number(row.dataset.tempo);
      const matchesRanges = d <= Number(distanza.value) && el <= Number(dislivello.value) && t <= Number(tempo.value);
      const matchesDifficolta = activeDifficolta.has(row.dataset.difficolta!);
      const matchesBambini = !bambini.checked || row.dataset.bambini === "true";
      const matchesInverno = !inverno.checked || row.dataset.inverno === "true";
      const matchesAnello = !anello.checked || row.dataset.anello === "true";
      const matchesVicino =
        !vicino.checked ||
        !userCoords ||
        haversineKm(userCoords.lat, userCoords.lon, Number(row.dataset.lat), Number(row.dataset.lon)) <= RAGGIO_VICINO_KM;

      const match = matchesRanges && matchesDifficolta && matchesBambini && matchesInverno && matchesAnello && matchesVicino;
      row.hidden = !match;
      if (match) visible += 1;
    }

    countEl.textContent = `${visible} ${visible === 1 ? "ITINERARIO" : "ITINERARI"}`;
  }

  function applySort() {
    const key = sort.value as "distanza" | "dislivello" | "tempo";
    const field = key === "distanza" ? "distanza" : key === "dislivello" ? "dislivello" : "tempo";
    const sorted = [...rows].sort((a, b) => Number(a.dataset[field]) - Number(b.dataset[field]));
    for (const row of sorted) list.appendChild(row);
  }

  function updateLabels() {
    distanzaLabel.textContent = `0 – ${distanza.value} km`;
    dislivelloLabel.textContent = `0 – ${dislivello.value} m`;
    tempoLabel.textContent = `fino a ${tempo.value} h`;
  }

  for (const input of [distanza, dislivello, tempo, bambini, inverno, anello, ...difficoltaBoxes]) {
    input.addEventListener("input", () => {
      updateLabels();
      applyFilters();
    });
  }

  vicino.addEventListener("change", () => {
    if (!vicino.checked) {
      applyFilters();
      return;
    }
    if (!navigator.geolocation) {
      vicino.checked = false;
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        userCoords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        applyFilters();
      },
      () => {
        vicino.checked = false;
      },
    );
  });

  sort.addEventListener("change", applySort);

  azzera.addEventListener("click", () => {
    distanza.value = String(distanzaMax);
    dislivello.value = String(dislivelloMax);
    tempo.value = String(tempoMax);
    bambini.checked = false;
    inverno.checked = false;
    anello.checked = false;
    vicino.checked = false;
    userCoords = null;
    for (const box of difficoltaBoxes) box.checked = true;
    updateLabels();
    applyFilters();
  });
</script>
```

Notes on the above:
- `row.hidden = !match` uses the native `hidden` attribute rather than a
  Tailwind class toggle — no CSS specificity fights, and it's the same
  mechanism the wider Claude Code / artifact conventions already favor for
  visibility toggles.
- The script is a plain `<script>` in the `.astro` file (client-side,
  processed by Vite/Astro same as any page script) — no
  `client:load`/island directive, because there's no framework component
  here at all, consistent with Decision #5.
- `applySort()` moves existing nodes (`appendChild` on an already-attached
  element re-parents it, doesn't clone) — cheap at this data volume, and
  keeps every event listener/hidden-state on the row intact across a
  re-sort.

### `src/lib/directus.ts` — extend `getItinerari()`'s fields

```ts
export function getItinerari() {
  return client.request(
    readItems("itinerari", {
      fields: [
        "titolo", "slug", "difficolta", "distanza_km", "dislivello_positivo",
        "dislivello_negativo", "tempo_medio_ore", "is_loop", "is_child_friendly",
        "is_winter_friendly", "punto_partenza", "punto_arrivo", "descrizione",
      ],
      sort: ["-date_created"],
    }),
  );
}
```

Only change from Step 7: `is_child_friendly` and `is_winter_friendly`
added, needed for the `data-bambini`/`data-inverno` attributes above.

## What "done" looks like

- Every slider narrows the list live as it's dragged, and its adjacent label
  (`"0 – X km"` etc.) tracks the current value.
- Unchecking nothing / checking a caratteristica narrows the list to
  matching rows only; unchecking a difficulty chip removes that difficulty
  from the results.
- "Vicino a me": checking it prompts for geolocation; on grant, the list
  narrows to routes within `RAGGIO_VICINO_KM`; on denial or an
  unsupported browser, the checkbox silently unchecks itself rather than
  erroring.
- The `"N ITINERARI"` label always matches the count of currently-visible
  rows.
- "Ordina per..." reorders the visible rows by the chosen numeric field.
- "Azzera" returns every control to its rest state and the full list
  reappears.
- No network request fires as a result of any filter/sort interaction
  (verify via the browser's network panel) — everything happens against
  data already present in the DOM from the initial server render.
- Checked at mobile width first, then wider viewports (slider `<input>`s in
  particular need a real touch-drag check, not just a mouse-drag one).

## Open questions

- **`RAGGIO_VICINO_KM = 30` is a placeholder**, not a measured decision —
  there's no real routes-per-area density yet to size a sensible "nearby"
  radius against. Revisit once there's enough real itinerari data to see
  what radius actually produces a useful result set.
- **"Vicino a me" has no visible error state** — a denied/unsupported
  geolocation request just silently unchecks the box. Fine for a personal
  blog's first pass; revisit if it proves confusing in practice (e.g. a
  brief inline message instead of silent failure).
- **Sort is single-key, ascending only** — no descending toggle, no
  secondary sort key, and "vicino a me" doesn't yet plug into the sort
  dropdown as a fourth option (distance-from-me) the way `PROJECT_SPEC.md`'s
  phrasing loosely implies it might. Add it if/when it turns out to matter
  in practice — not blocking for v1.
