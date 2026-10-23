// A2 : transition A -> B calée sur le temps. Joue A depuis 8 temps avant un premier temps
// de mesure, puis au moment de ce premier temps lance B directement sur son drop.
// Renvoie l'instant visé et l'instant réel du changement, pour l'analyse de l'enregistrement.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const P = Spicetify.Player;
  const LEAD = 115;
  const A = 'spotify:track:1pKYYY0dkg23sQQXi0Q5zN'; // Around the World
  const B = globalThis.__A2_B ?? (Spicetify.Queue?.nextTracks ?? []).map((t) => t.contextTrack?.uri).find((u) => u?.startsWith('spotify:track:') && u !== A);

  const [a, b] = await Promise.all([Spicetify.getAudioData(A), Spicetify.getAudioData(B)]);
  const bDrop = b.sections.reduce((m, s) => (s.loudness > m.loudness ? s : m));
  const bEntry = b.bars.find((x) => x.start >= bDrop.start - 0.05) ?? b.bars[0]; // premier temps de mesure du drop
  const aExitBar = a.bars.find((x) => x.start > 60 && x.confidence > 0.5) ?? a.bars[30];
  const aExit = aExitBar.start * 1000;

  await P.playUri(A);
  for (let i = 0; i < 100 && P.data?.item?.uri !== A; i++) await sleep(50);
  await sleep(800);
  const beat = 60000 / a.track.tempo;
  P.seek(aExit - 8 * beat);
  await sleep(600);

  Spicetify.showNotification('Transition dans quelques secondes');
  while (aExit - P.getProgress() > LEAD) await sleep(Math.max(4, (aExit - P.getProgress() - LEAD) / 2));
  const at = Date.now();
  const lateMs = Math.round(P.getProgress() - aExit);
  // playUri accepte une position de départ via les options du lecteur interne
  await Spicetify.Platform.PlayerAPI.play({ uri: B }, {}, { seekTo: Math.round(bEntry.start * 1000) });
  const t0 = performance.now();
  for (let i = 0; i < 400 && P.data?.item?.uri !== B; i++) await sleep(5);
  const switchReportedMs = Math.round(performance.now() - t0);
  await sleep(300);
  const posB = Math.round(P.getProgress());

  return {
    A: P.data && 'Around the World', B: b && (await Spicetify.CosmosAsync.get(`https://api.spotify.com/v1/tracks/${B.split(':')[2]}`).then((r) => r.name).catch(() => B)),
    aExitS: +(aExit / 1000).toFixed(3), confSortie: aExitBar.confidence,
    bEntreeS: +bEntry.start.toFixed(3), confEntree: bEntry.confidence,
    tempoA: Math.round(a.track.tempo), tempoB: Math.round(b.track.tempo),
    at, lateMs, switchReportedMs, posBApres300ms: posB,
  };
})()
