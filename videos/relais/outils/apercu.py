#!/usr/bin/env python3
"""Aperçu rapide d'un projet de carte (sans rendu) : instants choisis, capturés dans Chromium, en une planche : usage :

    /root/.pwtest/bin/python3 outils/apercu.py <carte>/<boucle|complete> -o planche.png [--at 1,2.5,…] [--pas 0.5] [--cote 360]
                                              [--json etat.json]

  Chaque vignette porte l'instant et le nombre d'ÉLÉMENTS visibles (data-el, opacité effective > 0,02 : règle des trois
  éléments). --json écrit, par instant, les éléments visibles, le plus petit corps de texte visible (px du cadre) et les
  erreurs internes du gabarit (window.__relais.erreurs). Sert aussi à controles_relais.py (fonction etat()).
"""
import argparse
import asyncio
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

JS_ETAT = """(t) => {
  const tl = window.__timelines.relais; tl.seek(t, false);
  const op = (e) => { let o = 1; for (let x = e; x && x !== document.body; x = x.parentElement) {
      const c = getComputedStyle(x); if (c.display === 'none' || c.visibility === 'hidden') return 0; o *= parseFloat(c.opacity); } return o; };
  const els = [...document.querySelectorAll('[data-el]')].filter((e) => op(e) > 0.02).map((e) => e.dataset.el);
  let corps = Infinity, textes = [];
  const r0 = document.getElementById('root').getBoundingClientRect(), k = r0.width / 1080;
  const w = document.createTreeWalker(document.getElementById('root'), NodeFilter.SHOW_TEXT);
  let hors = [], derog = new Set(), horsSit = [];
  while (w.nextNode()) { const n = w.currentNode, e = n.parentElement; if (!n.textContent.trim() || op(e) < 0.3) continue;
    if (e.closest('#mesure')) continue;
    if (e.closest('[data-derogation]')) { derog.add(e.closest('[data-derogation]').dataset.derogation); continue; }
    const fs = parseFloat(getComputedStyle(e).fontSize); corps = Math.min(corps, fs); textes.push(n.textContent.trim());
    if (!e.closest('#situation')) horsSit.push(n.textContent.trim());
    const r = document.createRange(); r.selectNodeContents(n); const b = r.getBoundingClientRect();
    const x0 = (b.left - r0.left) / k, x1 = (b.right - r0.left) / k, y0 = (b.top - r0.top) / k, y1 = (b.bottom - r0.top) / k;
    if (!e.closest('#sms') && (x0 < 60 || x1 > 1020 || y0 < 40 || y1 > 1060)) hors.push([n.textContent.trim().slice(0, 30), Math.round(x0), Math.round(y0), Math.round(x1), Math.round(y1)]);
  }
  return { t, textes_hors_situation: horsSit, derogations: [...derog], elements: els, n: els.length, corps_min: corps === Infinity ? null : corps, textes, hors_marges: hors };
}"""


async def etat(projet, instants, captures=None, cote=360):
    out = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1080})
        erreurs = []
        pg.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
        await pg.goto(Path(projet, "index.html").resolve().as_uri())
        await pg.wait_for_function("window.__relais && window.__relais.pret", timeout=30000)
        for t in instants:
            e = await pg.evaluate(JS_ETAT, t)
            if captures is not None:
                png = await pg.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
                captures.append(Image.open(io.BytesIO(png)).convert("RGB").resize((cote, cote), Image.LANCZOS))
            out.append(e)
        internes = await pg.evaluate("window.__relais")
        await b.close()
    return out, erreurs, internes


def main():
    A = argparse.ArgumentParser()
    A.add_argument("projet")
    A.add_argument("-o", "--sortie")
    A.add_argument("--at")
    A.add_argument("--pas", type=float, default=0.5)
    A.add_argument("--cote", type=int, default=360)
    A.add_argument("--cols", type=int, default=6)
    A.add_argument("--json")
    a = A.parse_args()
    D = json.loads(Path(a.projet, "donnees.js").read_text().split("=", 1)[1].rstrip().rstrip(";"))
    inst = [float(x) for x in a.at.split(",")] if a.at else [round(k * a.pas, 3) for k in range(int(D["duree"] / a.pas) + 1) if k * a.pas < D["duree"]]
    caps = [] if a.sortie else None
    E, err, internes = asyncio.run(etat(a.projet, inst, caps, a.cote))
    if a.sortie:
        c = a.cols
        L = math.ceil(len(caps) / c)
        P = Image.new("RGB", (c * (a.cote + 6) + 6, L * (a.cote + 30) + 6), (140, 140, 140))
        f = ImageFont.load_default()
        for k, (im, e) in enumerate(zip(caps, E)):
            x, y = 6 + (k % c) * (a.cote + 6), 6 + (k // c) * (a.cote + 30)
            P.paste(im, (x, y + 24))
            ImageDraw.Draw(P).text((x + 2, y + 4), f"{e['t']:.2f}s  {e['n']} él.  corps {e['corps_min']}", fill=(255, 255, 255), font=f)
        P.save(a.sortie)
        print("planche :", a.sortie)
    trop = [e for e in E if e["n"] > 3]
    print(f"{len(E)} instants ; > 3 éléments : {[(e['t'], e['elements']) for e in trop]} ; erreurs : {err or internes.get('erreurs')}")
    if a.json:
        Path(a.json).write_text(json.dumps({"instants": E, "erreurs": err, "internes": internes}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
