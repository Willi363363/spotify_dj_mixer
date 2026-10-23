# Catalogue des transitions

Colonne **Chez nous** : ✅ validé à l'oreille · 🧪 maquetté, non jugé ou jugé insuffisant · ⬜ à faire · ❌ hors de portée. E1 / E2 : cf. [`../../architecture.md`](../../architecture.md).

## Transitions de base

| Transition | Exécution | Usage | Chez nous |
|---|---|---|---|
| **Long mélange + échange des basses** | B entre bas, basses coupées, pendant une partie rythmique ; sur 16 à 32 mesures, B monte et A descend ; **l'échange des basses, d'un coup, est le moment de la transition** ([Mixgraph](https://www.mixgraph.io/learn/dj-transition-techniques)) | Même genre, tonalités proches, énergie voisine ; house, techno. À éviter avec des voix qui se chevauchent | 🧪 E2 sur 8 mesures : jugé « juste un fondu ». À refaire sur 16 à 32 mesures, B audible plus tôt, filtre plutôt que volume, ou réservé à la house |
| **Coupe** | B calé sur son premier temps ; sur un temps fort de A, idéalement un début de phrase, on coupe A et on lance B en même temps | Tempos calés mais tonalités incompatibles, changement de genre, de partie du set. **Signature du hip-hop** | ⬜ E1 possible mais avec le trou de Spotify (12 à 400 ms) ; E2 nette, sans trou |
| **Coupe sèche (« power cut »)** | Coupe au milieu d'une phrase, un instant de silence, puis le drop | Effet dramatique | ❌ par choix : le blanc avant le drop a déplu à l'écoute |
| **Balayage de filtre** | A passe dans un passe-bas qui se ferme (aigus, puis médiums, il reste grosse caisse et sub) ; B dans un passe-haut qui s'ouvre, ses graves en dernier | Textures ou énergies différentes, morceaux en conflit de tonalité ; pas sur chaque transition | ⬜ E2 (un filtre par morceau) ; E1 seulement sur tout le son |
| **Sortie en écho** | En fin de phrase, écho sur le dernier temps ou la dernière voix, on coupe A et sa traîne sonne 2 à 4 mesures pendant que B démarre | Fin de warm-up, entrée en peak time, gros écart de tempo ; pas quand la salle doit garder son énergie | ⬜ E2 (écho sur A seul) ; écho validé techniquement, cf. [`../../tests/07-serie-b-effets.md`](../../tests/07-serie-b-effets.md) |
| **Boucle et montée** | Boucle de 4 ou 8 temps de A, filtre qui monte, réverbération et bruit blanc qui croissent ; sur un temps fort, on relâche, on coupe A, B entre | Monter vers un pic, lancer un gros morceau, changer de genre | ✅ **validé** sous forme de roulements qui se resserrent et montent, sans blanc, jusqu'au drop de B |
| **Échange sur un break** | B commence son intro sous le break de A (8 à 16 mesures sans percussions), son beat tombe quand le break de A se résout | Progressive, techno mélodique, trance | ⬜ E2 ; demande de repérer les breaks (sections calmes) |
| **Réverbération qui noie** | A est noyé dans la réverbération jusqu'à n'être plus qu'une traîne | Signature de l'afro house | ⬜ E2 ; réverbération à ajouter |

## Transitions de performance (hip-hop, open format)

Détails d'exécution : [We Are Crossfader](https://wearecrossfader.co.uk/blog/12-high-energy-dj-transitions/).

| Transition | Principe | Chez nous |
|---|---|---|
| **Resserrement de boucle** | Boucle d'un temps sur un mot, divisée par deux, coupée en rythme au fader, puis freinée par à-coups sur 8 temps avant le drop | ✅ proche de la montée validée ; le freinage par à-coups est à ajouter |
| **Frein** | Vinyle qui ralentit jusqu'à l'arrêt, vitesse et hauteur ensemble | 🧪 E2 maquetté, non jugé |
| **Retour arrière (« spinback »)** | A rejoué à l'envers en accélérant, puis B tombe | ⬜ E2 : le son passé est en mémoire |
| **Coupe en rythme** | Le fader de A est ouvert et fermé en rythme pendant que B s'installe | ⬜ E2 (portes de volume calées sur la grille) |
| **Boucle polyrythmique** | Boucle de 3/2 temps sur une voix, écho ping-pong, puis 3/4, puis moitié avant la basse de B | ⬜ E2 ; utile pour les gros écarts de tempo |
| **Montée de tempo (« wide sync »)** | Boucle de 16 temps sur le break de A, tempo monté (ex. 125 → 183 BPM) sur 16 mesures, coupe sur le drop de B | ⬜ E2 avec `rubberband` ; limité par l'avance en mémoire |
| **Jeu sur les paroles, a cappella** | Isoler la voix d'un morceau (séparation de pistes) et la poser sur l'autre | ❌ pour l'instant : demande une séparation de sources (type Demucs), lourde en calcul |

## Ce qu'on en retient pour le moteur

- **Pour la playlist testée** (bouyon, rap, afro) : privilégier **coupe sur le temps, montée par roulements, retour arrière, sortie en écho**, et garder le long mélange pour les morceaux house ou techno à tempo et tonalité proches.
- **Varier** : un DJ n'utilise pas la même transition deux fois de suite ; le moteur doit tourner entre plusieurs.
