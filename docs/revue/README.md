# Revue du 2026-10-26

Revue complète demandée après l'essai 14 (« pas encore si ouf, toujours pareil »). Trois volets :

| Fichier | Contenu |
|---|---|
| [`bugs.md`](bugs.md) | Revue du code : bugs confirmés, problèmes probables, gains rapides |
| [`../recherche/axes-amelioration.md`](../recherche/axes-amelioration.md) | Ce que font les meilleurs systèmes (djay, DJ.Studio, Serato, Mosaikbox, Vande Veire, Kim et al.) et les outils locaux disponibles |
| Ce fichier | Diagnostic produit et plan proposé |

## Diagnostic : pourquoi ça ne sonne « pas encore si ouf »

### 1. Des transitions ratées en silence (bug, mesuré dans le code)

Chaque transition douce **saute les 4 mesures de B lancées en avance** : l'avance de 50 s fond de ~6 s (160 BPM) à ~10 s (100 BPM) par transition, un mélange en mode auto ~24 s, et rien ne la regagne. Après 4 ou 5 transitions, la maquette est « prête trop tard », **abandonne**, et on entend le saut brut de Spotify. C'est l'explication la plus probable des arrivées « parfois brutales, brèves, sèches ». Et la mémoire n'étant pas circulaire, **le son s'arrête au bout de 10 minutes** de maquette. Détails : [`bugs.md`](bugs.md).

### 2. Toujours la même forme

Les 6 styles changent ce que fait A, mais gardent **la même trame** : A s'appauvrit, B monte filtré dessous, drop. La recherche montre que la variété perçue vient des **types** de transition (Vande Veire : *double drop*, *rolling*, *relaxed*, enchaînés par une chaîne de Markov), pas des effets.

### 3. Jamais deux rythmes calés ensemble

Mesuré sur 110 morceaux de la playlist : **21 %** des paires consécutives à moins de 3 % de tempo, 33 % à moins de 6 %. Les tempos forment **deux familles** (45 % sous 110 BPM, 45 % au-dessus de 140). Dans 4 cas sur 5, rien ne se superpose en rythme : on n'entend que des effets sur A. Or les DJ réels décalent le tempo jusqu'à 5-10 % (86 % des morceaux à moins de 5 %, Kim et al. 2020), et sous les roulements B garde aujourd'hui son propre tempo.

### 4. Une analyse trop fragile

Mesures bien détectées par Spotify (fiabilité > 0,5) : **47 %** des morceaux. Le « drop » = section la plus forte ne tombe dans les 40 premiers % que pour **48 %** des morceaux : B entre alors tard, et on n'en joue qu'un bout. Rien ne protège contre deux voix qui se chevauchent.

### 5. Ce qui manque par rapport aux meilleurs systèmes

| Manque | Qui le fait | Effet |
|---|---|---|
| Séparation en pistes (voix, batterie, basse, reste) | djay Neural Mix, DJ.Studio, Mosaikbox | Batterie de A sous la voix de B, écho sur la voix seule, pas de voix superposées |
| Niveau sonore égalisé (LUFS) | Mosaikbox (−14 LUFS) | Pas de saut de volume entre deux morceaux |
| Grille de phrases fiable (8, 16, 32 mesures) | Kim et al. : les transitions réelles durent des multiples de 8 mesures | Entrées et sorties qui tombent « juste » |
| Mix double / moitié de tempo | DJ.Studio | Ouvre les paires 80 ↔ 160 |

## Plan proposé, par ordre de priorité

| # | Chantier | Pourquoi d'abord | Effort |
|---|---|---|---|
| 1 | **Fiabilité** : mémoire circulaire ; regagner l'avance (ne plus sauter les mesures de B : les jouer, ou rallonger le retard) ; ne planifier que ce que l'avance permet ; `wait` avant de chercher le changement ; volume sans saut aux bords des segments ; clics des roulements | Sans ça, toute écoute est faussée par des transitions qui ratent | Moyen |
| 2 | **Niveau égalisé** (pyloudnorm, LUFS court terme de A et B) | Gain audible immédiat, coût faible | Faible |
| 3 | **Types de transition et chaîne de Markov** : *double drop* (drops alignés), *rolling* (enchaînement sur 16 mesures), *relaxed* (B part de son début), *drop swap* percussif ; jamais deux fois le même type | Réponse directe au « toujours pareil » | Faible à moyen |
| 4 | **Tempo de B calé sous la montée** (étirer ses 4 mesures au tempo de A, puis glisser), mélange autorisé jusqu'à 6-8 %, mix double / moitié | Fait enfin sonner deux rythmes ensemble | Moyen |
| 5 | **Grille fiable** : *Beat This!* (MIT, CPU) sur la mémoire, entrées et sorties sur des phrases de 8 mesures | Corrige les 53 % de morceaux mal mesurés | Moyen |
| 6 | **Pistes séparées** : d'abord une séparation percussions / harmonie quasi instantanée, puis Demucs (≈ 1,5 × la durée sur CPU, juste dans l'avance) | Le plus gros saut de qualité, le plus coûteux | Élevé |
| 7 | **Banc d'écoute** : bouton de note 1 à 5 sur chaque transition dans l'app, journal pour régler les probabilités | Remplace « pas si ouf » par des chiffres | Faible |

Décision produit toujours en attente, qui change beaucoup le rendu : **durée de chaque morceau** (en entier, ou 30 à 90 s comme en club, cf. [`../recherche/dj/scene-fr.md`](../recherche/dj/scene-fr.md)).
