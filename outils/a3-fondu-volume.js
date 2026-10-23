// A3 : fondu de volume par paliers via le lecteur. Descend de V à 30 % de V en 2 s, tient 1 s,
// remonte en 2 s, puis rend le volume d'origine. Renvoie les instants pour l'analyse.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const api = Spicetify.Platform.PlaybackAPI;
  const v0 = await api.getVolume();
  const V = typeof v0 === 'number' ? v0 : v0?.volume ?? Spicetify.Player.getVolume();
  if (!Spicetify.Player.isPlaying()) { Spicetify.Player.play(); await sleep(1500); }
  const STEPS = 50, DUR = 2000;
  const marks = { start: Date.now() };
  for (let i = 1; i <= STEPS; i++) { await api.setVolume(V * (1 - 0.7 * i / STEPS)); await sleep(DUR / STEPS); }
  marks.bas = Date.now();
  await sleep(1000);
  marks.remonte = Date.now();
  for (let i = 1; i <= STEPS; i++) { await api.setVolume(V * (0.3 + 0.7 * i / STEPS)); await sleep(DUR / STEPS); }
  marks.fin = Date.now();
  await api.setVolume(V);
  const vFinal = await api.getVolume();
  return { volumeOrigine: V, volumeFinal: typeof vFinal === 'number' ? vFinal : vFinal?.volume, marks };
})()
