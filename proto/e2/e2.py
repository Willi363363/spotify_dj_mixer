"""Maquette E2 : Spotify -> sortie virtuelle dj_in -> ce programme (D secondes d'avance) -> haut-parleurs.

Ordres reçus en UDP sur 127.0.0.1:47801 (run.sh) ou en POST /order (extension dj-auto), JSON :
  {"cmd": "transition", "mode": <préréglage de recettes.py>, "t_wall": <ms de l'ordre de saut donné à Spotify>,
   "bar_s": <mesure de A>, "bar_b_s": <mesure de B>, "ratio": <tempo A / tempo B>, "pre_s": <avance de B>,
   "gapless": <saut dans la playlist, sans silence>, "manuel": <changement de morceau non prévu>, "raison": ...}
  {"cmd": "track", ...}  infos de morceau envoyées par espion.mjs (écran, pause).
Le programme situe le changement dans la mémoire (silence numérique s'il y en a, sinon l'heure de l'ordre),
recale la fin de A sur ses temps, fait rendre la recette par rendu.py, puis la joue à la place du flux.
Écran : http://127.0.0.1:47802
Usage : python3 -I proto/e2/e2.py [délai_s]   (journal sur la sortie standard)
"""
import bisect
import collections
import http.server
import importlib
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

import recettes  # noqa: E402
import rendu  # noqa: E402
from recettes import CH, SR  # noqa: E402

# Avance visée : un mélange de 8 mesures doit recevoir tout B puis être rendu avant que la lecture n'atteigne
# son début (~16 mesures + calcul). Un mélange la fait fondre de ~8 mesures ; les styles doux la regagnent
# (jusqu'à 2 mesures chacun) en prolongeant A un peu plus longtemps.
D = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
# Pour les boutons : dossier de travail de run.sh ; l'adresse de débogage de Spotify est retrouvée à
# chaque lancement (elle change à chaque redémarrage de Spotify), DJ_WS ne sert que de secours.
WS = os.environ.get("DJ_WS", "")
WORK = os.environ.get("DJ_WORK", "")
NOTES = os.environ.get("DJ_NOTES", os.path.join(HERE, "..", "..", "docs", "tests", "notes-ecoute.jsonl"))
ORIGIN = "http://127.0.0.1:47802"
# Pages autorisées à interroger la maquette et à lancer une transition : l'écran local et l'app Spicetify
ORIGINS = {ORIGIN, "https://xpui.app.spotify.com"}
URI = re.compile(r"^spotify:track:[A-Za-z0-9]{22}$")
LAT = 0.2            # latence de pacat (s) : délai entre l'écriture d'un bloc et le moment où on l'entend
GAIN_S = 16          # durée du retour du gain de B à 1 après une transition
SWITCH_S = 0.09      # délai entre l'ordre de saut et le changement dans le flux (mesuré, saut dans la playlist)
SLOW = 1.06          # ralenti de regain d'avance entre les transitions (cf. slower)
BLOCK = 1024
N = SR * 600         # 10 min de mémoire, en anneau
buf = np.zeros((N, CH), dtype=np.float32)
written = 0          # échantillons reçus depuis le lancement (la position dans buf est written % N)
clock = []           # (ms mur, échantillons reçus) pour relier l'heure à la mémoire
lock = threading.Lock()  # protège plan, current, last, last_resume, stream_gain
plan = []            # segments à jouer à la place du flux : (début, tableau, reprise, préréglage, infos, gain)
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
spotify_paused = False  # d'après espion.mjs : la maquette se met en pause en même temps que Spotify
pause_votes = 0      # messages « en pause » de suite : un seul ne suffit pas (pause passagère pendant un saut)
last_track_t = 0.0   # heure du dernier message d'espion : sans nouvelles, la pause expire
levels = [0.0] * 16  # niveau de 16 bandes de fréquences de ce qui part vers les haut-parleurs (visualiseur)
events = collections.deque(maxlen=12)  # derniers événements notables (refus, abandons), pour l'app
run_proc = None      # run.sh en cours, lancé depuis l'écran
last_request = None  # dernière transition demandée depuis l'écran, pour « Rejouer »


_mtimes = {m.__name__: os.path.getmtime(m.__file__) for m in (recettes, rendu)}
_reload_lock = threading.Lock()


def fresh():
    """Recharge recettes.py et rendu.py s'ils ont changé : régler un rendu ne demande pas de relancer la
    maquette (et d'attendre à nouveau D secondes de remplissage)."""
    global recettes, rendu
    with _reload_lock:
        now = {m.__name__: os.path.getmtime(m.__file__) for m in (recettes, rendu)}
        if now == _mtimes:
            return
        _mtimes.update(now)  # un fichier en erreur n'est retenté qu'à sa prochaine modification
        try:
            # rechargés hors place puis basculés d'un coup : un rendu en cours garde ses modules entiers
            import importlib.util
            new = {}
            for name in ("recettes", "rendu"):
                spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, f"{name}.py"))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[name] = mod  # rendu importe le nouveau recettes
                spec.loader.exec_module(mod)
                new[name] = mod
            recettes, rendu = new["recettes"], new["rendu"]
            log("recettes.py et rendu.py rechargés")
        except Exception as e:  # fichier à moitié sauvé, erreur de syntaxe : on garde la version qui marche
            sys.modules["recettes"], sys.modules["rendu"] = recettes, rendu
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
    """Ce que rendu.py voit de la mémoire."""
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
    heard = track_at(rp - int(LAT * SR))
    if cur_t:
        heard = {**(heard or {}), "name": cur_t["from"], "artist": "transition en cours", "pos_s": None, "dur_s": None}
    nxt = None
    if p:
        to = track_at(p[2] + 3 * SR)  # le nom de B arrive après son son : on le relit 3 s après la reprise
        nxt = {**p[4], "to": to and to["name"], "to_uri": to and to.get("uri"), "mode": p[3], "in_s": (p[0] - rp) / SR}
    cur = {**cur_t, "elapsed_s": time.time() - cur_t["t0"]} if cur_t else None
    done = {**last_t, "elapsed_s": time.time() - last_t["t0"]} if last_t and time.time() - last_t["t_end"] < 20 else None
    busy = run_proc is not None and run_proc.poll() is None
    return {"heard": heard, "spotify": track_at(written), "delay_s": current_delay() / SR, "target_s": D,
            "next": nxt, "current": cur, "last": done, "busy": busy, "last_request": last_request,
            "can_run": bool(WORK), "levels": [round(v, 3) for v in levels], "events": list(events),
            "notes": notes_avg}


def launch(req):
    """Lance run.sh pour la paire et le préréglage demandés depuis l'écran ; une seule à la fois."""
    global run_proc, last_request
    ws = spotify_ws()
    if not (ws and WORK):
        return 503, "Spotify n'est pas en mode débogage, ou maquette lancée sans DJ_WORK"
    if run_proc is not None and run_proc.poll() is None:
        return 409, "une transition est déjà en préparation"
    if plan or current:
        return 409, "une transition est déjà prévue ou en cours"
    mode, a, b = str(req.get("mode", "auto")), str(req.get("a", "")), str(req.get("b", ""))
    # les uri finissent dans du JS exécuté dans Spotify (run.sh) : format strict
    if mode not in {"auto", *recettes.PRESETS, *recettes.ALIASES} or not (URI.match(a) and URI.match(b)):
        return 400, "demande invalide"
    if mode == "auto":  # « Rejouer » doit refaire le même choix : on oublie le préréglage précédent
        try:
            os.remove(os.path.join(WORK, "dernier-mode"))
        except FileNotFoundError:
            pass
    last_request = {"mode": mode, "a": a, "b": b, "name": str(req.get("name", ""))[:200]}
    run_proc = subprocess.Popen(["bash", os.path.join(HERE, "run.sh"), ws, mode, WORK, a, b],
                                stdout=open(os.path.join(WORK, "run.out"), "w"), stderr=subprocess.STDOUT)
    log(f"écran : transition demandée ({mode}, {last_request['name']})")
    return 202, "lancée"


def note_averages():
    """Note moyenne par préréglage d'après le journal NOTES ; une transition notée deux fois compte pour sa
    dernière note. L'extension s'en sert pour favoriser les styles qui plaisent."""
    last_notes = {}
    try:
        with open(NOTES) as f:
            for line in f:
                try:
                    e = json.loads(line)
                    last_notes[(e.get("mode"), e.get("from"), e.get("to"))] = int(e["note"])
                except (ValueError, KeyError, TypeError):
                    continue
    except FileNotFoundError:
        return {}
    by_mode = collections.defaultdict(list)
    for (mode, _, _), n in last_notes.items():
        by_mode[mode].append(n)
    return {m: round(sum(v) / len(v), 2) for m, v in by_mode.items()}


notes_avg = note_averages()


def rate(req):
    """Note d'écoute d'une transition (1 à 5), ajoutée au journal NOTES."""
    global notes_avg
    note = req.get("note")
    if not isinstance(note, int) or not 1 <= note <= 5:
        return 400, "note invalide"
    entry = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "note": note,
             **{k: str(req.get(k, ""))[:200] for k in ("mode", "from", "to", "raison", "commentaire")}}
    with open(NOTES, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    notes_avg = note_averages()
    log(f"note {note}/5 : {entry['mode']} ({entry['from']} -> {entry['to']})")
    return 201, "notée"


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
        else:
            self._send(200, open(os.path.join(HERE, "ecran.html"), "rb").read(), "text/html; charset=utf-8")

    def do_POST(self):
        # Seules l'écran et l'app Spicetify peuvent lancer une transition : une autre page web ouverte
        # dans le navigateur pourrait sinon envoyer cette demande à la maquette.
        if self.path not in ("/run", "/order", "/rating", "/double") or self.headers.get("Origin") not in ORIGINS:
            code, msg = 403, "refusé"
        else:
            try:
                n = min(int(self.headers.get("Content-Length", 0)), 32768)  # les grilles de temps de A et B
                req = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(req, dict):
                    raise ValueError
                if self.path == "/run":
                    code, msg = launch(req)
                elif self.path == "/rating":
                    code, msg = rate(req)
                elif self.path == "/double":
                    code, msg = double(req)
                elif req.get("manuel") and run_proc is not None and run_proc.poll() is None:
                    code, msg = 409, "test manuel en cours : pas de rattrapage"  # le saut vient de run.sh
                elif valid_order(req):  # ordre de l'extension dj-auto : le saut est déjà fait dans Spotify
                    threading.Thread(target=handle_order, args=(req,), daemon=True).start()
                    code, msg = 202, "ordre reçu"
                else:
                    code, msg = 400, "ordre invalide"
            except (ValueError, json.JSONDecodeError):
                code, msg = 400, "demande invalide"
        self._send(code, json.dumps({"message": msg}).encode(), "application/json")

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
    new = [i for i, (n, info) in enumerate(tracks) if info.get("uri") == o.get("to_uri") and n > idx - 5 * SR]
    if new and new[0] > 0:
        return tracks[new[0] - 1][0] - int(0.2 * SR), tracks[new[0]][0] + int(0.2 * SR)
    return idx - int(0.5 * SR), idx + int(0.4 * SR)


def find_switch(o):
    """(fin de A, début de B) dans la mémoire.
    - Saut vers un morceau seul (run.sh) : silence numérique (zéros exacts) ; on prend la plus longue suite de
      quasi-zéros entre -50 et +400 ms de l'ordre, une fois ce son reçu (sinon la zone pas encore reçue
      passerait pour du silence).
    - Saut dans la playlist (`gapless`, mode auto) : aucun trou ni clic exploitable (mesuré le 2026-10-26) ; le
      changement tombe SWITCH_S après l'ordre, avec une marge pour ne jamais prendre de B dans A. Si B commence
      par son propre silence près de cette heure, son début est exact.
    - Changement non prévu (`manuel`) : fenêtre donnée par espion."""
    t_wall = float(o["t_wall"])
    deadline = time.time() + 10
    while not clock or clock[-1][0] < t_wall:
        if time.time() > deadline:  # plus rien n'arrive de dj_in : l'ordre ne peut pas être situé
            raise ValueError("aucun son reçu depuis l'ordre")
        time.sleep(0.02)
    idx = sample_at(t_wall)
    a, b = _manual_window(o, idx) if o.get("manuel") else (idx - int(0.05 * SR), idx + int(0.4 * SR))
    Memoire.wait(b + int(0.05 * SR))
    est = (a + b) // 2 if o.get("manuel") else idx + int(SWITCH_S * SR)
    sil = _longest_silence(a, b)
    if sil and not o.get("gapless"):
        return (*sil, 0)
    if sil and abs(sil[0] - est) < int(0.06 * SR):
        log("saut dans la playlist : B commence par un silence, son début est exact")
        return sil[0], sil[0], 0
    if o.get("manuel"):  # fenêtre large : A s'arrête au début (côté sûr), B part du milieu
        log("changement à la main sans silence : fin de A au début de la fenêtre d'espion")
        return a, est, 0
    log("changement sans silence : placé à l'heure de l'ordre")
    # B commence un peu avant l'estimation : la recherche de sa grosse caisse part de là et regarde devant.
    # Pas de pas en avant pour la fin de A : le délai du saut n'est mesuré qu'à quelques dizaines de ms près, et
    # quelques ms de B prises dans A se rejoueraient à chaque tour de boucle.
    return est - int(0.04 * SR), est - int(0.02 * SR), 0


def _beats(v):
    """Grille de temps envoyée par l'extension : au moins 8 temps, 120 au plus, en secondes, sinon None."""
    try:
        b = [float(x) for x in v][:120]
    except (TypeError, ValueError):
        return None
    return b if len(b) >= 8 and all(-60 < x < 60 for x in b) else None


def prepare(o, ctx):
    """Rend la recette demandée ; si elle refuse (calage impossible), se replie sur la montée courte, qui ne
    demande aucun calage et fait monter les premières mesures de B quand il n'a pas été lancé en avance.
    `ctx` reçoit de quoi rendre le secours si la transition ne peut pas être jouée."""
    fresh()
    R = rendu  # le module du rendu en cours, même s'il est rechargé entre-temps
    renderers = R.RENDERERS
    end_a, start_b, ahead = find_switch(o)  # ahead : marge sûre après la fin de A estimée
    if o.get("manuel"):
        cancel_after(end_a)
    bar = int(float(o["bar_s"]) * SR)
    # rapport des mesures réelles de A et B quand l'extension les donne, sinon des tempos globaux
    ratio = float(o["bar_b_s"]) / float(o["bar_s"]) if 0.3 < float(o.get("bar_b_s") or 0) < 5 else float(o["ratio"])
    # Calage sur les grilles de temps de Spotify quand l'extension les envoie : la fin de A est posée sur le
    # premier temps de la mesure de sortie, le début de B sur son temps de lancement. Les attaques servent
    # seulement à trouver le décalage entre la mémoire et ces grilles (toutes les attaques, pas la plus forte,
    # qui tombe à contretemps en rap). Sinon, ancien calage sur les grosses caisses.
    beats_a, beats_b = _beats(o.get("beatsA")), _beats(o.get("beatsB"))
    snap, how = True, "grosses caisses"
    lag_a = lag_b = None
    if beats_a:
        lag, st = R.grid_lag(Memoire, end_a, beats_a)
        if st >= 1.5:
            lag_a = lag if lag <= ahead else lag - bar  # premier temps au-delà du raccord : la mesure d'avant
    if lag_a is not None:
        end_a, shift = end_a + lag_a, lag_a
        how = "grille de Spotify"
    else:
        end_a, shift = R.grid_end(Memoire, end_a, float(o["bar_s"]) * SR / 4, ahead)
    if beats_b:
        lag, st = R.grid_lag(Memoire, start_b, beats_b)
        if st >= 1.5:
            lag_b, start_b, snap = lag, start_b + lag, False
    log(f"changement repéré : fin de A à {end_a} (recalée de {shift / SR * 1000:+.0f} ms, {how}), début de B à "
        f"{start_b}{f' (calé sur la grille de Spotify, {lag_b / SR * 1000:+.0f} ms)' if lag_b is not None else ''}")
    ctx.update(end_a=end_a, start_b=start_b, bar=bar, ratio=ratio)
    preset = recettes.ALIASES.get(o["mode"], o["mode"])
    raison = o.get("raison")
    pre = int(float(o.get("pre_s", 0)) * SR)
    # Avance regagnée quand elle manque : jusqu'à 2 mesures de A prolongé de plus (au-delà, un creux s'entend).
    # Jamais de raccourci quand elle dépasse : il écourtait la montée de B (« trop bref », essai 21) ; c'est
    # le mélange qui la fait redescendre.
    # Négatif (avance au-dessus de la cible de plus d'une demi-mesure) : le rendu arrondit au plus proche au
    # lieu d'arrondir au-dessus, sinon l'avance dérive vers le haut transition après transition.
    extra = int(np.clip(D * SR - current_delay(), -bar, 2 * bar))
    if -bar // 2 < extra < 0:
        extra = 0

    def render(name):
        kw = {"bars": int(o["bars"])} if name == "melange" and str(o.get("bars")) in ("4", "8") else {}
        R._ctx.snap = snap
        try:
            return renderers[name](Memoire, end_a, start_b, bar, ratio, pre=pre, extra=extra, **kw)
        finally:
            R._ctx.snap = True
    try:
        out = render(preset)
    except Exception as e:
        if type(e).__name__ != "Refus":
            raise
        event("refus", f"refus de « {recettes.PRESETS[preset]['label']} » : {e} ; repli sur la montée courte")
        raison, preset = f"repli : {e}", "montee_courte"
        out = render(preset)
    return (*out, preset, raison)


def control():
    global spotify_paused, pause_votes, last_track_t
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 47801))
    while True:
        try:
            o = json.loads(s.recv(65536))
            if o.get("cmd") == "track":
                pause_votes = pause_votes + 1 if o.get("paused") else 0
                spotify_paused, last_track_t = pause_votes >= 2, time.time()
                n = sample_at(o["t_wall"])
                if not tracks or tracks[-1][0] < n:
                    tracks.append((n, o))
                    track_samples.append(n)
                continue
            if valid_order(o):
                threading.Thread(target=handle_order, args=(o,), daemon=True).start()
            else:
                log("ordre UDP invalide ignoré")
        except Exception as e:  # un datagramme invalide ne doit pas couper les ordres suivants
            log("UDP :", repr(e))


def schedule(o, out, end_a, margin):
    """Programme un segment rendu ; rend None, ou la raison pour laquelle il ne peut pas être joué."""
    global last_resume
    start, seg, resume, g, preset, raison = out
    p = recettes.PRESETS[preset]
    frm = track_at(start)
    info = {"from": frm and frm["name"], "from_uri": frm and frm.get("uri"), "bar_s": o["bar_s"],
            "dur_s": max(len(seg) / SR, 0.01), "label": p["label"], "ingredients": p["ingredients"],
            "raison": raison, "resume": resume, "gain": round(g, 2), **recettes.PHASES[preset],
            # positions dans les morceaux, pour les cercles de l'app : fin de la transition dans A, durée
            # réellement rejouée de A avant elle, point d'entrée (drop) dans B
            "sortieA": o.get("sortieA"), "real_s": (end_a - start) / SR, "entreeB": o.get("entreeB")}
    with lock:
        if start < rp + margin:
            # jouer maintenant ramènerait A en arrière
            return f"« {p['label']} » prête trop tard ({(rp - start) / SR:+.1f} s)"
        if start < last_resume:
            return f"« {p['label']} » chevaucherait la transition précédente"
        plan.append((start, seg, resume, preset, info, g))
        plan.sort(key=lambda x: x[0])
        last_resume = max(last_resume, resume)
    log(f"transition prête : {p['label']}, {len(seg) / SR:.2f} s de segment, "
        f"avance après {(current_delay() - (resume - start) + len(seg)) / SR:.1f} s")
    return None


def track_sample(uri, pos_s):
    """Échantillon de la mémoire où le morceau `uri` était à la position pos_s (s), d'après le dernier message
    d'espion le concernant pendant la lecture."""
    for n, info in reversed(tracks):
        if info.get("uri") == uri and not info.get("paused"):
            return int(n + (pos_s - info["pos_ms"] / 1000) * SR)
    return None


def double(req):
    """Refrain doublé : rejouer les mesures [from_s, to_s) du morceau en cours juste après elles, comme un DJ de
    rap qui double un refrain. Regagne autant d'avance, sans effet synthétique : chaque superposition réelle en
    consomme (refonte du 26/10)."""
    uri = str(req.get("uri", ""))
    try:
        f, t, bar_s = float(req["from_s"]), float(req["to_s"]), float(req["bar_s"])
    except (KeyError, TypeError, ValueError):
        return 400, "demande invalide"
    if not URI.match(uri) or not (0 <= f < t and 4 <= t - f <= 40 and 0.3 < bar_s < 5):
        return 400, "demande invalide"
    s_to = track_sample(uri, t)
    if s_to is None or s_to + SR > written:
        return 409, "ce passage n'est pas encore en mémoire"
    # le point de reprise est recalé sur les temps du morceau ; la longueur rejouée reste celle de l'analyse
    s_to, _ = rendu.grid_end(Memoire, s_to, bar_s * SR / 4)
    s_from = s_to - int(round((t - f) * SR))
    seg = rendu._finish(Memoire, s_to, read(s_from, s_to), s_to, 1.0)
    o = {"bar_s": bar_s, "sortieA": None, "entreeB": None}
    why = schedule(o, (*seg, "refrain", f"avance à regagner : {(t - f):.1f} s rejouées"), s_to, int(0.5 * SR))
    if why:
        event("abandon", f"refrain doublé : {why}")
        return 409, why
    return 202, "refrain doublé prévu"


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


def handle_order(o):
    """Prépare puis programme une transition (ordre de run.sh en UDP, ou de l'extension dj-auto en HTTP).
    Spotify a déjà sauté : si la transition ne peut pas être jouée, un secours d'un temps remplace la coupe
    sèche, tant que la lecture n'a pas atteint le changement."""
    log("ordre reçu", o)
    ctx = {}
    try:
        why = schedule(o, prepare(o, ctx), ctx["end_a"], int(0.5 * SR))
    except Exception as e:  # la maquette doit survivre à un ordre raté
        why = f"échec de préparation : {e!r}"
    if why is None:
        return
    if "end_a" not in ctx:
        event("echec", f"{why} : transition abandonnée")
        return
    try:
        out = rendu.secours(Memoire, ctx["end_a"], ctx["start_b"], ctx["bar"], ctx["ratio"])
        why2 = schedule(o, (*out, "secours", why), ctx["end_a"], int(0.15 * SR))
        event("abandon", f"{why} : secours d'un temps à la place" if why2 is None else f"{why} : transition abandonnée")
    except Exception as e:
        event("echec", f"{why} ; secours impossible : {e!r}")


def valid_order(o):
    """Un ordre doit avoir les champs attendus, de bons types et un préréglage connu."""
    try:
        return (o.get("mode") in {*recettes.PRESETS, *recettes.ALIASES} and float(o["t_wall"]) > 0 and 0.3 < float(o["bar_s"]) < 5
                and 0.3 < float(o["ratio"]) < 3 and 0 <= float(o.get("pre_s", 0)) < 40)
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


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
    """Regain d'avance imperceptible : chaque superposition réelle en consomme ~8 mesures. Entre les
    transitions, tant que l'avance est sous la cible, la musique est jouée SLOW fois plus lentement, sans
    changer la hauteur (rubberband), par tranches de 8 s raccordées au flux par des fondus de 15 ms. Un DJ fait
    varier le tempo de cet ordre en permanence. (Le refrain doublé, l'autre moyen, a été jugé « absolument
    horrible », essai 29.)"""
    global slow_next
    ctx, xf, span = int(0.3 * SR), int(0.015 * SR), 8 * SR
    while True:
        time.sleep(0.2)
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
            y = recettes._rubberband(read(s - ctx, e + ctx), ["-t", f"{SLOW}"])
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
            start, seg, resume, preset, info, g = p
            to = track_at(resume + 3 * SR)
            with lock:
                plan.pop(0)
                current = {**info, "to": to and to["name"], "to_uri": to and to.get("uri"), "mode": preset,
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


threading.Thread(target=reader, daemon=True).start()
threading.Thread(target=control, daemon=True).start()
threading.Thread(target=keep_routing, daemon=True).start()
threading.Thread(target=slower, daemon=True).start()
screen = http.server.ThreadingHTTPServer(("127.0.0.1", 47802), Screen)
threading.Thread(target=screen.serve_forever, daemon=True).start()
log("écran sur http://127.0.0.1:47802")
writer()
