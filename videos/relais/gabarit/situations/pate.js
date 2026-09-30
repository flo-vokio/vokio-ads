/* Animateur « pâte » (boulangerie). τ = FX.tau(t, mode). Avant : la pâte étalée respire à peine, le coupe-pâte attend.
   Geste : le coupe-pâte glisse sous le bord (sio), soulève la moitié droite, qui BASCULE autour de la pliure (le coupe-pâte
   suit sa pointe puis la lâche) et retombe en accélérant (p2i) ; réception : la pâte s'écrase (épaisseur −22 %, étalement),
   puis se regonfle ; bouffée de farine par les côtés ; le coupe-pâte se retire. */
(function () {
  const REGLAGES = {
    pli: [236, 432], epaisseur: 40, longueur: 150,
    rabat: [[-9, 0], [0.28, 0], [0.46, -118, "sio"], [0.62, -180, "p2i"], [9, -180]],
    corne: [[-9, 470, 412, 16], [0.1, 470, 412, 16], [0.28, 482, 470, 6, "sio"], [0.46, 270, 372, 52, "sio"], [0.56, 330, 380, 30, "p2o"],
            [0.95, 470, 412, 16, "sio"], [9, 470, 412, 16]],   // [τ, x, y, angle] : le coupe-pâte pointe vers la gauche (lame sous la pâte)
    reception: 0.62, ecrase: 0.22, ecrase_duree: 0.22,
    farine: { n: 10, forme: "poussiere", couleur: "#FFFFFF", contour: "#B3AB9E", epaisseur: 2.5, taille: [10, 17], vitesse: [80, 200], ouverture: 1.3, gravite: 70, duree: 0.7, graine: 23 }
  };
  const R = REGLAGES, PI = Math.PI, f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const gauche = $("pa-gauche"), rabat = $("pa-rabat"), corne = $("pa-corne");
  const farineG = FX.particules($("pa-fx"), R.farine), farineD = FX.particules($("pa-fx"), Object.assign({}, R.farine, { graine: 29 }));
  function bande(x0, x1, y0, e, bombe, rondG, rondD) {   // une épaisseur de pâte : dessus bombé, bords arrondis (ou droits à la pliure)
    const r = e * 0.5, g = rondG === false ? 0 : 1, d = rondD === false ? 0 : 1;
    const xa = x0 + r * g, xb = x1 - r * d;
    let p = "M" + f2(xa) + " " + f2(y0 + e);
    p += g ? " C" + f2(x0 - r * 0.6) + " " + f2(y0 + e) + " " + f2(x0 - r * 0.6) + " " + f2(y0) + " " + f2(xa) + " " + f2(y0) : " L" + f2(x0) + " " + f2(y0);
    p += " C" + f2(xa + (xb - xa) * 0.35) + " " + f2(y0 - bombe) + " " + f2(xa + (xb - xa) * 0.65) + " " + f2(y0 - bombe) + " " + f2(xb) + " " + f2(y0);
    p += d ? " C" + f2(x1 + r * 0.6) + " " + f2(y0) + " " + f2(x1 + r * 0.6) + " " + f2(y0 + e) + " " + f2(xb) + " " + f2(y0 + e) : " L" + f2(x1) + " " + f2(y0 + e);
    return p + " Z";
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode), P = R.pli, E = R.epaisseur, L = R.longueur;
    const [phi] = FX.cles(T, R.rabat);
    // écrasement à la réception : la pâte perd de l'épaisseur et s'étale un peu, puis revient
    const d = T - R.reception, q = d >= 0 && d < R.ecrase_duree ? Math.sin(PI * d / R.ecrase_duree) * (1 - 0.3 * d / R.ecrase_duree) : 0;
    const e = E * (1 - R.ecrase * q), etale = 10 * q, respire = 1.2 * Math.sin(2 * PI * t / 2.5);
    const plie = phi < -0.01;
    if (!plie) {                                  // étalée : UNE seule bande, d'un seul tenant
      gauche.setAttribute("d", bande(P[0] - L, P[0] + L, 470 - E, E, 10 + respire));
      rabat.setAttribute("d", "");
    } else {
      gauche.setAttribute("d", bande(P[0] - L - etale, P[0] + (T >= R.reception ? etale * 0.5 : 0), 470 - e, e, 6 + respire, true, T >= R.reception));
      // le rabat : même bande, qui tourne autour du haut de la pliure ; posé, il s'écrase avec le reste
      const e2 = T >= R.reception ? e : E;
      rabat.setAttribute("d", bande(P[0], P[0] + L + (T >= R.reception ? etale : 0), 470 - e2, e2, 6 + respire, T >= R.reception, true));
    }
    // pâte molle : pendant la bascule, le bout du rabat traîne derrière (cisaillement autour de la pliure, follow-through)
    const sv = T > 0.28 && T < R.reception ? Math.sin(PI * (T - 0.28) / (R.reception - 0.28)) : 0;
    const hy = 470 - (T >= R.reception ? e : E);
    rabat.setAttribute("transform", "rotate(" + f2(phi) + " " + P[0] + " " + f2(hy) + ") translate(" + P[0] + " " + f2(hy) + ") skewY(" + f2(14 * sv) + ") translate(" + (-P[0]) + " " + f2(-hy) + ")");
    const [cx, cy, ca] = FX.cles(T, R.corne);
    corne.setAttribute("transform", "translate(" + f2(cx) + " " + f2(cy) + ") rotate(" + f2(ca) + ") scale(-1 1)");
    farineG(FX.fenetre(T, R.reception, R.farine.duree), P[0] - L - 6, 440, -PI * 0.85);
    farineD(FX.fenetre(T, R.reception, R.farine.duree), P[0] + 6, 400, -PI * 0.25);
  };
})();
