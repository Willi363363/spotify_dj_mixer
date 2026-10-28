// Voix par mesure au moment du plan (ADR 0002) : un score dans [0 ; 1] par mesure et une source.
// - V2 (défaut) : heuristique sur les segments de l'analyse Spotify, normalisée par morceau (z-scores).
// - V1 (option) : paroles synchronisées, seulement si LocalStorage 'dj-mixer:paroles' === '1'.
// - Sans segments : toutes les mesures à 1 (pire cas : vocal), source 'aucune'.
// Seuils communs : vocal ≥ SEUIL_VOCAL, sans voix < SEUIL_SANS_VOIX. Fonctions pures sauf chargerParoles.
// Chargé comme extension Spicetify (globalThis.DJCore.voix) et par Node (require) pour les tests.
(function (racine) {
  const SEUIL_VOCAL = 0.5;
  const SEUIL_SANS_VOIX = 0.3;
  const DRAPEAU = 'dj-mixer:paroles';
  const DELAI_PAROLES_MS = 3000;
  const LIGNE_MAX_S = 8;
  // V2 : poids des z-scores par mesure (non calibrés, tâche 2-direct). Hypothèse : une voix (rap ou chant) ajoute
  // des attaques serrées (syllabes), de la brillance (timbre[1]), une chroma dominée par une note et du niveau.
  const V2 = { brillance: 1.0, densite: 0.8, pic: 0.6, sonie: 0.4, biais: 0.4, silence_db: -45 };

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

  // Scores V2 de toutes les mesures du morceau (cache par analyse), ou null sans segments
  const cacheV2 = new WeakMap();
  function scoresV2(analyse) {
    if (!analyse || typeof analyse !== 'object') return null;
    if (cacheV2.has(analyse)) return cacheV2.get(analyse);
    const bars = analyse.bars ?? [], segs = analyse.segments ?? [];
    if (!bars.length || !segs.length) { cacheV2.set(analyse, null); return null; }
    const f = [];
    let j = 0;
    for (const b of bars) {
      const fin = b.start + b.duration;
      while (j < segs.length && segs[j].start < b.start - 1e-6) j++;
      let n = 0, dur = 0, brill = 0, pic = 0, sonie = -Infinity;
      for (let i = j; i < segs.length && segs[i].start < fin - 1e-6; i++) {
        const s = segs[i], d = Math.max(s.duration ?? 0, 1e-3);
        n++; dur += d;
        brill += (s.timbre?.[1] ?? 0) * d;
        const p = s.pitches ?? [];
        pic += (p.length ? 1 - p.reduce((x, y) => x + y, 0) / p.length : 0) * d;
        sonie = Math.max(sonie, s.loudness_max ?? -60);
      }
      f.push(n ? { brill: brill / dur, pic: pic / dur, dens: n / 4, sonie, silence: sonie < V2.silence_db }
        : { brill: 0, pic: 0, dens: 0, sonie: -60, silence: true });
    }
    const actives = f.filter((x) => !x.silence);
    const stat = (cle, plancher) => {
      if (!actives.length) return [0, 1];
      const m = actives.reduce((x, y) => x + y[cle], 0) / actives.length;
      const v = actives.reduce((x, y) => x + (y[cle] - m) ** 2, 0) / actives.length;
      return [m, Math.max(Math.sqrt(v), plancher)];
    };
    const [mb, sb] = stat('brill', 3), [md, sd] = stat('dens', 0.1), [mp, sp] = stat('pic', 0.03), [ml, sl] = stat('sonie', 1);
    const out = f.map((x) => (x.silence ? 0 : +sigmoide(V2.brillance * (x.brill - mb) / sb + V2.densite * (x.dens - md) / sd
      + V2.pic * (x.pic - mp) / sp + V2.sonie * (x.sonie - ml) / sl + V2.biais).toFixed(3)));
    cacheV2.set(analyse, out);
    return out;
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
      lignes.push({ debut_s: debut, vide: !mots || /^[♪\s]+$/u.test(mots) });
    }
    lignes.sort((a, b) => a.debut_s - b.debut_s);
    lignes.forEach((x, i) => {
      const suiv = lignes[i + 1]?.debut_s ?? Infinity;
      x.fin_s = +Math.min(suiv, x.debut_s + LIGNE_MAX_S).toFixed(3);
    });
    return lignes;
  }

  // Part de chaque mesure couverte par une ligne non vide
  function voixParoles(lignes, mesures) {
    const pleines = (lignes ?? []).filter((x) => !x.vide);
    return mesures.map((m) => {
      const a = m.start, b = m.start + m.duration;
      let c = 0;
      for (const x of pleines) c += Math.max(0, Math.min(b, x.fin_s) - Math.max(a, x.debut_s));
      return +borne(c / Math.max(m.duration, 1e-6)).toFixed(3);
    });
  }

  // Seul appel réseau : paroles d'un morceau (cache), derrière le drapeau. Tout échec → null, sans erreur visible.
  const cacheParoles = new Map();
  async function chargerParoles(uri) {
    const S = racine.Spicetify;
    try {
      if (S?.LocalStorage?.get(DRAPEAU) !== '1' || !S?.CosmosAsync?.get) return null;
      const id = /^spotify:track:([A-Za-z0-9]{22})$/.exec(uri ?? '')?.[1];
      if (!id) return null;
      if (cacheParoles.has(id)) return cacheParoles.get(id);
      const url = `https://spclient.wg.spotify.com/color-lyrics/v2/track/${id}?format=json&market=from_token`;
      let minuteur;
      const delai = new Promise((r) => { minuteur = setTimeout(() => r(null), DELAI_PAROLES_MS); });
      const json = await Promise.race([S.CosmosAsync.get(url).catch(() => null), delai]);
      clearTimeout(minuteur);
      const lignes = parserParoles(json);
      cacheParoles.set(id, lignes);
      return lignes;
    } catch { return null; }
  }

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

  const api = { SEUIL_VOCAL, SEUIL_SANS_VOIX, DRAPEAU, V2, voixSegments, parserParoles, voixParoles, chargerParoles,
    voixBord, voixMesure, fenetre, indexMesure, scoresV2 };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else (racine.DJCore ??= {}).voix = api;
})(globalThis);
