// Serveur de test : reçoit des messages HTTP et WebSocket depuis l'extension, sur 127.0.0.1 uniquement.
import http from 'node:http';
import crypto from 'node:crypto';

const PORT = 47800;
const log = (...a) => console.log(new Date().toISOString().slice(11, 23), ...a);

const server = http.createServer((req, res) => {
  const cors = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
  };
  if (req.method === 'OPTIONS') { res.writeHead(204, cors); return res.end(); }
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    log('HTTP', req.method, req.url, 'origin=', req.headers.origin, 'body=', body);
    res.writeHead(200, { ...cors, 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true, received: body }));
  });
});

// Poignée de main WebSocket minimale + renvoi en écho des trames texte courtes.
server.on('upgrade', (req, socket) => {
  const accept = crypto.createHash('sha1')
    .update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
  socket.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
  log('WS connecté, origin=', req.headers.origin);
  socket.on('data', (buf) => {
    const op = buf[0] & 0x0f;
    if (op === 8) { socket.end(); return log('WS fermé'); }
    const len = buf[1] & 0x7f;
    const mask = buf.subarray(2, 6);
    const data = Buffer.from(buf.subarray(6, 6 + len).map((b, i) => b ^ mask[i % 4]));
    log('WS reçu', data.toString());
    socket.write(Buffer.concat([Buffer.from([0x81, data.length]), data]));
  });
  socket.on('error', () => {});
});

server.listen(PORT, '127.0.0.1', () => log('écoute sur 127.0.0.1:' + PORT));
