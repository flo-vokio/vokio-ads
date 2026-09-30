/* Animateur « chaudière » (chauffagiste). τ = FX.tau(t, mode). Avant : quatre flammes bleues vivantes (FX.flamme : tracé
   déformé), aiguille stable qui frémit. Geste : la flamme TOUSSE (chute, reprise, chute, reprise plus faible), s'éteint
   (p2i) dans une petite bouffée de fumée ; l'aiguille tremble pendant la toux puis retombe à zéro, en retard sur la flamme. */
(function () {
  const REGLAGES = {
    flammes: [[240, 58], [277, 76], [314, 70], [350, 56]], base: 470,
    couleurs: { couleur: "#5B8DB8", coeur: "#CFE0EE" },
    intensite: [[-9, 1], [0.22, 1], [0.29, 0.3, "p2o"], [0.36, 0.95, "p2o"], [0.44, 0.22, "p2o"], [0.52, 0.7, "p2o"],
                [0.62, 0.12, "p2o"], [0.68, 0.32], [0.78, 0, "p2i"], [9, 0]],
    aiguille: [[-9, 22], [0.70, 22], [1.08, -118, "sio"], [1.2, -114, "sio"], [9, -114]],
    tremble: { de: 0.26, a: 0.72, amplitude: 4 },
    fumee: { de: 0.76, reglages: { n: 6, forme: "poussiere", couleur: "#B3AB9E", taille: [8, 14], vitesse: [50, 100], ouverture: 1.4, gravite: -120, duree: 0.8, graine: 13 } }
  };
  const R = REGLAGES, PI = Math.PI, NS = "http://www.w3.org/2000/svg", f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const C = [295, 214];
  // graduations (−135° à +135°) et zone rouge (fin d'échelle)
  for (let i = 0; i <= 8; i++) {
    const a = (-135 + i * 270 / 8 - 90) * PI / 180, r0 = i % 2 ? 52 : 46;
    const p = document.createElementNS(NS, "path");
    p.setAttribute("d", "M" + f2(C[0] + r0 * Math.cos(a)) + " " + f2(C[1] + r0 * Math.sin(a)) + " L" + f2(C[0] + 60 * Math.cos(a)) + " " + f2(C[1] + 60 * Math.sin(a)));
    $("ch-graduations").appendChild(p);
  }
  const a0 = (100 - 90) * PI / 180, a1 = (135 - 90) * PI / 180;
  $("ch-rouge").setAttribute("d", "M" + f2(C[0] + 56 * Math.cos(a0)) + " " + f2(C[1] + 56 * Math.sin(a0)) + " A56 56 0 0 1 " + f2(C[0] + 56 * Math.cos(a1)) + " " + f2(C[1] + 56 * Math.sin(a1)));
  const groupes = R.flammes.map(function (f, i) {
    const g = document.createElementNS(NS, "g"); $("ch-flammes").appendChild(g);
    return { g: g, x: f[0], maj: FX.flamme(g, Object.assign({ x: 0, base: 0, h: f[1], w: 15, phase: i * 0.27, flammeche: null,
      ondulation: { periode: 0.5, amplitude: 0.34, longueur: 0.85 }, torsion: [[0.625, 0.18], [0.4, 0.08]] }, R.couleurs)) };
  });
  const aiguille = $("ch-aiguille"), fumee = FX.particules($("ch-fx"), R.fumee.reglages);
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    const [k] = FX.cles(T, R.intensite);
    groupes.forEach(function (o, i) {
      const ki = Math.max(0, Math.min(1.05, k * (1 + 0.08 * Math.sin(i * 1.7 + T * 9))));     // les flammes ne toussent pas d'un bloc
      o.g.setAttribute("transform", "translate(" + o.x + " " + R.base + ") scale(" + (0.6 + 0.4 * ki).toFixed(4) + " " + ki.toFixed(4) + ")");
      o.g.setAttribute("opacity", ki < 0.02 ? "0" : "1");
      o.maj(t, 0);
    });
    let [a] = FX.cles(T, R.aiguille);
    if (T > R.tremble.de && T < R.tremble.a) a += R.tremble.amplitude * (Math.round(t * 30) % 2 ? 1 : -1) * (0.5 + 0.5 * Math.sin(PI * (T - R.tremble.de) / (R.tremble.a - R.tremble.de)));
    else if (T < R.tremble.de) a += 0.8 * Math.sin(2 * PI * t / 0.625);
    aiguille.setAttribute("transform", "rotate(" + a.toFixed(2) + " " + C[0] + " " + C[1] + ")");
    fumee(FX.fenetre(T, R.fumee.de, R.fumee.reglages.duree), 295, 440, -PI / 2);
  };
})();
