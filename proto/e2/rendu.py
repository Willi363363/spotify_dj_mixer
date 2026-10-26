"""Rendu des préréglages de recettes.py à partir de la mémoire de e2.py.

Chaque fonction reçoit `m` (accès à la mémoire : m.buf, m.wait(n), m.log), la fin de A et le début
de B dans la mémoire, la durée d'une mesure de A et le rapport de tempo A / B. Elle rend
(début du segment, segment, reprise du flux, raison d'un éventuel repli).
"""
import numpy as np

from recettes import CH, SR, Refus, band, edges, kick_agreement, kick_env, pitched, ramp, smooth, stretch_map, sweep


def entry_kick(m, start_b, beat):
    """Décalage jusqu'à l'attaque de grosse caisse la plus forte des 3/4 de temps qui suivent le début de B.
    L'analyse commence 30 ms avant, dans le silence de Spotify : sinon une attaque pile au début est invisible
    (l'enveloppe ne mesure que les montées) et on prend la grosse caisse du temps suivant."""
    m.wait(start_b + 2 * beat)
    pre, h = int(0.03 * SR), int(0.005 * SR)
    env = kick_env(m.buf[start_b - pre:start_b + int(0.75 * beat)])
    return max(0, int(np.argmax(env)) * h - pre)


def coupe(m, end_a, start_b, bar, ratio):
    """A s'arrête sur son premier temps, B part sur le sien ; 5 ms de fondu pour éviter le claquement."""
    first = entry_kick(m, start_b, bar // 4)
    n = int(0.005 * SR)
    return end_a - n, m.buf[end_a - n:end_a] * ramp(n, 1, 0), start_b + first


def montee(m, end_a, start_b, bar, ratio, pre=0):
    """Montée validée à l'écoute : 4 mesures de A dont les graves partent, puis roulements de plus en plus
    serrés et aigus jusqu'au drop de B, sans blanc. Si B a été lancé `pre` échantillons avant son drop,
    ces mesures montent sous les derniers roulements (sans basses, filtre qui s'ouvre) et B enchaîne
    sur son drop sans raccord : son arrivée n'est plus sèche."""
    if pre:
        return _montee_douce(m, end_a, start_b, bar, pre)
    beat = bar // 4
    a = m.buf[end_a - 8 * bar:end_a].copy()
    parts = [edges(band(a[k * beat:(k + 1) * beat], lo=20 + 280 * (k / 15) ** 2), 2) for k in range(16)]
    src = a[4 * bar:4 * bar + beat]  # le premier temps de la mesure 5 sert de matière aux roulements
    # (division du temps, répétitions, coupure des graves en Hz, vitesse de départ, vitesse d'arrivée)
    for div, count, lo, r0, r1 in [(1, 4, 300, 1.0, 1.0), (2, 8, 500, 1.0, 1.03), (4, 16, 800, 1.04, 1.12),
                                   (8, 16, 1400, 1.12, 1.3), (16, 32, 2000, 1.3, 1.5)]:
        piece = src[: beat // div]
        for i in range(count):
            r = r0 + (r1 - r0) * i / max(1, count - 1)
            parts.append(edges(band(pitched(piece, r), lo=lo) * (0.8 + 0.2 * i / count), 1))
    seg = np.concatenate(parts)
    seg = np.concatenate([seg, np.zeros((8 * bar - len(seg), CH), dtype=np.float32)])  # 8 mesures pile
    return end_a - 8 * bar, seg, start_b + entry_kick(m, start_b, beat)


def _montee_douce(m, end_a, start_b, bar, pre):
    beat = bar // 4
    _, seg, _ = montee(m, end_a, start_b + pre, bar, 1.0)  # la montée seule, B recalé plus bas
    drop = start_b + pre + entry_kick(m, start_b + pre, beat)
    n = min(drop - start_b, 2 * bar, len(seg))  # au plus les 2 dernières mesures de la montée
    m.wait(drop + beat)
    b_pre = m.buf[drop - n:drop].copy()
    # B monte sous les roulements : filtre qui s'ouvre de 1500 à 120 Hz, volume de 0 à 0,85
    b_pre = sweep(b_pre, lo=lambda t: 1500 * (120 / 1500) ** t) * smooth(n, 0.0, 0.85)
    seg = seg.copy()
    seg[-n:] = seg[-n:] * smooth(n, 1.0, 0.55) + b_pre  # les roulements s'effacent un peu pour faire place
    peak = float(np.abs(seg).max())
    if peak > 0.98:
        seg *= 0.98 / peak
    m.log(f"montée douce : B monte sur les {n / SR:.2f} dernières secondes, drop recalé à {(drop - start_b - pre) / SR * 1000:.0f} ms")
    return end_a - 8 * bar, seg, drop


def retour(m, end_a, start_b, bar, ratio):
    """Disque ramené en arrière à la main sur la dernière mesure de A (vitesse en sinus, jusqu'à 3,5 fois)."""
    t = np.arange(bar) / bar
    start = end_a - bar
    pos = np.clip(start - np.cumsum(3.5 * np.sin(np.pi * t) ** 1.3), 0, None)
    out = np.stack([np.interp(pos, np.arange(start - 4 * bar, start), m.buf[start - 4 * bar:start, c], left=0)
                    for c in range(CH)], axis=1).astype(np.float32)
    out = band(out, lo=60) * ramp(bar, 1.0, 0.0) ** 0.5
    return start, edges(out, 2), start_b + entry_kick(m, start_b, bar // 4)


def frein(m, end_a, start_b, bar, ratio):
    """Vinyle qui ralentit jusqu'à l'arrêt sur la dernière mesure de A, puis B sur le premier temps."""
    tail = m.buf[end_a - bar:end_a]
    pos = np.cumsum(np.linspace(1.0, 0.0, bar) ** 1.5)
    pos = pos[pos < bar - 1]
    out = np.stack([np.interp(pos, np.arange(bar), tail[:, c]) for c in range(CH)], axis=1).astype(np.float32)
    out = np.concatenate([out * ramp(len(out), 1, 0.6), np.zeros((bar - len(out), CH), np.float32)])
    return end_a - bar, edges(out, 2), start_b + entry_kick(m, start_b, bar // 4)


def boucle(m, end_a, start_b, bar, ratio):
    """Dernière mesure de A rejouée 4 fois depuis la mémoire, puis B net sur le premier temps."""
    seg = np.concatenate([edges(m.buf[end_a - bar:end_a], 1)] * 4)
    return end_a, seg, start_b + entry_kick(m, start_b, bar // 4)


def echo(m, end_a, start_b, bar, ratio):
    """B part net sur le premier temps ; par-dessus, le dernier temps de A se répète tous les ½ temps,
    sans graves, en s'éteignant sur 2 mesures (« Echo ½ out end » de Spotify)."""
    beat = bar // 4
    first = entry_kick(m, start_b, beat)
    b0, L = start_b + first, 2 * bar
    m.wait(b0 + L)
    src = band(edges(m.buf[end_a - beat:end_a], 3), lo=300)
    tail = np.zeros((L + beat, CH), np.float32)
    for k in range(1, 12):
        s = k * beat // 2
        if s >= L:
            break
        tail[s:s + beat] += src * (0.55 ** k)
    seg = m.buf[b0:b0 + L] + tail[:L]
    return end_a, seg, b0 + L


def melange(m, end_a, start_b, bar, ratio, bars=8):
    """Superposition de `bars` mesures. Le tempo glisse temps par temps de celui de A vers celui de B
    (méthode de l'article Spotify 2017) ; échange des basses au centre ; B entre vite, A sort lentement
    sous un passe-bas qui se ferme. Refus si les tempos sont trop éloignés ou si les temps ne se calent pas."""
    if not 0.94 <= ratio <= 1.06:
        raise Refus(f"tempos trop éloignés ({abs(ratio - 1) * 100:.0f} %)")
    N, d1 = bars * 4, bar / 4
    d2 = d1 * ratio                      # durée d'un temps de B à son propre tempo
    dout = np.array([((N - n) / N) * d1 + (n / N) * d2 for n in range(N)])
    dst = np.concatenate([[0], np.cumsum(dout)]).round()
    L = int(dst[-1])
    b0 = start_b + entry_kick(m, start_b, int(d2))
    m.wait(b0 + int(N * d2) + SR)
    a_src = m.buf[end_a - int(N * d1):end_a]
    # Calage fin : décalage de B (±½ temps) qui accorde le mieux ses grosses caisses avec A sur les
    # 2 premières mesures, où les tempos n'ont pas encore dérivé. Indispensable quand la grosse caisse
    # n'est pas sur chaque temps (bouyon, shatta).
    win, h = int(8 * d1), int(0.005 * SR)
    shifts = range(-int(d2 / 2), int(d2 / 2), h)
    score = {s: kick_agreement(a_src[:win], m.buf[b0 + s:b0 + s + win]) for s in shifts if b0 + s >= start_b}
    s_best = max(score, key=score.get)
    m.log(f"mélange : B décalé de {s_best / SR * 1000:+.0f} ms, accord sur 2 mesures {score.get(0, 0):.2f} -> {score[s_best]:.2f}")
    b0 += s_best
    b_src = m.buf[b0:b0 + int(N * d2)]
    a = stretch_map(a_src, np.arange(N + 1) * d1, dst)[:L]
    b = stretch_map(b_src, np.arange(N + 1) * d2, dst)[:L]
    a, b = [np.concatenate([x, np.zeros((L - len(x), CH), np.float32)]) for x in (a, b)]
    agree = kick_agreement(a, b)
    m.log(f"mélange : tempo de {60 * SR / d1:.1f} à {60 * SR / d2:.1f} BPM, accord des grosses caisses {agree:.2f}")
    if agree < 0.15:
        raise Refus(f"temps mal calés (accord {agree:.2f})")
    half, xf = L // 2, int(0.03 * SR)
    swap = np.concatenate([np.zeros(half - xf), np.linspace(0, 1, xf), np.ones(L - half)])[:L, None].astype(np.float32)
    a_eq = a * (1 - swap) + band(a, lo=200) * swap
    b_eq = band(b, lo=200) * (1 - swap) + b * swap
    a_eq = sweep(a_eq, hi=lambda t: 20000 if t < 0.6 else 20000 * (300 / 20000) ** ((t - 0.6) / 0.4))
    q = L // 4
    vol_b = np.concatenate([smooth(q, 0, 1), np.ones((L - q, 1), np.float32)])
    vol_a = np.concatenate([np.ones((L - 2 * q, 1), np.float32), smooth(2 * q, 1, 0)])
    seg = a_eq * vol_a + b_eq * vol_b
    peak = float(np.abs(seg).max())
    if peak > 0.98:  # pas de bosse de volume : on ramène la crête sous le maximum
        seg *= 0.98 / peak
    return end_a - int(N * d1), seg.astype(np.float32), b0 + int(N * d2)


RENDERERS = {"coupe": coupe, "montee": montee, "retour": retour, "frein": frein, "boucle": boucle,
             "echo": echo, "melange": melange}
