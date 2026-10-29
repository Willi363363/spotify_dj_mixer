# Roadmap

Statuts : ⬜ à faire · 🚧 en cours · ✅ fait · ⏳ en attente d'une décision.

## E0 : cadrage ✅

| Tâche | Statut |
|---|---|
| Vérifier l'accès à l'analyse musicale | ✅ 2026-10-23 |
| Vérifier le contrôle de vitesse | ✅ 2026-10-23 (refusé) |
| Mesurer la boucle par saut, la calibrer | ✅ 2026-10-23 |
| Tester un filtre PipeWire sur Spotify | ✅ 2026-10-23 |
| Tester la connexion extension → programme local | ✅ 2026-10-23 |
| Relire Smart DJ, étudier Eternal Jukebox et l'existant | ✅ 2026-10-23 |
| Tester tous les « supposé » : séries A, B, C (maquette E2) | ✅ 2026-10-23 |
| Recherche sur les transitions (plateformes, logiciels, méthodes des DJ) | ✅ refaite le 2026-10-28, cf. [`recherche/`](recherche/README.md) |
| Observer une vraie pub avec l'API `inStreamApi` | ⏳ au premier passage de pub |
| Documenter le tout | ✅ 2026-10-23 |

## E1 : prototype sans module audio maison ⏳

Objectif : des transitions calées sur le rythme et des effets de filtre pilotés par l'extension, avec les briques déjà testées.

**⏳ Décision attendue** : quelles fonctions entrent dans E1. Candidates, toutes listées dans [`faisabilite.md`](faisabilite.md) :

| Candidate | Brique |
|---|---|
| Transition au moment choisi (fin de phrase, de section) | Extension |
| Entrée du suivant sur son drop | Extension |
| Entrée sur le temps qui ressemble au dernier joué | Extension |
| Boucle sur le drop | Extension |
| Coupe des basses relâchée sur le drop | Extension + programme local + PipeWire |
| Balayage de filtre pendant la transition | idem |
| Écho en sortie de morceau | idem |
| Affichage tempo et tonalité | Extension |
| Bouton « transition maintenant » | Extension |
| Repli quand l'analyse manque, gestion des pubs | Extension |

Choix techniques à trancher au démarrage de E1 :
- **Partir de Smart DJ ou repartir de zéro** pour l'extension.
- **Langage du programme local**.
- **Installation du filtre** : chargé à la demande par le programme local, ou installé dans la config PipeWire.

## E2 : module PipeWire avec avance 🚧

Objectif : superposition de deux morceaux, échange des basses, calage du tempo, boucle sans silence, « vinyle qui freine ». Conception dans [`architecture.md`](architecture.md#e2-le-module-avec-avance).

| Tâche | Statut |
|---|---|
| Maquette Python : son retardé en mémoire, pause, rattrapage d'un changement manuel ([`proto/e2/`](../proto/e2/README.md)) | ✅ |
| Calage des superpositions sur la grille de Spotify, 0 à 10 ms ([test 10](tests/10-calage.md)) | ✅ 2026-10-26 |
| Mode DJ automatique dans Spotify ([`spicetify/`](../spicetify/README.md)) | ✅ |
| **Transitions v2** refaites de zéro : catalogue C1-C8, replis R1/R2, placement, choix, voix ([spec](specs/transitions-v2.md)) | ✅ 2026-10-28, tests hors ligne au vert |
| **Protocole d'écoute** : 16 paires, écoute à l'aveugle, note et étiquettes ([`specs/protocole-ecoute.md`](specs/protocole-ecoute.md)) | ⬜ prochaine étape ; URI des paires à remplir |
| Calibrer la voix (paroles sur compte gratuit, V2/V3 sur ≥ 20 morceaux) | ⬜ tâche 2-direct de la spec |
| Ajuster les poids de choix à la main d'après les notes | ⬜ après le protocole |
| Réécrire le moteur en Rust ou C | ⬜ hors v1 |

## Décisions

Les décisions de transition prises avant le 2026-10-28 (styles « doux », montée par roulements, mélange, drop swap, chaîne de Markov, refrain doublé…) sont **caduques**, comme les avis d'écoute qui les justifiaient : la v2 repart sans préférence enregistrée. Les décisions en vigueur sont :

- la spec [`specs/transitions-v2.md`](specs/transitions-v2.md) (catalogue, placement, choix, repli, critères, objectifs O1-O8) ;
- les ADR [`adr/`](adr/README.md) : contrat d'ordre v2 (0001), voix (0002), ralenti et quota du refrain (0003, provisoire), ancien code retiré (0004), modules (0005), traitement sans dépendance (0006).

Le journal des notes d'écoute (`tests/notes-ecoute.jsonl`) repart vide : `e2.py` le crée à la première note. En v1, les notes ne règlent pas les poids automatiquement.

## Questions ouvertes

Q1 (ralenti de regain), Q2 (entrée sur le refrain) et Q3 (paroles sur compte gratuit) : cf. [§13 de la spec](specs/transitions-v2.md#13-questions-ouvertes). Pubs : observer `inStreamApi` au premier passage.

## Hors périmètre

| Piste | Raison |
|---|---|
| Thème Spicetify | Coût en performance jugé trop élevé |
| Client librespot | Client non officiel, risque de bannissement du compte |
| Son récupéré sur YouTube (méthode Eternal Jukebox) | Contraire aux conditions de YouTube, et on sort de Spotify |
| Spotify Mix, fondu natif | Réservés à Premium |
