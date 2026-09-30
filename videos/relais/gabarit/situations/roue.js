/* Animateur « roue » (garage). τ = FX.tau(t, mode). Avant : la roue tourne (540°/s), le sol défile, arcs de vitesse sur le
   pneu. Geste : l'étrier serre (petite secousse), la roue décélère (vitesse en p2o vers 0) en un tour et demi, gerbe
   d'étincelles au contact (tangentes au disque, dans le sens de rotation), arcs et sol qui ralentissent, arrêt net avec un
   léger rappel (la voiture pique du nez puis se repose). */
(function () {
  const REGLAGES = {
    centre: [300, 320], vitesse: 540, freinage: [0.28, 1.0], branches: 5,
    etincelles: { de: 0.3, a: 0.92, cadence: 0.07,
                  reglages: { n: 6, forme: "etincelle", couleur: "#EFA424", epaisseur: 7, vitesse: [420, 700], ouverture: 0.8, gravite: 1400, duree: 0.3, trainee: 0.075 } },
    secousse: { t: 0.3, amplitude: 5 }, rappel: { t: 1.0, amplitude: 4, duree: 0.3 }
  };
  const R = REGLAGES, C = R.centre, PI = Math.PI, NS = "http://www.w3.org/2000/svg", f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  for (let i = 0; i < R.branches; i++) {        // jante : cinq branches (trous sombres) et cinq écrous
    const a = i * 2 * PI / R.branches;
    const g = el($("ro-jante"), "g", { transform: "rotate(" + (a * 180 / PI) + " " + C[0] + " " + C[1] + ")" });
    el(g, "path", { d: "M" + (C[0] - 20) + " " + (C[1] - 50) + " Q " + C[0] + " " + (C[1] - 122) + " " + (C[0] + 20) + " " + (C[1] - 50) + " Q " + C[0] + " " + (C[1] - 62) + " " + (C[0] - 20) + " " + (C[1] - 50) + " Z", fill: "#262019" });
    el(g, "circle", { cx: C[0], cy: C[1] - 42, r: 5, fill: "#262019" });
  }
  const roue = $("ro-roue"), etrier = $("ro-etrier");
  const arcs = [0, 1, 2].map(() => el($("ro-arcs"), "path", {}));
  const tirets = [0, 1, 2, 3, 4].map(() => el($("ro-tirets"), "path", {}));
  const gerbes = [0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => FX.particules($("ro-fx"), Object.assign({}, R.etincelles.reglages, { graine: 21 + i * 7 })));
  const [f0, f1] = R.freinage, w0 = R.vitesse;
  function angle(T) {                           // angle intégré de la vitesse (freinage p2o : la vitesse tombe vite puis finit)
    if (T < f0) return w0 * T;
    const D = f1 - f0;
    if (T < f1) { const s = (T - f0) / D; return w0 * f0 + w0 * D * (s - s * s + s * s * s / 3); }
    return w0 * f0 + w0 * D / 3;
  }
  function vitesse(T) { if (T < f0) return w0; if (T < f1) { const s = (T - f0) / (f1 - f0); return w0 * (1 - s) * (1 - s); } return 0; }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode), a = angle(T), w = vitesse(T) / w0;
    let dy = 0;
    const S = R.secousse, P = R.rappel;
    if (T > S.t && T < S.t + 0.12) dy = S.amplitude * Math.sin(PI * (T - S.t) / 0.12);
    if (T > P.t && T < P.t + P.duree) dy += -P.amplitude * Math.sin(PI * (T - P.t) / P.duree);
    roue.setAttribute("transform", "translate(0 " + f2(dy) + ") rotate(" + f2(a % 360) + " " + C[0] + " " + C[1] + ")");
    etrier.setAttribute("transform", "translate(0 " + f2(dy) + ") rotate(-40 " + C[0] + " " + C[1] + ")" + (T > f0 && T < f1 + 0.05 ? " translate(0 3)" : ""));
    // arcs de vitesse sur le pneu (clairs sur le noir), longueur ∝ vitesse
    arcs.forEach(function (p, i) {
      const r = 138 + i * 12, L = w * (60 + 18 * i) * PI / 180, a0 = (a * PI / 180) + i * 2.1;
      if (w < 0.05) { p.setAttribute("d", ""); return; }
      p.setAttribute("d", "M" + f2(C[0] + r * Math.cos(a0 - L)) + " " + f2(C[1] + dy + r * Math.sin(a0 - L)) + " A" + r + " " + r + " 0 0 1 " + f2(C[0] + r * Math.cos(a0)) + " " + f2(C[1] + dy + r * Math.sin(a0)));
      p.setAttribute("opacity", (0.35 + 0.4 * w).toFixed(3));
    });
    // le sol défile vers la gauche à la vitesse du pneu (170 px de rayon)
    const dec = (angle(T) * PI / 180 * 170) % 130;
    tirets.forEach(function (p, i) {
      const x = 560 - ((i * 130 + dec) % 650);
      p.setAttribute("d", w > 0.02 || T < f1 ? "M" + f2(x) + " 520 H " + f2(x + 50 * (0.3 + 0.7 * w)) : "");
      p.setAttribute("opacity", (0.18 + 0.3 * w).toFixed(3));
    });
    // étincelles : une gerbe toutes les 70 ms au point de contact de l'étrier, tangente, dans le sens de rotation
    const E = R.etincelles, ac = -40 * PI / 180 - PI / 2, px = C[0] + 124 * Math.cos(ac), py = C[1] + dy + 124 * Math.sin(ac);
    gerbes.forEach(function (g, i) {
      const t0 = E.de + i * E.cadence;
      const v = t0 < E.a ? FX.fenetre(T, t0, E.reglages.duree) : -1;
      g(v, px, py, ac + PI / 2 + 0.25);
    });
  };
})();
