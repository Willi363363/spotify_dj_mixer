"""Mesures sur le son rendu (critères 9.1 n° 1 à 7) : chacune doit voir le défaut qu'on lui présente et rester muette
sur un signal propre. Signaux de synthèse uniquement.
Usage : python3 -I proto/e2/test_mesures.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synthese as S  # noqa: E402
from transitions import mesures as M  # noqa: E402
from transitions.contrat import Automation  # noqa: E402
from transitions.outils import CH, SR  # noqa: E402

ok = True


def verifie(label, cond, detail=""):
    global ok
    print(f"{'ok' if cond else '✗ '} {label}{' : ' + detail if detail else ''}")
    ok &= bool(cond)


beat = SR // 2  # 120 BPM
a = S.track(120, 16, 220, basse=True)
b = S.track(120, 16, 330, basse=True, seed=2)
marks = np.arange(8, 24) * beat

# 1. Calage
e, n = M.calage(a, b, marks)
verifie("calage : deux pistes sur la grille → ≈ 0 ms", abs(e) <= 5 and n > 1.5, f"{e:+.1f} ms, netteté {n:.1f}")
d = int(0.03 * SR)
b_tard = np.concatenate([np.zeros((d, CH), np.float32), b[:-d]])
e, _ = M.calage(a, b_tard, marks)
verifie("calage : B en retard de 30 ms → ≈ +30 ms", abs(e - 30) <= 5, f"{e:+.1f} ms")
bruit = (0.2 * np.random.default_rng(3).standard_normal(a.shape)).astype(np.float32)
_, n0 = M.calage(a, b, marks)
_, n = M.calage(a, bruit, marks)
verifie("calage : pas de pulsation → netteté bien plus faible", n < n0 / 2, f"{n:.2f} contre {n0:.2f}")

# 2. Basses superposées
L = len(a)
cut = 8 * beat
pa = a.copy()
pa[cut:] = 0
pb = b.copy()
pb[:cut] = 0
verifie("basses : échange franc → ≤ 1 temps", M.basses(pa, pb, beat) <= 500, f"{M.basses(pa, pb, beat):.0f} ms")
pa2 = a.copy()
pa2[cut + 4 * beat:] = 0
ms = M.basses(pa2, pb, beat)
verifie("basses : 4 temps de graves doublés → vus (≥ 1 temps)", ms > 500, f"{ms:.0f} ms")

# 3. Échange sur le 1
uns = np.arange(0, L, 4 * beat)
ech = M.echange(pa, pb, uns)
verifie("échange au 1 → ≤ 10 ms", ech is not None and ech <= 10, f"{ech} ms")
pb3 = b_tard.copy()
pb3[:cut + d] = 0
ech = M.echange(pa, pb3, uns)
verifie("échange 30 ms après le 1 → vu", ech is not None and ech >= 20, f"{ech} ms")
verifie("échange : B sans graves → None", M.echange(pa, np.zeros_like(pb), uns) is None)

# 4. Trous
x = a.copy()
x[SR:SR + int(0.03 * SR)] = 0
x[3 * SR:3 * SR + int(0.01 * SR)] = 0
t = M.trous(x)
verifie("trous : 30 ms vus, 10 ms ignorés", len(t) == 1 and t[0][0] == SR and abs(t[0][1] - 30) < 1, str(t))
verifie("trous : silence propre au morceau exclu", M.trous(x, [(SR - 10, SR + SR)]) == [])

# 5. Clics
x = a.copy()
pos = 5 * SR + beat // 3  # hors attaque
x[pos:] += 0.3
verifie("clics : marche de 0,3 vue", M.clics(x, [pos], beat=beat) == [pos])
verifie("clics : borne propre (même sur une attaque) ignorée", M.clics(a, [5 * SR, pos, 0, L - 1], beat=beat) == [])

# 6. Niveau et crête
lo, hi = M.sonie(a, a[:4 * SR], b[-4 * SR:])
verifie("sonie : même niveau → ≈ 0 dB", -1 < lo <= hi < 1, f"[{lo:.2f} ; {hi:.2f}]")
y = a.copy()
y[6 * SR:10 * SR] *= 0.5
lo, hi = M.sonie(y, a[:4 * SR], b[-4 * SR:])
verifie("sonie : creux de −6 dB → vu", lo < -4, f"[{lo:.2f} ; {hi:.2f}]")
verifie("crête en dBFS", abs(M.crete_dbfs(np.full((10, 2), 0.5, np.float32)) + 6.02) < 0.01)

# 7. Courbes
auto = [Automation("a", "volume", 100, 0.5), Automation("b", "passe_bas_hz", 100, 1000.0),
        Automation("a", "graves", 100, 0.0)]
verifie("courbes : conformes", M.courbes(auto, [("a", "volume", 100, 0.52), ("b", "passe_bas_hz", 100, 1080),
                                               ("a", "graves", 100, 0.001)]) == [])
err = M.courbes(auto, [("a", "volume", 100, 0.7), ("b", "passe_bas_hz", 100, 1200), ("b", "volume", 100, 1)])
verifie("courbes : 3 écarts vus (gain, fréquence, automation absente)", len(err) == 3, "; ".join(err))

print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
sys.exit(0 if ok else 1)
