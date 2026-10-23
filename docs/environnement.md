# Environnement de référence

Toutes les mesures de [`tests/`](tests/README.md) ont été faites sur cette machine. Un chiffre de calage (comme les 115 ms du saut) ne vaut que pour elle.

## Versions

| Composant | Version |
|---|---|
| OS | Arch Linux, session Wayland |
| Spotify desktop | 1.3.4.258 (`/opt/spotify`) |
| Spicetify | 2.46.2 (installé par le script officiel dans `~/.spicetify`, pas par pacman) |
| PipeWire | 1.6.9 (serveur), paquet 1.6.10 |
| Node.js | 20.18 (WebSocket client derrière `--experimental-websocket`) |
| Python | avec numpy 2.4, pour l'analyse des enregistrements |
| Sortie son | haut-parleurs intégrés du portable (`…HiFi__Speaker__sink`) |
| Compte Spotify | **gratuit** |

## Config Spicetify

Fichier : `~/.config/spicetify/config-xpui.ini`.

| Clé | Valeur | Pourquoi |
|---|---|---|
| `custom_apps` | `marketplace` | Seule app installée |
| `extensions` | vide | Aucune extension pour l'instant |
| `current_theme` / `color_scheme` | `marketplace` | Prêt pour les thèmes du Marketplace, mais **aucun thème choisi** (performance) |
| `replace_colors` / `inject_theme_js` | `1` | idem |
| `spotify_launch_flags` | vide | Ne contient `--remote-debugging-port=9222` que pendant un test |
| `expose_apis` | `1` | Indispensable : rend `Spicetify.Platform`, `CosmosAsync`, etc. disponibles |

Après tout changement : `spicetify apply` (redémarre Spotify). Après une mise à jour de Spicetify : `spicetify restore backup apply`.

## Haut-parleurs du portable

Ils ne restituent presque rien sous ~150 Hz : une coupe des basses y est **mesurable mais peu audible**. Pour juger un effet sur les graves, écouter au casque ou monter la fréquence de coupure (cf. [`tests/04-filtre-pipewire.md`](tests/04-filtre-pipewire.md)).
