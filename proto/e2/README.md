# Maquette E2 : moteur des transitions v2

Module « son retardé en mémoire » (cf. [`../../docs/architecture.md`](../../docs/architecture.md#e2-le-module-avec-avance)) qui rend les transitions v2 : catalogue C1-C8, replis R1/R2, secours. Spec : [`../../docs/specs/transitions-v2.md`](../../docs/specs/transitions-v2.md) ; contrat : [ADR 0001](../../docs/adr/0001-contrat-ordre-v2.md) ; découpage : [ADR 0005](../../docs/adr/0005-modules-transitions.md). Preuves de l'infrastructure : tests [08](../../docs/tests/08-serie-c-maquette-e2.md) et [10](../../docs/tests/10-calage.md). **Pas encore écouté** : cf. [protocole d'écoute](../../docs/specs/protocole-ecoute.md).

Le moteur ne choisit rien : l'extension ([`../../spicetify/`](../../spicetify/README.md)) décide la transition, les points et l'échelle de repli, et envoie un ordre v2. Le moteur repère le saut dans le flux, recale A et B sur les grilles de Spotify, essaie la transition puis ses replis, mesure le rendu et en rend compte.

## Fichiers

| Fichier | Rôle |
|---|---|
| [`e2.py`](e2.py) | Lit `dj_in.monitor` dans une mémoire circulaire de 10 min, joue avec ~60 s d'avance ; reçoit les ordres v2 (`POST /order` de l'extension, UDP 47801 de `run.sh`), les valide, fait rendre la transition (`catalogue.rendre`), publie le rapport dans `/state`, enregistre les notes (`/rating`), lance un essai (`/run`) ; ralentit la lecture pour regagner l'avance (`DJ_SLOW`) |
| [`transitions/`](transitions/) | Paquet des rendus, rechargé à chaud quand un fichier change |
| ├ `contrat.py` | Validation de l'ordre v2 (`valider_ordre`), identifiants, recouvrements permis |
| ├ `catalogue.py` | Fiches C1-C8, R1, R2 et échelle de repli au rendu |
| ├ `seches.py`, `boucle.py`, `superposees.py` | Rendus C1, C2, C3, R2 · C4 et secours · C5 à C8 et R1 |
| ├ `primitives.py`, `outils.py` | EQ 3 bandes (FFT à phase nulle, ADR 0006), courbes, filtres balayés, écho, limiteur, étirement |
| ├ `calage.py` | Calage sur la grille de Spotify (`grid_lag`, `grid_fit`, `caler_superposition`) |
| ├ `voix.py` | Voix par mesure sur la mémoire (V3, ADR 0002), pour dégrader une transition au rendu |
| └ `mesures.py` | Critères 9.1 sur le son rendu : calage, basses, échange, niveau, crête, trous, clics, courbes |
| [`synthese.py`](synthese.py) | Morceaux de synthèse pour les tests (grille connue, basse, voix factice) |
| [`ecran.html`](ecran.html) | Écran sur `http://127.0.0.1:47802` : écoute à l'aveugle, note et étiquettes, lancement d'un essai |
| [`etat-factice.json`](etat-factice.json) | Un `/state` v2 factice, pour travailler l'écran sans Spotify ni moteur |
| [`transition.js`](transition.js) | Dans Spotify : demande le plan à l'extension (`DJ.planTransition`), joue A jusqu'à sa sortie, saute sur B (`DJ.switchAt`), rend l'ordre v2 ; `__DRY` pour calculer à blanc |
| [`run.sh`](run.sh) | Enregistre entrée et sortie, lance `transition.js`, envoie l'ordre au moteur en UDP |
| [`espion.mjs`](espion.mjs) | Envoie à `e2.py`, 4 fois par seconde, le morceau et la position de Spotify |
| [`analyse.py`](analyse.py) | Retard réel, fidélité, silences dans la sortie enregistrée par `run.sh` |

## Lancer

**Automatique** : `outils/installer-maquette-auto.sh` une fois ; ensuite la maquette démarre à chaque ouverture de Spotify (avance 60 s, `DJ_WORK=~/spotify_dj_mixer-travail`) et s'arrête à sa fermeture. Journal : `journalctl --user -u dj-maquette -f` ; sorties de `e2.py` et `espion.mjs` dans `$XDG_RUNTIME_DIR/dj-maquette/`. Retirer : `outils/installer-maquette-auto.sh --retirer`.

**À la main** :

```bash
pactl load-module module-null-sink sink_name=dj_in        # note le numéro renvoyé
DJ_WORK=/tmp/essai python3 -I -u proto/e2/e2.py 60 &    # 60 s d'avance ; DJ_WORK active /run et les boutons
node --experimental-websocket proto/e2/espion.mjs &      # positions de Spotify pour l'écran et l'app
proto/e2/run.sh "<ws://…>" auto /tmp/essai <uri A> <uri B>   # ou C1…C8, R1, R2 pour forcer
python3 -I proto/e2/analyse.py /tmp/essai /tmp/essai/ordre-auto.json 60
```

`e2.py` ramène lui-même Spotify dans `dj_in` (toutes les 2 s). Le mode débogage de Spotify doit être ouvert (cf. [`../../docs/tests/methode.md`](../../docs/tests/methode.md)) et l'extension v2 installée. Les anciens noms (`montee`, `melange`…) sont refusés.

| Variable | Rôle |
|---|---|
| `DJ_WORK` | Dossier de travail des essais ; sans elle, `/run` répond 503 |
| `DJ_NOTES` | Journal des notes, défaut `docs/tests/notes-ecoute.jsonl` : **nouveau journal**, vide au départ, créé à la première note |
| `DJ_JOURNAL` | Rapports de transition en JSONL ; vide = coupé |
| `DJ_SLOW` | Ralenti de regain, 1,00 à 1,06, défaut 1,03 (ADR 0003) |
| `DJ_WS` | Adresse de débogage de Spotify si la recherche automatique échoue |

## Points d'entrée HTTP (`127.0.0.1:47802`)

Les POST n'acceptent que deux origines : l'écran local et `https://xpui.app.spotify.com`. Détail des champs : ADR 0001.

| Route | Rôle |
|---|---|
| `GET /state` | État, `derniere_transition` et `transitions_recentes` (10), chacune avec son `id` |
| `GET /dj-catalogue.js` | Catalogue d'affichage de l'extension, pour `ecran.html` |
| `POST /order` | Ordre v2 : 202, 400 (hors bornes, ancien `mode`), 409 (chevauchement, trop tard) |
| `POST /run` | `{transition: "auto"|C1…R2, a, b, name}` : lance `run.sh` ; l'ordre produit reçoit l'id `essai-<t_wall>` |
| `POST /rating` | `{id, note, etiquettes, commentaire}` : la transition est retrouvée par `id` parmi les 10 récentes, sans que l'écran connaisse son nom (écoute à l'aveugle) ; 409 si l'id est inconnu |

## Comportements

- **Avance** : une superposition de T mesures exige (2T + 2) × mesure de A + 8 s d'avance ; sinon repli. Les transitions sèches ne consomment rien, C4 en regagne.
- **Repli au rendu** : grille pas assez nette, calage > 20 ms, voix mesurée, B absent ou avance trop courte → transition suivante de l'échelle. Toute l'échelle refusée ou prête trop tard → **secours** (A en boucle sans graves, B qui monte filtré).
- **Pause** : le moteur se tait avec Spotify et retire le silence reçu avant la confirmation ; la reprise garde l'avance.
- **Morceau changé à la main** : l'extension envoie un ordre de rattrapage R1 (repli R2).
- **parec / pacat arrêtés** (PipeWire relancé) : relancés automatiquement.
- **Réglage** : `transitions/` est rechargé à chaque ordre s'il a changé ; seul un changement de `e2.py` demande de relancer (1 min de remplissage).

## Tests hors ligne

```bash
for t in proto/e2/test_*.py; do python3 -I $t; done
```

| Test | Vérifie |
|---|---|
| `test_primitives.py` | Courbes, EQ 3 bandes à somme plate, échange des basses, filtres, écho, journal des automations |
| `test_mesures.py` | Chaque mesure voit le défaut présenté et reste muette sur un rendu propre |
| `test_rendu.py` | Chaque rendu C1-C8, R1, R2, secours : raccords, calage, avance |
| `test_ordre.py` | Validation de l'ordre v2, échelle de repli au rendu, rapport |
| `test_voix.py` | Voix V3 sur synthèse, temps de calcul |
| `test_criteres.py` | Critères d'acceptation 9.1 ; écarts O5 connus affichés « ~ » (cf. spec, arbitrages) |

Chaque fichier finit par `RÉSULTAT : tout passe`. Dépendances : `numpy`, la commande `rubberband`.

## Ranger

1. Arrêter `e2.py` et son `pacat` **par numéro de processus** (cf. [`../../docs/pieges.md`](../../docs/pieges.md)).
2. `pactl unload-module <numéro>` : Spotify revient seul sur la sortie par défaut.

## Limites

- Python : des trous de lecture possibles pendant les calculs ; `pacat` à 200 ms de latence pour les absorber.
- Pas de gestion des pubs.
- Le changement de morceau d'un saut dans la playlist est placé à l'heure : précision de quelques dizaines de ms.
- Le port UDP n'accepte que `127.0.0.1` mais ne vérifie pas l'expéditeur.
