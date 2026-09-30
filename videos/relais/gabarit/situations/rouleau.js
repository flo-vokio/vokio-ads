/* Animateur « rouleau » (boulangerie). τ = FX.tau(t, mode). Avant : la boule de pâte respire à peine, le rouleau attend
   au-dessus. Geste : élan (le rouleau monte, sio), chute (p3i), IMPACT : la pâte s'écrase (hauteur −55 %, largeur ×1,5 :
   volume conservé), gerbes de farine des deux côtés ; le rouleau roule vers la droite (ses veines défilent) en étalant ;
   il se relève, la pâte se rétracte à moitié et un pli se dessine (elle se replie). */
(function () {
  const REGLAGES = {
    centre: 250, base: 470, boule: [200, 124], ecrasee: [310, 54], etalee: [340, 44], repliee: [250, 78],
    pate: [[-9, 0], [0.36, 0], [0.44, 1, "p3o"], [0.72, 2, "sio"], [1.05, 3, "sio"], [9, 3]],      // 0 boule · 1 écrasée · 2 étalée · 3 repliée
    rouleau: [[-9, 250, -30], [0.1, 250, -30], [0.26, 250, -92, "sio"], [0.36, 250, 0, "p3i"], [0.72, 280, 0, "sio"], [0.95, 280, -120, "sio"], [9, 280, -120]],
    impact: 0.36,
    farine: { n: 12, forme: "poussiere", couleur: "#FFFFFF", contour: "#B3AB9E", epaisseur: 2.5, taille: [16, 26], vitesse: [140, 300], ouverture: 1.1, gravite: 60, duree: 0.8, graine: 41 }
  };
  const R = REGLAGES, PI = Math.PI, f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const pate = $("ro-pate"), pli = $("ro-pli"), rouleau = $("ro-rouleau"), veines = $("ro-veines");
  const NS = "http://www.w3.org/2000/svg";
  const V = [-110, -60, -10, 40, 90].map(() => { const p = document.createElementNS(NS, "path"); veines.appendChild(p); return p; });
  const fG = FX.particules($("ro-fx"), R.farine), fD = FX.particules($("ro-fx"), Object.assign({}, R.farine, { graine: 47 }));
  const F = [R.boule, R.ecrasee, R.etalee, R.repliee];
  function forme(k) { const i = Math.min(2, Math.floor(k)), s = k - i; return [F[i][0] + (F[i + 1][0] - F[i][0]) * s, F[i][1] + (F[i + 1][1] - F[i][1]) * s]; }
  function dome(cx, w, h) {                       // la pâte : dôme posé, bas légèrement renflé
    const b = R.base, g = cx - w / 2, d = cx + w / 2;
    return "M" + f2(g) + " " + b + " C" + f2(g - w * 0.04) + " " + f2(b - h * 0.9) + " " + f2(cx - w * 0.3) + " " + f2(b - h * 1.02) + " " + f2(cx) + " " + f2(b - h) +
      " C" + f2(cx + w * 0.3) + " " + f2(b - h * 1.02) + " " + f2(d + w * 0.04) + " " + f2(b - h * 0.9) + " " + f2(d) + " " + b + " Z";
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    const [k] = FX.cles(T, R.pate), [w, h0] = forme(k);
    const h = h0 * (1 + 0.012 * Math.sin(2 * PI * t / 2.5));
    const cx = R.centre + (k > 1 ? Math.min(1, k - 1) * 30 : 0);
    pate.setAttribute("d", dome(cx, w, h));
    // le pli : n'apparaît qu'en se repliant
    const pl = Math.max(0, Math.min(1, k - 2));
    pli.setAttribute("d", pl > 0.02 ? "M" + f2(cx - w * 0.3) + " " + f2(R.base - h * 0.62) + " Q" + f2(cx) + " " + f2(R.base - h * (0.62 + 0.25 * pl)) + " " + f2(cx + w * 0.28 * pl) + " " + f2(R.base - h * 0.7) : "");
    // le rouleau : posé sur la pâte (hauteur courante) ; ty = décalage au-dessus
    let [rx, ty] = FX.cles(T, R.rouleau);
    const ry = R.base - (T >= R.impact && T < 0.95 ? h : Math.max(h, h0)) - 30 + ty;
    const rot = (rx - 250) / 30 * 180 / PI;        // roule sans glisser (rayon 30)
    rouleau.setAttribute("transform", "translate(" + f2(rx) + " " + f2(ry) + ")");
    V.forEach(function (p, i) {                   // veines du bois qui défilent quand il roule
      const x = ((-110 + i * 50 - rot * 30 * PI / 180) % 250 + 375) % 250 - 125;
      p.setAttribute("d", "M" + f2(x) + " -14 Q" + f2(x + 8) + " 0 " + f2(x) + " 14");
    });
    fG(FX.fenetre(T, R.impact, R.farine.duree), cx - w / 2 - 6, R.base - 12, -PI * 0.88);
    fD(FX.fenetre(T, R.impact, R.farine.duree), cx + w / 2 + 6, R.base - 12, -PI * 0.12);
  };
})();
