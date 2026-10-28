"""Vérifie hors ligne chaque rendu du catalogue v2 (C1-C8, R1, R2, secours) sur des morceaux de synthèse.

Pour chaque rendu, à tempo égal (120/120) et proche (120/124, étiré) : valeurs saines, raccords sans saut avec le flux
aux deux bouts, avance (9.1-9), courbes conformes au §4 (9.1-7, valeurs attendues réécrites ici depuis la spec),
basses (9.1-2), échange sur le 1 (9.1-3), trous (9.1-4), clics (9.1-5), niveau O5 (9.1-6), calage (9.1-1).
Puis : refus (tempos), variantes (C7 16, C8 8, C2 queue 4, C3 lent), sans grille, B décalé, recalage de la fin de A.
Usage : python3 -I proto/e2/test_rendu.py
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synthese as S  # noqa: E402
from transitions import calage as K  # noqa: E402
from transitions import mesures as M  # noqa: E402
from transitions.boucle import secours  # noqa: E402
from transitions.catalogue import FICHES  # noqa: E402
from transitions.outils import SR, Refus  # noqa: E402
from transitions.primitives import milieux  # noqa: E402

ok = True
# O5 n'est pas tenable par construction pour ces deux effets (spec §4 contre O5) : rapporté, pas bloquant
ECARTS_O5 = {"C4": "roulement sous passe-haut 800 Hz et volume 0,8", "C8": "A sous passe-haut, B sous passe-bas"}


def verifie(label, cond, detail=""):
    global ok
    print(f"  {'ok' if cond else '✗ '} {label}{' : ' + detail if detail else ''}")
    ok &= bool(cond)


# ─── Courbes attendues, d'après le §4 de la spec ────────────────────────────────────────────────────────────

def _up(x):
    return math.sin(math.pi / 2 * min(1, max(0, x)))


def _down(x):
    return math.cos(math.pi / 2 * min(1, max(0, x)))


def _lin(v0, v1, x):
    x = min(1, max(0, x))
    return v0 + (v1 - v0) * x


def _expo(f0, f1, x):
    return f0 * (f1 / f0) ** min(1, max(0, x))


def attendu(ident, r, T):
    """[(piste, param, t, valeur)] au milieu de chaque temps."""
    pts = milieux(r.reperes)
    out = []

    def add(piste, param, f, de=0, a=None):
        for t in pts:
            if t >= de and (a is None or t < a):
                out.append((piste, param, int(t), float(f(t))))
    if ident in ("C5", "C6", "C7", "C8", "R1"):
        u = r.reperes[::4] if ident != "R1" else [r.reperes[0], r.reperes[-1]]
        L = u[-1]
        if ident == "C5":
            add("a", "mediums", lambda t: _down(t / L), a=L)
            add("a", "aigus", lambda t: _down(t / L), a=L)
            add("b", "mediums", lambda t: _up(t / L), a=L)
            add("b", "aigus", lambda t: _up(t / L), a=L)
            add("a", "graves", lambda t: 1 if t < u[1] else 0, a=L)
            add("b", "graves", lambda t: 0 if t < u[1] else 1, a=L)
        elif ident == "C6":
            add("b", "volume", lambda t: _up(t / u[1]), a=L)
            add("b", "mediums", lambda t: 0.5 if t < u[1] else 1, a=L)
            add("b", "aigus", lambda t: 1, a=L)
            add("b", "graves", lambda t: 0 if t < u[2] else 1, a=L)
            add("a", "mediums", lambda t: _lin(1, 0.5, t / u[2]) if t < u[2] else _lin(0.5, 0, (t - u[2]) / (u[3] - u[2])), a=L)
            add("a", "aigus", lambda t: 1 if t < u[2] else _lin(1, 0, (t - u[2]) / (u[4] - u[2])), a=L)
            add("a", "graves", lambda t: 1 if t < u[2] else 0, a=L)
            add("a", "volume", lambda t: 1 if t < u[3] else _down((t - u[3]) / (u[4] - u[3])), a=L)
        elif ident == "C7":
            mid = u[T // 2]
            add("b", "volume", lambda t: _up(t / mid), a=L)
            add("b", "aigus", lambda t: _lin(0.5, 1, t / mid), a=L)
            add("b", "graves", lambda t: 0 if t < mid else 1, a=L)
            add("a", "volume", lambda t: 1 if t < mid else _down((t - mid) / (L - mid)), a=L)
            add("a", "aigus", lambda t: 1 if t < mid else _lin(1, 0, (t - mid) / (L - mid)), a=L)
            add("a", "graves", lambda t: 1 if t < mid else 0, a=L)
        elif ident == "C8":
            last = u[T - 1]
            add("b", "passe_bas_hz", lambda t: _expo(400, 16000, t / L), a=L)
            add("b", "volume", lambda t: _up(t / u[T // 2]), a=L)
            add("b", "graves", lambda t: 0, a=L)
            add("a", "passe_haut_hz", lambda t: _expo(20, 250, t / last) if t < last else _expo(250, 1000, (t - last) / (L - last)), a=L)
            add("a", "volume", lambda t: _lin(1, 0.7, t / L), a=L)
            add("a", "graves", lambda t: 1, a=L)
        else:  # R1
            add("a", "volume", lambda t: _down(t / L), a=L)
            add("b", "volume", lambda t: _up(t / L), a=L)
            add("b", "graves", lambda t: 0, a=L)
        return out
    j = r.infos["jonction"]
    n = len(r.seg)
    if ident != "C4":  # C4 : volume de A propre au roulement, ci-dessous
        add("a", "volume", lambda t: 1 if t < j else 0)
    add("b", "volume", lambda t: 0 if t < j else 1)
    if ident == "C2":
        s0 = j - int(round(r.reperes[1] - r.reperes[0]))
        add("effet", "volume", lambda t: 1 if t < j else _lin(1, 0, (t - j) / (n - j)), de=s0)
        add("effet", "passe_bas_hz", lambda t: _expo(8000, 2000, (t - s0) / (n - s0)), de=s0)
        add("effet", "passe_haut_hz", lambda t: 300, de=s0)
    if ident == "C3":
        beat = r.reperes[1] - r.reperes[0]
        s = j - int(round(r.infos["frein_temps"] * beat))
        k = 4.0
        add("a", "vitesse", lambda t: 1 if t < s else (math.exp(-k * (t - s) / (j - s)) - math.exp(-k)) / (1 - math.exp(-k)), a=j)
        add("a", "passe_bas_hz", lambda t: _expo(16000, 500, (t - s) / (j - s)), de=s, a=j)
    if ident == "C4":
        bar = 4 * (r.reperes[1] - r.reperes[0])
        n_a = j - 2 * bar
        add("a", "volume", lambda t: 1 if t < n_a else (_lin(1, 0.8, (t - n_a) / (2 * bar)) if t < j else 0))
        add("a", "passe_haut_hz", lambda t: _expo(20, 800, (t - n_a) / (2 * bar)), de=n_a, a=j)
    return out


# ─── Contrôles communs ──────────────────────────────────────────────────────────────────────────────────────

def controle(ident, m, p, r, T, bpm_b):
    beat = p.bar_a / 4
    gap = (m.start_b - m.end_a) / beat
    seg = r.seg
    j0 = float(np.abs(seg[0] - m.read(r.debut, r.debut + 1)[0]).max())
    j1 = float(np.abs(seg[-1] - m.read(r.reprise - 1, r.reprise)[0] * r.gain).max())
    bord = int(0.15 * SR)  # aux bords, le segment rejoint le flux (gain 1) : sa crête est celle du morceau
    cr = M.crete_dbfs(seg[bord:-bord])
    verifie("valeurs saines, crête ≤ −0,3 dBFS hors raccords", np.isfinite(seg).all() and cr <= -0.3
            and np.abs(seg).max() <= 1, f"crête {cr:.2f} dBFS")
    verifie("raccords avec le flux", j0 < 0.02 and j1 < 0.02, f"{j0:.3f} / {j1:.3f}")
    verifie("pistes de même longueur que le segment", all(len(v) == len(seg) for v in r.pistes.values()))
    conso = ((r.reprise - r.debut) - len(seg)) / beat - gap  # en temps de A, trou du saut retiré
    if ident == "C4":
        verifie("avance regagnée ≥ 1,5 mesure", -conso >= 6, f"{-conso / 4:.2f} mesure")
    else:
        verifie(f"avance consommée {4 * T} temps ± 1", abs(conso - 4 * T) <= 1, f"{conso:+.2f} temps")
    e = M.courbes(r.automations, attendu(ident, r, T))
    verifie("courbes conformes au §4 (±1 dB, ±10 %)", not e and len(r.automations) >= len(r.reperes) - 1,
            "; ".join(e[:3]) or f"{len(r.automations)} automations")
    rap = M.rapport(r, p, complet=True)
    verifie("basses superposées ≤ 1 temps", rap["basses_ms"] <= beat / SR * 1000, f"{rap['basses_ms']} ms")
    if ident != "R2" and not (ident == "R1" and bpm_b != m.bpm_a):  # R2 et R1 non étiré : pas de 1 commun
        verifie("échange des graves sur un 1 (±10 ms)", rap["echange_ms"] is not None and rap["echange_ms"] <= 10,
                f"{rap['echange_ms']} ms")
    verifie("pas de trou > 20 ms", not rap["trous"], str(rap["trous"]))
    verifie("pas de clic aux bornes", not rap["clics"], str(rap["clics"]))
    s = rap["sonie_db"]
    if ident in ECARTS_O5 and not (-3 <= s[0] and s[1] <= 2):
        print(f"  ~  niveau O5 hors bornes, écart connu ({ECARTS_O5[ident]}) : {s}")
    else:
        verifie("niveau O5 dans [−3 ; +2] dB", -3 <= s[0] and s[1] <= 2, str(s))
    if ident in ("C5", "C6", "C7", "C8"):
        verifie("calage ≤ 20 ms", abs(rap["calage_ms"]) <= 20, f"{rap['calage_ms']} ms, netteté {rap['nettete']}")
    return rap


for bpm_b in (120, 124):
    for ident in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "R1", "R2"):
        m = S.Mem(bpm_b, riche=True)
        p = m.place()
        o = S.ordre(ident, bpm_b=bpm_b)
        r = FICHES[ident].rendu(m, o, p)
        print(f"-- {ident}, B à {bpm_b} BPM : {len(r.seg) / SR:.2f} s, gain {r.gain:.2f}")
        controle(ident, m, p, r, o.bars, bpm_b)

print("-- variantes")
for ident, bars, params, bpm_a in (("C7", 16, {}, 120), ("C8", 8, {}, 120), ("C2", 0, {"queue_mesures": 4}, 120),
                                   ("C3", 0, {"frein_temps": 2}, 120), ("C3", 0, {}, 85)):
    m = S.Mem(bpm_a, bpm_a=bpm_a, riche=True, mesures_a=24 if bpm_a > 100 else 20)
    p = m.place()
    o = S.ordre(ident, bars, params=params, bpm_a=bpm_a, bpm_b=bpm_a)
    r = FICHES[ident].rendu(m, o, p)
    print(f"-- {ident} T={bars} {params} à {bpm_a} BPM : {len(r.seg) / SR:.2f} s")
    controle(ident, m, p, r, bars, bpm_a)
    if ident == "C3":
        verifie("frein de 2 temps", r.infos["frein_temps"] == 2)

print("-- refus et calage")
for ident, bpm_b in (("C5", 140), ("C7", 127)):
    m = S.Mem(bpm_b, riche=True)
    try:
        FICHES[ident].rendu(m, S.ordre(ident, bpm_b=bpm_b), m.place())
        verifie(f"{ident} à {bpm_b} BPM refusé", False)
    except Refus as e:
        verifie(f"{ident} à {bpm_b} BPM refusé", True, str(e))
m = S.Mem(127, riche=True)
r = FICHES["C5"].rendu(m, S.ordre("C5", bpm_b=127), m.place())
verifie("C5 à 5,8 % accepté (C7 seulement ≤ 5 %)", r.transition == "C5")

m = S.Mem(120, riche=True)
r = FICHES["C6"].rendu(m, S.ordre("C6"), m.place(grille=False))
verifie("C6 sans grille de Spotify (calage sur la pulsation)", abs(r.infos["calage_ms"]) <= 20, f"{r.infos['calage_ms']:+.1f} ms")

m = S.Mem(120, off=int(0.04 * SR), riche=True)  # B annoncé 40 ms trop tôt : la boucle de correction doit rattraper
try:
    r = FICHES["C5"].rendu(m, S.ordre("C5"), m.place())
    verifie("B décalé de 40 ms corrigé à ≤ 20 ms", abs(r.infos["calage_ms"]) <= 20, f"{r.infos['calage_ms']:+.1f} ms")
except Refus as e:
    verifie("B décalé de 40 ms : refus (calage)", "calage" in str(e), str(e))

m = S.Mem(124, riche=True)
r = secours(m, S.ordre("R1"), m.place())
j0 = float(np.abs(r.seg[0] - m.read(r.debut, r.debut + 1)[0]).max())
j1 = float(np.abs(r.seg[-1] - m.read(r.reprise - 1, r.reprise)[0]).max())
print("-- secours")
verifie("secours : raccords et valeurs saines", np.isfinite(r.seg).all() and j0 < 0.02 and j1 < 0.02 and
        np.abs(r.seg).max() <= 1, f"{j0:.3f} / {j1:.3f}")

print("-- recalage de la fin de A sur ses temps (grid_end, sans grille de Spotify)")
for bpm_a in (95, 120, 128, 140, 170):
    beat_f = 60 / bpm_a * SR
    m = S.Mem(120, bpm_a=bpm_a)
    errs = []
    g0 = int(np.floor((m.end_a - 4 * beat_f) / beat_f) * beat_f)
    for given, ahead in ((g0 - int(0.1 * SR), 0), (g0 - int(0.02 * SR), int(0.04 * SR))):
        e, _ = K.grid_end(m, given, beat_f, ahead)
        target = np.floor(given / beat_f) * beat_f if not ahead else np.ceil(given / beat_f) * beat_f
        errs.append((e - target) / SR * 1000)
    verifie(f"{bpm_a} BPM : écarts {', '.join(f'{x:+.0f}' for x in errs)} ms", all(abs(x) <= 12 for x in errs))

print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
sys.exit(0 if ok else 1)
