"""V3 : voix par mesure sur la mémoire (ADR 0002), numpy seul. Sert uniquement à DÉGRADER une transition au rendu
(passer au repli suivant), jamais à la choisir.

Méthode, par mesure, sur du mono ramené à 11 025 Hz :
1. séparation harmonique/percussive par médianes (comme `outils.percussive`) : on garde le masque harmonique ;
2. dans 300 Hz à 3,4 kHz, on retire la part stationnaire de chaque fréquence (médiane sur ~3 s) : une nappe ou un
   accord tenu disparaissent, une voix (formants qui bougent à chaque syllabe) reste ;
3. deux indices : part de cette énergie harmonique non stationnaire dans l'énergie totale de la mesure, et part de la
   modulation de son enveloppe entre 3 et 8 Hz (débit syllabique) ;
4. score = logistique de leur combinaison, dans [0, 1].
Les constantes sont réglées sur la voix factice de `synthese.py` ; la calibration sur de vrais morceaux est la
tâche 2-direct. Seuils communs (ADR 0002) : vocal ≥ 0,5, sans voix < 0,3, repli au rendu ≥ SEUIL_REPLI_RENDU.
"""
import numpy as np

SEUIL_VOCAL = 0.5
SEUIL_SANS_VOIX = 0.3
SEUIL_REPLI_RENDU = 0.6

SR_IN = 44100
SR_V = 11025
W = 512                  # 46 ms à 11 025 Hz
HOP = 256                # 23 ms, soit ~43 trames par seconde (assez pour une modulation ≤ 20 Hz)
MED_T = 9                # médiane temporelle (harmonique) : ~210 ms
MED_F = 17               # médiane fréquentielle (percussif) : ~370 Hz
STAT_S = 3.0             # fenêtre de la part stationnaire
BANDE = (300.0, 3400.0)
MOD = (3.0, 8.0)         # débit syllabique
# combinaison (réglée sur synthese.voix_factice contre nappe, batterie, basse 808)
A_RHO, C_RHO = 2.5, -2.6      # log10 de la part d'énergie harmonique non stationnaire (voix ≈ −1,5, sans ≈ −5)
MAX_RHO = 2.5                 # plafond du terme d'énergie : une mélodie forte ne suffit pas à faire une voix
A_MOD, C_MOD = 10.0, 0.40     # part de la modulation 3-8 Hz (voix ≈ 0,3 à 0,9 ; mélodie d'une note par temps ≈ 0,1)
SILENCE = 1e-7                # énergie moyenne sous laquelle une mesure est silencieuse (score 0)


def _mono_11k(x):
    x = np.asarray(x, np.float32)
    m = x.mean(axis=1) if x.ndim == 2 else x
    k = SR_IN // SR_V
    n = len(m) // k * k
    # moyenne par blocs de 4 (passe-bas grossier) puis 1 échantillon sur 4
    return m[:n].reshape(-1, k).mean(axis=1)


def _stft_mag(y):
    if len(y) < W:
        y = np.pad(y, (0, W - len(y)))
    win = np.hanning(W).astype(np.float32)
    nfr = 1 + (len(y) - W) // HOP
    idx = np.arange(nfr)[:, None] * HOP + np.arange(W)[None, :]
    return np.abs(np.fft.rfft(y[idx] * win, axis=1)).astype(np.float32)


def _mediane_glissante(a, k, axis):
    sw = np.lib.stride_tricks.sliding_window_view
    h = k // 2
    pad = [(0, 0), (0, 0)]
    pad[axis] = (h, h)
    return np.median(sw(np.pad(a, pad, mode="edge"), k, axis=axis), axis=-1)


def indices(x, bornes):
    """Par mesure : (rho, mod, actif). rho = part d'énergie harmonique non stationnaire 300 Hz-3,4 kHz,
    mod = part de la modulation 3-8 Hz de son enveloppe, actif = mesure ni silencieuse ni trop courte."""
    bornes = np.asarray(bornes, np.int64)
    k = max(0, len(bornes) - 1)
    rhos, mods, actifs = np.zeros(k), np.zeros(k), np.zeros(k, bool)
    if k == 0 or len(x) == 0:
        return rhos, mods, actifs
    y = _mono_11k(x)
    mag = _stft_mag(y)                                   # (trames, fréquences)
    f = np.fft.rfftfreq(W, 1 / SR_V)
    # médianes calculées seulement autour de la bande utile (la médiane fréquentielle déborde de MED_F // 2)
    j0 = max(0, int(np.searchsorted(f, BANDE[0])) - MED_F // 2)
    j1 = min(len(f), int(np.searchsorted(f, BANDE[1], side="right")) + MED_F // 2)
    sub = mag[:, j0:j1]
    harm = _mediane_glissante(sub, MED_T, 0)
    perc = _mediane_glissante(sub, MED_F, 1)
    h = sub * (harm ** 2 / (harm ** 2 + perc ** 2 + 1e-12))
    bande = (f[j0:j1] >= BANDE[0]) & (f[j0:j1] <= BANDE[1])
    hb = h[:, bande] ** 2
    # part stationnaire par fréquence : médiane glissante longue (par blocs pour rester rapide)
    fr = SR_V / HOP
    L = max(1, int(STAT_S * fr))
    stat = np.empty_like(hb)
    for i0 in range(0, len(hb), L // 2 or 1):
        a, b = max(0, i0 - L // 2), min(len(hb), i0 + L)
        stat[i0:i0 + (L // 2 or 1)] = np.median(hb[a:b], axis=0)
    resid = np.maximum(hb - 1.5 * stat, 0)
    env = resid.sum(axis=1)                              # enveloppe de la voix supposée
    total = (mag ** 2).sum(axis=1)
    t_fr = (np.arange(len(mag)) * HOP + W / 2) / SR_V * SR_IN   # centre de trame, en échantillons de x
    for i in range(k):
        sel = (t_fr >= bornes[i]) & (t_fr < bornes[i + 1])
        if sel.sum() < 8:
            continue
        e_tot = total[sel].mean()
        if e_tot / W < SILENCE:
            continue
        rho = env[sel].mean() / (e_tot + 1e-12)
        e = env[sel] - env[sel].mean()
        sp = np.abs(np.fft.rfft(e * np.hanning(len(e)))) ** 2
        fm = np.fft.rfftfreq(len(e), 1 / fr)
        utile = (fm >= 0.5) & (fm <= 20)
        mod = sp[(fm >= MOD[0]) & (fm <= MOD[1])].sum() / (sp[utile].sum() + 1e-12)
        rhos[i], mods[i], actifs[i] = rho, mod, True
    return rhos, mods, actifs


def voix_par_mesure(x: np.ndarray, bornes: np.ndarray) -> np.ndarray:
    """x : (n, CH) float32 ; bornes : k + 1 débuts de mesure (échantillons relatifs à x). Rend k scores dans [0, 1]."""
    rho, mod, actif = indices(x, bornes)
    z = np.minimum(A_RHO * (np.log10(rho + 1e-9) - C_RHO), MAX_RHO) + A_MOD * (mod - C_MOD)
    out = np.where(actif, 1 / (1 + np.exp(-z)), 0.0)
    return np.clip(out, 0, 1).astype(np.float32)
