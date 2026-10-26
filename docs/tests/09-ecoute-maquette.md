# 09 · Écoute de la maquette E2

Écoutes du 2026-10-23 (haut-parleurs du portable) et du 2026-10-26 (écouteurs Bluetooth). Code : [`../../proto/e2/`](../../proto/e2/README.md). Paires choisies par [`choisir-paires.js`](../../outils/choisir-paires.js) dans la playlist bouyon. Ce que le développeur aime et n'aime pas, résumé : [`../gouts.md`](../gouts.md).

## Essais et verdicts

| # | Date | Transition | Morceaux | Verdict du développeur |
|---|---|---|---|---|
| 1 | 23/10 | Mix 4 mesures, échange des basses, fondu de volume | « B.M.S » → « Miss Kitoko » (154 BPM) | ❌ « horrible, juste un fondu, pas d'adaptation du rythme » |
| 2 | 23/10 | Mix 8 mesures **recalé sur les grosses caisses**, B à plein volume sans basses, échange à la mesure 5 | idem | ❌ « juste un fondu, nul » |
| 3 | 23/10 | **Montée** : roulements 1 → 1/8 de temps qui montent en hauteur, écho, **un temps de silence**, drop de B | « CHOKOLA » → « Sit on My Face » (160 BPM) | « incroyable, je valide », mais le silence après les roulements « pas si ouf » |
| 4 | 23/10 | **Montée continue** : roulements jusqu'au 1/16 de temps, sans écho ni silence | idem | ✅ « on dirait vraiment des transitions comme en boîte » |
| 5 | 23/10 | Retour arrière (1 mesure à l'envers), puis drop de B | « Doglife! Vcvc » → « Supla », « Sex time » → « Mon BB est fâché » | non jugé |
| 6 | 23/10 | **Mélange v3** : points choisis par score, **calage fin à ±½ temps**, **tempo qui glisse temps par temps**, échange des basses au centre, passe-bas qui se ferme sur A | « Am to Pm » → « De Rum » (160 BPM) | ✅ « clean de fou » |
| 7 | 26/10 | **Coupe** nette sur le premier temps (choix automatique), jouée deux fois | « KONGOLESE SOUS BBL » → « Jumping Jack » (156 → 158 BPM) | ❌ « absolument horrible, c'était bien mieux l'autre jour » |
| 8 | 26/10 | Même paire en montée | idem | « pas remarqué » : joué alors que l'écran n'aidait pas à suivre ; nouvel écran (frise) |
| 9 | 26/10 | Montée lancée depuis le bouton de l'écran | idem | ⚠️ **essai invalide** : Spotify contournait la maquette (écouteurs Bluetooth connectés), cf. [`../pieges.md`](../pieges.md) |
| 10 | 26/10 | Montée, routage corrigé | idem | ✅ basses qui disparaissent et roulements qui accélèrent aimés, disparition de A « clean de fou » ; ❌ B « apparaît d'un coup sans prévenir, sec, pas smooth » |
| 12 | 26/10 | Auto : mélange tenté puis **refusé** (accord −0,25), repli sur une montée **sans montée douce** et prête 23 s trop tard (avance de 30 s insuffisante) | « Tic » → « La Choré Des Shattas » (104 BPM) | fin de A « clean » ; ❌ arrivée de B « sèche ». Corrigé : avance de 45 s, B toujours lancé 2 mesures avant, transition trop tardive abandonnée |
| 13 | 26/10 | Auto : mélange **refusé dès 2 mesures** (accord 0,06), **repli en montée douce** prêt avec 13 s de marge ; avance de 50 s | « Tic » → « La Choré Des Shattas » (104 BPM) | ✅ « ça me va, je valide, c'était doux » |
| 11 | 26/10 | **Montée douce** : B lancé 2 mesures avant son drop, qui montent sous les roulements (filtre qui s'ouvre, volume 0 → 0,85), puis drop sans raccord | « Money Pull Up » → « SO COMAN » (100 BPM) | ✅ « ça va, je valide » |

Avant l'essai 6, le même mélange sur « Doglife! Vcvc » → « Supla » a été **refusé** par la maquette (accord des grosses caisses 0,11) : le repli fonctionne.

## Mesures

| Mesure | Valeur |
|---|---|
| Accord des grosses caisses A / B sans recalage (essai 2) | 0,02 : aucun alignement |
| Accord avec recalage (essais 2, 6) | 0,32 ; 0,43 → 0,35 après étirement |
| Blanc entre la montée continue et le drop (essai 4) | aucun passage de 15 ms à plus de 30 dB sous le niveau |
| Essai 9 : son entrant dans la maquette | **silence total** (Spotify parti vers le Bluetooth) |
| Essais 10 et 11 : son entrant / sortie | −19 et −18 dB ; sortie = entrée retardée de 30,02 s (ressemblance 0,968 et 0,897) |
| Montée douce (essai 11) | B monte sur les 4,79 dernières secondes ; drop recalé de 80 ms |
| Essai 12 : préparation du mélange avant refus | 32 s (attente de 10 mesures de B) pour 30 s d'avance : repli joué trop tard |
| Essai 13 : refus décidé sur 2 mesures | 18 s après le changement ; repli prêt 13 s avant de jouer ; sortie = entrée retardée de 50,04 s (0,983) |

## Ce qu'on en tire

- **Toujours recaler sur le son** (attaques de grosse caisse), sur plusieurs mesures : en bouyon, la grosse caisse la plus forte n'est pas toujours sur le temps.
- **Un essai n'est valable que si le son passe par la maquette** : contrôler l'enregistrement (entrée non silencieuse, sortie = entrée retardée) avant de croire un verdict.
- Les décisions qui en découlent sont dans [`../roadmap.md`](../roadmap.md#décisions).

## Méthode d'écoute retenue

Un essai à la fois ; l'écran ([`../../proto/e2/README.md`](../../proto/e2/README.md)) montre la frise A → B et un compte à rebours ; l'heure exacte de chaque étape est donnée avant l'écoute ; une notification arrive 10 s avant ; des morceaux pas encore entendus ; le développeur donne son avis avant l'essai suivant, et chaque avis est reporté ici et dans [`../gouts.md`](../gouts.md).
