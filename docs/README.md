# Index de la documentation

Chaque fichier traite un seul sujet et reste sous 200 lignes. Une information vit à un seul endroit, les autres fichiers y renvoient par lien.

## Cadrage

| Fichier | Contenu |
|---|---|
| [`vision.md`](vision.md) | Objectif, ce que l'utilisateur veut obtenir, contraintes |
| [`faisabilite.md`](faisabilite.md) | Catalogue complet : possible, impossible, statut, étape |
| [`architecture.md`](architecture.md) | Les trois briques (extension, programme local, PipeWire) et leurs échanges |
| [`roadmap.md`](roadmap.md) | Étapes E1 et E2, décisions, questions ouvertes |
| [`gouts.md`](gouts.md) | Ce que le développeur aime et n'aime pas à l'écoute, mis à jour à chaque essai |

## Preuves

| Dossier | Contenu |
|---|---|
| [`tests/`](tests/README.md) | Un fichier par test : protocole, mesures, conclusion |
| [`recherche/`](recherche/README.md) | Ce qui existe déjà et ce qu'on en retient |

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
