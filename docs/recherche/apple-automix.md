# Apple Music AutoMix, et ce qu'on retient des deux

## Apple Music AutoMix (iOS 26)

Apple n'a publié **aucun détail d'algorithme** et aucun brevet rattaché n'a été trouvé. Ce qui est établi :

| Point | Détail | Source |
|---|---|---|
| Méthode | **Étirement temporel et calage des temps** ; la hauteur reste intacte quand le tempo change | [Apple Support](https://support.apple.com/guide/iphone/transition-songs-iphadf2fe1f4/ios), [MusicTech](https://musictech.com/news/gear/apple-music-automix-ai/) |
| Choix | Transitions fondées sur l'analyse de **tonalité et tempo** ; AutoMix choisit la transition selon la musique | Apple Support |
| Variété | Parfois un fondu, parfois une superposition calée, parfois **une courte pause** | [TapSmart](https://www.tapsmart.com/tips-and-tricks/apple-music-automix/) |
| Refus | **Renonce à la transition** quand aucune n'est assez propre | [MusicTech](https://musictech.com/news/music/apple-music-ios-26-updates/) |
| Silences | Retire les longs silences en début ou en fin de morceau | guide tiers |
| Périmètre | Playlists et stations ; pas les albums joués dans l'ordre, ni les fichiers locaux, ni le Dolby Atmos | [Mac Observer](https://www.macobserver.com/tips/automix-explained-ios-26/) |
| Calcul | Présenté comme de l'« intelligence » d'analyse ; ce n'est **pas** une fonction Apple Intelligence et elle n'exige pas d'iPhone récent ; « sur l'appareil » non confirmé par Apple | [MacRumors](https://www.macrumors.com/2025/06/12/ios-26-automix-apple-music/), [9to5Mac](https://9to5mac.com/2025/06/16/automix-apple-music-ios-26/) |

Apple ne propose **pas** d'effets (écho, filtre, boucle) : AutoMix est un mélange calé, sobre.

## Ce qu'on en retient pour le projet

| Idée | D'où | Ce que ça change chez nous |
|---|---|---|
| **Une transition = une recette de 5 ingrédients** (volume, égaliseur, filtre, effets, boucle), chacun une courbe sur N mesures | Spotify Mix | Réécrire `prepare()` comme un **compilateur de recettes** : nos transitions (montée, retour arrière, mix) deviennent des combinaisons d'ingrédients, faciles à varier et à régler |
| **Préréglages nommés** (Rise, Slam, Surge…) | Spotify Mix | Nos transitions validées deviennent des préréglages ; la montée validée ressemble à un « Loop halving » + passe-haut en entrée |
| **Loop halving** comme style de boucle officiel | Spotify Mix | Confirme notre montée par roulements |
| **Points de sortie et d'entrée choisis par coût** : premiers temps de mesure, drops et frontières de section favorisés, timbre et notes proches, pas de voix superposées, pas de zone trop calme | Article Spotify 2017 | Remplacer notre choix « première mesure fiable après N s » par cette **matrice de coût** ; on a déjà timbre, notes, volume, sections dans l'analyse |
| **Sortie dans les 25 % finaux, entrée dans les 20 % initiaux** | idem | Bornes simples à reprendre… sauf si on décide de jouer seulement 30 à 90 s par morceau (cf. [`dj/scene-fr.md`](dj/scene-fr.md)) |
| **Tempo qui glisse temps par temps** de A vers B pendant la transition | idem | Améliore notre mix : au lieu d'étirer B d'un bloc, étirer chaque temps progressivement |
| **15 % d'échecs dus aux temps mal détectés** | idem | Même problème que nous : le recalage sur les grosses caisses est indispensable |
| **Renoncer** quand le calage est impossible (« Beatmatch unavailable ») | Spotify, Apple | Notre règle « refuser la superposition » est la bonne ; préférer coupe ou écho |
| **Réordonner la playlist** pour enchaîner les morceaux compatibles | Spotify Mix, article 2017 | Ordre par plus court chemin dans l'espace tempo + tonalité + timbre |
| **Puissance constante** et limiteur pendant la transition | Brevet Spotify | Ajouter un limiteur en sortie de la maquette ; éviter les bosses de volume |
| **Retirer les silences** de début et de fin | Apple | Simple à faire avec l'analyse et le son en mémoire |
| Les **drops** repérés par les sauts de tête de lecture des auditeurs | Article Spotify 2017 | Inaccessible pour nous ; on garde la section la plus forte, recalée sur le son |

## Limites

- La composition exacte des préréglages Spotify et l'algorithme d'Apple restent **inconnus**.
- L'article de 2017 précède Spotify Mix : la méthode actuelle peut avoir changé.
