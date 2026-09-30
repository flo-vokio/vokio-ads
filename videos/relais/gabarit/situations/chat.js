/* Animateur « chat » (vétérinaire). τ = FX.tau(t, mode). La queue balaie en permanence (période 2,5 s, diviseur de 10 s) :
   chaque segment suit le précédent avec un retard (onde de la base à la pointe), amplitude croissante vers la pointe.
   Geste : Moka approche le nez de la gamelle (sio), renifle (deux petits à-coups), se détourne en relevant la tête (p3o),
   une oreille frémit, puis la tête retombe dans sa bouderie. Les yeux restent mi-clos. */
(function () {
  const REGLAGES = {
    cou: [352, 336],
    tete: [[-9, 7, 0], [0.12, 7, 0], [0.42, -13, -16, "sio"], [0.5, -10, -14, "sio"], [0.56, -13, -16, "sio"], [0.62, -11, -15, "sio"],
           [0.82, 12, 6, "p3o"], [1.25, 7, 0, "sio"], [9, 7, 0]],                   // [τ, rotation (°), avancée (px)]
    oreille: { t: 0.9, duree: 0.24, amplitude: 16 },
    queue: { base: [452, 494], segments: 7, longueur: 24, courbure: [2, -8, -18, -26, -30, -28, -22], amplitude: [3, 5, 7, 9, 11, 13, 15],
             periode: 2.5, retard: 0.55 },
    corps: { souffle: 1.6, periode: 2.5 }
  };
  const R = REGLAGES, PI = Math.PI, f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const tete = $("ca-tete"), oreille = $("ca-oreille"), queue = $("ca-queue"), corps = $("ca-corps");
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    const [r, av] = FX.cles(T, R.tete);
    const respire = Math.sin(2 * PI * t / R.corps.periode);
    tete.setAttribute("transform", "translate(" + f2(av) + " " + f2(respire * 1.2) + ") rotate(" + f2(r) + " " + R.cou[0] + " " + R.cou[1] + ")");
    corps.setAttribute("transform", "translate(0 " + f2(-respire * 0.8) + ") scale(1 " + (1 + 0.006 * respire).toFixed(4) + ")");
    const O = R.oreille, d = T - O.t;
    const oe = d > 0 && d < O.duree ? O.amplitude * Math.sin(PI * d / O.duree * 2) * (1 - d / O.duree) : 0;
    oreille.setAttribute("transform", "rotate(" + f2(oe) + " 356 256)");
    const Q = R.queue;
    let x = Q.base[0], y = Q.base[1], a = 0, dpath = "M" + f2(x) + " " + f2(y);
    for (let i = 0; i < Q.segments; i++) {
      a += (Q.courbure[i] + Q.amplitude[i] * Math.sin(2 * PI * t / Q.periode - i * Q.retard)) * PI / 180;
      const nx = x + Q.longueur * Math.cos(a), ny = y + Q.longueur * Math.sin(a);
      dpath += " Q" + f2(x + (nx - x) * 0.5 + 2 * Math.sin(a)) + " " + f2(y + (ny - y) * 0.5) + " " + f2(nx) + " " + f2(ny);
      x = nx; y = ny;
    }
    queue.setAttribute("d", dpath);
  };
})();
