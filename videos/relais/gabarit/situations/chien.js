/* Animateur « chien » (toiletteur). τ = FX.tau(t, mode). Avant : le chien attend, la mousse respire, la queue remue à
   peine. Geste : il se tasse (élan, sio), puis s'ébroue à 5 Hz (le corps tourne autour du garrot, amplitude qui monte puis
   décroît), la tête suit avec un retard d'une image et plus d'amplitude, l'oreille encore plus (follow-through) ; à chaque
   extrême, une gerbe d'eau part en arc du côté où il tourne ; des bulles de mousse sautent ; il se calme. */
(function () {
  const REGLAGES = {
    garrot: [350, 380], tasse: [[-9, 0], [0.14, 0], [0.3, 8, "sio"], [0.38, -4, "p2o"], [1.1, 0, "sio"], [9, 0]],
    ebroue: { de: 0.34, a: 1.08, frequence: 5, amplitude: 14 },
    retard_tete: 0.035, gain_tete: 1.5, gain_oreille: 2.6,
    gouttes: { n: 6, forme: "goutte", couleur: "#DCE8EE", contour: "#262019", epaisseur: 3, taille: [10, 15], vitesse: [320, 520],
               ouverture: 0.9, gravite: 1300, duree: 0.55, trainee: 0.022 },
    mousse: [[178, 392, 14], [206, 386, 11], [236, 394, 16], [300, 390, 12], [332, 394, 15], [396, 388, 13], [430, 394, 16], [470, 390, 12], [498, 394, 14]]
  };
  const R = REGLAGES, PI = Math.PI, NS = "http://www.w3.org/2000/svg", f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const chien = $("cn-chien"), tete = $("cn-tete"), oreille = $("cn-oreille"), queue = $("cn-queue");
  const bulles = R.mousse.map((m) => { const c = document.createElementNS(NS, "circle"); c.setAttribute("r", m[2]); $("cn-mousse").appendChild(c); return { c: c, m: m }; });
  const E = R.ebroue, demi = 0.5 / E.frequence, nGerbes = Math.floor((E.a - E.de) / demi);
  const gerbes = []; for (let i = 0; i < nGerbes; i++) gerbes.push(FX.particules(i % 2 ? $("cn-fx") : $("cn-fx-arriere"), Object.assign({}, R.gouttes, { graine: 31 + i * 13 })));
  function rot(T) {                              // rotation du corps (°) : amplitude en cloche sur la durée de l'ébrouement
    if (T < E.de || T > E.a) return 0;
    const s = (T - E.de) / (E.a - E.de), env = Math.sin(PI * Math.min(1, s * 1.6)) * (1 - 0.55 * s);
    return E.amplitude * env * Math.sin(2 * PI * E.frequence * (T - E.de));
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode);
    const [ta] = FX.cles(T, R.tasse), a = rot(T), at = rot(T - R.retard_tete) * R.gain_tete, ao = rot(T - 2 * R.retard_tete) * R.gain_oreille;
    chien.setAttribute("transform", "translate(0 " + f2(ta) + ") rotate(" + f2(a) + " " + R.garrot[0] + " " + R.garrot[1] + ")");
    tete.setAttribute("transform", "rotate(" + f2(at - a) + " 272 312)");
    oreille.setAttribute("transform", "rotate(" + f2(ao - at - 6 * Math.sin(2 * PI * t / 1.25)) + " 262 222)");
    queue.setAttribute("transform", "rotate(" + f2(8 * Math.sin(2 * PI * t / 0.625) + 2 * a) + " 466 346)");
    // gerbes : une par demi-oscillation, lancées du dos du côté vers lequel le chien tourne
    gerbes.forEach(function (g, i) {
      const t0 = E.de + demi * (i + 0.5), cote = i % 2 ? 1 : -1;
      const x = cote > 0 ? 440 : 226, y = cote > 0 ? 312 : 222;
      g(FX.fenetre(T, t0, R.gouttes.duree), x, y, cote > 0 ? -PI / 3 : -2 * PI / 3);
    });
    bulles.forEach(function (b, i) {
      const saut = T > E.de && T < E.a + 0.3 ? Math.abs(Math.sin(2 * PI * E.frequence * (T - E.de) + i)) * 10 * Math.max(0, 1 - (T - E.de) / 1.0) : 0;
      b.c.setAttribute("cx", b.m[0]); b.c.setAttribute("cy", f2(b.m[1] - saut + 1.5 * Math.sin(2 * PI * t / 2.5 + i)));
    });
  };
})();
