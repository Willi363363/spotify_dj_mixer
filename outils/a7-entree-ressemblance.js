// A7 : point d'entrée de B choisi par ressemblance avec la mesure de sortie de A (timbre + notes
// des segments, comme Eternal Jukebox). Compare au simple « entrer sur le drop ». Calcul seul.
(async () => {
  const A = 'spotify:track:1pKYYY0dkg23sQQXi0Q5zN';
  const B = globalThis.__A7_B ?? 'spotify:track:1GiJNHhNGReHSeHbkU02DX'; // Mwen An Sa
  const [a, b] = await Promise.all([Spicetify.getAudioData(A), Spicetify.getAudioData(B)]);

  // Empreinte d'une mesure : moyenne des 12 timbres et des 12 notes de ses segments, normalisées.
  const fingerprint = (data, bar) => {
    const segs = data.segments.filter((s) => s.start >= bar.start && s.start < bar.start + bar.duration);
    if (!segs.length) return null;
    const v = new Array(24).fill(0);
    for (const s of segs) { s.timbre.forEach((t, i) => (v[i] += t / 100)); s.pitches.forEach((p, i) => (v[12 + i] += p)); }
    const n = Math.hypot(...v) || 1;
    return v.map((x) => x / n);
  };
  const cos = (x, y) => x.reduce((s, xi, i) => s + xi * y[i], 0);

  const exitBar = a.bars.find((x) => x.start > 60 && x.confidence > 0.5);
  const fa = fingerprint(a, exitBar);
  const candidates = b.bars
    .filter((x) => x.confidence > 0.3 && x.start > 5 && x.start < b.track.duration - 20)
    .map((x) => ({ start: +x.start.toFixed(2), conf: +x.confidence.toFixed(2), sim: fingerprint(b, x) && +cos(fa, fingerprint(b, x)).toFixed(3) }))
    .filter((c) => c.sim !== null)
    .sort((p, q) => q.sim - p.sim);
  const drop = b.sections.reduce((m, s) => (s.loudness > m.loudness ? s : m));
  const dropBar = b.bars.find((x) => x.start >= drop.start - 0.05);
  return {
    sortieA: +exitBar.start.toFixed(2), mesuresCandidates: candidates.length,
    meilleures: candidates.slice(0, 3), pire: candidates.at(-1),
    entreeDrop: { start: +dropBar.start.toFixed(2), sim: +cos(fa, fingerprint(b, dropBar)).toFixed(3) },
  };
})()
