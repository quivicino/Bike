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
- punti utili: **fontanelle** (solo a meno di 300 m da un percorso), **colonnine attrezzi** (`amenity=bicycle_repair_station`), **negozi e officine bici**
  (`shop=bicycle`, `craft=bicycle_repair`), **ricariche e-bike** (`amenity=charging_station` + `bicycle=yes`), **rifugi**;
- **bar e ristoranti** (`amenity=restaurant|cafe|bar|pub`) e **agriturismi** (`agriturismo=yes` o `guest_house=agritourism`):
  come le fontanelle, solo quelli a meno di **300 m** da un percorso. Voce «Bar e ristoranti» nel menu, spenta all'inizio;
  nella scheda di ogni percorso l'elenco dei locali lungo il tracciato, con i km dalla partenza;
- **funivie, cabinovie, seggiovie** (`aerialway=cable_car|gondola|chair_lift|mixed_lift`) e **funicolari** (`railway=funicular`):
  linea sulla mappa e scheda con lunghezza, durata, posti e se si può salire con la bici (`aerialway:bicycle`). Spente all'inizio.

## Come funziona

- **Dati salvati nel sito per tutta l'Italia, dalla copia del computer.** Ogni giorno `osm_bike.py`, sul computer di paolo,
  estrae dal PBF Italia di Geofabrik percorsi, tag delle loro vie e punti (gli stessi oggetti della query Overpass), li carica
  come `bike.json.gz` sulla release `dati-osm` e fa ripartire la pubblicazione: `aggiorna_percorsi.js` li divide nelle tessere
  e la zona coperta diventa tutta l'Italia. Serve `pip install osmium` e `gh` collegato all'account; uso:
  `python3 osm_bike.py percorso/italy-latest.osm.pbf` (senza percorso scarica il PBF).
- **Riserva: Lombardia e Valle d'Aosta da Overpass.** Se la copia manca o ha più di 3 giorni (e sul sito non ci sono già i dati d'Italia),
  GitHub esegue `aggiorna_percorsi.js` (workflow `.github/workflows/pubblica.yml`): scarica da Overpass percorsi, tag delle loro vie e punti della Lombardia e della Valle d'Aosta
  allargate di 15 km, a blocchi di mezzo grado, unisce i pezzi dei percorsi tagliati tra un blocco e l'altro e li salva nella
  cartella `dati/` del sito, divisi in tessere da 0,1°. Ogni percorso è salvato una volta sola (nella tessera dove inizia).
  Dentro la zona salvata l'app legge da lì; fuori interroga i server pubblici di Overpass (2–25 km intorno a te).
- I dati **non** stanno nel repository, solo nel sito pubblicato. Per riscaricarli subito: Actions →
  *Pubblica sito e aggiorna percorsi* → *Run workflow*.
- Alla fine dello scaricamento arriva una notifica con l'app **ntfy** se nel repository c'è il secret `NTFY_TOPIC`.
- L'ultima risposta resta sul telefono (IndexedDB): senza campo l'app usa quella.
- Toccando un percorso si apre la sua **scheda**; da lì: navigazione sul percorso (velocità e freccia), «In auto alla partenza»,
  Street View agli estremi, **Scarica il percorso** (GPX, KML, GeoJSON, dal sito MTB o cycling di Waymarked Trails) e
  **Invia Percorso con WhatsApp** (link `?s=percorso&c=centro&v=lat,lon,zoom&r=raggio&k=cosa mostrare&f=filtri&o=ordine&b=mappa`).
- **Da A a B** (pulsante sotto Aggiorna): percorso in bici tra due posti, cercati con Nominatim. Mountain bike con
  [BRouter](https://brouter.de) (profili in `profiliMtb` di config.js, poi `trekking`, poi OSRM), strada e gravel con
  [OSRM bici](https://routing.openstreetmap.de) (se non risponde BRouter `fastbike`). Barra con km, salita (quote di BRouter
  o di Open-Meteo) e tempo stimato; toccando la linea: profilo, pendenza massima, **Salva GPX** e «Pedala sul percorso».
- Pulsanti in basso: **attrezzi** (colonnina o officina aperta più vicina) e **fontanella** più vicina.
- Statistiche d'uso anonime, senza cookie, con [GoatCounter](https://www.goatcounter.com): https://quibike.goatcounter.com
  (da creare con lo stesso login delle altre app).

## Pubblicazione

Impostazioni del repository → Pages → Source: **GitHub Actions**. A ogni modifica su `main` il workflow
pubblica il sito su `https://quivicino.github.io/Bike/`.

## File

- `index.html`, `style.css`: interfaccia (stessi stili di Qui-Trekking, colori viola del logo Qui-Bike)
- `core.js`: logica (difficoltà MTB, fondo, tipo di percorso, unione dei tratti, lunghezza, dislivello, pendenza, tempo,
  orari, query Overpass); si può usare anche da Node (`require("./core.js")`)
- `app.js`: mappa, GPS, percorsi, elenco, impostazioni
- `config.js`: impostazioni iniziali e numero di versione
- `sw.js`, `manifest.webmanifest`, `installa.js`: installazione come app
- `osm_bike.py`: copia di tutta l'Italia dal PBF di Geofabrik, da far girare ogni giorno sul computer
- `aggiorna_percorsi.js`, `.github/workflows/pubblica.yml`: tessere dalla copia del computer (o da Lombardia e Valle d'Aosta via Overpass) e pubblicazione
- `icon-*.png`, `favicon-64.png`, `apple-touch-icon.png`: logo Qui-Bike
