# Audit des transitions (2026-10-26) : vrais mixes, pratique des DJ, critique du code, plan

Recherche en lecture seule sur le projet. Aucun audio téléchargé ; seul fichier récupéré : les **métadonnées** JSON de djmix-dataset (11,6 Mo, sans piste audio), pour compter les genres.

**Légende** : **[V]** vérifié dans la source citée · **[D]** déjà vérifié dans `docs/recherche/` · **[S]** source tierce, forum, blog · **[I]** déduction · **[M]** mesuré (calcul sur données ou lecture du code).

| Fichier | Contenu |
|---|---|
| Ce fichier | Les 5 enseignements et le plan priorisé |
| [`donnees-et-pratique.md`](donnees-et-pratique.md) | Jeux de données de vrais mixes (ce qu'on peut en tirer légalement, chiffres publiés) ; pratique des DJ en club pour nos genres |
| [`critique-et-banc.md`](critique-et-banc.md) | Écarts du programme, style par style et dans le choix ; ce que disent les notes ; banc de mesure local en 3 niveaux |

## Les 5 enseignements qui comptent

1. **Aucune donnée publique de vrais mixes pour nos genres.** Sur les 5 040 mixes de djmix-dataset : **24** « Hip Hop », **2** « Reggae », **0** « Dancehall » ou « Afro » [M]. Les chiffres publiés (transitions sur des multiples de 32 temps, tempo modifié de moins de 5 % pour 86 %) décrivent la house. Pour le rap, le shatta et le bouyon, la seule source fiable sera **notre propre banc**.
2. **Aucune statistique agrégée publiée sur les courbes de volume et d'égaliseur de vrais DJ** : les articles qui les estiment (NIME 2021, DAFx 2022) publient une méthode, pas des courbes moyennes [V]. Nos courbes viennent de règles écrites à la main (Spotify, Vande Veire).
3. **Nos six styles « doux » sont une seule transition** (`_douce`) : même montée de B sur 8 mesures, même échange, même traîne de A ; seul l'habillage de A change, et il n'est fait que d'**une seule mesure réelle de A répétée** jusqu'à 8 fois [M]. Un DJ boucle 4 à 16 temps et change la boucle toutes les 2 à 4 mesures, ou laisse jouer la vraie fin du morceau [V]. Cause la plus probable de « toujours le même style » (essai 14) et de « juste une sorte de fondu » (essai 22).
4. **Le mélange jugé « clean de fou » (essai 6) n'est presque jamais tiré** : tonalité Spotify sûre ET voisine exigée, alors qu'elle est incertaine sur 12 des 19 transitions notées ; sous ~105 BPM, l'avance exigée dépasse la cible de 60 s [M].
5. **B monte à plein volume des médiums pendant ses 8 mesures d'avant-drop sans regarder ni la voix ni la tonalité** : en rap et en shatta, ces mesures sont souvent chantées, d'où deux voix superposées [I]. Faire monter **seulement la batterie de B** (séparation percussions / harmonie, quasi instantanée) jusqu'à 2 mesures du drop règle les deux conflits.

## Plan priorisé

Tri par impact sur la qualité perçue au vu des goûts ([`../../gouts.md`](../../gouts.md)). Effort : **XS** < 1 h, **S** ½ journée, **M** 1 à 2 jours, **L** plus.

| # | Action | Chiffres | Effort |
|---|---|---|---|
| 1 | **Boucle de phrase** : sous la montée de B, rejouer les 4 ou 8 dernières **vraies** mesures de A, puis seulement les 2 dernières en boucle qui se divisent ; changer l'état de A toutes les 2 mesures | Aucune mesure répétée plus de 2 fois | S |
| 2 | **B monte par sa batterie** (séparation percussions / harmonie) ; harmonie et voix de B sur les 2 dernières mesures ou au drop | Plus de voix superposées sur ~6 des 8 mesures | M |
| 3 | **Débloquer le mélange** : refuser seulement si les deux tonalités sont sûres et à distance ≥ 3 ; mélange de 4 mesures sous 120 BPM ; fin sur le drop de B | ~3 paires éligibles sur 19 → 11 sur 19 | S |
| 4 | **Énergie → style** : énergie qui baisse → filtre, frein ; jamais de montée vers un B plus calme | 1 ligne | XS |
| 5 | **Drop swap refait** : jouer la vraie montée de A (4 à 8 mesures), couper A sur le drop de B sous réverbération | Tension portée par la vraie musique | M |
| 6 | **Varier la longueur** (montée de B sur 4, 8 ou 16 mesures) et la sortie de A (1, 2 ou 4 mesures, écho, réverbération) | Six formes perçues | S |
| 7 | **Écoute en aveugle** : B étiré et calé contre B non étiré sans graves, sur 4 paires | Notes 3,25 contre 4,3 (n = 19, biaisé) | S |
| 8 | **Roulements plafonnés à +3 demi-tons** (aujourd'hui +7) | ×1,19 au plus | XS |
| 9 | **Boucler une mesure sans voix** (la moins chantée des 4 dernières) | Plus de mot qui bégaie | M |
| 10 | **Secours de 2 mesures** au lieu d'une | 3 s au lieu de 1,5 s à 160 BPM | XS |
| 11 | **Mode annotation dans l'app** (banc niveau 1) | 50 transitions par genre | M |
| 12 | **Regagner l'avance en doublant un refrain** hors transition, pour superposer la vraie fin de A | Un refrain doublé rend 16 mesures | L |
| 13 | **Banc automatique en mémoire** (niveau 2), puis calage de 6 paramètres | | L |
| 14 | Essayer une fois une **sortie en écho hip-hop** (B lancé un temps avant, sur le 4) | Risquée face au goût « jamais A coupé net » | S |
| 15 | **Commentaire du side chain** : −6 dB réels, −12 dB annoncés | 1 ligne | XS |

Ordre conseillé [I] : 4, 15, 8, 10 (gains rapides) → 1, 3, 2 (cœur du problème) → 7 → 5, 6 → 11 → 9, 12, 13 ; 14 à part.
