#!/usr/bin/env bash
# Installe le lancement automatique de la maquette E2 avec Spotify :
# - ajoute --remote-debugging-port=9222 à ~/.config/spotify-flags.conf (lu par /usr/bin/spotify sous Arch) ;
# - crée et active le service utilisateur systemd dj-maquette, qui lance outils/maquette-auto.sh.
# Usage : outils/installer-maquette-auto.sh            Désinstaller : outils/installer-maquette-auto.sh --retirer
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
FLAGS=${XDG_CONFIG_HOME:-$HOME/.config}/spotify-flags.conf
UNIT=${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/dj-maquette.service
DEBUG=--remote-debugging-port=9222

if [[ "${1:-}" == "--retirer" ]]; then
  systemctl --user disable --now dj-maquette.service 2>/dev/null || true
  rm -f "$UNIT"
  systemctl --user daemon-reload
  [[ -f "$FLAGS" ]] && sed -i "/^${DEBUG}\$/d" "$FLAGS"
  echo "Lancement automatique retiré (Spotify gardera le mode débogage jusqu'à son prochain redémarrage)."
  exit 0
fi

NODE=$(command -v node) || { echo "node introuvable dans le PATH" >&2; exit 1; }
mkdir -p "$(dirname "$FLAGS")" "$(dirname "$UNIT")"
grep -qx -- "$DEBUG" "$FLAGS" 2>/dev/null || echo "$DEBUG" >> "$FLAGS"

cat > "$UNIT" <<EOF
[Unit]
Description=Maquette du mode DJ : démarre avec Spotify, s'arrête avec lui
After=pipewire-pulse.service

[Service]
Environment=NODE=$NODE
ExecStart=$HERE/maquette-auto.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now dj-maquette.service
echo "Installé : la maquette démarre à l'ouverture de Spotify. Journal : journalctl --user -u dj-maquette -f"
