// Voix au plan (dj-voix.js, ADR 0002) : V2 sur segments, paroles V1 derrière drapeau, cas sans segments.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const V = require('../dj-voix.js');
const { fabriquer, paroles } = require('./fixtures/fabrique.js');

const sections = [{ mesures: 8, sonie: -13, voix: false }, { mesures: 16, sonie: -8, voix: true },
  { mesures: 8, sonie: -6, voix: true }, { mesures: 8, sonie: -12, voix: false }, { mesures: 16, sonie: -8, voix: true },
  { mesures: 8, sonie: -14, voix: false }];
const verite = sections.flatMap((s) => new Array(s.mesures).fill(s.voix));

test('V2 sépare mesures vocales et instrumentales (analyses factices, plusieurs graines)', () => {
  let vp = 0, fp = 0, fn = 0, sansVoixOk = 0, nInstru = 0;
  for (let g = 1; g <= 8; g++) {
    const a = fabriquer({ tempo: 90 + g * 5, sections, graine: g });
    const s = V.scoresV2(a);
    assert.equal(s.length, a.bars.length);
    s.forEach((x, i) => {
      assert.ok(x >= 0 && x <= 1);
      const vocal = x >= V.SEUIL_VOCAL;
      if (vocal && verite[i]) vp++; else if (vocal) fp++; else if (verite[i]) fn++;
      if (!verite[i]) { nInstru++; if (x < V.SEUIL_SANS_VOIX) sansVoixOk++; }
    });
  }
  const precision = vp / (vp + fp), rappel = vp / (vp + fn);
  assert.ok(precision >= 0.9, `précision ${precision}`);
  assert.ok(rappel >= 0.9, `rappel ${rappel}`);
  assert.ok(sansVoixOk / nInstru >= 0.9, `sans voix ${sansVoixOk / nInstru}`);
});

test('voixSegments : 16 mesures avant (la dernière en dernier) ou après un point', () => {
  const a = fabriquer({ tempo: 120, sections, graine: 3 });
  const t = a.bars[24].start;   // début de la 3ᵉ section (vocale), après 8 instrumentales et 16 vocales
  const avant = V.voixSegments(a, t, 16, 'avant');
  assert.equal(avant.length, 16);
  assert.ok(avant.at(-1) >= V.SEUIL_VOCAL);
  const apres = V.voixSegments(a, a.bars[32].start, 16, 'apres');
  assert.equal(apres.length, 16);
  assert.ok(apres.slice(0, 8).every((x) => x < V.SEUIL_SANS_VOIX));
  assert.ok(apres.slice(8).every((x) => x >= V.SEUIL_VOCAL));
  // début de morceau : moins de 16 mesures disponibles avant
  assert.equal(V.voixSegments(a, a.bars[3].start, 16, 'avant').length, 3);
});

test('sans segments : toutes les mesures à 1, source « aucune »', () => {
  const a = fabriquer({ tempo: 100, sections, segments: false });
  const r = V.voixBord(a, null, a.bars[10].start, 16, 'apres');
  assert.equal(r.source, 'aucune');
  assert.equal(r.valeurs.length, 16);
  assert.ok(r.valeurs.every((x) => x === 1));
});

test('mesures silencieuses : score 0', () => {
  const a = fabriquer({ tempo: 100, sections: [{ mesures: 4, sonie: -70, voix: false }, ...sections] });
  assert.ok(V.scoresV2(a).slice(0, 4).every((x) => x === 0));
});

test('parserParoles : lignes synchronisées, fin bornée à 8 s, ♪ et vides instrumentales', () => {
  const l = V.parserParoles(paroles([[10, 'Première ligne'], [12.5, '♪'], [13, 'deux'], [40, 'loin'], [41, '']]));
  assert.deepEqual(l.map((x) => [x.debut_s, x.fin_s, x.vide]),
    [[10, 12.5, false], [12.5, 13, true], [13, 21, false], [40, 41, false], [41, 49, true]]);
  assert.equal(V.parserParoles(paroles([[1, 'a']], 'UNSYNCED')), null);
  assert.equal(V.parserParoles(null), null);
  assert.equal(V.parserParoles({ lyrics: { syncType: 'LINE_SYNCED', lines: [{ startTimeMs: 'x', words: 'a' }] } }), null);
  assert.equal(V.parserParoles({ autre: 1 }), null);
});

test('voixParoles : part de la mesure couverte par une ligne non vide', () => {
  const l = V.parserParoles(paroles([[1, 'a'], [3, '♪'], [5, 'b']]));
  const m = [{ start: 0, duration: 2 }, { start: 2, duration: 2 }, { start: 4, duration: 2 }, { start: 14, duration: 2 }];
  assert.deepEqual(V.voixParoles(l, m), [0.5, 0.5, 0.5, 0]);
  const a = fabriquer({ tempo: 120, sections, graine: 2 });
  const r = V.voixBord(a, l, a.bars[0].start, 4, 'apres');
  assert.equal(r.source, 'paroles');
  assert.equal(r.valeurs.length, 4);
});

test('chargerParoles : éteint par défaut, cache, tout échec → null', async () => {
  let appels = 0;
  const store = {};
  globalThis.Spicetify = {
    LocalStorage: { get: (k) => store[k] ?? null },
    CosmosAsync: { get: async (url) => { appels++; if (url.includes('ZZZZ')) throw new Error('404'); return paroles([[1, 'a'], [2, 'b']]); } },
  };
  try {
    const u = 'spotify:track:1bepxgCj8gKHOmoSGiW5J3';
    assert.equal(await V.chargerParoles(u), null);
    assert.equal(appels, 0);
    store[V.DRAPEAU] = '1';
    const l = await V.chargerParoles(u);
    assert.equal(l.length, 2);
    await V.chargerParoles(u);
    assert.equal(appels, 1);
    assert.equal(await V.chargerParoles('spotify:track:ZZZZZZZZZZZZZZZZZZZZZZ'), null);
    assert.equal(await V.chargerParoles('pas une uri'), null);
  } finally { delete globalThis.Spicetify; }
});
