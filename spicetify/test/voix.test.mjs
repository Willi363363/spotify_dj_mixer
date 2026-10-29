// Voix au plan (dj-voix.js, ADR 0002) : V2 sur segments, paroles V1 derrière drapeau, cas sans segments.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const V = require('../dj-voix.js');
const { fabriquer, paroles } = require('./fixtures/fabrique.js');
const REELS = require('./fixtures/voix-reelle.js');

const sections = [{ mesures: 8, sonie: -13, voix: false }, { mesures: 16, sonie: -8, voix: true },
  { mesures: 8, sonie: -6, voix: true }, { mesures: 8, sonie: -12, voix: false }, { mesures: 16, sonie: -8, voix: true },
  { mesures: 8, sonie: -14, voix: false }];
const verite = sections.flatMap((s) => new Array(s.mesures).fill(s.voix));

const auc = (scores, verite) => {
  const pos = scores.filter((_, i) => verite[i]), neg = scores.filter((_, i) => !verite[i]);
  let n = 0;
  for (const p of pos) for (const q of neg) n += p > q ? 1 : p === q ? 0.5 : 0;
  return n / (pos.length * neg.length);
};

test('V2 sur 5 vrais morceaux tenus à l\'écart de l\'ajustement (caractéristiques dérivées, vérité = paroles)', () => {
  const s = [], v = [];
  for (const m of REELS) {
    const sc = V.scoresCaracteristiques({ lignes: m.car, actif: m.actif.map(Boolean) });
    assert.equal(sc.length, m.voix.length);
    // portage figé : mêmes scores qu'à l'ajustement (caractéristiques arrondies à 0,01 près)
    sc.forEach((x, i) => assert.ok(Math.abs(x - m.v2_attendu[i]) < 0.03, `${m.genre} mesure ${i} : ${x} ≠ ${m.v2_attendu[i]}`));
    s.push(...sc); v.push(...m.voix.map(Boolean));
  }
  const sansVoix = s.map((x) => x < V.SEUIL_SANS_VOIX), vocal = s.map((x) => x >= V.SEUIL_VOCAL);
  const precSans = v.filter((x, i) => sansVoix[i] && !x).length / sansVoix.filter(Boolean).length;
  const precVoc = v.filter((x, i) => vocal[i] && x).length / vocal.filter(Boolean).length;
  const rapVoc = v.filter((x, i) => vocal[i] && x).length / v.filter(Boolean).length;
  assert.ok(auc(s, v) >= 0.9, `AUC ${auc(s, v)}`);
  assert.ok(precSans >= 0.7, `« sans voix » juste ${precSans}`);
  assert.ok(precVoc >= 0.9 && rapVoc >= 0.9, `vocal : précision ${precVoc}, rappel ${rapVoc}`);
});

test('V2 sur analyses factices : mesures chantées vocales, mesures instrumentales plus basses, « sans voix » jamais faux', () => {
  let vp = 0, fn = 0, sansFaux = 0, sansTotal = 0;
  const s = [], v = [];
  for (let g = 1; g <= 8; g++) {
    const a = fabriquer({ tempo: 90 + g * 5, sections, graine: g });
    const sc = V.scoresV2(a);
    assert.equal(sc.length, a.bars.length);
    sc.forEach((x, i) => {
      assert.ok(x >= 0 && x <= 1);
      if (verite[i]) { if (x >= V.SEUIL_VOCAL) vp++; else fn++; }
      if (x < V.SEUIL_SANS_VOIX) { sansTotal++; if (verite[i]) sansFaux++; }
    });
    s.push(...sc); v.push(...verite);
  }
  assert.ok(vp / (vp + fn) >= 0.9, `rappel vocal ${vp / (vp + fn)}`);
  assert.ok(auc(s, v) >= 0.9, `AUC ${auc(s, v)}`);
  assert.equal(sansFaux, 0, `${sansFaux} mesures chantées jugées sans voix sur ${sansTotal}`);
});

test('voixSegments : 16 mesures avant (la dernière en dernier) ou après un point', () => {
  const a = fabriquer({ tempo: 120, sections, graine: 3 });
  const t = a.bars[24].start;   // début de la 3ᵉ section (vocale), après 8 instrumentales et 16 vocales
  const avant = V.voixSegments(a, t, 16, 'avant');
  assert.equal(avant.length, 16);
  assert.deepEqual(avant, V.scoresV2(a).slice(8, 24));
  assert.ok(avant.at(-1) >= V.SEUIL_VOCAL);
  const apres = V.voixSegments(a, a.bars[32].start, 16, 'apres');
  assert.equal(apres.length, 16);
  const moy = (x) => x.reduce((p, q) => p + q, 0) / x.length;
  assert.ok(moy(apres.slice(0, 8)) < moy(apres.slice(8)) - 0.2);
  assert.ok(apres.slice(10).every((x) => x >= V.SEUIL_VOCAL));
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

test('voixParoles (V1) : 0 sans ligne ; sinon part couverte, au moins SEUIL_SANS_VOIX (trois zones)', () => {
  const l = V.parserParoles(paroles([[1, 'a'], [3, '♪'], [5, 'b'], [20, 'c']]));
  const m = [{ start: 0, duration: 2 }, { start: 2, duration: 2 }, { start: 4, duration: 2 }, { start: 14, duration: 2 },
    { start: 19.95, duration: 2 }, { start: 18, duration: 1.95 }, { start: 12.5, duration: 2 }, { start: 19.95, duration: 0.15 }];
  // [5 ; 13] : 3e à moitié, 7e sur 0,5 s (part 0,25 → 0,3 : ni sans voix ni vocale) ; 4e [14 ; 16] au-delà des 8 s ;
  // 50 ms de ligne (19,95 → 20) ne suffisent pas à la 6e ; la 8e (150 ms) est recouverte sur 100 ms, sa moitié
  assert.deepEqual(V.voixParoles(l, m), [0.5, 0.5, 0.5, 0, 0.975, 0, 0.3, 0.667]);
  const v = V.voixParoles(l, m);
  assert.ok(v[6] >= V.SEUIL_SANS_VOIX && v[6] < V.SEUIL_VOCAL);
  const a = fabriquer({ tempo: 120, sections, graine: 2 });
  const r = V.voixBord(a, l, a.bars[0].start, 4, 'apres');
  assert.equal(r.source, 'paroles');
  assert.equal(r.valeurs.length, 4);
  // paroles factices de fabrique : la vérité des sections est retrouvée exactement
  const v1 = V.voixParoles(V.parserParoles(a.paroles), a.bars);
  assert.deepEqual(v1.map((x) => x >= V.SEUIL_VOCAL), verite);
  assert.deepEqual(v1.map((x) => x < V.SEUIL_SANS_VOIX), verite.map((x) => !x));
});

// Faux Spicetify : LocalStorage en mémoire, CosmosAsync programmable ; journal des requêtes (heure, id)
function fauxSpicetify(repondre) {
  const store = {}, journal = [];
  globalThis.Spicetify = {
    LocalStorage: { get: (k) => store[k] ?? null, set: (k, v) => { store[k] = String(v); } },
    CosmosAsync: { get: async (url) => { const id = /track\/(\w+)/.exec(url)[1]; journal.push([Date.now(), id]); return repondre(id); } },
  };
  return { store, journal };
}
const U = (c) => `spotify:track:${c.repeat(22)}`;

test('chargerParoles : allumé par défaut, éteint par « 0 », cache LocalStorage qui survit à un redémarrage', async () => {
  V.reinitialiser();
  V.reglerFile({ espacement_ms: 20, attente_max_ms: 1000 });
  const { store, journal } = fauxSpicetify((id) => (id.startsWith('Z') ? { code: 404, message: 'Failed to fetch' }
    : paroles([[1, 'a'], [2, 'b']])));
  try {
    const l = await V.chargerParoles(U('A'));
    assert.equal(l.length, 2);
    assert.equal(journal.length, 1);
    assert.equal(await V.chargerParoles(U('Z')), null);              // 404 : pas de paroles, mis en cache
    V.reinitialiser();                                               // redémarrage de Spotify : seul le LocalStorage reste
    assert.ok(store[V.CLE_CACHE]);
    assert.deepEqual((await V.chargerParoles(U('A'))).map((x) => x.vide), [false, false]);
    assert.equal(await V.chargerParoles(U('Z')), null);
    assert.equal(journal.length, 2, 'aucune nouvelle requête : tout vient du cache');
    store[V.DRAPEAU] = '0';
    assert.equal(await V.chargerParoles(U('B')), null);
    assert.equal(journal.length, 2);
    assert.equal(await V.chargerParoles('pas une uri'), null);
  } finally { delete globalThis.Spicetify; V.reinitialiser(); }
});

test('chargerParoles : file espacée, back-off sur 429 (repli V2 immédiat), délai d\'attente', async () => {
  V.reinitialiser();
  V.reglerFile({ espacement_ms: 40, attente_max_ms: 1000, backoff_min_ms: 150, backoff_max_ms: 1000 });
  let limite = false, lent = false;
  const { journal } = fauxSpicetify(async (id) => {
    if (lent) await new Promise((r) => setTimeout(r, 120));
    return limite ? { code: 429, message: 'Too Many Requests' } : paroles([[1, id]]);
  });
  try {
    // 4 morceaux demandés ensemble : une requête toutes les 40 ms au moins
    const r = await Promise.all(['A', 'B', 'C', 'D'].map((c) => V.chargerParoles(U(c))));
    assert.ok(r.every((x) => x?.length === 1));
    for (let i = 1; i < journal.length; i++) assert.ok(journal[i][0] - journal[i - 1][0] >= 35, 'espacement');
    // 429 : null (→ V2), puis pause : les demandes suivantes ne partent pas
    limite = true;
    assert.equal(await V.chargerParoles(U('E')), null);
    const n = journal.length;
    assert.equal(await V.chargerParoles(U('F')), null);
    assert.equal(journal.length, n, 'en pause après un 429 : pas de requête');
    assert.ok(V.etatParoles().pause_s >= 0 && V.etatParoles().limite === 1);
    await new Promise((r) => setTimeout(r, 200));                   // fin de la pause (150 ms)
    limite = false;
    assert.equal((await V.chargerParoles(U('E'))).length, 1, 'après la pause, la requête repart');
    // attente plafonnée : null tout de suite, mais la requête continue et remplit le cache
    lent = true;
    assert.equal(await V.chargerParoles(U('G'), { attenteMax: 30 }), null);
    await new Promise((r) => setTimeout(r, 250));
    const avant = journal.length;
    assert.equal((await V.chargerParoles(U('G'))).length, 1);
    assert.equal(journal.length, avant, 'servi par le cache');
  } finally { delete globalThis.Spicetify; V.reinitialiser(); V.reglerFile({ espacement_ms: 3000, attente_max_ms: 8000,
    backoff_min_ms: 30000, backoff_max_ms: 600000 }); }
});

test('coupeLigne, finDeLigne : une ligne chantée à t coupe ; fin chantée ≤ 0,45 s par mot ; tolérance 100 ms', () => {
  // ligne de 2 mots à 10 s (fin chantée 10,9 s, fin « au suivant » 18 s), ♪ à 18 s, ligne à 20 s
  const l = V.parserParoles(paroles([[10, 'deux mots'], [18, '♪'], [20, 'un deux trois quatre cinq six sept huit neuf dix']]));
  assert.deepEqual(l.map((x) => x.chant_s), [10.9, 18.45, 24.5]);
  assert.equal(V.coupeLigne(l, 10.5), true);
  assert.equal(V.coupeLigne(l, 12), false, 'fin chantée passée : la queue estimée ne compte pas');
  assert.equal(V.coupeLigne(l, 18.2), false, '♪ ne compte pas');
  assert.equal(V.coupeLigne(l, 20.05), false, 'ligne qui commence à t (±100 ms) : pas coupée');
  assert.equal(V.coupeLigne(l, 20.2), true);
  assert.equal(V.coupeLigne(l, 24.45), false, 'fin à t (±100 ms)');
  assert.equal(V.coupeLigne(null, 12), null);
  assert.equal(V.finDeLigne(l, 12, 2), true);
  assert.equal(V.finDeLigne(l, 14, 2), false);
  assert.equal(V.finDeLigne([], 14, 2), null);
});

test('chargerParoles : 429 et 401 sous toutes leurs formes → pause, jamais mis en cache ; 404 → absent en cache', async () => {
  assert.equal(V.statutHttp({ error: { status: 429 } }), 429);
  assert.equal(V.statutHttp({ code: 404, message: 'Failed to fetch' }), 404);
  assert.equal(V.statutHttp(new Error('Request failed with status 401')), 401);
  assert.equal(V.statutHttp({ status: '503' }), 503);
  assert.equal(V.statutHttp({ lyrics: {} }), null);
  for (const forme of [{ error: { status: 429 } }, { error: { status: 401, message: 'Unauthorized' } }, { status: 503 },
    'throw401']) {
    V.reinitialiser();
    V.reglerFile({ espacement_ms: 5, attente_max_ms: 1000, backoff_min_ms: 80, backoff_max_ms: 1000 });
    let n = 0;
    const { store, journal } = fauxSpicetify(() => {
      if (n++ === 0) { if (forme === 'throw401') throw new Error('HTTP 401'); return forme; }
      return paroles([[1, 'a']]);
    });
    try {
      assert.equal(await V.chargerParoles(U('A')), null, JSON.stringify(forme));
      assert.ok(!store[V.CLE_CACHE] || !JSON.parse(store[V.CLE_CACHE])[U('A').slice(-22)], 'pas en cache');
      assert.ok(V.etatParoles().pause_s >= 0 && V.etatParoles().requetes === 1);
      assert.equal(await V.chargerParoles(U('A')), null, 'en pause : pas de requête');
      assert.equal(journal.length, 1);
      await new Promise((r) => setTimeout(r, 120));
      assert.equal((await V.chargerParoles(U('A'))).length, 1, 'après la pause, la requête repart');
    } finally { delete globalThis.Spicetify; }
  }
  // erreur réseau sans statut : passagère, ni cache ni pause ; 404 : absent mis en cache
  V.reinitialiser();
  const { store } = fauxSpicetify((id) => { if (id.startsWith('N')) throw new Error('Failed to fetch'); return { code: 404 }; });
  try {
    assert.equal(await V.chargerParoles(U('N')), null);
    assert.equal(await V.chargerParoles(U('Z')), null);
    const c = JSON.parse(store[V.CLE_CACHE]);
    assert.deepEqual(Object.keys(c), ['Z'.repeat(22)]);
    assert.equal(c['Z'.repeat(22)][1], null);
    assert.equal(V.etatParoles().pause_s, 0);
  } finally { delete globalThis.Spicetify; V.reinitialiser(); V.reglerFile({ espacement_ms: 3000, attente_max_ms: 8000,
    backoff_min_ms: 30000, backoff_max_ms: 600000 }); }
});

test('cache des paroles : entrée corrompue réparée, éviction de la moins récemment utilisée, paroles expirées', async () => {
  V.reinitialiser();
  V.reglerFile({ espacement_ms: 1, attente_max_ms: 1000, cache_max: 2, present_ttl_ms: 30 * 86400000 });
  let panne = false;
  const { store, journal } = fauxSpicetify((id) => (panne ? { error: { status: 500 } } : paroles([[1, id.slice(0, 1)], [3, 'b']])));
  const id = (c) => c.repeat(22), pause = (ms) => new Promise((r) => setTimeout(r, ms));
  try {
    // corrompue : e[1] n'est pas un tableau, ou une ligne illisible → supprimée et redemandée
    store[V.CLE_CACHE] = JSON.stringify({ [id('A')]: [Date.now(), 'x'], [id('B')]: [Date.now(), [[1, 'z', 0]]] });
    assert.equal((await V.chargerParoles(U('A'))).length, 2);
    assert.equal((await V.chargerParoles(U('B'))).length, 2);
    assert.equal(journal.length, 2);
    assert.equal(V.etatParoles().repare, 2);
    assert.ok(Array.isArray(JSON.parse(store[V.CLE_CACHE])[id('A')][1]));
    // LRU : A écrit avant B, mais relu après ; C entre → B (la moins récemment utilisée) sort, pas A
    await pause(5); await V.chargerParoles(U('A')); await pause(5);
    await V.chargerParoles(U('C'));
    V.reinitialiser();
    V.reglerFile({ espacement_ms: 1, attente_max_ms: 1000, cache_max: 2 });
    assert.deepEqual(Object.keys(JSON.parse(store[V.CLE_CACHE])).sort(), [id('A'), id('C')]);
    // paroles présentes expirées : redemandées ; servies telles quelles si la nouvelle requête échoue
    V.reglerFile({ present_ttl_ms: 1 });
    await pause(5);
    const n = journal.length;
    panne = true;
    assert.equal((await V.chargerParoles(U('C'))).length, 2, 'ancienne version servie pendant la panne');
    assert.equal(journal.length, n + 1, 'mais redemandée');
    V.reinitialiser(); await pause(5);
    panne = false;
    assert.equal((await V.chargerParoles(U('C'))).length, 2);
    assert.equal(journal.length, n + 2);
  } finally { delete globalThis.Spicetify; V.reinitialiser(); V.reglerFile({ espacement_ms: 3000, attente_max_ms: 8000,
    backoff_min_ms: 30000, backoff_max_ms: 600000, cache_max: 600, present_ttl_ms: 30 * 86400000 }); }
});
