/* Animateur de la situation « lb-cloche » (traiteur, lot B). SITUATION_ANIM(t, periode, mode) : fonction pure du temps.
   Horloge u sur 10 s, qui part du retour de la situation dans la boucle (DONNEES.situation.revient) ; visible de u = 0 à
   u ≈ 3,2. Anticipation (la cloche se tasse et s'incline), levée par le bouton (power3.out, en arc), la cloche pend sous la
   main : son angle suit l'accélération du bouton avec retard (follow-through), dépasse et se stabilise (amorti) ; la vapeur :
   une première bouffée épaisse libérée à la levée, puis trois filets qui montent en ondulant (onde montante, amplitude qui
   croît avec la hauteur), s'amincissent et s'effacent. Complète : même horloge. */
(function () {
  const REGLAGES = {
    decalage_complete: 0.0,
    bouton: { repos: [300, 284], haut: [238, 96] }, bouton_local: 192,
    temps: { tasse: [0.3, 0.44], leve: [0.44, 1.0], cache: 3.8 },
    bascule: -24, suivi: { gain: 0.012, periode: 0.7, amorti: 0.35 },
    vapeur: { filets: [[252, 0.0], [300, 0.37], [350, 0.71]], base: 430, montee: 300, vie: 2.5, bouffees: 3, longueur: 90,
              onde: { longueur: 140, periode: 2.5, amplitude: [4, 30] }, epaisseur: [12, 3], depart: 0.5 }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos, exp = Math.exp;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const E = { sio: (x) => 0.5 - 0.5 * cos(PI * x), p3o: (x) => 1 - Math.pow(1 - x, 3) };
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const D = window.DONNEES || { situation: {} };
  const RETOUR = D.situation && D.situation.revient != null ? D.situation.revient : 8.75;
  const $ = (i) => document.getElementById(i);
  const cloche = $("cl-cloche"), dedans = $("cl-dedans");
  const V = R.vapeur, bouffees = [];
  V.filets.forEach((f, i) => { for (let k = 0; k < V.bouffees; k++) bouffees.push({ x: f[0], ph: f[1], k: k, i: i, p: el($("cl-vapeur"), "path", {}) }); });
  const bouffe = el($("cl-vapeur"), "path", {});                 // la bouffée libérée à la levée
  const T = R.temps, B = R.bouton;
  function bouton(u) {
    if (u < T.tasse[0] || u >= T.cache + 1.5) return [B.repos[0], B.repos[1], 0];
    if (u < T.tasse[1]) { const e = sin(PI * (u - T.tasse[0]) / (T.tasse[1] - T.tasse[0])); return [B.repos[0], B.repos[1] + 5 * e, 1.5 * e]; }
    if (u < T.cache) {
      const e = E.p3o(cl((u - T.tasse[1]) / (T.leve[1] - T.tasse[1]), 0, 1));
      const x = B.repos[0] + (B.haut[0] - B.repos[0]) * e, y = B.repos[1] + (B.haut[1] - B.repos[1]) * e - 18 * sin(PI * e);
      return [x, y + 3 * sin(2 * PI * u / 2.5) * e, R.bascule * E.sio(cl((u - T.tasse[1]) / 0.5, 0, 1))];
    }
    const e = E.sio((u - T.cache) / 1.5);
    return [B.haut[0] + (B.repos[0] - B.haut[0]) * e, B.haut[1] + (B.repos[1] - B.haut[1]) * e, R.bascule * (1 - e)];
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const u = mode === "complete" ? t + R.decalage_complete : ((t - RETOUR) % 10 + 10) % 10;
    const K = bouton(u), h = 0.01;
    // la cloche pend sous la main : angle = bascule voulue + retard proportionnel à l'accélération horizontale du bouton
    const a0 = bouton(u - h), a2 = bouton(u + h), acc = (a2[0] - 2 * K[0] + a0[0]) / (h * h);
    const S = R.suivi, s = u - T.leve[1];
    let phi = K[2] - cl(acc * S.gain * 0.02, -14, 14);
    if (s > 0 && u < T.cache) phi += 7 * exp(-s / S.amorti) * sin(2 * PI * s / S.periode);
    cloche.setAttribute("transform", "translate(" + f2(K[0]) + " " + f2(K[1]) + ") rotate(" + f2(phi) + ") translate(0 " + R.bouton_local + ")");
    dedans.setAttribute("ry", f2(8 + 0.75 * Math.abs(phi)));
    // vapeur : rien tant que la cloche est posée ; une bouffée libérée, puis les filets (intensité qui s'installe)
    const q = u - V.depart, actif = q > 0 && u < T.cache + 0.4;
    const force = actif ? cl(q / 0.6, 0, 1) : 0, O = V.onde;
    bouffees.forEach(function (b) {
      const vie = ((q / V.vie + b.ph + b.k / V.bouffees) % 1 + 1) % 1;
      if (!actif || vie * V.vie > q) { b.p.setAttribute("d", ""); return; }      // une bouffée naît à la surface, jamais en l'air
      const pts = [];
      for (let k = 0; k <= 10; k++) {
        const hh = V.montee * vie - V.longueur * (k / 10) * (0.6 + 0.6 * vie);
        if (hh < 0) break;
        const hr = hh / V.montee, amp = O.amplitude[0] + (O.amplitude[1] - O.amplitude[0]) * hr;
        pts.push(f2(b.x + amp * sin(2 * PI * (hh / O.longueur - u / O.periode + b.i * 0.33)) + 12 * hr * sin(2 * PI * (u / 5 + b.i * 0.2))) + " " + f2(V.base - hh));
      }
      const alpha = sin(PI * vie) * cl(vie / 0.15, 0, 1) * force;
      if (pts.length < 2 || alpha < 0.02) { b.p.setAttribute("d", ""); return; }
      b.p.setAttribute("d", "M" + pts.join(" L"));
      b.p.setAttribute("stroke-width", f2(V.epaisseur[0] + (V.epaisseur[1] - V.epaisseur[0]) * vie));
      b.p.setAttribute("opacity", (0.75 * alpha).toFixed(3));
    });
    // la bouffée : un nuage festonné qui monte, gonfle et se défait (0,9 s)
    const bq = (u - T.leve[0] - 0.08) / 0.9;
    if (bq > 0 && bq < 1 && u < T.cache) {
      const cx = 300 + 20 * bq, cy = 430 - 190 * E.p3o(bq), r = 26 + 34 * bq, n = 7;
      let d = "";
      for (let k = 0; k <= n; k++) {
        const a = PI + k * PI / n, x = cx + r * 1.4 * cos(a), y = cy + r * 0.8 * sin(a);
        d += (k ? " A" + f2(r * 0.42) + " " + f2(r * 0.42) + " 0 0 1 " : "M") + f2(x) + " " + f2(y);
      }
      bouffe.setAttribute("d", d);
      bouffe.setAttribute("stroke-width", f2(9 - 5 * bq));
      bouffe.setAttribute("opacity", (0.8 * sin(PI * Math.min(1, bq * 1.3)) ).toFixed(3));
    } else bouffe.setAttribute("d", "");
  };
})();
