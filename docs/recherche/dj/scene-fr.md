# Soirées rap français, shatta, bouyon en France

Recherche du 2026-10-23. **Limite** : aucun tutoriel technique dédié à ces scènes n'a été trouvé (seulement des vidéos TikTok de DJ francophones qui montrent des « transitions shatta » sans les expliquer, et des mix YouTube). Ce fichier croise donc trois sources : les genres eux-mêmes, la culture sound system dont vient le shatta, et la pratique « open format » des clubs hip-hop. Chaque ligne indique sa source ; ce qui est déduit est marqué *déduit*.

## Les genres

| Genre | Origine | Tempo | Son | Sources |
|---|---|---|---|---|
| **Shatta** | Dérivé de la dancehall jamaïcaine, né à Volga-Plage (Fort-de-France, Martinique) | non donné | Basses 808 très puissantes, peu de mélodie, percussions de carnaval, parfois ti-bwa | [Billboard France](https://fr.billboard.com/shatta-bouyon-les-antilles-influencent-les-plus-gros-hits-du-moment/) |
| **Bouyon** | Dominique, années 1980 | **~152 BPM** (Dominique), **~160** (bouyon dur de Guadeloupe) | Batterie acoustique dominante, rythmes de carnaval très rapides | idem, [TIITII NBA](https://tiitii-nba.com/bouyon/c-est-quoi-le-bouyon/) |
| **Bouyon « warm up »** | Même genre joué plus lent | **117 à 134 BPM** | Laisse la place aux pas de danse et aux refrains chantés | [TIITII NBA](https://tiitii-nba.com/en/bouyon/ch-08-warm-up/) |
| **Rap français de club** | — | variable ; souvent en moitié de tempo du bouyon (*déduit* : 76-80 BPM ↔ 152-160) | Hymnes à reprendre en chœur, refrains | [Red Bull](https://www.redbull.com/fr-fr/morceaux-rap-francais-club) |

Les ponts entre genres sont réels : « Alpha » (Damso et Kalash) est composé par un compositeur de rap, Vald, Shay et Niska touchent au bouyon (Billboard France). Sur la playlist testée, les tempos se groupent autour de **154 et 160 BPM**, cohérent avec le bouyon (cf. [`../../tests/09-ecoute-maquette.md`](../../tests/09-ecoute-maquette.md)).

## Ce que font les DJ de ces soirées

### Morceaux courts, refrain d'abord (open format)

- En club hip-hop « open format », le DJ joue **rarement plus d'une minute par morceau**, et la convention courante est de **30 à 90 secondes** : l'essentiel de l'attrait d'un morceau tient dans un passage court, le refrain ou le drop ; un morceau joué en entier devant un public venu pour les refrains crée un creux ([Mixgraph](https://www.mixgraph.io/glossary/quick-mix), [forum DJ TechTools](https://forum.djtechtools.com/t/rapid-fire-song-mixing-vs-start-to-finish-mixing/69958), [Digital DJ Tips](https://www.digitaldjtips.com/should-djs-play-the-whole-track/)).
- Ce style repose sur des **points d'entrée préparés** à l'avance (Mixgraph).
- Transitions typiques : **coupe sur le premier temps**, entrée directe sur le refrain, sortie en écho (cf. [`transitions.md`](transitions.md)).

### Le « rewind » de la culture sound system (shatta, dancehall)

- **Rewind, pull up, wheel up** : le DJ arrête le morceau et le relance au début, ou ramène le disque en arrière pour rejouer un passage, **quand le public réclame le morceau** au moment le plus chaud. Version propre au bouton marche / arrêt, version brute en ramenant le disque à la main ([Dub-Stuy](https://www.dub-stuy.com/wheel-it-up-history-of-the-rewind/), [Sonicfield](https://sonicfield.org/wiki/selector)).
- C'est un geste de lecture de la salle : mal placé, il paraît prétentieux (Dub-Stuy).
- Toujours en usage dans la culture sound system et ses descendantes ; quasi absent de la house et de la techno (Dub-Stuy).
- **Juggling** : enchaîner plusieurs versions du même riddim (la même instru) sous un MC, pour tenir l'énergie longtemps ([Sonicfield](https://sonicfield.org/wiki/juggling)).
- **Sirènes, cornes de brume** : très présentes dans les mix shatta et dancehall, mais **aucune source trouvée** ne les décrit (observation courante, non vérifiée).

### Gestion de la nuit (bouyon)

- Le **warm up** ouvre la soirée, puis **revient entre deux pics** pour laisser respirer la piste avant la poussée suivante ; les DJ alternent les deux tempos dans une même nuit, et ralentissent parfois des morceaux existants pour en faire du warm up (TIITII NBA).

## Ce que ça change pour le moteur (*déduit*)

| Pratique | Traduction chez nous | État |
|---|---|---|
| Morceaux de 30 à 90 s, refrain ou drop d'abord | **Raccourcir chaque morceau** : entrer sur le refrain ou le drop, sortir après 1 ou 2 phrases. Décision produit à prendre : c'est très différent d'une écoute normale | ⏳ à décider |
| Coupe sur le premier temps | E2 sans trou de Spotify | ⬜ |
| Montée par roulements jusqu'au drop | Déjà faite | ✅ validée |
| Rewind | Retour arrière rapide (son passé en mémoire), puis relance du passage fort, rarement et sur les morceaux à plus forte énergie | ⬜ E2 |
| Sirène, corne de brume | Sons ajoutés par-dessus, calés sur le temps fort (ce sont des sons à nous, pas ceux de Spotify) | ⬜ E1 possible |
| Rap ~80 ↔ bouyon ~160 | Calage **double / moitié** de tempo, sans étirement | ⬜ |
| Warm up puis pics | Ordonner la file : tempos plus lents en début et entre les pics | ⬜ |

## Pour aller plus loin

Les meilleures sources manquent encore : des **interviews de DJ** de ces soirées (Paris, Antilles), ou l'analyse de quelques mix publiés (durée par morceau, type de transition) ; cette seconde piste est faisable à partir de vidéos de mix, par écoute.
