/* Animateur de la situation « lb-refracteur » (opticien, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps,
   périodique (2,5 s, 4 séquences par boucle). Chaque molette tourne d'un cran de 30° : départ sec, dépassement amorti
   (le cran « claque »), traits de choc au bouton sur 3 images, l'appareil encaisse (1 px) ; le verre change à mi-course
   (un anneau, puis deux : deux états, la boucle en compte un nombre pair). Le reflet glisse ensuite en diagonale sur le verre
   de gauche, puis de droite (décalé). */
(function () {
  const REGLAGES = {
    decalage_complete: 0.0,
    yeux: [[186, 330], [414, 330]], crans: [0.18, 0.52], cran: 30, duree: 0.28,
    reflet: { depart: [0.95, 1.08], duree: 0.34 },
    traits: { n: 2, longueurs: [18, 24], ecart: 14, recul: 12, epaisseur: 5 }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos, exp = Math.exp;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const $ = (i) => document.getElementById(i);
  const tout = $("rf-tout");
  const cotes = ["g", "d"].map(function (c, i) {
    const C = R.yeux[i], mol = el($("rf-molette-" + c), "g", {});
    for (let k = 0; k < 12; k++) {                       // 12 crans : la molette est symétrique par pas de 30°
      const a = k * PI / 6, r0 = 72, r1 = 90;
      el(mol, "path", { d: "M" + f2(C[0] + r0 * cos(a)) + " " + f2(C[1] + r0 * sin(a)) + " L" + f2(C[0] + r1 * cos(a)) + " " + f2(C[1] + r1 * sin(a)),
        stroke: "#262019", "stroke-width": 5, "stroke-linecap": "round" });
    }
    [0, 1, 2].forEach((k) => el(mol, "circle", { cx: f2(C[0] + 81 * cos(k * 2 * PI / 3 + PI / 12)), cy: f2(C[1] + 81 * sin(k * 2 * PI / 3 + PI / 12)), r: 11, fill: "#262019" }));   // 3 boutons à 120° : 4 crans de 30° par boucle
    // deux verres possibles (un anneau / deux anneaux) : on bascule de l'un à l'autre à chaque cran
    const vg = $("rf-verre-" + c);
    const A = el(vg, "g", {}), B = el(vg, "g", {});
    el(A, "circle", { cx: C[0], cy: C[1], r: 28, fill: "none", stroke: "#EFA424", "stroke-width": 7 });
    el(B, "circle", { cx: C[0], cy: C[1], r: 16, fill: "none", stroke: "#EFA424", "stroke-width": 7 });
    el(B, "circle", { cx: C[0], cy: C[1], r: 38, fill: "none", stroke: "#EFA424", "stroke-width": 7 });
    return { C: C, mol: mol, A: A, B: B, reflet: $("rf-reflet-" + c), traits: FX.traits($("rf-traits"), R.traits) };
  });
  // cran : 0 → 1 avec départ sec et dépassement amorti
  function cran(s) {
    if (s <= 0) return 0;
    if (s >= R.duree) return 1;
    const e = 1 - exp(-s / 0.035) * cos(2 * PI * s / 0.16);
    return e;
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const tt = mode === "complete" ? t + R.decalage_complete : t;
    const n = Math.floor(tt / periode), s = tt - n * periode;          // n : séquences déjà faites
    let choc = 0;
    cotes.forEach(function (c, i) {
      const q = s - R.crans[i], e = cran(q);
      const angle = R.cran * (n + e);
      c.mol.setAttribute("transform", "rotate(" + f2(angle % 360) + " " + c.C[0] + " " + c.C[1] + ")");
      const etat = (n + (q > 0.05 ? 1 : 0)) % 2;
      c.A.setAttribute("visibility", etat ? "hidden" : "visible");
      c.B.setAttribute("visibility", etat ? "visible" : "hidden");
      // traits de choc au bouton solaire, dans le sens de la rotation
      const a = (angle + 15) * PI / 180, bx = c.C[0] + 81 * cos(a), by = c.C[1] + 81 * sin(a);
      c.traits(FX.fenetre(q, 0.0, 0.1), bx, by, a + PI / 2);
      if (q > 0 && q < 0.12) choc += sin(PI * q / 0.12);
      // reflet : une bande qui traverse le verre en diagonale
      const r = s - R.reflet.depart[i], v = r / R.reflet.duree;
      if (v > 0 && v < 1) {
        const e2 = 0.5 - 0.5 * cos(PI * v), d = -80 + 160 * e2;
        const x0 = c.C[0] + d - 40, y0 = c.C[1] + d * 0.2 - 60, x1 = c.C[0] + d + 20, y1 = c.C[1] + d * 0.2 + 60;
        c.reflet.setAttribute("d", "M" + f2(x0) + " " + f2(y0) + " L" + f2(x1) + " " + f2(y1));
      } else c.reflet.setAttribute("d", "");
    });
    tout.setAttribute("transform", "translate(0 " + f2(1.2 * choc) + ")");
  };
})();
