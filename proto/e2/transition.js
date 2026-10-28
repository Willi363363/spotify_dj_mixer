// Côté Spotify pour les tests du moteur E2 (run.sh, boutons « Lancer ») : rejoue A depuis PREROLL s avant sa sortie,
// saute vers B à son entrée, et rend l'ordre v2 (ADR 0001) que run.sh envoie au moteur. Le choix de la transition et
// des points vient de l'extension (window.DJ.planTransition, modules DJCore), source unique avec le mode automatique.
// Réglages : __A, __B (uri), __TRANSITION (« auto » ou C1…C8, R1, R2), __LAST (transition précédente, pour la
// variété), __PREROLL (s), __GRAINE (hasard reproductible), __DRY (calcule l'ordre sans rien jouer).
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  if (window.DJ?.version !== 2 || !window.DJ.planTransition || !window.DJ.ordre) {
    return { erreur: 'extension dj-auto v2 absente : lancer spicetify/installer.sh' };
  }
  const P = Spicetify.Player;
  const PREROLL = globalThis.__PREROLL ?? 32;
  const A = globalThis.__A, B = globalThis.__B;
  const T = globalThis.__TRANSITION ?? 'auto';
  const last = globalThis.__LAST ?? '';
  const choix = await DJ.planTransition(A, B, {
    force: T === 'auto' ? null : T, minExit_s: PREROLL + 20, contexte: null,
    graine: globalThis.__GRAINE ?? null, historique: last ? [{ transition: last, entree: 'E0' }] : [],
  });
  if (choix.erreur) return choix;
  if (globalThis.__DRY) return DJ.ordre(choix, { t_wall: Date.now(), id: `essai-${Date.now()}` });

  const sortieMs = choix.sortie_s * 1000;
  await P.playUri(A);
  for (let k = 0; k < 100 && P.data?.item?.uri !== A; k++) await sleep(50);
  await sleep(800);
  P.seek(Math.max(0, sortieMs - PREROLL * 1000));
  await sleep(1000);
  const t_wall = await DJ.switchAt(sortieMs, { uri: B }, choix.entree_s, null);
  if (t_wall === null) return { erreur: 'saut annulé (morceau changé ou pause)' };
  return DJ.ordre(choix, { t_wall, gapless: false, id: `essai-${t_wall}` });
})()
