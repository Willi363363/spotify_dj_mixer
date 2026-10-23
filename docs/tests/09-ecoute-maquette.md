# 09 · Écoute de la maquette E2

Écoutes du 2026-10-23 sur les haut-parleurs du portable (pas de casque). Code : [`../../proto/e2/`](../../proto/e2/README.md). Paires choisies par [`choisir-paires.js`](../../outils/choisir-paires.js) dans la playlist bouyon : 82 morceaux analysés, 24 au tempo stable et aux mesures fiables.

## Essais et verdicts

| # | Transition | Morceaux | Verdict du développeur |
|---|---|---|---|
| 1 | Mix 4 mesures, échange des basses, fondu de volume | « B.M.S » → « Miss Kitoko » (154 BPM) | « horrible, juste un fondu, pas d'adaptation du rythme » |
| 2 | Mix 8 mesures **recalé sur les grosses caisses**, B à plein volume sans basses, échange à la mesure 5 | idem | « juste un fondu, nul » |
| 3 | **Montée** : roulements 1 → 1/2 → 1/4 → 1/8 temps qui montent en hauteur, écho, **un temps de silence**, drop de B | « CHOKOLA » → « Sit on My Face » (160 BPM) | « incroyable, je valide », mais le silence après les roulements « pas si ouf » |
| 4 | **Montée continue** : roulements jusqu'au 1/16 de temps, sans écho ni silence, drop de B | idem | ✅ « validé, on dirait vraiment des transitions comme en boîte » |
| 5 | Retour arrière (1 mesure à l'envers), puis drop de B | « Doglife! Vcvc » → « Supla », puis « Sex time » → « Mon BB est fâché » | non jugé (avis demandé, pas reçu) |
| 6 | **Mélange v3** (recettes) : choix automatique, points choisis par score, **calage fin à ±½ temps**, **tempo qui glisse temps par temps**, échange des basses au centre, passe-bas qui se ferme sur A | « Am to Pm » (Ridge) → « De Rum » (Litle Boy), 160 BPM | ✅ « clean de fou » |

Avant l'essai 6, le même mélange sur « Doglife! Vcvc » → « Supla » a été **refusé** par la maquette (accord des grosses caisses 0,11) et remplacé par une coupe : le repli fonctionne. Le calage fin a ensuite fait passer l'accord à 0,52 sur cette paire, et à 0,43 → 0,35 (après étirement) sur l'essai 6.

## Mesures

| Mesure | Valeur |
|---|---|
| Accord des grosses caisses A / B **sans** recalage (essai 2) | 0,02 : aucun alignement |
| Accord **avec** B avancé de 50 ms | 0,32 |
| Recalage du premier temps de B sur sa grosse caisse (essais 3-4) | 274 à 324 ms, presque un temps (375 ms) |
| Blanc entre la montée continue et le drop (essai 4) | **aucun** passage de 15 ms à plus de 30 dB sous le niveau |
| Durée de la montée | 12,00 s = 8 mesures pile à 160 BPM |

## Ce qu'on en tire

- **Le premier mix était décalé** : les positions de Spotify ne suffisent pas, il faut **toujours recaler sur le son** (attaques de grosse caisse), et chercher le meilleur décalage sur plusieurs mesures : en bouyon, la grosse caisse la plus forte n'est pas toujours sur le temps.
- **Un fondu de volume seul ne sonne pas DJ** ; un mélange calé temps par temps, avec échange des basses et filtre, si (essai 6). Cohérent avec la recherche : les longs mélanges sont faits pour la house et la techno (cf. [`../recherche/dj/transitions.md`](../recherche/dj/transitions.md)).
- **Décision produit** : la montée par roulements **sans blanc** est la transition de référence ; un silence avant le drop est à éviter.
- **Non jugé** : la boucle et le frein des essais précédents, écoutés sans repères.

## Méthode d'écoute retenue

Un essai à la fois, annoncé par deux notifications de la maquette (« Dans 5 s », puis « Maintenant ») ; des morceaux différents de ceux déjà entendus ; le développeur donne son avis avant l'essai suivant.
