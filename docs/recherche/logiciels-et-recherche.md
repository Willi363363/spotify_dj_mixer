# Logiciels de DJ et recherche sur le mix automatique : état de l'art (oct. 2026)

Audit web fait à partir de zéro, sans tenir compte des choix passés du projet.
Légende : **[S]** fait sourcé (URL donnée), **[D]** déduction ou estimation de notre part, **[?]** source faible
(blog d'un éditeur concurrent, forum) ou non vérifiée.

## 1. Logiciels : comment leur automix décide

| Logiciel | Choix des points sortie/entrée | Durée | Technique | Stems |
|---|---|---|---|---|
| **Mixxx** (GPL, Linux) | Repères Intro/Outro, posés à la main ou par détection de silence. Mode « Full Intro + Outro » (par défaut) : il fait coïncider la **fin** de l'outro et la **fin** de l'intro, sur la plus courte des deux sections. « Fade at Outro Start » aligne leurs **débuts** et tronque la fin de l'outro [S1] | Égale à la section la plus courte, sinon un temps fixe (10 s par défaut [?S2]) | Mouvement du crossfader, sans EQ ni filtre automatiques [D, d'après le code et la doc] | non |
| **VirtualDJ** | « Smart » : il analyse l'outro du morceau courant et l'intro du suivant. Les POI « Automix Mix In/Out » se corrigent à la main [S3] | Smart ≈ **4 à 8 s** ; sinon `fadeLength` en secondes, réglable [S3] | Fondu, « fade out / cut in » façon radio, ou cut sec. Beatmatch seulement si les tempos sont proches (`autoMixBeatMatchOnFade`), recalage ±10 % [S3] | Stems 2.0 en temps réel, **GPU recommandé**. Sans GPU, une qualité réduite est proposée [S4] |
| **djay Pro (Algoriddim)** | « Song range » auto ou manuel. « Mix Now » prend le « plus proche point de mélange convenable ». Méthode non publiée [S5] | En **mesures** ou en secondes, ou « Automatic » [S5] | Filter, Echo, Tremolo, Riser, Dissolve, **Neural Mix**. « Automatic » tire le type au hasard. Tempo : Sync ou Sync + Tempo Blend [S5][S6] | Neural Mix : croise **séparément** chaque paire de stems (voix, batterie, harmonie/basse) pour garder l'énergie sans voix qui se chevauchent [S6]. Sur iOS, ça tourne sur le Neural Engine |
| **rekordbox** | Analyse de « phrases » selon l'humeur détectée (High/Mid/Low). Étiquettes High : Intro, Up, Down, Chorus, Outro [S7]. Pas trouvé de doc qui montre l'automix s'en servir | – | – | Stems en temps réel, jugés de qualité inférieure dans les comparaisons communautaires [?S8] |
| **Serato** | Pas d'automix sérieux (lecture enchaînée) | – | – | Stems + **Stems FX** : vocal echo, instrumental echo, instrumental braker, drums echo. Sert à sortir une voix en écho pendant que l'instru continue [S9] |
| **Traktor / Engine DJ** | Automix rudimentaire (enchaînement de liste) [D] | – | – | Fichiers .stem.mp4 et, plus récemment, séparation intégrée [?S8] |
| **DJ.Studio** (hors ligne, sur une frise) | « Harmonize » trie la liste par clé Camelot et BPM. Choix des points peu documenté, avec des plaintes d'utilisateurs (« mixe dans un refrain au lieu d'un break ») [S10] | Éditable | Préréglages : fondu, **bass swap**, **echo swap** [?S11] | Stems sur la frise, pour échanger les basses [?S11] |
| **Pacemaker** | Automix pour des listes Spotify, accès coupé par Spotify en 2020 [S12] | – | – | – |
| **Apple Music AutoMix** (iOS 26) | Apprentissage automatique sur le tempo, la tonalité et la structure. Time-stretch et beatmatch à la place du crossfade [?S13] | – | Ratés signalés sur les fins complexes [?S13] | – |

Ce qu'on en retient :
- **[D]** Aucun logiciel grand public ne publie son algorithme de choix des points. Les plus robustes s'appuient sur des
  **repères de structure** (intro/outro, phrases) et laissent l'utilisateur les corriger.
- **[S]** Les durées « automatiques » sont courtes (VirtualDJ Smart 4-8 s). Le réglage en **mesures** (djay) est la
  bonne unité.
- **[S]** L'usage des stems qui fait consensus en transition : **ne jamais superposer deux voix**, sortir la voix ou
  l'instru en écho, échanger les basses. Le « drum swap » n'est documenté comme mode automatique nulle part.

## 2. Recherche académique

### 2.1 Vande Veire & De Bie, 2018 : auto-DJ drum & bass (EURASIP JASMP, CC-BY) [S14][S15]
- **Analyse** : battements (fonction d'onset, autocorrélation, d'après Davies & Plumbley) **98,2 %** ; premier temps
  de la mesure (classifieur) **98,1 %** ; segmentation par matrice d'auto-similarité de Foote, recalée sur les premiers
  temps et sur un **nombre entier de phrases**, **94,3 %**. Au total, 91 % des morceaux sont annotés sans erreur.
- **3 transitions, de durée fixe par type** : *double drop* (les deux drops alignés), *rolling* (partie principale vers
  le drop du suivant, l'énergie reste haute), *relaxed* (outro ou break vers l'intro, plus calme). Pas de double drop
  juste après un rolling ou un autre double drop. Cue : fondu d'entrée de **16 mesures**, fondu de sortie de
  **32 mesures** [S16, extrait de résultat de recherche].
- **Mixage** : EQ 3 bandes par canal façon Pioneer (low shelf **≈70 Hz**, peak **≈1 kHz**, high shelf **≈13 kHz**),
  pas de filtres balayés. Le tempo est calé par **découpe et recollage aux battements**, sans time-stretch. Le crossfade
  est **calculé en arrière-plan et mis en tampon** avant la lecture.
- **Choix du morceau suivant** : clé compatible (avec pitch-shift pour élargir le choix), descripteur de « thème » en
  3 dimensions (énergie, spectre), rythme proche (courbes d'onset), **détection de voix pour éviter qu'elles se
  chevauchent**. Test avec 18 fans de drum & bass. Code : github.com/lenvdv/auto-dj.
- Limite : un seul genre, très normé (phrases de 32 mesures, drops nets).

### 2.2 Kim, Choi, Sacks, Yang, Nam : analyse de vrais mixes (ISMIR 2020) [S17]
1 557 mixes 1001Tracklists, 13 728 morceaux, **20 765 transitions**, alignés mix-morceau par DTW sur des chromas.
- **Durée de transition** : histogramme avec des pics **tous les 32 temps** (8 mesures), en particulier 32 et 64. La
  masse est entre 0 et 64 temps, avec une longue traîne au-delà de 128 temps.
- **Tempo** : 86,1 % des morceaux sont décalés de moins de 5 %, 94,5 % de moins de 10 %, 98,6 % de moins de 20 %.
- **Tonalité** : seuls **2,5 %** des morceaux sont transposés, dont 94,3 % d'un seul demi-ton. Le key-lock est la norme.
- **Points de cue** : entre DJ différents sur un même morceau, 23,6 % des cues sont identiques, 40,4 % à moins
  d'1 mesure, 73,6 % à moins de 8 mesures, 86,2 % à moins de 16 mesures. Il existe donc des règles communes.
- **Limite des humains** : l'écart-type de l'annotation d'une frontière entre deux morceaux est d'environ 9 s.

### 2.3 Suites du même groupe
- **NIME 2021**, Kim, Yang & Nam [S18] : rétro-ingénierie des réglages de fader et d'EQ dans les transitions, par
  optimisation convexe sur des sous-bandes. Meilleur score de l'écoute (14 personnes). Démo : mir-aidj/transition-analysis.
  Je n'ai pas pu lire le détail chiffré des courbes d'EQ dans le texte complet.
- **All-In-One** (Kim & Nam, WASPAA 2023) [S19] : `allin1` donne tempo, battements, premiers temps, frontières et
  étiquettes (intro, verse, chorus, bridge, outro). Il **fait tourner Demucs avant**, donc il est lourd sur CPU [D].
  Licence non vérifiée.

### 2.4 DJtransGAN, Chen et al., ICASSP 2022 [S20]
- Le générateur pilote un **EQ et un fader différentiables** : courbes de fondu par sous-bande, découpage
  20-300 / 300-5 000 / 5 000-20 000 Hz, 24 paramètres. Entraînement adversarial sur de vrais mixes.
- Transition fixée à **8 mesures** : entrée sur le 1er temps des 8 dernières mesures de A, sortie à la fin des
  8 premières mesures de B.
- Écoute (136 participants valides) : **aucune différence significative entre GAN, fondu linéaire et règles
  d'expert**. Tous battent la somme brute, l'humain reste au-dessus. Défaut cité : transitions trop rapides entre deux
  morceaux chantés.
- **[D]** Enseignement : avec un bon calage temporel, un fondu bien placé vaut autant qu'un modèle appris. **Le placement
  et l'évitement des voix comptent plus que la forme exacte des courbes.**

### 2.5 Détection de points de cue
- **CUE-DETR** (ETH, 2024) [S21] : détecteur d'objets DETR appliqué aux mél-spectrogrammes. Jeu **EDM-CUE** : 4 710
  morceaux, 21 461 cues tirés de collections rekordbox de 4 DJ. F1 de 0,36 à 0,46, meilleur que les cues automatiques de
  Mixed In Key et de l'automix (F1 0,13 à 0,22). Imposer un **espacement de 16 ou 8 mesures** aide. Code :
  ETH-DISCO/cue-detr. Coût CPU non publié.
- **[D]** Même l'état de l'art place mal plus d'une cue sur deux à 1 temps près. Une règle simple (frontière de section,
  recalée sur une mesure multiple de 8 ou 16) est un plancher raisonnable.

### 2.6 Séparation de sources (stems) : faisabilité sur CPU Linux
| Modèle | Licence | Qualité (SDR MUSDB) | Vitesse CPU | Latence |
|---|---|---|---|---|
| HT-Demucs v4 [S22] | MIT, dépôt archivé (fork adefossez) | **9,0 dB** | « ≈ **1,5 × la durée** du morceau » sur CPU | Hors ligne, segments ≤ 7,8 s |
| Hybrid Demucs v3 [S22] | MIT | 7,7 dB | plus rapide [D] | hors ligne |
| Spleeter 2/4 stems [S23] | MIT (TensorFlow) | ≈ 5-6 dB [?] | ≈ **18 s pour 4 min** en 4 stems sur Ryzen 9 [?S23] | hors ligne |
| Open-Unmix UMX/UMX-HQ [S24] | MIT, mais poids UMX-L en **CC BY-NC-SA** [?] | ≈ 6,3 dB (UMX-L) [?] | rapide [D] | hors ligne |
| HS-TasNet (L-Acoustics, 2024) [S25] | Implémentation non officielle sur PyPI | 4,65 à 5,55 dB | conçu pour le temps réel | **23 ms** |
| VirtualDJ Stems 2.0 [S4] | propriétaire | meilleure réputation chez les DJ [?] | temps réel sur **GPU** | – |

- **[D]** Notre avance d'environ 20 s change la donne : on n'a pas besoin de séparation *temps réel à faible latence*.
  Il suffit de séparer **la seule fenêtre de transition** (16 à 32 s) plus vite qu'elle n'arrive. Avec HT-Demucs à
  1,5 × la durée sur CPU, c'est **trop juste** dans 20 s ; avec un modèle 2 stems (voix / accompagnement) de type Spleeter
  ou Open-Unmix, quelques secondes suffisent. À mesurer sur la machine avant de s'engager.

## 3. Synthèse des chiffres utiles
| Paramètre | Valeur | Source |
|---|---|---|
| Unité de durée | **8 mesures** (32 temps) et ses multiples (16, 32 mesures) | Kim 2020, DJtransGAN, Vande Veire |
| Écart de tempo accepté | < 5 % dans 86 % des cas, < 10 % dans 94,5 % des cas | Kim 2020 |
| Transposition | rare (2,5 %), garder le key-lock | Kim 2020 |
| Bandes d'EQ « mixette » | ≈70 Hz / 1 kHz / 13 kHz (Pioneer) ; 300 Hz / 5 kHz (DJtransGAN) | Vande Veire, DJtransGAN |
| Automix commercial | 4-8 s (VirtualDJ Smart) : court, parce que sans structure | VirtualDJ |
| Voix | ne jamais superposer deux voix | djay Neural Mix, Vande Veire |

## Ce qu'on peut reprendre

Transposable dans notre moteur (PipeWire, environ 20 s d'avance en mémoire, superposition, EQ, Rubber Band, boucle),
du moins coûteux au plus coûteux :

1. **Points de cue = frontières de `sections` Spotify recalées sur des `bars`**, en ne gardant que les mesures dont
   l'index depuis le début de la section, ou depuis le premier temps fort, est multiple de 8. On évite les cues au
   milieu d'un refrain (plainte DJ.Studio). Coût CPU : nul, c'est de la métadonnée.
2. **Durée en mesures, 8 par défaut, 16 si les deux bords sont calmes**, à la manière du *relaxed* de Vande Veire, en
   s'aidant du `loudness` des sections. 4 mesures ou une coupe sur le premier temps si l'écart de tempo dépasse ≈ 8 %
   (au-delà, les DJ réels ne mélangent quasiment pas). Coût : nul.
3. **Trois recettes typées par l'énergie** : relaxed (outro vers intro, long), rolling (corps vers corps, 8 mesures,
   bass swap), drop sur drop (réservé aux sections à fort loudness, jamais deux de suite). Coût : nul.
4. **Bass swap par EQ 3 bandes** (crossovers ≈ 200 Hz et ≈ 2 à 5 kHz, filtres Linkwitz-Riley ou biquads) : la basse de
   A est coupée sur **un premier temps**, pendant que celle de B est rendue au même instant, à mi-transition. Médiums et
   aigus en fondu à puissance constante. Coût : quelques biquads par canal, négligeable. Le travail DJtransGAN montre
   qu'on gagne peu à affiner davantage les courbes.
5. **Calage du tempo** : Rubber Band sur B seulement, vers le tempo de A, pendant la transition, puis retour progressif à
   100 % sur 8 à 16 mesures. Clé verrouillée, pas de transposition. Coût : Rubber Band en mode temps réel, de l'ordre
   d'un cœur partiel pour une voie stéréo [D, à mesurer].
6. **Garde-fou voix sans stems** : Spotify ne fournit pas de détection de voix. Il faut donc une heuristique, par exemple
   éviter les sections centrales à fort loudness des deux côtés en même temps, ou une petite détection de voix sur le
   tampon [D]. À valider à l'écoute.
7. **Stems en option, seulement sur la fenêtre de transition** : séparation 2 stems (voix / accompagnement) avec un
   modèle MIT léger (Open-Unmix UMX-HQ ou Spleeter 2stems) lancée **dès qu'on entre dans les ~20 s d'avance**. Ça permet
   de sortir la voix de A en écho (Serato) et de ne jamais superposer deux voix (djay). HT-Demucs est probablement trop
   lent sur CPU pour notre avance [D, 1,5 × la durée selon le README]. Coût : de quelques secondes à plusieurs dizaines de
   secondes de CPU par transition, **à mesurer avant tout engagement**.
8. **À écarter** : modèles génératifs (DJtransGAN, et diffusion : rien de publié et vérifiable en 2023-2026 trouvé), et
   détection de cues par apprentissage (CUE-DETR, F1 ≤ 0,46). Le gain est incertain, le coût est élevé, et la grille
   Spotify fait déjà le travail de base.

## Sources
- S1 Mixxx 2.3, Intro/Outro et AutoDJ : https://mixxx.org/news/2020-07-09-intro-outro-sections
- S2 Note sur le défaut de 10 s : https://github.com/byronxu99/AutoDJ
- S3 Manuel Automix VirtualDJ : https://www.virtualdj.com/wiki/AutoMix.html
- S4 VirtualDJ Stems 2.0 : https://www.virtualdj.com/manuals/virtualdj/interface/stems2/index.html ; https://djmag.com/tech/virtualdj-2023-released-new-stem-separation-engine-studio-quality
- S5 Automix djay : https://help.algoriddim.com/user-manual/djay-pro-mac/mixing-basics/using-automix
- S6 Automix AI et Neural Mix : https://musictech.com/news/gear/algoriddim-free-dj-software-djay-pro-ai-automix-and-neural-mix
- S7 Phrases rekordbox : https://thediscdjstore.com/blog/phrase-analysis.html ; https://rekordbox.com/en/feature/overview/
- S8 Comparatifs de stems (éditeurs, à prendre avec prudence) : https://dj.studio/blog/stem-separation-quality-integration-dj ; https://stemsplit.io/blog/dj-stem-separation-guide
- S9 Serato Stems FX : https://musictech.com/news/gear/serato-stems-serato-dj-pro-lite-3-stem-separation
- S10 DJ.Studio, demande d'automix tenant compte des phrases : https://feedback.dj.studio/p/integrating-phrases-into-automix-for-enhanced-transitions ; https://dj.studio/automix
- S11 Transitions DJ.Studio : https://dj-studio-fos.p.accept.appmachine.com/transitions
- S12 Pacemaker et Spotify : https://archive.completemusicupdate.com/article/pacemaker-dj-app-to-directly-license-music-after-spotify-drops-api-access/
- S13 Apple Music AutoMix : https://www.musicradar.com/music-tech/sack-the-dj-apple-music-now-uses-ai-to-mix-tracks
- S14 Vande Veire & De Bie 2018 : https://asmp-eurasipjournals.springeropen.com/articles/10.1186/s13636-018-0134-8
- S15 Billet de l'auteur : https://lenvdv.github.io/2018-03-20-autodj/ ; code : https://github.com/lenvdv/auto-dj
- S16 Figure des cues (ResearchGate) : https://www.researchgate.net/figure/Illustration-of-the-cue-point-selection-for-the-three-transition-types-The-fade-in-and_fig3_327851916
- S17 Kim et al. ISMIR 2020 : https://arxiv.org/abs/2008.10267 ; https://mir-aidj.github.io/djmix-analysis
- S18 Kim, Yang, Nam NIME 2021 : https://nime.org/proc/nime2021_87/ ; https://github.com/mir-aidj/transition-analysis
- S19 All-In-One : https://arxiv.org/abs/2307.16425 ; https://pypi.org/project/allin1/
- S20 DJtransGAN : https://arxiv.org/abs/2110.06525 ; https://github.com/ChenPaulYu/DJtransGAN
- S21 CUE-DETR : https://arxiv.org/abs/2407.06823
- S22 Demucs : https://github.com/facebookresearch/demucs
- S23 Spleeter : https://research.deezer.com/projects/spleeter ; https://stemsplit.io/blog/spleeter-vs-demucs
- S24 Open-Unmix : https://sigsep.github.io/open-unmix ; https://huggingface.co/edgetools/umx-hq
- S25 HS-TasNet : https://arxiv.org/abs/2402.17701
