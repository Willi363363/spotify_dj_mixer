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
| Une boucle sonne décalée alors que les chiffres de Spotify sont bons | `getProgress()` annonce la position **avant** que le son ne reparte : ~80 ms d'écart | Mesurer sur un enregistrement de la sortie son, jamais sur la position annoncée |
| Coupe des basses inaudible | Haut-parleurs du portable | Casque, ou mesure par enregistrement |
| Spotify en pause après l'arrêt du filtre de test | La sortie virtuelle disparaît, Spotify s'arrête | Relancer la lecture ; prévoir le cas dans le programme local |
| La maquette ne trouve pas le changement de morceau (« aucun silence ») en mode auto | Un saut **dans la playlist** (`skipTo`) enchaîne A et B sans silence ni clic exploitable ; seul le saut vers un morceau seul laisse un trou | Changement placé à l'heure de l'ordre + 90 ms (`SWITCH_S` dans `e2.py`), avec une marge |
| La dernière mesure de A manque (journal : fin de A « recalée de −1 600 à −2 500 ms ») ; une coupe sèche consomme ~2 s d'avance | Le 1 de sortie était bien en mémoire, mais `placer` le cherchait à ±150 ms de la fin estimée avec une mesure de temps **après** la sortie, c'est-à-dire sur le son de B : un lag positif le faisait reculer d'une mesure (10 essais sur 23). L'instant du saut varie de ±100 ms d'un essai à l'autre | Temps de A limités à la sortie (`dj-choix.js`), recherche dans [−320 ; +30] ms (`A_AVANT_S`, `A_APRES_S`, `e2.py`), saut 60 ms après la sortie (`LEAD = −60`) ; cf. [`tests/13-essai-direct-v2.md`](tests/13-essai-direct-v2.md) |
| Un clic est signalé au premier ou au dernier échantillon d'un rendu réel, absent de l'enregistrement | Au bout d'un tableau, la médiane locale ne voit qu'un côté (ex. intro calme de B), le vrai flux est plus chargé | `mesures.rapport(..., complet=True, avant=…, apres=…)` avec le flux ; sans lui, les bornes de bord ne sont pas jugées |
| Un « clic » sur un 1, alors que la sortie est fidèle au rendu | Attaque propre au morceau (premier temps accentué), plus forte que les temps voisins de référence | Chercher le même clic dans le flux de Spotify (`dj_in.monitor`) au même instant musical : s'il y est, ce n'est pas le moteur |
| `echange_ms` de 400 à 550 ms sur une coupe sèche (C1) | B commence sans basse : la mesure voit sa première note de basse, pas la rampe | Ne juger le critère 9.1-3 que si B a des graves dès son 1 |
| Paroles synchronisées absentes par rafales (`{"code":429}`) | L'adresse `color-lyrics` limite le débit (≈ 30 requêtes rapprochées) | Une requête toutes les 2 à 3 s au plus, en cache ; V1 retombe sur V2 sans erreur |

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
