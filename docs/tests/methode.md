# Méthode de test

Tous les tests exécutent du JavaScript **dans Spotify** via le protocole de débogage de Chromium, depuis le terminal. Scripts dans [`../../outils/`](../../outils/README.md).

## 1. Ouvrir le mode débogage

Dans `~/.config/spicetify/config-xpui.ini` :

```ini
spotify_launch_flags   = --remote-debugging-port=9222
```

Puis `spicetify apply` (redémarre Spotify). Le port n'écoute que sur `127.0.0.1`.

Trouver la page de Spotify :

```bash
curl -s 127.0.0.1:9222/json/list | grep -A1 'xpui.app.spotify.com/index' | grep -o 'ws://[^"]*'
```

**Attendre ~10 s** après le démarrage : Spicetify se charge après la page (cf. [`../pieges.md`](../pieges.md)).

## 2. Exécuter du code dans Spotify

```bash
node --experimental-websocket outils/cdp-eval.mjs "<ws://…>" "<expression JavaScript>"
```

L'expression peut être asynchrone, son résultat est affiché en JSON. Exemple :

```bash
node --experimental-websocket outils/cdp-eval.mjs "$W" "$(cat outils/loop-test.js)"
```

## 3. Mesurer le son

Enregistrer la sortie pendant le test, en mono 44,1 kHz :

```bash
parec -d "$(pactl get-default-sink).monitor" --format=s16le --rate=44100 --channels=1 --latency-msec=10 > rec.raw
```

- Pour comparer **avant / après un filtre**, enregistrer aussi `dj_filter.monitor`.
- Noter l'heure de début (`date +%s%3N`) et faire renvoyer par le script les instants de ses actions (`Date.now()`) pour aligner.
- Analyse : `python3 -I outils/analyse-boucle.py <dossier>` (silences, période réelle de la boucle).
- **Supprimer les enregistrements** après analyse.

## 4. Refermer

1. Remettre `spotify_launch_flags   =` (vide), puis `spicetify apply`.
2. Vérifier : `ss -ltn | grep 9222` ne renvoie rien.
3. Arrêter tout programme de test lancé (filtre, serveur local) et vérifier que Spotify est revenu sur la sortie par défaut.
