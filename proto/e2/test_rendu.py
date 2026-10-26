"""Vérifie hors ligne chaque préréglage sur des morceaux de synthèse (grosse caisse + nappe).

A à 120 BPM, puis 350 ms de silence (le trou de Spotify), puis B au tempo voulu.
Contrôles : pas d'erreur, pas de NaN, crête sous 1, raccords sans saut avec le flux aux deux bouts,
avance conservée (le segment dure au moins ce qu'il consomme), regain demandé obtenu, mélange refusé
quand les tempos sont trop éloignés, recalage du premier temps.
Usage : python3 -I proto/e2/test_rendu.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recettes import CH, PRESETS, SR, Refus, band  # noqa: E402
from rendu import DOUX, RENDERERS, entry_kick, grid_end  # noqa: E402


def track(bpm, seconds, note):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    beat = 60 / bpm
    phase = t % beat
    kick = np.sin(2 * np.pi * (50 + 100 * np.exp(-phase * 30)) * phase) * np.exp(-phase * 12)
    pad = 0.15 * np.sin(2 * np.pi * note * t)
    # charleston sur chaque demi-temps : des aigus, comme dans la vraie musique (un filtre à 2 kHz ne rend
    # pas le morceau muet)
    hat = 0.05 * np.random.default_rng(1).standard_normal(n) * np.exp(-(t % (beat / 2)) * 60)
    hat = band(hat[:, None].astype(np.float32), lo=5000)[:, 0]  # une vraie charleston n'a que des aigus
    return np.stack([kick * 0.6 + pad + hat] * CH, axis=1).astype(np.float32)


class Mem:
    log = staticmethod(lambda *a: None)

    def __init__(self, bpm_b, off=0, bpm_a=120):
        a, b = track(bpm_a, 40, 220), track(bpm_b, 40, 330)
        gap = np.zeros((int(0.35 * SR) + off, CH), np.float32)
        self.buf = np.concatenate([a, gap, b])
        self.end_a, self.start_b = len(a), len(a) + len(gap)

    def read(self, a, b):
        assert 0 <= a <= b <= len(self.buf), "lecture hors mémoire"
        return self.buf[int(a):int(b)].copy()

    def wait(self, n):
        assert n <= len(self.buf), "la recette demande plus de son que la mémoire n'en a"


BAR = int(2 * SR)  # une mesure de A à 120 BPM
ok = True


def check(label, m, out, lost_max, gain_min=None):
    """Valeurs saines, raccords, et avance perdue (consommé - joué) sous lost_max secondes."""
    global ok
    start, seg, resume, g = out
    lost = ((resume - start) - len(seg)) / SR
    j0 = float(np.abs(seg[0] - m.read(start, start + 1)[0]).max())
    j1 = float(np.abs(seg[-1] - m.read(resume - 1, resume)[0] * g).max())
    # après la reprise, le flux joue B × g : il ne doit pas dépasser la crête non plus
    post = float(np.abs(m.read(resume, min(resume + 2 * BAR, len(m.buf)))).max()) * g
    # aucun trou dans le segment (le frein et le retour finissent volontairement en silence)
    quiet = np.abs(seg).max(axis=1) < 1e-4
    run = longest = 0
    for q in quiet:
        run = run + 1 if q else 0
        longest = max(longest, run)
    holes = longest > 0.005 * SR and label not in ("Frein", "Retour arrière")
    good = (np.isfinite(seg).all() and np.abs(seg).max() <= 1.0 and post <= 1.0 and not holes
            and j0 < 0.02 and j1 < 0.02 and lost <= lost_max)
    if gain_min is not None:
        good &= -lost >= gain_min
    print(f"{label:34s} {len(seg) / SR:6.2f} s, avance {-lost:+6.2f} s, raccords {j0:.3f}/{j1:.3f}, gain {g:.2f}"
          f"{'  trou de ' + str(round(longest / SR * 1000)) + ' ms' if holes else ''}{'' if good else '  ✗'}")
    ok &= bool(good)


# Styles doux : B lancé 4 mesures (de B) avant son drop ; tempos égal, proche (étiré), double, éloigné.
# Le trou du saut et le recalage du drop (moins d'un tiers de temps) peuvent être pris sur l'avance.
for bpm_b in (120, 126, 110, 240, 150):
    print(f"-- B à {bpm_b} BPM")
    pre = int(16 * 60 / bpm_b * SR)
    for name in sorted(DOUX):
        m = Mem(bpm_b)
        out = RENDERERS[name](m, m.end_a, m.start_b, BAR, 120 / bpm_b, pre=pre)
        check(PRESETS[name]["label"], m, out, 0.6)
        if bpm_b == 120 and name == "montee":  # 4 mesures réelles + 4 de prolongement + 2 mesures d'atterrissage
            ok &= abs(len(out[1]) / SR - 20.0) < 0.01
            print(f"   drop de B {len(out[1]) / SR - 12.0:.2f} s après la fin de A (attendu 8,00 : 4 mesures)")

print("-- B lancé 8 mesures avant son drop (réglage actuel de l'extension) : il monte sur 8 mesures")
for name in ("montee", "montee_courte", "filtre", "frein_doux"):
    m = Mem(126)
    out = RENDERERS[name](m, m.end_a, m.start_b, BAR, 120 / 126, pre=int(32 * 60 / 126 * SR))
    check(PRESETS[name]["label"], m, out, 0.6)

print("-- regain d'avance (2 mesures demandées)")
for name in ("montee", "filtre", "drop_swap"):
    m = Mem(120)
    pre = BAR if name == "drop_swap" else 4 * BAR
    check(PRESETS[name]["label"], m, RENDERERS[name](m, m.end_a, m.start_b, BAR, 1.0, pre=pre, extra=2 * BAR),
          0.6, gain_min=2 * BAR / SR - 0.4)

print("-- avance au-dessus de la cible : arrondi à la mesure la plus proche (au plus une demi-mesure rendue)")
for name, bpm_b in (("montee", 120), ("echo_doux", 120), ("frein_doux", 126)):
    m = Mem(bpm_b)
    out = RENDERERS[name](m, m.end_a, m.start_b, BAR, 120 / bpm_b, pre=int(16 * 60 / bpm_b * SR), extra=-BAR)
    check(f"{PRESETS[name]['label']} (B à {bpm_b})", m, out, BAR / SR / 2 + 0.4)

print("-- sans avance de B (repli d'un mélange) : B monte sur ses premières mesures")
m = Mem(120)
check("Montée courte", m, RENDERERS["montee_courte"](m, m.end_a, m.start_b, BAR, 1.0), 0.6)

print("-- drop swap (B lancé 1 mesure avant son drop) et mélange (pas d'avance de B)")
m = Mem(124)
check("Drop swap", m, RENDERERS["drop_swap"](m, m.end_a, m.start_b, BAR, 120 / 124, pre=int(4 * 60 / 124 * SR)), 0.0)
m = Mem(124)
check("Drop swap sans avance de B", m, RENDERERS["drop_swap"](m, m.end_a, m.start_b, BAR, 120 / 124), 0.0)
for bpm_b in (124, 246):
    m = Mem(bpm_b)
    check(f"Mélange à {bpm_b} BPM", m, RENDERERS["melange"](m, m.end_a, m.start_b, BAR, 120 / bpm_b), 18.0)
m = Mem(102, bpm_a=100)  # sous 120 BPM, l'extension demande un mélange de 4 mesures
end_a = int(np.floor(m.end_a / (0.6 * SR)) * 0.6 * SR)  # fin de A sur un de ses temps, comme après grid_end
check("Mélange de 4 mesures à 100 BPM", m,
      RENDERERS["melange"](m, end_a, m.start_b, int(4 * 60 / 100 * SR), 100 / 102, bars=4), 11.0)

m = Mem(140)  # 14 % d'écart : le mélange doit refuser
try:
    RENDERERS["melange"](m, m.end_a, m.start_b, BAR, 120 / 140)
    print("mélange à 14 % d'écart : ✗ aurait dû refuser")
    ok = False
except Refus as e:
    print(f"mélange à 14 % d'écart : refus attendu ({e})")

m = Mem(120, off=int(0.25 * SR))  # B décalé d'un demi-temps : le recalage doit le rattraper ou refuser
try:
    RENDERERS["melange"](m, m.end_a, m.start_b - int(0.26 * SR), BAR, 1.0)
    print("mélange à contretemps : accepté (le recalage sur la grosse caisse a rattrapé le décalage)")
except Refus as e:
    print(f"mélange à contretemps : refus ({e})")

print("-- B à peine moins fort que A mais à la crête (master à 0 dBFS) : le gain ne doit pas faire écrêter")
m = Mem(120)
m.buf[m.start_b:] *= 0.99 / np.abs(m.buf[m.start_b:]).max()
m.buf[:m.end_a] *= 1.0 / np.abs(m.buf[:m.end_a]).max()
m.buf[m.start_b:, :] = np.where(np.abs(m.buf[m.start_b:]) > 0.5, m.buf[m.start_b:], m.buf[m.start_b:] * 0.6)
check("Montée, B à la crête", m, RENDERERS["montee"](m, m.end_a, m.start_b, BAR, 1.0, pre=4 * BAR), 0.6)

print("-- secours (transition prête trop tard) : un temps de fondu, il saute le reste")
m = Mem(124)
check("Secours", m, RENDERERS["secours"](m, m.end_a, m.start_b, BAR, 120 / 124), 1.0)

# Fin de A annoncée 100 ms après un temps : recalée sur le temps d'avant ; 20 ms avant un temps avec 40 ms de
# marge sûre : avancée sur ce temps. Plusieurs tempos : un temps n'est pas un nombre entier de pas de 5 ms.
for bpm_a in (95, 120, 128, 140, 170):
    beat_f = 60 / bpm_a * SR
    m = Mem(120, bpm_a=bpm_a)
    errs = []
    g0 = int(np.floor(m.end_a / beat_f) * beat_f)  # un temps de A (les grosses caisses sont en k × temps)
    for given, ahead in ((g0 - int(0.1 * SR), 0), (g0 - int(0.02 * SR), int(0.04 * SR))):
        e, _ = grid_end(m, given, beat_f, ahead)
        target = np.floor(given / beat_f) * beat_f if not ahead else np.ceil(given / beat_f) * beat_f
        errs.append((e - target) / SR * 1000)
    good = all(abs(x) <= 12 for x in errs)  # résolution de l'enveloppe : 5 ms
    print(f"recalage de la fin de A à {bpm_a} BPM : écarts {', '.join(f'{x:+.0f}' for x in errs)} ms (attendu ≈ 0)"
          f"{'' if good else '  ✗'}")
    ok &= good

m = Mem(120)
k = entry_kick(m, m.start_b, BAR // 4)
print(f"recalage du premier temps de B (attaque pile au début) : {k} échantillons (attendu ≈ 0)")
ok &= k < int(0.01 * SR)
print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
sys.exit(0 if ok else 1)
