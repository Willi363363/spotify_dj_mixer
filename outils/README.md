# Outils de test

Scripts qui ont servi aux tests de [`../docs/tests/`](../docs/tests/README.md). Mode d'emploi général : [`../docs/tests/methode.md`](../docs/tests/methode.md).

| Fichier | Rôle | Test |
|---|---|---|
| [`cdp-eval.mjs`](cdp-eval.mjs) | Exécute une expression JavaScript dans Spotify (mode débogage) et affiche le résultat | tous |
| [`loop-test.js`](loop-test.js) | Lance « Around the World », boucle une mesure du passage le plus fort 8 fois, renvoie les instants des sauts. Réglage : `LEAD` | 03 |
| [`analyse-boucle.py`](analyse-boucle.py) | Période réelle de la boucle et silences, sur un enregistrement | 03 |
| [`dj-filter.conf`](dj-filter.conf) | Instance PipeWire temporaire : sortie `dj_filter` avec un passe-haut `hp` | 04 |
| [`analyse-bandes.py`](analyse-bandes.py) | Énergie des basses et des médiums avant et après le filtre | 04 |
| [`local-server.mjs`](local-server.mjs) | Serveur HTTP + WebSocket minimal sur `127.0.0.1:47800`, journalise ce qu'il reçoit | 05 |

## Limites

- Scripts **de test** : `local-server.mjs` ne vérifie pas l'origine des messages et ne gère que des trames WebSocket courtes. Ne pas le laisser tourner.
- `loop-test.js` remplace le morceau en cours et dépend de l'identifiant de « Around the World » (`spotify:track:1pKYYY0dkg23sQQXi0Q5zN`).
- Les analyses Python s'exécutent avec `python3 -I` et lisent des fichiers bruts sans en-tête.
