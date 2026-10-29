# ADR 0006 · Traitement du son : numpy seul, EQ 3 bandes par FFT à phase nulle

Statut : accepté, 2026-10-28.

## Contexte

La spec demande un EQ 3 bandes Linkwitz-Riley d'ordre 4 « dont la somme est plate », automatisable sans clic, des filtres
balayés à 12 dB/oct et un écho calé sur le tempo. Le moteur ne dépend aujourd'hui que de numpy et de la commande
`rubberband`. scipy est présent sur la machine (1.18) mais n'est pas une dépendance déclarée. Le rendu est **hors ligne** :
tout le segment est disponible avant d'être joué (avance de 60 s), on n'a pas besoin de filtres causaux.

## Options

1. **scipy.signal** (`butter`, `sosfilt`) : vrais biquads LR4. Nouvelle dépendance (~40 Mo) ; filtres causaux dont il faut
   gérer le déphasage entre bandes ; automatisation par blocs.
2. **Biquads en Python pur** : trop lents échantillon par échantillon (30 s de stéréo = 2,6 M itérations par filtre).
3. **FFT à phase nulle** (comme `outils.band`) : séparation en 3 bandes avec les **amplitudes** LR4
   (`|H_bas| = 1 / (1 + (f/fc)^4)`), la bande haute étant le complément exact (`1 − H`), la médiane la différence. La
   somme vaut l'original à l'arrondi près. Gains de bande appliqués ensuite dans le temps, lissés ≥ 5 ms.

## Décision

Option 3, numpy seul.

- `primitives.eq3(x, graves, mediums, aigus, fc=(200, 4000))` : une seule séparation par piste et par transition, puis trois
  enveloppes de gain (tableaux par échantillon) ; renvoie la somme et journalise les automations.
- Filtres balayés : `outils.sweep` gagne un paramètre `ordre` (2 = 12 dB/oct, demandé par la spec ; 4 = comportement
  actuel, gardé par défaut pour `secours`).
- Écho : somme vectorisée de copies décalées de ½ temps × 0,5^k, filtrée (passe-haut 300 Hz, passe-bas balayé 8 → 2 kHz),
  tronquée sous −60 dB.
- Frein (C3) : `outils.frein` (ex-`_brake`) avec courbe exponentielle et passe-bas 16 kHz → 500 Hz ; hauteur non conservée.
- Courbes nommées `lin`, `cos`, `carre` (rampe de 10 ms) : fonctions de `primitives`, échantillonnées en tableaux.

## Conséquences

- Pas de dépendance nouvelle ; `README` de e2 inchangé sur ce point.
- La phase nulle est non causale (le filtre « voit » quelques ms d'avance) : sans effet audible pour des transitions
  rendues hors ligne, et cela supprime le déphasage entre bandes que LR4 causal aurait.
- Coût : une FFT de 2×longueur par piste. Pour C7 sur 16 mesures (~35 s), < 0,5 s sur la machine de référence ;
  `rendu_s` du rapport le surveille (critère 9.1-12).
- Le critère 9.1-7 (« courbes conformes ») se vérifie sur le journal d'automations, pas sur le son.
