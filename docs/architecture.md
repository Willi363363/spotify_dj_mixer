# Architecture

Trois briques, validées par les tests. L'état actuel est une **maquette** : extension [`spicetify/dj-auto.js`](../spicetify/README.md) (le cerveau), programme Python [`proto/e2/`](../proto/e2/README.md) qui joue le rôle du programme local **et** du module avec avance (E2), relié en HTTP (`/order`, `/state`) plutôt qu'en WebSocket. Le schéma ci-dessous reste la cible.

```
┌──────────────── Spotify desktop ────────────────┐
│  Extension Spicetify  (le cerveau)              │
│  - lit l'analyse : temps, mesures, sections     │
│  - décide quand et où transitionner             │
│  - pilote le lecteur : saut, morceau suivant    │
└──────────┬──────────────────────────────────────┘
           │ WebSocket ws://127.0.0.1:<port>  (0,7 ms)
┌──────────▼──────────────────────────────────────┐
│  Programme local  (le chef d'orchestre)         │
│  - reçoit les ordres horodatés de l'extension   │
│  - règle les filtres PipeWire (pw-cli)          │
└──────────┬──────────────────────────────────────┘
           │ paramètres des filtres
┌──────────▼──────────────────────────────────────┐
│  PipeWire                                       │
│  Spotify ─► filtre DJ ─► haut-parleurs          │
└─────────────────────────────────────────────────┘
```

## 1. Extension Spicetify

- **Analyse** : `Spicetify.getAudioData(uri)`, qui interroge `spclient.wg.spotify.com/audio-attributes/v1/audio-analysis/{id}` avec la session du client. Renvoie `track`, `bars`, `beats`, `sections`, `segments`, `tatums` (cf. [`tests/01-analyse-audio.md`](tests/01-analyse-audio.md)).
- **Lecteur** : `Spicetify.Player.seek`, `playUri`, `next`, `getProgress`, et les événements `songchange`, `onprogress`.
- **Chargement** : Spicetify n'est pas prêt juste après le démarrage de Spotify. L'extension doit attendre que `Spicetify.Player.data.item` et `Spicetify.URI` existent (cf. [`pieges.md`](pieges.md)).
- **Calage d'un saut** : lancer le saut **115 ms** avant l'instant visé, valeur mesurée sur la machine de référence et à rendre réglable (cf. [`tests/03-boucle-par-saut.md`](tests/03-boucle-par-saut.md)).

## 2. Programme local

- Écoute **uniquement sur `127.0.0.1`**. Spotify accepte HTTP et WebSocket vers cette adresse, sans règle de sécurité bloquante (cf. [`tests/05-connexion-locale.md`](tests/05-connexion-locale.md)).
- **WebSocket ouvert au lancement** : le tout premier message a mis 0,56 s, les suivants 0,7 ms.
- Les ordres portent un **horodatage** (instant musical visé) plutôt que « maintenant », pour absorber la gigue.
- Langage à choisir (Node.js suffit en E1 ; Rust ou C seront nécessaires en E2 pour le traitement du son).

## 3. PipeWire

### E1 : le module de filtres fourni

- Un `filter-chain` déclare une sortie son virtuelle, `dj_filter`, que Spotify utilise à la place des haut-parleurs.
- Filtres disponibles d'office : passe-haut, passe-bas, égaliseur (`bq_highpass`, `bq_lowpass`, `bq_peaking`…), délai.
- Réglage en direct : `pw-cli s <id> Props '{ params = [ "hp:Freq" 300 ] }'`.
- Config de test : [`outils/dj-filter.conf`](../outils/dj-filter.conf). Détail et mesures : [`tests/04-filtre-pipewire.md`](tests/04-filtre-pipewire.md).
- **Limite** : un seul flux, donc un effet touche tout ce qui sort de Spotify.

### E2 : le module avec avance

Un module maison qui **retarde le son de quelques secondes** et garde ces secondes en mémoire. Il connaît donc toujours la suite immédiate du morceau.

| Gain | Mécanisme |
|---|---|
| Deux platines | Au passage de A à B, la fin de A et le début de B sont tous deux en mémoire : le module les superpose lui-même |
| Effet sur un seul morceau | A et B sont des signaux séparés : égaliseur propre à chacun, échange des basses |
| Calage du tempo | Étirement temporel sans changer la hauteur (bibliothèque libre Rubber Band). Ralentir accumule de l'avance, accélérer en consomme |
| Boucle sans silence | Rejouer une mesure depuis la mémoire au lieu de faire sauter Spotify |
| Masquer les micro-silences | Le module voit le trou arriver et le comble par un court fondu |

**Budget d'avance** : superposer L secondes consomme L secondes d'avance. Il faut une avance au moins égale à la transition la plus longue, et la regagner ensuite. En v2, la plupart des transitions ne superposent rien (avance intacte) ; C5 à C8 consomment T mesures, C4 en regagne 2, et le ralenti de regain (×1,03) rend le reste entre les transitions (cf. §4 et [ADR 0003](adr/0003-ralenti-et-quota-refrain.md)).

**Points durs** :
- détecter précisément l'instant du changement de morceau dans le flux (événement de l'extension + repérage du micro-silence) ;
- vider la mémoire sur pause ou morceau suivant demandé à la main ;
- ne pas mixer les **pubs** du compte gratuit ;
- décalage entre l'écran et le son, inhérent à l'avance.

Modèle d'implémentation : le moteur de **Mixxx** (libre), pour les égaliseurs et le calage du tempo.

## 4. Transitions v2

Spec : [`specs/transitions-v2.md`](specs/transitions-v2.md). Décisions : [`adr/`](adr/README.md) (0001 à 0006).

### Flux

```
Spotify (analyse getAudioData, paroles si drapeau)
   │
   ▼
dj-voix.js ──► dj-placement.js ──► dj-choix.js ──► dj-auto.js ───────────── window.DJ ──► dj-mixer/index.js
 voix/mesure    phrases, grille,     éligibilité,     tick, saut pile sur        (statut, forcer)   (écran, note
 (V2 / V1)      sorties, E0-E2,      poids, variété,  le temps (switchAt),                          à l'aveugle)
                ΔE, profil           tirage, repli    POST /order v2 ─────┐            ▲
                                     au plan                              │            │ GET /state (rapport)
                                                                          ▼            │ POST /rating {id, note…}
e2.py : find_switch ─► Place (grid_lag / grid_end) ─► catalogue.rendre ─► schedule ─► lecture
                                                       │  essaie transition puis replis :
                                                       │  seches (C1-C3, R2) · boucle (C4, secours)
                                                       │  superposees (C5-C8, R1) via calage + primitives
                                                       │  voix.py (V3) pour dégrader
                                                       └► mesures.rapport ─► derniere_transition (/state, DJ_JOURNAL)
```

- **Le plan est dans l'extension**, sur l'analyse de Spotify seule (H3). Le moteur ne fait que **dégrader** : il descend
  l'échelle de repli quand une condition mesurée sur le son échoue (netteté, calage > 20 ms, voix, avance).
- **Recouvrement** : Spotify saute de sortieA à entreeB ; le moteur superpose les T dernières mesures de A (déjà en mémoire)
  aux T premières de B. Avance consommée = T mesures, regagnée par le ralenti (×1,03, `DJ_SLOW`) et par C4.
- **Calage** : grille de Spotify (`beats` relatifs aux points) puis boucle de correction, extraits de l'ancien mélange
  (`calage.py`).

### Modules

| Couche | Fichier | Responsabilité | Rôle |
|---|---|---|---|
| Extension | `spicetify/dj-voix.js` | voix par mesure (segments, paroles derrière `dj-mixer:paroles`) | data-ml-engineer |
| | `spicetify/dj-placement.js` | §5 de la spec | data-ml-engineer |
| | `spicetify/dj-choix.js` | §7 et §8 au plan, construction de l'ordre v2 | data-ml-engineer |
| | `spicetify/dj-auto.js` | orchestration, `window.DJ` | data-ml-engineer |
| | `spicetify/dj-catalogue.js` | libellés, couleurs, étapes de frise | ui-engineer |
| | `spicetify/dj-mixer/index.js`, `proto/e2/ecran.html` | écrans | ui-engineer |
| Moteur | `proto/e2/e2.py` | mémoire, repérage, ordre, échelle, rapport, HTTP | backend-dev |
| | `proto/e2/transitions/contrat.py` | `Ordre`, `Place`, `Rendu`, `Automation`, validation | backend-dev |
| | `transitions/outils.py`, `calage.py`, `primitives.py` | outils gardés, calage, EQ 3 bandes, courbes, écho | backend-dev |
| | `transitions/seches.py`, `boucle.py`, `superposees.py` | rendus du catalogue | backend-dev |
| | `transitions/catalogue.py` | fiches et échelle au rendu | backend-dev |
| | `transitions/mesures.py` | critères 9.1 sur le son rendu | backend-dev |
| | `transitions/voix.py` | V3 | data-ml-engineer |

Signatures et propriété complète : [ADR 0005](adr/0005-modules-transitions.md). Format de l'ordre et du rapport :
[ADR 0001](adr/0001-contrat-ordre-v2.md).

### Tests hors ligne

- Moteur : `python3 -I proto/e2/test_*.py`, sur `synthese.py` (grille connue, basse, voix factice).
- Extension : `node --test spicetify/test/`, sur des analyses factices au format `getAudioData` et une réponse de paroles
  factice. Les analyses réelles capturées plus tard vont dans `spicetify/test/fixtures/reelles/` (non commité).
- Vérifications en direct (paroles sur compte gratuit, calibrage V2/V3, écoute) : tâche 2-direct et protocole §9.2, par le
  développeur.
