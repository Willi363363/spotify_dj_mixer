#!/usr/bin/env bash
# Démarre la maquette E2 quand Spotify s'ouvre, l'arrête quand il se ferme.
# Tourne en continu (service utilisateur systemd, cf. installer-maquette-auto.sh) et regarde toutes les 2 s.
#
# Au démarrage de Spotify : crée la sortie virtuelle dj_in (sans changer la sortie ni le micro par défaut),
# puis lance e2.py et espion.mjs. À la fermeture : arrête les deux et retire dj_in.
# Spotify doit être lancé avec --remote-debugging-port=9222 (~/.config/spotify-flags.conf, posé par l'installeur).
#
# Variables : NODE (chemin de node), DJ_AVANCE (s, défaut 60), DJ_WORK (défaut ~/spotify_dj_mixer-travail).
set -uo pipefail

REPO=$(cd "$(dirname "$0")/.." && pwd)
NODE=${NODE:-$(command -v node)}
AVANCE=${DJ_AVANCE:-60}
export DJ_WORK=${DJ_WORK:-$HOME/spotify_dj_mixer-travail}
RUN=${XDG_RUNTIME_DIR:-/tmp}/dj-maquette
mkdir -p "$RUN" "$DJ_WORK"

log() { echo "$(date +%H:%M:%S) $*"; }
vivant() { [[ -f "$RUN/$1.pid" ]] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }
spotify_ouvert() { pgrep -x spotify >/dev/null; }

demarrer() {
  local sink src
  sink=$(pactl get-default-sink)
  src=$(pactl get-default-source)
  if ! pactl list short sinks | grep -q $'\tdj_in\t'; then
    pactl load-module module-null-sink sink_name=dj_in > "$RUN/dj_in.module"
    # PipeWire peut prendre la nouvelle sortie par défaut : on remet celle d'avant (appels, autres applis)
    [[ "$(pactl get-default-sink)" == "$sink" ]] || pactl set-default-sink "$sink"
    [[ "$(pactl get-default-source)" == "$src" ]] || pactl set-default-source "$src"
  fi
  python3 -I -u "$REPO/proto/e2/e2.py" "$AVANCE" >> "$RUN/e2.log" 2>&1 &
  echo $! > "$RUN/e2.pid"
  "$NODE" --experimental-websocket "$REPO/proto/e2/espion.mjs" >> "$RUN/espion.log" 2>&1 &
  echo $! > "$RUN/espion.pid"
  log "Spotify ouvert : maquette lancée (avance ${AVANCE} s, sortie par défaut ${sink})"
}

arreter() {
  local p
  for p in e2 espion; do
    vivant "$p" && kill "$(cat "$RUN/$p.pid")" 2>/dev/null
    rm -f "$RUN/$p.pid"
  done
  # Ne retire dj_in que si c'est nous qui l'avons créée
  if [[ -s "$RUN/dj_in.module" ]]; then
    pactl unload-module "$(cat "$RUN/dj_in.module")" 2>/dev/null
    rm -f "$RUN/dj_in.module"
  fi
  log "maquette arrêtée"
}

trap 'arreter; exit 0' TERM INT

for (( ; ; )); do
  if spotify_ouvert; then
    if ! vivant e2 || ! vivant espion; then
      vivant e2 || vivant espion && arreter   # un seul des deux est mort : on repart propre
      demarrer
    fi
  elif vivant e2 || vivant espion || [[ -s "$RUN/dj_in.module" ]]; then
    log "Spotify fermé"
    arreter
  fi
  sleep 2
done
