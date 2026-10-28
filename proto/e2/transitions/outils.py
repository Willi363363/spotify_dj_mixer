"""Outils de traitement gardés de l'ancien code (ADR 0004), sans changement de comportement sauf indiqué.

Viennent de recettes.py (ramp, smooth, band, sweep, edges, level, limiter, rubberband, stretch_map, kick_env, Refus)
et de rendu.py (fit, loop, resample, percussive, frein, unit, gain, finir ; anciens noms avec « _ »).
Changements : `band` et `sweep` acceptent `ordre` (2 = 12 dB/oct, demandé par la spec ; 4 = comportement d'avant,
par défaut) ; `frein` suit la courbe de C3 (ADR 0006).
"""
import os
import subprocess
import tempfile
import wave

import numpy as np

SR, CH = 44100, 2


class Refus(Exception):
    """Le rendu est impossible dans ces conditions : l'échelle de repli passe au suivant."""


def ramp(n, a, b):
    return np.linspace(a, b, n, dtype=np.float32)[:, None]


def smooth(n, a, b):
    """Courbe en S (lissée aux deux bouts), plus naturelle qu'une droite pour un volume."""
    t = np.linspace(0, 1, n, dtype=np.float32)
    return (a + (b - a) * (3 * t ** 2 - 2 * t ** 3))[:, None]


def band(x, lo=None, hi=None, ordre=4):
    """Filtre par FFT, sans déphasage : garde [lo, hi] avec des flancs de pente `ordre` × 6 dB/oct (amplitude
    Butterworth). Le signal est complété de zéros avant la FFT : sans ça, la FFT circulaire replie la fin du signal
    sur son début (petits clics aux bords des tranches courtes)."""
    if len(x) == 0:
        return x.astype(np.float32)
    n = 2 * len(x)
    f = np.fft.rfftfreq(n, 1 / SR)[:, None]
    m = np.ones_like(f)
    p = 2 * ordre
    if lo:
        m = m / np.sqrt(1 + (lo / np.maximum(f, 1)) ** p)
    if hi:
        m = m / np.sqrt(1 + (f / hi) ** p)
    return np.fft.irfft(np.fft.rfft(x, n=n, axis=0) * m, n=n, axis=0)[: len(x)].astype(np.float32)


def sweep(x, lo=None, hi=None, w=4096, ordre=4):
    """Filtre qui évolue dans le temps, sans clic : trames de Hann à 50 % de recouvrement, chacune
    filtrée avec sa propre fréquence. `lo` / `hi` sont des fonctions de t ∈ [0, 1] → Hz (ou None)."""
    hop = w // 2
    win = np.hanning(w + 1)[:w].astype(np.float32)[:, None]  # Hann périodique : la somme vaut 1
    pad = np.concatenate([np.zeros((hop, CH), np.float32), x, np.zeros((w, CH), np.float32)])
    out = np.zeros_like(pad)
    for s in range(0, len(pad) - w, hop):
        t = min(1.0, max(0.0, (s - hop + w / 2) / max(1, len(x))))
        out[s:s + w] += band(pad[s:s + w] * win, lo and lo(t), hi and hi(t), ordre)
    return out[hop:hop + len(x)]


def edges(x, ms=3):
    """Fondus de quelques ms aux deux bouts d'une tranche, pour qu'une reprise ne claque pas.
    À appliquer après les filtres, pour que le filtre ne réintroduise pas de bord franc."""
    n = min(int(ms / 1000 * SR), len(x) // 2)
    x = x.copy()
    if n:
        x[:n] *= ramp(n, 0, 1)
        x[-n:] *= ramp(n, 1, 0)
    return x


def level(x):
    """Niveau perçu, à la manière de la norme BS.1770 (LUFS) : pondération K (passe-haut vers 40 Hz,
    aigus au-dessus de 1,5 kHz relevés de 4 dB), puissance par blocs de 400 ms, blocs plus de 10 dB sous
    la moyenne écartés (silences, fins de phrase). Rendu en amplitude efficace."""
    h = int(0.4 * SR)
    if len(x) < h:
        return 1e-6
    f = np.fft.rfftfreq(h, 1 / SR)
    w = (1 / (1 + (40 / np.maximum(f, 1)) ** 4)) * (1 + 0.585 / (1 + (1500 / np.maximum(f, 1)) ** 2)) ** 2
    win = np.hanning(h)[:, None]
    p = np.array([(np.abs(np.fft.rfft(x[i:i + h] * win, axis=0)) ** 2 * w[:, None]).sum()
                  for i in range(0, len(x) - h + 1, h // 2)])
    p = p[p > p.mean() * 0.1] if (p > 0).any() else p
    return float(np.sqrt(p.mean() / (h * (win ** 2).mean() * h)) + 1e-6)


def limiter(seg, ceiling=0.97, edge_ms=150):
    """Évite l'écrêtage d'un segment sans saut de volume : gain qui ne baisse que là où la crête dépasse,
    avec attaque rapide et retour lent, et qui vaut exactement 1 aux deux bouts (raccord avec le flux)."""
    h = int(0.01 * SR)
    n = len(seg) // h + 1
    peaks = np.array([np.abs(seg[i * h:(i + 1) * h]).max() if i * h < len(seg) else 0 for i in range(n)])
    target = np.minimum(1.0, ceiling / np.maximum(peaks, 1e-9))
    # anticipation de 30 ms : la baisse commence avant la crête
    target = np.array([target[max(0, i - 1):i + 3].min() for i in range(n)])
    g, out = 1.0, np.empty(n)
    for i, t in enumerate(target):
        g = t if t < g else g + (t - g) * 0.05  # attaque immédiate, retour lent (~200 ms)
        out[i] = g
    gain = np.interp(np.arange(len(seg)), np.arange(n) * h, out).astype(np.float32)
    e = min(int(edge_ms / 1000 * SR), len(seg) // 2)
    if e:
        gain[:e] = 1 + (gain[:e] - 1) * np.linspace(0, 1, e)
        gain[-e:] = 1 + (gain[-e:] - 1) * np.linspace(1, 0, e)
    return (seg * gain[:, None]).astype(np.float32)


def rubberband(x, args):
    """Passe x dans la commande rubberband (étirement de qualité, hauteur conservée)."""
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.wav"), os.path.join(d, "out.wav")
        with wave.open(src, "wb") as w:
            w.setnchannels(CH); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
        subprocess.run(["rubberband", "-q", *[a.replace("{dir}", d) for a in args], src, dst], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(dst) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, CH).astype(np.float32) / 32767


_rubberband = rubberband  # ancien nom, appelé par e2.slower


def stretch_map(x, src_marks, dst_marks):
    """Étire x pour que chaque repère source tombe sur son repère cible (un repère par temps)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "map.txt")
        with open(path, "w") as f:
            for s, t in zip(src_marks, dst_marks):
                f.write(f"{int(s)} {int(t)}\n")
        y = rubberband(x, ["-M", path, "-D", f"{dst_marks[-1] / SR:.6f}"])
    y = y[: int(dst_marks[-1])]
    return np.concatenate([y, np.zeros((int(dst_marks[-1]) - len(y), CH), np.float32)])


def kick_env(x):
    """Enveloppe des attaques de grosse caisse : énergie 40-150 Hz par pas de 5 ms, montées seules."""
    lo = band(x.mean(axis=1, keepdims=True), lo=40, hi=150)[:, 0]
    h = int(0.005 * SR)
    e = np.sqrt((lo[: len(lo) // h * h].reshape(-1, h) ** 2).mean(axis=1))
    d = np.maximum(0, np.diff(e, prepend=e[0]))
    return (d - d.mean()) / (d.std() + 1e-9)


def fit(x, n):
    """x coupé ou complété de silence à n échantillons."""
    n = int(n)
    return x[:n] if len(x) >= n else np.concatenate([x, np.zeros((n - len(x), CH), np.float32)])


def resample(x, n):
    """x ramené à n échantillons par interpolation linéaire (change aussi la hauteur)."""
    pos = np.linspace(0, len(x) - 1, n)
    return np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(CH)], axis=1).astype(np.float32)


def loop(x, n):
    """x répété sur n échantillons, chaque reprise adoucie pour ne pas claquer."""
    n = int(n)
    if n <= 0 or len(x) == 0:
        return np.zeros((max(n, 0), CH), np.float32)
    piece = edges(x, 2)
    return edges(np.tile(piece, (-(-n // len(piece)), 1))[:n], 2)


def percussive(x, w=2048):
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


def vitesse_frein(n, k=4.0):
    """Vitesse du frein (C3) sur n échantillons : de 1 à 0 en courbe exponentielle."""
    t = np.linspace(0, 1, n)
    return ((np.exp(-k * t) - np.exp(-k)) / (1 - np.exp(-k))).astype(np.float64)


def frein(x, n, f0=16000.0, f1=500.0):
    """Disque qui s'arrête (C3, ADR 0006) : x lu de plus en plus lentement sur n échantillons de sortie (vitesse
    `vitesse_frein`, hauteur non conservée), sous un passe-bas balayé de f0 à f1 Hz (12 dB/oct, expo).
    x doit commencer au début du frein ; il en consomme moins que n."""
    v = vitesse_frein(n)
    pos = np.concatenate([[0.0], np.cumsum(v)[:-1]])
    pos = np.minimum(pos, len(x) - 1)
    out = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(CH)], axis=1).astype(np.float32)
    out = sweep(out, hi=lambda t: f0 * (f1 / f0) ** t, ordre=2)
    # le volume suit la vitesse (un disque qui s'arrête s'éteint) : pas de valeur figée qui claquerait à la fin
    return (out * np.sqrt(v)[:, None]).astype(np.float32)


def unit(beat, beat_b):
    """Pulsation de B ramenée près de celle de A (mix à tempo double ou moitié) : (durée, rapport à A)."""
    u = min((beat_b * f for f in (0.5, 1.0, 2.0)), key=lambda v: abs(np.log(v / beat)))
    return u, u / beat


def gain(a, b):
    """Gain qui ramène B au niveau de A, borné à 0,8..1,0 et par la marge de crête de B : les masters
    rap / shatta frôlent 0 dBFS, un gain au-dessus de 1 ferait écrêter leur drop. Jamais de hausse."""
    if len(a) == 0 or len(b) == 0:
        return 1.0
    return float(np.clip(min(level(a) / level(b), 0.97 / max(float(np.abs(b).max()), 1e-6)), 0.8, 1.0))


CRETE = 10 ** (-0.35 / 20)  # O5 : crête ≤ −0,3 dBFS


def finir(m, start, seg, resume, g, ceiling=CRETE):
    """Limiteur (plafond −0,35 dBFS, O5), puis raccords de 20 ms avec le flux aux deux bouts (le flux reprend avec
    le gain g)."""
    seg = limiter(seg, ceiling)
    f = min(int(0.02 * SR), len(seg) // 2)
    seg[:f] = m.read(start, start + f) * ramp(f, 1, 0) + seg[:f] * ramp(f, 0, 1)
    seg[-f:] = seg[-f:] * ramp(f, 1, 0) + m.read(resume - f, resume) * g * ramp(f, 0, 1)
    return start, seg.astype(np.float32), resume, g
