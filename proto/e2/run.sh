#!/usr/bin/env bash
# Lance une transition v2 du moteur E2 et enregistre entrée et sortie.
# Prérequis : sortie virtuelle dj_in chargée, Spotify routé dessus, e2.py lancé, mode débogage ouvert, extension
# dj-auto v2 installée (spicetify/installer.sh).
# Usage : proto/e2/run.sh <ws://…> <auto|C1…C8|R1|R2> <dossier de travail> [uri A] [uri B]
# La transition jouée est notée dans <dossier>/derniere-transition, pour qu'« auto » ne la répète pas.
set -euo pipefail
W=$1 TR=$2 S=$3
A=${4:-spotify:track:1bepxgCj8gKHOmoSGiW5J3}  # Bubble Like Soup
B=${5:-spotify:track:1YKIUWyelwdDfeKzwSTBn1}  # Coucounia
# A, B et TR finissent dans du JS exécuté dans Spotify : format strict. Les anciens préréglages sont refusés.
URI_RE='^spotify:track:[A-Za-z0-9]{22}$'
TR_RE='^(auto|C[1-8]|R[12])$'
[[ $A =~ $URI_RE && $B =~ $URI_RE ]] || { echo "uri invalide" >&2; exit 2; }
[[ $TR =~ $TR_RE ]] || { echo "transition invalide : $TR (attendu auto, C1…C8, R1, R2)" >&2; exit 2; }
HERE=$(cd "$(dirname "$0")/../.." && pwd)
OUT="$(pactl get-default-sink).monitor"
LAST=$(cat "$S/derniere-transition" 2>/dev/null || true)
[[ $LAST =~ ^(C[1-8]|R[12])?$ ]] || LAST=

# 150 s : 32 s avant le saut + 60 s d'avance du moteur + la transition entendue
date +%s%3N > "$S/rec-start.txt"
timeout 150 parec -d dj_in.monitor --format=s16le --rate=44100 --channels=1 --latency-msec=10 > "$S/in.raw" & P1=$!
timeout 150 parec -d "$OUT" --format=s16le --rate=44100 --channels=1 --latency-msec=10 > "$S/out.raw" & P2=$!
R=$(node --experimental-websocket "$HERE/outils/cdp-eval.mjs" "$W" \
  "globalThis.__DRY=false; globalThis.__A='$A'; globalThis.__B='$B'; globalThis.__TRANSITION='$TR'; globalThis.__LAST='$LAST'; $(cat "$HERE/proto/e2/transition.js")" \
  2>&1 | grep -vi experimental)
echo "$R" | tee "$S/ordre-$TR.json"
# Même ordre v2 qu'en POST /order (ADR 0001), en UDP ; « cmd » le distingue des messages d'espion.mjs
python3 -I -c "
import json, socket, sys
o = json.loads(sys.argv[1])
if 'erreur' in o:
    sys.exit('transition annulée : ' + o['erreur'])
o['cmd'] = 'transition'
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(json.dumps(o).encode(), ('127.0.0.1', 47801))
open(sys.argv[2], 'w').write(o['transition'])
print('ordre envoyé :', o['transition'], '(choisie', o['choisie'] + ') |', o['raison'])" "$R" "$S/derniere-transition"
wait $P1 $P2 || true
