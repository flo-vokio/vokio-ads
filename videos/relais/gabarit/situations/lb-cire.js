/* Animateur de la situation « lb-cire » (institut de beauté, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du
   temps, périodique (un tour de spatule en 2,5 s, 4 tours par boucle de 10 s ; la fumée a ses périodes, diviseurs de 10).
   La spatule : son pied décrit l'ellipse de la surface, pousse plus vite devant (la main appuie) ; le manche suit avec un
   retard d'angle (follow-through) ; le bas est enrobé de cire. La cire : deux arcs de remous qui tournent derrière la
   spatule, en retard (overlap), et un bourrelet autour du pied. La fumée : trois filets, chacun fait de bouffées qui montent,
   s'étirent, ondulent (le tracé suit une onde qui monte et dont l'amplitude croît avec la hauteur), s'amincissent et
   s'effacent en haut. */
(function () {
  const REGLAGES = {
    centre: [300, 340], surface: [82, 17], haut: [112, 24], hauteur: 196, pousse: 0.07, retard: 0.5, largeur: 54, cire: [122, 25],
    coulures: [[222, 44, 0.0], [300, 70, 0.4], [370, 30, 0.75]],   // [x, longueur, phase] : la cire qui a coulé sur le bord, qui s'allonge à peine
    remous: [[0.62, 0.5, 1.1], [0.36, 0.3, 1.6]],     // [rayon relatif, retard (tours), longueur d'arc (rad)]
    fumee: { filets: [[242, 0.0], [300, 0.37], [356, 0.71]], base: 312, montee: 250, vie: 2.5, bouffees: 3, longueur: 70,
             onde: { longueur: 120, periode: 2.5, amplitude: [4, 26] }, epaisseur: [9, 3] }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const $ = (i) => document.getElementById(i);
  const gS = $("ci-spatule"), gR = $("ci-remous"), gF = $("ci-fumee");
  const bourrelet = el(gS, "ellipse", { rx: 26, ry: 6, fill: "#EFA424", stroke: "#262019", "stroke-width": 4 });
  const baton = el(gS, "path", { fill: "#F4F1E8", stroke: "#262019", "stroke-width": 7, "stroke-linejoin": "round" });
  const enrobe = el(gS, "path", { fill: "#EFA424", stroke: "#262019", "stroke-width": 5, "stroke-linejoin": "round" });
  const remous = R.remous.map(() => el(gR, "path", {}));
  const coulures = R.coulures.map((c) => ({ x: c[0], L: c[1], ph: c[2], p: el($("ci-coulures"), "path", {}) }));
  const F = R.fumee, bouffees = [];
  F.filets.forEach((f, i) => { for (let k = 0; k < F.bouffees; k++) bouffees.push({ x: f[0], ph: f[1], k: k, i: i, p: el(gF, "path", {}) }); });
  const C = R.centre;
  // bâton de spatule (langue de bois) entre le pied P et le haut H : largeur 26, bout arrondi en haut
  function langue(P, H, w, de, a) {
    const dx = H[0] - P[0], dy = H[1] - P[1], L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, nx = -uy * w / 2, ny = ux * w / 2;
    const A = [P[0] + ux * L * de, P[1] + uy * L * de], B = [P[0] + ux * L * a, P[1] + uy * L * a];
    const bout = a >= 0.999;
    let d = "M" + f2(A[0] + nx) + " " + f2(A[1] + ny) + " L" + f2(B[0] + nx) + " " + f2(B[1] + ny);
    if (bout) d += " A" + f2(w / 2) + " " + f2(w / 2) + " 0 0 0 " + f2(B[0] - nx) + " " + f2(B[1] - ny);
    else d += " L" + f2(B[0] - nx) + " " + f2(B[1] - ny);
    return d + " L" + f2(A[0] - nx) + " " + f2(A[1] - ny) + " Z";
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const tour = t / periode, th = 2 * PI * (tour + R.pousse * sin(2 * PI * tour));
    const P = [C[0] + R.surface[0] * cos(th), C[1] + R.surface[1] * sin(th)];
    const tl = th - R.retard;                         // le manche suit en retard
    const H = [C[0] + R.haut[0] * cos(tl) * 0.9, C[1] - R.hauteur + R.haut[1] * sin(tl)];
    // pied derrière (haut de l'ellipse) : on voit moins de bâton ; devant : plus long, il passe devant la cire
    baton.setAttribute("d", langue(P, H, R.largeur, 0, 1));
    enrobe.setAttribute("d", langue(P, H, R.largeur + 3, 0, 0.3));
    coulures.forEach(function (c) {
      const x = c.x, L = c.L * (1 + 0.08 * sin(2 * PI * (t / 5 + c.ph))), y0 = 360, w = 12;
      c.p.setAttribute("d", "M" + (x - w) + " " + y0 + " L" + f2(x - w * 0.8) + " " + f2(y0 + L) + " Q" + f2(x - w * 0.8) + " " + f2(y0 + L + w * 1.3) + " " + x + " " + f2(y0 + L + w * 1.3) + " Q" + f2(x + w * 0.8) + " " + f2(y0 + L + w * 1.3) + " " + f2(x + w * 0.8) + " " + f2(y0 + L) + " L" + (x + w) + " " + y0 + " Z");
    });
    bourrelet.setAttribute("cx", f2(P[0])); bourrelet.setAttribute("cy", f2(P[1] + 1));
    remous.forEach(function (p, i) {
      const r = R.remous[i], a1 = th - 2 * PI * r[1] * 0.25 - 0.35, a0 = a1 - r[2];
      const rx = R.cire[0] * r[0], ry = R.cire[1] * r[0], x0 = C[0] + rx * cos(a0), y0 = C[1] + ry * sin(a0), x1 = C[0] + rx * cos(a1), y1 = C[1] + ry * sin(a1);
      p.setAttribute("d", "M" + f2(x0) + " " + f2(y0) + " A" + f2(rx) + " " + f2(ry) + " 0 0 1 " + f2(x1) + " " + f2(y1));
    });
    // fumée
    const O = F.onde;
    bouffees.forEach(function (b) {
      const vie = ((t / F.vie + b.ph + b.k / F.bouffees) % 1 + 1) % 1;      // 0 → 1 : de la surface au haut
      const pts = [], n = 10;
      for (let q = 0; q <= n; q++) {
        const h = F.montee * vie - F.longueur * (q / n) * (0.6 + 0.6 * vie);
        if (h < 0) break;
        const hr = h / F.montee, amp = O.amplitude[0] + (O.amplitude[1] - O.amplitude[0]) * hr;
        const x = b.x + amp * sin(2 * PI * (h / O.longueur - t / O.periode + b.i * 0.33)) + 10 * hr * sin(2 * PI * (t / 5 + b.i * 0.2));
        pts.push(f2(x) + " " + f2(F.base - h));
      }
      const alpha = sin(PI * cl(vie, 0, 1)) * cl(vie / 0.15, 0, 1);
      if (pts.length < 2 || alpha < 0.02) { b.p.setAttribute("d", ""); return; }
      b.p.setAttribute("d", "M" + pts.join(" L"));
      b.p.setAttribute("stroke-width", f2(F.epaisseur[0] + (F.epaisseur[1] - F.epaisseur[0]) * vie));
      b.p.setAttribute("stroke-linejoin", "round");
      b.p.setAttribute("opacity", (0.75 * alpha).toFixed(3));
    });
  };
})();
