"""Vérifie hors ligne la détection de voix au rendu (V3, transitions/voix.py, ADR 0002).

V3 est ajusté sur l'audio réel (2026-10-29, docs/tests/11-voix.md). Contrôles :
1. vrais morceaux tenus à l'écart de l'ajustement (test_voix_reel.json : 8 indices par mesure dérivés de l'audio, vérité
   des paroles synchronisées ; aucun audio) : au seuil de repli, ≤ 15 % de faux positifs sur les mesures sans paroles
   (cible 10 %, marge pour le petit échantillon) et précision ≥ 0,85 ; l'ancienne V3 (seuil 0,6) y avait ≥ 40 % de faux
   positifs ; le portage rend les mêmes scores qu'à l'ajustement ;
2. synthèse instrumentale (grosse caisse, charleston, nappe simple ou riche, basse 808, mélodie de synthé changeante) à
   90, 120 et 150 BPM : aucune mesure au seuil de repli (V3 ne dégrade jamais un passage instrumental) ;
3. silence, bornes vides, bornes hors du signal, mono : pas d'erreur, scores dans [0, 1] ;
4. temps de calcul ≤ 0,3 s pour 32 mesures ;
5. extraction des indices stable (`_mono_11k`, `_analyse`) : 8 indices sur un signal de synthèse déterministe comparés à
   test_voix_indices.json, figés avec le code qui a produit les indices de l'ajustement (vérifié le 2026-10-29 : écart
   nul sur 615 mesures de l'audio réel) ; `_mono_11k` comparé à une moyenne de référence ;
6. bout en bout : un vrai signal de voix fort (audio capté, hors dépôt, ~/spotify_dj_mixer-donnees/voix ou
   $DJ_DONNEES_VOIX) dans l'intro de B fait replier C6 → C5 au rendu (catalogue.rendre, V3 non bouchonnée) ; ignoré si
   les données sont absentes.
La voix factice de synthese.py (source harmonique et formants) n'est pas représentative d'une vraie voix mixée : son
score est seulement affiché.
Usage : python3 -I proto/e2/test_voix.py [--fixture]  (--fixture : réécrit test_voix_indices.json, après un changement
voulu de l'extraction ; il faut alors réajuster V3)
"""
import json
import os
import sys
import time

import numpy as np

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import synthese  # noqa: E402
from transitions import voix  # noqa: E402
from transitions.outils import CH, SR  # noqa: E402

ok = True


def verifie(cond, texte):
    global ok
    print(("  ok  " if cond else "  ✗   ") + texte)
    ok &= bool(cond)


def bornes(bar, n, off=0):
    return (off + np.arange(n + 1) * bar * SR).astype(np.int64)


def auc(s, y):
    o = np.argsort(s)
    r = np.empty(len(s))
    r[o] = np.arange(1, len(s) + 1)
    return (r[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum())


# 1. Vrais morceaux tenus à l'écart
reel = json.load(open(os.path.join(ICI, "test_voix_reel.json")))
F = np.array(reel["indices"], float)
actif = np.array(reel["actif"], bool)
y = np.array(reel["voix"], bool)
s = voix.scores(F, actif)
verifie(np.allclose(s, reel["score_attendu"], atol=2e-3), "portage : mêmes scores qu'à l'ajustement")
a, yy, ss = actif, y[actif], s[actif]
rep = ss >= voix.SEUIL_REPLI_RENDU
fp, prec, rap = rep[~yy].mean(), yy[rep].mean() if rep.any() else 1.0, rep[yy].mean()
lr, md = F[a, 0], F[a, 1]
ancien = 1 / (1 + np.exp(-(np.minimum(2.5 * (lr + 2.6), 2.5) + 10 * (md - 0.40))))
fp0 = (ancien[~yy] >= 0.6).mean()
print(f"{reel['morceaux']} morceaux, {len(yy)} mesures ({(~yy).sum()} sans paroles) : AUC {auc(ss, yy):.2f} ; "
      f"repli (≥ {voix.SEUIL_REPLI_RENDU}) : faux positifs {fp:.2f}, précision {prec:.2f}, rappel {rap:.2f} ; "
      f"ancienne V3 (≥ 0,6) : faux positifs {fp0:.2f}")
verifie(fp <= 0.15, "≤ 15 % de faux positifs au seuil de repli sur les mesures sans paroles")
verifie(prec >= 0.85, "précision ≥ 0,85 au seuil de repli")
verifie(auc(ss, yy) >= 0.8, "AUC ≥ 0,8")
verifie(fp0 >= 0.4, "l'ancienne V3 avait ≥ 40 % de faux positifs (constat de l'essai 13)")

# 2. Synthèse instrumentale : jamais au seuil de repli
pire = 0.0
for bpm in (90, 120, 150):
    for riche in (False, True):
        for seed in (1, 2):
            bar = 240 / bpm
            x = synthese.track(bpm, 16 * bar, 196 if seed == 1 else 233, basse=True, riche=riche, seed=seed)
            pire = max(pire, float(voix.voix_par_mesure(x, bornes(bar, 16)).max()))
bar = 2.0
base = synthese.track(120, 8 * bar, 220, basse=True, riche=True, seed=3)
t = np.arange(int(8 * bar * SR)) / SR
notes = np.random.default_rng(5).choice([262, 294, 330, 392, 440, 523], size=8 * 4)
f = notes[np.minimum((t / 0.5).astype(int), len(notes) - 1)]
mel = 0.15 * sum(np.sin(2 * np.pi * k * np.cumsum(f) / SR) / k for k in range(1, 6))
s_mel = voix.voix_par_mesure(base + np.stack([mel.astype(np.float32)] * CH, axis=1), bornes(bar, 8))
pire = max(pire, float(s_mel.max()))
print(f"synthèse instrumentale (12 morceaux + mélodie de synthé) : score max {pire:.2f}")
verifie(pire < voix.SEUIL_REPLI_RENDU, "aucune mesure instrumentale de synthèse au seuil de repli")
x = synthese.track(120, 16 * bar, 220, basse=True, riche=True, voix=[(4 * bar, 12 * bar)])
sv = voix.voix_par_mesure(x, bornes(bar, 16))
print(f"(info) voix factice de synthese.py : moyenne {sv[4:12].mean():.2f} chantée, {np.r_[sv[:4], sv[12:]].mean():.2f} "
      "sans — non représentative d'une vraie voix mixée")

# 3. Cas limites
verifie(len(voix.voix_par_mesure(base, np.array([0]))) == 0, "une seule borne : aucun score")
verifie(len(voix.voix_par_mesure(np.zeros((0, CH), np.float32), bornes(bar, 4))) == 4, "signal vide : 4 scores")
s = voix.voix_par_mesure(np.zeros((int(8 * bar * SR), CH), np.float32), bornes(bar, 8))
verifie(np.all(s == 0), "silence : 0 partout")
s = voix.voix_par_mesure(base, bornes(bar, 12))   # 4 mesures au-delà du signal
verifie(len(s) == 12 and np.all((s >= 0) & (s <= 1)) and np.all(s[8:] == 0), "bornes hors du signal : 0")
mono = voix.voix_par_mesure(base[:, 0], bornes(bar, 8))
verifie(len(mono) == 8 and np.allclose(mono, voix.voix_par_mesure(np.stack([base[:, 0]] * CH, 1), bornes(bar, 8)),
                                        atol=1e-4), "signal mono accepté (= stéréo identique)")
verifie(len(voix.NOMS) == len(voix.POIDS), "un poids par indice")

# 4. Temps de calcul : 32 mesures à 120 BPM (64 s)
x = synthese.track(120, 32 * bar, 220, basse=True, riche=True, voix=[(10, 40)])
voix.voix_par_mesure(x, bornes(bar, 32))
dts = []
for _ in range(5):   # meilleur de 5 : la machine est partagée, la charge des autres processus ne compte pas
    t = time.perf_counter()
    voix.voix_par_mesure(x, bornes(bar, 32))
    dts.append(time.perf_counter() - t)
dt = min(dts)
print(f"temps pour 32 mesures : {dt:.3f} s (meilleur de 5, médiane {sorted(dts)[2]:.3f} s)")
verifie(dt <= 0.3, "≤ 0,3 s pour 32 mesures")

# 5. Extraction stable : indices d'un signal déterministe (stéréo aux canaux différents), figés dans une fixture
def signal_fixe():
    x = synthese.track(120, 8 * 2.0, 220, basse=True, riche=True, voix=[(4.0, 12.0)], seed=3)
    x[:, 1] *= 0.5
    return x


xf = signal_fixe()
bf = bornes(2.0, 8)
Ff, af = voix.caracteristiques(xf, bf)
sf = voix.voix_par_mesure(xf, bf)
FIX = os.path.join(ICI, "test_voix_indices.json")
if "--fixture" in sys.argv:
    json.dump({"description": "Indices V3 (transitions/voix.py, NOMS) de synthese.track(120, 16 s, 220, basse, riche, "
                              "voix 4-12 s, seed 3), canal droit à 0,5 ; 8 mesures de 2 s. Régénérer : "
                              "python3 -I proto/e2/test_voix.py --fixture",
               "noms": list(voix.NOMS), "indices": [[float(f"{v:.6g}") for v in r] for r in Ff],
               "actif": [int(v) for v in af], "score": [round(float(v), 6) for v in sf]},
              open(FIX, "w"), ensure_ascii=False, separators=(",", ":"))
    print("fixture réécrite :", FIX)
fx = json.load(open(FIX))
ecart = np.abs(Ff - np.array(fx["indices"])) / (np.abs(np.array(fx["indices"])) + 1e-3)
print(f"indices de la fixture : écart relatif max {ecart.max():.1e}, scores {np.abs(sf - fx['score']).max():.1e}")
verifie(list(voix.NOMS) == fx["noms"], "mêmes indices (NOMS) que la fixture")
verifie(ecart.max() < 1e-3 and list(af.astype(int)) == fx["actif"], "extraction des indices inchangée (fixture)")
verifie(np.allclose(sf, fx["score"], atol=1e-3), "scores inchangés sur le signal de la fixture")
k = SR // voix.SR_V
n = len(xf) // k * k
ref = xf[:n].reshape(-1, k, CH).mean(axis=(1, 2))
verifie(np.allclose(voix._mono_11k(xf), ref, atol=1e-6) and np.allclose(voix._mono_11k(xf[:, 0]), xf[:n, 0].reshape(-1, k).mean(1),
                                                                        atol=1e-6), "_mono_11k = moyenne des canaux et par blocs de 4")

# 6. Bout en bout : vrai signal de voix fort dans l'intro de B → C6 replié en C5 au rendu
from transitions import catalogue as CAT  # noqa: E402
from transitions.outils import Refus  # noqa: E402

DONNEES = os.environ.get("DJ_DONNEES_VOIX", os.path.expanduser("~/spotify_dj_mixer-donnees/voix"))


def voix_reelle_forte(dossier, n_max=20):
    """Premier bloc de 4 mesures de l'audio capté où V3 dépasse le seuil de repli partout : (mono, tempo) ou None."""
    import glob
    for fj in sorted(glob.glob(os.path.join(dossier, "audio", "*.json")))[:n_max]:
        try:
            meta = json.load(open(fj))
            tempo = json.load(open(os.path.join(dossier, "analyses", meta["id"] + ".json")))["track"]["tempo"]
            x = np.fromfile(fj[:-5] + ".raw", np.int16).astype(np.float32) / 32768
        except (OSError, ValueError, KeyError):
            continue
        B = int(round(240 / tempo * SR))
        for j in range(len(x) // B - 8):
            if (voix.voix_par_mesure(x[j * B:(j + 4) * B], np.arange(5) * B) >= voix.SEUIL_REPLI_RENDU).all():
                return x[j * B:(j + 8) * B], tempo
    return None


def rendu_c6(m, tempo):
    o = synthese.ordre("C6", replis=["C5", "R1", "R2"], bpm_a=tempo, bpm_b=tempo)
    try:
        r, replis = CAT.rendre(m, o, m.place(), avance=60 * SR)
        return [x["de"] for x in replis] + [r.transition], replis
    except Refus as e:
        return [x["de"] for x in getattr(e, "replis", [])] + ["secours"], getattr(e, "replis", [])


trouve = voix_reelle_forte(DONNEES) if os.path.isdir(os.path.join(DONNEES, "audio")) else None
if trouve is None:
    print(f"(info) bout en bout sur voix réelle ignoré : pas d'audio capté dans {DONNEES}")
else:
    vx, tempo = trouve
    m = synthese.Mem(tempo, bpm_a=tempo, riche=True, mesures_b=24)
    ref_chemin, ref_replis = rendu_c6(m, tempo)          # B de synthèse, instrumental : pas de repli pour la voix
    b = np.zeros_like(m.buf[m.start_b:])
    b[:len(vx)] = np.stack([vx] * CH, axis=1)[:len(b)]
    m.buf[m.start_b:] = b                                # B = vrai signal chanté dès son premier temps
    chemin, replis = rendu_c6(m, tempo)
    print(f"bout en bout, voix réelle (tempo {tempo:.0f}) : {' → '.join(chemin)}"
          + (f" ({replis[0]['raison']})" if replis else "") + f" ; B instrumental : {' → '.join(ref_chemin)}")
    verifie(chemin[:2] == ["C6", "C5"] and replis[0]["ou"] == "rendu" and "intro de B" in replis[0]["raison"],
            "voix réelle forte dans l'intro de B : C6 → C5 au rendu (V3)")
    verifie(not any("voix" in x["raison"] for x in ref_replis), "même paire, B instrumental : aucun repli pour la voix")

print("RÉSULTAT :", "tout passe" if ok else "ÉCHEC")
sys.exit(0 if ok else 1)
