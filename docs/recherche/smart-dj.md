# Smart DJ (extension Spicetify)

Dépôt : [guilhepinheiro1701-create/spicetify-automix](https://github.com/guilhepinheiro1701-create/spicetify-automix), licence MIT.

## Ce qu'il fait

Pour chaque paire de morceaux, il décide **quand** transitionner (fin de phrase, frontière de section, calé sur le premier temps), **combien de temps**, **avec quelle technique** (mélange long, court, coupe franche ou rien), et **où entrer** dans le suivant (saut d'intro vide).

- Note de compatibilité pondérée : tempo 30 %, tonalité 22 % (roue de Camelot), énergie 18 %, phrase 15 %, volume 9 %, style 6 %.
- Neuf stratégies (SMOOTH, DJ, FAST, LONG, ENERGY RISE…), réglages Style et Intensité.
- **Superposition réelle** seulement s'il peut piloter le fondu enchaîné de Spotify (en général Premium). Sinon : « Phrase-Timed Fade », une coupe calée sur la phrase avec un creux de volume d'une mesure.
- Son README liste honnêtement ses limites : pas de calage de tempo, pas d'égaliseur ni de filtre, pas de gain par morceau pendant une superposition.

## Relecture du code (2026-10-23)

Relecture ciblée (recherche des motifs à risque, puis lecture complète des fichiers concernés), pas ligne à ligne des ~10 000 lignes.

| Point | Constat |
|---|---|
| Réseau | Uniquement les adresses internes de Spotify via `CosmosAsync` (analyse, `audio-features`). Une source d'analyse externe est **désactivée par défaut** ; activée, elle n'envoie qu'identifiant, titre et artiste, en `credentials: "omit"` |
| Code dynamique | Aucun `eval` ni script chargé à distance. `new Function` seulement dans les scripts de test Node |
| Affichage | `innerHTML` uniquement avec échappement du texte |
| Écritures | Volume, fondu enchaîné, file d'attente (réorganisation désactivée par défaut) |
| Installation | `scripts/install.mjs` copie un seul fichier et lance `spicetify config extensions smart-dj.js` puis `apply` |
| Dépendances | Seulement pour le développement (esbuild, typescript, vitest), toutes du dépôt officiel npm |
| Auteur | 6 commits signés « Claude », du 3 au 5 septembre 2026, 0 étoile : écrit par une IA, jamais relu publiquement |

### Point de vigilance

Pour superposer, il réécrit avant chaque transition un **réglage du compte** :

```js
ConfigAPI.setAccountSetting("audio.crossfade_v2", enabled)
ConfigAPI.setAccountSetting("audio.crossfade.time_v2", ms)
```

Il restaure la valeur d'origine à l'arrêt propre de l'extension. Si Spotify plante, la dernière valeur reste, peut-être sur les autres appareils du compte (supposé). Quatre façons de piloter ce fondu sont essayées, aucune n'est documentée par Spotify.

## Ce qu'on en retient

- **Réutilisable pour le cerveau** : la logique de choix du moment, la note de compatibilité, la détection de structure (intro, montée, drop, outro), le réglage de latence du saut.
- **Inutile pour nous** : son pilotage du fondu natif, puisque le compte est gratuit.
- **Manquant** : le choix du point d'entrée par ressemblance des temps (cf. [`eternal-jukebox.md`](eternal-jukebox.md)) et tout ce qui touche au son (PipeWire).

Décision « partir de Smart DJ ou repartir de zéro » : ouverte, cf. [`../roadmap.md`](../roadmap.md).
