import type { GeoPoint, Itinerario } from "./types";

export function formatTimeLabel(hours: number | string): string {
  const h = Number(hours);
  const wholeHours = Math.floor(h);
  const minutes = Math.round((h - wholeHours) * 60);
  return minutes === 0 ? `${wholeHours} h` : `${wholeHours} h ${minutes}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("it-IT", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatExcerpt(markdown: string, maxLength = 140): string {
  const firstParagraph = markdown.split(/\n\s*\n/)[0].trim();
  if (firstParagraph.length <= maxLength) return firstParagraph;
  const truncated = firstParagraph.slice(0, maxLength);
  return `${truncated.slice(0, truncated.lastIndexOf(" "))}…`;
}

export function getTypeLabel(it: Pick<Itinerario, "is_loop" | "punto_partenza" | "punto_arrivo">): string {
  if (it.is_loop) return "anello";
  const [lonA, latA] = it.punto_partenza.coordinates;
  const [lonB, latB] = it.punto_arrivo.coordinates;
  return lonA === lonB && latA === latB ? "andata e ritorno" : "traversata";
}

export function formatHoursDecimal(hours: number | string): string {
  return `${Number(hours).toLocaleString("it-IT", { maximumFractionDigits: 1 })} h`;
}

export function formatCoordinates(point: GeoPoint): string {
  const [lon, lat] = point.coordinates;
  return `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

export function sameCoordinates(a: GeoPoint, b: GeoPoint): boolean {
  return a.coordinates[0] === b.coordinates[0] && a.coordinates[1] === b.coordinates[1];
}

export function caratteristicheLines(it: Pick<Itinerario, "is_child_friendly" | "is_winter_friendly" | "is_loop">): string[] {
  return [
    it.is_child_friendly ? "Adatto ai bambini." : "Non adatto ai bambini.",
    it.is_winter_friendly ? "Adatto in inverno." : "Non adatto in inverno.",
    it.is_loop ? "Ad anello." : "Non ad anello.",
  ];
}
