#!/root/.pwtest/bin/python
"""Lit les contrôles INTERNES des scènes (window.__<scène>Controle) d'un ou plusieurs projets rendables : usage en une ligne :

    /root/.pwtest/bin/python outils/controles_internes.py <racine> [<racine> …] [--attente 4] [--json rapport.json]

  Pourquoi : une scène qui se recontrôle après le chargement des polices (s3-ecoute : resserrage du tamis contre DONNEES.pages,
  largeur de la mention ; s6 via lib/iphone.js : lignes de la bulle) n'écrit dans la console qu'en cas d'ÉCART, et se tait
  aussi quand elle n'a rien pu mesurer (hôte non mis en page : « mesure: false »). hf check ne voit donc que les écarts,
  jamais l'absence de mesure. Cet outil monte le film (outils/banc-film.html du projet, comme outils/controles_dom.py) dans
  le chrome-headless-shell de HyperFrames, à la taille de DONNEES.taille, attend les polices et les contrôles (--attente s),
  puis relève chaque window.__*Controle, les console.error et les erreurs de page.
  <racine> : le projet 9:16 (/opt/vokio-ads/videos/showcase-iphone), formats/16x9, ou une copie de contrôle
  (outils/format.py --dossier) : toute racine qui a donnees/donnees.js et outils/banc-film.html.
  Code 1 si une racine a une erreur de page, un console.error, un contrôle « mesure: false » ou un champ ecart_* > 0,5 px.
  Lecture seule (rien n'est écrit, hors --json). Idempotent.
"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROME_HF = Path("/root/.cache/hyperframes/chrome/chrome-headless-shell/linux-152.0.7977.30/"
                 "chrome-headless-shell-linux64/chrome-headless-shell")
SEUIL_ECART = 0.5


class Silencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class Serveur(http.server.ThreadingHTTPServer):
    def handle_error(self, *a):          # le navigateur coupe les flux audio à la fermeture : sans intérêt
        pass


def relever(racine, attente):
    js = (racine / "donnees" / "donnees.js").read_text()
    D = json.loads(js[js.index("{"):js.rindex("}") + 1])
    taille = D.get("taille", [1080, 1920])
    srv = Serveur(("127.0.0.1", 0), functools.partial(Silencieux, directory=str(racine)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/outils/banc-film.html"
    erreurs, consoles = [], []
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=str(CHROME_HF), args=["--font-render-hinting=none"])
        page = nav.new_page(viewport={"width": taille[0], "height": taille[1]}, device_scale_factor=1)
        page.on("pageerror", lambda e: erreurs.append(str(e)))
        page.on("console", lambda m: consoles.append(m.text) if m.type == "error" else None)
        page.goto(url)
        montage = page.evaluate("monterFilm()")
        page.wait_for_timeout(int(attente * 1000))
        ctl = page.evaluate("""() => { const o = {};
            Object.keys(window).filter(k => /^__\\w+Controle$/.test(k)).forEach(k => { o[k] = window[k]; });
            return o; }""")
        nav.close()
    srv.shutdown()
    fautes = []
    for k, v in ctl.items():
        if isinstance(v, dict):
            if v.get("mesure") is False:
                fautes.append(f"{k} : rien mesuré (mesure: false)")
            for c, x in v.items():
                if c.startswith("ecart") and isinstance(x, (int, float)) and x > SEUIL_ECART:
                    fautes.append(f"{k}.{c} = {x} > {SEUIL_ECART}")
            if v.get("erreurs"):
                fautes.append(f"{k}.erreurs : {v['erreurs']}")
    fautes += [f"erreur de page : {e}" for e in erreurs] + [f"console.error : {c}" for c in consoles]
    return {"racine": str(racine), "format": (D.get("format") or {}).get("nom", "9x16"), "taille": taille,
            "montage_ok": bool(montage and montage.get("main")), "controles": ctl, "fautes": fautes}


def main():
    args = sys.argv[1:]
    sortie, attente = None, 4.0
    for opt in ("--json", "--attente"):
        if opt in args:
            i = args.index(opt)
            v = args[i + 1]
            del args[i:i + 2]
            if opt == "--json":
                sortie = Path(v)
            else:
                attente = float(v)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    res, code = [], 0
    for r in args:
        racine = Path(r).resolve()
        if not (racine / "outils" / "banc-film.html").exists():
            raise SystemExit(f"{racine} : pas de outils/banc-film.html (copie faite par outils/format.py ?)")
        x = relever(racine, attente)
        res.append(x)
        etat = "ok" if not x["fautes"] and x["montage_ok"] else "ÉCHEC"
        print(f"{etat:5s} {x['format']:5s} {racine}")
        for k, v in x["controles"].items():
            print(f"      {k} = {json.dumps(v, ensure_ascii=False)}")
        for f in x["fautes"]:
            print(f"   ✗ {f}")
        if etat != "ok":
            code = 1
    if sortie:
        sortie.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        print(f"rapport : {sortie}")
    return code


if __name__ == "__main__":
    sys.exit(main())
