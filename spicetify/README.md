# Mode DJ dans Spotify

Deux pièces, installées par `installer.sh` :

- **`dj-auto.js`**, extension toujours active : quand le **mode DJ automatique** est allumé, chaque morceau enchaîne tout seul sur le suivant de la file. Elle tire d'abord un **type** de transition par une chaîne de Markov (B sur son drop, B depuis son début, mélange calé, drop swap ; jamais deux drop swaps de suite, mélange seulement si tempos à 6 % près, tonalités voisines sur la roue de Camelot et avance suffisante), puis un style de ce type selon l'énergie, jamais un des 2 derniers. Sorties et entrées sur des débuts de phrase de 8 mesures (à défaut 4) ; le drop de B est cherché dans sa première moitié. Elle saute pile sur le temps dans la playlist et envoie l'ordre à la maquette. Maquette éteinte : aucun saut, Spotify joue normalement. Elle expose `window.DJ.planTransition` et `DJ.switchAt`, utilisés par les tests (`proto/e2/transition.js`).
- **`dj-mixer/`**, page « Mode DJ » : affiche en direct ce que joue la maquette E2 ([`../proto/e2/`](../proto/e2/README.md)), en 2 colonnes à la hauteur de l'écran.

| Bloc | Ce qu'il montre |
|---|---|
| Dans tes oreilles | Le morceau entendu (avec le retard de la maquette), l'étape de transition en cours, le compte à rebours, l'avance de la maquette (en rouge si basse) et le dernier incident (transition abandonnée ou refusée) |
| Morceaux | **Cercle façon Eternal Jukebox** : chaque temps du morceau entendu, coloré par section ; aiguille verte = position ; temps en jaune = zone de transition. Second cercle (rose) : le morceau qui arrive, point jaune = son point d'entrée (drop) |
| Visualiseur | 16 bandes de fréquences de ce qui sort vraiment des haut-parleurs, calculées par la maquette |
| Transition | Frise A → B avec étapes nommées et curseur, et la raison du choix |
| Mode DJ automatique | Interrupteur, et la prochaine transition prévue |
| Étapes | Les étapes de la transition numérotées, l'étape en cours se remplit |
| À venir | Les 6 prochains morceaux de la file, tempo, tonalité et style prévu pour le premier |
| Dernières transitions | Historique avec une étiquette de couleur par style, **note de 1 à 5 étoiles** (journal `docs/tests/notes-ecoute.jsonl`), et le test manuel (**Tester**, **Rejouer**) |

## Installer / retirer

```bash
spicetify/installer.sh            # lien vers le dépôt, inscription dans Spicetify, redémarre Spotify
spicetify/installer.sh --retirer
```

Après une modification de `dj-mixer/index.js` ou de `dj-auto.js`, relancer **`spicetify apply`** : Spicetify copie les fichiers dans Spotify à ce moment-là, un simple rechargement de la page garde l'ancienne version (cf. [`../docs/pieges.md`](../docs/pieges.md)).

## Fonctionnement

- L'app interroge la maquette sur `http://127.0.0.1:47802` (`/state` 8 fois par seconde, `/run` pour lancer). La maquette n'accepte que deux origines : l'écran local et `https://xpui.app.spotify.com`.
- Lancer une transition passe encore par `run.sh` et le **mode débogage** de Spotify (cf. [`../docs/tests/methode.md`](../docs/tests/methode.md)) ; la maquette retrouve seule l'adresse de Spotify à chaque lancement.
- Sans maquette, l'app l'indique et n'affiche rien d'autre.
- Les cercles utilisent l'analyse de Spotify (`Spicetify.getAudioData`), mise en cache par morceau.
