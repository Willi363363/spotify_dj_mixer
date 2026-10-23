(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const P = Spicetify.Player;
  for (let i = 0; i < 100 && !P.data?.item; i++) await sleep(100);
  const found = { uri: 'spotify:track:1pKYYY0dkg23sQQXi0Q5zN' };
  await P.playUri(found.uri);
  for (let i = 0; i < 100 && P.data?.item?.uri !== found.uri; i++) await sleep(100);
  await sleep(1500);
  if (!P.isPlaying()) { P.play(); await sleep(1500); }

  const a = await Spicetify.getAudioData(P.data.item.uri);
  const loudest = a.sections.reduce((m, s) => (s.loudness > m.loudness ? s : m));
  const bars = a.bars.filter((b) => b.start >= loudest.start);
  const loopStart = bars[0].start * 1000;
  const loopEnd = bars[1].start * 1000; // une mesure

  // Mesure la latence d'un saut : temps entre l'appel et la position effectivement mise à jour.
  const seekAndWait = async (target) => {
    const t0 = performance.now();
    P.seek(target);
    for (let i = 0; i < 200; i++) {
      if (Math.abs(P.getProgress() - target) < 400) break;
      await sleep(5);
    }
    return Math.round(performance.now() - t0);
  };

  Spicetify.showNotification('Test de boucle dans 3 secondes : écoute les reprises');
  await sleep(3000);
  await seekAndWait(loopStart);
  const loops = [];
  for (let n = 0; n < 8; n++) {
    // Attend la fin de boucle en polling fin pour limiter la gigue du timer.
    const LEAD = 115;
    while (loopEnd - P.getProgress() > LEAD) await sleep(Math.max(5, (loopEnd - P.getProgress() - LEAD) / 2));
    const late = Math.round(P.getProgress() - loopEnd);
    const at = Date.now();
    const latency = await seekAndWait(loopStart);
    loops.push({ late, latency, at });
  }
  return {
    track: `${P.data.item.name} - ${P.data.item.artists?.map((x) => x.name).join(', ')}`,
    tempo: Math.round(a.track.tempo),
    loop: `${(loopStart / 1000).toFixed(1)}s → ${(loopEnd / 1000).toFixed(1)}s`,
    loops,
  };
})()
