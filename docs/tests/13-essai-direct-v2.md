# 13 · Essai en direct des transitions v2

Essai du 2026-10-28, sur la machine de [`../environnement.md`](../environnement.md), compte gratuit, mode débogage
([`methode.md`](methode.md)). Fait seul, développeur absent : tout est **mesuré sur le son réel**, rien n'est **écouté**.
Spec : [`../specs/transitions-v2.md`](../specs/transitions-v2.md) ; paires : [`../specs/protocole-ecoute.md`](../specs/protocole-ecoute.md).

## Ce qui a été joué

- **64 transitions réelles** : 23 avant correctifs, 9 en **mode auto réel** (playlist « RAP FRANCAIS 2026 », changement
  de morceau à la main, album), 32 en lots de validation, dont **31 avec tous les correctifs** (les 15 paires en auto
  + 16 forçages) : ce sont elles qui sont mesurées ci-dessous et dont les extraits sont gardés. Les 10 transitions du catalogue ont été **rendues et jouées** au moins une fois.
- Paires : les 16 du protocole (URI réelles, critères vérifiés sur `getAudioData`), plus 5 paires de forçage (17 à 21).
  Le cas 4 n'existe pas dans la bibliothèque (aucune paire n'a 16 mesures sans voix des deux côtés, cf. voix) : paire approchée.
- Banc (scratchpad, hors dépôt) : `run.sh` inchangé, plus un enregistrement stéréo de la **vraie sortie** ; `e2.py` lancé
  par un lanceur qui sauve chaque rendu (pistes A et B, bornes) et son `mesures.rapport(complet=True)`. Forçage « hors
  règle » (g05, h01, h02, h04) : variante de `transition.js` qui construit les points d'une transition que la règle refuse
  (C7 n'est jamais éligible), pour exercer son rendu.

## Mesures sur le son réel (31 transitions finales)

Calage, basses, échange : mesurés sur le rendu (critères 9.1-1 à 3). Sonie O5, crête, trous, clics : sur l'enregistrement
de la sortie. Marge : temps entre la fin du rendu et le début du segment (9.1-12).

| Essai | Paire | Demandée → jouée | Replis au rendu | Calage ms | Basses ms | Échange ms | Sonie sortie dB | Crête dBFS | Marge s |
|---|---|---|---|---|---|---|---|---|---|
| a01 | 1 | C6 → **C5** | C6→C5 | +0 | +0 | +18 | +0.8 / +5.3 | -8.4 | 35 |
| a02 | 2 | C2 → **C2** | — | — | +0 | +1 | -6.3 / -0.7 | -5.8 | 46 |
| a03 | 3 | C6 → **R1** | C6→R1 | +25 | +0 | +176 | +1.0 / +1.0 | -6.1 | 37 |
| a04 | 4 | C2 → **C2** | — | — | +0 | +7 | -0.9 / +0.8 | -6.2 | 47 |
| a05 | 5 | C1 → **C1** | — | — | +0 | +2 | -3.6 / +1.4 | -4.2 | 56 |
| a06 | 6 | C2 → **C2** | — | — | +0 | +1 | -4.8 / +3.0 | -3.3 | 50 |
| a07 | 7 | C4 → **C4** | — | — | +0 | +1 | -2.2 / +0.9 | -6.2 | 53 |
| a08 | 8 | C8 → **C5** | C8→C5 | +5 | +0 | +2 | -6.8 / -2.4 | -4.6 | 46 |
| a09 | 9 | C2 → **C2** | — | — | +9 | +2 | -17.1 / +4.7 | -5.8 | 50 |
| a10 | 10 | C1 → **C1** | — | — | +0 | +1 | -4.5 / -3.6 | -6.6 | 52 |
| a11 | 11 | C5 → **C5** | — | +10 | +0 | +49 | -5.8 / -5.8 | -7.0 | 46 |
| a12 | 12 | C2 → **C2** | — | — | +0 | +15 | -1.0 / -0.3 | -7.1 | 50 |
| a13 | 13 | C1 → **C1** | — | — | +0 | +444 | +2.8 / +3.3 | -3.8 | 53 |
| a14 | 14 | C2 → **C2** | — | — | +0 | +5 | -10.8 / +3.1 | -7.5 | 51 |
| a15 | 15 | C5 → **R1** | C5→R1 | -90 | +0 | +18 | -2.6 / -2.6 | -5.8 | 50 |
| g01 | 5 | C3 (forcée) → **C3** | — | — | +0 | +3 | -2.5 / -0.6 | -4.8 | 51 |
| g02 | 17 | C4 (forcée) → **C1** | C4→C1 | — | +0 | +11 | +3.9 / +4.3 | -3.8 | 53 |
| g03 | 15 | C5 (forcée) → **R1** | C5→R1 | +25 | +0 | +18 | -2.8 / -2.8 | -6.2 | 52 |
| g04 | 3 | C6 (forcée) → **R1** | C6→R1 | +25 | +0 | +183 | +1.1 / +1.1 | -6.9 | 44 |
| g05 | 15 | C7 (hors règle) → **C5** | C7→C5 | -5 | +0 | +235 | -1.9 / -1.2 | -5.5 | 37 |
| g06 | 18 | C8 (forcée) → **C8** | — | -5 | +0 | +42 | -21.3 / -7.0 | -3.7 | 28 |
| g07 | 7 | R1 (forcée) → **R1** | — | +135 | +0 | +742 | -0.6 / -0.6 | -6.2 | 45 |
| g08 | 12 | R2 (forcée) → **R2** | — | — | +0 | +1 | -1.6 / -1.6 | -6.7 | 39 |
| g09 | 6 | C3 (forcée) → **C3** | — | — | +0 | +4 | -1.6 / -0.9 | -3.3 | 49 |
| g10 | 14 | C6 (forcée) → **R1** | C6→C5, C5→R1 | +90 | +0 | +609 | -0.3 / -0.3 | -6.6 | 49 |
| g11 | 8 | C8 (forcée) → **C5** | C8→C5 | +0 | +0 | +4 | -6.8 / -2.4 | -5.3 | 46 |
| g13 | 7 | C4 (forcée) → **C1** | C4→C1 | — | +0 | +386 | +0.6 / +0.6 | -5.8 | 54 |
| g14 | 5 | C5 (forcée) → **C5** | — | +0 | +0 | +8 | -1.0 / +1.2 | -3.4 | 44 |
| h01 | 19 | C7 (hors règle) → **C7** | — | +5 | +0 | +8 | -2.0 / +4.6 | -4.1 | 23 |
| h02 | 20 | C6 (hors règle) → **C5** | C6→C5 | +0 | +0 | +2 | +0.1 / +1.1 | -7.2 | 32 |
| h04 | 21 | C6 (hors règle) → **C6** | — | +0 | +0 | +4 | -1.6 / +1.9 | -4.0 | 39 |

Mode auto réel (non enregistré, journal du moteur) : R1, C2→R2 (défaut 2 ci-dessous), C2, C1, C6→R1 (voix), C2→R2,
R1 de **rattrapage** après « suivant » à la main (accepté, rendu en 1 s), R2 d'album (défaut 3), puis R2 d'album corrigé.

### Critères 9.1, sur le son réel

| Critère | Résultat |
|---|---|
| Sortie = rendu | Corrélation sortie / rendu ≥ 0,986 sur les 31 (le moteur joue exactement ce qu'il calcule) |
| 1 Calage (C5-C8) | 0 à 10 ms sur 12 superpositions ; 4 refus > 20 ms → R1 (repli correct). **R1** n'est pas corrigé (par conception) : jusqu'à 135 ms |
| 2 Basses | 0 ms partout (9 ms sur a09) |
| 3 Échange sur le 1 | ≤ 18 ms sur 19 des 24 C1-C8 ; 42-49 ms (a11, g06), 235 ms (g05) ; 386-444 ms sur 2 C1 où B commence sans basse (la mesure voit sa 1re note, pas la rampe) |
| 4 Trous | **0** imputable au moteur ; 2 trous (31 et 72 ms) vus dans g06 sont dans le flux de Spotify (changement de morceau du banc) |
| 5 Clics | **0** imputable au moteur ; 3 « clics » sur un 1, déjà présents dans le flux de Spotify au même instant musical |
| 6 Niveau O5 | **17 / 31** dans [−3 ; +2] dB ; crête ≤ −3,3 dBFS. Échecs : ΔE de −15 à −30 dB (intro de B calme, A fort) ou A en fondu |
| 9 Avance | C1-C3 : 0 à 0,6 temps ; C4 : −7,9 temps (regain) ; C6/C7 : T mesures + 0,5 temps ; C5 : +0,3 à +1,3 temps, C8 +1,7 (A joué après le 1, sauté) |
| 11 Replis | 13 replis au rendu, tous vers le bon échelon : 9 sur voix (V3), 4 sur calage > 20 ms ; aucun secours, aucun abandon |
| 12 Marge | 23 à 56 s (≥ 2 s) ; rendu le plus long 24 s (C8, 8 mesures) |
| O1 Fin de A | 30 / 30 dans le garde-fou (max 29,2 s jamais entendus) ; dernière mesure de A perdue : 7 / 23 en direct avant correctif 1, **0 / 31** après |

## Problèmes trouvés et corrigés

1. **Dernière mesure de A perdue** (7 transitions jouées sur 23 ; 10 sur 23 en rejouant l'ancien code hors ligne sur les mêmes enregistrements). Journal : « fin de A recalée de −1 600 à −2 500 ms ». Cause
   (vérité terrain : A réenregistré en continu au-delà de sa sortie, même A dans deux essais) : le 1 de sortie était bien
   en mémoire, mais `placer` le cherchait à ±150 ms de la fin estimée avec une mesure de temps **après** la sortie,
   c'est-à-dire dans le son de B ; un lag positif faisait reculer d'une mesure. L'instant du saut varie de ±100 ms.
   Correctifs : `spicetify/dj-choix.js:446` (temps de A sur [−T − 2 ; 0] mesures, ADR 0001 mis à jour) ;
   `proto/e2/e2.py:582-590` (temps d'avant la sortie seulement, recherche dans [−320 ; +30] ms, `A_AVANT_S`,
   `A_APRES_S` l. 63-64) ; `e2.py:569` (marge de 20 ms jusqu'au début estimé de B, au lieu de 0) ;
   `spicetify/dj-auto.js:16` (`LEAD = −60` : saut 60 ms après la sortie). Tests : `proto/e2/test_ordre.py:288`
   (saut 30 à 300 ms après le 1, ordres actuels et anciens : l'ancien code perd une mesure ou pose A dans B),
   `spicetify/test/choix.test.mjs:46`, `spicetify/test/auto.test.mjs:89`. En direct : **0 mesure perdue sur 31**.
2. **Repli au plan C2 → R2 « grille floue »** en mode auto. `replierAuPlan` refusait toute transition dès qu'une grille
   était floue, alors que C2 n'exige que la grille de A (cas 11 du protocole) : `dj-choix.js:373`. Test :
   `choix.test.mjs:107`. (`run.sh` n'appelle pas `replierAuPlan` : invisible sur le banc.)
3. **Album quitté** : après une playlist, `chooseNext` gardait la réserve de la playlist ; en album (cas 16), le mode auto
   sautait vers un morceau de cette réserve et sortait de l'album. `dj-auto.js:192-198` : en album joué dans l'ordre,
   B = piste suivante de la file. Test : `auto.test.mjs:145`. En direct : R2 « Graine de sablier » → « Beautiful » dans
   l'album.
4. **Faux clics** de `mesures.rapport(complet=True)` sur un rendu réel, au premier ou au dernier échantillon (la médiane
   locale n'y voit qu'un côté). `proto/e2/transitions/mesures.py:165-193` : raccords jugés avec le flux (`avant`,
   `apres`), bornes de bord non jugées sans lui. Test : `proto/e2/test_mesures.py:79`.

Aussi : `spicetify/README.md` (`DJ.status` est un objet, `DJ.LEAD`), `docs/pieges.md` (6 pièges),
[`../specs/protocole-ecoute.md`](../specs/protocole-ecoute.md) (URI). Tests : `node --test spicetify/test/` 56/56 ;
`proto/e2/test_*.py` : tout passe.

## Constats non corrigés (décisions du développeur)

- **Voix V2 (plan)** sur 21 morceaux avec paroles synchronisées (748 mesures uniques) : « sans voix » juste 1 fois sur 3 ;
  ne voit que 45 % des mesures sans paroles. Il juge « vocale » la fin de 67 % des morceaux, y compris de la techno : cas 4
  introuvable, **C7 jamais éligible** sur 76 000 paires de la bibliothèque, C8 sur 1 %.
- **Voix V3 (rendu)** : au seuil de repli 0,6, elle classe « voix » 62 % des mesures sans paroles (83 % avec) : presque
  aucune discrimination. Elle a refusé C6 8 fois sur 9 (même l'intro instrumentale de Mau P), C4 5 fois sur 7, C8 et C7
  hors règle. C6 n'est passée que sur l'intro batterie/basse de « Around the World ». Calibrage : tâche 2-direct.
- **Paroles (V1)** : synchronisées pour 46 / 60 morceaux (77 %, ≥ 60 % : seuil de l'ADR 0002 pour allumer le drapeau par
  défaut ; shatta/bouyon 2 / 11). L'adresse renvoie 429 au-delà de ~30 requêtes rapprochées. Drapeau non touché.
- **O5** tel que défini (moyenne de A avant et B après) est inatteignable quand A et B diffèrent de plus de ~10 dB ; ΔE
  ≤ −4 dB sur 65 % des paires (B part de son intro, plus calme).
- `echange_ms` sur coupe sèche, et R1 sans correction de calage (jusqu'à 135 ms, 742 ms d'échange) : cf. tableau.
- `chooseNext` rend des morceaux sans `uid` : B est joué seul et le contexte de la playlist est quitté (hors périmètre v2).
- Aucune pub pendant ~3 h de lecture (compte gratuit).

## Ce qui reste

- **Écoute** (O8) : 31 extraits de ~45 s (stéréo, ogg) dans `~/spotify_dj_mixer-ecoute/` (hors dépôt), nommés par paire
  sans la transition ; `LISEZ-MOI.md` (liste à l'aveugle) et `correspondance-cachee.json` (à n'ouvrir qu'après la note).
- O6 (séance d'1 h sans secours) et O7 (variété) en mode auto : seulement 9 transitions auto, sans secours.
- Pubs, cas 4 réel, et toute la chaîne voix (V2/V3) à recalibrer avant de juger C6, C7, C8, C4.
- Les transitions en mode auto réel n'ont pas été enregistrées (journal seulement).
