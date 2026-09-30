/* Animateur « clé » (plombier). SITUATION_ANIM(t, periode, mode) ; temps du geste τ = FX.tau(t, mode) : la fin de la boucle
   montre l'avant du geste (gouttes régulières, clé en prise), qui rejoint l'image 0 sans saut.
   Geste : anticipation (la clé recule de 5°, l'écrou ne bouge pas : le jeu), serrage horaire de 60° (l'écrou tourne avec la
   clé ; 60° = un hexagone identique), léger dépassement puis blocage (l'écrou est serré : petit tremblement de l'effort),
   traits de vitesse au bout du manche au plus vite du coup. Gouttes : elles perlent, se détachent (étirées), tombent en
   accélérant, éclaboussent la flaque ; la dernière part pendant le serrage, la suivante perle à peine et se résorbe. */
(function () {
  const REGLAGES = {
    centre: [380, 300], point_fuite: [392, 403], sol: 548,
    cle: [[-9, 0, 0], [0.10, 0, 0], [0.28, -5, 0, "sio"], [0.95, 63, 60, "sio"], [1.08, 60, 60, "p2o"], [2.4, 60, 60], [9, 60, 60]],
    tremble: { de: 0.95, a: 1.2, amplitude: 0.9, periode: 0.0667 },
    gouttes: { periode: 1.25, derniere: 0.45, croissance: 0.9, rayon: 20, gravite: 2400 },
    arretee: { de: 0.98, a: 1.9, rayon: 9, point: [380, 371] },   // sous l'écrou, une fois la mâchoire passée
    traits: { u: 0.52, duree: 0.1, reglages: { n: 3, longueurs: [60, 80, 50], ecart: 18, recul: 16, epaisseur: 6 } },
    eclabousse: { n: 5, forme: "goutte", couleur: "#EFA424", contour: "#262019", epaisseur: 2.5, taille: [5.5, 8.5], vitesse: [140, 260], ouverture: 1.6, gravite: 1500, duree: 0.34, graine: 11 }
  };
  const R = REGLAGES, C = R.centre, PI = Math.PI;
  const cle = document.getElementById("cl-cle"), ecrou = document.getElementById("cl-ecrou");
  const gG = document.getElementById("cl-gouttes"), flaque = document.getElementById("cl-flaque-p");
  const NS = "http://www.w3.org/2000/svg";
  const goutte = document.createElementNS(NS, "path"); goutte.setAttribute("fill", "#EFA424"); goutte.setAttribute("stroke", "#262019"); goutte.setAttribute("stroke-width", "3"); gG.appendChild(goutte);
  const traits = FX.traits(document.getElementById("cl-traits"), R.traits.reglages);
  const eclab = FX.particules(gG, R.eclabousse);
  const f2 = (v) => v.toFixed(2);
  function larme(x, y, r, etire) {           // goutte pendue (etire = 0) ou en chute (etire > 0) : tête ronde en bas, pointe en haut
    const h = r * (1.5 + etire);
    return "M" + f2(x) + " " + f2(y - h - r) + " C" + f2(x + r * 0.35) + " " + f2(y - h * 0.6 - r) + " " + f2(x + r) + " " + f2(y - r * 0.6) + " " + f2(x + r) + " " + f2(y) +
      " A" + f2(r) + " " + f2(r) + " 0 0 1 " + f2(x - r) + " " + f2(y) + " C" + f2(x - r) + " " + f2(y - r * 0.6) + " " + f2(x - r * 0.35) + " " + f2(y - h * 0.6 - r) + " " + f2(x) + " " + f2(y - h - r) + " Z";
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    let [a, n] = FX.cles(T, R.cle);
    const tr = R.tremble;
    if (T > tr.de && T < tr.a) a += tr.amplitude * Math.sin(2 * PI * (T - tr.de) / tr.periode) * (1 - (T - tr.de) / (tr.a - tr.de));
    cle.setAttribute("transform", "rotate(" + a.toFixed(3) + " " + C[0] + " " + C[1] + ")");
    ecrou.setAttribute("transform", "rotate(" + Math.max(0, n).toFixed(3) + " " + C[0] + " " + C[1] + ")");
    // traits : au bout du manche (qui remonte : rotation horaire, manche à gauche)
    const ang = a * PI / 180, bx = C[0] + (44 - C[0]) * Math.cos(ang), by = C[1] + (44 - C[0]) * Math.sin(ang);
    traits(FX.fenetre(T, R.traits.u, R.traits.duree), bx, by, ang - PI / 2);
    // gouttes
    const G = R.gouttes, P = R.point_fuite;
    let d = "", impact = -9;
    const k = Math.floor((T - G.derniere) / G.periode), rel = G.derniere + Math.min(0, k) * G.periode;   // dernier lâcher passé (≤ la dernière)
    const prochain = rel + G.periode;
    const chute = Math.sqrt(2 * (R.sol - P[1]) / G.gravite);
    if (T >= rel && T < rel + chute) {                                 // en chute
      const s = T - rel, y = P[1] + 0.5 * G.gravite * s * s, v = G.gravite * s;
      d = larme(P[0], y, G.rayon * 0.9, Math.min(1.6, v / 900));
    }
    if (T - rel >= chute) impact = T - rel - chute;
    if (prochain <= G.derniere + 1e-6 && T > prochain - G.croissance) {  // la suivante perle
      const w = (T - (prochain - G.croissance)) / G.croissance, r = G.rayon * Math.pow(w, 0.6);
      d += (d ? " " : "") + larme(P[0], P[1] + r * 0.8 + w * 6, r, 0.2 * w);
    }
    const A = R.arretee;                                              // après le serrage : une perle qui se résorbe
    if (T > A.de && T < A.a) { const w = (T - A.de) / (A.a - A.de), r = A.rayon * Math.sin(PI * w); if (r > 0.4) d += " " + larme(A.point[0], A.point[1] + r * 0.8, r, 0); }
    goutte.setAttribute("d", d);
    eclab(FX.fenetre(impact, 0, R.eclabousse.duree), P[0], R.sol - 2, -PI / 2);
    // flaque : s'élargit à chaque impact (onde), revient au repos
    const o = impact >= 0 && impact < 0.5 ? Math.sin(PI * Math.min(1, impact / 0.5)) : 0;
    const rx = 58 + 16 * o, ry = 7 + 2 * o;
    flaque.setAttribute("d", "M" + f2(P[0] - rx) + " " + R.sol + " a" + f2(rx) + " " + f2(ry) + " 0 1 0 " + f2(2 * rx) + " 0 a" + f2(rx) + " " + f2(ry) + " 0 1 0 " + f2(-2 * rx) + " 0 Z");
  };
})();
