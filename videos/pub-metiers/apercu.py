#!/usr/bin/env python3
"""Planche d'aperçu sans rendu (Chromium, seek du timeline) + erreurs internes : usage :
  /root/.pwtest/bin/python3 apercu.py [-o /dev/shm/pub-apercu.png] [--instants 0,1,2.5,...]
"""
import argparse, json, os, sys
from playwright.sync_api import sync_playwright
from PIL import Image
ICI = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("-o", default="/dev/shm/pub-apercu.png"); ap.add_argument("--instants", default=None); ap.add_argument("--echelle", type=float, default=0.3)
a = ap.parse_args()
m = json.load(open(f"{ICI}/donnees/montage.json"))
ts = [float(x) for x in a.instants.split(",")] if a.instants else [round(x * 1.0, 2) for x in range(0, int(m["duree"]) + 1)]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto("file://" + ICI + "/index.html")
    for _ in range(100):
        if pg.evaluate("!!(window.__pub && window.__pub.pret)"): break
        pg.wait_for_timeout(100)
    info = pg.evaluate("JSON.parse(JSON.stringify({erreurs: __pub.erreurs, pages: __pub.pages, objets: __pub.objets, non_montres: __pub.non_montres, bulle_bas: __pub.bulle_bas}))")
    ims = []
    for t in ts:
        pg.evaluate(f"__timelines.pub.seek({t}, false), 0")
        pg.wait_for_timeout(30)
        f = f"/dev/shm/pub-ap-{t}.png"; pg.screenshot(path=f); ims.append((t, f))
    b.close()
print(json.dumps(info, ensure_ascii=False, indent=1))
w, h = int(1080 * a.echelle), int(1920 * a.echelle)
cols = 6; rows = (len(ims) + cols - 1) // cols
from PIL import ImageDraw
pl = Image.new("RGB", (cols * w, rows * (h + 24)), "white")
d = ImageDraw.Draw(pl)
for k, (t, f) in enumerate(ims):
    im = Image.open(f).convert("RGB").resize((w, h))
    x, y = (k % cols) * w, (k // cols) * (h + 24)
    pl.paste(im, (x, y + 24)); d.text((x + 6, y + 4), f"{t:.2f} s", fill="black")
    # zones Meta : 250 / 1250
    d.line([(x, y + 24 + 250 * a.echelle), (x + w, y + 24 + 250 * a.echelle)], fill=(220, 60, 60))
    d.line([(x, y + 24 + 1250 * a.echelle), (x + w, y + 24 + 1250 * a.echelle)], fill=(220, 60, 60))
    os.remove(f)
pl.save(a.o); print(a.o)
