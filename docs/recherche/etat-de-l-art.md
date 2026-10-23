# État de l'art

## Dans Spotify

| Fonction | Accès | Ce qu'elle fait |
|---|---|---|
| **Fondu enchaîné** (Paramètres → Lecture) | Premium sur les versions récentes (selon le README de Smart DJ) | Superpose fin et début, sans calage du rythme |
| **Automix** | Premium | Transitions calées sur le rythme, sur certaines playlists Spotify ([Spotify](https://community.spotify.com/t5/FAQs/Automix-Overview/ta-p/5257278/highlight/true), [aide](https://support.spotify.com/article/tracks-transitions)) |
| **Mix** (août 2025) | Premium | Transitions réglables dans ses playlists : volume, égaliseur, courbes d'effets, tempo et tonalité affichés, préréglages Fade et Rise ([GSMArena](https://www.gsmarena.com/spotify_now_lets_you_mix_your_playlists_with_your_own_transitions-news-69116.php), [Android Authority](https://www.androidauthority.com/spotify-playlists-custom-transitions-3588565/), [CMU](https://completemusicupdate.com/spotify-launches-new-tool-to-add-customised-transitions-to-playlists/)). Disponibilité sur desktop non vérifiée |
| Égaliseur | Mobile seulement | Absent du client Linux ([forum](https://community.spotify.com/t5/Desktop-Linux/Linux-Desktop-No-equalizer/td-p/5020753)) |

Tout est **Premium** : rien n'est utilisable avec le compte gratuit du projet.

## Apple Music AutoMix (iOS 26)

Analyse tempo et tonalité, puis **étirement temporel et calage des temps** pendant la lecture, sur l'appareil, sans changer la hauteur ([MusicTech](https://musictech.com/news/gear/apple-music-automix-ai/), [9to5Mac](https://9to5mac.com/2025/06/16/automix-apple-music-ios-26/)). Toutes les transitions ne sont pas des mélanges : parfois un blanc, parfois une simple superposition.

C'est exactement la méthode prévue pour l'étape E2 (cf. [`../architecture.md`](../architecture.md#e2-le-module-avec-avance)) : elle a fait ses preuves.

## Logiciels de DJ

| Outil | Intérêt | Limite |
|---|---|---|
| **Mixxx** | Libre, disponible sur Arch : deux platines, calage du tempo, filtres, Auto DJ | Fichiers locaux uniquement. Sert de **modèle** pour le moteur E2 |
| djay, rekordbox, Serato | Intégration Apple Music depuis 2024 (de mémoire, non vérifié), TIDAL, Beatport | Pas de Linux ; Spotify retiré des logiciels de DJ depuis 2020 |

## Filtres système sous Linux

**EasyEffects** applique égaliseur et renfort des basses à une appli comme Spotify via PipeWire ([OMG! Ubuntu](https://omgubuntu.co.uk/2023/05/easy-effects-ubuntu)). Réglage fixe, pas piloté par la musique. Notre filtre du [test 04](../tests/04-filtre-pipewire.md) fait la même chose, mais piloté.

## Extensions Spicetify existantes

| Extension | Ce qu'elle fait |
|---|---|
| [Smart DJ](https://github.com/guilhepinheiro1701-create/spicetify-automix) | Transitions intelligentes, cf. [`smart-dj.md`](smart-dj.md) |
| [spicetify-dj-info](https://github.com/L3-N0X/spicetify-dj-info) (71 étoiles) | Affiche tempo, tonalité, année, popularité |
| [copopit/spicetify-dj](https://github.com/copopit/spicetify-dj) | Squelette de projet vide |

## Écarté : librespot

Client Spotify libre (base de spotifyd et raspotify), capable d'envoyer le son vers un autre programme ([wiki](https://github.com/librespot-org/librespot/wiki)). **Écarté** : client non officiel, donc risque de bannissement du compte, et décoder plus vite que le temps réel revient à télécharger les morceaux.
