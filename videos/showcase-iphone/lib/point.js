/* lib/point.js · « Le point sur le i » v2 · état du point racine à tout instant, fonction pure du temps FILM
 *
 * Chargé une fois par la racine, après donnees/donnees.js et GSAP. La racine dessine #point avec
 * POINT.proprietes(t) ; les scènes qui doivent s'aligner sur lui (le déroulé du bloc en s5, la secousse
 * du téléphone en s6, les masques du wordmark en s7) appellent LA MÊME fonction au lieu de recopier des
 * nombres. Aucune scène ne dessine ni n'anime le point.
 *
 *   POINT.etat(t) → { x, y,            centre DESSINÉ en px film (secousses comprises)
 *                     x_sans, y_sans,  centre sans secousse (trajectoire pure : pour les masques et les bords révélés)
 *                     dx, dy,          secousses appliquées (x = x_sans + dx, y = y_sans + dy)
 *                     d,               diamètre en px (sans écrasement ni étirement)
 *                     sx, sy, rot,     déformation : écrasement (table, prioritaire) ou étirement de vitesse ;
 *                                      rot en degrés (0 hors étirement) ; diamètres visibles = d·sx × d·sy
 *                     vx, vy, v,       vitesse sans secousse, en px PAR IMAGE (différence centrée sur ±1/60 s)
 *                     couleur,         "#rrggbb"
 *                     image }          round(t × 30)
 *   POINT.position(t)       → [x_sans, y_sans]
 *   POINT.secousse(nom, t)  → dx en px de la piste DONNEES.secousses[nom] ("s1" ou "s6") à l'image de t
 *   POINT.secousseY(nom, t) → dy en px (0 si la piste n'a pas de motif_y)
 *   POINT.suiveur(t)        → [x, y] du premier trajet planifié (s2-s3), ou null hors de sa fenêtre
 *   POINT.trajet(t)         → [x, y] du trajet planifié qui couvre t (s2-s3 ou s6), ou null
 *   POINT.ease(nom)         → fonction d'ease : GSAP (gsap.parseEase) ou « bezier(x1,y1,x2,y2) » (Newton, 8 itérations)
 *   POINT.proprietes(t)     → { xPercent, yPercent, x, y, rotation, scaleX, scaleY, backgroundColor } pour gsap.set
 *   POINT.diametre_disque   → D0 = 44 (diamètre CSS de #point = diamètre mesuré de #mot-pt)
 *
 * Données (DONNEES.point) : position [{t, x, y, ease, arc:{dx,dy}}], taille [{t, d, ease}], couleur [{t, c, ease}],
 * trajets [{nom, t0, t1, image0, x[], y[]}] (suiveur = alias du premier), pistes {trajets, secousses:[{piste,t0,t1}]},
 * ecrasements {image: {sx, sy}}, etirement {seuil, pente, max, sans}. Entre deux clés : de la clé i à la clé i+1 avec
 * l'ease de la clé i+1 ; arc ajouté × 4p(1−p) (p = progression après ease) ; avant la 1re / après la dernière : tenue.
 * Pendant un trajet, la position est celle du trajet (échantillons par image, interpolés linéairement).
 */
(function () {
  if (window.POINT) return;
  const D = window.DONNEES;
  if (!D || !D.point) throw new Error("lib/point.js : window.DONNEES.point absent");
  const P = D.point;
  const FPS = D.fps || 30;
  const EPS = 1e-5;   // les temps des clés sont arrondis à 1 µs dans les données : 620/30 = 20,666667

  // ── eases ──
  function bezier(x1, y1, x2, y2) {
    const bx = function (s) { const r = 1 - s; return 3 * r * r * s * x1 + 3 * r * s * s * x2 + s * s * s; };
    const by = function (s) { const r = 1 - s; return 3 * r * r * s * y1 + 3 * r * s * s * y2 + s * s * s; };
    const dbx = function (s) { const r = 1 - s; return 3 * r * r * x1 + 6 * r * s * (x2 - x1) + 3 * s * s * (1 - x2); };
    return function (u) {
      if (u <= 0) return 0;
      if (u >= 1) return 1;
      let s = u;
      for (let k = 0; k < 8; k++) {              // Newton sur x(s) = u
        const e = bx(s) - u, dd = dbx(s);
        if (Math.abs(dd) < 1e-9) break;
        s = Math.min(1, Math.max(0, s - e / dd));
      }
      return by(s);
    };
  }
  const eases = {};
  function ease(nom) {
    if (!nom || nom === "none" || nom === "linear") return function (p) { return p; };
    if (!eases[nom]) {
      const m = /^bezier\(\s*([^)]*)\)$/.exec(nom);
      if (m) {
        const a = m[1].split(",").map(Number);
        if (a.length !== 4 || a.some(isNaN)) throw new Error("lib/point.js : ease " + nom + " illisible");
        eases[nom] = bezier(a[0], a[1], a[2], a[3]);
      } else {
        eases[nom] = gsap.parseEase(nom);
        if (!eases[nom]) throw new Error("lib/point.js : ease inconnue " + nom);
      }
    }
    return eases[nom];
  }

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

  // ── trajets planifiés (finition du 27/09 : s2-s3 et s6), échantillonnés par image dans construire.py ──
  // Chaque trajet {nom, image0, t0, t1, x[], y[]} donne la position à chaque image de sa fenêtre (interpolée entre deux
  // images). Sans DONNEES.point.trajets (v2 d'avant la finition), l'ancien suiveur unique fait office de trajet.
  const TRAJETS = P.trajets || (P.suiveur && P.pistes && P.pistes.suiveur ?
    [{ nom: "suiveur", image0: P.suiveur.image0, t0: P.pistes.suiveur.t0, t1: P.pistes.suiveur.t1, x: P.suiveur.x, y: P.suiveur.y }] : []);
  function trajet(t) {
    for (let n = 0; n < TRAJETS.length; n++) {
      const S = TRAJETS[n];
      if (t < S.t0 - EPS || t > S.t1 + EPS) continue;
      const f = t * FPS - S.image0;
      const i = Math.max(0, Math.min(S.x.length - 1, Math.floor(f)));
      const j = Math.min(S.x.length - 1, i + 1);
      const k = Math.max(0, Math.min(1, f - i));
      return [S.x[i] + (S.x[j] - S.x[i]) * k, S.y[i] + (S.y[j] - S.y[i]) * k];
    }
    return null;
  }
  function suiveur(t) {                    // compatibilité : le premier trajet (s2-s3)
    const S = TRAJETS[0];
    return S && t >= S.t0 - EPS && t <= S.t1 + EPS ? trajet(t) : null;
  }

  function position(t) {
    const s = trajet(t);
    if (s) return s;
    return piste(P.position, t, function (c) { return [c.x, c.y]; }, function (a, b, p) {
      let x = a.x + (b.x - a.x) * p, y = a.y + (b.y - a.y) * p;
      if (b.arc) { const w = 4 * p * (1 - p); x += (b.arc.dx || 0) * w; y += (b.arc.dy || 0) * w; }
      return [x, y];
    });
  }

  // ── secousses : décalage = amplitude × enveloppe(image) × motif[phase] ──
  function motifA(S, n, k, motif) {
    const i = S.phase_par_image_absolue ? n : k;
    return motif[((i % motif.length) + motif.length) % motif.length];
  }
  function secousseAxe(nom, t, axe) {
    const S = D.secousses && D.secousses[nom];
    if (!S) return 0;
    const n = Math.round(t * FPS);
    const k = n - S.image0;
    if (k < 0 || k >= S.enveloppe.length) return 0;
    const motif = axe === "y" ? S.motif_y : (S.motif_x || S.motif);
    const amp = axe === "y" ? S.amplitude_y : (S.amplitude_x != null ? S.amplitude_x : S.amplitude_px);
    if (!motif || !amp) return 0;
    return amp * S.enveloppe[k] * motifA(S, n, k, motif);
  }
  function secousse(nom, t) { return secousseAxe(nom, t, "x"); }
  function secousseY(nom, t) { return secousseAxe(nom, t, "y"); }

  const ECR = P.ecrasements || {};
  const ETI = P.etirement || { seuil: 30, pente: 90, max: 0.25 };   // repli seulement : DONNEES.point.etirement fait foi
  const SANS = ETI.sans || [];            // fenêtres [t0, t1] sans étirement (l'écriture de « Vokıo » : le point reste rond)
  function sansEtirement(t) { return SANS.some(function (w) { return t >= w[0] - EPS && t <= w[1] + EPS; }); }
  const DEMI = 1 / (2 * FPS);

  function etat(t) {
    const pos = position(t);
    let dx = 0, dy = 0;
    (P.pistes && P.pistes.secousses || []).forEach(function (s) {
      if (t >= s.t0 - EPS && t <= s.t1 + EPS) { dx += secousse(s.piste, t); dy += secousseY(s.piste, t); }
    });
    // vitesse en px par image : déplacement sur une durée d'image, centré sur t, trajectoire sans secousse
    const a = position(t - DEMI), b = position(t + DEMI);
    const vx = b[0] - a[0], vy = b[1] - a[1], v = Math.hypot(vx, vy);
    const image = Math.round(t * FPS);
    let sx = 1, sy = 1, rot = 0;
    const e = ECR[String(image)];
    if (e) { sx = e.sx; sy = e.sy; }
    else if (v > ETI.seuil && !sansEtirement(t)) {
      const long = 1 + Math.min(ETI.max, (v - ETI.seuil) / ETI.pente);
      sx = long; sy = 1 / Math.sqrt(long); rot = Math.atan2(vy, vx) * 180 / Math.PI;
    }
    const d = piste(P.taille, t, function (c) { return c.d; }, function (a2, b2, p) { return a2.d + (b2.d - a2.d) * p; });
    const couleur = piste(P.couleur, t, function (c) { return c.c; }, function (a2, b2, p) {
      const A = hex(a2.c), B = hex(b2.c);
      return versHex([0, 1, 2].map(function (k) { return A[k] + (B[k] - A[k]) * p; }));
    });
    return { x: pos[0] + dx, y: pos[1] + dy, x_sans: pos[0], y_sans: pos[1], dx: dx, dy: dy, d: d,
             sx: sx, sy: sy, rot: rot, vx: vx, vy: vy, v: v, couleur: couleur, image: image };
  }

  const D0 = P.diametre_disque;
  function proprietes(t) {
    const s = etat(t);
    return { xPercent: -50, yPercent: -50, x: s.x, y: s.y, rotation: s.rot,
             scaleX: s.d / D0 * s.sx, scaleY: s.d / D0 * s.sy, backgroundColor: s.couleur };
  }

  window.POINT = { etat: etat, position: position, secousse: secousse, secousseY: secousseY, suiveur: suiveur, trajet: trajet,
                   ease: ease, proprietes: proprietes, diametre_disque: D0 };
})();
