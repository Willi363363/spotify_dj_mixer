# 08 · Série C : maquette E2 (son retardé en mémoire)

Test du 2026-10-23. Code : [`proto/e2/`](../../proto/e2/README.md).

## Montage

```
Spotify ─► dj_in (sortie virtuelle muette, module-null-sink)
              │ parec dj_in.monitor
              ▼
           e2.py : mémoire de 10 min, lecture 20 s en retard ─► pacat ─► haut-parleurs
              ▲ ordre UDP 127.0.0.1:47801 (heure du changement, tempo, mesure)
           run.sh ◄── transition.js dans Spotify (mode débogage)
```

`transition.js` joue A, puis lance B sur son drop au premier temps d'une mesure de A (saut avancé de 115 ms). `e2.py` retrouve l'**échantillon exact** du changement (la suite de quasi-zéros que Spotify insère), puis prépare le segment de transition et le joue à la place du flux.

Morceaux : A « Bubble Like Soup » (117,6 BPM), B « Coucounia » (118 BPM).

## Résultats

| Essai | Ce que fait la maquette | Mesure |
|---|---|---|
| **Passage direct** | rejoue le son 20 s plus tard | retard **20,01 s** et 20,03 s ; ressemblance sortie / entrée **0,976** et **0,9998** |
| **Mix** | 4 mesures de superposition, B calé au tempo de A par `rubberband`, **échange des basses** à mi-parcours (A perd ses graves < 180 Hz, B les reçoit, fondu de 50 ms) | segment de 7,81 s préparé en 10 s, joué à temps ; il restait 11,6 s d'avance |
| **Boucle** | rejoue 4 fois la dernière mesure de A depuis la mémoire, puis B net sur le temps | **aucun silence** dans la sortie ; l'avance passe à 27,2 s |
| **Vinyle qui freine** | ralentit la dernière mesure de A jusqu'à l'arrêt, puis B | segment de 1,95 s joué, aucun silence pendant la transition |

Trou laissé par Spotify au changement A → B : **354 ms, 400 ms, 330 ms** selon l'essai. Dans les trois cas, la maquette le **saute entièrement**.

## Défauts constatés

| Défaut | Cause probable | Correction |
|---|---|---|
| 2 silences de ~45 ms dans la sortie, 33 s après le mix | la lecture en Python a manqué de données (absent de l'entrée) | moteur en Rust ou C, tampon de sortie plus large |
| Silences sur le redémarrage de A | le script de test relance A : la maquette transmet les trous du flux hors transition | normal ; en vrai, chaque changement passe par une transition |
| Première détection : faux trou de 201 ms | un passage calme de A pris pour le silence | corrigé : on ne cherche que du silence numérique |
| Premier mix raté (19 % d'écart de tempo, erreur de longueur) | morceaux mal choisis, et j'avais inversé le calcul de la durée à étirer | corrigé |
| L'avance varie (11,6 → 27,2 s) | un mix la consomme, une boucle la rallonge | à piloter : budget d'avance, cf. [`../architecture.md`](../architecture.md#e2-le-module-avec-avance) |

## Non vérifié

- **Le rendu à l'oreille** des trois transitions : alignement des temps dans le mix, propreté de la boucle, naturel du freinage.
- **Le calage des temps** dans le mix : il repose sur le point de changement (fin de A au premier temps), dont la précision dépend du saut calibré à 115 ms.

## Conclusion

✅ Le principe de l'étape E2 marche sur une vraie lecture Spotify : retard stable, deux morceaux séparés en mémoire, superposition avec échange des basses, calage du tempo, boucle sans trou, freinage. Le prototype Python suffit à valider l'idée, pas à l'utiliser au quotidien.
