// Analyses factices au format de Spicetify.getAudioData (track, bars, beats, sections, segments), pour tester la
// voix (V2), le placement et le choix hors de Spotify. Rien ici n'est calibré sur de vrais morceaux : la forme des
// segments « vocaux » (syllabes serrées, timbre brillant, chroma pointue) reprend seulement l'hypothèse de V2.
//
// fabriquer({
//   tempo: 120, cle: 0, mode: 1, cleConf: 0.8,       // tonalité Spotify (key, mode, key_confidence)
//   sections: [{ mesures: 8, sonie: -9, voix: false }, …],  // voix : booléen, ou tableau d'un booléen par mesure
//   confiance: 0.7, gigue: 0.004,                     // confiance des mesures, écart relatif de leur durée
//   silenceDebut: 0.3, silenceFin: 1.5,               // secondes
//   segments: true, graine: 1, uri,
// })
'use strict';

function rng(graine) {
  let s = graine >>> 0 || 1;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const r3 = (x) => Math.round(x * 1000) / 1000;

function segment(start, duration, sonie, vocal, alea) {
  const n = (k) => (alea() - 0.5) * 2 * k;
  const timbre = new Array(12).fill(0).map(() => n(15));
  timbre[0] = 45 + sonie + n(2);
  timbre[1] = vocal ? 35 + n(12) : -15 + n(12);
  timbre[2] = vocal ? -10 + n(10) : 10 + n(10);
  const pitches = new Array(12).fill(0).map(() => (vocal ? 0.05 + alea() * 0.25 : 0.45 + alea() * 0.55));
  pitches[Math.floor(alea() * 12)] = 1;
  const lmax = sonie + (vocal ? 2 : 0) + n(1.5);
  return { start: r3(start), duration: r3(duration), confidence: 0.6, loudness_start: r3(lmax - 12),
    loudness_max: r3(lmax), loudness_max_time: r3(duration * 0.2), timbre: timbre.map(r3), pitches: pitches.map(r3) };
}

function fabriquer(o = {}) {
  const alea = rng(o.graine ?? 1);
  const tempo = o.tempo ?? 120;
  const beat = 60 / tempo;
  const confiance = o.confiance ?? 0.7;
  const gigue = o.gigue ?? 0.004;
  const silenceDebut = o.silenceDebut ?? 0.3, silenceFin = o.silenceFin ?? 1.5;
  const sections = o.sections ?? [{ mesures: 8, sonie: -12, voix: false }, { mesures: 32, sonie: -8, voix: true },
    { mesures: 8, sonie: -12, voix: false }];
  const bars = [], beats = [], segs = [], secs = [];
  if (silenceDebut > 0) segs.push(segment(0, silenceDebut, -60, false, alea));
  let t = silenceDebut;
  for (const s of sections) {
    const t0 = t;
    for (let m = 0; m < s.mesures; m++) {
      const d = 4 * beat * (1 + (alea() - 0.5) * 2 * gigue);
      const conf = typeof confiance === 'function' ? confiance(bars.length) : confiance;
      bars.push({ start: r3(t), duration: r3(d), confidence: r3(conf) });
      for (let k = 0; k < 4; k++) beats.push({ start: r3(t + (k * d) / 4), duration: r3(d / 4), confidence: r3(conf) });
      const vocal = Array.isArray(s.voix) ? !!s.voix[m] : !!s.voix;
      const nSeg = vocal ? 8 : 4;
      for (let k = 0; k < nSeg; k++) segs.push(segment(t + (k * d) / nSeg, d / nSeg, s.sonie, vocal, alea));
      t += d;
    }
    secs.push({ start: r3(t0), duration: r3(t - t0), confidence: 0.8, loudness: s.sonie, tempo, tempo_confidence: 0.7,
      key: o.cle ?? 0, key_confidence: 0.5, mode: o.mode ?? 1, mode_confidence: 0.5, time_signature: 4,
      time_signature_confidence: 1 });
  }
  if (silenceFin > 0) segs.push(segment(t, silenceFin, -60, false, alea));
  const duree = t + silenceFin;
  // Spotify fait commencer la première section à 0 : elle absorbe le silence initial
  if (secs.length) { secs[0].duration = r3(secs[0].duration + secs[0].start); secs[0].start = 0; }
  if (secs.length) secs[secs.length - 1].duration = r3(duree - secs[secs.length - 1].start);
  const sonieMoy = sections.reduce((x, s) => x + s.sonie * s.mesures, 0) / sections.reduce((x, s) => x + s.mesures, 0);
  return {
    uri: o.uri,
    track: { duration: r3(duree), tempo, tempo_confidence: 0.7, key: o.cle ?? 0, mode: o.mode ?? 1,
      key_confidence: o.cleConf ?? 0.8, loudness: r3(sonieMoy), time_signature: 4, end_of_fade_in: silenceDebut,
      start_of_fade_out: r3(t) },
    bars, beats, sections: secs, segments: o.segments === false ? [] : segs, tatums: [],
  };
}

// Réponse factice de l'endpoint de paroles (color-lyrics v2) : lignes [debut_s, texte]
function paroles(lignes, syncType = 'LINE_SYNCED') {
  return { lyrics: { syncType, lines: lignes.map(([s, w]) => ({ startTimeMs: String(Math.round(s * 1000)), words: w,
    syllables: [], endTimeMs: '0' })), provider: 'Fake', language: 'fr' }, colors: {}, hasVocalRemoval: false };
}

module.exports = { fabriquer, paroles, rng };
