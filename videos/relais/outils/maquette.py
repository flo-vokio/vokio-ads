#!/usr/bin/env python3
"""Maquette d'intégration des vidéos du relais : une COPIE de la page d'accueil où les cartes des recettes portent leur
vidéo. Le site (/opt/vokio-site-repo, /opt/vokio-site) n'est JAMAIS touché : usage en une ligne :

    python3 outils/maquette.py <carte>/recette.json [<carte2>/recette.json …]     → maquette/index.html

  Chaque carte dont l'eyebrow (.n) vaut recette « carte » reçoit, en tête, une <figure class="rv"> (boucle muette en
  autoplay quand elle est à l'écran, poster, preload="none", playsinline ; au toucher la version complète avec le son) ;
  son lecteur audio devient le contrôle de la vidéo (même bouton lecture/pause, même barre, même temps restant).
  Les chemins sont ceux du site (/assets/relais/<nom>-…) : servis par outils/captures_maquette.py depuis
  /root/vokio-uploads/videos/relais/. Tout l'ajout est balisé « RELAIS-VIDEO » (CSS, HTML, JS) pour l'intégration.
"""
import json
import re
import sys
from pathlib import Path

SITE = Path("/opt/vokio-site-repo/index.html")
SORTIE = Path(__file__).resolve().parent.parent / "maquette" / "index.html"

CSS = """
  /* RELAIS-VIDEO · vidéo en tête de carte (les trois cartes de la section relais, 29/09) */
  .temps-card .rv{position:relative;margin:-32px -28px 26px;aspect-ratio:1/1;overflow:hidden;
    border-radius:var(--r-sm) var(--r-sm) 0 0;background:#F4F1E8;cursor:pointer}
  .temps-card .rv video,.temps-card .rv img{display:block;width:100%;height:100%;object-fit:cover}
  .rv-appel{position:absolute;left:12px;bottom:12px;display:inline-flex;align-items:center;gap:8px;border:0;cursor:pointer;
    padding:8px 13px 8px 10px;border-radius:999px;background:var(--noir);color:var(--ivoire);
    font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;transition:opacity .2s ease}
  .rv-appel svg{flex:none}
  .rv.complete .rv-appel{opacity:0;pointer-events:none}
  .rv:focus-visible,.rv-appel:focus-visible{outline:2px solid var(--solaire-2);outline-offset:2px}
  /* sur tablette (une colonne, carte large) : la vidéo ne dépasse pas 440 px, à gauche du texte */
  @media (min-width:560px) and (max-width:860px){
    .temps-card:has(.rv){display:grid;grid-template-columns:minmax(0,300px) 1fr;column-gap:28px;align-items:start}
    .temps-card:has(.rv) .rv{grid-row:1 / span 6;margin:-32px 0 -32px -28px;border-radius:var(--r-sm) 0 0 var(--r-sm);height:100%;aspect-ratio:auto;min-height:300px}
    .temps-card:has(.rv) > :not(.rv){grid-column:2}
  }
  @media (prefers-reduced-motion:reduce){.rv-appel{transition:none}}
"""

JS = r"""
  /* RELAIS-VIDEO · cartes vidéo de la section relais (maquette du 29/09).
     Boucle muette : jouée seulement quand la carte est à l'écran (IntersectionObserver), une seule vidéo à la fois
     (la plus visible), jamais si prefers-reduced-motion (poster fixe). Au toucher : l'appel complet, avec le son ;
     le lecteur de la carte devient son contrôle. Rien ne se charge avant d'être visible (preload="none"). */
  (function(){
    var cartes = [].slice.call(document.querySelectorAll('.rv'));
    if(!cartes.length) return;
    var reduit = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var ratio = new Map(), actif = null;
    function mmss(t){ t = Math.max(0, Math.round(t || 0)); return Math.floor(t / 60) + ':' + ('0' + (t % 60)).slice(-2); }
    function charger(c, mode){
      var v = c.v, base = c.fig.dataset.base;
      if(c.mode === mode) return;
      c.mode = mode;
      v.pause(); v.removeAttribute('src'); while(v.firstChild) v.removeChild(v.firstChild);
      v.poster = base + '-' + mode + '-poster.webp';
      var m = document.createElement('source'); m.src = base + '-' + mode + '.mp4'; m.type = 'video/mp4'; v.appendChild(m);
      v.muted = mode === 'boucle'; v.loop = mode === 'boucle';
      c.fig.classList.toggle('complete', mode === 'complete');
      v.load();
    }
    function pauseAutres(sauf){
      cartes.forEach(function(c){ if(c !== sauf && !c.v.paused) c.v.pause(); });
      document.dispatchEvent(new CustomEvent('vk-lecture', {detail: 'video'}));
    }
    function elire(){                          // la boucle à jouer : la carte la plus visible (≥ 50 %)
      if(reduit) return;
      if(cartes.some(function(c){ return c.mode === 'complete' && !c.v.paused; })) return;
      var meilleure = null, r = 0.5;
      // une carte passée en version complète reste comme la personne l'a laissée (en pause, à sa place) jusqu'à la fin
      cartes.forEach(function(c){ var x = ratio.get(c) || 0; if(c.mode !== 'complete' && x >= r){ r = x; meilleure = c; } });
      cartes.forEach(function(c){
        if(c.mode === 'complete') return;
        if(c === meilleure){ charger(c, 'boucle'); if(c.v.paused) c.v.play().catch(function(){}); }
        else if(c.mode === 'boucle' && !c.v.paused) c.v.pause();
      });
      actif = meilleure;
    }
    function complete(c){
      if(c.mode !== 'complete'){ charger(c, 'complete'); }
      pauseAutres(c);
      c.v.muted = false;
      c.v.play().catch(function(){});
    }
    function basculer(c){
      if(c.mode === 'complete' && !c.v.paused){ c.v.pause(); return; }
      complete(c);
    }
    cartes.forEach(function(fig){
      var carte = fig.closest('.temps-card');
      var c = {fig: fig, v: fig.querySelector('video'), mode: null, lec: carte.querySelector('.lecteur[data-video]')};
      fig.__rv = c; cartes[cartes.indexOf(fig)] = c;
      c.v.poster = fig.dataset.base + '-boucle-poster.webp';
      fig.addEventListener('click', function(){ basculer(c); });
      fig.addEventListener('keydown', function(ev){ if(ev.key === 'Enter' || ev.key === ' '){ ev.preventDefault(); basculer(c); } });
      var lec = c.lec;
      if(lec){
        var btn = lec.querySelector('.lec-btn'), piste = lec.querySelector('.lec-piste'),
            avance = lec.querySelector('.lec-avance'), temps = lec.querySelector('.lec-temps');
        var total = parseFloat(fig.dataset.duree) || 0;
        btn.addEventListener('click', function(ev){ ev.stopPropagation(); basculer(c); });
        piste.addEventListener('click', function(ev){
          if(c.mode !== 'complete') return;
          var r = piste.getBoundingClientRect();
          c.v.currentTime = Math.min(total, Math.max(0, (ev.clientX - r.left) / r.width) * total);
        });
        c.v.addEventListener('timeupdate', function(){
          if(c.mode !== 'complete') return;
          avance.style.width = (c.v.currentTime / total * 100) + '%';
          temps.textContent = mmss(total - c.v.currentTime);
        });
        c.v.addEventListener('play', function(){ if(c.mode === 'complete'){ lec.classList.add('joue'); lec.classList.remove('lec-inerte'); btn.setAttribute('aria-pressed', 'true'); } });
        c.v.addEventListener('pause', function(){ lec.classList.remove('joue'); btn.setAttribute('aria-pressed', 'false'); });
        c.v.addEventListener('ended', function(){
          if(c.mode !== 'complete') return;
          avance.style.width = '0'; temps.textContent = mmss(total);
          charger(c, 'boucle'); elire();
        });
      }
    });
    document.addEventListener('vk-lecture', function(ev){      // un appel audio démarre : on coupe la vidéo parlante
      if(ev.detail === 'audio') cartes.forEach(function(c){ if(c.mode === 'complete' && !c.v.paused) c.v.pause(); });
    });
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){ ratio.set(e.target.__rv, e.isIntersecting ? e.intersectionRatio : 0); });
      elire();
    }, {threshold: [0, .25, .5, .75, 1]});
    cartes.forEach(function(c){ io.observe(c.fig); });
    window.__rv = cartes;
  })();
"""


def figure(R, duree):
    base = f"/assets/relais/{R['nom']}"
    return (f'\n        <!-- RELAIS-VIDEO · {R["carte"]} -->\n'
            f'        <figure class="rv" data-base="{base}" data-duree="{duree:.2f}" tabindex="0" role="button" '
            f'aria-label="Voir et écouter l’appel en entier, avec le son">\n'
            f'          <video muted playsinline loop preload="none" disablepictureinpicture aria-hidden="true" '
            f'poster="{base}-boucle-poster.webp"></video>\n'
            # (pastille « Écouter l'appel » retirée le 29/09 : un seul bouton de lecture, le lecteur de la carte)
            f'        </figure>')


def main():
    html = SITE.read_text()
    if "RELAIS-VIDEO" in html:
        # le site porte déjà l'intégration : la maquette = le site, avec les durées des complètes remises à jour
        for r in sys.argv[1:]:
            R = json.loads(Path(r).read_text())
            D = json.loads((Path(r).parent / "donnees-complete.json").read_text())
            html = re.sub(r'(data-base="/assets/relais/' + re.escape(R["nom"]) + r'" data-duree=")[0-9.]+', lambda m: m.group(1) + f'{D["duree"]:.2f}', html)
        SORTIE.write_text(html)
        print("maquette (site déjà intégré, durées remises à jour) :", SORTIE)
        return
    for r in sys.argv[1:]:
        R = json.loads(Path(r).read_text())
        D = json.loads((Path(r).parent / "donnees-complete.json").read_text())
        motif = re.compile(r'(<div class="temps-card">)(\s*<div class="n mono">' + re.escape(R["carte"]) + r'</div>)')
        assert motif.search(html), f"carte « {R['carte']} » introuvable"
        html = motif.sub(lambda m: m.group(1) + figure(R, D["duree"]) + m.group(2), html, count=1)
        # le lecteur de cette carte pilote la vidéo (la durée affichée est celle de la version complète)
        i = html.index(f'<div class="n mono">{R["carte"]}</div>')
        j = html.index('<div class="lecteur"', i)
        k = html.index('<span class="lec-temps mono">', j)
        k2 = html.index('</span>', k)
        # la transcription de la carte : le texte DIT (celui de la recette), prénom de l'agente, comme sur le site
        d0 = html.index('<details class="tr">', i)
        d1 = html.index('</details>', d0)
        s0 = html.index('</summary>', d0) + len('</summary>')
        paras = "".join(f'\n        <p class="{"tr-vokio" if e["qui"] == "agente" else "tr-client"}"><b>'
                        f'{R["agente"] if e["qui"] == "agente" else "L’appelant"}</b>{e.get("transcription", e["texte"])}</p>'
                        for e in R["enonces"])
        html = html[:s0] + paras + "\n        " + html[d1:]
        tot = round(D["duree"])
        html = (html[:j] + '<div class="lecteur" data-video' + html[j + len('<div class="lecteur"'):k]
                + f'<span class="lec-temps mono">{tot // 60}:{tot % 60:02d}' + html[k2:])
    html = html.replace("</style>", CSS + "</style>", 1)
    # le lecteur audio du site ignore les lecteurs vidéo et se coupe quand une vidéo parle (et le dit)
    a = "var lecteurs = [].slice.call(document.querySelectorAll('.lecteur'));"
    assert a in html
    html = html.replace(a, "var lecteurs = [].slice.call(document.querySelectorAll('.lecteur:not([data-video])')); /* RELAIS-VIDEO */")
    b = "          son.play().catch(function(){ /* lecture refusée : on ne casse rien */ });"
    assert b in html
    html = html.replace(b, b + "\n          document.dispatchEvent(new CustomEvent('vk-lecture', {detail: 'audio'})); /* RELAIS-VIDEO */")
    c = "      son.addEventListener('timeupdate', peindre);"
    html = html.replace(c, c + "\n      document.addEventListener('vk-lecture', function(ev){ if(ev.detail === 'video') son.pause(); }); /* RELAIS-VIDEO */")
    idx = html.rindex("</script>")
    html = html[:idx] + JS + html[idx:]
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(html)
    # les blocs à reporter dans index.html du site, tels quels (fichier de passation pour l'intégration)
    B = ["<!-- Blocs RELAIS-VIDEO à reporter dans /opt/vokio-site-repo/index.html (générés par outils/maquette.py). -->",
         "<!-- 1. CSS : à coller juste avant le premier </style> -->", "<style>" + CSS + "</style>",
         "<!-- 2. Dans chaque carte, juste après <div class=\"temps-card\"> : la figure ; dans le lecteur de la carte, "
         "remplacer <div class=\"lecteur\" par <div class=\"lecteur\" data-video et le temps affiché par la durée ci-dessous ; "
         "remplacer le contenu de <details class=\"tr\"> (après </summary>) par les paragraphes ci-dessous -->"]
    for r in sys.argv[1:]:
        R = json.loads(Path(r).read_text())
        D = json.loads((Path(r).parent / "donnees-complete.json").read_text())
        tot = round(D["duree"])
        B.append(f"<!-- carte « {R['carte']} » : durée affichée {tot // 60}:{tot % 60:02d} -->" + figure(R, D["duree"]))
        B.append("        <!-- transcription (texte dit) -->" + "".join(
            f'\n        <p class="{"tr-vokio" if e["qui"] == "agente" else "tr-client"}"><b>'
            f'{R["agente"] if e["qui"] == "agente" else "L’appelant"}</b>{e.get("transcription", e["texte"])}</p>' for e in R["enonces"]))
    B += ["<!-- 3. Script du lecteur audio existant : trois lignes -->",
          "<!--   a) var lecteurs = [].slice.call(document.querySelectorAll('.lecteur:not([data-video])')); /* RELAIS-VIDEO */",
          "       b) après son.play().catch(…); : document.dispatchEvent(new CustomEvent('vk-lecture', {detail: 'audio'})); /* RELAIS-VIDEO */",
          "       c) après son.addEventListener('timeupdate', peindre); : document.addEventListener('vk-lecture', function(ev){ if(ev.detail === 'video') son.pause(); }); /* RELAIS-VIDEO */ -->",
          "<!-- 4. JS : à coller à la fin du dernier <script> (avant son </script>) -->", "<script>" + JS + "</script>",
          "<!-- 5. Fichiers : /root/vokio-uploads/videos/relais/relais-<carte>-{boucle,complete}.mp4 et -{boucle,complete}-poster.webp "
          "vers /assets/relais/ du site (les .jpg sont des posters de secours, non référencés). -->"]
    (SORTIE.parent / "blocs-relais-video.html").write_text("\n".join(B) + "\n")
    print("maquette :", SORTIE)


if __name__ == "__main__":
    main()
