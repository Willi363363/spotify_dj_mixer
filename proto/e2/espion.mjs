// Lit toutes les 250 ms le morceau et la position de Spotify (mode débogage) et les envoie à e2.py,
// qui les relie à sa mémoire pour savoir ce que l'on entend vraiment, en retard.
// Usage : node --experimental-websocket proto/e2/espion.mjs <ws://…>
import dgram from 'node:dgram';

const udp = dgram.createSocket('udp4');
const ws = new WebSocket(process.argv[2]);
const EXPR = `(() => { const d = Spicetify.Player.data; const it = d?.item;
  return it ? { name: it.name, artist: it.artists?.map((a) => a.name).join(', '), uri: it.uri,
    pos_ms: Spicetify.Player.getProgress(), dur_ms: it.duration?.milliseconds ?? Spicetify.Player.getDuration(),
    paused: d.isPaused } : null; })()`;
let id = 0;
ws.onopen = () => setInterval(() => ws.send(JSON.stringify({ id: ++id, method: 'Runtime.evaluate', params: { expression: EXPR, returnByValue: true } })), 250);
ws.onmessage = (m) => {
  const v = JSON.parse(m.data).result?.result?.value;
  if (!v) return;
  udp.send(JSON.stringify({ cmd: 'track', t_wall: Date.now(), ...v }), 47801, '127.0.0.1');
};
ws.onclose = () => process.exit(0);
