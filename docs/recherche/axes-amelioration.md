# Axes d'amélioration : ce que font les meilleurs systèmes

Recherche du 2026-10-26. **[V]** vérifié dans la source citée, **[I]** inférence. Synthèse et plan : [`../revue/README.md`](../revue/README.md).

## Ce qu'ils font et pas nous

| Technique | Qui | Ce qu'il faut | Pour nous |
|---|---|---|---|
| Transition par pistes séparées : effet (réverbération…) sur la seule voix de A [V] | djay Automix AI + Neural Mix (voix, batterie, basse, harmonie) [1][2] | Séparation de sources | Faisable sur CPU, serré dans l'avance [I] |
| Préréglages de pistes : *Swap* (les pistes de A s'arrêtent au milieu, celles de B démarrent, décalage de 0/1/2/4 temps), *Crossfade* plus long sur la batterie [V] | DJ.Studio [3] | Pistes | Oui une fois les pistes disponibles [I] |
| Coupe des pistes incompatibles : voix de A atténuée si les voix se chevauchent plus de 2 s, batterie atténuée si les rythmes diffèrent [V] | Mosaikbox, ISMIR 2024 [4] | Pistes + détection de voix | Oui [I] |
| Écho sur la voix seule [V] | Serato, « FX Vocal Echo » [5] | Piste voix | Oui [I] |
| Mix à tempo double ou moitié au-delà de 25-30 % d'écart [V] | DJ.Studio [6] | Rapport 2:1 | Facile [I] |
| Étirement + calage des temps [V] | Apple Music AutoMix [7] | Déjà là (rubberband) | — |
| Courbes de volume, EQ, effets éditables, préréglages [V] | Spotify Mix (Premium) [9] | — | Déjà notre modèle (recettes) |

Rekordbox 7 sépare en 4 pistes sans automatiser de transitions avec [V] [10].

## Règles chiffrées

- **Longueur** : sur 1 557 mixes réels et 20 765 transitions, les durées culminent à chaque **multiple de 32 temps (8 mesures)** [V] [11].
- **Tempo** : 86,1 % des morceaux décalés de moins de 5 %, 94,5 % de moins de 10 % ; 2,5 % transposés, presque toujours d'un demi-ton [V] [11]. Mosaikbox accepte ±8 % [V] [4].
- **Points d'entrée prévisibles** : entre deux DJ, 40,4 % des points tombent à une mesure près, 73,6 % à 8 mesures près [V] [11].
- **EQ** (Vande Veire) : B monte basses et aigus coupés, puis basses et aigus **basculent d'un coup** de A vers B ; jamais deux basses ensemble [V] [12].
- **Trois types** (Vande Veire) [V] [12] : *double drop* (drops alignés, entrée 16 mesures avant), *rolling* (enchaînement sur 16 mesures), *relaxed* (B part de son début, pour respirer). Enchaînés par une **chaîne de Markov** : après *relaxed* → *rolling* 0,7 / *double drop* 0,3 ; après *rolling* ou *double drop* → *rolling* 0,8 / *relaxed* 0,2 ; jamais deux *double drops* de suite.
- **Écoute** : chevauchement de voix toléré sur une mesure ; choix par style noté 3,89 contre 2,39 sans [V] [12]. Mosaikbox : niveau ramené à **−14 LUFS**, transitions de 16 mesures ; 3,457 avec la coupe des pistes contre 3,076 sans [V] [4].
- Aucun modèle neuronal de transition directement utilisable : DJtransGAN n'apprend qu'un EQ et un fader [V] [13].

## Outils locaux (Linux, Python, CPU)

| Outil | Licence | CPU | Apport |
|---|---|---|---|
| **Beat This!** (ISMIR 2024) | MIT, poids inclus [V] | Oui, modèle « small » de 8,1 Mo [V] [14] | Grille temps / mesures fiable sur la mémoire |
| BeatNet | CC-BY-4.0 [V] | Temps réel [V] [15] | Suivi de mesure en flux |
| madmom | Code BSD, **modèles non commerciaux** [V] [16] | Oui | Usage personnel seulement |
| Demucs htdemucs | MIT [V] | ≈ 1,5 × la durée sur CPU [V] [17] | 4 pistes ; 30 s de A ≈ 45 s de calcul, juste dans 50 s [I] |
| Séparation percussions / harmonie par filtre médian (librosa) | ISC [I] | Quasi instantané [I] | « Fausses pistes » batterie / reste (utilisé par Vande Veire) [V] [12] |
| All-In-One (allin1) | MIT [V] | Lourd, à l'arrêt depuis 2024 [V] [19] | Couplets / refrains |
| pyloudnorm | MIT, BS.1770-4 [V] [20] | Négligeable | Niveau A / B égalisé |
| Essentia | AGPL-3.0 [V] | Oui | Tonalité, détection de voix (usage personnel) |

## Genres percussifs

Aucune source sur les pratiques DJ du shatta et du bouyon. Extrapolé du hip-hop et du dancehall [V] [21][22] : **mix double / moitié**, **drop swap** (coupe sur le 1 de A juste avant son drop, impact + nappe de réverbération ou écho gelé de A, drop de B immédiat).

## Sources

1. https://djmag.com/news/new-djay-ai-ios-adds-improved-ai-mixing
2. https://community.algoriddim.com/t/now-available-major-update-to-djay-pro-ai-on-ios/13690
3. https://help.dj.studio/en/articles/9292881-making-mashups-with-stem-separation
4. https://repositum.tuwien.at/bitstream/20.500.12708/212628/1/Sowula-2024-Mosaikbox%20Improving%20Fully%20Automatic%20DJ%20Mixing%20Through%20Rule-ba...-vor.pdf
5. https://support.serato.com/hc/en-us/articles/5700921209615
6. https://help.dj.studio/en/articles/15359028-double-and-half-tempo
7. https://musictech.com/news/gear/apple-music-automix-ai/
9. https://www.tomsguide.com/entertainment/music-streaming/spotifys-new-mixing-feature-lets-you-dj-your-own-playlists-heres-how-it-works
10. https://www.digitaldjtips.com/rekordbox-v7-2-8-adds-4-stem-separation/
11. https://arxiv.org/abs/2008.10267 (Kim et al., ISMIR 2020)
12. https://asmp-eurasipjournals.springeropen.com/track/pdf/10.1186/s13636-018-0134-8 (Vande Veire & De Bie, 2018)
13. https://arxiv.org/abs/2110.06525 (DJtransGAN)
14. https://github.com/CPJKU/beat_this
15. https://github.com/mjhydri/BeatNet
16. https://github.com/CPJKU/madmom/blob/main/LICENSE
17. https://github.com/adefossez/demucs
19. https://github.com/mir-aidj/all-in-one
20. https://github.com/csteinmetz1/pyloudnorm
21. https://www.londonsoundacademy.com/blog/10-hip-hop-dj-transitions
22. https://djclass.net/learn/mixing-between-genres
