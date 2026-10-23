# spotify_dj_mixer

Un **mode DJ pour le client Spotify desktop** (Linux) : transitions calées sur le rythme, boucles, coupe des basses, filtres, et à terme superposition de deux morceaux avec calage du tempo, comme en boîte de nuit.

Le projet tient sur deux leviers, tous deux vérifiés par des tests :

- **Spicetify** donne accès à l'analyse musicale de Spotify (tempo, temps, mesures, sections, tonalité) et aux commandes du lecteur. C'est le **cerveau** : il décide quand et où agir.
- **PipeWire** reçoit le son déjà décodé de Spotify. C'est la **table de mixage** : filtres, égaliseur, effets, et plus tard des platines en mémoire.

## État

Phase de **cadrage** terminée : toutes les pistes ont été testées, y compris une **maquette de l'étape E2** (son retardé en mémoire, mix avec échange des basses, calage du tempo, boucle, freinage) dans [`proto/e2/`](proto/e2/README.md). Prochaine étape : le prototype E1 (cf. [`docs/roadmap.md`](docs/roadmap.md)).

## Lire la doc

| Tu cherches… | Va voir |
|---|---|
| Ce que le projet veut faire, et ses contraintes | [`docs/vision.md`](docs/vision.md) |
| Ce qui est possible, impossible, et par où | [`docs/faisabilite.md`](docs/faisabilite.md) |
| Comment les briques s'assemblent | [`docs/architecture.md`](docs/architecture.md) |
| Les étapes de construction | [`docs/roadmap.md`](docs/roadmap.md) |
| Les tests réalisés et leurs résultats | [`docs/tests/`](docs/tests/README.md) |
| L'existant (Smart DJ, Eternal Jukebox, apps du marché) | [`docs/recherche/`](docs/recherche/README.md) |
| La machine de référence et sa config | [`docs/environnement.md`](docs/environnement.md) |
| Les pièges rencontrés | [`docs/pieges.md`](docs/pieges.md) |

Index complet : [`docs/README.md`](docs/README.md).

## Scripts

Les scripts qui ont servi aux tests sont dans [`outils/`](outils/README.md), la maquette E2 dans [`proto/e2/`](proto/e2/README.md), réutilisables tels quels.
