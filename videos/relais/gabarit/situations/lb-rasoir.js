/* Animateur de la situation « lb-rasoir » (barbier, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps.
   Boucle : l'horloge du geste part du retour de la situation (DONNEES.situation.revient, 8,75 s) et fait 10 s ; la situation
   est visible de u = 0 à u ≈ 3,2 (8,75 → 10 → 1,95 s du film), la mousse se reforme ensuite, cachée : raccord parfait.
   Deux passes : anticipation (le poignet recule), glisse le long de la joue (la peau apparaît sous la lame, la mousse
   s'accumule sur le fil), coup de poignet (traits de vitesse sur 3 images), flocons qui s'envolent (smear au départ, freinés
   par l'air, flottent en retombant, se défont). Complète : même horloge, décalée pour que la première passe tombe dans la
   seconde où la situation est montrée. */
(function () {
  const REGLAGES = {
    decalage_complete: 0.0,
    mousse: { points: [[282, 316], [330, 298], [382, 300], [424, 320], [434, 348], [450, 386], [452, 424], [428, 454], [388, 470],
                       [330, 470], [288, 444], [268, 386], [272, 344]], bosse: 30, relief: 0.12,
              bulles: [[300, 366, 7], [352, 424, 9], [406, 356, 6], [420, 430, 7], [336, 336, 5], [292, 412, 6]] },
    passes: [
      { chemin: "M342 282 C 344 336 347 392 350 446", lame: 44, u0: 0.45, u1: 0.95, coup: 0.95, depart: 1.0 },
      { chemin: "M394 286 C 396 340 399 392 402 440", lame: 44, u0: 1.72, u1: 2.2, coup: 2.2, depart: 2.25 }],
    survol: 16,                      // la lame au-dessus de la peau entre deux passes
    coup: { dx: 30, dy: 4, rot: 26, duree: 0.17 },
    flocons: { n: 5, vitesse: [600, 800], angles: [-58, -4], frein: 4.2, chute: 70, flotte: 9, freq: 2.6, vie: [0.8, 1.05], taille: [13, 19] },
    smear: { duree: 0.07, etirement: 0.9, vitesse: 0.0009, vitesse_max: 0.55 },
    traits: { n: 3, longueurs: [46, 62, 38], ecart: 16, recul: 30, epaisseur: 5 }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const E = { lin: (x) => x, sio: (x) => 0.5 - 0.5 * cos(PI * x), p2o: (x) => 1 - (1 - x) * (1 - x), p2i: (x) => x * x,
              p3o: (x) => 1 - Math.pow(1 - x, 3) };
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const D = window.DONNEES || { situation: {} };
  const RETOUR = D.situation && D.situation.revient != null ? D.situation.revient : 8.75;
  // hasard déterministe
  const hasard = (i) => { const x = sin(i * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

  // contour festonné (mousse) : chaque arête devient une suite de bosses tournées vers l'extérieur
  function feston(P, bosse, relief) {
    let aire = 0; for (let i = 0; i < P.length; i++) { const a = P[i], b = P[(i + 1) % P.length]; aire += a[0] * b[1] - b[0] * a[1]; }
    const bal = aire > 0 ? 1 : 0;                   // sens de parcours : les arcs bombent toujours vers l'extérieur
    let d = "M" + f2(P[0][0]) + " " + f2(P[0][1]);
    for (let i = 0; i < P.length; i++) {
      const a = P[i], b = P[(i + 1) % P.length], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      const n = Math.max(1, Math.round(L / bosse));
      for (let k = 0; k < n; k++) {
        const s1 = (k + 1) / n, c = L / n, r = c / 2 * (1 + relief * (0.6 + 0.8 * hasard(i * 13 + k)));
        d += " A" + f2(r) + " " + f2(r) + " 0 0 " + bal + " " + f2(a[0] + dx * s1) + " " + f2(a[1] + dy * s1);
      }
    }
    return d + " Z";
  }
  const blob = (r, graine) => { const P = []; for (let k = 0; k < 6; k++) { const a = k * PI / 3 + graine, rr = r * (0.8 + 0.3 * hasard(graine * 7 + k)); P.push([rr * cos(a), rr * sin(a)]); } return feston(P, r * 0.9, 0.1); };

  const gM = document.getElementById("ra-mousse"), gR = document.getElementById("ra-rase"), gF = document.getElementById("ra-flocons");
  const rasoir = document.getElementById("ra-rasoir"), lameMousse = document.getElementById("ra-lame-mousse");
  const dMousse = feston(R.mousse.points, R.mousse.bosse, R.mousse.relief);
  el(gM, "path", { d: dMousse, fill: "#FFFFFF", stroke: "#262019", "stroke-width": 7, "stroke-linejoin": "round" });
  const defs = el(document.getElementById("objet"), "defs", {}), clip = el(defs, "clipPath", { id: "ra-clip" });
  el(clip, "path", { d: dMousse });
  const gBords = el(document.getElementById("ra-rase").parentNode, "g", { "clip-path": "url(#ra-clip)", fill: "none", stroke: "#262019", "stroke-width": 4.5, "stroke-linecap": "round" });
  document.getElementById("ra-rase").after(gBords);
  R.mousse.bulles.forEach((b) => el(gM, "circle", { cx: b[0], cy: b[1], r: b[2], fill: "none", stroke: "#262019", "stroke-width": 3.5 }));
  const passes = R.passes.map(function (p) {
    const ch = el(gR, "path", { d: p.chemin, "stroke-width": p.lame }), L = ch.getTotalLength();
    // les deux bords de la mousse coupée : le chemin décalé de ± la demi-lame, légèrement festonné
    const bords = [-1, 1].map(function (cote) {
      let d = "";
      for (let k = 0; k <= 16; k++) {
        const s = k / 16, a = ch.getPointAtLength(s * L), b = ch.getPointAtLength(Math.min(L, s * L + 1)), c = ch.getPointAtLength(Math.max(0, s * L - 1));
        const tx = b.x - c.x, ty = b.y - c.y, n = Math.hypot(tx, ty) || 1, w = p.lame / 2 + 1.5 + 2 * sin(k * 0.9 + cote * 1.7);
        d += (k ? " L" : "M") + f2(a.x - cote * ty / n * w) + " " + f2(a.y + cote * tx / n * w);
      }
      return el(gBords, "path", { d: d });
    });
    return Object.assign({ el: ch, L: L, bords: bords }, p);
  });
  const amas = el(lameMousse, "path", { d: blob(15, 0.4), fill: "#FFFFFF", stroke: "#262019", "stroke-width": 5, "stroke-linejoin": "round" });
  const traits = FX.traits(document.getElementById("ra-traits"), R.traits);
  // flocons : 5 par passe, tirés une fois pour toutes
  const F = R.flocons, flocons = [];
  passes.forEach(function (p, ip) {
    for (let i = 0; i < F.n; i++) {
      const h = (k) => hasard(ip * 50 + i * 7 + k);
      const ang = (F.angles[0] + (F.angles[1] - F.angles[0]) * (i + 0.5 * h(1)) / F.n) * PI / 180, v = F.vitesse[0] + (F.vitesse[1] - F.vitesse[0]) * h(2);
      flocons.push({ passe: ip, depart: p.depart + i * 0.018, bord: (i / (F.n - 1) - 0.5) * 56, vx: v * cos(ang), vy: v * sin(ang),
        vie: F.vie[0] + (F.vie[1] - F.vie[0]) * h(3), r: F.taille[0] + (F.taille[1] - F.taille[0]) * h(4), tour: (h(5) - 0.5) * 900,
        ph: h(6) * 2 * PI, g: el(gF, "g", {}) });
    }
  });
  flocons.forEach((f, i) => el(f.g, "path", { d: blob(f.r, i * 0.9 + 0.3), fill: "#FFFFFF", stroke: "#262019", "stroke-width": 5, "stroke-linejoin": "round" }));

  // ---------------- pose du rasoir (x, y du milieu du fil ; rotation en degrés) en fonction de u
  const pt = (p, s) => { const q = p.el.getPointAtLength(cl(s, 0, 1) * p.L); return [q.x, q.y]; };
  const A = passes[0], B = passes[1], C = R.coup, S = R.survol;
  const haut = (p, dy, r) => { const q = pt(p, 0); return [q[0], q[1] - dy, r]; };
  const fin = (p) => pt(p, 1);
  const mix = (a, b, e) => [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e];
  function pose(u) {
    const tA = haut(A, S, -4), tB = haut(B, S, -4), armeA = haut(A, S + 14, -11), armeB = haut(B, S + 14, -11);
    const fa = fin(A), fb = fin(B), coupA = [fa[0] + C.dx, fa[1] + C.dy - 26, C.rot], coupB = [fb[0] + C.dx, fb[1] + C.dy - 26, C.rot];
    const s = (a, b) => cl((u - a) / (b - a), 0, 1);
    if (u < 0.3) return tA;
    if (u < 0.41) return mix(tA, armeA, E.sio(s(0.3, 0.41)));                                   // anticipation
    if (u < A.u0) return mix(armeA, [pt(A, 0)[0], pt(A, 0)[1], 0], E.p2i(s(0.41, A.u0)));      // la lame se pose
    if (u < A.u1) { const q = pt(A, E.sio(s(A.u0, A.u1))); return [q[0], q[1], 2 * sin(PI * s(A.u0, A.u1))]; }
    if (u < A.u1 + C.duree) return mix([fa[0], fa[1], 0], coupA, E.p2o(s(A.u1, A.u1 + C.duree)));   // coup de poignet
    if (u < 1.58) { const e = E.sio(s(A.u1 + C.duree, 1.58)), q = mix(coupA, tB, e); q[1] -= 34 * sin(PI * e); return q; }
    if (u < 1.66) return mix(tB, armeB, E.sio(s(1.58, 1.66)));
    if (u < B.u0) return mix(armeB, [pt(B, 0)[0], pt(B, 0)[1], 0], E.p2i(s(1.66, B.u0)));
    if (u < B.u1) { const q = pt(B, E.sio(s(B.u0, B.u1))); return [q[0], q[1], 2 * sin(PI * s(B.u0, B.u1))]; }
    if (u < B.u1 + C.duree) return mix([fb[0], fb[1], 0], coupB, E.p2o(s(B.u1, B.u1 + C.duree)));
    if (u < 3.0) { const e = E.sio(s(B.u1 + C.duree, 3.0)), q = mix(coupB, tA, e); q[1] -= 30 * sin(PI * e); return q; }
    return tA;                                                                                    // prêt pour la passe suivante
  }
  const bordLame = (P, off) => { const a = P[2] * PI / 180; return [P[0] + off * cos(a), P[1] + off * sin(a)]; };

  window.SITUATION_ANIM = function (t, periode, mode) {
    const u = mode === "complete" ? t + R.decalage_complete : ((t - RETOUR) % 10 + 10) % 10;
    const P = pose(u);
    rasoir.setAttribute("transform", "translate(" + f2(P[0]) + " " + f2(P[1]) + ") rotate(" + P[2].toFixed(3) + ")");
    // peau découverte : le trait s'arrête sous le fil (son bout rond ne dépasse jamais la lame)
    passes.forEach(function (p) {
      let vis = 0;
      if (u >= p.u0 && u < 3.7) vis = u >= p.u1 ? 1 : E.sio((u - p.u0) / (p.u1 - p.u0));
      const long = vis * p.L - p.lame / 2 + 4;
      if (long <= 0.5) { p.el.setAttribute("visibility", "hidden"); p.bords.forEach((b) => b.setAttribute("visibility", "hidden")); return; }
      p.el.setAttribute("visibility", "visible");
      p.el.setAttribute("stroke-dasharray", f2(long) + " " + f2(p.L + 200));
      p.bords.forEach(function (b) { b.setAttribute("visibility", "visible"); b.setAttribute("stroke-dasharray", f2(Math.max(0, vis * p.L - 6)) + " " + f2(p.L + 200)); });
    });
    // mousse accumulée sur le fil pendant la passe, lâchée au coup de poignet
    let amasS = 0;
    passes.forEach(function (p) { if (u >= p.u0 && u < p.depart) amasS = u >= p.u1 ? 1 : 0.3 + 0.7 * (u - p.u0) / (p.u1 - p.u0); });
    amas.setAttribute("transform", amasS > 0 ? "translate(-6 5) scale(" + (amasS * 1.0).toFixed(3) + " " + (amasS * 0.8).toFixed(3) + ")" : "scale(0)");
    // traits de vitesse du coup de poignet
    let tr = -1, ang = 0;
    passes.forEach(function (p) { const v = FX.fenetre(u, p.u1 + 0.01, 0.1); if (v >= 0) { tr = v; const a = pose(u), b = pose(u + 0.004); ang = Math.atan2(b[1] - a[1], b[0] - a[0]); } });
    const pe = bordLame(P, 0);
    traits(tr, pe[0], pe[1], ang);
    // flocons
    flocons.forEach(function (f) {
      const s = u - f.depart;
      if (s < 0 || s > f.vie) { f.g.setAttribute("transform", "scale(0)"); return; }
      const Pd = pose(f.depart), o = bordLame(Pd, f.bord), k = F.frein, vt = F.chute;
      const pos = (s) => { const e = Math.exp(-k * s); return [o[0] + f.vx * (1 - e) / k + F.flotte * sin(2 * PI * F.freq * s + f.ph) * (1 - e), o[1] + 4 + vt * s + (f.vy - vt) * (1 - e) / k]; };
      const q = pos(s), q2 = pos(s + 0.004), vx = (q2[0] - q[0]) / 0.004, vy = (q2[1] - q[1]) / 0.004, vit = Math.hypot(vx, vy);
      const Sm = R.smear, fe = Math.max(1 + Math.min(Sm.vitesse_max, vit * Sm.vitesse), s < Sm.duree ? 1 + Sm.etirement * (1 - s / Sm.duree) : 1);
      const naissance = cl(s / 0.06, 0, 1), mort = cl((f.vie - s) / 0.32, 0, 1);
      const sc = (0.55 + 0.45 * E.p2o(naissance)) * E.sio(mort);
      const rot = f.tour * (1 - Math.exp(-k * s)) / k;
      f.g.setAttribute("transform", "translate(" + f2(q[0]) + " " + f2(q[1]) + ") " + FX.etirer(vx, vy, fe) + " scale(" + sc.toFixed(4) + ") rotate(" + f2(rot) + ")");
    });
  };
})();
