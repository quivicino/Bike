#!/usr/bin/env python3
"""
Qui-Bike – copia di tutta l'Italia, da far girare ogni giorno sul computer di paolo (accanto a osm_italia.py).

Legge il PBF Italia di Geofabrik ed estrae gli stessi oggetti che l'app chiede a Overpass:
  - i percorsi in bici (relazioni route=mtb e route=bicycle) con la geometria delle loro vie;
  - i tag delle vie dei percorsi che servono per fondo e difficoltà (highway, surface, tracktype, mtb:scale);
  - colonnine attrezzi, negozi e officine bici, ricariche e-bike, rifugi, funivie e seggiovie (con la traccia);
  - fontanelle e bar, ristoranti e agriturismi, solo vicino ai percorsi (il controllo preciso dei 300 m lo fa il sito).
Scrive bike.json.gz nello stesso formato di una risposta di Overpass, lo carica sulla release «dati-osm»
del repository quivicino/Bike e fa ripartire la pubblicazione del sito, che lo trasforma nelle tessere dell'app
(aggiorna_percorsi.js). Se la copia manca o ha più di 3 giorni, il sito torna alle regioni scaricate da Overpass.

Per occupare poco disco e poca memoria, prima ritaglia dal PBF Italia un piccolo PBF (bike-filtrato.osm.pbf, qualche
decina di MB) con solo i percorsi, i punti e le vie e i nodi che servono, e lavora su quello.

Serve:   pip install osmium  (versione 4 o successiva)
Invio:   con il token GitHub in token.txt (nella cartella dello script, come osm_italia.py, o indicato con
         --token=percorso); il token deve poter scrivere su quivicino/Bike (Contents e Actions). Senza token usa
         il programma «gh» (GitHub CLI) collegato all'account quivicino.
Uso:     py -3.12 osm_bike.py [percorso/italy-latest.osm.pbf]
         senza percorso scarica il PBF da Geofabrik (circa 2 GB) nella cartella di questo script, se non c'è
         già una copia di meno di 20 ore. Con --senza-invio crea solo il file, senza caricarlo.
Aggiornamento: lo script NON si aggiorna da solo, così il codice che gira con il token cambia solo quando lo
         decide paolo. Con --aggiorna scarica da GitHub l'ultima versione, la salva al suo posto e la usa.
"""
import gzip
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

import osmium

REPO = "quivicino/Bike"
RELEASE = "dati-osm"
API = "https://api.github.com/repos/" + REPO
NOME = "bike"                      # bike.json.gz (e bike-2.json.gz, … se serve dividerlo)
PBF_URL = "https://download.geofabrik.de/europe/italy-latest.osm.pbf"
CARTELLA = os.path.dirname(os.path.abspath(__file__))
TAG_VIE = ("highway", "surface", "tracktype", "mtb:scale")
FILTRO = [("route", "mtb"), ("route", "bicycle"), ("amenity", "drinking_water"), ("amenity", "water_point"),
          ("amenity", "fountain"), ("amenity", "bicycle_repair_station"), ("shop", "bicycle"),
          ("craft", "bicycle_repair"), ("amenity", "bicycle_rental"), ("amenity", "charging_station"),
          ("tourism", "alpine_hut"), ("amenity", "restaurant"), ("amenity", "cafe"), ("amenity", "bar"),
          ("amenity", "pub"), ("agriturismo", "yes"), ("guest_house", "agritourism"), ("aerialway", "cable_car"),
          ("aerialway", "gondola"), ("aerialway", "mixed_lift"), ("aerialway", "chair_lift"), ("railway", "funicular")]
SOLO_VICINO = {"L", "W"}            # tenuti solo vicino ai percorsi
CELLA = 0.005                      # griglia per il filtro grossolano «vicino ai percorsi» (circa 550 × 400 m)
SCRIPT_URL = "https://raw.githubusercontent.com/quivicino/Bike/main/osm_bike.py"
MAX_PARTE = 150 * 1024 * 1024      # oltre questa misura (JSON non compresso) si apre una nuova parte:
                                   # Node non legge testi più lunghi di circa 500 MB


def tipo_impianto(t):
    if t.get("disused") == "yes" or t.get("abandoned") == "yes" or t.get("construction") or t.get("proposed") or \
            "progett" in (t.get("name") or "").lower():
        return None
    if t.get("railway") == "funicular" or t.get("aerialway") in ("cable_car", "gondola", "mixed_lift", "chair_lift"):
        return "F"
    return None


def tipo_punto(t):
    """Come tipoDaTag in core.js: W fontanella, A colonnina attrezzi, N negozio/officina, C ricarica, R rifugio,
    L bar/ristorante/agriturismo, F impianto a fune."""
    a = t.get("amenity")
    if a == "drinking_water" or (a == "fountain" and t.get("drinking_water") == "yes") or \
            (a == "water_point" and t.get("drinking_water") != "no"):
        return "W"
    if a == "bicycle_repair_station":
        return "A"
    if t.get("shop") == "bicycle" or t.get("craft") == "bicycle_repair" or \
            (a == "bicycle_rental" and t.get("service:bicycle:repair") == "yes"):
        return "N"
    if a == "charging_station" and t.get("bicycle") == "yes":
        return "C"
    if t.get("tourism") == "alpine_hut":
        return "R"
    if t.get("agriturismo") == "yes" or t.get("guest_house") == "agritourism" or a in ("restaurant", "cafe", "bar", "pub"):
        return "L"
    return tipo_impianto(t)


class Percorsi(osmium.SimpleHandler):
    """Primo giro: le relazioni dei percorsi in bici e le vie che servono."""

    def __init__(self):
        super().__init__()
        self.rel = []
        self.vie = set()

    def relation(self, r):
        t = r.tags
        if t.get("type") != "route" or t.get("route") not in ("mtb", "bicycle"):
            return
        membri = [(m.ref, m.role) for m in r.members if m.type == "w"]
        if not membri:
            return
        self.rel.append({"id": r.id, "tags": {k.k: k.v for k in t}, "membri": membri})
        self.vie.update(ref for ref, _ in membri)


class VieEPunti(osmium.SimpleHandler):
    """Secondo giro (con le coordinate dei nodi): geometria e tag delle vie dei percorsi, e i punti."""

    def __init__(self, vie):
        super().__init__()
        self.cercate = vie
        self.geometria = {}
        self.tag = {}
        self.punti = []

    def node(self, n):
        if not n.tags or not tipo_punto(n.tags):
            return
        self.punti.append({"type": "node", "id": n.id, "lat": round(n.location.lat, 7),
                           "lon": round(n.location.lon, 7), "tags": {k.k: k.v for k in n.tags}})

    def way(self, w):
        serve = w.id in self.cercate
        punto = bool(w.tags) and tipo_punto(w.tags)
        if not serve and not punto:
            return
        coord = []
        for nd in w.nodes:
            try:
                if nd.location.valid():
                    coord.append((round(nd.location.lat, 7), round(nd.location.lon, 7)))
            except osmium.InvalidLocationError:
                pass
        if serve and len(coord) >= 2:
            self.geometria[w.id] = coord
            tv = {k: w.tags[k] for k in TAG_VIE if k in w.tags}
            if tv:
                self.tag[w.id] = tv
        if punto == "F":
            if len(coord) >= 2:
                self.punti.append({"type": "way", "id": w.id, "tags": {k.k: k.v for k in w.tags},
                                   "geometry": [{"lat": la, "lon": lo} for la, lo in coord]})
        elif punto and coord:
            la = sum(c[0] for c in coord) / len(coord)
            lo = sum(c[1] for c in coord) / len(coord)
            self.punti.append({"type": "way", "id": w.id, "center": {"lat": round(la, 7), "lon": round(lo, 7)},
                               "tags": {k.k: k.v for k in w.tags}})


def data_osm(pbf):
    """Data dei dati OSM: dall'intestazione del PBF (Geofabrik la scrive), se no dalla data del file."""
    try:
        h = osmium.io.Reader(pbf, osmium.osm.osm_entity_bits.NOTHING).header()
        ts = h.get("osmosis_replication_timestamp")
        if ts:
            return ts
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(pbf), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prendi_pbf(argomento):
    if argomento:
        return argomento
    pbf = os.path.join(CARTELLA, "italy-latest.osm.pbf")
    if os.path.exists(pbf) and time.time() - os.path.getmtime(pbf) < 20 * 3600:
        return pbf
    print(f"Scarico {PBF_URL} …", flush=True)
    urllib.request.urlretrieve(PBF_URL, pbf + ".part")
    os.replace(pbf + ".part", pbf)
    return pbf


def scrivi(elementi, base, cartella):
    """Scrive bike.json.gz (con la lista "parti" se il file è stato diviso). Restituisce i file scritti."""
    gruppi, attuale, misura = [], [], 0
    for el in elementi:
        testo = json.dumps(el, ensure_ascii=False, separators=(",", ":"))
        if attuale and misura + len(testo) > MAX_PARTE:
            gruppi.append(attuale)
            attuale, misura = [], 0
        attuale.append(testo)
        misura += len(testo) + 1
    gruppi.append(attuale)
    nomi = [f"{NOME}.json.gz"] + [f"{NOME}-{i}.json.gz" for i in range(2, len(gruppi) + 1)]
    file = []
    for i, (nome, gruppo) in enumerate(zip(nomi, gruppi)):
        testa = {"version": 0.6, "generator": "Qui-Bike osm_bike.py", "osm3s": {"timestamp_osm_base": base}}
        if i == 0 and len(nomi) > 1:
            testa["parti"] = nomi[1:]
        percorso = os.path.join(cartella, nome)
        with gzip.open(percorso, "wt", encoding="utf-8", compresslevel=9) as f:
            f.write(json.dumps(testa, ensure_ascii=False)[:-1] + ',"elements":[\n')
            f.write(",\n".join(gruppo))
            f.write("\n]}\n")
        print(f"  {nome}: {len(gruppo)} elementi, {os.path.getsize(percorso) / 1048576:.1f} MB", flush=True)
        file.append(percorso)
    return file


def ritaglia(pbf, filtrato):
    """Piccolo PBF con gli oggetti di FILTRO e tutte le vie e i nodi a cui rimandano (con i loro tag)."""
    w = osmium.BackReferenceWriter(filtrato, ref_src=pbf, overwrite=True, remove_tags=False)
    try:
        for o in osmium.FileProcessor(pbf).with_filter(osmium.filter.TagFilter(*FILTRO)):
            w.add(o)
    finally:
        w.close()
    print(f"PBF ritagliato: {os.path.getsize(filtrato) / 1048576:.1f} MB", flush=True)


def leggi_token(argomento):
    percorso = argomento or os.path.join(CARTELLA, "token.txt")
    if not os.path.exists(percorso):
        return None
    for riga in open(percorso, encoding="utf-8-sig"):
        riga = riga.strip()
        if riga and not riga.startswith("#"):
            return riga.split("=", 1)[-1].strip().strip('"')
    return None


def github(token, metodo, url, dati=None, tipo="application/json"):
    corpo = dati if isinstance(dati, (bytes, type(None))) else json.dumps(dati).encode()
    req = urllib.request.Request(url if url.startswith("http") else API + url, data=corpo, method=metodo, headers={
        "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Qui-Bike osm_bike.py", "Content-Type": tipo})
    with urllib.request.urlopen(req, timeout=600) as r:
        testo = r.read()
    return json.loads(testo) if testo else None


def invia_con_token(token, file):
    import urllib.error
    try:
        rel = github(token, "GET", f"/releases/tags/{RELEASE}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        print(f"Creo la release {RELEASE} su {REPO} …", flush=True)
        rel = github(token, "POST", "/releases", {
            "tag_name": RELEASE, "target_commitish": "main", "name": "Dati OpenStreetMap (copia del computer)",
            "body": "File creati ogni giorno da osm_bike.py dal PBF Italia di Geofabrik. © OpenStreetMap contributors (ODbL)."})
    nomi = {os.path.basename(f) for f in file}
    for a in rel.get("assets", []):
        if a["name"] in nomi or (a["name"].startswith(NOME + "-") and a["name"].endswith(".json.gz")):
            github(token, "DELETE", f"/releases/assets/{a['id']}")
    print("Carico i file sulla release …", flush=True)
    base = rel["upload_url"].split("{")[0]
    for f in file:
        with open(f, "rb") as h:
            github(token, "POST", f"{base}?name={os.path.basename(f)}", h.read(), "application/gzip")
    print("Faccio ripartire la pubblicazione del sito …", flush=True)
    github(token, "POST", "/actions/workflows/pubblica.yml/dispatches", {"ref": "main"})


def gh(*argomenti, controlla=True):
    return subprocess.run(["gh", *argomenti], check=controlla, capture_output=True, text=True)


def invia_con_gh(file):
    if gh("release", "view", RELEASE, "-R", REPO, controlla=False).returncode != 0:
        print(f"Creo la release {RELEASE} su {REPO} …", flush=True)
        gh("release", "create", RELEASE, "-R", REPO, "--title", "Dati OpenStreetMap (copia del computer)",
           "--notes", "File creati ogni giorno da osm_bike.py dal PBF Italia di Geofabrik. © OpenStreetMap contributors (ODbL).")
    print("Carico i file sulla release …", flush=True)
    gh("release", "upload", RELEASE, *file, "-R", REPO, "--clobber")
    print("Faccio ripartire la pubblicazione del sito …", flush=True)
    gh("workflow", "run", "pubblica.yml", "-R", REPO, "--ref", "main")


def celle_percorsi(geometrie):
    """Celle della griglia (con le 8 accanto) toccate dalle vie dei percorsi, con un punto ogni circa 200 m."""
    celle = set()
    for g in geometrie:
        for (la1, lo1), (la2, lo2) in zip(g, g[1:] or g):
            passi = max(1, int(max(abs(la2 - la1), abs(lo2 - lo1)) / 0.002))
            for k in range(passi + 1):
                i = int((la1 + (la2 - la1) * k / passi) // CELLA)
                j = int((lo1 + (lo2 - lo1) * k / passi) // CELLA)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        celle.add((i + di, j + dj))
    return celle


def vicino(el, celle):
    c = el.get("center") or el
    return (int(c["lat"] // CELLA), int(c["lon"] // CELLA)) in celle


def aggiorna_script():
    """Scarica l'ultima versione dello script da GitHub; se è cambiata la salva e la lancia al posto di questa."""
    if "--aggiorna" not in sys.argv or os.environ.get("OSM_BIKE_AGGIORNATO"):
        return
    try:
        with urllib.request.urlopen(urllib.request.Request(SCRIPT_URL, headers={"User-Agent": "Qui-Bike osm_bike.py"}),
                                    timeout=60) as r:
            nuovo = r.read()
        questo = os.path.abspath(__file__)
        with open(questo, "rb") as f:
            vecchio = f.read()
        if nuovo.replace(b"\r\n", b"\n") == vecchio.replace(b"\r\n", b"\n"):
            return
        compile(nuovo, questo, "exec")     # se non è Python valido non si tocca niente
        with open(questo + ".nuovo", "wb") as f:
            f.write(nuovo)
        os.replace(questo + ".nuovo", questo)
        print("Script aggiornato all'ultima versione di GitHub: riparto con quella.", flush=True)
    except Exception as e:
        print(f"Aggiornamento dello script non riuscito ({e}): uso questa versione.", flush=True)
        return
    ambiente = dict(os.environ, OSM_BIKE_AGGIORNATO="1")
    sys.exit(subprocess.run([sys.executable, os.path.abspath(__file__), *sys.argv[1:]], env=ambiente).returncode)


def main():
    aggiorna_script()
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    pbf = prendi_pbf(argomenti[0] if argomenti else None)
    base = data_osm(pbf)
    inizio = time.time()
    print(f"PBF {pbf} (dati OSM del {base})", flush=True)

    filtrato = os.path.join(CARTELLA, NOME + "-filtrato.osm.pbf")
    ritaglia(pbf, filtrato)

    p = Percorsi()
    p.apply_file(filtrato, locations=False)
    print(f"Percorsi in bici: {len(p.rel)}, vie: {len(p.vie)}", flush=True)

    v = VieEPunti(p.vie)
    v.apply_file(filtrato, locations=True, idx="flex_mem")
    print(f"Vie trovate: {len(v.geometria)}, punti: {len(v.punti)}", flush=True)

    elementi = []
    for r in p.rel:
        membri = []
        for ref, ruolo in r["membri"]:
            m = {"type": "way", "ref": ref, "role": ruolo}
            g = v.geometria.get(ref)
            if g:
                m["geometry"] = [{"lat": la, "lon": lo} for la, lo in g]
            membri.append(m)
        elementi.append({"type": "relation", "id": r["id"], "members": membri, "tags": r["tags"]})
    elementi.extend({"type": "way", "id": i, "tags": t} for i, t in v.tag.items())
    celle = celle_percorsi(v.geometria.values())
    tenuti = [el for el in v.punti if tipo_punto(el["tags"]) not in SOLO_VICINO or vicino(el, celle)]
    print(f"Punti tenuti: {len(tenuti)} (scartati {len(v.punti) - len(tenuti)} fontanelle e locali lontani dai percorsi)", flush=True)
    elementi.extend(tenuti)

    file = scrivi(elementi, base, CARTELLA)
    print(f"Fatto in {(time.time() - inizio) / 60:.1f} minuti", flush=True)
    if "--senza-invio" not in sys.argv:
        tok = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--token=")]
        token = leggi_token(tok[0] if tok else None)
        if token:
            invia_con_token(token, file)
        else:
            invia_con_gh(file)
        print("Inviato: tra qualche minuto il sito ha i percorsi di tutta l'Italia.", flush=True)


if __name__ == "__main__":
    main()
