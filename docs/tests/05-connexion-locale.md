# 05 · Connexion locale

**Question** : une extension Spicetify peut-elle envoyer des ordres à un programme qui tourne sur le PC, assez vite pour caler des effets sur le rythme ?

Serveur de test : [`../../outils/local-server.mjs`](../../outils/local-server.mjs) (HTTP + WebSocket minimal, `127.0.0.1:47800` uniquement).

## Protocole

1. Vérifier l'absence de règle de sécurité dans la page de Spotify (`index.html`) : aucune.
2. Depuis Spotify : `fetch` POST vers `http://127.0.0.1:47800/ping`, puis ouverture d'un WebSocket et envoi d'un message.
3. Sur une connexion déjà ouverte : 20 allers-retours, mesure du délai.

## Résultat

| Mesure | Valeur |
|---|---|
| HTTP POST | ✅ reçu, réponse 200 lue par Spotify |
| Origine annoncée | `https://xpui.app.spotify.com` |
| WebSocket | ✅ ouvert, message reçu et renvoyé |
| Ouverture d'un WebSocket (à chaud) | 2 ms |
| Aller-retour | min 0,4 ms, médiane **0,7 ms**, max 1,2 ms |
| Premier message après démarrage de Spotify | 0,56 s |

## Conséquences pour l'architecture

- **WebSocket ouvert au lancement** de l'extension, pour ne pas payer le premier délai au moment d'une transition.
- Le programme local doit **refuser toute origine autre que `https://xpui.app.spotify.com`** : n'importe quelle page web ouverte sur le PC pourrait sinon lui envoyer des ordres.
- Délai négligeable devant la précision du saut (≈ 9 ms) : on peut caler un effet sur le temps.

## Conclusion

✅ Pas de blocage côté Spotify. L'extension peut piloter les filtres PipeWire via un programme local.
