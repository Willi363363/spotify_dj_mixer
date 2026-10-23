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

## Hors périmètre

| Piste | Raison |
|---|---|
| Thème Spicetify | Coût en performance jugé trop élevé |
| Client librespot | Client non officiel, risque de bannissement du compte |
| Son récupéré sur YouTube (méthode Eternal Jukebox) | Contraire aux conditions de YouTube, et on sort de Spotify |
| Spotify Mix, fondu natif | Réservés à Premium |
