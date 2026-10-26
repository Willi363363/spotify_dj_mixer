// Extension Spicetify « Mode DJ automatique » : quand le mode est allumé (interrupteur de l'app Mode DJ),
// chaque morceau enchaîne tout seul vers le suivant de la file, avec la transition la plus adaptée.
// - Choix de la transition et des points (méthode de l'article Spotify 2017, règles de
//   docs/recherche/dj/automatisation.md, goûts de docs/gouts.md) : DJ.planTransition().
// - Le saut se fait pile sur le temps, dans le contexte de lecture (la playlist continue), directement
//   à la bonne position dans B : une seule commande, ~5 ms de silence.
// - La maquette (proto/e2/e2.py, http://127.0.0.1:47802) reçoit l'ordre et joue la transition.
(function djAuto() {
  if (!Spicetify?.Player?.data || !Spicetify.Platform?.PlayerAPI || !Spicetify.getAudioData) {
    setTimeout(djAuto, 500);
    return;
  }
  const MAQUETTE = 'http://127.0.0.1:47802';
  const KEY = 'dj-mixer:auto';
  const LEAD = 115;        // ms : avance du saut, mesurée (docs/tests/03-boucle-par-saut.md)
  const PRE_BARS = 4;      // B lancé 4 mesures avant son entrée : il monte sous la fin de A (jamais d'arrivée sèche)
  const LABELS = { melange: 'mélange', montee: 'montée', montee_courte: 'montée courte', echo_doux: 'écho',
    retour_doux: 'retour arrière', frein_doux: 'frein', filtre: 'balayage de filtre' };
  const MARGIN_S = 15;     // une sortie trop proche de maintenant n'est pas prévue
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const P = Spicetify.Player, API = Spicetify.Platform.PlayerAPI;
  const cache = new Map();
  const audio = async (uri) => {
    if (!cache.has(uri)) cache.set(uri, await Spicetify.getAudioData(uri));
    return cache.get(uri);
  };

  // ── Choix de la transition ───────────────────────────────────────────────────────────────────────
  async function planTransition(A, B, { mode = 'auto', last = '', history = [], minExit = 0 } = {}) {
    if (last && !history.length) history = [last];
    const [a, b] = await Promise.all([audio(A), audio(B)]);
    if (!a?.bars?.length || !b?.bars?.length || !b.sections?.length) return { erreur: 'analyse manquante' };
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
    const durA = a.track.duration, durB = b.track.duration;
    const outs = a.bars.filter((x) => x.confidence > 0.3 && x.start >= Math.max(minExit, 0.75 * durA) && x.start <= durA - 6);
    const ins = b.bars.filter((x) => x.confidence > 0.3 && x.start >= 5 && x.start <= 0.4 * durB);
    if (!outs.length || !ins.length) return { erreur: 'aucun point de sortie ou d\'entrée possible' };
    // Mélange : la paire de mesures qui se ressemble le plus (timbre, notes, volume, sections, drop)
    const rows = [];
    for (const i of outs) for (const j of ins) {
      const za = zone(a, i.start - 2 * i.duration, i.start), zb = zone(b, j.start, j.start + 2 * j.duration);
      rows.push({ i, j, cT: dist(za.timbre, zb.timbre), cC: dist(za.pitch, zb.pitch), cL: -(za.loud + zb.loud) / 2,
        cS: (nearSection(a, i.start) ? 0 : 1) + (nearSection(b, j.start) ? 0 : 1), cD: Math.abs(j.start - drop.start) < 0.2 ? 0 : 1 });
    }
    const W = { cT: 1, cC: 1, cL: 0.7, cS: 1, cD: 1.5 };
    for (const k of Object.keys(W)) {
      const vals = rows.map((r) => r[k]), lo = Math.min(...vals), hi = Math.max(...vals);
      for (const r of rows) r[k + 'n'] = hi > lo ? (r[k] - lo) / (hi - lo) : 0;
    }
    for (const r of rows) r.cost = Object.keys(W).reduce((s, k) => s + W[k] * r[k + 'n'], 0);
    rows.sort((x, y) => x.cost - y.cost);
    // Montée : B tombe sur son drop ; le score ne choisit que la sortie de A
    const dropBar = b.bars.find((x) => x.start >= drop.start - 0.05) ?? b.bars[0];
    const zDrop = zone(b, dropBar.start, dropBar.start + 2 * dropBar.duration);
    const exitForDrop = outs.map((i) => {
      const za = zone(a, i.start - 2 * i.duration, i.start);
      return { i, j: dropBar, cost: dist(za.timbre, zDrop.timbre) / 100 + dist(za.pitch, zDrop.pitch) + (nearSection(a, i.start) ? 0 : 1) };
    }).sort((x, y) => x.cost - y.cost)[0];
    // Préréglage : de la variété (« toujours le même style » a été rejeté), sans reprendre les 2 derniers.
    // Mélange si les morceaux se calent ; sinon un style doux (B monte sous A) choisi selon l'énergie.
    const ratio = a.track.tempo / b.track.tempo, gap = Math.abs(ratio - 1);
    const keySure = a.track.key_confidence > 0.4 && b.track.key_confidence > 0.4;
    const blend = gap < 0.03 && keySure;
    const zA = zone(a, exitForDrop.i.start - 4 * exitForDrop.i.duration, exitForDrop.i.start);
    const zB = zone(b, dropBar.start, dropBar.start + 4 * dropBar.duration);
    const energy = zB.loud - zA.loud;  // > 0 : ça monte vers B
    const pool = energy > 1.5 ? ['montee', 'montee_courte', 'retour_doux', 'echo_doux', 'filtre', 'frein_doux']
      : energy < -1.5 ? ['echo_doux', 'filtre', 'frein_doux', 'montee_courte', 'retour_doux', 'montee']
      : ['montee_courte', 'echo_doux', 'retour_doux', 'filtre', 'montee', 'frein_doux'];
    if (blend) pool.unshift('melange');
    let raison = 'choisi à la main';
    if (mode === 'auto') {
      const recent = history.slice(-2);
      const fresh = pool.filter((m) => !recent.includes(m));
      const top = fresh.slice(0, blend ? 1 : 3);  // un peu de hasard parmi les mieux adaptés
      mode = top[Math.floor(Math.random() * top.length)] ?? pool[0];
      raison = `${blend ? 'tempos et tonalités proches' : gap > 0.06 ? `tempos éloignés (${(gap * 100).toFixed(0)} %)` : 'tonalité incertaine'}, `
        + `${energy > 1.5 ? "l'énergie monte" : energy < -1.5 ? "l'énergie redescend" : 'énergie stable'} : ${LABELS[mode] ?? mode}`;
    }
    const best = mode === 'melange' ? rows[0] : exitForDrop;
    const bStart = Math.max(0, best.j.start - PRE_BARS * best.j.duration);
    return { mode, raison, bar_s: best.i.duration, ratio, pre_s: +(best.j.start - bStart).toFixed(3), bStart,
      tempoA: +a.track.tempo.toFixed(1), tempoB: +b.track.tempo.toFixed(1),
      sortieA: +best.i.start.toFixed(2), entreeB: +best.j.start.toFixed(2), dropB: +drop.start.toFixed(2) };
  }

  // ── Saut pile sur le temps ───────────────────────────────────────────────────────────────────────
  async function switchAt(exitMs, B, bStartS, ctx) {
    while (exitMs - P.getProgress() > LEAD) await sleep(Math.max(4, (exitMs - P.getProgress() - LEAD) / 2));
    const t_wall = Date.now();
    const seekTo = Math.round(bStartS * 1000);
    if (ctx?.uri && B.uid && !ctx.uri.startsWith('spotify:track:')) {
      await API.play({ uri: ctx.uri, url: ctx.url }, {}, { skipTo: { uid: B.uid, uri: B.uri }, seekTo });
    } else {
      await API.play({ uri: B.uri }, {}, { seekTo });  // hors playlist (file, lecture auto) : B seul
    }
    return t_wall;
  }

  async function sendOrder(order) {
    try {
      await fetch(`${MAQUETTE}/order`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(order) });
      return true;
    } catch { return false; }
  }

  // ── Mode automatique ─────────────────────────────────────────────────────────────────────────────
  // history : préréglages joués ; log : dernières transitions faites (pour l'historique de l'app)
  const status = { enabled: false, text: 'Mode DJ automatique éteint.', plan: null, history: [], log: [] };
  let planning = false, maquetteOk = false, lastCheck = 0;
  const isOn = () => Spicetify.LocalStorage.get(KEY) === '1';
  const nextTrack = () => (Spicetify.Queue?.nextTracks ?? []).map((t) => t.contextTrack).find((t) => t?.uri?.startsWith('spotify:track:'));

  async function tick() {
    status.enabled = isOn();
    const item = P.data?.item;
    if (!status.enabled) { status.plan = null; status.text = 'Mode DJ automatique éteint.'; return; }
    if (!item?.uri?.startsWith('spotify:track:')) { status.text = 'En attente d\'un morceau.'; return; }
    const B = nextTrack();
    const p = status.plan;
    if (p && (p.forUri !== item.uri || (!p.done && B && p.B.uri !== B.uri))) status.plan = null;  // morceau ou file changés
    if (!status.plan && !planning) {
      if (!B) { status.text = 'Pas de morceau suivant dans la file.'; return; }
      // Sans maquette, un saut couperait le morceau sans transition : on ne prévoit rien.
      if (Date.now() - lastCheck > 5000) {
        lastCheck = Date.now();
        try { maquetteOk = (await fetch(`${MAQUETTE}/state`, { cache: 'no-store' })).ok; } catch { maquetteOk = false; }
      }
      if (!maquetteOk) { status.text = 'Maquette éteinte : Spotify joue normalement, sans transition.'; return; }
      planning = true;
      try {
        const choix = await planTransition(item.uri, B.uri, { history: status.history, minExit: P.getProgress() / 1000 + MARGIN_S });
        status.plan = { forUri: item.uri, A: item.name, B, choix, done: false, failed: !!choix.erreur };
        status.text = choix.erreur ? `Pas de transition pour ce morceau : ${choix.erreur}.` : `Prévu : ${LABELS[choix.mode] ?? choix.mode} vers « ${B.metadata?.title ?? 'suivant'} » à ${fmt(choix.sortieA)}.`;
      } catch (e) { status.plan = { forUri: item.uri, B, failed: true }; status.text = `Analyse impossible : ${e}`; }
      planning = false;
    }
    const q = status.plan;
    if (!q || q.done || q.failed || !q.choix) return;
    const exitMs = q.choix.sortieA * 1000;
    const remaining = exitMs - P.getProgress();
    if (remaining < -500) { q.failed = true; status.text = 'Point de sortie dépassé (saut manuel ?) : pas de transition.'; return; }
    if (remaining > 1500 || P.data?.isPaused) return;
    q.done = true;
    const t_wall = await switchAt(exitMs, q.B, q.choix.bStart, P.data?.context);
    status.history = [...status.history, q.choix.mode].slice(-10);
    status.log = [{ at: Date.now(), mode: q.choix.mode, label: LABELS[q.choix.mode] ?? q.choix.mode, A: q.A, B: q.B.metadata?.title ?? '' }, ...status.log].slice(0, 8);
    const ok = await sendOrder({ ...q.choix, t_wall });
    status.text = ok ? `Transition lancée vers « ${q.B.metadata?.title ?? 'suivant'} » : elle s'entendra dans la maquette.` : 'La maquette ne répond pas : saut fait sans transition.';
  }
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  let busy = false;
  setInterval(async () => { if (busy) return; busy = true; try { await tick(); } finally { busy = false; } }, 250);

  window.DJ = {
    planTransition, switchAt, sendOrder, status, LABELS,
    setAuto: (on) => { Spicetify.LocalStorage.set(KEY, on ? '1' : '0'); status.plan = null; },
  };
})();
