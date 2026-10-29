"""Primitives communes des transitions v2 (spec §3, ADR 0006), numpy seul.

- Courbes nommées `lin`, `cos` (puissance constante), `carre` (marche avec rampe anti-clic de 10 ms).
- `Env` : enveloppe par échantillon construite par segments (`vers`, `marche`), lissée ≥ 5 ms à l'emploi.
- `bandes` / `eq3` : EQ 3 bandes par FFT à phase nulle, amplitudes Linkwitz-Riley d'ordre 4 (200 Hz, 4 kHz), somme
  plate à l'arrondi près.
- `echange_basses` : graves de A 1 → 0 et de B 0 → 1 sur 30 ms, la rampe finit sur le 1.
- `filtre_balaye` : passe-bas ou passe-haut 12 dB/oct dont la coupure suit une courbe (Hz par échantillon).
- `echo` : répétitions à ½ temps × rétroaction^k, passe-haut 300 Hz, passe-bas balayé 8 → 2 kHz, coupé sous −60 dB.
- `Journal` : automations relevées au milieu de chaque temps (critère 9.1-7).
- `assembler` : somme des pistes, limiteur et raccords (outils.finir), niveaux de référence → contrat.Rendu.
"""
import numpy as np

from transitions import outils as O
from transitions.contrat import Automation, Rendu
from transitions.outils import CH, SR

FC = (200.0, 4000.0)
RAMPE_CARRE_MS = 10
RAMPE_BASSES_MS = 30
LISSAGE_MS = 5


def courbe(nom, n, v0, v1):
    """n valeurs de v0 à v1 (v1 atteinte au dernier échantillon). `cos` : en montée sin(πt/2), en descente
    cos(πt/2) (puissance constante quand A descend et B monte sur le même intervalle)."""
    n = int(n)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0.0, 1.0, n)
    if nom == "lin":
        return v0 + (v1 - v0) * t
    if nom == "cos":
        if v1 >= v0:
            return v0 + (v1 - v0) * np.sin(np.pi * t / 2)
        return v1 + (v0 - v1) * np.cos(np.pi * t / 2)
    if nom == "expo":  # fréquences : progression géométrique
        return v0 * (v1 / v0) ** t
    if nom == "carre":
        r = min(n, int(RAMPE_CARRE_MS / 1000 * SR))
        return np.concatenate([np.full(n - r, v0), v0 + (v1 - v0) * np.linspace(0, 1, r)])
    raise ValueError(f"courbe inconnue : {nom}")


class Env:
    """Enveloppe de n échantillons, valeur de départ v ; chaque segment tient sa valeur d'arrivée ensuite."""

    def __init__(self, n, v):
        self.n = int(n)
        self.v = np.full(self.n, float(v))

    def vers(self, t0, t1, v1, nom="lin"):
        t0, t1 = max(0, int(round(t0))), min(self.n, int(round(t1)))
        if t1 > t0:
            v0 = self.v[t0]
            self.v[t0:t1] = courbe(nom, t1 - t0, v0, v1)
        self.v[max(t0, t1):] = v1
        return self

    def marche(self, t, v1, ms=RAMPE_CARRE_MS, fin=True):
        """Marche vers v1 au point t, en rampe de `ms` qui finit (fin=True) ou commence à t."""
        r = int(ms / 1000 * SR)
        return self.vers(t - r, t, v1) if fin else self.vers(t, t + r, v1)

    def __call__(self):
        return self.v


def lisser(g, ms=LISSAGE_MS):
    """Moyenne glissante de `ms` (anti-clic sur les gains) ; un scalaire est rendu tel quel."""
    if np.isscalar(g):
        return float(g)
    g = np.asarray(g, dtype=np.float64)
    w = max(1, int(ms / 1000 * SR))
    if len(g) < 2 or w < 2:
        return g
    pad = np.pad(g, (w // 2, w - 1 - w // 2), mode="edge")
    c = np.cumsum(np.concatenate([[0.0], pad]))
    return (c[w:] - c[:-w]) / w


def taille_rapide(n):
    """Plus petite taille ≥ n de la forme 2^a 3^b 5^c : la FFT de numpy est lente sur une taille à grand facteur
    premier (C7 de 8 mesures : 5 s au lieu de 0,3 s, critère 9.1-12 manqué sur une machine chargée)."""
    n = int(n)
    best = 1 << max(0, (n - 1).bit_length())
    p5 = 1
    while p5 < best:
        p35 = p5
        while p35 < best:
            q = p35
            while q < n:
                q *= 2
            best = min(best, q)
            p35 *= 3
        p5 *= 5
    return best


def bandes(x, fc=FC):
    """(graves, médiums, aigus) de x par FFT à phase nulle ; graves = |H_bas(fc0)|, aigus = 1 − |H_bas(fc1)|
    (amplitudes LR4 : 1 / (1 + (f/fc)^4)), médiums = le reste. graves + médiums + aigus = x."""
    if len(x) == 0:
        z = x.astype(np.float32)
        return z, z, z
    n = taille_rapide(2 * len(x))
    f = np.fft.rfftfreq(n, 1 / SR)[:, None]
    X = np.fft.rfft(x, n=n, axis=0)
    hb = 1 / (1 + (f / fc[0]) ** 4)
    hh = 1 - 1 / (1 + (f / fc[1]) ** 4)
    lo = np.fft.irfft(X * hb, n=n, axis=0)[:len(x)]
    hi = np.fft.irfft(X * hh, n=n, axis=0)[:len(x)]
    return lo.astype(np.float32), (x - lo - hi).astype(np.float32), hi.astype(np.float32)


def _col(g):
    g = lisser(g)
    return g if np.isscalar(g) else np.asarray(g, dtype=np.float32)[:, None]


def eq3(x, graves=1.0, mediums=1.0, aigus=1.0, fc=FC):
    """x avec un gain par bande (scalaires ou tableaux par échantillon, lissés 5 ms)."""
    lo, mid, hi = bandes(x, fc)
    return (lo * _col(graves) + mid * _col(mediums) + hi * _col(aigus)).astype(np.float32)


def echange_basses(n, un, ms=RAMPE_BASSES_MS):
    """Enveloppes des graves (A, B) sur n échantillons : seul moment où les deux graves coexistent, une rampe de
    `ms` qui finit sur le 1 `un` (échantillon)."""
    r = int(ms / 1000 * SR)
    return Env(n, 1).vers(un - r, un, 0), Env(n, 0).vers(un - r, un, 1)


def filtre_balaye(x, hz, genre, ordre=2):
    """Passe-bas (`genre="bas"`) ou passe-haut (`"haut"`) dont la coupure suit `hz` (tableau par échantillon de x),
    pente ordre × 6 dB/oct (12 dB/oct par défaut, biquad de la spec)."""
    hz = np.asarray(hz, dtype=float)
    k = len(hz) - 1

    def f(t):
        return float(hz[min(k, max(0, int(round(t * k))))])
    if genre == "bas":
        return O.sweep(x, hi=f, ordre=ordre)
    return O.sweep(x, lo=f, ordre=ordre)


def echo(hit, n, demi, retro=0.5, hp=300.0, lp=(8000.0, 2000.0), plancher_db=-60.0):
    """Queue d'écho de `hit` sur n échantillons : copies décalées de k × `demi` (k ≥ 1), gain retro^k, arrêtées
    sous `plancher_db` ; passe-haut `hp`, passe-bas balayé lp[0] → lp[1] (expo) sur n. Rend (queue, coupure Hz)."""
    out = np.zeros((int(n), CH), np.float32)
    kmax = int(np.ceil(plancher_db / (20 * np.log10(retro))))
    for k in range(1, kmax + 1):
        s = int(round(k * demi))
        if s >= n:
            break
        e = min(int(n), s + len(hit))
        out[s:e] += hit[:e - s] * retro ** k
    out = O.band(out, lo=hp, ordre=2)
    hz = courbe("expo", int(n), lp[0], lp[1])
    return filtre_balaye(out, hz, "bas"), hz


def milieux(reperes):
    """Milieu de chaque temps de la grille (points de relevé des automations)."""
    r = np.asarray(reperes, dtype=float)
    return np.round((r[:-1] + r[1:]) / 2).astype(np.int64) if len(r) > 1 else r.astype(np.int64)


class Journal:
    """Automations d'un rendu (contrat.Automation), relevées aux points donnés (au moins une par temps)."""

    def __init__(self, points):
        self.points = np.asarray(points, dtype=np.int64)
        self.liste = []

    def courbe(self, piste, param, valeurs, de=0, a=None):
        """Relève `valeurs` (tableau par échantillon) aux points situés dans [de ; a[."""
        valeurs = np.asarray(valeurs, dtype=float)
        a = len(valeurs) if a is None else min(int(a), len(valeurs))
        for t in self.points:
            if int(de) <= t < a:
                self.liste.append(Automation(piste, param, int(t), float(valeurs[t])))
        return valeurs


def grille_seche(n_a, beat_a, beat_b, longueur):
    """Repères et premiers temps d'un rendu sans recouvrement : temps de A jusqu'à la jonction `n_a` (un 1), puis
    temps de B. Rend (reperes, uns) en échantillons du segment."""
    ra = n_a - beat_a * np.arange(int(n_a // beat_a), 0, -1)
    rb = n_a + beat_b * np.arange(0, int((longueur - n_a) // beat_b) + 1)
    rep = np.round(np.concatenate([ra, rb])).astype(np.int64)
    rep = rep[(rep >= 0) & (rep <= longueur)]
    ua = n_a - 4 * beat_a * np.arange(int(n_a // (4 * beat_a)), 0, -1)
    ub = n_a + 4 * beat_b * np.arange(0, int((longueur - n_a) // (4 * beat_b)) + 1)
    uns = np.round(np.concatenate([ua, ub])).astype(np.int64)
    return rep, uns[(uns >= 0) & (uns <= longueur)]


def _niveau(m, a, b, g=1.0):
    try:
        m.wait(b)
        x = m.read(max(0, a), b)
    except (AssertionError, ValueError):
        return None
    return O.level(x) * g if len(x) >= int(0.4 * SR) else None


def assembler(m, transition, debut, pistes, reprise, g, reperes, uns, journal, infos=None):
    """Somme des pistes (même longueur), limiteur et raccords de 20 ms avec le flux → Rendu. Les niveaux de A juste
    avant et de B juste après (× g) servent de référence à la mesure de sonie (O5)."""
    n = {len(v) for v in pistes.values()}
    if len(n) != 1:
        raise ValueError(f"pistes de longueurs différentes : {n}")
    seg = np.sum([v for v in pistes.values()], axis=0).astype(np.float32)
    debut, seg, reprise, g = O.finir(m, int(debut), seg, int(reprise), float(g))
    infos = dict(infos or {})
    infos.setdefault("ref_a", _niveau(m, debut - 3 * SR, debut))
    infos.setdefault("ref_b", _niveau(m, reprise, reprise + 3 * SR, g))
    return Rendu(debut=debut, seg=seg, reprise=reprise, gain=g, transition=transition,
                 pistes={k: v.astype(np.float32) for k, v in pistes.items()}, reperes=np.asarray(reperes, np.int64),
                 uns=np.asarray(uns, np.int64), automations=journal.liste, infos=infos)
