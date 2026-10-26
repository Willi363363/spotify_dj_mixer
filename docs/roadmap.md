# Roadmap

Statuts : ⬜ à faire · 🚧 en cours · ✅ fait · ⏳ en attente d'une décision.

## E0 : cadrage ✅

| Tâche | Statut |
|---|---|
| Vérifier l'accès à l'analyse musicale | ✅ 2026-10-23 |
| Vérifier le contrôle de vitesse | ✅ 2026-10-23 (refusé) |
| Mesurer la boucle par saut, la calibrer | ✅ 2026-10-23 |
| Tester un filtre PipeWire sur Spotify | ✅ 2026-10-23 |
| Tester la connexion extension → programme local | ✅ 2026-10-23 |
| Relire Smart DJ, étudier Eternal Jukebox et l'existant | ✅ 2026-10-23 |
| Tester tous les « supposé » : séries A, B, C (maquette E2) | ✅ 2026-10-23 |
| Écouter les transitions de la maquette E2 | ✅ 2026-10-23 : montée continue validée, mix par fondu rejeté |
| Recherche sur les techniques des DJ | ✅ 2026-10-23, cf. [`recherche/dj/`](recherche/dj/README.md) |
| Observer une vraie pub avec l'API `inStreamApi` | ⏳ au premier passage de pub |
| Documenter le tout | ✅ 2026-10-23 |

## E1 : prototype sans module audio maison ⏳

Objectif : des transitions calées sur le rythme et des effets de filtre pilotés par l'extension, avec les briques déjà testées.

**⏳ Décision attendue** : quelles fonctions entrent dans E1. Candidates, toutes listées dans [`faisabilite.md`](faisabilite.md) :

| Candidate | Brique |
|---|---|
| Transition au moment choisi (fin de phrase, de section) | Extension |
| Entrée du suivant sur son drop | Extension |
| Entrée sur le temps qui ressemble au dernier joué | Extension |
| Boucle sur le drop | Extension |
| Coupe des basses relâchée sur le drop | Extension + programme local + PipeWire |
| Balayage de filtre pendant la transition | idem |
| Écho en sortie de morceau | idem |
| Affichage tempo et tonalité | Extension |
| Bouton « transition maintenant » | Extension |
| Repli quand l'analyse manque, gestion des pubs | Extension |

Choix techniques à trancher au démarrage de E1 :
- **Partir de Smart DJ ou repartir de zéro** pour l'extension (cf. [`recherche/smart-dj.md`](recherche/smart-dj.md)).
- **Langage du programme local**.
- **Installation du filtre** : chargé à la demande par le programme local, ou installé dans la config PipeWire.

## E2 : module PipeWire avec avance ⬜

Objectif : superposition de deux morceaux, échange des basses, calage du tempo, boucle sans silence, « vinyle qui freine ». Conception dans [`architecture.md`](architecture.md#e2-le-module-avec-avance).

Premier jalon à définir au démarrage : un module qui retarde le son de N secondes sans artefact, mesuré par enregistrement.

## Décisions

| Décision | Pourquoi |
|---|---|
| La **montée par roulements sans blanc** est la transition de référence | Validée à l'écoute ; un temps de silence avant le drop a déplu |
| Le **fondu de volume seul** n'est pas une transition DJ | Rejeté deux fois à l'écoute, même calé sur le rythme |
| Le **mélange** se fait temps par temps (tempo qui glisse), recalé à ±½ temps, avec échange des basses et filtre | Validé à l'écoute (« clean de fou ») ; méthode de l'article Spotify 2017 |
| Les transitions sont des **recettes** d'ingrédients (volume, égaliseur, filtre, effets, boucle), choisies automatiquement | Modèle de Spotify Mix, cf. [`recherche/spotify-transitions.md`](recherche/spotify-transitions.md) |
| Le mélange **décide de son refus sur 2 mesures de B** ; repli sur la **montée courte** (B monte sur ses premières mesures) ; une transition prête trop tard ou qui chevaucherait la précédente est **abandonnée** | Essai 12 : repli prêt 23 s trop tard et sec ; essai 13 validé (« c'était doux ») |
| **Mode DJ automatique** (extension `dj-auto.js`) : chaque morceau enchaîne seul sur le suivant de la file, saut dans le contexte de lecture à la bonne position (une commande, ~5 ms de silence) | Demande du développeur ; placement validé à l'écoute (essai 14) |
| **Variété par types** enchaînés par une chaîne de Markov (Vande Veire 2018) : B sur son drop, B depuis son début, mélange, drop swap ; puis un style du type selon l'énergie, jamais un des 2 derniers | « Toujours le même style, aucune originalité » (essai 14) ; revue du 2026-10-26 |
| Styles doux : **B lancé 4 mesures avant** et monte sous A, **calé sur la pulsation de A** (tempo qui glisse vers celui de B, double / moitié compris) quand l'écart ramené est entre −15 et +18 % ; **atterrissage** avec un écho du dernier temps réel de A | Arrivée de B « parfois brutale, brève, sèche » avec 2 mesures (essai 14) |
| Styles doux : **A prolongé** par du synthétique pendant que B monte, en mesures entières, au lieu de sauter les mesures de B : l'avance ne fond plus ; jusqu'à 4 mesures de plus pour la regagner après un mélange ; avance cible **60 s** | Bug de la revue : l'avance fondait de 6 à 10 s par transition, d'où des transitions abandonnées et des sauts secs |
| **Mélange** seulement si tempos à 6 % près (double / moitié compris), tonalités à 1 cran sur la roue de Camelot, et au moins 16 mesures + 8 s d'avance | Un mélange consomme ~8 mesures d'avance ; le choix ne vérifiait que la fiabilité des tonalités |
| **Niveau** : B ramené au niveau de A pendant la transition (borné 0,6 à 1,25), puis revient à son niveau en 16 s ; limiteur au lieu d'une normalisation globale | Saut de volume aux bords des segments (revue) |
| Sorties et entrées sur des **débuts de phrase de 8 mesures** (à défaut 4) ; drop de B cherché dans sa **première moitié** | Kim et al. 2020 ; seuls 48 % des drops tombaient dans les 40 premiers % |
| Chaque transition **se note de 1 à 5** dans l'app (journal `tests/notes-ecoute.jsonl`) | Remplacer « pas si ouf » par des chiffres pour régler les probabilités |
| Chaque avis d'écoute est reporté dans [`gouts.md`](gouts.md) et dans [`tests/09-ecoute-maquette.md`](tests/09-ecoute-maquette.md) | Demande du développeur |
| La **coupe seule** n'est jamais choisie d'office | Rejetée à l'écoute (« absolument horrible ») alors que la recherche la donne comme signature du rap |
| Tout point de transition se **recale sur le son** (attaques de grosse caisse) | Les positions de Spotify ont laissé A et B décalés (accord 0,02) |
| Choix de la transition selon le genre, le tempo, la tonalité, l'énergie, et sans répéter la précédente | Pratique des DJ, cf. [`recherche/dj/automatisation.md`](recherche/dj/automatisation.md) |
| Tests d'écoute : un essai à la fois, annoncé, sur des morceaux pas encore entendus | Sans repères, le développeur ne sait pas ce qu'il entend |

## Hors périmètre

| Piste | Raison |
|---|---|
| Thème Spicetify | Coût en performance jugé trop élevé |
| Client librespot | Client non officiel, risque de bannissement du compte |
| Son récupéré sur YouTube (méthode Eternal Jukebox) | Contraire aux conditions de YouTube, et on sort de Spotify |
| Spotify Mix, fondu natif | Réservés à Premium |
