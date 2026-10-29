// Petite bibliothèque factice (rap FR, shatta, bouyon, house) : analyses getAudioData générées par fabrique.js,
// avec des structures plausibles (intro, couplets, refrains, outro). Sert aux tests du placement, du choix et de
// dj-auto.js. Aucune donnée réelle : les URI sont inventées (format valide).
'use strict';
const { fabriquer, rng } = require('./fabrique.js');

// paroles : part des morceaux qui ont des paroles synchronisées (essai 13 et collecte du 2026-10-29 : rap ~90 %,
// shatta/bouyon 2 sur 11, house instrumentale sans paroles)
const GENRES = {
  rap: { tempo: [88, 100], cleConf: [0.2, 0.7], paroles: 0.9 },
  shatta: { tempo: [98, 108], cleConf: [0.3, 0.8], paroles: 0.2 },
  bouyon: { tempo: [148, 160], cleConf: [0.2, 0.6], paroles: 0.2 },
  house: { tempo: [120, 126], cleConf: [0.5, 0.9], paroles: 0 },
};

const B62 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
function uri(n) {
  let s = '', x = n + 1;
  for (let i = 0; i < 22; i++) { s = B62[x % 62] + s; x = Math.floor(x / 62) + (i === 0 ? 7 : 0); }
  return `spotify:track:${s}`;
}

// Un morceau : structure tirée selon le genre ; o surcharge (intro, outro, voixIntro…)
function morceau(genre, graine, o = {}) {
  const a = rng(graine * 7919 + 13);
  const g = GENRES[genre];
  const pick = (v) => v[Math.floor(a() * v.length)];
  const tempo = o.tempo ?? +(g.tempo[0] + a() * (g.tempo[1] - g.tempo[0])).toFixed(1);
  const intro = o.intro ?? (genre === 'house' ? 16 : pick([0, 4, 8, 8]));
  const outro = o.outro ?? (genre === 'house' ? 16 : pick([0, 4, 8, 8, 16]));
  const vocal = genre !== 'house';
  const s = [];
  if (intro) s.push({ mesures: intro, sonie: -14, voix: o.voixIntro ?? false });
  const couplet = { mesures: 16, sonie: -9, voix: vocal };
  const refrain = { mesures: 8, sonie: -5.5, voix: vocal };
  s.push(couplet, refrain, { ...couplet }, { ...refrain });
  if (a() < 0.6) s.push({ mesures: 8, sonie: -10, voix: vocal && a() < 0.5 }, { ...refrain });
  if (genre === 'house') s.splice(1, 0, { mesures: 16, sonie: -7, voix: false });
  if (outro) s.push({ mesures: outro, sonie: o.sonieOutro ?? -15, voix: o.voixOutro ?? false });
  return fabriquer({
    tempo, cle: o.cle ?? Math.floor(a() * 12), mode: o.mode ?? (a() < 0.5 ? 0 : 1),
    cleConf: o.cleConf ?? +(g.cleConf[0] + a() * (g.cleConf[1] - g.cleConf[0])).toFixed(2),
    sections: o.sections ?? s, confiance: o.confiance ?? 0.65, gigue: o.gigue ?? 0.004,
    silenceDebut: o.silenceDebut ?? 0.2, silenceFin: o.silenceFin ?? 1.5, segments: o.segments, graine,
    uri: o.uri ?? uri(graine), paroles: o.paroles ?? a() < g.paroles,
  });
}

// Bibliothèque de n morceaux, genres en proportion de la bibliothèque du développeur (H1)
function bibliotheque(n = 24, graine = 1) {
  const a = rng(graine);
  const out = [];
  for (let i = 0; i < n; i++) {
    const r = a();
    const genre = r < 0.5 ? 'rap' : r < 0.75 ? 'shatta' : r < 0.92 ? 'bouyon' : 'house';
    out.push(morceau(genre, graine * 1000 + i));
  }
  return out;
}

module.exports = { morceau, bibliotheque, uri, GENRES };
