# Tests

Tests réalisés du **2026-10-23** au **2026-10-28** sur la machine de [`../environnement.md`](../environnement.md). Comment les rejouer : [`methode.md`](methode.md).

| # | Test | Question | Verdict |
|---|---|---|---|
| 01 | [Analyse audio](01-analyse-audio.md) | Spicetify donne-t-il encore tempo, temps, sections ? | ✅ Oui |
| 02 | [Vitesse de lecture](02-vitesse-lecture.md) | Peut-on ralentir ou accélérer la musique dans Spotify ? | ❌ Non, refusé |
| 03 | [Boucle par saut](03-boucle-par-saut.md) | Une boucle par saut est-elle propre ? | ✅ Rythme juste après calibrage, ⚠️ micro-silences |
| 04 | [Filtre PipeWire](04-filtre-pipewire.md) | Peut-on couper les basses de Spotify en direct ? | ✅ Oui, −17 dB |
| 05 | [Connexion locale](05-connexion-locale.md) | L'extension peut-elle piloter un programme local ? | ✅ Oui, 0,7 ms |
| 06 | [Série A : Spotify seul](06-serie-a-spotify.md) | Décisions, transition, volume, interface, file, pubs, ressemblance | ✅ sauf pubs non observées ; trou de changement 12 à 400 ms |
| 07 | [Série B : effets](07-serie-b-effets.md) | Égaliseur, écho, clics des balayages | ✅ égaliseur et écho, ⚠️ clics |
| 08 | [Série C : maquette E2](08-serie-c-maquette-e2.md) | Son retardé, mix avec échange des basses, calage du tempo, boucle, freinage | ✅ principe validé |
| 10 | [Preuve du calage](10-calage.md) | Les temps de A et B tombent-ils ensemble pendant une superposition ? | ❌ ancien calage : ~½ temps d'erreur ; ✅ grille de Spotify + correction : **0 à 10 ms** sur 5 paires rap FR |
| 13 | [Essai en direct des transitions v2](13-essai-direct-v2.md) | Le catalogue v2 tient-il sur de vrais morceaux, dans Spotify ? | ✅ 10 transitions jouées, son fidèle au rendu, aucun trou ni clic du moteur ; 4 défauts corrigés ; ⚠️ voix (V2, V3) et O5 ; **pas écouté** |

## Règle

Un résultat audio se juge **à l'oreille et sur un enregistrement**. Les positions annoncées par Spotify ont menti de 80 ms au test 03 : seules les mesures sur la sortie son font foi.

## Journal des notes d'écoute

`notes-ecoute.jsonl` (ou `DJ_NOTES`) : une ligne par note envoyée depuis l'écran (`POST /rating`), avec le rapport complet de la transition. Il **repart vide** pour la v2 et n'existe qu'après la première note ; `e2.py` le crée. Les résultats du protocole d'écoute ([`../specs/protocole-ecoute.md`](../specs/protocole-ecoute.md)) iront dans `12-ecoute-transitions-v2.md` (le 11 est réservé à `11-voix.md`, calibrage de la voix). Le numéro 09 (ancienne écoute) est retiré et n'est pas réutilisé.
