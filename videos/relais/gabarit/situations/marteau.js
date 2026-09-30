/* Animateur « marteau » (rénovation). τ = FX.tau(t, mode). Avant : marteau levé qui respire (léger va-et-vient), clou
   entier. Geste : élan (le marteau remonte, lent, sio), frappe (p3i, 3 images), impact : le clou s'enfonce d'un cran, la
   planche vibre, bouffée de poussière, le marteau rebondit (petit recul p2o) ; deuxième coup plus court ; le marteau se
   relève. L'angle d'impact suit la tête du clou qui descend. */
(function () {
  const REGLAGES = {
    pivot: [60, 266], rayon_tete: 277, cran: [0, 0.42, 0.8], course: 60,
    // [τ, angle (°, négatif = levé)] — l'impact exact est recalculé sur la tête du clou (voir impacts)
    angle: [[-9, -30], [0, -30], [0.24, -58, "sio"], [0.36, "impact0", "p3i"], [0.46, -12, "p2o"], [0.64, -46, "sio"], [0.72, "impact1", "p3i"],
            [0.82, -10, "p2o"], [1.2, -34, "sio"], [9, -34]],
    impacts: [0.36, 0.72], respire: { amplitude: 3, periode: 2.5 },
    traits: { avant: 0.0, duree: 0.07, reglages: { n: 3, longueurs: [56, 76, 46], ecart: 20, recul: 14, epaisseur: 6 } },
    poussiere: { n: 7, forme: "poussiere", couleur: "#B3AB9E", taille: [8, 14], vitesse: [90, 210], ouverture: 2.8, gravite: 90, duree: 0.55, graine: 17 }
  };
  const R = REGLAGES, PI = Math.PI, f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const marteau = $("ma-marteau"), clou = $("ma-clou"), planche = $("ma-planche");
  const traits = FX.traits($("ma-fx"), R.traits.reglages);
  const pouss = R.impacts.map((t0, i) => FX.particules($("ma-fx"), Object.assign({}, R.poussiere, { graine: R.poussiere.graine + i * 11 })));
  const angleImpact = (k) => Math.asin(R.cran[k + 1] * R.course / R.rayon_tete) * 180 / PI;   // la tête suit le clou
  const CL = R.angle.map((c) => c.map((v) => (v === "impact0" ? angleImpact(0) : v === "impact1" ? angleImpact(1) : v)));
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    let [a] = FX.cles(T, CL);
    if (T < 0.05) a += R.respire.amplitude * Math.sin(2 * PI * t / R.respire.periode);
    marteau.setAttribute("transform", "rotate(" + f2(a) + " " + R.pivot[0] + " " + R.pivot[1] + ")");
    let prof = R.cran[0];
    R.impacts.forEach((t0, i) => { if (T >= t0) prof = R.cran[i + 1]; });
    clou.setAttribute("transform", "translate(0 " + f2(prof * R.course) + ")");
    // la planche vibre après chaque impact ; poussière au pied du clou ; traits sur la tête juste avant le choc
    let vib = 0;
    R.impacts.forEach(function (t0, i) {
      const d = T - t0;
      if (d >= 0 && d < 0.18) vib += 3.5 * Math.sin(d * 2 * PI / 0.066) * (1 - d / 0.18);
      pouss[i](FX.fenetre(T, t0, R.poussiere.duree), 330, 418, -PI / 2);
    });
    planche.setAttribute("transform", "translate(0 " + f2(vib) + ")");
    const k = R.impacts.findIndex((t0) => T >= t0 - R.traits.avant - R.traits.duree && T <= t0);
    const ar = a * PI / 180, hx = R.pivot[0] + (330 - R.pivot[0]) * Math.cos(ar) - (290 - R.pivot[1]) * Math.sin(ar),
          hy = R.pivot[1] + (330 - R.pivot[0]) * Math.sin(ar) + (290 - R.pivot[1]) * Math.cos(ar);
    traits(k >= 0 ? FX.fenetre(T, R.impacts[k] - R.traits.avant - R.traits.duree, R.traits.duree) : -1, hx, hy, ar + PI / 2);
  };
})();
