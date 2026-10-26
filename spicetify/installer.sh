#!/usr/bin/env bash
# Installe dans Spotify, via Spicetify :
# - l'app « Mode DJ » (page dans la barre de Spotify) ;
# - l'extension dj-auto.js (mode DJ automatique, toujours active, allumée depuis l'app).
# Liens symboliques vers le dépôt (une modification du code ne demande qu'un rechargement de Spotify),
# inscription dans la config, puis `spicetify apply` (redémarre Spotify).
# Usage : spicetify/installer.sh            Désinstaller : spicetify/installer.sh --retirer
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DATA=$(spicetify path userdata)
CONF="$DATA/config-xpui.ini"

if [[ "${1:-}" == "--retirer" ]]; then
  spicetify config custom_apps dj-mixer- extensions dj-auto.js-   # le « - » final retire de la liste
  rm -f "$DATA/CustomApps/dj-mixer" "$DATA/Extensions/dj-auto.js"
  spicetify apply
  exit 0
fi

mkdir -p "$DATA/CustomApps" "$DATA/Extensions"
ln -sfn "$HERE/dj-mixer" "$DATA/CustomApps/dj-mixer"
ln -sfn "$HERE/dj-auto.js" "$DATA/Extensions/dj-auto.js"
grep -q '^custom_apps.*dj-mixer' "$CONF" || spicetify config custom_apps dj-mixer
grep -q '^extensions.*dj-auto.js' "$CONF" || spicetify config extensions dj-auto.js
spicetify apply
echo "Mode DJ installé : page « Mode DJ » dans Spotify, extension dj-auto active."
