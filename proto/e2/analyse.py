"""Mesures de la maquette E2 sur in.raw (dj_in.monitor) et out.raw (haut-parleurs), s16le mono 44,1 kHz.

- retard réel sortie / entrée et fidélité du passage direct (avant la transition) ;
- silences numériques dans la sortie (trous) pendant toute la lecture ;
- trou de Spotify dans l'entrée au moment du changement.
Usage : python3 -I proto/e2/analyse.py <dossier> <résultat.json de transition.js>
"""
import json
import sys

import numpy as np

R = 44100
d, res = sys.argv[1], json.load(open(sys.argv[2]))
x = np.fromfile(f"{d}/in.raw", dtype="<i2").astype(np.float64) / 32768
y = np.fromfile(f"{d}/out.raw", dtype="<i2").astype(np.float64) / 32768
t_switch = (res["t_wall"] - int(open(f"{d}/rec-start.txt").read())) / 1000


def runs(sig, a, b, thr=2 / 32768, min_ms=3):
    """Suites de silence numérique d'au moins min_ms dans sig[a:b] (secondes), renvoyées en (début s, ms)."""
    s = np.abs(sig[int(a * R):int(b * R)]) < thr
    out, cur = [], 0
    for i, v in enumerate(s):
        if v:
            cur += 1
        else:
            if cur >= min_ms * R / 1000:
                out.append((round(a + (i - cur) / R, 3), round(cur / R * 1000, 1)))
            cur = 0
    return out


# Retard : intercorrélation d'un extrait de 3 s pris 8 s avant le changement.
a = int((t_switch - 8) * R)
ref = x[a:a + 3 * R]
lags = range(int(19.5 * R), int(21.5 * R), 8)
best = max(lags, key=lambda k: np.dot(ref, y[a + k:a + k + len(ref)]))
best = max(range(best - 8, best + 9), key=lambda k: np.dot(ref, y[a + k:a + k + len(ref)]))
fid = np.corrcoef(ref, y[a + best:a + best + len(ref)])[0, 1]
print(f"retard réel : {best / R:.3f} s, ressemblance sortie / entrée : {fid:.4f}")

print("trou de Spotify dans l'entrée au changement :", runs(x, t_switch - 0.05, t_switch + 0.6))
out_switch = t_switch + best / R
print(f"changement attendu dans la sortie vers {out_switch:.1f} s (transition entre {out_switch - 8:.1f} et {out_switch:.1f} s)")
start = 20 + 1  # la sortie ne commence qu'après le remplissage de la mémoire
silences = runs(y, start + 1, len(y) / R - 0.5)
print(f"silences numériques dans la sortie ({start + 1:.0f} s -> fin) :", silences or "aucun")
