/* Animateur « évier » (plombier, v3). τ = FX.tau(t, mode). Avant (fin de boucle) : gouttes régulières (période 1,25 s),
   pas de clé. Geste : une goutte tombe (étirée, accélérée, écrasée au sol, ondes sur la flaque) ; la clé entre (sio), se pose
   sur l'écrou, prend son élan (recule de 4°), serre de 38° (sens horaire vu du dessus : le manche part vers le fond, les pans
   de l'écrou glissent vers la gauche), tremble d'effort ; une perle se forme à peine et se résorbe (fuite arrêtée) ; la clé
   ressort à gauche. La clé est vue d'un peu au-dessus : son plan est écrasé à 55 % en hauteur. */
(function () {
  const REGLAGES = {
    ecrou: [280, 340], point_bas: [315, 434], sol: 540, ecrasement: 0.78, echelle: 1.2,
    // [τ, décalage x de la clé, angle dans son plan (°, + = horaire vu du dessus)]
    cle: [[-9, -420, 0], [0.08, -420, 0], [0.46, 0, 0, "p3o"], [0.56, 0, -4, "sio"], [0.9, 0, 38, "sio"], [1.1, 0, 36, "p2o"],
          [1.2, 0, 36], [1.5, -420, 30, "sio"], [9, -420, 0]],
    tremble: { de: 0.88, a: 1.08, amplitude: 1.4 },
    gouttes: { periode: 1.25, derniere: 0.3, croissance: 0.9, rayon: 17, gravite: 2400 },
    perle: { de: 0.96, a: 1.7, rayon: 7 },
    pans: [-18, -6, 6, 18], espace_pans: 12,
    eclabousse: { n: 5, forme: "goutte", couleur: "#EFA424", contour: "#262019", epaisseur: 2.5, taille: [5, 8], vitesse: [140, 250], ouverture: 1.7, gravite: 1500, duree: 0.34, graine: 11 }
  };
  const R = REGLAGES, PI = Math.PI, NS = "http://www.w3.org/2000/svg", f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const cle = $("ev-cle"), pans = $("ev-pans"), flaque = $("ev-flaque-p"), onde = $("ev-onde");
  const P = R.pans.map(() => { const p = document.createElementNS(NS, "path"); pans.appendChild(p); return p; });
  const goutte = document.createElementNS(NS, "path");
  goutte.setAttribute("fill", "#EFA424"); goutte.setAttribute("stroke", "#262019"); goutte.setAttribute("stroke-width", "3.5");
  $("ev-gouttes").appendChild(goutte);
  const eclab = FX.particules($("ev-gouttes"), R.eclabousse);
  function larme(x, y, r, etire, sx) {           // goutte pendue (etire 0) ou en chute ; sx : écrasement horizontal à l'impact
    const h = r * (1.5 + etire), w = r * (sx || 1);
    return "M" + f2(x) + " " + f2(y - h - r) + " C" + f2(x + w * 0.35) + " " + f2(y - h * 0.6 - r) + " " + f2(x + w) + " " + f2(y - r * 0.6) + " " + f2(x + w) + " " + f2(y) +
      " A" + f2(w) + " " + f2(r) + " 0 0 1 " + f2(x - w) + " " + f2(y) + " C" + f2(x - w) + " " + f2(y - r * 0.6) + " " + f2(x - w * 0.35) + " " + f2(y - h * 0.6 - r) + " " + f2(x) + " " + f2(y - h - r) + " Z";
  }
  const ell = (cx, cy, rx, ry) => "M" + f2(cx - rx) + " " + f2(cy) + " a" + f2(rx) + " " + f2(ry) + " 0 1 0 " + f2(2 * rx) + " 0 a" + f2(rx) + " " + f2(ry) + " 0 1 0 " + f2(-2 * rx) + " 0 Z";
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    let [dx, a] = FX.cles(T, R.cle);
    const tr = R.tremble;
    if (T > tr.de && T < tr.a) a += tr.amplitude * Math.sin(2 * PI * (T - tr.de) / 0.0667) * (1 - (T - tr.de) / (tr.a - tr.de));
    cle.setAttribute("transform", "translate(" + f2(R.ecrou[0] + dx) + " " + R.ecrou[1] + ") scale(" + R.echelle + " " + (R.echelle * R.ecrasement).toFixed(3) + ") rotate(" + f2(a) + ")");
    // pans de l'écrou : ils glissent vers la gauche quand il tourne (même angle que la clé une fois en prise)
    const n = Math.max(0, Math.min(38, dx > -1 ? a : 0));
    const dec = -(n / 38) * R.espace_pans;
    P.forEach(function (p, i) {
      let x = R.pans[i] + dec; x = ((x + 26) % 52 + 52) % 52 - 26;
      p.setAttribute("d", Math.abs(x) < 23 ? "M" + f2(R.ecrou[0] + x) + " 330 V 350" : "");
    });
    // gouttes : elles perlent au point bas du siphon, tombent, éclaboussent ; la dernière part à τ = 0,3
    const G = R.gouttes, B = R.point_bas;
    let d = "", impact = -9;
    const k = Math.floor((T - G.derniere) / G.periode), rel = G.derniere + Math.min(0, k) * G.periode, prochain = rel + G.periode;
    const chute = Math.sqrt(2 * (R.sol - B[1]) / G.gravite);
    if (T >= rel && T < rel + chute) { const s = T - rel, y = B[1] + 0.5 * G.gravite * s * s; d = larme(B[0], y, G.rayon * 0.9, Math.min(1.7, G.gravite * s / 800)); }
    if (T - rel >= chute) impact = T - rel - chute;
    if (impact >= 0 && impact < 0.07) { const q = 1 - impact / 0.07; d = larme(B[0], R.sol - 6 * q, G.rayon * 0.9 * (0.6 + 0.4 * q) * 0.7, 0, 1.6); }
    if (prochain <= G.derniere + 1e-6 && T > prochain - G.croissance) {
      const w = (T - (prochain - G.croissance)) / G.croissance, r = G.rayon * Math.pow(w, 0.6);
      d += (d ? " " : "") + larme(B[0], B[1] + r * 0.8 + w * 5, r, 0.25 * w);
    }
    const Pe = R.perle;
    if (T > Pe.de && T < Pe.a) { const w = (T - Pe.de) / (Pe.a - Pe.de), r = Pe.rayon * Math.sin(PI * w); if (r > 0.4) d += " " + larme(B[0], B[1] + r * 0.8, r, 0); }
    goutte.setAttribute("d", d);
    eclab(FX.fenetre(impact, 0.02, R.eclabousse.duree), B[0], R.sol - 2, -PI / 2);
    // flaque (s'élargit d'un cran à chaque impact) et onde qui s'éloigne en s'effaçant
    const o = impact >= 0 && impact < 0.6 ? impact / 0.6 : -1;
    const base = 44 + 6 * Math.sin(PI * Math.max(0, Math.min(1, impact / 0.3)));
    flaque.setAttribute("d", ell(B[0], R.sol, base, 7));
    onde.setAttribute("d", o >= 0 ? ell(B[0], R.sol, base + 50 * o, 7 + 6 * o) : "");
    onde.setAttribute("opacity", o >= 0 ? (1 - o).toFixed(3) : "0");
  };
})();
