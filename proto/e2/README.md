# Maquette E2

Preuve de concept du module « son retardé en mémoire » (cf. [`../../docs/architecture.md`](../../docs/architecture.md#e2-le-module-avec-avance)). Résultats : [`../../docs/tests/08-serie-c-maquette-e2.md`](../../docs/tests/08-serie-c-maquette-e2.md), écoutes : [`../../docs/tests/09-ecoute-maquette.md`](../../docs/tests/09-ecoute-maquette.md).

| Fichier | Rôle |
|---|---|
| [`e2.py`](e2.py) | Lit `dj_in.monitor` dans une mémoire circulaire de 10 min, joue avec ~60 s d'avance, fait rendre la recette demandée (ordre UDP de `run.sh` ou POST `/order` de l'extension), se replie sur la montée courte en cas de refus ; regagne l'avance perdue ; sert l'écran, l'état (`/state`) et les notes d'écoute (`/rating`) |
| [`recettes.py`](recettes.py) | Préréglages (montée, montée courte, écho, retour arrière, frein, balayage de filtre, drop swap, mélange) et leurs ingrédients ; outils de traitement (filtres sans clic, limiteur, niveau perçu, étirement par carte des temps, accord des grosses caisses) |
| [`rendu.py`](rendu.py) | Rendu de chaque préréglage à partir de la mémoire |
| [`test_rendu.py`](test_rendu.py) | Vérifie hors ligne chaque préréglage sur des morceaux de synthèse : raccords, avance conservée, regain, refus |
| [`espion.mjs`](espion.mjs) | Envoie à `e2.py`, 4 fois par seconde, le morceau et la position de Spotify ; retrouve seul la page de Spotify et se reconnecte après un redémarrage |
| [`ecran.html`](ecran.html) | Écran servi sur `http://127.0.0.1:47802` : boutons **Lancer** / **Rejouer** (paire, préréglage), ce qu'on entend, **frise** A → B. Les boutons n'acceptent que les demandes venant de cette page ou de l'app (en-tête `Origin`) |
| [`transition.js`](transition.js) | Dans Spotify : demande le choix à l'extension (`DJ.planTransition`), joue A jusqu'à sa sortie, saute sur B (`DJ.switchAt`), renvoie l'heure du changement ; `__DRY` pour calculer à blanc |
| [`run.sh`](run.sh) | Enregistre entrée et sortie, lance `transition.js`, envoie l'ordre à `e2.py` |
| [`analyse.py`](analyse.py) | Retard réel, fidélité, silences dans la sortie |

## Avance et regain

Chaque style doux prolonge A (boucles, roulements) pendant que B monte, lancé 8 mesures avant son drop : le segment dure au moins ce qu'il consomme, arrondi à la mesure. Un mélange superpose 8 mesures et fait fondre l'avance d'autant ; les styles doux suivants la regagnent (jusqu'à 2 mesures de A prolongé en plus chacun). La montée de B n'est jamais raccourcie pour rendre de l'avance : quand elle dépasse la cible de 8 s, l'extension favorise le mélange. L'avance comptée inclut le segment en cours et les transitions déjà prévues. Chaque style exige une avance minimale (mesures de A rejouées + avance de B + 2 mesures + calcul), relue juste avant le saut ; sinon, montée courte.

## Comportements

- **Pause** : la maquette se tait en même temps que Spotify (d'après l'espion, 2 messages de suite, ~0,5 s) et retire le silence reçu avant la confirmation ; à la reprise, la musique repart où on l'entendait, avance intacte, même au milieu d'une transition.
- **Transition prête trop tard ou en échec** : Spotify a déjà sauté ; un **secours** d'une mesure (A en boucle sans graves, B qui monte filtré) remplace la coupe sèche.
- **parec / pacat arrêtés** (PipeWire relancé) : relancés automatiquement.
- **Morceau changé à la main** (ou fin naturelle après un saut raté) : l'extension envoie une montée courte de rattrapage, B monte sur ses premières mesures.
- **Réglage du rendu** : `recettes.py` et `rendu.py` sont relus à chaque ordre s'ils ont changé ; seul un changement de `e2.py` demande de relancer la maquette (1 min de remplissage).

## Lancer

```bash
pactl load-module module-null-sink sink_name=dj_in        # note le numéro renvoyé
DJ_WORK=/tmp/essai python3 -I -u proto/e2/e2.py 60 &    # 60 s d'avance ; DJ_WORK active les boutons
node --experimental-websocket proto/e2/espion.mjs &      # positions de Spotify pour l'écran et l'app
proto/e2/run.sh "<ws://…>" montee /tmp/essai <uri A> <uri B>   # ou auto, melange, drop_swap…
python3 -I proto/e2/analyse.py /tmp/essai /tmp/essai/c-montee.json 60
```

`e2.py` ramène lui-même Spotify dans `dj_in` (toutes les 2 s). Le mode débogage de Spotify doit être ouvert (cf. [`../../docs/tests/methode.md`](../../docs/tests/methode.md)). Les notes d'écoute vont dans `docs/tests/notes-ecoute.jsonl` (ou `DJ_NOTES`).

## Ranger

1. Arrêter `e2.py` et son `pacat` **par numéro de processus** (cf. [`../../docs/pieges.md`](../../docs/pieges.md)).
2. `pactl unload-module <numéro>` : Spotify revient seul sur la sortie par défaut.

## Limites

- Python : des trous de lecture possibles pendant les calculs ; `pacat` à 200 ms de latence pour les absorber.
- Dépend de `rubberband` (CLI) et de `numpy`.
- Pas de gestion des pubs.
- Le changement de morceau d'un saut dans la playlist est placé à l'heure (pas de silence à repérer) : précision de quelques dizaines de ms.
- Le port UDP n'accepte que `127.0.0.1` mais ne vérifie pas l'expéditeur.
