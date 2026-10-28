"""Vérifie hors ligne la détection de voix au rendu (V3, transitions/voix.py, ADR 0002) sur des morceaux de synthèse.

Voix factice de synthese.py (F0 120 à 250 Hz avec vibrato, formants qui changent à chaque syllabe, modulation 4 à 6 Hz)
sur certaines mesures, contre grosse caisse, charleston, nappe simple ou riche et basse 808, à 90, 120 et 150 BPM.
Contrôles :
- précision et rappel par mesure ≥ 0,9 (vocal ≥ 0,5) ; mesures sans voix sous 0,3 ;
- voix plus faible (−8 dB) encore détectée ; mesure à moitié chantée entre les deux extrêmes ;
- silence, bornes vides, bornes hors du signal : pas d'erreur, scores dans [0, 1] ;
- temps de calcul ≤ 0,3 s pour 32 mesures.
Une mélodie de synthé changeante (non stationnaire, comme une voix) est mesurée et affichée, sans seuil : c'est la
limite connue de V3, à calibrer en direct (tâche 2-direct).
Usage : python3 -I proto/e2/test_voix.py
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synthese  # noqa: E402
from transitions import voix  # noqa: E402
from transitions.outils import CH, SR  # noqa: E402

ok = True


def verifie(cond, texte):
    global ok
    print(("  ok  " if cond else "  ✗   ") + texte)
    ok &= bool(cond)


def bornes(bar, n, off=0):
    return (off + np.arange(n + 1) * bar * SR).astype(np.int64)


# 1. Précision et rappel par mesure
vp = fp = fn = 0
sans_ok = n_sans = 0
for bpm in (90, 120, 150):
    for riche in (False, True):
        for seed in (1, 2):
            bar = 240 / bpm
            n = 16
            rng = np.random.default_rng(bpm * 10 + seed + riche)
            chant = sorted(rng.choice(n, size=7, replace=False).tolist())
            x = synthese.track(bpm, n * bar, 196 if seed == 1 else 233, basse=True, riche=riche, seed=seed,
                               voix=[(i * bar, (i + 1) * bar) for i in chant])
            s = voix.voix_par_mesure(x, bornes(bar, n))
            for i in range(n):
                vocal = s[i] >= voix.SEUIL_VOCAL
                if i in chant:
                    vp += vocal
                    fn += not vocal
                else:
                    fp += vocal
                    n_sans += 1
                    sans_ok += s[i] < voix.SEUIL_SANS_VOIX
precision, rappel = vp / max(vp + fp, 1), vp / max(vp + fn, 1)
print(f"précision {precision:.2f}, rappel {rappel:.2f}, mesures sans voix sous 0,3 : {sans_ok}/{n_sans}")
verifie(precision >= 0.9, "précision ≥ 0,9")
verifie(rappel >= 0.9, "rappel ≥ 0,9")
verifie(sans_ok / n_sans >= 0.9, "≥ 90 % des mesures sans voix sous 0,3")

# 2. Voix plus faible (niveau 0,1 au lieu de 0,25, soit −8 dB) et mesure à moitié chantée
bar = 2.0
base = synthese.track(120, 8 * bar, 220, basse=True, riche=True, seed=3)
faible = base.copy()
v = synthese.voix_factice(len(base), [(2 * bar, 6 * bar)], seed=11, niveau=0.1)
faible += np.stack([v] * CH, axis=1)
s = voix.voix_par_mesure(faible, bornes(bar, 8))
print("voix faible :", " ".join(f"{x:.2f}" for x in s))
verifie(all(s[2:6] >= voix.SEUIL_VOCAL) and all(s[[0, 1, 6, 7]] < voix.SEUIL_SANS_VOIX), "voix à −8 dB détectée")
moitie = base.copy()
moitie += np.stack([synthese.voix_factice(len(base), [(3 * bar, 3.5 * bar)], seed=12)] * CH, axis=1)
s = voix.voix_par_mesure(moitie, bornes(bar, 8))
print(f"mesure à moitié chantée : {s[3]:.2f}")
verifie(s[3] >= voix.SEUIL_SANS_VOIX, "mesure à moitié chantée au moins « incertaine »")

# 3. Cas limites
verifie(len(voix.voix_par_mesure(base, np.array([0]))) == 0, "une seule borne : aucun score")
verifie(len(voix.voix_par_mesure(np.zeros((0, CH), np.float32), bornes(bar, 4))) == 4, "signal vide : 4 scores")
s = voix.voix_par_mesure(np.zeros((int(8 * bar * SR), CH), np.float32), bornes(bar, 8))
verifie(np.all(s == 0), "silence : 0 partout")
s = voix.voix_par_mesure(base, bornes(bar, 12))   # 4 mesures au-delà du signal
verifie(len(s) == 12 and np.all((s >= 0) & (s <= 1)) and np.all(s[8:] == 0), "bornes hors du signal : 0")
mono = voix.voix_par_mesure(base[:, 0], bornes(bar, 8))
verifie(len(mono) == 8, "signal mono accepté")

# 4. Temps de calcul : 32 mesures à 120 BPM (64 s)
x = synthese.track(120, 32 * bar, 220, basse=True, riche=True, voix=[(10, 40)])
voix.voix_par_mesure(x, bornes(bar, 32))
dts = []
for _ in range(5):   # meilleur de 5 : la machine est partagée, la charge des autres processus ne compte pas
    t = time.perf_counter()
    voix.voix_par_mesure(x, bornes(bar, 32))
    dts.append(time.perf_counter() - t)
dt = min(dts)
print(f"temps pour 32 mesures : {dt:.3f} s (meilleur de 5, médiane {sorted(dts)[2]:.3f} s)")
verifie(dt <= 0.3, "≤ 0,3 s pour 32 mesures")

# 5. Limite connue : mélodie de synthé non stationnaire (une note par temps), sans voix
t = np.arange(int(8 * bar * SR)) / SR
notes = np.random.default_rng(5).choice([262, 294, 330, 392, 440, 523], size=8 * 4)
f = notes[np.minimum((t / 0.5).astype(int), len(notes) - 1)]
mel = 0.15 * sum(np.sin(2 * np.pi * k * np.cumsum(f) / SR) / k for k in range(1, 6))
s = voix.voix_par_mesure(base + np.stack([mel.astype(np.float32)] * CH, axis=1), bornes(bar, 8))
print(f"(info) mélodie de synthé sans voix : moyenne {s.mean():.2f}, max {s.max():.2f} "
      "— faux positifs attendus de V3, d'où un seuil de repli à 0,6 tant que V3 n'est pas calibré")

print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
sys.exit(0 if ok else 1)
