/* Animateur de la situation « lb-vertebres » (ostéopathe, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps.
   Horloge u sur 10 s, qui part du retour de la situation dans la boucle (DONNEES.situation.revient) ; visible de u = 0 à
   u ≈ 3,2. Bloqué : vertèbres décalées et tournées, la plus bloquée tremble, traits de douleur. Anticipation : la colonne se
   tasse (écrasement vertical, base fixe). Cascade : chaque vertèbre revient en 0,26 s (départ sec, dépassement amorti),
   décalées de 0,11 s du haut vers le bas (overlap) ; les disques suivent leurs voisines ; au passage de la plus bloquée,
   les traits s'éteignent. Puis la colonne s'étire (soulagement) et respire. Complète : même horloge. */
(function () {
  const REGLAGES = {
    decalage_complete: 0.0,
    x: 250, y0: 120, pas: 74, n: 6,
    decale: [[-8, -5], [14, 6], [-24, -9], [28, 10], [-10, -5], [5, 2]],   // [dx, rotation] au repos bloqué
    bloquee: 3,
    temps: { tasse: [0.34, 0.5], cascade: 0.5, echelon: 0.11, retour: 0.26, etire: [1.35, 1.75], cache: 3.8 },
    tasse: 0.05, etire: 0.035
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos, exp = Math.exp;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const E = { sio: (x) => 0.5 - 0.5 * cos(PI * x) };
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const D = window.DONNEES || { situation: {} };
  const RETOUR = D.situation && D.situation.revient != null ? D.situation.revient : 8.75;
  const $ = (i) => document.getElementById(i);
  const gC = $("vb-colonne"), gD = $("vb-douleur");
  const disques = [], vert = [];
  for (let i = 0; i < R.n - 1; i++) disques.push(el(gC, "ellipse", { rx: 40, ry: 9, fill: "#EFA424", stroke: "#262019", "stroke-width": 5 }));
  for (let i = 0; i < R.n; i++) {                           // vertèbre vue de face : corps arrondi et deux apophyses
    const g = el(gC, "g", {}), k = 0.9 + 0.035 * i, at = { fill: "#F4F1E8", stroke: "#262019", "stroke-width": f2(7 / k), "stroke-linejoin": "round" };
    const h = el(g, "g", { transform: "scale(" + k.toFixed(3) + ")" });
    el(h, "path", Object.assign({ d: "M-40 -12 L -96 -22 Q -110 -22 -108 -8 Q -106 6 -92 6 L -40 10 Z" }, at));
    el(h, "path", Object.assign({ d: "M40 -12 L 96 -22 Q 110 -22 108 -8 Q 106 6 92 6 L 40 10 Z" }, at));
    el(h, "rect", Object.assign({ x: -50, y: -26, width: 100, height: 52, rx: 18 }, at, { "stroke-width": f2(8 / k) }));
    vert.push(g);
  }
  const douleur = [0, 1, 2].map(() => el(gD, "path", { d: "" }));
  const T = R.temps;
  function retour(s) {                                       // 0 (bloquée) → 1 (en place) : départ sec, dépassement amorti
    if (s <= 0) return 0;
    if (s >= T.retour + 0.3) return 1;
    return 1 - exp(-s / 0.05) * cos(2 * PI * s / 0.24);
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const u = mode === "complete" ? t + R.decalage_complete : ((t - RETOUR) % 10 + 10) % 10;
    const cache = u >= T.cache;
    // écrasement / étirement de toute la colonne (base fixe : la dernière vertèbre)
    let sy = 1;
    if (!cache) {
      if (u >= T.tasse[0] && u < T.cascade + 0.2) sy -= R.tasse * sin(PI * cl((u - T.tasse[0]) / (T.cascade + 0.2 - T.tasse[0]), 0, 1));
      if (u >= T.etire[0]) sy += R.etire * sin(PI * cl((u - T.etire[0]) / (T.etire[1] - T.etire[0]), 0, 1));
      if (u >= T.etire[1]) sy += 0.008 * sin(2 * PI * (u - T.etire[1]) / 2.5);
    }
    const base = R.y0 + (R.n - 1) * R.pas;
    const pos = [];
    for (let i = 0; i < R.n; i++) {
      const e = cache ? 0 : retour(u - T.cascade - i * T.echelon);
      let dx = R.decale[i][0] * (1 - e), rot = R.decale[i][1] * (1 - e);
      if (i === R.bloquee && e < 0.05 && !cache) dx += 1.6 * sin(2 * PI * u * 11);   // la plus bloquée tremble
      const y = base - (base - (R.y0 + i * R.pas)) * sy;
      pos.push([R.x + dx, y, rot, e]);
      vert[i].setAttribute("transform", "translate(" + f2(R.x + dx) + " " + f2(y) + ") rotate(" + f2(rot) + ")");
    }
    for (let i = 0; i < R.n - 1; i++) {
      const a = pos[i], b = pos[i + 1];
      disques[i].setAttribute("transform", "translate(" + f2((a[0] + b[0]) / 2) + " " + f2((a[1] + b[1]) / 2) + ") rotate(" + f2((a[2] + b[2]) / 2) + ")");
    }
    // traits de douleur autour de la plus bloquée, jusqu'à ce qu'elle se remette en place
    const B = pos[R.bloquee], vis = !cache && B[3] < 0.6;
    douleur.forEach(function (p, k) {
      if (!vis) { p.setAttribute("d", ""); return; }
      const a = (-35 + k * 35) * PI / 180, j = 3 * sin(2 * PI * (u * 7 + k * 0.3)), r0 = 132 + j, r1 = 164 + j;
      const cx = B[0] + 10, cy = B[1];
      p.setAttribute("d", "M" + f2(cx + r0 * cos(a)) + " " + f2(cy + r0 * sin(a)) + " L" + f2(cx + r1 * cos(a)) + " " + f2(cy + r1 * sin(a)));
    });
  };
})();
