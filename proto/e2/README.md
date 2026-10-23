# Maquette E2

Preuve de concept du module « son retardé en mémoire » (cf. [`../../docs/architecture.md`](../../docs/architecture.md#e2-le-module-avec-avance)). Résultats : [`../../docs/tests/08-serie-c-maquette-e2.md`](../../docs/tests/08-serie-c-maquette-e2.md).

| Fichier | Rôle |
|---|---|
| [`e2.py`](e2.py) | Lit `dj_in.monitor`, garde 10 min en mémoire, joue avec D secondes de retard, fait rendre la recette demandée sur ordre UDP, se replie sur une coupe en cas de refus ; sert l'écran ; notifie « Dans 5 s » puis « Maintenant » |
| [`recettes.py`](recettes.py) | Préréglages (montée, retour arrière, coupe, écho, mélange, frein, boucle) et leurs ingrédients ; outils de traitement (filtres sans clic, étirement par carte des temps, accord des grosses caisses) |
| [`rendu.py`](rendu.py) | Rendu de chaque préréglage à partir de la mémoire |
| [`test_rendu.py`](test_rendu.py) | Vérifie hors ligne chaque préréglage sur des morceaux de synthèse |
| [`espion.mjs`](espion.mjs) | Envoie à `e2.py`, 4 fois par seconde, le morceau et la position de Spotify, pour l'écran |
| [`ecran.html`](ecran.html) | Écran servi sur `http://127.0.0.1:47802` : ce qu'on entend, la transition à venir ou en cours, ce que Spotify joue |
| [`transition.js`](transition.js) | Dans Spotify : choisit les points par score et le préréglage (si `auto`), joue A jusqu'à sa sortie, lance B sur son entrée, renvoie l'heure du changement ; `__DRY` pour calculer à blanc |
| [`run.sh`](run.sh) | Enregistre entrée et sortie, lance `transition.js`, envoie l'ordre à `e2.py` |
| [`analyse.py`](analyse.py) | Retard réel, fidélité, silences dans la sortie |

## Lancer

```bash
pactl load-module module-null-sink sink_name=dj_in        # note le numéro renvoyé
pactl move-sink-input <flux Spotify> dj_in
python3 -I -u proto/e2/e2.py 30 &                         # 30 s d'avance (un mix de 8 mesures en demande ~20)
proto/e2/run.sh "<ws://…>" build /tmp/essai <uri A> <uri B>   # ou mix (BARS=8), loop, brake
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
