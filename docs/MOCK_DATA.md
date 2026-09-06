# Mock Data

Content to type into Directus (after [`DIRECTUS_SETUP.md`](./DIRECTUS_SETUP.md) and [`DIRECTUS_USERS.md`](./DIRECTUS_USERS.md) are done) so the Astro frontend has something real to fetch and render while it's being built. Two authors, two articoli, two itinerari (reusing the "Rifugio Curò → Lago Gelt" example from `PROJECT_SPEC.md`, linked as a `prosecuzione`).

Coordinates and GPX tracks below are **placeholders**, not surveyed — good enough to render a map pin and a line, not good enough to actually hike from. Swap in real recorded tracks later.

---

## Autori

### Autore 1

- `nome`: Michele Curtaz
- `bio`: Escursionista per passione, in giro per le Orobie e le Alpi ogni volta che il tempo lo permette.
- `foto`: any placeholder image you have on hand — not critical for mock content.

### Autore 2

- `nome`: Sara Bonetti
- `bio`: Guida escursionistica amatoriale, appassionata di itinerari ad anello e ciaspolate invernali.
- `foto`: optional, same as above.

---

## Articoli

### Articolo 1

- `status`: `published`
- `titolo`: Cosa mettere nello zaino per un'escursione di giornata
- `slug`: cosa-mettere-nello-zaino
- `autore`: Michele Curtaz
- `immagine`: any placeholder image
- `testo`:

```md
Prima di partire per un'escursione di giornata, vale la pena controllare lo zaino con una checklist minima. Non serve portare tutto quello che si possiede, ma nemmeno partire impreparati.

## L'essenziale

- Acqua: almeno 1.5 litri, di più se fa caldo o l'itinerario è lungo
- Cibo: barrette, frutta secca, un pranzo al sacco se il giro dura tutto il giorno
- Abbigliamento a strati: una giacca a vento/impermeabile anche se il meteo sembra stabile
- Scarpe da trekking con suola scolpita, non scarpe da ginnastica
- Kit di primo soccorso essenziale
- Frontalino, anche in estate: un imprevisto può far calare il buio prima del previsto
- Power bank per il telefono, soprattutto se usi il GPS per seguire la traccia

## Da non dimenticare

- Traccia GPX del percorso scaricata offline, non solo salvata "online"
- Mappa cartacea di riserva se la zona non ha copertura
- Crema solare e occhiali da sole, anche in quota con neve residua

Meglio uno zaino un po' più pesante con l'occorrente, che uno leggero senza l'essenziale.
```

### Articolo 2

- `status`: `published`
- `titolo`: Come leggere la scala di difficoltà CAI
- `slug`: scala-difficolta-cai
- `autore`: Sara Bonetti
- `immagine`: any placeholder image
- `testo`:

```md
Ogni itinerario su questo sito riporta una sigla di difficoltà secondo la scala del Club Alpino Italiano (CAI). Ecco cosa significano.

## Le sigle

- **T — Turistico**: percorsi facili, sentieri o mulattiere ben evidenti, adatti a chiunque abbia un minimo di allenamento.
- **E — Escursionistico**: sentieri di montagna su terreno vario, richiedono un minimo di esperienza ed equipaggiamento adeguato.
- **EE — Escursionisti Esperti**: terreno esposto, tratti ripidi o non segnalati, serve esperienza, passo sicuro e assenza di vertigini.
- **EEA — Escursionisti Esperti con Attrezzatura**: vie ferrate o percorsi attrezzati, obbligatori imbrago, casco e set da ferrata.
- **OFA — Occorrono Fune e/o Attrezzatura Alpinistica**: terreno glaciale o alpinistico, necessaria corda ed equipaggiamento da alpinismo.

## Un consiglio

La sigla descrive il tratto più impegnativo dell'intero percorso, non la media. Un itinerario "EE" può avere lunghi tratti facili e un singolo passaggio esposto che ne alza la difficoltà complessiva: leggi sempre la descrizione, non fermarti alla sigla.
```

---

## Itinerari

### Itinerario 1

- `status`: `published`
- `titolo`: Gita al Rifugio Curò
- `slug`: gita-al-rifugio-curo
- `autore`: Michele Curtaz
- `dislivello_positivo`: 850
- `dislivello_negativo`: 850
- `tempo_medio_ore`: 3.5
- `distanza_km`: 9.2
- `difficolta`: E
- `is_child_friendly`: false
- `is_winter_friendly`: false
- `is_loop`: false — andata e ritorno sullo stesso sentiero
- `punto_partenza`: parcheggio Valbondione — lat `46.0090`, lon `9.9520` (placeholder)
- `punto_arrivo`: stesso punto del parcheggio (andata e ritorno)
- `traccia_gpx`: see the placeholder GPX template below, upload as `gita-al-rifugio-curo.gpx`
- `descrizione`:

```md
Salita classica al Rifugio Curò, punto di appoggio per chi vuole proseguire verso i laghi dell'alta Val Seriana. Sentiero ben segnalato, fondo misto sterrato e mulattiera, un tratto finale più ripido negli ultimi tornanti prima del rifugio.

Si sale e si scende dallo stesso sentiero: nessun bivio significativo lungo il percorso.
```

- `galleria`: optional, add 1-2 placeholder images with captions e.g. "Vista sul rifugio dagli ultimi tornanti"

### Itinerario 2

- `status`: `published`
- `titolo`: Rifugio Curò → Lago Gelt
- `slug`: rifugio-curo-lago-gelt
- `autore`: Michele Curtaz
- `dislivello_positivo`: 180
- `dislivello_negativo`: 20
- `tempo_medio_ore`: 1
- `distanza_km`: 2.4
- `difficolta`: E
- `is_child_friendly`: false
- `is_winter_friendly`: false
- `is_loop`: false — traversata, punto di partenza e arrivo diversi
- `punto_partenza`: Rifugio Curò — lat `46.0145`, lon `9.9610` (placeholder)
- `punto_arrivo`: Lago Gelt — lat `46.0210`, lon `9.9680` (placeholder)
- `traccia_gpx`: see placeholder GPX template below, upload as `rifugio-curo-lago-gelt.gpx`
- `descrizione`:

```md
Prosecuzione naturale della salita al Rifugio Curò per chi vuole raggiungere il Lago Gelt. Sentiero meno battuto, alcuni tratti su pietraia. Da valutare in caso di neve residua a inizio stagione.
```

- `galleria`: optional

### Link tra i due itinerari

In `itinerari_correlati`, crea una riga:

- `itinerario_da`: Gita al Rifugio Curò
- `itinerario_a`: Rifugio Curò → Lago Gelt
- `tipo`: `prosecuzione`

Questo è l'esempio esatto discusso in `PROJECT_SPEC.md` per la modeling philosophy: due record indipendenti, collegati da una relazione tipizzata, invece di un unico percorso composto automaticamente.

---

## Placeholder GPX template

Minimal valid GPX with a handful of trackpoints — enough to render a line on a map and confirm the Astro build can parse/display a `.gpx` file. **Not a real track.** Adjust coordinates slightly between the two files so they don't overlap identically, or just reuse as-is for a first smoke test.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="scaiodellamontagna-mock" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Mock track</name>
    <trkseg>
      <trkpt lat="46.0090" lon="9.9520"><ele>900</ele></trkpt>
      <trkpt lat="46.0110" lon="9.9550"><ele>1050</ele></trkpt>
      <trkpt lat="46.0130" lon="9.9580"><ele>1250</ele></trkpt>
      <trkpt lat="46.0145" lon="9.9610"><ele>1750</ele></trkpt>
    </trkseg>
  </trk>
</gpx>
```

Save this as a `.gpx` file locally (any text editor) and upload it through the Directus file library when filling in `traccia_gpx` on each itinerario.
