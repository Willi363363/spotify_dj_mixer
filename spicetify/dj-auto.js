// Extension Spicetify « Mode DJ automatique » (transitions v2) : quand le mode est allumé (interrupteur de l'app
// Mode DJ), chaque morceau enchaîne tout seul vers le suivant, avec une transition du catalogue v2 (C1…C8, R1, R2).
// Orchestration seulement (ADR 0005) : la voix (DJCore.voix), le placement (DJCore.placement), le choix, le repli
// au plan et l'ordre v2 (DJCore.choix) vivent dans leurs modules, testés en `node --test spicetify/test/`.
// - Le saut se fait pile sur le temps, dans le contexte de lecture (la playlist continue), directement à
//   entreeB : une seule commande, sans silence (le moteur situe le changement à l'heure).
// - Le moteur (proto/e2/e2.py, http://127.0.0.1:47802) reçoit l'ordre v2 (ADR 0001) et joue la transition.
// Dans Node, le fichier exporte creer(env) pour les tests, avec un faux Spicetify.
(function (racine) {
  const MAQUETTE = 'http://127.0.0.1:47802';
  const KEY = 'dj-mixer:auto';
  // ms : ordre de saut donné quand la position annoncée dépasse la sortie de −LEAD ms ; le saut se produit ~90 ms
  // plus tard (e2.py, SWITCH_S), donc ~150 ms après le 1 de sortie. Le 1 de A est ainsi dans la mémoire du moteur,
  // qui le cherche avant la fin estimée de A (e2.py, A_AVANT_S). Essai direct 13 : l'instant du saut varie de ±100 ms
  // d'un essai à l'autre ; avec LEAD = +30 il tombait parfois sur le 1 ou juste avant.
  const LEAD = -60;
  const MARGIN_S = 15;      // une sortie trop proche de maintenant n'est pas prévue
  const AVANT_SAUT_MS = 1500;
  // Genre : l'API des genres n'est pas joignable depuis l'extension. On garde les morceaux dont un artiste figure
  // dans les playlists de référence du développeur (rap FR, shatta, bouyon) : sans ça, une grande playlist
  // fourre-tout faisait enchaîner sur du metal. (Choix du suivant : hors périmètre de la spec v2, H7.)
  const GENRE_REFS = ['4qKKSgcuPJ9D1DGwAAqquG', '39NDse2QZPhw2FMFO76C6N', '7xvIav5szRrdPSlZzKVTMh', '33T2yN3jibAPkkyhK1IC5g',
    '2UM5OkfUVT6BZkZ0j9Wpwp', '6Fs4BkSykcFsqz9XMXdpmU', '0WzHAU6W4iSq1n1s0zD3L3'];

  function creer(env) {
    const S = env.Spicetify, C = env.DJCore;
    const fetch_ = env.fetch;
    const sleep = env.sleep ?? ((ms) => new Promise((r) => setTimeout(r, ms)));
    const maintenant = env.maintenant ?? (() => Date.now());
    const P = S.Player, API = S.Platform.PlayerAPI;
    const nom = (id) => C.catalogue?.info?.(id)?.nom ?? id;
    const cache = new Map();
    async function audio(uri) {
      if (!cache.has(uri)) {
        const d = await S.getAudioData(uri);
        if (d && typeof d === 'object') d.uri = uri;
        cache.set(uri, d);
      }
      return cache.get(uri);
    }

    // status.plan : { forUri, A, B, choix, done, failed } ; choix.transition = identifiant v2 prévu
    // status.historique : [{ id, transition, entree }] (transition jouée si le moteur l'a rapportée)
    // status.log : [{ at, id, transition, nom, A, B, raison }], la plus récente d'abord
    const status = { enabled: false, text: 'Mode DJ automatique éteint.', plan: null, historique: [], log: [], force: null };
    let maquetteOk = false, maquetteBusy = false, delay = 0, target = 60, lastCheck = 0, expectedAt = 0;

    async function readState() {
      try {
        const r = await fetch_(`${MAQUETTE}/state`, { cache: 'no-store' });
        maquetteOk = r.ok;
        if (!r.ok) return;
        const s = await r.json();
        delay = s.delay_s ?? 0; target = s.target_s ?? 60; maquetteBusy = !!s.busy;
        // la variété suit ce que le moteur a vraiment joué (repli au rendu)
        const d = s.derniere_transition;
        const h = d && status.historique.find((x) => x.id === d.id);
        if (h && C.choix.IDS.includes(d.transition_jouee)) h.transition = d.transition_jouee;
      } catch { maquetteOk = false; }
    }

    const contexteLecture = () => {
      const ctx = P.data?.context?.uri ?? '';
      const melange = typeof P.getShuffle === 'function' ? P.getShuffle() : !!P.data?.shuffle;
      return ctx.startsWith('spotify:album:') && !melange ? 'album' : null;
    };

    // ── Plan d'une transition A → B ─────────────────────────────────────────────────────────────────
    // Rend le choix (DJCore.choix.choisir) enrichi de sortie_s et entree_s, ou { erreur }.
    // historique : remplace celui du mode auto (run.sh passe la transition précédente du banc d'essai)
    // minExit_s : nombre, ou fonction relue après les attentes (position de lecture + marge, mode auto).
    async function planTransition(A, B, { force = null, minExit_s = 0, graine = null, contexte, historique } = {}) {
      const [a, b] = await Promise.all([audio(A).catch(() => null), audio(B).catch(() => null)]);
      // Paroles (V1, allumé par défaut, ADR 0002) : cache, file espacée et back-off dans dj-voix.js ; null → V2.
      // Celles de A sont en général déjà en cache (chargées quand A était B). L'attente peut durer 8 s.
      const [la, lb] = await Promise.all([C.voix.chargerParoles(A), C.voix.chargerParoles(B)]);
      // Avance et sortie au plus tôt lues APRÈS les attentes (analyses, paroles) : pendant ce temps A a avancé et
      // l'avance du moteur a pu fondre. delay n'est rafraîchi par tick que si le mode auto est allumé (forçage).
      await readState();
      const minExit = typeof minExit_s === 'function' ? minExit_s() : minExit_s;
      const paire = C.placement.paire(a, b, { minExit_s: minExit, avance_s: delay, cible_avance_s: target,
        contexte: contexte === undefined ? contexteLecture() : contexte, voixA: la, voixB: lb, uriA: A, uriB: B });
      const alea = graine === null || graine === undefined ? Math.random : C.choix.rng(graine);
      const choix = C.choix.choisir(paire, historique ?? status.historique, { rng: alea, force: force ?? status.force });
      if (choix.erreur) return choix;
      if (!choix.points) return { erreur: `pas de transition : ${paire.refus ?? 'points introuvables'}` };
      choix.sortie_s = choix.points.sortie.t;
      choix.entree_s = choix.points.entree.t;
      // Mode auto (minExit_s fonction, A en cours de lecture) : sortie déjà dépassée ou trop proche pour le saut →
      // R2 (A jusqu'à sa fin) si elle est encore devant, sinon pas de plan. Le banc d'essai (transition.js) rejoue A
      // après le plan : il n'est pas concerné.
      const jouee = typeof minExit_s === 'function' && P.data?.item?.uri === A ? P.getProgress() : null;
      if (jouee !== null && choix.sortie_s * 1000 - jouee < AVANT_SAUT_MS) {
        const r2 = C.choix.choisir(paire, historique ?? status.historique, { rng: alea, force: 'R2' });
        if (r2.erreur || !r2.points || r2.points.sortie.t * 1000 - jouee < AVANT_SAUT_MS) {
          return { erreur: `sortie ${fmt(choix.sortie_s)} déjà dépassée (attente des paroles)` };
        }
        r2.replis_plan = [{ de: choix.transition, vers: 'R2', raison: 'sortie dépassée pendant l\'attente des paroles', ou: 'plan' }];
        r2.choisie = choix.choisie;
        r2.sortie_s = r2.points.sortie.t;
        r2.entree_s = r2.points.entree.t;
        return finirPlan(r2);
      }
      return finirPlan(choix);
    }
    function finirPlan(choix) {
      // repli décidé au plan (forçage impossible, moteur injoignable) : raison visible à l'écran
      const avis = [];
      if (!maquetteOk) avis.push('moteur injoignable : avance inconnue (0 s)');
      if (choix.transition !== choix.choisie) {
        const r = choix.replis_plan.map((x) => `${x.de} → ${x.vers} : ${x.raison}`).join(' ; ');
        avis.push(`${choix.choisie} impossible, ${choix.transition} à la place (${r || 'aucune transition éligible'})`);
      }
      choix.avertissement = avis.join(' · ') || null;
      if (choix.avertissement) status.text = `Plan : ${choix.avertissement}.`;
      return choix;
    }
    const ordre = (choix, opts) => C.choix.ordre(choix, choix.paire, opts);

    // ── Saut pile sur le temps ──────────────────────────────────────────────────────────────────────
    // Rend l'heure du saut, ou null s'il a été annulé (morceau changé à la main, ou pause, pendant l'attente).
    async function switchAt(exitMs, Bt, bStartS, ctx) {
      const aUri = P.data?.item?.uri;
      // posé avant l'attente : un changement de morceau d'ici au saut (Spotify qui passe seul au suivant juste
      // avant la sortie) ne doit pas déclencher de rattrapage vers un autre morceau que B
      expectedAt = maintenant() + Math.max(0, exitMs - P.getProgress());
      while (exitMs - P.getProgress() > LEAD) {
        if (P.data?.item?.uri !== aUri || P.data?.isPaused) return null;
        await sleep(Math.max(4, (exitMs - P.getProgress() - LEAD) / 2));
      }
      const t_wall = maintenant();
      const seekTo = Math.round(bStartS * 1000);
      // ce changement de morceau vient de nous : pas de rattrapage en plus
      expectedAt = maintenant();
      if (ctx?.uri && Bt.uid && !ctx.uri.startsWith('spotify:track:')) {
        await API.play({ uri: ctx.uri, url: ctx.url }, {}, { skipTo: { uid: Bt.uid, uri: Bt.uri }, seekTo });
      } else {
        await API.play({ uri: Bt.uri }, {}, { seekTo });  // hors playlist (file, lecture auto) : B seul
      }
      return t_wall;
    }

    // Rend null si le moteur a accepté l'ordre, sinon la raison du refus
    async function sendOrder(order) {
      try {
        const r = await fetch_(`${MAQUETTE}/order`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(order) });
        if (r.ok) return null;
        return (await r.json().catch(() => ({}))).message ?? `erreur ${r.status}`;
      } catch { return 'maquette injoignable'; }
    }

    const isOn = () => S.LocalStorage.get(KEY) === '1';
    const nextTrack = () => (S.Queue?.nextTracks ?? []).map((t) => t.contextTrack).find((t) => t?.uri?.startsWith('spotify:track:'));

    // ── Morceau suivant choisi par le mode DJ (gardé tel quel, ADR 0004) ────────────────────────────
    const pool = { ctx: null, items: [] };
    const played = new Set();
    async function contents(uri) {
      let items = [];
      for (let off = 0; off < 5000; off += 500) {
        const c = await S.Platform.PlaylistAPI.getContents(uri, { limit: 500, offset: off });
        items = items.concat(c.items);
        if (c.items.length < 500) break;
      }
      return items;
    }
    let genreArtists = null;
    async function loadPool() {
      const ctx = P.data?.context?.uri;
      if (!ctx?.startsWith('spotify:playlist:') || pool.ctx === ctx || !S.Platform.PlaylistAPI) return;
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
      const PL = C.placement;
      const a = await audio(aUri).catch(() => null);
      if (!a?.track || !pool.items.length) return null;
      const cands = pool.items.filter((t) => t.uri !== aUri && !played.has(t.uri)).sort(() => Math.random() - 0.5).slice(0, 40);
      let best = null;
      for (const t of cands) {
        const b = await audio(t.uri).catch(() => null);
        if (!b?.bars?.length || !b.sections?.length) continue;
        const gap = PL.ecartTempo(a.track.tempo, b.track.tempo);
        const kd = PL.camelotDist(PL.camelot(a.track), PL.camelot(b.track));
        const score = gap * 100 + (kd === null ? 1 : kd >= 3 ? 5 : kd) + (t.metadata.artist_name === aArtist ? 2 : 0)
          + Math.abs(a.track.loudness - b.track.loudness) / 3;
        if (!best || score < best.score) best = { score, gap, track: t };
      }
      return best;
    }

    const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
    const titre = (Bt) => Bt?.metadata?.title ?? 'suivant';

    // ── Mode automatique ────────────────────────────────────────────────────────────────────────────
    async function tick() {
      status.enabled = isOn();
      const item = P.data?.item;
      if (!status.enabled) { status.plan = null; status.text = 'Mode DJ automatique éteint.'; return; }
      if (!item?.uri?.startsWith('spotify:track:')) { status.text = 'En attente d\'un morceau.'; return; }
      played.add(item.uri);
      await loadPool();
      // Album joué dans l'ordre (cas 16) : B est la piste suivante de l'album, jamais un morceau de la réserve d'une
      // playlist écoutée avant (essai direct 13 : le mode auto quittait l'album)
      const album = contexteLecture() === 'album';
      if (!album && pool.items.length && status.next?.forUri !== item.uri) {
        status.next = { forUri: item.uri, pick: null };
        status.text = 'Recherche du morceau suivant le plus compatible…';
        status.next.pick = await chooseNext(item.uri, item.artists?.[0]?.name);
      }
      const Bt = !album && status.next?.forUri === item.uri && status.next.pick ? status.next.pick.track : nextTrack();
      const p = status.plan;
      if (p && (p.forUri !== item.uri || (!p.done && Bt && p.B.uri !== Bt.uri))) status.plan = null;  // morceau ou file changés
      if (maintenant() - lastCheck > 5000) { lastCheck = maintenant(); await readState(); }
      // Un test lancé depuis l'écran (run.sh) pilote Spotify lui-même : le mode auto se met en veille
      if (maquetteBusy) { status.plan = null; status.text = 'Test manuel en cours : mode auto en veille.'; return; }
      if (!status.plan) {
        if (!Bt) { status.text = 'Pas de morceau suivant dans la file.'; return; }
        // Sans moteur, un saut couperait le morceau sans transition : on ne prévoit rien (R3).
        if (!maquetteOk) { status.text = 'Maquette éteinte : Spotify joue normalement, sans transition.'; return; }
        try {
          const choix = await planTransition(item.uri, Bt.uri, { minExit_s: () => P.getProgress() / 1000 + MARGIN_S });
          status.plan = { forUri: item.uri, A: item.name ?? item.metadata?.title ?? '', B: Bt, choix, done: false, failed: !!choix.erreur };
          status.text = choix.erreur ? `Pas de transition pour ce morceau : ${choix.erreur}.`
            : `Prévu : ${nom(choix.transition)} vers « ${titre(Bt)} » à ${fmt(choix.sortie_s)}.`
              + (choix.avertissement ? ` (${choix.avertissement})` : '');
        } catch (e) { status.plan = { forUri: item.uri, B: Bt, failed: true }; status.text = `Analyse impossible : ${e}`; }
      }
      const q = status.plan;
      if (!q || q.done || q.failed || !q.choix) return;
      const exitMs = q.choix.sortie_s * 1000;
      const remaining = exitMs - P.getProgress();
      if (remaining < -500) { q.failed = true; status.text = 'Point de sortie dépassé (saut manuel ?) : pas de transition.'; return; }
      if (remaining > AVANT_SAUT_MS || P.data?.isPaused) return;
      // Juste avant le saut : l'avance réelle a pu fondre depuis le plan → repli au plan (§8)
      await readState();
      if (!maquetteOk || maquetteBusy) { q.failed = true; status.text = 'Maquette indisponible au moment du saut : pas de transition.'; return; }
      const avant = q.choix.transition;
      q.choix = C.choix.replierAuPlan(q.choix, { avance_s: delay });
      q.choix.sortie_s = q.choix.points.sortie.t;
      q.choix.entree_s = q.choix.points.entree.t;
      if (q.choix.transition !== avant) {
        status.text = `Repli au plan ${avant} → ${q.choix.transition} (${q.choix.replis_plan.at(-1)?.raison ?? ''}).`;
        if (q.choix.sortie_s * 1000 - P.getProgress() > AVANT_SAUT_MS) return;   // R2 : A va jusqu'à sa fin
      }
      // Ordre vérifié avant le saut : un ordre refusé après coup donnerait une coupe sèche
      const erreurs = C.choix.valider(ordre(q.choix, { t_wall: maintenant() }));
      if (erreurs.length) { q.failed = true; status.text = `Ordre invalide (${erreurs.join(', ')}) : pas de transition.`; return; }
      q.done = true;
      const ctx = P.data?.context;
      const t_wall = await switchAt(q.choix.sortie_s * 1000, q.B, q.choix.entree_s, ctx);
      if (t_wall === null) { q.failed = true; status.text = 'Saut annulé (morceau changé ou pause).'; return; }
      const gapless = !!(ctx?.uri && q.B.uid && !ctx.uri.startsWith('spotify:track:'));  // saut dans la playlist
      const o = ordre(q.choix, { t_wall, gapless });
      q.ordre = o;
      status.historique = [...status.historique, { id: o.id, transition: o.transition, entree: o.b.entree }].slice(-12);
      status.log = [{ at: maintenant(), id: o.id, transition: o.transition, nom: nom(o.transition), A: q.A, B: titre(q.B),
        raison: o.raison }, ...status.log].slice(0, 8);
      if (status.force) status.force = null;   // forçage valable pour la prochaine transition seulement
      const refus = await sendOrder(o);
      status.text = refus === null ? `Transition lancée vers « ${titre(q.B)} » : elle s'entendra dans la maquette.`
        : `La maquette a refusé l'ordre (${refus}) : saut fait sans transition.`;
    }

    // Morceau changé sans nous (bouton suivant, fin naturelle après un saut raté) : ordre de rattrapage R1
    let prev = { uri: P.data?.item?.uri, progress: 0 };
    const suivreProgression = () => { if (P.data?.item?.uri === prev.uri) prev.progress = P.getProgress(); };
    async function onSongChange() {
      const uri = P.data?.item?.uri, from = prev;
      prev = { uri, progress: 0 };
      if (maintenant() - expectedAt < 3000) return null;
      await readState();  // l'état d'il y a 5 s peut ignorer un test manuel qui vient de démarrer
      if (!isOn() || !maquetteOk || maquetteBusy || !from.uri?.startsWith('spotify:track:') || !uri?.startsWith('spotify:track:')
        || from.uri === uri || from.progress < 10000) return null;
      // l'événement arrive après le changement dans le flux ; le moteur le situe d'après ce qu'espion a vu
      const t_wall = maintenant() - 300;
      try {
        const [a, b] = await Promise.all([audio(from.uri), audio(uri)]);
        const o = C.choix.ordreRattrapage(a, b, { t_wall, to_uri: uri, uriA: from.uri });
        if (o.erreur) return null;
        const refus = await sendOrder(o);
        status.text = refus === null ? 'Morceau changé à la main : transition de rattrapage envoyée.' : `Rattrapage refusé : ${refus}.`;
        return o;
      } catch (e) { status.text = `Rattrapage impossible : ${e?.message ?? e}`; return null; }
    }

    // Force la prochaine transition (C1…C8, R1, R2) ; null annule. Le plan en cours est refait.
    function forcer(id) {
      if (id !== null && id !== undefined && !C.choix.IDS.includes(id)) return false;
      status.force = id ?? null;
      status.plan = null;
      return true;
    }

    const DJ = {
      version: 2, status, planTransition, switchAt, sendOrder, ordre, forcer, LEAD,
      // paroles : compteurs de la file (requêtes, 429, cache) ; allumer / éteindre V1 (drapeau dj-mixer:paroles)
      paroles: () => C.voix.etatParoles?.() ?? null,
      setParoles: (on) => S.LocalStorage.set(C.voix.DRAPEAU, on ? '1' : '0'),
      setAuto: (on) => { S.LocalStorage.set(KEY, on ? '1' : '0'); status.plan = null; },
    };

    function demarrer() {
      setInterval(suivreProgression, 500);
      P.addEventListener('songchange', onSongChange);
      let busy = false;
      setInterval(async () => {
        if (busy) return;
        busy = true;
        try { await tick(); } catch (e) {
          console.error('dj-auto', e);
          status.text = `Erreur du mode auto : ${e?.message ?? e}`;
        } finally { busy = false; }
      }, 250);
    }

    return { DJ, tick, onSongChange, suivreProgression, readState, demarrer, status };
  }

  if (typeof module === 'object' && module.exports) { module.exports = { creer, LEAD, MAQUETTE }; return; }
  (function attendre() {
    const S = racine.Spicetify, C = racine.DJCore;
    if (!S?.Player?.data || !S.Platform?.PlayerAPI || !S.getAudioData || !C?.catalogue || !C?.voix || !C?.placement || !C?.choix) {
      setTimeout(attendre, 500);
      return;
    }
    const inst = creer({ Spicetify: S, fetch: racine.fetch.bind(racine), DJCore: C });
    racine.DJ = inst.DJ;
    inst.demarrer();
  })();
})(globalThis);
