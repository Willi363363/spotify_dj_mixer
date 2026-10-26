"""Transitions décrites comme des recettes, sur le modèle de Spotify Mix (cf. docs/recherche/spotify-transitions.md).

Une recette combine des ingrédients (volume, égaliseur, filtre, effets, boucle, tempo) étalés sur
N mesures. `render()` la transforme en segment audio à jouer à la place du flux, à partir de la
mémoire de e2.py. Si le calage est impossible, une recette qui superpose se replie sur une coupe.
"""
import os
import subprocess
import tempfile
import wave

import numpy as np

SR, CH = 44100, 2

# Préréglages : ce que l'écran affiche, et la fonction qui les rend.
PRESETS = {
    "montee":  {"label": "Montée", "bars": 8, "ingredients": {
        "filtre": "passe-haut qui monte sur A, filtre qui s'ouvre sur B", "boucle": "roulements 1 → 1/16 de temps",
        "effets": "hauteur qui monte", "volume": "B monte sous les 2 dernières mesures, puis son drop"}},
    "retour":  {"label": "Retour arrière", "bars": 1, "ingredients": {
        "boucle": "disque ramené à l'envers", "filtre": "graves de A retirés", "volume": "B net sur le premier temps"}},
    "coupe":   {"label": "Coupe", "bars": 0, "ingredients": {"volume": "A coupé, B net sur le premier temps"}},
    "echo":    {"label": "Sortie en écho", "bars": 2, "ingredients": {
        "effets": "écho ½ temps du dernier temps de A", "filtre": "écho sans graves", "volume": "B net sur le premier temps"}},
    "melange": {"label": "Mélange", "bars": 8, "ingredients": {
        "tempo": "glisse temps par temps de A vers B", "eq": "échange des basses au centre",
        "volume": "B entre vite, A sort lentement", "filtre": "passe-bas qui se ferme sur A"}},
    "frein":   {"label": "Frein", "bars": 1, "ingredients": {"effets": "vinyle qui ralentit", "volume": "B net sur le premier temps"}},
    "boucle":  {"label": "Boucle", "bars": 4, "ingredients": {"boucle": "dernière mesure de A ×4", "volume": "B net sur le premier temps"}},
}
ALIASES = {"build": "montee", "spinback": "retour", "mix": "melange", "brake": "frein", "loop": "boucle"}

# Pour l'écran : étapes (libellé, début, fin, en fraction de la transition) et moment où B devient
# audible (0 = dès le début, B superposé à A ; 1 = à la fin, B tombe net).
PHASES = {
    "montee":  {"b_from": 0.75, "phases": [("A perd ses basses", 0, 0.5), ("Roulements qui accélèrent", 0.5, 0.75),
                                            ("B monte sous les roulements", 0.75, 1)]},
    "melange": {"b_from": 0, "phases": [("B entre, sans ses basses", 0, 0.25), ("A et B ensemble", 0.25, 0.5),
                                         ("Basses passées à B, A s'éteint", 0.5, 1)]},
    "retour":  {"b_from": 1, "phases": [("A tourne à l'envers", 0, 1)]},
    "echo":    {"b_from": 0, "phases": [("B démarre, A en écho", 0, 1)]},
    "frein":   {"b_from": 1, "phases": [("A ralentit jusqu'à l'arrêt", 0, 1)]},
    "boucle":  {"b_from": 1, "phases": [("Dernière mesure de A en boucle", 0, 1)]},
    "coupe":   {"b_from": 1, "phases": []},
}


class Refus(Exception):
    """Le calage est impossible : la recette doit se replier."""


# ─── Outils de traitement ───────────────────────────────────────────────────────────────────────

def ramp(n, a, b):
    return np.linspace(a, b, n, dtype=np.float32)[:, None]


def smooth(n, a, b):
    """Courbe en S (lissée aux deux bouts), plus naturelle qu'une droite pour un volume."""
    t = np.linspace(0, 1, n, dtype=np.float32)
    return (a + (b - a) * (3 * t ** 2 - 2 * t ** 3))[:, None]


def band(x, lo=None, hi=None):
    """Filtre par FFT, sans déphasage : garde [lo, hi] avec des flancs doux (pente d'ordre 4)."""
    f = np.fft.rfftfreq(len(x), 1 / SR)[:, None]
    m = np.ones_like(f)
    if lo:
        m = m / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 8)
    if hi:
        m = m / np.sqrt(1 + (f / hi) ** 8)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * m, n=len(x), axis=0).astype(np.float32)


def sweep(x, lo=None, hi=None, w=4096):
    """Filtre qui évolue dans le temps, sans clic : trames de Hann à 50 % de recouvrement, chacune
    filtrée avec sa propre fréquence. `lo` / `hi` sont des fonctions de t ∈ [0, 1] → Hz (ou None)."""
    hop = w // 2
    win = np.hanning(w + 1)[:w].astype(np.float32)[:, None]  # Hann périodique : la somme vaut 1
    pad = np.concatenate([np.zeros((hop, CH), np.float32), x, np.zeros((w, CH), np.float32)])
    out = np.zeros_like(pad)
    for s in range(0, len(pad) - w, hop):
        t = min(1.0, max(0.0, (s - hop + w / 2) / max(1, len(x))))
        out[s:s + w] += band(pad[s:s + w] * win, lo and lo(t), hi and hi(t))
    return out[hop:hop + len(x)]


def edges(x, ms=3):
    """Fondus de quelques ms aux deux bouts d'une tranche, pour qu'un roulement ne claque pas."""
    n = min(int(ms / 1000 * SR), len(x) // 2)
    x = x.copy()
    x[:n] *= ramp(n, 0, 1)
    x[-n:] *= ramp(n, 1, 0)
    return x


def pitched(x, r):
    """Rejoue une tranche r fois plus vite (plus aiguë) en gardant sa durée : bouclée si trop courte."""
    n = len(x)
    pos = (np.arange(n) * r) % n
    return np.stack([np.interp(pos, np.arange(n), x[:, c]) for c in range(CH)], axis=1).astype(np.float32)


def _rubberband(x, args):
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.wav"), os.path.join(d, "out.wav")
        with wave.open(src, "wb") as w:
            w.setnchannels(CH); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
        subprocess.run(["rubberband", "-q", *[a.replace("{dir}", d) for a in args], src, dst], check=True)
        with wave.open(dst) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, CH).astype(np.float32) / 32767


def stretch_map(x, src_marks, dst_marks):
    """Étire x pour que chaque repère source tombe sur son repère cible (un repère par temps)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "map.txt")
        with open(path, "w") as f:
            for s, t in zip(src_marks, dst_marks):
                f.write(f"{int(s)} {int(t)}\n")
        y = _rubberband(x, ["-M", path, "-D", f"{dst_marks[-1] / SR:.6f}"])
    return y[: int(dst_marks[-1])]


def kick_env(x):
    """Enveloppe des attaques de grosse caisse : énergie 40-150 Hz par pas de 5 ms, montées seules."""
    lo = band(x.mean(axis=1, keepdims=True), lo=40, hi=150)[:, 0]
    h = int(0.005 * SR)
    e = np.sqrt((lo[: len(lo) // h * h].reshape(-1, h) ** 2).mean(axis=1))
    d = np.maximum(0, np.diff(e, prepend=e[0]))
    return (d - d.mean()) / (d.std() + 1e-9)


def kick_agreement(a, b):
    """Accord des grosses caisses de deux signaux de même longueur : 1 = identiques, ≈ 0 = sans rapport.
    Enveloppes lissées sur 15 ms et meilleur décalage à ±20 ms : un étirement décale le son de quelques
    ms, et une attaque d'un pas de 5 ms à côté ne doit pas compter comme un temps raté."""
    k = np.array([0.25, 0.5, 1.0, 0.5, 0.25])
    ea, eb = (np.convolve(kick_env(x), k, mode="same") for x in (a, b))
    n = min(len(ea), len(eb)) - 8
    best = max(float(np.dot(ea[4:4 + n], eb[4 + s:4 + s + n])) for s in range(-4, 5))
    return best / float(np.dot(ea[4:4 + n], ea[4:4 + n]) + 1e-9) ** 0.5 / float(np.dot(eb[4:4 + n], eb[4:4 + n]) + 1e-9) ** 0.5
