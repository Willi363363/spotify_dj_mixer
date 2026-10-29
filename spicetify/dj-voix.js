// Voix par mesure au moment du plan (ADR 0002) : un score dans [0 ; 1] par mesure et une source.
// - V1 (défaut depuis le 2026-10-29) : paroles synchronisées ; une mesure qu'une ligne de paroles recouvre (≥ RECOUVRE_S)
//   vaut la part couverte, au moins SEUIL_SANS_VOIX ; 0 sinon. Éteint seulement si LocalStorage 'dj-mixer:paroles' === '0'. Cache LocalStorage par
//   morceau (LRU, absents 14 j, présents 30 j), file espacée, back-off sur 429/401/403/5xx ; tout échec → V2.
// - V2 (repli) : régression logistique sur les segments de l'analyse Spotify, normalisée par morceau.
// - Sans segments : toutes les mesures à 1 (pire cas : vocal), source 'aucune'.
// Seuils communs : vocal ≥ SEUIL_VOCAL, sans voix < SEUIL_SANS_VOIX. Fonctions pures sauf chargerParoles.
// Chargé comme extension Spicetify (globalThis.DJCore.voix) et par Node (require) pour les tests.
(function (racine) {
  const SEUIL_VOCAL = 0.5;
  const SEUIL_SANS_VOIX = 0.3;
  const DRAPEAU = 'dj-mixer:paroles';
  const LIGNE_MAX_S = 8;
  const RECOUVRE_S = 0.1;           // une ligne « recouvre » une mesure au-delà de 100 ms (précision des débuts de ligne)
  // Fin chantée d'une ligne (pour couper sans couper un mot) : au plus S_PAR_MOT s par mot après son début. Au-delà,
  // les scores V3 sur l'audio réel sont ceux des mesures sans paroles (docs/tests/11-voix.md, « Limites »).
  const S_PAR_MOT = 0.45;
  // Une ligne « chevauche » un instant t si elle a commencé avant t − COUPE_TOL_S et se chante encore après
  // t + COUPE_TOL_S (même tolérance que RECOUVRE_S : la précision des débuts de ligne).
  const COUPE_TOL_S = RECOUVRE_S;
  // File des requêtes de paroles (essai 13 : 429 au-delà de ~30 requêtes rapprochées ; 77 requêtes à 3 s : aucun 429)
  const FILE = { espacement_ms: 3000, delai_requete_ms: 5000, attente_max_ms: 8000, backoff_min_ms: 30000,
    backoff_max_ms: 600000, absent_ttl_ms: 14 * 86400000, present_ttl_ms: 30 * 86400000, cache_max: 600 };
  const CLE_CACHE = 'dj-mixer:paroles-cache';
  // V2 : régression logistique sur les caractéristiques des segments (z-scores robustes par morceau, plus leur moyenne
  // sur ±2 mesures), recalibrée en probabilité de voix (Platt). Ajustée le 2026-10-29 sur les morceaux à paroles
  // synchronisées (vérité terrain : une ligne de paroles recouvre la mesure), validation croisée groupée par morceau.
  // Résultats : docs/tests/11-voix.md. Poids : `caracteristiques` puis leurs moyennes sur ±contexte mesures.
  const V2 = { silence_db: -45, contexte: 2,
    planchers: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.02, 0.1, 1.0, 1.0, 0.03],
    poids: [0.1466, 0.0219, -0.0449, -0.0143, 0.054, 0.1327, -0.0607, -0.0032, 0.0165, 0.0203, 0.0216, 0.0302, -0.0214, 0.0105, 0.024, -0.011, -0.0833, 0.4092, -0.0711, -0.3054, -0.2633, 0.3334, 0.3787, -0.0895, 0.0518, -0.0808, -0.1741, -0.1407, -0.1515, -0.066, 0.197, 0.1561, 0.213, -0.1847],
    biais: 2.5506 };

  const sigmoide = (x) => 1 / (1 + Math.exp(-x));
  const borne = (x) => Math.min(1, Math.max(0, x));

  // Index de la première mesure qui commence à t (à 50 ms près), ou bars.length
  function indexMesure(bars, t) {
    const k = bars.findIndex((x) => x.start >= t - 0.05);
    return k < 0 ? bars.length : k;
  }
  // Les n mesures avant t (la dernière en dernier) ou les n mesures à partir de t
  function fenetre(analyse, t0, n, sens) {
    const bars = analyse?.bars ?? [];
    const k = indexMesure(bars, t0);
    return sens === 'avant' ? bars.slice(Math.max(0, k - n), k) : bars.slice(k, k + n);
  }

  // Quantile à interpolation linéaire (comme numpy.percentile)
  function quantile(trie, q) {
    const h = (trie.length - 1) * q, i = Math.floor(h);
    return i + 1 < trie.length ? trie[i] + (h - i) * (trie[i + 1] - trie[i]) : trie[i];
  }
  // Scores V2 de toutes les mesures du morceau (cache par analyse), ou null sans segments
  const cacheV2 = new WeakMap();
  function scoresV2(analyse) {
    if (!analyse || typeof analyse !== 'object') return null;
    if (cacheV2.has(analyse)) return cacheV2.get(analyse);
    const car = caracteristiques(analyse);
    const out = car ? scoresCaracteristiques(car) : null;
    cacheV2.set(analyse, out);
    return out;
  }
  // Scores V2 à partir des caractéristiques brutes { lignes, actif } d'un morceau entier
  function scoresCaracteristiques({ lignes, actif }) {
    const n = lignes.length, K = NOMS_CAR.length;
    const ref = lignes.filter((_, i) => actif[i]);
    const base = ref.length ? ref : lignes;
    // z-scores robustes : (x − médiane) / max(écart interquartile / 1,349, plancher), bornés à ±4
    const Z = lignes.map(() => new Array(K));
    for (let k = 0; k < K; k++) {
      const col = base.map((x) => x[k]).sort((x, y) => x - y);
      const med = quantile(col, 0.5), s = Math.max((quantile(col, 0.75) - quantile(col, 0.25)) / 1.349, V2.planchers[k]);
      for (let i = 0; i < n; i++) Z[i][k] = Math.min(4, Math.max(-4, (lignes[i][k] - med) / s));
    }
    const r = V2.contexte;
    return Z.map((z, i) => {
      if (!actif[i]) return 0;
      const i0 = Math.max(0, i - r), i1 = Math.min(n, i + r + 1);
      let x = V2.biais;
      for (let k = 0; k < K; k++) {
        let m = 0;
        for (let j = i0; j < i1; j++) m += Z[j][k];
        x += V2.poids[k] * z[k] + V2.poids[K + k] * (m / (i1 - i0));
      }
      return +sigmoide(x).toFixed(3);
    });
  }

  // Caractéristiques brutes par mesure (moyennes pondérées par la durée des segments qui commencent dans la mesure) :
  // [timbre 0…11, pic de chroma, densité (segments par temps), sonie max, attaque (max − début), confiance]
  // et actif (mesure non silencieuse). Normalisées ensuite par morceau (z-scores robustes).
  const NOMS_CAR = ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9', 't10', 't11', 'pic', 'dens', 'sonie',
    'attaque', 'conf'];
  function caracteristiques(analyse) {
    const bars = analyse?.bars ?? [], segs = analyse?.segments ?? [];
    if (!bars.length || !segs.length) return null;
    const lignes = [], actif = [];
    let j = 0;
    for (const b of bars) {
      const fin = b.start + b.duration;
      while (j < segs.length && segs[j].start < b.start - 1e-6) j++;
      const v = new Array(NOMS_CAR.length).fill(0);
      let n = 0, dur = 0, sonie = -60;
      for (let i = j; i < segs.length && segs[i].start < fin - 1e-6; i++) {
        const s = segs[i], d = Math.max(s.duration ?? 0, 1e-3);
        n++; dur += d;
        for (let k = 0; k < 12; k++) v[k] += (s.timbre?.[k] ?? 0) * d;
        const p = s.pitches ?? [];
        v[12] += (p.length ? 1 - p.reduce((x, y) => x + y, 0) / p.length : 0) * d;
        v[15] += ((s.loudness_max ?? -60) - (s.loudness_start ?? -60)) * d;
        v[16] += (s.confidence ?? 0) * d;
        sonie = Math.max(sonie, s.loudness_max ?? -60);
      }
      if (n) for (const k of [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 16]) v[k] /= dur;
      v[13] = n / 4;
      v[14] = sonie;
      lignes.push(v);
      actif.push(n > 0 && sonie >= V2.silence_db);
    }
    return { lignes, actif };
  }

  // V2 sur les n mesures d'un bord (sens 'avant' : les n avant t0, la dernière en dernier ; 'apres' : les n après)
  function voixSegments(analyse, t0, nMesures, sens) {
    const bars = analyse?.bars ?? [];
    const k = indexMesure(bars, t0);
    const [i0, i1] = sens === 'avant' ? [Math.max(0, k - nMesures), k] : [k, Math.min(bars.length, k + nMesures)];
    const s = scoresV2(analyse);
    if (!s) return new Array(Math.max(0, i1 - i0)).fill(1);
    return s.slice(i0, i1);
  }

  // Réponse color-lyrics → lignes [{ debut_s, fin_s, vide }], ou null si inutilisable (non synchronisé, format inconnu)
  function parserParoles(json) {
    const l = json?.lyrics;
    if (!l || l.syncType !== 'LINE_SYNCED' || !Array.isArray(l.lines) || !l.lines.length) return null;
    const lignes = [];
    for (const x of l.lines) {
      const debut = Number(x?.startTimeMs) / 1000;
      if (!Number.isFinite(debut) || debut < 0) return null;
      const mots = typeof x.words === 'string' ? x.words.trim() : '';
      const vide = !mots || /^[♪\s]+$/u.test(mots);
      lignes.push({ debut_s: debut, vide, mots: vide ? 0 : mots.split(/\s+/u).length });
    }
    lignes.sort((a, b) => a.debut_s - b.debut_s);
    lignes.forEach((x, i) => {
      const suiv = lignes[i + 1]?.debut_s ?? Infinity;
      x.fin_s = +Math.min(suiv, x.debut_s + LIGNE_MAX_S).toFixed(3);
      x.chant_s = +Math.min(x.fin_s, x.debut_s + Math.max(1, x.mots) * S_PAR_MOT).toFixed(3);
      delete x.mots;
    });
    return lignes;
  }

  // Une ligne de paroles (non vide) est-elle en train d'être chantée à l'instant t (un mot serait coupé) ?
  // true / false avec des paroles, null sans paroles (l'appelant garde alors la règle « voix sur la dernière mesure »).
  // Fin d'une ligne : sa fin chantée estimée (chant_s, au plus S_PAR_MOT s par mot), sinon le début de la suivante.
  function coupeLigne(lignes, t) {
    if (!Array.isArray(lignes) || !lignes.length) return null;
    return lignes.some((x) => !x.vide && x.debut_s < t - COUPE_TOL_S && (x.chant_s ?? x.fin_s) > t + COUPE_TOL_S);
  }
  // Une ligne finit-elle (fin chantée) dans [t − avant_s ; t + COUPE_TOL_S] ? null sans paroles.
  function finDeLigne(lignes, t, avant_s) {
    if (!Array.isArray(lignes) || !lignes.length) return null;
    return lignes.some((x) => !x.vide && (x.chant_s ?? x.fin_s) >= t - avant_s && (x.chant_s ?? x.fin_s) <= t + COUPE_TOL_S);
  }

  // V1, en trois zones (ADR 0002) : 0 si aucune ligne non vide ne recouvre la mesure (« sans voix ») ; sinon la part
  // couverte, au moins SEUIL_SANS_VOIX (une mesure recouverte n'est jamais « sans voix ») : « vocale » dès la moitié
  // couverte, « ni l'un ni l'autre » en dessous (bloque C4, C6, C7, mais ne compte ni pour la sortie ni pour O4).
  // Recouvrir = au moins RECOUVRE_S (ou la moitié d'une mesure très courte), la précision des débuts de ligne.
  function voixParoles(lignes, mesures) {
    const pleines = (lignes ?? []).filter((x) => !x.vide);
    return mesures.map((m) => {
      const a = m.start, b = m.start + m.duration;
      let c = 0;
      for (const x of pleines) c += Math.max(0, Math.min(b, x.fin_s) - Math.max(a, x.debut_s));
      if (!(c > 0 && c >= Math.min(RECOUVRE_S, m.duration / 2))) return 0;
      return +Math.max(SEUIL_SANS_VOIX, borne(c / Math.max(m.duration, 1e-6))).toFixed(3);
    });
  }

  // ── Chargement des paroles : cache LocalStorage, file espacée, back-off sur les erreurs HTTP ──────────
  // Cache : { id: [t_ecrit, lignes | null, t_utilise] } (null = pas de paroles synchronisées, réessayé après
  // absent_ttl_ms ; paroles présentes redemandées après present_ttl_ms, l'ancienne version servant tant que la
  // nouvelle n'est pas arrivée). lignes : [[debut_s, fin_s, vide 0|1, chant_s], …]. Éviction : la moins récemment
  // utilisée. Une entrée illisible est supprimée et redemandée. Seuls un succès et une absence avérée (404, réponse
  // sans paroles synchronisées) vont en cache ; jamais une erreur passagère (429, 401, 5xx, délai, réseau, format inconnu).
  const etat = { cache: null, enCours: new Map(), derniere: 0, pauseJusqua: 0, attente429: 0, chaine: Promise.resolve(),
    stats: { requetes: 0, ok: 0, absent: 0, limite: 0, echec: 0, cache: 0, repare: 0 } };
  const maintenant = () => Date.now();
  const dormir = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));
  const UTILISE_PAS_MS = 60000;    // l'heure d'utilisation n'est réécrite dans le LocalStorage qu'au-delà d'une minute
  function lireCache(S) {
    if (etat.cache) return etat.cache;
    try { etat.cache = JSON.parse(S?.LocalStorage?.get(CLE_CACHE) ?? '{}') ?? {}; } catch { etat.cache = {}; }
    if (typeof etat.cache !== 'object' || Array.isArray(etat.cache)) etat.cache = {};
    return etat.cache;
  }
  function sauver(S) {
    try { S?.LocalStorage?.set(CLE_CACHE, JSON.stringify(etat.cache ?? {})); } catch { /* quota : le cache mémoire suffit */ }
  }
  const utilise = (e) => (Number.isFinite(e?.[2]) ? e[2] : Number.isFinite(e?.[0]) ? e[0] : 0);
  function ecrireCache(S, id, lignes) {
    const c = lireCache(S), t = maintenant();
    c[id] = [t, lignes ? lignes.map((x) => [x.debut_s, x.fin_s, x.vide ? 1 : 0, x.chant_s ?? x.fin_s]) : null, t];
    const ids = Object.keys(c);
    if (ids.length > FILE.cache_max) {
      ids.sort((x, y) => utilise(c[x]) - utilise(c[y])).slice(0, ids.length - FILE.cache_max).forEach((x) => delete c[x]);
    }
    sauver(S);
  }
  // Entrée lisible ? [t fini, null | tableau de [d, f, v(, c)] numériques]
  const ligneOk = (x) => Array.isArray(x) && Number.isFinite(x[0]) && Number.isFinite(x[1]) && x[1] >= x[0]
    && (x[3] === undefined || Number.isFinite(x[3]));
  const entreeOk = (e) => Array.isArray(e) && Number.isFinite(e[0]) && (e[1] === null || (Array.isArray(e[1]) && e[1].every(ligneOk)));
  // Rend { trouve: true, lignes } si le cache répond ; sinon { trouve: false, perime } (perime : paroles expirées,
  // servies seulement si la nouvelle requête échoue)
  function depuisCache(S, id) {
    const c = lireCache(S), e = c[id];
    if (e === undefined) return { trouve: false };
    if (!entreeOk(e)) { delete c[id]; etat.stats.repare++; sauver(S); return { trouve: false }; }
    const age = maintenant() - e[0];
    if (e[1] === null) return age < FILE.absent_ttl_ms ? { trouve: true, lignes: null } : { trouve: false };
    const lignes = e[1].map(([d, f, v, ch]) => ({ debut_s: d, fin_s: f, vide: !!v, chant_s: ch ?? f }));
    if (age >= FILE.present_ttl_ms) return { trouve: false, perime: lignes };
    if (maintenant() - utilise(e) > UTILISE_PAS_MS) { e[2] = maintenant(); sauver(S); } else e[2] = maintenant();
    return { trouve: true, lignes };
  }
  // Statut HTTP d'une réponse ou d'une erreur, quelle que soit sa forme : {code}, {status}, {error: {status|code}},
  // message « … 429 … » ; null si aucun
  function statutHttp(x) {
    if (x === null || x === undefined) return null;
    for (const v of [x.code, x.status, x.statusCode, x.error?.status, x.error?.code]) {
      const n = Number(v);
      if (Number.isInteger(n) && n >= 100 && n < 600) return n;
    }
    const m = /\b([1-5]\d\d)\b/.exec(String(x.message ?? x.error?.message ?? (typeof x === 'string' ? x : '')));
    return m ? Number(m[1]) : null;
  }
  async function requete(S, id) {
    const url = `https://spclient.wg.spotify.com/color-lyrics/v2/track/${id}?format=json&market=from_token`;
    let minuteur;
    const delai = new Promise((r) => { minuteur = setTimeout(() => r({ delai: true }), FILE.delai_requete_ms); });
    etat.stats.requetes++;
    const json = await Promise.race([S.CosmosAsync.get(url).catch((e) => ({ erreur: e ?? 'erreur' })), delai]);
    clearTimeout(minuteur);
    etat.derniere = maintenant();
    if (json?.delai) { etat.stats.echec++; return undefined; }
    const lignes = parserParoles(json);
    if (lignes) { etat.attente429 = 0; etat.stats.ok++; ecrireCache(S, id, lignes); return lignes; }
    const statut = json?.erreur !== undefined ? statutHttp(json.erreur) : statutHttp(json);
    // Absence avérée : 404, ou réponse de paroles valide mais non synchronisée → en cache (absent_ttl_ms)
    if (statut === 404 || (statut === null && json?.lyrics && typeof json.lyrics === 'object')) {
      etat.attente429 = 0; etat.stats.absent++; ecrireCache(S, id, null); return null;
    }
    // 429, 401, 403, 5xx : pause de la file (30 s doublée jusqu'à 10 min) ; jamais en cache
    if (statut === 429 || statut === 401 || statut === 403 || (statut !== null && statut >= 500)) {
      etat.attente429 = Math.min(FILE.backoff_max_ms, Math.max(FILE.backoff_min_ms, 2 * etat.attente429));
      etat.pauseJusqua = maintenant() + etat.attente429;
      etat.stats[statut === 429 ? 'limite' : 'echec']++;
      return undefined;
    }
    // réseau, format inconnu, autre statut : passager, ni cache ni pause
    etat.stats.echec++;
    return undefined;
  }
  // Paroles d'un morceau (V1) : cache, sinon requête dans la file (une toutes les FILE.espacement_ms). Rend les lignes,
  // ou null (drapeau éteint, pas de paroles synchronisées, file en pause, attente > FILE.attente_max_ms) :
  // l'appelant passe alors à V2. Une requête qui dépasse l'attente continue et remplit le cache pour la fois suivante.
  // Paroles expirées en cache : redemandées, mais servies si la requête échoue.
  async function chargerParoles(uri, { attenteMax = FILE.attente_max_ms } = {}) {
    const S = racine.Spicetify;
    try {
      if (S?.LocalStorage?.get(DRAPEAU) === '0' || !S?.CosmosAsync?.get) return null;
      const id = /^spotify:track:([A-Za-z0-9]{22})$/.exec(uri ?? '')?.[1];
      if (!id) return null;
      const c = depuisCache(S, id);
      if (c.trouve) { etat.stats.cache++; return c.lignes; }
      const perime = c.perime ?? null;
      if (maintenant() < etat.pauseJusqua) return perime;
      if (!etat.enCours.has(id)) {
        const tache = etat.chaine.then(async () => {
          await dormir(etat.derniere + FILE.espacement_ms - maintenant());
          if (maintenant() < etat.pauseJusqua) return undefined;
          const d = depuisCache(S, id);
          return d.trouve ? d.lignes : requete(S, id);
        }).catch(() => undefined).finally(() => etat.enCours.delete(id));
        etat.chaine = tache;
        etat.enCours.set(id, tache);
      }
      let minuteur;
      const delai = new Promise((r) => { minuteur = setTimeout(() => r(undefined), attenteMax); });
      const r = await Promise.race([etat.enCours.get(id) ?? Promise.resolve(depuisCache(S, id).lignes), delai]);
      clearTimeout(minuteur);
      return r === undefined ? perime : r;
    } catch { return null; }
  }
  // Pour les tests et le débogage : réglages de la file, remise à zéro, compteurs
  function reglerFile(o = {}) { Object.assign(FILE, o); return { ...FILE }; }
  function reinitialiser() {
    etat.cache = null; etat.enCours.clear(); etat.derniere = 0; etat.pauseJusqua = 0; etat.attente429 = 0;
    etat.chaine = Promise.resolve();
    for (const k of Object.keys(etat.stats)) etat.stats[k] = 0;
  }
  const etatParoles = () => ({ ...etat.stats, pause_s: Math.max(0, Math.round((etat.pauseJusqua - maintenant()) / 1000)),
    en_attente: etat.enCours.size });

  // Voix d'un bord : paroles si disponibles, sinon segments, sinon 1 partout
  function voixBord(analyse, lignes, t0, nMesures, sens) {
    if (Array.isArray(lignes) && lignes.length) {
      return { valeurs: voixParoles(lignes, fenetre(analyse, t0, nMesures, sens)), source: 'paroles' };
    }
    const n = fenetre(analyse, t0, nMesures, sens).length;
    if (!scoresV2(analyse)) return { valeurs: new Array(n).fill(1), source: 'aucune' };
    return { valeurs: voixSegments(analyse, t0, nMesures, sens), source: 'segments' };
  }

  // Score d'une mesure donnée par son index (paroles ou V2) ; 1 si inconnu
  function voixMesure(analyse, lignes, i) {
    const b = analyse?.bars?.[i];
    if (!b) return 1;
    if (Array.isArray(lignes) && lignes.length) return voixParoles(lignes, [b])[0];
    const s = scoresV2(analyse);
    return s ? s[i] : 1;
  }

  const api = { SEUIL_VOCAL, SEUIL_SANS_VOIX, DRAPEAU, CLE_CACHE, RECOUVRE_S, S_PAR_MOT, COUPE_TOL_S, coupeLigne, finDeLigne,
    statutHttp, V2, NOMS_CAR, caracteristiques, scoresCaracteristiques, voixSegments,
    parserParoles, voixParoles, chargerParoles, reglerFile, reinitialiser, etatParoles, voixBord, voixMesure, fenetre,
    indexMesure, scoresV2 };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else (racine.DJCore ??= {}).voix = api;
})(globalThis);
