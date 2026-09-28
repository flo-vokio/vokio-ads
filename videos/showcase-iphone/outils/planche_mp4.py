#!/usr/bin/env python3
"""Planches de relecture d'un MP4 rendu, en plusieurs feuilles lisibles (1 image toutes les --pas s) : usage en une ligne :

    python3 outils/planche_mp4.py film.mp4 -o dossier/ [--pas 0.5] [--cols 4] [--largeur 480] [--par-feuille 24]
                                  [--zones <racine>] [--de 0 --a 47]

  Décode le film en flux (ffmpeg, rien sur le disque) et garde l'image n = ceil(t × fps) pour t = de, de + pas, … (jamais
  avant l'instant, comme outils/revue_scene.py). Chaque image est réduite à --largeur px, étiquetée « image n · t s » et
  posée en grille de --cols colonnes ; une feuille par --par-feuille images → <dossier>/planche-01.png, -02… (une feuille
  entière se lit d'un coup d'œil, contrairement à une planche géante réduite à l'affichage).
  --zones <racine> : dessine par-dessus les zones sûres de DONNEES.format de <racine> (rouge = interdite, ambre = prudence)
  et les marges latérales, comme outils/format.py --planche.
  Idempotent (les feuilles sont réécrites, les anciennes planche-*.png du dossier effacées). Lecture seule sur le film.
Exemple : planche_mp4.py /root/vokio-uploads/videos/showcase/le-point-sur-le-i-16x9-image.mp4 -o /tmp/x --zones formats/16x9
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def infos(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_read_packets", "-of", "json", str(mp4)], capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(a) / float(b), int(s["nb_read_packets"])


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("film")
    A.add_argument("-o", "--dossier", required=True)
    A.add_argument("--pas", type=float, default=0.5)
    A.add_argument("--cols", type=int, default=4)
    A.add_argument("--largeur", type=int, default=480)
    A.add_argument("--par-feuille", type=int, default=24)
    A.add_argument("--zones")
    A.add_argument("--de", type=float, default=0.0)
    A.add_argument("--a", type=float)
    a = A.parse_args()
    W, H, fps, total = infos(a.film)
    fin = a.a if a.a is not None else total / fps
    voulues, t = [], a.de
    while t < fin - 1e-9:
        n = min(total - 1, math.ceil(round(t * fps, 6)))
        if not voulues or voulues[-1][0] != n:
            voulues.append((n, t))
        t = round(t + a.pas, 6)
    F = None
    if a.zones:
        js = (Path(a.zones) / "donnees" / "donnees.js").read_text()
        F = json.loads(js[js.index("{"):js.rindex("}") + 1]).get("format")
    cible = {n for n, _ in voulues}
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(a.film), "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    k = a.largeur / W
    w, h = a.largeur, int(round(H * k))
    vignettes, n = {}, 0
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        if n in cible:
            im = Image.fromarray(np.frombuffer(buf, np.uint8).reshape(H, W, 3))
            if F:
                dr = ImageDraw.Draw(im, "RGBA")
                for z in F.get("zones", []):
                    c = (192, 69, 44, 60) if z["sorte"] == "interdite" else (239, 164, 36, 40)
                    dr.rectangle(z["boite"], fill=c, outline=c[:3] + (200,), width=3)
                m = F["marge_laterale"]
                for x in (m, W - m):
                    dr.line([(x, 0), (x, H)], fill=(38, 32, 25, 90), width=2)
            vignettes[n] = im.resize((w, h), Image.LANCZOS)
        n += 1
        if n > max(cible):
            break
    p.kill()
    p.wait()
    D = Path(a.dossier)
    D.mkdir(parents=True, exist_ok=True)
    for f in D.glob("planche-*.png"):
        f.unlink()
    try:
        police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        police = ImageFont.load_default()
    feuilles = []
    for i in range(0, len(voulues), a.par_feuille):
        lot = voulues[i:i + a.par_feuille]
        rows = (len(lot) + a.cols - 1) // a.cols
        P = Image.new("RGB", (a.cols * (w + 10) + 10, rows * (h + 34) + 10), (255, 255, 255))
        d = ImageDraw.Draw(P)
        for j, (m, t) in enumerate(lot):
            x, y = 10 + (j % a.cols) * (w + 10), 10 + (j // a.cols) * (h + 34)
            d.text((x, y + 2), f"image {m} · {t:.2f} s", fill=(38, 32, 25), font=police)
            if m in vignettes:
                P.paste(vignettes[m], (x, y + 24))
        f = D / f"planche-{len(feuilles) + 1:02d}.png"
        P.save(f)
        feuilles.append(str(f))
        print(f"{f} : {lot[0][1]:.2f} → {lot[-1][1]:.2f} s ({len(lot)} images)")
    return 0 if feuilles and len(vignettes) == len(voulues) else 1


if __name__ == "__main__":
    sys.exit(main())
