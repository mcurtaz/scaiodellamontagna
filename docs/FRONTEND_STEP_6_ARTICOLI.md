# Step 6 — Articoli listing + Articolo detail

Part of `FRONTEND_BUILD_PLAN.md`. Adds the two Articoli pages — `/articoli`
(listing) and `/articoli/[slug]` (detail) — wired to Directus using the fetch
pattern Step 5 already proved on the Home page. Both routes already have live
links pointing at them: Nav's "Articoli" item (`src/components/Nav.astro`)
and Home's "Tutti gli articoli →" action (`src/pages/index.astro`) both
target `/articoli`, and every `ArticleListItem` on Home already links to
`/articoli/${slug}` — so this step fills in routes that are currently 404s.

## Goal

- `npm run build` succeeds against the live local Directus instance.
- `/articoli` lists every `articoli` row, most recent first, with real data.
- `/articoli/[slug]` renders a real detail page for every article's slug.
- Nav's "Articoli" link, Home's "Tutti gli articoli →" link, and every
  `ArticleListItem` href on Home resolve to a real page instead of 404ing.

## Schema facts

- `articoli` fields in scope: `titolo`, `slug`, `immagine` (file id), `testo`
  (markdown, plain string), `autore` (m2o → `autori`, only `nome` needed).
  Plus the Directus system field `date_created` — already used for sorting in
  Step 5's Home queries, but never typed or read as a value until now.
- **Gap vs. the mockup.** The mockup's Articoli listing and Articolo detail
  cards show a one-line "dek" excerpt under every title, and the detail page
  has a bespoke "quick facts" sidebar box (e.g. "acqua · 1,5 l"). Neither is
  backed by a Directus field — the schema has no excerpt/summary field and no
  structured facts field. **Decision: drop both for v1.** Listing rows are
  thumbnail + title + author + date; the detail page has no dek and no facts
  box. Only reconsider if a real field for either gets added to the schema.
- **Markdown rendering wrinkle.** `testo` is markdown, but Astro 7.3's
  default markdown engine (`@astrojs/markdown-satteri`, confirmed installed
  under `astro/node_modules/@astrojs/markdown-satteri`) has no simple public
  "string in, HTML out" function — it's a plugin/processor architecture, not
  meant for ad hoc use outside Astro's own `.md`-file pipeline. The older
  `@astrojs/markdown-remark` package would give a straightforward
  `renderMarkdown(content, opts)` call and is even listed as a compatible
  peer in `astro`'s own `package.json` (`^7.3.0`), but isn't installed by
  default since satteri is now the default engine. **Decision: don't add
  either dependency in this step.** Render `testo` as plain paragraphs
  (split on blank lines) instead of parsed HTML — see "Open questions" below.

## Decisions for this step

### `src/lib/types.ts` — add `date_created` to `Articolo`

```ts
export interface Articolo {
  id: number;
  titolo: string;
  slug: string;
  immagine: string | null;
  testo: string;
  date_created: string;
  autore: number | Autore;
}
```

### `src/lib/directus.ts` — add `getArticoli()`

```ts
export function getArticoli() {
  return client.request(
    readItems("articoli", {
      fields: ["titolo", "slug", "immagine", "testo", "date_created", { autore: ["nome"] }],
      sort: ["-date_created"],
    }),
  );
}
```

No `limit` (unlike `getHomeArticoli`) — fetches every article. Fine at this
content volume and matches `PROJECT_SPEC.md`'s "no pagination" stance. Used
for both the listing page (ignores `testo`) and the detail page's
`getStaticPaths` below — one query, no per-slug re-fetch, no N+1.

### `src/lib/format.ts` — add `formatDate()`

```ts
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
```

Produces e.g. `2 set 2026`, matching the mockup's date format.

### `src/components/ArticleListItem.astro` — add optional `date` prop

```astro
---
interface Props {
  title: string;
  href: string;
  author: string;
  date?: string;
  imageUrl?: string;
}

const { title, href, author, date, imageUrl } = Astro.props;
---

<div class="grid grid-cols-[64px_1fr] sm:grid-cols-[96px_1fr_150px] gap-4 sm:gap-6 items-center py-5">
  {imageUrl ? (
    <a href={href} class="block h-16 sm:h-[72px] row-span-2 sm:row-span-1 overflow-hidden">
      <img src={imageUrl} alt="" class="h-full w-full object-cover" />
    </a>
  ) : (
    <a href={href} class="media-placeholder media-placeholder-diagonal h-16 sm:h-[72px] row-span-2 sm:row-span-1"></a>
  )}
  <h3 class="text-xl sm:text-2xl font-normal tracking-tight leading-snug">
    <a href={href} class="hover:text-terra">{title}</a>
  </h3>
  <div class="col-start-2 sm:col-start-3 font-mono-data text-xs text-inchiostro/80 sm:text-right">
    {author}{date && <><br />{date}</>}
  </div>
</div>
```

Home's existing usage (`author={a.autore.nome}`, no `date` passed) is
unaffected — its rendered output stays identical to Step 5's.

### `src/components/SectionHeader.astro` — add optional `meta` prop

```astro
---
interface Props {
  label: string;
  tone?: "onCrema" | "onSage";
  action?: { label: string; href: string };
  meta?: string;
}

const { label, tone = "onCrema", action, meta } = Astro.props;
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
</div>
```

`meta` is plain right-aligned text, not a link — used for "N pubblicati" on
the listing page and "autore · data" on the detail page. Nothing currently
passes both `action` and `meta` together, but the component doesn't need to
forbid it.

### `src/pages/articoli/index.astro` (new — listing page)

```astro
---
import Layout from "../../layouts/Layout.astro";
import SageBand from "../../components/SageBand.astro";
import SectionHeader from "../../components/SectionHeader.astro";
import PageHeader from "../../components/PageHeader.astro";
import ArticleListItem from "../../components/ArticleListItem.astro";
import { getArticoli, assetUrl } from "../../lib/directus";
import { formatDate } from "../../lib/format";

const articoli = await getArticoli();
---

<Layout title="Articoli" active="articoli">
  <SageBand>
    <SectionHeader label="ARTICOLI" tone="onSage" meta={`${articoli.length} pubblicati`} />
    <div class="mt-8">
      <PageHeader title="Appunti di montagna">
        <p class="text-inchiostro/82">
          Attrezzatura, lettura della difficoltà, cose imparate sbagliando.
          In ordine di pubblicazione.
        </p>
      </PageHeader>
    </div>
  </SageBand>

  <section class="px-4 py-8 sm:px-8 md:px-14">
    <div class="divide-y divide-inchiostro/14">
      {articoli.map((a) => (
        <ArticleListItem
          title={a.titolo}
          href={`/articoli/${a.slug}`}
          author={a.autore.nome}
          date={formatDate(a.date_created)}
          imageUrl={a.immagine ? assetUrl(a.immagine, { width: 192, quality: 80 }) : undefined}
        />
      ))}
    </div>
  </section>
</Layout>
```

H1 and lead copy are the mockup's authored Italian text, used directly (not
placeholder). No filters, no search, no pagination — matches
`PROJECT_SPEC.md` ("no categories/tags for v1 ... nothing to filter").

### `src/pages/articoli/[slug].astro` (new — detail page)

```astro
---
import Layout from "../../layouts/Layout.astro";
import SageBand from "../../components/SageBand.astro";
import SectionHeader from "../../components/SectionHeader.astro";
import PageHeader from "../../components/PageHeader.astro";
import ArticleListItem from "../../components/ArticleListItem.astro";
import { getArticoli, assetUrl } from "../../lib/directus";
import { formatDate } from "../../lib/format";
import type { Articolo, Autore } from "../../lib/types";

export async function getStaticPaths() {
  const articoli = await getArticoli();
  return articoli.map((articolo) => ({
    params: { slug: articolo.slug },
    props: {
      articolo,
      others: articoli.filter((a) => a.slug !== articolo.slug).slice(0, 3),
    },
  }));
}

interface Props {
  articolo: Articolo & { autore: Autore };
  others: (Articolo & { autore: Autore })[];
}

const { articolo, others } = Astro.props;
const paragraphs = articolo.testo.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
---

<Layout title={articolo.titolo} active="articoli">
  <div class="px-4 pt-8 sm:px-8 md:px-14">
    <SectionHeader label="ARTICOLO" meta={`${articolo.autore.nome} · ${formatDate(articolo.date_created)}`} />
    <div class="mt-8">
      <PageHeader title={articolo.titolo} />
    </div>
  </div>

  <div class="px-4 py-8 sm:px-8 md:px-14">
    {articolo.immagine ? (
      <img
        src={assetUrl(articolo.immagine, { width: 1200, quality: 80 })}
        alt=""
        class="h-[320px] w-full rounded-lg object-cover"
      />
    ) : (
      <div class="media-placeholder media-placeholder-diagonal h-[320px] w-full"></div>
    )}
  </div>

  <div class="px-4 pb-8 sm:px-8 md:px-14">
    <SectionHeader label="TESTO" />
    <div class="mt-8 grid grid-cols-1 gap-4 md:grid-cols-[1.5fr_1fr] md:gap-12">
      <div class="space-y-5">
        {paragraphs.map((p) => (
          <p class="text-[17.5px] leading-[1.72] text-inchiostro">{p}</p>
        ))}
      </div>
    </div>
  </div>

  {others.length > 0 && (
    <SageBand>
      <SectionHeader
        label="ALTRI ARTICOLI"
        tone="onSage"
        action={{ label: "Tutti gli articoli →", href: "/articoli" }}
      />
      <div class="mt-8 divide-y divide-inchiostro/14">
        {others.map((a) => (
          <ArticleListItem
            title={a.titolo}
            href={`/articoli/${a.slug}`}
            author={a.autore.nome}
            imageUrl={a.immagine ? assetUrl(a.immagine, { width: 192, quality: 80 }) : undefined}
          />
        ))}
      </div>
    </SageBand>
  )}
</Layout>
```

`getStaticPaths` fetches the full article list once and passes each item
straight through as a prop (plus up to 3 "related" others) — no per-slug
query. `getArticoli()`'s SDK-inferred type has `autore: number | Autore` per
`Schema`, but the query's `fields` always expands `autore` to `{ nome }`; the
`Props` interface above narrows it to `Autore` directly, the same trust
`index.astro` already places in `a.autore.nome` for the Home queries.

Related articles reuse `ArticleListItem` without the `date` prop, matching
the mockup's related-row treatment (thumbnail / title / author only).

## What "done" looks like

- `Articolo` in `types.ts` has `date_created: string`.
- `directus.ts` has `getArticoli()` — no `limit`, sorted `-date_created`.
- `format.ts` has `formatDate()`.
- `ArticleListItem.astro` has the optional `date` prop; Home's rendered
  output is unchanged (no `date` passed there).
- `SectionHeader.astro` has the optional `meta` prop.
- `src/pages/articoli/index.astro` exists and lists every real article.
- `src/pages/articoli/[slug].astro` exists; `getStaticPaths` returns one path
  per article; each page renders real title, author, date, cover image (or
  placeholder), body paragraphs, and up to 3 related articles.
- Nav's "Articoli" link, Home's "Tutti gli articoli →" link, and every
  per-article link on Home resolve instead of 404ing.
- `npm run build` succeeds against the live local Directus instance.
- Checked at mobile width first, then wider viewports (mobile-first rule
  from `FRONTEND_BUILD_PLAN.md`).

## Open questions

- **Markdown rendering is deferred.** `testo` renders as plain paragraphs —
  no `##` headings, lists, bold, or links get parsed. Follow-up: evaluate
  adding `@astrojs/markdown-remark` (matches Astro's own compatible-peer
  version, closer to "native") vs. `marked` (simpler, no coupling to Astro's
  internal engine choices) once real article content actually needs
  formatting beyond paragraphs.
- **Dek excerpt and quick-facts sidebar are intentionally dropped, not
  deferred** — no schema field backs either today. Only reconsider if a real
  field gets added to `articoli` in Directus.
