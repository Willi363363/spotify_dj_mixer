# Comment Spotify et les meilleurs systèmes construisent une transition

Recherche du 2026-10-26, après « les transitions sont horribles » (essais 21 à 24). **[V]** vérifié dans la source, **[S]** source tierce, **[I]** déduction. Complète [`spotify-transitions.md`](spotify-transitions.md) et [`veille-2026-10.md`](veille-2026-10.md).

## Ce qui change tout : la superposition finit sur le drop de B

- **Spotify** (ISMIR 2017, brevet US20200401619) [V] : une superposition est pénalisée si elle **ne finit pas** sur un drop ou une frontière de section des deux morceaux. La partie de B jouée pendant la superposition est donc ce qui **précède** son point fort.
- **Spotify** (brevet US20230409281, 2023) [V] : le point d'entrée de B est l'instant où **B atteint son plein volume** ; le point de sortie de A est l'instant où **A ne s'entend plus**. Au point fort de B, B est déjà à 100 %.
- **Vande Veire & De Bie 2018** [V] : pendant la montée, le **volume de B monte jusqu'au plein niveau** mais ses graves et aigus restent coupés ; **au point d'échange**, graves et aigus de B remontent d'un coup et ceux de A sont coupés ; **ensuite seulement**, le volume de A (médiums seuls) descend. Double drop : entrée 16 mesures avant, sortie de A sur 32.

Notre erreur (essais 21-24) : B encore en train de monter au drop, A presque coupé avant, puis une **marche de volume** au drop (« B pop », « A coupé de manière horriblement brève »).

## Courbes et tempo

| Point | Pratique | Statut |
|---|---|---|
| Volume | Égale puissance (−3 dB au centre) pour des signaux sans rapport ; linéaire (−6 dB) s'ils sont corrélés (deux grosses caisses calées : +3 dB de bosse dans les basses en égale puissance → raison d'échanger les basses) | [V] [I] |
| Asymétrie | B monte tôt et vite, A descend tard | [V] |
| Tempo | Spotify n'évalue que des paires à ≤ 5 BPM d'écart (±2,5 BPM par défaut au brevet) ; glissement temps par temps `d_n = (N−n)/N·d1 + n/N·d2` | [V] |
| Préréglages Spotify Mix | Tous reposent sur un échange des basses (Fade, Rise, Blend, Wave, Melt, Slam) ; 2, 4 ou 8 mesures, seulement si la grille est nette | [S] |
| Apple | Brevet 2010 (US8805693) : temps détectés dans les graves, courbes α / 1−α non forcément symétriques ; iOS 27 répète des passages pour faire le pont ; critiqué pour sauter jusqu'à 1 min et pour des B qui passent par-dessus A 1-2 s | [V] |

## Recette appliquée (2026-10-26)

| | B | A |
|---|---|---|
| Montée (8 mesures de A) | De −15 dB au plein volume en S, **plein à 70 %** puis tenu ; sans graves (sous 300-400 Hz) ni aigus (au-dessus de 6 kHz) | Plein jusqu'à mi-montée (son effet audible), puis descend à **0,4 (−8 dB)** au drop ; baisse sur chaque grosse caisse de B (side chain) |
| Drop | Graves et aigus rendus en ½ temps : **l'échange**, sans marche de volume | — |
| Après le drop | — | Continue de s'éteindre sur **2 mesures** (sauf frein et retour : écho seul) |

Pistes suivantes : mélange qui finit sur le drop de B (N = 8 mesures au-dessus de 120 BPM, 4 en dessous), tempo qui glisse sur la 2ᵉ moitié, boucler la dernière mesure de B avant son drop s'il en manque, éviter deux voix (coût sur la voix au choix des points).

## Sources

- https://archives.ismir.net/ismir2017/paper/000086.pdf
- https://patents.google.com/patent/US20200401619A1/en
- https://patents.google.com/patent/US20230409281A1/en
- https://patents.google.com/patent/US8805693B2/en
- https://asmp-eurasipjournals.springeropen.com/track/pdf/10.1186/s13636-018-0134-8
- https://www.hsu-hh.de/ant/wp-content/uploads/sites/699/2017/10/Fink-Holters-Z%C3%B6lzer-2016-Signal-matched-power-complementary-cross-fading-and-dry-wet-mixing.pdf
- https://www.lettmusic.com/blog/how-to-arrange-spotify-playlists
- https://9to5mac.com/2026/07/16/ios-27-makes-one-of-my-favorite-apple-music-features-even-better/
- https://www.howtogeek.com/i-disabled-apple-music-automix/
