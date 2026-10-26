"""Maquette E2 : Spotify -> sortie virtuelle dj_in -> ce programme (D secondes d'avance) -> haut-parleurs.

Ordres reçus en UDP sur 127.0.0.1:47801, JSON :
  {"cmd": "transition", "mode": <préréglage de recettes.py>, "t_wall": <ms du changement A->B>,
   "bar_s": <durée d'une mesure de A>, "ratio": <tempo A / tempo B>, "raison": <pourquoi ce choix>}
  {"cmd": "track", ...}  infos de morceau envoyées par espion.mjs, pour l'écran.
Le programme retrouve l'échantillon exact du changement (micro-silence de Spotify), fait rendre la
recette par rendu.py à partir de la mémoire, puis la joue à la place du flux. Écran : http://127.0.0.1:47802
Usage : python3 -I proto/e2/e2.py [délai_s]   (journal sur la sortie standard)
"""
import bisect
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I n'ajoute pas le dossier du script au chemin d'import

from recettes import ALIASES, CH, PHASES, PRESETS, SR, Refus  # noqa: E402
from rendu import RENDERERS  # noqa: E402

# Avance en mémoire : un mélange de 8 mesures doit recevoir tout B puis être rendu avant que la lecture
# n'atteigne son début, soit au moins 2 × sa durée + 2 mesures + le calcul (~50 s à 100 BPM).
D = float(sys.argv[1]) if len(sys.argv) > 1 else 50.0
# Pour les boutons de l'écran : adresse de débogage de Spotify et dossier de travail de run.sh
WS = os.environ.get("DJ_WS", "")
WORK = os.environ.get("DJ_WORK", "")
ORIGIN = "http://127.0.0.1:47802"
run_proc = None      # run.sh en cours, lancé depuis l'écran
last_request = None  # dernière transition demandée depuis l'écran, pour « Rejouer »
BLOCK = 1024
buf = np.zeros((SR * 600, CH), dtype=np.float32)  # 10 min de mémoire
written = 0          # échantillons reçus
clock = []           # (ms mur, échantillons reçus) pour relier l'heure à la mémoire
plan = []            # segments à jouer à la place du flux : (début, tableau, reprise, préréglage, infos)
tracks = []          # (échantillon d'entrée, infos du morceau envoyées par espion.mjs)
track_samples = []   # les mêmes échantillons seuls, pour la recherche dichotomique
rp = 0               # position de lecture dans la mémoire (ce qui part vers les haut-parleurs)
current = None       # transition en train d'être jouée
last = None          # dernière transition jouée, gardée 20 s pour que l'écran montre B qui continue
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


class Memoire:
    """Ce que rendu.py voit de la mémoire."""
    buf = buf
    log = staticmethod(log)

    @staticmethod
    def wait(n):
        while written < n:
            time.sleep(0.02)


def sample_at(t_wall):
    """Échantillon de la mémoire reçu à l'heure t_wall (ms)."""
    i = bisect.bisect_left(clock, (t_wall,))
    return clock[min(i, len(clock) - 1)][1] if clock else 0


def track_at(sample):
    """Morceau joué à cet endroit de la mémoire, et sa position en secondes."""
    i = bisect.bisect_right(track_samples, sample) - 1
    if i < 0:
        return None
    s, info = tracks[i]
    pos = info["pos_ms"] / 1000 + (0 if info.get("paused") else (sample - s) / SR)
    return {"name": info["name"], "artist": info["artist"], "pos_s": pos, "dur_s": info["dur_ms"] / 1000}


def state():
    heard = track_at(rp - int(0.06 * SR))  # latence de pacat
    if current:
        heard = {**(heard or {}), "name": current["from"], "artist": "transition en cours", "pos_s": None, "dur_s": None}
    nxt = None
    if plan:
        p = plan[0]
        to = track_at(p[2] + 3 * SR)  # le nom de B arrive après son son : on le relit 3 s après la reprise
        nxt = {**p[4], "to": to and to["name"], "mode": p[3], "in_s": (p[0] - rp) / SR}
    cur = {**current, "elapsed_s": time.time() - current["t0"]} if current else None
    done = None
    if last and time.time() - last["t_end"] < 20:
        done = {**last, "elapsed_s": time.time() - last["t0"]}
    busy = run_proc is not None and run_proc.poll() is None
    return {"heard": heard, "spotify": track_at(written), "delay_s": (written - rp) / SR,
            "next": nxt, "current": cur, "last": done, "busy": busy, "last_request": last_request,
            "can_run": bool(WS and WORK)}


def launch(req):
    """Lance run.sh pour la paire et le préréglage demandés depuis l'écran ; une seule à la fois."""
    global run_proc, last_request
    if not (WS and WORK):
        return 503, "maquette lancée sans DJ_WS / DJ_WORK : boutons indisponibles"
    if run_proc is not None and run_proc.poll() is None:
        return 409, "une transition est déjà en préparation"
    if plan or current:
        return 409, "une transition est déjà prévue ou en cours"
    mode, a, b = str(req.get("mode", "auto")), str(req.get("a", "")), str(req.get("b", ""))
    valid = {"auto", *PRESETS, *ALIASES}
    if mode not in valid or not (a.startswith("spotify:track:") and b.startswith("spotify:track:")):
        return 400, "demande invalide"
    if mode == "auto":  # « Rejouer » doit refaire le même choix : on oublie le préréglage précédent
        try:
            os.remove(os.path.join(WORK, "dernier-mode"))
        except FileNotFoundError:
            pass
    last_request = {"mode": mode, "a": a, "b": b, "name": req.get("name")}
    run_proc = subprocess.Popen(["bash", os.path.join(HERE, "run.sh"), WS, mode, WORK, a, b],
                                stdout=open(os.path.join(WORK, "run.out"), "w"), stderr=subprocess.STDOUT)
    log(f"écran : transition demandée ({mode}, {req.get('name')})")
    return 202, "lancée"


class Screen(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/state"):
            body, kind = json.dumps(state()).encode(), "application/json"
        else:
            body, kind = open(os.path.join(HERE, "ecran.html"), "rb").read(), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Seule la page de l'écran peut lancer une transition : une autre page web ouverte dans le
        # navigateur pourrait sinon envoyer cette demande à la maquette.
        if self.path != "/run" or self.headers.get("Origin") != ORIGIN:
            code, msg = 403, "refusé"
        else:
            try:
                n = min(int(self.headers.get("Content-Length", 0)), 4096)
                code, msg = launch(json.loads(self.rfile.read(n) or b"{}"))
            except (ValueError, json.JSONDecodeError):
                code, msg = 400, "demande invalide"
        body = json.dumps({"message": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def reader():
    global written
    p = subprocess.Popen(["parec", "-d", "dj_in.monitor", "--format=float32le", f"--rate={SR}",
                          f"--channels={CH}", "--latency-msec=10"], stdout=subprocess.PIPE)
    while True:
        raw = p.stdout.read(BLOCK * CH * 4)
        if not raw:
            return
        x = np.frombuffer(raw, dtype=np.float32).reshape(-1, CH)
        buf[written:written + len(x)] = x
        written += len(x)
        clock.append((time.time() * 1000, written))


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


def find_switch(t_wall):
    """Échantillon du changement : Spotify y insère du silence numérique (zéros exacts).
    On prend la plus longue suite de quasi-zéros entre -50 et +400 ms de l'heure annoncée."""
    idx = next(n for t, n in clock if t >= t_wall)
    a = idx - int(0.05 * SR)
    silent = np.abs(buf[a:idx + int(0.4 * SR)]).max(axis=1) < 1e-4
    best, cur, best_end = 0, 0, 0
    for i, s in enumerate(silent):
        cur = cur + 1 if s else 0
        if cur > best:
            best, best_end = cur, i + 1
    if best < int(0.002 * SR):
        raise ValueError("aucun silence de changement trouvé")
    return a + best_end - best, a + best_end  # fin de A, début de B


def prepare(o):
    """Rend la recette demandée ; si elle refuse (calage impossible), se replie sur la montée, qui ne
    demande aucun calage (la coupe seule a été rejetée à l'écoute)."""
    end_a, start_b = find_switch(o["t_wall"])
    bar = int(o["bar_s"] * SR)
    log(f"changement repéré : fin de A à {end_a}, début de B à {start_b}, trou {(start_b - end_a) / SR * 1000:.1f} ms")
    preset = ALIASES.get(o["mode"], o["mode"])
    raison = o.get("raison")
    # Spotify a pu lancer B quelques mesures avant son point d'entrée (pre_s) : la montée s'en sert pour
    # faire monter B sous la fin de A ; les autres préréglages entrent directement au point d'entrée.
    pre = int(o.get("pre_s", 0) * SR)

    def render(name):
        if name == "montee":
            return RENDERERS[name](Memoire, end_a, start_b, bar, o["ratio"], pre=pre)
        return RENDERERS[name](Memoire, end_a, start_b + pre, bar, o["ratio"])
    try:
        start, seg, resume = render(preset)
    except Refus as e:
        log(f"refus de « {preset} » : {e} ; repli sur la montée")
        raison, preset = f"repli : {e}", "montee"
        start, seg, resume = render("montee")
    return start, seg, resume, preset, raison


def control():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 47801))
    while True:
        o = json.loads(s.recv(4096))
        if o.get("cmd") == "track":
            n = sample_at(o["t_wall"])
            if not tracks or tracks[-1][0] < n:
                tracks.append((n, o))
                track_samples.append(n)
            continue
        log("ordre reçu", o)
        try:
            start, seg, resume, preset, raison = prepare(o)
            if start < rp + int(0.5 * SR):
                # Prête trop tard : la jouer maintenant ramènerait A en arrière. On laisse la musique continuer.
                log(f"« {preset} » prête trop tard ({(rp - start) / SR:+.1f} s) : transition abandonnée")
                continue
            frm = track_at(start)
            p = PRESETS[preset]
            info = {"from": frm and frm["name"], "bar_s": o["bar_s"], "dur_s": max(len(seg) / SR, 0.01),
                    "label": p["label"], "ingredients": p["ingredients"], "raison": raison, **PHASES[preset]}
            plan.append((start, seg, resume, preset, info))
            log(f"transition prête : {p['label']}, {len(seg) / SR:.2f} s de segment")
        except Exception as e:  # la maquette doit survivre à un ordre raté
            log("échec de préparation :", repr(e))


def writer():
    global rp, current, last
    out = subprocess.Popen(["pacat", "--playback", "--format=float32le", f"--rate={SR}",
                            f"--channels={CH}", "--latency-msec=60", "--client-name=dj-e2"], stdin=subprocess.PIPE)
    while written < D * SR:
        time.sleep(0.01)
    log(f"lecture démarrée avec {D:.0f} s d'avance")
    warned = None
    while True:
        if plan and plan[0] is not warned and plan[0][0] - rp < 10 * SR:
            warned = plan[0]
            subprocess.Popen(["notify-send", "Maquette E2", f"Dans 10 s : {plan[0][4]['label']}"])
        if plan and rp >= plan[0][0]:
            start, seg, resume, preset, info = plan[0]
            # le son sort ~60 ms après l'écriture (latence de pacat) : la notification tombe avec la transition
            subprocess.Popen(["notify-send", "Maquette E2", f"Maintenant : {info['label']}"])
            to = track_at(resume + 3 * SR)
            current = {**info, "to": to and to["name"], "mode": preset, "t0": time.time() + 0.06}
            plan.pop(0)
            for k in range(0, len(seg), BLOCK):  # par blocs, pour que l'écran suive la progression
                out.stdin.write(seg[k:k + BLOCK].tobytes())
            last = {**current, "t_end": current["t0"] + len(seg) / SR}
            current = None
            log(f"segment joué ({len(seg) / SR:.2f} s), reprise du flux, avance restante {(written - resume) / SR:.1f} s")
            rp = resume
            continue
        while written - rp < BLOCK:
            time.sleep(0.005)
        n = min(BLOCK, plan[0][0] - rp) if plan and plan[0][0] > rp else BLOCK
        out.stdin.write(buf[rp:rp + n].tobytes())
        rp += n


threading.Thread(target=reader, daemon=True).start()
threading.Thread(target=control, daemon=True).start()
threading.Thread(target=keep_routing, daemon=True).start()
screen = http.server.ThreadingHTTPServer(("127.0.0.1", 47802), Screen)
threading.Thread(target=screen.serve_forever, daemon=True).start()
log("écran sur http://127.0.0.1:47802")
writer()
