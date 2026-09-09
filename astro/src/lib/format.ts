import type { Itinerario } from "./types";

export function formatTimeLabel(hours: number | string): string {
  const h = Number(hours);
  const wholeHours = Math.floor(h);
  const minutes = Math.round((h - wholeHours) * 60);
  return minutes === 0 ? `${wholeHours} h` : `${wholeHours} h ${minutes}`;
}

export function getTypeLabel(it: Pick<Itinerario, "is_loop" | "punto_partenza" | "punto_arrivo">): string {
  if (it.is_loop) return "anello";
  const [lonA, latA] = it.punto_partenza.coordinates;
  const [lonB, latB] = it.punto_arrivo.coordinates;
  return lonA === lonB && latA === latB ? "andata e ritorno" : "traversata";
}
