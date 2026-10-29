# Mode DJ dans Spotify (transitions v2)

Installé par `installer.sh` : cinq extensions et une app. La règle de choix vit ici ; le moteur [`../proto/e2/`](../proto/e2/README.md) ne fait que rendre ce qu'on lui demande. Spec : [`../docs/specs/transitions-v2.md`](../docs/specs/transitions-v2.md) ; découpage en modules : [ADR 0005](../docs/adr/0005-modules-transitions.md).

| Fichier | Rôle |
|---|---|
| `dj-catalogue.js` | Catalogue d'affichage : nom, famille, couleur, étapes de frise de C1-C8, R1, R2, R3, secours ; étiquettes de note ; `masquer` pour l'écoute à l'aveugle. Servi aussi par le moteur à `ecran.html` |
| `dj-voix.js` | Voix par mesure au plan (ADR 0002) : segments de Spotify (V2) par défaut ; paroles synchronisées (V1) seulement si `dj-mixer:paroles` vaut `1` dans le LocalStorage |
| `dj-placement.js` | Placement (§5) : phrases, confiance de grille, dernière section pleine, sortie de A avec garde-fou fin coupée, entrées E0/E1/E2, ΔE, profil court/long, tempo et Camelot |
| `dj-choix.js` | Choix automatique (§7), repli au plan (§8), construction de l'ordre v2 (ADR 0001) |
| `dj-auto.js` | Orchestration : quand le mode automatique est allumé, planifie la transition vers le suivant de la file, saute pile sur le temps dans le contexte de lecture, envoie l'ordre au moteur, rattrape un changement manuel (R1). Moteur éteint : aucun saut, Spotify joue seul (R3) |
| `dj-mixer/` | Page « Mode DJ » (ci-dessous) |

Les quatre premiers sont des modules purs (`globalThis.DJCore`), sans appel à Spicetify, chargés aussi par Node pour les tests. `dj-auto.js` attend qu'ils soient là.

## Catalogue

| Id | Transition | Famille | Recouvrement (mesures) |
|---|---|---|---|
| C1 | Coupe sur phrase | sec | 0 |
| C2 | Écho | sec | 0 |
| C3 | Frein | effet | 0 |
| C4 | Montée en boucle | effet | 0 (A prolongé, regagne de l'avance) |
| C5 | Fondu calé | superposé | 2 |
| C6 | Mix 3 bandes | superposé | 4 |
| C7 | Échange de basses | superposé | 8 ou 16 |
| C8 | Montée filtrée | superposé | 4 ou 8 |
| R1 · R2 | Fondu court · Bord à bord (replis) | repli | 1 · 0 |
| R3 · secours | Spotify seul (moteur éteint) · transition prête trop tard | — | — |

Courbes, conditions d'usage et échelle de repli : §4 et §8 de la spec.

## Règle de choix

Une fois par morceau : refus d'office (album dans l'ordre, analyse absente → R2) ; caractéristiques de la paire (écart de tempo, Camelot, ΔE, grilles, voix, profil, avance du moteur) ; éligibilité ; poids de base par profil, modulés par l'énergie, la tonalité et l'avance ; variété (jamais la précédente, quotas d'effets, de C2, C3, C4 et du refrain) ; tirage parmi les 3 meilleurs. Une superposition de T mesures exige (2T + 2) × mesure de A + 8 s d'avance. La raison du choix part dans l'ordre (`raison`) pour l'écran.

## API `window.DJ` (console de Spotify, mode débogage)

| Appel | Rôle |
|---|---|
| `DJ.planTransition(A, B, {force, graine, contexte, historique})` | Plan complet à blanc : transition, points, raison, refus de chaque autre transition |
| `DJ.forcer('C4')` | Force la transition suivante du mode automatique |
| `DJ.ordre(choix, {t_wall, id})` | Construit l'ordre v2 ; utilisé par `proto/e2/transition.js` |
| `DJ.switchAt`, `DJ.sendOrder`, `DJ.setAuto(bool)` | Saut 60 ms après la sortie (`DJ.LEAD = −60`), envoi au moteur, interrupteur |
| `DJ.status` | Objet (pas une fonction) : `text`, `plan`, `historique`, `log`, `force` |

## Page « Mode DJ »

Affiche en direct ce que joue le moteur, en 2 colonnes : morceau entendu et compte à rebours, **cercles façon Eternal Jukebox** (A coloré par section, B avec son point d'entrée), visualiseur 16 bandes, frise de la transition, interrupteur du mode automatique, file à venir, et **À noter**.

- **Écoute à l'aveugle** (par défaut, mémorisée) : tant qu'une transition n'est pas notée, ni son nom, ni sa couleur, ni sa frise, ni sa raison ne s'affichent. La note (1 à 5 étoiles, 10 étiquettes, commentaire) part en `POST /rating` avec le seul `id` de la transition ; la ligne se dévoile ensuite (demandée → jouée, replis, mesures).
- **Tester / Rejouer** : choisit une paire et « Auto » ou une transition forcée, puis `POST /run` ; l'ordre produit reçoit un `id` (`essai-<t_wall>`), noté comme les autres.
- États (moteur éteint, sans `DJ_WORK`, extension absente, analyse indisponible, repli, secours) : cf. [`../docs/ux/transitions-v2.md`](../docs/ux/transitions-v2.md).

## Installer / retirer

```bash
spicetify/installer.sh            # liens vers le dépôt, inscription dans Spicetify, redémarre Spotify
spicetify/installer.sh --retirer
```

Après toute modification d'un `dj-*.js` ou de `dj-mixer/index.js`, relancer **`spicetify apply`** : Spicetify copie les fichiers à ce moment-là, un rechargement garde l'ancienne version (cf. [`../docs/pieges.md`](../docs/pieges.md)).

## Tests hors ligne

```bash
node --test spicetify/test/
```

Sur des analyses factices (`test/fixtures/`) et un faux Spicetify : voix (`voix`), placement (`placement`), choix et ordre (`choix`), mode automatique (`auto`), simulation à blanc de 30 transitions avec avance du moteur, O1, O7, quotas et cohérence des identifiants entre les trois catalogues (`simulation`).

## Fonctionnement

- L'app interroge le moteur sur `http://127.0.0.1:47802` (`/state` 8 fois par seconde). Le moteur n'accepte que deux origines : l'écran local et `https://xpui.app.spotify.com`.
- `/run` passe par `run.sh` et le **mode débogage** de Spotify (cf. [`../docs/tests/methode.md`](../docs/tests/methode.md)) ; le moteur retrouve seul l'adresse de Spotify.
- Le choix du morceau suivant (`chooseNext`, playlists de référence) n'a pas changé : hors périmètre de la v2.
