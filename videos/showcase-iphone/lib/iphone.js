/* lib/iphone.js · « Le point sur le i », VERSION iPHONE (27/09) · l'objet téléphone de s6, construit d'après DONNEES.geometrie.s6
 *
 * Chargé UNE fois par la racine (index.html), après donnees/donnees.js, GSAP, lib/texte.js et lib/point.js. Utilisé par
 * compositions/s6-sms.html, qui garde le minutage, le sous-titre, l'éclosion et tous les contrôles de la v2. Rien d'animé ici :
 * ce fichier pose une fois les chemins statiques de l'iPhone (fonctions pures de la géométrie) et vérifie la coupe du SMS.
 *
 *   IPHONE.arrondi(x, y, w, h, r, lissage)  → chemin SVG d'un rectangle aux coins continus (courbure sans cassure, comme les
 *                                             coins d'Apple ; algorithme des « squircles » de Figma : l'arc central couvre
 *                                             90°(1 − lissage), deux cubiques le raccordent aux côtés)
 *   IPHONE.construire(G6)                   → pose le corps (#s6-couches), les boutons (#s6-boutons), la découpe de l'écran
 *                                             (#s6-ecran) et la forme de la bulle (#s6-forme-bulle) ; rend {bx, by, bw, bh}
 *                                             (la bulle en coordonnées de l'écran, px)
 *   IPHONE.controlerCoupe(G6, bulle, ecran) → après le chargement d'Inter : chaque ligne du SMS tient dans texte_max_pt et le
 *                                             premier mot de la suivante n'y tenait pas (la coupe d'iOS, au plus long) ; la
 *                                             ligne la plus longue vaut largeur_texte_pt. Erreurs dans la console (hf check).
 *   IPHONE.controlerContenu(G6, bulle, exiger) → le SMS (gabarit corrigé, six lignes = DONNEES), la date soulignée, l'expéditeur
 *                                             réel « Vokio », corps et place du texte ; rend {x0, y0} du texte (écran, px)
 *   IPHONE.fonduTexte(B, T, exiger)         → l'opacité du texte et de la mention (fonction pure du temps film) : 0 tant que
 *                                             le disque de l'éclosion ne couvre pas TOUTE la boîte du texte, puis fondu
 *                                             jusqu'à l'ouverture de la forme (aucune lettre coupée par le bord du disque)
 *   IPHONE.controlerSortie(etat, n0, n1, enImage, exiger) → la sortie sans fantôme : opaque tant qu'il n'a pas monté de 4 px,
 *                                             jamais sous 0,5 d'opacité sans avancer d'au moins 12 px par image
 *   IPHONE.controlerDepart(G6, etat, n0, n1, enImage, exiger) → le départ du point vers le stylo (relecture du 27/09) : tant
 *                                             que le téléphone est visible, le disque (étirement compris, pris rond au plus
 *                                             grand axe) reste à ≥ 6 px de la bulle qui monte avec lui (coins de 20 pt) et de
 *                                             sa queue ; rend l'écart minimal en px
 */
(function () {
  if (window.IPHONE) return;
  const NS = "http://www.w3.org/2000/svg";
  const f3 = function (v) { return +v.toFixed(3); };

  function arrondi(x, y, w, h, r, xi) {
    const rad = function (d) { return d * Math.PI / 180; };
    const p = Math.min((1 + xi) * r, Math.min(w, h) / 2);
    const arc = 90 * (1 - xi);
    const lArc = Math.sin(rad(arc / 2)) * r * Math.SQRT2;
    const alpha = (90 - arc) / 2;
    const p34 = r * Math.tan(rad(alpha / 2));
    const beta = 45 * xi;
    const c = p34 * Math.cos(rad(beta));
    const d = c * Math.tan(rad(beta));
    const b = (p - lArc - c - d) / 3, a = 2 * b;
    const f = f3;
    return "M" + f(x + w - p) + " " + f(y) +
      " c" + f(a) + " 0 " + f(a + b) + " 0 " + f(a + b + c) + " " + f(d) + " a" + f(r) + " " + f(r) + " 0 0 1 " + f(lArc) + " " + f(lArc) +
      " c" + f(d) + " " + f(c) + " " + f(d) + " " + f(b + c) + " " + f(d) + " " + f(a + b + c) +
      " L" + f(x + w) + " " + f(y + h - p) +
      " c0 " + f(a) + " 0 " + f(a + b) + " " + f(-d) + " " + f(a + b + c) + " a" + f(r) + " " + f(r) + " 0 0 1 " + f(-lArc) + " " + f(lArc) +
      " c" + f(-c) + " " + f(d) + " " + f(-(b + c)) + " " + f(d) + " " + f(-(a + b + c)) + " " + f(d) +
      " L" + f(x + p) + " " + f(y + h) +
      " c" + f(-a) + " 0 " + f(-(a + b)) + " 0 " + f(-(a + b + c)) + " " + f(-d) + " a" + f(r) + " " + f(r) + " 0 0 1 " + f(-lArc) + " " + f(-lArc) +
      " c" + f(-d) + " " + f(-c) + " " + f(-d) + " " + f(-(b + c)) + " " + f(-d) + " " + f(-(a + b + c)) +
      " L" + f(x) + " " + f(y + p) +
      " c0 " + f(-a) + " 0 " + f(-(a + b)) + " " + f(d) + " " + f(-(a + b + c)) + " a" + f(r) + " " + f(r) + " 0 0 1 " + f(lArc) + " " + f(-lArc) +
      " c" + f(c) + " " + f(-d) + " " + f(b + c) + " " + f(-d) + " " + f(a + b + c) + " " + f(-d) + " Z";
  }

  function construire(G6) {
    const TEL = G6.telephone, ECR = G6.ecran, BU = G6.bulle, K = G6.pt;
    const W = TEL.largeur, H = TEL.hauteur, XI = TEL.lissage;
    // Le corps : titane naturel (bord extérieur ombré, reflet, arête intérieure), lèvre sombre, bord noir du verre ;
    // chaque couche est concentrique à la précédente (retrait en px, rayon diminué d'autant).
    const COUCHES = [[0, "#8E8A83"], [1.5, "#C9C5BE"], [3, "url(#s6-titane)"], [5.5, "#BDB9B1"], [8.5, "#6A6862"], [10, "#242424"], [12.5, "#050505"]];
    const gC = document.getElementById("s6-couches");
    COUCHES.forEach(function (c) {
      const e = document.createElementNS(NS, "path");
      e.setAttribute("d", arrondi(c[0], c[0], W - 2 * c[0], H - 2 * c[0], TEL.rayon - c[0], XI)); e.setAttribute("fill", c[1]);
      gC.appendChild(e);
    });
    // Les boutons (Action, volume +, volume −, à gauche ; bouton latéral à droite), 6 px de relief, placés d'après la photo
    // de presse d'Apple (fractions de la hauteur du corps).
    const gB = document.getElementById("s6-boutons");
    [[-6, 0.205, 0.2497], [-6, 0.285, 0.359], [-6, 0.380, 0.453], [W - 4, 0.311, 0.429]].forEach(function (b) {
      const r = document.createElementNS(NS, "rect");
      r.setAttribute("x", b[0]); r.setAttribute("y", (b[1] * H).toFixed(1)); r.setAttribute("width", 10);
      r.setAttribute("height", ((b[2] - b[1]) * H).toFixed(1)); r.setAttribute("rx", 3); r.setAttribute("fill", "url(#s6-bouton)");
      gB.appendChild(r);
    });
    // La fente de l'écouteur, entre le cadre et le verre, au milieu du bord haut (21 % de la largeur, comme sur l'appareil).
    const fente = document.createElementNS(NS, "rect");
    fente.setAttribute("x", f3(W * 0.395)); fente.setAttribute("y", 5.6); fente.setAttribute("width", f3(W * 0.21)); fente.setAttribute("height", 2.4);
    fente.setAttribute("rx", 1.2); fente.setAttribute("fill", "#4A4843");
    gC.appendChild(fente);
    // L'écran : mêmes coins continus, concentriques au corps.
    document.getElementById("s6-ecran").style.clipPath = "path('" + arrondi(0, 0, ECR.largeur, ECR.hauteur, ECR.rayon, XI) + "')";
    // La bulle reçue (iOS 26) : coins de 20 pt ; la queue, relevée au pixel sur la photo de presse, prend le coin bas gauche
    // à 10,5 pt du bord : son flanc gauche descend droit, sa pointe (9 pt ; 7,1 pt sous le bas) revient un peu vers la
    // gauche, son flanc droit remonte presque droit et rejoint le bas de la bulle à 24 pt. Coordonnées de l'écran (px).
    const bx = BU.x0 - ECR.x0, by = BU.haut - ECR.haut, bw = BU.largeur, bh = BU.hauteur, rb = BU.rayon_pt * K;
    const q = function (u, v) { return f3(bx + u * K) + " " + f3(by + bh + v * K); };   // (pt depuis le coin bas gauche)
    const A = function (x, y) { return " A" + f3(rb) + " " + f3(rb) + " 0 0 1 " + f3(x) + " " + f3(y); };
    const d = "M" + f3(bx + rb) + " " + f3(by) + " H" + f3(bx + bw - rb) + A(bx + bw, by + rb) +
      " V" + f3(by + bh - rb) + A(bx + bw - rb, by + bh) + " H" + f3(bx + 24 * K) +
      " C" + q(20.5, 0) + " " + q(15, 3.6) + " " + q(BU.queue_pointe_pt[0], BU.queue_pointe_pt[1]) +
      " C" + q(8.4, 6.2) + " " + q(10.5, 4.8) + " " + q(10.5, 3.3) +
      " L" + q(10.5, -(BU.rayon_pt - Math.sqrt(BU.rayon_pt * BU.rayon_pt - Math.pow(BU.rayon_pt - 10.5, 2)))) +
      A(bx, by + bh - rb) + " V" + f3(by + rb) + A(bx + rb, by) + " Z";
    document.getElementById("s6-forme-bulle").setAttribute("d", d);
    return { bx: bx, by: by, bw: bw, bh: bh };
  }

  function controlerCoupe(G6, bulle, ecran) {
    const BU = G6.bulle, K = G6.pt, MAX = BU.texte_max_pt;
    const corps = getComputedStyle(bulle).fontSize;
    function controler() {
      const erreurs = [];
      const sonde = document.createElement("span");
      sonde.style.cssText = "position:absolute;left:0;top:0;visibility:hidden;white-space:pre;font:400 " + corps + ' "Inter";letter-spacing:-.013em';
      sonde.style.fontVariationSettings = '"opsz" 17';
      ecran.appendChild(sonde);
      const largeur = function (t) { sonde.textContent = t; return sonde.getBoundingClientRect().width / K; };
      const lignes = Array.from(bulle.querySelectorAll(".s6-l"));
      let plusLongue = 0;
      lignes.forEach(function (el, i) {
        const l = el.textContent, rg = document.createRange();
        rg.selectNodeContents(el);
        const w = rg.getBoundingClientRect().width / K;                       // la ligne rendue, telle quelle
        plusLongue = Math.max(plusLongue, w);
        if (Math.abs(w - largeur(l)) > 0.05) erreurs.push("la sonde ne mesure pas comme la bulle (« " + l + " »)");
        if (w > MAX) erreurs.push("ligne « " + l + " » de " + w.toFixed(2) + " pt > " + MAX);
        if (i < lignes.length - 1) {
          const suivant = lignes[i + 1].textContent.split(" ")[0], w2 = largeur(l + " " + suivant);
          if (w2 <= MAX) erreurs.push("« " + suivant + " » tiendrait sur la ligne « " + l + " » (" + w2.toFixed(2) + " pt)");
        }
      });
      if (Math.abs(plusLongue - BU.largeur_texte_pt) > 0.3) erreurs.push("ligne la plus longue " + plusLongue.toFixed(2) + " pt ≠ " + BU.largeur_texte_pt);
      ecran.removeChild(sonde);
      if (erreurs.length) console.error("s6-sms : " + erreurs.join(" ; "));
      window.__s6Controle = { mesure: true, plus_longue_pt: +plusLongue.toFixed(3), erreurs: erreurs };
    }
    if (document.fonts && document.fonts.load) {
      document.fonts.load("400 " + corps + ' "Inter"').then(function () { return document.fonts.ready; }).then(controler)
        .catch(function (e) { console.error("s6-sms : contrôle impossible, " + e); });
    }
  }

  // Le contenu de l'écran, contrôlé une fois (ne change rien).
  const SMS = "Bonjour Florian, votre rendez-vous est confirmé : Consultation vétérinaire, le samedi 19 septembre " +
              "à 09:00, Clinique vétérinaire du Port. Démo Vokio, RDV fictif.";      // la formulation corrigée du gabarit
  function controlerContenu(G6, bulle, exiger) {
    const BU = G6.bulle, K = G6.pt;
    const lignes = Array.from(bulle.querySelectorAll(".s6-l")).map(function (l) { return l.textContent; });
    exiger(lignes.join(" ") === SMS, "le texte de la bulle n'est pas le SMS corrigé");
    exiger(lignes.join("|") === BU.lignes.join("|"), "les lignes de la bulle ≠ DONNEES.geometrie.s6.bulle.lignes");
    exiger(bulle.textContent === lignes.join(""), "du texte hors des lignes de la bulle");
    // la date détectée par Messages : soulignée dans la 4e ligne, sans rien changer au texte ni aux largeurs
    const date = bulle.querySelector("u.s6-date");
    exiger(date && date.textContent === "samedi 19 septembre à 09:00" && date.parentNode.textContent === BU.lignes[3],
           "la date soulignée n'est pas « samedi 19 septembre à 09:00 » dans la 4e ligne");
    // l'expéditeur : alphanumérique réel (≤ 11 caractères : lettres, chiffres, espace), celui que le produit pose par défaut
    const nom = document.querySelector("#s6-nom span").textContent;
    exiger(/^[A-Za-z0-9 ]{1,11}$/.test(nom) && nom === "Vokio", "expéditeur « " + nom + " » : attendu « Vokio » (alphanumérique ≤ 11)");
    const cs = getComputedStyle(bulle);
    exiger(Math.abs(parseFloat(cs.fontSize) - BU.corps_px) < 0.01 && parseFloat(cs.fontSize) >= 36, "corps du SMS ≠ 17 pt = 36,1 px");
    exiger(Math.abs(parseFloat(cs.lineHeight) - BU.interligne_px) < 0.01, "interligne du SMS ≠ 22 pt");
    exiger(Math.abs(parseFloat(cs.left) - (BU.gauche_pt + BU.padding_pt[3]) * K) < 0.01 &&
           Math.abs(parseFloat(cs.top) - (BU.haut_pt + BU.padding_pt[0]) * K) < 0.01, "texte du SMS mal placé dans la bulle");
    return { x0: parseFloat(cs.left), y0: parseFloat(cs.top) };
  }

  // B : {G6, bx, by, bw, bh (la bulle), x0, y0 (le texte), cx, cy (le centre du disque)}, en px de l'écran.
  // T : {rayon(tF), enImage(n), nBulle, nOuverte, tOuverte, ease, eps}. Boîte du texte : six lignes de 22 pt ; largeur = la
  // ligne la plus longue (remesurée par controlerCoupe à 0,3 pt près) + 0,5 pt. Le fondu finit à l'ouverture de la forme.
  function fonduTexte(B, T, exiger) {
    const BU = B.G6.bulle, K = B.G6.pt;
    const x1 = B.x0 + (BU.largeur_texte_pt + 0.5) * K, y1 = B.y0 + BU.lignes.length * BU.interligne_px;
    exiger(B.x0 > B.bx && x1 < B.bx + B.bw && B.y0 > B.by && y1 < B.by + B.bh, "la boîte du texte sort de la bulle");
    const R = Math.max.apply(null, [[B.x0, B.y0], [x1, B.y0], [x1, y1], [B.x0, y1]].map(function (c) { return Math.hypot(c[0] - B.cx, c[1] - B.cy); }));
    let n0 = T.nBulle;
    while (T.rayon(T.enImage(n0)) < R) n0++;
    const t0 = T.enImage(n0 - 1), t1 = T.tOuverte;
    function opacite(tF) {
      if (tF <= t0 + T.eps) return 0;
      if (tF >= t1 - T.eps) return 1;
      return T.ease((tF - t0) / (t1 - t0));
    }
    exiger(n0 > T.nBulle && T.nOuverte - n0 >= 4, "fondu du texte trop court (" + n0 + " → " + T.nOuverte + ")");
    exiger(opacite(T.enImage(n0 - 1)) === 0 && opacite(T.enImage(n0)) > 0 && opacite(t1) === 1, "le texte n'apparaît pas quand le disque l'a couvert");
    for (let n = T.nBulle - 1; n <= T.nOuverte; n++) {
      if (opacite(T.enImage(n)) > 0) exiger(T.rayon(T.enImage(n)) >= R, "le bord du disque couperait le texte à l'image " + n);
    }
    return { image: n0, rayon: R, opacite: opacite };
  }

  function controlerSortie(etat, n0, n1, enImage, exiger) {
    for (let n = n0; n < n1; n++) {
      const a = etat(enImage(n - 1)), b = etat(enImage(n));
      if (Math.abs(b.y) < 4) exiger(b.o >= 0.999, "l'iPhone s'efface avant de bouger (image " + n + ", o = " + b.o.toFixed(3) + ")");
      if (b.o < 0.5) exiger(Math.abs(b.y - a.y) >= 12, "l'iPhone est à moitié effacé sans vitesse (image " + n + ")");
    }
  }

  // Distance signée d'un point à un rectangle aux coins arrondis (négative dedans), en px film.
  function distanceRect(px, py, x0, y0, x1, y1, r) {
    const qx = Math.abs(px - (x0 + x1) / 2) - ((x1 - x0) / 2 - r), qy = Math.abs(py - (y0 + y1) / 2) - ((y1 - y0) / 2 - r);
    return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
  }
  function controlerDepart(G6, etat, n0, n1, enImage, exiger) {
    const BU = G6.bulle, K = G6.pt, MARGE = 6;
    let pire = Infinity;
    for (let n = n0; n < n1; n++) {
      const t = enImage(n), tel = etat(t), e = POINT.etat(t);
      if (tel.o <= 0.01) continue;
      const r = e.d / 2 * Math.max(e.sx, e.sy);
      const dB = distanceRect(e.x, e.y, BU.x0, BU.haut + tel.y, BU.x1, BU.bas + tel.y, BU.rayon_pt * K);
      const dQ = distanceRect(e.x, e.y, BU.x0 + 8 * K, BU.bas + tel.y - 1, BU.x0 + 24 * K, BU.queue_pointe.y + tel.y + 0.5, 0);
      const g = Math.min(dB, dQ) - r;
      pire = Math.min(pire, g);
      exiger(g >= MARGE, "au départ vers le stylo, le point touche la bulle à l'image " + n + " (écart " + g.toFixed(1) + " px < " + MARGE + ")");
    }
    return pire;
  }

  window.IPHONE = { arrondi: arrondi, construire: construire, controlerCoupe: controlerCoupe, controlerContenu: controlerContenu,
                    fonduTexte: fonduTexte, controlerSortie: controlerSortie, controlerDepart: controlerDepart };
})();
