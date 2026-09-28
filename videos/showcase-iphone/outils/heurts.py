#!/root/.pwtest/bin/python
"""Heurts du point avec les textes, IMAGE PAR IMAGE, dans un projet rendable (9:16 ou copie de format) : usage en une ligne :

    /root/.pwtest/bin/python outils/heurts.py <racine> [<scène>…] [--de N --a N] [--marge 0] [--permis motif] [--json r.json]

  Monte le film dans le chrome-headless-shell de HyperFrames (outils/banc-film.html de <racine>, comme controles_dom.py),
  place le film à chaque image des scènes demandées (toutes si aucune ; --de / --a : bornes d'images, incluses) et relève :
    · le disque du point racine : POINT.etat(t) (centre dessiné, diamètre × écrasement : rayon = d × max(sx, sy) / 2),
      compté seulement s'il est dessiné (#point visible, opacité > 0,01, d > 0) ;
    · l'ENCRE de chaque mot visible (feuilles texte des [data-element], opacité effective > 0,01, partie visible dans
      le cadre et sous les découpes) : boîte du nœud texte (Range) réduite à l'encre par measureText du canvas
      (actualBoundingBox*, police calculée du nœud ; transformations d'échelle prises en compte par le rapport
      hauteur de la boîte / hauteur de la police).
  Heurt = le disque (agrandi de --marge px, défaut 0) recoupe l'encre d'un mot. Les heurts voulus (le point qui écrit
  un mot, qui se pose sur le ı) se déclarent par --permis <motif fnmatch sur « scène:élément:texte »>, répétable,
  ex. --permis "s5-rendez-vous:bloc:*" --permis "s7-signature:*:*".
  Imprime les heurts groupés en plages d'images consécutives (scène, élément, mot, profondeur max, opacité max) ;
  code 1 s'il reste un heurt non permis. --json : le rapport complet (chaque image). Lecture seule, idempotent :
  n'écrit que --json. Pourquoi : un objet qui se déplace SOUS le point (la mention de l'agenda qui monte, en 16:9)
  ne passe pas par le planificateur de construire.py, qui ne connaît que les sous-titres.
"""
import argparse
import fnmatch
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME_HF = Path("/root/.cache/hyperframes/chrome/chrome-headless-shell/linux-152.0.7977.30/"
                 "chrome-headless-shell-linux64/chrome-headless-shell")

# Relevé d'une image, évalué dans banc-film.html (placer, feuilles, opacite, visible, aire y sont globales).
JS_IMAGE = r"""
(t) => {
  placer(t);
  const pt = document.getElementById("point");
  const e = POINT.etat(t);
  const csp = getComputedStyle(pt);
  const opP = opacite(pt);
  const dessine = csp.visibility === "visible" && opP > 0.01 && e.d > 0;
  const R = e.d * Math.max(e.sx || 1, e.sy || 1) / 2;
  const c = window.__heurtsCanvas || (window.__heurtsCanvas = document.createElement("canvas").getContext("2d"));
  const mots = [];
  document.querySelectorAll("[data-element]").forEach(function (el) {
    if (el === pt || el.contains(pt)) return;
    const hote = el.closest("[data-composition-src]");
    feuilles(el).forEach(function (f) {
      if (f.type !== "texte") return;
      const o = opacite(f.el);
      if (o <= 0.01) return;
      const v = visible(f.el, f.r);
      if (aire(v) <= 1) return;
      const cs = getComputedStyle(f.el);
      c.font = cs.fontStyle + " " + cs.fontWeight + " " + cs.fontSize + " " + cs.fontFamily;
      const m = c.measureText(f.texte);
      const hp = m.fontBoundingBoxAscent + m.fontBoundingBoxDescent;
      const k = hp > 0 ? (f.r.y1 - f.r.y0) / hp : 1;
      const base = f.r.y0 + k * m.fontBoundingBoxAscent;
      let x0 = f.r.x0 - k * m.actualBoundingBoxLeft, x1 = f.r.x0 + k * m.actualBoundingBoxRight;
      let y0 = base - k * m.actualBoundingBoxAscent, y1 = base + k * m.actualBoundingBoxDescent;
      // l'encre ne dépasse pas la partie visible (masques de ligne, cadre)
      x0 = Math.max(x0, v.x0); x1 = Math.min(x1, v.x1); y0 = Math.max(y0, v.y0); y1 = Math.min(y1, v.y1);
      if (x1 <= x0 || y1 <= y0) return;
      mots.push({ scene: hote ? hote.getAttribute("data-composition-id") : "racine", element: el.getAttribute("data-element"),
                  texte: f.texte.trim(), encre: [+x0.toFixed(1), +y0.toFixed(1), +x1.toFixed(1), +y1.toFixed(1)], opacite: +o.toFixed(3) });
    });
  });
  return { t: t, point: { x: e.x, y: e.y, r: +R.toFixed(2), dessine: dessine, opacite: +opP.toFixed(3) }, mots: mots };
}
"""


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError):   # le banc coupe les médias qu'il ne lit pas
            pass


def distance_rect(cx, cy, b):
    dx = max(b[0] - cx, 0, cx - b[2])
    dy = max(b[1] - cy, 0, cy - b[3])
    return (dx * dx + dy * dy) ** 0.5


def lire_donnees(racine):
    t = (racine / "donnees" / "donnees.js").read_text()
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("racine")
    A.add_argument("scenes", nargs="*")
    A.add_argument("--de", type=int)
    A.add_argument("--a", type=int)
    A.add_argument("--marge", type=float, default=0.0)
    A.add_argument("--permis", action="append", default=[])
    A.add_argument("--json")
    a = A.parse_args()
    racine = Path(a.racine).resolve()
    D = lire_donnees(racine)
    fps = D.get("fps", 30)
    scenes = a.scenes or list(D["scenes"].keys())
    images = set()
    for s in scenes:
        if s not in D["scenes"]:
            raise SystemExit(f"scène inconnue : {s} ({', '.join(D['scenes'])})")
        sc = D["scenes"][s]
        images.update(range(sc["image_debut"], sc["image_fin"]))
    if a.de is not None:
        images = {n for n in images if n >= a.de}
    if a.a is not None:
        images = {n for n in images if n <= a.a}
    images = sorted(images)
    taille = D.get("taille", [1080, 1920])
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencieux, directory=str(racine)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    releves, erreurs = [], []
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=str(CHROME_HF), args=["--font-render-hinting=none"])
        page = nav.new_page(viewport={"width": taille[0], "height": taille[1]}, device_scale_factor=1)
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.goto(f"http://127.0.0.1:{srv.server_address[1]}/outils/banc-film.html")
        page.evaluate("monterFilm()")
        for n in images:
            r = page.evaluate(JS_IMAGE, round(n / fps, 6))
            r["image"] = n
            releves.append(r)
        nav.close()
    srv.shutdown()
    heurts = []
    for r in releves:
        P = r["point"]
        if not P["dessine"]:
            continue
        for m in r["mots"]:
            d = distance_rect(P["x"], P["y"], m["encre"])
            prof = P["r"] + a.marge - d
            if prof > 0:
                cle = f"{m['scene']}:{m['element']}:{m['texte']}"
                heurts.append({"image": r["image"], "t": r["t"], "cle": cle, "profondeur": round(prof, 1),
                               "opacite": m["opacite"], "encre": m["encre"], "point": [P["x"], P["y"], P["r"]],
                               "permis": any(fnmatch.fnmatchcase(cle, motif) for motif in a.permis)})
    plages = []
    for h in sorted(heurts, key=lambda h: (h["cle"], h["image"])):
        if plages and plages[-1]["cle"] == h["cle"] and h["image"] == plages[-1]["images"][1] + 1:
            pl = plages[-1]
            pl["images"][1] = h["image"]
            pl["profondeur_max"] = max(pl["profondeur_max"], h["profondeur"])
            pl["opacite_max"] = max(pl["opacite_max"], h["opacite"])
        else:
            plages.append({"cle": h["cle"], "images": [h["image"], h["image"]], "profondeur_max": h["profondeur"],
                           "opacite_max": h["opacite"], "permis": h["permis"]})
    plages.sort(key=lambda p: p["images"][0])
    print(f"{racine} · {len(images)} image(s) ({images[0]} → {images[-1]}) · marge {a.marge} px · "
          f"{len(erreurs)} erreur(s) de page")
    for e in erreurs:
        print("  erreur de page : " + e)
    if not plages:
        print("  aucun heurt du point avec un texte")
    for pl in plages:
        n0, n1 = pl["images"]
        print(f"  {'permis ' if pl['permis'] else 'HEURT  '} images {n0:4d} → {n1:4d} ({n0 / fps:6.3f} → {n1 / fps:6.3f} s)  "
              f"prof. max {pl['profondeur_max']:5.1f} px  opacité max {pl['opacite_max']:.2f}  {pl['cle']}")
    if a.json:
        Path(a.json).write_text(json.dumps({"racine": str(racine), "scenes": scenes, "marge": a.marge, "permis": a.permis,
                                            "erreurs_page": erreurs, "plages": plages, "images": releves},
                                           ensure_ascii=False))
        print(f"→ {a.json}")
    return 1 if erreurs or any(not pl["permis"] for pl in plages) else 0


if __name__ == "__main__":
    sys.exit(main())
