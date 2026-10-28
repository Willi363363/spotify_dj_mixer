# Index de la documentation

Chaque fichier traite un seul sujet et reste sous 200 lignes. Une information vit à un seul endroit, les autres fichiers y renvoient par lien.

## Cadrage

| Fichier | Contenu |
|---|---|
| [`vision.md`](vision.md) | Objectif, ce que l'utilisateur veut obtenir, contraintes |
| [`faisabilite.md`](faisabilite.md) | Catalogue complet : possible, impossible, statut, étape |
| [`architecture.md`](architecture.md) | Les trois briques (extension, programme local, PipeWire) et leurs échanges |
| [`roadmap.md`](roadmap.md) | Étapes E1 et E2, prochaine étape, questions ouvertes |

## Preuves

| Dossier | Contenu |
|---|---|
| [`tests/`](tests/README.md) | Un fichier par test : protocole, mesures, conclusion |
| [`recherche/`](recherche/README.md) | Audit du 2026-10-28 : plateformes, logiciels et recherche, méthodes des DJ |

## Transitions v2

| Dossier | Contenu |
|---|---|
| [`specs/`](specs/transitions-v2.md) | Spec des transitions v2 (catalogue, placement, choix, repli, critères) et [protocole d'écoute](specs/protocole-ecoute.md) |
| [`adr/`](adr/README.md) | Décisions d'architecture : contrat d'ordre, voix, modules, ce qu'on garde de l'ancien code |
| [`ux/`](ux/transitions-v2.md) | Écran : écoute à l'aveugle, note, états |

## Pratique

| Fichier | Contenu |
|---|---|
| [`environnement.md`](environnement.md) | Machine de référence, versions, config Spicetify |
| [`pieges.md`](pieges.md) | Erreurs déjà commises et comment les éviter |

## Conventions de statut

| Mot | Sens |
|---|---|
| **Testé** | Mesuré sur la machine de référence, résultat dans `tests/` |
| **Supposé** | Déduit de la doc, du code d'un tiers ou d'un test voisin, pas mesuré |
| **Établi** | Conséquence directe d'une limite testée |
