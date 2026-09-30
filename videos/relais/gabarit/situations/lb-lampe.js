/* Animateur de la situation « lb-lampe » (dentiste, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps.
   Horloge u sur 10 s, qui part du retour de la situation dans la boucle (DONNEES.situation.revient) ; visible de u = 0 à
   u ≈ 3,2. La tête pivote autour de l'axe de sa fourche : phi = angle entre sa face et nous (90° : face vers le haut, on
   ne voit que la coque ; 0° : face vers nous). Anticipation (elle se relève un peu plus), pivot power3.out avec dépassement
   puis retour amorti ; au coup d'arrêt, le bras plonge de quelques pixels et le miroir part en pendule amorti (tête du
   miroir en léger retard : il est souple) ; la lampe s'allume en clignant (allumée, éteinte, allumée), les LED s'éclairent,
   les rayons poussent puis respirent. Complète : même horloge, décalée. */
(function () {
  const REGLAGES = {
    decalage_complete: 0.0,
    centre: [300, 250], profondeur: 46,
    range: 80, arme: 88, pose: 0, depasse: -17,        // phi en degrés
    temps: { arme: [0.26, 0.44], pivot: [0.44, 0.92], amorti: 0.62, allume: 1.0, eteint_cache: 3.8 },
    bras: { plonge: 7, periode: 0.42, amorti: 0.28 },
    miroir: { pivot: [52, 108], amplitude: 16, periode: 1.0, amorti: 1.3 },
    rayons: { n: 10, r0: 20, r1: 58, respire: [1.0, 0.06] }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos, exp = Math.exp;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const E = { sio: (x) => 0.5 - 0.5 * cos(PI * x), p3o: (x) => 1 - Math.pow(1 - x, 3) };
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const D = window.DONNEES || { situation: {} };
  const RETOUR = D.situation && D.situation.revient != null ? D.situation.revient : 8.75;
  const $ = (i) => document.getElementById(i);
  const tete = $("la-tete"), face = $("la-face"), coque = $("la-coque"), verre = $("la-verre"), leds = $("la-leds"), bras = $("la-bras"), miroir = $("la-miroir"), fac = $("la-facettes");
  const rayons = []; for (let i = 0; i < R.rayons.n; i++) rayons.push(el($("la-rayons"), "path", { d: "" }));
  const T = R.temps, C = R.centre;

  function phi(u) {
    if (u < T.arme[0]) return R.range;
    if (u < T.arme[1]) return R.range + (R.arme - R.range) * E.sio((u - T.arme[0]) / (T.arme[1] - T.arme[0]));
    if (u < T.pivot[1]) return R.arme + (R.depasse - R.arme) * E.sio((u - T.arme[1]) / (T.pivot[1] - T.arme[1]));   // sinus : la face s'ouvre régulièrement à l'œil (projection en cosinus)
    if (u < T.eteint_cache) { const s = u - T.pivot[1]; return R.depasse * exp(-s / (T.amorti * 0.35)) * cos(PI * s / T.amorti); }
    if (u < T.eteint_cache + 1.5) return R.range * E.sio((u - T.eteint_cache) / 1.5);          // caché : elle se relève
    return R.range;
  }
  // rectangle arrondi (demi-largeur a, demi-hauteur b, rayon r), aplati en hauteur par k, décalé de dy
  function rr(a, b, r, k, dy) {
    const B = b * k, rv = Math.min(r * k, B), P = (x, y) => f2(x) + " " + f2(y + dy);
    return "M" + P(-a + r, -B) + " L" + P(a - r, -B) + " Q" + P(a, -B) + " " + P(a, -B + rv) + " L" + P(a, B - rv) + " Q" + P(a, B) + " " + P(a - r, B) +
      " L" + P(-a + r, B) + " Q" + P(-a, B) + " " + P(-a, B - rv) + " L" + P(-a, -B + rv) + " Q" + P(-a, -B) + " " + P(-a + r, -B) + " Z";
  }
  function lumiere(u) {
    if (u < T.allume || u >= T.eteint_cache) return 0;
    const s = u - T.allume;
    return s < 0.067 || s >= 0.133 ? 1 : 0;
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const u = mode === "complete" ? t + R.decalage_complete : ((t - RETOUR) % 10 + 10) % 10;
    const p = phi(u) * PI / 180, k = Math.max(0.02, cos(p)), dep = R.profondeur * sin(p);
    // bras : il encaisse l'arrêt du pivot (plonge puis revient, amorti)
    const sb = u - T.pivot[1];
    const plonge = sb > 0 && u < T.eteint_cache + 1.5 ? R.bras.plonge * exp(-sb / R.bras.amorti) * sin(2 * PI * sb / R.bras.periode) : 0;
    bras.setAttribute("transform", "translate(0 " + f2(plonge) + ")");
    tete.setAttribute("transform", "translate(" + C[0] + " " + C[1] + ")");
    face.setAttribute("transform", "translate(0 " + f2(-dep * 0.5) + ") scale(1 " + k.toFixed(4) + ")");
    // la coque : l'épaisseur de la tête, vue sous la face quand elle est relevée
    coque.setAttribute("d", rr(134, 84, 62, k, dep * 0.5) + " " + rr(134, 84, 62, k, -dep * 0.5));
    const L = lumiere(u), s = u - T.allume;
    verre.setAttribute("fill", L ? "#EFA424" : "#E8E2D5");
    leds.setAttribute("fill", L ? "#FFF6E3" : "#F4F1E8");
    fac.setAttribute("stroke", L ? "#F8D69B" : "#262019");
    const Rr = R.rayons, pousse = L && s >= 0.133 ? E.p3o(cl((s - 0.133) / 0.3, 0, 1)) : 0;
    rayons.forEach(function (ray, i) {
      if (!pousse) { ray.setAttribute("d", ""); return; }
      const g = (i / Rr.n) * 2 * PI + PI / Rr.n, resp = 1 + Rr.respire[1] * sin(2 * PI * (u / Rr.respire[0] + i * 0.13));
      // point du bord de la face dans la direction g (ellipse englobante), puis vers l'extérieur
      const ex = 150 * cos(g), ey = 98 * k * sin(g) - dep * 0.5, n = Math.hypot(cos(g), sin(g) * 1.3);
      const ux = cos(g) / n, uy = sin(g) * 1.3 / n, a0 = Rr.r0, a1 = a0 + (Rr.r1 - a0) * pousse * resp;
      ray.setAttribute("d", "M" + f2(ex + ux * a0) + " " + f2(ey + uy * a0) + " L" + f2(ex + ux * a1) + " " + f2(ey + uy * a1));
    });
    // miroir : lancé par le coup d'arrêt, pendule amorti
    const M = R.miroir, sm = u - T.pivot[1] + 0.04;
    let th = 0;
    if (sm > 0 && u < T.eteint_cache + 1.5) th = -M.amplitude * exp(-sm / M.amorti) * sin(2 * PI * sm / M.periode) * cl(sm / 0.05, 0, 1);
    miroir.setAttribute("transform", "rotate(" + th.toFixed(3) + " " + M.pivot[0] + " " + M.pivot[1] + ")");
  };
})();
