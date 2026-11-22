/*
 * Qui-Bike – configurazione
 */
window.QT_CONFIG = {
  // Versione dell'app, mostrata in fondo alla pagina Elenco. Aumentala a ogni aggiornamento.
  versione: "7",

  // Raggio di ricerca iniziale in metri (modificabile anche dall'app)
  raggioMetri: 15000,

  // Ricentra e ricalcola quando ti sposti di più di questi metri
  ricaricaDopoMetri: 500,

  // Cosa mostrare all'inizio: tipi di percorso (TM mountain bike, TG gravel, TS strada), difficoltà (DF facile,
  // DM media, DD difficile, DX per esperti, DND non indicata) e punti (W fontanelle, A colonnine attrezzi,
  // N negozi e officine, C ricariche e-bike, R rifugi, L bar e ristoranti vicino ai percorsi, F funivie e seggiovie)
  categorie: ["TM", "TG", "TS", "DF", "DM", "DD", "DX", "DND", "W", "A", "N"],

  // Massimo di segnaposto sulla mappa (i più vicini): oltre, la mappa diventa lenta sul telefono
  maxSegnaposto: 800,

  // Server Overpass (OpenStreetMap), in ordine di preferenza
  overpass: [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
  ],

  // Quote del terreno per dislivello, pendenza e profilo (Open-Meteo, gratuito)
  quote: "https://api.open-meteo.com/v1/elevation",

  // Percorso in bici da A a B (gratuiti, dati OpenStreetMap): OSRM bici per strada e gravel, BRouter per la mountain bike.
  // Profili BRouter MTB in ordine: se il primo non c'è sul server si prova il successivo.
  osrmBici: "https://routing.openstreetmap.de/routed-bike",
  brouter: "https://brouter.de/brouter",
  profiliMtb: ["mtb-zossebart", "trekking"],

  // Auto-refresh a ogni avvio, in secondi (0 = spento: l'app riparte dall'ultima posizione). Si cambia dalla pagina elenco, solo per quella volta.
  autoRefreshSecondi: 0
};
