# Protocole d'écoute v2 : les 16 paires (§9.2 de [`transitions-v2.md`](transitions-v2.md), tâche 16)

Statut : critères fixés à blanc le 2026-10-28, **paires remplies et jouées en direct le même jour** (essai
[`../tests/13-essai-direct-v2.md`](../tests/13-essai-direct-v2.md) : mesuré, **pas écouté**). Morceaux pris dans les
playlists de la bibliothèque (`GENRE_REFS` et 5 autres), critères vérifiés sur `getAudioData` avec `DJCore` (avance 60 s).
Extraits enregistrés de chaque transition jouée : `~/spotify_dj_mixer-ecoute/` (hors dépôt, à l'aveugle). Les résultats
de l'écoute vont dans `docs/tests/12-ecoute-transitions-v2.md`.

## Comment vérifier qu'une paire remplit son critère

Dans la console de Spotify (mode débogage), avec l'extension v2 installée :

```js
const c = await DJ.planTransition('spotify:track:A…', 'spotify:track:B…', { contexte: null, graine: 1 });
c.raison;                                    // profil · g (écart de tempo) · k (Camelot) · ΔE · poids
c.paire;                                     // tempo, g, k, rapport32, voix_source, profil, deltaE
c.points.bords;                              // grilleA/B, voixA/B par mesure, sansVoixA/B
c.refus;                                     // pourquoi chaque autre transition est inéligible
```

Notations : g = écart de tempo (moitié et double comptés), k = distance Camelot (null si `key_confidence` < 0,4),
ΔE = sonie de B après son point d'arrivée moins celle de A avant sa sortie, « sans voix » = V2 < 0,3 par mesure.

## Les 16 paires

| # | Cas (§9.2) | Critère mesurable sur la paire | Transitions attendues | A (uri) | B (uri) |
|---|---|---|---|---|---|
| 1 | rap FR → rap FR, tempos proches, bords vocaux | g ≤ 2 %, sansVoixA < 8 et sansVoixB < 8, grilles nettes | C6 ou C5 (profil court) ; C1, C2 possibles | Lacrim – LOSE CONTROL `0qW7TuFAr8erCQRcnbFXtE` | Alonzo – HASTA LA VISTA `14j9HbZoSdTooGK12uTNRc` |
| 2 | rap FR → rap FR, tempos à 6-10 % | 6 % < g ≤ 10 % | C1, C2, C3 (pas de superposition) | Ashvma – VIENS VOIR `6c5ognUdZPoE8Ou4BMpLwk` | RDN – Prêt à partir `3c0pxgMUOq5I1A0KvrZavB` |
| 3 | rap → rap, intro de B instrumentale ≥ 4 mesures | g ≤ 6 %, `voixB[0..3]` toutes < 0,3, k ≤ 2 ou inconnue | C6 (sinon C5) | Zola – NETFLIX CHILL `6Ap1nvdC4XT3p2Oj627ciD` | Lacrim – François Besse `5U5FsHmXubZJsot12ebXlA` |
| 4 | outro instrumentale longue des deux côtés | sansVoixA ≥ 16, sansVoixB ≥ 16, g ≤ 5 %, k ≤ 1 sûre, tempo 110-135 | C7 sur 16 mesures (profil long) | Age Of Love – The Age Of Love (remix) `38i2IOw4HtOUDDocgNT0o7` | Yeah Yeah Yeahs – Heads Will Roll (A-Trak) `5bs8OXiOt4BPF2FAnRFP1u` |
| 5 | shatta → shatta | deux morceaux de la playlist shatta, g ≤ 6 % | C3, C1, C5 | Damso – Alpha `2dVDbbS9W6n6YY80R4aJdZ` | Loco – Wolidèh `2NcN3pHVhYO2PeZy7bPSUS` |
| 6 | shatta → bouyon (≈ 3:2) | `paire.rapport32` vrai | C1, C2, C3 ; jamais C5-C8 | BAD BITCH JD – TON MEC `70GTNgFb4oAReeYd08kcuI` | Lomiiel – HAY LUPITA `0vCmFYoAvaPuXi1efkHn8O` |
| 7 | bouyon → bouyon | deux morceaux bouyon (≈ 150-160 BPM), g ≤ 6 % | C5, C6, C1 | LeJuh – Air Force One `0pSvdkde7vTbWl0w2G66dQ` | Theodora – KONGOLESE SOUS BBL `5dBRz6giSIBDkXOhOD80KF` |
| 8 | calme → fort | ΔE ≥ +4 dB, refrain de B à ≤ 45 s et ≤ 25 % | C4, C8, C1 sur E2 | Josman – LONDON ST TROPEZ `6kyi8X8pjlkMROgFNb3ttA` | Luidji – Pour deux âmes solitaires `78SR3uKM8liycwwuLky8ub` |
| 9 | fort → calme | ΔE ≤ −4 dB | C2, C7 (si instrumental), C1 ; jamais C4 ni C8 | Guy2Bezbar – Nouvelle R `5sD5Ee7owEXhN46QGaebi6` | HOUDI – MODE HARDCORE `1LZEnWMTFXZ9uhlMIyLJtM` |
| 10 | tonalités qui se heurtent | k ≥ 4, les deux `key_confidence` ≥ 0,4 | C1, C2, C3 (C5/C6 refusés : Camelot) | Guy2Bezbar – Tentation `18M04FaA1qU3GYrynMMz2j` | RDN – Prêt à partir `3c0pxgMUOq5I1A0KvrZavB` |
| 11 | grille floue (« ! » chez Spotify) | `grilleA` ou `grilleB` = `floue` | C2 si grille de A correcte, sinon R1 / R2 | Alonzo – FAGNA BOOSTÉ `2l7dqp2Ln2lC2j8VrRTgIS` | D2L – Mandarine `31aLact8JEefiiF4UGBFy7` |
| 12 | A qui finit net (pas d'outro) | dernière section de A = dernière section pleine (`sectionsA`) | sortie de repli (dernière phrase avant les 6 dernières s), C1 ou C2 | Bilouki – Tchébé 2x `7l3b0X95GdYfRuW8Kq5ixC` | Guy2Bezbar – Big mama `1TXuor1bUOZQnWrksFoccd` |
| 13 | A à longue fin (fade-out, outro parlée) | outro de A > 30 s | garde-fou : jamais entendu ≤ 30 s ; vérifier la note « fin coupée » | Kendrick Lamar – Poetic Justice `3MLOAIJNWWS8FQpvdaiKR7` | Niska – Matuidi Charo `2CLe4twLMtjKwWzRYzGaIA` |
| 14 | même artiste | même `artist_name` | toutes ; sert à juger le contraste | Ninho – Elle a mal `2ct8sYE8u8UZT229rWvXwL` | Ninho – Mood `2KnZ3KmkarHJM6F1t6vdk2` |
| 15 | tonalités et tempos identiques | g ≤ 1 %, k = 0 sûre | C5, C6, C7 favorisés (× 1,5) | Central Cee – Bolide Noir `14DLZ9FaTofhnXBiV38axE` | Hornet La Frappe – Sentimental `20EsC68rnqaVgLsfgJbI78` |
| 16 | album dans l'ordre | contexte `spotify:album:…`, lecture aléatoire coupée, deux pistes qui se suivent | R2 (refus d'office) | Damso – Graine de sablier (album Batterie faible, piste 7) `0H9sMunfG1M6HshCifS0ex` | Damso – Beautiful (piste 8) `1Dh0jxIlFvGLgTEfg7qe6P` |

Mesuré sur ces paires (avance 60 s, sortie après 52 s de A) : 1 g 1,6 % ΔE −14,8 dB grilles nette/nette ; 2 g 7,0 % ;
3 g 6,0 % k 0, intro de B sans voix (V2) ; **4 approchée** : aucune paire de la bibliothèque ne remplit le critère (V2 juge
« vocal » la fin de 67 % des morceaux, même instrumentaux), prise au plus près (sans voix 6/16, k inconnue) ; 5 g 0,0 % k 0 ;
6 rapport 3:2 (98 → 145) ; 7 g 2,7 % ; 8 ΔE +5,9 dB, C4 et C8 éligibles ; 9 ΔE −29,6 dB ; 10 k 4 sûre ; 11 grille de B
floue ; 12 fin de A = dernière section pleine ; 13 outro de A 41 s (fondu) ; 14 même artiste ; 15 g 0,7 % k 0 ; 16 contexte
`spotify:album:4beTtJKeg3ITJsiVuxkiV0`, lecture aléatoire coupée ; il ne se joue qu'en **mode auto** (`run.sh` et l'écran
passent `contexte: null`, donc jamais de refus d'office).
Paires de forçage ajoutées : **17** Kendrick Lamar – Poetic Justice `3MLOAIJNWWS8FQpvdaiKR7` → Gazo – FIESTA
`46Vrz1HTKrD5A5Hbr52VdQ` (C4, C8 sur 8 mesures) ; **18** Poetic Justice → HOUDI – SENSATION `0pIWSS7xmChrYzfNFEfdzn` (C8).

## Couvrir les 8 transitions au moins 2 fois

Après la première séance (choix automatique), compter les transitions jouées. Pour chacune qui manque, la forcer sur une
paire où elle est éligible (les refus de `c.refus` disent laquelle) avec `DJ.forcer('C4')` (vaut pour la transition
suivante) ou `proto/e2/run.sh <ws> C4 <dossier> <A> <B>`. Paires de forçage prévues :

| Transition | Paires où elle est éligible (critère) |
|---|---|
| C1 | 2, 6, 10 |
| C2 | 2, 9, 11 (grille de A correcte) |
| C3 | 5, 6 (profil court ; au plus 1 sur 6) |
| C4 | 8 (ΔE ≥ +2, refrain proche, mesure bouclée sans voix) |
| C5 | 1, 7, 15 |
| C6 | 3, 15 |
| C7 | 4 (seule paire sûre ; V2 reconnaît mal un morceau entièrement instrumental, cf. limites) |
| C8 | 8 (si le refrain de B est à ≤ T mesures après son intro) |

Le nom de la transition reste masqué jusqu'à la note (écran en mode aveugle). Deux séances de 15 min.

## Limites connues avant l'écoute

- Voix au plan (V2) non calibrée : relative au morceau, elle peut croire « vocal » un morceau entièrement
  instrumental, donc moins de C6/C7 que prévu. Allumer les paroles (`dj-mixer:paroles` = `1`) pour comparer, si elles
  sont disponibles sur le compte (tâche 2-direct).
- Voix au rendu (V3) : faux positifs sur des mélodies de synthé rapides (seuil de repli à 0,6).
- Les cas 4 et 8 sont rares en rap FR : les chercher en priorité.
