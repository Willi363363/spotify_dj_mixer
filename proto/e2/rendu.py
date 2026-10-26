"""Rendu des préréglages de recettes.py à partir de la mémoire de e2.py.

Chaque fonction reçoit `m` (accès à la mémoire : m.read(a, b), m.wait(n), m.log), la fin de A et le début
de B dans la mémoire, la durée d'une mesure de A, le rapport de tempo A / B, l'avance de B (`pre`, B lancé
par Spotify `pre` échantillons avant son point d'entrée) et `extra` (échantillons à regagner sur l'avance
de la maquette). Elle rend (début du segment, segment, reprise du flux, gain de B à la reprise).

Règle commune aux styles doux : le segment dure au moins ce qu'il consomme dans la mémoire. Pendant que B
monte (ses mesures jouées en avance), A est prolongé par du synthétique (boucles, roulements, écho) au lieu
d'être sauté : l'avance de la maquette ne fond plus d'une transition à l'autre.
"""
import threading

import numpy as np

from recettes import (CH, SR, Refus, band, edges, kick_agreement, kick_env, level, limiter, pitched, ramp, smooth,
                      stretch_map, sweep)


# Calage sur la grille de Spotify : quand e2.py a placé les temps de A et de B d'après l'analyse de Spotify
# (grid_lag), les recalages sur la frappe la plus forte sont coupés pour ce rendu (ils tombent à contretemps
# en rap). Propre au fil du rendu : deux ordres peuvent se préparer en même temps.
_ctx = threading.local()


def _snap():
    return getattr(_ctx, "snap", True)


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


def entry_kick(m, pos, beat):
    """Décalage jusqu'à l'attaque de grosse caisse la plus forte des 3/4 de temps qui suivent `pos`.
    L'analyse commence 30 ms avant, dans le silence de Spotify : sinon une attaque pile au début est invisible
    (l'enveloppe ne mesure que les montées) et on prend la grosse caisse du temps suivant. Sans effet quand le
    rendu est calé sur la grille de Spotify."""
    if not _snap():
        return 0
    m.wait(pos + 2 * beat)
    pre, h = int(0.03 * SR), int(0.005 * SR)
    env = kick_env(m.read(pos - pre, pos + int(0.75 * beat)))
    return max(0, int(np.argmax(env)) * h - pre)


def _unit(beat, beat_b):
    """Pulsation de B ramenée près de celle de A (mix à tempo double ou moitié) : (durée, rapport à A)."""
    u = min((beat_b * f for f in (0.5, 1.0, 2.0)), key=lambda v: abs(np.log(v / beat)))
    return u, u / beat


def _gain(a, b):
    """Gain qui ramène B au niveau de A, borné à 0,8..1,0 et par la marge de crête de B : les masters
    rap / shatta frôlent 0 dBFS, un gain au-dessus de 1 ferait écrêter leur drop."""
    # baisse limitée à -2 dB (comparé à la fin de A, souvent un outro, B serait écrasé à son drop) ; jamais de
    # hausse : un B monté au-dessus de son niveau « sort de nulle part, d'un coup » (essai 21)
    return float(np.clip(min(level(a) / level(b), 0.97 / max(float(np.abs(b).max()), 1e-6)), 0.8, 1.0))


def grid_end(m, end_a, beat, ahead=0):
    """Fin de A recalée sur ses propres temps : l'heure du saut est connue à quelques dizaines de ms près, et
    une boucle de A coupée à côté de ses temps décale ses grosses caisses sous B. Phase des attaques de grosse
    caisse repliée sur les 16 derniers temps. On avance d'au plus `ahead` (la marge prise avant l'heure
    estimée du saut, sûre) ; au-delà on recule (B est peut-être déjà là), au pire d'un temps de A.
    Rend (nouvelle fin, décalage en échantillons)."""
    h = int(0.005 * SR)
    span = int(16 * beat)
    env = kick_env(m.read(end_a - span, end_a))
    nb = max(1, int(beat // h))
    folded = np.zeros(nb + 1)
    for i, v in enumerate(env):  # chaque pas classé par sa vraie phase dans le temps (beat n'est pas un multiple de h)
        folded[min(nb, int(((i * h) % beat) / h))] += v
    # attaque après chaque début de temps ; l'enveloppe la voit avec un pas de retard
    phase = max(0, int(np.argmax(np.convolve(folded, [0.5, 1, 0.5], mode="same"))) - 1) * h
    beat = int(round(beat))
    if phase <= ahead:
        return end_a + phase, phase
    if phase < int(0.015 * SR) or phase > beat - int(0.015 * SR):
        return end_a, 0
    return end_a - beat + phase, phase - beat


def secours(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """Quand la transition prévue arrive trop tard ou échoue alors que Spotify a déjà sauté : A perd ses graves
    sur son dernier temps puis sa dernière mesure tourne deux fois pendant que B monte dessous, filtré, sur deux
    mesures (une seule mesure faisait encore « B sec », audit). Mieux que la coupe sèche (« absolument
    horrible ») ; ne coûte pas d'avance. Rendu court : il doit être prêt vite."""
    beat = bar // 4
    n = 2 * int(bar * ratio)
    a = m.read(end_a - bar, end_a)
    head = sweep(a[-beat:], lo=lambda t: 20 * (300 / 20) ** t)
    m.wait(start_b + n)
    loop = _loop(band(a, lo=300), n) * smooth(n, 1.0, 0.3)
    rise = sweep(m.read(start_b, start_b + n), lo=lambda t: 1500 * (60 / 1500) ** t) * smooth(n, 0.0, 1.0)
    return _finish(m, end_a - beat, np.concatenate([head, loop + rise]), start_b + n, 1.0)


def _fit(x, n):
    """x coupé ou complété de silence à n échantillons."""
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x), CH), np.float32)])


def _resample(x, n):
    """x ramené à n échantillons par interpolation linéaire (change aussi la hauteur : pour l'analyse)."""
    pos = np.linspace(0, len(x) - 1, n)
    return np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(CH)], axis=1).astype(np.float32)


def _loop(x, n):
    """x répété sur n échantillons, chaque reprise adoucie pour ne pas claquer."""
    if n <= 0:
        return np.zeros((0, CH), np.float32)
    piece = edges(x, 2)
    return edges(np.tile(piece, (-(-n // len(piece)), 1))[:n], 2)


def _phrase(src, n, bar, lo0, lo1):
    """Phrase réelle de A (`src`, plusieurs mesures) rejouée sur n échantillons, comme un DJ qui redouble une
    phrase, au lieu d'une seule mesure en boucle (« une machine », audit). Sans graves sous lo0 ; le passe-haut
    monte d'un cran toutes les 2 mesures jusqu'à lo1 : l'état de A change, il ne tourne pas figé."""
    if n <= 0:
        return np.zeros((0, CH), np.float32)
    k = max(1, -(-n // (2 * bar)))
    return sweep(_loop(src, n), lo=lambda t: lo0 * (lo1 / lo0) ** (min(k - 1, int(t * k)) / max(1, k - 1)))


def _percussive(x, w=2048):
    """Batterie seule de x (séparation percussions / harmonie par filtres médians, Fitzgerald 2010) : la voix et
    les nappes, tenues dans le temps, s'effacent ; les attaques restent."""
    hop = w // 4
    win = np.hanning(w).astype(np.float32)
    pad = np.concatenate([np.zeros((w, CH), np.float32), x, np.zeros((w, CH), np.float32)])
    nfr = (len(pad) - w) // hop + 1
    out = np.zeros_like(pad)
    norm = np.zeros(len(pad), np.float32)
    idx = np.arange(nfr)[:, None] * hop + np.arange(w)[None, :]
    for c in range(CH):
        spec = np.fft.rfft(pad[:, c][idx] * win, axis=1)
        mag = np.abs(spec)
        sw = np.lib.stride_tricks.sliding_window_view
        harm = np.median(sw(np.pad(mag, ((8, 8), (0, 0)), mode="edge"), 17, axis=0), axis=-1)
        perc = np.median(sw(np.pad(mag, ((0, 0), (8, 8)), mode="edge"), 17, axis=1), axis=-1)
        mask = perc ** 2 / (perc ** 2 + harm ** 2 + 1e-12)
        frames = np.fft.irfft(spec * mask, n=w, axis=1).astype(np.float32) * win
        np.add.at(out[:, c], idx, frames)
    np.add.at(norm, idx, np.broadcast_to(win ** 2, idx.shape))
    return (out / np.maximum(norm, 1e-3)[:, None])[w:w + len(x)].astype(np.float32)


def _grid_fit(x, marks, max_ms=120):
    """Décalage (ms) qui place le mieux les attaques de x sur les repères `marks` (échantillons), et netteté."""
    h, r = int(0.005 * SR), int(max_ms / 1000 * SR)
    env = _flux(x, h)
    pos = (np.asarray(marks) / h).astype(int)
    lags = np.arange(-r, r + 1, h)
    score = np.array([env[np.clip(pos + lag // h, 0, len(env) - 1)].sum() for lag in lags])
    k = int(np.argmax(score))
    return float(lags[k] / SR * 1000), float(score[k] / (np.abs(score).mean() + 1e-9))


def _beat_phase(env, beat, h):
    """Phase des attaques dans le temps (échantillons depuis le début de `env`, enveloppe par pas de h) et
    netteté de la pulsation (pic du repli sur sa moyenne : ~1 sans pulsation, 2 à 5 pour une batterie)."""
    nb = max(1, int(beat // h))
    folded = np.zeros(nb + 1)
    for i, v in enumerate(env):
        folded[min(nb, int(((i * h) % beat) / h))] += v
    folded = np.convolve(folded, [0.5, 1, 0.5], mode="same")
    k = int(np.argmax(folded))
    return max(0, k - 1) * h, float(folded[k] / (np.abs(folded).mean() + 1e-9))


def _stages(src, unit, stages, total):
    """Roulements : pour chaque étape (division, longueur, coupure des graves, vitesse de départ, d'arrivée),
    `src` rejoué par tranches de unit/division, de plus en plus aigu. Les étapes sont prises en partant de la
    fin si `total` ne suffit pas ; le reste est rendu à l'appelant (à remplir en tête)."""
    parts, used = [], 0
    for div, length, lo, r0, r1 in reversed(stages):
        n = unit // div
        count = min(length, total - used) // n
        if count <= 0:
            break
        pieces = [edges(band(pitched(src, r0 + (r1 - r0) * i / max(1, count - 1), n), lo=lo) * (0.8 + 0.2 * i / count), 1)
                  for i in range(count)]
        parts.insert(0, np.concatenate(pieces))
        used += count * n
    return (np.concatenate(parts) if parts else np.zeros((0, CH), np.float32)), total - used


def _hp_rise(x, top=300):
    """A perd ses graves peu à peu (passe-haut de 20 Hz à `top`)."""
    return sweep(x, lo=lambda t: 20 * (top / 20) ** t)


def _spin(hist, n, lo=300):
    """Disque ramené en arrière sur n échantillons depuis la fin de `hist` (vitesse en sinus, jusqu'à 3,5 fois)."""
    t = np.arange(n) / n
    pos = len(hist) - 1 - np.cumsum(3.5 * np.sin(np.pi * t) ** 1.3)
    out = np.stack([np.interp(pos, np.arange(len(hist)), hist[:, c], left=0) for c in range(CH)], axis=1)
    return edges(band(out.astype(np.float32), lo=lo) * ramp(n, 1.0, 0.0) ** 0.5, 2)


def _brake(x, lo=300):
    """Vinyle qui ralentit jusqu'à l'arrêt sur la durée de x. Filtré après le ralenti : ralentir fait
    descendre les aigus dans les graves, qu'on ne veut plus entendre de A à ce stade."""
    n = len(x)
    pos = np.cumsum(np.linspace(1.0, 0.0, n) ** 1.5)
    pos = pos[pos < n - 1]
    out = np.stack([np.interp(pos, np.arange(n), x[:, c]) for c in range(CH)], axis=1).astype(np.float32)
    out = np.concatenate([out * ramp(len(out), 1, 0.6), np.zeros((n - len(out), CH), np.float32)])
    return edges(band(out, lo=lo), 2)


def _wash(hit, n):
    """Nappe : `hit` puis sa réverbération (bruit qui s'éteint en ~1 s), sans graves, sur n échantillons."""
    t = np.arange(n) / SR
    ir = np.random.default_rng(0).standard_normal((n, CH)) * np.exp(-t / 0.35)[:, None]
    size = n + len(hit)
    y = np.fft.irfft(np.fft.rfft(hit, size, axis=0) * np.fft.rfft(ir, size, axis=0), size, axis=0)[:n]
    y = band(y.astype(np.float32), lo=300, hi=8000)
    y *= 0.5 * np.abs(hit).max() / max(float(np.abs(y).max()), 1e-9)
    y[:len(hit)] += hit * 0.6
    return edges(y * smooth(n, 1.0, 0.0), 5)


def _finish(m, start, seg, resume, g):
    """Limiteur, puis raccords de 20 ms avec le flux aux deux bouts (le flux reprend avec le gain g)."""
    seg = limiter(seg)
    f = min(int(0.02 * SR), len(seg) // 2)
    seg[:f] = m.read(start, start + f) * ramp(f, 1, 0) + seg[:f] * ramp(f, 0, 1)
    seg[-f:] = seg[-f:] * ramp(f, 1, 0) + m.read(resume - f, resume) * g * ramp(f, 0, 1)
    return start, seg.astype(np.float32), resume, g


# ─── Transitions douces ─────────────────────────────────────────────────────────────────────────────
# Règles tirées de l'écoute (docs/gouts.md) : B ne surgit jamais d'un coup. Il monte sous la fin de A
# (filtre qui s'ouvre, volume qui monte) sur jusqu'à 8 mesures, calé sur la pulsation de A quand les tempos
# le permettent, pendant que A descend en miroir ; à son drop, ses basses arrivent et le dernier temps réel
# de A résonne encore en écho. Chaque style ne fait que changer ce que A fait pendant ce temps.

def _douce(m, end_a, start_b, bar, ratio, pre, extra, build, name, min_beats=4, b_lo=300):
    """`build(E)` rend (partie réelle de A avec son effet, prolongement synthétique de E temps de A) et
    éventuellement une troisième valeur : ce que A fait encore pendant la mesure qui suit le drop (None : rien
    que l'écho ; par défaut sa dernière mesure qui s'éteint)."""
    beat = bar // 4
    beat_b = beat * ratio
    u, rr = _unit(beat, beat_b)
    if pre <= 0:  # B lancé sans avance (repli d'un mélange, rattrapage) : ses premières mesures servent de montée
        pre = entry_kick(m, start_b, int(u)) + int(round(16 * u))
    drop = start_b + pre + entry_kick(m, start_b + pre, int(beat_b))
    bar_b = int(4 * beat_b)
    m.wait(drop + 2 * bar_b)
    g = _gain(m.read(end_a - 4 * bar, end_a), m.read(drop, drop + 2 * bar_b))
    aligned = 0.85 <= rr <= 1.18
    stretch = aligned and abs(rr - 1) > 0.005
    # Toute l'avance de B sert à sa montée (comptée en unités de la pulsation de A) : plafonnée, B à tempo
    # moitié laissait A tourner seul 14 à 16 s avant de monter (3ᵉ revue).
    kb = int((drop - start_b) // u) if aligned else 0
    need = drop - end_a + max(0, extra)

    def grid(E):
        """Repères des E temps du prolongement ; sous la montée, le tempo glisse de celui de A vers celui de B."""
        k = min(kb, E)
        d = [float(beat)] * (E - k) + [beat + (u - beat) * (i + 1) / k if stretch else float(beat) for i in range(k)]
        return np.concatenate([[0], np.cumsum(d)]).round().astype(int)

    # Mesures entières : le drop de B tombe sur un premier temps de A, et 8 mesures d'avance de B donnent
    # 8 mesures de prolongement, pas 9 (le trou du saut et le recalage du drop, quelques dizaines de ms, sont
    # pris sur l'avance). `extra` > 0 : arrondi au-dessus (on regagne de l'avance) ; `extra` < 0 (avance
    # au-dessus de la cible) : arrondi à la mesure la plus proche, au plus une demi-mesure du début de la
    # montée de B sautée, pour que l'avance ne dérive pas vers le haut transition après transition.
    tol = beat // 3 + (start_b - end_a)
    if extra < 0:
        E = max(min_beats + -min_beats % 4, int(round(need / beat / 4)) * 4)
    else:
        E = max(min_beats, -(-(need - tol) // beat))
        E += -E % 4
        while grid(E)[-1] < need - tol:
            E += 4
    marks = grid(E)
    built = build(E)
    real, ext = built[0], built[1]
    ext = _fit(ext, E * beat)
    if stretch:  # tout le prolongement glisse vers le tempo de B, sans couper ses effets temps par temps
        ext = _fit(stretch_map(ext, np.arange(E + 1) * beat, marks), marks[-1])
    k = min(kb, E)
    if k:  # les k dernières unités de B avant son drop, calées temps sur temps sous la fin du prolongement
        src = m.read(drop - int(round(k * u)), drop)
        rise = stretch_map(src, np.arange(k + 1) * u, marks[-k - 1:] - marks[-k - 1]) if stretch else src
    else:
        # tempos trop éloignés pour se caler : B monte aussi longtemps, mais sans rien sous 400 Hz, pour ne pas
        # faire entendre deux grosses caisses qui se contredisent
        n = int(drop - start_b)
        rise = m.read(drop - n, drop)
        b_lo = max(b_lo, 400)
    rise = rise[-len(ext):] if len(ext) else rise[:0]
    n = len(rise)
    if n > 3 * bar:
        # B monte par sa batterie seule ; sa voix et ses nappes n'arrivent que sur les 2 dernières mesures :
        # en rap et en shatta, les mesures d'avant-drop sont souvent chantées, et deux voix se superposaient
        # (audit, enseignement 5).
        f = 2 * bar
        mix = np.concatenate([np.zeros((n - f, 1), np.float32), smooth(f, 0.0, 1.0)])
        rise = _percussive(rise) * (1 - mix) + rise * mix
    a_part = np.concatenate([real, ext])
    # ce que A fait après le drop : par défaut sa dernière mesure qui continue de s'éteindre ; None pour un
    # effet qui ne doit pas repartir (un frein ou un disque en arrière qui redémarreraient sous B)
    a_tail = built[2] if len(built) > 2 else band(a_part[-bar:], lo=300)
    if n:
        # Side chain : A s'efface sur chaque grosse caisse de B, de plus en plus fort au fil de la montée
        # (jusqu'à -6 dB, retour en 1/8 de temps). L'effet sur A évolue et B s'entend arriver par sa batterie,
        # sans fondu (veille 2026-10 : « Side Chain » de DJ.Studio).
        hk = int(0.005 * SR)
        env = np.repeat(np.clip(kick_env(rise), 0, None), hk)[:n]
        env = np.convolve(env, np.exp(-np.arange(int(beat / 8)) / (beat / 32)), mode="full")[:n]
        env = np.clip(env / (np.percentile(env, 99) + 1e-9), 0, 1)
        if len(env) < n:
            env = np.concatenate([env, np.zeros(n - len(env))])
        duck = (1 - 0.5 * np.linspace(0, 1, n) * env).astype(np.float32)[:, None]
        a_part[-n:] *= duck
        # Courbes de Spotify (article 2017, brevet US20230409281) et de Vande Veire (2018) : B est à PLEIN volume
        # avant son drop, mais sans ses basses (sous b_lo) ni ses aigus (au-dessus de 6 kHz) ; il atteint son
        # plein niveau à 70 % de la montée et le tient. A reste à plein jusqu'à mi-montée puis descend à 0,4
        # (-8 dB) au drop. Au drop, pas de marche de volume : un échange de fréquences (voir l'atterrissage).
        # Nos versions précédentes faisaient l'inverse (B encore en montée au drop, A presque coupé avant) :
        # « B pop », « A coupé de manière horriblement brève » (essais 21, 24).
        p = np.linspace(0, 1, n, dtype=np.float32)
        vb = np.where(p < 0.7, 0.18 + 0.82 * (3 * (p / 0.7) ** 2 - 2 * (p / 0.7) ** 3), 1.0).astype(np.float32)
        va = np.where(p < 0.5, 1.0, 1.0 - 0.6 * (3 * ((p - 0.5) / 0.5) ** 2 - 2 * ((p - 0.5) / 0.5) ** 3)).astype(np.float32)
        rise = sweep(rise, lo=lambda t: 800 * (b_lo / 800) ** min(1.0, t / 0.3), hi=lambda t: 6000) * vb[:, None] * g
        a_part[-n:] = a_part[-n:] * va[:, None] + rise
    # Atterrissage sur 2 mesures de B : au drop, ses basses et ses aigus reviennent en ½ temps (l'échange) ;
    # A, qui n'est plus qu'à 0,4, continue de s'éteindre sur ces 2 mesures (son « point de sortie » est là où
    # on ne l'entend plus, après le drop de B), avec le début de son dernier temps réel en écho.
    bar_b = int(4 * beat_b)
    land = m.read(drop, drop + 2 * bar_b) * g
    hb = max(1, int(beat_b) // 2)
    land[:hb] = sweep(land[:hb], lo=lambda t: b_lo * (20 / b_lo) ** t, hi=lambda t: 6000 * (20000 / 6000) ** t)
    if a_tail is not None:
        land += _loop(a_tail, 2 * bar_b) * 0.4 * smooth(2 * bar_b, 1.0, 0.0)
    hit = edges(band(m.read(end_a - beat, end_a - beat + beat // 4), lo=400), 2)
    for i in range(4):
        s = i * int(beat_b) // 4
        land[s:s + len(hit)] += hit[:len(land) - s] * (0.5 * 0.55 ** i)
    start = end_a - len(real)
    seg = np.concatenate([a_part, land])
    m.log(f"{name} : A prolongé de {len(ext) / SR:.2f} s, B monte sur {n / SR:.2f} s"
          f"{' calé sur A' if k else ''}{' (étiré)' if stretch else ''}, gain de B {g:.2f}, "
          f"avance {'+' if len(seg) >= drop + len(land) - start else ''}{(len(seg) - (drop + len(land) - start)) / SR:.2f} s")
    return _finish(m, start, seg, drop + len(land), g)


def montee(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """Montée validée à l'écoute : 4 mesures de A dont les graves partent, puis roulements de plus en plus
    serrés et aigus (1 temps → 1/16 de temps) jusqu'au drop de B, qui monte dessous."""
    beat = bar // 4
    a = m.read(end_a - 4 * bar, end_a)

    def build(E):
        # La phrase réelle de A (ses 4 dernières mesures) est rejouée sous la montée de B, puis les roulements
        # (4 mesures au plus) la resserrent jusqu'au drop. Hauteur plafonnée à ×1,19 (+3 demi-tons) : au-delà,
        # une voix de rap sonne « dessin animé » (audit).
        stages = [(1, 4, 300, 1.0, 1.0), (2, 4, 500, 1.0, 1.02), (4, 4, 800, 1.02, 1.06), (8, 2, 1400, 1.06, 1.12), (16, 2, 2000, 1.12, 1.19)]
        rolls, hold = _stages(a[3 * bar:3 * bar + beat], beat,
                              [(d, nb * beat, lo, r0, r1) for d, nb, lo, r0, r1 in stages], E * beat)
        ext = np.concatenate([_phrase(a, hold, bar, 300, 900), rolls])
        return _hp_rise(a, 300), ext, _loop(ext[-beat:], bar)  # après le drop : le roulement le plus serré s'éteint
    return _douce(m, end_a, start_b, bar, ratio, pre, extra, build, "montée", min_beats=8)


def montee_courte(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """La dernière mesure de A perd ses graves ; sa phrase réelle (4 dernières mesures) est rejouée sous la
    montée de B, puis sa dernière mesure tourne en se divisant par deux (½, ¼, ⅛ de mesure), de plus en plus
    aiguë, jusqu'au drop."""
    a4 = m.read(end_a - 4 * bar, end_a)
    a = a4[3 * bar:]

    def build(E):
        rolls, hold = _stages(a, bar, [(2, bar, 300, 1.0, 1.02), (4, bar, 600, 1.02, 1.08), (8, bar, 1000, 1.08, 1.19)],
                              E * (bar // 4))
        return _hp_rise(a, 100), np.concatenate([_phrase(a4, hold, bar, 100, 600), rolls])
    return _douce(m, end_a, start_b, bar, ratio, pre, extra, build, "montée courte")


def echo_doux(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """A perd ses graves sur 2 mesures, puis sa dernière mesure tourne en s'effaçant pendant que son premier
    temps rebondit en écho (½ temps), et B monte dessous."""
    beat = bar // 4
    a = m.read(end_a - 2 * bar, end_a)

    def build(E):
        n = E * beat
        f = min(n, 16 * beat)  # A ne s'efface que sous la montée de B : sinon, un long prolongement fait un blanc
        tail = _loop(band(a[bar:], lo=300), n) * np.concatenate([np.ones((n - f, 1), np.float32), smooth(f, 1.0, 0.0)])
        hit = edges(band(a[bar:bar + beat], lo=300), 3)
        for k in range(1, 32):
            s = k * beat // 2
            if s >= n:
                break
            tail[s:s + beat] += hit[:n - s] * (0.7 ** k)
        return _hp_rise(a, 250), tail
    return _douce(m, end_a, start_b, bar, ratio, pre, extra, build, "écho")


def _loop_then(m, end_a, bar, effect):
    """Pour retour et frein : 3 mesures de A qui perdent leurs graves, puis sa phrase réelle (4 dernières
    mesures) rejouée, puis une mesure qui bégaie, puis une mesure d'effet (`effect(historique, suite)`)."""
    a4 = m.read(end_a - 4 * bar, end_a)
    a = a4[bar:]

    def build(E):
        real, last = _hp_rise(a, 300), band(a[2 * bar:], lo=300)
        total = E * (bar // 4)
        hold = max(0, total - bar)
        # A évolue au lieu de tourner figé : sa phrase s'amincit cran par cran (passe-haut de 300 à 1200 Hz
        # toutes les 2 mesures), puis bégaie en demi-mesures, avant l'effet (essai 22 : « aucun effet »).
        stutter = min(bar, hold)
        loop = np.concatenate([_phrase(a4, hold - stutter, bar, 300, 1200),
                               band(_loop(last[:bar // 2], stutter + bar), lo=1200)])
        tail = band(loop[hold:], lo=1200)  # l'effet garde l'amincissement de la boucle
        hist = band(np.concatenate([real, loop[:hold]])[-3 * bar:], lo=1200)
        # après le drop : rien que l'écho (un ralenti ou un disque en arrière qui redémarre sous B, non)
        return real, np.concatenate([loop[:hold], effect(hist, tail)]), None
    return build


def retour_doux(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """A perd ses graves, tourne en boucle pendant que B monte, puis repart à l'envers sur une mesure."""
    build = _loop_then(m, end_a, bar, lambda hist, nxt: _spin(hist, len(nxt), lo=1200))
    return _douce(m, end_a, start_b, bar, ratio, pre, extra, build, "retour arrière")


def frein_doux(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """A perd ses graves, tourne en boucle pendant que B monte, puis ralentit jusqu'à l'arrêt sur une mesure."""
    build = _loop_then(m, end_a, bar, lambda hist, nxt: _brake(nxt, lo=1200))
    return _douce(m, end_a, start_b, bar, ratio, pre, extra, build, "frein")


def filtre(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """A se ferme peu à peu (passe-bas de 18 kHz à 200 Hz : il ne reste que ses basses), sa phrase réelle
    (4 dernières mesures) rejouée pendant que B monte dessous, sans ses basses jusqu'au drop."""
    a = m.read(end_a - 4 * bar, end_a)

    def build(E):
        mat = np.concatenate([a, _loop(a, E * (bar // 4))])
        eff = sweep(mat, hi=lambda t: 18000 * (200 / 18000) ** (t ** 1.5)) * smooth(len(mat), 1.0, 0.75)
        return eff[:4 * bar], eff[4 * bar:]
    return _douce(m, end_a, start_b, bar, ratio, pre, extra, build, "balayage de filtre", b_lo=250)


def drop_swap(m, end_a, start_b, bar, ratio, pre=0, extra=0):
    """Pour les morceaux percussifs : un vrai échange, pas un fondu. A perd ses graves sur 2 mesures, sa
    dernière mesure tourne puis se resserre en roulements de plus en plus aigus (la tension monte). B reste
    absent jusqu'à son drop, sauf son premier temps joué à l'envers qui enfle sur le dernier temps de A
    (il annonce B sans le fondre). Puis B tombe à plein, basses comprises, sous une nappe faite du dernier
    temps de A. À l'écoute : B à plein sans annonce « trop sec » (essai 16), B qui monte en fondu « juste un
    fondu, nul » (essai 19)."""
    beat = bar // 4
    beat_b = int(beat * ratio)
    a = m.read(end_a - 2 * bar, end_a)
    drop = start_b + pre + entry_kick(m, start_b + pre, beat_b)
    L = 8 * beat_b
    m.wait(drop + L)
    g = _gain(a, m.read(drop, drop + L))
    # mesures entières (le drop de B tombe sur un premier temps de A), au moins une pour la montée de tension
    hold = max(bar, -(-max(0, drop - end_a + extra) // bar) * bar)
    rolls, rest = _stages(a[bar:bar + beat], beat, [(2, beat, 600, 1.0, 1.02), (4, beat, 900, 1.02, 1.06),
                                                   (8, beat, 1400, 1.08, 1.12), (16, beat, 2000, 1.12, 1.19)], bar)
    ext = np.concatenate([_loop(band(a[bar:], lo=300), hold - bar + rest), rolls])
    rev = band(m.read(drop, drop + beat_b)[::-1].copy(), lo=1000) * smooth(beat_b, 0.0, 0.8) ** 2 * g
    rev = rev[-len(ext):]
    ext[-len(rev):] += rev
    b = m.read(drop, drop + L) * g + _wash(edges(band(m.read(end_a - beat, end_a), lo=300), 3), L)
    m.log(f"drop swap : A prolongé de {hold / SR:.2f} s (roulements sur la dernière mesure), B à plein sur son drop, gain {g:.2f}")
    return _finish(m, end_a - 2 * bar, np.concatenate([_hp_rise(a, 300), ext, b]), drop + L, g)


def melange(m, end_a, start_b, bar, ratio, pre=0, extra=0, bars=8):
    """Superposition de `bars` mesures réelles de A et de B, qui finit sur le drop de B (B lancé à son entrée
    = drop moins `bars` mesures). Le tempo glisse temps par temps de celui de A vers celui de B (article
    Spotify 2017). Refus si les tempos sont trop éloignés ou si B n'a pas de pulsation nette. Tempo double ou
    moitié : B est compté en unités de deux temps ou d'un demi-temps."""
    d1 = bar / 4
    d2, rr = _unit(d1, d1 * ratio)  # durée d'une unité de B à son propre tempo
    if abs(rr - 1) > 0.06:
        raise Refus(f"tempos trop éloignés ({abs(rr - 1) * 100:.0f} %)")
    start_b += pre
    N = bars * 4
    dout = np.array([((N - n) / N) * d1 + (n / N) * d2 for n in range(N)])
    dst = np.concatenate([[0], np.cumsum(dout)]).round()
    L = int(dst[-1])
    b0 = start_b + entry_kick(m, start_b, int(d2))
    a_src = m.read(end_a - int(N * d1), end_a)
    # Calage par la pulsation, comme un DJ : où tombent les temps de B (phase de ses attaques repliée sur
    # 8 unités), puis le temps de B le plus proche de son entrée est posé sur celui de A (la fin de A est déjà
    # sur ses temps, cf. grid_end). On ne demande pas aux deux rythmes de se ressembler : en rap, deux
    # morceaux parfaitement calés ont des motifs différents (808, charleston), et l'ancien test de
    # ressemblance refusait des paires à 144/144 BPM (essai du 26/10). Refus seulement si B n'a pas de
    # pulsation nette. Décidé sur 2 mesures de B : le repli doit rester prêt à temps.
    if _snap():  # sans grille de Spotify : recalage sur la pulsation des attaques
        h, half, wb = int(0.005 * SR), int(d2 / 2), int(8 * d2)
        lo = max(start_b, b0 - half)
        m.wait(lo + wb + int(d2))
        phase, strength = _beat_phase(kick_env(m.read(lo, lo + wb)), d2, h)
        if strength < 1.4:
            raise Refus(f"pulsation de B introuvable (netteté {strength:.2f})")
        grid0 = lo + phase
        b_new = int(round(grid0 + round((b0 - grid0) / d2) * d2))
        m.log(f"mélange : temps de B recalé de {(b_new - b0) / SR * 1000:+.0f} ms (pulsation nette à {strength:.1f})")
        b0 = max(start_b, b_new)
    m.wait(b0 + int(N * d2) + SR)
    b_src = m.read(b0, b0 + int(N * d2))
    g = _gain(a_src[-int(16 * d1):], b_src[-int(8 * d2):])
    a = _fit(stretch_map(a_src, np.arange(N + 1) * d1, dst), L)
    b = _fit(stretch_map(b_src, np.arange(N + 1) * d2, dst), L) * g
    # Superposition à la manière d'Apple / Spotify (refonte du 26/10, après « toujours le même système ») :
    # la vraie fin de A sous les vraies mesures de B qui précèdent son drop, sans boucle ni effet synthétique.
    # - B monte jusqu'à son plein volume à 70 % (courbe en S), sans graves ni aigus ; sa batterie d'abord,
    #   sa voix et ses nappes seulement sur le dernier quart (pas deux voix superposées) ;
    # - A reste à plein jusqu'à mi-chemin puis descend vers 0,25 ;
    # - au drop de B (fin de la superposition) : l'échange, en ½ temps, graves et aigus de B rendus, A coupé
    #   sous sa réverbération qui s'éteint sur une mesure de B.
    # La grosse caisse de B reste audible (seule la sous-basse, sous 120 Hz, attend le drop) et sa batterie
    # entre franchement dès le début : c'est elle qui fait entendre que les deux morceaux sont calés. Sans elle
    # (B filtré sous 400 Hz quand les motifs différaient), la superposition sonnait « juste un fondu simple,
    # sans caler aucun rythme » (essai 28).
    agree = kick_agreement(a, b)
    # Contrôle du calage sur le son produit : chaque morceau est confronté à la grille commune de la
    # superposition (les repères `dst`, où A et B doivent avoir leurs temps). Écart de A, écart de B, et leur
    # différence = l'erreur de calage, quels que soient les motifs de batterie (comparer les attaques de A à
    # celles de B se contredisait en rap, où deux morceaux calés ne frappent pas aux mêmes endroits).
    ea, sa = _grid_fit(a, dst[:-1])
    eb, sb = _grid_fit(b, dst[:-1])
    m.log(f"superposition : calage mesuré sur la grille commune : A {ea:+.0f} ms (netteté {sa:.1f}), "
          f"B {eb:+.0f} ms (netteté {sb:.1f}), écart B - A {eb - ea:+.0f} ms")
    # Boucle de correction : l'écart mesuré (25 à 90 ms sur 5 paires de rap le 26/10, calage sur la grille de
    # Spotify seule) est retiré en relisant B décalé d'autant, puis remesuré. Seulement si les deux mesures
    # sont nettes, sinon on corrigerait au hasard.
    if sa >= 2.5 and sb >= 2.5 and 10 <= abs(eb - ea) <= 150:
        b0 += int(round((eb - ea) / 1000 * SR * d2 / dout.mean()))
        b_src = m.read(b0, b0 + int(N * d2))
        b = _fit(stretch_map(b_src, np.arange(N + 1) * d2, dst), L) * g
        eb, sb = _grid_fit(b, dst[:-1])
        m.log(f"superposition : B corrigé : écart B - A {eb - ea:+.0f} ms (netteté {sb:.1f})")
    b_lo = 120
    m.log(f"superposition : tempo de {60 * SR / d1:.1f} à {60 * SR / d2:.1f} BPM, ressemblance des grosses caisses "
          f"{agree:.2f}, gain de B {g:.2f}")
    p = np.linspace(0, 1, L, dtype=np.float32)
    s = lambda x: 3 * x ** 2 - 2 * x ** 3  # noqa: E731
    vb = np.where(p < 0.7, 0.45 + 0.55 * s(np.clip(p / 0.7, 0, 1)), 1.0)[:, None]
    va = np.where(p < 0.5, 1.0, 1.0 - 0.75 * s(np.clip((p - 0.5) / 0.5, 0, 1)))[:, None]
    vox = np.clip((p - 0.75) / 0.25, 0, 1)[:, None]
    b = _percussive(b) * (1 - vox) + b * vox
    b = sweep(b, lo=lambda t: b_lo, hi=lambda t: 6000)
    seg = a * va + b * vb
    # L'échange au drop : ½ temps de B qui retrouve graves et aigus, puis une mesure de B à plein sous la
    # réverbération du dernier temps de A
    b_end = b0 + int(N * d2)
    bar_b = int(4 * d2)
    m.wait(b_end + bar_b)
    land = m.read(b_end, b_end + bar_b) * g
    hb = max(1, int(d2) // 2)
    land[:hb] = sweep(land[:hb], lo=lambda t: b_lo * (20 / b_lo) ** t, hi=lambda t: 6000 * (20000 / 6000) ** t)
    land += _wash(edges(band(a_src[-int(d1):], lo=300), 3), bar_b) * 0.6
    return _finish(m, end_a - int(N * d1), np.concatenate([seg, land]), b_end + bar_b, g)


RENDERERS = {"montee": montee, "montee_courte": montee_courte, "echo_doux": echo_doux, "retour_doux": retour_doux,
             "frein_doux": frein_doux, "filtre": filtre, "drop_swap": drop_swap, "melange": melange, "secours": secours}
# Préréglages qui font monter B sous la fin de A : ils attendent B lancé ~8 mesures de A avant son entrée
DOUX = {"montee", "montee_courte", "echo_doux", "retour_doux", "frein_doux", "filtre"}
