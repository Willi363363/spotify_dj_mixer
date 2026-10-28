"""Morceaux de synthèse pour les tests hors ligne (grille connue, basse, voix factice).

- `track(bpm, secondes, note, basse=False, voix=[(t0, t1), …])` : grosse caisse sur chaque temps (le temps 0 est
  un « 1 »), nappe à `note` Hz, charleston sur les demi-temps, basse 808 facultative, voix factice sur les
  intervalles donnés (ADR 0002 : source harmonique F0 120 à 250 Hz avec vibrato, 2 formants qui changent toutes les
  150 à 250 ms, modulation d'amplitude 4 à 6 Hz).
- `Mem` : A puis le trou du saut puis B, comme la mémoire de e2.py (read, wait, log). A finit sur un « 1 ».
- `Mem.place()` et `ordre()` : Place et Ordre v2 construits à la main pour appeler un rendu sans e2.py.
Usage : `sys.path.insert(0, "proto/e2")` puis `import synthese`.
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transitions.contrat import Place, valider_ordre  # noqa: E402
from transitions.outils import CH, SR, band  # noqa: E402


def voix_factice(n, segments, seed=7, niveau=0.25):
    """Voix chantée/rappée factice sur n échantillons, présente sur les intervalles `segments` (secondes)."""
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(seed)
    for t0, t1 in segments:
        i0, i1 = max(0, int(t0 * SR)), min(n, int(t1 * SR))
        m = i1 - i0
        if m <= 0:
            continue
        t = np.arange(m) / SR
        # syllabes de 150 à 250 ms : F0 et formants changent à chacune
        bords = [0]
        while bords[-1] < m:
            bords.append(bords[-1] + int(rng.uniform(0.15, 0.25) * SR))
        bords[-1] = m
        f0 = np.empty(m)
        f1 = np.empty(m)
        f2 = np.empty(m)
        for s, e in zip(bords[:-1], bords[1:]):
            f0[s:e] = rng.uniform(120, 250)
            f1[s:e] = rng.uniform(300, 900)
            f2[s:e] = rng.uniform(900, 2500)
        k = np.ones(int(0.01 * SR)) / int(0.01 * SR)  # transitions de 10 ms entre syllabes
        f0, f1, f2 = (np.convolve(np.pad(x, (len(k), len(k)), mode="edge"), k, mode="same")[len(k):-len(k)]
                      for x in (f0, f1, f2))
        f0 = f0 * (1 + 0.03 * np.sin(2 * np.pi * 5.5 * t))  # vibrato
        ph = 2 * np.pi * np.cumsum(f0) / SR
        y = np.zeros(m)
        for h in range(1, 30):
            fh = h * f0
            amp = (np.exp(-((fh - f1) / 120) ** 2) + 0.7 * np.exp(-((fh - f2) / 200) ** 2) + 0.02) / h ** 0.5
            amp[fh > 4000] = 0
            y += amp * np.sin(h * ph)
        am = 0.55 + 0.45 * np.sin(2 * np.pi * rng.uniform(4, 6) * t)  # débit syllabique
        y *= am / (np.abs(y).max() + 1e-9)
        f = min(int(0.01 * SR), m // 2)
        if f:
            y[:f] *= np.linspace(0, 1, f)
            y[-f:] *= np.linspace(1, 0, f)
        out[i0:i1] += (niveau * y).astype(np.float32)
    return out


def track(bpm, seconds, note, basse=False, voix=(), seed=1, riche=False):
    """Morceau de synthèse stéréo (n, CH) float32 ; les temps tombent sur k × 60 / bpm secondes."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    beat = 60 / bpm
    phase = t % beat
    kick = np.sin(2 * np.pi * (50 + 100 * np.exp(-phase * 30)) * phase) * np.exp(-phase * 12)
    pad = 0.15 * np.sin(2 * np.pi * note * t)
    # charleston sur chaque demi-temps : des aigus, comme dans la vraie musique
    hat = 0.05 * np.random.default_rng(seed).standard_normal(n) * np.exp(-(t % (beat / 2)) * 60)
    hat = band(hat[:, None].astype(np.float32), lo=5000)[:, 0]
    if riche:  # nappe à 8 harmoniques (jusqu'à ~2,6 kHz) : des médiums, comme un accord de synthé
        pad = sum(0.15 / k * np.sin(2 * np.pi * k * note * t) for k in range(1, 9))
    x = kick * 0.6 + pad + hat
    if basse:  # 808 : attaque sur chaque temps, longue tenue (la basse qui ne doit jamais être doublée)
        x = x + 0.3 * np.sin(2 * np.pi * 55 * phase) * np.exp(-phase * 3) * np.minimum(1, phase / 0.003)
    if voix:
        x = x + voix_factice(n, voix, seed=seed + 6)
    return np.stack([x] * CH, axis=1).astype(np.float32)


class Mem:
    """A (`mesures_a` mesures à bpm_a) puis `gap_s` de silence puis B (`mesures_b` mesures à bpm_b).
    `off` décale B de quelques échantillons (silence en plus avant son premier temps)."""
    log = staticmethod(lambda *a: None)

    def __init__(self, bpm_b=120, off=0, bpm_a=120, *, mesures_a=24, mesures_b=24, basse=True, voix_a=(), voix_b=(),
                 gap_s=0.35, note_a=220, note_b=330, riche=False):
        self.bpm_a, self.bpm_b = bpm_a, bpm_b
        self.beat_a, self.beat_b = 60 / bpm_a * SR, 60 / bpm_b * SR
        da, db = mesures_a * 4 * 60 / bpm_a, mesures_b * 4 * 60 / bpm_b
        a = track(bpm_a, da, note_a, basse=basse, voix=voix_a, seed=1, riche=riche)
        b = track(bpm_b, db, note_b, basse=basse, voix=voix_b, seed=2, riche=riche)
        gap = np.zeros((int(gap_s * SR) + off, CH), np.float32)
        self.buf = np.concatenate([a, gap, b])
        self.end_a, self.start_b = len(a), len(a) + len(gap)
        self.journal = []

    def read(self, a, b):
        assert 0 <= a <= b <= len(self.buf), f"lecture hors mémoire ({a}..{b}, {len(self.buf)})"
        return self.buf[int(a):int(b)].copy()

    def wait(self, n):
        assert n <= len(self.buf), "le rendu demande plus de son que la mémoire n'en a"

    def place(self, grille=True, extra=0, nettete=4.0, fin_a=None, debut_b=None):
        """Place exacte (la grille de synthèse est connue) ; grille=False : sans temps de Spotify."""
        fa = self.end_a if fin_a is None else fin_a
        db = self.start_b if debut_b is None else debut_b
        ba = np.arange(0, self.end_a + 1, self.beat_a)
        bb = self.start_b + np.arange(0, len(self.buf) - self.start_b, self.beat_b)
        return Place(fin_a=int(fa), debut_b=int(db), bar_a=int(round(4 * self.beat_a)), bar_b=int(round(4 * self.beat_b)),
                     beats_a=np.round(ba).astype(np.int64) if grille else None,
                     beats_b=np.round(bb).astype(np.int64) if grille else None,
                     nettete_a=nettete, nettete_b=nettete, extra=int(extra))


def ordre_dict(transition="C1", bars=None, *, replis=(), params=None, bpm_a=120, bpm_b=120, voix_a=(), voix_b=(),
               grille="nette", entree="E0", manuel=False, **autres):
    """Ordre v2 valide (ADR 0001), en dict JSON, pour une paire de synthèse."""
    from transitions.contrat import BARS_PERMIS
    bars = BARS_PERMIS[transition][0] if bars is None else bars
    bar_a, bar_b = 240 / bpm_a, 240 / bpm_b
    d = {"v": 2, "id": "t-synthese-1", "transition": transition, "choisie": transition, "replis": list(replis),
         "replis_plan": [], "bars": bars, "params": params or {}, "t_wall": time.time() * 1000, "gapless": True,
         "manuel": manuel, "to_uri": "spotify:track:" + "B" * 22 if manuel else None, "ratio": bpm_b / bpm_a,
         "a": {"uri": "spotify:track:" + "A" * 22, "duree_s": 48.0, "sortie_s": None if manuel else 48.0,
               "sortie_mesure": None if manuel else 24, "bar_s": bar_a,
               "beats": [] if manuel else [round(-(bars + 1) * bar_a + k * bar_a / 4, 4) for k in range(4 * (bars + 2) + 1)],
               "grille": grille, "voix": list(voix_a), "jamais_entendu_s": 0.0},
         "b": {"uri": "spotify:track:" + "B" * 22, "duree_s": 48.0, "entree_s": 0.0, "entree_mesure": 0, "entree": entree,
               "cible_s": bars * bar_b, "bar_s": bar_b,
               "beats": [] if manuel else [round(-bar_b + k * bar_b / 4, 4) for k in range(4 * (bars + 3) + 1)],
               "grille": grille, "voix": list(voix_b), "saute_s": 0.0},
         "voix_source": "segments", "raison": "synthèse"}
    d.update(autres)
    return d


def ordre(transition="C1", bars=None, **kw):
    """Ordre v2 validé (contrat.Ordre)."""
    return valider_ordre(ordre_dict(transition, bars, **kw))
