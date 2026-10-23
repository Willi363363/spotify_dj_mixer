# Tests

Tests réalisés le **2026-10-23** sur la machine de [`../environnement.md`](../environnement.md). Comment les rejouer : [`methode.md`](methode.md).

| # | Test | Question | Verdict |
|---|---|---|---|
| 01 | [Analyse audio](01-analyse-audio.md) | Spicetify donne-t-il encore tempo, temps, sections ? | ✅ Oui |
| 02 | [Vitesse de lecture](02-vitesse-lecture.md) | Peut-on ralentir ou accélérer la musique dans Spotify ? | ❌ Non, refusé |
| 03 | [Boucle par saut](03-boucle-par-saut.md) | Une boucle par saut est-elle propre ? | ✅ Rythme juste après calibrage, ⚠️ micro-silences |
| 04 | [Filtre PipeWire](04-filtre-pipewire.md) | Peut-on couper les basses de Spotify en direct ? | ✅ Oui, −17 dB |
| 05 | [Connexion locale](05-connexion-locale.md) | L'extension peut-elle piloter un programme local ? | ✅ Oui, 0,7 ms |

## Règle

Un résultat audio se juge **à l'oreille et sur un enregistrement**. Les positions annoncées par Spotify ont menti de 80 ms au test 03 : seules les mesures sur la sortie son font foi.
