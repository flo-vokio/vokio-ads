#!/usr/bin/env python3
"""Planche du GESTE d'une carte : les images de la boucle livrée, une par image (ou tous les --pas images), sur la fenêtre du
geste d'ouverture, pour juger l'animation image par image : usage en une ligne :

    python3 outils/planche_geste.py <carte>/recette.json [--de 0.1] [--a 1.4] [--pas 2] [--cote 260] [--cadre x,y,l,h]

  Lit /root/vokio-uploads/videos/relais/<nom>-boucle.mp4 ; écrit <carte>/planche-geste.png (numéro d'image et instant sur
  chaque vignette). --cadre : recadrage en px du 1080 (défaut : le cadre entier).
"""
import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

SORTIES = Path("/root/vokio-uploads/videos/relais")


def main():
    A = argparse.ArgumentParser()
    A.add_argument("recette")
    A.add_argument("--de", type=float, default=0.1)
    A.add_argument("--a", type=float, default=1.4)
    A.add_argument("--pas", type=int, default=2)
    A.add_argument("--cote", type=int, default=260)
    A.add_argument("--cols", type=int, default=7)
    A.add_argument("--cadre", default="0,0,1080,1080")
    a = A.parse_args()
    rec = Path(a.recette).resolve()
    R = json.loads(rec.read_text())
    f = SORTIES / f"{R['nom']}-boucle.mp4"
    x, y, l, h = (int(v) for v in a.cadre.split(","))
    hh = round(a.cote * h / l)
    N = list(range(round(a.de * 30), round(a.a * 30) + 1, a.pas))
    L = (len(N) + a.cols - 1) // a.cols
    P = Image.new("RGB", (a.cols * (a.cote + 6) + 6, L * (hh + 24) + 6), (140, 140, 140))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-vf", f"crop={l}:{h}:{x}:{y},scale={a.cote}:{hh}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    taille = a.cote * hh * 3
    for k, n in enumerate(N):
        im = Image.frombytes("RGB", (a.cote, hh), raw[n * taille:(n + 1) * taille])
        px, py = 6 + (k % a.cols) * (a.cote + 6), 6 + (k // a.cols) * (hh + 24)
        P.paste(im, (px, py + 18))
        ImageDraw.Draw(P).text((px + 2, py + 3), f"image {n} · {n / 30:.3f} s", fill=(255, 255, 255))
    out = rec.parent / "planche-geste.png"
    P.save(out, optimize=True)
    print("planche du geste :", out)


if __name__ == "__main__":
    main()
