# 03 · Boucle par saut

**Question** : peut-on rallonger un passage en faisant revenir Spotify au début de la mesure, sans que ça s'entende ?

Script : [`../../outils/loop-test.js`](../../outils/loop-test.js). Analyse : [`../../outils/analyse-boucle.py`](../../outils/analyse-boucle.py).

## Protocole

1. Choisir la section la plus forte, prendre sa première mesure (ou ses deux premières).
2. Quand la position approche la fin de la mesure, appeler `Spicetify.Player.seek(début)`, en avance de `LEAD` ms.
3. Répéter 4 à 8 fois. Relever l'avance réelle et le temps de réaction annoncé par Spotify.
4. Enregistrer la sortie son, mesurer la **période réelle** de la boucle (autocorrélation) et les silences.

## Essais

| Essai | Morceau | Boucle | `LEAD` | Écoute |
|---|---|---|---|---|
| 1 | « Levrette ou missionnaire » | 2 mesures, ×4 | 40 ms | jugé propre |
| 2 | idem | 2 mesures, ×6 | 40 ms | jugé propre |
| 3 | « Around the World » | 1 mesure, ×8 | 40 ms | « bizarre, pas clair comme coupe » |
| 4 | idem, enregistré | 1 mesure, ×8 | 40 ms | mesuré, ci-dessous |
| 5 | idem, enregistré | 1 mesure, ×8 | **115 ms** | « clair » |

## Mesures (Around the World, mesure de 1,979 s)

| Mesure | `LEAD` 40 ms | `LEAD` 115 ms |
|---|---|---|
| Réaction annoncée par Spotify | 31 à 56 ms | 32 à 54 ms |
| Écart entre deux sauts | 2,052 à 2,055 s (un à 2,124) | 1,977 à 1,988 s |
| **Période réelle du son** | **2,058 s** (+79 ms) | **1,988 s** (+9 ms) |
| Silences de 5 à 10 ms | 2 reprises sur 8 | 4 reprises sur 8 |

## Ce qu'on en tire

- **Spotify ment sur sa position** : `getProgress()` annonce la nouvelle position environ 80 ms avant que le son ne reparte vraiment. D'où le rythme décalé de l'essai 3.
- **L'écart est stable** (quelques ms de gigue) : une avance fixe le corrige. **115 ms** sur cette machine, à rendre réglable.
- **Les micro-silences viennent de Spotify** et ne se corrigent pas par le calage. En E1, ils restent ; en E2, le module peut rejouer la boucle depuis sa mémoire ou combler le trou.
- **Le premier temps de la mesure** choisie avait une fiabilité de 0,401 : une boucle peut aussi sonner faux parce qu'elle démarre sur le mauvais temps.

## Conclusion

✅ Boucles et sauts calés sur le temps sont faisables en E1, à 9 ms près. ⚠️ Un petit « tic » est possible sur une boucle répétée ; sur une transition unique, il passe mieux.
