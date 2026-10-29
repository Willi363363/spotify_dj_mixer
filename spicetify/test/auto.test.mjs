// dj-auto.js avec un faux Spicetify et un faux moteur : le mode automatique produit des ordres v2 valides,
// sans la même transition deux fois de suite, avec le garde-fou fin-coupée, le quota refrain, le repli au plan,
// le rattrapage et le forçage (DJ.forcer).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const DJCore = {
  voix: require('../dj-voix.js'), placement: require('../dj-placement.js'), choix: require('../dj-choix.js'),
  catalogue: (() => { try { return require('../dj-catalogue.js'); } catch { return null; } })(),
};
const { creer } = require('../dj-auto.js');
const { bibliotheque, morceau } = require('./fixtures/bibliotheque.js');

// Faux Spotify : horloge virtuelle, lecture d'une file de morceaux, saut par PlayerAPI.play({ seekTo })
function monde(pistes, { avance = () => 60, contexte = 'spotify:playlist:37i9dQZF1DX0000000000000', reserve = null } = {}) {
  const parUri = new Map([...pistes, ...(reserve ?? [])].map((p) => [p.uri, p]));
  let horloge = 1_800_000_000_000;
  const lecture = { uri: pistes[0].uri, debut: horloge, pos0: 0, contexte };
  const file = [...pistes.slice(1)];
  const ordres = [], sauts = [];
  const store = { 'dj-mixer:auto': '1' };
  let auditeur = null;
  const data = () => ({ item: { uri: lecture.uri, name: lecture.uri.slice(-6) }, isPaused: false, context: { uri: lecture.contexte } });
  const S = {
    Player: {
      get data() { return data(); },
      getProgress: () => lecture.pos0 + (horloge - lecture.debut),
      getShuffle: () => false,
      addEventListener: (e, f) => { auditeur = f; },
    },
    Platform: { PlayerAPI: { play: async (quoi, _o, { seekTo, skipTo }) => {
      const vers = skipTo?.uri ?? quoi.uri;
      sauts.push({ de: lecture.uri, vers, contexte: quoi.uri, seekTo, a: S.Player.getProgress() });
      Object.assign(lecture, { uri: vers, debut: horloge, pos0: seekTo, contexte: skipTo ? quoi.uri : vers });
      file.shift();
    } },
    PlaylistAPI: reserve ? { getContents: async () => ({ items: reserve.map((p) => ({ uri: p.uri, name: p.uri.slice(-6), artists: [{ name: 'x' }] })) }) } : undefined },
    getAudioData: async (uri) => parUri.get(uri),
    LocalStorage: { get: (k) => store[k] ?? null, set: (k, v) => { store[k] = v; } },
    get Queue() { return { nextTracks: file.map((p, i) => ({ contextTrack: { uri: p.uri, uid: `uid${i}${p.uri.slice(-4)}`, metadata: { title: p.uri.slice(-6) } } })) }; },
  };
  const fetch = async (url, o = {}) => {
    if (url.endsWith('/state')) return { ok: true, json: async () => ({ delay_s: avance(ordres.length), target_s: 60, busy: false }) };
    if (url.endsWith('/order')) { ordres.push({ ...JSON.parse(o.body), _maintenant: horloge }); return { ok: true, json: async () => ({ ok: true }) }; }
    return { ok: false, status: 404, json: async () => ({}) };
  };
  const inst = creer({ Spicetify: S, fetch, DJCore, maintenant: () => horloge, sleep: async (ms) => { horloge += ms; } });
  return {
    inst, ordres, sauts, store, lecture, file,
    avancer: (ms) => { horloge += ms; },
    // Joue jusqu'à n ordres (ou fin de la file), tick toutes les 250 ms, saut de 5 s quand rien n'est imminent
    async jouer(n) {
      for (let k = 0; k < 200000 && ordres.length < n; k++) {
        await inst.tick();
        const q = inst.status.plan;
        const reste = q?.choix?.sortie_s ? q.choix.sortie_s * 1000 - S.Player.getProgress() : Infinity;
        horloge += reste > 8000 ? 5000 : 250;
        const p = parUri.get(lecture.uri);
        if (S.Player.getProgress() > p.track.duration * 1000) {   // fin naturelle : Spotify passe au suivant
          if (!file.length) break;
          const suiv = file.shift();
          Object.assign(lecture, { uri: suiv.uri, debut: horloge, pos0: 0 });
        }
      }
    },
    get auditeur() { return auditeur; },
  };
}

test('mode auto : 20 ordres v2 valides, variété, garde-fou O1, quota refrain', async () => {
  const pistes = bibliotheque(30, 21);
  const m = monde(pistes, { avance: (i) => 30 + (i * 13) % 40 });
  await m.jouer(20);
  assert.ok(m.ordres.length >= 20, `${m.ordres.length} ordres`);
  const ids = m.ordres.map((o) => o.transition);
  for (const [i, o] of m.ordres.entries()) {
    const { _maintenant, ...ordre } = o;
    assert.deepEqual(DJCore.choix.valider(ordre, _maintenant), [], JSON.stringify(ordre).slice(0, 200));
    if (i && o.transition !== 'R2') assert.notEqual(o.transition, ids[i - 1], ids.join(' '));
    if (o.transition !== 'R2') assert.ok(o.a.jamais_entendu_s <= 30, `O1 ${o.a.jamais_entendu_s}`);
    if (o.b.entree === 'E2') assert.ok(o.b.saute_s <= 45 && o.b.saute_s <= 0.25 * o.b.duree_s);
  }
  for (let i = 2; i < m.ordres.length; i++) {
    assert.ok(m.ordres.slice(i - 2, i + 1).filter((o) => o.b.entree === 'E2').length <= 1, 'E2 au plus 1 sur 3');
  }
  // le saut tombe juste après le 1 de sortie (−LEAD ms, essai direct 13 : jamais avant) et vise entreeB
  const { LEAD } = require('../dj-auto.js');
  assert.ok(LEAD < 0, `LEAD ${LEAD}`);
  for (const [i, s] of m.sauts.entries()) {
    const o = m.ordres[i];
    const ecart = s.a - o.a.sortie_s * 1000;
    assert.ok(ecart >= -LEAD && ecart <= -LEAD + 40, `saut à ${s.a} pour ${o.a.sortie_s}`);
    assert.equal(s.seekTo, Math.round(o.b.entree_s * 1000));
  }
  assert.ok(new Set(ids).size >= 4, ids.join(' '));
  assert.equal(m.inst.status.historique.length, Math.min(12, m.ordres.length));
});

test('forçage : DJ.forcer(id) vaut pour la prochaine transition ; id inconnu refusé', async () => {
  const pistes = [morceau('rap', 61, { tempo: 95 }), morceau('rap', 62, { tempo: 95.5 }), morceau('rap', 63, { tempo: 96 })];
  const m = monde(pistes);
  assert.equal(m.inst.DJ.forcer('melange'), false);
  assert.equal(m.inst.DJ.forcer('C2'), true);
  await m.jouer(1);
  assert.equal(m.ordres[0].choisie, 'C2');
  assert.equal(m.inst.status.force, null);
  assert.equal(m.inst.DJ.version, 2);
});

test('repli au plan : l\'avance s\'effondre juste avant le saut', async () => {
  const instru = { outro: 16 };
  const h1 = morceau('house', 71, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124, ...instru });
  const h2 = morceau('house', 72, { cle: 0, mode: 1, cleConf: 0.9, tempo: 124, intro: 16 });
  let n = 0;
  const m = monde([h1, h2], { avance: () => (n++ < 1 ? 120 : 14) });
  m.inst.DJ.forcer('C6');
  await m.jouer(1);
  const o = m.ordres[0];
  assert.equal(o.choisie, 'C6');
  if (o.transition !== 'C6') assert.ok(o.replis_plan.length >= 1 && o.replis_plan.every((r) => r.ou === 'plan'));
  assert.ok(DJCore.choix.avanceRequise(o.bars, o.a.bar_s) <= 14, `avance 14 s, ${o.transition} T=${o.bars}`);
});

test('album dans l\'ordre : R2 (A jusqu\'à sa fin) ; rattrapage après un changement à la main', async () => {
  const pistes = bibliotheque(3, 31);
  const m = monde(pistes, { contexte: 'spotify:album:4aawyAB9vmqN3uQ7FjRGTy' });
  await m.jouer(1);
  assert.equal(m.ordres[0].transition, 'R2');
  assert.ok(m.ordres[0].a.sortie_s >= pistes[0].track.duration - 3);

  const m2 = monde(bibliotheque(3, 41));
  await m2.inst.tick();
  m2.avancer(30000);
  m2.inst.suivreProgression();
  Object.assign(m2.lecture, { uri: bibliotheque(3, 41)[2].uri, pos0: 0 });
  m2.avancer(4000);
  const o = await m2.inst.onSongChange();
  assert.ok(o, 'ordre de rattrapage envoyé');
  assert.equal(o.transition, 'R1');
  assert.equal(o.manuel, true);
  assert.deepEqual(DJCore.choix.valider(o), []);
});

test('album après une playlist : R2 vers la piste suivante de l\'album, sans sortir de l\'album (cas 16, essai direct 13)', async () => {
  const album = bibliotheque(4, 51), reserve = bibliotheque(30, 52);
  const m = monde(album, { reserve });
  await m.inst.tick();                       // contexte playlist : la réserve se charge, un suivant est choisi
  assert.ok(m.inst.status.next?.pick, 'suivant choisi dans la réserve de la playlist');
  m.lecture.contexte = 'spotify:album:4beTtJKeg3ITJsiVuxkiV0';   // l'utilisateur lance un album
  m.inst.status.plan = null;
  await m.jouer(1);
  const o = m.ordres[0];
  assert.equal(o.transition, 'R2', o.raison);
  assert.equal(o.b.uri, album[1].uri, 'B = piste suivante de l\'album');
  assert.equal(m.sauts[0].contexte, 'spotify:album:4beTtJKeg3ITJsiVuxkiV0', 'saut dans le contexte de l\'album');
});

test('planTransition lit l\'avance du moteur même mode auto éteint, et rend visible un repli au plan', async () => {
  const pistes = [morceau('rap', 81, { tempo: 95, cle: 0, mode: 1, cleConf: 0.9 }),
    morceau('rap', 82, { tempo: 95.5, cle: 0, mode: 1, cleConf: 0.9 })];
  const m = monde(pistes, { avance: () => 60 });
  m.store['dj-mixer:auto'] = '0';
  const c = await m.inst.DJ.planTransition(pistes[0].uri, pistes[1].uri, { force: 'C5', contexte: null });
  assert.equal(c.transition, 'C5', c.avertissement ?? c.raison);
  assert.equal(c.avertissement, null);
  const m2 = monde(pistes, { avance: () => 3 });
  const c2 = await m2.inst.DJ.planTransition(pistes[0].uri, pistes[1].uri, { force: 'C5', contexte: null });
  assert.notEqual(c2.transition, 'C5');
  assert.match(c2.avertissement, /C5 impossible.*avance 3 s/);
  assert.match(m2.inst.status.text, /C5 impossible/);
});
