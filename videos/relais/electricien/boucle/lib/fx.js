/* lib/fx.js · effets réutilisables des situations animées (cartes « Le relais », puis animations par métier).
 *
 * Tout est une FONCTION PURE DU TEMPS (seek image par image, rendu déterministe) et PÉRIODIQUE si l'on choisit des périodes
 * qui divisent la durée de la boucle (10 s : 0,3125 · 0,4 · 0,5 · 0,625 · 1 · 1,25 · 2 · 2,5 · 5). Au trait, dans la palette
 * Plein Jour : aucun flou, aucun dégradé.
 *
 *   FX.flamme(parent, reglages)   → maj(t, aviver)   une langue de feu dont le TRACÉ se déforme (ondes déphasées qui montent
 *                                  le long de la langue, pointe qui se tord et s'étire), cœur clair, et une flammèche qui se
 *                                  détache de la pointe, monte et s'éteint. aviver ∈ [0, 1] : plus haute (un souffle d'air).
 *   FX.traits(parent, reglages)   → maj(v, x, y, angle)   2-3 traits de vitesse parallèles derrière un mouvement : v ∈ [0, 1]
 *                                  sur leur courte vie (ils poussent depuis l'arrière puis se rétractent vers l'avant) ;
 *                                  v hors de [0, 1] : invisibles. angle : direction du MOUVEMENT (radians, repère SVG).
 *   FX.etirer(vx, vy, f)          → transformation SVG « rotate scale rotate » : étire de f le long de la vitesse (smear
 *                                  frame), comprime d'autant en travers (volume conservé).
 *   FX.fenetre(t, t0, duree)      → v ∈ [0, 1] pendant [t0, t0 + duree], sinon −1 (pour piloter traits et smears en images).
 *   FX.cles(u, clés), FX.EASE      → clés interpolées avec easing nommé (sio, p2o, p3o, p4o, p2i, p3i, lin), sans rebond
 *   FX.particules(parent, r)      → maj(v, x, y, angle) : gerbe déterministe (goutte · poussiere · etincelle), gravité
 *   FX.eclat(parent, r)           → maj(v, x, y, t) : étincelle électrique qui change de forme à chaque image
 *   FX.chute(tc, r), FX.pendule    → mèche qui volette en tombant ; pendule amorti (ficelle, trousseau)
 *
 * Réglages par défaut ci-dessous (FX.DEFAUTS) ; chaque situation passe les siens (voir situations/poele.js).
 */
(function () {
  if (window.FX) return;
  const NS = "http://www.w3.org/2000/svg", PI = Math.PI, sin = Math.sin, cos = Math.cos;
  const onde = (t, p, ph) => sin(2 * PI * (t / p + ph));
  const f2 = (v) => v.toFixed(2);
  const el = (parent, tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent.appendChild(e); return e; };

  const DEFAUTS = {
    flamme: {
      x: 0, base: 0, h: 80, w: 25, couleur: "#EFA424", coeur: "#F8D69B", coeur_echelle: 0.52,
      phase: 0,
      // ondes (périodes en s, diviseurs de 10) : hauteur qui respire, pointe qui se tord, ondulation qui monte le long des flancs
      hauteur: [[0.5, 0.10], [0.3125, 0.05]],        // [période, amplitude relative]
      torsion: [[0.625, 0.20], [0.4, 0.08]],         // déplacement latéral de la pointe, en fraction de h
      ondulation: { periode: 0.5, amplitude: 0.28, longueur: 0.9 },   // flancs : amplitude en fraction de w, longueur d'onde en h
      flammeche: { periode: 2.5, decalage: 0, duree: 0.5, montee: 0.9, taille: 0.22, retrait: 0.10 }  // null : aucune
    },
    traits: { n: 3, longueurs: [70, 92, 56], ecart: 20, recul: 26, epaisseur: 6, couleur: "#262019" }
  };
  const fusion = (a, b) => { const o = Object.assign({}, a); for (const k in (b || {})) o[k] = (b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a[k]) ? fusion(a[k], b[k]) : b[k]; return o; };

  // Tracé d'une langue : base (−w, 0) → (w, 0), pointe (px, −H). Flancs en deux cubiques, chaque point de contrôle décalé par
  // une onde qui MONTE (phase qui dépend de la hauteur) : la langue ondule, se tord, s'amincit et se regonfle.
  function langue(H, w, px, t, R, echelle) {
    const O = R.ondulation, k = O.amplitude * w;
    const ond = (y, cote) => k * onde(t - y / (O.longueur * R.h) * O.periode, O.periode, R.phase + cote * 0.18);
    const y1 = -H * 0.34, y2 = -H * 0.66;
    const gx1 = -w * 1.12 + ond(0.34 * H, 0), gx2 = -w * 0.34 + px * 0.55 + ond(0.66 * H, 0);
    const dx1 = w * 1.12 + ond(0.34 * H, 1), dx2 = w * 0.34 + px * 0.55 + ond(0.66 * H, 1);
    const s = echelle;
    const P = (x, y) => f2(x * s) + " " + f2(y * s);
    return "M" + P(-w, 0) + " C" + P(gx1, y1) + " " + P(gx2, y2) + " " + P(px, -H) + " C" + P(dx2, y2) + " " + P(dx1, y1) + " " + P(w, 0) +
      " Q" + P(0, w * 0.42) + " " + P(-w, 0) + " Z";
  }

  function flamme(parent, reglages) {
    const R = fusion(DEFAUTS.flamme, reglages);
    const g = el(parent, "g", {});
    const ext = el(g, "path", { fill: R.couleur }), int = el(g, "path", { fill: R.coeur });
    const fm = R.flammeche ? el(g, "path", { fill: R.couleur }) : null;
    return function maj(t, aviver) {
      let hr = 1 + (aviver || 0);
      R.hauteur.forEach((o, i) => { hr += o[1] * onde(t, o[0], R.phase + i * 0.29); });
      let px = 0;
      R.torsion.forEach((o, i) => { px += o[1] * R.h * onde(t, o[0], R.phase * 1.7 + i * 0.41); });
      let fv = -1;                                         // vie de la flammèche en cours, [0, 1]
      if (fm) {
        const F = R.flammeche, u = ((t - F.decalage) % F.periode + F.periode) % F.periode;
        fv = u < F.duree ? u / F.duree : -1;
        if (fv >= 0) hr -= F.retrait * sin(PI * Math.min(1, fv * 1.6));   // la pointe se rétracte en lâchant sa flammèche
      }
      const H = R.h * hr;
      g.setAttribute("transform", "translate(" + f2(R.x) + " " + f2(R.base) + ")");
      ext.setAttribute("d", langue(H, R.w, px, t, R, 1));
      int.setAttribute("d", langue(H * R.coeur_echelle, R.w * 0.48, px * 0.6, t + 0.07, R, 1));   // le cœur suit, un peu en retard
      if (fm) {
        if (fv < 0) { fm.setAttribute("d", ""); }
        else {
          const F = R.flammeche, r = R.w * F.taille * 2.2 * (1 - fv) + 0.5, yb = -H - F.montee * R.h * (fv * (2 - fv)) * 0.9;
          const xb = px * (1 + fv) + R.w * 0.35 * onde(t, R.torsion[0][0], R.phase + 0.5);
          fm.setAttribute("d", "M" + f2(xb - r) + " " + f2(yb) + " Q" + f2(xb - r) + " " + f2(yb - r * 1.6) + " " + f2(xb) + " " + f2(yb - r * 2.6) +
            " Q" + f2(xb + r) + " " + f2(yb - r * 1.6) + " " + f2(xb + r) + " " + f2(yb) + " Q" + f2(xb) + " " + f2(yb + r * 0.9) + " " + f2(xb - r) + " " + f2(yb) + " Z");
        }
      }
    };
  }

  function traits(parent, reglages) {
    const R = fusion(DEFAUTS.traits, reglages);
    const g = el(parent, "g", { fill: "none", stroke: R.couleur, "stroke-width": R.epaisseur, "stroke-linecap": "round" });
    const L = []; for (let i = 0; i < R.n; i++) L.push(el(g, "path", { d: "" }));
    return function maj(v, x, y, angle) {
      if (!(v >= 0 && v <= 1)) { L.forEach((p) => p.setAttribute("d", "")); return; }
      const ux = cos(angle), uy = sin(angle), nx = -uy, ny = ux;          // u : sens du mouvement ; n : travers
      L.forEach(function (p, i) {
        const lg = R.longueurs[i % R.longueurs.length], off = (i - (R.n - 1) / 2) * R.ecart;
        const dec = (i % 2) * 0.12;                                        // les traits ne naissent pas tous ensemble
        const w = Math.max(0, Math.min(1, (v - dec) / (1 - dec)));
        const avant = Math.min(1, w / 0.45), arriere = Math.max(0, (w - 0.55) / 0.45);   // pousse puis se rétracte vers l'avant
        const a0 = -R.recul - lg * (1 - arriere), a1 = -R.recul - lg * (1 - avant);
        if (a1 - a0 < 1) { p.setAttribute("d", ""); return; }
        const X = (a) => x + ux * a + nx * off, Y = (a) => y + uy * a + ny * off;
        p.setAttribute("d", "M" + f2(X(a0)) + " " + f2(Y(a0)) + " L" + f2(X(a1)) + " " + f2(Y(a1)));
      });
    };
  }

  function etirer(vx, vy, f) {
    if (!(f > 1.001) || (!vx && !vy)) return "";
    const a = Math.atan2(vy, vx) * 180 / PI;
    return "rotate(" + f2(a) + ") scale(" + f.toFixed(4) + " " + (1 / Math.sqrt(f)).toFixed(4) + ") rotate(" + f2(-a) + ")";
  }

  const fenetre = (t, t0, duree) => (t >= t0 && t <= t0 + duree ? (t - t0) / duree : -1);

  // ------------------------------------------------------------------ ajouts du 29/09 (lot des pages métier)
  // Easings (sans rebond élastique) et clés : FX.cles(u, [[u0, a, b…], [u1, a, b…, "p2o"], …]) → [a, b…] interpolés.
  const EASE = { lin: (x) => x, sio: (x) => 0.5 - 0.5 * cos(PI * x), p2o: (x) => 1 - (1 - x) * (1 - x), p3o: (x) => 1 - Math.pow(1 - x, 3),
                 p2i: (x) => x * x, p3i: (x) => x * x * x, p4o: (x) => 1 - Math.pow(1 - x, 4) };
  function cles(u, C) {
    if (u <= C[0][0]) return C[0].slice(1).filter((v) => typeof v === "number");
    for (let k = 1; k < C.length; k++) if (u <= C[k][0]) {
      const a = C[k - 1], b = C[k], n = b.length - (typeof b[b.length - 1] === "string" ? 2 : 1);
      const e = EASE[typeof b[b.length - 1] === "string" ? b[b.length - 1] : "sio"]((u - a[0]) / (b[0] - a[0]));
      const out = []; for (let i = 1; i <= n; i++) out.push(a[i] + (b[i] - a[i]) * e);
      return out;
    }
    const L = C[C.length - 1]; return L.slice(1).filter((v) => typeof v === "number");
  }
  // Pseudo-hasard déterministe (graine) : mêmes particules à chaque rendu.
  function hasard(graine) { let s = graine >>> 0 || 1; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

  // Gerbe de particules au trait : gouttes (étirées le long de la vitesse), poussière (disques qui s'éteignent en rapetissant),
  // étincelles (courts traits le long de la vitesse). v ∈ [0, 1] : vie de la gerbe ; hors de [0, 1] : rien.
  DEFAUTS.particules = { n: 7, forme: "goutte", couleur: "#262019", contour: null, epaisseur: 5, taille: [7, 12], vitesse: [260, 420],
                         ouverture: 1.1, gravite: 900, duree: 0.6, graine: 7, trainee: 0.045 };
  function particules(parent, reglages) {
    const R = fusion(DEFAUTS.particules, reglages), rnd = hasard(R.graine);
    const P = []; for (let i = 0; i < R.n; i++) P.push({ a: (rnd() - 0.5) * R.ouverture, v: R.vitesse[0] + rnd() * (R.vitesse[1] - R.vitesse[0]),
      r: R.taille[0] + rnd() * (R.taille[1] - R.taille[0]), d: rnd() * 0.18 });
    const g = el(parent, "g", {});
    const E = P.map(() => el(g, "path", R.forme === "etincelle" ? { fill: "none", stroke: R.couleur, "stroke-width": R.epaisseur, "stroke-linecap": "round" }
      : { fill: R.couleur, stroke: R.contour || "none", "stroke-width": R.contour ? R.epaisseur : 0 }));
    return function maj(v, x, y, angle) {
      P.forEach(function (p, i) {
        const w = (v - p.d) / (1 - p.d);
        if (!(v >= 0 && v <= 1) || w < 0 || w > 1) { E[i].setAttribute("d", ""); return; }
        const t = w * R.duree * (1 - p.d), a = angle + p.a, vx = cos(a) * p.v, vy = sin(a) * p.v + R.gravite * t;
        const px = x + cos(a) * p.v * t, py = y + sin(a) * p.v * t + 0.5 * R.gravite * t * t;
        const vit = Math.hypot(vx, vy), ux = vx / vit, uy = vy / vit;
        if (R.forme === "poussiere") {
          const r = p.r * (0.5 + 0.9 * w) * (1 - w * w);
          E[i].setAttribute("d", r < 0.3 ? "" : "M" + f2(px - r) + " " + f2(py) + " a" + f2(r) + " " + f2(r) + " 0 1 0 " + f2(2 * r) + " 0 a" + f2(r) + " " + f2(r) + " 0 1 0 " + f2(-2 * r) + " 0 Z");
        } else if (R.forme === "etincelle") {
          const L = Math.max(4, vit * R.trainee) * (1 - w);
          E[i].setAttribute("d", L < 1 ? "" : "M" + f2(px) + " " + f2(py) + " L" + f2(px - ux * L) + " " + f2(py - uy * L));
        } else {                                                    // goutte : tête ronde, queue le long de la vitesse
          const r = p.r * (1 - 0.35 * w), L = r + Math.min(3.2 * r, vit * R.trainee);
          const nx = -uy, ny = ux, tx = px - ux * L, ty = py - uy * L;
          E[i].setAttribute("d", "M" + f2(px + nx * r) + " " + f2(py + ny * r) + " A" + f2(r) + " " + f2(r) + " 0 1 1 " + f2(px - nx * r) + " " + f2(py - ny * r) +
            " Q" + f2(px - nx * r * 0.4 - ux * L * 0.5) + " " + f2(py - ny * r * 0.4 - uy * L * 0.5) + " " + f2(tx) + " " + f2(ty) +
            " Q" + f2(px + nx * r * 0.4 - ux * L * 0.5) + " " + f2(py + ny * r * 0.4 - uy * L * 0.5) + " " + f2(px + nx * r) + " " + f2(py + ny * r) + " Z");
        }
      });
    };
  }

  // Éclat électrique : une étoile dont les branches changent de longueur et d'angle à chaque image (même famille que la
  // flamme : une forme qui se déforme), cœur clair ; v ∈ [0, 1] : éclosion rapide puis extinction.
  DEFAUTS.eclat = { branches: 6, rayon: 46, creux: 0.28, couleur: "#EFA424", coeur: "#F8D69B", graine: 3, cadence: 30 };
  function eclat(parent, reglages) {
    const R = fusion(DEFAUTS.eclat, reglages);
    const g = el(parent, "g", {}), ext = el(g, "path", { fill: R.couleur }), int = el(g, "path", { fill: R.coeur });
    const etoile = (n, rr, cr, rot, jit) => { let d = ""; for (let i = 0; i < 2 * n; i++) { const a = rot + i * PI / n;
      const r = i % 2 ? rr * cr : rr * jit[(i >> 1) % jit.length]; d += (i ? " L" : "M") + f2(cos(a) * r) + " " + f2(sin(a) * r); } return d + " Z"; };
    return function maj(v, x, y, t) {
      if (!(v >= 0 && v <= 1)) { ext.setAttribute("d", ""); int.setAttribute("d", ""); return; }
      const rnd = hasard(R.graine + Math.floor(t * R.cadence) * 97);           // une nouvelle forme à chaque image
      const jit = []; for (let i = 0; i < R.branches; i++) jit.push(0.55 + 0.6 * rnd());
      const k = v < 0.25 ? EASE.p3o(v / 0.25) : 1 - EASE.p2i((v - 0.25) / 0.75), rot = rnd() * PI;
      g.setAttribute("transform", "translate(" + f2(x) + " " + f2(y) + ")");
      ext.setAttribute("d", etoile(R.branches, R.rayon * k, R.creux, rot, jit));
      int.setAttribute("d", etoile(R.branches, R.rayon * 0.45 * k, R.creux * 1.3, rot + 0.2, jit));
    };
  }

  // Chute voletante (mèche, feuille, farine en flocon) : descente freinée, balancement latéral, rotation qui suit le balancement.
  function chute(tc, R) {        // tc : temps depuis le lâcher (s) ; R : {x, y, vitesse, amplitude, pulsation, tour, phase}
    const w = R.pulsation || 5, ph = R.phase || 0;
    return { x: R.x + (R.amplitude || 30) * sin(w * tc + ph) * Math.min(1, tc * 3), y: R.y + (R.vitesse || 160) * tc,
             rot: (R.tour || 0) * tc + 28 * cos(w * tc + ph) * Math.min(1, tc * 3) };
  }
  // Pendule amorti (ficelle, trousseau) : angle en degrés, lâché à t0 avec l'amplitude A.
  const pendule = (t, t0, A, periode, amorti) => (t < t0 ? 0 : A * Math.exp(-(t - t0) * (amorti || 1.6)) * cos(2 * PI * (t - t0) / periode));

  // Temps du geste : dans la boucle, t ≥ 5 s devient négatif (t − 10) : la fin de la boucle montre l'AVANT du geste, qui
  // rejoint sans saut l'image 0 ; dans la complète, le temps tel quel.
  const tau = (t, mode) => (mode === "boucle" && t >= 5 ? t - 10 : t);
  window.FX = { tau: tau, DEFAUTS: DEFAUTS, flamme: flamme, traits: traits, etirer: etirer, fenetre: fenetre, onde: onde,
                EASE: EASE, cles: cles, hasard: hasard, particules: particules, eclat: eclat, chute: chute, pendule: pendule };
})();
