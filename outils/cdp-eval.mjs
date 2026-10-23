// Exécute une expression JavaScript dans Spotify (mode débogage) et affiche son résultat en JSON.
// En cas d'erreur dans l'expression, affiche { erreur, ligne } au lieu d'un objet vide.
// Usage : node --experimental-websocket outils/cdp-eval.mjs <ws://…> "<expression>"
const ws = new WebSocket(process.argv[2]);
ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: process.argv[3], awaitPromise: true, returnByValue: true } }));
ws.onmessage = (m) => {
  const r = JSON.parse(m.data);
  if (r.id !== 1) return;
  const ex = r.result?.exceptionDetails;
  const out = ex ? { erreur: ex.exception?.description?.split('\n')[0] ?? ex.text, ligne: ex.lineNumber } : r.result?.result?.value ?? r.result;
  console.log(JSON.stringify(out));
  ws.close();
};
