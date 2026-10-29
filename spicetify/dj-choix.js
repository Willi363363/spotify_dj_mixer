// Règle de choix automatique (§7), échelle de repli au plan (§8) et ordre v2 (ADR 0001) des transitions.
// Fonctions pures, aucun appel à Spicetify ; hasard à graine fixe (rng) pour les simulations.
// Chargé comme extension Spicetify (globalThis.DJCore.choix) et par Node (require) pour les tests.
(function (racine) {
  const enNode = typeof module === 'object' && module.exports;
  const PL = () => (enNode ? require('./dj-placement.js') : racine.DJCore.placement);
  const VX = () => (enNode ? require('./dj-voix.js') : racine.DJCore.voix);

  // Avance requise pour une superposition (même règle que transitions/catalogue.py) : le rendu attend que B soit en
  // mémoire (T + 2 mesures, puis 3 s) après les T mesures de A, plus la marge de calcul :
  // (2 T + 2) × bar_s + 8 s (rendu des superpositions étirées ≈ 4 s, plus ≥ 2 s de marge, critère 9.1-12),
  // bar_s = mesure de A au bord. Les transitions sans recouvrement (T = 0) n'en demandent pas.
  const MARGE_AVANCE_S = 8;
  const avanceRequise = (T, bar_s) => (T > 0 ? (2 * T + 2) * bar_s + MARGE_AVANCE_S : 0);
  const QUOTA_E2 = { max: 1, sur: 3, part: 0.25, max_s: 45 };   // ADR 0003
  const EFFETS = { max: 1, sur: 4 };                            // au plus 1 effet (C3, C4) sur 4
  const TOP = 3;                                                 // tirage parmi les 3 meilleurs poids
  const G_MAX = { C5: 0.06, C6: 0.06, C7: 0.05, C8: 0.06 };
  const VOIX_ENSEMBLE_MAX = 2;     // O4 : voix des deux côtés ensemble ≤ 2 mesures
  const R2_MARGE_S = 1.0;
  const IDS = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'R1', 'R2'];
  const CHOISISSABLES = IDS.slice(0, 8);

  // ── Hasard à graine (mulberry32) ──────────────────────────────────────────────────────────────────
  function rng(graine) {
    let s = (Number(graine) >>> 0) || 1;
    return () => {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const fr = (x, d = 1) => (Math.round(x * 10 ** d) / 10 ** d).toString().replace('.', ',');
  const signe = (x) => (x > 0 ? '+' : x < 0 ? '−' : '±') + fr(Math.abs(x));

  // ── Points d'une transition ───────────────────────────────────────────────────────────────────────
  // Rend { T, sortie, entree, typeEntree, bords, deltaE } ou { raison } (pas de point possible).
  // cible : 'E0' (B part de son début), 'E1' (cible = fin de l'intro), 'E2' (cible = refrain),
  //         'section' (cible = premier début de section de B à au moins T mesures de son début : E1 si possible,
  //         sinon une section plus loin ; aucune → pas de point, §3 : entreeB + T tombe sur un début de section).
  function points(paire, T, cible, sortieForcee = null) {
    const s = sortieForcee ?? paire.sortie(T);
    if (!s) return { raison: `aucune sortie de A pour ${T} mesures` };
    const e = paire.entrees(T);
    const en = cible === 'section' ? (e.E1 ?? entreeSection(paire, T)) : e[cible];
    if (!en) return { raison: `pas d'entrée ${cible === 'section' ? 'sur section' : cible} pour B` };
    const trop = sauteTrop(en);
    if (trop) return { raison: trop };
    const bords = paire.bords(s, en, T);
    return { T, sortie: s, entree: en, typeEntree: PL().typeEntree(paire.b.analyse, en.t), bords, deltaE: bords.deltaE };
  }
  function entreeSection(paire, T) {
    const b = paire.b.analyse, e0 = paire.entrees(0).E0;
    if (!e0 || !b?.bars?.length) return null;
    const i0 = e0.mesure, deb = PL().debutEffectif(b);
    for (const sec of b.sections ?? []) {
      const c = PL().mesureProche(b, sec.start);
      if (c <= i0 || c - T < i0) continue;
      const ie = c - T, saute = Math.max(0, b.bars[ie].start - deb);
      return { t: b.bars[ie].start, mesure: ie, cible_s: b.bars[c].start, cible_mesure: c, saute_s: +saute.toFixed(2),
        part: +(saute / (paire.b.duree_s || 1)).toFixed(4) };
    }
    return null;
  }
  // Mesures où A et B sont tous deux vocaux pendant le recouvrement (A : ses T dernières, B : ses T premières)
  function voixEnsemble(pts) {
    const T = pts.T, sv = VX().SEUIL_VOCAL;
    const a = pts.bords.voixA.slice(-T), b = pts.bords.voixB.slice(0, T);
    let n = 0;
    for (let i = 0; i < Math.min(a.length, b.length); i++) if (a[i] >= sv && b[i] >= sv) n++;
    return n;
  }
  const avanceOk = (paire, pts) => {
    const need = avanceRequise(pts.T, pts.bords.barA);
    return paire.avance_s >= need ? true : `avance ${fr(paire.avance_s, 0)} s < ${fr(need, 0)} s requises (${pts.T} mesures)`;
  };
  const tempoOk = (paire, max) => (paire.rapport32 ? 'rapport de tempo 3:2'
    : paire.g > max ? `tempos à ${fr(paire.g * 100)} % > ${fr(max * 100, 0)} %` : true);
  const cleOk = (paire, max) => (paire.k === null || paire.k <= max ? true : `Camelot ${paire.k} > ${max}`);
  const grillesPas = (pts, ...interdites) => {
    const { grilleA, grilleB } = pts.bords;
    if (interdites.includes(grilleA)) return `grille de A ${grilleA}`;
    if (interdites.includes(grilleB)) return `grille de B ${grilleB}`;
    return true;
  };
  // Plafond du début de B sauté (ADR 0003), pour toute entrée, quelle que soit son étiquette
  const sauteTrop = (en) => (en.part > QUOTA_E2.part || en.saute_s > QUOTA_E2.max_s
    ? `B sauté ${fr(en.saute_s, 0)} s (${fr(en.part * 100, 0)} %)` : null);
  // Sauter le début de B jusqu'au refrain (E2) n'est permis qu'à C1, C3 et C4 (§5.6)
  const SAUT_PERMIS = ['C1', 'C3', 'C4', 'R2'];
  const pasE2 = (pts) => (pts.typeEntree === 'E2' ? 'entrerait sur le refrain de B (réservé à C1, C3, C4)' : true);
  const e2Ok = (pts, ctx) => {
    if (pts.typeEntree !== 'E2') return true;
    if (!ctx.e2Permis) return 'quota d\'entrée sur le refrain atteint';
    if (pts.entree.part > QUOTA_E2.part || pts.entree.saute_s > QUOTA_E2.max_s)
      return `B sauté ${fr(pts.entree.saute_s, 0)} s (${fr(pts.entree.part * 100, 0)} %)`;
    return true;
  };
  const tous = (...c) => c.find((x) => x !== true) ?? true;
  const sansVoixFin = (pts) => (pts.sortie.vocale ? 'voix de A sur la dernière mesure' : true);

  // ── Règles par transition (§4, §7, §8) ────────────────────────────────────────────────────────────
  // points(paire, ctx) → pts | { raison } ; eligible(paire, pts, ctx) → true | raison du refus
  const REGLES = {
    C1: {
      famille: 'sec', bars: [0], replis: ['R2'], poids: { court: 3, long: 0.5 }, quota: null,
      points(paire, ctx) {
        const p = points(paire, 0, 'E2');
        if (!p.raison && e2Ok(p, ctx) === true && p.deltaE >= 2) return p;
        return points(paire, 0, 'E0');
      },
      eligible: (paire, pts, ctx) => tous(grillesPas(pts, 'floue'), sansVoixFin(pts), e2Ok(pts, ctx)),
    },
    C2: {
      famille: 'sec', bars: [0], replis: ['C1', 'R2'], poids: { court: 2, long: 1 }, quota: { max: 1, sur: 3 },
      params: () => ({ queue_mesures: 2 }),
      points: (paire) => points(paire, 0, 'E0'),
      eligible: (paire, pts) => (pts.bords.grilleA === 'floue' ? 'grille de A floue (écho calé)' : true),
    },
    C3: {
      famille: 'effet', bars: [0], replis: ['C1', 'R2'], poids: { court: 1, long: 0.3 }, quota: { max: 1, sur: 6 },
      params: (paire) => ({ frein_temps: paire.a.tempo < 90 ? 2 : 1 }),
      points(paire, ctx) {
        const p = points(paire, 0, 'E2');
        if (!p.raison && e2Ok(p, ctx) === true && p.deltaE >= 2) return p;
        return points(paire, 0, 'E1');
      },
      eligible: (paire, pts, ctx) => tous(paire.profil === 'court' ? true : 'profil long',
        grillesPas(pts, 'floue'), sansVoixFin(pts), e2Ok(pts, ctx)),
    },
    C4: {
      famille: 'effet', bars: [0], replis: ['C1', 'R2'], poids: { court: 1.5, long: 1 }, quota: { max: 1, sur: 5 },
      points: (paire) => points(paire, 0, 'E2'),
      eligible(paire, pts, ctx) {
        const boucle = pts.bords.voixA.at(-1) ?? 1;
        return tous(pts.deltaE >= 2 ? true : `ΔE ${signe(pts.deltaE)} dB < +2`,
          boucle < VX().SEUIL_SANS_VOIX ? true : 'voix sur la mesure bouclée',
          grillesPas(pts, 'floue'), e2Ok(pts, ctx));
      },
    },
    C5: {
      famille: 'superpose', bars: [2], replis: ['R1', 'R2'], poids: { court: 2, long: 2 }, quota: null,
      points: (paire) => points(paire, 2, 'section'),
      eligible: (paire, pts) => tous(tempoOk(paire, G_MAX.C5), grillesPas(pts, 'floue', 'moyenne'), cleOk(paire, 2),
        avanceOk(paire, pts), pasE2(pts)),
    },
    C6: {
      famille: 'superpose', bars: [4], replis: ['C5', 'R1', 'R2'], poids: { court: 3, long: 1 }, quota: null,
      points: (paire) => points(paire, 4, 'E0'),
      eligible(paire, pts) {
        const intro = pts.bords.voixB.slice(0, 4);
        return tous(paire.profil === 'court' ? true : 'profil long', tempoOk(paire, G_MAX.C6), cleOk(paire, 2),
          grillesPas(pts, 'floue'),
          intro.length === 4 && intro.every((v) => v < VX().SEUIL_SANS_VOIX) ? true : 'voix dans les 4 premières mesures de B',
          avanceOk(paire, pts), pasE2(pts));
      },
    },
    C7: {
      famille: 'superpose', bars: [8, 16], replis: ['C5', 'R1', 'R2'], poids: { court: 1, long: 4 }, quota: null,
      points(paire, ctx) {
        const p16 = points(paire, 16, 'section');
        if (!p16.raison && paire.k !== null && p16.bords.sansVoixA >= 16 && p16.bords.sansVoixB >= 16
          && this.eligible(paire, p16, ctx) === true) return p16;
        return points(paire, 8, 'section');
      },
      eligible(paire, pts, ctx) {
        const { profilA, profilB } = pts.bords;
        const instru = profilA === 'instrumental' && profilB === 'instrumental';
        const cle = paire.k !== null ? (paire.k <= 1 ? true : `Camelot ${paire.k} > 1`)
          : pts.T === 8 && instru ? true : 'tonalité inconnue';
        const ens = voixEnsemble(pts);
        return tous(tempoOk(paire, G_MAX.C7), cle, instru ? true : 'bords pas tous deux instrumentaux',
          grillesPas(pts, 'floue', 'moyenne'), ens <= VOIX_ENSEMBLE_MAX ? true : `voix ensemble ${ens} mesures`,
          avanceOk(paire, pts), pasE2(pts));
      },
    },
    C8: {
      famille: 'superpose', bars: [4, 8], replis: ['C5', 'R1', 'R2'], poids: { court: 1.5, long: 2 }, quota: null,
      points(paire, ctx) {
        const p8 = points(paire, 8, 'E2');
        if (!p8.raison && Math.max(...p8.bords.voixA.slice(-8)) < VX().SEUIL_VOCAL && voixEnsemble(p8) <= VOIX_ENSEMBLE_MAX
          && this.eligible(paire, p8, ctx) === true) return p8;
        return points(paire, 4, 'E2');
      },
      eligible: (paire, pts) => tous(pts.deltaE >= 1.5 ? true : `ΔE ${signe(pts.deltaE)} dB < +1,5`,
        pts.typeEntree === 'E2' ? 'sauterait le début de B' : true,
        tempoOk(paire, G_MAX.C8), cleOk(paire, 2), grillesPas(pts, 'floue'),
        voixEnsemble(pts) <= VOIX_ENSEMBLE_MAX ? true : `voix ensemble ${voixEnsemble(pts)} mesures`, avanceOk(paire, pts)),
    },
    R1: {
      famille: 'repli', bars: [1], replis: ['R2'], poids: { court: 0, long: 0 }, quota: null,
      points: (paire) => points(paire, 1, 'section'),
      eligible: (paire, pts) => tous(avanceOk(paire, pts), pasE2(pts)),
    },
    R2: {
      famille: 'repli', bars: [0], replis: [], poids: { court: 0, long: 0 }, quota: null,
      // A joue jusqu'à sa fin réelle, B part de son début
      points(paire) {
        const a = paire.a.analyse;
        // fin réelle, mais au moins 1 s avant la fin du morceau : sinon Spotify passe seul au suivant avant le saut
        const fin = Math.min(PL().finEffective(a) || paire.a.duree_s, paire.a.duree_s - R2_MARGE_S);
        const ia = Math.max(0, (a?.bars?.length ?? 0) - 1);
        const s = { t: +fin.toFixed(3), mesure: a?.bars?.length ? PL().indexMesure(a, fin - 0.1) : null,
          jamais_entendu_s: 0, voixFin: 0, vocale: false, repli: false };
        if (s.mesure !== null) s.mesure = Math.min(s.mesure, ia);
        const e = paire.entrees(0).E0 ?? { t: 0, mesure: 0, cible_s: 0, cible_mesure: 0, saute_s: 0, part: 0 };
        const bords = paire.bords(s, e, 0);
        return { T: 0, sortie: s, entree: e, typeEntree: 'E0', bords, deltaE: bords?.deltaE ?? 0 };
      },
      eligible: () => true,
    },
  };

  // ── Historique, quotas et variété (§7.6) ──────────────────────────────────────────────────────────
  // historique : [{ transition, entree }], la plus récente en dernier
  const derniers = (h, n) => h.slice(-n).map((x) => x.transition);
  function contexte(historique) {
    const h = historique ?? [];
    return { e2Permis: h.slice(-(QUOTA_E2.sur - 1)).filter((x) => x.entree === 'E2').length < QUOTA_E2.max };
  }
  function exclueParQuota(id, h) {
    const q = REGLES[id].quota;
    if (q && derniers(h, q.sur - 1).filter((x) => x === id).length >= q.max) return `quota ${id} (${q.max} sur ${q.sur})`;
    if (REGLES[id].famille === 'effet' && derniers(h, EFFETS.sur - 1).some((x) => REGLES[x]?.famille === 'effet'))
      return `au plus ${EFFETS.max} effet sur ${EFFETS.sur}`;
    return null;
  }

  // Poids modulés (§7.4, §7.5)
  function poidsDe(id, paire, pts) {
    let w = REGLES[id].poids[paire.profil];
    const dE = pts.deltaE;
    if (dE >= 2) {
      if (id === 'C4' || id === 'C8') w *= 2;
      if (id === 'C1' && pts.typeEntree === 'E2') w *= 1.5;
    }
    if (dE <= -2) {
      if (id === 'C4' || id === 'C8') return 0;
      if (id === 'C2' || id === 'C7') w *= 1.5;
    }
    if (paire.k !== null && paire.k <= 1 && ['C5', 'C6', 'C7'].includes(id)) w *= 1.5;
    if (paire.avance_s < paire.cible_avance_s) {
      if (id === 'C4') w *= 2;
      else if (REGLES[id].bars[0] === 0) w *= 1.5;
    }
    // A finit sur une voix : l'écho prolonge la phrase au lieu de la couper (§4, C2)
    if (id === 'C2' && pts.sortie.vocale) w *= 1.5;
    return w;
  }

  // Premier repli éligible d'une transition (même sortie), avec les replis faits ; R2 en dernier recours
  function descendre(id, paire, ctx, raison, pts0) {
    const faits = [];
    let de = id, why = raison;
    for (const vers of REGLES[id].replis) {
      faits.push({ de, vers, raison: why, ou: 'plan' });
      const p = REGLES[vers].points(paire, ctx);
      const ok = p.raison ? p.raison : REGLES[vers].eligible(paire, p, ctx);
      if (ok === true) return { id: vers, pts: p, faits };
      de = vers; why = ok;
    }
    return { id: 'R2', pts: REGLES.R2.points(paire), faits };
  }
  // Échelle restante de la transition retenue : seulement les replis éligibles au plan, R2 toujours
  function echelle(id, paire, ctx) {
    return REGLES[id].replis.filter((r) => {
      if (r === 'R2') return true;
      const p = REGLES[r].points(paire, ctx);
      return !p.raison && REGLES[r].eligible(paire, p, ctx) === true;
    });
  }

  function texteRaison(paire, pts, cands, extra) {
    const morceaux = [paire.profil, paire.g === null ? null : `g ${fr(paire.g * 100)} %`,
      paire.k === null ? 'k ?' : `k ${paire.k}`, `ΔE ${signe(pts?.deltaE ?? paire.deltaE)} dB`, extra,
      cands?.length ? `poids ${cands.map((c) => `${c.id} ${fr(c.w)}`).join(' / ')}` : null].filter(Boolean);
    const t = morceaux.join(' · ');
    return t.length > 300 ? `${t.slice(0, 299)}…` : t;
  }

  function resultat(paire, id, choisie, pts, faits, ctx, poids, raison) {
    const r = { transition: id, choisie, replis: echelle(id, paire, ctx), replis_plan: faits, points: pts, poids, raison };
    Object.defineProperty(r, 'paire', { value: paire, enumerable: false });
    return r;
  }

  // ── Choix (§7) ────────────────────────────────────────────────────────────────────────────────────
  function choisir(paire, historique = [], { rng: alea = Math.random, force = null } = {}) {
    const h = historique ?? [];
    const ctx = contexte(h);
    if (paire.refus) {
      const pts = paire.refus === 'analyse absente' ? null : REGLES.R2.points(paire);
      const r = resultat(paire, 'R2', 'R2', pts, [], ctx, {}, `refus d'office : ${paire.refus}`);
      r.replis = [];
      return r;
    }
    if (force) {
      if (!IDS.includes(force)) return { erreur: `transition inconnue : ${force}` };
      const p = REGLES[force].points(paire, ctx);
      const ok = p.raison ? p.raison : REGLES[force].eligible(paire, p, { e2Permis: true });
      if (ok === true) return resultat(paire, force, force, p, [], ctx, {}, texteRaison(paire, p, null, `forcée ${force}`));
      const d = descendre(force, paire, ctx, ok, p);
      return resultat(paire, d.id, force, d.pts, d.faits, ctx, {}, texteRaison(paire, d.pts, null, `forcée ${force}, ${ok}`));
    }
    const refus = {}, cands = [];
    for (const id of CHOISISSABLES) {
      const q = exclueParQuota(id, h);
      if (q) { refus[id] = q; continue; }
      const p = REGLES[id].points(paire, ctx);
      const ok = p.raison ? p.raison : REGLES[id].eligible(paire, p, ctx);
      if (ok !== true) { refus[id] = ok; continue; }
      const w = poidsDe(id, paire, p);
      if (w <= 0) { refus[id] = 'énergie qui baisse'; continue; }
      cands.push({ id, w, pts: p });
    }
    const prev = h.at(-1)?.transition, avant = h.at(-2)?.transition;
    // La précédente est exclue. Écart assumé au §7.6 (« sauf si elle est la seule éligible ») au profit d'O7
    // (« jamais deux fois de suite ») : si elle reste seule, on passe à R1 ou R2 ci-dessous.
    const liste = cands.filter((c) => c.id !== prev);
    if (cands.some((c) => c.id === prev)) refus[prev] = 'jouée juste avant';
    for (const c of liste) if (c.id === avant) c.w *= 0.5;
    // Ajout pour O7 (≥ 4 différentes et aucune > 40 % sur 10) : le §7.6 seul ne le garantit pas (simulation :
    // fenêtres à 3 transitions). Sur les 9 dernières, 3 fois → poids × 0,3 ; 4 fois → exclue.
    const neuf = derniers(h, 9);
    for (const c of liste) {
      const n = neuf.filter((x) => x === c.id).length;
      if (n >= 4) { c.w = 0; refus[c.id] = 'déjà 4 fois sur les 9 dernières'; } else if (n === 3) c.w *= 0.3;
    }
    for (let i = liste.length - 1; i >= 0; i--) if (liste[i].w <= 0) liste.splice(i, 1);
    liste.sort((x, y) => y.w - x.w);
    const top = liste.slice(0, TOP);
    const poids = Object.fromEntries(top.map((c) => [c.id, +c.w.toFixed(2)]));
    if (!top.length) {
      const p = REGLES.R1.points(paire, ctx);
      const ok = !p.raison && REGLES.R1.eligible(paire, p, ctx) === true && prev !== 'R1';
      // R2 deux fois de suite reste possible (seul repli sans condition) : c'est une absence de transition
      const id = ok ? 'R1' : 'R2', pts = ok ? p : REGLES.R2.points(paire);
      const r = resultat(paire, id, id, pts, [], ctx, {}, texteRaison(paire, pts, null, 'aucune transition éligible'));
      r.refus = refus;
      return r;
    }
    const total = top.reduce((x, c) => x + c.w, 0);
    let u = alea() * total, pick = top[top.length - 1];
    for (const c of top) { if ((u -= c.w) <= 0) { pick = c; break; } }
    const extra = [pick.pts.typeEntree !== 'E0' ? `entrée ${pick.pts.typeEntree}` : null,
      pick.pts.sortie.repli ? 'sortie de repli' : null].filter(Boolean).join(' · ');
    const r = resultat(paire, pick.id, pick.id, pick.pts, [], ctx, poids, texteRaison(paire, pick.pts, top, extra || null));
    r.refus = refus;
    return r;
  }

  // ── Repli au plan, juste avant le saut (§8 côté extension) ───────────────────────────────────────
  // avance_s : avance mesurée maintenant ; grille : { a, b } facultatif (revérification). La sortie ne bouge
  // pas (sauf R2, qui laisse A finir) ; l'entrée est recalculée depuis la même cible.
  function replierAuPlan(choix, { avance_s, grille } = {}) {
    const paire = choix.paire;
    if (!paire || paire.refus) return choix;
    const P = { ...paire, avance_s: avance_s ?? paire.avance_s };
    const besoin = (id, pts) => {
      if (id === 'R2') return true;
      const trop = sauteTrop(pts.entree);
      if (trop) return trop;
      if (!SAUT_PERMIS.includes(id) && pts.typeEntree === 'E2') return pasE2(pts);
      if (pts.T > 0) {
        const need = avanceRequise(pts.T, pts.bords.barA);
        if (P.avance_s < need) return `avance ${fr(P.avance_s, 0)} s < ${fr(need, 0)} s requises (${pts.T} mesures)`;
      }
      const ga = grille?.a ?? pts.bords.grilleA, gb = grille?.b ?? pts.bords.grilleB;
      // même règle qu'à l'éligibilité : C2 n'a besoin que de la grille de A (écho calé sur A), R1 d'aucune
      if (id !== 'R1' && (ga === 'floue' || (gb === 'floue' && id !== 'C2'))) return 'grille floue';
      return true;
    };
    let id = choix.transition, pts = choix.points;
    let ok = besoin(id, pts);
    if (ok === true) return choix;
    const faits = [...choix.replis_plan];
    const echelleRestante = [...choix.replis];
    while (ok !== true && echelleRestante.length) {
      const vers = echelleRestante.shift();
      faits.push({ de: id, vers, raison: ok, ou: 'plan' });
      id = vers;
      pts = vers === 'R2' ? REGLES.R2.points(P) : refaire(P, vers, pts);
      ok = besoin(id, pts);
    }
    if (ok !== true) { faits.push({ de: id, vers: 'R2', raison: ok, ou: 'plan' }); id = 'R2'; pts = REGLES.R2.points(P); }
    const r = { ...choix, transition: id, points: pts, replis: echelleRestante, replis_plan: faits.slice(-3),
      raison: texteRaison(P, pts, null, `repli au plan ${choix.transition} → ${id}`) };
    Object.defineProperty(r, 'paire', { value: P, enumerable: false });
    return r;
  }
  // Points d'un repli : même sortie, entrée = cible − T' (T' = recouvrement du repli)
  function refaire(paire, id, pts) {
    const T = REGLES[id].bars[0];
    const b = paire.b.analyse, bars = b.bars;
    const ic = pts.entree.cible_mesure ?? pts.entree.mesure;
    const ie = Math.max(0, ic - T);
    const deb = PL().debutEffectif(b);
    const saute = Math.max(0, bars[ie].start - deb);
    const entree = { t: bars[ie].start, mesure: ie, cible_s: bars[ic].start, cible_mesure: ic, saute_s: +saute.toFixed(2),
      part: +(saute / (paire.b.duree_s || 1)).toFixed(4) };
    const bords = paire.bords(pts.sortie, entree, T);
    return { T, sortie: pts.sortie, entree, typeEntree: PL().typeEntree(b, entree.t), bords, deltaE: bords.deltaE };
  }

  // ── Ordre v2 (ADR 0001) ───────────────────────────────────────────────────────────────────────────
  let compteur = 0;
  const nouvelId = (t) => `t-${Math.round(t ?? Date.now())}-${++compteur}`;
  const r3 = (x) => +(+x).toFixed(3);
  function grilleRel(analyse, t0, t1, ref, garder) {
    let v = (analyse?.beats ?? []).filter((x) => x.start >= t0 && x.start <= t1).map((x) => r3(x.start - ref))
      .filter((x) => x > -60 && x < 60);
    if (v.length > 120) v = garder === 'fin' ? v.slice(-120) : v.slice(0, 120);
    return v.length >= 8 ? v : [];
  }
  function ordre(choix, paire, { t_wall, gapless = false, manuel = false, to_uri = null, id } = {}) {
    paire = paire ?? choix.paire;
    const pts = choix.points;
    if (!pts?.sortie || !pts?.entree) return { erreur: 'pas de points pour cette transition' };
    const id_ = choix.transition;
    const T = pts.T;
    const a = paire.a.analyse, b = paire.b.analyse;
    const barA = pts.bords?.barA ?? 240 / (paire.a.tempo || 120), barB = pts.bords?.barB ?? 240 / (paire.b.tempo || 120);
    const s = pts.sortie.t, e = pts.entree.t;
    const params = REGLES[id_].params ? REGLES[id_].params(paire) : {};
    const o = {
      v: 2,
      id: id ?? nouvelId(t_wall),
      transition: id_,
      choisie: choix.choisie,
      replis: [...choix.replis],
      replis_plan: [...(choix.replis_plan ?? [])].slice(-3),
      bars: T,
      params,
      t_wall,
      gapless: !!gapless,
      manuel: !!manuel,
      to_uri,
      ratio: r3(paire.ratio),
      a: {
        uri: paire.a.uri, duree_s: r3(paire.a.duree_s),
        sortie_s: r3(s), sortie_mesure: pts.sortie.mesure,
        // A : seulement les temps d'avant la sortie (après, la mémoire du moteur contient B : essai direct 13)
        bar_s: r3(barA), beats: grilleRel(a, s - (T + 2) * barA - 0.05, s + 0.05, s, 'fin'),
        grille: pts.bords?.grilleA ?? 'floue', voix: (pts.bords?.voixA ?? []).map(r3).slice(-16),
        jamais_entendu_s: r3(pts.sortie.jamais_entendu_s ?? 0),
      },
      b: {
        uri: paire.b.uri, duree_s: r3(paire.b.duree_s),
        entree_s: r3(e), entree_mesure: pts.entree.mesure, entree: pts.typeEntree,
        cible_s: r3(T === 0 ? e : Math.max(e, pts.entree.cible_s)),
        bar_s: r3(barB), beats: grilleRel(b, e - barB - 0.05, e + (T + 2) * barB + 0.05, e, 'debut'),
        grille: pts.bords?.grilleB ?? 'floue', voix: (pts.bords?.voixB ?? []).map(r3).slice(0, 16),
        saute_s: r3(pts.entree.saute_s ?? 0),
      },
      voix_source: paire.voix_source ?? 'aucune',
      raison: String(choix.raison ?? '').slice(0, 300),
    };
    return o;
  }

  // Ordre de rattrapage (morceau changé à la main, ADR 0001)
  function ordreRattrapage(a, b, { t_wall, to_uri, id, uriA } = {}) {
    const PLc = PL();
    const med = (d) => PLc.mediane((d?.bars ?? []).filter((x) => x.confidence > 0.3).map((x) => x.duration))
      ?? (d?.track?.tempo ? 240 / d.track.tempo : null);
    const barA = med(a), barB = med(b);
    if (!barA || !barB || !a?.track?.tempo || !b?.track?.tempo) return { erreur: 'analyse absente' };
    return {
      v: 2, id: id ?? nouvelId(t_wall), transition: 'R1', choisie: 'R1', replis: ['R2'], replis_plan: [], bars: 1,
      params: {}, t_wall, gapless: false, manuel: true, to_uri, ratio: r3(a.track.tempo / b.track.tempo),
      a: { uri: uriA ?? a.uri ?? null, duree_s: r3(a.track.duration ?? 0), sortie_s: null, sortie_mesure: null,
        bar_s: r3(barA), beats: [], grille: 'floue', voix: [], jamais_entendu_s: 0 },
      b: { uri: to_uri, duree_s: r3(b.track.duration ?? 0), entree_s: 0, entree_mesure: 0, entree: 'E0', cible_s: r3(barB),
        bar_s: r3(barB), beats: [], grille: 'floue', voix: [], saute_s: 0 },
      voix_source: 'aucune', raison: 'morceau changé à la main : fondu court de rattrapage',
    };
  }

  // ── Validation (miroir des bornes de l'ADR 0001, pour les tests et avant envoi) ───────────────────
  const BARS_PERMIS = { C1: [0], C2: [0], C3: [0], C4: [0], C5: [2], C6: [4], C7: [8, 16], C8: [4, 8], R1: [1], R2: [0] };
  function valider(o, maintenant = null) {
    const e = [];
    const num = (x) => typeof x === 'number' && Number.isFinite(x);
    const ent = (x) => Number.isInteger(x) && x >= 0;
    if (o?.v !== 2) e.push('v');
    if (typeof o?.id !== 'string' || !/^[A-Za-z0-9_-]{1,40}$/.test(o.id)) e.push('id');
    if (!IDS.includes(o?.transition)) e.push('transition');
    if (!IDS.includes(o?.choisie)) e.push('choisie');
    if ('mode' in (o ?? {})) e.push('mode (ancien contrat)');
    if (!Array.isArray(o?.replis) || o.replis.length > 3 || !o.replis.every((x) => IDS.includes(x))) e.push('replis');
    if (!Array.isArray(o?.replis_plan) || o.replis_plan.length > 3
      || !o.replis_plan.every((x) => IDS.includes(x?.de) && IDS.includes(x?.vers) && x.ou === 'plan')) e.push('replis_plan');
    if (!(BARS_PERMIS[o?.transition] ?? []).includes(o?.bars)) e.push('bars');
    const p = o?.params ?? null;
    if (!p || typeof p !== 'object') e.push('params');
    else if (o.transition === 'C2' && p.queue_mesures !== undefined && !(p.queue_mesures >= 2 && p.queue_mesures <= 4)) e.push('params.queue_mesures');
    else if (o.transition === 'C3' && p.frein_temps !== undefined && ![1, 2].includes(p.frein_temps)) e.push('params.frein_temps');
    if (!num(o?.t_wall) || o.t_wall <= 0 || (maintenant !== null && Math.abs(o.t_wall - maintenant) > 30000)) e.push('t_wall');
    if (typeof o?.gapless !== 'boolean' || typeof o?.manuel !== 'boolean') e.push('gapless/manuel');
    if (o?.manuel && !/^spotify:track:[A-Za-z0-9]{22}$/.test(o.to_uri ?? '')) e.push('to_uri');
    if (!num(o?.ratio) || o.ratio < 0.3 || o.ratio > 3) e.push('ratio');
    for (const c of ['a', 'b']) {
      const x = o?.[c];
      if (!x) { e.push(c); continue; }
      if (!num(x.bar_s) || x.bar_s < 0.3 || x.bar_s > 5) e.push(`${c}.bar_s`);
      if (!Array.isArray(x.beats) || (x.beats.length && (x.beats.length < 8 || x.beats.length > 120))
        || !x.beats.every((v) => num(v) && v > -60 && v < 60)) e.push(`${c}.beats`);
      if (!['nette', 'moyenne', 'floue'].includes(x.grille)) e.push(`${c}.grille`);
      if (!Array.isArray(x.voix) || x.voix.length > 16 || !x.voix.every((v) => num(v) && v >= 0 && v <= 1)) e.push(`${c}.voix`);
    }
    const A = o?.a ?? {}, B = o?.b ?? {};
    if (!(A.sortie_s === null && o?.manuel) && !(num(A.sortie_s) && A.sortie_s >= 0)) e.push('a.sortie_s');
    if (!(A.sortie_mesure === null && o?.manuel) && !ent(A.sortie_mesure)) e.push('a.sortie_mesure');
    if (!num(B.entree_s) || B.entree_s < 0) e.push('b.entree_s');
    if (!ent(B.entree_mesure)) e.push('b.entree_mesure');
    if (!['E0', 'E1', 'E2'].includes(B.entree)) e.push('b.entree');
    if (!num(B.cible_s) || B.cible_s < B.entree_s) e.push('b.cible_s');
    if (!(num(A.jamais_entendu_s) && A.jamais_entendu_s >= 0) || !(num(B.saute_s) && B.saute_s >= 0)) e.push('jamais/saute');
    if (!['paroles', 'segments', 'aucune'].includes(o?.voix_source)) e.push('voix_source');
    if (typeof o?.raison !== 'string' || o.raison.length > 300) e.push('raison');
    return e;
  }

  const api = { REGLES, QUOTA_E2, EFFETS, IDS, BARS_PERMIS, MARGE_AVANCE_S, R2_MARGE_S, avanceRequise, G_MAX, rng, choisir, replierAuPlan, ordre,
    ordreRattrapage, valider, contexte, voixEnsemble, points };
  if (enNode) module.exports = api;
  else (racine.DJCore ??= {}).choix = api;
})(globalThis);
