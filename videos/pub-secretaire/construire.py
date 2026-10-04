#!/usr/bin/env python3
"""index.html (rendable par HyperFrames) depuis gabarit.html + donnees/montage.json + la situation « évier » du relais.
  python3 son/monter.py && python3 construire.py
"""
import json, os
ICI = os.path.dirname(os.path.abspath(__file__))
g = open(f"{ICI}/gabarit.html", encoding="utf-8").read()
m = json.load(open(f"{ICI}/donnees/montage.json"))
svg = open(f"{ICI}/situations/evier.svg", encoding="utf-8").read()
g = g.replace("__EVIER__", svg + '\n<script src="situations/evier.js"></script>').replace("__DUREE__", str(m["duree"]))
assert "__" not in g.split("<script>")[0].replace("__timelines", ""), "jeton non remplacé"
open(f"{ICI}/index.html", "w", encoding="utf-8").write(g)
print(f"index.html · {m['duree']} s")
