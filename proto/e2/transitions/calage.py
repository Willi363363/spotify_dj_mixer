"""Calage sur la grille de temps (ADR 0004) : grid_lag, grid_end, grid_fit, et la boucle de correction du calage
extraite de l'ancien mélange (`caler_superposition`, tâche 9)."""
import numpy as np

from transitions import outils as O
from transitions.outils import SR, Refus

CALAGE_MAX_MS = 20.0   # O2 : écart B − A toléré après correction
NETTETE_MIN = 1.5      # en dessous, pas de superposition (§5.2, §8)


def _flux(x, h):
    """Attaques toutes fréquences (flux spectral) par pas de h échantillons, centrées réduites."""
    w = 1024
    mono = x.mean(axis=1)
    n = (len(mono) - w) // h
    if n < 4:
        return np.zeros(max(n, 1))
    frames = np.stack([mono[i * h:i * h + w] * np.hanning(w) for i in range(n)])
    mag = np.abs(np.fft.rfft(frames, axis=1))
    f = np.concatenate([[0], np.maximum(0, np.diff(mag, axis=0)).sum(axis=1)])
    return (f - f.mean()) / (f.std() + 1e-9)


def grid_lag(m, ref, beats, max_ms=150):
    """Décalage (échantillons) entre la mémoire et la grille de temps de Spotify : `beats` sont les temps du
    morceau en secondes relatives à l'instant qui se trouve vers `ref` dans la mémoire. On cherche, à
    ±max_ms, le décalage qui place le plus d'attaques sur ces temps (toutes les attaques, pas la plus forte).
    Rend (décalage, netteté : pic sur la moyenne, ~1 sans accord)."""
    beats = np.asarray(beats, dtype=float)
    h, r = int(0.005 * SR), int(max_ms / 1000 * SR)
    lo = int(ref + beats.min() * SR) - r - 1024
    hi = int(ref + beats.max() * SR) + r + 1024
    m.wait(hi)
    env = _flux(m.read(lo, hi), h)
    pos = ((ref - lo + beats * SR) / h).astype(int)
    lags = np.arange(-r, r + 1, h)
    score = np.array([env[np.clip(pos + lag // h, 0, len(env) - 1)].sum() for lag in lags])
    k = int(np.argmax(score))
    return int(lags[k]), float(score[k] / (np.abs(score).mean() + 1e-9))


def grid_end(m, end_a, beat, ahead=0):
    """Fin de A recalée sur ses propres temps (sans grille de Spotify) : phase des attaques de grosse caisse
    repliée sur les 16 derniers temps. On avance d'au plus `ahead` ; au-delà on recule, au pire d'un temps.
    Rend (nouvelle fin, décalage en échantillons)."""
    h = int(0.005 * SR)
    span = int(16 * beat)
    env = O.kick_env(m.read(end_a - span, end_a))
    nb = max(1, int(beat // h))
    folded = np.zeros(nb + 1)
    for i, v in enumerate(env):
        folded[min(nb, int(((i * h) % beat) / h))] += v
    phase = max(0, int(np.argmax(np.convolve(folded, [0.5, 1, 0.5], mode="same"))) - 1) * h
    beat = int(round(beat))
    if phase <= ahead:
        return end_a + phase, phase
    if phase < int(0.015 * SR) or phase > beat - int(0.015 * SR):
        return end_a, 0
    return end_a - beat + phase, phase - beat


def grid_fit(x, marks, max_ms=120):
    """Décalage (ms) qui place le mieux les attaques de x sur les repères `marks` (échantillons), et netteté."""
    h, r = int(0.005 * SR), int(max_ms / 1000 * SR)
    env = _flux(x, h)
    pos = (np.asarray(marks) / h).astype(int)
    lags = np.arange(-r, r + 1, h)
    score = np.array([env[np.clip(pos + lag // h, 0, len(env) - 1)].sum() for lag in lags])
    k = int(np.argmax(score))
    return float(lags[k] / SR * 1000), float(score[k] / (np.abs(score).mean() + 1e-9))


PHASE_NETTETE_MIN = 3.5  # phase d'attaques fiable si netteté ≥ 3,5 (bruit : 1,9 à 4,7 ; batterie : 5,5 à 10)…
PHASE_ACCORD_MIN = 0.6   # … et accord ≥ 0,6 (bruit, nappe : ≤ 0,53 ; batterie, même syncopée : 0,7 à 1)


def phase_attaques(x, marks, max_ms=120, ignore_avant=None):
    """Phase des attaques de x sur les temps `marks` (échantillons dans x), cherchée à ±max_ms comme grid_fit.
    Rend (décalage en échantillons, netteté, accord) :
    - netteté : score du meilleur décalage sur la moyenne des |scores| (celle de grid_fit) ;
    - accord : part des temps dont l'attaque la plus forte à ±max_ms tombe à ±15 ms du décalage retenu.
      Une batterie, même syncopée, met la plupart de ses attaques sur les temps (0,7 à 1) ; un bruit, une nappe
      n'en mettent qu'au hasard (≤ 0,5 sur 8 temps, ≤ 0,53 sur 16). La netteté seule ne suffit pas : un bruit
      modulé atteint 4,7 (QA de l'essai 13 : 1,9 à 3,0 en direct, contre 5,5 à 8 avec batterie).
    `ignore_avant` (échantillon) : le flux avant lui (et les trames de 1024 qui le chevauchent) n'entre pas dans la
    mesure : une entrée en marche (silence → son, début d'un morceau) n'est pas une attaque."""
    h, r = int(0.005 * SR), int(max_ms / 1000 * SR)
    env = _flux(x, h)
    garde = np.ones(len(env), bool)
    if ignore_avant is not None:
        garde[:min(len(env), max(0, int(ignore_avant)) // h + 2)] = False
        if garde.sum() < 8:
            return 0, 0.0, 0.0
        v = env[garde]
        env = np.where(garde, (env - v.mean()) / (v.std() + 1e-9), 0.0)
    pos = (np.asarray(marks) / h).astype(int)
    lags = np.arange(-r, r + 1, h)
    score = np.array([env[np.clip(pos + lag // h, 0, len(env) - 1)].sum() for lag in lags])
    k = int(np.argmax(score))
    nettete = float(score[k] / (np.abs(score).mean() + 1e-9))
    rh, tol = r // h, int(0.015 * SR) // h
    vus = d_accord = 0
    for q in pos:
        if q - rh < 0 or q + rh >= len(env) or not garde[q - rh:q + rh + 1].all():
            continue
        vus += 1
        d_accord += abs(int(np.argmax(env[q - rh:q + rh + 1])) - rh - lags[k] // h) <= tol
    return int(lags[k]), nettete, (d_accord / vus if vus >= 2 else 0.0)


def phase_fiable(nettete, accord):
    """La phase d'attaques mesurée est-elle fiable (attaques nettes sur les temps) ? Sinon : temps estimés gardés,
    ou mesure « non mesurable »."""
    return nettete >= PHASE_NETTETE_MIN and accord >= PHASE_ACCORD_MIN


def beat_phase(env, beat, h):
    """Phase des attaques dans le temps (échantillons depuis le début de `env`, enveloppe par pas de h) et
    netteté de la pulsation (pic du repli sur sa moyenne : ~1 sans pulsation, 2 à 5 pour une batterie)."""
    nb = max(1, int(beat // h))
    folded = np.zeros(nb + 1)
    for i, v in enumerate(env):
        folded[min(nb, int(((i * h) % beat) / h))] += v
    folded = np.convolve(folded, [0.5, 1, 0.5], mode="same")
    k = int(np.argmax(folded))
    return max(0, k - 1) * h, float(folded[k] / (np.abs(folded).mean() + 1e-9))


def nettete_pulsation(m, debut, fin, beat):
    """Netteté de la pulsation de la mémoire entre debut et fin (sans grille de Spotify)."""
    m.wait(fin)
    return beat_phase(O.kick_env(m.read(debut, fin)), beat, int(0.005 * SR))[1]


def grille_temps(beats, ancre, avant, apres, pas, apres_min):
    """Temps (échantillons absolus) autour de `ancre` : les `avant` temps qui la précèdent, puis elle et jusqu'à
    `apres` − 1 suivants. Espacement pris aux temps de Spotify recalés (`beats`) s'ils encadrent l'ancre (à un quart
    de temps près) avec au moins `apres_min` temps depuis elle ; sinon grille uniforme de pas `pas`, `apres_min` temps.
    Sert à R1 (superposees) et à caler_superposition (C5 à C8). Essai direct 13 bis (g07) : la mesure d'entrée de B
    durait 1,537 s chez Spotify, ses temps 375 ms, pas 384 : une grille uniforme dérivait de 9 ms par temps et posait
    le 1 final de B 34 ms trop tard."""
    if beats is not None and len(beats) >= 2:
        b = np.asarray(beats, np.float64)
        j = int(np.argmin(np.abs(b - ancre)))
        k = min(apres, len(b) - j)
        if abs(b[j] - ancre) <= pas / 4 and j >= avant and k >= apres_min:
            return ancre + b[j - avant:j + k] - b[j]
    return ancre + np.arange(-avant, apres_min) * float(pas)


def caler_superposition(m, p, T, *, ecart_max=0.06, log=None):
    """Superpose les T dernières mesures de A (avant p.fin_a) et les T premières de B (depuis p.debut_b) sur une
    grille commune dont le tempo glisse temps par temps de celui de A vers celui de B (stretch_map), puis mesure le
    calage sur le son produit (grid_fit) et corrige B une fois si l'écart dépasse 10 ms.
    Temps de A et de B : ceux de Spotify recalés (`grille_temps`), qui suivent le jeu réel, uniformes (mesure / 4) à
    défaut ; chaque temps réel est posé sur un repère de la grille commune (QA de l'essai 13 : avec des temps
    uniformes, des temps réels inégaux de 2-3 % décalaient B de plus de 20 ms, et C5 se repliait sur R1).
    Rend un dict : a, b (L échantillons, avant EQ et gain), dst (N + 1 repères), a0, b0, b_fin (fin de B lue dans
    la mémoire), calage_ms, nettete, d1, d2. Lève Refus : tempos trop éloignés, pulsation de B introuvable,
    calage > 20 ms après correction, netteté < 1,5."""
    log = log or m.log
    d1 = p.bar_a / 4
    d2, rr = O.unit(d1, p.bar_b / 4)
    if abs(rr - 1) > ecart_max:
        raise Refus(f"tempos trop éloignés ({abs(rr - 1) * 100:.1f} % > {ecart_max * 100:.0f} %)")
    N = 4 * T
    meme_pulsation = abs(d2 - p.bar_b / 4) <= 1     # tempo double ou moitié : temps de B uniformes
    ta = grille_temps(p.beats_a, p.fin_a, N, 1, d1, 1)
    tb = grille_temps(p.beats_b if meme_pulsation else None, p.debut_b, 0, N + 1, d2, N + 1) - p.debut_b
    d1, d2 = (ta[-1] - ta[0]) / N, (tb[-1] - tb[0]) / N   # temps moyens réels
    etire = abs(d2 / d1 - 1) > 0.005
    if etire:
        dout = np.array([((N - n) / N) * d1 + (n / N) * d2 for n in range(N)])
    else:
        dout = np.full(N, d1)
    dst = np.concatenate([[0], np.cumsum(dout)]).round()
    L = int(dst[-1])
    a0 = int(round(ta[0]))
    src_a = ta - a0
    etire_a = etire or np.abs(src_a - dst).max() > 0.001 * SR
    etire_b = etire or np.abs(tb - dst).max() > 0.001 * SR
    b0 = int(p.debut_b)
    if p.beats_b is None:  # sans grille de Spotify : B posé sur la phase de ses attaques (ancien mélange)
        h, half, wb = int(0.005 * SR), int(d2 / 2), int(8 * d2)
        lo = max(p.debut_b, b0 - half)
        m.wait(lo + wb + int(d2))
        phase, force = beat_phase(O.kick_env(m.read(lo, lo + wb)), d2, h)
        if force < 1.4:
            raise Refus(f"pulsation de B introuvable (netteté {force:.2f})")
        grid0 = lo + phase
        b_new = int(round(grid0 + round((b0 - grid0) / d2) * d2))
        b0 = max(p.debut_b, b_new)
    a_src = m.read(a0, p.fin_a)
    nb_ = int(round(tb[-1]))

    def rendre_b(b0):
        m.wait(b0 + nb_ + SR)
        src = m.read(b0, b0 + nb_)
        return O.fit(O.stretch_map(src, np.round(tb), dst), L) if etire_b else O.fit(src, L)

    a = O.fit(O.stretch_map(a_src, np.round(src_a), dst), L) if etire_a else O.fit(a_src, L)
    b = rendre_b(b0)
    ea, sa = grid_fit(a, dst[:-1])
    eb, sb = grid_fit(b, dst[:-1])
    log(f"calage mesuré : A {ea:+.0f} ms (netteté {sa:.1f}), B {eb:+.0f} ms (netteté {sb:.1f})")
    if sa >= 2.5 and sb >= 2.5 and 10 <= abs(eb - ea) <= 150:
        b0 += int(round((eb - ea) / 1000 * SR * d2 / dout.mean()))
        b = rendre_b(b0)
        eb, sb = grid_fit(b, dst[:-1])
        log(f"calage corrigé : écart B − A {eb - ea:+.0f} ms (netteté {sb:.1f})")
    nettete = min(sa, sb)
    if nettete < NETTETE_MIN:
        raise Refus(f"netteté {nettete:.2f} < {NETTETE_MIN}")
    if abs(eb - ea) > CALAGE_MAX_MS:
        raise Refus(f"calage {eb - ea:+.0f} ms > {CALAGE_MAX_MS:.0f} ms après correction")
    return {"a": a, "b": b, "dst": dst, "a0": a0, "b0": b0, "b_fin": b0 + nb_,
            "calage_ms": float(eb - ea), "nettete": float(nettete), "d1": d1, "d2": d2, "etire": etire_b}
