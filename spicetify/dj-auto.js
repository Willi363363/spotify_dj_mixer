// Extension Spicetify « Mode DJ automatique » : quand le mode est allumé (interrupteur de l'app Mode DJ),
// chaque morceau enchaîne tout seul vers le suivant de la file, avec la transition la plus adaptée.
// - Choix de la transition et des points (méthode de l'article Spotify 2017, types de Vande Veire 2018,
//   règles de docs/recherche/axes-amelioration.md, goûts de docs/gouts.md) : DJ.planTransition().
// - Le saut se fait pile sur le temps, dans le contexte de lecture (la playlist continue), directement
//   à la bonne position dans B : une seule commande, sans silence (la maquette situe le changement à l'heure).
// - La maquette (proto/e2/e2.py, http://127.0.0.1:47802) reçoit l'ordre et joue la transition.
(function djAuto() {
  if (!Spicetify?.Player?.data || !Spicetify.Platform?.PlayerAPI || !Spicetify.getAudioData) {
    setTimeout(djAuto, 500);
    return;
  }
  const MAQUETTE = 'http://127.0.0.1:47802';
  const KEY = 'dj-mixer:auto';
  // ms : le saut par play se produit ~90 ms après l'ordre (e2.py, SWITCH_S). Avec 30 ms d'avance, il tombe
  // ~60 ms APRÈS le premier temps de la mesure de sortie : la maquette recale alors la fin de A de quelques ms
  // en arrière, sur ce premier temps. Avant ce temps (ancienne valeur 115 ms), elle reculait d'un temps
  // entier et le drop de B tombait sur le 4ᵉ temps de A.
  const LEAD = 30;
  // Mesures de A rejouées avant la sortie par chaque style : avec l'avance de B et 2 mesures de B à attendre,
  // elles fixent l'avance minimale de la maquette pour que la transition soit prête à temps
  const REAL_BARS = { montee: 4, filtre: 4, frein_doux: 3, retour_doux: 3, echo_doux: 2, drop_swap: 2, montee_courte: 1, melange: 8 };
  // B lancé 8 mesures avant son entrée : il monte longtemps sous A, qui descend en miroir (4 mesures,
  // puis moins, ont donné « trop bref, le son sort de nulle part d'un coup », essai 21)
  const PRE_BARS = 8;
  const LABELS = { melange: 'superposition', montee: 'montée', montee_courte: 'montée courte', echo_doux: 'écho',
    retour_doux: 'retour arrière', frein_doux: 'frein', filtre: 'balayage de filtre', drop_swap: 'drop swap' };
  const TYPES = { drop: 'B entre sur son drop', relaxed: 'B part de son début', blend: 'mélange calé',
    swap: 'drop swap' };
  // Chaîne de Markov entre types (Vande Veire 2018, adaptée) : la variété perçue vient du type, pas de l'effet
  // Le drop swap (B sans montée) n'est plus tiré : B qui arrive sans monter sous A a été rejeté à chaque
  // version (essais 16, 19, 21) ; il reste disponible à la main.
  const MARKOV = {
    relaxed: { drop: 0.7, blend: 0.3 },
    drop: { drop: 0.6, relaxed: 0.4 },
    blend: { drop: 0.6, relaxed: 0.4 },
    swap: { relaxed: 0.5, drop: 0.5 },
  };
  const MARGIN_S = 15;     // une sortie trop proche de maintenant n'est pas prévue
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const P = Spicetify.Player, API = Spicetify.Platform.PlayerAPI;
  const cache = new Map();
  const audio = async (uri) => {
    if (!cache.has(uri)) cache.set(uri, await Spicetify.getAudioData(uri));
    return cache.get(uri);
  };

  // Roue de Camelot : numéro (quintes) et lettre (A mineur, B majeur) ; null si la tonalité est incertaine
  const camelot = (t) => {
    if (t.key < 0 || t.key_confidence < 0.4) return null;
    const k = t.mode === 1 ? t.key : (t.key + 3) % 12;  // mineur : même numéro que son relatif majeur
    return { n: ((k * 7) % 12 + 7) % 12 + 1, minor: t.mode !== 1 };
  };
  const camelotName = (c) => c && `${c.n}${c.minor ? 'A' : 'B'}`;
  const camelotDist = (x, y) => {
    if (!x || !y) return null;
    const d = Math.abs(x.n - y.n);
    return Math.min(d, 12 - d) + (x.minor !== y.minor ? 1 : 0);
  };
  // Écart de tempo, B compté à tempo double ou moitié si c'est plus proche de A
  const tempoGap = (ta, tb) => Math.min(...[0.5, 1, 2].map((f) => Math.abs(Math.log((ta / tb) * f))));

  // Mesures annotées de leur place dans la phrase : 8 = début de phrase de 8 mesures (depuis le début de
  // section), 4 = demi-phrase, 0 = ailleurs. Les DJ entrent et sortent sur des multiples de 8 mesures.
  const phrased = (d) => {
    let si = 0, k = 0;
    return d.bars.map((x) => {
      while (si + 1 < d.sections.length && d.sections[si + 1].start <= x.start + 0.1) { si++; k = 0; }
      const phrase = k % 8 === 0 ? 8 : k % 4 === 0 ? 4 : 0;
      k++;
      return { ...x, phrase };
    });
  };
  const onPhrase = (bars) => {
    for (const p of [8, 4]) { const c = bars.filter((x) => x.phrase >= p); if (c.length) return c; }
    return bars;
  };
  const sample = (probs) => {
    const total = Object.values(probs).reduce((s, v) => s + v, 0);
    let r = Math.random() * total;
    for (const [k, v] of Object.entries(probs)) { if ((r -= v) <= 0) return k; }
    return Object.keys(probs)[0];
  };
  const typeOf = (mode) => mode === 'melange' ? 'blend' : mode === 'drop_swap' ? 'swap'
    : ['echo_doux', 'filtre'].includes(mode) ? 'relaxed' : 'drop';

  // ── Choix de la transition ───────────────────────────────────────────────────────────────────────
  // history : préréglages joués ; types : types joués ; delay, target : avance de la maquette et sa cible (s)
  async function planTransition(A, B, { mode = 'auto', last = '', history = [], types = [], minExit = 0, delay = 60, target = 60, notes = {} } = {}) {
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
    const durA = a.track.duration, durB = b.track.duration;
    const barsA = phrased(a), barsB = phrased(b);
    // Drop de B : la section la plus forte de sa première moitié (au-delà, on n'en jouerait qu'un bout) ;
    // à défaut, la première section au moins aussi forte que la médiane après 10 s.
    const early = b.sections.filter((s) => s.start >= 5 && s.start <= 0.5 * durB);
    const med = [...b.sections].map((s) => s.loudness).sort((x, y) => x - y)[Math.floor(b.sections.length / 2)];
    const drop = early.length ? early.reduce((m, s) => (s.loudness > m.loudness ? s : m))
      : b.sections.find((s) => s.start >= 10 && s.loudness >= med) ?? b.sections[0];
    const dropBar = barsB.find((x) => x.start >= drop.start - 0.05) ?? barsB[0];
    const outs = onPhrase(barsA.filter((x) => x.confidence > 0.3 && x.start >= Math.max(minExit, 0.75 * durA) && x.start <= durA - 6));
    if (!outs.length) return { erreur: 'aucun point de sortie possible' };
    // Entrée « relaxed » : B part presque de son début, sur la première demi-phrase après 4 mesures
    const relaxBar = barsB.find((x, k) => k >= PRE_BARS && x.phrase >= 4) ?? barsB[Math.min(PRE_BARS, barsB.length - 1)];
    // Sortie de A la plus proche (timbre, notes, frontière de section) d'une entrée de B donnée
    const exitFor = (j) => {
      const zj = zone(b, j.start, j.start + 2 * j.duration);
      return outs.map((i) => {
        const za = zone(a, i.start - 2 * i.duration, i.start);
        return { i, j, cost: dist(za.timbre, zj.timbre) / 100 + dist(za.pitch, zj.pitch) + (nearSection(a, i.start) ? 0 : 1) };
      }).sort((x, y) => x.cost - y.cost)[0];
    };
    const ratio = a.track.tempo / b.track.tempo, gap = Math.exp(tempoGap(a.track.tempo, b.track.tempo)) - 1;
    const ca = camelot(a.track), cb = camelot(b.track), keyD = camelotDist(ca, cb);
    // Mélange : tempos à 6 % près (double / moitié compris) et tonalités voisines sur la roue de Camelot ;
    // il fait fondre l'avance de la maquette d'environ 8 mesures, donc il faut en avoir assez.
    const barA = outs[0].duration;
    // Mélange (« clean de fou », essai 6), débloqué d'après l'audit : il FINIT sur le drop de B (superposition
    // des N mesures de B qui le précèdent, comme Spotify) ; refusé seulement
    // si les deux tonalités sont sûres et éloignées (≥ 3 crans) : une tonalité incertaine ne l'empêche plus
    // (12 transitions sur 19). L'avance doit couvrir le mélange et la transition suivante.
    // 8 mesures dès que l'avance le permet (le mélange « clean de fou » en durait 8 ; 4 mesures, essai 26 :
    // « assez bizarre »), 4 sinon
    const barA0 = 240 / a.track.tempo, barB0 = 240 / b.track.tempo;
    const blendBars = delay >= needS('melange', barA0, barB0, 0, 8) + 12 ? 8 : 4;
    const iDrop = barsB.indexOf(dropBar);
    const blendEntry = iDrop >= blendBars ? barsB[iDrop - blendBars] : null;
    const blendOk = !!blendEntry && gap < 0.06 && !(keyD !== null && keyD >= 3)
      && delay >= needS('melange', barA, blendEntry.duration, 0, blendBars) + 12;
    const prevType = types[types.length - 1] ?? 'relaxed';
    let type = typeOf(mode);
    if (mode === 'auto' && blendOk && gap < 0.03) {
      // Refonte du 26/10 : quand les morceaux se calent (le cas normal, le suivant étant choisi pour ça), la
      // transition est une vraie superposition, comme chez Apple et Spotify ; les styles à boucles et effets
      // synthétiques ne servent plus que de repli (« toujours le même système », essai 27).
      type = 'blend';
    } else if (mode === 'auto') {
      const probs = { ...MARKOV[prevType] };
      if (!blendOk) delete probs.blend;
      else if (delay > target + 8) probs.blend *= 3;  // seul le mélange consomme de l'avance : il la fait redescendre
      if (prevType === 'swap') delete probs.swap;  // jamais deux drop swaps de suite
      type = sample(probs);
    }
    // Drop trop près du début de B : pas assez de B avant lui pour une montée de 8 mesures. B part alors de son
    // début (entrée « relaxed »), qui en a toujours assez.
    if (type === 'drop' && dropBar.start < PRE_BARS * barA) type = 'relaxed';
    // Mélange demandé à la main alors que le drop de B est trop près de son début : il part du début de B
    const entry = type === 'blend' ? (blendEntry ?? barsB[Math.max(0, iDrop - blendBars)])
      : type === 'relaxed' ? relaxBar : dropBar;
    if (!entry) return { erreur: 'aucun point d\'entrée possible' };
    const best = exitFor(entry);
    // Énergie sur des zones de même longueur : 4 mesures avant la sortie de A, 4 après l'entrée de B
    const zA = zone(a, best.i.start - 4 * best.i.duration, best.i.start);
    const zB = zone(b, entry.start, entry.start + 4 * entry.duration);
    const energy = zB.loud - zA.loud;  // > 0 : ça monte vers B
    const pools = {
      // Retour arrière et écho hors du choix automatique : jugés « horrible » et « que des fondus » (essais
      // 19-20) ; ils restent disponibles à la main. Les styles à effets marqués (roulements, frein) plaisent.
      // Jamais de montée vers un B plus calme (« montée qui débouche sur plus calme » : erreur de DJ citée
      // par Mixgraph, audit du 26/10) : quand l'énergie baisse, frein ou filtre seulement.
      drop: energy > 1.5 ? ['montee', 'montee_courte', 'frein_doux']
        : energy < -1.5 ? ['frein_doux', 'filtre'] : ['montee_courte', 'montee', 'frein_doux'],
      relaxed: energy < -1.5 ? ['filtre', 'frein_doux'] : ['filtre', 'montee_courte'],
      blend: ['melange'], swap: ['drop_swap'],
    };
    let raison = 'choisi à la main';
    if (mode === 'auto') {
      const pool = pools[type];
      const recent = history.slice(-2);
      const fresh = pool.filter((m) => !recent.includes(m));
      // Hasard parmi les 3 mieux adaptés, pondéré par la place (énergie) et par la note moyenne donnée à
      // l'écoute (un style noté 5 sort ~2,8 fois plus qu'un style noté 3 ; 3,5 tant qu'il n'est pas noté)
      const top = (fresh.length ? fresh : pool).slice(0, 3);
      const w = Object.fromEntries(top.map((m, i) => [m, (notes[m] ?? 3.5) ** 2 * [1.5, 1, 0.6][i]]));
      mode = sample(w);
      const keyTxt = keyD === null ? 'tonalité incertaine' : `${camelotName(ca)} → ${camelotName(cb)}${keyD <= 1 ? ' compatibles' : ''}`;
      raison = `${TYPES[type]} ; tempos à ${(gap * 100).toFixed(0)} %, ${keyTxt}, `
        + `${energy > 1.5 ? "l'énergie monte" : energy < -1.5 ? "l'énergie redescend" : 'énergie stable'} : ${LABELS[mode] ?? mode}`;
    }
    // Durée d'une mesure : médiane des 8 mesures fiables autour du point, gardée seulement si elle colle au
    // tempo du morceau à 5 % près ; sinon le tempo fait foi. Les mesures d'une fin de morceau sont souvent
    // irrégulières dans l'analyse (1,20 s relevé au lieu de 1,50 s) : la boucle de A tombait hors temps.
    const barAt = (d, t, before) => {
      const ref = 240 / d.track.tempo;
      let k = d.bars.findIndex((x) => x.start >= t - 0.05);
      if (k < 0) k = d.bars.length;
      const sel = (before ? d.bars.slice(Math.max(0, k - 8), k) : d.bars.slice(k, k + 8))
        .filter((x) => x.confidence > 0.3).map((x) => x.duration).sort((x, y) => x - y);
      const med = sel[sel.length >> 1];
      return med && Math.abs(med / ref - 1) < 0.05 ? med : ref;
    };
    const bar_s = barAt(a, best.i.start, true), bar_b_s = barAt(b, entry.start, entry.start > 4 * entry.duration);
    // B lancé avant son entrée pour monter sous A : 8 mesures DE A (la montée dure alors 8 mesures entendues,
    // même si B est à tempo moitié), 1 mesure de B pour le drop swap, rien pour le mélange qui superpose déjà
    // A et B
    const preOf = (m) => Math.min(m === 'melange' ? 0 : m === 'drop_swap' ? bar_b_s : PRE_BARS * bar_s, entry.start);
    let pre = preOf(mode);
    // Avance trop courte pour ce style (après un mélange, à tempo lent) : il serait prêt trop tard et Spotify
    // aurait déjà sauté. Repli sur la montée courte (une mesure de A rejouée), avec l'avance de B que la
    // maquette peut tenir (vérifiée elle aussi : sinon le repli serait prêt trop tard à son tour).
    if (delay < needS(mode, bar_s, bar_b_s, pre, blendBars)) {
      raison += ` ; avance trop courte (${delay.toFixed(0)} s) pour ${LABELS[mode] ?? mode} : montée courte`;
      mode = 'montee_courte';
      type = typeOf(mode);
      pre = shortPre(delay, bar_s, bar_b_s, entry.start);
    }
    // mêmes bornes que la maquette : un ordre refusé après le saut donnerait la coupe sèche
    if (!(bar_s > 0.3 && bar_s < 5 && pre < 40 && ratio > 0.3 && ratio < 3)) return { erreur: 'mesures ou tempos hors limites' };
    // Grilles de temps de Spotify autour des points de raccord, pour que la maquette cale sur les vrais temps
    // (relatives à la sortie de A et au lancement de B) : la frappe la plus forte, en rap, tombe souvent à
    // contretemps et décalait B d'une fraction de temps (−235 ms mesurés le 26/10).
    const grid = (d, t0, t1, ref) => d.beats.filter((x) => x.start >= t0 && x.start <= t1).slice(-80)
      .map((x) => +(x.start - ref).toFixed(3));
    const beatsA = grid(a, best.i.start - 16 * bar_s, best.i.start + 0.05, best.i.start);
    const beatsB = grid(b, entry.start - pre - 0.05, entry.start + 8 * bar_b_s, entry.start - pre);
    return { mode, type, raison, beatsA, beatsB, bars: blendBars, bar_s: +bar_s.toFixed(4), bar_b_s: +bar_b_s.toFixed(4), ratio, pre_s: +pre.toFixed(3),
      bStart: entry.start - pre, tempoA: +a.track.tempo.toFixed(1), tempoB: +b.track.tempo.toFixed(1),
      sortieA: +best.i.start.toFixed(2), entreeB: +entry.start.toFixed(2), dropB: +drop.start.toFixed(2) };
  }
  // Avance (s) dont la maquette a besoin pour être prête avant de jouer : mesures de A rejouées, avance de B,
  // 2 mesures de B après son drop (gain, recalage), et le calcul
  const needS = (mode, bar_s, bar_b_s, pre, bars = 8) => mode === 'melange'
    ? bars * bar_s + bars * bar_b_s + 2 * bar_b_s + 6
    : (REAL_BARS[mode] ?? 4) * bar_s + pre + 2 * bar_b_s + 6;
  // Avance de B que la montée courte peut se permettre avec l'avance donnée (au moins 2 mesures de A)
  const shortPre = (delay, bar_s, bar_b_s, entryStart) =>
    Math.min(Math.max(2 * bar_s, delay - (bar_s + 2 * bar_b_s + 6)), PRE_BARS * bar_s, entryStart);

  // ── Saut pile sur le temps ───────────────────────────────────────────────────────────────────────
  // Rend l'heure du saut, ou null s'il a été annulé (morceau changé à la main, ou pause, pendant l'attente).
  async function switchAt(exitMs, B, bStartS, ctx) {
    const aUri = P.data?.item?.uri;
    while (exitMs - P.getProgress() > LEAD) {
      if (P.data?.item?.uri !== aUri || P.data?.isPaused) return null;
      await sleep(Math.max(4, (exitMs - P.getProgress() - LEAD) / 2));
    }
    const t_wall = Date.now();
    const seekTo = Math.round(bStartS * 1000);
    // ce changement de morceau vient de nous : pas de rattrapage en plus (comparé à l'heure et non à l'uri,
    // que Spotify peut remplacer par une autre version du morceau)
    expectedAt = Date.now();
    if (ctx?.uri && B.uid && !ctx.uri.startsWith('spotify:track:')) {
      await API.play({ uri: ctx.uri, url: ctx.url }, {}, { skipTo: { uid: B.uid, uri: B.uri }, seekTo });
    } else {
      await API.play({ uri: B.uri }, {}, { seekTo });  // hors playlist (file, lecture auto) : B seul
    }
    return t_wall;
  }

  // Rend null si la maquette a accepté l'ordre, sinon la raison du refus
  async function sendOrder(order) {
    try {
      const r = await fetch(`${MAQUETTE}/order`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(order) });
      if (r.ok) return null;
      return (await r.json().catch(() => ({}))).message ?? `erreur ${r.status}`;
    } catch { return 'maquette injoignable'; }
  }

  // ── Mode automatique ─────────────────────────────────────────────────────────────────────────────
  // history : préréglages joués ; types : types joués ; log : dernières transitions (historique de l'app)
  const status = { enabled: false, text: 'Mode DJ automatique éteint.', plan: null, history: [], types: [], log: [] };
  let maquetteOk = false, maquetteBusy = false, delay = 0, target = 60, lastCheck = 0, expectedAt = 0, notes = {};
  const readState = async () => {
    try {
      const r = await fetch(`${MAQUETTE}/state`, { cache: 'no-store' });
      maquetteOk = r.ok;
      if (r.ok) ({ delay_s: delay = 0, target_s: target = 60, busy: maquetteBusy = false, notes = {} } = await r.json());
    } catch { maquetteOk = false; }
  };
  const isOn = () => Spicetify.LocalStorage.get(KEY) === '1';
  const nextTrack = () => (Spicetify.Queue?.nextTracks ?? []).map((t) => t.contextTrack).find((t) => t?.uri?.startsWith('spotify:track:'));

  // ── Morceau suivant choisi par le mode DJ (refonte du 26/10) ───────────────────────────────────────
  // Comme le « Smart Reorder » de Spotify : au lieu de l'ordre de la playlist (où les tempos sautent de 98 à
  // 157 BPM), le suivant est le morceau de la playlist de départ le plus compatible avec celui qui joue
  // (tempo à 3 % près, double / moitié compris, tonalité voisine), pour que la transition soit une vraie
  // superposition. Les playlists ne sont jamais modifiées : B est lancé directement.
  const pool = { ctx: null, items: [] };
  const played = new Set();
  // Genre : l'API des genres n'est pas joignable depuis l'extension. On garde les morceaux dont un artiste
  // figure dans les playlists de référence du développeur (rap FR, shatta, bouyon) : sans ça, une grande
  // playlist fourre-tout (« All song ») faisait enchaîner sur du metal.
  const GENRE_REFS = ['4qKKSgcuPJ9D1DGwAAqquG', '39NDse2QZPhw2FMFO76C6N', '7xvIav5szRrdPSlZzKVTMh', '33T2yN3jibAPkkyhK1IC5g',
    '2UM5OkfUVT6BZkZ0j9Wpwp', '6Fs4BkSykcFsqz9XMXdpmU', '0WzHAU6W4iSq1n1s0zD3L3'];
  const contents = async (uri) => {
    let items = [];
    for (let off = 0; off < 5000; off += 500) {
      const c = await Spicetify.Platform.PlaylistAPI.getContents(uri, { limit: 500, offset: off });
      items = items.concat(c.items);
      if (c.items.length < 500) break;
    }
    return items;
  };
  let genreArtists = null;
  async function loadPool() {
    const ctx = P.data?.context?.uri;
    if (!ctx?.startsWith('spotify:playlist:') || pool.ctx === ctx) return;
    if (!genreArtists) {
      genreArtists = new Set();
      for (const id of GENRE_REFS) {
        for (const it of await contents(`spotify:playlist:${id}`).catch(() => [])) for (const a of it.artists ?? []) genreArtists.add(a.name);
      }
    }
    const items = (await contents(ctx)).filter((i) => i.uri?.startsWith('spotify:track:'));
    const inGenre = items.filter((i) => (i.artists ?? []).some((a) => genreArtists.has(a.name)));
    pool.ctx = ctx;
    pool.items = (inGenre.length >= 20 ? inGenre : items)
      .map((i) => ({ uri: i.uri, metadata: { title: i.name, artist_name: i.artists?.[0]?.name ?? '' } }));
  }
  async function chooseNext(aUri, aArtist) {
    const a = await audio(aUri).catch(() => null);
    if (!a?.track || !pool.items.length) return null;
    const cands = pool.items.filter((t) => t.uri !== aUri && !played.has(t.uri)).sort(() => Math.random() - 0.5).slice(0, 40);
    let best = null;
    for (const t of cands) {
      const b = await audio(t.uri).catch(() => null);
      if (!b?.bars?.length || !b.sections?.length) continue;
      const gap = Math.exp(tempoGap(a.track.tempo, b.track.tempo)) - 1;
      const kd = camelotDist(camelot(a.track), camelot(b.track));
      const score = gap * 100 + (kd === null ? 1 : kd >= 3 ? 5 : kd) + (t.metadata.artist_name === aArtist ? 2 : 0)
        + Math.abs(a.track.loudness - b.track.loudness) / 3;
      if (!best || score < best.score) best = { score, gap, track: t };
    }
    return best;
  }
  // Refrain doublé : chaque superposition réelle consomme ~8 mesures d'avance ; on les regagne en rejouant
  // une fois 8 mesures d'un refrain de B, comme un DJ de rap.
  async function maybeDouble(item) {
    const d = status.double;
    if (!d || d.done || d.uri !== item.uri || delay > target - 3) return;
    if (!d.from) {
      const b = await audio(item.uri).catch(() => null);
      if (!b?.bars?.length) { d.done = true; return; }
      const med = [...b.sections].map((s) => s.loudness).sort((x, y) => x - y)[b.sections.length >> 1];
      const sec = b.sections.find((s) => s.start >= d.after && s.loudness >= med && s.duration >= 8 * 240 / b.track.tempo);
      const k = sec ? b.bars.findIndex((x) => x.start >= sec.start - 0.05) : -1;
      if (k < 0 || k + 8 >= b.bars.length || b.bars[k + 8].start > 0.7 * b.track.duration) { d.done = true; return; }
      Object.assign(d, { from: b.bars[k].start, to: b.bars[k + 8].start, bar_s: (b.bars[k + 8].start - b.bars[k].start) / 8 });
    }
    if (P.getProgress() / 1000 < d.to + 1.5) return;
    d.done = true;
    try {
      const r = await fetch(`${MAQUETTE}/double`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ uri: item.uri, from_s: d.from, to_s: d.to, bar_s: d.bar_s }) });
      if (r.ok) status.log = [{ at: Date.now(), mode: 'refrain', label: 'refrain doublé', A: item.name, B: item.name,
        raison: 'avance regagnée' }, ...status.log].slice(0, 8);
    } catch { /* la maquette ne répond pas : rien à regagner */ }
  }

  async function tick() {
    status.enabled = isOn();
    const item = P.data?.item;
    if (!status.enabled) { status.plan = null; status.text = 'Mode DJ automatique éteint.'; return; }
    if (!item?.uri?.startsWith('spotify:track:')) { status.text = 'En attente d\'un morceau.'; return; }
    played.add(item.uri);
    await loadPool();
    if (pool.items.length && status.next?.forUri !== item.uri) {
      status.next = { forUri: item.uri, pick: null };
      status.text = 'Recherche du morceau suivant le plus compatible…';
      status.next.pick = await chooseNext(item.uri, item.artists?.[0]?.name);
    }
    const B = status.next?.forUri === item.uri && status.next.pick ? status.next.pick.track : nextTrack();
    const p = status.plan;
    if (p && (p.forUri !== item.uri || (!p.done && B && p.B.uri !== B.uri))) status.plan = null;  // morceau ou file changés
    if (Date.now() - lastCheck > 5000) { lastCheck = Date.now(); await readState(); }
    await maybeDouble(item);
    // Un test lancé depuis l'écran (run.sh) pilote Spotify lui-même : le mode auto se met en veille
    if (maquetteBusy) { status.plan = null; status.text = 'Test manuel en cours : mode auto en veille.'; return; }
    if (!status.plan) {
      if (!B) { status.text = 'Pas de morceau suivant dans la file.'; return; }
      // Sans maquette, un saut couperait le morceau sans transition : on ne prévoit rien.
      if (!maquetteOk) { status.text = 'Maquette éteinte : Spotify joue normalement, sans transition.'; return; }
      try {
        const choix = await planTransition(item.uri, B.uri, { history: status.history, types: status.types, delay, target, notes,
          minExit: P.getProgress() / 1000 + MARGIN_S });
        status.plan = { forUri: item.uri, A: item.name, B, choix, done: false, failed: !!choix.erreur };
        status.text = choix.erreur ? `Pas de transition pour ce morceau : ${choix.erreur}.` : `Prévu : ${LABELS[choix.mode] ?? choix.mode} vers « ${B.metadata?.title ?? 'suivant'} » à ${fmt(choix.sortieA)}.`;
      } catch (e) { status.plan = { forUri: item.uri, B, failed: true }; status.text = `Analyse impossible : ${e}`; }
    }
    const q = status.plan;
    if (!q || q.done || q.failed || !q.choix) return;
    const exitMs = q.choix.sortieA * 1000;
    const remaining = exitMs - P.getProgress();
    if (remaining < -500) { q.failed = true; status.text = 'Point de sortie dépassé (saut manuel ?) : pas de transition.'; return; }
    if (remaining > 1500 || P.data?.isPaused) return;
    q.done = true;
    // Juste avant le saut, l'avance réelle : elle a pu fondre depuis la planification (mélange entre-temps)
    await readState();
    if (!maquetteOk || maquetteBusy) { q.failed = true; status.text = 'Maquette indisponible au moment du saut : pas de transition.'; return; }
    const c = q.choix;
    if (delay < needS(c.mode, c.bar_s, c.bar_b_s, c.pre_s, c.bars)) {
      c.raison += ` ; avance tombée à ${delay.toFixed(0)} s : montée courte`;
      c.mode = 'montee_courte';
      c.type = typeOf(c.mode);  // la chaîne de Markov doit suivre ce qui a vraiment joué
      c.pre_s = +shortPre(delay, c.bar_s, c.bar_b_s, c.entreeB).toFixed(3);
      c.bStart = c.entreeB - c.pre_s;
    }
    const ctx = P.data?.context;
    const t_wall = await switchAt(exitMs, q.B, q.choix.bStart, ctx);
    if (t_wall === null) { q.failed = true; status.text = 'Saut annulé (morceau changé ou pause).'; return; }
    status.history = [...status.history, q.choix.mode].slice(-10);
    status.types = [...status.types, q.choix.type].slice(-10);
    status.log = [{ at: Date.now(), mode: q.choix.mode, label: LABELS[q.choix.mode] ?? q.choix.mode, A: q.A,
      B: q.B.metadata?.title ?? '', raison: q.choix.raison }, ...status.log].slice(0, 8);
    const gapless = !!(ctx?.uri && q.B.uid && !ctx.uri.startsWith('spotify:track:'));  // saut dans la playlist
    const refus = await sendOrder({ ...q.choix, t_wall, gapless });
    // Refrain doublé désactivé : « absolument horrible, recommence pas » (essai 29). maybeDouble ne fait rien
    // tant que status.double reste vide.
    status.double = null;
    status.text = refus === null ? `Transition lancée vers « ${q.B.metadata?.title ?? 'suivant'} » : elle s'entendra dans la maquette.`
      : `La maquette a refusé l'ordre (${refus}) : saut fait sans transition.`;
  }
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  // Morceau changé sans nous (bouton suivant, fin naturelle après un saut raté) : la maquette fait monter les
  // premières mesures de B sous une boucle de A (montée courte, sans avance de B) au lieu d'un saut brut.
  let prev = { uri: P.data?.item?.uri, progress: 0 };
  setInterval(() => { if (P.data?.item?.uri === prev.uri) prev.progress = P.getProgress(); }, 500);
  P.addEventListener('songchange', async () => {
    const uri = P.data?.item?.uri, from = prev;
    prev = { uri, progress: 0 };
    if (Date.now() - expectedAt < 3000) return;
    await readState();  // l'état d'il y a 5 s peut ignorer un test manuel qui vient de démarrer
    if (!isOn() || !maquetteOk || maquetteBusy || !from.uri?.startsWith('spotify:track:') || !uri?.startsWith('spotify:track:')
      || from.uri === uri || from.progress < 10000) return;
    // l'événement arrive après le changement dans le flux ; la maquette le situe d'après ce qu'espion a vu
    const t_wall = Date.now() - 300;
    try {
      const [a, b] = await Promise.all([audio(from.uri), audio(uri)]);
      const median = (d) => {
        const v = (d?.bars ?? []).filter((x) => x.confidence > 0.3).map((x) => x.duration).sort((x, y) => x - y);
        return v[Math.floor(v.length / 2)];
      };
      const bar_s = median(a), bar_b_s = median(b);
      if (!bar_s || !b?.track) return;
      const order = { mode: 'montee_courte', type: 'manuel', raison: 'morceau changé sans transition prévue : B monte sur ses premières mesures',
        bar_s, bar_b_s, ratio: a.track.tempo / b.track.tempo, pre_s: 0, t_wall, manuel: true, to_uri: uri, sortieA: null, entreeB: 0 };
      const refus = await sendOrder(order);
      status.text = refus === null ? 'Morceau changé à la main : transition de rattrapage envoyée.' : `Rattrapage refusé : ${refus}.`;
    } catch (e) { status.text = `Rattrapage impossible : ${e?.message ?? e}`; }
  });

  let busy = false;
  setInterval(async () => {
    if (busy) return;
    busy = true;
    try { await tick(); } catch (e) {
      // une erreur (saut refusé par Spotify, analyse illisible) ne doit pas passer inaperçue
      console.error('dj-auto', e);
      status.text = `Erreur du mode auto : ${e?.message ?? e}`;
    } finally { busy = false; }
  }, 250);

  window.DJ = {
    planTransition, switchAt, sendOrder, status, LABELS, TYPES,
    setAuto: (on) => { Spicetify.LocalStorage.set(KEY, on ? '1' : '0'); status.plan = null; },
  };
})();
