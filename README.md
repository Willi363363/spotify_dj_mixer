# spotify_dj_mixer

Un **mode DJ pour le client Spotify desktop** (Linux) : transitions calées sur le rythme, boucles, coupe des basses, filtres, et à terme superposition de deux morceaux avec calage du tempo, comme en boîte de nuit.

Le projet tient sur deux leviers, tous deux vérifiés par des tests :

- **Spicetify** donne accès à l'analyse musicale de Spotify (tempo, temps, mesures, sections, tonalité) et aux commandes du lecteur. C'est le **cerveau** : il décide quand et où agir.
- **PipeWire** reçoit le son déjà décodé de Spotify. C'est la **table de mixage** : filtres, égaliseur, effets, et plus tard des platines en mémoire.

## État

Cadrage terminé, **maquette E2** en place (son retardé en mémoire, calage sur la grille de Spotify) dans [`proto/e2/`](proto/e2/README.md). Le système de transitions a été **refait de zéro** (v2 : catalogue C1-C8, replis R1/R2, choix automatique) : tests hors ligne au vert, **pas encore écouté**. Prochaine étape : le protocole d'écoute (cf. [`docs/roadmap.md`](docs/roadmap.md)).

## Lire la doc

| Tu cherches… | Va voir |
|---|---|
| Ce que le projet veut faire, et ses contraintes | [`docs/vision.md`](docs/vision.md) |
| Ce qui est possible, impossible, et par où | [`docs/faisabilite.md`](docs/faisabilite.md) |
| Comment les briques s'assemblent | [`docs/architecture.md`](docs/architecture.md) |
| Les étapes de construction | [`docs/roadmap.md`](docs/roadmap.md) |
| Les transitions v2 et les décisions | [`docs/specs/`](docs/specs/transitions-v2.md), [`docs/adr/`](docs/adr/README.md) |
| Les tests réalisés et leurs résultats | [`docs/tests/`](docs/tests/README.md) |
| L'existant (plateformes, logiciels de DJ, méthodes des DJ) | [`docs/recherche/`](docs/recherche/README.md) |
| La machine de référence et sa config | [`docs/environnement.md`](docs/environnement.md) |
| Les pièges rencontrés | [`docs/pieges.md`](docs/pieges.md) |

Index complet : [`docs/README.md`](docs/README.md).

## Scripts

Les scripts qui ont servi aux tests sont dans [`outils/`](outils/README.md), la maquette E2 dans [`proto/e2/`](proto/e2/README.md), réutilisables tels quels.

## Dans Spotify

L'app Spicetify **« Mode DJ »** ([`spicetify/`](spicetify/README.md)) affiche dans Spotify le morceau entendu sur un cercle façon Eternal Jukebox, le morceau qui arrive, un visualiseur, la frise de la transition, la file d'attente et la note des transitions (écoute à l'aveugle), avec les boutons pour lancer une transition. Installation : `spicetify/installer.sh`.
