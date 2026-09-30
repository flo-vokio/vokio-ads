/* Animateur de la situation « lb-gerbe » (fleuriste, lot B, ton sobre). SITUATION_ANIM(t, periode, mode) : fonction pure
   du temps. Horloge u sur 10 s, qui part du retour de la situation dans la boucle (DONNEES.situation.revient) ; visible de
   u = 0 à u ≈ 3,2. Le ruban : les deux boucles naissent du nœud, s'ouvrent lentement (sinus, 1 s), la gauche puis la droite
   (décalage), pendant que les pans remontent (le ruban passe dans les boucles) ; les pans se balancent ensuite, à peine,
   et s'arrêtent. La feuille frémit, se détache, descend en feuille morte : balancement latéral, inclinaison liée au sens du
   balancement, chute lente. Complète : même horloge. */
(function () {
  const REGLAGES = {
    decalage_complete: 0.0,
    fleurs: [[170, 214, 50, 0], [300, 150, 56, 0], [410, 208, 50, 0], [136, 312, 42, 0], [450, 318, 42, 0]],
    noeud: { g: [0.22, 1.22], d: [0.4, 1.4], serre: [1.1, 1.5] },
    pans: { longueur_avant: 1.28, balance: 3.2, periode: 1.25, amorti: 0.75 },
    feuille: { attache: [338, 298], angle: 58, fremit: [1.05, 1.3], depart: 1.3, chute: 88, ampl: 38, periode: 1.25, incline: 30, derive: 16 }
  };
  const R = REGLAGES, PI = Math.PI, sin = Math.sin, cos = Math.cos, exp = Math.exp;
  const cl = (x, a, b) => Math.max(a, Math.min(b, x)), f2 = (v) => v.toFixed(2);
  const E = { sio: (x) => 0.5 - 0.5 * cos(PI * x) };
  const NS = "http://www.w3.org/2000/svg";
  const el = (p, tag, a) => { const e = document.createElementNS(NS, tag); for (const k in a) e.setAttribute(k, a[k]); p.appendChild(e); return e; };
  const D = window.DONNEES || { situation: {} };
  const RETOUR = D.situation && D.situation.revient != null ? D.situation.revient : 8.75;
  const $ = (i) => document.getElementById(i);
  // fleurs : pétales arrondis au trait, cœur plein
  const gF = $("gb-fleurs");
  R.fleurs.forEach(function (f) {             // roses de profil : coupe, pétales qui s'ouvrent, bouton serré au centre
    const k = f[2] / 50, a = Math.atan2(f[1] - 404, f[0] - 276) * 180 / PI + 90;
    const g = el(gF, "g", { transform: "translate(" + f[0] + " " + f[1] + ") rotate(" + f2(a) + ") scale(" + k.toFixed(3) + ") translate(0 -40)" });
    const at = { fill: "#F4F1E8", stroke: "#262019", "stroke-width": f2(6 / k), "stroke-linejoin": "round", "stroke-linecap": "round" };
    el(g, "path", Object.assign({ d: "M-48 -14 C -54 28 -26 54 0 54 C 26 54 54 28 48 -14 C 36 -30 18 -30 0 -16 C -18 -30 -36 -30 -48 -14 Z" }, at));
    el(g, "path", Object.assign({ d: "M-24 -20 C -26 -50 -6 -60 0 -60 C 8 -60 26 -50 24 -20 C 14 -8 -14 -8 -24 -20 Z" }, at));
    el(g, "path", Object.assign({ d: "M-42 8 C -24 26 24 26 42 8", fill: "none" }, at));
    el(g, "path", Object.assign({ d: "M-6 -46 C 2 -40 6 -30 2 -22", fill: "none" }, at));
  });
  const bg = $("gb-boucle-g"), bd = $("gb-boucle-d"), pg = $("gb-pan-g"), pd = $("gb-pan-d"), noeud = $("gb-noeud"), feuille = $("gb-feuille");
  const N = R.noeud, P = R.pans, F = R.feuille;
  const ouvre = (u, w) => E.sio(cl((u - w[0]) / (w[1] - w[0]), 0, 1));
  window.SITUATION_ANIM = function (t, periode, mode) {
    let u = mode === "complete" ? t + R.decalage_complete : ((t - RETOUR) % 10 + 10) % 10;
    const cache = u > 3.8;                        // caché : le nœud défait, la feuille remise
    const og = cache ? 0 : ouvre(u, N.g), od = cache ? 0 : ouvre(u, N.d);
    // une boucle naît repliée contre le nœud (petite, tournée vers le bas) et s'ouvre en tournant vers sa place
    bg.setAttribute("transform", "rotate(" + f2(-55 * (1 - og)) + ") scale(" + (0.08 + 0.92 * og).toFixed(4) + ")");
    bd.setAttribute("transform", "rotate(" + f2(55 * (1 - od)) + ") scale(" + (0.08 + 0.92 * od).toFixed(4) + ")");
    const serre = cache ? 0 : ouvre(u, N.serre);
    noeud.setAttribute("transform", "scale(" + (1.12 - 0.12 * serre).toFixed(4) + " " + (0.9 + 0.1 * serre).toFixed(4) + ")");
    // pans : longs avant le nœud, ils remontent pendant qu'il se fait, puis se balancent à peine (amorti)
    const lg = P.longueur_avant - (P.longueur_avant - 1) * og, ld = P.longueur_avant - (P.longueur_avant - 1) * od;
    const s = u - N.d[1], bal = !cache && s > 0 ? P.balance * exp(-s / P.amorti) * sin(2 * PI * s / P.periode) : 0;
    pg.setAttribute("transform", "rotate(" + f2(bal + 4 * (1 - og)) + ") scale(1 " + lg.toFixed(4) + ")");
    pd.setAttribute("transform", "rotate(" + f2(bal * 0.8 - 4 * (1 - od)) + ") scale(1 " + ld.toFixed(4) + ")");
    // feuille : frémit, se détache, descend en se balançant
    const A = F.attache;
    let x = A[0], y = A[1], rot = F.angle;
    if (!cache) {
      if (u >= F.fremit[0] && u < F.depart) rot += 3 * sin(2 * PI * (u - F.fremit[0]) / 0.1);
      if (u >= F.depart) {
        const q = u - F.depart, entre = cl(q / 0.5, 0, 1);          // le balancement s'installe (la feuille part de sa pose)
        const ph = 2 * PI * q / F.periode;
        x += F.ampl * sin(ph) * entre + F.derive * q;
        y += F.chute * q + 10 * entre * (1 - cos(2 * ph)) * 0.5;      // elle remonte un peu en bout de balancement
        rot = F.angle * (1 - entre) + (F.incline * cos(ph) + 90) * entre;
      }
    }
    feuille.setAttribute("transform", "translate(" + f2(x) + " " + f2(y) + ") rotate(" + f2(rot) + ")");
  };
})();
