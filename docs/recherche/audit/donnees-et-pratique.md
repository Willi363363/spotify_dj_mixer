# Audit (1/2) : données de vrais mixes et pratique des DJ

Suite de [`README.md`](README.md) (légende des statuts). Ne refait pas `docs/recherche/`.

## 1. Données de vrais mixes exploitables légalement

| Jeu de données | Contenu | Genres | Licence / accès | Ce qu'on peut en tirer sans audio | Statut |
|---|---|---|---|---|---|
| **1001Tracklists (Kim et al., ISMIR 2020)** | 1 557 mixes, 13 728 morceaux, 20 765 transitions | Surtout house et trance | Métadonnées obtenues avec la permission du site | Statistiques publiées seulement | [V] [arXiv](https://arxiv.org/abs/2008.10267) |
| **djmix-dataset (DAFx 2022)** | 5 040 mixes, 50 742 transitions ; listes de morceaux, étiquettes | House 1 555, Techno 1 547… **Hip Hop 24, Reggae 2, Dancehall 0** [M] | Dépôt sans licence ; article CC BY 4.0 ; le paquet `djmix` télécharge l'audio (**à ne pas utiliser**) | Liste des mixes et étiquettes | [V] [dépôt](https://github.com/mir-aidj/djmix-dataset) |
| **Raveform (TISMIR 2026)** | 4 902 mixes, 53 780 transitions ; 1 423 morceaux annotés (Intro, Buildup, Breakdown, Drop, Cooldown, Outro) | Techno, trance, DnB, house | Article CC BY 4.0 | Annotations de structure EDM (détecteur de drop) | [V] [TISMIR](https://transactions.ismir.net/articles/288) |
| **NIME 2021** | Gains par bande estimés par optimisation convexe | Électronique | Code sans licence | La méthode ; aucune statistique agrégée | [V] [NIME](https://nime.org/proc/nime2021_87/) |
| **DAFx 2022 djmixer-estimation** | Fader + égaliseur 3 bandes (graves < 180 Hz, médiums 1 kHz, aigus > 3 kHz) | Électronique | Code **MIT** | Méthode et modèle d'égaliseur | [V] [PDF](https://mac.kaist.ac.kr/pubs/KimYangNam-dafx2022.pdf) |
| **UnmixDB / Mixotic** | Mixes synthétiques à fondus linéaires, vérité terrain exacte | Électronique, Creative Commons | CC BY-NC-ND 4.0 | Tester un banc (pas des pratiques réelles) | [V] [Zenodo](https://zenodo.org/record/1422385) |
| **CUE-DETR (2024)** | ~21 000 points de repère posés par 4 DJ sur ~5 000 morceaux | EDM | Modèle MIT | Place des repères dans la phrase | [V] [arXiv](https://arxiv.org/abs/2407.06823) |

### Chiffres publiés

| Mesure | Valeur | Source | Pour nos genres |
|---|---|---|---|
| Longueur | Pics à chaque multiple de **32 temps** (≈ 15 s à 127 BPM) | [V] Kim 2020 | 8 mesures = 12 s à 160 BPM, 19,2 s à 100 BPM |
| Tempo | 86,1 % < 5 %, 94,5 % < 10 %, 98,6 % < 20 % | [V] Kim 2020 | Plafond de 6 % du mélange cohérent |
| Tonalité | 2,5 % des morceaux transposés, 94 % d'un demi-ton | [V] Kim 2020 | Ne pas transposer |
| Accord entre DJ sur les repères | 40,4 % à une mesure près, 73,6 % à 8 mesures | [V] Kim 2020 | Placement prévisible (cohérent avec « placement validé ») |
| Frontière perçue | Sur l'arrivée complète de B (52 %) | [V] Kim 2020 | L'oreille retient l'arrivée complète de B comme « le changement » [I] |

Ce qui manque partout [V] : courbes moyennes mesurées sur de vrais DJ, moment réel de l'échange des basses, part des effets, et tout chiffre sur le rap, le dancehall, le shatta, le bouyon.

Légalement : lire les articles et reprendre leurs chiffres et méthodes ; réutiliser le code MIT (`djmixer-estimation`, `beat_this`, `cue-detr`) ; ré-implémenter depuis l'article ce qui n'a pas de licence ; ne télécharger l'audio Creative Commons que si le développeur le décide.

## 2. Pratique des DJ en club pour nos genres

Aucune source technique sérieuse pour le dancehall, le shatta, le bouyon, l'amapiano [V]. Pour le rap et l'open format : Digital DJ Tips, We Are Crossfader, Mixgraph.

| Technique | Exécution et longueur | Usage | Source |
|---|---|---|---|
| Dropmix « sur le 4 » | B lancé **un temps avant** la mesure, chevauchement d'un temps | Hip-hop, R&B | [V] [Digital DJ Tips](https://www.digitaldjtips.com/dropmix-like-a-pro-hip-hop-dj/) |
| Échange des basses | Transition de 8 mesures, B sans graves, **échange à la 4ᵉ** | Partout | [V] [Digital DJ Tips](https://www.digitaldjtips.com/?p=2799229) |
| Blend court hip-hop | Rarement plus de 4 mesures, parfois 8 | Hip-hop | [S] [forum DJ TechTools](https://forum.djtechtools.com/t/mixing-hip-hop/22555) |
| Long mélange | 16 à 32 mesures, à abandonner si les tonalités se heurtent | House, techno | [V] [Mixgraph](https://www.mixgraph.io/learn/dj-transition-techniques) |
| Boucle et montée | Boucle de **4 ou 8 temps** de A, filtre, réverbération, bruit qui montent ; erreurs : en abuser, monter vers un morceau plus calme | Monter vers un pic | [V] Mixgraph |
| Balayage de filtre | A en passe-bas, B en passe-haut qui s'ouvre, ses graves en dernier | Textures différentes | [V] Mixgraph |
| Resserrement de boucle | Boucle d'un temps sur un mot de A divisée, hachée ; 8 temps de frein par à-coups, frein final sur le drop | Performance | [V] [We Are Crossfader](https://wearecrossfader.co.uk/blog/12-high-energy-dj-transitions/) |
| Fente + coupe nette | Au drop de B : graves échangés, A en passe-haut + réverbération, fader de A fermé d'un coup | Performance | [V] We Are Crossfader |
| Doubler un refrain | Saut de 16 mesures en arrière | Hip-hop | [V] [We Are Crossfader](https://wearecrossfader.co.uk/blog/how-to-mix-hip-hop/) |
| Frein | Environ **un temps**, écho d'un demi-temps en option | Tous genres | [V] [We Are Crossfader](https://wearecrossfader.co.uk/blog/five-ways-djs-mix-songs-together) |
| Drop swap | La montée de A se joue, **on coupe A sur le drop de B** | EDM, open format | [S] [Mixgraph](https://www.mixgraph.io/glossary/drop-swap) |

### Ce qui sonne « amateur »

| Défaut | Chez nous |
|---|---|
| Deux basses ensemble | Évité |
| Toujours la même technique | **Oui** : squelette unique |
| Montée qui débouche sur plus calme | **Oui** quand l'énergie baisse |
| Voix qui se chevauchent, voix coupée en plein mot | **Oui** : rien ne regarde la voix |
| Effet qui cache un mauvais mix | Risque : la boucle d'une mesure masque l'absence de vraie musique de A |

Pour nos genres [I] : la pratique club rap repose sur des transitions courtes (1 temps à 8 mesures), des points d'entrée préparés (refrain, gimmick) et des gestes marqués. Le compromis qui colle à la pratique et au goût : **geste marqué sur A + B annoncé par sa batterie**. Les longues montées existent, mais la boucle de A y change.

Tempos : bouyon ~152-160, amapiano 108-115 [S] ; le mix double / moitié rap ↔ bouyon reste utile.
