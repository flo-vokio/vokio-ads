/* Animateur de la situation « lb-elastique » (kiné, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps,
   périodique (2,5 s par geste, 4 par boucle). Deux poings tiennent l'élastique. Anticipation (ils se rapprochent), traction
   lente qui ralentit quand la tension monte (sinus), poings qui s'inclinent vers l'extérieur, tremblement d'effort au bout ;
   relâché : retour sec (accélération), dépassement, oscillation amortie autour du repos, traits de vitesse sur trois images.
   L'élastique garde son volume (plus long = plus mince), se tend en ligne droite, pend et ondule quand il est détendu (onde
   stationnaire amortie). Les avant-bras suivent les poings (ils sortent du cadre en bas). */
(function () {
  const REGLAGES = {
    decalage_complete: 0.7,
    centre: [300, 300], repos: 96, tire: 224, avance: 14, depasse: 22,
    temps: { anticipe: [0.2, 0.38], tire: [0.38, 1.3], effort: [1.02, 1.45], lache: 1.45, retour: 0.12, oscille: 0.36, amorti: 0.26 },
    largeur: 42, bord: 7, pend: 30, onde: { amplitude: 24, periode: 0.24, amorti: 0.32, ventres: 1 },
    coude: [[150, 640], [470, 640]],
    traits: { n: 3, longueurs: [40, 56, 34], ecart: 18, recul: 58, epaisseur: 5 }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos, exp = Math.exp;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const E = { sio: (x) => 0.5 - 0.5 * cos(PI * x), p2i: (x) => x * x };
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const $ = (i) => document.getElementById(i);
  const bande = $("el-bande"), bord = $("el-bande-bord");
  const T = R.temps, C = R.centre;
  // avant-bras (bord encre, intérieur papier) et poings
  const bras = [0, 1].map(() => ({ b: el($("el-bras"), "path", { fill: "none", stroke: "#262019", "stroke-width": 62, "stroke-linecap": "round" }),
                                    c: el($("el-bras"), "path", { fill: "none", stroke: "#F4F1E8", "stroke-width": 48, "stroke-linecap": "round" }) }));
  const poings = [-1, 1].map(function (cote) {
    const g = el($("el-poings"), "g", {}), h = el(g, "g", { transform: "scale(" + cote + " 1)" });
    const at = { fill: "#F4F1E8", stroke: "#262019", "stroke-width": 7, "stroke-linejoin": "round" };
    // poing vu de face : le dos de la main, quatre doigts repliés sur l'élastique, le pouce par-dessus
    el(h, "rect", Object.assign({ x: -56, y: -12, width: 112, height: 70, rx: 24 }, at));
    for (let k = 0; k < 4; k++) el(h, "rect", Object.assign({ x: -56 + k * 28, y: -44, width: 28, height: 50, rx: 13 }, at));
    el(h, "rect", Object.assign({ x: -50, y: 8, width: 82, height: 26, rx: 13, transform: "rotate(-6 -9 21)" }, at));
    return { g: g, cote: cote };
  });
  const traits = [0, 1].map(() => FX.traits($("el-traits"), R.traits));
  function demi(s) {                           // demi-écart des poings dans le geste
    if (s < T.anticipe[0]) return R.repos;
    if (s < T.anticipe[1]) return R.repos - R.avance * E.sio((s - T.anticipe[0]) / (T.anticipe[1] - T.anticipe[0]));
    if (s < T.tire[1]) return R.repos - R.avance + (R.tire - R.repos + R.avance) * E.sio((s - T.tire[0]) / (T.tire[1] - T.tire[0]));
    if (s < T.lache) return R.tire;
    const q = s - T.lache;
    if (q < T.retour) return R.tire + (R.repos - R.depasse - R.tire) * E.p2i(q / T.retour);
    const r = q - T.retour;
    return R.repos - R.depasse * exp(-r / T.amorti) * cos(PI * r / T.oscille);
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const tt = mode === "complete" ? t + R.decalage_complete : t;
    const s = ((tt % periode) + periode) % periode;
    let w = demi(s);
    const dw = demi(Math.min(periode - 1e-4, s + 0.004)) - w;
    let tr = 0;
    if (s >= T.effort[0] && s < T.lache) tr = sin(PI * (s - T.effort[0]) / (T.lache - T.effort[0]));
    const tremble = [2.2 * tr * sin(2 * PI * s * 13), 2.2 * tr * sin(2 * PI * s * 11 + 1.3)];
    const tension = cl((w - R.repos) / (R.tire - R.repos), 0, 1);
    const P = [[C[0] - w + tremble[0], C[1] + 1.5 * tr * sin(2 * PI * s * 17)], [C[0] + w + tremble[1], C[1] + 1.5 * tr * sin(2 * PI * s * 15 + 2)]];
    // élastique entre les deux mains
    const A = P[0], B = P[1], dx = B[0] - A[0], dy = B[1] - A[1], L = Math.hypot(dx, dy), L0 = 2 * R.repos;
    const Wd = R.largeur * Math.sqrt(L0 / Math.max(L, 60));
    const mou = cl((L0 + 20 - L) / 70, 0, 1), q = s - T.lache - T.retour * 0.6, On = R.onde;
    const ond = q > 0 ? On.amplitude * exp(-q / On.amorti) * sin(2 * PI * q / On.periode) : 0;
    const n = 28, pts = [];
    for (let k = 0; k <= n; k++) {
      const f = k / n, off = R.pend * mou * 4 * f * (1 - f) + ond * sin(PI * On.ventres * f);
      pts.push(f2(A[0] + dx * f) + " " + f2(A[1] + dy * f + off));
    }
    const d = "M" + pts.join(" L");
    bande.setAttribute("d", d); bande.setAttribute("stroke-width", f2(Wd));
    bord.setAttribute("d", d); bord.setAttribute("stroke-width", f2(Wd + 2 * R.bord));
    // poings (inclinés vers l'extérieur sous la tension) et avant-bras
    poings.forEach(function (p, i) {
      const rot = p.cote * (8 * tension - 4 * mou);
      p.g.setAttribute("transform", "translate(" + f2(P[i][0]) + " " + f2(P[i][1]) + ") rotate(" + f2(rot) + ")");
      const Cd = R.coude[i], x0 = P[i][0], y0 = P[i][1] + 44;
      const dd = "M" + f2(x0) + " " + f2(y0) + " Q" + f2((x0 + Cd[0]) / 2 + p.cote * 10) + " " + f2((y0 + Cd[1]) / 2) + " " + Cd[0] + " " + Cd[1];
      bras[i].b.setAttribute("d", dd); bras[i].c.setAttribute("d", dd);
      traits[i](FX.fenetre(s, T.lache + 0.02, 0.1), P[i][0] + p.cote * 20, P[i][1] - 60, p.cote > 0 ? PI : 0);
    });
  };
})();
