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

## Corrections après essai

Faites hors ligne le 2026-10-29 (sans Spotify), sur des morceaux de synthèse (`proto/e2/synthese.py`). Arbitrages :
spec [§14](../specs/transitions-v2.md#14-arbitrages-pendant-limplémentation). **À revérifier en direct.**

1. **R1 non calé** (calage jusqu'à 135 ms, échange jusqu'à 742 ms). Reproduit : tempos de B à 2-8 % de A (et 16 %), fin
   de A et début de B estimés à −60 à +90 ms de leurs vrais temps → calage jusqu'à 185 ms, graves de B jusqu'à 417 ms
   après le vrai 1 de A. Cause : R1 posait B tel quel (sans étirement) sur les temps estimés ; à 8 % d'écart, le 1 de B
   arrive 160 ms après celui de A, et l'échange des graves (au 1 de A) tombait entre deux notes de basse de B.
   Correctif : `proto/e2/transitions/superposees.py`, `phases_r1` et `r1` : phase réelle de A et de B mesurée sur leur
   son (`grid_fit`, ±120 ms), segment calé sur le vrai 1 de A, mesure de B étirée (`stretch_map`, 1 mesure) temps par
   temps sur A, 1 final de B = 1 final de A. Résultat sur les 24 combinaisons : calage 0 à 5 ms, échange 1 à 2 ms
   (graves de B à −4 ms du vrai 1). Calcul : +0,3 s (rubberband sur une mesure).
   Tests : `proto/e2/test_rendu.py` (« corrections après l'essai direct 13 », 6 cas tempo × grille fausse : calage
   ≤ 20 ms, graves ≤ 20 ms des vrais 1 de A et de B, ni trou ni clic) ; R1 n'est plus exempté de 9.1-1 et 9.1-3 dans
   `test_rendu.py` et `test_criteres.py`, qui ajoute R1 à 128 et 113 BPM.
2. **Échange de +444 ms (a13) et +386 ms (g13) sur C1** : **artefact de la mesure**. Sur l'extrait réel de a13
   (`paire-13-a.ogg`), B (136 BPM, temps de 441 ms) entre sur son temps (phase de ses attaques ≈ 0 ms à la jonction) et
   sa 1re note de basse arrive **un temps plus tard** (444 ms) : `instant_echange` prenait la 1re note de basse de B,
   pas l'échange. Sur une coupe, les graves passent avec tout le reste à l'entrée de B. Correctif :
   `proto/e2/transitions/mesures.py`, `instant_echange` : si A est muet avant que B ne sonne (à 15 ms près), l'échange
   est le premier échantillon non nul de B ; superposition inchangée. Le rendu de C1 n'est pas touché.
   Tests : `proto/e2/test_mesures.py` (coupe avec basse sur le 2 → 0 ms ; B entré 30 ms tard → 30 ms ; superposition
   au 1 et 60 ms tard), `test_rendu.py` (C1, C3, C4 avec la basse de B sur le 2 : échange ≤ 10 ms, à la jonction).
3. **O5 tenu 17/31** : critère redéfini (`mesures.sonie`) en saut de niveau perçu par rapport aux niveaux propres :
   sonie 3 s ≥ le plus calme de A et B − 3 dB et ≤ le plus fort + 2 dB. Même forme dans le rapport (`sonie_db`). Le
   moteur **ne relève pas** B (§14). Tests : `test_mesures.py` (B 20 dB sous A : conforme ; creux sous le plus calme et
   bosse au-dessus du plus fort : vus), `test_rendu.py` (C1, C2, C5, C6, R1 avec B 20 et 30 dB sous A : conformes ;
   l'ancien critère donnait jusqu'à +29 dB). Les valeurs « Sonie sortie » du tableau ci-dessus restent à l'ancienne
   définition (réécoute des extraits à refaire avec la nouvelle).
4. En plus : `mesures.clics` prend la référence aux temps de A **et** de B (reprise de R1 calé sur un temps de B : faux
   clic sinon) ; `primitives.bandes` calcule sa FFT sur une taille 2^a·3^b·5^c (`taille_rapide`) : C7 de 8 mesures rendu
   en 1,5 à 2,5 s au lieu de 6,5 à 10 s, ce qui faisait manquer 9.1-12 (C7 et C8 à T = 8, 124 BPM) sur machine chargée.

5. **Après la revalidation (QA, 2026-10-29)**, hors ligne : R1 garde les temps estimés d'un morceau sans batterie (phase
   fiable : netteté ≥ 3,5 **et** accord ≥ 0,6, `calage.phase_attaques` ; bruit et nappe y prenaient ±115 ms) et rapporte
   son calage sur les 8 temps qui suivent le 1 final de B (`superposees.calage_r1`, « non mesurable » sans attaques) ;
   C5 à C8 posent les temps réels de Spotify sur la grille commune (`calage.grille_temps`) ; sur une coupe, 9.1-3 mesure
   aussi la phase des attaques de B après la jonction (`mesures.phase_entree_b`) ; la fenêtre du 1 de sortie est
   recentrée au-delà de ~150 BPM (`e2.fenetre_un`). Tests : `test_rendu.py` (« 1 ter » à « 1 quinquies », « 2 bis »),
   `test_mesures.py`, `test_ordre.py` (placement à 120, 190, 200 BPM). Spec §14 mise à jour.

Tests (`for t in proto/e2/test_*.py; do python3 -I $t; done`) : tout passe (6 / 6), `test_voix` compris (le travail
sur `transitions/voix.py` et `test_voix_reel.json` qui les faisait échouer est livré depuis).

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
  ≤ −4 dB sur 65 % des paires (B part de son intro, plus calme). Redéfini depuis : cf. Corrections après essai.
- `echange_ms` sur coupe sèche, et R1 sans correction de calage (jusqu'à 135 ms, 742 ms d'échange) : cf. tableau.
  Corrigés depuis : cf. Corrections après essai.
- `chooseNext` rend des morceaux sans `uid` : B est joué seul et le contexte de la playlist est quitté (hors périmètre v2).
- Aucune pub pendant ~3 h de lecture (compte gratuit).

## Ce qui reste

- **Écoute** (O8) : 31 extraits de ~45 s (stéréo, ogg) dans `~/spotify_dj_mixer-ecoute/` (hors dépôt), nommés par paire
  sans la transition ; `LISEZ-MOI.md` (liste à l'aveugle) et `correspondance-cachee.json` (à n'ouvrir qu'après la note).
- O6 (séance d'1 h sans secours) et O7 (variété) en mode auto : seulement 9 transitions auto, sans secours.
- Pubs, cas 4 réel, et toute la chaîne voix (V2/V3) à recalibrer avant de juger C6, C7, C8, C4.
- Les transitions en mode auto réel n'ont pas été enregistrées (journal seulement).

## Revalidation du 2026-10-29

En direct, seul, même machine et même banc (mode débogage, `e2.py` lancé par un lanceur hors dépôt qui sauve chaque
rendu, sa mémoire autour du saut et son `mesures.rapport(complet=True)` avec le flux ; sortie enregistrée en stéréo).
Ciblée sur les **corrections après essai** ci-dessus. **19 transitions jouées** : 2 R1 avant le correctif ci-dessous
(g07, référence), puis **17 après** : 11 par `run.sh` (cas fautifs d'hier, `auto` ou forcés) et **6 en mode auto réel**
sur « RAP FRANCAIS 2026 » (lecture aléatoire, avance rapide jusqu'à 40 s de chaque sortie prévue). Mesuré, **pas écouté**.

### Mesures (17 transitions après correctif)

Calage : rapporté par le moteur / **vérifié** (vrai 1 de B, d'après ses attaques sur les 8 temps qui suivent son 1 final
dans la mémoire, moins le vrai 1 de A, d'après ses 8 derniers temps). Sonie : nouvelle définition O5 `[min ; max]`
(conforme si min ≥ −3 et max ≤ +2), sur le rendu puis sur la sortie. Corr. : corrélation sortie / rendu. Trous/clics :
rendu raccordé au flux · sortie. Marge en s.

| Essai | Paire | Demandée → jouée | Replis (où, raison) | Calage ms rapp. / vérifié | Basses ms | Échange ms | Sonie rendu dB | Sonie sortie dB | Crête dBFS | Corr. | Trous/clics | Marge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| j-g07 | 7 | R1 (forcée) → **R1** | — | +105 / **−5** | +0 | +560 ¹ | [−0,0 ; −2,7] | [+0,1 ; −2,6] | −6,6 | 0,996 | 0/0 · 0/0 | 53 |
| j-g10 | 14 | C6 (forcée) → **R1** | C6→C5 (plan, voix dans les 4 premières mesures de B), C5→R1 (rendu, netteté −0,07) | +5 / **−0** | +0 | +18 | [−3,7 ; −4,6] ² | [−3,7 ; −4,8] | −9,9 | 0,995 | 0/0 · 0/0 | 51 |
| j-a15 | 15 | C5 → **R1** | C5→R1 (rendu, calage +35 ms > 20 après correction) | +15 / **−15** | +0 | +20 | [−1,6 ; −2,5] | [−1,6 ; −2,5] | −8,2 | 1,000 | 0/0 · 0/0 | 50 |
| j-a03 | 3 | C2 → **C2** | — | — | +0 | +0 | [+1,1 ; +0,5] | [+1,1 ; +0,5] | −6,1 | 1,000 | 0/0 · 0/0 | 50 |
| j-a13 | 13 | C2 → **C2** | — | — | +0 | +10 | [+21,8 ; +0,0] | [+21,8 ; −0,2] | −7,7 | 1,000 | 0/0 · 0/0 | 51 |
| j-g04 | 3 | C6 (forcée) → **R1** | C6→C5 (plan, voix dans les 4 premières mesures de B), C5→R1 (plan, grille de B floue) | −5 / **−5** | +0 | +23 | [−1,1 ; −1,2] | [−1,0 ; −1,1] | −8,2 | 0,999 | 0/0 · 0/0 | 50 |
| j-a13c | 13 | C1 (forcée) → **R2** | C1→R2 (plan, voix de A sur la dernière mesure) | — | +0 | (+433) ³ | [−0,6 ; −1,6] | [−0,6 ; −1,6] | −7,0 | 0,998 | 0/0 · 0/0 | 48 |
| j-g13 | 7 | C4 (forcée) → **R2** | C4→C1 (plan, voix sur la mesure bouclée), C1→R2 (plan, voix de A sur la dernière mesure) | — | +0 | (+262) ³ | [+4,1 ; −2,3] | [+4,1 ; −2,3] | −6,5 | 0,997 | 0/0 · 0/0 | 49 |
| j-g06 | 18 | C8 (forcée) → **C5** | C8→C5 (plan, sauterait le début de B) | −5 / **−13** | +0 | +12 | [+5,8 ; +0,1] | [+5,8 ; +0,2] | −13,7 | 0,997 | 0/0 · 0/0 | 48 |
| j-c1p10 | 10 | C1 (forcée) → **R2** | C1→R2 (plan, voix de A sur la dernière mesure) | — | +0 | (+3) | [+10,0 ; −0,5] | [+10,0 ; −0,7] | −16,5 | 1,000 | 0/0 · 0/0 | 54 |
| j-c1p2 | 2 | C1 (forcée) → **R2** | C1→R2 (plan, voix de A sur la dernière mesure) | — | +0 | (+3) | [+0,0 ; −9,7] | [+0,1 ; −9,7] | −14,6 | 1,000 | 0/0 · 0/0 | 47 |
| auto1 | rattrapage | R1 → **R1** | — (ordre manuel, sans grille) | +125 / **+35** ⁴ | +0 | +43 | [+13,6 ; −1,9] | [+13,3 ; −1,9] | −7,4 | 0,992 | 0/0 · 0/0 | 49 |
| auto2 | auto | R1 → **R1** | — (aucune transition éligible) | −30 / **−0** | +0 | +17 | [−0,1 ; −2,6] | [−0,0 ; −2,8] | −8,4 | 0,998 | 0/0 · 0/0 | 54 |
| auto3 | auto | C2 → **C2** | — | — | +0 | +15 | [−2,4 ; −3,3] | [−2,3 ; −3,6] | −7,8 | 0,986 | 0/0 · 0/0 | 45 |
| auto4 | auto | R1 → **R1** | — (aucune transition éligible) | −55 / **+5** | +0 | +18 | [−9,7 ; −9,4] ² | [−9,4 ; −9,4] | −8,0 | 0,999 | 0/0 · 0/1 ⁵ | 48 |
| auto5 | auto | R2 → **R2** | — (aucune transition éligible) | — | +0 | (+2) | [+12,5 ; +1,2] | [+12,5 ; +1,0] | −13,8 | 1,000 | 0/0 · 0/0 | 48 |
| auto6 | auto | C2 → **C2** | — | — | +0 | +0 | [−11,5 ; +0,7] ² | [−11,5 ; +0,8] | −7,3 | 0,997 | 0/0 · 0/0 | 46 |

Avant le correctif, même paire que j-g07 (deux fois) : phase de B mesurée **+50 ms**, calage rapporté +50 / +55 ms,
**vérifié +104 ms**, échange +611 ms (hier : +135 et +742 ms).

1. B (« KONGOLESE SOUS BBL ») entre sans grosse caisse ni basse sur ses 6 premiers temps : le calage rapporté (mesuré
   sur la 1re mesure de B, netteté 2,5) et l'échange (1re note de basse de B, 1,5 temps après son 1) n'y voient rien.
   Ses grosses caisses suivantes tombent à −5 ms du 1 de A (vérifié). Même artefact que a13 hier, côté superposition.
2. Creux O5 venu du contenu, pas du moteur (gain de B 0,81 à 1, aucune atténuation au-delà des courbes du §4) :
   j-g10, l'entrée de « Mood » est presque muette ; auto4, A décroît de lui-même (−19 → −41 dB) dans sa dernière
   mesure et B entre sur une mesure muette avant son drop ; auto6, le segment C2 contient 3,5 s de l'intro calme de B
   (−31 dB) alors que la référence de B est prise après la reprise (−19 dB). Limite de la mesure O5 : elle compare à B
   **après** le segment.
3. R2 est exempté de 9.1-3 (bord à bord, pas de 1 commun ; `test_rendu.py`) ; son raccord de 20 ms dépasse
   `COUPE_MS` (15 ms) : `instant_echange` le traite en superposition et prend la 1re note de basse de B.
4. Rattrapage après un changement de morceau à la main (lancement de la playlist) : ordre sans temps de Spotify,
   A coupé où l'utilisateur a sauté ; le « 1 de A » n'y est qu'estimé (§8).
5. Un écart de ~60 ms à la reprise, sur la sortie seulement : le rendu raccordé au flux de la mémoire n'a pas de clic,
   le moteur reprend le flux à l'échantillon exact, et l'écart sortie / attendu y est du même ordre qu'au milieu du
   segment (0,09 contre 0,04). Non imputable au calcul ; cause non établie (sortie son).

### Bilan par correction

| Correction | En direct |
|---|---|
| R1 calé (≤ 20 ms) | **Défaut encore présent avant correctif** (+104 ms vérifié sur g07), corrigé ci-dessous. Après : vérifié −15 à +5 ms sur les 6 R1 avec grille (5 sur 6 à ≤ 5 ms) ; rattrapage sans grille +35 ms. Échange 17 à 23 ms sur 5 R1 (≤ 20 sur 4), hors j-g07 (¹) |
| Échange des coupes | C2 : 0 à 15 ms sur 4. Aucune C1 jouée : C1 forcée sur 4 paires (13, 7, 10, 2) toujours rabattue en R2 au plan par V1 (« voix de A sur la dernière mesure ») |
| O5 relatif | Conforme sur **14 / 17** (rendu et sortie concordent à 0,3 dB près) ; 3 creux venus du contenu (²) |
| Crête | −6,1 à −16,5 dBFS (≤ −3) |
| Trous, clics | 0 imputable au moteur (rendu raccordé au flux : 0 / 0 sur les 17) |
| Sortie = rendu | Corrélation 0,986 à 1,000 |
| Rendu FFT plus rapide | Marges 45 à 54 s ; rendu 0,1 à 0,5 s (R1, C5), 2,7 à 3,6 s (C2), 5,1 à 6,9 s (R2, qui attend 10 s de B en mémoire) ; préparation complète 5,2 à 11,4 s ; pas de C7 ni de C8 jouée (C8 forcée rabattue en C5 au plan) |
| V1 par défaut | 22 requêtes de paroles, 14 trouvées, 8 absentes, 18 servies par le cache, **0 × 429**. Utilisées au plan (`voix_source: paroles` quand A et B en ont, `segments` sinon) ; en auto, 3 des 7 morceaux ont des paroles |
| V3 recalibrée | 0 repli au rendu sur la voix (hier : 9). Les replis viennent maintenant du plan (V1) : C6 → C5 (×2), C4 → C1, C1 → R2 (×4) |
| Mode auto réel | 6 transitions sans secours ni abandon : R1 ×3 (dont 1 rattrapage, 2 « aucune transition éligible »), C2 ×2, R2 ×1 (« aucune transition éligible ») |

### Corrigé pendant la revalidation

**R1 non calé en direct** (j-g07 avant correctif : vérifié +104 ms). Reproduit hors ligne sur la mémoire vidée par le
banc. Deux causes dans `proto/e2/transitions/superposees.py` (`phases_r1`, `r1`) : (1) grille **uniforme** `bar/4` au
lieu de l'espacement réel des temps de Spotify : la mesure d'entrée de B durait 1,537 s chez Spotify, ses temps 375 ms
et non 384, si bien que la grille dérivait de 9 ms par temps et posait le 1 final de B 34 ms trop tard (et étirait B de
2,5 % à tort) ; (2) phase de B mesurée sur **2 mesures** seulement : l'entrée de B, sans grosse caisse et syncopée
(coups à +90 ms), donnait +50 ms (+100 ms sur les vrais temps), alors que sur 13 temps elle vaut −0,3 ms. Correctif :
temps de A et de B pris aux temps de Spotify recalés (`_grille`, `_grilles_r1` ; uniforme à défaut), phase de B mesurée
sur jusqu'à 16 temps (`R1_TEMPS_B`), durée de la dernière mesure de A et étirement de B calculés sur ces temps. Sur la
même mémoire : phase de B +5 ms, vérifié −5 ms (avant : +104). Test : `proto/e2/test_rendu.py` (« 1 bis », R1 à 155 et
128 BPM, mesure de B fausse de ±2,5 %, 6 temps d'entrée sans grosse caisse, coup syncopé à +90 ms un temps sur quatre :
1 final de B à +63, +66, −28 ms de son vrai 1 avant, −5 ms après). Spec §14 mise à jour.

Tests après correctif : `for t in proto/e2/test_*.py; do python3 -I $t; done` : tout passe (6 / 6) ;
`node --test spicetify/test/` : 59 / 59.

### Constats non corrigés (décisions du développeur)

- **Calage rapporté de R1** : mesuré sur la 1re mesure de B, il ne voit rien quand B entre sans attaques (rapporté
  +105, −30, −55 ms pour un calage vérifié de −5, −0, +5 ms) : l'écran affichera de faux échecs de 9.1-1. Le mesurer
  sur les temps de B qui suivent son 1 final serait plus juste. **Corrigé depuis** (Corrections après essai, 5).
- **C5 à C8** (`calage.caler_superposition`) gardent la grille uniforme `bar/4` : même cause que R1, mais le calage y
  est mesuré sur le son produit et refusé au-delà de 20 ms (repli vers R1, comme j-a15 à +35 ms) : pas de son décalé,
  des replis en plus. L'écart de tempo du plan (`g`) vient aussi des durées de mesure : 2,7 % sur la paire 7 alors que
  les temps de A et de B sont égaux à 0,3 % près. **Grille corrigée depuis** (Corrections après essai, 5) ; l'écart
  de tempo du plan, non.
- **C1 presque jamais jouée en rap FR avec V1** : la fin de A est chantée sur les 4 paires essayées (R2 à la place).
- **O5** compare le segment à B **après** la reprise : une intro calme de B incluse dans le segment (C2, R1) compte
  comme un creux.
- `echange_ms` de R2 : raccord de 20 ms vu comme une superposition (critère non applicable à R2).
- Enregistrements supprimés après analyse ; extraits gardés (`j2-*`, ci-dessous).

### Écoute

17 extraits `j2-*.ogg` ajoutés dans `~/spotify_dj_mixer-ecoute/` (même convention à l'aveugle : `LISEZ-MOI.md`,
entrées `j2-…` de `correspondance-cachee.json` avec le calage vérifié). Les 2 R1 d'avant correctif ne sont pas gardés.
