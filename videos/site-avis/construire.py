#!/usr/bin/env python3
"""Boucles vidéo de vokio.fr/avis/ (06/10/2026) : sms/index.html et etapes/index.html, rendables par HyperFrames.
  python3 construire.py
sms : gabarits/sms.src.html + pièces iPhone (Messages iOS) reprises telles quelles de ../pub-secretaire/gabarit.html, la source unique
de l'iPhone (même extraction que ../pub-metiers/construire.py). etapes : gabarits/etapes.src.html seul.
Les gabarits vivent HORS des dossiers rendus : HyperFrames prend tout .html à data-composition-id pour une entrée
(lint multiple_root_compositions) et avait rendu le gabarit, jetons non remplacés : vidéo vide.
Aperçu sans rendu : /root/.pwtest/bin/python3 apercu.py sms|etapes [--instants …]
Rendu : python3 rendre.py (les deux MP4 + affiches, dans /opt/vokio-site-repo/assets/ sous un nom versionné).
"""
import os, re
ICI = os.path.dirname(os.path.abspath(__file__))
src = open(f"{ICI}/../pub-secretaire/gabarit.html", encoding="utf-8").read()
def entre(a, b):
    i = src.index(a); return src[i:src.index(b, i)]
css = entre("#sms{position:absolute;inset:0}", "/* fin */")
html = entre('  <div id="sms" data-layout-allow-overflow>', '  <div id="titre2"')
arrondi = entre("  function arrondi(x, y, w, h, r, xi) {", "  function construire() {")
js = entre('    const sms = $("#sms");', "    // ---------------- la révélation")
for a, b in [("const K = 2.45, K0", "const K = ip.K, K0"), ("const heure = \"16:49\", txt = ", "const heure = ip.heure, txt = ip.txt; const _ancien = "),
             ("yE = 330,", "yE = ip.yE,")]:
    assert a in js, a; js = js.replace(a, b)
g = open(f"{ICI}/gabarits/sms.src.html", encoding="utf-8").read()
g = g.replace("__CSS_IPHONE__", css).replace("__HTML_IPHONE__", html).replace("__ARRONDI__", arrondi).replace("__JS_IPHONE__", js)
assert not re.search(r"__[A-Z_]+__", g), "jeton non remplacé"
open(f"{ICI}/sms/index.html", "w", encoding="utf-8").write(g)
e = open(f"{ICI}/gabarits/etapes.src.html", encoding="utf-8").read() if os.path.exists(f"{ICI}/gabarits/etapes.src.html") else None
if e:
    open(f"{ICI}/etapes/index.html", "w", encoding="utf-8").write(e)
print("sms/index.html" + (" · etapes/index.html" if e else ""))
