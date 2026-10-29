// App Spicetify « Mode DJ » : affiche dans Spotify, en direct, ce que joue la maquette E2 (proto/e2/), allume le mode
// DJ automatique (extension dj-auto.js) et sert à noter les transitions (écoute à l'aveugle, docs/ux/transitions-v2.md).
// Page en 2 colonnes à la hauteur de l'écran :
// - à gauche : ce qu'on entend, le cercle façon Eternal Jukebox du morceau entendu (temps colorés par section,
//   aiguille, zone de transition), le cercle du morceau qui arrive, le visualiseur ;
// - à droite : le mode automatique (et le forçage), la frise de la transition, les transitions à noter, la file à
//   venir et le lancement manuel d'une transition de test.
// Noms, couleurs et étapes de frise viennent de spicetify/dj-catalogue.js (DJCore.catalogue, ADR 0005), lu à
// l'appel : l'ordre de chargement des extensions n'est pas garanti.
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
const KEYS = ['Do', 'Do#', 'Ré', 'Mib', 'Mi', 'Fa', 'Fa#', 'Sol', 'Lab', 'La', 'Sib', 'Si'];
const C = { a: '#4f8cff', b: '#ff5ea8', zone: '#ffb020', head: '#1ed760', bad: '#ff5e7a', line: 'rgba(255,255,255,.10)', sub: 'rgba(255,255,255,.6)' };

// Catalogue partagé ; sans lui (extension pas encore chargée), l'app marche avec les identifiants seuls.
const SANS_CATALOGUE = {
  JOUABLES: ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'R1', 'R2'],
  ETIQUETTES: ['rythme_decroche', 'basses_doublees', 'voix_superposees', 'fin_coupee', 'mauvais_endroit', 'trop_long',
    'trop_court', 'saut_volume', 'clic_trou', 'effet_de_trop'].map((k) => [k, k.replace(/_/g, ' ')]),
  info: (id) => ({ id, nom: id ?? 'Transition', couleur: '#888888', phases: [], b_debut: 1 }),
  masquer: (t) => String(t ?? '').replace(/\b(?:C[1-8]|R[1-3])\b|secours/gi, '?'),
  nomCourt: (id) => String(id ?? 'aucune'),
  lignesRapport: (r) => [`Demandée ${r.transition_demandee}, jouée ${r.transition_jouee}`],
};
const cat = () => globalThis.DJCore?.catalogue ?? SANS_CATALOGUE;

const CSS = `
.djm { color: var(--spice-text); padding: 18px 24px; box-sizing: border-box; display: grid; gap: 14px;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); }
.djm * { box-sizing: border-box; }
.djm :focus-visible { outline: 2px solid ${C.head}; outline-offset: 2px; }
.djm-col { display: flex; flex-direction: column; gap: 14px; min-height: 0; overflow-y: auto; }
.djm-card { background: var(--spice-card); border-radius: 14px; padding: 14px 16px; min-height: 0; flex: none;
  border: 1px solid rgba(255,255,255,.04); transition: box-shadow .4s, border-color .4s; animation: djm-in .45s ease both; }
.djm-card.live { border-color: rgba(255,176,32,.6); box-shadow: 0 0 24px rgba(255,176,32,.18); }
.djm-label { font-size: 11px; letter-spacing: .09em; text-transform: uppercase; opacity: .6; margin: 0 0 6px; font-weight: 600; }
.djm-head { font-size: 26px; font-weight: 800; line-height: 1.15; animation: djm-in .35s ease both; }
.djm-count { color: ${C.zone}; font-weight: 700; margin-top: 2px; font-variant-numeric: tabular-nums; }
.djm-switch { display: flex; align-items: center; gap: 14px; cursor: pointer; user-select: none; background: none; border: 0;
  padding: 0; color: inherit; text-align: left; font: inherit; }
.djm-switch.small { gap: 8px; font-size: 12px; font-weight: 600; }
.djm-track { width: 54px; height: 30px; border-radius: 999px; background: rgba(255,255,255,.18); position: relative; transition: background .25s; flex: none; }
.djm-track::after { content: ''; position: absolute; top: 3px; left: 3px; width: 24px; height: 24px; border-radius: 50%; background: #fff; transition: transform .25s cubic-bezier(.3,1.4,.6,1); }
.djm-switch.small .djm-track { width: 36px; height: 20px; }
.djm-switch.small .djm-track::after { width: 14px; height: 14px; }
.djm-switch[aria-checked="true"] .djm-track { background: ${C.head}; }
.djm-switch[aria-checked="true"] .djm-track::after { transform: translateX(24px); }
.djm-switch.small[aria-checked="true"] .djm-track::after { transform: translateX(16px); }
.djm-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.djm select { flex: 1 1 140px; min-width: 0; padding: 8px 30px 8px 12px; border-radius: 999px; font-size: 13px; font-weight: 600;
  appearance: none; cursor: pointer; color: #fff; border: 1px solid rgba(255,255,255,.14); transition: border-color .2s, background-color .2s;
  background: #2a2a2a url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23fff' stroke-width='1.6' fill='none'/%3E%3C/svg%3E") no-repeat right 12px center; }
.djm select:hover { background-color: #333; }
.djm select:focus { border-color: ${C.head}; }
/* le menu déroulant s'ouvre avec le fond du système (clair sous Linux) : sans fond propre, texte blanc illisible */
.djm option { background: #1f1f1f; color: #fff; }
.djm button { padding: 7px 14px; border-radius: 999px; border: 0; font-weight: 700; cursor: pointer; background: rgba(255,255,255,.1); color: var(--spice-text); transition: transform .12s, opacity .2s; }
.djm button:hover:not(:disabled) { transform: scale(1.04); }
.djm button.go { background: ${C.head}; color: #000; }
.djm button:disabled { opacity: .4; cursor: not-allowed; }
.djm button.djm-switch { padding: 0; background: none; }
.djm button.djm-switch:hover { transform: none; }
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
.djm-list { list-style: none; margin: 0; padding: 0; }
.djm-hist { padding: 7px 0; font-size: 12px; border-bottom: 1px solid ${C.line}; animation: djm-in .35s ease both; }
.djm-hist:last-child { border-bottom: 0; }
.djm-hist .top { display: flex; gap: 8px; align-items: center; }
.djm-hist .top button { padding: 3px 10px; font-size: 12px; flex: none; }
.djm-tag { flex: none; padding: 2px 8px; border-radius: 999px; font-weight: 700; font-size: 11px; color: #111; white-space: nowrap; }
.djm-tag.masque { background: rgba(255,255,255,.1); color: ${C.sub}; }
.djm-tag.alerte { background: ${C.bad}; }
.djm-rap { margin: 6px 0 0; padding-left: 16px; opacity: .7; }
.djm-form { margin-top: 8px; display: grid; gap: 8px; }
.djm-form fieldset { border: 0; margin: 0; padding: 0; }
.djm-form legend { font-size: 11px; opacity: .6; padding: 0; margin-bottom: 4px; }
.djm-stars { display: flex; gap: 2px; }
.djm .djm-stars button { font-size: 20px; line-height: 1; padding: 2px 6px; background: none; color: rgba(255,255,255,.25); }
.djm .djm-stars button.on { color: ${C.zone}; }
.djm-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.djm-tags label { display: inline-flex; align-items: center; gap: 5px; background: rgba(255,255,255,.07); border-radius: 999px; padding: 3px 9px; cursor: pointer; }
.djm-tags input { margin: 0; accent-color: ${C.zone}; }
.djm-form textarea { width: 100%; min-height: 2.2em; resize: vertical; border-radius: 8px; padding: 6px 8px; font: inherit;
  color: #fff; background: #2a2a2a; border: 1px solid rgba(255,255,255,.14); }
@keyframes djm-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
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

// undefined = en cours de chargement ; null = Spotify n'a pas d'analyse pour ce morceau
const analyses = new Map();
function useAnalysis(uri) {
  const [a, set] = useState(() => analyses.get(uri));
  useEffect(() => {
    if (!uri) return set(null);
    if (analyses.has(uri)) return set(analyses.get(uri));
    set(undefined);
    let alive = true;
    // Un morceau sans analyse ne fait pas échouer l'appel : il rend {code: 404, …}. Pris pour une analyse,
    // il faisait planter la page (« Something went wrong ») : on le traite comme une absence d'analyse.
    Spicetify.getAudioData(uri).then((d) => {
      const ok = d?.track && d?.beats?.length ? d : null;
      analyses.set(uri, ok);
      if (alive) set(ok);
    }).catch(() => { analyses.set(uri, null); if (alive) set(null); });
    return () => { alive = false; };
  }, [uri]);
  return a;
}

// dep : l'élément mesuré n'existe pas quand la maquette est éteinte ; on se rattache quand il apparaît
function useSize(ref, dep) {
  const [size, set] = useState({ w: 0, h: 0 });
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => set({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [dep]);
  return size;
}

// ── Écoute à l'aveugle : le nom d'une transition reste caché jusqu'à sa note ──────────────────────
const lire = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const ecrire = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* quota */ } };
function useAveugle() {
  const [aveugle, setA] = useState(() => lire('dj-mixer:aveugle', true));
  const [notees, setN] = useState(() => lire('dj-mixer:notees', {}));   // id → note envoyée (50 dernières)
  const basculer = () => setA((v) => { ecrire('dj-mixer:aveugle', !v); return !v; });
  const noter = (id, note) => setN((n) => {
    const m = { ...n, [id]: note }, ids = Object.keys(m);
    if (ids.length > 50) delete m[ids[0]];
    ecrire('dj-mixer:notees', m);
    return m;
  });
  const visible = (id) => !aveugle || (id != null && notees[id] != null);
  const texte = (id, t) => (visible(id) ? String(t ?? '') : cat().masquer(t));
  return { aveugle, basculer, notees, noter, visible, texte };
}

// Quoi montrer : morceau entendu (A), morceau suivant (B), transition concernée et temps écoulé dedans.
function view(st) {
  const x = st?.current ?? st?.next ?? st?.last ?? null;
  if (!x) return { aUri: st?.heard?.uri, aPos: st?.heard?.pos_s, x: null };
  const t = st.current ? st.current.elapsed_s : st.next ? -st.next.in_s : st.last.elapsed_s;
  // dans A, la transition ne rejoue que real_s secondes réelles avant la sortie ; ensuite A est prolongé
  // (boucle, écho, frein) : l'aiguille reste sur la sortie
  const real = x.real_s ?? x.dur_s;
  if (t < x.dur_s) return { aUri: x.from_uri ?? st.heard?.uri, aPos: (x.sortieA ?? 0) - real + Math.min(t, real), x, t, bUri: x.to_uri };
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
        g.fillStyle = C.sub; g.font = '13px sans-serif'; g.textAlign = 'center';
        g.fillText(an === null ? 'analyse indisponible' : 'analyse…', cx, cy);
        raf = requestAnimationFrame(draw); return;
      }
      const dur = an.track.duration, p = p0 == null ? null : p0 + (performance.now() - at) / 1000;
      const ang = (s) => -Math.PI / 2 + (s / dur) * Math.PI * 2;
      const secs = an.sections ?? [];
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
        g.strokeStyle = now ? '#fff' : inZone ? C.zone : `hsla(${(i * 47) % 360} 75% ${58 + ((secs[i]?.loudness ?? -15) + 15)}% / ${played ? 0.95 : 0.5})`;
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
    h('canvas', { ref, role: 'img', 'aria-label': `Cercle des temps de ${title ?? 'morceau'}`, style: { width: size, height: size, display: 'block' } }),
    h('div', { className: 'djm-cap', style: { width: size } },
      h('b', { className: 'djm-ell', style: { color } }, title ?? '…'),
      h('span', { style: { opacity: 0.6, fontSize: 12 } }, sub ?? '')));
}

function Spectrum({ levels }) {
  return h('div', { 'aria-hidden': true, style: { display: 'flex', alignItems: 'flex-end', gap: 3, height: 56, flex: 'none' } },
    (levels ?? new Array(16).fill(0)).map((v, i) => h('div', { key: i, style: {
      flex: 1, height: `${Math.max(4, v * 100)}%`, borderRadius: 3, transition: 'height .12s linear',
      background: `linear-gradient(to top, ${C.a}, ${i < 4 ? C.b : C.head})`, opacity: 0.55 + 0.45 * v } })));
}

// Étapes de la transition (catalogue) ; masquées en écoute à l'aveugle : une seule étape « ? », B entre au bout.
function etapes(x, vu) {
  const f = cat().info(x?.transition);
  return vu && f.phases.length ? { phases: f.phases, bFrom: f.b_debut ?? 1, couleur: f.couleur }
    : { phases: [['?', 0, 1]], bFrom: vu ? f.b_debut ?? 1 : 1, couleur: null };
}

function Frise({ x, t, vu }) {
  if (!x) return h('div', { style: { opacity: 0.55, padding: '10px 0' } }, 'Aucune transition prévue pour l\'instant.');
  const dur = Math.max(x.dur_s, 0.01), t0 = -8, t1 = dur + 8, pct = (u) => `${((u - t0) / (t1 - t0)) * 100}%`;
  const w = (a, b) => `${((b - a) / (t1 - t0)) * 100}%`;
  const e = etapes(x, vu), bFrom = e.bFrom * dur;
  const bar = (left, width, color, faded) => h('div', { style: { position: 'absolute', left, width, top: 0, height: 16, borderRadius: 5, background: color, opacity: faded ? 0.35 : 1 } });
  const label = (text, color, left) => h('div', { className: 'djm-ell', style: { position: 'absolute', top: -16, left, maxWidth: '60%', color, fontWeight: 700, fontSize: 11 } }, text);
  const steps = [...e.phases.map(([name, a, b]) => [name, a * dur, b * dur]), [`${x.to ?? 'B'} seul`, dur, dur + 1e9]];
  return h('div', null,
    h('div', { 'aria-hidden': true, style: { position: 'relative', height: 64, margin: '18px 0 4px' } },
      h('div', { style: { position: 'absolute', left: pct(0), width: w(0, dur), top: -4, bottom: 0, background: e.couleur ? `${e.couleur}14` : 'rgba(255,176,32,.06)', borderLeft: '1px dashed #777', borderRight: '1px dashed #777' } }),
      h('div', { style: { position: 'absolute', top: 0, left: 0, right: 0, height: 16 } }, label(`A · ${x.from ?? '?'} (finit)`, C.a, 0), bar(0, w(t0, 0), C.a), vu ? bar(pct(0), w(0, dur), C.a, true) : null),
      h('div', { style: { position: 'absolute', top: 44, left: 0, right: 0, height: 16 } }, label(`B · ${x.to ?? '?'} (arrive)`, C.b, pct(Math.min(bFrom, dur - 0.01))), bFrom < dur ? bar(pct(bFrom), w(bFrom, dur), C.b, true) : null, bar(pct(dur), w(dur, t1), C.b)),
      h('div', { style: { position: 'absolute', top: -6, bottom: 0, width: 3, borderRadius: 2, left: pct(Math.min(t1, Math.max(t0, t))), background: C.head, boxShadow: `0 0 10px ${C.head}` } })),
    // étapes numérotées, l'étape en cours se remplit
    h('ol', { className: 'djm-steps', style: { listStyle: 'none', padding: 0, margin: '8px 0 0' } }, steps.map(([name, a, b], k) => {
      const on = t >= a && t < b, done = t >= b, fill = on && b < 1e8 ? ((t - a) / (b - a)) * 100 : done ? 100 : 0;
      return h('li', { key: `${k}-${name}`, className: `djm-step ${on ? 'on' : ''} ${done ? 'done' : ''}`, title: name, 'aria-current': on ? 'step' : undefined },
        h('div', { className: 'fill', style: { width: `${fill}%`, background: on && e.couleur ? `${e.couleur}55` : undefined } }),
        h('span', { className: 'djm-ell', style: { display: 'block' } }, `${k + 1} · ${name}`));
    })));
}

// ── Notation par id (POST /rating, ADR 0001) ───────────────────────────────────────────────────────
// La liste vient du moteur (/state transitions_recentes, la plus récente d'abord). Une transition prévue n'est notable
// qu'une fois entendue (avance de la maquette). Note obligatoire, étiquettes et commentaire facultatifs.
function Badge({ r, vu }) {
  if (!vu) return h('span', { className: 'djm-tag masque' }, '? masquée');
  if (r.issue === 'abandon') return h('span', { className: 'djm-tag alerte' }, 'abandon (Spotify seul)');
  if (r.issue === 'secours') return h('span', { className: 'djm-tag alerte' }, 'secours (échec)');
  const f = cat().info(r.transition_jouee);
  return h('span', { className: 'djm-tag', style: { background: f.couleur } }, `${cat().nomCourt(r.transition_jouee)}${r.replis?.length ? ' · repli' : ''}`);
}

function FormNote({ r, brouillon, maj, envoyer }) {
  const b = brouillon;
  return h('form', { className: 'djm-form', 'aria-label': `Noter la transition ${r.a?.nom ?? 'A'} vers ${r.b?.nom ?? 'B'}`,
    onSubmit: (e) => { e.preventDefault(); envoyer(); } },
    h('fieldset', null, h('legend', null, 'Note (obligatoire)'),
      h('div', { className: 'djm-stars' }, [1, 2, 3, 4, 5].map((n) => h('button', { key: n, type: 'button',
        className: b.note >= n ? 'on' : '', 'aria-pressed': b.note === n, 'aria-label': `Note ${n} sur 5`,
        onClick: () => maj({ note: n }) }, '★')))),
    h('fieldset', null, h('legend', null, 'Ce qui ne va pas (facultatif)'),
      h('div', { className: 'djm-tags' }, cat().ETIQUETTES.map(([k, l]) => h('label', { key: k },
        h('input', { type: 'checkbox', checked: b.etiquettes.includes(k),
          onChange: (e) => maj({ etiquettes: e.target.checked ? [...b.etiquettes, k] : b.etiquettes.filter((x) => x !== k) }) }), l)))),
    h('label', { style: { display: 'grid', gap: 4, fontSize: 11, opacity: 0.85 } }, 'Commentaire (facultatif)',
      h('textarea', { value: b.commentaire, maxLength: 500, onChange: (e) => maj({ commentaire: e.target.value }) })),
    h('div', { className: 'djm-row' },
      h('button', { type: 'submit', className: 'go', disabled: !b.note || b.envoi }, b.envoi ? 'Envoi…' : 'Envoyer la note'),
      h('span', { role: 'status', style: { color: b.erreur ? C.bad : undefined, opacity: b.erreur ? 1 : 0.7 } }, b.msg)));
}

function Notation({ st, av }) {
  const recents = st?.transitions_recentes ?? [];
  const [ouvert, setOuvert] = useState(null);      // null = le plus récent entendu et pas noté ; '' = aucun
  const [brouillons, setB] = useState({});
  const dessus = recents[0]?.id ?? null, prec = useRef(dessus);
  useEffect(() => { if (prec.current !== dessus) { prec.current = dessus; setOuvert(null); } }, [dessus]);
  if (!recents.length) return h('div', { style: { opacity: 0.55, fontSize: 12 } }, 'Rien à noter pour l\'instant.');
  const etat = (r) => (st.next?.id === r.id ? 'attente' : st.current?.id === r.id ? 'encours' : 'entendue');
  const cible = ouvert ?? recents.find((r) => etat(r) === 'entendue' && av.notees[r.id] == null)?.id ?? null;
  const vide = { note: 0, etiquettes: [], commentaire: '', msg: '', erreur: false, envoi: false };
  const maj = (id, d) => setB((m) => ({ ...m, [id]: { ...(m[id] ?? vide), ...d } }));
  const envoyer = async (id) => {
    const b = brouillons[id] ?? vide;
    if (!b.note || b.envoi) return;
    maj(id, { envoi: true, msg: '', erreur: false });
    try {
      const r = await fetch(`${MAQUETTE}/rating`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, note: b.note, etiquettes: b.etiquettes, commentaire: b.commentaire.slice(0, 500) }) });
      const j = await r.json().catch(() => ({}));
      if (r.ok) { av.noter(id, b.note); setB((m) => { const n = { ...m }; delete n[id]; return n; }); setOuvert(null); return; }
      maj(id, { envoi: false, erreur: true, msg: r.status === 409 ? 'Transition trop ancienne : le moteur ne la connaît plus.' : `Note refusée : ${j.message ?? r.status}.` });
    } catch { maj(id, { envoi: false, erreur: true, msg: 'La maquette ne répond pas : ta saisie est gardée, réessaie.' }); }
  };
  return h('ul', { className: 'djm-list' }, recents.map((r) => {
    const e = etat(r), note = av.notees[r.id], vu = av.visible(r.id), open = r.id === cible && e === 'entendue';
    const quand = e === 'attente' ? `s'entend dans ${Math.ceil(st.next.in_s ?? 0)} s` : e === 'encours' ? 'en cours…' : (r.t ?? '').slice(11);
    return h('li', { key: r.id, className: 'djm-hist', style: { opacity: e === 'entendue' ? 1 : 0.6 } },
      h('div', { className: 'top' },
        h(Badge, { r, vu }),
        h('span', { className: 'djm-ell', style: { flex: 1 } }, `${r.a?.nom ?? '?'} → ${r.b?.nom ?? '?'}`),
        note != null ? h('span', { 'aria-label': `Notée ${note} sur 5`, style: { color: C.zone, flex: 'none' } }, '★'.repeat(note)) : null,
        h('span', { style: { opacity: 0.5, flex: 'none' } }, quand),
        e === 'entendue' ? h('button', { type: 'button', 'aria-expanded': open, onClick: () => setOuvert(open ? '' : r.id) },
          open ? 'Fermer' : note != null ? 'Renoter' : 'Noter') : null),
      vu ? h('ul', { className: 'djm-rap' }, cat().lignesRapport(r).map((l, i) => h('li', { key: i }, l))) : null,
      open ? h(FormNote, { r, brouillon: brouillons[r.id] ?? vide, maj: (d) => maj(r.id, d), envoyer: () => envoyer(r.id) }) : null);
  }));
}

// Santé de la maquette : avance sur Spotify (une superposition en consomme, la boucle en regagne) et dernier
// incident (transition refusée, abandonnée) de la dernière minute, sans nom de transition en écoute à l'aveugle.
function Health({ st, av }) {
  const low = st.delay_s < 0.6 * (st.target_s ?? 60);
  const ev = (st.events ?? []).filter((e) => Date.now() / 1000 - e.t < 60).slice(-1)[0];
  return h('div', { style: { fontSize: 12, marginTop: 4 } },
    h('div', { style: { opacity: low ? 1 : 0.55, color: low ? C.bad : undefined } },
      `${st.delay_s.toFixed(0)} s d'avance sur Spotify (cible ${(st.target_s ?? 60).toFixed(0)} s), qui joue déjà « ${st.spotify?.name ?? '…'} »`),
    ev ? h('div', { style: { color: C.bad } }, av.aveugle ? cat().masquer(ev.msg) : ev.msg) : null);
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
        try {
          let a = analyses.get(t.uri);
          if (a === undefined) { a = await Spicetify.getAudioData(t.uri); a = a?.track && a?.beats?.length ? a : null; analyses.set(t.uri, a); }
          if (a) { tempo = Math.round(a.track.tempo); key = KEYS[a.track.key]; }
        } catch { analyses.set(t.uri, null); }
        rows.push({ uri: t.uri, name: t.metadata?.title ?? t.uri, artist: t.metadata?.artist_name ?? '', tempo, key, sans: analyses.get(t.uri) === null });
      }
      if (alive) set(rows);
    };
    load();
    const t = setInterval(load, 8000);
    Spicetify.Player.addEventListener('songchange', load);
    return () => { alive = false; clearInterval(t); Spicetify.Player.removeEventListener('songchange', load); };
  }, []);
  if (!items.length) return h('div', { style: { opacity: 0.55 } }, 'File vide.');
  return h('ul', { className: 'djm-list' }, items.map((r, i) => h('li', { key: r.uri + i, className: 'djm-q', style: { animationDelay: `${i * 40}ms` } },
    h('span', { className: 'djm-ell' }, h('b', null, r.name), ' ', h('span', { style: { opacity: 0.55 } }, r.artist)),
    h('span', { style: { flex: 'none', opacity: 0.85, fontVariantNumeric: 'tabular-nums' } },
      i === 0 && plan ? h('span', { style: { color: C.zone, marginRight: 8 } }, plan) : null,
      r.tempo ? `${r.tempo} BPM · ${r.key}` : r.sans ? 'sans analyse' : '…'))));
}

const Switch = ({ on, onClick, small, children }) => h('button', { type: 'button', role: 'switch', 'aria-checked': on,
  className: `djm-switch ${small ? 'small' : ''}`, onClick }, h('span', { className: 'djm-track', 'aria-hidden': true }), children);

// Mode automatique (window.DJ v2 de dj-auto.js) : interrupteur, statut, et forçage de la prochaine transition.
function AutoSwitch({ av, offline }) {
  const [, force] = useState(0);
  const [forcee, setForcee] = useState('auto');
  useEffect(() => { const t = setInterval(() => force((n) => n + 1), 500); return () => clearInterval(t); }, []);
  const dj = window.DJ;
  if (!dj) return h('div', { style: { opacity: 0.7 } }, 'Extension dj-auto absente : lancer spicetify/installer.sh.');
  const on = !!dj.status?.enabled;
  const statut = offline ? 'Maquette éteinte : Spotify joue seul, sans transition.' : (av.aveugle ? cat().masquer(dj.status?.text) : dj.status?.text);
  const forcer = (id) => { setForcee(id); try { dj.forcer?.(id === 'auto' ? null : id); } catch { /* extension v1 */ } };
  return h('div', null,
    h(Switch, { on, onClick: () => dj.setAuto(!on) },
      h('span', null, h('span', { style: { display: 'block', fontWeight: 800, fontSize: 16 } }, 'Mode DJ automatique'),
        h('span', { style: { display: 'block', opacity: 0.7, fontSize: 12 } }, on ? 'Chaque morceau enchaîne tout seul sur le suivant.' : 'Éteint : Spotify joue normalement.'))),
    h('div', { 'aria-live': 'polite', style: { marginTop: 8, fontSize: 13, color: on ? C.zone : C.sub, minHeight: 18 } }, statut),
    dj.forcer ? h('label', { className: 'djm-row', style: { marginTop: 8, fontSize: 12 } },
      h('span', { style: { opacity: 0.7, flex: 'none' } }, 'Prochaines transitions'),
      h('select', { value: forcee, onChange: (e) => forcer(e.target.value) },
        h('option', { value: 'auto' }, 'Choix automatique'),
        cat().JOUABLES.map((id) => h('option', { key: id, value: id }, `Forcer ${cat().nomCourt(id)}`)))) : null);
}

// une demande d'avant la v2 (champ `mode`) serait refusée par le moteur : on ne la rejoue pas
const rejouable = (q) => q && typeof q.transition === 'string' && !('mode' in q);

function Manual({ st }) {
  const [pair, setPair] = useState('queue');
  const [trans, setTrans] = useState('auto');
  const [msg, setMsg] = useState('');
  const blocked = !st?.can_run || st?.busy || !!st?.next || !!st?.current;
  const send = async (req) => {
    setMsg('Envoi…');
    try {
      const r = await fetch(`${MAQUETTE}/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req) });
      const j = await r.json().catch(() => ({}));
      setMsg(r.ok ? 'C\'est parti : la transition arrive dans environ 1 minute.' : `Impossible : ${j.message ?? r.status}.`);
    } catch { setMsg('La maquette ne répond pas.'); }
  };
  const go = () => {
    if (pair === 'queue') {
      const a = Spicetify.Player.data?.item, b = (Spicetify.Queue?.nextTracks ?? []).map((t) => t.contextTrack).find((t) => t?.uri?.startsWith('spotify:track:'));
      if (!a || !b) return setMsg('Il faut un morceau en cours et un suivant dans la file.');
      return send({ transition: trans, a: a.uri, b: b.uri, name: `${a.name} → ${b.metadata?.title ?? 'suivant'}` });
    }
    const [name, a, b] = PAIRS[+pair];
    send({ transition: trans, a: `spotify:track:${a}`, b: `spotify:track:${b}`, name });
  };
  const sel = (label, value, onChange, options) => h('select', { 'aria-label': label, value, onChange: (e) => onChange(e.target.value) },
    options.map(([v, l]) => h('option', { key: v, value: v }, l)));
  const note = !st?.can_run ? 'Test indisponible : maquette lancée sans DJ_WORK.' : st?.busy && !st?.next ? 'Préparation : Spotify rejoue le morceau A…' : msg;
  return h('div', null,
    h('div', { className: 'djm-row' },
      sel('Morceaux', pair, setPair, [['queue', 'En cours → suivant'], ...PAIRS.map(([n], i) => [String(i), n])]),
      sel('Transition', trans, setTrans, [['auto', 'Auto'], ...cat().JOUABLES.map((id) => [id, cat().nomCourt(id)])]),
      h('button', { type: 'button', className: 'go', onClick: go, disabled: blocked }, 'Tester'),
      h('button', { type: 'button', onClick: () => send(st.last_request), disabled: blocked || !rejouable(st?.last_request) }, 'Rejouer')),
    h('div', { 'aria-live': 'polite', style: { marginTop: 6, opacity: 0.7, fontSize: 12, minHeight: 16 } }, note));
}

const card = (title, props, ...children) => h('section', { className: `djm-card ${props?.live ? 'live' : ''}`, style: props?.style, 'aria-label': props?.aria ?? title ?? undefined },
  title ? h('h2', { className: 'djm-label' }, title) : null, ...children);

function App() {
  const { state: st, offline } = useMaquette();
  const av = useAveugle();
  const root = useRef(null), circles = useRef(null);
  const [height, setHeight] = useState(600);
  useEffect(() => {
    const fit = () => { if (root.current) setHeight(Math.max(480, window.innerHeight - root.current.getBoundingClientRect().top - 104)); };
    fit(); window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, []);
  const box = useSize(circles, offline);
  const v = view(offline ? null : st);
  const aAn = useAnalysis(v.aUri), bAn = useAnalysis(v.bUri);
  const x = v.x, live = !offline && !!st?.current;
  const vu = x ? av.visible(x.id) : true;
  const nom = x ? (vu ? cat().info(x.transition).nom : 'Transition masquée') : '';
  let headline = st?.heard?.name ?? '…', count = '';
  if (x && v.t != null) {
    const ph = etapes(x, vu).phases.find(([, a, b]) => v.t >= a * x.dur_s && v.t < b * x.dur_s);
    if (v.t < 0) { headline = `${x.from ?? 'A'} seul`; count = `${nom} dans ${(-v.t).toFixed(1)} s`; }
    else if (v.t < x.dur_s) { headline = ph && ph[0] !== '?' ? ph[0] : 'Transition en cours'; count = `${nom} : encore ${(x.dur_s - v.t).toFixed(1)} s, puis ${x.to ?? 'B'} seul`; }
    else { headline = `${x.to ?? 'B'} seul`; count = `${nom} terminée il y a ${(v.t - x.dur_s).toFixed(1)} s`; }
  }
  const zone = x && x.sortieA != null && !v.after ? [x.sortieA - (x.real_s ?? x.dur_s), x.sortieA] : null;
  const twoCircles = !!v.bUri;
  const big = Math.max(150, Math.min(twoCircles ? box.w * 0.56 : box.w * 0.8, box.h - 50));
  const small = Math.max(110, Math.min(box.w - big - 24, big * 0.7));
  const pc = window.DJ?.status?.plan;
  const prevue = pc?.choix && !pc.done && !pc.failed ? (pc.choix.transition ?? pc.choix.choisie) : null;
  const plan = prevue ? (av.aveugle ? 'transition ?' : cat().nomCourt(prevue)) : null;
  const sub = (an, extra) => (an === null ? 'sans analyse Spotify' : an ? `${Math.round(an.track.tempo)} BPM · ${extra(an)}` : '');
  return h('div', { ref: root, className: 'djm', style: { height } },
    h('style', null, CSS),
    h('div', { className: 'djm-col' },
      card('Dans tes oreilles', { live },
        h('div', { className: 'djm-head', key: headline }, offline ? 'Maquette éteinte' : headline),
        h('div', { className: 'djm-count', 'aria-live': 'polite' }, offline ? 'Lance proto/e2/e2.py : sans elle, Spotify joue seul.' : count),
        st && !offline ? h(Health, { st, av }) : null),
      offline ? null : card(null, { live, aria: 'Morceaux et visualiseur', style: { flex: 1, display: 'flex', flexDirection: 'column', gap: 8, minHeight: 260 } },
        h('div', { ref: circles, style: { flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 } },
          box.w ? h(Circle, { analysis: aAn, pos: v.aPos, zone, live, color: C.a, size: big, title: v.after ? x?.to : (x?.from ?? st?.heard?.name), sub: sub(aAn, (a) => KEYS[a.track.key]) }) : null,
          twoCircles && box.w ? h(Circle, { analysis: bAn, pos: null, mark: x?.entreeB, color: C.b, size: small, title: x?.to, sub: sub(bAn, () => 'entre au point jaune') }) : null),
        h(Spectrum, { levels: st?.levels }))),
    h('div', { className: 'djm-col' },
      card(null, { aria: 'Mode DJ automatique' }, h(AutoSwitch, { av, offline })),
      offline ? null : card(x ? `${vu ? cat().nomCourt(x.transition) : 'Transition ?'} : ${x.from ?? 'A'} → ${x.to ?? 'B'}` : 'Transition', { live },
        h(Frise, { x, t: v.t ?? 0, vu }),
        x?.raison && vu ? h('div', { style: { opacity: 0.7, fontSize: 12 } }, `Pourquoi : ${x.raison}`) : null),
      offline ? null : card(null, { aria: 'Transitions à noter' },
        h('div', { className: 'djm-row', style: { justifyContent: 'space-between', marginBottom: 6 } },
          h('h2', { className: 'djm-label', style: { margin: 0 } }, 'À noter'),
          h(Switch, { on: av.aveugle, onClick: av.basculer, small: true }, 'Écoute à l\'aveugle')),
        h(Notation, { st, av })),
      offline ? null : card('À venir dans la file', { style: { maxHeight: 220, overflow: 'hidden' } }, h(Queue, { plan })),
      offline ? null : card('Tester une transition', null, h(Manual, { st }))));
}

const render = () => h(App);
