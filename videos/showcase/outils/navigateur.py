#!/root/.pwtest/bin/python
"""Mesures dans Chromium (le chrome-headless-shell de HyperFrames, même moteur que le rendu).

    /root/.pwtest/bin/python outils/navigateur.py geometrie   → JSON : point final de s1, #mot-pt de s7
    /root/.pwtest/bin/python outils/navigateur.py resoudre    → JSON : POINT.etat(n/30) pour chaque image
    /root/.pwtest/bin/python outils/navigateur.py pages       → JSON : les sous-titres de la bible posés par TEXTE.poser
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
  sortie.s1_montage = await monter("s1-sonnerie", 0);
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
  sortie.s7 = { mot_pt: pt, centre: { x: pt.cx, y: pt.cy }, diametre: pt.l, mot: boite(document.getElementById("mot")),
                ligne_de_base: base7, glyphe_i: { origine: bi.left, avance: bi.width, encre: encI,
                fut_x0: bi.left - encI.gauche, fut_x1: bi.left + encI.droite, haut_encre: base7 - encI.haut } };
  return sortie;
}
"""

# Les pages de sous-titres de la bible, posées par TEXTE.poser : prouve la règle 8 et donne l'instant de chaque mot.
PAGES = [  # (scène, extrait, rang de départ « depuis », lignes)
    ("s2-voix", "A1", 0, ["Bonjour, je suis Élise,"]),
    ("s2-voix", "A1", 4, ["l’assistante vocale de la", "Clinique vétérinaire du Port."]),
    ("s2-voix", "A1", 12, ["Comment puis-je vous aider\\u202f?"]),
    ("s3-ecoute", "C1", 0, ["mon\\u00a0chat, euh, Moka,", "euh, mange plus", "depuis hier."]),
    ("s3-ecoute", "C2", 1, ["Demain, vous avez", "des disponibilités\\u202f?"]),
    ("s4-agenda", "A2A3", 0, ["Laissez-moi voir."]),
    ("s4-agenda", "A2A3", 2, ["Je peux vous proposer", "neuf heures, dix heures", "ou onze heures."]),
    ("s4-agenda", "C3", 2, ["À neuf heures,", "c’est parfait."]),
    ("s5-rendez-vous", "A4", 0, ["Parfait, je vous note ça", "pour Florian,"]),
    ("s5-rendez-vous", "A4", 7, ["pour une consultation vétérinaire,", "le samedi dix-neuf septembre", "à neuf heures."]),
    ("s6-sms", "A4", 18, ["Vous recevrez un SMS", "de confirmation."]),
]

PAGES_JS = r"""
(pages) => {
  const out = [];
  const box = document.createElement("div"); document.body.appendChild(box);
  for (const [scene, extrait, depuis, lignes] of pages) {
    const L = lignes.map((l) => l.replace(/\\u202f/g, "\u202f").replace(/\\u00a0/g, "\u00a0"));
    const p = TEXTE.poser(box, L, { extrait: extrait, depuis: depuis });
    const sc = TEXTE.scene(scene);
    out.push({ scene: scene, extrait: extrait, depuis: depuis, lignes: L, curseur_apres: p.curseur,
               mots: p.mots.map((u) => ({ texte: u.texte, ligne: u.ligne, rang: u.mot.rang, t: u.t, image: TEXTE.image(u.t),
                                          local: sc.local(TEXTE.aImage(u.t)), fin_voix: u.mots[u.mots.length - 1].fin,
                                          dits: u.mots.map((m) => m.texte) })) });
  }
  return out;
}
"""

RESOUDRE_JS = r"""
async (n) => {
  await charger("lib/point.js");
  const out = [];
  for (let k = 0; k <= n; k++) {
    const s = POINT.etat(k / 30);
    out.push([k, +s.x.toFixed(3), +s.y.toFixed(3), +s.d.toFixed(3), s.couleur, +s.dx.toFixed(3)]);
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
    k = 200 / upm
    s1 = r["s1"]
    s1["glyphe_point"] = {"unites": [x0, y0, x1, y1], "upm": upm, "avance": av, "corps_px": 200}
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
            r = {"pages": page.evaluate(PAGES_JS, PAGES)}
        else:
            n = int(sys.argv[2]) if len(sys.argv) > 2 else 1305
            r = {"images": page.evaluate(RESOUDRE_JS, n)}
        r["moteur"] = moteur
        r["erreurs_page"] = erreurs
        nav.close()
    srv.shutdown()
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
