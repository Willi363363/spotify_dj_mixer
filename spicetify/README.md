# Mode DJ dans Spotify

Deux pièces, installées par `installer.sh` :

- **`dj-auto.js`**, extension toujours active : quand le **mode DJ automatique** est allumé, chaque morceau enchaîne tout seul sur le suivant de la file. Elle choisit le style (mélange si les morceaux se calent, sinon un des 6 styles doux selon l'énergie, jamais un des 2 derniers), le point de sortie de A et l'entrée de B, saute pile sur le temps dans la playlist, et envoie l'ordre à la maquette. Maquette éteinte : aucun saut, Spotify joue normalement. Elle expose aussi `window.DJ.planTransition`, utilisé par les tests (`proto/e2/transition.js`).
- **`dj-mixer/`**, page « Mode DJ » : affiche en direct ce que joue la maquette E2 ([`../proto/e2/`](../proto/e2/README.md)), en 2 colonnes à la hauteur de l'écran.

| Bloc | Ce qu'il montre |
|---|---|
| Dans tes oreilles | Le morceau entendu (avec le retard de la maquette), l'étape de transition en cours, le compte à rebours |
| Morceaux | **Cercle façon Eternal Jukebox** : chaque temps du morceau entendu, coloré par section ; aiguille verte = position ; temps en jaune = zone de transition. Second cercle (rose) : le morceau qui arrive, point jaune = son point d'entrée (drop) |
| Visualiseur | 16 bandes de fréquences de ce qui sort vraiment des haut-parleurs, calculées par la maquette |
| Transition | Frise A → B avec étapes nommées et curseur, et la raison du choix |
| Mode DJ automatique | Interrupteur, et la prochaine transition prévue |
| Étapes | Les étapes de la transition numérotées, l'étape en cours se remplit |
| À venir | Les 6 prochains morceaux de la file, tempo, tonalité et style prévu pour le premier |
| Dernières transitions | Historique avec une étiquette de couleur par style, et le test manuel (**Tester**, **Rejouer**) |

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
