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
from transitions.contrat import Automation, Place, Rendu  # noqa: E402
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
# Coupe dont B n'a pas de basse sur son 1 (essai direct 13, a13 et g13 : +444 et +386 ms, un temps de B) : les graves
# passent à l'entrée de B, pas à sa 1re note de basse.
b_sur_2 = S.track(120, 16, 330, basse=True, seed=2, basse_des=1)
pb4 = b_sur_2.copy()
pb4[:cut] = 0
ech = M.echange(pa, pb4, uns)
verifie("échange d'une coupe, basse de B sur le 2 → au 1 (pas un temps plus tard)", ech is not None and ech <= 10,
        f"{ech} ms")
pb5 = b_sur_2.copy()
pb5[:cut + d] = 0
ech = M.echange(pa, pb5, uns)
verifie("échange d'une coupe : B entré 30 ms après le 1 → vu", ech is not None and 25 <= ech <= 35, f"{ech} ms")
# Coupe (QA de l'essai 13) : B entre pile au 1 de A mais 40 ms après son propre 1 (ses temps arrivent 40 ms trop tôt).
# L'entrée seule ne le voit pas ; la phase des attaques de B après la jonction, si.
d40 = int(0.04 * SR)
pb7 = np.zeros_like(b)
pb7[cut:len(b) - d40] = b[cut + d40:]
ech0 = M.echange(pa, pb7, uns)
ech = M.echange(pa, pb7, uns, beat_b=beat)
ph = M.phase_entree_b(pb7, cut, beat)
verifie("coupe : B entré au 1 de A mais 40 ms après son propre 1 → vu par la phase de ses attaques",
        ech0 <= 10 and ech is not None and 35 <= ech <= 50 and ph is not None and ph[0] < 0,
        f"entrée seule {ech0} ms, avec la phase {ech} ms ({ph[0]:+.0f} ms)" if ph else f"{ech0} / {ech}")
ech = M.echange(pa, pb, uns, beat_b=beat)
verifie("coupe : B entré sur son propre 1 → ≤ 10 ms avec la phase", ech is not None and ech <= 10, f"{ech} ms")
pb8 = np.zeros_like(b)
pb8[cut:] = bruit[cut:]
ech = M.echange(pa, pb8, uns, beat_b=beat)
verifie("coupe : B sans attaques (bruit) → phase non mesurable, seule l'entrée compte",
        M.phase_entree_b(pb8, cut, beat) is None and ech is not None and ech <= 10, f"{ech} ms")
# Superposition : A et B sonnent ensemble ; la rampe des graves (30 ms) finit 60 ms après le 1 → vue
from transitions import primitives as P  # noqa: E402
ga, gb = P.echange_basses(L, cut + 2 * d)
pa6 = P.eq3(a, graves=ga())
pb6 = P.eq3(b, graves=gb())
ech = M.echange(pa6, pb6, uns)
verifie("échange d'une superposition, rampe finie 60 ms après le 1 → vu", ech is not None and 30 <= ech <= 60,
        f"{ech} ms")
ga, gb = P.echange_basses(L, cut)
ech = M.echange(P.eq3(a, graves=ga()), P.eq3(b, graves=gb()), uns)
verifie("échange d'une superposition au 1 → ≤ 10 ms", ech is not None and ech <= 10, f"{ech} ms")

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
# Raccords d'un rendu réel (essai direct 13) : un segment coupé en pleine note n'a pas de clic à ses bouts ;
# sans le flux, rapport(complet=True) ne les juge pas ; avec le flux, un vrai clic au raccord est vu.
c0 = 3 * SR + int(0.15 * SR)
c0 += int(np.argmax(np.abs(a[c0:c0 + int(0.05 * SR), 0])))
c1 = 6 * SR + int(0.15 * SR)
c1 += int(np.argmax(np.abs(a[c1:c1 + int(0.05 * SR), 0])))
k = SR // 10
seg = a[c0:c1].copy()
rr = Rendu(debut=c0, seg=seg, reprise=c1, gain=1.0, transition="C1", pistes={}, reperes=np.array([]),
           uns=np.array([]), automations=[], infos={"bornes": [0, beat, len(seg)]})
pl = Place(fin_a=c1, debut_b=c1, bar_a=4 * beat, bar_b=4 * beat, beats_a=None, beats_b=None, nettete_a=3.0,
           nettete_b=3.0)
r0 = M.rapport(rr, pl, complet=True)
r1 = M.rapport(rr, pl, complet=True, avant=a[c0 - k:c0], apres=a[c1:c1 + k])
saut = a[c1:c1 + k].copy()
saut += 0.3
r2 = M.rapport(rr, pl, complet=True, avant=a[c0 - k:c0], apres=saut)
verifie("rapport : segment coupé en pleine note, sans flux → pas de faux clic aux bouts", r0["clics"] == [],
        f"{r0['clics']}, amplitude aux bouts {float(np.abs(seg[0]).max()):.2f} / {float(np.abs(seg[-1]).max()):.2f}")
verifie("rapport : avec le flux, raccords propres → pas de clic", r1["clics"] == [], str(r1["clics"]))
verifie("rapport : avec le flux, marche de 0,3 au raccord de fin → vue", r2["clics"] == [len(seg)], str(r2["clics"]))

# 6. Niveau et crête
lo, hi = M.sonie(a, a[:4 * SR], b[-4 * SR:])
verifie("sonie : même niveau → ≈ 0 dB", -1 < lo < 1 and -1 < hi < 1, f"[{lo:.2f} ; {hi:.2f}]")
y = a.copy()
y[6 * SR:10 * SR] *= 0.5
lo, hi = M.sonie(y, a[:4 * SR], b[-4 * SR:])
verifie("sonie : creux de −6 dB → vu", lo < -4, f"[{lo:.2f} ; {hi:.2f}]")
# O5 redéfini (essai direct 13, spec §14) : relatif aux niveaux propres de A et de B, pas à leur moyenne
calme = b * 0.1  # B 20 dB sous A (intro calme)
y = np.concatenate([a[:4 * SR], calme[:4 * SR]])
lo, hi = M.sonie(y, a[:4 * SR], calme[-4 * SR:])
verifie("sonie : A puis B 20 dB plus calme → pas un défaut", -3 <= lo and hi <= 2, f"[{lo:.2f} ; {hi:.2f}]")
verifie("sonie : écart des niveaux propres ≈ −20 dB", abs(M.ecart_niveaux(a[:4 * SR], calme[-4 * SR:]) + 20) < 1)
y2 = np.concatenate([a[:4 * SR], calme[:4 * SR] * 0.5, calme[:4 * SR]])
lo, hi = M.sonie(y2, a[:4 * SR], calme[-4 * SR:])
verifie("sonie : creux de −6 dB sous le plus calme des deux → vu", lo < -4, f"[{lo:.2f} ; {hi:.2f}]")
y3 = np.concatenate([calme[:4 * SR], a[:4 * SR] * 2, a[:4 * SR]])
lo, hi = M.sonie(y3, calme[:4 * SR], a[-4 * SR:])
verifie("sonie : bosse de +6 dB au-dessus du plus fort des deux → vue", hi > 4, f"[{lo:.2f} ; {hi:.2f}]")
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
