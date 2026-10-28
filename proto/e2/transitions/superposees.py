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
from transitions.outils import SR


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


def r1(m, o, p):
    """Fondu court : 1 mesure en `cos`, graves de B coupés jusqu'au 1 final, sans étirement ni refus de calage."""
    L = p.bar_a
    tail = int(round(p.bar_b / 4))
    n = L + tail
    debut = p.fin_a - L
    m.wait(p.debut_b + n + 2 * p.bar_b)
    a = O.fit(m.read(debut, p.fin_a), n)
    b_src = m.read(p.debut_b, p.debut_b + n)
    g = O.gain(m.read(max(0, p.fin_a - 4 * p.bar_a), p.fin_a), b_src)
    b = b_src * g
    dst = np.round(np.arange(5) * L / 4).astype(np.int64)
    ea, sa = K.grid_fit(a[:L], dst[:-1])
    eb, sb = K.grid_fit(b[:L], dst[:-1])
    ga, gb = P.echange_basses(n, L)
    va, vb = P.Env(n, 1).vers(0, L, 0, "cos"), P.Env(n, 0).vers(0, L, 1, "cos")
    pa = P.eq3(a, graves=ga()) * np.asarray(P.lisser(va()), np.float32)[:, None]
    pb = P.eq3(b, graves=gb()) * np.asarray(P.lisser(vb()), np.float32)[:, None]
    j = P.Journal(P.milieux(dst))
    for k, v, gr in (("a", va, ga), ("b", vb, gb)):
        j.courbe(k, "volume", v(), a=L)
        j.courbe(k, "graves", gr(), a=L)
    return P.assembler(m, "R1", debut, {"a": pa.astype(np.float32), "b": pb.astype(np.float32)},
                       p.debut_b + n, g, dst, dst[::4], j,
                       {"calage_ms": float(eb - ea), "nettete": float(min(sa, sb)), "recouvrement": (0, L), "T": 1,
                        "bornes": [0, L, n]})
