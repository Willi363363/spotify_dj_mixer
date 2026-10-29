# ADR 0002 · Détection de voix v1, sans spike en direct

Statut : accepté, 2026-10-28 ; **amendé le 2026-10-29** après la tâche 2-direct (calibrage sur de vrais morceaux,
[`../tests/11-voix.md`](../tests/11-voix.md)) : V1 allumé par défaut, V2 et V3 recalibrés, cf. « Amendement » en fin de
document. Tranche le §6 et la question Q3 de [`../specs/transitions-v2.md`](../specs/transitions-v2.md)
(tâche 4), sans attendre les spikes 2 et 3.

## Contexte

Le plan a besoin de la voix **par mesure** sur les 16 mesures avant la sortie de A et les 16 après l'entrée de B, **avant** le
saut (H3 : le son de B n'existe qu'après). Spotify n'est pas lancé pendant ce pipeline : on ne peut ni vérifier l'accès aux
paroles synchronisées sur un compte gratuit, ni mesurer précision et rappel sur la bibliothèque. Tout doit se tester hors
ligne.

## Options

| | Plan (avant saut) | Rendu (après saut) | Testable hors ligne | Risque |
|---|---|---|---|---|
| a. Attendre le spike | V1 ou V2 selon résultat | V3 | non | bloque les tâches 10, 11, 12 |
| b. V2 seul | segments | rien | oui | rappel faible en rap, aucune vérification |
| c. **V2 + V3, V1 en option** | paroles si drapeau et dispo, sinon segments | V3 sur la mémoire, pour dégrader | oui | V2 et V3 non calibrés au départ |
| d. Modèle pré-entraîné (V4) | — | VAD | non (dépendance, licence) | entraîné sur la parole |

## Décision

Option c.

1. **Contrat unique** : une voix est une liste de scores par mesure dans [0 ; 1] et une `source`
   (`paroles` | `segments` | `aucune`). Seuils communs : **vocale** si ≥ 0,5 ; **sans voix** si < 0,3 (prudent : une règle
   qui exige l'absence de voix, C4, C6, C7, profil « instrumental », exige < 0,3). Entre les deux : ni l'un ni l'autre.
2. **Au plan, dans l'extension** (`spicetify/dj-voix.js`, data-ml-engineer) :
   - **V2 (défaut)** : heuristique sur les `segments` de l'analyse, normalisée **par morceau** (z-scores du timbre et de la
     chroma sur tout le morceau : le timbre de Spotify est relatif). La formule et ses poids sont au data-ml-engineer ; ils
     se règlent d'abord sur des analyses factices, puis en direct (tâche 2-direct).
   - **V1 (option)** : paroles synchronisées, **seulement** si `Spicetify.LocalStorage.get('dj-mixer:paroles') === '1'`
     (éteint par défaut). Requête unique par morceau, en cache, délai maximal 3 s, via
     `Spicetify.CosmosAsync.get('https://spclient.wg.spotify.com/color-lyrics/v2/track/<id>?format=json&market=from_token')`.
     Utilisable seulement si `lyrics.syncType === 'LINE_SYNCED'`. Une ligne couvre de son `startTimeMs` au début de la
     suivante, bornée à 8 s ; une ligne vide ou « ♪ » est instrumentale. Score d'une mesure = part de la mesure couverte.
     Tout échec (404, non synchronisé, délai, format inconnu) → V2, sans erreur visible.
   - **Aucune** (pas de segments) : toutes les mesures à 1 (pire cas : vocal). Seules les règles qui tolèrent la voix
     restent éligibles.
3. **Au rendu, dans le moteur** (`proto/e2/transitions/voix.py`, V3, data-ml-engineer) : numpy seul. Par mesure : part de
   l'énergie **harmonique** (séparation harmonique/percussive par médianes, cf. `_percussive`) dans 300 Hz à 3,4 kHz, et
   modulation syllabique 3 à 8 Hz de son enveloppe. Sur du mono rééchantillonné à 11 025 Hz. Budget : ≤ 0,3 s pour 32 mesures.
   Il sert uniquement à **dégrader** (passer au repli suivant), jamais à choisir :
   - C4 : mesure bouclée ≥ 0,6 → repli ;
   - C6 : une des 4 premières mesures de B ≥ 0,6 → repli ;
   - C5, C7, C8 : nombre de mesures où A et B sont tous deux ≥ 0,6 pendant le recouvrement > 2 → repli (O4) ;
   - C1, C2, C3 : pas de repli (l'échelle n'offre rien de mieux), la valeur est seulement rapportée.
   Seuil de repli à 0,6 (et non 0,5) tant que V3 n'est pas calibré : on préfère laisser passer une voix que replier à tort,
   la variété (O7) en dépend. `voix_mesures` du rapport = nombre de mesures de voix superposées mesuré par V3.
4. **Tests hors ligne** :
   - V3 : signaux de synthèse (`proto/e2/synthese.py`, option `voix=[(t0, t1), …]`) : une « voix » = source harmonique
     (F0 120 à 250 Hz avec vibrato), filtrée par 2 formants qui changent toutes les 150 à 250 ms, modulée en amplitude à
     4 à 6 Hz ; contre nappe stationnaire, batterie, basse 808. Cible : précision et rappel par mesure ≥ 0,9 sur synthèse.
   - V2 et V1 : analyses factices au format `getAudioData` et réponse de paroles factice au format `color-lyrics`
     (`spicetify/test/fixtures/`).
5. **Réponse à Q3** : inconnue à ce jour, et **non bloquante**. La v1 marche sans paroles (V2 au plan, V3 au rendu). La
   vérification en direct (disponibilité sur compte gratuit, couverture sur 50 morceaux, précision des débuts de ligne,
   calibrage de V2 et V3 contre les paroles sur ≥ 20 morceaux) est la tâche **2-direct**, faite plus tard par le développeur.
   Si les paroles sont disponibles et couvrent ≥ 60 % de la bibliothèque, on allume le drapeau par défaut.

## Conséquences

- Les tâches 10, 11 et 12 ne dépendent plus des spikes. La tâche 4 est close par cet ADR.
- Tant que V2 n'est pas calibré, l'extension risque de croire « vocal » des bords instrumentaux : moins de C6 et C7 que la
  spec n'en prévoit. La simulation à blanc (critère 9.1-10) le mesure ; les seuils sont des constantes nommées
  (`SEUIL_VOCAL`, `SEUIL_SANS_VOIX`, `SEUIL_REPLI_RENDU`) pour être réglés après la tâche 2-direct.
- L'endpoint de paroles n'est pas une API publique : il peut changer. Il est derrière un drapeau et n'est jamais nécessaire.

## Amendement du 2026-10-29 (tâche 2-direct)

Mesures : [`../tests/11-voix.md`](../tests/11-voix.md) (77 morceaux, 58 à paroles synchronisées, audio réel de 33,
validation croisée groupée par morceau). Ce qui change par rapport à la décision ci-dessus :

1. **V1 par défaut** : 75 % des morceaux ont des paroles synchronisées (≥ 60 %). Le drapeau `dj-mixer:paroles` n'éteint
   V1 que s'il vaut `0`. Score en **trois zones** : 0 si aucune ligne non vide ne recouvre la mesure (≥ 100 ms) ; sinon
   la part couverte, au moins 0,3 (une mesure recouverte n'est jamais « sans voix »). Requêtes : **cache LocalStorage**
   par morceau (absents réessayés après 14 jours), **file** d'une requête toutes les 3 s, **pause sur 429** (30 s,
   doublée jusqu'à 10 min) pendant laquelle tout part sur V2 sans requête ; attente maximale **8 s** par plan (au lieu
   de 3 s : la file espace A et B), la requête continuant pour remplir le cache. Tout échec → V2, sans erreur visible.
2. **V2** : régression logistique sur 17 caractéristiques des segments (z-scores robustes par morceau et leur moyenne
   sur ±2 mesures), recalibrée en probabilité. « Sans voix » (< 0,3) juste 72 % du temps au lieu de 33 % (rappel 14 %
   au lieu de 41 %), AUC 0,70 → 0,80. Seuils communs inchangés (`SEUIL_VOCAL` 0,5, `SEUIL_SANS_VOIX` 0,3).
3. **V3** : huit indices sur la même STFT (l'énergie harmonique non stationnaire va contre la voix, au contraire de
   l'hypothèse de départ), régression logistique recalibrée. **`SEUIL_REPLI_RENDU` = 0,907**, quantile 90 % des scores
   des mesures sans paroles : 8 à 10 % de faux positifs au lieu de 60 %, précision 0,95, rappel 0,42. Règles de repli
   au rendu inchangées (C4, C6, C5/C7/C8). Cible du §4 sur synthèse abandonnée : la voix factice n'est pas
   représentative ; `test_voix.py` vérifie V3 sur des indices dérivés de vrais morceaux tenus à l'écart.
4. **Effet** (simulation sur les vrais morceaux) : C6 n'est plus rabattue au rendu (0 → 2 % des transitions jouées),
   C4 0,5 → 2,2 %, C4 + C6 + C7 + C8 jouées 1 → 5 %. Le frein restant des superpositions n'est plus la voix mais les
   sorties à 8/16 mesures, la tonalité et la netteté des grilles.
5. **Coupe en fin de ligne** (revalidation en direct, même jour) : avec paroles, C1 et C3 ne sont refusées que si une
   ligne de paroles chevauche la sortie (fin d'une ligne = fin chantée estimée, ≤ 0,45 s par mot) ; la sortie se cale de
   préférence juste après une fin de ligne. C1 éligible quand A a des paroles : 33 → 48 % des paires ; jouée 17 → 22 %.
   Sans paroles, règle inchangée (dernière mesure vocale). Cache : jamais d'erreur transitoire (429, 401, 403, 5xx sous
   toutes leurs formes → pause), éviction LRU, paroles redemandées après 30 jours. Détails : `11-voix.md`.
