// Côté Spotify pour la maquette E2. Choisit, par une matrice de coût (méthode de l'article Spotify
// 2017, cf. docs/recherche/spotify-transitions.md), la mesure de sortie de A et la mesure d'entrée de B,
// choisit le préréglage si __MODE vaut « auto », joue A jusqu'à sa sortie puis lance B sur son entrée.
// Renvoie l'heure du changement et le choix fait, que run.sh transmet à e2.py.
// Réglages : __A, __B (uri), __MODE (préréglage ou « auto »), __LAST (préréglage précédent), __PREROLL (s).
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const P = Spicetify.Player;
  const LEAD = 115, PREROLL = globalThis.__PREROLL ?? 32;
  const A = globalThis.__A ?? 'spotify:track:1pKYYY0dkg23sQQXi0Q5zN';
  const B = globalThis.__B ?? 'spotify:track:1GiJNHhNGReHSeHbkU02DX';
  const [a, b] = await Promise.all([Spicetify.getAudioData(A), Spicetify.getAudioData(B)]);

  // ── Empreinte d'une zone : moyenne des timbres, des notes et du volume de ses segments ──
  const zone = (d, t0, t1) => {
    const segs = d.segments.filter((s) => s.start >= t0 && s.start < t1);
    const v = { timbre: new Array(12).fill(0), pitch: new Array(12).fill(0), loud: -60 };
    if (!segs.length) return v;
    for (const s of segs) for (let i = 0; i < 12; i++) { v.timbre[i] += s.timbre[i] / segs.length; v.pitch[i] += s.pitches[i] / segs.length; }
    v.loud = segs.reduce((x, s) => x + s.loudness_max, 0) / segs.length;
    return v;
  };
  const dist = (x, y) => Math.hypot(...x.map((xi, i) => xi - y[i]));
  const nearSection = (d, t) => d.sections.some((s) => Math.abs(s.start - t) < 0.15);
  const drop = b.sections.reduce((m, s) => (s.loudness > m.loudness ? s : m));

  // ── Candidats : premiers temps de mesure fiables, sortie dans le dernier quart de A, entrée dans les 40 % de B ──
  const durA = a.track.duration, durB = b.track.duration;
  const outs = a.bars.filter((x) => x.confidence > 0.3 && x.start >= Math.max(PREROLL + 20, 0.75 * durA) && x.start <= durA - 6);
  const ins = b.bars.filter((x) => x.confidence > 0.3 && x.start >= 5 && x.start <= 0.4 * durB);
  if (!outs.length || !ins.length) return { erreur: 'aucun point candidat', outs: outs.length, ins: ins.length };

  // ── Coûts de chaque paire (A sort à i, B entre à j), sur 2 mesures de part et d'autre ──
  const rows = [];
  for (const i of outs) for (const j of ins) {
    const za = zone(a, i.start - 2 * i.duration, i.start), zb = zone(b, j.start, j.start + 2 * j.duration);
    rows.push({ i, j, cT: dist(za.timbre, zb.timbre), cC: dist(za.pitch, zb.pitch), cL: -(za.loud + zb.loud) / 2,
      cS: (nearSection(a, i.start) ? 0 : 1) + (nearSection(b, j.start) ? 0 : 1), cD: Math.abs(j.start - drop.start) < 0.2 ? 0 : 1 });
  }
  const W = { cT: 1, cC: 1, cL: 0.7, cS: 1, cD: 1.5 };  // le drop de B compte le plus : notre public veut le drop
  for (const k of Object.keys(W)) {
    const vals = rows.map((r) => r[k]), lo = Math.min(...vals), hi = Math.max(...vals);
    for (const r of rows) r[k + 'n'] = hi > lo ? (r[k] - lo) / (hi - lo) : 0;
  }
  for (const r of rows) r.cost = Object.keys(W).reduce((s, k) => s + W[k] * r[k + 'n'], 0);
  rows.sort((x, y) => x.cost - y.cost);
  // Deux points de vue : le mélange veut la paire qui se ressemble le plus (score complet) ; les transitions
  // « nettes » veulent que B tombe sur son drop, le score ne choisit alors que la sortie de A.
  const dropBar = b.bars.find((x) => x.start >= drop.start - 0.05) ?? b.bars[0];
  const zDrop = zone(b, dropBar.start, dropBar.start + 2 * dropBar.duration);
  const exitForDrop = outs.map((i) => {
    const za = zone(a, i.start - 2 * i.duration, i.start);
    return { i, j: dropBar, cost: dist(za.timbre, zDrop.timbre) / 100 + dist(za.pitch, zDrop.pitch) + (nearSection(a, i.start) ? 0 : 1) };
  }).sort((x, y) => x.cost - y.cost)[0];

  // ── Choix du préréglage (règle de docs/recherche/dj/automatisation.md) ──
  const ratio = a.track.tempo / b.track.tempo;
  const gap = Math.abs(ratio - 1);
  const energyUp = zone(b, dropBar.start, dropBar.start + 4 * dropBar.duration).loud
    > zone(a, exitForDrop.i.start - 4 * exitForDrop.i.duration, exitForDrop.i.start).loud + 1.5;
  const keySure = a.track.key_confidence > 0.4 && b.track.key_confidence > 0.4;
  // Seules les transitions validées à l'écoute sont choisies d'office : le mélange quand les morceaux se
  // calent, la montée sinon (elle ne demande aucun calage : B tombe net sur son drop). La coupe seule a été
  // rejetée à l'écoute (docs/tests/09-ecoute-maquette.md) ; les autres attendent d'être jugées.
  const blend = gap < 0.03 && keySure;
  const order = blend ? ['melange', 'montee'] : ['montee'];
  let mode = globalThis.__MODE ?? 'auto', raison = 'choisi à la main';
  if (mode === 'auto') {
    mode = order.find((m) => m !== globalThis.__LAST) ?? order[0];
    raison = blend ? 'tempos et tonalités proches'
      : gap > 0.06 ? `tempos éloignés (${(gap * 100).toFixed(0)} %) : montée, sans calage`
      : energyUp ? "l'énergie monte vers le drop de B" : 'tonalité incertaine : montée, sans calage';
    if (mode !== order[0]) raison += ', variante pour ne pas répéter';
  }
  const best = mode === 'melange' ? rows[0] : exitForDrop;
  // Transitions qui tombent sur le drop : Spotify lance B 2 mesures avant, pour que la maquette puisse
  // faire monter ces 2 mesures sous la fin de A au lieu de faire surgir B d'un coup.
  const PRE_BARS = mode === 'melange' ? 0 : 2;
  const bStart = Math.max(0, best.j.start - PRE_BARS * best.j.duration);
  const pre_s = best.j.start - bStart;

  const choix = { mode, raison, bar_s: best.i.duration, ratio, pre_s: +pre_s.toFixed(3),
    tempoA: +a.track.tempo.toFixed(1), tempoB: +b.track.tempo.toFixed(1),
    sortieA: +best.i.start.toFixed(2), entreeB: +best.j.start.toFixed(2), dropB: +drop.start.toFixed(2),
    paires: rows.length, cout: +best.cost.toFixed(2) };
  if (globalThis.__DRY) return choix;  // à blanc : calcule sans rien jouer

  // ── Lecture : A jusqu'à sa sortie, puis B sur son entrée ──
  const aExit = best.i.start * 1000;
  await P.playUri(A);
  for (let k = 0; k < 100 && P.data?.item?.uri !== A; k++) await sleep(50);
  await sleep(800);
  P.seek(aExit - PREROLL * 1000);
  await sleep(1000);
  while (aExit - P.getProgress() > LEAD) await sleep(Math.max(4, (aExit - P.getProgress() - LEAD) / 2));
  const t_wall = Date.now();
  await Spicetify.Platform.PlayerAPI.play({ uri: B }, {}, { seekTo: Math.round(bStart * 1000) });
  return { t_wall, ...choix };
})()
