// Cherche dans une playlist les paires de morceaux les plus faciles à mixer (et à entendre mixées) :
// tempo à moins de 1,5 % d'écart, mesures bien détectées, tonalités voisines sur la roue de Camelot.
// Lecture seule. Réglages : __PLAYLIST (uri), __MAX (nombre de morceaux analysés).
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const PL = globalThis.__PLAYLIST ?? 'spotify:playlist:39NDse2QZPhw2FMFO76C6N';
  const MAX = globalThis.__MAX ?? 90;
  const OFFSET = globalThis.__OFFSET ?? 0;
  const DEJA = new Set(globalThis.__DEJA ?? []); // morceaux déjà entendus, à écarter
  const CAM = [['5A', '8B'], ['12A', '3B'], ['7A', '10B'], ['2A', '5B'], ['9A', '12B'], ['4A', '7B'],
    ['11A', '2B'], ['6A', '9B'], ['1A', '4B'], ['8A', '11B'], ['3A', '6B'], ['10A', '1B']];
  const camDist = (a, b) => {
    const d = Math.abs(+a.slice(0, -1) - +b.slice(0, -1));
    return Math.min(d, 12 - d) + (a.slice(-1) === b.slice(-1) ? 0 : 1);
  };
  const c = await Spicetify.Platform.PlaylistAPI.getContents(PL, { offset: OFFSET, limit: MAX });
  const tracks = [];
  const seen = new Set();
  for (const t of c.items.slice(0, MAX)) {
    if (DEJA.has(t.uri) || seen.has(t.uri)) continue;
    seen.add(t.uri);
    try {
      const a = await Spicetify.getAudioData(t.uri);
      if (!a.sections?.length) continue;
      const barConf = a.bars.reduce((s, b) => s + b.confidence, 0) / a.bars.length;
      const tempoStable = a.sections.every((s) => Math.abs(s.tempo - a.track.tempo) < 2);
      tracks.push({
        name: t.name, uri: t.uri, artiste: t.artists?.[0]?.name, tempo: a.track.tempo,
        cam: CAM[a.track.key]?.[a.track.mode], keyConf: a.track.key_confidence,
        barConf, tempoStable, tempoConf: a.track.tempo_confidence,
      });
    } catch {}
    await sleep(120);
  }
  const good = tracks.filter((t) => t.tempoStable && t.barConf > 0.5);
  const pairs = [];
  for (const A of good) for (const B of good) {
    if (A === B) continue;
    const dt = Math.abs(B.tempo / A.tempo - 1) * 100;
    if (dt > 1.5) continue;
    const dk = A.keyConf > 0.4 && B.keyConf > 0.4 ? camDist(A.cam, B.cam) : 3;
    pairs.push({ score: +(dt * 2 + dk - (A.barConf + B.barConf) * 2).toFixed(2), dt: +dt.toFixed(2), dk, A, B });
  }
  pairs.sort((p, q) => p.score - q.score);
  const fmt = (t) => `${t.name} (${t.artiste}) ${t.tempo.toFixed(1)} BPM ${t.cam} mesures ${t.barConf.toFixed(2)}`;
  return {
    analyses: tracks.length, retenus: good.length,
    meilleures: pairs.slice(0, 6).map((p) => ({ A: fmt(p.A), B: fmt(p.B), uriA: p.A.uri, uriB: p.B.uri, ecartTempoPct: p.dt, distCamelot: p.dk })),
  };
})()
