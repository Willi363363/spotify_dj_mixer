# 11 · Calibrage de la voix (V1, V2, V3)

Fait le 2026-10-29, seul, sur la machine de [`../environnement.md`](../environnement.md), compte gratuit, mode débogage
([`methode.md`](methode.md)), lecture seule sur le compte. Tâche **2-direct** de l'[ADR 0002](../adr/0002-detection-voix-v1.md),
après les constats de l'essai [13](13-essai-direct-v2.md) : V2 « sans voix » juste 1 fois sur 3 (C7 jamais éligible),
V3 « voix » sur 62 % des mesures sans paroles (C6 refusée 8 fois sur 9).

## Vérité terrain

- **77 morceaux** variés : les 34 URI du [protocole d'écoute](../specs/protocole-ecoute.md) et 43 tirés régulièrement de
  9 playlists du développeur (« RAP FRANCAIS 2026 » 14, Yardland 6, Hardstyle 4, phonk 3, Top 2025 5, Jul 3,
  Uptempo 2, Sokuu 3, Pâtisserie 3). Pour chacun : `getAudioData` et paroles (`color-lyrics`).
- **Paroles synchronisées : 58 / 77 (75 %)** (protocole 25/34, rap FR 10/14, Yardland 6/6, hardstyle 2/4, uptempo 0/2).
  77 requêtes espacées de 3 s : **aucun 429**. Une réponse absente arrive en `{code: 404}` (pas d'exception).
- **Mesure « voix »** : une ligne non vide la recouvre d'au moins 100 ms (ligne : de son début au suivant, bornée à
  8 s, ADR 0002). 55 morceaux exploitables (5 297 mesures), dont 87 % « voix ».
- **Audio réel** pour V3 : 33 morceaux à paroles, 2 fenêtres de 36 s chacun (début du morceau, et une fenêtre de la
  seconde moitié qui mélange mesures avec et sans paroles), soit 66 fenêtres captées sur la sortie virtuelle `dj_in`
  (`parec`, mono 44,1 kHz). Alignement : positions annoncées par Spotify, affinées par corrélation des attaques avec les
  segments de l'analyse (correction de −0,25 à +0,17 s). V3 calculé comme le moteur, par blocs de k = 1, 4 et 8 mesures.
- Données et scripts **hors dépôt** : `~/spotify_dj_mixer-donnees/voix/` (230 Mo, dont l'audio) : `analyses/`,
  `paroles/`, `audio/`, `scripts/` (`collecte.mjs`, `capture.mjs`, `barres.mjs`, `ajuste_v2.py`, `mesures_v3.py`,
  `ajuste_v3.py`, `sim-reelle.mjs`). Dans le dépôt, seulement des caractéristiques numériques dérivées (fixtures).

Toutes les évaluations sont en **validation croisée groupée par morceau** (un morceau entier d'un seul côté), plus des
morceaux tenus à l'écart de tout ajustement, qui servent de fixtures de test.

## V1 : paroles synchronisées, allumées par défaut

Couverture 75 % ≥ 60 % : drapeau allumé par défaut (ADR 0002 mis à jour). `spicetify/dj-voix.js` :

- **Score en trois zones** : 0 si aucune ligne ne recouvre la mesure (« sans voix ») ; sinon la part couverte, au moins
  0,3 : « vocale » dès la moitié couverte, « ni l'un ni l'autre » en dessous. Une mesure recouverte n'est donc jamais
  « sans voix » (elle bloque C4, C6, C7) mais une fin de phrase qui déborde peu ne rend pas la sortie « vocale »
  (C1 garde 27 % d'éligibilité au lieu de 23 % avec un score 0/1).
- **Cache LocalStorage** `dj-mixer:paroles-cache` (≈ 750 octets par morceau, 600 morceaux au plus, absents réessayés
  après 14 jours) : survit au redémarrage de Spotify.
- **File** : une requête toutes les 3 s ; **429 → pause** de 30 s doublée jusqu'à 10 min, pendant laquelle tout part
  sur V2 sans requête ; attente maximale 8 s par plan (au-delà : V2, mais la requête continue et remplit le cache).
- Éteindre : `DJ.setParoles(false)` (`dj-mixer:paroles` = `0`). Compteurs : `DJ.paroles()`.
- **Vérifié dans Spotify** : drapeau absent → V1 actif ; 4 demandes simultanées servies à 0,1 / 3,2 / 6,2 / 8,0 s, la
  4ᵉ hors délai (V2) puis servie par le cache ; plan réel avec `voix_source: paroles`.

## V2 : segments Spotify (repli de V1)

Ancienne formule (4 z-scores à poids fixés à la main) remplacée par une **régression logistique** sur 17 caractéristiques
par mesure (timbre 0-11, pic de chroma, densité de segments, sonie, attaque, confiance ; z-scores robustes par morceau,
plus leur moyenne sur ±2 mesures), **recalibrée en probabilité** (Platt). Ce qui sépare le mieux, sur les vrais
morceaux : les mesures sans paroles sont moins fortes (timbre 0, sonie), moins brillantes (timbre 1), ont timbre 3 plus
haut, une chroma plus pointue et moins de segments ; l'hypothèse « chroma pointue = voix » de l'ancienne V2 était inversée.

| V2, 55 morceaux, 5 297 mesures | AUC | « sans voix » (< 0,3) précision | rappel | « vocale » (≥ 0,5) précision | rappel |
|---|---|---|---|---|---|
| Avant | 0,70 | **0,33** | 0,41 | 0,92 | 0,73 |
| Après (validation croisée, 50 morceaux) | **0,80** | **0,72** | 0,14 | 0,90 | **0,98** |
| Après, 5 morceaux tenus à l'écart (429 mesures) | 0,98 | 0,77 | 0,57 | 0,98 | 0,98 |

Règle d'usage : seuils communs inchangés (vocale ≥ 0,5, sans voix < 0,3) ; comme le score est une probabilité,
« sans voix » veut maintenant dire « au plus 30 % de chances de voix ». V2 dit rarement « sans voix » (rappel 14 %) mais
s'y trompe 2 à 3 fois moins : prudent, comme l'ADR le demande, et il ne sert plus que pour ~25 % des morceaux.

## V3 : voix au rendu (moteur)

`proto/e2/transitions/voix.py` : l'énergie harmonique non stationnaire (`rho`) que l'ancienne V3 comptait **pour** la
voix va en réalité **contre** (AUC seule 0,27 : nappes et mélodies). Nouvelle V3 : **8 indices** sur la même STFT
(`NOMS` : rho, modulation 3-8 Hz, flux spectral de la bande, centroïde et son écart-type, part 300 Hz-3,4 kHz, part
harmonique de la bande, part > 3,4 kHz), régression logistique recalibrée. **Seuil de repli 0,907** = quantile 90 % des
scores des mesures sans paroles (≤ 10 % de faux positifs). Temps : 0,17 s pour 32 mesures (médianes par
`np.partition`, mixage mono par tranches ; l'ancienne V3 prenait 0,38 s sur la même machine chargée).

| V3 (28 morceaux, 2 914 mesures, k = 1/4/8) | AUC | précision | rappel | faux positifs (mesures sans paroles) |
|---|---|---|---|---|
| Avant, seuil 0,6 | 0,60 à 0,62 | 0,80 à 0,82 | 0,75 à 0,77 | **0,60 à 0,62** |
| Après, seuil 0,907 (validation croisée) | 0,83 à 0,85 | 0,93 à 0,95 | 0,42 | **0,08 à 0,10** |
| 5 morceaux tenus à l'écart (avant → après) | 0,86 à 0,89 | 0,79 → 1,00 | 0,75 → 0,12 à 0,15 | 0,58 → **0,00** |

V3 ne dégrade plus que sur un score élevé : elle laisse passer une partie des voix (rappel 42 %), mais ne refuse plus à
tort une intro instrumentale. La voix factice de `synthese.py` n'est plus détectée (score ≈ 0) : elle n'est pas
représentative d'une vraie voix mixée ; les tests d'échelle (`test_ordre.py`, `test_criteres.py`) bouchonnent V3.

## Effet sur les transitions (simulation à blanc sur les vrais morceaux)

`scripts/sim-reelle.mjs` : la simulation de `spicetify/test/simulation.test.mjs` sur les 72 morceaux collectés qui ont
une analyse complète (55 avec paroles), 10 graines × 2 ordres (hasard, tempo proche) × 30 transitions = 600. Le rendu
modélise V3 par ses taux mesurés (vrais et faux positifs par k) sur la vérité des paroles, avec les règles de
`transitions/catalogue.py`. Avant = ancienne V2 sans paroles + ancienne V3 ; après = V1 + V2 + V3 recalibrées.

| Jouées (après repli V3) | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | R1 | R2 | replis V3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Avant | 20,0 % | 24,8 % | 5,0 % | 0,5 % | 8,0 % | **0** | 0 | 0,5 % | 25,5 % | 15,7 % | 6,2 % |
| Après | 15,3 % | 26,2 % | 4,3 % | **2,2 %** | 5,3 % | **2,0 %** | 0 | 0,8 % | 26,3 % | 17,5 % | 1,5 % |

- C6 était **toujours** rabattue en C5 au rendu (comme en direct : 8 sur 9) : elle est maintenant jouée ; C4 ×4, C8
  ×1,6 ; C4 + C6 + C7 + C8 jouées : **1,0 % → 5,0 %**. Le total des superpositions jouées (C5-C8) reste ~8 % : avant,
  la plupart des « C5 » étaient des C6 rabattues.
- Au plan, la voix n'est plus le premier frein des superpositions sur cette bibliothèque : sur les 1 120 paires à tempos
  ≤ 6 %, C7 est refusée d'abord faute de sortie de A à 8/16 mesures (406), de tonalité connue (332) ou de Camelot
  compatible (195), C5 et C6 par la netteté des grilles et le Camelot. V1 dit (à raison) qu'une fin de A est chantée plus
  souvent que l'ancienne V2 : C1 et C3 baissent un peu, R2 monte.
- Bibliothèque factice (`node --test spicetify/test/`, paroles factices pour 90 % du rap, 20 % du shatta/bouyon) :
  C1 23 %, C2 28 %, C3 6 %, C4 3 %, C5 11 %, C6 12 %, C8 2 %, R1 11 %, R2 4 %.

## Coupe sur fin de ligne (revalidation en direct du 2026-10-29)

Constat en direct ([13](13-essai-direct-v2.md), « Revalidation ») : C1 n'était jamais jouée, rabattue en R2 au plan
(« voix de A sur la dernière mesure ») : en rap, A chante presque toujours jusqu'au bout, et la coupe de DJ se fait en
fin de ligne. Nouvelle règle (`dj-placement.js`, `dj-choix.js`, `dj-voix.js : coupeLigne, finDeLigne`) :

- **Avec paroles**, C1 et C3 ne sont refusées que si une ligne **chevauche** la sortie t (elle a commencé avant
  t − 0,1 s et se chante encore après t + 0,1 s : un mot serait coupé). Fin d'une ligne = sa **fin chantée estimée**,
  au plus 0,45 s par mot après son début (au-delà, V3 sur l'audio réel ne voit plus de voix, cf. « Limites »), sinon le
  début de la suivante. Raison du refus : « ligne de paroles de A coupée à la sortie ».
- Sortie : si la préférée coupe une ligne, la frontière de phrase (4 ou 8 mesures) suivante qui ne coupe pas, jusqu'à
  8 mesures plus loin, de préférence juste après une fin de ligne (dans la dernière mesure).
- **Sans paroles** (V2) : règle inchangée. C2 n'a pas de refus pour la voix ; C4 (« voix sur la mesure bouclée ») a une
  autre cause : la voix est vraiment dans la mesure bouclée (essayé avec la fin chantée : 8,6 % → 8,6 % de refus).

| Sur les 72 vrais morceaux (`scripts/sim-reelle.mjs`, 600 transitions) | Avant | Après |
|---|---|---|
| C1 éligible, A avec paroles (3 905 paires) | 32,8 % | **48,2 %** |
| C1 refusée pour la voix, A avec paroles | 29,5 % | 14,1 % |
| C1 jouée, A avec paroles | 17,4 % | **22,2 %** |
| C1 jouée, toutes transitions | 15,3 % | 18,3 % |
| C3 / C4 / R2 jouées | 4,3 / 2,2 / 17,5 % | 6,5 / 2,7 / 14,2 % |

Sans l'estimation de la fin chantée (fin = début de la ligne suivante), C1 éligible ne monte qu'à 39,8 %. Sorties :
`sim-c1-avant.json`, `sim-c1-apres.json` (hors dépôt).

## Correctifs de la QA (2026-10-29)

- **Erreurs transitoires** : le statut HTTP est lu sous toutes ses formes (`{code}`, `{status}`, `{error: {status}}`,
  message « … 429 … ») ; seuls un succès et une absence avérée (404, réponse de paroles non synchronisée) vont en cache.
  429, 401, 403, 5xx → pause de la file (30 s doublée jusqu'à 10 min), jamais en cache ; réseau, délai, format inconnu :
  ni cache ni pause.
- **Cache** : entrée illisible supprimée et redemandée ; éviction de la **moins récemment utilisée** ; paroles présentes
  redemandées après **30 jours** (l'ancienne version reste servie si la nouvelle requête échoue).
- **Plan** (`dj-auto.js`) : l'avance du moteur et la sortie au plus tôt (position + 15 s) sont lues **après** l'attente
  des paroles (jusqu'à 8 s) ; si la sortie visée est déjà dépassée, repli en R2 (fin de A encore devant) ou pas de plan.
- **V3** : indices d'un signal de synthèse déterministe figés (`proto/e2/test_voix_indices.json`) ; l'extraction actuelle
  redonne exactement les indices de l'ajustement sur l'audio réel (615 mesures, écart nul). Bout en bout : un vrai
  signal chanté (audio capté, hors dépôt) dans l'intro de B fait replier C6 → C5 au rendu ; B instrumental : C6 jouée.

## Limites

- Vérité = paroles : les ad-libs, chœurs et voix découpées (EDM) non transcrits comptent « sans voix » ; la fin d'une
  ligne est estimée (début de la suivante, ≤ 8 s). Les queues de ligne (au-delà de ~0,45 s par mot) ont des scores V3
  proches des mesures sans paroles (5 % au seuil, contre 36 % au cœur des lignes) : bruit connu de la vérité.
- 77 morceaux, 33 avec audio : peu de morceaux sans paroles du tout (techno, house) ; à revalider sur une soirée réelle.
- L'adresse `color-lyrics` n'est pas une API publique ; un 429 durable fait tout retomber sur V2 (prudente).
- La simulation suppose les erreurs de V3 indépendantes d'une mesure à l'autre.

## Tests

- `node --test spicetify/test/` : 64 / 64 (coupe sur fin de ligne, erreurs transitoires, cache LRU et expiration,
  plan relu après l'attente des paroles ; V2 sur 5 vrais morceaux tenus à l'écart, `fixtures/voix-reelle.js` ; V1 trois
  zones ; cache, file, 429, délai avec un faux Spicetify ; simulation avec paroles factices).
- `for t in proto/e2/test_*.py; do python3 -I $t; done` : tout passe (`test_voix.py` : V3 sur 5 vrais morceaux tenus à
  l'écart, `test_voix_reel.json`, aucun faux positif de synthèse instrumentale au seuil, temps, indices figés
  `test_voix_indices.json`, bout en bout C6 → C5 sur voix réelle si `~/spotify_dj_mixer-donnees/voix` est là).
- Rejouer le calibrage : `scripts/barres.mjs` puis `ajuste_v2.py barres.json --poids tenus-v2.json` et
  `porte_v2.py` ; `mesures_v3.py`, `ajuste_v3.py v3.json`, `porte_v3.py`, `fixture_v3.py` (usages en tête de chaque script).
