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

**Budget d'avance** : superposer L secondes consomme L secondes d'avance. Il faut une avance au moins égale à la transition la plus longue, et la regagner ensuite. Dans la maquette, les styles doux prolongent A par du synthétique (boucles, roulements) pendant que B monte, ce qui conserve l'avance et permet d'en regagner ; seul le mélange en consomme (détail : [`proto/e2/README.md`](../proto/e2/README.md#avance-et-regain)).

**Points durs** :
- détecter précisément l'instant du changement de morceau dans le flux (événement de l'extension + repérage du micro-silence) ;
- vider la mémoire sur pause ou morceau suivant demandé à la main ;
- ne pas mixer les **pubs** du compte gratuit ;
- décalage entre l'écran et le son, inhérent à l'avance.

Modèle d'implémentation : le moteur de **Mixxx** (libre), pour les égaliseurs et le calage du tempo.
