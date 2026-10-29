# ADR 0003 · Ralenti de regain (Q1) et quota d'entrée sur le refrain (Q2)

Statut : accepté à titre provisoire, 2026-10-28. Valeurs de départ, à confirmer par le développeur pendant le protocole
d'écoute (§9.2 de [`../specs/transitions-v2.md`](../specs/transitions-v2.md)).

## Contexte

- **Q1** : `SLOW = 1.06` dans `e2.py` était dimensionné pour un mélange de 8 mesures à chaque morceau. Le catalogue v2 est
  surtout sans recouvrement.
- **Q2** : entrer sur le refrain de B (E2) saute son début. La spec propose 1 transition sur 3 et ≤ 25 % de B sauté.

## Calcul (Q1)

Avec les poids du profil court (§7) : consommation moyenne par transition = (2×2 + 4×3 + 8×1 + 6×1,5 − 2×1,5) / 15
≈ **2 mesures**, soit ~4 s à 120 BPM. À ×1,03, le ralenti regagne 0,03/1,03 ≈ 2,9 % du temps joué hors transition, soit
**~5 s par morceau de 3 min**. C'est suffisant, avec C4 qui regagne 2 mesures et l'éligibilité qui exclut les recouvrements
quand l'avance manque. Un écart de 3 % de tempo, hauteur conservée, est sous le seuil où un auditeur non DJ le remarque.

## Options

- Q1 : garder 1,06 ; passer à 1,03 ; passer à 1,02 ; le rendre réglable.
- Q2 : accepter 1/3 et 25 % ; resserrer ; interdire E2.

## Décision

- **Q1** : `SLOW = 1.03` par défaut, réglable par la variable d'environnement `DJ_SLOW` (bornée à 1,00 à 1,06, 1,00 =
  ralenti coupé). La valeur en cours est écrite dans le rapport (`ralenti`) et donc dans chaque note : le protocole peut
  comparer 1,02, 1,03 et 1,06 sans changer de code. Le reste du mécanisme (`slower`, tranches de 8 s, fondus de 15 ms) est
  gardé.
- **Q2** : quota gardé, **resserré** : E2 au plus 1 transition sur 3, jamais deux de suite, et B sauté ≤ 25 % de sa durée
  **et** ≤ 45 s (symétrique du garde-fou de 30 s sur A). Constantes `QUOTA_E2 = { max: 1, sur: 3, part: 0.25, max_s: 45 }`
  dans `dj-choix.js`. L'étiquette `mauvais_endroit` sur les transitions en E2 décide de la suite (> 20 % des notes E2 :
  quota à 1 sur 4).

## Conséquences

- La simulation à blanc doit suivre l'avance pour vérifier que 1,03 suffit sur 30 transitions (critère 9.1-10) : le
  simulateur modélise le regain comme `durée_jouée × (1 − 1/SLOW)`.
- Q1 et Q2 restent des questions au développeur : les réponses définitives vont dans `docs/tests/12-ecoute-transitions-v2.md`.
