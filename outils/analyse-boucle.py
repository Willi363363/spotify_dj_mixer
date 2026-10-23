"""Analyse d'une boucle enregistrée : période réelle du son et silences à chaque reprise.

Entrées dans <dossier> :
  rec.raw          sortie son, s16le mono 44,1 kHz (parec)
  rec-start.txt    début de l'enregistrement, en ms depuis l'époque (date +%s%3N)
  loop-result.json sortie de loop-test.js (instants `at` de chaque saut)

Usage : python3 -I outils/analyse-boucle.py <dossier>
"""
import json
import sys

import numpy as np

RATE = 44100

d = sys.argv[1]
x = np.fromfile(f"{d}/rec.raw", dtype="<i2").astype(np.float32) / 32768
rec_start = int(open(f"{d}/rec-start.txt").read())
loops = json.load(open(f"{d}/loop-result.json"))["loops"]
ats = [(l["at"] - rec_start) / 1000 for l in loops]

print("intervalles entre sauts (s) :", [round(b - a, 3) for a, b in zip(ats, ats[1:])])

# Période réelle : autocorrélation de l'enveloppe à 1 ms entre le premier et le dernier saut.
w = int(RATE * 0.001)
seg = x[int(ats[0] * RATE) : int(ats[-1] * RATE)]
n = len(seg) // w
env = np.abs(seg[: n * w]).reshape(n, w).mean(axis=1)
env -= env.mean()
lags = np.arange(1000, 4000)
ac = [np.dot(env[:-lag], env[lag:]) for lag in lags]
print("période réelle du son bouclé (s) :", lags[int(np.argmax(ac))] / 1000)

# Silences : fenêtres de 5 ms à plus de 40 dB sous le niveau médian, autour de chaque reprise.
w5 = int(RATE * 0.005)
m = len(x) // w5
db = 20 * np.log10(np.sqrt((x[: m * w5].reshape(m, w5) ** 2).mean(axis=1)) + 1e-9)
ref = np.median(db[db > -60])
for k, t in enumerate(ats):
    s = db[int((t - 0.05) / 0.005) : int((t + 0.4) / 0.005)]
    print(f"reprise {k + 1} : creux {s.min() - ref:6.1f} dB, silence {int((s < ref - 40).sum()) * 5} ms")
