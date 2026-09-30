/* Animateur de la situation « poêle » (restaurant). Appelé à chaque image par le gabarit : SITUATION_ANIM(t, periode, mode).
   Fonction pure du temps, périodique : la boucle de 10 s se raccorde seule (10 / 1,25 = 8 gestes).
   Principes : anticipation (la poêle recule avant le coup), coup sec (power2.out) marqué de TRAITS DE VITESSE sur 3 images,
   aliments décalés (overlap), arcs balistiques, un tour sur eux-mêmes, SMEAR au décollage (étirés le long de la vitesse sur
   3 images, puis étirement proportionnel à la vitesse), écrasement à l'atterrissage (base fixe), poêle qui encaisse la
   réception, flammes au tracé vivant (lib/fx.js : ondes qui montent, pointe qui se tord, flammèches) ravivées par le coup.
   RÉGLAGES : tout ce qu'une autre situation voudra changer est dans l'objet ci-dessous. */
(function () {
  const REGLAGES = {
    pivot: [96, 318],                               // la main (bout du manche)
    // clés de la poêle : [u, tx, ty, rotation (degrés, + = pointe vers le bas), easing du segment qui y mène]
    cles: [[0, 0, 0, 0], [0.14, 0, 0, 0, "sio"], [0.28, -11, 5, 4.5, "sio"], [0.40, 26, -9, -12, "p2o"], [0.52, -3, 2, 1.6, "sio"],
           [0.62, 0, 0, 0, "sio"], [0.765, 0, 0, 0, "sio"], [0.83, 0, 8, 3, "p2o"], [0.96, 0, 0, 0, "sio"], [1, 0, 0, 0, "sio"]],
    aliments: { depart: [0.385, 0.405, 0.425], arrivee: [0.74, 0.775, 0.81], hauteur: [178, 214, 158], recul: [48, 64, 38],
                tour: [-360, 360, -360] },
    smear: { duree: 0.1, etirement: 0.95, vitesse: 0.00022, vitesse_max: 0.28 },   // s ; +95 % au décollage ; puis ∝ vitesse
    traits_coup: { u: 0.295, duree: 0.1, point: [262, 336], reglages: { n: 3, longueurs: [80, 104, 64], ecart: 24, recul: 18, epaisseur: 6 } },
    traits_aliments: { duree: 0.12, reglages: { n: 2, longueurs: [30, 42], ecart: 18, epaisseur: 5 } },
    flammes: [
      { x: 352, base: 470, h: 66, w: 24, phase: 0.00, flammeche: { periode: 2.5, decalage: 0.35, duree: 0.5 } },
      { x: 412, base: 470, h: 90, w: 26, phase: 0.37, flammeche: { periode: 2.5, decalage: 1.55, duree: 0.55 } },
      { x: 472, base: 470, h: 64, w: 23, phase: 0.71, flammeche: { periode: 2.5, decalage: 0.95, duree: 0.45 } }],
    flamme_commune: { ondulation: { periode: 0.5, amplitude: 0.36, longueur: 0.85 }, torsion: [[0.625, 0.26], [0.4, 0.09]] },
    aviver: 0.16,                                   // les flammes montent quand la poêle s'écarte du feu
    phase_complete: 0.14                            // la complète ne montre la situation qu'une seconde : le geste y tombe
  };
  const R = REGLAGES, PIV = R.pivot, PI = Math.PI, sin = Math.sin;
  const E = { sio: (x) => 0.5 - 0.5 * Math.cos(PI * x), p2o: (x) => 1 - (1 - x) * (1 - x) };
  const al = [].slice.call(document.querySelectorAll("#objet .po-al")).map((g, i) => ({ g: g, x: +g.dataset.x, y: +g.dataset.y, r: +g.dataset.r, i: i }));
  const poele = document.getElementById("po-poele"), gT = document.getElementById("po-traits"), gF = document.getElementById("po-flammes");
  const flammes = R.flammes.map((f) => FX.flamme(gF, Object.assign({}, R.flamme_commune, f)));
  const traitsCoup = FX.traits(gT, R.traits_coup.reglages);
  const traitsAl = al.map((a) => FX.traits(gT, Object.assign({}, R.traits_aliments.reglages, { recul: a.r + 18 })));   // derrière l'aliment, jamais dessus
  function pose(u) {
    const C = R.cles;
    for (let k = 1; k < C.length; k++) if (u <= C[k][0]) {
      const a = C[k - 1], b = C[k], e = E[b[4]]((u - a[0]) / (b[0] - a[0]));
      return { tx: a[1] + (b[1] - a[1]) * e, ty: a[2] + (b[2] - a[2]) * e, r: a[3] + (b[3] - a[3]) * e };
    }
    return { tx: 0, ty: 0, r: 0 };
  }
  function monde(p, x, y) {                       // un point de la poêle (au repos) → dans le dessin, poêle posée en p
    const a = p.r * PI / 180, c = Math.cos(a), s = Math.sin(a);
    return [PIV[0] + (x - PIV[0]) * c - (y - PIV[1]) * s + p.tx, PIV[1] + (x - PIV[0]) * s + (y - PIV[1]) * c + p.ty];
  }
  const A = R.aliments;
  function vol(a, u) {                            // position et rotation d'un aliment en vol (u dans ]départ, arrivée[)
    const i = a.i, u0 = A.depart[i], u1 = A.arrivee[i], s = (u - u0) / (u1 - u0);
    const L = monde(pose(u0), a.x, a.y), D = monde(pose(u1), a.x, a.y);
    return { x: L[0] + (D[0] - L[0]) * s - A.recul[i] * sin(PI * s), y: L[1] + (D[1] - L[1]) * s - A.hauteur[i] * 4 * s * (1 - s),
             rot: pose(u0).r * (1 - s) + pose(u1).r * s + A.tour[i] * s };
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    let u = t / periode + (mode === "complete" ? R.phase_complete : 0); u -= Math.floor(u);
    const tc = u * periode, du = 0.002;           // temps dans le geste (s)
    const p = pose(u);
    poele.setAttribute("transform", "translate(" + p.tx.toFixed(2) + " " + p.ty.toFixed(2) + ") rotate(" + p.r.toFixed(3) + " " + PIV[0] + " " + PIV[1] + ")");
    // traits de vitesse du coup : derrière le cul de la poêle, dans le sens du mouvement, trois images
    const TC = R.traits_coup, q0 = monde(pose(u), TC.point[0], TC.point[1]), q1 = monde(pose(Math.min(1, u + du)), TC.point[0], TC.point[1]);
    traitsCoup(FX.fenetre(tc, TC.u * periode, TC.duree), q0[0], q0[1], Math.atan2(q1[1] - q0[1], q1[0] - q0[0]));
    al.forEach(function (a) {
      const i = a.i, u0 = A.depart[i], u1 = A.arrivee[i];
      let x, y, rot, sx = 1, sy = 1, smear = "";
      if (u > u0 && u < u1) {
        const v = vol(a, u), w = vol(a, Math.min(u1 - 1e-4, u + du));
        x = v.x; y = v.y; rot = v.rot;
        const vx = (w.x - v.x) / (du * periode), vy = (w.y - v.y) / (du * periode), vit = Math.hypot(vx, vy);
        const dt = (u - u0) * periode, S = R.smear;
        const f = Math.max(1 + Math.min(S.vitesse_max, vit * S.vitesse), dt < S.duree ? 1 + S.etirement * (1 - dt / S.duree) : 1);
        smear = FX.etirer(vx, vy, f);
        traitsAl[i](FX.fenetre(dt, 0, R.traits_aliments.duree), x, y, Math.atan2(vy, vx));
      } else {
        const P = monde(p, a.x, a.y); x = P[0]; y = P[1]; rot = p.r;
        let v = (u - u1) / 0.1;                                  // écrasement à l'atterrissage (base fixe)
        if (v >= 0 && v <= 1) { const q = sin(PI * v) * (1 - 0.35 * v); sy = 1 - 0.3 * q; sx = 1 + 0.22 * q; }
        v = (u - (u0 - 0.06)) / 0.06;                            // tassé par l'accélération du coup, juste avant de partir
        if (v >= 0 && v <= 1) { const q = sin(PI * v); sy = 1 - 0.1 * q; sx = 1 + 0.07 * q; }
        traitsAl[i](-1);
      }
      a.g.setAttribute("transform", "translate(" + x.toFixed(2) + " " + (y + a.r * (1 - sy)).toFixed(2) + ") " + smear + " scale(" +
        sx.toFixed(4) + " " + sy.toFixed(4) + ") rotate(" + rot.toFixed(2) + ")");
    });
    const aviv = Math.max(0, sin(PI * Math.min(1, Math.max(0, (u - 0.3) / 0.35)))) * R.aviver;
    flammes.forEach((maj) => maj(t, aviv));
  };
})();
