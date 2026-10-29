"""Rendus avec recouvrement : C5 (fondu calé), C6 (mix 3 bandes), C7 (échange de basses), C8 (montée filtrée) et
R1 (fondu court). Spec §3, §4, §8.

A joue [sortieA − T ; sortieA] sous B [entreeB ; entreeB + T] sur une grille commune (calage.caler_superposition) ;
les mesures m1…mT commencent aux repères dst[0], dst[4]… ; le « 1 final » est dst[4T]. Le segment finit un temps de B
après ce 1 final, pour que l'arrivée des graves de B y soit entière. Avance consommée : T mesures.
"""
import numpy as np

from transitions import calage as K
from transitions import outils as O
from transitions import primitives as P
from transitions.outils import CH, SR


def _superposer(m, o, p, nom, T, ecart_max, courbes):
    """Squelette commun. `courbes(n, u, L)` (u = premiers temps des mesures, u[T] = L) rend
    {"a": {param: Env}, "b": {...}} ; params : volume, graves, mediums, aigus, passe_bas_hz, passe_haut_hz."""
    c = K.caler_superposition(m, p, T, ecart_max=ecart_max)
    dst = c["dst"]
    L = len(c["a"])
    tail = int(round(c["d2"]))
    n = L + tail
    m.wait(c["b_fin"] + tail + 2 * p.bar_b)
    g = O.gain(m.read(c["a0"], p.fin_a), m.read(c["b0"], c["b_fin"]))
    bb = c["b"].copy()
    if c["etire"]:  # B étiré rejoint B lu tel quel : fondu de 5 ms (le tempo glissé finit sur celui de B)
        x = int(0.005 * SR)
        bb[-x:] = bb[-x:] * O.ramp(x, 1, 0) + m.read(c["b_fin"] - x, c["b_fin"]) * O.ramp(x, 0, 1)
    src = {"a": O.fit(c["a"], n), "b": np.concatenate([bb, m.read(c["b_fin"], c["b_fin"] + tail)]) * g}
    u = dst[::4].astype(np.int64)
    env = courbes(n, u, L)
    j = P.Journal(P.milieux(dst))
    pistes = {}
    for k in ("a", "b"):
        e = {q: v() for q, v in env[k].items()}
        x = src[k]
        if "passe_haut_hz" in e:
            x = P.filtre_balaye(x, e["passe_haut_hz"], "haut")
        if "passe_bas_hz" in e:
            x = P.filtre_balaye(x, e["passe_bas_hz"], "bas")
        x = P.eq3(x, e.get("graves", 1.0), e.get("mediums", 1.0), e.get("aigus", 1.0))
        vol = P.lisser(e.get("volume", np.ones(n)))
        pistes[k] = (x * np.asarray(vol, np.float32)[:, None]).astype(np.float32)
        for q in ("volume", "graves", "mediums", "aigus", "passe_bas_hz", "passe_haut_hz"):
            if q in e:
                j.courbe(k, q, e[q], a=L)
            elif q in ("volume", "graves", "mediums", "aigus"):
                j.courbe(k, q, np.ones(n), a=L)
    m.log(f"{nom} : {T} mesures, calage {c['calage_ms']:+.0f} ms (netteté {c['nettete']:.1f}), gain de B {g:.2f}"
          f"{', étiré' if c['etire'] else ''}")
    return P.assembler(m, nom, c["a0"], pistes, c["b_fin"] + tail, g, dst, u, j,
                       {"calage_ms": c["calage_ms"], "nettete": c["nettete"], "recouvrement": (0, L), "T": T,
                        "bornes": [0, L, n]})


def c5(m, o, p):
    """Fondu calé, 2 mesures : médiums et aigus en `cos` (A 1 → 0, B 0 → 1) sur m1-m2, graves échangés au 1 de m2."""
    def courbes(n, u, L):
        ga, gb = P.echange_basses(n, u[1])
        fa, fb = P.Env(n, 1).vers(0, L, 0, "cos"), P.Env(n, 0).vers(0, L, 1, "cos")
        return {"a": {"graves": ga, "mediums": fa, "aigus": fa}, "b": {"graves": gb, "mediums": fb, "aigus": fb}}
    return _superposer(m, o, p, "C5", 2, 0.06, courbes)


def c6(m, o, p):
    """Mix 3 bandes, 4 mesures (radio edit)."""
    def courbes(n, u, L):
        ga, gb = P.echange_basses(n, u[2])
        return {
            "b": {"volume": P.Env(n, 0).vers(u[0], u[1], 1, "cos"), "mediums": P.Env(n, 0.5).marche(u[1], 1),
                  "aigus": P.Env(n, 1), "graves": gb},
            "a": {"mediums": P.Env(n, 1).vers(u[0], u[2], 0.5, "lin").vers(u[2], u[3], 0, "lin"),
                  "aigus": P.Env(n, 1).vers(u[2], u[4], 0, "lin"), "graves": ga,
                  "volume": P.Env(n, 1).vers(u[3], u[4], 0, "cos")}}
    return _superposer(m, o, p, "C6", 4, 0.06, courbes)


def c7(m, o, p):
    """Échange de basses, 8 ou 16 mesures : B monte en `cos` sur la première moitié, A descend sur la seconde,
    graves échangés au 1 de m(T/2 + 1)."""
    T = o.bars if o.bars in (8, 16) else 8

    def courbes(n, u, L):
        mid = u[T // 2]
        ga, gb = P.echange_basses(n, mid)
        return {"b": {"volume": P.Env(n, 0).vers(0, mid, 1, "cos"), "aigus": P.Env(n, 0.5).vers(0, mid, 1, "lin"),
                      "graves": gb},
                "a": {"volume": P.Env(n, 1).vers(mid, L, 0, "cos"), "aigus": P.Env(n, 1).vers(mid, L, 0, "lin"),
                      "graves": ga}}
    return _superposer(m, o, p, "C7", T, 0.05, courbes)


def c8(m, o, p):
    """Montée filtrée, 4 ou 8 mesures : B sous un passe-bas 400 Hz → 16 kHz, A sous un passe-haut 20 → 250 Hz puis
    1 kHz sur la dernière mesure ; graves de B pleins au 1 final, A coupé au 1 final."""
    T = o.bars if o.bars in (4, 8) else 4

    def courbes(n, u, L):
        ga, gb = P.echange_basses(n, L)
        return {"b": {"passe_bas_hz": P.Env(n, 400).vers(0, L, 16000, "expo"),
                      "volume": P.Env(n, 0).vers(0, u[T // 2], 1, "cos"), "graves": gb},
                "a": {"passe_haut_hz": P.Env(n, 20).vers(0, u[T - 1], 250, "expo").vers(u[T - 1], L, 1000, "expo"),
                      "volume": P.Env(n, 1).vers(0, L, 0.7, "lin").marche(L, 0), "graves": ga}}
    return _superposer(m, o, p, "C8", T, 0.06, courbes)


R1_ETIRE_MAX = 0.25    # au-delà (tempo double, moitié…), B n'est pas étiré : seul son 1 final est posé sur celui de A
R1_NETTETE_MIN = K.PHASE_NETTETE_MIN   # phase d'un morceau non fiable (calage.phase_fiable) : temps estimés gardés
R1_ACCORD_MIN = K.PHASE_ACCORD_MIN
R1_PHASE_MS = 120      # recherche de la phase de chaque morceau autour de ses temps estimés
R1_TEMPS_B = 16        # temps de B (depuis debut_b) sur lesquels sa phase est mesurée, si la grille de Spotify les a


_grille = K.grille_temps   # temps réels de Spotify autour d'une ancre (déplacé dans calage, partagé avec C5-C8)


def _grilles_r1(p):
    """Temps de A (les 8 avant fin_a, puis fin_a) et de B (debut_b puis jusqu'à R1_TEMPS_B − 1 suivants, 9 au
    moins), d'après la grille de Spotify recalée si elle est là."""
    ta = _grille(p.beats_a, p.fin_a, 8, 1, p.bar_a / 4, 1)
    tb = _grille(p.beats_b, p.debut_b, 0, R1_TEMPS_B + 1, p.bar_b / 4, 9)
    return ta, tb


def _phase(x, marks, muet=None):
    """calage.phase_attaques à ±R1_PHASE_MS ; `muet` : fin du silence ajouté avant le début estimé du morceau (à
    ~±100 ms du vrai) : ce qui précède muet + 100 ms est ignoré (la marche silence → son n'est pas une attaque ; une
    nappe seule y prenait une netteté de 13)."""
    return K.phase_attaques(x, marks, R1_PHASE_MS, None if muet is None else muet + int(0.1 * SR))


phase_fiable = K.phase_fiable


_MARGE = int(R1_PHASE_MS / 1000 * SR) + int(0.02 * SR)   # son lu autour des temps : recherche ± R1_PHASE_MS


def _son_a(m, p, ta):
    """Son de A autour de ses 8 derniers temps `ta[:-1]`, silence après fin_a (B n'est pas A) : (x, début de x)."""
    r = _MARGE
    lo = int(round(ta[0])) - r
    if lo >= 0:
        return O.fit(m.read(lo, p.fin_a), p.fin_a - lo + r), lo
    return O.fit(np.concatenate([np.zeros((-lo, CH), np.float32), m.read(0, p.fin_a)]), p.fin_a - lo + r), lo


def calage_r1(m, p, ta, tb, ea, eb):
    """Calage de R1 tel qu'il s'entend : (vrai 1 de B − vrai 1 de A) en ms, et netteté. Vrai 1 de A : phase de ses
    attaques sur ses 8 derniers temps (`ta[:-1]` + ea) ; vrai 1 de B : phase de ses attaques sur les 8 temps
    depuis son 1 final (`tb[4:12]` + eb), où B est lu tel quel et a d'ordinaire ses attaques. Avant (QA de l'essai
    13), le calage se mesurait sur la 1re mesure de B, dans le segment : une entrée de B sans attaques rapportait de
    faux échecs (+105 ms rapportés pour −5 ms vérifiés, g07). (None, netteté) si l'un des deux n'a pas d'attaques
    nettes (`phase_fiable`) : non mesurable."""
    r = _MARGE
    xa, lo = _son_a(m, p, ta)
    da, sa, aa = _phase(xa, ta[:-1] + ea - lo)
    mb = tb[4:min(12, len(tb) - 1) + 1] + eb
    b0, b1 = int(round(mb[0])) - r, int(round(mb[-1])) + r
    m.wait(b1)
    db, sb, ab = _phase(m.read(b0, b1), mb - b0)
    nettete = float(min(sa, sb))
    if not (phase_fiable(sa, aa) and phase_fiable(sb, ab)):
        return None, nettete
    return float((db - da) / SR * 1000), nettete


def phases_r1(m, p):
    """Phase réelle de A (ses 8 derniers temps avant fin_a) et de B (jusqu'à 16 temps depuis debut_b) par rapport
    aux temps estimés, mesurée sur le son de chacun : (décalage de A, décalage de B, netteté). Le son hors du
    morceau (après fin_a, avant debut_b : trou du saut, autre morceau) est mis à zéro. Le décalage d'un morceau est
    nul si sa phase n'est pas fiable (`phase_fiable` : netteté < R1_NETTETE_MIN ou accord < R1_ACCORD_MIN, son
    sans batterie : nappe, bruit) : ses temps estimés sont gardés (« temps estimé », §8, §14) au lieu d'une phase
    arbitraire (jusqu'à ±115 ms, QA de l'essai 13). B est mesuré sur 4 mesures, pas 2 : une entrée calme (pas de
    grosse caisse) et syncopée donnait une phase fausse de +50 à +100 ms (g07). Netteté rendue : la plus faible des
    deux, 0 pour un morceau non fiable."""
    r = _MARGE
    ta, tb = _grilles_r1(p)
    nb = len(tb) - 1                                 # le dernier temps de gb borne la lecture
    m.wait(int(round(tb[-1])) + r)
    xa, lo = _son_a(m, p, ta)
    ea, sa, aa = _phase(xa, ta[:-1] - lo)
    xb = np.concatenate([np.zeros((r, xa.shape[1]), np.float32), m.read(p.debut_b, int(round(tb[-1])) + r)])
    eb, sb, ab = _phase(xb, r + tb[:nb] - p.debut_b, muet=r)
    if not phase_fiable(sa, aa):
        m.log(f"R1 : phase de A non fiable (netteté {sa:.1f}, accord {aa:.2f}) : temps estimés")
        ea, sa = 0, 0.0
    if not phase_fiable(sb, ab):
        m.log(f"R1 : phase de B non fiable (netteté {sb:.1f}, accord {ab:.2f}) : temps estimés")
        eb, sb = 0, 0.0
    return ea, eb, float(min(sa, sb))


def r1(m, o, p):
    """Fondu court : 1 mesure en `cos`, graves de B coupés jusqu'au 1 final ; jamais de refus de calage.
    Calage (essai direct 13, §14) : la phase réelle de A et de B est mesurée sur leur son (`phases_r1`) ; le
    segment commence au vrai 1 de la dernière mesure de A, et la mesure de B qui précède son 1 final est étirée
    (stretch_map, 1 mesure seulement) pour que chacun de ses temps tombe sur ceux de A : le 1 final de B est
    celui de A, où les graves s'échangent. Après ce 1, B est lu tel quel. Temps de A et de B : ceux de Spotify
    (recalés), uniformes à défaut. Calage rapporté : `calage_r1` (None si non mesurable)."""
    ta, tb = _grilles_r1(p)
    ea, eb, nettete = phases_r1(m, p)
    debut = int(round(ta[-5])) + ea                  # vrai 1 de la dernière mesure de A
    L = int(round(ta[-1] - ta[-5]))                  # sa durée réelle
    b1 = int(round(tb[4])) + eb                      # 1 final de B (dans la mémoire)
    beat_b = (tb[4] - tb[0]) / 4
    tail = int(round(beat_b))
    n = L + tail
    m.wait(b1 + tail + 2 * p.bar_b)
    a = O.fit(m.read(debut, p.fin_a), n)             # après fin_a : silence (le son de A s'arrête au saut)
    rr = (tb[4] - tb[0]) / L
    etire = 0.005 < abs(rr - 1) <= R1_ETIRE_MAX
    b0 = int(round(tb[0])) + eb if etire else b1 - L
    src = m.read(max(0, b0), b1)
    if b0 < 0:
        src = np.concatenate([np.zeros((-b0, src.shape[1]), np.float32), src])
    k = p.debut_b - b0                               # avant debut_b, ce n'est pas B
    if k > 0:
        src[:k] = 0
    dst = np.round(ta[-5:] - ta[-5]).astype(np.int64)
    if etire:
        tete = O.fit(O.stretch_map(src, np.round(tb[:5] + eb - b0), dst), L)
        x = int(0.005 * SR)  # B étiré rejoint B lu tel quel : fondu de 5 ms
        tete[-x:] = tete[-x:] * O.ramp(x, 1, 0) + m.read(b1 - x, b1) * O.ramp(x, 0, 1)
    else:
        tete = O.fit(src, L)
    b_src = np.concatenate([tete, m.read(b1, b1 + tail)])
    g = O.gain(m.read(max(0, p.fin_a - 4 * p.bar_a), p.fin_a), m.read(b1, b1 + 2 * p.bar_b))
    b = b_src * g
    cal, net = calage_r1(m, p, ta, tb, ea, eb)
    ga, gb = P.echange_basses(n, L)
    va, vb = P.Env(n, 1).vers(0, L, 0, "cos"), P.Env(n, 0).vers(0, L, 1, "cos")
    pa = P.eq3(a, graves=ga()) * np.asarray(P.lisser(va()), np.float32)[:, None]
    pb = P.eq3(b, graves=gb()) * np.asarray(P.lisser(vb()), np.float32)[:, None]
    j = P.Journal(P.milieux(dst))
    for k_, v, gr in (("a", va, ga), ("b", vb, gb)):
        j.courbe(k_, "volume", v(), a=L)
        j.courbe(k_, "graves", gr(), a=L)
    m.log(f"R1 : phase de A {ea / SR * 1000:+.0f} ms, de B {eb / SR * 1000:+.0f} ms (netteté {nettete:.1f}), "
          f"calage {'non mesurable' if cal is None else f'{cal:+.0f} ms'}, gain de B {g:.2f}"
          f"{', étiré' if etire else ''}")
    return P.assembler(m, "R1", debut, {"a": pa.astype(np.float32), "b": pb.astype(np.float32)},
                       b1 + tail, g, dst, dst[::4], j,
                       {"calage_ms": cal, "nettete": net, "recouvrement": (0, L), "T": 1,
                        "bornes": [0, L, n], "phase_a_ms": ea / SR * 1000, "phase_b_ms": eb / SR * 1000,
                        "etire": etire})
