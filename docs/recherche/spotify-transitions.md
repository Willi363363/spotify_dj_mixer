# Comment Spotify fait ses transitions

Étude du 2026-10-23. Trois sources : le **code et les textes de traduction du client installé** (Spotify 1.3.4, dossier `/opt/spotify/Apps/xpui/`, lecture seule), un **article de recherche de Spotify** (ISMIR 2017) et un **brevet** de Spotify. Rien n'a été contourné : le client contient en clair les noms des réglages qu'il affiche.

## Trois fonctions différentes

| Fonction | Ce qu'elle fait | Accès |
|---|---|---|
| **Fondu enchaîné** (« Crossfade songs ») | Même durée de superposition pour toutes les transitions | Réglage, Premium sur les versions récentes |
| **Automix** | « Transitions fluides sur certaines playlists » : Spotify fixe lui-même les points d'entrée et de sortie, morceau par morceau ([aide Spotify](https://support.spotify.com/bf-en/article/tracks-transitions), [communauté](https://community.spotify.com/t5/Desktop-Mac/New-quot-Automix-quot-setting-to-quot-allow-smooth-transitions/td-p/4822298)) | Playlists choisies par Spotify |
| **Mix** (« Mixed playlist », bêta, 2025) | Transitions réglables par l'utilisateur dans ses playlists | Premium ; édition sur mobile seulement pour l'instant (« Editing transitions is coming to desktop soon ») |

## Une transition = une recette de 5 ingrédients

Le client décrit chaque transition comme une **recette** (`automix.auto_transition_recipe`, stockée en protobuf dans les attributs de la playlist), calculée **côté serveur** (`getComputedTransitions`) et **jouée par le client**. Une recette combine cinq « ingrédients » (`ingredient.volume`, `eq`, `filter`, `effects`, `looping`), chacun étant un **style** étalé sur un nombre de mesures (`numBars`, `durationBars`), avec un éditeur de courbes (« Curve point », « % through transition »).

Champs relevés dans le code : `startAMs`, `startBMs`, `overlap`, `overlapPadding`, `durationBars`, `isBeatmatched`, `itemSpeedA`, `itemSpeedB` (vitesse de chaque morceau : c'est le calage du tempo), `volumeStyleId`, `eqStyleId`, `filterFxStyleId`, `fxStyleId`, `loopingStyleId`, `presetId`, `beatmatchOptOutDurationMs`, `getMaxTransitionLength`.

### Préréglages (`transition.*`)

Auto · Blend · Fade · Rise · Slam · Surge · Wave · Melt · Dissolve · Afterglow · Custom · No transition.

La composition de chaque préréglage vient du serveur (`getStylesForPresetId`) : **non visible** sans compte Premium.

### Les styles de chaque ingrédient

| Ingrédient | Styles proposés |
|---|---|
| **Volume** | Crossfade · Smooth crossfade · Center cut · Cut in fade out · Fade in cut out · Fade in fade out · Fade in fast out · Fast in slow out · Overlap |
| **EQ** | Bass fade out · Start / Center / End bass swap · Long bass cut · Quick bass cut · Start fade out · 3-band fade |
| **Filtre** | Passe-haut ou passe-bas, en entrée (fi) et / ou en sortie (fo), toutes combinaisons · High-pass filter half out |
| **Effets** | Echo ½ / ¾ / 1 temps, « cut end » ou « out end » · Delay ½ / ¾ cut end · Reverb cut end / out end / out center · Noise out end |
| **Boucles** | Boucle de 1, 2, 4, 8, 16 temps · **Loop halving** (boucle qui se divise par deux) |

Autres indices : « Beatmatching » et « Beatmatch unavailable » / « Beat matching not possible between these tracks » (Spotify renonce au calage quand c'est impossible) ; « Playlist has been mixed and **reordered** for smooth transitions » (il réordonne la playlist) ; notation **Camelot** proposée pour les tonalités.

## Comment il choisit les points de transition (article 2017)

[Bittner et al., « Automatic Playlist Sequencing and Transitions », ISMIR 2017](https://research.atspotify.com/publications/automatic-playlist-sequencing-and-transitions) :

| Étape | Méthode |
|---|---|
| Points candidats | Uniquement des **premiers temps de mesure**, avec priorité aux **drops**, puis aux **frontières de section** |
| Zones permises | Sortie de A dans ses **25 % finaux**, entrée de B dans ses **20 % initiaux** |
| Score de chaque paire de points | Somme pondérée de 6 coûts sur la zone de superposition : écart de **timbre**, écart de **notes (chroma)**, **faible volume** pénalisé, **voix** des deux côtés pénalisées, bonus si la zone finit sur un **drop** ou une **frontière de section** |
| Drops | Trouvés par les **endroits où les auditeurs déplacent la tête de lecture** (pics de saut, données réelles), recalés sur le premier temps précédent, en ignorant les 15 premières secondes |
| Rendu | Temps des deux morceaux alignés ; **chaque temps est étiré** pour que le tempo glisse de celui de A à celui de B au fil de la transition |
| Ordre de la playlist | Plus court chemin passant par tous les morceaux, dans un espace timbre + tonalité + tempo |
| Résultat | 64 % jugées bonnes, 28 % correctes, 8 % mauvaises par des curateurs ; **15 % de « temps non alignés »**, dus aux erreurs de détection des temps ; **aucun** conflit de tonalité relevé |
| Usage réel | A/B test sur 10 % des utilisateurs : +1,4 point de retour quotidien sur les playlists avec transitions ; 95 % des utilisateurs n'activaient pas le fondu |

## Le brevet ([US10101960B2](https://patents.google.com/patent/US10101960B2/en))

- **Point d'entrée** : on découpe le premier sixième du morceau en 6 segments d'une mesure ou plus, on prend celui qui a le **plus d'énergie** ; **point de sortie** : idem sur le dernier sixième.
- Les **premiers temps** des deux segments sont alignés ; superposition d'exemple : 2 temps avant et 2 temps après.
- Puissance **à peu près constante** avant, pendant et après, avec un **limiteur**.
- Tolérance de tempo de **±2,5 BPM** par défaut ; calcul sur le serveur, fondu joué sur l'appareil.

## Ce qu'on en retient

Cf. [`apple-automix.md`](apple-automix.md#ce-quon-en-retient-pour-le-projet) pour la synthèse commune.
