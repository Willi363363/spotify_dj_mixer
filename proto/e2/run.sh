#!/usr/bin/env bash
# Lance une transition de la maquette E2 et enregistre entrée et sortie.
# Prérequis : sortie virtuelle dj_in chargée, Spotify routé dessus, e2.py lancé, mode débogage ouvert.
# Usage : proto/e2/run.sh <ws://…> <mode mix|loop|brake> <dossier de travail> [uri A] [uri B]
set -euo pipefail
W=$1 MODE=$2 S=$3
A=${4:-spotify:track:1bepxgCj8gKHOmoSGiW5J3}  # Bubble Like Soup
B=${5:-spotify:track:1YKIUWyelwdDfeKzwSTBn1}  # Coucounia
HERE=$(cd "$(dirname "$0")/../.." && pwd)
OUT="$(pactl get-default-sink).monitor"

date +%s%3N > "$S/rec-start.txt"
timeout 90 parec -d dj_in.monitor --format=s16le --rate=44100 --channels=1 --latency-msec=10 > "$S/in.raw" & P1=$!
timeout 90 parec -d "$OUT" --format=s16le --rate=44100 --channels=1 --latency-msec=10 > "$S/out.raw" & P2=$!
R=$(node --experimental-websocket "$HERE/outils/cdp-eval.mjs" "$W" \
  "globalThis.__A='$A'; globalThis.__B='$B'; $(cat "$HERE/proto/e2/transition.js")" 2>&1 | grep -vi experimental)
echo "$R" | tee "$S/c-$MODE.json"
python3 -I -c "
import json, socket, sys
o = json.loads(sys.argv[1]); o.update(cmd='transition', mode=sys.argv[2], bars=4)
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(json.dumps(o).encode(), ('127.0.0.1', 47801))
print('ordre envoyé :', sys.argv[2])" "$R" "$MODE"
wait $P1 $P2 || true
