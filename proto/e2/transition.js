// Côté Spotify pour les tests de la maquette E2 (run.sh, boutons « Lancer ») : rejoue A depuis PREROLL s
// avant sa sortie, puis lance B à son point de départ. Le choix de la transition et des points vient de
// l'extension dj-auto (window.DJ.planTransition), source unique partagée avec le mode automatique.
// Réglages : __A, __B (uri), __MODE (préréglage ou « auto »), __LAST (préréglage précédent), __PREROLL (s),
// __DRY (calcule sans rien jouer).
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  if (!window.DJ?.planTransition) return { erreur: 'extension dj-auto absente : lancer spicetify/installer.sh' };
  const P = Spicetify.Player;
  const PREROLL = globalThis.__PREROLL ?? 32;
  const A = globalThis.__A, B = globalThis.__B;
  const choix = await DJ.planTransition(A, B, { mode: globalThis.__MODE ?? 'auto', last: globalThis.__LAST ?? '', minExit: PREROLL + 20 });
  if (choix.erreur || globalThis.__DRY) return choix;

  const aExit = choix.sortieA * 1000;
  await P.playUri(A);
  for (let k = 0; k < 100 && P.data?.item?.uri !== A; k++) await sleep(50);
  await sleep(800);
  P.seek(aExit - PREROLL * 1000);
  await sleep(1000);
  const t_wall = await DJ.switchAt(aExit, { uri: B }, choix.bStart, null);
  if (t_wall === null) return { erreur: 'saut annulé (morceau changé ou pause)' };
  return { t_wall, ...choix };
})()
