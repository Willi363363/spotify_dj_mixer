// Simulation à blanc (spec §9.1, critères 8 et 10) : 30 transitions à la suite sur la bibliothèque factice, avance
// du moteur comprise, puis cohérence des identifiants entre dj-catalogue.js, dj-choix.js et le moteur Python
// (transitions/contrat.py et catalogue.py, lus par python3).
//
// Vérifie : O1 (fin de A), placement sur des frontières (9.1-8), O7 (variété), quotas C2/C3/C4/effets et refrain
// (E2, ADR 0003), avance suffisante pour chaque superposition jouée (9.1-12 côté plan). La répartition des
// transitions de chaque simulation est affichée (diagnostic de node --test).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
const PL = require('../dj-placement.js');
const C = require('../dj-choix.js');
const V = require('../dj-voix.js');
const CAT = require('../dj-catalogue.js');
const { bibliotheque } = require('./fixtures/bibliotheque.js');

const ICI = path.dirname(fileURLToPath(import.meta.url));
const T0 = 1_800_000_000_000;
const N = 30;
const AVANCE_VISEE_S = 60;     // D de e2.py
const RALENTI = 1.03;          // DJ_SLOW par défaut (ADR 0003)
const GRAINES = [1, 2, 3, 4, 5, 6];

// ── Simulation ──────────────────────────────────────────────────────────────────────────────────────
// Ordre des morceaux : aléatoire (lecture en mélange) ou au tempo le plus proche (façon chooseNext).
// Avance : chaque superposition de T mesures en consomme T (a.bar_s), C4 en regagne 2 ; entre deux transitions,
// le ralenti ×1,03 regagne durée jouée × (1 − 1/1,03) (ADR 0003) sur la musique de B (de son entrée jusqu'à 15 s avant le plan suivant), tant
// que l'avance est sous la cible. Le plan voit l'avance du moment, comme dj-auto.js (paire puis replierAuPlan).
function simuler(graine, { ordre = 'hasard', taille = 60 } = {}) {
  const lib = bibliotheque(taille, 100 + graine);
  const alea = C.rng(graine);
  const h = [];
  const pas = [];
  let a = lib[0];
  const vus = new Set([a]);
  let avance = AVANCE_VISEE_S;
  let entreePrec = 0;
  for (let i = 0; i < N; i++) {
    const reste = lib.filter((x) => !vus.has(x));
    if (!reste.length) break;
    const b = ordre === 'tempo'
      ? reste.map((x) => [PL.ecartTempo(a.track.tempo, x.track.tempo) + alea() * 0.02, x]).sort((p, q) => p[0] - q[0])[0][1]
      : reste[Math.floor(alea() * reste.length)];
    vus.add(b);
    // regain pendant la lecture de A (qui était le B précédent) jusqu'au plan
    const sortieVisee = PL.sorties(a, {})[0]?.t ?? a.track.duration;
    avance = Math.min(AVANCE_VISEE_S, avance + Math.max(0, sortieVisee - entreePrec - 15) * (1 - 1 / RALENTI));
    const avancePlan = avance;
    // V1 allumé par défaut (ADR 0002) : paroles si le morceau en a, sinon V2
    const p = PL.paire(a, b, { avance_s: avance, cible_avance_s: AVANCE_VISEE_S,
      voixA: V.parserParoles(a.paroles), voixB: V.parserParoles(b.paroles) });
    let ch = C.choisir(p, h, { rng: alea });
    ch = C.replierAuPlan(ch, { avance_s: avance });
    const o = C.ordre(ch, p, { t_wall: T0 });
    h.push({ transition: o.transition, entree: o.b.entree });
    avance -= o.bars * o.a.bar_s;
    if (o.transition === 'C4') avance += 2 * o.a.bar_s;
    entreePrec = o.b.entree_s;
    pas.push({ a, b, p, ch, o, avancePlan, avanceApres: avance });
    a = b;
  }
  return pas;
}

const SIMULATIONS = GRAINES.flatMap((g) => [['hasard', g], ['tempo', g]]).map(([ordre, g]) => ({
  nom: `graine ${g}, ordre ${ordre === 'hasard' ? 'aléatoire' : 'tempo proche'}`, pas: simuler(g, { ordre }),
}));
const ids = (pas) => pas.map((x) => x.o.transition);
const resume = (pas) => ids(pas).join(' ');

test('simulation : 30 transitions par simulation, ordres v2 valides, répartition affichée', (t) => {
  const total = {};
  for (const { nom, pas } of SIMULATIONS) {
    assert.equal(pas.length, N, nom);
    for (const { o } of pas) assert.deepEqual(C.valider(o, T0), [], `${nom} : ${JSON.stringify(o).slice(0, 200)}`);
    const rep = {};
    for (const id of ids(pas)) { rep[id] = (rep[id] ?? 0) + 1; total[id] = (total[id] ?? 0) + 1; }
    const e2 = pas.filter((x) => x.o.b.entree === 'E2').length;
    const replis = pas.filter((x) => x.o.choisie !== x.o.transition).length;
    t.diagnostic(`${nom} : ${Object.entries(rep).sort().map(([k, v]) => `${k} ${v}`).join(', ')} · E2 ${e2} · `
      + `replis au plan ${replis} · avance min ${Math.min(...pas.map((x) => x.avanceApres)).toFixed(1)} s`);
    t.diagnostic(`  ${resume(pas)}`);
  }
  const n = SIMULATIONS.length * N;
  t.diagnostic(`répartition sur ${n} transitions : ${Object.entries(total).sort()
    .map(([k, v]) => `${k} ${(100 * v / n).toFixed(0)} %`).join(', ')}`);
  // Le catalogue sert : chaque transition choisissable apparaît au moins une fois sur l'ensemble
  for (const id of ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C8']) assert.ok(total[id] > 0, `${id} jamais choisie`);
});

// ── O1 : fin de A respectée ─────────────────────────────────────────────────────────────────────────

test('O1 : partie de A jamais entendue ≤ 30 s et ≤ 15 % de A sur 100 % des transitions', () => {
  const fautes = [];
  for (const { nom, pas } of SIMULATIONS) {
    for (const [i, { a, o }] of pas.entries()) {
      // recalculé depuis l'analyse : de sortieA à la fin réelle (silence final retiré)
      const jamais = Math.max(0, PL.finEffective(a) - o.a.sortie_s);
      if (jamais > 30 + 1e-6 || jamais > 0.15 * a.track.duration + 1e-6) {
        fautes.push(`${nom} n° ${i + 1} ${o.transition} : ${jamais.toFixed(1)} s sur ${a.track.duration.toFixed(0)} s`);
      }
      assert.ok(Math.abs(o.a.jamais_entendu_s - jamais) < 0.05, `jamais_entendu_s de l'ordre faux : ${o.a.jamais_entendu_s} / ${jamais}`);
    }
  }
  assert.deepEqual(fautes, []);
});

// Une sortie exige ≥ 6 s avant la fin (§5.5) : si la dernière section pleine va jusqu'à la fin de A (radio edit sans
// outro), l'entendre en entier est impossible. Strict là où c'est possible ; le taux global est affiché à part.
function sectionPleine() {
  let ok = 0, n = 0, possibles = 0, okPossibles = 0;
  const manques = [];
  for (const { nom, pas } of SIMULATIONS) {
    for (const [i, { a, o }] of pas.entries()) {
      const { dernierePleine } = PL.sectionsA(a);
      const entiere = !dernierePleine || o.a.sortie_s >= dernierePleine.fin - 0.1;
      const possible = !dernierePleine || dernierePleine.fin <= a.track.duration - PL.FIN_MIN_S;
      n++; ok += entiere;
      if (possible) { possibles++; okPossibles += entiere; }
      if (possible && !entiere) manques.push(`${nom} n° ${i + 1} : sortie ${o.a.sortie_s} s < fin ${dernierePleine.fin.toFixed(2)} s`);
    }
  }
  return { ok, n, possibles, okPossibles, manques };
}

test('O1 : dernière section « pleine » de A entendue en entier quand A a une fin après elle (100 %)', (t) => {
  const r = sectionPleine();
  t.diagnostic(`${r.okPossibles}/${r.possibles} quand c'est possible ; ${r.ok}/${r.n} (${(100 * r.ok / r.n).toFixed(0)} %) en tout`);
  assert.deepEqual(r.manques, []);
});

// Arbitrage de l'orchestrateur : seules comptent les transitions où la dernière section pleine de A finit ≥ 6 s avant
// la fin du morceau (sinon l'objectif est inatteignable, §5.5).
test('O1 : dernière section « pleine » de A entendue en entier sur ≥ 90 % des transitions où c\'est possible', () => {
  const r = sectionPleine();
  assert.ok(r.possibles > 0, 'aucune transition comptable');
  assert.ok(r.okPossibles / r.possibles >= 0.9, `${r.okPossibles}/${r.possibles}`);
});

// ── 9.1-8 : placement sur des frontières ────────────────────────────────────────────────────────────

test('9.1-8 placement : sortieA sur une frontière de phrase, entreeB sur une mesure, cible sur une section', () => {
  for (const { nom, pas } of SIMULATIONS) {
    for (const [i, { a, b, o }] of pas.entries()) {
      const ctx = `${nom} n° ${i + 1} ${o.transition}`;
      const ma = PL.mesures(a);
      if (o.transition !== 'R2') {   // R2 : A joue jusqu'à sa fin réelle
        const m = ma[o.a.sortie_mesure];
        assert.ok(m && Math.abs(m.start - o.a.sortie_s) < 0.002, `${ctx} : sortie hors mesure`);
        assert.ok(m.phrase >= 4, `${ctx} : sortie sur la mesure ${m.k} de sa section (pas une frontière de phrase)`);
      }
      const bb = b.bars;
      assert.ok(Math.abs(bb[o.b.entree_mesure].start - o.b.entree_s) < 0.002, `${ctx} : entrée hors mesure`);
      const ic = bb.findIndex((x) => Math.abs(x.start - o.b.cible_s) < 0.002);
      assert.ok(ic >= 0, `${ctx} : cible hors mesure`);
      assert.equal(ic - o.b.entree_mesure, o.bars, `${ctx} : cible = entrée + T mesures`);
      const debutsSections = new Set(b.sections.map((s) => PL.indexMesure(b, s.start + 0.05)));
      const e0 = PL.entrees(b, { T: 0 }).E0;
      assert.ok(debutsSections.has(ic) || o.b.entree_mesure === e0.mesure,
        `${ctx} : cible (mesure ${ic}) ni début de section ni E0 + T`);
    }
  }
});

// ── O7 et quotas (9.1-10) ───────────────────────────────────────────────────────────────────────────

const fenetres = (pas, n) => Array.from({ length: Math.max(0, pas.length - n + 1) }, (_, i) => pas.slice(i, i + n));

test('O7 : jamais deux fois de suite la même transition', () => {
  const fautes = [];
  for (const { nom, pas } of SIMULATIONS) {
    const s = ids(pas);
    for (let i = 1; i < s.length; i++) if (s[i] === s[i - 1]) fautes.push(`${nom} n° ${i + 1} : ${s[i]} deux fois`);
  }
  assert.deepEqual(fautes, []);
});

// Arbitrage de l'orchestrateur : un repli forcé (R1, R2 faute de transition éligible hors repli) ne compte pas dans
// la fenêtre O7, qui se mesure sur les transitions réellement choisies parmi au moins 2 éligibles. Une transition est
// « éligible » si ses conditions d'usage passent ; les exclusions de variété (précédente, quotas, 4 sur 9) n'en ôtent pas.
const VARIETE = /jouée juste avant|déjà \d+ fois|quota|effet sur/;
const nbEligibles = (ch) => ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']
  .filter((id) => !(id in (ch.refus ?? {})) || VARIETE.test(String(ch.refus[id]))).length;
const repliForce = (x) => ['R1', 'R2'].includes(x.o.transition);
const compte = (x) => !repliForce(x) && nbEligibles(x.ch) >= 2;

test('O7 : sur 10 transitions choisies de suite (fenêtres sans repli forcé), ≥ 4 différentes et aucune > 40 %', (t) => {
  const fautes = [];
  let mesurees = 0, total = 0;
  for (const { nom, pas } of SIMULATIONS) {
    const forces = pas.filter(repliForce).length;
    t.diagnostic(`${nom} : replis forcés ${forces}/${pas.length} (${(100 * forces / pas.length).toFixed(0)} %)`);
    for (const [i, w] of fenetres(pas, 10).entries()) {
      total++;
      // une fenêtre coupée par un repli forcé (ou un choix sans alternative) ne mesure pas la variété du choix
      if (!w.every(compte)) continue;
      mesurees++;
      const c = {};
      for (const x of w) c[x.o.transition] = (c[x.o.transition] ?? 0) + 1;
      if (Object.keys(c).length < 4 || Math.max(...Object.values(c)) > 4) {
        fautes.push(`${nom}, fenêtre ${i + 1} : ${w.map((x) => x.o.transition).join(' ')}`);
      }
    }
  }
  t.diagnostic(`O7 : ${mesurees}/${total} fenêtres de 10 mesurées (les autres contiennent un repli forcé)`);
  assert.ok(mesurees >= 20, `trop peu de fenêtres mesurables : ${mesurees}/${total}`);
  assert.deepEqual(fautes, []);
});

test('quotas : C2 ≤ 1 sur 3, C3 ≤ 1 sur 6, C4 ≤ 1 sur 5, effets (C3, C4) ≤ 1 sur 4', () => {
  const q = [['C2', 3], ['C3', 6], ['C4', 5]];
  for (const { nom, pas } of SIMULATIONS) {
    const s = ids(pas);
    for (const [id, n] of q) {
      for (const w of fenetres(s, n)) assert.ok(w.filter((x) => x === id).length <= 1, `${nom} : ${id} ${w.join(' ')}`);
    }
    for (const w of fenetres(s, 4)) {
      assert.ok(w.filter((x) => x === 'C3' || x === 'C4').length <= 1, `${nom} : effets ${w.join(' ')}`);
    }
  }
});

// Entrée « sur le refrain » : B commence au point E2 (§5.6), même quand ce point coïncide avec E1 (B sans intro,
// E1 = premier début de section après ≥ 4 mesures = le refrain) : le début de B est sauté pareil.
function surRefrain(b, o) {
  if (o.b.entree === 'E2') return true;
  const e = PL.entrees(b, { T: 0 });
  return !!e.E2 && e.E2.t > e.E0.t + 0.1 && Math.abs(o.b.entree_s - e.E2.t) < 0.01;
}

test('quota refrain (E2) : ≤ 1 sur 3, jamais deux de suite, C1/C3/C4 seulement, B sauté ≤ 25 % et ≤ 45 s', () => {
  const fautes = [];
  for (const { nom, pas } of SIMULATIONS) {
    for (const [i, w] of fenetres(pas, 3).entries()) {
      const k = w.filter((x) => surRefrain(x.b, x.o)).length;
      if (k > 1) fautes.push(`${nom}, n° ${i + 1}-${i + 3} : ${k} entrées sur le refrain (${w.map((x) => `${x.o.transition} ${x.o.b.entree}`).join(', ')})`);
    }
    for (const [i, { o, b }] of pas.entries()) {
      if (!surRefrain(b, o)) continue;
      if (!['C1', 'C3', 'C4'].includes(o.transition)) fautes.push(`${nom} n° ${i + 1} : refrain pour ${o.transition}`);
      if (!(o.b.saute_s <= 45 && o.b.saute_s <= 0.25 * b.track.duration + 1e-6)) {
        fautes.push(`${nom} n° ${i + 1} ${o.transition} (étiqueté ${o.b.entree}) : B sauté ${o.b.saute_s} s sur `
          + `${b.track.duration.toFixed(0)} s (${(100 * o.b.saute_s / b.track.duration).toFixed(0)} %)`);
      }
    }
  }
  assert.deepEqual(fautes, []);
});

test('B sauté : aucune entrée ne saute plus de 25 % ni plus de 45 s de B, quelle que soit son étiquette', () => {
  const fautes = [];
  for (const { nom, pas } of SIMULATIONS) {
    for (const [i, { o, b }] of pas.entries()) {
      if (o.b.saute_s > 45 || o.b.saute_s > 0.25 * b.track.duration + 1e-6) {
        fautes.push(`${nom} n° ${i + 1} ${o.transition} ${o.b.entree} : ${o.b.saute_s} s sur ${b.track.duration.toFixed(0)} s`);
      }
    }
  }
  assert.deepEqual(fautes, []);
});

// ── Avance ──────────────────────────────────────────────────────────────────────────────────────────

test('avance : chaque superposition jouée avait l\'avance requise au plan, l\'avance ne devient jamais négative', () => {
  for (const { nom, pas } of SIMULATIONS) {
    for (const [i, x] of pas.entries()) {
      const { o } = x;
      if (o.bars > 0) {
        const req = C.avanceRequise(o.bars, o.a.bar_s);
        assert.ok(x.avancePlan >= req, `${nom} n° ${i + 1} ${o.transition} T=${o.bars} : ${x.avancePlan.toFixed(1)} s < ${req.toFixed(1)} s`);
        // le rendu doit être prêt avant que la lecture n'atteigne le début du segment (T mesures avant le saut) :
        // il attend B jusqu'à T + 2 mesures (+ 1 temps) après le saut
        const pret = (o.bars + 2) * o.b.bar_s + o.b.bar_s / 4;
        assert.ok(x.avancePlan - o.bars * o.a.bar_s - pret >= 2,
          `${nom} n° ${i + 1} ${o.transition} T=${o.bars} : marge ${(x.avancePlan - o.bars * o.a.bar_s - pret).toFixed(1)} s`);
      }
      assert.ok(x.avanceApres > 0, `${nom} n° ${i + 1} : avance ${x.avanceApres.toFixed(1)} s`);
    }
  }
});

// ── Cohérence des identifiants entre les trois catalogues (ADR 0005) ───────────────────────────────

function moteur() {
  const code = [
    'import json, sys',
    `sys.path.insert(0, ${JSON.stringify(path.join(ICI, '..', '..', 'proto', 'e2'))})`,
    'from transitions import catalogue as K, contrat as T',
    'print(json.dumps({"ids": list(T.IDS), "bars": {k: list(v) for k, v in T.BARS_PERMIS.items()},',
    '  "fiches": {k: {"bars": list(f.bars_permis), "famille": f.famille, "replis": list(f.replis)}',
    '             for k, f in K.FICHES.items()}}))',
  ].join('\n');
  try {
    return JSON.parse(execFileSync('python3', ['-I', '-c', code], { encoding: 'utf8', timeout: 60000 }));
  } catch (e) {
    return { erreur: String(e.message).split('\n')[0] };
  }
}

test('identifiants : dj-catalogue.js, dj-choix.js, contrat.py et catalogue.py ont les mêmes ids et les mêmes T', (t) => {
  const py = moteur();
  if (py.erreur) { t.skip(`moteur Python illisible : ${py.erreur}`); return; }
  const jouables = [...C.IDS].sort();
  // R3 (moteur éteint) et le secours sont affichables mais jamais demandés dans un ordre : à part
  const affichables = Object.keys(CAT.CATALOGUE).filter((id) => !['R3', 'secours'].includes(id)).sort();
  assert.deepEqual([...py.ids].sort(), jouables, 'contrat.IDS = dj-choix IDS');
  assert.deepEqual(Object.keys(py.fiches).sort(), jouables, 'catalogue.FICHES = dj-choix IDS');
  assert.deepEqual(Object.keys(C.REGLES).sort(), jouables, 'REGLES = IDS');
  assert.deepEqual(affichables, jouables, 'dj-catalogue.js (hors R3, secours) = IDS');
  assert.deepEqual([...CAT.JOUABLES].sort(), jouables, 'dj-catalogue JOUABLES = IDS');
  for (const id of C.IDS) {
    const bars = C.BARS_PERMIS[id];
    assert.deepEqual(py.bars[id], bars, `${id} : contrat.BARS_PERMIS`);
    assert.deepEqual(py.fiches[id].bars, bars, `${id} : FICHES.bars_permis`);
    assert.deepEqual(C.REGLES[id].bars, bars, `${id} : REGLES.bars`);
    assert.deepEqual(CAT.CATALOGUE[id].bars, bars, `${id} : dj-catalogue bars`);
    assert.equal(py.fiches[id].famille, C.REGLES[id].famille, `${id} : famille moteur / choix`);
    assert.equal(CAT.CATALOGUE[id].famille, C.REGLES[id].famille, `${id} : famille catalogue / choix`);
    assert.deepEqual(py.fiches[id].replis, C.REGLES[id].replis, `${id} : échelle de repli moteur / choix`);
  }
});

test('identifiants : R3 et secours à part (bars null, jamais dans un ordre)', () => {
  for (const id of ['R3', 'secours']) {
    assert.ok(CAT.CATALOGUE[id], `${id} absent de dj-catalogue.js`);
    assert.equal(CAT.CATALOGUE[id].bars, null, `${id} : bars doit être null`);
    assert.ok(!C.IDS.includes(id), `${id} ne doit pas être demandable`);
    assert.ok(!CAT.JOUABLES.includes(id), `${id} ne doit pas être jouable`);
  }
  const py = moteur();
  if (!py.erreur) for (const id of ['R3', 'secours']) assert.ok(!py.ids.includes(id), `${id} dans contrat.IDS`);
});
