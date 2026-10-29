# Faisabilité

Catalogue de tout ce qui a été envisagé. **E1** = prototype sans module audio maison, **E2** = module PipeWire avec avance en mémoire (cf. [`architecture.md`](architecture.md)). Statuts définis dans [`README.md`](README.md#conventions-de-statut). « Mesuré » = vérifié par un enregistrement, sans avis à l'oreille.

## Analyse et décisions (extension Spicetify)

| Fonction | Statut | Étape | Preuve |
|---|---|---|---|
| Tempo, tonalité, temps, mesures, sections | ✅ Testé, 9 morceaux sur 10 couverts | E1 | [01](tests/01-analyse-audio.md), [06 A1](tests/06-serie-a-spotify.md#a1--analyse-dune-vraie-file-dattente-a1-decisionsjs) |
| Énergie d'un morceau (`audio-features`) | ✅ Testé | E1 | [06 A1](tests/06-serie-a-spotify.md#a1--analyse-dune-vraie-file-dattente-a1-decisionsjs) |
| Repérer le drop (section la plus forte) | ✅ Testé | E1 | [01](tests/01-analyse-audio.md) |
| Repérer l'outro | ⚠️ Heuristique simple peu fiable, à reprendre | E1 | [06 A1](tests/06-serie-a-spotify.md#a1--analyse-dune-vraie-file-dattente-a1-decisionsjs) |
| Compatibilité de deux morceaux (tempo, Camelot, énergie) | ✅ Calculée ; tonalité souvent peu fiable | E1 | idem |
| Entrée sur le temps qui ressemble au dernier joué | ✅ Calculé (0,51 à 0,89), pas écouté | E1 | [06 A7](tests/06-serie-a-spotify.md#a7--entrée-par-ressemblance-a7-entree-ressemblancejs) |
| Ajouter / retirer un morceau de la file | ✅ Testé | E1 | [06 A5](tests/06-serie-a-spotify.md#a5--file-dattente) |
| Réordonner les morceaux de la playlist | ❌ Seuls les morceaux ajoutés à la main sont modifiables | — | idem |
| Bouton dans la barre de lecture, raccourci clavier | ✅ Testé | E1 | [06 A4](tests/06-serie-a-spotify.md#a4--interface-a4-interface-file-pubjs) |
| Afficher tempo et tonalité | ✅ Testé (libellé du bouton) | E1 | idem |
| Être prévenu d'une pub audio | ⚠️ API trouvée (`AdManagers.inStreamApi`), non observée en direct (aucune pub non plus pendant l'essai 13, ~2 h) | E1 | [06 A6](tests/06-serie-a-spotify.md#a6--pubs) |

## Commandes du lecteur (Spotify)

| Fonction | Statut | Étape | Preuve |
|---|---|---|---|
| Sauter dans un morceau, passer au suivant | ✅ Testé (compte gratuit) | E1 | [03](tests/03-boucle-par-saut.md) |
| Lancer un morceau à une position précise | ✅ Testé (`PlayerAPI.play` + `seekTo`) | E1 | [06 A2](tests/06-serie-a-spotify.md#a2--transition-vers-le-drop-du-suivant-a2-transitionjs) |
| Boucle calée sur la mesure | ✅ Testé, rythme juste (9 ms) | E1 | [03](tests/03-boucle-par-saut.md) |
| Trou à un saut dans le même morceau | ⚠️ 5 à 10 ms | E1, supprimé en E2 | idem |
| Trou au changement de morceau | ⚠️ **12 à 400 ms**, très variable | E1, supprimé en E2 | [06 A2](tests/06-serie-a-spotify.md#a2--transition-vers-le-drop-du-suivant-a2-transitionjs), [08](tests/08-serie-c-maquette-e2.md) |
| Fondu de volume | ✅ Mesuré ; courbe au cube, ~12 réglages/s | E1 | [06 A3](tests/06-serie-a-spotify.md#a3--fondu-de-volume-a3-fondu-volumejs) |
| Changer la vitesse de la musique | ❌ Testé : refusé par Spotify | — | [02](tests/02-vitesse-lecture.md) |
| Fondu enchaîné natif, Spotify Mix | ❌ Premium uniquement | — | [recherche](recherche/plateformes.md) |

## Effets sur le son (PipeWire)

| Fonction | Statut | Étape | Preuve |
|---|---|---|---|
| Couper les basses, balayage de filtre | ✅ Mesuré (−17 dB) | E1 | [04](tests/04-filtre-pipewire.md) |
| Égaliseur graves, médiums, aigus | ✅ Mesuré (−10 / 0 / +5 dB) | E1 | [07](tests/07-serie-b-effets.md) |
| Écho avec répétitions | ✅ Mesuré | E1 | idem |
| Réverbération | Supposé (nœud `convolver`, `lsp-plugins`) | E1 | idem |
| Balayage sans clic | ⚠️ Clics mesurés avec les nœuds fournis | E1 avec effets lissés, ou E2 | idem |
| Effets pilotés depuis l'extension | ✅ Connexion testée (0,7 ms) | E1 | [05](tests/05-connexion-locale.md) |
| Son retardé en mémoire, sans perte | ✅ Mesuré (20,01 s, ressemblance 0,9998) | E2 | [08](tests/08-serie-c-maquette-e2.md) |
| Superposer deux morceaux sans Premium | ✅ Maquette (mix de 4 mesures, échange des basses) | E2 | [08](tests/08-serie-c-maquette-e2.md) |
| Temps de A et B ensemble pendant une superposition | ✅ Mesuré : 0 à 10 ms (grille de Spotify + correction) | E2 | [10](tests/10-calage.md) |
| Échange des basses entre les deux morceaux | ✅ Maquette | E2 | [08](tests/08-serie-c-maquette-e2.md) |
| Caler les tempos sans changer la hauteur | ✅ Maquette (`rubberband`) ; utile sous ~6 % d'écart | E2 | idem |
| Boucle sans silence depuis la mémoire | ✅ Mesuré : aucun silence | E2 | idem |
| Effet « vinyle qui freine » | ✅ Maquette | E2 | idem |
| Catalogue v2 (C1-C8, replis R1/R2), placement et choix automatiques | ✅ Mesuré en direct dans Spotify (10 transitions, 16 paires, mode auto réel) ; **pas écouté** ; C7 seulement forcée (jamais éligible), voix V2/V3 peu fiables | E2 | [13](tests/13-essai-direct-v2.md), [spec](specs/transitions-v2.md), [protocole](specs/protocole-ecoute.md) |
| Scratch sur le son déjà passé | Supposé, même mécanisme que le freinage | E2 | — |

**Écoute** : aucune transition v2 n'a encore été jugée à l'oreille (essai 13 : mesures sur le son réel, extraits enregistrés pour l'écoute à l'aveugle) ; le protocole est dans [`specs/protocole-ecoute.md`](specs/protocole-ecoute.md). Transitions de DJ et ce qui est faisable chez nous : [`recherche/methodes-dj.md`](recherche/methodes-dj.md).

## Impossible

| Fonction | Pourquoi |
|---|---|
| Effet sur un seul morceau **en E1** | Une seule sortie son : le filtre touche tout ce qui passe |
| Accélérer longtemps | L'avance en mémoire s'épuise. Ralentir n'a pas de limite |
| Connaître le son au-delà de l'avance | Spotify envoie le son en temps réel. L'analyse compense |
| Modifier le son dans Spotify lui-même | Décodage hors de la partie web |

## Coûts de l'étape E2

- **Décalage écran / son** de l'avance (~60 s dans la maquette ; à réduire).
- **Pubs** à faire traiter par le module (pause et morceau changé à la main sont traités par la maquette).
- **Moteur à écrire en Rust ou C** : la maquette Python a laissé passer 2 trous de 45 ms.
