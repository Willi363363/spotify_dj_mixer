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

## PipeWire

| Symptôme | Cause | Parade |
|---|---|---|
| `can't load config outils/….conf: No such file or directory` | `pipewire -c` cherche un chemin relatif dans ses propres dossiers de config | Toujours un chemin absolu : `pipewire -c "$PWD/outils/….conf"` |
| Un balayage de filtre claque | Les nœuds `bq_*` changent leurs coefficients d'un coup | Moins de paliers, effets lissés, ou fondu croisé entre deux chaînes (cf. [`tests/07-serie-b-effets.md`](tests/07-serie-b-effets.md)) |
| Le trou au changement de morceau est mal repéré (200 ms au lieu de 40) | Un passage calme du morceau confondu avec le silence | Ne chercher que du silence numérique (quasi-zéros) |

| On n'entend pas A, la transition sonne « fausse », l'enregistrement de l'entrée est **silencieux** | Un appareil Bluetooth connecté devient la sortie par défaut, et PipeWire y bascule Spotify, qui contourne la maquette | `e2.py` vérifie toutes les 2 s que Spotify entre dans `dj_in` et que sa propre sortie suit l'appareil par défaut ; toujours contrôler l'enregistrement avant de croire un verdict |
| Spicetify à moitié chargé après un redémarrage de Spotify (`Spicetify.URI` absent, `Player.data.item` vide) | Spotify ne joue rien : une partie de Spicetify attend un morceau chargé | Lancer un morceau (`PlayerAPI.play`), et au besoin recharger la page (`location.reload()`) |

| Une transition saute en arrière dans A, ou n'est pas jouée | Préparée après le moment où elle devait commencer : l'avance en mémoire était trop courte pour attendre B puis calculer | Avance ≥ 2 × la durée de la transition + 2 mesures + le calcul (50 s à 100 BPM) ; décider d'un refus sur 2 mesures ; abandonner une transition prête trop tard |

## Spicetify (interface)

| Symptôme | Cause | Parade |
|---|---|---|
| Une modification de l'app ou de l'extension n'apparaît pas dans Spotify, même après rechargement | Spicetify **copie** extensions et apps dans Spotify au moment de `apply` ; les liens symboliques ne sont pas suivis ensuite | `spicetify apply` après chaque modification |
| Un test clique sur autre chose que le bouton visé et change la lecture | Recherche d'élément par texte partiel (« DJ » dans « (DJ Mix) ») | Viser par la référence renvoyée par l'API (`button.element`) |
| Le libellé d'un `Playbar.Button` est introuvable dans la page | Il n'est pas posé en `aria-label`, seulement en info-bulle | Idem |

## Shell (zsh)

| Symptôme | Cause | Parade |
|---|---|---|
| `==== not found` et la suite de la commande ne s'exécute pas | zsh interprète `=mot` comme un chemin de commande | Mettre les séparateurs entre guillemets : `echo '-----'` |
| `pkill -f motif` tue la commande elle-même (code 144) | Le motif figure dans la ligne de commande du shell qui l'exécute | `pkill -f '[m]otif'`, ou tuer par numéro de processus |
| `pkill -f 'parec -d dj_in.monitor'` coupe aussi la maquette E2 | La maquette lit avec la même commande | Garder les numéros des enregistrements et ne tuer qu'eux |
| `wait` ne rend jamais la main | Il attend aussi un programme lancé en arrière-plan qui ne s'arrête pas | `wait $PID1 $PID2`, ou lancer le programme avec `setsid … & disown` |
