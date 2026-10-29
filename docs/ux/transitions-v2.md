# UX · Écran des transitions v2 (app « Mode DJ » et `proto/e2/ecran.html`)

Spec : tâches 13 et 14 de [`../specs/transitions-v2.md`](../specs/transitions-v2.md) ; contrat : ADR 0001 (`/state`,
`/rating` par `id`, `/run`), ADR 0005 (`dj-catalogue.js`). Libellés, couleurs et étapes de frise viennent tous du catalogue.

## Parcours principal : écouter, noter, découvrir

1. Le développeur allume le mode auto (app) ou lance une paire (« Tester » / `/run`, transition « Auto » ou forcée).
2. « Dans tes oreilles » annonce la transition à venir (compte à rebours), puis l'étape en cours, puis « B seul ».
3. Dès qu'une transition est entendue, elle apparaît en tête de « À noter » avec le formulaire ouvert : 5 étoiles,
   10 étiquettes à cocher, un commentaire facultatif, bouton « Envoyer la note ».
4. Après un envoi réussi (`POST /rating {id, note, etiquettes, commentaire}`), la ligne se dévoile : nom et couleur de
   la transition jouée, demandée → jouée, replis avec leur raison, mesures (calage, basses, sonie, ralenti, marge).
5. Les transitions plus anciennes (10 récentes) restent notables en cliquant « Noter » sur leur ligne.

## Écoute à l'aveugle (par défaut, interrupteur « Écoute à l'aveugle » mémorisé)

- Tant qu'un `id` n'est pas noté, rien ne trahit la transition : ni nom, ni couleur (gris neutre), ni étapes de frise,
  ni raison, ni replis, ni mesures. La frise montre A, une zone « ? » et B, sans dire si B entre en superposition.
- Les textes libres (statut du mode auto, incidents, raison) passent par `catalogue.masquer` : identifiants et noms
  remplacés par « ? ».
- Le forçage reste visible : celui qui force sait ce qu'il a demandé.
- Aveugle éteint : tout est affiché tout de suite, la note reste possible.

## États

| État | Ce que montre l'écran |
|---|---|
| Moteur éteint (`/state` ne répond pas) | Une seule carte : « Maquette éteinte : lance `proto/e2/e2.py` » ; le mode auto dit que Spotify joue seul (R3). Boutons désactivés |
| Moteur sans `DJ_WORK` (`can_run` faux) | Boutons de test désactivés, avec la raison |
| Extension absente (`window.DJ` absent, app) | « Extension dj-auto absente : lancer `spicetify/installer.sh` » |
| Aucune transition | « Aucune transition prévue pour l'instant » ; liste à noter : « Rien à noter » |
| Analyse absente (`getAudioData` vide, app) | Cercle remplacé par « analyse indisponible » (plus de « analyse… » sans fin) ; le reste marche |
| Transition prévue pas encore entendue | Ligne grisée « s'entend dans N s », pas de note possible |
| Repli (`replis` non vide) | Après dévoilement : badge « repli », chaîne « C7 → C6 (plan) → C5 (rendu) » et raisons |
| Secours / abandon (`issue`) | Après dévoilement : badge rouge « secours » ou « abandon (Spotify seul) » |
| Note refusée | 409 : « transition trop ancienne » ; 400 : message du moteur ; réseau : « maquette injoignable », la saisie est gardée |
| Avance basse | Avance en rouge sous 60 % de la cible |

## Accessibilité

- Étoiles : groupe de boutons (`aria-pressed`, `aria-label="Note 3 sur 5"`) ; étiquettes : cases à cocher réelles.
- Interrupteurs : `button role="switch" aria-checked`. Selects avec `label`. Focus visible (contour vert 2 px).
- Message d'envoi et compte à rebours dans une zone `aria-live="polite"`. Couleur jamais seule porteuse de sens
  (badge texte à côté de la pastille).

## Retiré

Anciens styles (montée, mélange, écho doux, drop swap…), refrain doublé et `/double`, `ingredients`, `phases`,
`b_from` et `label` de `/state`, note par `mode`/`from`/`to`.
