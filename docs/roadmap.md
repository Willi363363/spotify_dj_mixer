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
| Dans une montée, **B monte sous les 2 dernières mesures** (Spotify le lance 2 mesures avant son drop) et enchaîne sur son drop sans raccord | Validé à l'écoute (essai 11) ; B qui surgit d'un coup a été jugé « sec, pas smooth » |
| Chaque avis d'écoute est reporté dans [`gouts.md`](gouts.md) et dans [`tests/09-ecoute-maquette.md`](tests/09-ecoute-maquette.md) | Demande du développeur |
| La **coupe seule** n'est jamais choisie d'office | Rejetée à l'écoute (« absolument horrible ») alors que la recherche la donne comme signature du rap |
| Choix automatique limité aux transitions **validées à l'écoute** : mélange si les morceaux se calent, **montée** sinon ; une superposition impossible **se replie sur la montée** | La montée ne demande aucun calage ; les autres préréglages attendent d'être jugés |
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
