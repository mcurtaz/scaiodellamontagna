export interface Autore {
  id: number;
  nome: string;
  bio: string;
  foto: string | null;
}

export interface GeoPoint {
  type: "Point";
  coordinates: [number, number]; // [lon, lat]
}

export interface Articolo {
  id: number;
  titolo: string;
  slug: string;
  immagine: string | null;
  testo: string;
  date_created: string;
  autore: number | Autore;
}

export interface GalleriaImage {
  directus_files_id: string;
  didascalia: string | null;
  sort: number | null;
}

export interface Itinerario {
  id: number;
  titolo: string;
  slug: string;
  dislivello_positivo: number;
  dislivello_negativo: number;
  tempo_medio_ore: string;
  distanza_km: string;
  difficolta: "T" | "E" | "EE" | "EEA" | "OFA";
  is_child_friendly: boolean;
  is_winter_friendly: boolean;
  is_loop: boolean;
  punto_partenza: GeoPoint;
  punto_arrivo: GeoPoint;
  traccia_gpx: string | null;
  descrizione: string;
  autore: number | Autore;
  galleria?: GalleriaImage[];
}

export interface ItinerarioCorrelatoJunction {
  id: number;
  tipo: "prosecuzione" | "variante" | "nella_zona";
  itinerari_id: number | Itinerario;
  itinerario_correlato: number | Itinerario;
}

export interface Schema {
  articoli: Articolo[];
  itinerari: Itinerario[];
  itinerari_correlati: ItinerarioCorrelatoJunction[];
  autori: Autore[];
}
