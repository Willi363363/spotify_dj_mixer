// A1 : analyse de la file d'attente réelle. Couverture de l'analyse, points de sortie
// et d'entrée, compatibilité des paires consécutives. Ne touche pas à la lecture.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < 100 && !Spicetify.Player.data?.item; i++) await sleep(100);

  const CAMELOT = { // [key][mode] -> code Camelot (mode 1 = majeur "B", 0 = mineur "A")
    0: ['5A', '8B'], 1: ['12A', '3B'], 2: ['7A', '10B'], 3: ['2A', '5B'], 4: ['9A', '12B'], 5: ['4A', '7B'],
    6: ['11A', '2B'], 7: ['6A', '9B'], 8: ['1A', '4B'], 9: ['8A', '11B'], 10: ['3A', '6B'], 11: ['10A', '1B'],
  };
  const camelot = (k, m) => CAMELOT[k]?.[m] ?? null;
  const camelotDist = (a, b) => {
    if (!a || !b) return null;
    const na = +a.slice(0, -1), nb = +b.slice(0, -1);
    const d = Math.min((na - nb + 12) % 12, (nb - na + 12) % 12);
    return d + (a.slice(-1) === b.slice(-1) ? 0 : 1);
  };

  const items = [Spicetify.Player.data.item, ...(Spicetify.Queue?.nextTracks ?? []).map((t) => t.contextTrack)]
    .filter((t) => t?.uri?.startsWith('spotify:track:')).slice(0, 10);

  const tracks = [];
  for (const it of items) {
    const name = it.name ?? it.metadata?.title;
    try {
      const a = await Spicetify.getAudioData(it.uri);
      const secs = a.sections;
      const drop = secs.reduce((m, s) => (s.loudness > m.loudness ? s : m));
      // sortie : début de la dernière section dont le volume baisse d'au moins 3 dB (outro), sinon dernière section
      const outro = [...secs].reverse().find((s, i, arr) => arr[i + 1] && s.loudness < arr[i + 1].loudness - 3) ?? secs[secs.length - 1];
      const barConf = a.bars.reduce((s, b) => s + b.confidence, 0) / a.bars.length;
      let energy = null;
      try {
        const id = it.uri.split(':')[2];
        const f = await Spicetify.CosmosAsync.get(`https://spclient.wg.spotify.com/audio-attributes/v1/audio-features/${id}?format=json`);
        energy = f?.energy ?? null;
      } catch { energy = 'erreur'; }
      tracks.push({
        name, tempo: +a.track.tempo.toFixed(1), camelot: camelot(a.track.key, a.track.mode),
        keyConf: +a.track.key_confidence.toFixed(2), sections: secs.length,
        drop: +drop.start.toFixed(1), outro: +outro.start.toFixed(1), duree: +a.track.duration.toFixed(0),
        confMesures: +barConf.toFixed(2), energy,
      });
    } catch (e) {
      tracks.push({ name, erreur: String(e?.message ?? e).slice(0, 80) });
    }
    await sleep(150);
  }

  const paires = [];
  for (let i = 0; i + 1 < tracks.length; i++) {
    const A = tracks[i], B = tracks[i + 1];
    if (A.erreur || B.erreur) continue;
    const ratio = B.tempo / A.tempo;
    const dt = Math.min(Math.abs(ratio - 1), Math.abs(ratio * 2 - 1), Math.abs(ratio / 2 - 1)) * 100;
    paires.push({ de: A.name, vers: B.name, ecartTempoPct: +dt.toFixed(1), distCamelot: camelotDist(A.camelot, B.camelot) });
  }
  return { couverture: `${tracks.filter((t) => !t.erreur).length}/${tracks.length}`, tracks, paires };
})()
