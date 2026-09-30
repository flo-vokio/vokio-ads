/* Animateur « disjoncteur » (électricien). τ = FX.tau(t, mode). Avant : tout est armé, l'ampoule brille (rayons qui
   respirent). Geste : le 3e module tremble (anticipation), le levier SAUTE vers le bas en 2 images (p3i) avec une étincelle
   (FX.eclat : une forme neuve à chaque image) et des traits ; l'ampoule vacille (deux clignements) et s'éteint ; puis le
   levier se rebascule tout seul, plus lentement (sio), la lumière revient en un clignement. */
(function () {
  const REGLAGES = {
    modules: [150, 240, 330, 420], saute: 2, haut: 262, bas: 350, largeur: 72,
    levier: [[-9, 0], [0.16, 0], [0.33, 0], [0.40, 1, "p3i"], [0.92, 1], [1.18, 0, "sio"], [9, 0]],   // 0 armé, 1 déclenché
    tremble: { de: 0.18, a: 0.33, amplitude: 2.2 },
    lumiere: [[0.34, 0.2], [0.36, 0.9], [0.39, 0.1], [0.42, 0.55], [0.46, 0]],                          // clignements à l'extinction
    retour: [[1.16, 0], [1.19, 0.8], [1.22, 0.3], [1.27, 1]],
    eclat: { de: 0.36, duree: 0.24, reglages: { branches: 7, rayon: 80 } },
    traits: { de: 0.35, duree: 0.1, reglages: { n: 3, longueurs: [40, 56, 34], ecart: 18, recul: 16, epaisseur: 6 } },
    etincelles: { n: 8, forme: "etincelle", couleur: "#EFA424", epaisseur: 6, vitesse: [320, 560], ouverture: 2.6, gravite: 900, duree: 0.4, graine: 9 }
  };
  const R = REGLAGES, NS = "http://www.w3.org/2000/svg", PI = Math.PI, f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const leviers = R.modules.map(function (x, i) {
    const g = el($("dj-modules"), "g", {});
    el(g, "rect", { x: x - R.largeur / 2, y: 248, width: R.largeur, height: 164, rx: 10, fill: "#F4F1E8", stroke: "#262019", "stroke-width": 6 });
    el(g, "rect", { x: x - 16, y: 262, width: 32, height: 120, rx: 8, fill: "#262019", opacity: 0.14 });
    const lv = el(g, "rect", { x: x - 14, y: R.haut, width: 28, height: 34, rx: 7, fill: "#262019" });
    el(g, "path", { d: "M" + (x - 22) + " 396 H " + (x + 22), stroke: "#262019", "stroke-width": 5, "stroke-linecap": "round", opacity: 0.5 });
    return { g: g, lv: lv, x: x };
  });
  const verre = $("dj-verre"), rayons = $("dj-rayons");
  const eclat = FX.eclat($("dj-fx"), R.eclat.reglages), traits = FX.traits($("dj-fx"), R.traits.reglages), etinc = FX.particules($("dj-fx"), R.etincelles);
  function palier(T, P) { let v = null; P.forEach((q) => { if (T >= q[0]) v = q[1]; }); return v; }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    const [e] = FX.cles(T, R.levier), L = leviers[R.saute];
    let dx = 0;
    if (T > R.tremble.de && T < R.tremble.a) dx = R.tremble.amplitude * (Math.round(t * 30) % 2 ? 1 : -1);
    L.lv.setAttribute("y", f2(R.haut + (R.bas - R.haut) * e));
    L.g.setAttribute("transform", "translate(" + dx + " 0)");
    // lumière : 1 allumée, 0 éteinte ; clignements à l'extinction et au retour
    let lum = 1;
    if (T >= 0.34 && T < 1.16) lum = palier(T, R.lumiere);
    else if (T >= 1.16 && T < 1.27) lum = palier(T, R.retour);
    const souffle = 1 + 0.08 * Math.sin(2 * PI * t / 1.25);
    verre.setAttribute("fill", lum > 0.5 ? "#F8D69B" : lum > 0.05 ? "#F4E6C4" : "#F4F1E8");
    rayons.setAttribute("opacity", (lum * 1).toFixed(3));
    rayons.setAttribute("transform", "translate(300 110) scale(" + (souffle * (0.8 + 0.2 * lum)).toFixed(4) + ") translate(-300 -110)");
    const px = L.x, py = R.haut + 60;
    eclat(FX.fenetre(T, R.eclat.de, R.eclat.duree), px + 30, py, t);
    etinc(FX.fenetre(T, R.eclat.de, R.etincelles.duree), px + 30, py, -PI / 4);
    traits(FX.fenetre(T, R.traits.de, R.traits.duree), px, R.bas + 20, PI / 2);
  };
})();
