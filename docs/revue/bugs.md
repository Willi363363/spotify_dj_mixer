# Revue du code (2026-10-26)

Revue en lecture seule de `proto/e2/` et `spicetify/`, puis correctifs le même jour. ✅ = corrigé et couvert par `test_rendu.py` ou `node --check` ; 🔎 = corrigé, à confirmer en essai réel ; ⏳ = laissé, raison donnée.

## Bugs confirmés (du plus grave au moins grave)

| # | Bug | Effet | Correctif | Statut |
|---|---|---|---|---|
| 1 | **Mémoire non circulaire** (10 min) | À 600 s, fil de lecture mort, silence total (arrivé en vrai le 26/10) | Anneau, accès par `read(a, b)` | 🔎 |
| 2 | **L'avance fond à chaque transition** : les 4 mesures de B lancées en avance étaient sautées | Après 4-5 transitions, « prête trop tard », saut brut de Spotify | A prolongé par du synthétique pendant que B monte ; regain jusqu'à 4 mesures ; pas d'avance de B pour le mélange et le drop swap | ✅ |
| 3 | Mélange accepté puis abandonné sous ~100 BPM | Transition perdue | L'extension lit l'avance (`delay_s`) et n'autorise le mélange qu'au-delà de 16 mesures + 8 s ; avance cible 60 s | 🔎 |
| 4 | **Saut de volume aux bords** (normalisation globale) | A baisse d'un coup au début, remonte à la reprise | Limiteur qui vaut 1 aux deux bouts + raccords de 20 ms avec le flux | ✅ |
| 5 | **Clics dans les roulements** (`pitched` rebouclait) | Petits claquements | Lecture sans rebouclage | ✅ |
| 6 | Basses de A qui reviennent (`_brake` non filtré, `_spin` à 60 Hz) | Bosse de graves avant B | Filtrés à 300 Hz, après le ralenti | ✅ |
| 7 | Fil UDP mort sur un datagramme invalide | Plus d'ordres de `run.sh` | `try/except` + validation de l'ordre | ✅ |
| 8 | Segments qui se chevauchent | Passage rejoué | Refus d'un segment qui commence avant la reprise du précédent | ✅ |
| 9 | `switchAt` sans contrôle du morceau ni de la pause | Boucle sans fin, mode auto bloqué | Sortie si le morceau change ou si pause | ✅ |
| 10 | `sendOrder` ignorait la réponse | Un refus s'affichait « transition lancée » | Réponse lue, raison du refus affichée | ✅ |
| 11 | Uri insérées dans du JS exécuté dans Spotify | Injection possible (risque faible) | Format strict dans `e2.py` et `run.sh` | ✅ |
| 12 | `analyse.py` figé sur 20 s d'avance | Mesures fausses | Avance en paramètre | ✅ |

## Problèmes probables

| # | Problème | Correctif | Statut |
|---|---|---|---|
| B1 | `find_switch` lisait sans attendre le son reçu | Attente de +450 ms avant la recherche | ✅ |
| B2 | Filtres FFT circulaires, parfois après `edges` | Remplissage de zéros, filtre avant `edges` | ✅ |
| B3 | Coupures possibles avec `pacat` à 60 ms | 200 ms | 🔎 |
| B4 | Accès concurrents à `plan` / `current` | Verrou | ✅ |
| B5 | Un vrai blanc dans A près du saut peut tromper la détection | — | ⏳ rare, à croiser avec l'heure attendue si constaté |

## Faiblesses musicales

| Faiblesse | Statut |
|---|---|
| Drop de B non borné | ✅ cherché dans la première moitié |
| « Tonalités proches » sans distance | ✅ roue de Camelot, affichée dans la raison |
| B garde son tempo sous la montée | ✅ calé sur A puis glisse vers son tempo (double / moitié compris) |
| Écho d'atterrissage inaudible après frein / retour / filtre | ✅ pris sur le dernier temps réel de A |
| Énergie comparée à la section la plus forte de B | ✅ 4 mesures de chaque côté |
| Toujours la même forme | ✅ types + chaîne de Markov, drop swap ajouté |
| Fin de A non recalée sur la grosse caisse | ⏳ grille fiable (Beat This!) à venir |
| Mesures supposées à 4 temps | ⏳ |
| Pause et pubs non gérées | ⏳ |

## Seconde revue (même jour, après l'essai réel)

| # | Point | Correctif | Statut |
|---|---|---|---|
| R1 | Gain de B > 1 : drop écrêté | Gain borné par la crête de B ; flux baissé par bloc au lieu d'être rogné | ✅ |
| R2 | Ordre refusé ou abandonné après le saut = coupe sèche | Bornes vérifiées avant le saut ; **secours** d'un temps (fondu filtré) si la transition est prête trop tard ou échoue | 🔎 |
| R3 | Avance trop courte pour un style long après un mélange lent | Avance nécessaire calculée par style, relue juste avant le saut ; sinon montée courte | 🔎 |
| R4-5 | Fin de A pas sur ses temps (heure du saut ± dizaines de ms) | Fin de A recalée sur la phase de ses grosses caisses ; heure interpolée dans le bloc reçu | ✅ |
| R6 | Recalage temps par temps qui hachait frein, retour, écho | Prolongement étiré d'un seul tenant | ✅ |
| R7 | Tempos non calables : deux rythmes qui se contredisent | Montée de B réduite à 2 mesures, sans graves sous 400 Hz | ✅ |
| R8 | Drop de B 5 mesures après la fin de A au lieu de 4 | Tolérance d'un tiers de temps + trou du saut | ✅ |
| R9 | B lancé depuis 0:00 : drop mal placé, silence de tête pris pour le saut | Repli seulement sans avance ; silence de tête de B accepté comme son début | ✅ |
| R10 | Pause : muette si espion s'arrête, segment non suspendu | Pause confirmée par 2 messages, expire sans nouvelles ; suspendue aussi pendant une transition | 🔎 |
| R11 | Rattrapage situé au hasard ; uri remplacée par Spotify | Fenêtre donnée par espion ; saut reconnu à l'heure, pas à l'uri | 🔎 |
| R12 | Mode auto pendant un test manuel | Mode auto en veille tant qu'un test tourne | ✅ |
| R13 | Mesure de A prise sur une seule mesure, B déduit des tempos globaux | Moyenne de 4 mesures de A et de B, envoyées toutes deux | ✅ |
| R14 | Mélange jugé sur 2 mesures alors qu'il en superpose 8 | Zones de 8 mesures | ✅ |
| R15 | Écho : blanc au milieu d'un long prolongement | A ne s'efface que sous la montée de B | ✅ |
| R16 | Frein / retour sans effet sur un prolongement d'une mesure | Longueur de boucle bornée à 0 | ✅ |
| R17 | Aiguille de l'app décalée de ~5 mesures | Durée réelle de A envoyée (`real_s`) | ✅ |
| R18 | Refus d'un ancien module après rechargement non attrapé | Reconnu par son nom | ✅ |
| R19-20 | Docs en écart, tests manquants, code mort (`planning`) | Corrigés ; tests : crête après reprise, trous, avance trop grande étirée, secours, recalage de A | ✅ |

## Code mort et docs

Anciens préréglages (`coupe`, `retour`, `frein`, `boucle`, `echo`) retirés : leurs noms restent acceptés et renvoient aux styles doux. `transition.js` appelle `DJ.switchAt`. Docs mises à jour : `proto/e2/README.md`, `architecture.md`, `roadmap.md`, `spicetify/README.md`, `installer.sh`.
