# ADR 0001 · Contrat extension → moteur v2 (ordre, rapport, note)

Statut : accepté, 2026-10-28. Remplace le §10 de [`../specs/transitions-v2.md`](../specs/transitions-v2.md), qui renvoie ici.

## Contexte

L'ordre v1 (`mode` = préréglage de `recettes.py`, champs à plat `bar_s`, `pre_s`, `beatsA`…) ne porte ni les points de
sortie/entrée en mesures, ni la voix, ni l'échelle de repli. La spec propose un format à plat et demande au tech-lead de le
valider. Trois consommateurs : `e2.py` (backend-dev), l'écran (`dj-mixer/index.js`, `ecran.html`, ui-engineer) et les tests.

## Options

1. Garder le format à plat de la spec (`beatsA`, `beatsB`, `voix.a`…).
2. Regrouper ce qui concerne A et B dans deux objets `a` et `b` de même forme, plus un identifiant de transition.

## Décision

Option 2. Un seul format, en JSON, sur `POST /order` (HTTP, origine contrôlée comme aujourd'hui) et sur UDP 47801 (`run.sh`).
Les anciens noms (`montee`, `melange`, `drop_swap`…) et le champ `mode` sont **refusés** (400) : ils ne restent pas jouables à
la main. Le forçage d'une transition passe par les identifiants v2 (`/run` et `DJ.forcer`).

### Ordre

```json
{
  "v": 2,
  "id": "t-1730149451123-3",
  "transition": "C6",
  "choisie": "C7",
  "replis": ["C5", "R1", "R2"],
  "replis_plan": [{ "de": "C7", "vers": "C6", "raison": "avance 31 s < 44 s requises (8 mesures)", "ou": "plan" }],
  "bars": 4,
  "params": {},
  "t_wall": 1730149451123,
  "gapless": true,
  "manuel": false,
  "to_uri": null,
  "ratio": 1.018,
  "a": {
    "uri": "spotify:track:…", "duree_s": 201.3,
    "sortie_s": 176.42, "sortie_mesure": 88,
    "bar_s": 2.004, "beats": [-16.03, -15.53, "…", 1.98],
    "grille": "nette", "voix": [0.1, 0.0, "…"], "jamais_entendu_s": 18.7
  },
  "b": {
    "uri": "spotify:track:…", "duree_s": 188.0,
    "entree_s": 0.48, "entree_mesure": 0, "entree": "E0", "cible_s": 8.36,
    "bar_s": 1.97, "beats": [-1.97, "…", 9.8],
    "grille": "nette", "voix": [0.0, 0.0, "…"], "saute_s": 0.48
  },
  "voix_source": "segments",
  "raison": "court · g 1,8 % · k 1 · ΔE +0,4 dB · intro de B sans voix 6 mesures · poids C6 4,5 / C5 3 / C1 3"
}
```

| Champ | Sens | Bornes vérifiées par `e2.py` (sinon 400) |
|---|---|---|
| `v` | version du contrat | `2` exactement |
| `id` | identifiant donné par l'extension, repris dans le rapport et la note | `^[A-Za-z0-9_-]{1,40}$` |
| `transition` | ce que le moteur doit tenter en premier (après les replis décidés au plan) | `C1`…`C8`, `R1`, `R2` |
| `choisie` | le premier choix de la règle, avant tout repli (rapport : `transition_demandee`) | idem |
| `replis` | échelle restante, dans l'ordre (§8 de la spec) | 0 à 3 identifiants connus |
| `replis_plan` | replis déjà faits par l'extension | 0 à 3 objets `{de, vers, raison, ou: "plan"}` |
| `bars` | T = recouvrement en mesures | C1-C4 et R2 : 0 ; R1 : 1 ; C5 : 2 ; C6 : 4 ; C7 : 8 ou 16 ; C8 : 4 ou 8 |
| `params` | réglages propres à une transition, défauts de la spec si absents | C2 `{queue_mesures: 2..4}` ; C3 `{frein_temps: 1|2}` ; autres : `{}` |
| `t_wall` | heure (ms, horloge murale) de l'ordre de saut donné à Spotify | > 0, ni plus de 30 s dans le passé ni dans le futur |
| `gapless`, `manuel`, `to_uri` | inchangés depuis la v1 (repérage du changement, `find_switch`) | `to_uri` au format `spotify:track:` si `manuel` |
| `ratio` | tempo A / tempo B (global) | 0,3 à 3 |
| `a.sortie_s` | position de A (s) où Spotify saute = sortieA. Pour un recouvrement, A joue [sortieA − T ; sortieA] | ≥ 0, ou `null` si `manuel` |
| `a.sortie_mesure` | index dans `analysis.bars` de la mesure qui **commence** à sortieA | entier ≥ 0 ou `null` |
| `b.entree_s`, `b.entree_mesure` | position de B où Spotify reprend = entreeB, et son index de mesure | idem |
| `b.entree` | type d'entrée (§5.6) | `E0`, `E1`, `E2` |
| `b.cible_s` | entreeB + T mesures (début de section visé) ; = `entree_s` si T = 0 | ≥ `entree_s` |
| `*.bar_s` | durée médiane d'une mesure au bord | 0,3 à 5 |
| `*.beats` | temps de Spotify (s) **relatifs** au point (sortieA pour A, entreeB pour B). A couvre [−T − 1 ; +1] mesures, B [−1 ; T + 2] | 8 à 120 valeurs dans ]−60 ; 60[, ou `[]` (pas de grille) |
| `*.grille` | confiance de grille au bord (§5.2) | `nette`, `moyenne`, `floue` |
| `a.voix` / `b.voix` | voix par mesure, A : les 16 mesures **avant** sortieA (la dernière en dernier) ; B : les 16 **après** entreeB | ≤ 16 valeurs dans [0 ; 1] |
| `voix_source` | d'où viennent ces valeurs (ADR 0002) | `paroles`, `segments`, `aucune` |
| `a.jamais_entendu_s`, `b.saute_s` | pour O1 et le quota E2 (journal seulement) | ≥ 0 |
| `raison` | texte pour l'écran | ≤ 300 caractères |

Le moteur ne recalcule rien du plan : il repère le saut (`find_switch`), recale sur les grilles (`grid_lag`), essaie
`transition` puis `replis` et rend compte. Il ne vérifie pas que l'échelle est « la bonne » : c'est le rôle de l'extension.

**Ordre de rattrapage** (morceau changé à la main) : `transition: "R1"`, `replis: ["R2"]`, `manuel: true`, `to_uri`,
`a.sortie_s: null`, `b.entree_s: 0`, `b.entree: "E0"`, grilles et voix vides.

### Réponses de `POST /order`

- `202 {"ok": true, "id": "…"}` ;
- `400 {"message"}` : champ manquant ou hors bornes, transition inconnue, ancien `mode` ;
- `403` : origine refusée ;
- `409 {"message"}` : une transition chevauche déjà ce moment, ou ordre trop tard (la lecture a dépassé le saut).

### Rapport dans `GET /state`

Deux nouvelles clés : `derniere_transition` (objet ci-dessous) et `transitions_recentes` (les 10 dernières, la plus récente
d'abord). Le même objet est ajouté en une ligne au journal `DJ_JOURNAL` (fichier JSONL, désactivé si la variable est vide ;
jamais commité).

```json
{
  "id": "t-1730149451123-3", "t": "2026-10-28 21:04:11",
  "a": { "uri": "…", "nom": "…", "sortie_s": 176.42, "jamais_entendu_s": 18.7 },
  "b": { "uri": "…", "nom": "…", "entree_s": 0.48, "entree": "E0", "saute_s": 0.48 },
  "transition_demandee": "C7",
  "transition_jouee": "C5",
  "issue": "jouee",
  "replis": [
    { "de": "C7", "vers": "C6", "raison": "avance 31 s < 44 s requises (8 mesures)", "ou": "plan" },
    { "de": "C6", "vers": "C5", "raison": "voix mesurée sur 3 mesures de l'intro de B", "ou": "rendu" }
  ],
  "mesures": { "calage_ms": 4.0, "nettete": 3.1, "basses_ms": 31, "echange_ms": 3, "voix_mesures": 1,
               "sonie_db": [-1.2, 0.8], "crete_dbfs": -0.6 },
  "avance_avant_s": 58.3, "avance_apres_s": 54.2,
  "rendu_s": 1.7, "marge_s": 9.4,
  "ralenti": 1.03,
  "raison": "…"
}
```

- `issue` : `jouee`, `secours` (transition prête trop tard ou toute l'échelle refusée : `transition_jouee: "secours"`) ou
  `abandon` (`transition_jouee: null`). O6 se calcule sur ce champ.
- `mesures` : valeurs `null` quand elles ne s'appliquent pas (pas de recouvrement : `calage_ms`, `nettete`, `voix_mesures`).
  Seules les mesures rapides (calage, basses, échange, voix, sonie, crête) tournent en production ; trous et clics ne
  tournent que dans les tests (`mesures.rapport(..., complet=True)`).
- `marge_s` : temps entre la fin du rendu et le début du segment (critère 9.1-12 : ≥ 2 s).
- Les clés `next`, `current`, `last` gardent leur forme, mais `mode`, `label`, `ingredients`, `phases`, `b_from` sont
  remplacés par `transition` (identifiant) et `id`. Libellés, couleurs et étapes de frise viennent de
  `spicetify/dj-catalogue.js` (ADR 0005), servi aussi par `e2.py` sur `GET /dj-catalogue.js` pour `ecran.html`.
- `notes` devient la moyenne par identifiant de transition jouée (affichage seulement, H8).

### `POST /rating`

```json
{ "id": "t-1730149451123-3", "note": 4, "etiquettes": ["trop_court"], "commentaire": "" }
```

- `etiquettes` ⊂ `rythme_decroche`, `basses_doublees`, `voix_superposees`, `fin_coupee`, `mauvais_endroit`, `trop_long`,
  `trop_court`, `saut_volume`, `clic_trou`, `effet_de_trop`.
- Le moteur retrouve la transition par `id` parmi les 10 récentes : l'écran n'a pas besoin de connaître le nom (écoute à
  l'aveugle). `id` inconnu : `409`. Note hors 1-5, étiquette inconnue : `400`.
- Ligne ajoutée à `DJ_NOTES` (défaut `docs/tests/notes-ecoute.jsonl`, qui repart vide) : la note, les étiquettes, le
  commentaire **et** le rapport complet (paire, transition demandée et jouée, replis, mesures, entrée, ralenti).

### `POST /run` (écran, `DJ_WORK`)

`{"transition": "auto|C1…C8|R1|R2", "a": "spotify:track:…", "b": "spotify:track:…", "name": "…"}`. L'ancien champ `mode` est
refusé.

### Retiré

`POST /double` (refrain doublé) et le champ `pre_s` : en v2, B n'est jamais lancé avant entreeB, le recouvrement se fait avec
les T dernières mesures de A déjà en mémoire.

## Conséquences

- `e2.py`, `dj-auto.js`, `transition.js`, `run.sh`, `index.js` et `ecran.html` changent tous de contrat d'un coup : la branche
  n'est pas jouable entre la tâche 5a et la tâche 12. Accepté (branche de fonctionnalité).
- La validation vit dans `proto/e2/transitions/contrat.py` (`valider_ordre`), testable sans le moteur.
- Le moteur reste bête sur le plan : toute la règle de choix est côté extension, testable en `node --test`.
