"""C4 (montée en boucle, loop roll) et le secours (transition prête trop tard). Spec §4 et §8."""
import numpy as np

from transitions import outils as O
from transitions import primitives as P
from transitions.outils import CH, SR

# m1 : unité de 2 temps × 2 ; m2 : 1 temps × 2, ½ temps × 2, ¼ temps × 4 (en temps de A)
ROULEMENT = [2, 2, 1, 1, 0.5, 0.5, 0.25, 0.25, 0.25, 0.25]


def _z(n):
    return np.zeros((int(n), CH), np.float32)


def roulement(boucle, beat):
    """Les 2 mesures de roulement à partir de la mesure bouclée (chaque morceau repart du début de la mesure)."""
    bornes = np.round(np.concatenate([[0], np.cumsum(ROULEMENT)]) * beat).astype(int)
    return np.concatenate([O.edges(boucle[:e - s], 2) for s, e in zip(bornes[:-1], bornes[1:])])


def c4(m, o, p):
    """A s'arrête au 1 ; sa dernière mesure réelle est rejouée en roulement pendant 2 mesures (passe-haut 20 Hz →
    800 Hz, volume 1 → 0,8), puis B entre sec et plein au 1. Regagne 2 mesures d'avance."""
    beat = p.bar_a / 4
    n_a, n_r, n_b = p.bar_a, 2 * p.bar_a, p.bar_b
    L = n_a + n_r + n_b
    debut = p.fin_a - n_a
    m.wait(p.debut_b + 2 * n_b)
    reel = m.read(debut, p.fin_a)
    g = O.gain(m.read(max(0, p.fin_a - 4 * p.bar_a), p.fin_a), m.read(p.debut_b, p.debut_b + 2 * n_b))
    roll = O.fit(roulement(reel, beat), n_r)
    hz = np.concatenate([np.full(n_a, 20.0), P.courbe("expo", n_r, 20.0, 800.0), np.full(n_b, 800.0)])
    roll = P.filtre_balaye(roll, hz[n_a:n_a + n_r], "haut")
    j1 = n_a + n_r  # le 1 où B entre
    va = P.Env(L, 1).vers(n_a, j1, 0.8, "lin").marche(j1, 0)
    vb = P.Env(L, 0).marche(j1, 1, ms=5, fin=False)
    pa = np.concatenate([reel, roll, _z(n_b)]) * va()[:, None]
    pb = np.concatenate([_z(j1), m.read(p.debut_b, p.debut_b + n_b) * g]) * vb()[:, None]
    rep, uns = P.grille_seche(j1, beat, p.bar_b / 4, L)
    j = P.Journal(P.milieux(rep))
    j.courbe("a", "volume", va())
    j.courbe("a", "passe_haut_hz", hz, de=n_a, a=j1)
    j.courbe("b", "volume", vb())
    j.courbe("b", "graves", vb())
    return P.assembler(m, "C4", debut, {"a": pa, "b": pb}, p.debut_b + n_b, g, rep, uns, j,
                       {"jonction": j1, "regagne_s": n_r / SR, "bornes": [0, n_a, j1, L]})


def secours(m, o, p):
    """Transition prête trop tard ou échelle refusée alors que Spotify a déjà sauté : A perd ses graves sur son
    dernier temps, sa dernière mesure tourne deux fois pendant que B monte dessous, filtré, sur deux mesures. Ne coûte
    pas d'avance ; rendu court, il doit être prêt vite (porté de l'ancien rendu.secours)."""
    beat = p.bar_a // 4
    n = 2 * p.bar_b
    a = m.read(p.fin_a - p.bar_a, p.fin_a)
    head = O.sweep(a[-beat:], lo=lambda t: 20 * (300 / 20) ** t)
    m.wait(p.debut_b + n)
    loop = O.loop(O.band(a, lo=300), n) * O.smooth(n, 1.0, 0.3)
    rise = O.sweep(m.read(p.debut_b, p.debut_b + n), lo=lambda t: 1500 * (60 / 1500) ** t) * O.smooth(n, 0.0, 1.0)
    pa = np.concatenate([head, loop])
    pb = np.concatenate([_z(beat), rise])
    L = len(pa)
    rep, uns = P.grille_seche(beat, p.bar_a / 4, p.bar_b / 4, L)
    return P.assembler(m, "secours", p.fin_a - beat, {"a": pa, "b": pb}, p.debut_b + n, 1.0, rep, uns,
                       P.Journal(P.milieux(rep)), {"bornes": [0, beat, L]})
