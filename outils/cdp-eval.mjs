const ws = new WebSocket(process.argv[2]);
ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: process.argv[3], awaitPromise: true, returnByValue: true } }));
ws.onmessage = (m) => { const r = JSON.parse(m.data); if (r.id !== 1) return; console.log(JSON.stringify(r.result?.result?.value ?? r.result)); ws.close(); };
