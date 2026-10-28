# ADR 0002 · Détection de voix v1, sans spike en direct

Statut : accepté, 2026-10-28. Tranche le §6 et la question Q3 de [`../specs/transitions-v2.md`](../specs/transitions-v2.md)
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
