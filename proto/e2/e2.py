"""Moteur E2 : Spotify -> sortie virtuelle dj_in -> ce programme (D secondes d'avance) -> haut-parleurs.

Ordres v2 (ADR 0001) reçus en POST /order (extension dj-auto) ou en UDP sur 127.0.0.1:47801 (run.sh, avec
"cmd": "transition") ; validés par transitions/contrat.valider_ordre. Messages {"cmd": "track", …} d'espion.mjs en UDP.
Le programme situe le saut dans la mémoire (find_switch), recale A et B sur les grilles de Spotify (Place), essaie
la transition demandée puis ses replis (catalogue.rendre), mesure le rendu (mesures.rapport), le joue à la place du
flux et en rend compte dans /state (derniere_transition, transitions_recentes) et DJ_JOURNAL.
Écran : http://127.0.0.1:47802 ; GET /dj-catalogue.js sert spicetify/dj-catalogue.js.
Variables : DJ_WORK (boutons de l'écran), DJ_NOTES (notes d'écoute), DJ_JOURNAL (rapports JSONL, vide = coupé),
DJ_SLOW (ralenti de regain, 1,00 à 1,06, défaut 1,03 ; ADR 0003), DJ_WS (secours de l'adresse de débogage).
Usage : python3 -I proto/e2/e2.py [délai_s]   (journal sur la sortie standard)
"""
import bisect
import collections
import http.server
import importlib
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I n'ajoute pas le dossier du script au chemin d'import

import transitions  # noqa: E402

# Ordre de rechargement (ADR 0005) : chaque module ne dépend que des précédents
MODULES = ("outils", "contrat", "calage", "primitives", "voix", "mesures", "seches", "boucle", "superposees",
           "catalogue")
X = {n: importlib.import_module(f"transitions.{n}") for n in MODULES}
SR, CH = X["outils"].SR, X["outils"].CH
OrdreInvalide = X["contrat"].OrdreInvalide


def _slow(v):
    """Ralenti de regain d'après DJ_SLOW, borné à 1,00..1,06 (ADR 0003) ; valeur illisible : défaut 1,03."""
    try:
        return float(min(1.06, max(1.0, float(v))))
    except (TypeError, ValueError):
        return 1.03


D = 60.0             # avance visée (s), argument de la ligne de commande
WS = os.environ.get("DJ_WS", "")
WORK = os.environ.get("DJ_WORK", "")
NOTES = os.environ.get("DJ_NOTES", os.path.join(HERE, "..", "..", "docs", "tests", "notes-ecoute.jsonl"))
JOURNAL = os.environ.get("DJ_JOURNAL", "")
CATALOGUE_JS = os.path.join(HERE, "..", "..", "spicetify", "dj-catalogue.js")
ORIGIN = "http://127.0.0.1:47802"
# Pages autorisées à interroger le moteur et à lancer une transition : l'écran local et l'app Spicetify
ORIGINS = {ORIGIN, "https://xpui.app.spotify.com"}
URI = re.compile(r"^spotify:track:[A-Za-z0-9]{22}$")
LAT = 0.2            # latence de pacat (s) : délai entre l'écriture d'un bloc et le moment où on l'entend
GAIN_S = 16          # durée du retour du gain de B à 1 après une transition
SWITCH_S = 0.09      # délai entre l'ordre de saut et le changement dans le flux (mesuré, saut dans la playlist)
A_AVANT_S = 0.32     # le 1 de sortie de A est cherché jusqu'à 320 ms avant la fin estimée de A (LEAD = −60 ms)…
A_APRES_S = 0.03     # … et jusqu'à 30 ms après
A_CENTRE_S = 0.11    # place attendue du 1 avant la fin estimée de A : LEAD 60 + SWITCH_S 90 − marge 40 ms
SLOW = _slow(os.environ.get("DJ_SLOW", "1.03"))
BLOCK = 1024
MAX_CORPS = 65536    # corps JSON d'un POST (ordre v2 avec 2 × 120 temps : ~5 Ko), au-delà : 400
N = SR * 600         # 10 min de mémoire, en anneau
buf = np.zeros((N, CH), dtype=np.float32)
written = 0          # échantillons reçus depuis le lancement (la position dans buf est written % N)
clock = []           # (ms mur, échantillons reçus) pour relier l'heure à la mémoire
lock = threading.Lock()  # protège plan, current, last, last_resume, stream_gain, recentes
plan = []            # segments à jouer à la place du flux : (début, tableau, reprise, transition, infos, gain)
last_resume = 0      # reprise du dernier segment prévu : un segment suivant ne peut commencer avant
tracks = []          # (échantillon d'entrée, infos du morceau envoyées par espion.mjs)
track_samples = []   # les mêmes échantillons seuls, pour la recherche dichotomique
rp = 0               # position de lecture dans la mémoire (ce qui part vers les haut-parleurs)
current = None       # transition en train d'être jouée
last = None          # dernière transition jouée, gardée 20 s pour que l'écran montre B qui continue
stream_gain = None   # (gain de B, échantillon de reprise) : le flux revient à 1 en GAIN_S secondes
started = False      # la lecture a commencé (la mémoire a reçu D secondes)
seg_resume = 0       # pendant un segment : sa reprise dans la mémoire…
seg_left = 0         # … et ce qu'il en reste à jouer (0 hors segment)
slow_next = None     # prochaine tranche ralentie : (début, fin dans la mémoire, son étiré)
clock_lock = threading.Lock()  # le lecteur purge `clock` pendant que d'autres fils y cherchent une heure
spotify_paused = False  # d'après espion.mjs : le moteur se met en pause en même temps que Spotify
pause_votes = 0      # messages « en pause » de suite : un seul ne suffit pas (pause passagère pendant un saut)
last_track_t = 0.0   # heure du dernier message d'espion : sans nouvelles, la pause expire
levels = [0.0] * 16  # niveau de 16 bandes de fréquences de ce qui part vers les haut-parleurs (visualiseur)
events = collections.deque(maxlen=12)  # derniers événements notables (refus, abandons), pour l'app
recentes = collections.deque(maxlen=10)  # rapports des 10 dernières transitions, la plus récente d'abord
run_proc = None      # run.sh en cours, lancé depuis l'écran
last_request = None  # dernière transition demandée depuis l'écran, pour « Rejouer »


def _fichiers():
    return {n: os.path.getmtime(os.path.join(HERE, "transitions", f"{n}.py")) for n in MODULES}


_mtimes = _fichiers()
_reload_lock = threading.Lock()


def fresh():
    """Recharge le paquet transitions/ si un de ses fichiers a changé : régler un rendu ne demande pas de relancer
    le moteur (et d'attendre à nouveau D secondes de remplissage). Tous les modules sont rechargés hors place, dans
    l'ordre MODULES, puis basculés d'un coup ; en cas d'erreur, l'ancienne version est gardée entière."""
    global X, OrdreInvalide
    with _reload_lock:
        now = _fichiers()
        if now == _mtimes:
            return
        _mtimes.update(now)  # un fichier en erreur n'est retenté qu'à sa prochaine modification
        old = dict(X)
        new = {}
        try:
            for n in MODULES:
                name = f"transitions.{n}"
                spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "transitions", f"{n}.py"))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[name] = mod  # les modules suivants importent la nouvelle version
                setattr(transitions, n, mod)
                spec.loader.exec_module(mod)
                new[n] = mod
            X = new
            OrdreInvalide = new["contrat"].OrdreInvalide
            log("paquet transitions/ rechargé")
        except Exception as e:  # fichier à moitié sauvé, erreur de syntaxe : on garde la version qui marche
            for n, mod in old.items():
                sys.modules[f"transitions.{n}"] = mod
                setattr(transitions, n, mod)
            event("echec", f"rechargement du rendu impossible, ancienne version gardée : {e!r}")


def paused():
    """Spotify en pause, d'après au moins 2 messages d'espion de suite, le dernier datant de moins de 1,5 s
    (si espion s'arrête pendant une pause, la maquette ne doit pas rester muette pour toujours)."""
    return spotify_paused and time.time() - last_track_t < 1.5


def ramp_out(n):
    return np.linspace(1, 0, n, dtype=np.float32)[:, None]


def current_delay():
    """Avance de la lecture sur la mémoire, en échantillons, une fois jouées les transitions déjà prévues :
    pendant un segment, la position équivalente est sa reprise moins ce qu'il reste à jouer ; chaque segment
    en attente ajoute ce qu'il gagne (ou perd) d'avance."""
    if not started:
        return int(D * SR)
    pos = seg_resume - seg_left if seg_left else rp
    with lock:
        pending = sum(len(p[1]) - (p[2] - p[0]) for p in plan)
    return written - pos + pending


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def event(kind, msg):
    """Événement visible dans l'app (abandon, refus, échec) en plus du journal."""
    log(msg)
    events.append({"t": time.time(), "kind": kind, "msg": msg})


def read(a, b):
    """Copie des échantillons [a, b) de la mémoire. Erreur s'ils ne sont pas (ou plus) en mémoire."""
    a, b = int(a), int(b)
    if not (max(0, written - N) <= a <= b <= written):
        raise ValueError(f"lecture hors mémoire ({a}..{b}, reçus {written})")
    i = a % N
    if i + b - a <= N:
        return buf[i:i + b - a].copy()
    return np.concatenate([buf[i:], buf[:i + b - a - N]])


class Memoire:
    """Ce que les rendus (transitions/) voient de la mémoire : read, wait, log."""
    read = staticmethod(read)
    log = staticmethod(log)

    @staticmethod
    def wait(n):
        deadline = time.time() + 60  # dj_in muet trop longtemps : le rendu abandonne au lieu d'attendre toujours
        while written < n:
            if paused():
                deadline = time.time() + 60  # une pause de Spotify ne compte pas
            elif time.time() > deadline:
                raise ValueError("son attendu jamais reçu")
            time.sleep(0.02)


def sample_at(t_wall):
    """Échantillon de la mémoire reçu à l'heure t_wall (ms), interpolé entre deux blocs reçus (un bloc dure
    23 ms : sans interpolation, l'erreur atteint un bloc)."""
    with clock_lock:
        if not clock:
            return 0
        i = bisect.bisect_left(clock, (t_wall,))
        if i == 0 or i >= len(clock):
            return clock[min(i, len(clock) - 1)][1]
        (t0, w0), (t1, w1) = clock[i - 1], clock[i]
    return int(w0 + (w1 - w0) * (t_wall - t0) / max(t1 - t0, 1e-3))


def track_at(sample):
    """Morceau joué à cet endroit de la mémoire, et sa position en secondes."""
    i = bisect.bisect_right(track_samples, sample) - 1
    if i < 0:
        return None
    s, info = tracks[i]
    pos = info["pos_ms"] / 1000 + (0 if info.get("paused") else (sample - s) / SR)
    return {"name": info["name"], "artist": info["artist"], "uri": info.get("uri"), "pos_s": pos,
            "dur_s": info["dur_ms"] / 1000}


def spotify_ws():
    """Adresse de débogage de la page de Spotify, relue à chaque fois (elle change au redémarrage)."""
    import urllib.request
    try:
        pages = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=2))
        return next(p["webSocketDebuggerUrl"] for p in pages if p.get("url", "").startswith("https://xpui.app.spotify.com/index"))
    except Exception:
        return WS


_BANDS = np.geomspace(40, 16000, 17)


def update_levels(block):
    """Niveaux de 16 bandes (40 Hz à 16 kHz) d'un bloc qui part vers les haut-parleurs, lissés."""
    mono = block.mean(axis=1)
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))
    f = np.fft.rfftfreq(len(mono), 1 / SR)
    for i in range(16):
        sel = spec[(f >= _BANDS[i]) & (f < _BANDS[i + 1])]
        db = 20 * np.log10(sel.mean() + 1e-9) if len(sel) else -120
        v = min(1.0, max(0.0, (db + 10) / 50))  # −10 à +40 dB ramenés sur 0..1
        levels[i] = max(v, levels[i] * 0.85)      # retombée douce


def state():
    with lock:
        p, cur_t, last_t = (plan[0] if plan else None), current, last
        recent = list(recentes)
    heard = track_at(rp - int(LAT * SR))
    if cur_t:
        heard = {**(heard or {}), "name": cur_t["from"], "artist": "transition en cours", "pos_s": None, "dur_s": None}
    nxt = None
    if p:
        to = track_at(p[2] + 3 * SR)  # le nom de B arrive après son son : on le relit 3 s après la reprise
        nxt = {**p[4], "to": to and to["name"], "to_uri": to and to.get("uri"), "transition": p[3],
               "in_s": (p[0] - rp) / SR}
    cur = {**cur_t, "elapsed_s": time.time() - cur_t["t0"]} if cur_t else None
    done = {**last_t, "elapsed_s": time.time() - last_t["t0"]} if last_t and time.time() - last_t["t_end"] < 20 else None
    busy = run_proc is not None and run_proc.poll() is None
    return {"heard": heard, "spotify": track_at(written), "delay_s": current_delay() / SR, "target_s": D,
            "next": nxt, "current": cur, "last": done, "busy": busy, "last_request": last_request,
            "can_run": bool(WORK), "levels": [round(v, 3) for v in levels], "events": list(events),
            "notes": notes_avg, "ralenti": SLOW, "derniere_transition": recent[0] if recent else None,
            "transitions_recentes": recent}


def launch(req):
    """Lance run.sh pour la paire et la transition demandées depuis l'écran (POST /run v2) ; une seule à la fois."""
    global run_proc, last_request
    if "mode" in req:
        return 400, "champ « mode » (contrat v1) refusé : utiliser « transition »"
    tr, a, b = req.get("transition", "auto"), req.get("a", ""), req.get("b", "")
    # les uri et la transition finissent dans du JS exécuté dans Spotify (run.sh) : format strict
    if not isinstance(tr, str) or tr not in {"auto", *X["contrat"].IDS} or not (
            isinstance(a, str) and isinstance(b, str) and URI.match(a) and URI.match(b)):
        return 400, "demande invalide"
    ws = spotify_ws()
    if not (ws and WORK):
        return 503, "Spotify n'est pas en mode débogage, ou moteur lancé sans DJ_WORK"
    if run_proc is not None and run_proc.poll() is None:
        return 409, "une transition est déjà en préparation"
    if plan or current:
        return 409, "une transition est déjà prévue ou en cours"
    if tr == "auto":  # « Rejouer » doit refaire le même choix : on oublie la transition précédente
        try:
            os.remove(os.path.join(WORK, "derniere-transition"))
        except FileNotFoundError:
            pass
    last_request = {"transition": tr, "a": a, "b": b, "name": str(req.get("name", ""))[:200]}
    run_proc = subprocess.Popen(["bash", os.path.join(HERE, "run.sh"), ws, tr, WORK, a, b],
                                stdout=open(os.path.join(WORK, "run.out"), "w"), stderr=subprocess.STDOUT)
    log(f"écran : transition demandée ({tr}, {last_request['name']})")
    return 202, "lancée"


def note_averages():
    """Note moyenne par transition jouée d'après le journal NOTES (affichage seulement, H8) ; une transition notée
    deux fois compte pour sa dernière note. Les lignes v1 (sans rapport) sont ignorées."""
    last_notes = {}
    try:
        with open(NOTES) as f:
            for line in f:
                try:
                    e = json.loads(line)
                    tr = e["rapport"]["transition_jouee"]
                    if tr:
                        last_notes[e["id"]] = (tr, int(e["note"]))
                except (ValueError, KeyError, TypeError):
                    continue
    except FileNotFoundError:
        return {}
    by_tr = collections.defaultdict(list)
    for tr, n in last_notes.values():
        by_tr[tr].append(n)
    return {t: round(sum(v) / len(v), 2) for t, v in by_tr.items()}


notes_avg = note_averages()


def rate(req):
    """Note d'écoute v2 (ADR 0001) : la transition est retrouvée par `id` parmi les 10 récentes (écoute à l'aveugle)
    ; ligne ajoutée à NOTES avec le rapport complet."""
    global notes_avg
    note, etiq, com = req.get("note"), req.get("etiquettes", []), req.get("commentaire", "")
    if isinstance(note, bool) or not isinstance(note, int) or not 1 <= note <= 5:
        return 400, "note invalide (1 à 5)"
    if not isinstance(etiq, list) or any(e not in X["contrat"].ETIQUETTES for e in etiq):
        return 400, "étiquette inconnue"
    if not isinstance(com, str) or len(com) > 1000:
        return 400, "commentaire invalide"
    with lock:
        rap = next((r for r in recentes if r["id"] == req.get("id")), None)
    if rap is None:
        return 409, "transition inconnue (id absent des 10 dernières)"
    entry = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "id": rap["id"], "note": note, "etiquettes": sorted(set(etiq)),
             "commentaire": com, "rapport": rap}
    try:
        with open(NOTES, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        event("echec", f"note non enregistrée : {e!r}")
        return 500, "note non enregistrée"
    notes_avg = note_averages()
    log(f"note {note}/5 : {rap['transition_jouee']} ({rap['id']})")
    return 201, "notée"


def accept_order(req, demarrer=True):
    """POST /order et UDP : (code HTTP, corps). 202 : ordre valide, préparé dans un fil ; 400 : invalide (dont
    ancien `mode`) ; 409 : test manuel en cours, ordre trop tard ou qui chevauche la transition précédente."""
    req = dict(req)
    req.pop("cmd", None)  # run.sh distingue ses ordres des messages d'espion par "cmd": "transition"
    try:
        o = X["contrat"].valider_ordre(req)
    except ValueError as e:  # OrdreInvalide
        return 400, {"message": str(e)}
    if o.manuel and run_proc is not None and run_proc.poll() is None:
        return 409, {"message": "test manuel en cours : pas de rattrapage"}  # le saut vient de run.sh
    why = conflit(o)
    if why:
        return 409, {"message": why}
    if demarrer:
        threading.Thread(target=handle_order, args=(o,), daemon=True).start()
    return 202, {"ok": True, "id": o.id}


def conflit(o):
    """Raison de refuser l'ordre tout de suite (409), ou None : la lecture a déjà dépassé le début du segment, ou
    une transition prévue reprend après lui."""
    if not started or not clock or o.t_wall > clock[-1][0]:
        return None
    idx = sample_at(o.t_wall)
    debut = idx - int((o.bars + 1) * o.a.bar_s * SR)
    if debut < rp + int(0.5 * SR):
        return f"ordre trop tard : la lecture a dépassé le saut ({(rp - debut) / SR:+.1f} s)"
    with lock:
        if debut < last_resume:
            return "une transition chevauche déjà ce moment"
    return None


class Screen(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        """Autorise l'app Spicetify (page de Spotify) à lire l'état et lancer une transition."""
        origin = self.headers.get("Origin")
        if origin in ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")

    def _send(self, code, body, kind):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # pré-vérification du navigateur avant un POST en JSON
        self._send(204 if self.headers.get("Origin") in ORIGINS else 403, b"", "text/plain")

    def do_GET(self):
        if self.path.startswith("/state"):
            self._send(200, json.dumps(state()).encode(), "application/json")
        elif self.path.split("?")[0] == "/dj-catalogue.js":
            try:
                with open(CATALOGUE_JS, "rb") as f:
                    self._send(200, f.read(), "text/javascript; charset=utf-8")
            except OSError:
                self._send(404, b"// dj-catalogue.js introuvable", "text/javascript; charset=utf-8")
        else:
            with open(os.path.join(HERE, "ecran.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")

    def do_POST(self):
        # Seuls l'écran et l'app Spicetify peuvent lancer une transition : une autre page web ouverte dans le
        # navigateur pourrait sinon envoyer cette demande au moteur.
        body = None
        if self.path not in ("/run", "/order", "/rating") or self.headers.get("Origin") not in ORIGINS:
            code, msg = 403, "refusé"
        else:
            try:
                n = int(self.headers.get("Content-Length", 0))
                if not 0 <= n <= MAX_CORPS:  # négatif : rfile.read(-1) bloquerait le fil jusqu'à la fermeture
                    raise ValueError("Content-Length hors bornes")
                req = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(req, dict):
                    raise ValueError
                if self.path == "/run":
                    code, msg = launch(req)
                elif self.path == "/rating":
                    code, msg = rate(req)
                else:
                    code, body = accept_order(req)
            except (ValueError, json.JSONDecodeError):
                code, msg = 400, "demande invalide"
        out = body if body is not None else {"message": msg}
        self._send(code, json.dumps(out, ensure_ascii=False).encode(), "application/json")

    def log_message(self, *a):
        pass


def _trim_pause_silence():
    """La pause n'est confirmée qu'après 2 messages d'espion (250-500 ms) : le silence reçu entre-temps est
    retiré de la fin de la mémoire, sinon il s'entendrait une minute plus tard."""
    global written
    n = 0
    while n < SR and written - n - BLOCK > rp + SR and np.abs(read(written - n - BLOCK, written - n)).max() < 1e-4:
        n += BLOCK
    if n:
        written -= n
        with clock_lock:
            while clock and clock[-1][1] > written:
                clock.pop()


def reader():
    """Lit dj_in en continu ; relance parec s'il s'arrête (PipeWire redémarré), sinon la maquette se tairait."""
    global written
    while True:
        p = subprocess.Popen(["parec", "-d", "dj_in.monitor", "--format=float32le", f"--rate={SR}",
                              f"--channels={CH}", "--latency-msec=10"], stdout=subprocess.PIPE)
        trimmed = False
        while True:
            raw = p.stdout.read(BLOCK * CH * 4)
            if not raw:
                break
            x = np.frombuffer(raw, dtype=np.float32).reshape(-1, CH)
            if paused():
                if not trimmed:
                    _trim_pause_silence()
                    trimmed = True
                if np.abs(x).max() < 1e-4:
                    continue  # pause : le silence n'entre pas en mémoire, la reprise se raccorde sans trou
            else:
                trimmed = False
            i = written % N
            k = min(len(x), N - i)
            buf[i:i + k] = x[:k]
            buf[:len(x) - k] = x[k:]
            written += len(x)
            with clock_lock:
                clock.append((time.time() * 1000, written))
                if len(clock) > 40000:  # ~15 min de repères : on garde ceux de la mémoire
                    del clock[:10000]
        event("echec", "lecture de dj_in interrompue : relance dans 1 s")
        time.sleep(1)


def _sink_inputs():
    """(numéro, sortie, nom d'appli) de chaque flux audio, d'après pactl."""
    out = subprocess.run(["pactl", "-f", "json", "list", "sink-inputs"], capture_output=True, text=True).stdout
    return [(s["index"], s["sink"], s["properties"].get("application.name", "")) for s in json.loads(out or "[]")]


def keep_routing():
    """Toutes les 2 s : Spotify doit entrer dans dj_in, et notre sortie suivre l'appareil par défaut.
    Sans ça, brancher un casque Bluetooth y bascule Spotify, qui contourne alors la maquette."""
    while True:
        try:
            sinks = json.loads(subprocess.run(["pactl", "-f", "json", "list", "short", "sinks"],
                                              capture_output=True, text=True).stdout or "[]")
            by_name = {s["name"]: s["index"] for s in sinks}
            default = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True).stdout.strip()
            if default == "dj_in":  # ne jamais jouer dans notre propre entrée
                default = next((n for n in by_name if n != "dj_in"), default)
            for idx, sink, app in _sink_inputs():
                if app == "Spotify" and sink != by_name.get("dj_in"):
                    subprocess.run(["pactl", "move-sink-input", str(idx), "dj_in"])
                    log("routage : Spotify ramené dans dj_in")
                if app == "dj-e2" and default in by_name and sink != by_name[default]:
                    subprocess.run(["pactl", "move-sink-input", str(idx), default])
                    log(f"routage : sortie de la maquette déplacée vers {default}")
        except Exception as e:  # le routage ne doit jamais arrêter la lecture
            log("routage :", repr(e))
        time.sleep(2)


def _longest_silence(a, b):
    """(début, fin) de la plus longue suite de quasi-zéros de la mémoire entre a et b, ou None sous 2 ms."""
    silent = np.abs(read(a, b)).max(axis=1) < 1e-4
    best, cur, best_end = 0, 0, 0
    for i, s in enumerate(silent):
        cur = cur + 1 if s else 0
        if cur > best:
            best, best_end = cur, i + 1
    return (a + best_end - best, a + best_end) if best >= int(0.002 * SR) else None


def _manual_window(o, idx):
    """Pour un changement non prévu : l'heure de l'événement de Spotify est approximative, mais espion a vu
    l'uri changer entre deux messages (250 ms) ; on cherche entre les deux, avec 200 ms de marge."""
    new = [i for i, (n, info) in enumerate(tracks) if info.get("uri") == o.to_uri and n > idx - 5 * SR]
    if new and new[0] > 0:
        return tracks[new[0] - 1][0] - int(0.2 * SR), tracks[new[0]][0] + int(0.2 * SR)
    return idx - int(0.5 * SR), idx + int(0.4 * SR)


def find_switch(o):
    """(fin de A, début de B, marge sûre) dans la mémoire, pour un Ordre.
    - Saut vers un morceau seul (run.sh) : silence numérique (zéros exacts) ; on prend la plus longue suite de
      quasi-zéros entre -50 et +400 ms de l'ordre, une fois ce son reçu.
    - Saut dans la playlist (`gapless`) : aucun trou ni clic exploitable ; le changement tombe SWITCH_S après
      l'ordre, avec une marge pour ne jamais prendre de B dans A. Si B commence par son propre silence près de cette
      heure, son début est exact.
    - Changement non prévu (`manuel`) : fenêtre donnée par espion."""
    deadline = time.time() + 10
    while not clock or clock[-1][0] < o.t_wall:
        if time.time() > deadline:  # plus rien n'arrive de dj_in : l'ordre ne peut pas être situé
            raise ValueError("aucun son reçu depuis l'ordre")
        time.sleep(0.02)
    idx = sample_at(o.t_wall)
    a, b = _manual_window(o, idx) if o.manuel else (idx - int(0.05 * SR), idx + int(0.4 * SR))
    Memoire.wait(b + int(0.05 * SR))
    est = (a + b) // 2 if o.manuel else idx + int(SWITCH_S * SR)
    sil = _longest_silence(a, b)
    if sil and not o.gapless:
        return (*sil, 0)
    if sil and abs(sil[0] - est) < int(0.06 * SR):
        log("saut dans la playlist : B commence par un silence, son début est exact")
        return sil[0], sil[0], 0
    if o.manuel:  # fenêtre large : A s'arrête au début (côté sûr), B part du milieu
        log("changement à la main sans silence : fin de A au début de la fenêtre d'espion")
        return a, est, 0
    log("changement sans silence : placé à l'heure de l'ordre")
    # A est valable jusqu'au début estimé de B : marge de 20 ms pour son 1 (essai direct 13 : à 0, un 1 trouvé 4 ms
    # après la fin estimée de A faisait reculer d'une mesure)
    return est - int(0.04 * SR), est - int(0.02 * SR), int(0.02 * SR)


def fenetre_un(beat_s):
    """(avant, après) en s : fenêtre où chercher le 1 de sortie de A autour de sa fin estimée. [−A_AVANT_S ;
    +A_APRES_S] tant qu'elle tient dans 0,85 temps (deux temps n'y tiennent pas) ; au-delà (≳ 150 BPM), elle est
    raccourcie à 0,85 temps et recentrée sur la place attendue du 1 (A_CENTRE_S avant la fin estimée), sans sortir de
    [−A_AVANT_S ; +A_APRES_S]. Avant (QA de l'essai 13) : seul le côté « avant » rétrécissait, et au-delà de ~185 BPM
    la fenêtre ne couvrait plus un saut tardif (60 + 90 ± 100 ms après le 1)."""
    w = min(A_AVANT_S + A_APRES_S, 0.85 * beat_s)
    c = min(max(A_CENTRE_S, w / 2 - A_APRES_S), A_AVANT_S - w / 2)
    return c + w / 2, w / 2 - c


def placer(o, end_a, start_b, ahead):
    """Place de A et B dans la mémoire (contrat.Place). Avec une grille de Spotify, la fin de A est posée sur le
    premier temps de la mesure de sortie et le début de B sur son temps d'entrée (grid_lag : toutes les attaques, pas
    la plus forte) ; sans grille, ou si elle ne s'accorde pas au son (netteté < 1,5), recalage sur les grosses
    caisses (grid_end) et netteté de la pulsation."""
    K = X["calage"]
    bar_a, bar_b = int(round(o.a.bar_s * SR)), int(round(o.b.bar_s * SR))
    beats_a = beats_b = None
    na = nb = 0.0
    shift, how = 0, "grosses caisses"
    beats_av = [t for t in o.a.beats if t <= 0.05]  # après la sortie, la mémoire contient B : on l'ignore
    if len(beats_av) >= 4:
        # Le 1 de sortie est avant le saut (dj-auto saute après lui, LEAD < 0) : recherche dans
        # [end_a − A_AVANT_S ; end_a + A_APRES_S], fenêtre plus courte qu'un temps (sinon deux temps y tiennent).
        # Essai direct 13 : à ±150 ms autour de end_a, avec les temps d'après la sortie calés sur les attaques de B,
        # le moteur reculait d'une mesure entière dans 10 essais sur 23.
        av, ap = fenetre_un(o.a.bar_s / 4)
        mi = (av - ap) / 2
        lag, st = K.grid_lag(Memoire, end_a - int(mi * SR), beats_av, max_ms=(av + ap) / 2 * 1000)
        lag -= int(mi * SR)
        if st >= K.NETTETE_MIN:
            lag_a = lag if lag <= ahead else lag - bar_a  # premier temps au-delà du raccord : la mesure d'avant
            beats_a = np.round(end_a + lag + np.asarray(o.a.beats) * SR).astype(np.int64)
            end_a, shift, na, how = end_a + lag_a, lag_a, st, "grille de Spotify"
    if beats_a is None:
        end_a, shift = K.grid_end(Memoire, end_a, bar_a / 4, ahead)
        na = K.nettete_pulsation(Memoire, end_a - 4 * bar_a, end_a, bar_a / 4)
    lag_b = None
    if o.b.beats:
        lag, st = K.grid_lag(Memoire, start_b, o.b.beats)
        if st >= K.NETTETE_MIN:
            lag_b = lag
            beats_b = np.round(start_b + lag + np.asarray(o.b.beats) * SR).astype(np.int64)
            start_b, nb = start_b + lag, st
    if beats_b is None:
        nb = K.nettete_pulsation(Memoire, start_b, start_b + 4 * bar_b, bar_b / 4)
    log(f"changement repéré : fin de A à {end_a} (recalée de {shift / SR * 1000:+.0f} ms, {how}, netteté {na:.1f}), "
        f"début de B à {start_b}{f' (grille de Spotify, {lag_b / SR * 1000:+.0f} ms)' if lag_b is not None else ''}"
        f", netteté {nb:.1f}")
    return X["contrat"].Place(fin_a=int(end_a), debut_b=int(start_b), bar_a=bar_a, bar_b=bar_b, beats_a=beats_a,
                              beats_b=beats_b, nettete_a=float(na), nettete_b=float(nb))


def prepare(o, ctx):
    """Situe le saut, place A et B, puis rend la transition par l'échelle de repli (catalogue.rendre).
    `ctx` reçoit la Place (pour le secours) et les modules utilisés. Rend (Rendu, replis au rendu, mesures)."""
    fresh()
    mods = X  # les modules du rendu en cours, même s'ils sont rechargés entre-temps
    ctx["mods"] = mods
    end_a, start_b, ahead = find_switch(o)
    if o.manuel:
        cancel_after(end_a)
    p = placer(o, end_a, start_b, ahead)
    ctx["place"] = p
    r, replis = mods["catalogue"].rendre(Memoire, o, p, avance=current_delay())
    return r, replis, mods["mesures"].rapport(r, p)


def control():
    global spotify_paused, pause_votes, last_track_t
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 47801))
    while True:
        try:
            o = json.loads(s.recv(65536))
            if not isinstance(o, dict):
                raise ValueError("objet JSON attendu")
            if o.get("cmd") == "track":
                pause_votes = pause_votes + 1 if o.get("paused") else 0
                spotify_paused, last_track_t = pause_votes >= 2, time.time()
                n = sample_at(o["t_wall"])
                if not tracks or tracks[-1][0] < n:
                    tracks.append((n, o))
                    track_samples.append(n)
                continue
            code, body = accept_order(o)
            if code != 202:
                event("refus", f"ordre UDP refusé ({code}) : {body['message']}")
        except Exception as e:  # un datagramme invalide ne doit pas couper les ordres suivants
            log("UDP :", repr(e))


def schedule(o, r, p, margin):
    """Programme un segment rendu ; rend None, ou la raison pour laquelle il ne peut pas être joué."""
    global last_resume
    frm = track_at(r.debut)
    info = {"id": o.id, "transition": r.transition, "from": frm and frm["name"], "from_uri": frm and frm.get("uri"),
            "bar_s": o.a.bar_s, "dur_s": max(len(r.seg) / SR, 0.01), "raison": o.raison, "resume": r.reprise,
            "gain": round(r.gain, 2),
            # positions dans les morceaux, pour les cercles de l'app : sortie de A, durée réellement jouée de A
            # dans le segment, point d'entrée dans B
            "sortieA": o.a.point_s, "real_s": max(0, p.fin_a - r.debut) / SR, "entreeB": o.b.point_s}
    with lock:
        if r.debut < rp + margin:
            return f"{r.transition} prête trop tard ({(rp - r.debut) / SR:+.1f} s)"
        if r.debut < last_resume:
            return f"{r.transition} chevaucherait la transition précédente"
        plan.append((r.debut, r.seg, r.reprise, r.transition, info, r.gain))
        plan.sort(key=lambda x: x[0])
        last_resume = max(last_resume, r.reprise)
    log(f"transition prête : {r.transition}, {len(r.seg) / SR:.2f} s de segment, "
        f"avance après {current_delay() / SR:.1f} s")
    return None


def rapport_vide(o, avance_avant):
    """Squelette du rapport de l'ADR 0001."""
    return {"id": o.id, "t": time.strftime("%Y-%m-%d %H:%M:%S"),
            "a": {"uri": o.a.uri, "nom": None, "sortie_s": o.a.point_s, "jamais_entendu_s": o.a.perdu_s},
            "b": {"uri": o.b.uri or o.to_uri, "nom": None, "entree_s": o.b.point_s, "entree": o.b.entree,
                  "saute_s": o.b.perdu_s},
            "transition_demandee": o.choisie, "transition_jouee": None, "issue": "abandon",
            "replis": list(o.replis_plan), "mesures": None, "avance_avant_s": round(avance_avant / SR, 2),
            "avance_apres_s": None, "rendu_s": None, "marge_s": None, "ralenti": SLOW, "raison": o.raison}


def enregistrer(rap):
    """Rapport ajouté aux récentes (/state) et au journal DJ_JOURNAL s'il est demandé."""
    with lock:
        recentes.appendleft(rap)
    if JOURNAL:
        try:
            with open(JOURNAL, "a") as f:
                f.write(json.dumps(rap, ensure_ascii=False) + "\n")
        except OSError as e:
            event("echec", f"journal DJ_JOURNAL inaccessible : {e!r}")


def handle_order(o):
    """Prépare puis programme une transition. Spotify a déjà sauté : si toute l'échelle échoue ou si le rendu est
    prêt trop tard, un secours remplace la coupe sèche, tant que la lecture n'a pas atteint le changement. Chaque
    ordre laisse un rapport (issue jouee, secours ou abandon)."""
    log(f"ordre reçu : {o.id} {o.transition} (choisie {o.choisie}, replis {list(o.replis)})")
    ctx = {}
    rap = rapport_vide(o, current_delay())
    t0 = time.time()
    why = None
    try:
        r, replis, mes = prepare(o, ctx)
        rap["replis"] += replis
        rap["rendu_s"] = round(time.time() - t0, 2)
        why = schedule(o, r, ctx["place"], int(0.5 * SR))
        if why is None:
            rap.update(transition_jouee=r.transition, issue="jouee", mesures=mes, marge_s=round((r.debut - rp) / SR, 2))
    except Exception as e:  # le moteur doit survivre à un ordre raté
        rap["replis"] += getattr(e, "replis", [])
        why = f"échec de préparation : {e}" if type(e).__name__ == "Refus" else f"échec de préparation : {e!r}"
    if why is not None:
        if "place" not in ctx:
            event("echec", f"{why} : transition abandonnée")
        else:
            try:
                r = ctx["mods"]["boucle"].secours(Memoire, o, ctx["place"])
                why2 = schedule(o, r, ctx["place"], int(0.15 * SR))
                if why2 is None:
                    rap.update(transition_jouee="secours", issue="secours", marge_s=round((r.debut - rp) / SR, 2))
                    event("abandon", f"{why} : secours à la place")
                else:
                    event("abandon", f"{why} : transition abandonnée ({why2})")
            except Exception as e:
                event("echec", f"{why} ; secours impossible : {e!r}")
    p = ctx.get("place")
    if p is not None:
        na, nb = track_at(p.fin_a - SR), track_at(p.debut_b + 3 * SR)
        rap["a"]["nom"] = na and na["name"]
        rap["b"]["nom"] = nb and nb["name"]
    rap["avance_apres_s"] = round(current_delay() / SR, 2)
    enregistrer(rap)


def cancel_after(sample):
    """Un changement de morceau à la main à `sample` rend fausse toute transition prévue qui lit du son
    au-delà (elle prendrait le morceau suivant pour le drop de B) : on l'annule avant de rattraper."""
    global last_resume
    with lock:
        kept = [p for p in plan if p[2] <= sample]
        dropped = len(plan) - len(kept)
        plan[:] = kept
        last_resume = max([p[2] for p in kept] + [rp if not seg_left else seg_resume])
    if dropped:
        event("abandon", "morceau changé pendant la montée de B : transition prévue annulée, rattrapage à la place")


class Sortie:
    """pacat vers les haut-parleurs, relancé s'il meurt (sinon tout le programme s'arrêterait)."""

    def __init__(self):
        self._open()

    def _open(self):
        self.p = subprocess.Popen(["pacat", "--playback", "--format=float32le", f"--rate={SR}", f"--channels={CH}",
                                   f"--latency-msec={int(LAT * 1000)}", "--client-name=dj-e2"], stdin=subprocess.PIPE)

    def write(self, x):
        try:
            self.p.stdin.write(np.ascontiguousarray(x, dtype=np.float32).tobytes())
        except (BrokenPipeError, OSError):
            event("echec", "sortie son perdue : pacat relancé")
            self._open()


def ramp_in(n):
    return np.linspace(0, 1, n, dtype=np.float32)[:, None]


def slower():
    """Regain d'avance imperceptible : chaque superposition en consomme T mesures. Entre les transitions, tant que
    l'avance est sous la cible, la musique est jouée SLOW fois plus lentement (DJ_SLOW, ×1,03 par défaut, ADR 0003),
    sans changer la hauteur (rubberband), par tranches de 8 s raccordées au flux par des fondus de 15 ms."""
    global slow_next
    ctx, xf, span = int(0.3 * SR), int(0.015 * SR), 8 * SR
    while True:
        time.sleep(0.2)
        if SLOW <= 1.0:  # ralenti coupé
            continue
        try:
            if (not started or paused() or slow_next is not None or seg_left or stream_gain
                    or current_delay() > D * SR - SR // 2):
                continue
            s = rp + 2 * SR
            e = s + span
            with lock:
                nxt = plan[0][0] if plan else None
            if (nxt is not None and e + SR > nxt) or e + ctx > written:
                continue
            y = X["outils"].rubberband(read(s - ctx, e + ctx), ["-t", f"{SLOW}"])
            a = int(round(ctx * SLOW))
            core = y[a:a + int(round(span * SLOW))].copy()
            core[:xf] = read(s, s + xf) * ramp_out(xf) + core[:xf] * ramp_in(xf)
            core[-xf:] = core[-xf:] * ramp_out(xf) + read(e - xf, e) * ramp_in(xf)
            with lock:
                if rp < s - BLOCK and (not plan or plan[0][0] >= e + SR // 2):
                    slow_next = (s, e, core.astype(np.float32))
        except Exception as e:  # le ralenti ne doit jamais arrêter la lecture
            log("ralenti :", repr(e))
            time.sleep(2)


def writer():
    global rp, current, last, stream_gain, started, seg_resume, seg_left, slow_next
    out = Sortie()
    while written < D * SR:
        time.sleep(0.01)
    rp = written - int(D * SR)
    started = True
    log(f"lecture démarrée avec {D:.0f} s d'avance")
    out_gain = 1.0  # 0 pendant une pause de Spotify, avec un court fondu à l'entrée et à la sortie
    while True:
        with lock:
            p = plan[0] if plan else None
        if p and rp >= p[0]:
            _, seg, resume, preset, info, g = p
            to = track_at(resume + 3 * SR)
            with lock:
                plan.pop(0)
                current = {**info, "to": to and to["name"], "to_uri": to and to.get("uri"), "transition": preset,
                           "t0": time.time() + LAT}
            seg_resume, seg_left = resume, len(seg)
            k = 0
            while k < len(seg):  # par blocs, pour que l'écran suive la progression
                if paused():  # pause pendant la transition : fondu de sortie, silence, fondu d'entrée au même endroit
                    n = min(256, len(seg) - k)
                    out.write(seg[k:k + n] * ramp_out(n))
                    k += n
                    t_pause = time.time()
                    while paused():
                        out.write(np.zeros((BLOCK, CH), np.float32))
                    with lock:
                        current["t0"] += time.time() - t_pause  # l'aiguille de l'app ne dérive pas
                    n = min(256, len(seg) - k)
                    out.write(seg[k:k + n] * ramp_in(n))
                    k += n
                    continue
                block = seg[k:k + BLOCK]
                out.write(block)
                update_levels(block)
                k += len(block)
                seg_left = len(seg) - k
            with lock:
                last = {**current, "t_end": current["t0"] + len(seg) / SR}
                current = None
                stream_gain = (g, resume) if abs(g - 1) > 0.01 else None
            log(f"segment joué ({len(seg) / SR:.2f} s), reprise du flux, avance restante {(written - resume) / SR:.1f} s")
            rp = resume
            seg_left = 0
            continue
        target = 0.0 if paused() else 1.0
        if target == out_gain == 0.0:  # en pause : du silence, la position de lecture ne bouge pas
            out.write(np.zeros((BLOCK, CH), np.float32))
            continue
        with lock:
            sn = slow_next
        if sn and rp >= sn[0]:
            with lock:
                slow_next = None
            if rp == sn[0] and not (p and p[0] < sn[1]) and not paused():
                for k in range(0, len(sn[2]), BLOCK):  # tranche jouée 6 % plus lentement : l'avance remonte
                    out.write(sn[2][k:k + BLOCK])
                    update_levels(sn[2][k:k + BLOCK])
                rp = sn[1]
                continue
        while written - rp < BLOCK:
            time.sleep(0.005)
        bound = min([q for q in (p and p[0], sn and sn[0]) if q and q > rp], default=rp + BLOCK)
        n = min(BLOCK, bound - rp)
        x = read(rp, rp + n)
        if target != out_gain:
            x = (x * np.linspace(out_gain, target, n, dtype=np.float32)[:, None]).astype(np.float32)
            out_gain = target
        if stream_gain:  # B revient à son niveau propre peu à peu après la transition (gain ≤ 1 : pas d'écrêtage)
            g, at = stream_gain
            t = (rp - at + np.arange(n)) / (GAIN_S * SR)
            x = (x * (1 + (g - 1) * np.clip(1 - t, 0, 1))[:, None]).astype(np.float32)
            if t[-1] >= 1:
                stream_gain = None
        out.write(x)
        if n >= 256:
            update_levels(x)
        rp += n


def main():
    global D
    D = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    threading.Thread(target=reader, daemon=True).start()
    threading.Thread(target=control, daemon=True).start()
    threading.Thread(target=keep_routing, daemon=True).start()
    threading.Thread(target=slower, daemon=True).start()
    screen = http.server.ThreadingHTTPServer(("127.0.0.1", 47802), Screen)
    threading.Thread(target=screen.serve_forever, daemon=True).start()
    log(f"écran sur http://127.0.0.1:47802 (ralenti ×{SLOW:.2f})")
    writer()


if __name__ == "__main__":
    main()
