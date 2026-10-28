# Décisions d'architecture (ADR)

Une décision structurante par fichier : contexte, options, décision, conséquences. Numéros dans l'ordre, jamais réutilisés ;
une décision remplacée garde son fichier avec le statut « remplacé par NNNN ».

| N° | Décision | Statut |
|---|---|---|
| [0001](0001-contrat-ordre-v2.md) | Contrat extension → moteur v2 : ordre, rapport `/state`, note, `/run` | accepté |
| [0002](0002-detection-voix-v1.md) | Voix : segments au plan, signal en mémoire au rendu, paroles derrière un drapeau (Q3) | accepté |
| [0003](0003-ralenti-et-quota-refrain.md) | Ralenti de regain à ×1,03 réglable (Q1), quota E2 resserré (Q2) | provisoire |
| [0004](0004-ancien-code-garde-supprime.md) | Ce qu'on garde et ce qu'on retire de l'ancien code | accepté |
| [0005](0005-modules-transitions.md) | Paquet `proto/e2/transitions/`, extension en modules `DJCore`, propriété des fichiers | accepté |
| [0006](0006-traitement-sans-dependance.md) | Traitement du son en numpy seul, EQ 3 bandes par FFT à phase nulle | accepté |
