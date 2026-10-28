# ADR 0004 · Ce qu'on garde et ce qu'on retire de l'ancien code

Statut : accepté, 2026-10-28.

## Contexte

La spec refait le catalogue, les courbes, le placement, le choix, le repli et la voix, et garde l'infrastructure prouvée
(tests 01-08 et 10). Il faut dire précisément quelles fonctions survivent, où elles vont (ADR 0005), et ce qui disparaît,
pour qu'aucun développeur ne reconstruise un ancien style par habitude. Les anciennes notes d'écoute et `docs/gouts.md` ont
été supprimés volontairement : on ne les reconstitue pas depuis git, et les commentaires de code qui les citent sont
retirés avec le code qu'ils justifient.

## Décision

### Gardé tel quel (déplacé si indiqué)

| Élément | Fichier actuel | Destination |
|---|---|---|
| Mémoire circulaire, lecteur, `Sortie`/pacat, routage PipeWire, pause, `find_switch`, `_manual_window`, `cancel_after`, `schedule`, `secours` en cas de retard, `slower` | `e2.py` | `e2.py` (sauf `secours` → `transitions/boucle.py`) |
| Calage sur la grille : `grid_lag`, `grid_end`, `_grid_fit`, `_flux`, `_beat_phase` | `rendu.py` | `transitions/calage.py` (noms publics : `grid_lag`, `grid_end`, `grid_fit`) |
| Boucle de correction du calage (mesurer, relire B décalé, remesurer) et étirement glissant A → B (`dout`, `dst`, `stretch_map`) | dans `melange` | extraits en `calage.caler_superposition` (tâche 9) |
| Outils : `ramp`, `smooth`, `band`, `sweep`, `edges`, `level`, `limiter`, `_rubberband`, `stretch_map`, `kick_env`, `Refus`, `SR`, `CH` | `recettes.py` | `transitions/outils.py` |
| `_fit`, `_loop`, `_resample`, `_percussive`, `_brake`, `_unit`, `_gain`, `_finish` | `rendu.py` | `transitions/outils.py` (noms sans `_` : appelés d'un autre module) |
| Morceaux de synthèse `track`, `Mem` | `test_rendu.py` | `proto/e2/synthese.py` |
| Avance d'un saut (`LEAD`), `switchAt`, `sendOrder`, `readState`, rattrapage sur `songchange`, `chooseNext`/`loadPool`/`GENRE_REFS` (hors périmètre, H7), `camelot`, `camelotDist`, `tempoGap`, `phrased` | `dj-auto.js` | `dj-auto.js` ; `camelot*`, `tempoGap`, `phrased` → `dj-placement.js` |
| Cercles, visualiseur, interrupteur, file à venir | `dj-mixer/index.js` | inchangés |

### Retiré

| Élément | Raison |
|---|---|
| `PRESETS`, `ALIASES`, `PHASES` de `recettes.py` | remplacés par le catalogue v2 (C1-C8, R1, R2) |
| Rendus `montee`, `montee_courte`, `echo_doux`, `retour_doux`, `frein_doux`, `filtre`, `drop_swap`, `melange`, `_douce`, `_stages`, `_spin`, `_hp_rise`, `_wash`, `_phrase`, `pitched`, `entry_kick`, `kick_agreement` | styles v1 : B lancé 8 mesures avant son drop sous du synthétique, à l'opposé du catalogue v2. Le calage du `melange` est extrait avant suppression |
| Refrain doublé : `POST /double`, `double()`, `track_sample`, `maybeDouble`, `status.double` | hors catalogue v2 ; le regain passe par le ralenti et C4 |
| Champ `pre_s`, `PRE_BARS`, `REAL_BARS`, `needS`, `shortPre` | B n'est plus lancé avant entreeB ; l'avance requise vient de la règle (2T + 2) × mesure de A + 8 s (spec §14) |
| `MARKOV`, `TYPES`, `typeOf`, `sample`, la recherche de sortie par ressemblance de timbre (`exitFor`, `zone`, `dist`) | remplacés par la règle de choix §7 et le placement §5 |
| `note_averages` comme poids de choix (`notes` passé à `planTransition`) | H8 : les notes ne règlent rien automatiquement en v1 ; moyenne gardée pour l'affichage |
| Ancien `mode` dans `/order`, `/run`, `run.sh` (`dernier-mode`) | contrat v2 (ADR 0001) |
| `rendu.py` et `recettes.py` | vidés par le déménagement (tâche 5a), puis supprimés |
| `fresh()` sur deux fichiers | réécrit pour recharger le paquet `transitions/` (ADR 0005) |

## Conséquences

- La tâche 5a (backend-dev) fait le déménagement **sans changer le comportement des outils gardés**, puis supprime les
  anciens rendus. `test_rendu.py` garde ses vérifications de raccords et de calage, réécrites sur les outils déplacés.
- Les anciens libellés disparaissent de l'écran ; le sélecteur de transition liste C1-C8, R1, R2 (tâche 14).
