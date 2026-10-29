"""Catalogue v1 (spec §4) et échelle de repli au rendu (§8, ADR 0005).

`rendre` essaie o.transition puis o.replis ; il passe au suivant sur Refus, netteté < 1,5 pour une superposition,
calage > 20 ms après correction, voix au-delà des seuils (ADR 0002), avance < avance_requise(T, mesure).
"""
import dataclasses
import time
from collections import namedtuple

import numpy as np

from transitions import boucle, seches, superposees
from transitions import calage as K
from transitions import voix as V
from transitions.contrat import BARS_PERMIS
from transitions.outils import SR, Refus

Fiche = namedtuple("Fiche", "rendu bars_permis famille exige replis")

FICHES = {
    "C1": Fiche(seches.c1, BARS_PERMIS["C1"], "sec", frozenset(), ("R2",)),
    "C2": Fiche(seches.c2, BARS_PERMIS["C2"], "sec", frozenset(), ("C1", "R2")),
    "C3": Fiche(seches.c3, BARS_PERMIS["C3"], "effet", frozenset(), ("C1", "R2")),
    "C4": Fiche(boucle.c4, BARS_PERMIS["C4"], "effet", frozenset({"voix_boucle"}), ("C1", "R2")),
    "C5": Fiche(superposees.c5, BARS_PERMIS["C5"], "superpose", frozenset({"grille", "voix_superposees"}), ("R1", "R2")),
    "C6": Fiche(superposees.c6, BARS_PERMIS["C6"], "superpose", frozenset({"grille", "voix_intro_b"}),
                ("C5", "R1", "R2")),
    "C7": Fiche(superposees.c7, BARS_PERMIS["C7"], "superpose", frozenset({"grille", "voix_superposees"}),
                ("C5", "R1", "R2")),
    "C8": Fiche(superposees.c8, BARS_PERMIS["C8"], "superpose", frozenset({"grille", "voix_superposees"}),
                ("C5", "R1", "R2")),
    "R1": Fiche(superposees.r1, BARS_PERMIS["R1"], "repli", frozenset(), ("R2",)),
    "R2": Fiche(seches.r2, BARS_PERMIS["R2"], "repli", frozenset(), ()),
}
MARGE_AVANCE_S = 8.0  # temps de rendu (C7/C8 étirés : jusqu'à 4 s) + 2 s de marge (critère 9.1-12)


def avance_requise(T, bar_s):
    """Avance (s) qu'exige un recouvrement de T mesures, même règle que dj-choix.js (revue QA 1) : le rendu attend
    que B soit en mémoire (T + 2 mesures pour la grille, puis T mesures + 2 mesures) avant de calculer, et doit être
    prêt avant que la lecture n'atteigne le début du segment (T mesures avant le saut). 0 sans recouvrement."""
    return (2 * T + 2) * bar_s + MARGE_AVANCE_S if T > 0 else 0.0
VOIX_SUPERPOSEES_MAX = 2   # O4 : au-delà, repli
INTRO_B_MESURES = 4        # C6 : les 4 premières mesures de B doivent être sans voix


def _voix(m, debut, bar, k):
    x = m.read(debut, debut + k * bar)
    return np.asarray(V.voix_par_mesure(x, np.arange(k + 1) * bar), dtype=float)


def verifier_voix(m, ident, T, p):
    """(raison du repli ou None, nombre de mesures de voix superposées ou None), d'après V3 sur la mémoire."""
    fiche = FICHES[ident]
    seuil = V.SEUIL_REPLI_RENDU
    if "voix_boucle" in fiche.exige:
        v = _voix(m, p.fin_a - p.bar_a, p.bar_a, 1)
        if len(v) and v[0] >= seuil:
            return f"voix mesurée sur la mesure bouclée ({v[0]:.2f})", None
    if "voix_intro_b" in fiche.exige:
        m.wait(p.debut_b + INTRO_B_MESURES * p.bar_b)
        v = _voix(m, p.debut_b, p.bar_b, INTRO_B_MESURES)
        k = int(np.count_nonzero(v >= seuil))
        if k:
            return f"voix mesurée sur {k} mesure(s) de l'intro de B", None
    if T > 0 and fiche.famille == "superpose":
        m.wait(p.debut_b + T * p.bar_b)
        va = _voix(m, p.fin_a - T * p.bar_a, p.bar_a, T)
        vb = _voix(m, p.debut_b, p.bar_b, T)
        k = int(np.count_nonzero((va >= seuil) & (vb >= seuil)))
        if "voix_superposees" in fiche.exige and k > VOIX_SUPERPOSEES_MAX:
            return f"voix superposées sur {k} mesures (> {VOIX_SUPERPOSEES_MAX})", k
        return None, k
    return None, None


def rendre(m, o, p, *, avance):
    """Rend (Rendu, replis faits au rendu [{de, vers, raison, ou: "rendu"}]). `avance` en échantillons. Lève Refus
    si toute l'échelle échoue (e2.py joue alors le secours). Une erreur inattendue d'un rendu est journalisée et
    traitée comme un refus : la lecture ne doit jamais s'arrêter."""
    echelle = [o.transition, *o.replis]
    replis = []
    for i, ident in enumerate(echelle):
        fiche = FICHES[ident]
        T = o.bars if i == 0 else fiche.bars_permis[0]
        oi = o if i == 0 else dataclasses.replace(o, transition=ident, bars=T, params={})
        raison = None
        voix_k = None
        try:
            besoin = avance_requise(T, o.a.bar_s)  # même entrée que dj-choix.js : a.bar_s de l'ordre
            if T > 0 and avance / SR < besoin:
                raise Refus(f"avance {avance / SR:.1f} s < {besoin:.1f} s ((2 × {T} + 2) mesures + "
                            f"{MARGE_AVANCE_S:.0f} s)")
            if "grille" in fiche.exige and min(p.nettete_a, p.nettete_b) < K.NETTETE_MIN:
                raise Refus(f"netteté {min(p.nettete_a, p.nettete_b):.2f} < {K.NETTETE_MIN}")
            raison, voix_k = verifier_voix(m, ident, T, p)
            if raison:
                raise Refus(raison)
            t0 = time.time()
            r = fiche.rendu(m, oi, p)
            r.infos["rendu_s"] = round(time.time() - t0, 3)
            r.infos["voix_mesures"] = voix_k
            if fiche.famille == "superpose" and abs(r.infos.get("calage_ms") or 0) > K.CALAGE_MAX_MS:
                raise Refus(f"calage {r.infos['calage_ms']:+.0f} ms > {K.CALAGE_MAX_MS:.0f} ms")
            return r, replis
        except Refus as e:
            raison = str(e)
        except Exception as e:  # erreur de rendu : journalisée, repli comme un refus
            raison = f"erreur de rendu : {e!r}"
            m.log(f"{ident} : {raison}")
        if i + 1 < len(echelle):
            replis.append({"de": ident, "vers": echelle[i + 1], "raison": raison, "ou": "rendu"})
            m.log(f"repli au rendu : {ident} → {echelle[i + 1]} ({raison})")
        else:
            replis.append({"de": ident, "vers": "secours", "raison": raison, "ou": "rendu"})
            err = Refus(f"toute l'échelle refusée ({ident} : {raison})")
            err.replis = replis  # pour le rapport du secours
            raise err
    raise Refus("échelle vide")
