# Vision

## Ce que l'on veut

Écouter Spotify sur PC comme si un DJ mixait : des enchaînements « comme en boîte », pas un simple fondu. Concrètement :

- **Transitions calées sur le rythme** : on sort d'un morceau sur une fin de phrase et on entre dans le suivant sur le temps, idéalement sur son drop.
- **Effets de club** : coupe des basses relâchée sur le drop, balayage de filtre, écho, boucle qui rallonge un passage.
- **Superposition de deux morceaux** avec calage des tempos et échange des basses, comme sur une vraie table de mixage.
- **Ralentis et accélérations** (effet « vinyle qui freine », ajustement de tempo pendant la transition).

La référence citée est l'**AutoMix d'Apple Music**, qui fait déjà du calage de tempo et de temps (cf. [`recherche/etat-de-l-art.md`](recherche/etat-de-l-art.md)).

## Contraintes

| Contrainte | Conséquence |
|---|---|
| **Compte Spotify gratuit** (pas Premium) | Pas de fondu enchaîné natif, pas de Spotify Mix, pubs dans le flux. La superposition doit venir de nous (étape E2) |
| **Client Spotify desktop sous Linux** (Arch) | Spicetify pour l'extension, PipeWire pour le son |
| **Performance** | Aucun thème Spicetify (jugé trop coûteux). L'extension doit rester légère : du calcul à chaque changement de morceau, rien en continu |
| **Rester dans le client officiel** | Pas de client tiers (librespot) ni de téléchargement de morceaux, cf. [`recherche/etat-de-l-art.md`](recherche/etat-de-l-art.md) |
| **Pas d'accès au son dans Spotify** | Spotify décode le son hors de la partie web : une extension ne peut ni filtrer, ni changer la vitesse. Tout traitement du son passe par PipeWire |

## Ce que l'on ne cherche pas

- Remplacer un logiciel de DJ complet (Mixxx fait ça avec des fichiers locaux).
- Mixer en direct à la main avec des platines : le mode DJ est automatique, avec au plus un bouton « transition maintenant ».

## Critère de réussite

À l'oreille, une transition doit sonner **mixée** : le rythme ne décroche pas, aucun trou ni clic audible, et l'effet tombe sur le temps. Chaque étape se valide en écoutant **et** en mesurant (enregistrement de la sortie son, cf. [`tests/methode.md`](tests/methode.md)).
