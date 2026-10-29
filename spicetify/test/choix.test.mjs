// Choix (§7), repli au plan (§8) et ordre v2 (ADR 0001) : dj-choix.js sur analyses factices.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const PL = require('../dj-placement.js');
const C = require('../dj-choix.js');
const { fabriquer } = require('./fixtures/fabrique.js');
const { morceau, bibliotheque } = require('./fixtures/bibliotheque.js');

const T0 = 1_800_000_000_000;
const S = (mesures, sonie, voix = false) => ({ mesures, sonie, voix });
const instru = [{ debut_s: 0, fin_s: 1e4, vide: true }];   // paroles vides : bords sûrement instrumentaux

// Enchaînement façon chooseNext : B = morceau restant au tempo le plus proche
function enchainer(lib, n, graine, avance = () => 60) {
  const r = C.rng(graine);
  const h = [], sortie = [];
  let a = lib[0];
  const vus = new Set([a]);
  for (let i = 0; i < n; i++) {
    const reste = lib.filter((x) => !vus.has(x));
    if (!reste.length) break;
    const b = reste.map((x) => [PL.ecartTempo(a.track.tempo, x.track.tempo) * 100 + r() * 3, x]).sort((p, q) => p[0] - q[0])[0][1];
    vus.add(b);
    const p = PL.paire(a, b, { avance_s: avance(i), cible_avance_s: 60 });
    const ch = C.choisir(p, h, { rng: r });
    const o = C.ordre(ch, p, { t_wall: T0 });
    h.push({ transition: o.transition, entree: o.b.entree });
    sortie.push({ p, ch, o });
    a = b;
  }
  return sortie;
}

test('ordres v2 valides sur 60 transitions factices (bornes de l\'ADR 0001)', () => {
  const lib = bibliotheque(70, 2);
  for (const { o, p } of enchainer(lib, 60, 3, (i) => 20 + (i * 7) % 50)) {
    assert.deepEqual(C.valider(o, T0), [], JSON.stringify(o).slice(0, 300));
    assert.ok(C.BARS_PERMIS[o.transition].includes(o.bars));
    assert.ok(o.raison.length <= 300);
    // garde-fou O1 dans l'ordre : jamais entendu ≤ 30 s et ≤ 15 % de A (sauf sortie de repli signalée)
    if (o.transition !== 'R2') assert.ok(o.a.jamais_entendu_s <= 30 || p.sortie(o.bars)?.repli, `O1 ${o.a.jamais_entendu_s}`);
    assert.ok(o.a.sortie_s <= o.a.duree_s);
    assert.ok(o.b.cible_s >= o.b.entree_s);
    // temps de A : rien après la sortie (la mémoire du moteur y contient B), T + 2 mesures avant (essai direct 13)
    if (o.a.beats.length) {
      assert.ok(Math.max(...o.a.beats) <= 0.05, `temps de A après la sortie : ${Math.max(...o.a.beats)}`);
      assert.ok(Math.min(...o.a.beats) <= -(o.bars + 1.5) * o.a.bar_s, `temps de A : ${Math.min(...o.a.beats)}`);
    }
  }
});

test('variété (O7) et quotas : jamais deux fois de suite, C2 1/3, C3 1/6, C4 1/5, effets 1/4, E2 1/3', () => {
  for (const g of [1, 2, 3, 4]) {
    const seq = enchainer(bibliotheque(50, 10 + g), 40, g).map((x) => x.o);
    const ids = seq.map((o) => o.transition);
    for (let i = 1; i < ids.length; i++) {
      if (ids[i] !== 'R2') assert.notEqual(ids[i], ids[i - 1], `deux ${ids[i]} de suite : ${ids.join(' ')}`);
    }
    const fenetre = (n, f) => { for (let i = 0; i + n <= seq.length; i++) assert.ok(f(seq.slice(i, i + n)), ids.join(' ')); };
    fenetre(3, (w) => w.filter((o) => o.transition === 'C2').length <= 1);
    fenetre(6, (w) => w.filter((o) => o.transition === 'C3').length <= 1);
    fenetre(5, (w) => w.filter((o) => o.transition === 'C4').length <= 1);
    fenetre(4, (w) => w.filter((o) => ['C3', 'C4'].includes(o.transition)).length <= 1);
    fenetre(3, (w) => w.filter((o) => o.b.entree === 'E2').length <= 1);
    for (const o of seq) {
      if (o.b.entree === 'E2') {
        assert.ok(['C1', 'C3', 'C4'].includes(o.transition), `E2 interdit pour ${o.transition}`);
        assert.ok(o.b.saute_s <= 45 && o.b.saute_s <= 0.25 * o.b.duree_s);
      }
    }
    // O7 sur des fenêtres de 10 : ≥ 4 transitions différentes
    for (let i = 0; i + 10 <= ids.length; i++) assert.ok(new Set(ids.slice(i, i + 10)).size >= 4, ids.join(' '));
  }
});

test('refus d\'office : album → R2 sans repli ; analyse absente → pas de points', () => {
  const a = morceau('rap', 1), b = morceau('rap', 2);
  const ch = C.choisir(PL.paire(a, b, { contexte: 'album' }), []);
  assert.equal(ch.transition, 'R2');
  assert.deepEqual(ch.replis, []);
  const o = C.ordre(ch, null, { t_wall: T0 });
  assert.deepEqual(C.valider(o, T0), []);
  assert.ok(o.a.sortie_s >= a.track.duration - 2, 'R2 : A joue jusqu\'à sa fin réelle');
  assert.equal(o.b.entree, 'E0');
  const vide = C.choisir(PL.paire(a, { track: {} }, {}), []);
  assert.equal(vide.transition, 'R2');
  assert.equal(vide.points, null);
});

test('tempos incompatibles (shatta → bouyon, 3:2) : aucune superposition', () => {
  const a = morceau('shatta', 5, { tempo: 104 }), b = morceau('bouyon', 6, { tempo: 156 });
  const p = PL.paire(a, b, { avance_s: 60 });
  assert.ok(p.rapport32);
  const ch = C.choisir(p, [], { rng: C.rng(1) });
  for (const id of ['C5', 'C6', 'C7', 'C8']) assert.match(String(ch.refus[id]), /tempo|3:2|sortie|début|ΔE|Camelot/);
  assert.ok(!['C5', 'C6', 'C7', 'C8'].includes(ch.transition));
});

test('grille floue : ni superposition ni effet', () => {
  const a = morceau('rap', 7, { confiance: 0.1 }), b = morceau('rap', 8, { confiance: 0.1 });
  const ch = C.choisir(PL.paire(a, b, { avance_s: 90 }), [], { rng: C.rng(2) });
  assert.ok(!['C1', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8'].includes(ch.transition), ch.transition);
});

test('repli au plan : C2 garde une grille de B floue (seule la grille de A compte, cas 11 ; essai direct 13)', () => {
  const a = morceau('rap', 9, { confiance: 0.8 }), b = morceau('rap', 10, { confiance: 0.1 });
  const p = PL.paire(a, b, { avance_s: 60 });
  const ch = C.choisir(p, [], { force: 'C2' });
  assert.equal(ch.transition, 'C2', ch.raison);
  assert.equal(ch.points.bords.grilleB, 'floue');
  assert.notEqual(ch.points.bords.grilleA, 'floue');
  const r = C.replierAuPlan(ch, { avance_s: 60 });
  assert.equal(r.transition, 'C2', r.replis_plan.map((x) => `${x.de}→${x.vers} ${x.raison}`).join(' ; '));
  // grille de A floue à la revérification : C2 ne tient plus
  assert.notEqual(C.replierAuPlan(ch, { avance_s: 60, grille: { a: 'floue', b: 'floue' } }).transition, 'C2');
});

test('C7 : deux bords instrumentaux, même tonalité, tempos proches ; 16 mesures si possible', () => {
  const h1 = morceau('house', 21, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124, outro: 32 });
  const h2 = morceau('house', 22, { cle: 7, mode: 1, cleConf: 0.9, tempo: 124.5, intro: 32 });
  const p = PL.paire(h1, h2, { avance_s: 120, voixA: instru, voixB: instru });
  assert.equal(p.profil, 'long');
  const ch = C.choisir(p, [], { force: 'C7' });
  assert.equal(ch.transition, 'C7');
  assert.equal(ch.points.T, 16);
  const o = C.ordre(ch, p, { t_wall: T0 });
  assert.deepEqual(C.valider(o, T0), []);
  assert.equal(o.bars, 16);
  // bords vocaux : C7 refusé, repli au plan vers C5 (premier repli éligible) consigné
  const v = PL.paire(morceau('rap', 23, { tempo: 95, cle: 0, mode: 1, cleConf: 0.9, outro: 0 }),
    morceau('rap', 24, { tempo: 95.5, cle: 0, mode: 1, cleConf: 0.9, intro: 0 }), { avance_s: 120 });
  const f = C.choisir(v, [], { force: 'C7' });
  assert.equal(f.choisie, 'C7');
  assert.notEqual(f.transition, 'C7');
  assert.equal(f.replis_plan[0].de, 'C7');
  assert.equal(f.replis_plan[0].ou, 'plan');
  assert.deepEqual(C.valider(C.ordre(f, v, { t_wall: T0 }), T0), []);
});

test('C6 : refusé si l\'intro de B est chantée ; C4 : ΔE ≥ +2, refrain proche, mesure bouclée sans voix', () => {
  const a = morceau('rap', 31, { tempo: 96, cle: 0, mode: 1, cleConf: 0.9 });
  const b = morceau('rap', 32, { tempo: 96.5, intro: 8, voixIntro: true, cle: 0, mode: 1, cleConf: 0.9 });
  const ch = C.choisir(PL.paire(a, b, { avance_s: 90 }), [], { rng: C.rng(1) });
  assert.match(String(ch.refus.C6), /voix|Camelot|tempo|sortie/);
  // B : intro calme, couplet court, refrain fort à 16 mesures (≤ 45 s) ; A finit par une outro sans voix
  const a2 = fabriquer({ tempo: 100, graine: 4, sections: [S(8, -14), S(16, -8, true), S(8, -5, true), S(16, -8, true),
    S(8, -5, true), S(16, -8, true), S(8, -5, true), S(8, -15)] });
  const b2 = fabriquer({ tempo: 100, graine: 5, sections: [S(8, -16), S(8, -9, true), S(8, -3, true), S(16, -9, true),
    S(8, -3, true), S(16, -9, true), S(8, -3, true), S(8, -16)] });
  const p2 = PL.paire(a2, b2, { avance_s: 60 });
  const c4 = C.REGLES.C4.points(p2, C.contexte([]));
  assert.equal(C.REGLES.C4.eligible(p2, c4, C.contexte([])), true);
  assert.equal(c4.typeEntree, 'E2');
  // quota E2 atteint : C4 inéligible
  assert.notEqual(C.REGLES.C4.eligible(p2, c4, C.contexte([{ transition: 'C1', entree: 'E2' }])), true);
});

test('repli au plan : l\'avance tombe juste avant le saut', () => {
  const h1 = morceau('house', 41, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124, outro: 16 });
  const h2 = morceau('house', 42, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124, intro: 16 });
  const p = PL.paire(h1, h2, { avance_s: 90, voixA: instru, voixB: instru });
  const ch = C.choisir(p, [], { force: 'C7' });
  assert.equal(ch.transition, 'C7');
  const r = C.replierAuPlan(ch, { avance_s: 22 });   // C5 : 6 × 1,94 + 8 ≈ 19,6 s passe ; C7 non
  assert.equal(r.transition, 'C5');
  assert.equal(r.choisie, 'C7');
  assert.deepEqual(r.replis_plan.map((x) => [x.de, x.vers, x.ou]), [['C7', 'C5', 'plan']]);
  assert.equal(r.points.sortie.t, ch.points.sortie.t, 'la sortie ne bouge pas');
  assert.equal(r.points.entree.cible_mesure, ch.points.entree.cible_mesure, 'même cible dans B');
  assert.equal(r.points.entree.mesure, ch.points.entree.cible_mesure - 2);
  assert.deepEqual(C.valider(C.ordre(r, null, { t_wall: T0 }), T0), []);
  const r2 = C.replierAuPlan(ch, { avance_s: 5 });
  assert.ok(['R2'].includes(r2.transition));
  assert.ok(r2.points.sortie.t > ch.points.sortie.t, 'R2 : A va jusqu\'à sa fin');
  assert.deepEqual(C.valider(C.ordre(r2, null, { t_wall: T0 }), T0), []);
  assert.equal(C.replierAuPlan(ch, { avance_s: 90 }), ch, 'avance suffisante : rien ne change');
});

test('même graine → même choix ; transition forcée inconnue → erreur', () => {
  const lib = bibliotheque(10, 5);
  const p = PL.paire(lib[0], lib[1], { avance_s: 60 });
  assert.equal(C.choisir(p, [], { rng: C.rng(7) }).transition, C.choisir(p, [], { rng: C.rng(7) }).transition);
  assert.ok(C.choisir(p, [], { force: 'melange' }).erreur);
});

test('ordre de rattrapage valide (R1, manuel, grilles et voix vides)', () => {
  const a = morceau('rap', 51), b = morceau('rap', 52);
  const o = C.ordreRattrapage(a, b, { t_wall: T0, to_uri: 'spotify:track:1YKIUWyelwdDfeKzwSTBn1', uriA: a.uri });
  assert.deepEqual(C.valider(o, T0), []);
  assert.equal(o.transition, 'R1');
  assert.deepEqual(o.replis, ['R2']);
  assert.equal(o.a.sortie_s, null);
  assert.equal(o.b.entree_s, 0);
});

test('valider : ancien champ mode, transition inconnue, bars incohérent → erreurs', () => {
  const lib = bibliotheque(4, 9);
  const p = PL.paire(lib[0], lib[1], { avance_s: 60 });
  const o = C.ordre(C.choisir(p, [], { rng: C.rng(1) }), p, { t_wall: T0 });
  assert.ok(C.valider({ ...o, mode: 'melange' }, T0).length);
  assert.ok(C.valider({ ...o, transition: 'montee' }, T0).includes('transition'));
  assert.ok(C.valider({ ...o, transition: 'C7', bars: 4 }, T0).includes('bars'));
  assert.ok(C.valider({ ...o, t_wall: T0 - 60000 }, T0).includes('t_wall'));
});

test('identifiants : mêmes ids et mêmes T permis que dj-catalogue.js', () => {
  let cat;
  try { cat = require('../dj-catalogue.js'); } catch { return; }
  for (const id of C.IDS) {
    assert.ok(cat.CATALOGUE[id], id);
    assert.deepEqual(cat.CATALOGUE[id].bars, C.BARS_PERMIS[id], id);
    assert.deepEqual(C.REGLES[id].bars, C.BARS_PERMIS[id], id);
  }
  assert.deepEqual([...cat.JOUABLES].sort(), [...C.IDS].sort());
});

test('avance requise = (2 T + 2) × bar_s + 8 s pour une superposition (même règle que catalogue.py)', () => {
  assert.equal(C.avanceRequise(0, 2), 0);
  assert.equal(C.avanceRequise(16, 2), 76);
  assert.equal(C.avanceRequise(2, 2), 20);
  assert.equal(C.avanceRequise(1, 2), 16);
  // C7 sur 16 mesures à 124 BPM : 44 s d'avance ne suffisent plus (≈ 71 s requises)
  const h1 = morceau('house', 91, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124, outro: 32 });
  const h2 = morceau('house', 92, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124, intro: 32 });
  const court = C.choisir(PL.paire(h1, h2, { avance_s: 44, voixA: instru, voixB: instru }), [], { force: 'C7' });
  assert.ok(!(court.transition === 'C7' && court.points.T === 16), `${court.transition} T=${court.points?.T}`);
  const long = C.choisir(PL.paire(h1, h2, { avance_s: 75, voixA: instru, voixB: instru }), [], { force: 'C7' });
  assert.equal(long.transition, 'C7');
  assert.equal(long.points.T, 16);
  assert.ok(C.avanceRequise(16, long.points.bords.barA) > 44);
});

test('cible sur un début de section de B (§3) pour C5, C7, R1, y compris sans entrée E1', () => {
  const lib = bibliotheque(60, 12);
  let vus = 0;
  for (let i = 0; i + 1 < lib.length; i++) {
    const p = PL.paire(lib[i], lib[i + 1], { avance_s: 200 });
    for (const id of ['C5', 'C7', 'R1']) {
      for (const T of C.REGLES[id].bars) {
        const pts = C.points(p, T, 'section');
        if (pts.raison) continue;
        vus++;
        const b = p.b.analyse;
        const c = b.bars[pts.entree.cible_mesure].start;
        assert.ok(b.sections.some((s) => s.start > 0 && Math.abs(s.start - c) < 0.15), `${id} T=${T} : cible ${c} hors section`);
        assert.equal(pts.entree.cible_mesure - pts.entree.mesure, T);
      }
    }
  }
  assert.ok(vus > 50, `${vus}`);
  // B dont la seule section après l'intro est trop tôt pour T = 16 : plus de cible E0 + T, pas de point
  const b = fabriquer({ tempo: 120, sections: [S(4, -14), S(40, -8, true)] });
  const p = PL.paire(morceau('rap', 93), b, { avance_s: 200 });
  assert.ok(C.points(p, 16, 'section').raison);
});

test('R2 : sortie au moins 1 s avant la fin du morceau', () => {
  for (const a of bibliotheque(10, 13).concat([fabriquer({ sections: [S(32, -8, true)], silenceFin: 0 })])) {
    const r = C.REGLES.R2.points(PL.paire(a, morceau('rap', 94), { contexte: 'album' }));
    assert.ok(r.sortie.t <= a.track.duration - C.R2_MARGE_S + 1e-9, `${r.sortie.t} / ${a.track.duration}`);
  }
});
