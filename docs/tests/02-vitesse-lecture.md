# 02 · Vitesse de lecture

**Question** : peut-on ralentir ou accélérer la musique dans Spotify, pour un effet « vinyle qui freine » ou un calage de tempo ?

## Protocole

1. Lister les méthodes du lecteur interne contenant `speed`, `rate`, `tempo` ou `pitch`.
2. Appeler `Spicetify.Platform.PlayerAPI.setSpeed(1.5)` sur un morceau de musique, relire l'état, remettre `1`.

## Résultat

| Élément | Constat |
|---|---|
| Méthode trouvée | `PlayerAPI.setSpeed` (une seule) |
| Morceau | « Money Pull Up », type `track` |
| Réponse | `Command failed with code '1' and reasons 'not_supported_by_content_type'` |
| Vitesse après l'appel | inchangée (1) |

La vitesse est réservée aux podcasts et livres audio.

## API voisines relevées

| API | Méthodes utiles |
|---|---|
| `Platform.PlaybackAPI` | `getVolume`, `setVolume`, `raiseVolume`, `lowerVolume`, `getPlaybackInfo`, `getCapabilities` |
| `Platform.PlaybackFiltersAPI` | `getFilterState`, `isNormalizationOverridden`… (normalisation du volume, pas d'égaliseur) |

Aucune n'agit sur la vitesse ni sur les fréquences.

## Conclusion

❌ Impossible dans Spotify. La vitesse ne peut se changer qu'**après** Spotify, dans le module PipeWire de l'étape E2 (cf. [`../architecture.md`](../architecture.md#e2-le-module-avec-avance)).
