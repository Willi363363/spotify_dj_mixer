# Principes du mixage

## Phrases musicales

| Règle | Détail |
|---|---|
| Longueurs de phrase | 4, 8, 16, 32 mesures ; la plupart des changements tous les 8 ou 16 ([DJ.Studio](https://dj.studio/blog/phrasing-dj-mixing)) |
| Règle des 32 temps | La plupart des morceaux s'organisent en blocs de 32 temps (8 mesures) : aligner ces blocs laisse la production faire le travail ([DJ TechTools](https://djtechtools.com/amp/tag/phrasing/)) |
| Intro et outro | L'outro fait souvent 16 à 32 mesures, pensée pour mixer. En hip-hop et en pop, intros plus courtes (8 à 16 temps), refrains de 32 ou 64 temps |
| Où démarrer B | Au début d'une phrase de A. Exemple : outro de A à la mesure 32, intro de B de 8 mesures → lancer B 8 mesures avant, pour que son couplet tombe sur l'outro ([forum DJ TechTools](https://forum.djtechtools.com/t/tips-on-phrase-matching/49511)) |
| Repères | Les producteurs signalent presque toujours la fin d'une phrase par un petit roulement de batterie |
| Souplesse | Certains DJ superposent 64 temps, d'autres coupent sur 1 temps : la phrase est un guide |

**Pour nous** : l'analyse de Spotify donne `bars` et `sections` ; il faut en tirer une **grille de phrases** (8 ou 16 mesures) et ne déclencher que sur ses frontières. La fiabilité des mesures (0,4 à 0,6 sur la playlist testée) rend ce calcul fragile : à recouper avec les attaques de grosse caisse dans le son (cf. l'alignement de la maquette, [`../../tests/09-ecoute-maquette.md`](../../tests/09-ecoute-maquette.md)).

## Tempo

| Règle | Détail |
|---|---|
| Superposition | Tempos calés ; écart rattrapable en général de ±6 à 8 % sans que ça s'entende trop |
| Double / moitié | 80 et 160 BPM se mixent : on cale l'un sur le double de l'autre. DJ.Studio détecte ces cas et évite d'étirer ([aide DJ.Studio](https://help.dj.studio/en/articles/15359028-double-and-half-tempo)) |
| Plafond d'un logiciel | DJ.Studio limite l'ajustement dans une transition à environ 25 à 30 % ; au-delà, double ou moitié |
| Gros écart | Pas de superposition : coupe, écho, ou montée de tempo sur une boucle (cf. [`transitions.md`](transitions.md)) |

## Tonalité (roue de Camelot)

| Mouvement | Effet | Sources |
|---|---|---|
| Même code (8A → 8A) | le plus sûr | [Mixed In Key](https://mixedinkey.com/workflows/how-to-use-the-camelot-wheel/) |
| ±1 (8A → 7A ou 9A) | légère montée ou descente d'énergie | idem, [Signalkey](https://www.signalkey.io/learn/what-is-camelot-wheel) |
| Même nombre, autre lettre (8A → 8B) | passage mineur ↔ majeur | idem |
| +2 (8A → 10A) | « energy boost » selon Mixed In Key | [Mixed In Key](https://mixedinkey.com/workflows/change-energy-with-camelot-wheel/) |
| +7 (= un demi-ton plus haut) | « energy boost » selon d'autres outils | [DEV Community](https://dev.to/birrings/camelot-wheel-for-developers-harmonic-mixing-without-the-music-theory-phd-21i8) |
| −5 (« Jaws Mix ») | changement dramatique, à garder pour de rares moments | Mixed In Key |

Les sources se contredisent sur les étiquettes, pas sur les mouvements. **Pour nous** : la fiabilité de la tonalité Spotify était sous 0,4 pour 5 morceaux sur 9 ; ne tenir compte de la tonalité qu'au-dessus d'un seuil, et préférer alors une coupe ou un écho (insensibles à la tonalité) à un long mélange.

## Énergie et voix

- **Jamais deux voix ni deux basses en même temps** : c'est l'erreur la plus citée.
- **Suivre l'énergie de la salle** : en hip-hop grand public, le choix des morceaux compte plus que les effets de tension (avis d'un DJ, Reddit).
- **L'énergie de Spotify** (`audio-features`, 0 à 1) permet de décider : énergie qui monte → montée par roulements ; qui descend → sortie en écho ou fondu filtré.
