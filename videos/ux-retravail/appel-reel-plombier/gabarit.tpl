<!doctype html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<title>L'appel réel · plombier · retravail HyperFrames</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
  @font-face{font-family:"Geist Mono";font-weight:400;font-style:normal;font-display:block;src:url("assets/fonts/GeistMono-Regular.woff2") format("woff2");}
  @font-face{font-family:"Geist";font-weight:400;font-style:normal;font-display:block;src:url("assets/fonts/Geist-Regular.woff2") format("woff2");}
  @font-face{font-family:"Instrument Serif";font-weight:400;font-style:normal;font-display:block;src:url("assets/fonts/InstrumentSerif-Regular.woff2") format("woff2");}
  @font-face{font-family:"Instrument Serif";font-weight:400;font-style:italic;font-display:block;src:url("assets/fonts/InstrumentSerif-Italic.woff2") format("woff2");}

  *{margin:0;padding:0;box-sizing:border-box}
  html,body{width:1080px;height:1920px;overflow:hidden;background:#F4F1E8}
  #root{position:relative;width:100%;height:100%;overflow:hidden;background:#F4F1E8;
        color:#262019;font-family:"Geist",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
  .clip{position:absolute;inset:0}

  /* le sol : papier + un halo solaire discret derrière la carte (frame.md, sun-bloom) */
  #sol{background:
      radial-gradient(60% 34% at 50% 46%, rgba(239,164,36,.11) 0%, rgba(248,214,155,.09) 42%,
                      rgba(245,198,119,.04) 68%, rgba(244,241,232,0) 100%), #F4F1E8}

  /* ── l'ouverture ── */
  #ouv-texte{position:absolute;left:90px;right:90px;top:780px;font-family:"Instrument Serif",serif;
             font-size:118px;line-height:1.02;letter-spacing:-.018em}
  #ouv-texte .l{display:block;overflow:hidden;padding:0 0 .14em;margin-bottom:-.14em}
  #ouv-texte .w{display:inline-block}
  #ouv-texte em{font-style:italic}

  /* ── l'état de la ligne : qui parle = typographie, pas de capitale mono ici ── */
  #etat{position:absolute;left:90px;top:146px;display:flex;align-items:center;font-size:36px;
        letter-spacing:.005em;color:rgba(38,32,25,.62)}
  #etat-point{position:relative;flex:none;width:16px;height:16px;margin-right:18px}
  #etat-point i{position:absolute;inset:0;border-radius:50%;background:#6E9C74}
  #etat-point b{position:absolute;inset:0;border-radius:50%;border:2px solid #6E9C74;opacity:0}
  #etat-point i.fini{background:#8A857C}
  #etat-textes{position:relative;height:44px;width:860px}
  #etat-textes span{position:absolute;left:0;top:0;white-space:nowrap;line-height:44px}

  /* ── les titres ── */
  .titre{position:absolute;left:90px;right:90px;top:222px;font-family:"Instrument Serif",serif;
         font-size:76px;line-height:1.06;letter-spacing:-.012em;color:#262019}
  .titre .l{display:block;overflow:hidden;padding:0 0 .16em;margin-bottom:-.16em}
  .titre .l > span{display:block}
  .titre .em{font-style:italic}

  /* ── la carte réelle, en trois couches ── */
  #carte{position:absolute;left:60px;top:440px;width:__CARTE_W__px;height:__CARTE_H__px}
  #carte-in{position:absolute;inset:0;border-radius:32px;overflow:hidden;
            box-shadow:0 0 0 1px rgba(38,32,25,.16)}
  #carte-in img{position:absolute;left:0;top:0;width:__CARTE_W__px;height:auto;display:block}
  #pastille{position:absolute;left:__PAST_X__px;top:__PAST_Y__px;width:__PAST_W__px}
  #pastille img{position:static;width:100%}
  #curseur{position:absolute;left:0;top:0;width:4px;height:__CUR_H__px;background:#EFA424;border-radius:2px}

  /* ── l'agenda du lendemain ── */
  #agenda{position:absolute;left:60px;top:440px;width:__AG_W__px;height:934px}
  #agenda-in{position:absolute;inset:0;border-radius:32px;overflow:hidden;box-shadow:0 0 0 1px rgba(38,32,25,.16)}
  #agenda-in img{position:absolute;left:0;top:0;width:__AG_W__px;height:auto;display:block;
                 transform-origin:__AG_FX__px __AG_FY__px}

  /* ── l'impact du mois ── */
  .plan{position:absolute;left:90px;width:900px}
  .plan div{border-radius:32px;overflow:hidden;box-shadow:0 0 0 1px rgba(38,32,25,.16)}
  .plan img{display:block;width:900px;height:auto}
  #p-nuit{top:414px} #p-rdv{top:894px}

  /* ── la fin, en clair ── */
  #clair-fond{background:
      radial-gradient(56% 26% at 50% 33%, rgba(239,164,36,.16) 0%, rgba(248,214,155,.12) 40%,
                      rgba(245,198,119,.05) 66%, rgba(251,249,242,0) 100%), #FBF9F2}
  #clair-dedans{position:absolute;left:90px;right:90px;top:470px;text-align:center}
  #clair-dedans .l{overflow:hidden;padding:0 0 .12em}
  #clair-dedans .l > *{display:inline-block}
  #clair-dedans .l:first-child{padding-top:.2em;margin-top:-.2em}
  #clair-dedans #fin-mot{display:inline-flex}
  .vk-word{font-family:"Instrument Serif",serif;font-weight:400;letter-spacing:-.045em;line-height:.9;
           font-size:210px;display:inline-flex;align-items:baseline;color:#262019}
  .vk-word .i{position:relative;font-style:normal}
  #point-i{position:absolute;left:63.5%;margin-left:-.055em;top:.13em;width:.11em;height:.11em;
           border-radius:50%;background:#EFA424}
  #prix{font-family:"Instrument Serif",serif;font-size:76px;line-height:1.1;margin-top:60px}
  #prix em{font-style:italic}
  #cta{margin-top:56px;font-size:44px;line-height:1.2}

  /* la mention, remontée au-dessus de l'interface Reels (deux <p> sans enfant) */
  .mention{position:absolute;left:60px;right:60px;text-align:center;font-size:36px;line-height:1;
           color:#716D66}
  #mention-1{top:1404px} #mention-2{top:1452px}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="__FIN_S__"
     data-width="1080" data-height="1920" data-fps="30">

  <div id="sol" class="clip" data-start="0" data-duration="__FIN_S__" data-track-index="0"></div>

  <div id="ouverture" class="clip" data-start="0" data-duration="1.6" data-track-index="1">
    <p id="ouv-texte" data-layout-allow-overflow><span class="l"><span class="w">Écoutez</span> <span class="w">Camille</span></span><span class="l"><em class="w">décrocher.</em></span></p>
  </div>

  <div id="etat-clip" class="clip" data-start="0" data-duration="72.6" data-track-index="2">
    <div id="etat"><div id="etat-point"><b></b><i></i></div><div id="etat-textes"><span id="etat-a" data-layout-allow-overlap>Appel réel · ligne de démonstration</span><span id="etat-b" data-layout-allow-overlap>Appel terminé · 1 min</span></div></div>
  </div>

  <div id="carte-clip" class="clip" data-start="1.4" data-duration="64.0" data-track-index="3">
    <div id="carte"><div id="carte-in">
      <img id="vide" src="assets/plans/carte-vide-sans-lien.png" alt="">
      <img id="plein" src="assets/plans/carte-pleine-sans-lien.png" alt="">
      <div id="pastille"><img src="assets/plans/pastille.png" alt=""></div>
      <div id="curseur"></div>
    </div></div>
  </div>

  <div id="agenda-clip" class="clip" data-start="65.3" data-duration="3.3" data-track-index="4">
    <div id="agenda"><div id="agenda-in"><img id="agenda-img" src="assets/plans/agenda-jour-entier.png" alt=""></div></div>
  </div>

  <div id="impact-clip" class="clip" data-start="68.5" data-duration="3.4" data-track-index="5">
    <div class="plan" id="p-nuit"><div><img src="assets/plans/impact-nuit.png" alt=""></div></div>
    <div class="plan" id="p-rdv"><div><img src="assets/plans/impact-rdv.png" alt=""></div></div>
  </div>

  <div id="titres" class="clip" data-start="0" data-duration="__FIN_S__" data-track-index="6">
    <div class="titre" data-layout-allow-overlap data-layout-allow-overflow id="t1"><span class="l"><span>Pendant qu'elle parle,</span></span><span class="l em"><span>l'écran se remplit.</span></span></div>
    <div class="titre" data-layout-allow-overlap data-layout-allow-overflow id="t2"><span class="l"><span>Elle a compris</span></span><span class="l em"><span>que c'est urgent.</span></span></div>
    <div class="titre" data-layout-allow-overlap data-layout-allow-overflow id="t3"><span class="l"><span>Elle note l'adresse.</span></span><span class="l em"><span>Vous n'êtes pas là.</span></span></div>
    <div class="titre" data-layout-allow-overlap data-layout-allow-overflow id="t4"><span class="l"><span>SMS envoyé.</span></span><span class="l em"><span>Le plombier de garde rappelle.</span></span></div>
    <div class="titre" data-layout-allow-overlap data-layout-allow-overflow id="t5"><span class="l"><span>Une minute.</span></span><span class="l em"><span>Vous n'avez rien eu à faire.</span></span></div>
    <div class="titre" data-layout-allow-overlap data-layout-allow-overflow id="t6"><span class="l"><span>Le lendemain,</span></span><span class="l em"><span>l'intervention est dans l'agenda.</span></span></div>
    <div class="titre" data-layout-allow-overlap data-layout-allow-overflow id="t7"><span class="l"><span>Et ce mois-ci,</span></span><span class="l em"><span>vous n'avez rien raté.</span></span></div>
  </div>

  <div id="clair" class="clip" data-start="71.7" data-duration="3.5" data-track-index="7">
    <div id="clair-fond" style="position:absolute;inset:0"></div>
    <div id="clair-dedans" data-layout-allow-overflow>
      <div class="l"><p class="vk-word" id="fin-mot">Vok<span class="i">ı<span id="point-i"></span></span>o</p></div>
      <div class="l"><p id="prix">59 € par mois, <em>sans engagement.</em></p></div>
      <div class="l"><p id="cta">Entendez-le vous-même sur vokio.fr</p></div>
    </div>
  </div>

  <div id="mentions" class="clip" data-start="0" data-duration="__FIN_S__" data-track-index="8">
    <p class="mention" id="mention-1">Établissement fictif de démonstration.</p>
    <p class="mention" id="mention-2">Appel réel, captures réelles de app.vokio.fr</p>
  </div>

  <!-- la piste de l'original, extraite sans réencodage (ffmpeg -vn -c:a copy) -->
  <audio id="appel" src="assets/appel.m4a" data-start="0" data-duration="__AUDIO_S__"
         data-track-index="10" data-volume="1"></audio>
</div>

<script>
(function(){
  const T = __T__;                 // ms, recalculés depuis monter_appel_reel.py, vérifiés contre l'original
  const MOTS = __MOTS__;           // position de chaque mot du résumé, px de la carte (960 de large)
  const ECRITURE = __ECRITURE__;   // [début ms, fin ms, mots déjà écrits, mots écrits à la fin]
  const S = ms => ms / 1000;
  const $ = s => document.querySelector(s);
  const E = "power3.out";
  const tl = gsap.timeline({ paused: true });

  // ── l'écriture mot à mot : la MÊME fonction du temps que l'original ──
  const lerp = (a,b,p) => a+(b-a)*p;
  const clamp = (x,a,b) => x<a?a:(x>b?b:x);
  function ecrits(t){
    let n = 0;
    for(const [a, b, de, vers] of ECRITURE){
      if(t >= b) n = vers;
      else if(t >= a){ n = lerp(de, vers, (t-a)/(b-a)); break; }
      else break;
    }
    return n;
  }
  const plein = $('#plein'), curseur = $('#curseur');
  const pointI = $('#etat-point i'), onde = $('#etat-point b');
  function dessiner(t){
    const n = ecrits(t);
    const k = Math.floor(n), frac = n - k;
    if(n <= 0){
      plein.style.clipPath = 'polygon(0 0, 0 0, 0 0)';
      curseur.style.opacity = '0';
      curseur.style.transform = `translate(${(MOTS[0].x + 6).toFixed(1)}px, ${(MOTS[0].y - 2).toFixed(1)}px)`;
    } else {
      const complet = k >= MOTS.length;
      const m = complet ? MOTS[MOTS.length-1] : MOTS[Math.min(k, MOTS.length-1)];
      const yTop = m.y - 4, yBot = m.y + m.h + 4;
      const xCur = complet ? m.x + m.w : (k === 0 && frac === 0 ? m.x : m.x + m.w * frac);
      const y0 = MOTS[0].y - 10;
      plein.style.clipPath = complet
        ? `polygon(0 ${y0}px, __CARTE_W__px ${y0}px, __CARTE_W__px 100%, 0 100%)`
        : `polygon(0 ${y0}px, __CARTE_W__px ${y0}px, __CARTE_W__px ${yTop}px, ${xCur.toFixed(1)}px ${yTop}px, ${xCur.toFixed(1)}px ${yBot}px, 0 ${yBot}px)`;
      const op = t < T.finEcriture ? 1 : 1 - clamp((t - T.finEcriture) / 900, 0, 1);
      curseur.style.opacity = op.toFixed(3);
      curseur.style.transform = `translate(${(xCur + 6).toFixed(1)}px, ${(m.y - 2).toFixed(1)}px)`;
    }
    // le point de la ligne : une onde lente tant que l'appel dure, éteint après
    const enCours = t < T.finParole;
    pointI.classList.toggle('fini', !enCours);
    const cyc = (t > T.etatIn && enCours) ? ((t - T.etatIn) % 2200) / 2200 : 1;
    const q = 1 - Math.pow(1 - clamp(cyc / .7, 0, 1), 3);
    onde.style.transform = `scale(${(1 + 1.6 * q).toFixed(3)})`;
    onde.style.opacity = (enCours ? .5 * (1 - q) : 0).toFixed(3);
  }
  const horloge = { t: 0 };
  tl.to(horloge, { t: T.fin, duration: S(T.fin), ease: "none",
                   onUpdate: () => dessiner(horloge.t) }, 0);
  dessiner(0);

  // ── l'ouverture : mot après mot, sous un masque ──
  tl.fromTo('#ouv-texte .w', { yPercent: 135 }, { yPercent: 0, duration: .8, ease: E, stagger: .11 }, S(150));
  tl.fromTo('#ouv-texte', { opacity: 1, y: 0 }, { opacity: 0, y: -28, duration: .5, ease: "power2.in" }, S(T.carteIn - 500));

  // ── l'état de la ligne ──
  tl.fromTo('#etat', { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: .7, ease: E }, S(T.etatIn));
  tl.fromTo('#etat-a', { opacity: 1 }, { opacity: 0, duration: .5, ease: "none" }, S(T.finParole));
  tl.fromTo('#etat-b', { opacity: 0 }, { opacity: 1, duration: .5, ease: "none" }, S(T.finParole));
  tl.fromTo('#etat', { opacity: 1 }, { opacity: 0, duration: .5, immediateRender: false, ease: "none" }, S(T.clairIn));

  // ── la carte : elle monte vide quand Camille décroche ──
  tl.fromTo('#carte', { opacity: 0, y: 70 }, { opacity: 1, y: 0, duration: 1.0, ease: E }, S(T.carteIn));
  tl.fromTo('#carte-in', { scale: 1 }, { scale: 1.02, duration: S(T.finParole - T.carteIn), ease: "sine.inOut" }, S(T.carteIn));
  tl.fromTo('#carte', { opacity: 1, y: 0 }, { opacity: 0, y: -40, duration: .6, ease: "power2.in", immediateRender: false }, S(T.agendaIn - 700));
  // la pastille URGENCE arrive quand Camille le dit
  tl.fromTo('#pastille', { opacity: 0, scale: .88 }, { opacity: 1, scale: 1, duration: .5, ease: E }, S(T.pastilleIn));

  // ── les titres : un à la fois, chaque ligne sort de son masque ──
  const titres = [
    ['#t1', T.t1In, T.t2In], ['#t2', T.t2In, T.t3In], ['#t3', T.t3In, T.t4In],
    ['#t4', T.t4In, T.t5In], ['#t5', T.t5In, T.agendaIn], ['#t6', T.agendaIn + 300, T.impactIn],
    ['#t7', T.impactIn + 300, T.clairIn - 400]
  ];
  for (const [id, a, b] of titres) {
    tl.fromTo(id, { opacity: 0 }, { opacity: 1, duration: .01, ease: "none" }, S(a));
    tl.fromTo(`${id} .l > span`, { yPercent: 135 }, { yPercent: 0, duration: .7, ease: E, stagger: .09 }, S(a));
    tl.fromTo(id, { opacity: 1, y: 0 }, { opacity: 0, y: -22, duration: .35, ease: "power2.in", immediateRender: false }, S(b - 350));
  }

  // ── l'agenda du lendemain, en entier et immobile : tous les rendez-vous restent lisibles ──
  tl.fromTo('#agenda', { opacity: 0, y: 90 }, { opacity: 1, y: 0, duration: .9, ease: E }, S(T.agendaIn));
  tl.fromTo('#agenda', { opacity: 1, y: 0 }, { opacity: 0, y: -40, duration: .5, ease: "power2.in", immediateRender: false }, S(T.impactIn - 600));

  // ── l'impact du mois ──
  tl.fromTo('#p-nuit', { opacity: 0, y: 80 }, { opacity: 1, y: 0, duration: .8, ease: E }, S(T.impactIn));
  tl.fromTo('#p-rdv', { opacity: 0, y: 80 }, { opacity: 1, y: 0, duration: .8, ease: E }, S(T.impactIn + 600));
  tl.fromTo('#p-nuit, #p-rdv', { opacity: 1, y: 0 }, { opacity: 0, y: -40, duration: .45, ease: "power2.in", immediateRender: false }, S(T.clairIn - 500));

  // ── la fin, en clair ──
  tl.fromTo('#clair-fond', { opacity: 0 }, { opacity: 1, duration: .8, ease: "sine.inOut" }, S(T.clairIn));
  tl.fromTo('#clair-dedans .l > *', { yPercent: 135 }, { yPercent: 0, duration: .62, ease: E, stagger: .52 }, S(T.finIn));
  tl.fromTo('#point-i', { scale: 0 }, { scale: 1, duration: .5, ease: E }, S(T.finIn + 450));

  window.__timelines["main"] = tl;
})();
</script>
</body>
</html>
