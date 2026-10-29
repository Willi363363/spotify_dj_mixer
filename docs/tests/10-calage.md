# 10 · Preuve du calage des superpositions

Test du 2026-10-26. Objectif : prouver, **sur le son produit et avant toute écoute**, que les temps de A et de B tombent ensemble pendant une superposition. Seuil visé : 30 ms (au-delà, deux rythmes s'entendent décalés).

## Mesure

Chaque morceau superposé est confronté à la grille commune de la superposition (les repères où A et B doivent avoir leurs temps) : décalage qui place le mieux ses attaques (flux spectral, toutes fréquences) sur ces repères. Erreur de calage = écart B − A. Vérifiée sur son de synthèse : une erreur volontaire de 120 ms est retrouvée à 1 ms près.

Une première mesure, qui comparait directement les attaques de A et de B, se contredisait en rap (deux morceaux calés ne frappent pas aux mêmes endroits) : abandonnée.

## Résultats (paires rap FR de « All song », tempos à moins de 2 % d'écart)

| Paire | Ancien calage (frappe la plus forte) | Grille de Spotify | Grille + correction |
|---|---|---|---|
| GIMS → Josman | −249 ms (autre mesure) | −5 ms | — |
| Kaaris → Ziak | +200 ms (autre mesure) | non superposé (repli) | — |
| Kerchak → menace Santana | ~±150 ms | −90 ms | **+5 ms** |
| Gazo → Wallace Cleaver | ~±145 ms | +55 ms | **0 ms** (netteté faible, 2,1) |
| Orelsan → Niska | — | −65 ms | **0 ms** |
| PLK → Josman | — | +40 ms | **0 ms** |
| Damso → Zola | — | −10 ms | −10 ms (sous le seuil, non corrigé) |

## Ce qu'on en tire

- **L'ancien calage ratait d'environ un demi-temps** : la grosse caisse la plus forte, en rap, tombe souvent à contretemps.
- Calage sur la **grille de temps de Spotify** (envoyée par l'extension) : 5 à 90 ms.
- Puis **boucle de correction** (mesurer, relire B décalé, remesurer) : **0 à 10 ms** sur les 5 paires.
- Limite : la correction et le contrôle utilisent la même mesure ; une vérification indépendante (enregistrement de la sortie, ou écoute) reste à faire. Sur Gazo → Wallace Cleaver, la netteté après correction est faible.
