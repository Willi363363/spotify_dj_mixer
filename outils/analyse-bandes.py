"""Énergie par bande de fréquences, phase par phase, avant et après le filtre.

Entrées dans <dossier> : pre.raw (dj_filter.monitor) et post.raw (sortie par défaut),
en s16le mono 44,1 kHz. Les phases sont en secondes depuis le début des enregistrements.

Usage : python3 -I outils/analyse-bandes.py <dossier>
"""
import sys

import numpy as np

RATE = 44100
PHASES = {"avant coupe": (0.5, 3.5), "basses coupées": (4.8, 9.0), "après": (10.0, 14.0)}


def band_db(x, lo, hi):
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / RATE)
    return 10 * np.log10(spectrum[(freqs >= lo) & (freqs < hi)].sum() + 1e-12)


d = sys.argv[1]
for name, label in [("pre", "avant le filtre"), ("post", "après le filtre")]:
    x = np.fromfile(f"{d}/{name}.raw", dtype="<i2").astype(np.float64) / 32768
    print(f"--- {label} ({len(x) / RATE:.1f} s)")
    for phase, (a, b) in PHASES.items():
        seg = x[int(a * RATE) : int(b * RATE)]
        if len(seg) < RATE:
            print(f"  {phase} : trop court")
            continue
        print(
            f"  {phase:15s} basses <150 Hz {band_db(seg, 30, 150):6.1f} dB"
            f" | médiums 300-3000 Hz {band_db(seg, 300, 3000):6.1f} dB"
        )
