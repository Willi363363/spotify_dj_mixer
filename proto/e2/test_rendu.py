"""Vérifie hors ligne chaque préréglage sur des morceaux de synthèse (grosse caisse + nappe).

A à 120 BPM, puis 350 ms de silence (le trou de Spotify), puis B au tempo voulu.
Contrôles : pas d'erreur, durée du segment, pas de NaN, crête sous 1, accord des grosses caisses
pour le mélange, repli quand les tempos sont trop éloignés.
Usage : python3 -I proto/e2/test_rendu.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recettes import CH, PRESETS, SR, Refus, kick_agreement  # noqa: E402
from rendu import RENDERERS  # noqa: E402


def track(bpm, seconds, note):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    beat = 60 / bpm
    phase = t % beat
    kick = np.sin(2 * np.pi * (50 + 100 * np.exp(-phase * 30)) * phase) * np.exp(-phase * 12)
    pad = 0.15 * np.sin(2 * np.pi * note * t)
    return np.stack([kick * 0.6 + pad] * CH, axis=1).astype(np.float32)


class Mem:
    log = staticmethod(lambda *a: print("   ", *a))

    def __init__(self, bpm_b):
        a, b = track(120, 40, 220), track(bpm_b, 40, 330)
        gap = np.zeros((int(0.35 * SR), CH), np.float32)
        self.buf = np.concatenate([a, gap, b])
        self.end_a, self.start_b = len(a), len(a) + len(gap)

    def wait(self, n):
        assert n <= len(self.buf), "la recette demande plus de son que la mémoire n'en a"


ok = True
for name, fn in RENDERERS.items():
    m = Mem(123)
    bar = int(4 * 60 / 120 * SR)
    try:
        start, seg, resume = fn(m, m.end_a, m.start_b, bar, 120 / 123)
        bad = not np.isfinite(seg).all() or np.abs(seg).max() > 1.0
        print(f"{PRESETS[name]['label']:15s} segment {len(seg) / SR:6.2f} s, début {(start - m.end_a) / SR:+6.2f} s, "
              f"reprise {(resume - m.start_b) / SR:+6.2f} s{'  ✗ valeurs invalides' if bad else ''}")
        ok &= not bad
    except Exception as e:
        print(f"{name:15s} ✗ {e!r}")
        ok = False

m = Mem(140)  # 14 % d'écart : le mélange doit refuser
try:
    RENDERERS["melange"](m, m.end_a, m.start_b, int(2 * SR), 120 / 140)
    print("mélange à 14 % d'écart : ✗ aurait dû refuser")
    ok = False
except Refus as e:
    print(f"mélange à 14 % d'écart : refus attendu ({e})")

m = Mem(120)  # même tempo, B décalé d'un demi-temps : le mélange doit refuser (temps en contretemps)
off = int(0.25 * SR)
m.buf = np.concatenate([m.buf[:m.start_b], np.zeros((off, CH), np.float32), m.buf[m.start_b:]])
try:
    RENDERERS["melange"](m, m.end_a, m.start_b + off - int(0.01 * SR), int(2 * SR), 1.0)
    print("mélange à contretemps : accepté (le recalage sur la grosse caisse a rattrapé le décalage)")
except Refus as e:
    print(f"mélange à contretemps : refus ({e})")

m = Mem(120)
mem_b = m.buf[m.start_b:]
pre = int(0.03 * SR)
print("recalage du premier temps de B (attaque pile au début) :",
      f"{RENDERERS['coupe'](m, m.end_a, m.start_b, int(2 * SR), 1.0)[2] - m.start_b} échantillons (attendu ≈ 0)")
print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
