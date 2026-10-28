# Spec : transitions v2

Statut : proposition du 2026-10-28, validée par le tech-lead le même jour (décisions : [`../adr/`](../adr/README.md)). Elle remplace toutes les décisions de transition de
[`../roadmap.md`](../roadmap.md) et les préréglages de `proto/e2/recettes.py`. Sources : [`../recherche/README.md`](../recherche/README.md).

## 1. Objectif

En une phrase : **chaque morceau enchaîne sur le suivant comme le ferait un DJ du genre**, sans amputer la fin de A, sans
basses ni voix superposées, calé sur le temps, avec une transition choisie automatiquement dans un petit catalogue varié et une
échelle de repli quand les conditions ne sont pas réunies.

### Ce qu'on garde (infrastructure prouvée, tests 01-08 et 10)

- Moteur `proto/e2/e2.py` : mémoire circulaire, lecture avec avance (~60 s), ordres HTTP `/order`, état `/state`, notes
  `/rating`, pause, rattrapage d'un changement manuel, routage PipeWire, ralenti de regain (`slower`).
- Saut de Spotify pile sur le temps (`switchAt`, `LEAD`), repérage du changement dans le flux (`find_switch`).
- **Calage sur la grille de beats de Spotify** (`grid_lag`, puis correction `_grid_fit`), 0 à 10 ms (test 10).
- Outils de traitement de `recettes.py` (`band`, `sweep`, `edges`, `limiter`, `level`, `stretch_map`, `_rubberband`) et de
  `rendu.py` (`_finish`, `_loop`, `_brake`, `_unit`, `_gain`, `secours`).

### Ce qu'on refait

Le catalogue, les courbes, le placement des points, la règle de choix, l'échelle de repli et la gestion des voix.

### Objectifs mesurables

| # | Objectif | Seuil | Mesure |
|---|---|---|---|
| O1 | Fin de A respectée | Partie de A jamais entendue ≤ 30 s **et** ≤ 15 % de A, sur 100 % des transitions ; dernière section « pleine » de A entendue en entier sur ≥ 90 % | Plan (positions) |
| O2 | Calage | Écart B − A ≤ 20 ms sur ≥ 95 % des superpositions, sinon repli | Son rendu (`_grid_fit`) |
| O3 | Une seule basse | Recouvrement des graves de A et B ≤ 1 temps | Signaux rendus avant somme |
| O4 | Voix | Voix superposées ≤ 2 mesures sur ≥ 95 % des transitions | Détecteur de voix retenu (§6) |
| O5 | Niveau | Sonie court terme (3 s) dans [−3 ; +2] dB de la moyenne entre A avant et B après ; crête ≤ −0,3 dBFS | Son rendu |
| O6 | Fiabilité | ≥ 95 % des transitions prévues jouées sans secours ni abandon, sur une séance d'1 h | Journal de `e2.py` |
| O7 | Variété | Sur 10 transitions de suite : ≥ 4 transitions différentes, aucune > 40 %, jamais deux fois de suite la même | Simulation à blanc |
| O8 | Écoute | Note moyenne ≥ 3,5/5 au protocole (§9) ; aucune transition < 3,0 ; étiquettes « fin coupée » ou « mauvais endroit » sur ≤ 10 % des écoutes | Notes du développeur |

## 2. Hypothèses

- **H1** La bibliothèque est surtout du rap FR, du shatta et du bouyon (cf. `GENRE_REFS`) : genres vocaux, en radio edit, mixés
  **courts** par les DJ. Le profil par défaut est donc « court ». Le profil « long » ne sert que si les deux bords sont
  instrumentaux.
- **H2** L'extension n'a pas accès au genre d'un artiste (commentaire de `dj-auto.js`). Le profil se déduit donc de la
  **structure** : longueur des bords sans voix, tempo.
- **H3** Le son de B n'existe en mémoire qu'**après** le saut de Spotify. Toute décision prise sur le son de B (voix, pulsation)
  ne peut que **dégrader** la transition au rendu, pas la choisir. Le plan se fait sur l'analyse Spotify, et peut-être sur les
  paroles (§6).
- **H4** Superposer T mesures consomme T mesures d'avance. Le ralenti de regain (×1,06) ne rend que ~0,5 s par 8 s de musique.
  Un mélange de 8 mesures par morceau n'est pas soutenable : la majorité des transitions doit être **sans recouvrement** ou
  courte. Cela colle à H1.
- **H5** Pas de transposition. Le tempo ne bouge que pendant un recouvrement : glissement de A vers B comme le `melange`
  actuel, borné à 6 %, hauteur conservée.
- **H6** Les seuils (confiance de grille, ΔE, poids de choix) sont des valeurs de départ. Ils se calibrent avec le protocole
  d'écoute et la simulation à blanc.
- **H7** Le choix du morceau suivant (`chooseNext`) n'entre pas dans cette spec. La règle doit marcher pour n'importe quelle
  paire, file manuelle comprise.
- **H8** Les anciennes notes d'écoute ne servent pas. Le journal repart vide. En v1, les notes ne règlent **pas**
  automatiquement les poids : on les ajuste à la main après le protocole.

## 3. Vocabulaire et primitives communes

- **Mesure** = 4 temps de l'analyse Spotify (`bars`). **Phrase** = 8 mesures depuis un début de section, à défaut 4. Le « 1 »
  est le premier temps d'une mesure. Les mesures de la transition se numérotent m1…mT. « Au 1 de m3 » = premier temps de la
  3ᵉ mesure.
- **sortieA** = fin de la partie réelle de A utilisée (instant du saut de Spotify). **entreeB** = position de B où Spotify
  reprend. Pour un recouvrement de T mesures, A joue [sortieA − T ; sortieA] sous B [entreeB ; entreeB + T], et
  **entreeB + T tombe sur un début de section de B** (« lancer B une phrase avant le point d'échange »).
- **EQ 3 bandes** par morceau : graves < 200 Hz, médiums 200 Hz à 4 kHz (zone des voix), aigus > 4 kHz. Filtres
  Linkwitz-Riley d'ordre 4, dont la somme est plate. Gains automatisés sans clic (lissage ≥ 5 ms). « Coupé » = gain 0.
- **Courbes nommées** (brevet Spotify) : `lin`, `cos` (puissance constante : A = cos(πt/2), B = sin(πt/2)), `carre`
  (marche avec une rampe anti-clic de 10 ms).
- **Échange des basses** : graves de A 1→0 et de B 0→1 sur une rampe de 30 ms qui **finit sur un 1**. C'est le seul moment
  où les deux graves coexistent (≤ 1 temps, O3).
- **Filtre balayé** : passe-bas ou passe-haut biquad (pente 12 dB/oct), fréquence de coupure en progression exponentielle.
- **Tempo** : pendant un recouvrement, B est étiré vers le tempo de A puis glisse temps par temps vers le sien (`stretch_map`,
  méthode du `melange` actuel). Hors recouvrement, aucun étirement.
- **Niveau** : B est ramené au niveau de A (`_gain`, baisse seulement, ≥ 0,8) puis revient à 1 en 16 s ; limiteur en sortie.

## 4. Catalogue v1

Huit transitions, toutes faisables sans stems avec le moteur actuel. Avance consommée : « 0 » = aucun recouvrement de son réel.

| Id | Nom affiché | Recouvrement | Avance | Famille |
|---|---|---|---|---|
| C1 | Coupe sur phrase | 0 | 0 | sec |
| C2 | Écho | 0 (queue synthétique) | 0 | sec |
| C3 | Frein | 0 | 0 | effet |
| C4 | Montée en boucle | 0 (A prolongé) | **regagne** 2 mesures | effet |
| C5 | Fondu calé | 2 mesures | 2 mesures | superposé |
| C6 | Mix 3 bandes (radio edit) | 4 mesures | 4 mesures | superposé |
| C7 | Échange de basses | 8 mesures (16 si deux bords instrumentaux) | 8 ou 16 | superposé |
| C8 | Montée filtrée | 4 ou 8 mesures | 4 ou 8 | superposé |

### C1 · Coupe sur phrase
- **Points** : sortieA = 1 d'un début de phrase, juste après une phrase vocale terminée (voix de A faible sur le dernier
  temps). entreeB = 1 d'un début de section : début musical (E0), fin de l'intro (E1) ou refrain (E2), cf. §5.
- **Courbes** : A 1→0 sur 10 ms qui finissent au 1 ; B 0→1 sur 5 ms à partir du 1. EQ et filtre : aucun.
- **Basses** : pas de coexistence.
- **Usage** : tempos incompatibles (> 6 %, rapport 3:2 shatta ↔ bouyon), tonalités qui se heurtent, énergie qui monte (entrée
  sur E2), profil court. Exige une grille au moins « moyenne » des deux côtés.

### C2 · Écho
- **Points** : sortieA = 1 d'un début de phrase. entreeB = E0 ou E1.
- **Courbes** : le dernier temps de A (temps 4 de la dernière mesure) est envoyé dans un écho de ½ temps (tempo de A),
  rétroaction 0,5 (−6 dB par répétition). L'écho passe par un passe-haut à 300 Hz et un passe-bas qui descend de 8 kHz à
  2 kHz. A sec 1→0 sur 10 ms au 1. La queue s'éteint en `lin` sur 2 mesures de B, au plus 4. B entre sec et plein au 1.
- **Basses** : l'écho n'en a pas, donc l'échange se fait au 1.
- **Usage** : A finit sur une voix (l'écho prolonge la phrase au lieu de la couper), tempo ou tonalité incompatibles, énergie
  stable ou qui baisse. Pas deux C2 sur 3 transitions.

### C3 · Frein
- **Points** : sortieA = 1 d'un début de phrase. entreeB = E1 ou E2.
- **Courbes** : sur le dernier temps de A, la vitesse passe de 1 à 0 en courbe exponentielle sur 1 temps (2 temps si le tempo
  est < 90 BPM). Hauteur non conservée : c'est l'effet voulu. Passe-bas de 16 kHz à 500 Hz pendant le frein. B sec et plein
  au 1.
- **Usage** : profil court (signature dancehall/shatta), contraste ou énergie qui monte. **Au plus 1 transition sur 6**,
  jamais deux de suite.

### C4 · Montée en boucle (loop roll)
- **Points** : A s'arrête au 1 d'un début de phrase. Sa dernière mesure réelle (la mesure de boucle) est rejouée
  pendant **2 mesures**, puis B entre au 1 de E2 (refrain ou section la plus forte).
- **Courbes** : m1 : unité de 2 temps × 2. m2 : 1 temps × 2 (temps 1-2), ½ temps × 2 (temps 3), ¼ temps × 4 (temps 4).
  Passe-haut sur la boucle de 20 Hz à 800 Hz (expo, sur les 2 mesures). Volume 1 → 0,8 en `lin`. B sec et plein au 1.
- **Basses** : A perd les siennes par le passe-haut, B arrive avec les siennes au 1.
- **Usage** : énergie qui monte (ΔE ≥ +2 dB) et E2 disponible. La **mesure bouclée doit être sans voix** (une voix bouclée
  s'entend comme un « disque rayé »), sinon C4 est inéligible. Au plus 1 sur 5.

### C5 · Fondu calé (Fade, 2 mesures)
- **Points** : recouvrement de 2 mesures, sortieA = fin de phrase de A, entreeB + 2 mesures = début de section de B.
- **Courbes** : médiums et aigus en `cos` (A 1→0, B 0→1) sur m1-m2. Échange des basses **au 1 de m2**.
- **Usage** : tempos ≤ 6 %, grille « nette » des deux côtés, Camelot ≤ 2 ou inconnue. Fondu de base du profil court
  quand aucun bord n'est instrumental. Il sert aussi de premier repli des C6 et C7.

### C6 · Mix 3 bandes (radio edit, 4 mesures)
- **Points** : B entre au début de son intro (E0), et entreeB + 4 mesures = première section vocale de B. A joue ses
  4 dernières mesures avant sortieA (fin de la dernière section pleine ou outro).
- **Courbes** :
  - B : volume `cos` 0→1 sur m1 ; médiums 0,5 sur m1 puis 1 dès m2 ; aigus à 1 dès le début ; graves coupés puis échangés
    **au 1 de m3**.
  - A : médiums 1 → 0,5 (fin de m2) → 0 (fin de m3) en `lin` ; aigus 1→0 sur m3-m4 ; graves échangés au 1 de m3 ; volume
    `cos` 1→0 sur m4.
  - A doit être à ≤ −20 dB avant la première phrase vocale de B.
- **Usage** : profil court, tempos ≤ 6 %. Intro de B ≥ 4 mesures **sans voix** (sinon repli C5). Camelot ≤ 2 ou inconnue.

### C7 · Échange de basses (Blend, 8 ou 16 mesures)
- **Points** : T = 8, ou 16 si les deux bords sont instrumentaux sur ≥ 16 mesures. Fenêtre de A = ses T dernières mesures
  avant sortieA (idéalement son outro) ; entreeB + T = début de section de B.
- **Courbes** :
  - B : volume `cos` 0→1 sur la première moitié ; aigus 0,5 → 1 sur la première moitié ; graves coupés jusqu'à l'échange.
  - A : volume 1 sur la première moitié, puis `cos` 1→0 sur la seconde ; aigus 1→0 en `lin` sur la seconde moitié.
  - Échange des basses **au 1 de m(T/2 + 1)** (m5 ou m9).
- **Usage** : tempos ≤ 5 %, Camelot ≤ 1 et connue (si la tonalité est inconnue : T = 8 seulement, et seulement si les deux
  bords sont instrumentaux). Voix des deux côtés ensemble ≤ 2 mesures. Grille nette. Avance ≥ (2T + 2) × mesure de A + 8 s. Profil long,
  ou profil court quand les deux bords sont instrumentaux.

### C8 · Montée filtrée (Rise, 4 ou 8 mesures)
- **Points** : entreeB + T = section forte de B (refrain ou drop). T = 8 si la voix de A est faible sur la fenêtre, sinon 4.
- **Courbes** :
  - B : passe-bas de 400 Hz à 16 kHz (expo) sur m1…mT ; volume `cos` 0→1 sur la première moitié ; graves coupés jusqu'au 1
    final.
  - A : passe-haut de 20 Hz à 250 Hz sur m1…m(T−1), puis jusqu'à 1 kHz sur la dernière mesure ; volume 1 → 0,7 en `lin`, puis
    0 au 1 final (rampe de 10 ms).
  - Échange des basses **à la fin** : les graves de B arrivent pleins au 1 final.
- **Usage** : énergie qui monte (ΔE ≥ +1,5 dB) vers une section forte, tempos ≤ 6 %, Camelot ≤ 2 ou inconnue (le passe-bas
  atténue les heurts). Jamais vers un B plus calme.

## 5. Placement des points

Le placement se calcule dans l'extension, à partir de l'analyse Spotify uniquement.

1. **Phrases** : chaque mesure reçoit son index depuis le début de sa section. Sont candidates les mesures d'index multiple de
   8, à défaut de 4, de confiance > 0,3.
2. **Confiance de grille** (par bord, sur 16 mesures autour du point) : `nette` si la médiane des confiances est ≥ 0,5 et
   l'écart-type relatif des durées de mesure ≤ 3 % ; `moyenne` si ≥ 0,3 et ≤ 6 % ; sinon `floue`. Une grille floue interdit
   tout recouvrement et tout effet (C3, C4) : repli R1 ou R2. Le moteur revérifie au rendu (netteté `grid_lag` ≥ 1,5).
3. **Sections de A** : la « dernière section pleine » est la dernière dont la sonie est ≥ médiane − 3 dB. Les sections qui la
   suivent forment l'outro.
4. **Sortie de A** (= sortieA) : la première frontière de phrase à partir de la fin de la dernière section pleine (ou d'une
   frontière dans l'outro). Pour un recouvrement, toute la fenêtre [sortieA − T ; sortieA] doit être après le début de cette
   section, ou dans l'outro.
5. **Garde-fou anti-fin-coupée** : la partie de A jamais entendue (de sortieA à la fin, moins le silence final) doit rester
   ≤ 30 s et ≤ 15 % de A (O1). Si aucune sortie ne le respecte, on prend la frontière de phrase la plus tardive avant les
   6 dernières secondes. Si elle n'existe pas : R2. On ne sort jamais au milieu d'une phrase vocale (voix de A sur le
   dernier temps → décaler d'une demi-phrase ou passer à C2).
6. **Entrée de B** :
   - E0 = premier 1 après le silence initial ;
   - E1 = premier début de section après ≥ 4 mesures ;
   - E2 = « refrain » : première section de la première moitié de B dont la sonie est ≥ médiane + 2 dB, ou à défaut la plus
     forte de cette moitié.
   - Sauter le début de B (E2) n'est permis que pour C1, C3 et C4, au plus **1 transition sur 3**, avec ≤ 25 % de B sauté.
7. **Énergie** : ΔE = sonie moyenne (segments, `loudness_max`) des 4 mesures de B après le point d'arrivée − celle des
   4 dernières mesures de A avant sa sortie.
8. **Profil d'un bord** : « instrumental long » si ≥ 8 mesures sans voix au bord (§6), sinon « vocal ». Le profil de la
   paire est `long` si les deux bords sont instrumentaux et le tempo entre 110 et 135 BPM, sinon `court`.

## 6. Gestion des voix sans stems (tranché : [ADR 0002](../adr/0002-detection-voix-v1.md))

Besoin : la présence de voix **par mesure** sur la fenêtre de sortie de A et la fenêtre d'entrée de B, au moment du plan
(avant le saut), puis une vérification au rendu.

| Option | Principe | Disponible pour B avant le saut ? | Coût | Risque |
|---|---|---|---|---|
| V1 Paroles synchronisées | Lignes horodatées des paroles du client (endpoint de paroles de Spotify via Spicetify) : une mesure est « vocale » si une ligne la couvre | **Oui** | Nul (une requête) | Disponibilité sur compte gratuit à vérifier ; couverture inégale ; fin de ligne inconnue (bornée par la ligne suivante) |
| V2 Segments Spotify | Heuristique sur `timbre` et `pitches` des segments (brillance, planéité, stabilité de la chroma) | Oui | Nul | Probablement faible en rap, où voix et instru ont un timbre proche |
| V3 Signal en mémoire | Par mesure : énergie harmonique 300 Hz à 3,4 kHz après séparation harmonique/percussive (médianes), plus modulation syllabique 3 à 8 Hz de l'enveloppe | **Non** (A seulement ; B après le saut) | Faible (numpy) | Calibrage par genre |
| V4 Petit modèle pré-entraîné | VAD ou segmenteur parole/musique sur CPU, sur la mémoire | Non (comme V3) | Moyen | Entraîné sur la parole, pas sur la voix chantée/rappée ; licence |

**Décision** (tâche 4, ADR 0002) : sans attendre de spike en direct. **Au plan** : V2 (segments) par défaut, V1 (paroles
synchronisées) seulement derrière le drapeau `dj-mixer:paroles`, éteint par défaut ; sans segments, toutes les mesures sont
comptées vocales. **Au rendu** : V3 sur la mémoire, pour dégrader seulement (C4, C6, C5/C7/C8). Contrat commun : un score par
mesure dans [0 ; 1], vocal ≥ 0,5, sans voix < 0,3, repli au rendu ≥ 0,6. Tests sur synthèse et analyses factices ; le
calibrage contre les paroles sur ≥ 20 morceaux et la vérification sur compte gratuit sont la tâche 2-direct (développeur).

Règles qui utilisent la voix : C1 et C2 (ne pas couper un mot), C4 (mesure bouclée sans voix), C6 (intro de B sans voix), C7
(≤ 2 mesures de voix ensemble), C8 (durée 4 ou 8), profil de bord.

## 7. Règle de choix automatique

Elle s'exécute dans l'extension, une fois par morceau, au plan. Le hasard est à graine fixe pour les simulations.

1. **Refus d'office** (on va directement à R2 « bord à bord ») : contexte `album` joué dans l'ordre, analyse absente, pub
   (si détectée), moteur éteint (R3).
2. **Caractéristiques de la paire** :
   - écart de tempo `g`, avec moitié et double comptés ; un rapport 3:2 compte comme incompatible ;
   - distance Camelot `k` (null si `key_confidence` < 0,4) ;
   - ΔE ;
   - confiance de grille des deux bords ;
   - voix par mesure ;
   - profil de la paire ;
   - avance disponible du moteur (`/state`).
3. **Éligibilité** : les conditions d'usage du §4. Avance requise pour un recouvrement de T mesures = (2T + 2) × mesure de A + 8 s (§14).
4. **Poids de base** (H6, à calibrer) :

   | Profil | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
   |---|---|---|---|---|---|---|---|---|
   | court | 3 | 2 | 1 | 1,5 | 2 | 3 | 1 | 1,5 |
   | long | 0,5 | 1 | 0,3 | 1 | 2 | 1 | 4 | 2 |

5. **Modulations** :
   - ΔE ≥ +2 dB : C4 et C8 × 2, C1 sur E2 × 1,5 ;
   - ΔE ≤ −2 dB : C4 et C8 exclus, C2 et C7 × 1,5 ;
   - tonalité sûre et `k` ≤ 1 : C5, C6, C7 × 1,5 ;
   - avance sous la cible : transitions sans recouvrement × 1,5 et C4 × 2 (C4 regagne de l'avance).
6. **Variété** :
   - la transition précédente est exclue (sauf si elle est la seule éligible) ;
   - celle d'avant-dernière × 0,5 ;
   - au plus 1 « effet » (C3 ou C4) sur 4 ;
   - les quotas C2, C3, C4 et E2 du §4 et du §5 s'appliquent.
7. **Tirage** : au hasard parmi les 3 meilleurs poids, proportionnellement à leur poids. La raison (paire, critères, poids)
   est rendue en texte pour l'écran.

## 8. Échelle de repli (façon Apple)

Chaque transition déclare son repli. Le premier repli éligible remplace la transition. Le repli est décidé au plan par
l'extension (conditions connues), ou au rendu par le moteur (`Refus` : netteté < 1,5, calage > 20 ms après correction, voix
mesurée au-delà de O4, B absent, avance insuffisante).

| Transition | Repli 1 | Repli 2 | Repli 3 |
|---|---|---|---|
| C7 | C5 | R1 | R2 |
| C6, C8 | C5 | R1 | R2 |
| C5 | R1 | R2 | — |
| C4, C3, C2 | C1 | R2 | — |
| C1 | R2 | — | — |

- **R1 · Fondu court** : 1 mesure en `cos`, graves de B coupés jusqu'au 1 final, sans étirement. Calé sur la grille si elle
  est moyenne, sur le temps estimé sinon.
- **R2 · Bord à bord** : aucun recouvrement. Le silence final de A et le silence initial de B (< −50 dBFS) sont retirés, avec
  un raccord de 20 ms. A joue jusqu'à sa fin réelle.
- **R3 · Spotify seul** : aucune intervention (moteur éteint).
- Le **secours** actuel (transition prête trop tard alors que Spotify a déjà sauté) est conservé et compté comme un échec dans O6.

## 9. Critères d'acceptation

### 9.1 Automatiques, sur le son rendu (moteur, hors Spotify)

Ils sont vérifiés sur des morceaux de synthèse (comme `test_rendu.py`) **et** sur des paires réelles capturées en mémoire par
`DJ_WORK`. Le son réel n'est jamais commité.

1. **Calage** : pour C5 à C8, |écart B − A| ≤ 20 ms (`_grid_fit`), sinon le rapport indique un repli.
2. **Basses** : sur les signaux de A et B rendus avant la somme, l'énergie < 150 Hz des deux dépasse −12 dB de leur max
   commun pendant ≤ 1 temps.
3. **Échange sur le 1** : le milieu de la rampe des graves tombe à ±10 ms d'un premier temps de la grille commune.
4. **Pas de trou** : aucune suite de quasi-zéros > 20 ms dans la sortie, hors silences propres aux morceaux (`analyse.py`).
5. **Pas de clic** : aux bords de chaque segment et à chaque rampe, la dérivée seconde du signal reste sous 6 dB au-dessus de
   la médiane locale.
6. **Niveau** : O5.
7. **Courbes conformes** : pour chaque transition, gains et fréquences de coupure relevés à chaque temps = ceux du §4 à ±1 dB
   et ±10 %. Le rendu journalise ses automations.
8. **Placement** (sur des analyses Spotify enregistrées, sans son) : sortieA et entreeB sur une frontière de phrase ; garde-fou
   O1 respecté ; E2 seulement aux quotas fixés.
9. **Avance** : C1 à C3 consomment 0 (±1 temps), C4 en regagne ≥ 1,5 mesure, C5 à C8 consomment T mesures (±1 temps).
10. **Variété** : simulation à blanc de 30 transitions sur des paires réelles de la bibliothèque (analyses en cache). O7
    respecté, et les quotas C3, C4 et E2 aussi.
11. **Repli** : chaque condition de refus du §8, provoquée, mène au bon repli. Aucune exception ne coupe la lecture.
12. **Temps de rendu** : la transition est prête ≥ 2 s avant d'être jouée, avec une avance de 60 s.

### 9.2 Protocole d'écoute du développeur

- **Paires** : 16 paires de la bibliothèque, choisies à blanc par le data-ml-engineer et présentées comme une playlist
  d'essai. Elles couvrent :
  1. rap FR → rap FR, tempos à ±2 %, bords vocaux ;
  2. rap FR → rap FR, tempos à 6-10 % ;
  3. rap → rap avec une intro instrumentale de B ≥ 4 mesures ;
  4. outro instrumentale longue des deux côtés ;
  5. shatta → shatta ;
  6. shatta → bouyon (rapport ~3:2) ;
  7. bouyon → bouyon ;
  8. calme → fort (ΔE ≥ +4 dB) ;
  9. fort → calme ;
  10. tonalités qui se heurtent (k ≥ 4, sûres) ;
  11. grille floue (« ! » chez Spotify) ;
  12. A qui finit net (pas d'outro) ;
  13. A avec une longue fin (fade-out ou outro parlée) ;
  14. même artiste ;
  15. tonalités identiques, tempos identiques ;
  16. album dans l'ordre (attendu : R2).
- **Déroulé** : 2 séances de 15 min. Chaque paire est jouée avec la transition que le choix automatique a retenue. Les
  8 transitions passent chacune au moins 2 fois en tout : le data-ml-engineer force la transition sur les paires éligibles
  qui manquent. Le nom de la transition reste **masqué** jusqu'à la note.
- **Note** dans l'écran : 1 à 5, plus des étiquettes à cocher : *rythme qui décroche*, *basses doublées*, *voix superposées*,
  *fin coupée*, *entrée au mauvais endroit*, *trop long*, *trop court*, *saut de volume*, *clic ou trou*, *effet de trop*.
  Un commentaire libre est facultatif. Journal : `docs/tests/notes-ecoute.jsonl` (repart vide), avec la paire, la transition,
  le repli éventuel et les mesures automatiques.
- **Verdict** : O8. Les résultats et les poids ajustés sont consignés dans `docs/tests/12-ecoute-transitions-v2.md`.

## 10. Contrat extension → moteur (validé : [ADR 0001](../adr/0001-contrat-ordre-v2.md))

Le format exact de l'ordre v2 (`POST /order`, UDP), des réponses, du rapport `derniere_transition` de `/state`, de
`POST /rating` (par `id`, pour l'écoute à l'aveugle) et de `POST /run` est dans l'ADR 0001, seule source de vérité.
Écarts avec la proposition initiale : champs de A et de B regroupés dans `a` et `b` avec position en secondes **et** index
de mesure ; `id`, `choisie` et `replis_plan` ajoutés ; `params` par transition ; `pre_s` et `/double` retirés. Les anciens
noms (`montee`, `melange`…) sont refusés et ne restent pas jouables à la main : le forçage passe par C1…R2.

## 11. Hors périmètre v1 (v2 et au-delà)

- Stems (séparation voix/accompagnement sur la fenêtre de transition), donc **échange des voix**, écho de voix seule,
  acapella, mashup.
- **Wordplay** (paroles horodatées au mot).
- Double drop, drop swap, échange de breakdowns, rampe de tempo au-delà de 6 %, mix à demi/double tempo **avec
  recouvrement**, transposition.
- Réglage automatique des poids par les notes. Points de mix appris (CUE-DETR, crowdsourcing).
- Choix et réordonnancement du morceau suivant (Smart Reorder). Gestion des pubs. Réécriture du moteur en Rust ou C.

## 12. Découpage en tâches

Ajusté par le tech-lead le 2026-10-28 (aucun spike en direct possible pendant le pipeline ; propriété des fichiers :
[ADR 0005](../adr/0005-modules-transitions.md)). Chaque tâche dure au plus une demi-journée. « // » = peut tourner en
parallèle des tâches indiquées.

| # | Rôle | Tâche | Fichiers | Dépend de | Parallèle |
|---|---|---|---|---|---|
| 1 | tech-lead | Contrat, rapport, modules, sort de l'ancien code | `docs/adr/0001` à `0006`, `docs/architecture.md`, §6, §10, §12, §13 | — | **fait** |
| 2 | data-ml-engineer | Voix au plan hors ligne : V2 sur segments, parseur et lecture de paroles derrière drapeau, analyses et paroles factices | `spicetify/dj-voix.js`, `spicetify/test/voix.test.mjs`, `spicetify/test/fixtures/` | 1 | // 3, 5a, 10 |
| 2-direct | développeur | Spike en direct, après le pipeline : paroles sur compte gratuit, couverture sur 50 morceaux, calibrage V2/V3 sur ≥ 20 morceaux | `docs/tests/11-voix.md` | 2, 3 | hors pipeline |
| 3 | data-ml-engineer | V3 sur la mémoire, testé sur `synthese.py` (voix factice) ; temps CPU | `proto/e2/transitions/voix.py`, `proto/e2/test_voix.py` | 1, 5a (`synthese.py`) | // 2, 10 |
| 4 | tech-lead | Trancher l'option voix | ADR 0002, §6 | — | **fait** |
| 5a | backend-dev | Déménagement : paquet `transitions/` (`contrat`, `outils`, `calage`, `catalogue` squelette), `synthese.py` (avec `voix=`), retrait des anciens préréglages et de `/double`, `fresh()` sur le paquet | `proto/e2/e2.py`, `proto/e2/transitions/`, `proto/e2/synthese.py`, `proto/e2/test_rendu.py`, suppression de `rendu.py` et `recettes.py` | 1 | // 2, 10, 13 |
| 5 | backend-dev | Primitives : EQ 3 bandes (ADR 0006), courbes nommées, échange des basses sur un 1, filtres balayés 12 dB/oct, écho calé, journal des automations | `transitions/primitives.py`, `transitions/outils.py` (`sweep`), `proto/e2/test_primitives.py` | 5a | // 6, 3, 10 |
| 6 | backend-dev | Mesures sur le son rendu (critères 9.1, n° 1 à 7) | `transitions/mesures.py`, `proto/e2/test_mesures.py` | 5a | // 5 |
| 7 | backend-dev | Rendus C1, C2, C3, R2 | `transitions/seches.py` | 5 | // 8, 9 |
| 8 | backend-dev | Rendu C4, secours porté | `transitions/boucle.py` | 5 | // 7, 9 |
| 9 | backend-dev | Rendus C5, C6, C7, C8, R1, avec `calage.caler_superposition` extrait du `melange` | `transitions/superposees.py`, `transitions/calage.py` | 5 | // 7, 8 |
| 10 | data-ml-engineer | Placement (§5) ; tests sur analyses factices | `spicetify/dj-placement.js`, `spicetify/test/placement.test.mjs`, `spicetify/test/fixtures/` | 1 | // 2, 3, 5 à 9 |
| 11 | data-ml-engineer | Choix (§7), repli au plan (§8), ordre v2, `window.DJ` v2 (`forcer`), intégration dans `dj-auto.js`, `installer.sh`, `transition.js`, `run.sh` | `spicetify/dj-choix.js`, `spicetify/dj-auto.js`, `spicetify/installer.sh`, `spicetify/test/choix.test.mjs`, `proto/e2/transition.js`, `proto/e2/run.sh` | 2, 10 | // 7 à 9, 12 |
| 12 | backend-dev | Ordre v2 dans `e2.py` : validation, `Place`, échelle au rendu (`catalogue.rendre`), voix V3, rapport `/state`, `DJ_JOURNAL`, `/rating` et `/run` v2, `DJ_SLOW`, `GET /dj-catalogue.js` | `proto/e2/e2.py`, `transitions/contrat.py`, `transitions/catalogue.py`, `proto/e2/test_ordre.py` | 5a, 6, 7 (et 3 pour la voix, sinon bouchon) | // 8, 9, 11 |
| 13 | ux-designer | Écran : écoute à l'aveugle, note et étiquettes, repli et raison, états | `docs/specs/transitions-v2-ecran.md` | 1 | // 2 à 12 |
| 14 | ui-engineer | Intégration de l'écran : `dj-catalogue.js`, note par `id` avec étiquettes, mode aveugle, forçage (`DJ.forcer`, `/run`) ; sur un `/state` factice d'abord | `spicetify/dj-catalogue.js`, `spicetify/dj-mixer/index.js`, `proto/e2/ecran.html` | 13 (contrat : ADR 0001) | // 5 à 12 |
| 15 | test-writer | Tests d'acceptation 9.1 sur synthèse, simulation à blanc de 30 transitions (avance comprise), cohérence des identifiants entre les trois catalogues | `proto/e2/test_criteres.py`, `spicetify/test/simulation.test.mjs` | 6, 7, 8, 9, 11, 12 | non |
| 16 | data-ml-engineer | Choisir les 16 paires du protocole 9.2 (à finir en direct) | `docs/tests/12-ecoute-transitions-v2.md` | 10, 11 | // 15 |
| 17 | qa-reviewer | Revue contre la spec ; le protocole d'écoute se fait ensuite avec le développeur | — | 14, 15, 16 | non |
| 18 | docs-writer | Architecture, faisabilité, roadmap, README de e2 | `docs/architecture.md`, `docs/faisabilite.md`, `docs/roadmap.md`, `proto/e2/README.md` | 17 | non |
| 19 | release-manager | Commits par lot et PR (point d'arrêt : push et PR demandent l'accord du développeur) | — | 18 | non |

**Chemin critique** : 5a → 5 → 9 → 12 → 15 → 17. Dès la fin de 1, trois voies tournent en parallèle sans fichier commun :
moteur (backend-dev : 5a, puis 5 // 6, puis 7 // 8 // 9, puis 12), extension (data-ml-engineer : 2 // 10, puis 11 ; 3 dès
que `synthese.py` existe) et écran (ux-designer 13, puis ui-engineer 14 sur un `/state` factice).

## 13. Questions ouvertes

- **Q1 (développeur)** Ralenti de regain : **×1,03 par défaut**, réglable par `DJ_SLOW` (1,00 à 1,06), écrit dans chaque note
  ([ADR 0003](../adr/0003-ralenti-et-quota-refrain.md)). À confirmer à l'écoute.
- **Q2 (développeur)** Entrée sur le refrain (E2) : 1 sur 3, jamais deux de suite, B sauté ≤ 25 % **et** ≤ 45 s
  (ADR 0003). À confirmer à l'écoute (étiquette « mauvais endroit »).
- **Q3 (tech-lead)** Paroles synchronisées sur compte gratuit : **inconnu, non bloquant**. La v1 n'en dépend pas (V2 au plan,
  V3 au rendu) ; réponse par la tâche 2-direct ([ADR 0002](../adr/0002-detection-voix-v1.md)).

## 14. Arbitrages pendant l'implémentation

Écarts assumés entre le texte ci-dessus et le code livré (tâches 5 à 15). Ils priment sur les sections concernées.

- **Avance requise** (§4 C7, §7.3, ADR 0001, 0004, 0005) : (2T + 2) × mesure de A + 8 s, au lieu de la marge fixe de 12 s
  prévue au départ. Le rendu attend
  que B soit en mémoire avant de calculer, puis doit finir ≥ 2 s avant d'être joué (critère 9.1-12). Même règle dans le
  moteur (`catalogue.avance_requise`) et l'extension (`dj-choix.js`, `avanceRequise`).
- **O7** : mesuré seulement sur les fenêtres de 10 sans repli forcé R1/R2, où chaque choix avait ≥ 2 transitions
  éligibles. Couverture faible : 40 fenêtres sur 252 dans la simulation à blanc. En ordre aléatoire, C1 domine.
- **O1** (dernière section pleine entendue en entier, ≥ 90 %) : mesuré seulement quand cette section finit ≥ 6 s avant la
  fin de A ; sinon aucune sortie ne peut la respecter (§5.5).
- **O5**, écarts connus, affichés « ~ » par `test_criteres.py` sans le faire échouer : C4 à −5,5 dB (passe-haut jusqu'à
  800 Hz et volume 0,8 imposés par §4) ; C8 à 124 BPM ≈ −3 dB (A sous passe-haut, B sous passe-bas).
- **C7 rarement choisie** : elle exige une tonalité connue et proche, des tempos à 5 % et des bords sans voix, rarement
  réunis en rap FR (V2 juge souvent « vocal » un bord instrumental). À surveiller pendant le protocole d'écoute.
