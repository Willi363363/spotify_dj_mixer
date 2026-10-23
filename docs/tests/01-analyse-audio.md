# 01 · Analyse audio

**Question** : l'analyse musicale de Spotify est-elle encore accessible depuis Spicetify ? Spotify a coupé fin 2024 l'accès public à cette analyse pour les nouvelles applis ; Spicetify passe par une autre porte.

## Ce que fait Spicetify

Code lu dans `/opt/spotify/Apps/xpui/helper/spicetifyWrapper.js` (Spicetify 2.46.2) :

```js
Spicetify.getAudioData = async (uri) =>
  Spicetify.CosmosAsync.get(
    `https://spclient.wg.spotify.com/audio-attributes/v1/audio-analysis/${id}?format=json`)
```

C'est une adresse **interne** du client, appelée avec la session de l'utilisateur, pas l'API web publique.

## Résultat

Morceau : « Mwen An Sa » (SKUNK, Tiitof, Leto).

| Donnée | Valeur |
|---|---|
| Clés renvoyées | `meta`, `track`, `bars`, `beats`, `sections`, `segments`, `tatums` |
| Tempo | 102,06 BPM |
| Tonalité | `key` 11, `mode` 1 = Si majeur |
| Durée | 179,8 s |
| Temps / mesures | 301 / 74 |
| Sections | 12, chacune avec `start`, `loudness`, `tempo` |
| Section la plus forte | 74,1 s à −5,9 dB : candidate pour le drop |

Revérifié sur « Around the World » (Daft Punk) : 121 BPM, mesures de 1,979 s, temps à 341,818 / 342,313 / 342,807 / 343,302 s.

## Limites constatées

- **Fiabilité variable des mesures** : chaque mesure porte un indice `confidence`. La mesure utilisée au test 03 valait **0,401** : son premier temps peut être faux. L'extension doit en tenir compte.
- **Un essai a échoué** (« URI is invalid. ») parce que Spicetify n'était pas chargé : cf. [`../pieges.md`](../pieges.md).
- **Couverture non vérifiée** : deux morceaux testés. Les sorties très récentes pourraient ne pas avoir d'analyse ; prévoir un repli.

## Conclusion

✅ Tout ce qu'il faut pour caler des transitions est disponible.
