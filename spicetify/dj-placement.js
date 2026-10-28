// Placement des points de transition (§5 de docs/specs/transitions-v2.md), à partir de l'analyse Spotify seule :
// phrases, confiance de grille, sections de A, sorties (garde-fou anti-fin-coupée), entrées E0/E1/E2 de B, ΔE,
// profils de bord et de paire, et caractéristiques d'une paire (§7.2). Fonctions pures, aucun appel à Spicetify.
// Chargé comme extension Spicetify (globalThis.DJCore.placement) et par Node (require) pour les tests.
(function (racine) {
  const enNode = typeof module === 'object' && module.exports;
  // Dépendance résolue à l'appel (l'ordre de chargement des extensions n'est pas garanti, ADR 0005)
  const V = () => (enNode ? require('./dj-voix.js') : racine.DJCore.voix);

  const SILENCE_DB = -50;          // sous ce niveau, un segment de début ou de fin compte comme silence
  const JAMAIS_MAX_S = 30;         // O1 : partie de A jamais entendue ≤ 30 s…
  const JAMAIS_MAX_PART = 0.15;    // … et ≤ 15 % de A
  const FIN_MIN_S = 6;             // aucune sortie dans les 6 dernières secondes
  const CONF_MESURE = 0.3;         // confiance minimale d'une mesure candidate
  const BORD = 16;                 // mesures examinées de chaque côté d'un point

  const mediane = (v) => {
    if (!v.length) return null;
    const s = [...v].sort((x, y) => x - y);
    return s.length % 2 ? s[s.length >> 1] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
  };

  // ── Tonalité et tempo (déplacés de dj-auto.js, ADR 0004) ──────────────────────────────────────────
  // Roue de Camelot : numéro (quintes) et lettre (A mineur, B majeur) ; null si la tonalité est incertaine
  function camelot(t) {
    if (!t || t.key < 0 || t.key == null || !(t.key_confidence >= 0.4)) return null;
    const k = t.mode === 1 ? t.key : (t.key + 3) % 12;   // mineur : même numéro que son relatif majeur
    return { n: ((k * 7) % 12 + 7) % 12 + 1, minor: t.mode !== 1 };
  }
  const camelotNom = (c) => c && `${c.n}${c.minor ? 'A' : 'B'}`;
  function camelotDist(x, y) {
    if (!x || !y) return null;
    const d = Math.abs(x.n - y.n);
    return Math.min(d, 12 - d) + (x.minor !== y.minor ? 1 : 0);
  }
  // Écart de tempo (log), B compté à tempo double ou moitié si c'est plus proche de A
  const tempoGap = (ta, tb) => Math.min(...[0.5, 1, 2].map((f) => Math.abs(Math.log((ta / tb) * f))));
  // Écart relatif (0,02 = 2 %) et rapport 3:2 (shatta ↔ bouyon), compté incompatible
  const ecartTempo = (ta, tb) => Math.exp(tempoGap(ta, tb)) - 1;
  const rapport32 = (ta, tb) => [1.5, 2 / 3, 0.75, 4 / 3].some((r) => Math.abs(Math.log(ta / tb / r)) < 0.04);

  // ── Mesures et phrases ────────────────────────────────────────────────────────────────────────────
  // Chaque mesure : index, section, rang k depuis le début de la section, phrase 8 (k multiple de 8), 4 ou 0
  const cacheMesures = new WeakMap();
  function mesures(analyse) {
    if (!analyse?.bars) return [];
    if (cacheMesures.has(analyse)) return cacheMesures.get(analyse);
    const secs = analyse.sections ?? [];
    let si = 0, k = 0;
    const out = analyse.bars.map((x, i) => {
      while (si + 1 < secs.length && secs[si + 1].start <= x.start + 0.1) { si++; k = 0; }
      const r = { i, start: x.start, duration: x.duration, confidence: x.confidence ?? 0, section: si, k,
        phrase: k % 8 === 0 ? 8 : k % 4 === 0 ? 4 : 0 };
      k++;
      return r;
    });
    cacheMesures.set(analyse, out);
    return out;
  }
  const indexMesure = (analyse, t) => V().indexMesure(analyse?.bars ?? [], t);
  // Mesure la plus proche d'un instant (début de section pas toujours calé sur une mesure)
  function mesureProche(analyse, t) {
    const b = analyse?.bars ?? [];
    let best = -1, d = Infinity;
    for (let i = 0; i < b.length; i++) { const e = Math.abs(b[i].start - t); if (e < d) { d = e; best = i; } }
    return best;
  }

  // Début et fin « réels » : premier et dernier segment au-dessus de SILENCE_DB
  function debutEffectif(analyse) {
    const s = (analyse?.segments ?? []).find((x) => x.loudness_max > SILENCE_DB);
    return s ? s.start : (analyse?.bars?.[0]?.start ?? 0);
  }
  function finEffective(analyse) {
    const segs = analyse?.segments ?? [];
    const dur = analyse?.track?.duration ?? 0;
    for (let i = segs.length - 1; i >= 0; i--) {
      if (segs[i].loudness_max > SILENCE_DB) return Math.min(dur || Infinity, segs[i].start + segs[i].duration);
    }
    return dur;
  }

  // Durée médiane d'une mesure au bord, gardée si elle colle au tempo à 5 % près (fins d'analyse irrégulières)
  function barAu(analyse, t, sens) {
    const ref = 240 / (analyse?.track?.tempo || 120);
    const sel = V().fenetre(analyse, t, 8, sens).filter((x) => (x.confidence ?? 0) > CONF_MESURE).map((x) => x.duration);
    const m = mediane(sel);
    return m && Math.abs(m / ref - 1) < 0.05 ? m : ref;
  }

  // ── Confiance de grille (§5.2) ────────────────────────────────────────────────────────────────────
  // sens 'avant' : les n mesures avant t ; 'apres' : les n à partir de t ; sinon n centrées sur t
  function grille(analyse, t, n = BORD, sens) {
    const bars = analyse?.bars ?? [];
    let sel;
    if (sens === 'avant' || sens === 'apres') sel = V().fenetre(analyse, t, n, sens);
    else { const k = indexMesure(analyse, t); sel = bars.slice(Math.max(0, k - (n >> 1)), k + (n - (n >> 1))); }
    if (sel.length < 4) return 'floue';
    const conf = mediane(sel.map((x) => x.confidence ?? 0));
    const d = sel.map((x) => x.duration);
    const m = d.reduce((x, y) => x + y, 0) / d.length;
    const cv = Math.sqrt(d.reduce((x, y) => x + (y - m) ** 2, 0) / d.length) / m;
    if (conf >= 0.5 && cv <= 0.03) return 'nette';
    if (conf >= 0.3 && cv <= 0.06) return 'moyenne';
    return 'floue';
  }

  // ── Sections de A (§5.3) ──────────────────────────────────────────────────────────────────────────
  function sectionsA(analyse) {
    const secs = analyse?.sections ?? [];
    if (!secs.length) return { dernierePleine: null, outro_s: analyse?.track?.duration ?? 0 };
    const med = mediane(secs.map((s) => s.loudness));
    let dp = 0;
    secs.forEach((s, i) => { if (s.loudness >= med - 3) dp = i; });
    const s = secs[dp];
    return { dernierePleine: { i: dp, start: s.start, fin: s.start + s.duration }, outro_s: s.start + s.duration };
  }

  // ── Sorties de A (§5.4, §5.5) ─────────────────────────────────────────────────────────────────────
  // voixA : fonction (index de mesure) → score de voix, facultative. Rend les sorties, la préférée d'abord :
  // [{ t, mesure, jamais_entendu_s, voixFin, vocale, repli }] ; [] si aucune (→ R2).
  function sorties(analyse, { minExit_s = 0, T = 0, voixA = null } = {}) {
    const m = mesures(analyse);
    if (!m.length) return [];
    const dur = analyse.track?.duration ?? (m[m.length - 1].start + m[m.length - 1].duration);
    const fin = finEffective(analyse);
    const { dernierePleine, outro_s } = sectionsA(analyse);
    const sv = V().SEUIL_VOCAL;
    const cand = (x) => {
      const jamais = Math.max(0, fin - x.start);
      const voixFin = voixA && x.i > 0 ? voixA(x.i - 1) : 0;
      return { t: x.start, mesure: x.i, jamais_entendu_s: +jamais.toFixed(2), voixFin, vocale: voixFin >= sv, repli: false };
    };
    const base = m.filter((x) => x.confidence > CONF_MESURE && x.start >= minExit_s && x.start <= dur - FIN_MIN_S
      && x.i - T >= 0);
    const garde = (x) => fin - x.start <= JAMAIS_MAX_S && fin - x.start <= JAMAIS_MAX_PART * dur;
    // fenêtre [t − T ; t] après le début de la dernière section pleine, ou dans l'outro
    const fenetreOk = (x) => !dernierePleine || T === 0 || m[x.i - T].start >= dernierePleine.start - 0.1;
    const valides = base.filter((x) => x.start >= outro_s - 0.1 && garde(x) && fenetreOk(x));
    const v8 = valides.filter((x) => x.phrase === 8), v4 = valides.filter((x) => x.phrase >= 4);
    let liste = (v8.length ? v8 : v4).map((x) => ({ ...cand(x), garde: true }));
    if (!liste.length) {
      // Pas de sortie au début de l'outro qui respecte le garde-fou (pas d'outro, outro trop longue) : la frontière
      // la plus tardive qui le respecte, de 8 mesures, à défaut de 4, à défaut de 2 ; sinon (abandon) la frontière
      // de phrase la plus tardive avant les 6 dernières secondes, garde-fou non tenu (garde: false).
      const ok = base.filter((x) => fenetreOk(x));
      for (const pas of [8, 4, 2]) {
        const der = ok.filter((x) => x.k % pas === 0 && garde(x)).at(-1);
        if (der) return [{ ...cand(der), repli: true, garde: true }];
      }
      const p = ok.filter((x) => x.phrase >= 4);
      const p8 = p.filter((x) => x.phrase === 8);
      const der = (p8.length ? p8 : p).at(-1);
      return der ? [{ ...cand(der), repli: true, garde: garde(der) }] : [];
    }
    // Voix de A sur la dernière mesure : décaler d'une demi-phrase (sinon C2 s'en charge)
    if (liste[0].vocale) {
      const alt = v4.map(cand).find((c) => c.t > liste[0].t && c.mesure - liste[0].mesure <= 4 && !c.vocale);
      if (alt) liste = [alt, ...liste.filter((c) => c.mesure !== alt.mesure)];
    }
    return liste;
  }

  // ── Entrées de B (§5.6) ───────────────────────────────────────────────────────────────────────────
  // Rend { E0, E1, E2 } : { t, mesure, cible_s, cible_mesure, saute_s, part } ou null. Avec un recouvrement de
  // T mesures, entreeB = cible − T (E1, E2) ; pour E0, B part de son début et la cible est E0 + T.
  function entrees(analyse, { T = 0 } = {}) {
    const m = mesures(analyse);
    const vide = { E0: null, E1: null, E2: null };
    if (!m.length) return vide;
    const dur = analyse.track?.duration ?? 0;
    const deb = debutEffectif(analyse);
    const i0 = m.findIndex((x) => x.start >= deb - 0.05);
    if (i0 < 0) return vide;
    const secs = analyse.sections ?? [];
    const pt = (iEntree, iCible) => {
      if (iEntree < i0 || iCible >= m.length || iEntree < 0) return null;
      const saute = Math.max(0, m[iEntree].start - deb);
      return { t: m[iEntree].start, mesure: iEntree, cible_s: m[iCible].start, cible_mesure: iCible,
        saute_s: +saute.toFixed(2), part: dur ? +(saute / dur).toFixed(4) : 0 };
    };
    const idxSecs = secs.map((s) => ({ s, i: mesureProche(analyse, s.start) })).filter((x) => x.i >= i0 + 4);
    const e1 = idxSecs[0] ?? null;
    const moitie = idxSecs.filter((x) => x.s.start <= 0.5 * dur);
    const med = mediane(secs.map((s) => s.loudness));
    let e2 = moitie.find((x) => x.s.loudness >= med + 2) ?? null;
    if (!e2 && moitie.length) e2 = moitie.reduce((a, b) => (b.s.loudness > a.s.loudness ? b : a));
    return {
      E0: pt(i0, i0 + T),
      E1: e1 ? pt(e1.i - T, e1.i) : null,
      E2: e2 ? pt(e2.i - T, e2.i) : null,
    };
  }
  // Nature d'un point d'entrée (pour b.entree et le quota E2) : E0 si B part de son début ; E2 si le début est
  // sauté et que B reprend dans un refrain (section ≥ médiane + 2 dB, ou la section E2), quelle que soit la
  // position ; E1 si au plus à la fin de l'intro ; E2 au-delà.
  function typeEntree(analyse, t) {
    const e = entrees(analyse, { T: 0 });
    if (!e.E0 || t <= e.E0.t + 0.1) return 'E0';
    const secs = analyse.sections ?? [];
    const med = mediane(secs.map((s) => s.loudness));
    const sec = secs.filter((s) => s.start <= t + 0.15).at(-1);
    const refrain = sec && (sec.loudness >= med + 2 || (e.E2 && Math.abs(analyse.bars[e.E2.mesure].start - sec.start) < 0.15
      && sec.start > e.E0.t + 0.1));
    if (refrain) return 'E2';
    if (e.E1 && t <= e.E1.t + 0.1) return 'E1';
    return 'E2';
  }

  // ── Énergie (§5.7) ────────────────────────────────────────────────────────────────────────────────
  function sonieMoyenne(analyse, t, sens) {
    const w = V().fenetre(analyse, t, 4, sens);
    if (!w.length) return null;
    const t0 = w[0].start, t1 = w.at(-1).start + w.at(-1).duration;
    const s = (analyse.segments ?? []).filter((x) => x.start >= t0 && x.start < t1);
    return s.length ? s.reduce((x, y) => x + y.loudness_max, 0) / s.length : null;
  }
  // ΔE = sonie des 4 mesures de B après son point d'arrivée − celle des 4 dernières de A avant sa sortie
  function deltaE(a, sortie_s, b, cible_s) {
    const la = sonieMoyenne(a, sortie_s, 'avant'), lb = sonieMoyenne(b, cible_s, 'apres');
    return la === null || lb === null ? 0 : +(lb - la).toFixed(2);
  }

  // ── Profils (§5.8) ────────────────────────────────────────────────────────────────────────────────
  // Mesures sans voix d'affilée depuis le bord (A : la fin de la liste ; B : le début)
  function sansVoix(voix, sens) {
    const v = sens === 'avant' ? [...voix].reverse() : voix;
    const s = V().SEUIL_SANS_VOIX;
    let n = 0;
    for (const x of v) { if (x < s) n++; else break; }
    return n;
  }
  function profilBord(voix, sens) {
    const n = sens ? sansVoix(voix, sens) : Math.max(sansVoix(voix, 'avant'), sansVoix(voix, 'apres'));
    return n >= 8 ? 'instrumental' : 'vocal';
  }
  const profilPaire = (bordA, bordB, tempo) =>
    bordA === 'instrumental' && bordB === 'instrumental' && tempo >= 110 && tempo <= 135 ? 'long' : 'court';

  // ── Paire (§7.2) ──────────────────────────────────────────────────────────────────────────────────
  // a, b : analyses getAudioData (avec .uri si connu). voixA, voixB : lignes de paroles (V1) ou null.
  // Les points dépendent du recouvrement T et de la cible d'entrée : ils sont calculés à la demande (bords()).
  function paire(a, b, { minExit_s = 0, avance_s = 60, cible_avance_s = 60, contexte = null, voixA = null, voixB = null,
    uriA, uriB } = {}) {
    const ok = (d) => d?.bars?.length && d.sections?.length && d.track?.tempo > 0;
    let refus = null;
    if (contexte === 'album') refus = 'album joué dans l\'ordre';
    else if (!ok(a) || !ok(b)) refus = 'analyse absente';
    const P = {
      a: { analyse: a, uri: uriA ?? a?.uri ?? null, duree_s: a?.track?.duration ?? 0, tempo: a?.track?.tempo ?? 0,
        cam: camelot(a?.track) },
      b: { analyse: b, uri: uriB ?? b?.uri ?? null, duree_s: b?.track?.duration ?? 0, tempo: b?.track?.tempo ?? 0,
        cam: camelot(b?.track) },
      contexte, avance_s, cible_avance_s, minExit_s, refus,
    };
    if (refus) return Object.assign(P, { g: null, rapport32: false, ratio: 1, k: null, voix_source: 'aucune',
      profil: 'court', deltaE: 0, sortie: () => null, entrees: () => ({ E0: null, E1: null, E2: null }), bords: () => null });
    P.ratio = P.a.tempo / P.b.tempo;
    P.g = ecartTempo(P.a.tempo, P.b.tempo);
    P.rapport32 = rapport32(P.a.tempo, P.b.tempo) && P.g > 0.06;
    P.k = camelotDist(P.a.cam, P.b.cam);
    const vx = V();
    const src = (l, d) => (Array.isArray(l) && l.length ? 'paroles' : vx.scoresV2(d) ? 'segments' : 'aucune');
    const sa = src(voixA, a), sb = src(voixB, b);
    P.voix_source = sa === 'aucune' || sb === 'aucune' ? 'aucune' : sa === 'paroles' && sb === 'paroles' ? 'paroles' : 'segments';
    const voixMesA = (i) => vx.voixMesure(a, voixA, i);
    const memo = new Map();
    P.sortie = (T) => {
      const c = `s${T}`;
      if (!memo.has(c)) memo.set(c, sorties(a, { minExit_s, T, voixA: voixMesA })[0] ?? null);
      return memo.get(c);
    };
    P.entrees = (T) => {
      const c = `e${T}`;
      if (!memo.has(c)) memo.set(c, entrees(b, { T }));
      return memo.get(c);
    };
    // Bords autour d'une sortie et d'une entrée données (instant en s), avec T mesures de recouvrement
    P.bords = (sortie, entree, T) => {
      if (!sortie || !entree) return null;
      const c = `b${sortie.t}|${entree.t}|${T}`;
      if (memo.has(c)) return memo.get(c);
      const va = vx.voixBord(a, voixA, sortie.t, BORD, 'avant');
      const vb = vx.voixBord(b, voixB, entree.t, BORD, 'apres');
      const r = {
        voixA: va.valeurs, voixB: vb.valeurs,
        grilleA: grille(a, sortie.t, BORD, 'avant'), grilleB: grille(b, entree.t, BORD, 'apres'),
        barA: barAu(a, sortie.t, 'avant'), barB: barAu(b, entree.t, 'apres'),
        deltaE: deltaE(a, sortie.t, b, entree.cible_s),
        sansVoixA: sansVoix(va.valeurs, 'avant'), sansVoixB: sansVoix(vb.valeurs, 'apres'),
      };
      r.profilA = r.sansVoixA >= 8 ? 'instrumental' : 'vocal';
      r.profilB = r.sansVoixB >= 8 ? 'instrumental' : 'vocal';
      memo.set(c, r);
      return r;
    };
    // Profil et ΔE de référence : sortie préférée, B depuis son début
    const s0 = P.sortie(0), e0 = P.entrees(0).E0;
    const b0 = P.bords(s0, e0, 0);
    const tempo = P.a.tempo * Math.exp(Math.log(P.b.tempo / P.a.tempo) / 2);
    P.profil = b0 ? profilPaire(b0.profilA, b0.profilB, tempo) : 'court';
    P.deltaE = b0 ? b0.deltaE : 0;
    return P;
  }

  const api = { SILENCE_DB, JAMAIS_MAX_S, JAMAIS_MAX_PART, FIN_MIN_S, BORD, mesures, grille, sectionsA, sorties, entrees,
    typeEntree, deltaE, profilBord, profilPaire, sansVoix, camelot, camelotNom, camelotDist, tempoGap, ecartTempo,
    rapport32, paire, barAu, mesureProche, debutEffectif, finEffective, indexMesure, mediane };
  if (enNode) module.exports = api;
  else (racine.DJCore ??= {}).placement = api;
})(globalThis);
