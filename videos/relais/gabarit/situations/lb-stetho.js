/* Animateur de la situation « lb-stetho » (médecin, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps.
   Le stéthoscope : balancement périodique autour de la patère (1,25 s, 8 par boucle) ; le tuyau est tracé point par point,
   chaque point tourné de l'angle qu'avait la patère un peu plus tôt (retard proportionnel à la distance) : le tuyau ondule,
   le pavillon (plus loin, plus lourd) traîne, les embouts aussi. Le thermomètre : horloge u sur 10 s qui part du retour de
   la situation dans la boucle ; la colonne monte de 30 % à 86 % (power3.out, puis un frémissement de 2 px), redescend
   cachée. Complète : même horloge. */
(function () {
  const REGLAGES = {
    decalage_complete: 0.0,
    patere: [212, 112], amplitude: 8, periode: 1.25, retard: 0.0012,      // retard en s par unité de longueur
    // les deux brins, depuis la patère (coordonnées au repos) : à gauche la lyre et ses deux embouts, à droite le pavillon
    // au repos : la lyre (deux branches métalliques et leurs embouts) posée sur la patère, puis le tuyau jusqu'au pavillon
    lyre: [[[212, 236], [184, 206], [174, 150], [180, 100], [192, 78]], [[212, 236], [240, 206], [250, 150], [244, 100], [232, 78]]],
    tuyau: [[212, 236], [212, 280], [202, 330], [206, 380], [230, 420], [262, 436]],
    pavillon: { r: 42, anneau: 26 },
    colonne: { bas: 18, haut: 90, montee: [0.3, 2.3], cache: 3.8 }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const D = window.DONNEES || { situation: {} };
  const RETOUR = D.situation && D.situation.revient != null ? D.situation.revient : 8.75;
  const $ = (i) => document.getElementById(i);
  const g = $("st-steto"), P = R.patere;
  const tube = (w, c) => el(g, "path", { stroke: c, "stroke-width": w });
  const bord = tube(22, "#262019"), coeur = tube(10, "#F4F1E8");
  const lyres = R.lyre.map(() => el(g, "path", { stroke: "#262019", "stroke-width": 11 }));
  const embouts = R.lyre.map(() => el(g, "ellipse", { rx: 10, ry: 13, fill: "#262019" }));
  const noeud = el(g, "circle", { r: 13, fill: "#262019" });
  const pav = el(g, "g", {});
  el(pav, "circle", { r: R.pavillon.r, fill: "#F4F1E8", stroke: "#262019", "stroke-width": 9 });
  el(pav, "circle", { r: R.pavillon.anneau, fill: "none", stroke: "#262019", "stroke-width": 5 });
  el(pav, "rect", { x: -11, y: -58, width: 22, height: 20, rx: 4, fill: "#262019" });
  const col = $("st-colonne");
  const longueur = (pts) => { let L = [0]; for (let i = 1; i < pts.length; i++) L.push(L[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])); return L; };
  const Lt = longueur(R.tuyau);
  function tourne(p, a) { const c = cos(a), s = sin(a), x = p[0] - P[0], y = p[1] - P[1]; return [P[0] + x * c - y * s, P[1] + x * s + y * c]; }
  const angle = (t) => R.amplitude * PI / 180 * sin(2 * PI * t / R.periode);
  // courbe lisse par les points (Catmull-Rom → Bézier)
  function lisse(Q) {
    let d = "M" + f2(Q[0][0]) + " " + f2(Q[0][1]);
    for (let i = 0; i < Q.length - 1; i++) {
      const p0 = Q[Math.max(0, i - 1)], p1 = Q[i], p2 = Q[i + 1], p3 = Q[Math.min(Q.length - 1, i + 2)];
      d += " C" + f2(p1[0] + (p2[0] - p0[0]) / 6) + " " + f2(p1[1] + (p2[1] - p0[1]) / 6) + " " + f2(p2[0] - (p3[0] - p1[0]) / 6) + " " + f2(p2[1] - (p3[1] - p1[1]) / 6) + " " + f2(p2[0]) + " " + f2(p2[1]);
    }
    return d;
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const u = mode === "complete" ? t + R.decalage_complete : ((t - RETOUR) % 10 + 10) % 10;
    const tb = mode === "complete" ? t : t;                   // balancement : périodique sur le temps du film
    // la lyre est rigide (métal) : elle tourne d'un bloc avec la patère ; le tuyau est souple : retard croissant
    R.lyre.forEach(function (br, k) {
      const Q = br.map((p) => tourne(p, angle(tb)));
      lyres[k].setAttribute("d", lisse(Q));
      const e = Q[Q.length - 1];
      embouts[k].setAttribute("cx", f2(e[0])); embouts[k].setAttribute("cy", f2(e[1]));
    });
    const Y = tourne(R.lyre[0][0], angle(tb)); noeud.setAttribute("cx", f2(Y[0])); noeud.setAttribute("cy", f2(Y[1]));
    const Tp = R.tuyau.map((p, i) => tourne(p, angle(tb - R.retard * Lt[i])));
    const dT = lisse(Tp);
    bord.setAttribute("d", dT); coeur.setAttribute("d", dT);
    const fin = Tp[Tp.length - 1], avant = Tp[Tp.length - 2], a = Math.atan2(fin[1] - avant[1], fin[0] - avant[0]) * 180 / PI;
    const cx = fin[0] + (R.pavillon.r + 16) * cos(a * PI / 180), cy = fin[1] + (R.pavillon.r + 16) * sin(a * PI / 180);
    pav.setAttribute("transform", "translate(" + f2(cx) + " " + f2(cy) + ") rotate(" + f2(a - 90) + ")");
    // thermomètre
    const C = R.colonne;
    let niv = C.bas;
    if (u < C.cache) {
      const s = cl((u - C.montee[0]) / (C.montee[1] - C.montee[0]), 0, 1);
      niv = C.bas + (C.haut - C.bas) * (1 - Math.pow(1 - s, 3));
      if (s >= 1) niv += 0.5 * sin(2 * PI * (u - C.montee[1]) / 0.5) * Math.exp(-(u - C.montee[1]) / 0.6);
    }
    const yb = 440, yt = 104, y = yb - (yb - yt) * niv / 100;
    col.setAttribute("y", f2(y)); col.setAttribute("height", f2(yb - y + 10));
  };
})();
