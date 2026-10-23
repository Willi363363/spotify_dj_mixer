# Eternal Jukebox

Dépôt maintenu : [EternalBox/EternalJukebox](https://github.com/EternalBox/EternalJukebox) (826 étoiles), reprise de l'Infinite Jukebox de Paul Lamere ([Music Machinery](https://musicmachinery.com/tag/echonest)).

## Comment ça marche

| Brique | Mécanisme |
|---|---|
| **Le son** | Le serveur télécharge le morceau sur **YouTube** avec `yt-dlp` et `ffmpeg` (`src/main/kotlin/…/YoutubeAudioSource.kt`) |
| **L'analyse** | Temps, mesures, timbre et notes de chaque passage viennent de **Spotify** : la même analyse qu'au [test 01](../tests/01-analyse-audio.md) |
| **La lecture** | Le navigateur a le vrai son, découpé temps par temps (`_web/files/jremix.js`, Web Audio API) |
| **L'effet** | Il relie les temps qui se ressemblent (timbre et notes proches) et saute de l'un à l'autre sans coupure : le morceau ne finit jamais |

Il peut tout faire au son parce qu'il **possède le fichier audio**. Ce n'est pas un contournement du blocage de Spotify.

## Ce qu'on en retient

| Idée | Transposable ? |
|---|---|
| **Temps qui se ressemblent** utilisés **entre deux morceaux** : sortir de A sur un temps, entrer dans B sur le temps le plus proche en timbre et en notes | ✅ Ne demande que l'analyse (`segments` : `timbre`, `pitches`). Absent de Smart DJ (supposé, d'après son README) |
| Boucle sur un passage | ✅ Par saut en E1 ([test 03](../tests/03-boucle-par-saut.md)), depuis la mémoire en E2 |
| Récupérer le son ailleurs pour le traiter | ❌ Contraire aux conditions de YouTube, et on sortirait de Spotify |
