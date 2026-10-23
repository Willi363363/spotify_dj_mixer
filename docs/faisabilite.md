# Faisabilité

Catalogue de tout ce qui a été envisagé. **E1** = prototype sans module audio maison, **E2** = module PipeWire avec avance en mémoire (cf. [`architecture.md`](architecture.md)). Statuts définis dans [`README.md`](README.md#conventions-de-statut).

## Analyse et décisions (extension Spicetify)

| Fonction | Statut | Étape | Preuve |
|---|---|---|---|
| Tempo, tonalité, temps, mesures, sections d'un morceau | ✅ Testé | E1 | [`tests/01-analyse-audio.md`](tests/01-analyse-audio.md) |
| Repérer le drop (section la plus forte) | ✅ Testé | E1 | idem |
| Choisir le moment de transition (fin de phrase, de section) | Supposé | E1 | Smart DJ le fait |
| Point d'entrée du suivant : drop, ou temps qui ressemble au dernier joué | Supposé | E1 | [`recherche/eternal-jukebox.md`](recherche/eternal-jukebox.md) |
| Noter la compatibilité de deux morceaux (tempo, tonalité, énergie) | Supposé | E1 | [`recherche/smart-dj.md`](recherche/smart-dj.md) |
| Trier la file d'attente pour enchaîner les morceaux compatibles | Supposé, seulement les morceaux ajoutés à la main | E1 | idem |
| Afficher tempo et tonalité | Supposé | E1 | spicetify-dj-info le fait |
| Bouton ou raccourci « transition maintenant » | Supposé | E1 | API Spicetify |
| Reconnaître une pub et ne pas la mixer | Supposé | E1 | à vérifier |

## Commandes du lecteur (Spotify)

| Fonction | Statut | Étape | Preuve |
|---|---|---|---|
| Sauter dans un morceau, lancer un morceau, passer au suivant | ✅ Testé (compte gratuit) | E1 | [`tests/03-boucle-par-saut.md`](tests/03-boucle-par-saut.md) |
| Boucle calée sur la mesure | ✅ Testé, rythme juste (9 ms) | E1 | idem |
| Micro-silences à chaque saut | ⚠️ Testé : 5 à 10 ms sur 2 à 4 reprises sur 8 | E1, masqués en E2 | idem |
| Fondu de volume réglable | Supposé | E1 | API Spicetify |
| Changer la vitesse de la musique | ❌ Testé : refusé par Spotify | — | [`tests/02-vitesse-lecture.md`](tests/02-vitesse-lecture.md) |
| Fondu enchaîné natif, Spotify Mix | ❌ Premium uniquement | — | [`recherche/etat-de-l-art.md`](recherche/etat-de-l-art.md) |

## Effets sur le son (PipeWire)

| Fonction | Statut | Étape | Preuve |
|---|---|---|---|
| Couper les basses, les relâcher sur le drop | ✅ Testé (−17 dB) | E1 | [`tests/04-filtre-pipewire.md`](tests/04-filtre-pipewire.md) |
| Balayage de filtre | ✅ Testé | E1 | idem |
| Égaliseur graves, médiums, aigus | Supposé (fourni avec PipeWire) | E1 | idem |
| Écho, réverbération | Supposé | E1 | idem |
| Effets pilotés au temps près depuis l'extension | ✅ Testé (0,7 ms) | E1 | [`tests/05-connexion-locale.md`](tests/05-connexion-locale.md) |
| Boucle sans silence, rejouée depuis la mémoire | Supposé | E2 | [`architecture.md`](architecture.md#e2-le-module-avec-avance) |
| Superposer deux morceaux sans Premium | Supposé | E2 | idem |
| Effet sur un seul des deux morceaux (échange des basses) | Supposé | E2 | idem |
| Caler les tempos pendant la transition, sans changer la hauteur | Supposé, environ ±6 % | E2 | idem |
| Effet « vinyle qui freine » | Supposé | E2 | idem |
| Scratch sur le son déjà passé | Supposé, théorique | E2 | idem |

## Impossible

| Fonction | Pourquoi |
|---|---|
| Effet sur un seul morceau **en E1** | Une seule sortie son : le filtre touche tout ce qui passe |
| Accélérer longtemps | L'avance en mémoire s'épuise. Ralentir n'a pas de limite |
| Connaître le son au-delà de l'avance en mémoire | Spotify envoie le son en temps réel. L'analyse de Spotify compense |
| Modifier le son dans Spotify lui-même | Décodage hors de la partie web, aucun accès |

## Coûts de l'étape E2

- **Décalage écran / son** de quelques secondes (barre de progression, paroles) pendant le mode DJ.
- **Pause et morceau suivant** à faire traiter par le module, sinon ils réagissent en retard.
- **Gros chantier** : un petit moteur de mixage en Rust ou en C.
