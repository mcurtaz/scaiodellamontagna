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
