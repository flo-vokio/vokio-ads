/* lib/point.js · « Le point sur le i » · état du point racine à tout instant, fonction pure du temps FILM
 *
 * Chargé une fois par la racine, après donnees/donnees.js et GSAP. La racine anime #point avec
 * POINT.etat(t) ; les scènes qui doivent s'aligner sur lui (la ligne de s2, le déroulé du bloc en s5,
 * la secousse de la silhouette en s6) appellent LA MÊME fonction au lieu de recopier des nombres.
 *
 *   POINT.etat(t)   → { x, y, d, couleur, dx, image }   centre en px film (dx = tremblement déjà inclus
 *                     dans x ; x_sans = x − dx), d = diamètre visible en px, couleur "#rrggbb"
 *   POINT.secousse(nom, t) → décalage x en px de la piste DONNEES.secousses[nom] ("s1" ou "s6") à l'image
 *   POINT.voix(t)   → x de la progression voisée de A1 (s2), ou null hors fenêtre
 *   POINT.ease(nom) → la fonction d'ease GSAP (gsap.parseEase), la même que celle de la racine
 *
 * Données : DONNEES.point = { diametre_disque, position: [{t,x,y,ease,arc}], taille: [{t,d,ease}],
 * couleur: [{t,c,ease}], pistes: {voix:{t0,t1}, secousses:[{piste,t0,t1}]} }. Entre deux clés, la
 * valeur va de la clé i à la clé i+1 avec l'ease de la clé i+1 ; avant la 1re / après la dernière : tenue.
 * arc = { dx } : écart en x ajouté au milieu du trajet, dx·4p(1−p) (p = progression après ease).
 */
(function () {
  if (window.POINT) return;
  const D = window.DONNEES;
  if (!D || !D.point) throw new Error("lib/point.js : window.DONNEES.point absent");
  const P = D.point;
  const FPS = D.fps || 30;
  const eases = {};
  function ease(nom) {
    if (!nom || nom === "none" || nom === "linear") return function (p) { return p; };
    if (!eases[nom]) eases[nom] = gsap.parseEase(nom);
    return eases[nom];
  }

  const EPS = 1e-5;   // les temps des clés sont arrondis à 1 µs dans le JSON : 620/30 = 20,666667
  function piste(cles, t, lire, melanger) {
    if (t <= cles[0].t + EPS) return lire(cles[0]);
    const n = cles.length;
    if (t >= cles[n - 1].t - EPS) return lire(cles[n - 1]);
    let i = 0;
    while (i < n - 1 && !(t >= cles[i].t - EPS && t < cles[i + 1].t - EPS)) i++;
    const a = cles[i], b = cles[i + 1];
    const u = (t - a.t) / (b.t - a.t);
    const p = ease(b.ease)(u);
    return melanger(a, b, p);
  }

  function hex(c) { return [1, 3, 5].map(function (k) { return parseInt(c.slice(k, k + 2), 16); }); }
  function versHex(r) {
    return "#" + r.map(function (v) { return Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, "0"); }).join("");
  }

  function voix(t) {
    const V = D.voixX;
    if (!V || t < V.t0 - EPS || t > V.t1 + EPS) return null;
    const f = t * FPS - V.image0;
    const i = Math.max(0, Math.min(V.x.length - 1, Math.floor(f)));
    const j = Math.min(V.x.length - 1, i + 1);
    const k = Math.max(0, Math.min(1, f - i));
    return V.x[i] + (V.x[j] - V.x[i]) * k;
  }

  function secousse(nom, t) {
    const S = D.secousses[nom];
    if (!S) return 0;
    const n = Math.round(t * FPS);
    const k = n - S.image0;
    if (k < 0 || k >= S.enveloppe.length) return 0;
    const motif = S.motif[((S.phase_par_image_absolue ? n : k) % S.motif.length + S.motif.length) % S.motif.length];
    return S.amplitude_px * S.enveloppe[k] * motif;
  }

  function etat(t) {
    const pos = piste(P.position, t, function (c) { return [c.x, c.y]; }, function (a, b, p) {
      let x = a.x + (b.x - a.x) * p, y = a.y + (b.y - a.y) * p;
      if (b.arc) { x += (b.arc.dx || 0) * 4 * p * (1 - p); y += (b.arc.dy || 0) * 4 * p * (1 - p); }
      return [x, y];
    });
    const vx = (P.pistes && P.pistes.voix && t >= P.pistes.voix.t0 - EPS && t <= P.pistes.voix.t1 + EPS) ? voix(t) : null;
    if (vx != null) pos[0] = vx;
    let dx = 0;
    (P.pistes && P.pistes.secousses || []).forEach(function (s) {
      if (t >= s.t0 - EPS && t <= s.t1 + EPS) dx += secousse(s.piste, t);
    });
    const d = piste(P.taille, t, function (c) { return c.d; }, function (a, b, p) { return a.d + (b.d - a.d) * p; });
    const couleur = piste(P.couleur, t, function (c) { return c.c; }, function (a, b, p) {
      const A = hex(a.c), B = hex(b.c);
      return versHex([0, 1, 2].map(function (k) { return A[k] + (B[k] - A[k]) * p; }));
    });
    return { x: pos[0] + dx, x_sans: pos[0], y: pos[1], d: d, couleur: couleur, dx: dx, image: Math.round(t * FPS) };
  }

  window.POINT = { etat: etat, voix: voix, secousse: secousse, ease: ease, diametre_disque: P.diametre_disque };
})();
