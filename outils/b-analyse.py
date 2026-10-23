"""Série B : mesure de l'égaliseur, de l'écho et des clics, avant / après le filtre.

Entrées dans <dossier> : pre.raw, post.raw (s16le mono 44,1 kHz), marks.txt (lignes « nom ms »
depuis le début des enregistrements).
Usage : python3 -I outils/b-analyse.py <dossier> <délai_écho_s>
"""
import sys

import numpy as np

R = 44100
d, echo_delay = sys.argv[1], float(sys.argv[2])
pre = np.fromfile(f"{d}/pre.raw", dtype="<i2").astype(np.float64) / 32768
post = np.fromfile(f"{d}/post.raw", dtype="<i2").astype(np.float64) / 32768
marks = {k: int(v) / 1000 for k, v in (l.split() for l in open(f"{d}/marks.txt"))}

# Les deux enregistrements ne démarrent pas au même échantillon : on recale « post » sur « pre »
# par intercorrélation sur la phase neutre (filtre transparent), à ±300 ms.
a0 = int((marks["neutre"] + 0.5) * R)
ref = pre[a0 : a0 + 2 * R]
best = max(range(-int(0.3 * R), int(0.3 * R), 4), key=lambda k: np.dot(ref, post[a0 + k : a0 + k + len(ref)]))
best = max(range(best - 4, best + 5), key=lambda k: np.dot(ref, post[a0 + k : a0 + k + len(ref)]))
post = post[best:] if best > 0 else np.concatenate([np.zeros(-best), post])
print(f"recalage : sortie décalée de {best / R * 1000:+.1f} ms par rapport à l'entrée")


def cut(x, a, b):
    return x[int(a * R) : int(b * R)]


def band(x, lo, hi):
    s = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / R)
    return 10 * np.log10(s[(f >= lo) & (f < hi)].sum() + 1e-12)


def gain(phase, lo, hi):
    a, b = marks[phase] + 0.5, marks[phase] + 3.5
    return band(cut(post, a, b), lo, hi) - band(cut(pre, a, b), lo, hi)


print("--- égaliseur (gain après - avant, dB)")
for phase in ["neutre", "eq"]:
    print(f"  {phase:7s} graves <120 Hz {gain(phase, 30, 120):6.1f} | médiums 500-2k {gain(phase, 500, 2000):6.1f} | aigus >6 kHz {gain(phase, 6000, 16000):6.1f}")

print("--- écho : ressemblance de la sortie avec l'entrée décalée")
a, b = marks["echo"] + 1.0, marks["echo"] + 3.5
y, x = cut(post, a, b), cut(pre, a - 1.0, b)  # x commence 1 s plus tôt pour couvrir le décalage
for lag in [0.0, echo_delay, 2 * echo_delay]:
    xs = x[int((1.0 - lag) * R) : int((1.0 - lag) * R) + len(y)]
    print(f"  décalage {lag:5.3f} s : corrélation {np.corrcoef(y, xs)[0, 1]:+.3f}")

print("--- clics : pics d'aigus (>10 kHz) ajoutés par le filtre, fenêtres de 10 ms")
w = int(R * 0.01)


def hf_db(x):
    n = len(x) // w
    frames = x[: n * w].reshape(n, w)
    spec = np.abs(np.fft.rfft(frames * np.hanning(w), axis=1)) ** 2
    f = np.fft.rfftfreq(w, 1 / R)
    return 10 * np.log10(spec[:, f >= 10000].sum(axis=1) + 1e-12)


for phase in ["neutre", "balayage_rapide", "balayage_lent"]:
    a, b = marks[phase], marks[phase] + 3.0
    diff = hf_db(cut(post, a, b)) - hf_db(cut(pre, a, b))
    print(f"  {phase:16s} fenêtres où la sortie dépasse l'entrée de +6 dB : {(diff > 6).sum()} / {len(diff)}, max {diff.max():+.1f} dB")
