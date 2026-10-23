// Capture d'écran de la page Spotify via le mode débogage, même si la fenêtre est cachée.
// Usage : node --experimental-websocket outils/cdp-capture.mjs <ws://…> <sortie.png>
import { writeFileSync } from 'node:fs';

const ws = new WebSocket(process.argv[2]);
ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: 'Page.captureScreenshot', params: { format: 'png' } }));
ws.onmessage = (m) => {
  const r = JSON.parse(m.data);
  if (r.id !== 1) return;
  writeFileSync(process.argv[3], Buffer.from(r.result.data, 'base64'));
  ws.close();
};
