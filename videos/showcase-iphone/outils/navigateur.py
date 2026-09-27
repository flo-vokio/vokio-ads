#!/root/.pwtest/bin/python
"""Mesures dans Chromium (le chrome-headless-shell de HyperFrames, même moteur que le rendu).

    /root/.pwtest/bin/python outils/navigateur.py geometrie   → JSON : point final de s1, #mot-pt de s7
    /root/.pwtest/bin/python outils/navigateur.py resoudre    → JSON : POINT.etat(n/30) pour chaque image
    /root/.pwtest/bin/python outils/navigateur.py pages       → JSON : les pages de sous-titres v2 posées par TEXTE.poser
                                                                avec le CSS du contrat de leur scène (DONNEES.geometrie) :
                                                                bord droit d'encre et ligne de base de chaque unité
Appelé par outils/construire.py ; utilisable seul pour vérifier une scène modifiée.
"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright

PROJET = Path(__file__).resolve().parents[1]
CHROME_HF = Path("/root/.cache/hyperframes/chrome/chrome-headless-shell/linux-152.0.7977.30/"
                 "chrome-headless-shell-linux64/chrome-headless-shell")


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serveur():
    h = functools.partial(Silencieux, directory=str(PROJET))
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


GEOMETRIE_JS = r"""
async () => {
  const sortie = {};
  // ── s1 : le « . » final de « mains prises. », remplacé par #s1-espaceur ──
  sortie.s1_montage = await monter("s1-sonnerie", 2.0);   // 2,0 s : l'accroche est posée (0 → 0,90), la relance pas encore partie
  const sp = document.getElementById("s1-espaceur");
  const b = boite(sp);                      // hauteur 0 : top = bottom = ligne de base
  const mot = sp.parentElement;
  // origine réelle du « . » après « prises » (crénage compris) : on le pose, on le mesure, on le retire
  const sonde = document.createElement("span"); sonde.textContent = ".";
  sp.style.display = "none"; mot.insertBefore(sonde, sp);
  const r = document.createRange(); r.selectNodeContents(sonde); const rb = r.getBoundingClientRect();
  const enc = encreGlyphe(mot, ".");
  mot.removeChild(sonde); sp.style.display = "";
  const lignes = Array.from(document.querySelectorAll("#s1-phrase .tx-ligne")).map((l) => {
    const z = document.createElement("span"); z.style.cssText = "display:inline-block;width:0;height:0";
    l.appendChild(z); const y = z.getBoundingClientRect().top; l.removeChild(z);
    const w = Array.from(l.querySelectorAll(".tx-w")); const x0 = w[0].getBoundingClientRect().left;
    const x1 = w[w.length - 1].getBoundingClientRect().right;
    return { ligne_de_base: y, x0: x0, x1: x1, largeur: x1 - x0 };
  });
  sortie.s1 = {
    corps: parseFloat(getComputedStyle(document.getElementById("s1-phrase")).fontSize),
    espaceur: b, ligne_de_base: b.y1, origine_point_reel: rb.left, avance_point: rb.width, encre_point: enc,
    centre: { x: rb.left + (enc.droite - enc.gauche) / 2, y: b.y1 - (enc.haut - enc.bas) / 2 },
    diametre: Math.max(enc.gauche + enc.droite, enc.haut + enc.bas),
    diametre_l: enc.gauche + enc.droite, diametre_h: enc.haut + enc.bas,
    centre_espaceur_x: b.cx, lignes: lignes,
  };
  // ── s7 : #mot-pt, la boîte de mesure du point du ı ──
  sortie.s7_montage = await monter("s7-signature", 1.2);
  const pt = boite(document.getElementById("mot-pt"));
  const a = document.getElementById("mot-a");
  const z = document.createElement("span"); z.style.cssText = "display:inline-block;width:0;height:0";
  a.appendChild(z); const base7 = z.getBoundingClientRect().top; a.removeChild(z);
  const i = document.getElementById("mot-i");
  const encI = encreGlyphe(i, "ı");
  const ri = document.createRange(); ri.selectNodeContents(i.firstChild); const bi = ri.getBoundingClientRect();
  const segs = {};
  for (const id of ["mot-a", "mot-i", "mot-o"]) {
    const e = document.getElementById(id);
    const tn = Array.from(e.childNodes).find((n) => n.nodeType === 3);
    const rg = document.createRange(); rg.selectNodeContents(tn); const rr = rg.getBoundingClientRect();
    const en = encreGlyphe(e, tn.textContent);
    segs[id] = { boite: boite(e), texte: tn.textContent, encre_x0: rr.left - en.gauche, encre_x1: rr.left + en.droite };
  }
  sortie.s7 = { mot_pt: pt, centre: { x: pt.cx, y: pt.cy }, diametre: pt.l, mot: boite(document.getElementById("mot")), segments: segs,
                ligne_de_base: base7, glyphe_i: { origine: bi.left, avance: bi.width, encre: encI,
                fut_x0: bi.left - encI.gauche, fut_x1: bi.left + encI.droite, haut_encre: base7 - encI.haut } };
  return sortie;
}
"""

# Les pages de sous-titres v2 (plan v2, chantier racine, C), posées par TEXTE.poser avec le CSS du contrat de
# leur scène : prouve la règle 8, donne l'instant de chaque mot, et mesure le bord droit d'encre et la ligne de
# base de chaque unité (cibles du suiveur de s2). (scène, extrait, rang de départ « depuis », lignes, style)
PAGES = [
    ("s2-voix", "A1", 0, ["Bonjour, je suis Élise,"], "s2_texte"),
    ("s2-voix", "A1", 4, ["l’assistante vocale", "de la Clinique vétérinaire", "du Port."], "s2_texte"),
    ("s2-voix", "A1", 12, ["Comment puis-je", "vous aider\\u202f?"], "s2_texte"),
    ("s3-ecoute", "C1", 0, ["mon\\u00a0chat, euh, Moka,", "euh, mange plus", "depuis hier."], "s3_texte"),
    ("s3-ecoute", "C2", 1, ["Demain, vous avez", "des disponibilités\\u202f?"], "s3_texte"),
    ("s4-agenda", "A2A3", 0, ["Laissez-moi voir."], "haut_agente"),
    ("s4-agenda", "A2A3", 2, ["Je peux vous proposer", "neuf heures, dix heures", "ou onze heures."], "haut_agente"),
    ("s4-agenda", "C3", 2, ["À neuf heures,", "c’est parfait."], "haut_appelant"),
    ("s5-rendez-vous", "A4", 0, ["Parfait, je vous note ça", "pour Florian,"], "haut_agente"),
    ("s5-rendez-vous", "A4", 7, ["pour une consultation", "vétérinaire,"], "haut_agente"),
    ("s5-rendez-vous", "A4", 11, ["le samedi dix-neuf", "septembre à neuf heures."], "haut_agente"),
    ("s6-sms", "A4", 18, ["Vous recevrez un SMS", "de confirmation."], "haut_agente"),
    ("s6-sms", "C4", 0, ["Super, merci beaucoup.", "Au revoir."], "haut_appelant"),
]

POLICES_CSS = (
    '@font-face{font-family:"Geist";font-weight:400;font-style:normal;font-display:block;src:url("assets/fonts/Geist-Regular.woff2") format("woff2")}'
    '@font-face{font-family:"Instrument Serif";font-weight:400;font-style:normal;font-display:block;src:url("assets/fonts/InstrumentSerif-Regular.woff2") format("woff2")}'
    '@font-face{font-family:"Instrument Serif";font-weight:400;font-style:italic;font-display:block;src:url("assets/fonts/InstrumentSerif-Italic.woff2") format("woff2")}')

PAGES_JS = r"""
async ([pages, styles, polices]) => {
  if (!document.getElementById("pg-polices")) {
    const st = document.createElement("style"); st.id = "pg-polices"; st.textContent = polices; document.head.appendChild(st);
  }
  await Promise.all([document.fonts.load('400 72px "Geist"'), document.fonts.load('400 36px "Geist"'),
                     document.fonts.load('italic 400 64px "Instrument Serif"'), document.fonts.load('400 64px "Instrument Serif"')]);
  await document.fonts.ready;
  const ctx = document.createElement("canvas").getContext("2d");
  function encre(noeud, el) {                       // bords d'encre d'un nœud texte (origine DOM + boîte canvas)
    const cs = getComputedStyle(el);
    ctx.font = cs.fontStyle + " " + cs.fontWeight + " " + cs.fontSize + " " + cs.fontFamily;
    const m = ctx.measureText(noeud.textContent);
    const r = document.createRange(); r.selectNodeContents(noeud); const b = r.getBoundingClientRect();
    return { x0: b.left - m.actualBoundingBoxLeft, x1: b.left + m.actualBoundingBoxRight, origine: b.left, avance: b.width,
             haut: m.actualBoundingBoxAscent, bas: m.actualBoundingBoxDescent };
  }
  function base(ligne) {
    const z = document.createElement("span"); z.style.cssText = "display:inline-block;width:0;height:0";
    ligne.appendChild(z); const y = z.getBoundingClientRect().top; ligne.removeChild(z); return y;
  }
  function textes(el) {
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); const out = []; let n;
    while ((n = w.nextNode())) if (n.textContent.trim()) out.push(n);
    return out;
  }
  function boiteDe(css) {
    const box = document.createElement("div");
    box.style.cssText = "position:absolute;margin:0;left:" + css.x + "px;top:0px;font-family:" + css.famille + ";font-style:" + css.style +
      ";font-weight:" + css.graisse + ";font-size:" + css.corps + "px;line-height:" + css.interligne + "px;letter-spacing:0;white-space:nowrap";
    document.getElementById("banc").appendChild(box);
    return box;
  }
  // décalage de la ligne de base (px sous le haut du conteneur) de chaque style
  const decalages = {};
  for (const [nom, css] of Object.entries(styles)) {
    const box = boiteDe(css);
    const p = TEXTE.poser(box, ["Hxg"], { extrait: null });
    decalages[nom] = base(p.lignes[0]);
    box.remove();
  }
  const out = [];
  for (const [scene, extrait, depuis, lignes, style] of pages) {
    const css = styles[style];
    const L = lignes.map((l) => l.replace(/\\u202f/g, "\u202f").replace(/\\u00a0/g, "\u00a0"));
    const box = boiteDe(css);
    const top = css.lignes_de_base[0] - decalages[style];
    box.style.top = top + "px";
    const p = TEXTE.poser(box, L, { extrait: extrait, depuis: depuis, chevauchement: true });
    const sc = TEXTE.scene(scene);
    const bases = p.lignes.map(base);
    const largeurs = p.lignes.map((l) => {
      const w = Array.from(l.querySelectorAll(".tx-w"));
      const t0 = textes(w[0])[0], t1 = textes(w[w.length - 1]).pop();
      const e0 = encre(t0, w[0]), e1 = encre(t1, w[w.length - 1]);
      return { x0: w[0].getBoundingClientRect().left, x1: w[w.length - 1].getBoundingClientRect().right,
               encre_x0: e0.x0, encre_x1: e1.x1 };
    });
    out.push({ scene: scene, extrait: extrait, depuis: depuis, lignes: L, style: style, top: top,
               lignes_de_base: bases, largeurs: largeurs, curseur_apres: p.curseur,
               mots: p.mots.map((u) => {
                 const tn = textes(u.el); const ea = encre(tn[0], u.el), eb = encre(tn[tn.length - 1], u.el);
                 const r = u.el.getBoundingClientRect();
                 const es = tn.map((n) => encre(n, u.el));
                 const haut = Math.max.apply(null, es.map((e) => e.haut)), bas = Math.max.apply(null, es.map((e) => e.bas));
                 return { texte: u.texte, ligne: u.ligne, rang: u.mot.rang, t: u.t, image: TEXTE.image(u.t),
                          local: sc.local(TEXTE.aImage(u.t)), revele: +(TEXTE.aImage(u.t) - 1 / TEXTE.FPS).toFixed(6),
                          fin_voix: u.mots[u.mots.length - 1].fin, dits: u.mots.map((m) => m.texte),
                          x0: r.left, x1: r.right, encre_x0: ea.x0, encre_x1: eb.x1, ligne_de_base: bases[u.ligne],
                          encre_haut: haut, encre_bas: bas };
               }) });
    box.remove();
  }
  return { pages: out, decalages: decalages };
}
"""

RESOUDRE_JS = r"""
async (n) => {
  await charger("lib/point.js");
  const out = [];
  for (let k = 0; k <= n; k++) {
    const s = POINT.etat(k / 30);
    out.push([k, +s.x.toFixed(3), +s.y.toFixed(3), +s.d.toFixed(3), s.couleur, +s.dx.toFixed(3), +s.dy.toFixed(3),
              +s.x_sans.toFixed(3), +s.y_sans.toFixed(3), +s.sx.toFixed(4), +s.sy.toFixed(4), +s.rot.toFixed(2), +s.v.toFixed(3)]);
  }
  return out;
}
"""


def boite_glyphe(police, car):
    """Boîte d'encre exacte du glyphe, en unités de fonte (xMin, yMin, xMax, yMax), et upm."""
    t = TTFont(str(PROJET / "assets" / "fonts" / police))
    g = t.getBestCmap()[ord(car)]
    bp = BoundsPen(t.getGlyphSet())
    t.getGlyphSet()[g].draw(bp)
    return bp.bounds, t["head"].unitsPerEm, t["hmtx"][g][0]


def completer_geometrie(r):
    """Centre du « . » de s1 depuis la boîte exacte du glyphe (le canvas arrondit l'encre au pixel)."""
    (x0, y0, x1, y1), upm, av = boite_glyphe("InstrumentSerif-Regular.woff2", ".")
    s1 = r["s1"]
    corps = s1["corps"]                    # corps CALCULÉ de #s1-phrase (150 px depuis la finition du 27/09, 200 avant)
    k = corps / upm
    s1["glyphe_point"] = {"unites": [x0, y0, x1, y1], "upm": upm, "avance": av, "corps_px": corps}
    s1["centre"] = {"x": round(s1["origine_point_reel"] + (x0 + x1) / 2 * k, 3),
                    "y": round(s1["ligne_de_base"] - (y0 + y1) / 2 * k, 3)}
    s1["diametre_l"] = round((x1 - x0) * k, 3)
    s1["diametre_h"] = round((y1 - y0) * k, 3)
    s1["diametre"] = round(((x1 - x0) + (y1 - y0)) / 2 * k, 3)
    s1["methode_centre"] = "origine DOM du « . » réel (Range, crénage compris) + centre de la boîte d'encre du glyphe (fontTools), ligne de base DOM"
    s7 = r["s7"]
    s7["centre"] = {"x": round(s7["centre"]["x"], 3), "y": round(s7["centre"]["y"], 3)}
    s7["diametre"] = round(s7["diametre"], 3)
    s7["methode_centre"] = "centre de getBoundingClientRect() de #mot-pt (boîte CSS du point de la DA)"
    return r


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "geometrie"
    srv = serveur()
    url = f"http://127.0.0.1:{srv.server_address[1]}/outils/banc.html"
    with sync_playwright() as p:
        try:
            nav = p.chromium.launch(executable_path=str(CHROME_HF), args=["--font-render-hinting=none"])
            moteur = "chrome-headless-shell HyperFrames 152.0.7977.30"
        except Exception as e:   # repli : le Chromium de Playwright
            print(f"repli Chromium Playwright ({e})", file=sys.stderr)
            nav = p.chromium.launch(args=["--font-render-hinting=none"])
            moteur = "chromium playwright"
        page = nav.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        erreurs = []
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.goto(url)
        page.wait_for_function("window.TEXTE !== undefined")
        if phase == "geometrie":
            r = completer_geometrie(page.evaluate(GEOMETRIE_JS))
        elif phase == "pages":
            styles = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else json.loads(
                (PROJET / "donnees" / "styles-pages.json").read_text())
            r = page.evaluate(PAGES_JS, [PAGES, styles, POLICES_CSS])
        else:
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 1350
            r = {"images": page.evaluate(RESOUDRE_JS, n)}
        r["moteur"] = moteur
        r["erreurs_page"] = erreurs
        nav.close()
    srv.shutdown()
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
