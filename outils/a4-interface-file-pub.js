// A4 interface (bouton, raccourci, affichage), A5 file d'attente, A6 repérage des pubs.
// Tout ce qui est ajouté est retiré à la fin, sauf le bouton laissé visible 20 s pour la capture.
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const out = {};

  // A4 : bouton dans la barre de lecture + raccourci clavier + affichage tempo/tonalité
  try {
    const a = await Spicetify.getAudioData(Spicetify.Player.data.item.uri);
    const label = `DJ ${Math.round(a.track.tempo)} BPM`;
    let clicks = 0;
    const btn = new Spicetify.Playbar.Button(label, 'play', () => { clicks++; Spicetify.showNotification(`${label}, transition demandée`); });
    btn.register();
    globalThis.__djBtn = btn;
    out.bouton = { ok: true, label, element: !!document.querySelector(`button[aria-label="${label}"]`) };
    globalThis.__djShortcut = () => Spicetify.showNotification('Raccourci DJ reçu');
    Spicetify.Keyboard.registerShortcut({ key: Spicetify.Keyboard.KEYS.D, ctrl: true, alt: true }, globalThis.__djShortcut);
    out.raccourci = { ok: true, touches: 'Ctrl+Alt+D' };
    setTimeout(() => { btn.deregister(); Spicetify.Keyboard._deregisterShortcut({ key: 'd', ctrl: true, alt: true }); }, 20000);
  } catch (e) { out.interface = { erreur: String(e?.message ?? e) }; }

  // A5 : ajout puis retrait d'un morceau dans la file
  try {
    const before = (Spicetify.Queue?.nextTracks ?? []).length;
    const uri = 'spotify:track:1pKYYY0dkg23sQQXi0Q5zN';
    await Spicetify.addToQueue([{ uri }]);
    await sleep(800);
    const q1 = Spicetify.Queue?.nextTracks ?? [];
    const pos = q1.findIndex((t) => t.contextTrack?.uri === uri);
    const provider = q1[pos]?.provider;
    await Spicetify.removeFromQueue([{ uri }]);
    await sleep(800);
    const q2 = Spicetify.Queue?.nextTracks ?? [];
    out.file = { avant: before, apresAjout: q1.length, position: pos, provider, apresRetrait: q2.length, encorePresent: q2.some((t) => t.contextTrack?.uri === uri && t.provider === 'queue') };
    out.fileProviders = [...new Set(q2.map((t) => t.provider))];
  } catch (e) { out.file = { erreur: String(e?.message ?? e) }; }

  // A6 : ce que le lecteur expose pour reconnaître une pub
  const it = Spicetify.Player.data?.item ?? {};
  out.pub = {
    champsItem: Object.keys(it),
    type: it.type, mediaType: it.mediaType, provider: it.provider,
    metadataCles: Object.keys(it.metadata ?? {}).filter((k) => /ad|advert|sponsor|is_/i.test(k)),
    etatCles: Object.keys(Spicetify.Player.data ?? {}).filter((k) => /ad|restrict|sign/i.test(k)),
    adsApi: Object.keys(Spicetify.Platform ?? {}).filter((k) => /ad/i.test(k) && !/load|read|head|thread/i.test(k)),
  };
  return out;
})()
