# Recherche : index et synthèse croisée (audit du 2026-10-28)

Audit refait à zéro. Les choix de transition antérieurs sont caducs : la spec qui en découle est
[`../specs/transitions-v2.md`](../specs/transitions-v2.md).

| Fichier | Contenu |
|---|---|
| [`plateformes.md`](plateformes.md) | Spotify Mix et Automix (styles, brevet), Apple AutoMix (iOS 26/27, critiques), Deezer, YouTube, Tidal |
| [`logiciels-et-recherche.md`](logiciels-et-recherche.md) | Automix de Mixxx, VirtualDJ, djay, rekordbox, Serato ; Vande Veire 2018, Kim 2020, DJtransGAN, CUE-DETR ; stems sur CPU |
| [`methodes-dj.md`](methodes-dj.md) | Règles universelles, taxonomie de 20 transitions, spécificités par genre (rap FR, shatta, bouyon…), ce qui est faisable chez nous |

## Ce que font les meilleurs

- **Spotify Mix** : grille de mesures, durées de **2, 4 ou 8 mesures**, sans toucher au tempo ni à la clé. Une transition = un
  *moment d'échange des basses* (milieu, fin, coupe) × un *habillage* (passe-bas, passe-haut, EQ 3 bandes, rien). Il interdit
  les transitions longues quand la grille n'est pas nette.
- **Apple AutoMix** : time-stretch, beatmatch et (iOS 27) boucles d'intro/outro. Il a une **échelle de repli** déclarée : mix,
  puis simple fondu, puis retrait des silences, puis rien. Il refuse d'office les albums dans l'ordre et les paires incompatibles.
- **djay / Serato** : avec stems, ils ne superposent jamais deux voix et sortent une voix en écho. **Mixxx** aligne l'outro de A
  sur l'intro de B, sur la plus courte des deux.
- **Recherche** : Vande Veire distingue trois types (relaxed, rolling, double drop) et met le mix en tampon avant de le jouer,
  comme notre moteur. Kim 2020 (20 765 transitions réelles) trouve des durées par multiples de 8 mesures, 94 % des écarts de
  tempo sous 10 %, et presque jamais de transposition.

## Les règles qui reviennent partout

1. **Une seule basse à la fois.** L'échange se fait d'un geste, sur un premier temps. C'est la règle d'or de tous les styles
   Spotify et l'erreur n° 1 citée par les écoles de DJ.
2. **Entrer et sortir sur des frontières de phrase** (8 mesures, à défaut 4) : début de section recalé sur une mesure.
3. **Jamais deux voix ensemble** au-delà de 4 mesures, et jamais rap contre rap. On laisse finir la phrase chantée.
4. **Durée selon le genre.** Le rap, le dancehall, le shatta et le bouyon se mixent court et sec (coupe, écho, frein,
   1 à 4 mesures). La house et l'amapiano se mixent long et superposé (8 à 32 mesures, échange des basses).
5. **Tempo à ±5 %**, sinon on coupe ou on passe par un écho. **Tonalité** : un mélange long seulement à Camelot ±1.
6. **L'énergie doit tenir la promesse** : pas de montée qui débouche sur un morceau plus calme.
7. **Varier** : la même technique à chaque fois s'entend et trahit l'automate.
8. **Toujours un repli** : grille floue, tempos ou tonalités incompatibles, album → transition plus simple.

## Transition réussie ou ratée, selon les critiques

| Réussie | Ratée |
|---|---|
| « On ne remarque pas qu'il agit » (MacStories) | **Fin amputée** de 30 s à 1 min : reproche n° 1 fait à Apple |
| Point de bascule bien choisi, court, un seul geste | Entrée de B « à un endroit aléatoire » (Spotify Auto), dans un refrain au lieu d'un break (DJ.Studio) |
| Rythme qui ne décroche pas, échange sur le « 1 » | Titre plaqué puis corrigé 1 à 2 s après, bégaiement « disque rayé » |
| Coïncidence révélée (mot, rythme), contraste net | Deux voix superposées, deux basses pleines, montée vers un titre mou |
| Respect de l'œuvre (fin entendue, album intact) | Même effet partout (le « sous l'eau » uniforme d'iOS 26), paires incompatibles forcées |

**Leçon principale.** Les plaintes visent le **placement** (fin coupée, entrée au hasard, voix superposées), presque jamais la
forme des courbes. DJtransGAN le confirme : bien calé, un fondu à règles vaut un modèle appris. Le placement et l'évitement des
voix passent avant le raffinement de l'EQ.

## Ce qui est hors de portée sans stems ni paroles horodatées au mot

Le wordplay, l'acapella, l'échange des voix et le double drop propre sont les transitions « virales ». Elles relèvent d'une v2.
