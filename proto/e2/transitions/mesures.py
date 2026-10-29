"""Critères automatiques 9.1 n° 1 à 7 sur le son rendu (ADR 0005).

En production, seules les mesures rapides tournent (calage, basses, échange, voix, sonie, crête) ; trous et clics
seulement dans les tests (`rapport(..., complet=True)`).
"""
import numpy as np

from transitions import calage as K
from transitions import outils as O
from transitions.outils import SR

QUASI_ZERO = 1e-4
TROU_MS = 20.0
BASSES_HZ = 150.0
BASSES_DB = -12.0
CLIC_DB = 6.0
PARAMS_HZ = {"passe_bas_hz", "passe_haut_hz"}


def calage(pa, pb, reperes):
    """Écart B − A (ms) des attaques de chaque piste par rapport à la grille commune, et netteté la plus faible."""
    ea, sa = K.grid_fit(pa, reperes)
    eb, sb = K.grid_fit(pb, reperes)
    return float(eb - ea), float(min(sa, sb))


def _puissance_graves(x, w):
    """Puissance < 150 Hz de x, lissée sur w échantillons (moyenne glissante), un point par échantillon."""
    lo = O.band(x.mean(axis=1, keepdims=True), hi=BASSES_HZ)[:, 0].astype(np.float64)
    c = np.cumsum(np.concatenate([[0.0], lo ** 2]))
    w = max(1, min(int(w), len(lo)))
    p = (c[w:] - c[:-w]) / w
    return np.concatenate([p, np.full(w - 1, p[-1] if len(p) else 0.0)])


def basses(pa, pb, beat):
    """Durée (ms) pendant laquelle les graves < 150 Hz de A et de B dépassent tous deux −12 dB de leur max commun
    (O3, critère 9.1-2 : ≤ 1 temps). Puissance lissée sur 1/16 de temps."""
    if len(pa) == 0:
        return 0.0
    w = max(int(0.005 * SR), int(beat / 16))
    ea, eb = _puissance_graves(pa, w), _puissance_graves(pb, w)
    seuil = max(ea.max(), eb.max()) * 10 ** (BASSES_DB / 10)
    if seuil <= 0:
        return 0.0
    return float(np.count_nonzero((ea > seuil) & (eb > seuil)) / SR * 1000)


def instant_echange(pa, pb, seuil_db=-10.0):
    """Échantillon où les graves de B arrivent : premier instant où leur puissance < 150 Hz (lissée 5 ms) atteint
    `seuil_db` de leur max. Avant l'échange, B est sans graves (EQ à 0, fuite ≤ −24 dB) ; avec une basse tenue, la
    montée suit la rampe, et l'instant mesuré est son milieu. None si B n'a pas de graves."""
    w = int(0.005 * SR)
    eb = _puissance_graves(pb, w)
    if eb.max() <= 0:
        return None
    i = np.flatnonzero(eb >= eb.max() * 10 ** (seuil_db / 10))
    return int(i[0]) if len(i) else None


def echange(pa, pb, uns):
    """Distance (ms) entre l'échange des graves et le premier temps le plus proche (critère 9.1-3 : ≤ 10 ms)."""
    t = instant_echange(pa, pb)
    if t is None or len(uns) == 0:
        return None
    return float(np.min(np.abs(np.asarray(uns) - t)) / SR * 1000)


def trous(x, silences=()):
    """(début, durée ms) des suites de quasi-zéros > 20 ms (critère 9.1-4), hors `silences` [(début, fin)] propres
    aux morceaux."""
    q = np.abs(x).max(axis=1) < QUASI_ZERO if x.ndim == 2 else np.abs(x) < QUASI_ZERO
    d = np.diff(np.concatenate([[0], q.astype(np.int8), [0]]))
    out = []
    for s, e in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        ms = (e - s) / SR * 1000
        if ms > TROU_MS and not any(a <= s and e <= b for a, b in silences):
            out.append((int(s), float(ms)))
    return out


def clics(x, bornes, beat=None, rayon_ms=1.0, local_ms=50.0, fc=2000.0):
    """Bornes où la dérivée seconde dépasse de plus de 6 dB sa médiane locale (critère 9.1-5). Calculée sous 2 kHz :
    un clic est large bande, alors que les charlestons et caisses claires (aigus) ont des dérivées secondes aussi
    raides qu'une marche et masqueraient tout. Valeur à la borne = max de |d²| sur ±1 ms ; médiane locale = médiane,
    sur ±50 ms, des maxima de |d²| par fenêtre de 1 ms. Avec `beat` (échantillons), la référence est aussi le pic à la
    même phase 1 et 2 temps avant et après : une borne posée sur un 1 tombe sur une attaque de grosse caisse, qui n'est
    pas un clic. Rend la liste des bornes en défaut."""
    mono = x.mean(axis=1, keepdims=True) if x.ndim == 2 else x[:, None]
    lo = O.band(mono.astype(np.float32), hi=fc)[:, 0].astype(np.float64)
    d2 = np.abs(np.diff(lo, 2))
    r, L, w = int(rayon_ms / 1000 * SR), int(local_ms / 1000 * SR), int(0.001 * SR)
    out = []
    for b in bornes:
        b = min(max(int(b), 0), len(d2) - 1)
        lo_i, hi_i = max(0, b - L), min(len(d2), b + L)
        if hi_i - lo_i < 8 * w:
            continue
        zone = d2[lo_i:hi_i][: (hi_i - lo_i) // w * w].reshape(-1, w).max(axis=1)
        ref = float(np.median(zone))
        def pic_a(c):
            return float(d2[max(0, c - r):min(len(d2), c + r + 1)].max(initial=0.0))
        pic = pic_a(b)
        if beat:
            voisins = [int(round(b + k * beat)) for k in (-2, -1, 1, 2)]
            ref = max([ref] + [pic_a(c) for c in voisins if 0 <= c < len(d2)])
        if pic > max(ref, 1e-7) * 10 ** (CLIC_DB / 20):
            out.append(int(b))
    return out


def _db(v):
    return 20 * np.log10(max(float(v), 1e-9))


def sonie(x, ref_avant, ref_apres, fenetre_s=3.0, pas_s=0.5):
    """(min, max) de la sonie court terme (fenêtres de 3 s) de x, en dB relatifs à la moyenne (en dB) des niveaux de
    A avant et de B après (O5 : dans [−3 ; +2]). Les références sont des signaux ou des niveaux déjà calculés."""
    ra = O.level(ref_avant) if isinstance(ref_avant, np.ndarray) else ref_avant
    rb = O.level(ref_apres) if isinstance(ref_apres, np.ndarray) else ref_apres
    refs = [_db(r) for r in (ra, rb) if r]
    if not refs or len(x) < int(0.4 * SR):
        return None
    ref = float(np.mean(refs))
    w, h = int(fenetre_s * SR), int(pas_s * SR)
    if len(x) <= w:
        vals = [_db(O.level(x))]
    else:
        vals = [_db(O.level(x[i:i + w])) for i in range(0, len(x) - w + 1, h)]
    return float(min(vals) - ref), float(max(vals) - ref)


def crete_dbfs(x):
    return float(_db(np.abs(x).max()) if len(x) else -180.0)


def courbes(automations, attendu, tol_db=1.0, tol_f=0.1, plancher_db=-40.0):
    """Écarts entre les automations journalisées et les valeurs attendues du §4 (liste d'Automation ou de tuples
    (piste, param, t, valeur)). Gains comparés en dB (deux gains sous le plancher sont égaux), fréquences et vitesse
    en relatif. Rend la liste des écarts (vide si conforme)."""
    index = {}
    for a in automations:
        index.setdefault((a[0], a[1]), {})[int(a[2])] = float(a[3])
    out = []
    for piste, param, t, v in attendu:
        serie = index.get((piste, param))
        if not serie:
            out.append(f"{piste}.{param} : aucune automation")
            continue
        tt = min(serie, key=lambda k: abs(k - t))
        if abs(tt - t) > int(0.002 * SR):
            out.append(f"{piste}.{param} : pas de relevé à t={t}")
            continue
        got = serie[tt]
        if param in PARAMS_HZ or param == "vitesse":
            ok = abs(got - v) <= tol_f * max(abs(v), 1e-9) or (param == "vitesse" and abs(got - v) <= 0.02)
        else:
            gd, vd = max(_db(got), plancher_db), max(_db(v), plancher_db)
            ok = abs(gd - vd) <= tol_db
        if not ok:
            out.append(f"{piste}.{param} à t={t} ({t / SR:.3f} s) : {got:.4g} au lieu de {v:.4g}")
    return out


def rapport(r, p, *, complet=False, avant=None, apres=None):
    """Le dict `mesures` de l'ADR 0001 pour un rendu. `p` : la Place (durée d'un temps de A).
    `avant`, `apres` : le flux juste avant le segment et juste après sa reprise (× gain de B), pour juger les clics
    aux deux raccords. Sans eux, les bornes à moins de 50 ms d'un bout ne sont pas jugées : la médiane locale n'y voit
    qu'un côté, et un segment réel qui finit sur un passage calme y montre un faux clic (essai direct 13)."""
    pa = r.pistes.get("a")
    pb = r.pistes.get("b")
    beat = p.bar_a / 4
    out = {"calage_ms": r.infos.get("calage_ms"), "nettete": r.infos.get("nettete"),
           "basses_ms": None, "echange_ms": None, "voix_mesures": r.infos.get("voix_mesures"),
           "sonie_db": None, "crete_dbfs": round(crete_dbfs(r.seg), 2)}
    if pa is not None and pb is not None:
        out["basses_ms"] = round(basses(pa, pb, beat), 1)
        e = echange(pa, pb, r.uns)
        out["echange_ms"] = None if e is None else round(e, 1)
    s = sonie(r.seg, r.infos.get("ref_a"), r.infos.get("ref_b"))
    out["sonie_db"] = None if s is None else [round(s[0], 2), round(s[1], 2)]
    for k in ("calage_ms", "nettete"):
        if out[k] is not None:
            out[k] = round(float(out[k]), 2)
    if complet:
        out["trous"] = trous(r.seg, r.infos.get("silences", ()))
        bornes = [int(b) for b in r.infos.get("bornes", ())]
        if avant is not None and apres is not None:
            k = len(avant)
            x = np.concatenate([avant, r.seg, apres]).astype(np.float32)
            out["clics"] = [b - k for b in clics(x, [b + k for b in bornes], beat=beat)]
        else:
            bord = int(0.05 * SR)
            out["clics"] = clics(r.seg, [b for b in bornes if bord <= b <= len(r.seg) - bord], beat=beat)
    return out
