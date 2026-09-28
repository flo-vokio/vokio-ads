#!/root/.pwtest/bin/python
"""Contrôles DOM du film entier, dans le chrome-headless-shell de HyperFrames (même moteur que le rendu).

    /root/.pwtest/bin/python outils/controles_dom.py [sortie.json] [pas_images] [--racine formats/16x9]

Monte outils/banc-film.html (index.html + les sept sous-compositions, scripts rejoués comme HyperFrames),
puis, pour chaque image n (pas 1 par défaut), place le film à n/30 et relève :
  · les [data-element] réellement visibles (opacité effective > 0,01, surface dessinée dans le cadre,
    découpes clip-path des ancêtres comprises : un mot sous son masque de ligne ne compte pas) ;
  · chaque nœud texte visible : corps, famille, boîte visible (visibilité CALCULÉE : un enfant forcé visible
    dans un hôte masqué compte, comme dans le rendu) ;
  · pour chaque page posée par TEXTE.poser, le nombre de mots visibles (durée de lecture des pages) ;
et une fois : la boîte de repos de chaque mot dit (pour comparer, sur le MP4, l'image où il apparaît à
l'image où il est dit). Appelé par outils/controles.py.
"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJET = Path(__file__).resolve().parents[1]
CHROME_HF = Path("/root/.cache/hyperframes/chrome/chrome-headless-shell/linux-152.0.7977.30/"
                 "chrome-headless-shell-linux64/chrome-headless-shell")


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    args = sys.argv[1:]
    racine = PROJET
    if "--racine" in args:                       # FORMATS : un projet de format (outils/format.py), servi tel quel
        i = args.index("--racine"); racine = Path(args[i + 1]).resolve(); del args[i:i + 2]
    sortie = Path(args[0]) if len(args) > 0 else None
    pas = int(args[1]) if len(args) > 1 else 1
    js = (racine / "donnees" / "donnees.js").read_text()
    taille = json.loads(js[js.index("{"):js.rindex("}") + 1]).get("taille", [1080, 1920])
    h = functools.partial(Silencieux, directory=str(racine))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/outils/banc-film.html"
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=str(CHROME_HF), args=["--font-render-hinting=none"])
        page = nav.new_page(viewport={"width": taille[0], "height": taille[1]}, device_scale_factor=1)
        erreurs = []
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.goto(url)
        montage = page.evaluate("monterFilm()")
        n_images = int(page.evaluate("DONNEES.images"))
        images = []
        for n in range(0, n_images, pas):
            images.append(page.evaluate("(t) => mesurer(t)", n / 30))
            images[-1]["image"] = n
        mots = page.evaluate("motsDits()")
        pages = page.evaluate("pagesPosees()")
        nav.close()
    srv.shutdown()
    r = {"montage": montage, "erreurs_page": erreurs, "images": images, "mots": mots, "pages": pages}
    txt = json.dumps(r, ensure_ascii=False)
    if sortie:
        sortie.write_text(txt)
        print(f"{len(images)} images mesurées, {len(mots)} mots, {len(erreurs)} erreur(s) de page → {sortie}")
    else:
        print(txt)


if __name__ == "__main__":
    main()
