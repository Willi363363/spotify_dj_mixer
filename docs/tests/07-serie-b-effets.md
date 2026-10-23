# 07 · Série B : effets PipeWire

Test du 2026-10-23. Config : [`dj-effets.conf`](../../outils/dj-effets.conf). Analyse : [`b-analyse.py`](../../outils/b-analyse.py).

## Montage

Une instance PipeWire temporaire (`pipewire -c <chemin absolu>/dj-effets.conf`) crée la sortie `dj_effets`, une chaîne de nœuds fournis avec PipeWire :

```
low (bq_lowshelf 120 Hz) → mid (bq_peaking 1 kHz) → high (bq_highshelf 6 kHz) → hp (bq_highpass)
      → mix:In 1  (son direct)
      → dly (delay) → mix:In 2  (écho)
```

Réglages exposés : `low:Gain`, `mid:Gain`, `high:Gain`, `hp:Freq`, `dly:Delay (s)`, **`dly:Feedback`** (répétitions), `mix:Gain 1..8`.

Enregistrement simultané avant (`dj_effets.monitor`) et après (sortie par défaut), recalés par intercorrélation (+5,3 ms). Morceau : « Around the World » à 1:00.

## Résultats

| Effet | Réglage | Mesure |
|---|---|---|
| **Égaliseur** | graves −15 dB, aigus +6 dB | graves < 120 Hz **−10,4 dB**, aigus > 6 kHz **+5,0 dB**, médiums 0,0 dB |
| **Écho** | 0,372 s (¾ de temps), répétition 0,45, niveau 0,6 | ressemblance avec l'entrée décalée : **0,43** à 0,372 s, **0,19** à 0,744 s, contre −0,03 et −0,02 sans écho |
| **Clics, balayage rapide** (15 paliers, 0,6 s) | passe-haut 20 → 2 000 → 20 Hz | 2 fenêtres de 10 ms sur 300 avec un pic d'aigus ajouté, max +11 dB |
| **Clics, balayage lent** (122 paliers, ~3 s) | idem | 6 fenêtres sur 300, max **+24 dB** |
| Référence neutre | tout à zéro | 0 fenêtre, max +0,1 dB |

Les plateaux d'égaliseur mesurés (−10,4 au lieu de −15) sont normaux : la bande mesurée déborde de la zone pleinement atténuée.

## Ce qu'on en tire

- ✅ **Égaliseur 3 bandes et écho avec répétitions** fonctionnent avec les nœuds fournis, réglables en direct.
- ⚠️ **Clics** : les nœuds `bq_*` changent leurs coefficients d'un coup, et chaque palier peut produire un petit claquement. Plus il y a de paliers, plus il y en a. Pistes :
  - effets à **lissage intégré** (paquet `lsp-plugins-lv2`, non installé, non testé) ;
  - **fondu croisé** entre deux chaînes réglées différemment, plutôt que de modifier une chaîne en cours ;
  - en E2, filtres maison dont les coefficients glissent à chaque échantillon.
- Réverbération : non testée (nœud `convolver` de PipeWire, ou `lsp-plugins`).
- Ressenti à l'oreille : non recueilli pour cette série.
