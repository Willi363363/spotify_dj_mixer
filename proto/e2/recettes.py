"""Transitions décrites comme des recettes, sur le modèle de Spotify Mix (cf. docs/recherche/spotify-transitions.md).

Une recette combine des ingrédients (volume, égaliseur, filtre, effets, boucle, tempo) étalés sur
quelques mesures. rendu.py la transforme en segment audio à jouer à la place du flux, à partir de la
mémoire de e2.py. Un mélange impossible à caler se replie sur la montée courte.
"""
import os
import subprocess
import tempfile
import wave

import numpy as np

SR, CH = 44100, 2

# Préréglages : ce que l'écran affiche. Tous les styles « doux » font monter B sous la fin de A
# (B lancé 8 mesures de A avant son entrée) et prolongent A par des boucles pendant ce temps, pour ne pas
# consommer l'avance de la maquette (cf. docs/revue/bugs.md, bug 2).
PRESETS = {
    "montee": {"label": "Montée", "ingredients": {
        "filtre": "A perd ses graves, filtre qui s'ouvre sur B", "boucle": "roulements 1 → 1/16 de temps",
        "effets": "hauteur qui monte", "tempo": "B calé sur A pendant qu'il monte"}},
    "montee_courte": {"label": "Montée courte", "ingredients": {
        "boucle": "une mesure de A qui se divise par deux", "effets": "hauteur qui monte", "tempo": "B calé sur A"}},
    "echo_doux": {"label": "Écho", "ingredients": {
        "filtre": "A perd ses graves", "effets": "dernier temps de A en écho ½ temps", "volume": "A s'efface, B monte dessous"}},
    "retour_doux": {"label": "Retour arrière", "ingredients": {
        "filtre": "A perd ses graves", "boucle": "dernière mesure en boucle puis à l'envers", "volume": "B monte dessous"}},
    "frein_doux": {"label": "Frein", "ingredients": {
        "filtre": "A perd ses graves", "effets": "A en boucle puis ralentit jusqu'à l'arrêt", "volume": "B monte dessous"}},
    "filtre": {"label": "Balayage de filtre", "ingredients": {
        "filtre": "A se ferme, il ne reste que ses basses", "volume": "B monte dessous"}},
    "drop_swap": {"label": "Drop swap", "ingredients": {
        "filtre": "A perd ses graves sur 2 mesures, B monte filtré sur 1 mesure", "effets": "dernier temps de A en nappe qui s'éteint",
        "volume": "B tombe sur son drop, sous la nappe, ses basses arrivent sur une mesure"}},
    "refrain": {"label": "Refrain doublé", "ingredients": {
        "boucle": "8 mesures de B rejouées, comme un DJ de rap qui double un refrain (regagne l'avance)"}},
    "secours": {"label": "Secours", "ingredients": {
        "filtre": "A perd ses graves sur son dernier temps, B entre filtré", "volume": "fondu croisé d'un temps"}},
    "melange": {"label": "Superposition", "ingredients": {
        "tempo": "glisse temps par temps de A vers B", "eq": "échange des basses et des aigus sur le drop de B",
        "volume": "vraie fin de A sous les vraies mesures de B avant son drop ; B plein à 70 %, A descend ensuite",
        "effets": "batterie de B d'abord, sa voix sur le dernier quart ; réverbération de A au drop"}},
}
# Anciens noms (essais, run.sh) vers les préréglages actuels
ALIASES = {"build": "montee", "spinback": "retour_doux", "retour": "retour_doux", "mix": "melange",
           "brake": "frein_doux", "frein": "frein_doux", "loop": "montee_courte", "boucle": "montee_courte",
           "echo": "echo_doux", "coupe": "drop_swap"}

# Pour l'écran : étapes (libellé, début, fin, en fraction de la transition) et moment où B devient
# audible (0 = dès le début, B superposé à A ; 1 = à la fin, B tombe net). Valeurs indicatives :
# la part de B dépend de l'avance de B et du tempo.
PHASES = {
    # Avec B lancé 8 mesures avant son drop : partie réelle de A, prolongement où B monte, mesure du drop
    "montee": {"b_from": 0.3, "phases": [("A perd ses graves", 0, 0.3), ("Roulements, B monte dessous", 0.3, 0.92),
                                         ("Drop de B", 0.92, 1)]},
    "montee_courte": {"b_from": 0.1, "phases": [("Boucle d'une mesure", 0, 0.1), ("B monte, la boucle se divise", 0.1, 0.9),
                                                ("Drop de B", 0.9, 1)]},
    "echo_doux": {"b_from": 0.3, "phases": [("A perd ses graves", 0, 0.3), ("Écho de A, B monte", 0.3, 1)]},
    "retour_doux": {"b_from": 0.3, "phases": [("A perd ses graves", 0, 0.3), ("A en boucle, B monte", 0.3, 0.8),
                                              ("A à l'envers", 0.8, 1)]},
    "frein_doux": {"b_from": 0.25, "phases": [("A perd ses graves", 0, 0.25), ("A en boucle qui s'amincit, B monte", 0.25, 0.85),
                                              ("A ralentit", 0.85, 0.92), ("Drop de B", 0.92, 1)]},
    "filtre": {"b_from": 0.3, "phases": [("A se ferme", 0, 0.3), ("Basses de A en boucle, B monte", 0.3, 0.92),
                                         ("Drop de B", 0.92, 1)]},
    "drop_swap": {"b_from": 0.3, "phases": [("A perd ses graves", 0, 0.3), ("B monte sous la boucle de A", 0.3, 0.5),
                                            ("Drop de B sous la nappe de A", 0.5, 1)]},
    "refrain": {"b_from": 0, "phases": [("Refrain rejoué", 0, 1)]},
    "secours": {"b_from": 0.5, "phases": [("A s'efface", 0, 0.5), ("B entre", 0.5, 1)]},
    "melange": {"b_from": 0, "phases": [("Batterie de B sous la fin de A", 0, 0.45), ("A descend, B à plein", 0.45, 0.68),
                                        ("Voix de B", 0.68, 0.88), ("Drop de B, échange", 0.88, 1)]},
}


class Refus(Exception):
    """Le calage est impossible : la recette doit se replier."""


# ─── Outils de traitement ───────────────────────────────────────────────────────────────────────

def ramp(n, a, b):
    return np.linspace(a, b, n, dtype=np.float32)[:, None]


def smooth(n, a, b):
    """Courbe en S (lissée aux deux bouts), plus naturelle qu'une droite pour un volume."""
    t = np.linspace(0, 1, n, dtype=np.float32)
    return (a + (b - a) * (3 * t ** 2 - 2 * t ** 3))[:, None]


def band(x, lo=None, hi=None):
    """Filtre par FFT, sans déphasage : garde [lo, hi] avec des flancs doux (pente d'ordre 4).
    Le signal est complété de zéros avant la FFT : sans ça, la FFT circulaire replie la fin du signal
    sur son début (petits clics aux bords des tranches courtes)."""
    if len(x) == 0:
        return x.astype(np.float32)
    n = 2 * len(x)
    f = np.fft.rfftfreq(n, 1 / SR)[:, None]
    m = np.ones_like(f)
    if lo:
        m = m / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 8)
    if hi:
        m = m / np.sqrt(1 + (f / hi) ** 8)
    return np.fft.irfft(np.fft.rfft(x, n=n, axis=0) * m, n=n, axis=0)[: len(x)].astype(np.float32)


def sweep(x, lo=None, hi=None, w=4096):
    """Filtre qui évolue dans le temps, sans clic : trames de Hann à 50 % de recouvrement, chacune
    filtrée avec sa propre fréquence. `lo` / `hi` sont des fonctions de t ∈ [0, 1] → Hz (ou None)."""
    hop = w // 2
    win = np.hanning(w + 1)[:w].astype(np.float32)[:, None]  # Hann périodique : la somme vaut 1
    pad = np.concatenate([np.zeros((hop, CH), np.float32), x, np.zeros((w, CH), np.float32)])
    out = np.zeros_like(pad)
    for s in range(0, len(pad) - w, hop):
        t = min(1.0, max(0.0, (s - hop + w / 2) / max(1, len(x))))
        out[s:s + w] += band(pad[s:s + w] * win, lo and lo(t), hi and hi(t))
    return out[hop:hop + len(x)]


def edges(x, ms=3):
    """Fondus de quelques ms aux deux bouts d'une tranche, pour qu'un roulement ne claque pas.
    À appliquer après les filtres, pour que le filtre ne réintroduise pas de bord franc."""
    n = min(int(ms / 1000 * SR), len(x) // 2)
    x = x.copy()
    if n:
        x[:n] *= ramp(n, 0, 1)
        x[-n:] *= ramp(n, 1, 0)
    return x


def pitched(src, r, n):
    """Joue `n` échantillons de `src` r fois plus vite (plus aigu), sans reboucler au début de la
    tranche (un rebouclage claque) : `src` doit contenir au moins n·r échantillons."""
    pos = np.minimum(np.arange(n) * r, len(src) - 1)
    return np.stack([np.interp(pos, np.arange(len(src)), src[:, c]) for c in range(CH)], axis=1).astype(np.float32)


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


def _rubberband(x, args):
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.wav"), os.path.join(d, "out.wav")
        with wave.open(src, "wb") as w:
            w.setnchannels(CH); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
        subprocess.run(["rubberband", "-q", *[a.replace("{dir}", d) for a in args], src, dst], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(dst) as w:
            return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, CH).astype(np.float32) / 32767


def stretch_map(x, src_marks, dst_marks):
    """Étire x pour que chaque repère source tombe sur son repère cible (un repère par temps)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "map.txt")
        with open(path, "w") as f:
            for s, t in zip(src_marks, dst_marks):
                f.write(f"{int(s)} {int(t)}\n")
        y = _rubberband(x, ["-M", path, "-D", f"{dst_marks[-1] / SR:.6f}"])
    y = y[: int(dst_marks[-1])]
    return np.concatenate([y, np.zeros((int(dst_marks[-1]) - len(y), CH), np.float32)])


def kick_env(x):
    """Enveloppe des attaques de grosse caisse : énergie 40-150 Hz par pas de 5 ms, montées seules."""
    lo = band(x.mean(axis=1, keepdims=True), lo=40, hi=150)[:, 0]
    h = int(0.005 * SR)
    e = np.sqrt((lo[: len(lo) // h * h].reshape(-1, h) ** 2).mean(axis=1))
    d = np.maximum(0, np.diff(e, prepend=e[0]))
    return (d - d.mean()) / (d.std() + 1e-9)


def kick_agreement(a, b):
    """Accord des grosses caisses de deux signaux de même longueur : 1 = identiques, ≈ 0 = sans rapport.
    Enveloppes lissées sur 15 ms et meilleur décalage à ±20 ms : un étirement décale le son de quelques
    ms, et une attaque d'un pas de 5 ms à côté ne doit pas compter comme un temps raté."""
    k = np.array([0.25, 0.5, 1.0, 0.5, 0.25])
    ea, eb = (np.convolve(kick_env(x), k, mode="same") for x in (a, b))
    n = min(len(ea), len(eb)) - 8
    best = max(float(np.dot(ea[4:4 + n], eb[4 + s:4 + s + n])) for s in range(-4, 5))
    return best / float(np.dot(ea[4:4 + n], ea[4:4 + n]) + 1e-9) ** 0.5 / float(np.dot(eb[4:4 + n], eb[4:4 + n]) + 1e-9) ** 0.5
