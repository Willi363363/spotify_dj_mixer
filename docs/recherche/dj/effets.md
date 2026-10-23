# Effets

Les effets de DJ se calent sur le temps : leurs réglages s'expriment en fractions de temps (1/8, 1/4, 1/2, 1, 2 temps), pas en millisecondes ([Digital DJ Tips](https://www.digitaldjtips.com/beginners-guide-to-dj-effects/), [DJ Class](https://djclass.net/learn/filters-and-fx)).

| Effet | Ce qu'il fait | Réglages types | Usage | Chez nous |
|---|---|---|---|---|
| **Écho (delay)** | Répète le son en se décalant d'une fraction de temps | 1/2 ou 1 temps ; **le retour (feedback) règle le nombre de répétitions** avant extinction | Sortie de morceau : 1 ou 2 temps d'écho pendant qu'on coupe A, l'effet le plus fiable | ✅ mesuré (nœud `delay` avec `Feedback`) ; à appliquer à A seul en E2 |
| **Écho ping-pong** | L'écho alterne gauche / droite | 1 temps | Remplir pendant une boucle | ⬜ deux délais croisés |
| **Réverbération** | Ajoute une salle, une traîne | longueur de traîne, mélange | Montées, transitions, juste avant un drop ; « noyer » A (afro house) | ⬜ nœud `convolver` de PipeWire ou réverbération maison |
| **Filtre passe-haut / passe-bas** | Retire graves ou aigus, balayé à la main | du neutre à la coupure franche | Faire place à l'autre morceau, cacher un conflit | ✅ mesuré ; clics à corriger (cf. [`../../tests/07-serie-b-effets.md`](../../tests/07-serie-b-effets.md)) |
| **Flanger, phaser** | Balayage « avion à réaction », retard très court modulé | vitesse calée sur 4, 8, 16 temps | Montées | ⬜ simple à faire en E2 |
| **Roulement (roll)** | Capture une tranche et la répète en saccade | 1, 1/2, 1/4, 1/8, 1/16 temps | Tension avant un drop | ✅ **validé** dans la montée continue |
| **Montée en hauteur (Helix, Spiral)** | Échos dont la hauteur monte, par paliers ou en glissant | sur 4 à 8 mesures | Tension, « riser » | ✅ présent dans la montée validée (tranches rejouées de plus en plus vite) |
| **Frein (brake)** | Vitesse et hauteur qui tombent ensemble, comme un vinyle arrêté | durée de 1/2 à 2 temps | Arrêt dramatique, style hip-hop | 🧪 maquetté, non jugé |
| **Retour arrière (spinback)** | Le disque tourne à l'envers puis s'arrête | 1 à 2 temps | Changement brutal assumé | ⬜ E2 |
| **Bruit blanc qui monte** | Souffle filtré qui monte en volume et en aigus | 4 à 8 mesures | Montée | ⬜ généré en E2 |

## Règles d'emploi

- **Sur des sons qui ont un début et une fin** (un coup de caisse claire, un mot), pas sur un tapis continu.
- **Pour souligner un moment** que la musique prépare déjà ; utilisés en continu, ils embrouillent le mix ([DJ Class](https://djclass.net/learn/filters-and-fx)).
- **Retirer l'effet au bon moment** : couper l'écho pendant le roulement de batterie de B, par exemple.

## Ce que l'écoute a appris

- La montée qui **ne s'arrête pas** jusqu'au drop plaît ; le **blanc d'un temps** avant le drop a déplu.
- Le schéma « volume de B monte, volume de A descend » s'entend comme un simple fondu, même avec l'échange des basses : sur ce genre de musique, il faut un effet marqué.
