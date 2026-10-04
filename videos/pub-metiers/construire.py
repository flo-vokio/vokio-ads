#!/usr/bin/env python3
"""index.html (rendable par HyperFrames) depuis gabarit.src.html + donnees/montage.json, avec les pièces iPhone
(Messages iOS) reprises telles quelles du gabarit de pub-secretaire (une seule source pour l'iPhone).
  python3 son/voix.py && python3 son/monter.py && python3 construire.py
"""
import json, os, re
ICI = os.path.dirname(os.path.abspath(__file__))
src = open(f"{ICI}/../pub-secretaire/gabarit.html", encoding="utf-8").read()
def entre(a, b, inclure_b=False):
    i = src.index(a); j = src.index(b, i)
    return src[i:j + (len(b) if inclure_b else 0)]
css = entre("#sms{position:absolute;inset:0}", "/* fin */")
html = entre('  <div id="sms" data-layout-allow-overflow>', '  <div id="titre2"')
arrondi = entre("  function arrondi(x, y, w, h, r, xi) {", "  function construire() {")
js = entre('    const sms = $("#sms");', "    // ---------------- la révélation")
for a, b in [("const K = 2.45, K0", "const K = ip.K, K0"), ("const heure = \"16:49\", txt = ", "const heure = ip.heure, txt = ip.txt; const _ancien = "),
             ("yE = 330,", "yE = ip.yE,")]:
    assert a in js, a; js = js.replace(a, b)
g = open(f"{ICI}/gabarit.src.html", encoding="utf-8").read()
m = json.load(open(f"{ICI}/donnees/montage.json"))
g = (g.replace("__CSS_IPHONE__", css).replace("__HTML_IPHONE__", html).replace("__ARRONDI__", arrondi)
      .replace("__JS_IPHONE__", js).replace("__DUREE__", str(m["duree"])))
assert not re.search(r"__[A-Z_]+__", g), "jeton non remplacé"
open(f"{ICI}/index.html", "w", encoding="utf-8").write(g)
print(f"index.html · {m['duree']} s")
