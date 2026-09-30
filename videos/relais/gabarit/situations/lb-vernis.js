/* Animateur de la situation « lb-vernis » (onglerie, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps.
   Horloge u sur 10 s, qui part du retour de la situation dans la boucle (DONNEES.situation.revient) ; visible de u = 0 à
   u ≈ 3,2. Anticipation (le pinceau se relève d'un rien), passe de la cuticule au bout (sinus), poils qui plient à
   l'opposé du mouvement (retard), vernis qui suit le pinceau ; relevé : un fil de vernis s'étire et s'amincit, casse, se
   rétracte dans la goutte qui grossit au bout des poils, pend (étirée par son poids) et tremble (oscillation amortie à
   volume constant) ; le pinceau s'écarte en arc ; la lampe s'allume en clignant, les rayons poussent vers l'ongle, le
   reflet apparaît. Complète : même horloge, décalée. */
(function () {
  const REGLAGES = {
    decalage_complete: 0.3,
    survol: [252, 396, -18], depart: [252, 438, -22], arrivee: [322, 438, -30], repos: [196, 300, -30],
    temps: { anticipe: [0.22, 0.38], passe: [0.38, 0.95], releve: [0.95, 1.14], casse: 1.1, ecarte: [1.14, 1.62],
             allume: 1.72, reflet: 1.9, cache: 3.8 },
    poils: { longueur: 44, largeur: 24, pli: 16 },
    goutte: { r: 14, tremble: { periode: 0.22, amorti: 0.28, amplitude: 0.22 } },
    rayons: [[-46, 0], [-15, 0], [16, 0], [47, 0]], rayon_long: 104
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos, exp = Math.exp;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const E = { sio: (x) => 0.5 - 0.5 * cos(PI * x), p2o: (x) => 1 - (1 - x) * (1 - x), p3o: (x) => 1 - Math.pow(1 - x, 3) };
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const D = window.DONNEES || { situation: {} };
  const RETOUR = D.situation && D.situation.revient != null ? D.situation.revient : 8.75;
  const $ = (i) => document.getElementById(i);
  const pinceau = $("vn-pinceau"), poils = $("vn-poils"), vernis = $("vn-vernis"), fil = $("vn-fil"), goutte = $("vn-goutte").firstElementChild;
  const gGoutte = $("vn-goutte"), led = $("vn-led"), reflet = $("vn-reflet");
  const rayons = R.rayons.map(() => el($("vn-rayons"), "path", { d: "" }));
  const T = R.temps;
  const mix = (a, b, e) => [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e];
  const s = (u, w) => cl((u - w[0]) / (w[1] - w[0]), 0, 1);
  function pose(u) {
    const arme = [R.survol[0] - 6, R.survol[1] - 14, R.survol[2] - 5];
    if (u < T.anticipe[0]) return R.survol;
    if (u < T.anticipe[1]) return mix(R.survol, arme, E.sio(s(u, T.anticipe)));
    if (u < T.passe[0] + 0.08) return mix(arme, R.depart, E.p2o(s(u, [T.anticipe[1], T.passe[0] + 0.08])));
    if (u < T.passe[1]) return mix(R.depart, R.arrivee, E.sio(s(u, [T.passe[0] + 0.08, T.passe[1]])));
    const haut = [R.arrivee[0] + 6, R.arrivee[1] - 70, R.arrivee[2] + 4];
    if (u < T.releve[1]) return mix(R.arrivee, haut, E.sio(s(u, T.releve)));
    if (u < T.ecarte[1]) { const e = E.sio(s(u, T.ecarte)), q = mix(haut, R.repos, e); q[1] -= 40 * sin(PI * e); return q; }
    if (u < T.cache) return R.repos;
    if (u < T.cache + 1.5) return mix(R.repos, R.survol, E.sio((u - T.cache) / 1.5));
    return R.survol;
  }
  const bout = (P) => [P[0], P[1]];            // le bout des poils est l'origine du pinceau
  window.SITUATION_ANIM = function (t, periode, mode) {
    const u = mode === "complete" ? t + R.decalage_complete : ((t - RETOUR) % 10 + 10) % 10;
    const P = pose(u), P2 = pose(u + 0.004), vx = (P2[0] - P[0]) / 0.004;
    pinceau.setAttribute("transform", "translate(" + f2(P[0]) + " " + f2(P[1]) + ") rotate(" + f2(P[2]) + ")");
    // les poils plient à l'opposé du mouvement (au contact seulement), leur pointe traîne
    const contact = u >= T.passe[0] + 0.06 && u < T.passe[1] + 0.02;
    const pli = contact ? -R.poils.pli * cl(vx / 160, -1, 1) : 0;
    const Pl = R.poils, w = Pl.largeur / 2, L = Pl.longueur;
    poils.setAttribute("d", "M" + f2(-w * 0.7) + " " + (-L) + " L" + f2(w * 0.7) + " " + (-L) + " C" + f2(w) + " " + f2(-L * 0.5) + " " + f2(w + pli * 0.5) + " " + f2(-L * 0.15) + " " + f2(pli + w * 0.35) + " 0" +
      " L" + f2(pli - w * 0.35) + " 0 C" + f2(-w + pli * 0.5) + " " + f2(-L * 0.15) + " " + f2(-w) + " " + f2(-L * 0.5) + " " + f2(-w * 0.7) + " " + (-L) + " Z");
    // vernis : suit le pinceau pendant la passe
    let x1 = 236;
    if (u >= T.passe[0] && u < T.cache) x1 = u >= T.passe[1] ? 344 : 236 + (P[0] + 10 - 236) * cl((u - T.passe[0]) / 0.06, 0, 1);
    vernis.setAttribute("width", f2(Math.max(0, x1 - 236)));
    // le fil puis la goutte
    const Rel = [R.arrivee[0], R.arrivee[1]];
    if (u >= T.releve[0] && u < T.casse) {
      const e = (u - T.releve[0]) / (T.casse - T.releve[0]);
      fil.setAttribute("d", "M" + f2(Rel[0] - 4) + " " + f2(Rel[1] + 2) + " Q" + f2((Rel[0] + P[0]) / 2 + 3) + " " + f2((Rel[1] + P[1]) / 2 + 6) + " " + f2(P[0]) + " " + f2(P[1]));
      fil.setAttribute("stroke-width", f2(10 * (1 - e) + 2));
    } else fil.setAttribute("d", "");
    const G = R.goutte;
    if (u >= T.releve[0] && u < T.cache) {
      const g0 = cl((u - T.releve[0]) / 0.1, 0, 1), casse = u >= T.casse ? cl((u - T.casse) / 0.08, 0, 1) : 0;
      const r = G.r * (0.55 + 0.25 * g0 + 0.3 * casse);
      const q = u - T.casse, Tr = G.tremble, j = q > 0 ? Tr.amplitude * exp(-q / Tr.amorti) * sin(2 * PI * q / Tr.periode) : 0;
      const sy = 1.18 + j, sx = 1 / Math.sqrt(sy);              // étirée par son poids, tremble à volume constant
      const d = "M0 " + f2(-r * 0.4) + " C" + f2(r * 1.1) + " " + f2(-r * 0.2) + " " + f2(r) + " " + f2(r * 1.5) + " 0 " + f2(r * 1.6) +
        " C" + f2(-r) + " " + f2(r * 1.5) + " " + f2(-r * 1.1) + " " + f2(-r * 0.2) + " 0 " + f2(-r * 0.4) + " Z";
      goutte.setAttribute("d", d);
      gGoutte.setAttribute("transform", "rotate(" + f2(-P[2]) + ") scale(" + sx.toFixed(4) + " " + sy.toFixed(4) + ")");
    } else goutte.setAttribute("d", "");
    // lampe
    const on = u >= T.allume && u < T.cache && !(u - T.allume >= 0.067 && u - T.allume < 0.133);
    led.setAttribute("fill", on ? "#EFA424" : "#E8E2D5");
    const pousse = on && u - T.allume >= 0.133 ? E.p3o(cl((u - T.allume - 0.133) / 0.3, 0, 1)) : 0;
    const a = 40 * PI / 180, c = cos(a), sn = sin(a), dirx = -sin(a), diry = cos(a);
    rayons.forEach(function (ray, i) {
      if (!pousse) { ray.setAttribute("d", ""); return; }
      const lx = R.rayons[i][0], ly = 44, x0 = 400 + lx * c - ly * sn, y0 = 316 + lx * sn + ly * c;
      const L2 = R.rayon_long * pousse * (1 + 0.05 * sin(2 * PI * (u + i * 0.25)));
      ray.setAttribute("d", "M" + f2(x0) + " " + f2(y0) + " L" + f2(x0 + dirx * L2) + " " + f2(y0 + diry * L2));
    });
    reflet.setAttribute("opacity", u >= T.reflet && u < T.cache ? E.sio(cl((u - T.reflet) / 0.25, 0, 1)).toFixed(3) : "0");
  };
})();
