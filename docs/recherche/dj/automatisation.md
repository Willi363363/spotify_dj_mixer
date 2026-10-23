# Mixage automatique : l'existant et notre règle de choix

## Ce que font les autres

| Système | Ce qu'il fait | Source |
|---|---|---|
| **Système DJ automatique (2018)** | Suivi des temps et des premiers temps de mesure, découpage en structure, choix des points d'entrée, choix d'un profil de fondu, et playlist qui équilibre nouveauté et continuité. Conçu pour la drum and bass (de mémoire : Vande Veire et De Bie, non vérifié, article inaccessible) | [EURASIP JASMP](https://link.springer.com/article/10.1186/s13636-018-0134-8) |
| **Égaliseur et faders appris (2021)** | Un réseau génératif apprend, sur de vrais mix de DJ, à régler égaliseur et faders. Les auteurs notent que les méthodes antérieures reposaient sur des règles écrites à la main | [arXiv 2110.06525](https://arxiv.org/pdf/2110.06525v1) |
| **Fondu par fréquence (2023)** | Choisit, fréquence par fréquence, quand passer de A à B (exemple sur 64 temps). Constate que la recherche précédente se limitait au fondu de volume | [arXiv 2301.13380](https://arxiv.org/pdf/2301.13380) |
| **Auto DJ de Mixxx** | Transitions aléatoires, un effet actif à la fois, calage double / moitié de tempo | [script autodj](https://github.com/rdircio/autodj) |
| **DJ.Studio** | Enchaînement harmonique et rythmique automatique, courbes de fondu et d'égaliseur modifiables, double / moitié de tempo, ajustement de tempo plafonné à 25-30 % | [DJ.Studio](https://dj.studio/blog/automation-powered-mixing-beatmatching-tempo-sync) |
| **Apple Music AutoMix** | Étirement temporel et calage des temps ; parfois un blanc, parfois une simple superposition | cf. [`../etat-de-l-art.md`](../etat-de-l-art.md) |

Notre constat rejoint celui de la recherche : un fondu de volume, même calé, ne suffit pas à sonner « DJ ».

## Règle de choix proposée pour notre moteur

Hypothèse de travail, à affiner à l'écoute. Entrées : écart de tempo, fiabilité et distance de tonalité, énergie de A et B, présence d'une outro ou d'un break, transition utilisée juste avant.

| Situation | Transition | Pourquoi |
|---|---|---|
| Énergie de B > énergie de A, B a un drop marqué | **Montée par roulements jusqu'au drop** | Validée à l'écoute ; crée la tension et la relâche |
| Tempos proches (< 3 %), tonalités sûres et compatibles, A a une outro longue, genre house / techno | **Long mélange + échange des basses** (16 à 32 mesures) | Ce pour quoi il est fait |
| Tempos proches, tonalité incertaine ou incompatible | **Coupe sur le premier temps d'une phrase** | Insensible à la tonalité ; signature du hip-hop |
| Écart de tempo de 6 à 30 % | **Sortie en écho** de A, B démarre sur son temps fort ; ou **montée de tempo** sur une boucle | Cache l'écart sans étirer |
| Écart proche du double ou de la moitié | Calage double / moitié, puis coupe ou montée | Évite un étirement extrême |
| Énergie de B < énergie de A | **Frein** ou **réverbération qui noie A**, puis B | Fait retomber proprement |
| Même transition que la précédente | Prendre la deuxième meilleure | Varier, comme un DJ |
| Analyse absente ou mesures peu fiables (< 0,4) | **Coupe simple** recalée sur les attaques du son | Le plus robuste |

## Points ouverts

- La **grille de phrases** n'est pas encore calculée : aujourd'hui, la sortie de A est « la première mesure fiable après N secondes ».
- Le **premier temps de B** a été recalé de 274 à 324 ms sur sa grosse caisse lors des essais : le point d'entrée annoncé par Spotify n'est pas fiable, il faut toujours recaler sur le son.
