# 06 · Série A : décisions et lecteur, dans Spotify seul

Tests du 2026-10-23, compte gratuit. Scripts `outils/a*.js`, exécutés avec [`methode.md`](methode.md).

## A1 · Analyse d'une vraie file d'attente ([`a1-decisions.js`](../../outils/a1-decisions.js))

10 morceaux de la playlist « SHATTA BOUYON MIX 2026 ».

| Mesure | Résultat |
|---|---|
| Couverture de l'analyse | **9/10** : « Bad (Latin Remix) » a répondu sans `sections` |
| Énergie (`audio-features`, interne) | ✅ disponible pour les 9 (0,27 à 0,89) |
| Fiabilité de la tonalité (`key_confidence`) | très variable : 0 à 0,82, sous 0,4 pour 5 morceaux sur 9 |
| Fiabilité moyenne des mesures | 0,44 à 0,60 |
| Écart de tempo entre morceaux consécutifs | 8,5 à 32 % : **aucune paire sous 6 %** |

**À retenir** : la file d'un utilisateur n'est pas une playlist de DJ. Le mode DJ doit savoir **refuser une superposition** (coupe calée sur le temps à la place) et ne pas se fier à la tonalité quand sa fiabilité est basse. Mon repérage de l'outro (baisse de 3 dB) donne des résultats douteux (outro à 74 s sur 133 pour « Bumpa ») : l'heuristique est à reprendre, Smart DJ en a une plus fine.

## A2 · Transition vers le drop du suivant ([`a2-transition.js`](../../outils/a2-transition.js))

« Around the World » → « Bubble Like Soup » sur son drop (53,86 s), saut lancé 115 ms en avance.

| Mesure | Résultat |
|---|---|
| Lancer B à une position précise | ✅ `PlayerAPI.play({uri}, {}, {seekTo})` : B joue à 54,32 s 300 ms après |
| Changement annoncé par Spotify | 88 ms après l'appel |
| Trou dans le son | **12 ms** (cet essai) ; **40 à 400 ms** lors des essais de la série C |

Le trou au changement de morceau est **bien plus variable** que pour un saut dans le même morceau. En E1, il s'entendra souvent. En E2, il disparaît (cf. [`08-serie-c-maquette-e2.md`](08-serie-c-maquette-e2.md)).

## A3 · Fondu de volume ([`a3-fondu-volume.js`](../../outils/a3-fondu-volume.js))

| Mesure | Résultat |
|---|---|
| Fondu par `PlaybackAPI.setVolume` | ✅ régulier à l'enregistrement |
| Courbe | **non linéaire** : volume 0,3 → −30 dB (au cube : 0,3³ ≈ −31 dB, supposé) |
| Cadence | chaque réglage prend **~80 ms** : 12 réglages par seconde au plus |
| Volume rendu à la fin | ✅ identique (1) |

Pour viser −10 dB, régler 0,3^(1/3) ≈ 0,67, pas 0,3.

## A4 · Interface ([`a4-interface-file-pub.js`](../../outils/a4-interface-file-pub.js))

| Élément | Résultat |
|---|---|
| Bouton dans la barre de lecture (`Spicetify.Playbar.Button`) | ✅ affiché, clic reçu via `button.element.click()` |
| Raccourci clavier `Ctrl+Alt+D` (`Spicetify.Keyboard.registerShortcut`) | ✅ reçu |
| Affichage tempo et tonalité | ✅ dans le libellé du bouton (« DJ 90 BPM · Fa ») ; libellé visible au survol seulement |
| Retrait | ✅ `deregister()` |

⚠️ Incident : une recherche de bouton par texte contenant « DJ » a cliqué une carte « (DJ Mix) » de l'accueil et changé la lecture. Toujours viser un élément par sa référence, jamais par un texte partiel.

## A5 · File d'attente

| Action | Résultat |
|---|---|
| `Spicetify.addToQueue` | ✅ ajouté en position 0, `provider: "queue"` |
| `Spicetify.removeFromQueue` | ✅ retiré, file revenue à 49 |
| Morceaux de la playlist | `provider: "autoplay"` ou contexte : non réordonnables (cf. Smart DJ) |

## A6 · Pubs

| Élément | Constat |
|---|---|
| `Platform.AdManagers.inStreamApi` | `subscribeToInStreamAds`, `getInStreamAd`, `skipToNext` : abonnement aux pubs audio possible |
| `Platform.AdManagers.audio` | `getEnabled`, `enable`, `disable` |
| Morceau courant | champs `type`, `mediaType`, `provider` |

**Non observé en direct** : impossible de déclencher une pub à la demande. La détection reste à valider au premier passage de pub.

## A7 · Entrée par ressemblance ([`a7-entree-ressemblance.js`](../../outils/a7-entree-ressemblance.js))

Empreinte d'une mesure = moyenne des 12 timbres et 12 notes de ses segments ; ressemblance = cosinus.

| Mesure | Résultat |
|---|---|
| Mesures candidates dans B | 46 |
| Meilleures | 0,89 (30,0 s), 0,89 (67,7 s), 0,88 (114,7 s) |
| Moins bonne | 0,51 |
| Entrée sur le drop | 0,82 |

✅ Le calcul discrimine bien (0,51 à 0,89). **Non écouté** : reste à vérifier à l'oreille qu'une entrée à 0,89 sonne mieux qu'une entrée sur le drop.
