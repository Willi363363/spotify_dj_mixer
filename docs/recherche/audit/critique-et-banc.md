# Audit (2/2) : critique du programme et banc de mesure

Suite de [`README.md`](README.md) (légende des statuts). Chiffres [M] = lecture du code à 160 BPM (mesure 1,5 s) et 100 BPM (2,4 s).

## 3. Critique du programme

**Déjà conforme** [M] : jamais deux basses ensemble ; échange net sur le drop de B ; B à plein avant son drop ; longueurs multiples de 4 mesures sur des débuts de phrase ; glissement de tempo temps par temps, double / moitié, plafond de 6 % ; A qui s'éteint 2 mesures après le drop.

### Écarts, style par style

| Style | Ce que fait le code [M] | Pratique réelle | Pourquoi ça peut sonner mal |
|---|---|---|---|
| Squelette `_douce` | B lancé 8 mesures de A avant son drop, plein à 70 %, sans graves ni aigus ; A à 0,4 au drop ; échange en ½ temps ; traîne de 2 mesures | Le DJ varie la **longueur**, ce qui porte la transition, et la sortie | Six styles, une seule dynamique |
| Boucle de A | Montée courte : 1 vraie mesure puis 8 mesures tirées de cette mesure ; frein : ~7 mesures d'une mesure en boucle ; à 98 BPM, 22 s d'une seule mesure (essai 22) | Boucle de 4 à 16 temps, modifiée toutes les 2 à 4 mesures | Une mesure répétée 8 fois s'entend comme une machine, un mot qui bégaie 8 fois |
| Montée de B | Les 8 mesures avant le drop, médiums à plein dès 70 % | En hip-hop, B entre souvent sur son refrain ou son intro instrumentale | Deux voix sur 2 à 4 mesures, deux harmonies si les tonalités se heurtent |
| Montée | Roulements jusqu'à **+7 demi-tons** | Roulements à hauteur fixe | Voix rap « dessin animé » [S] |
| Frein | ~7 mesures de boucle puis frein d'une mesure entière | Frein d'**environ un temps** sur une phrase réelle | Effet dilué : « aucun effet » (essai 22) |
| Filtre | A en passe-bas jusqu'à 200 Hz, B sans rien sous 250 Hz | Conforme à Mixgraph | Le plus proche de la pratique : 5, 5, 4 |
| Drop swap | Tension fabriquée en 4 temps (1,5 s à 160 BPM) | La vraie montée de A se joue (8 à 16 mesures), A coupé sur le drop de B | « B trop sec » (essai 16) |
| Mélange | 8 mesures, échange au centre | Conforme (8 mesures, échange à la 4ᵉ) | Ne finit pas sur le drop de B ; presque jamais tiré |
| Secours | B monte sur 1 mesure | — | Une mesure suffit à faire « B sec » |

### Écarts dans le choix (`dj-auto.js`)

| Point | Constat [M] | Effet |
|---|---|---|
| Mélange presque inaccessible | Tonalités sûres (≥ 0,4) et voisines exigées ; incertaines 12 fois sur 19 ; à 100 BPM, avance exigée 71,6 s > cible 60 s | Le style « clean de fou » presque jamais entendu |
| Énergie qui baisse → montée | Réserve « drop » : 2 montées sur 3 | « Montée qui débouche sur plus calme » (Mixgraph) |
| Variété | Habillage seulement ; longueur toujours ~8 + 2 mesures | « Toujours le même style » |
| Voix et tonalité ignorées pour les styles doux | `exitFor` ne compare que timbre, notes, section | Rien n'évite deux voix |

### Ce que disent les 19 notes de l'app (échantillon minuscule) [M]

| Groupe | Moyenne | n |
|---|---|---|
| Tonalité Spotify incertaine | **4,3** | 12 |
| Tonalité connue | **2,4** | 7 |
| B étiré et calé sous A (écart ≤ 10 %) | **3,25** | 12 |
| B non calé (≥ 24 %), rien sous 400 Hz | **4,3** | 7 |

Biais forts (n = 19, série de 1 et 2 entre 18 h 15 et 18 h 21). Deux hypothèses à tester, pas des conclusions : l'étirement abîme la batterie de B ; un B calé sous A fait entendre deux rythmes très proches qui se mélangent (en shatta, un calage faux de ¼ de temps s'entend).

## 4. Banc de mesure local

**Droit** : les conditions de Spotify interdisent d'enregistrer le contenu et de s'en servir pour entraîner un modèle d'IA [V] [User Guidelines](https://www.spotify.com/us/legal/user-guidelines/). Donc **jamais de fichier audio enregistré** : le banc ne garde que des mesures (quelques nombres par temps). Ce n'est pas un avis juridique.

| Niveau | Principe | Avantages / limites |
|---|---|---|
| 1. Annotation à l'oreille | Pendant l'écoute d'un **album mixé** sur Spotify, 4 touches dans l'app : B audible, échange des basses, A disparu, type de transition ; converties en mesures par la grille Spotify | Zéro audio ; précision ~1 temps ; 50 transitions par genre suffisent. Existence d'albums mixés shatta / bouyon non vérifiée |
| 2. Mesure automatique en mémoire | Sur le son en mémoire (rien sur disque) : énergie de 3 bandes par temps (graves < 180 Hz, médiums, aigus > 3 kHz), comparaison aux 8 mesures avant (A seul) et après (B seul) → longueur, place de l'échange, courbes par bande, effets détectés (boucle, écho, frein, blanc) ; méthode exacte Kim 2020 + DAFx 2022 si les originaux sont disponibles | Une ligne JSON par transition. Outils : Beat This! (MIT), librosa (ISC), CVXPY, djmixer-estimation (MIT), pyloudnorm |
| 3. Ses propres mixes | Mixxx avec des fichiers qu'il possède | Seule source de courbes exactes sur nos genres |

Ce que le banc calibre : `PRE_BARS` et la longueur totale, les courbes de A et de B, la durée et la place de l'échange, la traîne de A, la part des types de la chaîne de Markov.
