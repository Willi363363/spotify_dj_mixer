// Côté Spotify pour la maquette E2 : joue A depuis PREROLL s avant une mesure de sortie,
// puis lance B sur le premier temps de son drop. Renvoie l'heure du changement et le tempo,
// que l'orchestrateur transmet ensuite à e2.py.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const P = Spicetify.Player;
  const LEAD = 115, PREROLL = globalThis.__PREROLL ?? 32;
  const A = globalThis.__A ?? 'spotify:track:1pKYYY0dkg23sQQXi0Q5zN';   // Around the World
  const B = globalThis.__B ?? 'spotify:track:1GiJNHhNGReHSeHbkU02DX';   // Mwen An Sa
  const [a, b] = await Promise.all([Spicetify.getAudioData(A), Spicetify.getAudioData(B)]);
  const exitBar = a.bars.find((x) => x.start > PREROLL + 20 && x.confidence > 0.5);
  const drop = b.sections.reduce((m, s) => (s.loudness > m.loudness ? s : m));
  const entry = b.bars.find((x) => x.start >= drop.start - 0.05);
  const aExit = exitBar.start * 1000;

  await P.playUri(A);
  for (let i = 0; i < 100 && P.data?.item?.uri !== A; i++) await sleep(50);
  await sleep(800);
  P.seek(aExit - PREROLL * 1000);
  await sleep(1000);
  while (aExit - P.getProgress() > LEAD) await sleep(Math.max(4, (aExit - P.getProgress() - LEAD) / 2));
  const t_wall = Date.now();
  await Spicetify.Platform.PlayerAPI.play({ uri: B }, {}, { seekTo: Math.round(entry.start * 1000) });
  return {
    t_wall, bar_s: exitBar.duration, ratio: a.track.tempo / b.track.tempo,
    tempoA: +a.track.tempo.toFixed(1), tempoB: +b.track.tempo.toFixed(1),
    sortieA: exitBar.start, entreeB: entry.start, confSortie: exitBar.confidence, confEntree: entry.confidence,
  };
})()
