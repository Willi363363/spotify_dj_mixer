"""V3 : voix par mesure sur la mémoire (ADR 0002), numpy seul. Sert uniquement à DÉGRADER une transition au rendu
(passer au repli suivant), jamais à la choisir.

Méthode, par mesure, sur du mono ramené à 11 025 Hz (une seule STFT, `_analyse`) :
1. séparation harmonique/percussive par médianes (comme `outils.percussive`) : on garde le masque harmonique ;
2. dans 300 Hz à 3,4 kHz, on retire la part stationnaire de chaque fréquence (médiane sur ~3 s) ;
3. huit indices (`NOMS`, `caracteristiques`) : part d'énergie harmonique non stationnaire, modulation 3-8 Hz, flux
   spectral de la bande, centroïde et son écart-type, part de la bande, part harmonique de la bande, part > 3,4 kHz ;
4. score = probabilité de voix : régression logistique sur ces indices, recalibrée (Platt).
Ajusté le 2026-10-29 sur l'audio réel de morceaux de la bibliothèque (vérité terrain : paroles synchronisées), en
validation croisée groupée par morceau : cf. docs/tests/11-voix.md. Les constantes de l'ancienne version (réglées sur la
voix factice de `synthese.py`) donnaient ~50 % de faux positifs sur les mesures sans paroles.
Repli au rendu si score ≥ SEUIL_REPLI_RENDU : quantile 90 % des scores des mesures sans paroles (≤ 10 % de faux
positifs) ; seuils communs (ADR 0002) : vocal ≥ 0,5, sans voix < 0,3 (rapportés seulement).
"""
import numpy as np

SEUIL_VOCAL = 0.5
SEUIL_SANS_VOIX = 0.3
SEUIL_REPLI_RENDU = 0.907

SR_IN = 44100
SR_V = 11025
W = 512                  # 46 ms à 11 025 Hz
HOP = 256                # 23 ms, soit ~43 trames par seconde (assez pour une modulation ≤ 20 Hz)
MED_T = 9                # médiane temporelle (harmonique) : ~210 ms
MED_F = 17               # médiane fréquentielle (percussif) : ~370 Hz
STAT_S = 3.0             # fenêtre de la part stationnaire
BANDE = (300.0, 3400.0)
MOD = (3.0, 8.0)         # débit syllabique
# combinaison (régression logistique recalibrée, ajustée sur l'audio réel, cf. en-tête) : z = F · POIDS + BIAIS
POIDS = (4.3639, -0.74249, -0.60378, -0.00242, 0.00824, -5.43661, -4.83666, 0.57681)
BIAIS = 12.2455
SILENCE = 1e-7                # énergie moyenne sous laquelle une mesure est silencieuse (score 0)


def _mono_11k(x):
    x = np.asarray(x)
    k = SR_IN // SR_V
    n = len(x) // k * k
    # moyenne des canaux et par blocs de 4 (passe-bas grossier), puis 1 échantillon sur 4 ; sommes de tranches
    # plutôt que .mean(axis=…) sur des axes courts (5 fois plus rapide)
    if x.ndim == 2:
        m = x[:n:k].sum(axis=1, dtype=np.float32)
        for j in range(1, k):
            m += x[j:n:k].sum(axis=1, dtype=np.float32)
        return m / np.float32(k * x.shape[1])
    m = x[:n:k].astype(np.float32)
    for j in range(1, k):
        m += x[j:n:k]
    return m / np.float32(k)


def _stft_mag(y):
    if len(y) < W:
        y = np.pad(y, (0, W - len(y)))
    win = np.hanning(W).astype(np.float32)
    nfr = 1 + (len(y) - W) // HOP
    idx = np.arange(nfr)[:, None] * HOP + np.arange(W)[None, :]
    return np.abs(np.fft.rfft(y[idx] * win, axis=1)).astype(np.float32)


def _mediane_glissante(a, k, axis):
    """Médiane glissante (k impair) : np.partition sur une copie contiguë, 2 à 3 fois plus rapide que np.median."""
    sw = np.lib.stride_tricks.sliding_window_view
    h = k // 2
    pad = [(0, 0), (0, 0)]
    pad[axis] = (h, h)
    v = np.ascontiguousarray(sw(np.pad(a, pad, mode="edge"), k, axis=axis))
    v.partition(h, axis=-1)
    return v[..., h]


def _analyse(x, bornes):
    """Calcul commun (une seule STFT, une seule séparation harmonique/percussive) : (rho, mod, actif, F)."""
    bornes = np.asarray(bornes, np.int64)
    k = max(0, len(bornes) - 1)
    rhos, mods, actifs = np.zeros(k), np.zeros(k), np.zeros(k, bool)
    F = np.zeros((k, len(NOMS)))
    if k == 0 or len(x) == 0:
        return rhos, mods, actifs, F
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
    bande_sub = (f[j0:j1] >= BANDE[0]) & (f[j0:j1] <= BANDE[1])
    hb = h[:, bande_sub] ** 2
    # part stationnaire par fréquence : médiane glissante longue (par blocs pour rester rapide)
    fr = SR_V / HOP
    L = max(1, int(STAT_S * fr))
    stat = np.empty_like(hb)
    for i0 in range(0, len(hb), L // 2 or 1):
        a, b = max(0, i0 - L // 2), min(len(hb), i0 + L)
        stat[i0:i0 + (L // 2 or 1)] = np.median(hb[a:b], axis=0)
    resid = np.maximum(hb - 1.5 * stat, 0)
    env = resid.sum(axis=1)                              # enveloppe de la voix supposée
    P = mag ** 2
    total = P.sum(axis=1)
    # indices spectraux de la bande (cf. NOMS)
    bande = (f >= BANDE[0]) & (f <= BANDE[1])
    Pb = P[:, bande]
    eb = Pb.sum(axis=1) + 1e-12
    lb = np.log(Pb + 1e-9)
    flux = np.r_[0.0, np.maximum(np.diff(lb, axis=0), 0).mean(axis=1)]
    cen = (Pb * f[bande]).sum(axis=1) / eb
    haut = P[:, f > BANDE[1]].sum(axis=1)
    hbs = hb.sum(axis=1)
    t_fr = (np.arange(len(mag)) * HOP + W / 2) / SR_V * SR_IN   # centre de trame, en échantillons de x
    lim = np.searchsorted(t_fr, bornes)                  # trames de la mesure i : [lim[i] ; lim[i + 1][
    fen = {}
    for i in range(k):
        sel = slice(lim[i], lim[i + 1])
        n = lim[i + 1] - lim[i]
        if n < 8:
            continue
        e_tot = total[sel].mean()
        if e_tot / W < SILENCE:
            continue
        ev = env[sel]
        rho = ev.mean() / (e_tot + 1e-12)
        if n not in fen:
            fm = np.fft.rfftfreq(n, 1 / fr)
            fen[n] = (np.hanning(n), (fm >= MOD[0]) & (fm <= MOD[1]), (fm >= 0.5) & (fm <= 20))
        han, m_mod, m_utile = fen[n]
        sp = np.abs(np.fft.rfft((ev - ev.mean()) * han)) ** 2
        mod = sp[m_mod].sum() / (sp[m_utile].sum() + 1e-12)
        rhos[i], mods[i], actifs[i] = rho, mod, True
        tt = total[sel].sum() + 1e-12
        F[i] = (max(-6.0, np.log10(rho + 1e-9)), mod, flux[sel].mean(), cen[sel].mean(), cen[sel].std(), eb[sel].sum() / tt,
                hbs[sel].sum() / eb[sel].sum(), np.log10(haut[sel].sum() / tt + 1e-9))
    return rhos, mods, actifs, F


def indices(x, bornes):
    """Par mesure : (rho, mod, actif). rho = part d'énergie harmonique non stationnaire 300 Hz-3,4 kHz,
    mod = part de la modulation 3-8 Hz de son enveloppe, actif = mesure ni silencieuse ni trop courte."""
    rho, mod, actif, _ = _analyse(x, bornes)
    return rho, mod, actif


NOMS = ("lrho", "mod", "flux", "centroide", "centroide_sd", "part_bande", "part_harm", "lhaut")


def caracteristiques(x, bornes):
    """Par mesure : (F, actif), F de forme (k, 8), colonnes NOMS :
    lrho = log10 de la part d'énergie harmonique non stationnaire 300 Hz-3,4 kHz ; mod = part de la modulation 3-8 Hz de
    son enveloppe ; flux = flux spectral positif moyen (log) dans la bande (attaques des syllabes, formants qui bougent) ;
    centroide (Hz) et son écart-type dans la mesure ; part_bande = énergie 300 Hz-3,4 kHz / totale ; part_harm = part
    harmonique de l'énergie de la bande ; lhaut = log10 de la part au-dessus de 3,4 kHz (sifflantes)."""
    _, _, actif, F = _analyse(x, bornes)
    return F, actif


def scores(F, actif):
    """Probabilité de voix à partir des indices (k, 8) de `caracteristiques` ; 0 sur une mesure inactive."""
    z = np.asarray(F, float) @ np.asarray(POIDS) + BIAIS
    return np.where(np.asarray(actif, bool), 1 / (1 + np.exp(-np.clip(z, -30, 30))), 0.0)


def voix_par_mesure(x: np.ndarray, bornes: np.ndarray) -> np.ndarray:
    """x : (n, CH) float32 ; bornes : k + 1 débuts de mesure (échantillons relatifs à x). Rend k scores dans [0, 1] :
    probabilité de voix (régression logistique sur `caracteristiques`, recalibrée), 0 sur une mesure silencieuse."""
    F, actif = caracteristiques(x, bornes)
    return np.clip(scores(F, actif), 0, 1).astype(np.float32)
