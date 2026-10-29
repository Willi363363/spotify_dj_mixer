"""Primitives des transitions v2 (spec §3, ADR 0006) : courbes nommées, enveloppes, EQ 3 bandes à somme plate,
échange des basses sur un 1, filtres balayés 12 dB/oct, écho calé, journal des automations.
Usage : python3 -I proto/e2/test_primitives.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transitions import outils as O  # noqa: E402
from transitions import primitives as P  # noqa: E402
from transitions.outils import CH, SR  # noqa: E402

ok = True


def verifie(label, cond, detail=""):
    global ok
    print(f"{'ok' if cond else '✗ '} {label}{' : ' + detail if detail else ''}")
    ok &= bool(cond)


def sinus(f, s=1.0, a=0.5):
    t = np.arange(int(s * SR)) / SR
    return np.stack([a * np.sin(2 * np.pi * f * t)] * CH, axis=1).astype(np.float32)


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, dtype=float) ** 2)))


def db(a, b):
    return 20 * np.log10(max(a, 1e-12) / max(b, 1e-12))


# Courbes nommées
c = P.courbe("cos", 1001, 1, 0)
d = P.courbe("cos", 1001, 0, 1)
verifie("cos : A = cos(πt/2), B = sin(πt/2), puissance constante",
        abs(c[500] - np.cos(np.pi / 4)) < 1e-3 and np.allclose(c ** 2 + d ** 2, 1, atol=1e-9))
verifie("lin : droite", np.allclose(P.courbe("lin", 11, 0, 1), np.linspace(0, 1, 11)))
k = P.courbe("carre", SR, 1, 0)
r = int(0.01 * SR)
verifie("carre : marche avec rampe de 10 ms à la fin", k[-r - 1] == 1 and k[-1] == 0 and 0.4 < k[-r // 2] < 0.6)
e = P.courbe("expo", 3, 20, 800)
verifie("expo : progression géométrique", abs(e[1] - np.sqrt(20 * 800)) < 1e-6)

# Enveloppes
env = P.Env(1000, 1).vers(100, 200, 0.5).vers(300, 400, 0, "cos")
verifie("Env : tient sa valeur entre les segments", env()[50] == 1 and env()[250] == 0.5 and env()[999] == 0)
g = np.r_[np.ones(1000), np.zeros(1000)]
gl = P.lisser(g)
w = int(0.005 * SR)
verifie("lissage anti-clic ≥ 5 ms", 0 < gl[1000 - w // 4] < 1 and gl[1000 - w] == 1 and gl[1000 + w] == 0)

# EQ 3 bandes : somme plate
rng = np.random.default_rng(0)
x = (0.3 * rng.standard_normal((SR, CH))).astype(np.float32)
lo, mid, hi = P.bandes(x)
verifie("EQ 3 bandes : graves + médiums + aigus = original", np.abs(lo + mid + hi - x).max() < 1e-5,
        f"écart max {np.abs(lo + mid + hi - x).max():.1e}")
verifie("EQ gains 1 : signal inchangé", np.abs(P.eq3(x) - x).max() < 1e-5)
for f, band, nom in ((60, 0, "graves"), (1000, 1, "médiums"), (10000, 2, "aigus")):
    s = sinus(f)
    parts = P.bandes(s)
    part = rms(parts[band][SR // 4:-SR // 4]) / rms(s[SR // 4:-SR // 4])
    verifie(f"{f} Hz dans les {nom}", part > 0.9, f"{part:.2f}")
s = sinus(60)
cut = P.eq3(s, graves=0.0)
verifie("graves coupés : 60 Hz atténué ≥ 20 dB", db(rms(cut[SR // 4:-SR // 4]), rms(s[SR // 4:-SR // 4])) < -20)
s = sinus(1000)
half = P.eq3(s, mediums=0.5)
verifie("médiums à 0,5 : 1 kHz à −6 dB (±1)", abs(db(rms(half[SR // 4:-SR // 4]), rms(s[SR // 4:-SR // 4])) + 6) < 1)
# Gains automatisés sans clic : une marche de gain sur une sinusoïde reste continue
gstep = np.r_[np.ones(SR // 2), np.zeros(SR - SR // 2)]
y = P.eq3(sinus(1000), mediums=gstep)[:, 0]
verifie("gain automatisé sans clic (pente bornée)", np.abs(np.diff(y)).max() < 0.2)

# Échange des basses
n, un = SR, SR // 2
ga, gb = P.echange_basses(n, un)
r = int(0.03 * SR)
verifie("échange : rampe de 30 ms qui finit sur le 1", ga()[un] == 0 and gb()[un] == 1 and ga()[un - r - 1] == 1
        and gb()[un - r - 1] == 0 and 0 < ga()[un - r // 2] < 1)
verifie("échange : graves de A + B = 1 (pas de creux)", np.allclose(ga() + gb(), 1))

# Filtres balayés 12 dB/oct
s = sinus(2000, 2)
y = P.filtre_balaye(s, np.full(len(s), 1000.0), "bas")
att = db(rms(y[SR // 2:-SR // 2]), rms(s[SR // 2:-SR // 2]))
verifie("passe-bas 1 kHz à 12 dB/oct : 2 kHz à −12 dB (±1,5)", abs(att + 12.3) < 1.5, f"{att:.1f} dB")
y = P.filtre_balaye(sinus(250, 2), np.full(2 * SR, 1000.0), "haut")
att = db(rms(y[SR // 2:-SR // 2]), rms(sinus(250, 2)[SR // 2:-SR // 2]))
verifie("passe-haut 1 kHz : 250 Hz à −24 dB (±2)", abs(att + 24.1) < 2, f"{att:.1f} dB")
s = sinus(3000, 4)
y = P.filtre_balaye(s, P.courbe("expo", len(s), 16000, 500), "bas")
a0, a1 = rms(y[SR // 4:SR // 2]), rms(y[-SR // 2:-SR // 4])
verifie("balayage 16 kHz → 500 Hz : 3 kHz passe au début, coupé à la fin", a0 > 0.3 and a1 < 0.05, f"{a0:.2f} → {a1:.3f}")

# Écho calé
beat = SR // 2
hit = np.zeros((beat, CH), np.float32)
hit[:200] = 0.8 * np.sin(2 * np.pi * 2000 * np.arange(200) / SR)[:, None]
wet, hz = P.echo(hit, 8 * beat, beat / 2)
env = np.abs(wet[:, 0])
pics = [float(env[int(k * beat / 2):int(k * beat / 2) + 400].max()) for k in range(1, 6)]
rapports = [pics[i + 1] / pics[i] for i in range(4)]
verifie("écho : une répétition par ½ temps, −6 dB chacune", all(0.4 < q < 0.65 for q in rapports),
        ", ".join(f"{q:.2f}" for q in rapports))
# filtres à phase nulle (ADR 0006) : un léger pré-écho non causal, sous −30 dB de la première répétition
verifie("écho : rien avant la première répétition (< −30 dB), coupé sous −60 dB", env[:beat // 2 - 50].max() < pics[0] * 0.03
        and env[int(11 * beat / 2) + 1000:].max() < 1e-3)
verifie("écho : passe-bas de 8 kHz à 2 kHz", abs(hz[0] - 8000) < 1 and abs(hz[-1] - 2000) < 1)
lo_echo = P.echo(sinus(80, 0.5, 0.8), 4 * beat, beat / 2)[0]
verifie("écho sans graves (passe-haut 300 Hz)", rms(lo_echo) < 0.05 * 0.8, f"{rms(lo_echo):.3f}")

# Frein : vitesse exponentielle de 1 à 0
v = O.vitesse_frein(1000)
verifie("frein : vitesse 1 → 0, décroissante", v[0] == 1 and abs(v[-1]) < 1e-9 and np.all(np.diff(v) <= 0))
fr = O.frein(sinus(440, 1), SR // 2)
verifie("frein : sort sans valeur figée", np.abs(fr[-50:]).max() < 0.02 and np.isfinite(fr).all())

# Journal
j = P.Journal(P.milieux([0, 100, 200, 300]))
j.courbe("a", "volume", np.linspace(1, 0, 300))
verifie("journal : une automation par temps, au milieu", [a.t for a in j.liste] == [50, 150, 250]
        and abs(j.liste[0].valeur - (1 - 50 / 299)) < 1e-9)

print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
sys.exit(0 if ok else 1)
