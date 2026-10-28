"""Rendus sans recouvrement : C1 (coupe sur phrase), C2 (écho), C3 (frein), R2 (bord à bord). Spec §4 et §8.

Le segment couvre la dernière mesure de A avant sortieA (la jonction est un 1) puis le début de B : il remplace le
flux sans rien consommer de l'avance, sauf le trou du saut (critère 9.1-9 : 0 ± 1 temps).
"""
import numpy as np

from transitions import outils as O
from transitions import primitives as P
from transitions.outils import CH, SR

SILENCE_DBFS = -50.0
RACCORD_R2_MS = 20
ENTREE_B_MS = 5


def _z(n):
    return np.zeros((int(n), CH), np.float32)


def _gain(m, p):
    m.wait(p.debut_b + 2 * p.bar_b)
    return O.gain(m.read(max(0, p.fin_a - 4 * p.bar_a), p.fin_a), m.read(p.debut_b, p.debut_b + 2 * p.bar_b))


def _base(m, p, n_b):
    """A : sa dernière mesure, coupée au 1 (10 ms) ; B : n_b échantillons depuis le 1, entrée en 5 ms.
    Rend (debut, n_a, L, pa, pb, va, vb, g)."""
    n_a = p.bar_a
    L = n_a + int(n_b)
    debut = p.fin_a - n_a
    m.wait(p.debut_b + int(n_b))
    g = _gain(m, p)
    va = P.Env(L, 1).marche(n_a, 0)
    vb = P.Env(L, 0).marche(n_a, 1, ms=ENTREE_B_MS, fin=False)
    pa = O.fit(m.read(debut, p.fin_a), L)
    pb = np.concatenate([_z(n_a), m.read(p.debut_b, p.debut_b + int(n_b)) * g])
    return debut, n_a, L, pa, pb, va, vb, g


def _journal(reperes, va, vb):
    j = P.Journal(P.milieux(reperes))
    for piste, v in (("a", va), ("b", vb)):
        j.courbe(piste, "volume", v())
        j.courbe(piste, "graves", v())  # basses : celles de A partent avec A, celles de B arrivent avec B, au 1
    return j


def c1(m, o, p):
    """Coupe sur phrase : A 1 → 0 sur 10 ms qui finissent au 1, B 0 → 1 sur 5 ms à partir du 1."""
    debut, n_a, L, pa, pb, va, vb, g = _base(m, p, p.bar_b)
    rep, uns = P.grille_seche(n_a, p.bar_a / 4, p.bar_b / 4, L)
    j = _journal(rep, va, vb)
    pistes = {"a": pa * va()[:, None], "b": pb * vb()[:, None]}
    return P.assembler(m, "C1", debut, pistes, p.debut_b + p.bar_b, g, rep, uns, j,
                       {"jonction": n_a, "bornes": [0, n_a, L]})


def c2(m, o, p):
    """Écho : le dernier temps de A part dans un écho de ½ temps (rétroaction 0,5, passe-haut 300 Hz, passe-bas
    8 → 2 kHz), A sec coupé au 1, B sec et plein au 1, la queue s'éteint en `lin` sur 2 à 4 mesures de B."""
    q = int(o.params.get("queue_mesures", 2))
    beat = p.bar_a / 4
    debut, n_a, L, pa, pb, va, vb, g = _base(m, p, q * p.bar_b)
    s0 = n_a - int(round(beat))
    hit = m.read(p.fin_a - int(round(beat)), p.fin_a)
    wet, hz = P.echo(hit, L - s0, beat / 2)
    ve = P.Env(L, 1).vers(n_a, L, 0, "lin")
    fx = np.concatenate([_z(s0), wet]) * ve()[:, None]
    rep, uns = P.grille_seche(n_a, beat, p.bar_b / 4, L)
    j = _journal(rep, va, vb)
    j.courbe("effet", "volume", ve(), de=s0)
    j.courbe("effet", "passe_bas_hz", np.concatenate([np.full(s0, hz[0]), hz]), de=s0)
    j.courbe("effet", "passe_haut_hz", np.full(L, 300.0), de=s0)
    pistes = {"a": pa * va()[:, None], "b": pb * vb()[:, None], "effet": fx.astype(np.float32)}
    return P.assembler(m, "C2", debut, pistes, p.debut_b + q * p.bar_b, g, rep, uns, j,
                       {"jonction": n_a, "queue_mesures": q, "bornes": [0, n_a, L]})


def c3(m, o, p):
    """Frein : sur le dernier temps de A (2 temps sous 90 BPM, ou `frein_temps`), la vitesse passe de 1 à 0 en
    courbe exponentielle, hauteur non conservée, passe-bas 16 kHz → 500 Hz. B sec et plein au 1."""
    beat = p.bar_a / 4
    bpm = 60 * SR / beat
    nt = int(o.params.get("frein_temps", 2 if bpm < 90 else 1))
    debut, n_a, L, pa, pb, va, vb, g = _base(m, p, p.bar_b)
    nf = int(round(nt * beat))
    s = n_a - nf
    fr = O.frein(m.read(p.fin_a - nf, p.fin_a), nf)
    pa = np.concatenate([pa[:s], fr, _z(L - n_a)])
    vit = np.concatenate([np.ones(s), O.vitesse_frein(nf), np.zeros(L - n_a)])
    hz = np.concatenate([np.full(s, 16000.0), P.courbe("expo", nf, 16000.0, 500.0), np.full(L - n_a, 500.0)])
    rep, uns = P.grille_seche(n_a, beat, p.bar_b / 4, L)
    j = _journal(rep, va, vb)
    j.courbe("a", "vitesse", vit, a=n_a)
    j.courbe("a", "passe_bas_hz", hz, de=s, a=n_a)
    pistes = {"a": pa * va()[:, None], "b": pb * vb()[:, None]}
    return P.assembler(m, "C3", debut, pistes, p.debut_b + p.bar_b, g, rep, uns, j,
                       {"jonction": n_a, "frein_temps": nt, "bornes": [0, n_a, L]})


def _bord_sonore(x, seuil, depuis_la_fin):
    """Index du dernier (ou premier) échantillon au-dessus du seuil, None si tout est sous le seuil."""
    i = np.flatnonzero(np.abs(x).max(axis=1) > seuil)
    if not len(i):
        return None
    return int(i[-1]) + 1 if depuis_la_fin else int(i[0])


def r2(m, o, p):
    """Bord à bord : silence final de A et silence initial de B (< −50 dBFS) retirés, raccord de 20 ms. A joue
    jusqu'à sa fin réelle."""
    seuil = 10 ** (SILENCE_DBFS / 20)
    fen = 10 * SR
    a0 = max(0, p.fin_a - fen)
    k = _bord_sonore(m.read(a0, p.fin_a), seuil, True)
    a_fin = p.fin_a if k is None else a0 + k
    m.wait(p.debut_b + fen)
    k = _bord_sonore(m.read(p.debut_b, p.debut_b + fen), seuil, False)
    b_deb = p.debut_b if k is None else p.debut_b + k
    la, lb, x = p.bar_a // 2, p.bar_b // 2, int(RACCORD_R2_MS / 1000 * SR)
    L = la + lb - x
    debut = a_fin - la
    g = O.gain(m.read(max(0, a_fin - 4 * p.bar_a), a_fin), m.read(b_deb, b_deb + 2 * p.bar_b))
    va = P.Env(L, 1).vers(la - x, la, 0, "lin")
    vb = P.Env(L, 0).vers(la - x, la, 1, "lin")
    pa = O.fit(m.read(debut, a_fin), L)
    pb = np.concatenate([_z(la - x), m.read(b_deb, b_deb + lb) * g])
    rep, uns = P.grille_seche(la - x // 2, p.bar_a / 4, p.bar_b / 4, L)
    j = _journal(rep, va, vb)
    pistes = {"a": pa * va()[:, None], "b": pb * vb()[:, None]}
    return P.assembler(m, "R2", debut, pistes, b_deb + lb, g, rep, uns, j,
                       {"jonction": la - x // 2, "silence_a_s": (p.fin_a - a_fin) / SR,
                        "silence_b_s": (b_deb - p.debut_b) / SR, "bornes": [0, la - x, la, L]})
