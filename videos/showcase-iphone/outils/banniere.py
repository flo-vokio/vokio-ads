#!/usr/bin/env python3
"""Bannière d'accompagnement YouTube (companion banner) aux couleurs Vokio, à la taille exacte exigée par Google.

    python3 outils/banniere.py -o youtube/banniere-300x60.png [--taille 300x60] [--texte "Votre ligne répond, même quand vous ne pouvez pas."]
                               [--echelle 2 --o2 youtube/banniere-600x120.png]

Rendu par Chromium (Playwright de /root/.pwtest) avec les vraies polices du film (Instrument Serif, Geist) :
wordmark « Vokıo » (ı sans point + point solaire aux cotes de la DA : left 63,5 %, margin-left -.055em,
top .13em, .11em) à gauche, une phrase courte à droite, fond papier. Vérifie la taille et le poids (< 150 Ko).
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path
ICI = Path(__file__).resolve().parent.parent
FONTES = ICI / "assets" / "fonts"
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:IS;src:url('{f}/InstrumentSerif-Regular.woff2')}}
@font-face{{font-family:ISI;src:url('{f}/InstrumentSerif-Italic.woff2')}}
@font-face{{font-family:G;src:url('{f}/Geist-Regular.woff2')}}
html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:#F4F1E8}}
#b{{box-sizing:border-box;width:{w}px;height:{h}px;display:flex;align-items:center;gap:{gap}px;padding:0 {pad}px;
    border:1px solid rgba(38,32,25,.14)}}
#mot{{font-family:IS;font-size:{fm}px;line-height:1;letter-spacing:-.045em;color:#262019;display:inline-flex;align-items:baseline}}
#mot .i{{position:relative}}
#pt{{position:absolute;left:63.5%;margin-left:-.055em;top:.13em;width:.11em;height:.11em;border-radius:50%;background:#EFA424}}
#t{{font-family:ISI;font-size:{ft}px;line-height:1.1;color:#262019}}
</style></head><body><div id="b"><span id="mot">Vok<span class="i">ı<span id="pt"></span></span>o</span><span id="t">{texte}</span></div></body></html>"""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-o", "--sortie", required=True)
    p.add_argument("--taille", default="300x60")
    p.add_argument("--texte", default="Votre ligne répond, même quand vous ne pouvez pas.")
    p.add_argument("--echelle", type=float, default=1.0)
    a = p.parse_args()
    w, h = map(int, a.taille.split("x"))
    html = HTML.format(f=FONTES.as_uri(), w=w, h=h, gap=round(w * .04), pad=round(w * .045), fm=round(h * .62),
                       ft=round(h * .245), texte=a.texte)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "b.html"; page.write_text(html)
        script = f"""
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    nav = pw.chromium.launch(); ctx = nav.new_context(viewport={{"width": {w}, "height": {h}}}, device_scale_factor={a.echelle})
    pg = ctx.new_page(); pg.goto("{page.as_uri()}"); pg.wait_for_timeout(600)
    pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(200)
    pg.screenshot(path="{Path(a.sortie).resolve()}", clip={{"x": 0, "y": 0, "width": {w}, "height": {h}}})
    nav.close()
"""
        subprocess.run(["/root/.pwtest/bin/python", "-c", script], check=True)
    from PIL import Image
    im = Image.open(a.sortie); ko = Path(a.sortie).stat().st_size / 1024
    attendu = (round(w * a.echelle), round(h * a.echelle))
    ok = im.size == attendu and ko < 150
    print(f"{a.sortie} : {im.size[0]}×{im.size[1]} px, {ko:.0f} Ko {'✓' if ok else '✗ (attendu ' + str(attendu) + ', < 150 Ko)'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
