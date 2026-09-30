/* Animateur « porte » (serrurier). τ = FX.tau(t, mode). Avant le geste : porte entrouverte qui respire au vent, trousseau
   presque immobile. Geste : courant d'air (trois souffles qui traversent), petite ouverture d'élan, CLAQUE (accélération
   jusqu'au choc, p3i), choc : le chambranle tremble, traits sur le bord libre, poussière au pied ; le trousseau part en
   pendule amorti (en retard sur la porte : follow-through). */
(function () {
  const REGLAGES = {
    gond: 162, haut: 52, bas: 566, largeur: 280, perspective: 30,
    porte: [[-9, 38], [0.18, 38], [0.34, 44, "sio"], [0.56, 0, "p3i"], [9, 0]],     // angle d'ouverture (degrés)
    choc: 0.56, respire: { amplitude: 1.6, periode: 2.5 },
    serrure: [0.84, 0.5], echelle_serrure: 1.35,                                                          // (u, v) sur le battant
    trousseau: { amplitude: 46, periode: 0.62, amorti: 1.5, repos: 3, periode_repos: 2.5 },
    tremble: { duree: 0.2, amplitude: 5 },
    air: { de: 0.02, duree: 0.42, lignes: [[520, 170, 0], [560, 300, 0.06], [530, 430, 0.12]] },
    traits: { duree: 0.1, reglages: { n: 3, longueurs: [60, 84, 50], ecart: 26, recul: 10, epaisseur: 6 } },
    poussiere: { n: 6, forme: "poussiere", couleur: "#262019", taille: [5, 9], vitesse: [60, 140], ouverture: 2.4, gravite: -60, duree: 0.6, graine: 5 }
  };
  const R = REGLAGES, PI = Math.PI, f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const battant = $("po-battant"), p1 = $("po-panneau1"), p2 = $("po-panneau2"), serr = $("po-serrure"), trou = $("po-trousseau"), cadre = $("po-cadre");
  const airs = R.air.lignes.map(() => { const p = document.createElementNS("http://www.w3.org/2000/svg", "path"); $("po-air").appendChild(p); return p; });
  const traits = FX.traits($("po-fx"), R.traits.reglages), pouss = FX.particules($("po-fx"), R.poussiere);
  function P(phi, u, v) {                        // point (u, v) du battant ouvert de phi (degrés), vu de face avec perspective
    const c = Math.cos(phi * PI / 180), s = Math.sin(phi * PI / 180);
    const x = R.gond + u * R.largeur * c, yt = R.haut - u * R.perspective * s, yb = R.bas + u * R.perspective * s;
    return [x, yt + v * (yb - yt)];
  }
  const poly = (phi, pts) => "M" + pts.map((q) => { const p = P(phi, q[0], q[1]); return f2(p[0]) + " " + f2(p[1]); }).join(" L") + " Z";
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    let [phi] = FX.cles(T, R.porte);
    if (T < R.choc) phi += R.respire.amplitude * Math.sin(2 * PI * t / R.respire.periode) * (T < 0.18 ? 1 : Math.max(0, 1 - (T - 0.18) / 0.1));
    battant.setAttribute("d", poly(phi, [[0, 0], [1, 0], [1, 1], [0, 1]]));
    p1.setAttribute("d", poly(phi, [[0.16, 0.07], [0.84, 0.07], [0.84, 0.42], [0.16, 0.42]]));
    p2.setAttribute("d", poly(phi, [[0.16, 0.6], [0.84, 0.6], [0.84, 0.93], [0.16, 0.93]]));
    const S = P(phi, R.serrure[0], R.serrure[1]), sx = Math.cos(phi * PI / 180);
    serr.setAttribute("transform", "translate(" + f2(S[0]) + " " + f2(S[1]) + ") scale(" + (R.echelle_serrure * (0.55 + 0.45 * sx)).toFixed(4) + " " + R.echelle_serrure + ")");
    // trousseau : repos (léger balancement) puis pendule amorti au choc, en retard d'une image sur la porte
    const K = R.trousseau;
    let a = K.repos * Math.sin(2 * PI * t / K.periode_repos) * (T < R.choc ? 1 : Math.exp(-(T - R.choc) * 3));
    if (T >= R.choc) a += FX.pendule(T, R.choc + 0.03, -K.amplitude, K.periode, K.amorti) * Math.min(1, (T - R.choc) / 0.06);
    if (T > 0.34 && T < R.choc) a += 14 * (T - 0.34) / (R.choc - 0.34);      // la porte accélère : le trousseau traîne derrière
    trou.setAttribute("transform", "rotate(" + a.toFixed(2) + " 0 60)");
    // choc : le chambranle tremble, traits le long du bord libre, poussière au pied
    const ch = T - R.choc;
    const tr = ch >= 0 && ch < R.tremble.duree ? R.tremble.amplitude * Math.sin(ch * 2 * PI / 0.066) * (1 - ch / R.tremble.duree) : 0;
    cadre.setAttribute("transform", "translate(" + f2(tr) + " 0)");
    const bord = P(phi, 1, 0.5);
    traits(FX.fenetre(T, R.choc - 0.07, R.traits.duree), bord[0], bord[1], PI);
    pouss(FX.fenetre(T, R.choc, R.poussiere.duree), R.gond + R.largeur, R.bas - 4, -PI / 2);
    // courant d'air : trois souffles ondulés qui traversent de droite à gauche, dessinés puis effacés
    const A = R.air;
    airs.forEach(function (p, i) {
      const L = A.lignes[i], v = (T - A.de - L[2]) / A.duree;
      if (v < 0 || v > 1) { p.setAttribute("d", ""); return; }
      const x0 = L[0] - 360 * v, lg = 150 * Math.sin(PI * v), y = L[1];
      let d = "";
      for (let k = 0; k <= 12; k++) { const x = x0 + lg * k / 12, yy = y + 9 * Math.sin(k / 12 * 2 * PI + v * 6); d += (k ? " L" : "M") + f2(x) + " " + f2(yy); }
      p.setAttribute("d", d);
    });
  };
})();
