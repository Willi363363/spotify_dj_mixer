# ADR 0005 · Découpage en modules et propriété des fichiers

Statut : accepté, 2026-10-28.

## Contexte

Aujourd'hui tout le rendu tient dans `rendu.py` (600 lignes) et toute la décision dans `dj-auto.js` (470 lignes). Trois rôles
doivent travailler en parallèle (backend-dev, data-ml-engineer, ui-engineer) sans écrire dans les mêmes fichiers, et la
logique de décision doit se tester hors de Spotify (`node --test`), le rendu hors de PipeWire.

## Options

- **Python** : (a) garder `recettes.py` + `rendu.py` et les agrandir ; (b) un paquet `proto/e2/transitions/` avec un module
  par responsabilité.
- **Extension** : (a) un seul `dj-auto.js` ; (b) une étape de construction (bundler) ; (c) plusieurs fichiers d'extension
  Spicetify, chargés dans l'ordre, qui s'enregistrent sur `globalThis.DJCore` et exportent aussi en CommonJS pour Node.

## Décision

Python (b) et extension (c). Aucune dépendance nouvelle : Node 20 a `node:test`, Spicetify charge plusieurs extensions.

### Arborescence

```
proto/e2/
  e2.py                      moteur : mémoire, repérage, ordre v2, échelle au rendu, rapport, /state, /rating, /run
  synthese.py                morceaux de synthèse pour les tests (grille, basse, voix factice)
  transitions/
    __init__.py              vide (rechargement à chaud plus simple)
    contrat.py               Ordre, Place, Rendu, Automation, valider_ordre
    outils.py                outils gardés (ADR 0004)
    calage.py                grid_lag, grid_end, grid_fit, caler_superposition
    primitives.py            EQ 3 bandes, courbes nommées, échange des basses, filtre balayé, écho calé (ADR 0006)
    seches.py                C1, C2, C3, R2
    boucle.py                C4, secours
    superposees.py           C5, C6, C7, C8, R1
    catalogue.py             FICHES (id → rendu, T permis, exigences) et rendre() = échelle de repli au rendu
    mesures.py               critères 9.1 n° 1 à 7 sur le son rendu
    voix.py                  V3 (ADR 0002)
  test_rendu.py, test_primitives.py, test_mesures.py, test_voix.py, test_ordre.py, test_criteres.py
spicetify/
  dj-catalogue.js            libellés, familles, couleurs, étapes de frise (UI)
  dj-voix.js                 voix par mesure : segments (V2), paroles (V1 derrière drapeau)
  dj-placement.js            §5 : phrases, grille, sections, sorties, entrées E0/E1/E2, ΔE, profil
  dj-choix.js                §7-§8 : règles par transition, éligibilité, poids, variété, tirage, repli au plan, ordre v2
  dj-auto.js                 orchestration : tick, saut, envoi, rattrapage, window.DJ
  dj-mixer/index.js          app « Mode DJ »
  installer.sh
  test/  placement.test.mjs, voix.test.mjs, choix.test.mjs, simulation.test.mjs, fixtures/
```

### Forme d'un module partagé de l'extension

```js
// spicetify/dj-placement.js
(function (racine) {
  const api = { /* fonctions pures */ };
  if (typeof module === 'object' && module.exports) module.exports = api;   // node --test
  else (racine.DJCore ??= {}).placement = api;                              // Spotify
})(globalThis);
```

Les dépendances entre modules se résolvent **à l'appel** (`DJCore.voix` ou `require('./dj-voix.js')`), jamais au
chargement : l'ordre des extensions n'est pas garanti. `dj-auto.js` attend que `DJCore.catalogue`, `voix`, `placement` et
`choix` existent, comme il attend déjà Spicetify. `installer.sh` lie et inscrit les cinq fichiers. Aucun appel à `Spicetify`
dans `dj-placement.js` et `dj-choix.js` ; dans `dj-voix.js`, seulement dans `chargerParoles`.

### Contrats Python (dans `transitions/contrat.py`)

```python
@dataclass(frozen=True)
class Ordre:                    # ordre v2 validé (ADR 0001), champs a/b en sous-objets Bord
    id: str; transition: str; choisie: str; replis: tuple[str, ...]; replis_plan: tuple[dict, ...]
    bars: int; params: dict; t_wall: float; gapless: bool; manuel: bool; to_uri: str | None
    ratio: float; a: "Bord"; b: "Bord"; voix_source: str; raison: str

def valider_ordre(d: dict) -> Ordre: ...        # lève OrdreInvalide(message) -> 400

@dataclass
class Place:                    # où sont A et B dans la mémoire, calculé par e2.py avant tout rendu
    fin_a: int; debut_b: int    # échantillons, recalés sur la grille (grid_lag) ou sur les temps (grid_end)
    bar_a: int; bar_b: int      # échantillons par mesure
    beats_a: np.ndarray | None  # temps de Spotify en échantillons absolus de la mémoire, None sans grille
    beats_b: np.ndarray | None
    nettete_a: float; nettete_b: float
    extra: int                  # avance à regagner (> 0) ou à rendre (< 0), en échantillons

Automation = namedtuple("Automation", "piste param t valeur")
# piste : "a" | "b" | "effet" ; param : "volume" | "graves" | "mediums" | "aigus" | "passe_bas_hz" | "passe_haut_hz"
#         | "vitesse" ; t : échantillon dans le segment ; valeur : gain linéaire, Hz ou vitesse. Au moins une par temps.

@dataclass
class Rendu:
    debut: int                  # échantillon de la mémoire où le segment remplace le flux
    seg: np.ndarray             # (n, CH) float32, après limiteur et raccords (outils.finir)
    reprise: int                # échantillon de la mémoire où le flux reprend
    gain: float                 # gain de B à la reprise (revient à 1 en GAIN_S)
    transition: str             # identifiant réellement rendu
    pistes: dict                # "a", "b" (et "effet") avant somme, même longueur que seg
    reperes: np.ndarray         # temps de la grille commune dans seg (échantillons)
    uns: np.ndarray             # premiers temps de mesure dans seg
    automations: list           # [Automation]
    infos: dict                 # calage_ms, nettete… (repris dans le rapport)
```

Signature commune des rendus (`seches.py`, `boucle.py`, `superposees.py`) :

```python
def c5(m, o: Ordre, p: Place) -> Rendu: ...     # m : mémoire (m.read, m.wait, m.log) ; lève outils.Refus(raison)
```

Échelle au rendu (`catalogue.py`) :

```python
FICHES: dict[str, Fiche]        # Fiche(rendu, bars_permis, famille, exige) ; exige ⊂ {"grille", "voix_boucle",
                                #   "voix_intro_b", "voix_superposees"}
def rendre(m, o: Ordre, p: Place, *, avance: int) -> tuple[Rendu, list[dict]]:
    """Essaie o.transition puis o.replis. Passe au suivant sur Refus, netteté < 1,5 pour une superposition, calage
    > 20 ms après correction, voix au-delà des seuils (ADR 0002), avance < (2T + 2) × mesure + 8 s. Rend le rendu et les
    replis [{de, vers, raison, ou: "rendu"}]. Lève Refus si toute l'échelle échoue (e2.py joue alors le secours)."""
```

Voix au rendu (`voix.py`) et mesures (`mesures.py`) :

```python
SEUIL_REPLI_RENDU = 0.6
def voix_par_mesure(x: np.ndarray, bornes: np.ndarray) -> np.ndarray:
    """x : (n, CH) float32 ; bornes : k + 1 débuts de mesure (échantillons relatifs à x). Rend k scores dans [0, 1]."""

def calage(pa, pb, reperes) -> tuple[float, float]       # écart B − A (ms), netteté la plus faible
def basses(pa, pb, beat: int) -> float                    # ms où les graves < 150 Hz de A et B dépassent −12 dB du max commun
def echange(pa, pb, uns) -> float                         # ms entre le milieu de la rampe des graves et le 1 le plus proche
def trous(x, silences=()) -> list[tuple[int, float]]      # (début, durée ms) des quasi-zéros > 20 ms
def clics(x, bornes) -> list[int]
def sonie(x, ref_avant, ref_apres) -> tuple[float, float] # min et max de la sonie 3 s relative (dB), O5
def crete_dbfs(x) -> float
def courbes(automations, attendu, tol_db=1.0, tol_f=0.1) -> list[str]   # écarts au §4, vide si conforme
def rapport(r: Rendu, p: Place, *, complet=False) -> dict                 # le dict "mesures" de l'ADR 0001
```

### Contrats de l'extension

```js
// DJCore.voix (dj-voix.js)
voixSegments(analyse, t0, nMesures, sens /* 'avant' | 'apres' */) -> number[]
parserParoles(json) -> [{ debut_s, fin_s, vide }] | null
voixParoles(lignes, mesures) -> number[]
chargerParoles(uri) -> Promise<lignes | null>                 // seul appel réseau ; drapeau dj-mixer:paroles
voixBord(analyse, lignes | null, t0, nMesures, sens) -> { valeurs, source }
SEUIL_VOCAL = 0.5, SEUIL_SANS_VOIX = 0.3

// DJCore.placement (dj-placement.js)
mesures(analyse) -> [{ i, start, duration, confidence, section, k, phrase /* 8 | 4 | 0 */ }]
grille(analyse, t, n = 16) -> 'nette' | 'moyenne' | 'floue'
sectionsA(analyse) -> { dernierePleine, outro_s }
sorties(analyse, { minExit_s, T, voixA }) -> [{ t, mesure, jamais_entendu_s }]   // garde-fou O1 appliqué
entrees(analyse, { T }) -> { E0, E1, E2 }                                       // { t, mesure, cible_s, saute_s, part }
deltaE(a, sortie_s, b, cible_s) -> number
profilBord(voix) -> 'instrumental' | 'vocal' ; profilPaire(bordA, bordB, tempo) -> 'court' | 'long'
camelot, camelotDist, tempoGap
paire(a, b, { minExit_s, avance_s, contexte, voixA, voixB }) -> Paire          // caractéristiques §7.2

// DJCore.choix (dj-choix.js)
REGLES  // { C1: { famille, recouvrement, avance, replis, poids: { court, long }, quota, eligible(paire, pts) }, … }
QUOTA_E2
rng(graine) -> () => number
choisir(paire, historique, { rng, force }) -> { transition, choisie, replis, points, poids, raison } | { erreur }
replierAuPlan(choix, { avance_s, grille }) -> choix                              // §8 côté extension, ajoute replis_plan
ordre(choix, paire, { t_wall, gapless, manuel, to_uri, id }) -> objet v2 (ADR 0001)

// DJCore.catalogue (dj-catalogue.js)
CATALOGUE  // { C1: { nom, famille, couleur, description, phases: [[libellé, début, fin], …] }, …, R1, R2, R3, secours }

// window.DJ (dj-auto.js), lu par dj-mixer/index.js et transition.js
{ version: 2, status: { enabled, text, plan, historique, log }, planTransition(A, B, { force, minExit_s, graine }),
  switchAt, sendOrder, forcer(id | null), setAuto(on) }
```

### Propriété des fichiers

Un fichier = un seul rôle qui l'écrit. Les autres le lisent et demandent un changement au propriétaire.

| Rôle | Fichiers possédés |
|---|---|
| backend-dev | `proto/e2/e2.py`, `proto/e2/synthese.py`, `proto/e2/transitions/{__init__,contrat,outils,calage,primitives,seches,boucle,superposees,catalogue,mesures}.py`, `proto/e2/test_{rendu,primitives,mesures,ordre}.py` ; suppression de `rendu.py` et `recettes.py` |
| data-ml-engineer | `proto/e2/transitions/voix.py`, `proto/e2/test_voix.py`, `spicetify/{dj-voix,dj-placement,dj-choix,dj-auto}.js`, `spicetify/installer.sh`, `spicetify/test/{placement,voix,choix}.test.mjs`, `spicetify/test/fixtures/`, `proto/e2/transition.js`, `proto/e2/run.sh` |
| ui-engineer | `spicetify/dj-catalogue.js`, `spicetify/dj-mixer/index.js`, `proto/e2/ecran.html` |
| ux-designer | `docs/specs/transitions-v2-ecran.md` |
| test-writer | `proto/e2/test_criteres.py`, `spicetify/test/simulation.test.mjs` |
| tech-lead | `docs/adr/`, `docs/architecture.md`, §6, §10, §12, §13 de la spec |

Exception tolérée : `test_rendu.py` peut recevoir des cas du test-writer après la tâche 12, quand backend-dev a fini.

## Conséquences

- Chaque rendu se teste seul (`Mem` de `synthese.py`, `Ordre` et `Place` construits à la main), sans `e2.py`.
- Le rechargement à chaud (`fresh()`) surveille tous les `transitions/*.py` et les recharge dans l'ordre
  `outils, contrat, calage, primitives, voix, mesures, seches, boucle, superposees, catalogue`, hors place, puis bascule
  d'un coup comme aujourd'hui.
- Les identifiants existent en trois endroits (`catalogue.py`, `dj-choix.js`, `dj-catalogue.js`). Le test-writer ajoute
  un test de cohérence (Node lit `dj-catalogue.js` et `dj-choix.js`, Python lit `catalogue.FICHES` ; mêmes identifiants,
  mêmes T permis).
- `e2.py` sert `spicetify/dj-catalogue.js` sur `GET /dj-catalogue.js` (lecture seule, type `text/javascript`) pour
  `ecran.html`.
