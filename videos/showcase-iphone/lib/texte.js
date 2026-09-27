/* lib/texte.js · « Le point sur le i » · révélation de mots calée sur la voix (DONNEES.mots)
 *
 * Chargé UNE fois par la racine (index.html), après donnees/donnees.js et GSAP : window.TEXTE existe
 * quand le script d'une sous-composition s'exécute. Rien à inclure dans les scènes (si une scène ajoute
 * quand même <script src="lib/texte.js">, c'est sans effet : le fichier est idempotent).
 *
 * Tous les temps passés à ces fonctions et rendus par elles sont en SECONDES FILM, sauf mention
 * « local » (= temps dans la sous-composition = film − DONNEES.scenes[id].debut).
 *
 *   const s = TEXTE.scene("s2-voix");                   // {debut, fin, duree, local(t), film(t)}
 *   const p = TEXTE.poser("#s2-p1", ["Bonjour, je suis Élise,"], { extrait: "A1" });
 *   TEXTE.reveler(tl, p, { scene: "s2-voix" });          // chaque mot monte à son attaque mesurée
 *   TEXTE.sortir(tl, p, s.local(6.45), { duree: 0.15 }); // sortie de page par le masque, vers le bas
 *
 * Structure produite par TEXTE.poser dans le conteneur (le conteneur garde SA police et SA position) :
 *   <span class="tx-ligne">                 bloc ; clip-path inset(-.3em -.12em -.24em -.12em) = le masque de ligne
 *                                           (déborde de la boîte sans toucher la mise en page, jambages compris)
 *     <span class="tx-w" data-cle="bonjour">Bonjour,</span> <span class="tx-w">je</span> …
 *   </span>
 * Un « mot » affiché peut grouper plusieurs mots dits liés par une espace insécable U+00A0
 * (« mon chat, ») : ils forment une seule unité .tx-w, calée sur le premier mot dit.
 * L'espace fine U+202F (avant ? ! : et dans « 59 € ») n'existe pas dans nos woff2 : elle est rendue
 * par un <span class="tx-fine"> de 0,16 em, insécable.
 *
 * Règle 8 (texte montré = sous-suite du texte dit) : chaque mot affiché est cherché, dans l'ordre, parmi
 * les mots dits de l'extrait (clé normalisée : minuscules, sans accents ni ponctuation, ’ = ').
 * Un mot introuvable LÈVE une erreur (visible dans hf check) : on ne montre jamais un mot non dit.
 */
(function () {
  if (window.TEXTE) return;
  const D = window.DONNEES;
  if (!D) throw new Error("lib/texte.js : window.DONNEES absent (donnees/donnees.js doit être chargé avant)");
  const FPS = D.fps || 30;

  // CSS du masque, injecté une fois
  if (!document.getElementById("tx-style")) {
    const st = document.createElement("style");
    st.id = "tx-style";
    st.textContent =
      ".tx-ligne{display:block;white-space:nowrap;clip-path:inset(-.3em -.12em -.24em -.12em)}" +
      ".tx-w{display:inline-block}" +
      ".tx-fine{display:inline-block;width:.16em}";
    document.head.appendChild(st);
  }

  function cle(m) {
    return String(m).replace(/’/g, "'").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9'\-]/g, "").replace(/^['\-]+|['\-]+$/g, "");
  }

  function mots(extrait) {
    return D.mots.filter(function (m) { return m.extrait === extrait; });
  }

  // Le mot dit n° k (rang dans l'extrait) ou le premier mot de clé donnée à partir d'un rang.
  function mot(extrait, quoi, depuis) {
    const liste = mots(extrait);
    if (typeof quoi === "number") return liste[quoi];
    const c = cle(quoi);
    const m = liste.find(function (w) { return w.rang >= (depuis || 0) && w.cle === c; });
    if (!m) throw new Error("TEXTE.mot : « " + quoi + " » introuvable dans l'extrait " + extrait);
    return m;
  }

  function scene(id) {
    const s = D.scenes[id];
    if (!s) throw new Error("TEXTE.scene : scène inconnue " + id);
    return {
      id: id, debut: s.debut, fin: s.fin, duree: s.duree,
      local: function (tFilm) { return +(tFilm - s.debut).toFixed(6); },
      film: function (tLocal) { return +(tLocal + s.debut).toFixed(6); },
    };
  }

  function image(t) { return Math.round(t * FPS); }
  function aImage(t) { return Math.round(t * FPS) / FPS; }   // arrondi à l'image (film)

  // Construit les lignes dans le conteneur et apparie chaque unité affichée à ses mots dits.
  // options : { extrait (null = texte non dit), depuis (rang de départ, défaut 0),
  //             classe (classe ajoutée à chaque .tx-w), espaceur: { id, em } (inline-block vide en fin
  //             de dernière unité, hauteur 0 : son bord bas = ligne de base),
  //             chevauchement: true → data-layout-allow-overlap sur chaque .tx-w (interlignage < 1,3 em :
  //             les boîtes de police se chevauchent d'une ligne à l'autre, hf check le signale sinon) }
  function poser(conteneur, lignes, options) {
    const o = options || {};
    const el = typeof conteneur === "string" ? document.querySelector(conteneur) : conteneur;
    if (!el) throw new Error("TEXTE.poser : conteneur introuvable " + conteneur);
    const dits = o.extrait ? mots(o.extrait) : null;
    let curseur = o.depuis || 0;
    const sortie = { conteneur: el, lignes: [], mots: [] };
    el.textContent = "";
    lignes.forEach(function (texte, il) {
      const ligne = document.createElement("span");
      ligne.className = "tx-ligne";
      ligne.dataset.ligne = String(il);
      const unites = texte.split(" ").filter(function (u) { return u.length; });
      unites.forEach(function (u, iu) {
        const w = document.createElement("span");
        w.className = "tx-w" + (o.classe ? " " + o.classe : "");
        if (o.chevauchement) w.setAttribute("data-layout-allow-overlap", "");
        // espace fine U+202F → span insécable de largeur fixe
        u.split(" ").forEach(function (morceau, k) {
          if (k > 0) { const f = document.createElement("span"); f.className = "tx-fine"; w.appendChild(f); }
          w.appendChild(document.createTextNode(morceau));
        });
        const entree = { el: w, texte: u, ligne: il, mots: [], mot: null, t: null };
        if (dits) {
          u.split(" ").forEach(function (sous) {
            const c = cle(sous.replace(/ /g, ""));
            if (!c) return;   // ponctuation seule
            let k = curseur;
            while (k < dits.length && dits[k].cle !== c) k++;
            if (k >= dits.length) {
              throw new Error("TEXTE.poser : « " + sous + " » n'est pas dit dans l'extrait " + o.extrait +
                " après le rang " + curseur + " (règle 8 : le texte montré doit être une sous-suite du texte dit)");
            }
            entree.mots.push(dits[k]);
            curseur = k + 1;
          });
          entree.mot = entree.mots[0] || null;
          entree.t = entree.mot ? entree.mot.debut : null;
          if (entree.mot) w.dataset.cle = entree.mot.cle;
        }
        ligne.appendChild(w);
        if (iu < unites.length - 1) ligne.appendChild(document.createTextNode(" "));
        sortie.mots.push(entree);
      });
      el.appendChild(ligne);
      sortie.lignes.push(ligne);
    });
    if (o.espaceur) {
      const dern = sortie.mots[sortie.mots.length - 1].el;
      const sp = document.createElement("span");
      sp.id = o.espaceur.id;
      sp.style.cssText = "display:inline-block;width:" + (o.espaceur.em || 0.213) + "em;height:0";
      dern.appendChild(sp);
    }
    sortie.curseur = curseur;
    return sortie;
  }

  // Chaque unité monte de dy px et apparaît, à l'attaque de son premier mot dit (arrondie à l'image).
  // CALAGE COMMUN (arbitrage de l'assemblage, 26/09) : pour un mot DIT, le tween part UNE image avant
  // l'image de son attaque. Un tween qui part à l'image n y est encore à l'opacité 0 : sans cette avance,
  // le mot n'apparaissait qu'à l'image n + 1, 17 à 50 ms APRÈS le son (l'œil tolère mal une image en
  // retard sur la voix). Avec elle, la première image visible (≈ 40 %, 9 px sous sa place) est celle qui
  // contient l'attaque mesurée : ±17 ms. Même règle que s3 (C1/C2) et que la signature de s7.
  // Un texte NON dit (options.t) garde decalage 0 : son instant est une décision d'image, pas une voix.
  // options : { scene (id, obligatoire sauf origine), origine (s film, défaut = début de la scène),
  //             decalage (s ; défaut −1 image pour un mot dit, 0 pour options.t), duree (0,26), dy (16), ease ("power3.out"),
  //             t (s FILM : impose un instant unique pour les unités sans mot dit), pas (s entre unités sans mot) }
  function reveler(tl, pose, options) {
    const o = options || {};
    const origine = o.origine != null ? o.origine : scene(o.scene).debut;
    const dur = o.duree != null ? o.duree : 0.26;
    const dy = o.dy != null ? o.dy : 16;
    const ease = o.ease || "power3.out";
    const liste = pose.mots || pose;
    liste.forEach(function (u, i) {
      let t = u.t;
      let dec = o.decalage != null ? o.decalage : -1 / FPS;
      if (t == null) {
        if (o.t == null) throw new Error("TEXTE.reveler : « " + u.texte + " » n'a pas de mot dit ; passer options.t");
        t = o.t + i * (o.pas || 0);
        dec = o.decalage || 0;
      }
      const tl0 = Math.max(0, aImage(t + dec) - origine);
      tl.fromTo(u.el, { y: dy, opacity: 0 }, { y: 0, opacity: 1, duration: dur, ease: ease, immediateRender: true }, tl0);
    });
    return tl;
  }

  // Sortie par le masque vers le bas, au temps LOCAL tLocal. yPercent 130 par défaut : le masque déborde
  // de 0,24 em sous la ligne (pour ne pas rogner les jambages au repos), 110 % laisserait un liseré.
  // (Pas de padding + marge négative pour ce débord : les marges négatives de deux lignes voisines
  // fusionnent et décalent la 2e ligne, mesuré : +20 px à 200 px de corps.)
  // options : { duree (0,18), ease ("power3.in"), pas (stagger, 0), vers ("bas" | "haut"), yPercent (130) }
  // COUPE (rendu final, 27/09, demande transverse de s4) : un mot enfoncé de plus de 70 % de sa hauteur ne montre
  // plus que ses hauts (points des i, accents, fûts) : sur l'avant-dernière image d'une sortie de 0,15 à 0,26 s,
  // ça faisait des POINTS ISOLÉS sur le papier (images 137, 138, 458, 1016 du rendu de 03:14), dans un film sur un
  // point. Chaque mot passe donc à l'opacité 0 à l'instant exact où il atteint 70 % (inverse de l'ease, par
  // dichotomie). Les instants de départ et de fin des sorties ne changent pas ; au plus une image est retirée.
  // Estimé sur les métriques (Geist 72/84, Instrument Serif 96/104 et 200/184) : à 70 %, il reste 9 à 29 px du haut des
  // minuscules, le mot se lit « qui s'enfonce » ; les éclats n'apparaissent qu'au-delà de 81 à 86 %. Vérifié sur le rendu du
  // 27/09 (05:19) : plus aucun éclat aux images 137-138 (s1), 457-458 (s3) et 1015-1016 (s6). options.coupe = false la retire.
  const COUPE_PCT = 70;
  function sortir(tl, pose, tLocal, options) {
    const o = options || {};
    const els = (pose.mots || pose).map(function (u) { return u.el || u; });
    const yp = o.yPercent != null ? o.yPercent : 130;
    const duree = o.duree != null ? o.duree : 0.18;
    const nomEase = o.ease || "power3.in";
    tl.to(els, { yPercent: o.vers === "haut" ? -yp : yp, duration: duree, ease: nomEase, stagger: o.pas || 0 }, tLocal);
    if (o.coupe !== false && yp > COUPE_PCT) {
      const e = gsap.parseEase(nomEase);
      let a = 0, b = 1;
      for (let k = 0; k < 40; k++) { const m = (a + b) / 2; if (e(m) * yp >= COUPE_PCT) b = m; else a = m; }
      els.forEach(function (el, i) { tl.set(el, { opacity: 0 }, tLocal + i * (o.pas || 0) + duree * b); });
    }
    return tl;
  }

  window.TEXTE = { cle: cle, mots: mots, mot: mot, scene: scene, image: image, aImage: aImage,
                   poser: poser, reveler: reveler, sortir: sortir, FPS: FPS };
})();
