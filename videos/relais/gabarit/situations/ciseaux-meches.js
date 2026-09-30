/* Animateur « ciseaux-meches » (coiffure, reprise). Les lames sont animées par le gabarit (data-rot, période commune) ; ici,
   à chaque fermeture des lames (t = k × période), une mèche se détache au fil des lames et tombe en voletant (FX.chute :
   descente freinée, balancement, rotation qui suit le balancement), puis s'efface au sol. Dans la boucle, le temps de chute
   est pris modulo 10 s : les mèches de la fin de boucle sont celles qui tombent au début (raccord). */
(function () {
  const REGLAGES = { depart: [440, 226], chute: 1.5, vitesse: 220, amplitude: 30, pulsation: 7.5, tour: 70, sol: 560,
                     brins: [[-16, 3], [-8, -2], [0, 4], [8, -1], [16, 2]], longueur: 84 };
  const R = REGLAGES, NS = "http://www.w3.org/2000/svg", f2 = (v) => v.toFixed(2);
  const g = document.getElementById("cm-meches");
  const meches = []; for (let i = 0; i < 16; i++) { const p = document.createElementNS(NS, "path"); g.appendChild(p); meches.push(p); }
  function meche(x, y, rot, k) {                 // trois brins courbes (une mèche), orientés par rot
    const a = rot * Math.PI / 180, c = Math.cos(a), s = Math.sin(a), P = (u, v) => f2(x + u * c - v * s) + " " + f2(y + u * s + v * c);
    return R.brins.map((b, i) => { const off = b[0] * 0.5, cb = b[1] + 2 * Math.sin(k + i), dl = (i % 2) * 6;   // brins côte à côte
      return "M" + P(-R.longueur / 2 + dl, off) + " Q" + P(0, off + cb * 2.2) + " " + P(R.longueur / 2 - dl, off - cb); }).join(" ");
  }
  window.SITUATION_ANIM = function (t, periode, mode) {
    const N = mode === "boucle" ? Math.round(10 / periode) : 6;
    for (let i = 0; i < meches.length; i++) {
      const p = meches[i];
      if (i >= N + (mode === "boucle" ? 0 : 3)) { p.setAttribute("d", ""); continue; }
      const j = mode === "boucle" ? i : i - 3;
      let s = t - j * periode;
      if (mode === "boucle") s = ((s % 10) + 10) % 10;
      if (s < 0 || s > R.chute) { p.setAttribute("d", ""); continue; }
      const c = FX.chute(s, { x: R.depart[0] + (j % 3) * 6, y: R.depart[1], vitesse: R.vitesse, amplitude: R.amplitude, pulsation: R.pulsation, tour: R.tour * (j % 2 ? 1 : -1), phase: j });
      p.setAttribute("d", meche(c.x, Math.min(c.y, R.sol), c.rot - 28, j));
      p.setAttribute("opacity", (s > R.chute - 0.3 ? (R.chute - s) / 0.3 : 1).toFixed(3));
    }
  };
})();
