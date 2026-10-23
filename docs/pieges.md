# Pièges

Format : **symptôme → cause → parade**.

## Spicetify

| Symptôme | Cause | Parade |
|---|---|---|
| `current_theme` vaut soudain `color_scheme` | `spicetify config <clé> <valeur>` **écrit** la valeur, il ne lit pas | Lire la config avec `grep` sur `config-xpui.ini`, jamais avec `spicetify config` |
| `apply` ne fait rien et affiche « Preprocessed Spotify data is outdated » | Spicetify mis à jour, sauvegarde faite avec l'ancienne version | `spicetify restore backup apply` |
| Une édition de `spotify_launch_flags   = ` ne trouve plus la ligne | `apply` réécrit le fichier et retire l'espace final | Chercher `spotify_launch_flags   =` sans espace final |
| `getAudioData` répond « URI is invalid. » ou `CosmosAsync` indéfini | Spicetify pas encore chargé juste après le démarrage de Spotify | Attendre `Spicetify.Player.data.item` et `Spicetify.URI.Type` avant tout appel |
| Recherche via `api.spotify.com/v1/search` : code 429 | Limite de débit de l'API web publique | Ne pas dépendre de l'API web publique ; passer par les URI ou les API internes |

## Mode débogage (tests)

| Symptôme | Cause | Parade |
|---|---|---|
| Le port 9222 reste ouvert après un test | Option de lancement oubliée dans la config | Retirer l'option, `spicetify apply`, vérifier `ss -ltn \| grep 9222` vide |
| `WebSocket is not defined` dans Node | Node 20 n'a pas de client WebSocket stable | `node --experimental-websocket` |

## Mesures audio

| Symptôme | Cause | Parade |
|---|---|---|
| Une boucle « sonne bizarre » alors que les chiffres de Spotify sont bons | `getProgress()` annonce la position **avant** que le son ne reparte : ~80 ms d'écart | Mesurer sur un enregistrement de la sortie son, jamais sur la position annoncée |
| Coupe des basses inaudible | Haut-parleurs du portable | Casque, ou mesure par enregistrement |
| Spotify en pause après l'arrêt du filtre de test | La sortie virtuelle disparaît, Spotify s'arrête | Relancer la lecture ; prévoir le cas dans le programme local |

## Shell (zsh)

| Symptôme | Cause | Parade |
|---|---|---|
| `==== not found` et la suite de la commande ne s'exécute pas | zsh interprète `=mot` comme un chemin de commande | Mettre les séparateurs entre guillemets : `echo '-----'` |
