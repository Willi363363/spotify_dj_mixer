// Lit toutes les 250 ms le morceau et la position de Spotify (mode débogage) et les envoie à e2.py,
// qui les relie à sa mémoire pour savoir ce que l'on entend vraiment, en retard.
// Retrouve seul la page de Spotify et se reconnecte quand Spotify redémarre.
// Usage : node --experimental-websocket proto/e2/espion.mjs
import dgram from 'node:dgram';

const udp = dgram.createSocket('udp4');
const EXPR = `(() => { const d = Spicetify.Player.data; const it = d?.item;
  return it ? { name: it.name, artist: it.artists?.map((a) => a.name).join(', '), uri: it.uri,
    pos_ms: Spicetify.Player.getProgress(), dur_ms: it.duration?.milliseconds ?? Spicetify.Player.getDuration(),
    paused: d.isPaused } : null; })()`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function spotifyPage() {
  try {
    const pages = await (await fetch('http://127.0.0.1:9222/json/list')).json();
    return pages.find((p) => p.url?.startsWith('https://xpui.app.spotify.com/index'))?.webSocketDebuggerUrl;
  } catch { return null; }
}

for (;;) {
  const url = await spotifyPage();
  if (!url) { await sleep(2000); continue; }
  await new Promise((done) => {
    const ws = new WebSocket(url);
    let id = 0, timer;
    ws.onopen = () => { timer = setInterval(() => ws.send(JSON.stringify({ id: ++id, method: 'Runtime.evaluate', params: { expression: EXPR, returnByValue: true } })), 250); };
    ws.onmessage = (m) => {
      const v = JSON.parse(m.data).result?.result?.value;
      if (v) udp.send(JSON.stringify({ cmd: 'track', t_wall: Date.now(), ...v }), 47801, '127.0.0.1');
    };
    ws.onclose = ws.onerror = () => { clearInterval(timer); done(); };
  });
  await sleep(1000);
}
