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

  window.FX = { DEFAUTS: DEFAUTS, flamme: flamme, traits: traits, etirer: etirer, fenetre: fenetre, onde: onde };
})();
