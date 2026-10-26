// App Spicetify « Mode DJ » : affiche dans Spotify, en direct, ce que joue la maquette E2 (proto/e2/), et
// allume le mode DJ automatique (extension dj-auto.js). Page en 2 colonnes à la hauteur de l'écran :
// - à gauche : ce qu'on entend, le cercle façon Eternal Jukebox du morceau entendu (temps colorés par
//   section, aiguille, zone de transition), le cercle du morceau qui arrive, le visualiseur ;
// - à droite : l'interrupteur du mode automatique, la frise de la transition, la file à venir, et le
//   lancement manuel d'une transition de test.
const MAQUETTE = 'http://127.0.0.1:47802';
const React = Spicetify.React;
const h = React.createElement;
const { useState, useEffect, useRef } = React;

const PAIRS = [
  ['Money Pull Up → SO COMAN', '7Lr0PGZVb4EzyIhCIETFlG', '6W0iLz8aOKUzObanCzJj2U'],
  ['Tic → La Choré Des Shattas', '1rO9az1C7u2RXUK0E9YfUi', '1lpYczTQkuPn075NYrGyea'],
  ['Shatta Mad → Shatta (DJ Chinwax)', '08bOtraHk8waBUt6sQOZce', '3u023dY0esoiIcGwX1y6uu'],
  ['KONGOLESE SOUS BBL → Jumping Jack', '5dBRz6giSIBDkXOhOD80KF', '5uGVj3IDPsRFRyd5QwIpft'],
  ['Am to Pm → De Rum', '1xaz7OFM1Jnw8eVUdeFgcy', '2f5LK3pm7L3TsdMC205lbo'],
  ['Alpha → Laptop', '2dVDbbS9W6n6YY80R4aJdZ', '7e2vCAtcYXuM8JOUqIZ9GQ'],
];
const MODES = [['auto', 'Auto'], ['montee', 'Montée'], ['melange', 'Mélange'], ['montee_courte', 'Montée courte'],
  ['echo_doux', 'Écho'], ['retour_doux', 'Retour arrière'], ['frein_doux', 'Frein'], ['filtre', 'Balayage de filtre']];
const KEYS = ['Do', 'Do#', 'Ré', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'];
const C = { a: '#4f8cff', b: '#ff5ea8', zone: '#ffb020', head: '#1ed760', line: 'rgba(255,255,255,.10)', sub: 'rgba(255,255,255,.6)' };

const CSS = `
.djm { color: var(--spice-text); padding: 18px 24px; box-sizing: border-box; display: grid; gap: 14px;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); }
.djm * { box-sizing: border-box; }
.djm-col { display: flex; flex-direction: column; gap: 14px; min-height: 0; }
.djm-card { background: var(--spice-card); border-radius: 14px; padding: 14px 16px; min-height: 0;
  border: 1px solid rgba(255,255,255,.04); transition: box-shadow .4s, border-color .4s; animation: djm-in .45s ease both; }
.djm-card.live { border-color: rgba(255,176,32,.6); box-shadow: 0 0 24px rgba(255,176,32,.18); }
.djm-label { font-size: 11px; letter-spacing: .09em; text-transform: uppercase; opacity: .6; margin-bottom: 6px; }
.djm-head { font-size: 26px; font-weight: 800; line-height: 1.15; animation: djm-in .35s ease both; }
.djm-count { color: ${C.zone}; font-weight: 700; margin-top: 2px; font-variant-numeric: tabular-nums; }
.djm-switch { display: flex; align-items: center; gap: 14px; cursor: pointer; user-select: none; }
.djm-track { width: 54px; height: 30px; border-radius: 999px; background: rgba(255,255,255,.18); position: relative; transition: background .25s; flex: none; }
.djm-track::after { content: ''; position: absolute; top: 3px; left: 3px; width: 24px; height: 24px; border-radius: 50%; background: #fff; transition: transform .25s cubic-bezier(.3,1.4,.6,1); }
.djm-switch.on .djm-track { background: ${C.head}; }
.djm-switch.on .djm-track::after { transform: translateX(24px); }
.djm-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.djm select { flex: 1 1 140px; min-width: 0; padding: 7px 8px; border-radius: 8px; background: rgba(255,255,255,.06); color: var(--spice-text); border: 1px solid ${C.line}; }
.djm button { padding: 7px 14px; border-radius: 999px; border: 0; font-weight: 700; cursor: pointer; background: rgba(255,255,255,.1); color: var(--spice-text); transition: transform .12s, opacity .2s; }
.djm button:hover:not(:disabled) { transform: scale(1.04); }
.djm button.go { background: ${C.head}; color: #000; }
.djm button:disabled { opacity: .4; cursor: not-allowed; }
.djm-chip { display: inline-block; font-size: 11px; padding: 3px 8px; border-radius: 999px; background: rgba(255,255,255,.07); margin: 4px 4px 0 0; }
.djm-q { display: flex; justify-content: space-between; gap: 8px; padding: 6px 0; border-bottom: 1px solid ${C.line}; font-size: 13px; animation: djm-in .35s ease both; }
.djm-q:last-child { border-bottom: 0; }
.djm-ell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.djm-steps { display: flex; gap: 6px; margin-top: 8px; }
.djm-step { flex: 1; position: relative; overflow: hidden; border-radius: 8px; background: rgba(255,255,255,.06); padding: 6px 8px; font-size: 11px; min-width: 0; }
.djm-step .fill { position: absolute; inset: 0; width: 0; background: rgba(255,176,32,.28); transition: width .15s linear; }
.djm-step.on { color: ${C.zone}; font-weight: 700; }
.djm-step.done { opacity: .5; }
.djm-step span { position: relative; }
.djm-cap { text-align: center; margin-top: 6px; }
.djm-cap b { display: block; font-size: 14px; }
.djm-hist { display: flex; gap: 8px; align-items: center; padding: 5px 0; font-size: 12px; border-bottom: 1px solid ${C.line}; animation: djm-in .35s ease both; }
.djm-hist:last-child { border-bottom: 0; }
.djm-tag { flex: none; padding: 2px 8px; border-radius: 999px; font-weight: 700; font-size: 11px; color: #111; }
@keyframes djm-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes djm-pulse { 0%,100% { opacity: .55; } 50% { opacity: 1; } }
`;

// ── Données ────────────────────────────────────────────────────────────────────────────────────────
function useMaquette() {
  const [s, set] = useState({ state: null, offline: true });
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try { const r = await fetch(`${MAQUETTE}/state`, { cache: 'no-store' }); if (alive) set({ state: await r.json(), offline: false }); }
      catch { if (alive) set((p) => ({ ...p, offline: true })); }
    };
    tick();
    const t = setInterval(tick, 120);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return s;
}

const analyses = new Map();
function useAnalysis(uri) {
  const [a, set] = useState(() => analyses.get(uri) ?? null);
  useEffect(() => {
    if (!uri) return set(null);
    if (analyses.has(uri)) return set(analyses.get(uri));
    let alive = true;
    Spicetify.getAudioData(uri).then((d) => { analyses.set(uri, d); if (alive) set(d); }).catch(() => {});
    return () => { alive = false; };
  }, [uri]);
  return a;
}

function useSize(ref) {
  const [size, set] = useState({ w: 0, h: 0 });
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => set({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return size;
}

// Quoi montrer : morceau entendu (A), morceau suivant (B), transition concernée et temps écoulé dedans.
function view(st) {
  const x = st?.current ?? st?.next ?? st?.last ?? null;
  if (!x) return { aUri: st?.heard?.uri, aPos: st?.heard?.pos_s, x: null };
  const t = st.current ? st.current.elapsed_s : st.next ? -st.next.in_s : st.last.elapsed_s;
  if (t < x.dur_s) return { aUri: x.from_uri ?? st.heard?.uri, aPos: (x.sortieA ?? 0) - x.dur_s + t, x, t, bUri: x.to_uri };
  return { aUri: x.to_uri, aPos: st.heard?.pos_s, x, t, after: true };
}

// ── Cercle façon Eternal Jukebox ───────────────────────────────────────────────────────────────────
function Circle({ analysis, pos, zone, mark, color, title, sub, size, live }) {
  const ref = useRef(null);
  const data = useRef({});
  data.current = { analysis, pos, zone, mark, live, at: performance.now() };
  useEffect(() => {
    let raf, lastBeat = -1, flash = 0;
    const dpr = window.devicePixelRatio || 1;
    const draw = () => {
      const cv = ref.current;
      if (!cv) return;
      const W = size * dpr, g = cv.getContext('2d');
      if (cv.width !== W) { cv.width = W; cv.height = W; }
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, size, size);
      const { analysis: an, pos: p0, zone: z, mark: mk, live: lv, at } = data.current;
      const cx = size / 2, cy = size / 2, R = size / 2 - 16;
      if (!an?.beats?.length) {
        g.fillStyle = C.sub; g.font = '13px sans-serif'; g.textAlign = 'center'; g.fillText('analyse…', cx, cy);
        raf = requestAnimationFrame(draw); return;
      }
      const dur = an.track.duration, p = p0 == null ? null : p0 + (performance.now() - at) / 1000;
      const ang = (s) => -Math.PI / 2 + (s / dur) * Math.PI * 2;
      const secs = an.sections;
      const secOf = (s) => Math.max(0, secs.findIndex((x, i) => s >= x.start && (i === secs.length - 1 || s < secs[i + 1].start)));
      let cur = -1;
      an.beats.forEach((b, k) => { if (p != null && b.start <= p && p < b.start + b.duration) cur = k; });
      if (cur !== lastBeat && cur >= 0) { lastBeat = cur; flash = 1; }
      flash *= 0.9;
      // halo central qui pulse sur chaque temps (doré pendant une transition)
      const glow = g.createRadialGradient(cx, cy, 0, cx, cy, R * 0.75);
      glow.addColorStop(0, lv ? `rgba(255,176,32,${0.10 + 0.25 * flash})` : `rgba(79,140,255,${0.05 + 0.18 * flash})`);
      glow.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = glow; g.beginPath(); g.arc(cx, cy, R * 0.75, 0, Math.PI * 2); g.fill();
      an.beats.forEach((b, k) => {
        const i = secOf(b.start), inZone = z && b.start >= z[0] && b.start <= z[1], now = k === cur;
        const played = p != null && b.start < p;
        g.strokeStyle = now ? '#fff' : inZone ? C.zone : `hsla(${(i * 47) % 360} 75% ${58 + (secs[i].loudness + 15)}% / ${played ? 0.95 : 0.5})`;
        g.lineWidth = now ? 4.5 : 2.6;
        const a = ang(b.start), r0 = now ? R - 18 - 6 * flash : inZone ? R - 14 : R - 9;
        g.beginPath(); g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); g.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); g.stroke();
      });
      if (mk != null) {
        const a = ang(mk), x = cx + Math.cos(a) * (R + 9), y = cy + Math.sin(a) * (R + 9);
        g.fillStyle = C.zone; g.beginPath(); g.arc(x, y, 5 + 2 * Math.sin(performance.now() / 200), 0, Math.PI * 2); g.fill();
      }
      if (p != null && p >= 0 && p <= dur) {
        const a = ang(p), r = R - 24;
        g.strokeStyle = C.head; g.lineWidth = 2; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); g.stroke();
        g.fillStyle = C.head; g.shadowColor = C.head; g.shadowBlur = 12;
        g.beginPath(); g.arc(cx + Math.cos(a) * r, cy + Math.sin(a) * r, 5, 0, Math.PI * 2); g.fill(); g.shadowBlur = 0;
      }
      // au centre, seulement le temps (le nom du morceau est sous le cercle, l'aiguille ne le recouvre plus)
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillStyle = color; g.font = `800 ${Math.max(14, size / 9)}px sans-serif`;
      g.fillText(p != null ? `${Math.floor(p / 60)}:${String(Math.floor(p % 60)).padStart(2, '0')}` : '', cx, cy);
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [color, size]);
  return h('div', { style: { flex: 'none' } },
    h('canvas', { ref, style: { width: size, height: size, display: 'block' } }),
    h('div', { className: 'djm-cap', style: { width: size } },
      h('b', { className: 'djm-ell', style: { color } }, title ?? '…'),
      h('span', { style: { opacity: 0.6, fontSize: 12 } }, sub ?? '')));
}

function Spectrum({ levels }) {
  return h('div', { style: { display: 'flex', alignItems: 'flex-end', gap: 3, height: 56, flex: 'none' } },
    (levels ?? new Array(16).fill(0)).map((v, i) => h('div', { key: i, style: {
      flex: 1, height: `${Math.max(4, v * 100)}%`, borderRadius: 3, transition: 'height .12s linear',
      background: `linear-gradient(to top, ${C.a}, ${i < 4 ? C.b : C.head})`, opacity: 0.55 + 0.45 * v } })));
}

function Frise({ x, t }) {
  if (!x) return h('div', { style: { opacity: 0.55, padding: '10px 0' } }, 'Aucune transition prévue pour l\'instant.');
  const dur = Math.max(x.dur_s, 0.01), t0 = -8, t1 = dur + 8, pct = (u) => `${((u - t0) / (t1 - t0)) * 100}%`;
  const w = (a, b) => `${((b - a) / (t1 - t0)) * 100}%`, bFrom = (x.b_from ?? 1) * dur;
  const bar =(left, width, color, faded) => h('div', { style: { position: 'absolute', left, width, top: 0, height: 16, borderRadius: 5, background: color, opacity: faded ? 0.35 : 1 } });
  const label = (text, color, left) => h('div', { className: 'djm-ell', style: { position: 'absolute', top: -16, left, maxWidth: '60%', color, fontWeight: 700, fontSize: 11 } }, text);
  const steps = [...(x.phases ?? []).map(([name, a, b]) => [name, a * dur, b * dur]), [`${x.to ?? 'B'} seul`, dur, dur + 1e9]];
  return h('div', null,
    h('div', { style: { position: 'relative', height: 64, margin: '18px 0 4px' } },
      h('div', { style: { position: 'absolute', left: pct(0), width: w(0, dur), top: -4, bottom: 0, background: 'rgba(255,176,32,.06)', borderLeft: '1px dashed #777', borderRight: '1px dashed #777' } }),
      h('div', { style: { position: 'absolute', top: 0, left: 0, right: 0, height: 16 } }, label(`A · ${x.from ?? '?'} (finit)`, C.a, 0), bar(0, w(t0, 0), C.a), bar(pct(0), w(0, dur), C.a, true)),
      h('div', { style: { position: 'absolute', top: 44, left: 0, right: 0, height: 16 } }, label(`B · ${x.to ?? '?'} (arrive)`, C.b, pct(Math.min(bFrom, dur - 0.01))), bar(pct(bFrom), w(bFrom, dur), C.b, bFrom < dur), bar(pct(dur), w(dur, t1), C.b)),
      h('div', { style: { position: 'absolute', top: -6, bottom: 0, width: 3, borderRadius: 2, left: pct(Math.min(t1, Math.max(t0, t))), background: C.head, boxShadow: `0 0 10px ${C.head}` } })),
    // étapes numérotées, l'étape en cours se remplit
    h('div', { className: 'djm-steps' }, steps.map(([name, a, b], k) => {
      const on = t >= a && t < b, done = t >= b, fill = on && b < 1e8 ? ((t - a) / (b - a)) * 100 : done ? 100 : 0;
      return h('div', { key: name, className: `djm-step ${on ? 'on' : ''} ${done ? 'done' : ''}`, title: name },
        h('div', { className: 'fill', style: { width: `${fill}%` } }),
        h('span', { className: 'djm-ell', style: { display: 'block' } }, `${k + 1} · ${name}`));
    })));
}

const TAGS = { melange: '#1ed760', montee: '#ffb020', montee_courte: '#ff8a3d', echo_doux: '#7aa7ff', retour_doux: '#c38bff',
  frein_doux: '#ff5e7a', filtre: '#4fd1c5' };
function History() {
  const [, force] = useState(0);
  useEffect(() => { const t = setInterval(() => force((n) => n + 1), 1000); return () => clearInterval(t); }, []);
  const log = window.DJ?.status?.log ?? [];
  if (!log.length) return h('div', { style: { opacity: 0.55, fontSize: 12 } }, 'Aucune transition automatique pour l\'instant.');
  const ago = (ms) => { const s = Math.round((Date.now() - ms) / 1000); return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min`; };
  return h('div', null, log.slice(0, 5).map((e) => h('div', { key: e.at, className: 'djm-hist' },
    h('span', { className: 'djm-tag', style: { background: TAGS[e.mode] ?? '#ccc' } }, e.label),
    h('span', { className: 'djm-ell', style: { flex: 1 } }, `${e.A} → ${e.B}`),
    h('span', { style: { opacity: 0.5, flex: 'none' } }, `il y a ${ago(e.at)}`))));
}

function Queue({ plan }) {
  const [items, set] = useState([]);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      const next = (Spicetify.Queue?.nextTracks ?? []).map((t) => t.contextTrack).filter((t) => t?.uri?.startsWith('spotify:track:')).slice(0, 6);
      const rows = [];
      for (const t of next) {
        let tempo = null, key = null;
        try { const a = analyses.get(t.uri) ?? await Spicetify.getAudioData(t.uri); analyses.set(t.uri, a); tempo = Math.round(a.track.tempo); key = KEYS[a.track.key]; } catch {}
        rows.push({ uri: t.uri, name: t.metadata?.title ?? t.uri, artist: t.metadata?.artist_name ?? '', tempo, key });
      }
      if (alive) set(rows);
    };
    load();
    const t = setInterval(load, 8000);
    Spicetify.Player.addEventListener('songchange', load);
    return () => { alive = false; clearInterval(t); Spicetify.Player.removeEventListener('songchange', load); };
  }, []);
  if (!items.length) return h('div', { style: { opacity: 0.55 } }, 'File vide.');
  return h('div', null, items.map((r, i) => h('div', { key: r.uri + i, className: 'djm-q', style: { animationDelay: `${i * 40}ms` } },
    h('span', { className: 'djm-ell' }, h('b', null, r.name), ' ', h('span', { style: { opacity: 0.55 } }, r.artist)),
    h('span', { style: { flex: 'none', opacity: 0.85, fontVariantNumeric: 'tabular-nums' } },
      i === 0 && plan ? h('span', { style: { color: C.zone, marginRight: 8 } }, plan) : null, r.tempo ? `${r.tempo} BPM · ${r.key}` : '…'))));
}

function AutoSwitch() {
  const [, force] = useState(0);
  useEffect(() => { const t = setInterval(() => force((n) => n + 1), 500); return () => clearInterval(t); }, []);
  const dj = window.DJ;
  if (!dj) return h('div', { style: { opacity: 0.7 } }, 'Extension dj-auto absente : lancer spicetify/installer.sh.');
  const on = dj.status.enabled;
  return h('div', null,
    h('div', { className: `djm-switch ${on ? 'on' : ''}`, onClick: () => dj.setAuto(!on) },
      h('div', { className: 'djm-track' }),
      h('div', null, h('div', { style: { fontWeight: 800, fontSize: 16 } }, 'Mode DJ automatique'),
        h('div', { style: { opacity: 0.7, fontSize: 12 } }, on ? 'Chaque morceau enchaîne tout seul sur le suivant.' : 'Éteint : Spotify joue normalement.'))),
    h('div', { style: { marginTop: 8, fontSize: 13, color: on ? C.zone : C.sub, minHeight: 18 } }, dj.status.text));
}

function Manual({ st }) {
  const [pair, setPair] = useState('queue');
  const [mode, setMode] = useState('auto');
  const [msg, setMsg] = useState('');
  const blocked = !st?.can_run || st?.busy || !!st?.next || !!st?.current;
  const send = async (req) => {
    setMsg('Envoi…');
    try {
      const r = await fetch(`${MAQUETTE}/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req) });
      const j = await r.json();
      setMsg(r.ok ? 'C\'est parti : la transition arrive dans environ 1 minute.' : `Impossible : ${j.message}.`);
    } catch { setMsg('La maquette ne répond pas.'); }
  };
  const go = () => {
    if (pair === 'queue') {
      const a = Spicetify.Player.data?.item, b = (Spicetify.Queue?.nextTracks ?? []).map((t) => t.contextTrack).find((t) => t?.uri?.startsWith('spotify:track:'));
      if (!a || !b) return setMsg('Il faut un morceau en cours et un suivant dans la file.');
      return send({ mode, a: a.uri, b: b.uri, name: `${a.name} → ${b.metadata?.title ?? 'suivant'}` });
    }
    const [name, a, b] = PAIRS[+pair];
    send({ mode, a: `spotify:track:${a}`, b: `spotify:track:${b}`, name });
  };
  const sel = (value, onChange, options) => h('select', { value, onChange: (e) => onChange(e.target.value) }, options.map(([v, l]) => h('option', { key: v, value: v }, l)));
  return h('div', null,
    h('div', { className: 'djm-row' },
      sel(pair, setPair, [['queue', 'En cours → suivant'], ...PAIRS.map(([n], i) => [String(i), n])]),
      sel(mode, setMode, MODES),
      h('button', { className: 'go', onClick: go, disabled: blocked }, 'Tester'),
      h('button', { onClick: () => send(st.last_request), disabled: blocked || !st?.last_request }, 'Rejouer')),
    h('div', { style: { marginTop: 6, opacity: 0.7, fontSize: 12, minHeight: 16 } }, st?.busy && !st?.next ? 'Préparation : Spotify rejoue le morceau A…' : msg));
}

const card = (title, props, ...children) => h('div', { className: `djm-card ${props?.live ? 'live' : ''}`, style: props?.style },
  title ? h('div', { className: 'djm-label' }, title) : null, ...children);

function App() {
  const { state: st, offline } = useMaquette();
  const root = useRef(null), circles = useRef(null);
  const [height, setHeight] = useState(600);
  useEffect(() => {
    const fit = () => { if (root.current) setHeight(Math.max(480, window.innerHeight - root.current.getBoundingClientRect().top - 104)); };
    fit(); window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, []);
  const box = useSize(circles);
  const v = view(st);
  const aAn = useAnalysis(v.aUri), bAn = useAnalysis(v.bUri);
  const x = v.x, live = !!st?.current;
  let headline = st?.heard?.name ?? '…', count = '';
  if (x && v.t != null) {
    const ph = (x.phases ?? []).find(([, a, b]) => v.t >= a * x.dur_s && v.t < b * x.dur_s);
    if (v.t < 0) { headline = `${x.from ?? 'A'} seul`; count = `${x.label} dans ${(-v.t).toFixed(1)} s`; }
    else if (v.t < x.dur_s) { headline = ph ? ph[0] : `${x.label} en cours`; count = `encore ${(x.dur_s - v.t).toFixed(1)} s, puis ${x.to ?? 'B'} seul`; }
    else { headline = `${x.to ?? 'B'} seul`; count = `${x.label} terminée il y a ${(v.t - x.dur_s).toFixed(1)} s`; }
  }
  const zone = x && x.sortieA != null && !v.after ? [x.sortieA - x.dur_s, x.sortieA] : null;
  const twoCircles = !!v.bUri;
  const big = Math.max(150, Math.min(twoCircles ? box.w * 0.56 : box.w * 0.8, box.h - 50));
  const small = Math.max(110, Math.min(box.w - big - 24, big * 0.7));
  const pc = window.DJ?.status?.plan;
  const plan = pc?.choix && !pc.done && !pc.failed ? (window.DJ.LABELS?.[pc.choix.mode] ?? pc.choix.mode) : null;
  return h('div', { ref: root, className: 'djm', style: { height } },
    h('style', null, CSS),
    h('div', { className: 'djm-col' },
      card('Dans tes oreilles', { live },
        h('div', { className: 'djm-head', key: headline }, headline),
        h('div', { className: 'djm-count' }, offline ? 'Maquette éteinte : lance proto/e2/e2.py.' : count),
        st ? h('div', { style: { opacity: 0.55, fontSize: 12, marginTop: 4 } }, `${st.delay_s.toFixed(0)} s de retard sur Spotify, qui joue déjà « ${st.spotify?.name ?? '…'} »`) : null),
      card(null, { live, style: { flex: 1, display: 'flex', flexDirection: 'column', gap: 8 } },
        h('div', { ref: circles, style: { flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 } },
          box.w ? h(Circle, { analysis: aAn, pos: v.aPos, zone, live, color: C.a, size: big, title: v.after ? x?.to : (x?.from ?? st?.heard?.name), sub: aAn ? `${Math.round(aAn.track.tempo)} BPM · ${KEYS[aAn.track.key]}` : '' }) : null,
          twoCircles && box.w ? h(Circle, { analysis: bAn, pos: null, mark: x?.entreeB, color: C.b, size: small, title: x?.to, sub: bAn ? `${Math.round(bAn.track.tempo)} BPM · entre au point jaune` : '' }) : null),
        h(Spectrum, { levels: st?.levels }))),
    h('div', { className: 'djm-col' },
      card(null, null, h(AutoSwitch)),
      card(x ? `${x.label} : ${x.from ?? 'A'} → ${x.to ?? 'B'}` : 'Transition', { live },
        h(Frise, { x, t: v.t ?? 0 }),
        x?.raison ? h('div', { style: { opacity: 0.7, fontSize: 12 } }, `Pourquoi : ${x.raison}`) : null,
        x ? h('div', null, Object.entries(x.ingredients ?? {}).map(([k, val]) => h('span', { key: k, className: 'djm-chip' }, h('b', { style: { opacity: 0.6 } }, `${k} `), val))) : null),
      card('À venir dans la file', { style: { flex: 1, overflow: 'hidden' } }, h(Queue, { plan })),
      card('Dernières transitions', null, h(History),
        h('div', { style: { borderTop: `1px solid ${C.line}`, marginTop: 8, paddingTop: 8 } }, h(Manual, { st })))));
}

const render = () => h(App);
