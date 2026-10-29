# Transitions sur les plateformes de streaming (état fin octobre 2026)

Audit web du 2026-10-28. Légende : **[S]** fait sourcé (lien), **[D]** déduction de notre part,
**[A]** anecdote d'utilisateur ou de testeur (un seul témoignage, non mesuré).
Aucune plateforme ne publie de spécification chiffrée (durées, fréquences de coupure, courbes) :
tout ce qui est précis vient soit d'un brevet, soit de l'éditeur visible dans l'app.

## Vue d'ensemble

| Plateforme | Transition « intelligente » | Crossfade simple | Accès |
|---|---|---|---|
| Spotify | **Mix** (playlists perso, styles + éditeur), **Automix** (playlists Spotify choisies) | oui, curseur (1–12 s selon guides tiers) | Premium seulement ; tout désactivé via Spotify Connect |
| Apple Music | **AutoMix** (iOS 26, amélioré iOS 27) | oui, 1–12 s | abonné, catalogue Apple Music seulement |
| Deezer | non (rien d'annoncé) | oui, 1–30 s, Android (Labs → général fin 2025) | — |
| YouTube Music | non | **non** (extensions Chrome tierces seulement) | — |
| Amazon Music | non | incertain (sources contradictoires, peut-être desktop) | — |
| Tidal | non | **non** (retiré en 2018, pas revenu) | — |
| SoundCloud / Pandora | non | non / non établi | — |

## 1. Spotify

### 1a. Mix (playlists mixées) — le plus proche de notre projet
- **Lancement** : bêta Premium 2025-08-19, déployé à tous les Premium éligibles 2025-09-22 ; desktop annoncé 2026-05-19 ; « Smart Reorder » 2026-02-25 (réordonne la playlist par BPM et tonalité) ; courbes d'effet déplaçables à la main (mise à jour discrète, ~mi-2026). [S] [newsroom tag transitions](https://newsroom.spotify.com/tag/transitions), [Smart Reorder](https://newsroom.spotify.com/2026-02-25/smart-reorder-playlist-mixing/), [TechRadar](https://www.techradar.com/audio/spotify/spotify-didnt-tell-anyone-it-updated-its-song-mixing-feature-and-users-are-obsessed-with-it-now-im-putting-even-more-pride-into-how-i-curate-my-dj-set-playlists)
- **Périmètre** : playlists créées par l'utilisateur ; les comptes gratuits écoutent un mix comme une playlist normale ; via Connect, pas de transitions ; Auto est le seul réglage qui survit au mode aléatoire. [S] [support Spotify](https://support.spotify.com/us/article/mixed-playlists/), [Yahoo/TechRadar](https://tech.yahoo.com/audio/articles/havent-stopped-using-spotifys-custom-130000402.html)
- **Affichage** : BPM et clé Camelot de chaque titre ; deux formes d'onde, grille de mesures (traits longs), temps (traits courts), premiers temps en vert ; glisser une forme d'onde = déplacer le point d'entrée/sortie ; retour automatique si on dépasse un point valide. [S] [LETT Music](https://www.lettmusic.com/blog/how-to-arrange-spotify-playlists)
- **Durée** : menu **2 / 4 / 8 mesures**, proposé seulement quand Spotify détecte une grille de temps nette ; sinon pastille « ! » à côté du tempo et seule une transition courte est possible. [S] [LETT](https://www.lettmusic.com/blog/how-to-arrange-spotify-playlists). Un fil communautaire signale un plafond de 8 mesures jugé court pour la trance/techno ; un autre utilisateur dit avoir vu 12 mesures dans un cas, 4 dans un autre, sans logique visible. [A] [communauté](https://community.spotify.com/t5/Your-Library/Help-understanding-the-new-MIX-feature/m-p/7117514/highlight/true)
- **Pas de time-stretch ni de transposition** dans Mix : on ne change ni le tempo ni la clé, on ne superpose jamais plus de deux titres. [S] [Yahoo/TechRadar](https://tech.yahoo.com/audio/articles/havent-stopped-using-spotifys-custom-130000402.html)
- **Trois pistes d'automation par transition** : Volume (bleu), EQ 3 bandes graves/médiums/aigus (jaune), Effet = balayage de filtre passe-bas ou passe-haut (violet). [S] [support](https://support.spotify.com/us/article/mixed-playlists/), [LETT](https://www.lettmusic.com/blog/how-to-arrange-spotify-playlists)

**Styles** (libellés de l'app tels que rapportés par LETT ; Spotify ne nomme officiellement que Fade et Rise) :

| Style | Recette | Remarque [D] |
|---|---|---|
| Auto | Spotify choisit le style selon tempo, clé et « autres attributs » | logique non publiée |
| Fade | fondu enchaîné, échange des basses vers le milieu | le défaut sûr |
| Rise | chevauchement, échange des basses **à la fin** ; passe-bas sur l'entrant, passe-haut sur le sortant | montée : l'entrant reste étouffé puis s'ouvre |
| Blend | chevauchement, fondu EQ 3 bandes progressif | bande par bande, pas de filtre |
| Wave | échange des basses au centre ; passe-bas en entrée et en sortie | effet « sous l'eau » des deux côtés |
| Melt | l'entrant monte pendant que le sortant descend ; basses au centre ; passe-haut en entrée/sortie | « fondu » léger, sans basses au milieu |
| Slam | bascule franche du volume au centre | coupe sèche calée sur la grille |

Point clé : **la règle d'or de tous les styles est l'échange des basses** (jamais deux basses pleines
en même temps) ; ce qui varie, c'est *quand* (milieu / fin) et le filtre d'habillage. [D]

**Réception** : très bien reçu en pop/dance/électro (220 M d'heures de playlists mixées au 2026-02 [S] newsroom) ; Auto « place parfois l'entrée du titre suivant à un endroit aléatoire du titre en cours » et marche mieux à BPM proches [A] [TechRadar via recherche] ; demandes récurrentes : transitions plus longues, contrôle de tempo, API publique. [A]

### 1b. Automix (ancien) et AI DJ
- **Automix** : réglage Premium dans Lecture ; « transitions enchaînées et calées sur le temps » sur **certaines playlists Spotify**, y compris en aléatoire. Pas de détail technique publié. [S] [support Spotify](https://support.spotify.com/us/article/tracks-transitions/)
- **AI DJ** : surtout un commentaire vocal entre titres ; des utilisateurs disent que les enchaînements sans blanc ne marchent bien qu'en mode DJ et demandent leur généralisation. [A] [communauté](https://community.spotify.com/t5/Live-Ideas/Enable-seamless-AutoMix-transitions-by-default-not-just-in-AI-DJ/idi-p/7081313)

### 1c. Brevet « Systems and methods for automatic mixing of media »
US 10,721,556 B2 (famille 9,883,284 / 10,165,357 / 11,558,692), Spotify AB, priorité 2013, inventeurs dont G. Söderström. [S] [Google Patents](https://patents.google.com/patent/US10721556B2/en)
- **Points de mix issus des utilisateurs** (crowdsourcing) : le début du chevauchement = **médiane** des valeurs choisies par les utilisateurs (ou moyenne/mode).
- **Conflit de règles** entre deux titres : durées moyennées (exemple : sortie 6 s + entrée 4 s → 5 s) ; ou priorité au titre ayant le plus d'échantillons, ou au sortant, ou à l'entrant.
- **Courbes de volume** nommées : *smooth* (linéaire), *curvy* (cosinus), *sharp* (carré), *none*.
- **Tempo** : accélérer l'un, ralentir l'autre pendant le chevauchement (profils *playful/exact/bouncy*) ; **hauteur** : *return to original / begin pitched / stay pitched*.
- **Effets** possibles : flanger, delay/écho, réverb, distorsion, octave, vibrato.
- **Repli** : sans règle propre à la paire, on compose à partir des règles de chaque titre ; sans chevauchement, une pause fixe.
- **Droits** : une base de licences dit si l'ayant droit autorise seulement le crossfade ou le remix complet. [D] Ceci explique probablement l'absence de time-stretch dans Mix.

## 2. Apple Music AutoMix

- **Annonce** : WWDC 2025, iOS 26 ; activé par défaut ; remplace le réglage Crossfade dans Réglages > Apps > Musique > Transitions. Pas une fonction Apple Intelligence (iPhone 11 et +), Mac Apple silicon seulement. [S] [MacRumors](https://www.macrumors.com/2025/06/12/ios-26-automix-apple-music/), [support Apple](https://support.apple.com/en-us/105067)
- **Technique déclarée** : analyse des caractéristiques audio par IA, **time-stretch + beatmatching**, moment de transition choisi « selon la clé et le tempo ». Pas de durée fixe. [S] [MusicTech](https://musictech.com/news/gear/apple-music-automix-ai/), [Forbes](https://www.forbes.com/sites/prakharkhanna/2025/06/09/apple-music-gets-3-new-features-with-ios-26-wwdc-2025-recap/)
- **Hiérarchie de repli** déclarée par Apple : AutoMix « choisit le type de transition selon la musique » — parfois seulement **supprimer le silence** de début/fin, parfois **un simple fondu**. [S] [guide Apple](https://support.apple.com/en-hk/guide/music/aside/glosa3795b5d/mac)
- **Refus explicites** : album joué dans l'ordre ; genres ou tempos incompatibles ; titres importés ou achetés iTunes ; audio hi-res ; Apple Watch, Android, Windows. [S] [support Apple](https://support.apple.com/en-us/105067)
- **Style iOS 26** : un effet « sous l'eau » (filtre passe-bas, [D]) quasi systématique, transitions jugées uniformes. [S] [9to5Mac](https://9to5mac.com/2026/07/16/ios-27-makes-one-of-my-favorite-apple-music-features-even-better/)
- **iOS 27 (automne 2026)** : transitions plus variées et plus naturelles ; **remixe intros/outros** pour caler le tempo, **répète des passages** d'intro/outro pour faire durer le pont (boucles) ; arrive sur Apple TV et HomePod. [S] [9to5Mac](https://9to5mac.com/2026/07/16/ios-27-makes-one-of-my-favorite-apple-music-features-even-better/), [MBW](https://www.musicbusinessworldwide.com/apple-music-to-expand-lyrics-translation-upgrade-automix-and-lossless-audio-this-fall/)

**Critiques concrètes** (surtout iOS 26) :
- démarre **trop tôt**, ampute ~30 s de fin de titre (Reddit/TikTok) [A] [TechRadar](https://www.techradar.com/audio/apple-music/apple-music-fans-are-obsessed-with-automix-in-ios-26-but-one-big-flaw-could-be-its-downfall) ; jusqu'à **1 min sautée**, une fois 1 min entendue sur 3 [A] [How-To Geek](https://www.howtogeek.com/i-disabled-apple-music-automix/) ;
- titre suivant **plaqué par-dessus** puis corrigé 1–2 s après ; bégaiements « disque rayé » ; ne se déclenche pas entre deux titres qui s'y prêtent [A] How-To Geek ;
- ABBA « Keep An Eye on Dan » : accords finaux (clin d'œil à « S.O.S. ») couverts par le titre suivant ; « on n'entend presque jamais la fin d'un morceau » [A] [BGR](https://www.bgr.com/2059450/how-to-turn-off-automix-apple-music-worst-feature/) ;
- Kate Bush → Limp Bizkit : enchaînement incompréhensible [A] [heise](https://heise.de/-11139247) ;
- positif : « la plupart du temps on ne remarque pas qu'il agit » [S] [MacStories](https://www.macstories.net/stories/ios-and-ipados-26-the-macstories-review/15/) ; meilleur en électro/hip-hop qu'en rock/jazz/classique [A].

## 3. Autres plateformes
- **Deezer** : crossfade 1–30 s (Deezer Labs Android, puis tous les Android oct. 2025) ; aucune annonce de mix calé sur le temps (réponse de forum mars 2026). [S] [support Deezer](https://support.deezer.com/hc/en-gb/articles/115003862085-Crossfade), [communauté](https://en.deezercommunity.com/features-feedback-44/new-feature-available-crossfade-on-android-81435)
- **YouTube Music** : pas de crossfade natif fin 2026 ; extensions tierces (YouTube Playlist Crossfade, SyncMix avec points d'entrée/sortie manuels) ; le client tiers SimpMusic propose un « crossfade style DJ » ≤ 30 s avec un mouvement de passe-haut, sans détection de tempo. [S] [Chrome Web Store](https://chromewebstore.google.com/detail/gkadacfgimieldlpdallcdfnodkfjhlp), [SimpMusic](https://www.simpmusic.org/blogs/en/crossfade-beta)
- **Amazon Music** : aucune doc officielle trouvée ; sources contradictoires (desktop seulement ?) ; Sonos fait le fondu à sa place. [A]
- **Tidal** : crossfade retiré en 2018, pas revenu. **SoundCloud** : rien. **Pandora** : rien d'établi. [A] guides tiers ([Viwizard Tidal](https://www.viwizard.com/tidal-music-tips/tidal-crossfade.html))
- **Recherche académique** (hors plateformes) : détection de points de bascule en EDM, ~96 % jugés utilisables [S] [Zehren et al. 2020](https://arxiv.org/abs/2007.08411) ; le choix du point de mix reste « le moins étudié » et les logiciels DJ y sont « globalement insatisfaisants » [S] [TISMIR](https://transactions.ismir.net/articles/288).

## 4. Ce qui ressort (synthèse)
1. **Deux philosophies.** Spotify Mix : grille de mesures + EQ/filtre, *sans* toucher au tempo, durées courtes (2/4/8 mesures), contrôle utilisateur. Apple : time-stretch + beatmatching + (iOS 27) boucles d'intro/outro, entièrement automatique, aucun réglage.
2. **Les reproches visent le placement, pas le son.** Les plaintes portent sur des fins coupées, des entrées au mauvais endroit, des déclenchements imprévisibles ; personne ne se plaint d'un EQ mal réglé.
3. **Tout le monde a une échelle de repli** : transition riche → simple fondu → retrait des silences → rien (albums, genres/tempos incompatibles, pas de grille nette).
4. **Le respect de l'œuvre est une attente forte** : albums dans l'ordre exclus d'office chez Apple ; demandes « laissez-moi entendre la fin ».

## Ce qu'on peut reprendre

**Transposable dans notre architecture** (analyse Spotify : beats/bars/sections/tonalité ; moteur PipeWire avec ~20 s d'avance, deux voix, filtre, EQ par morceau, Rubber Band, boucle) :
- **Le vocabulaire de styles de Spotify Mix** comme recettes paramétrées : *quand* on échange les basses (milieu / fin / jamais de recouvrement) × *quel* habillage (passe-bas, passe-haut, EQ 3 bandes, aucun). Notre EQ par morceau + filtre suffit pour Fade, Rise, Blend, Wave, Melt, Slam.
- **Durées en mesures (2/4/8, voire 16)** calées sur les `bars` de l'analyse, avec **condition « grille nette »** : sous un seuil de confiance des beats/bars, on interdit les longues transitions et on retombe sur une courte.
- **Échelle de repli à la Apple** : mix calé → fondu court → simple retrait des silences de fin/début (on a `sections` et le volume) → enchaînement sec. Refus d'office : album en ordre, écart de tempo trop grand.
- **Boucle d'intro/outro (iOS 27)** : nous avons la boucle et 20 s d'avance ; répéter une mesure d'outro pour attendre un premier temps de l'entrant est faisable et répond à la critique « entrée au hasard ».
- **Time-stretch léger** pendant le recouvrement (ce que Mix ne fait pas) via Rubber Band, borné à de petits écarts ; le brevet Spotify décrit même l'étirement des deux titres l'un vers l'autre.
- **Courbes nommées** du brevet (linéaire / cosinus / carré) comme base des automations de volume.
- **Garde-fou anti-amputation** : ne jamais démarrer la sortie avant la dernière section « chantée/pleine » ; viser la dernière section de l'analyse ; plafonner la part du titre coupée. C'est le reproche n°1 fait à Apple.
- **Smart Reorder** (tri par BPM et clé Camelot) : faisable puisque l'analyse donne tempo et clé, mais seulement si l'utilisateur l'accepte (on ne contrôle pas forcément la file).

**Non transposable ou à écarter** :
- **Points de mix crowdsourcés** (médiane des choix des utilisateurs du brevet) : pas de base d'utilisateurs ; au mieux mémoriser localement les corrections de l'utilisateur.
- **Analyse IA propriétaire d'Apple** (et ses remixes d'intro) : on n'a que l'analyse publique de Spotify, sans détection de voix ni de « drop » ; l'énergie par section reste approximative.
- **Effets du brevet (flanger, distorsion, vibrato, octave)** : hors du « mode DJ doux » recherché ; l'écho/delay seul pourrait servir de sortie de secours sur un titre sans grille.
- **Changement de hauteur/clé** pendant la transition : risqué à l'oreille, et aucune plateforme grand public ne le fait.
- **Contrôle des droits** (base de licences du brevet) : sans objet pour un usage local et personnel, mais la retenue de Spotify (pas de stretch dans Mix) rappelle que la fidélité au morceau est attendue.
