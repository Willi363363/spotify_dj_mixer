# Maquette E2

Preuve de concept du module « son retardé en mémoire » (cf. [`../../docs/architecture.md`](../../docs/architecture.md#e2-le-module-avec-avance)). Résultats : [`../../docs/tests/08-serie-c-maquette-e2.md`](../../docs/tests/08-serie-c-maquette-e2.md).

| Fichier | Rôle |
|---|---|
| [`e2.py`](e2.py) | Lit `dj_in.monitor`, garde 10 min en mémoire, joue avec D secondes de retard, exécute les transitions `mix`, `loop`, `brake` sur ordre UDP |
| [`transition.js`](transition.js) | Dans Spotify : joue A, lance B sur son drop au premier temps d'une mesure de A, renvoie l'heure du changement |
| [`run.sh`](run.sh) | Enregistre entrée et sortie, lance `transition.js`, envoie l'ordre à `e2.py` |
| [`analyse.py`](analyse.py) | Retard réel, fidélité, silences dans la sortie |

## Lancer

```bash
pactl load-module module-null-sink sink_name=dj_in        # note le numéro renvoyé
pactl move-sink-input <flux Spotify> dj_in
python3 -I -u proto/e2/e2.py 20 &                         # 20 s d'avance
proto/e2/run.sh "<ws://…>" mix /tmp/essai                # ou loop, brake
python3 -I proto/e2/analyse.py /tmp/essai /tmp/essai/c-mix.json
```

Le mode débogage de Spotify doit être ouvert (cf. [`../../docs/tests/methode.md`](../../docs/tests/methode.md)).

## Ranger

1. Arrêter `e2.py` et son `pacat` **par numéro de processus** (cf. [`../../docs/pieges.md`](../../docs/pieges.md)).
2. `pactl unload-module <numéro>` : Spotify revient seul sur la sortie par défaut.

## Limites

- Python : des trous de lecture possibles (2 × 45 ms constatés). Suffit pour valider, pas pour écouter au quotidien.
- Dépend de `rubberband` (CLI) et de `numpy`.
- Pas de gestion de la pause, du morceau suivant à la main, ni des pubs.
- Le port UDP n'accepte que `127.0.0.1` mais ne vérifie pas l'expéditeur.
