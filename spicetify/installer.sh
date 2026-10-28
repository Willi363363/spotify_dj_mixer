#!/usr/bin/env bash
# Installe dans Spotify, via Spicetify :
# - l'app « Mode DJ » (page dans la barre de Spotify) ;
# - les extensions du mode DJ automatique (ADR 0005) : dj-catalogue.js, dj-voix.js, dj-placement.js, dj-choix.js
#   (modules purs, sur globalThis.DJCore) et dj-auto.js (orchestration, attend les quatre autres).
# Liens symboliques vers le dépôt, inscription dans la config, puis `spicetify apply` (redémarre Spotify).
# Spicetify copie les fichiers au moment de `apply` : toute modification du code demande un nouveau
# `spicetify apply`, un rechargement de Spotify garde l'ancienne version.
# Usage : spicetify/installer.sh            Désinstaller : spicetify/installer.sh --retirer
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
DATA=$(spicetify path userdata)
CONF="$DATA/config-xpui.ini"
EXTS=(dj-catalogue.js dj-voix.js dj-placement.js dj-choix.js dj-auto.js)

if [[ "${1:-}" == "--retirer" ]]; then
  args=(custom_apps dj-mixer-)
  for e in "${EXTS[@]}"; do args+=(extensions "$e-"); done   # le « - » final retire de la liste
  spicetify config "${args[@]}"
  rm -f "$DATA/CustomApps/dj-mixer"
  for e in "${EXTS[@]}"; do rm -f "$DATA/Extensions/$e"; done
  spicetify apply
  exit 0
fi

for e in "${EXTS[@]}"; do [[ -f "$HERE/$e" ]] || { echo "fichier manquant : $HERE/$e" >&2; exit 1; }; done
mkdir -p "$DATA/CustomApps" "$DATA/Extensions"
ln -sfn "$HERE/dj-mixer" "$DATA/CustomApps/dj-mixer"
grep -q '^custom_apps.*dj-mixer' "$CONF" || spicetify config custom_apps dj-mixer
for e in "${EXTS[@]}"; do
  ln -sfn "$HERE/$e" "$DATA/Extensions/$e"
  grep -q "^extensions.*$e" "$CONF" || spicetify config extensions "$e"
done
spicetify apply
echo "Mode DJ installé : page « Mode DJ » dans Spotify, extensions ${EXTS[*]} actives."
