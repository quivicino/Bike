# Qui-Bike

Web app per il telefono che mostra i **percorsi in mountain bike e gravel** vicino a te, con lo stesso aspetto e
funzionamento di [Qui-Trekking](https://github.com/quivicino/Trekking) e delle altre app Qui:

- itinerari MTB e in bici di OpenStreetMap (relazioni `route=mtb` e `route=bicycle` con qualunque `network`: `lcn`, `rcn`, `ncn` e anche gli EuroVelo `icn`, come VENTO lungo il Po),
  colorati secondo la **difficoltà MTB**, come le piste: verde **Facile** (S0), blu **Media** (S1), rosso **Difficile** (S2),
  nero **Per esperti** (S3 e oltre), grigio a puntini se non indicata. Viene da `mtb:scale` (o `mtb:scale:imba`) del percorso;
  se manca, dal grado più alto che copre almeno 300 m (o il 5%) delle sue vie. Senza tratti di sentiero il percorso è
  facile anche senza grado (difficoltà *stimata*);
- **fondo**: per ogni via del percorso `highway`, `surface`, `tracktype` e `mtb:scale` dicono se è asfalto, sterrato e ghiaia
  o sentiero; l'app mostra le percentuali in una barra colorata;
- **tipo di percorso** dal fondo: **MTB** (almeno il 15% di sentiero, o il 5% se è un itinerario MTB, o difficoltà D/X),
  **Gravel** (sterrato senza sentieri tecnici), **Strada** (almeno l'80% asfaltato, linea tratteggiata);
- **lunghezza**, **dislivello** (tag `ascent`/`descent` o stimato dalle quote di [Open-Meteo](https://open-meteo.com/en/docs/elevation-api)),
  quota minima e massima, **pendenza massima** su tratti di almeno 200 m, profilo altimetrico e **tempo in bici**
  (12 km/h su sentiero, 16 su sterrato, 20 su asfalto, più un'ora ogni 500 m di salita);
- percorsi **ad anello** (tag `roundtrip=yes`, o partenza e arrivo a meno di 300 m), con il filtro «Solo ad anello»;
- punti utili: **fontanelle**, **colonnine attrezzi** (`amenity=bicycle_repair_station`), **negozi e officine bici**
  (`shop=bicycle`, `craft=bicycle_repair`), **ricariche e-bike** (`amenity=charging_station` + `bicycle=yes`), **rifugi**.

## Come funziona

- **Dati salvati nel sito per tutta la Lombardia.** Ogni lunedì GitHub esegue `aggiorna_percorsi.js`
  (workflow `.github/workflows/pubblica.yml`): scarica da Overpass percorsi, tag delle loro vie e punti della Lombardia
  allargata di 15 km, a blocchi di mezzo grado, unisce i pezzi dei percorsi tagliati tra un blocco e l'altro e li salva nella
  cartella `dati/` del sito, divisi in tessere da 0,1°. Ogni percorso è salvato una volta sola (nella tessera dove inizia).
  In Lombardia l'app legge da lì; fuori interroga i server pubblici di Overpass (2–25 km intorno a te).
- I dati **non** stanno nel repository, solo nel sito pubblicato. Per riscaricarli subito: Actions →
  *Pubblica sito e aggiorna percorsi* → *Run workflow*.
- Alla fine dello scaricamento arriva una notifica con l'app **ntfy** se nel repository c'è il secret `NTFY_TOPIC`.
- L'ultima risposta resta sul telefono (IndexedDB): senza campo l'app usa quella.
- Toccando un percorso si apre la sua **scheda**; da lì: navigazione sul percorso (velocità e freccia), «In auto alla partenza»,
  Street View agli estremi, **Scarica il percorso** (GPX, KML, GeoJSON, dal sito MTB o cycling di Waymarked Trails) e
  **Invia Percorso con WhatsApp** (link `?s=percorso&c=centro&v=lat,lon,zoom&r=raggio&k=cosa mostrare&f=filtri&o=ordine&b=mappa`).
- Pulsanti in basso: **attrezzi** (colonnina o officina aperta più vicina) e **fontanella** più vicina.
- Statistiche d'uso anonime, senza cookie, con [GoatCounter](https://www.goatcounter.com): https://quibike.goatcounter.com
  (da creare con lo stesso login delle altre app).

## Pubblicazione

Impostazioni del repository → Pages → Source: **GitHub Actions**. A ogni modifica su `main` il workflow
pubblica il sito su `https://quivicino.github.io/Bike/`.

## File

- `index.html`, `style.css`: interfaccia (stessi stili di Qui-Trekking, barra color terra)
- `core.js`: logica (difficoltà MTB, fondo, tipo di percorso, unione dei tratti, lunghezza, dislivello, pendenza, tempo,
  orari, query Overpass); si può usare anche da Node (`require("./core.js")`)
- `app.js`: mappa, GPS, percorsi, elenco, impostazioni
- `config.js`: impostazioni iniziali e numero di versione
- `sw.js`, `manifest.webmanifest`, `installa.js`: installazione come app
- `aggiorna_percorsi.js`, `.github/workflows/pubblica.yml`: scaricamento settimanale della Lombardia e pubblicazione
- `icon-*.png`, `favicon-64.png`, `apple-touch-icon.png`: logo Qui con la bici
