/* Animateur « pancarte » (auto-école). τ = FX.tau(t, mode). Avant : « Ouvert », immobile, un souffle à peine.
   Geste : petite prise d'élan (la pancarte recule d'un rien), retournement en 0,3 s autour de l'axe vertical (la face
   s'amincit, l'autre apparaît : « Fermé », un peu plus sombre à la tranche), puis pendule amorti au bout de la ficelle ;
   les ficelles suivent. */
(function () {
  const REGLAGES = { axe: 300, clou: [300, 150], retourne: [0.26, 0.58], elan: [[-9, 0], [0.14, 0], [0.26, -3.5, "sio"], [9, -3.5]],
                     pendule: { t0: 0.52, amplitude: 11, periode: 0.9, amorti: 1.2 }, souffle: { amplitude: 1.2, periode: 2.5 } };
  const R = REGLAGES, PI = Math.PI, f2 = (v) => v.toFixed(2);
  const $ = (id) => document.getElementById(id);
  const plaque = $("pc-plaque"), texte = $("pc-texte"), fond = $("pc-fond"), pend = $("pc-pendule"), ficelles = $("pc-ficelles");
  window.SITUATION_ANIM = function (t, periode, mode) {
    const T = FX.tau(t, mode), [r0, r1] = R.retourne;
    const s = Math.max(0, Math.min(1, (T - r0) / (r1 - r0))), e = FX.EASE.sio(s);
    const k = Math.cos(PI * e);                       // 1 → 0 → −1 : la face s'amincit puis l'autre face s'ouvre
    texte.textContent = k >= 0 ? "Ouvert" : "Fermé";
    plaque.setAttribute("transform", "translate(" + R.axe + " 0) scale(" + Math.max(0.02, Math.abs(k)).toFixed(4) + " 1) translate(" + (-R.axe) + " 0)");
    fond.setAttribute("fill", Math.abs(k) < 0.35 ? "#E6DFD0" : "#F4F1E8");
    const lx = 124 * Math.max(0.02, Math.abs(k));          // les ficelles suivent les coins de la pancarte qui tourne
    ficelles.setAttribute("d", "M300 150 L " + f2(300 - lx) + " 262 M300 150 L " + f2(300 + lx) + " 262");
    let [a] = FX.cles(T, R.elan);
    if (T < r0) a += R.souffle.amplitude * Math.sin(2 * PI * t / R.souffle.periode);
    const P = R.pendule;
    a = T < P.t0 ? a : -3.5 * Math.exp(-(T - P.t0) * 2) + FX.pendule(T, P.t0, P.amplitude, P.periode, P.amorti);
    if (T >= 2.4) a = 0;                              // (hors champ) retour au repos avant la boucle suivante
    pend.setAttribute("transform", "rotate(" + f2(a) + " " + R.clou[0] + " " + R.clou[1] + ")");
  };
})();
