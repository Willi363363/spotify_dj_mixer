// Catalogue des transitions v2, côté affichage (ADR 0005) : nom, famille, couleur, description courte et étapes de
// frise de chaque identifiant de l'ADR 0001, plus les étiquettes de note (/rating) et deux aides d'affichage pures.
// Chargé comme extension Spicetify (globalThis.DJCore.catalogue), servi par e2.py sur GET /dj-catalogue.js pour
// ecran.html, et lu par Node (require) pour le test de cohérence des identifiants. Aucun appel à Spicetify ici.
//
// - `bars` : recouvrement T permis, en mesures (mêmes valeurs que transitions/catalogue.py et dj-choix.js).
//   `null` pour R3 (moteur éteint) et le secours, qui ne se demandent pas dans un ordre.
// - `phases` : [libellé, début, fin], en fractions de la durée du segment rendu (`dur_s` dans /state).
// - `b_debut` : fraction du segment où B commence à s'entendre (0 = superposition, 1 = B entre au bout).
(function (racine) {
  const CATALOGUE = {
    C1: {
      nom: 'Coupe sur phrase', famille: 'sec', couleur: '#4f8cff', bars: [0], b_debut: 1,
      description: 'A s\'arrête net au début d\'une phrase, B entre plein sur le 1.',
      phases: [['Coupe au 1', 0, 1]],
    },
    C2: {
      nom: 'Écho', famille: 'sec', couleur: '#7aa7ff', bars: [0], b_debut: 0.3,
      description: 'Le dernier temps de A part en écho, la queue s\'éteint sous B.',
      phases: [['Dernier temps de A en écho', 0, 0.3], ['B entre, l\'écho s\'éteint', 0.3, 1]],
    },
    C3: {
      nom: 'Frein', famille: 'effet', couleur: '#ff5e7a', bars: [0], b_debut: 1,
      description: 'A ralentit jusqu\'à l\'arrêt sur son dernier temps, B repart sec.',
      phases: [['A freine jusqu\'à l\'arrêt', 0, 1]],
    },
    C4: {
      nom: 'Montée en boucle', famille: 'effet', couleur: '#ffb020', bars: [0], b_debut: 1,
      description: 'La dernière mesure de A tourne en boucle de plus en plus serrée, B arrive sur son refrain.',
      phases: [['Boucle de 2 temps', 0, 0.5], ['La boucle accélère', 0.5, 1]],
    },
    C5: {
      nom: 'Fondu calé', famille: 'superpose', couleur: '#1ed760', bars: [2], b_debut: 0,
      description: 'Fondu de 2 mesures calé sur la grille, échange des basses au 1 de la 2e.',
      phases: [['B monte, basses de A', 0, 0.5], ['Basses de B, A s\'éteint', 0.5, 1]],
    },
    C6: {
      nom: 'Mix 3 bandes', famille: 'superpose', couleur: '#4fd1c5', bars: [4], b_debut: 0,
      description: 'Radio edit sur 4 mesures : B entre par l\'intro, médiums puis basses passent de A à B.',
      phases: [['B entre en douceur', 0, 0.25], ['Médiums de A baissent', 0.25, 0.5],
        ['Échange des basses', 0.5, 0.75], ['A s\'éteint', 0.75, 1]],
    },
    C7: {
      nom: 'Échange de basses', famille: 'superpose', couleur: '#38a169', bars: [8, 16], b_debut: 0,
      description: 'Long blend de 8 ou 16 mesures : B monte sous A, les basses s\'échangent au milieu.',
      phases: [['B monte sous A', 0, 0.5], ['Échange des basses, A s\'éteint', 0.5, 1]],
    },
    C8: {
      nom: 'Montée filtrée', famille: 'superpose', couleur: '#c38bff', bars: [4, 8], b_debut: 0,
      description: 'B s\'ouvre par un filtre pendant que A s\'amincit, tout bascule sur la section forte de B.',
      phases: [['Le filtre de B s\'ouvre, A s\'amincit', 0, 0.85], ['B plein au 1', 0.85, 1]],
    },
    R1: {
      nom: 'Fondu court', famille: 'repli', couleur: '#a0aec0', bars: [1], b_debut: 0,
      description: 'Repli : fondu d\'une mesure, basses de B coupées jusqu\'au 1 final.',
      phases: [['Fondu court', 0, 1]],
    },
    R2: {
      nom: 'Bord à bord', famille: 'repli', couleur: '#718096', bars: [0], b_debut: 1,
      description: 'Repli : A joue jusqu\'à sa fin, silences retirés, B enchaîne.',
      phases: [['Bord à bord', 0, 1]],
    },
    R3: {
      nom: 'Spotify seul', famille: 'repli', couleur: '#4a5568', bars: null, b_debut: 1,
      description: 'Moteur éteint : aucune intervention, Spotify enchaîne seul.',
      phases: [],
    },
    secours: {
      nom: 'Secours', famille: 'repli', couleur: '#e53e3e', bars: null, b_debut: 1,
      description: 'Transition prête trop tard ou toute l\'échelle refusée : raccord de secours (compté comme un échec).',
      phases: [['Secours', 0, 1]],
    },
  };

  // Identifiants qu'un ordre, /run ou DJ.forcer peuvent demander (ADR 0001).
  const JOUABLES = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'R1', 'R2'];

  const FAMILLES = { sec: 'sèche', effet: 'effet', superpose: 'superposée', repli: 'repli' };

  // Étiquettes de POST /rating (ADR 0001), dans l'ordre d'affichage.
  const ETIQUETTES = [
    ['rythme_decroche', 'Rythme qui décroche'],
    ['basses_doublees', 'Basses doublées'],
    ['voix_superposees', 'Voix superposées'],
    ['fin_coupee', 'Fin coupée'],
    ['mauvais_endroit', 'Entrée au mauvais endroit'],
    ['trop_long', 'Trop long'],
    ['trop_court', 'Trop court'],
    ['saut_volume', 'Saut de volume'],
    ['clic_trou', 'Clic ou trou'],
    ['effet_de_trop', 'Effet de trop'],
  ];

  // Fiche d'un identifiant, ou fiche neutre s'il est inconnu (jamais d'exception à l'affichage).
  function info(id) {
    if (id && CATALOGUE[id]) return { id, ...CATALOGUE[id] };
    return { id: id ?? null, nom: id ?? 'Transition', famille: null, couleur: '#888888', bars: null, b_debut: 1,
      description: '', phases: [] };
  }

  // Écoute à l'aveugle : retire d'un texte libre tout ce qui nomme une transition (identifiants et noms).
  const NOMS = Object.values(CATALOGUE).map((f) => f.nom).sort((a, b) => b.length - a.length);
  const echap = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const MOTIF = new RegExp(`\\b(?:C[1-8]|R[1-3])\\b|${NOMS.map(echap).join('|')}`, 'gi');
  function masquer(texte) {
    return String(texte ?? '').replace(MOTIF, '?');
  }

  // Rapport d'une transition (derniere_transition / transitions_recentes de /state, ADR 0001) en lignes lisibles,
  // affichées une fois la transition notée (ou hors écoute à l'aveugle).
  const nb = (v, d = 1) => (typeof v === 'number' && isFinite(v)
    ? v.toLocaleString('fr-FR', { maximumFractionDigits: d }) : null);
  const signe = (v) => (typeof v === 'number' ? `${v > 0 ? '+' : v < 0 ? '−' : ''}${nb(Math.abs(v))}` : null);
  function nomCourt(id) {
    if (!id) return 'aucune';
    if (!CATALOGUE[id]) return String(id);
    return /^[CR]\d$/.test(id) ? `${id} · ${CATALOGUE[id].nom}` : CATALOGUE[id].nom;
  }
  function lignesRapport(r) {
    if (!r) return [];
    const out = [];
    const jouee = r.transition_jouee, demandee = r.transition_demandee;
    if (r.issue === 'abandon') out.push(`Abandon : aucune transition jouée (demandée : ${nomCourt(demandee)})`);
    else if (demandee && demandee !== jouee) out.push(`Demandée ${nomCourt(demandee)}, jouée ${nomCourt(jouee)}`);
    else out.push(`Jouée : ${nomCourt(jouee)}`);
    for (const p of r.replis ?? []) out.push(`Repli ${p.de} → ${p.vers} (${p.ou === 'rendu' ? 'au rendu' : 'au plan'}) : ${p.raison ?? ''}`);
    const m = r.mesures ?? {};
    const mes = [
      m.calage_ms != null && `calage ${nb(m.calage_ms)} ms`,
      m.nettete != null && `netteté ${nb(m.nettete)}`,
      m.basses_ms != null && `basses doublées ${nb(m.basses_ms, 0)} ms`,
      m.echange_ms != null && `échange à ${nb(m.echange_ms, 0)} ms du 1`,
      m.voix_mesures != null && `voix superposées ${nb(m.voix_mesures, 0)} mes.`,
      Array.isArray(m.sonie_db) && `sonie ${signe(m.sonie_db[0])} / ${signe(m.sonie_db[1])} dB`,
      m.crete_dbfs != null && `crête ${signe(m.crete_dbfs)} dBFS`,
    ].filter(Boolean);
    if (mes.length) out.push(mes.join(' · '));
    const reste = [
      r.b?.entree && `entrée ${r.b.entree}`,
      r.ralenti != null && `ralenti ×${nb(r.ralenti, 2)}`,
      r.marge_s != null && `prête ${nb(r.marge_s)} s avant`,
      r.avance_avant_s != null && r.avance_apres_s != null && `avance ${nb(r.avance_avant_s, 0)} → ${nb(r.avance_apres_s, 0)} s`,
    ].filter(Boolean);
    if (reste.length) out.push(reste.join(' · '));
    if (r.raison) out.push(`Pourquoi : ${r.raison}`);
    return out;
  }

  const api = { CATALOGUE, JOUABLES, FAMILLES, ETIQUETTES, info, masquer, nomCourt, lignesRapport };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else (racine.DJCore ??= {}).catalogue = api;
})(globalThis);
