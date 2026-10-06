#!/usr/bin/env python3
"""Planche d'aperçu sans rendu (Chromium, seek du timeline) + erreurs internes.
  /root/.pwtest/bin/python3 apercu.py sms|etapes [--instants 0,1,2] [-o /dev/shm/x.png]"""
import argparse, json, os
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
ICI = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("projet"); ap.add_argument("--instants"); ap.add_argument("-o")
a = ap.parse_args()
ID = {"sms": "avis-sms", "etapes": "avis-etapes"}[a.projet]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 1080})
    logs = []; pg.on("console", lambda m: m.type == "error" and logs.append(m.text)); pg.on("pageerror", lambda e: logs.append(str(e)))
    pg.goto(f"file://{ICI}/{a.projet}/index.html")
    for _ in range(100):
        if pg.evaluate("!!(window.__pub && window.__pub.pret)"): break
        pg.wait_for_timeout(100)
    dur = pg.evaluate(f"__timelines['{ID}'].duration()")
    ts = [float(x) for x in a.instants.split(",")] if a.instants else [round(i * 0.5, 2) for i in range(int(dur * 2) + 1)]
    ims = []
    for t in ts:
        pg.evaluate(f"__timelines['{ID}'].seek({t}, false), 0"); pg.wait_for_timeout(40)
        f = f"/dev/shm/{a.projet}-ap-{t}.png"; pg.screenshot(path=f); ims.append((t, f))
    info = pg.evaluate("JSON.parse(JSON.stringify({erreurs: __pub.erreurs}))")
    b.close()
print(json.dumps({"duree": dur, **info, "console": logs[:5]}, ensure_ascii=False))
e = 0.28; w = h = int(1080 * e); cols = 6; rows = (len(ims) + cols - 1) // cols
pl = Image.new("RGB", (cols * w, rows * (h + 22)), "white"); d = ImageDraw.Draw(pl)
for k, (t, f) in enumerate(ims):
    x, y = (k % cols) * w, (k // cols) * (h + 22)
    pl.paste(Image.open(f).convert("RGB").resize((w, h)), (x, y + 22)); d.text((x + 6, y + 4), f"{t:.2f} s", fill="black"); os.remove(f)
out = a.o or f"/dev/shm/{a.projet}-apercu.png"; pl.save(out); print(out)
