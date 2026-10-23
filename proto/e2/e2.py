"""Maquette E2 : Spotify -> sortie virtuelle dj_in -> ce programme (D secondes d'avance) -> haut-parleurs.

Ordres reçus en UDP sur 127.0.0.1:47801, JSON :
  {"cmd": "transition", "mode": "mix"|"brake"|"loop", "t_wall": <ms du changement A->B>,
   "bar_s": <durée d'une mesure de A>, "ratio": <tempo A / tempo B>, "bars": 4}
Le programme retrouve l'échantillon exact du changement (micro-silence de Spotify), prépare le
segment de transition à partir de la mémoire, puis le joue à la place du flux.
Usage : python3 -I proto/e2/e2.py [délai_s]   (journal sur la sortie standard)
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import wave

import numpy as np

SR, CH = 44100, 2
D = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
BLOCK = 1024
buf = np.zeros((SR * 600, CH), dtype=np.float32)  # 10 min de mémoire
written = 0          # échantillons reçus
clock = []           # (ms mur, échantillons reçus) pour relier l'heure à la mémoire
plan = []            # segments à jouer à la place du flux : (début_lecture, tableau, reprise_lecture)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


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


def band(x, lo=None, hi=None):
    """Filtre par FFT, sans déphasage : garde [lo, hi] avec des flancs doux (pente d'ordre 4)."""
    f = np.fft.rfftfreq(len(x), 1 / SR)[:, None]
    m = np.ones_like(f)
    if lo:
        m = m / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 8)
    if hi:
        m = m / np.sqrt(1 + (f / hi) ** 8)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * m, n=len(x), axis=0).astype(np.float32)


def stretch(x, tempo):
    """Change le tempo sans changer la hauteur, via le programme rubberband."""
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.wav"), os.path.join(d, "out.wav")
        with wave.open(src, "wb") as w:
            w.setnchannels(CH); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
        subprocess.run(["rubberband", "-q", "-T", f"{tempo:.5f}", src, dst], check=True)
        with wave.open(dst) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, CH).astype(np.float32) / 32767


def ramp(n, a, b):
    return np.linspace(a, b, n, dtype=np.float32)[:, None]


def prepare(o):
    end_a, start_b = find_switch(o["t_wall"])
    bar = int(o["bar_s"] * SR)
    bars = o.get("bars", 4)
    L = bar * bars
    log(f"changement repéré : fin de A à {end_a}, début de B à {start_b}, trou {(start_b - end_a) / SR * 1000:.1f} ms")
    if o["mode"] == "loop":   # rejoue la dernière mesure de A depuis la mémoire, puis B net sur le temps
        seg = np.concatenate([buf[end_a - bar:end_a]] * bars)
        return end_a, seg, start_b
    if o["mode"] == "brake":  # « vinyle qui freine » sur la dernière mesure de A, puis B
        tail = buf[end_a - bar:end_a]
        speed = np.linspace(1.0, 0.0, bar) ** 1.5
        pos = np.cumsum(speed)
        pos = pos[pos < bar - 1]
        out = np.stack([np.interp(pos, np.arange(bar), tail[:, c]) for c in range(CH)], axis=1).astype(np.float32)
        return end_a - bar, out * ramp(len(out), 1, 0.6), start_b
    # mix : A sur ses `bars` dernières mesures, B calé au tempo de A, échange des basses à mi-parcours
    need = int(L * o["ratio"])  # accélérer B d'un facteur ratio raccourcit le son : il en faut L * ratio
    while written < start_b + need + SR:
        time.sleep(0.05)
    a = buf[end_a - L:end_a].copy()
    b = stretch(buf[start_b:start_b + need + SR], o["ratio"])[:L]
    half, xf = L // 2, int(0.05 * SR)
    swap = np.concatenate([np.zeros(half - xf // 2), np.linspace(0, 1, xf), np.ones(L - half - xf + xf // 2)])[:L, None].astype(np.float32)
    a_mix = a * (1 - swap) + band(a, lo=180) * swap           # A perd ses basses à la mi-transition
    b_mix = band(b, lo=180) * (1 - swap) + b * swap           # B les récupère au même instant
    vol_a = np.concatenate([np.ones(half), np.linspace(1, 0, L - half)])[:, None]
    vol_b = np.concatenate([np.linspace(0, 1, half), np.ones(L - half)])[:, None]
    seg = (a_mix * vol_a + b_mix * vol_b).astype(np.float32)
    return end_a - L, seg, start_b + need


def control():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 47801))
    while True:
        o = json.loads(s.recv(4096))
        log("ordre reçu", o)
        try:
            plan.append(prepare(o))
            log(f"transition prête : {len(plan[-1][1]) / SR:.2f} s de segment")
        except Exception as e:  # la maquette doit survivre à un ordre raté
            log("échec de préparation :", e)


def writer():
    out = subprocess.Popen(["pacat", "--playback", "--format=float32le", f"--rate={SR}",
                            f"--channels={CH}", "--latency-msec=60", "--client-name=dj-e2"], stdin=subprocess.PIPE)
    while written < D * SR:
        time.sleep(0.01)
    log(f"lecture démarrée avec {D:.0f} s d'avance")
    rp = 0
    while True:
        if plan and rp >= plan[0][0]:
            start, seg, resume = plan.pop(0)
            out.stdin.write(seg.tobytes())
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
writer()
