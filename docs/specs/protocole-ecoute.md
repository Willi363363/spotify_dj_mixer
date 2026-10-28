# Protocole d'écoute v2 : les 16 paires (§9.2 de [`transitions-v2.md`](transitions-v2.md), tâche 16)

Statut : choix à blanc du 2026-10-28, **à finir en direct**. Spotify n'était pas lancé : les paires sont définies par des
critères mesurables sur l'analyse Spotify. Les URI sont à remplir par le développeur dans sa bibliothèque (playlists de
`GENRE_REFS`, `spicetify/dj-auto.js`). Seules quatre URI apparaissent dans le dépôt (voir en bas). Les résultats
vont dans `docs/tests/12-ecoute-transitions-v2.md`.

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
| 1 | rap FR → rap FR, tempos proches, bords vocaux | g ≤ 2 %, sansVoixA < 8 et sansVoixB < 8, grilles nettes | C6 ou C5 (profil court) ; C1, C2 possibles | `…` | `…` |
| 2 | rap FR → rap FR, tempos à 6-10 % | 6 % < g ≤ 10 % | C1, C2, C3 (pas de superposition) | `…` | `…` |
| 3 | rap → rap, intro de B instrumentale ≥ 4 mesures | g ≤ 6 %, `voixB[0..3]` toutes < 0,3, k ≤ 2 ou inconnue | C6 (sinon C5) | `…` | `…` |
| 4 | outro instrumentale longue des deux côtés | sansVoixA ≥ 16, sansVoixB ≥ 16, g ≤ 5 %, k ≤ 1 sûre, tempo 110-135 | C7 sur 16 mesures (profil long) | `…` | `…` |
| 5 | shatta → shatta | deux morceaux de la playlist shatta, g ≤ 6 % | C3, C1, C5 | `…` | `…` |
| 6 | shatta → bouyon (≈ 3:2) | `paire.rapport32` vrai | C1, C2, C3 ; jamais C5-C8 | `…` | `…` |
| 7 | bouyon → bouyon | deux morceaux bouyon (≈ 150-160 BPM), g ≤ 6 % | C5, C6, C1 | `…` | `…` |
| 8 | calme → fort | ΔE ≥ +4 dB, refrain de B à ≤ 45 s et ≤ 25 % | C4, C8, C1 sur E2 | `…` | `…` |
| 9 | fort → calme | ΔE ≤ −4 dB | C2, C7 (si instrumental), C1 ; jamais C4 ni C8 | `…` | `…` |
| 10 | tonalités qui se heurtent | k ≥ 4, les deux `key_confidence` ≥ 0,4 | C1, C2, C3 (C5/C6 refusés : Camelot) | `…` | `…` |
| 11 | grille floue (« ! » chez Spotify) | `grilleA` ou `grilleB` = `floue` | C2 si grille de A correcte, sinon R1 / R2 | `…` | `…` |
| 12 | A qui finit net (pas d'outro) | dernière section de A = dernière section pleine (`sectionsA`) | sortie de repli (dernière phrase avant les 6 dernières s), C1 ou C2 | `…` | `…` |
| 13 | A à longue fin (fade-out, outro parlée) | outro de A > 30 s | garde-fou : jamais entendu ≤ 30 s ; vérifier la note « fin coupée » | `…` | `…` |
| 14 | même artiste | même `artist_name` | toutes ; sert à juger le contraste | `…` | `…` |
| 15 | tonalités et tempos identiques | g ≤ 1 %, k = 0 sûre | C5, C6, C7 favorisés (× 1,5) | `…` | `…` |
| 16 | album dans l'ordre | contexte `spotify:album:…`, lecture aléatoire coupée, deux pistes qui se suivent | R2 (refus d'office) | `…` | `…` |

Pistes déjà dans le dépôt, à placer après vérification de leur genre et de leur analyse :
`spotify:track:1bepxgCj8gKHOmoSGiW5J3` (Bubble Like Soup) → `spotify:track:1YKIUWyelwdDfeKzwSTBn1` (Coucounia) est
la paire par défaut de `run.sh` ; `spotify:track:1GiJNHhNGReHSeHbkU02DX` (Mwen An Sa) ;
`spotify:track:1pKYYY0dkg23sQQXi0Q5zN` (Around the World, house : candidat pour les cas 4 ou 13).

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
