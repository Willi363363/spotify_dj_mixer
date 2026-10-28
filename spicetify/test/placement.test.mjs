// Placement (dj-placement.js, §5) sur analyses factices : phrases, grille, sections, sorties et garde-fou O1,
// entrées E0/E1/E2, ΔE, profils, tonalité et tempo.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const PL = require('../dj-placement.js');
const V = require('../dj-voix.js');
const { fabriquer } = require('./fixtures/fabrique.js');
const { morceau, bibliotheque } = require('./fixtures/bibliotheque.js');

const S = (mesures, sonie, voix = false) => ({ mesures, sonie, voix });

test('mesures : rang dans la section et phrases de 8, à défaut 4', () => {
  const a = fabriquer({ sections: [S(6, -12), S(16, -8, true)] });
  const m = PL.mesures(a);
  assert.deepEqual(m.slice(0, 8).map((x) => [x.section, x.k, x.phrase]),
    [[0, 0, 8], [0, 1, 0], [0, 2, 0], [0, 3, 0], [0, 4, 4], [0, 5, 0], [1, 0, 8], [1, 1, 0]]);
  assert.equal(m[14].phrase, 8);
});

test('grille : nette, moyenne, floue (§5.2)', () => {
  const sec = [S(40, -8, true)];
  assert.equal(PL.grille(fabriquer({ sections: sec, confiance: 0.7, gigue: 0.004 }), 30), 'nette');
  assert.equal(PL.grille(fabriquer({ sections: sec, confiance: 0.4, gigue: 0.004 }), 30), 'moyenne');
  assert.equal(PL.grille(fabriquer({ sections: sec, confiance: 0.7, gigue: 0.07 }), 30), 'moyenne');
  assert.equal(PL.grille(fabriquer({ sections: sec, confiance: 0.1 }), 30), 'floue');
  assert.equal(PL.grille(fabriquer({ sections: sec, confiance: 0.7, gigue: 0.2 }), 30), 'floue');
});

test('sectionsA : dernière section pleine et début de l\'outro', () => {
  const a = fabriquer({ sections: [S(8, -14), S(16, -8, true), S(8, -6, true), S(16, -8, true), S(8, -6, true), S(8, -16)] });
  const r = PL.sectionsA(a);
  assert.equal(r.dernierePleine.i, 4);
  assert.ok(Math.abs(r.outro_s - a.sections[5].start) < 0.01);
});

test('sorties : sur une frontière de phrase, au début de l\'outro, garde-fou O1', () => {
  for (const a of bibliotheque(20, 7)) {
    const dur = a.track.duration, fin = PL.finEffective(a);
    for (const T of [0, 2, 4, 8]) {
      const s = PL.sorties(a, { T });
      if (!s.length) continue;
      const x = s[0];
      const m = PL.mesures(a)[x.mesure];
      assert.ok(m.phrase >= 4, 'frontière de phrase');
      assert.ok(x.t <= dur - PL.FIN_MIN_S);
      if (!x.repli) {
        assert.ok(x.jamais_entendu_s <= 30 && x.jamais_entendu_s <= 0.15 * dur, `O1 ${x.jamais_entendu_s}`);
        assert.ok(x.t >= PL.sectionsA(a).outro_s - 0.1);
      }
      assert.ok(Math.abs(x.jamais_entendu_s - Math.max(0, fin - x.t)) < 0.01);
    }
  }
});

test('garde-fou : une longue outro n\'est pas coupée de plus de 30 s', () => {
  // outro de 32 mesures à 100 BPM = 77 s : la sortie se fait dans l'outro, ≤ 30 s avant la fin
  const a = fabriquer({ tempo: 100, sections: [S(8, -14), S(16, -8, true), S(8, -5, true), S(16, -8, true), S(8, -5, true),
    S(16, -8, true), S(8, -5, true), S(32, -16)] });
  const s = PL.sorties(a, {})[0];
  assert.ok(s.t > PL.sectionsA(a).outro_s);
  assert.ok(s.jamais_entendu_s <= 30);
  assert.equal(s.repli, false);
});

test('garde-fou : aucune sortie possible → la phrase la plus tardive avant les 6 dernières s, ou rien', () => {
  const a = fabriquer({ tempo: 100, sections: [S(8, -14), S(16, -8, true), S(8, -5, true), S(16, -8, true), S(8, -5, true)],
    silenceFin: 0.5 });
  const s = PL.sorties(a, {});
  assert.equal(s.length, 1);
  assert.equal(s[0].repli, true);
  assert.ok(s[0].t <= a.track.duration - 6);
  assert.deepEqual(PL.sorties(a, { minExit_s: a.track.duration }), []);
});

test('sorties : minExit respecté, voix sur la dernière mesure → décalage d\'une demi-phrase', () => {
  const v = Array.from({ length: 16 }, (_, i) => i < 2);   // outro : 2 mesures encore chantées
  const a = fabriquer({ tempo: 140, sections: [S(8, -14), S(16, -8, true), S(8, -5, true), S(16, -8, true), S(8, -5, true),
    S(16, -8, true), S(8, -5, true), S(16, -8, true), S(8, -5, true), S(16, -16, v)] });
  const voixA = (i) => V.voixMesure(a, null, i);
  const s = PL.sorties(a, { voixA });
  assert.equal(s[0].vocale, false);
  const sans = PL.sorties(a, {});
  assert.ok(s[0].t > sans[0].t, 'décalée après la demi-phrase vocale');
  assert.ok(PL.sorties(a, { minExit_s: 1e4 }).length === 0);
});

test('entrées : E0 après le silence, E1 après ≥ 4 mesures, E2 = refrain de la première moitié', () => {
  const b = fabriquer({ tempo: 120, silenceDebut: 1.2, sections: [S(8, -14), S(16, -8, true), S(8, -4, true), S(16, -8, true),
    S(8, -4, true), S(8, -14)] });
  const e = PL.entrees(b, { T: 0 });
  assert.equal(e.E0.mesure, 0);
  assert.ok(e.E0.t >= 1.15);
  assert.equal(e.E1.mesure, 8);
  assert.equal(e.E2.mesure, 24);
  assert.ok(e.E2.saute_s > 40);
  const e4 = PL.entrees(b, { T: 4 });
  assert.equal(e4.E0.mesure, 0);
  assert.equal(e4.E0.cible_mesure, 4);
  assert.equal(e4.E1.mesure, 4);
  assert.equal(e4.E1.cible_mesure, 8);
  assert.equal(PL.entrees(b, { T: 16 }).E1, null, 'cible − T avant le début de B');
  assert.equal(PL.typeEntree(b, e.E0.t), 'E0');
  assert.equal(PL.typeEntree(b, e4.E1.t), 'E1');
  assert.equal(PL.typeEntree(b, e.E2.t), 'E2');
});

test('ΔE : énergie qui monte et qui baisse', () => {
  const a = fabriquer({ sections: [S(16, -8, true), S(8, -16)] });
  const b = fabriquer({ sections: [S(8, -16), S(8, -4, true)] });
  assert.ok(PL.deltaE(a, a.bars[16].start, b, b.bars[8].start) > 2);
  assert.ok(PL.deltaE(a, a.bars[16].start, b, b.bars[0].start) < -2);
});

test('profils de bord et de paire (§5.8)', () => {
  assert.equal(PL.profilBord([0.9, 0.9, ...new Array(8).fill(0.1)], 'avant'), 'instrumental');
  assert.equal(PL.profilBord([0.9, 0.9, ...new Array(8).fill(0.1)], 'apres'), 'vocal');
  assert.equal(PL.profilBord(new Array(7).fill(0.1), 'avant'), 'vocal');
  assert.equal(PL.profilPaire('instrumental', 'instrumental', 124), 'long');
  assert.equal(PL.profilPaire('instrumental', 'instrumental', 95), 'court');
  assert.equal(PL.profilPaire('instrumental', 'vocal', 124), 'court');
});

test('tonalité et tempo : Camelot, moitié/double, rapport 3:2', () => {
  const c = (key, mode, key_confidence = 0.9) => PL.camelot({ key, mode, key_confidence });
  assert.deepEqual(c(0, 1), { n: 8, minor: false });   // do majeur = 8B
  assert.deepEqual(c(9, 0), { n: 8, minor: true });    // la mineur = 8A
  assert.equal(PL.camelotDist(c(0, 1), c(9, 0)), 1);
  assert.equal(PL.camelotDist(c(0, 1), c(7, 1)), 1);    // sol majeur = 9B
  assert.equal(c(0, 1, 0.2), null);
  assert.equal(PL.camelotDist(null, c(0, 1)), null);
  assert.ok(PL.ecartTempo(100, 200) < 1e-9);
  assert.ok(Math.abs(PL.ecartTempo(100, 102) - 0.02) < 1e-9);
  assert.ok(PL.rapport32(104, 156));
  assert.ok(!PL.rapport32(100, 102));
});

test('paire : refus d\'office (album, analyse absente), profil et voix_source', () => {
  const a = morceau('rap', 1), b = morceau('rap', 2);
  assert.equal(PL.paire(a, b, { contexte: 'album' }).refus, 'album joué dans l\'ordre');
  assert.equal(PL.paire(a, { track: {} }, {}).refus, 'analyse absente');
  const p = PL.paire(a, b, { avance_s: 60 });
  assert.equal(p.refus, null);
  assert.equal(p.voix_source, 'segments');
  assert.ok(['court', 'long'].includes(p.profil));
  const h1 = morceau('house', 3, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124 });
  const h2 = morceau('house', 4, { cle: 7, mode: 1, cleConf: 0.9, tempo: 125 });
  // V2 est relatif au morceau : un morceau sans aucune voix n'est pas reconnu instrumental (limite connue, ADR 0002).
  // Avec des paroles vides (instrumental sûr), la paire devient « long ».
  const instru = [{ debut_s: 0, fin_s: 1e4, vide: true }];
  assert.equal(PL.paire(h1, h2, { voixA: instru, voixB: instru }).profil, 'long');
  assert.equal(PL.paire(a, fabriquer({ sections: [S(16, -8, true)], segments: false }), {}).voix_source, 'aucune');
});
