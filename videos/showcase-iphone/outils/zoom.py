#!/usr/bin/env python3
"""Planche ZOOMÉE d'une région du cadre sur des instants précis (hf snapshot), pour juger un détail image par image :

    python3 outils/zoom.py <racine> --images 552-560 [--boite x0,y0,x1,y1] [--echelle 1] [--cols 3] -o planche.png [--png D]

  <racine> : projet rendable (9:16 ou copie de format). --images : numéros d'images (« 552-560 », « 519,534,551 »,
  combinables) ; l'instant de l'image n = ceil(n / fps, 6 décimales) (jamais avant l'image, comme outils/revue_scene.py). hf snapshot sous flock /tmp/hf-rendu.lock → --png D (défaut : dossier temporaire effacé),
  puis chaque image est recadrée sur --boite (défaut : le cadre entier), agrandie × --echelle, étiquetée
  « image n · t s » et posée en grille de --cols colonnes. Lecture seule sur <racine> ; idempotent.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HF = "/opt/vokio-ads/bin/hf"
VERROU = "/tmp/hf-rendu.lock"


def lire_images(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    return sorted(set(out))


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("racine")
    A.add_argument("--images", required=True)
    A.add_argument("--boite")
    A.add_argument("--echelle", type=float, default=1.0)
    A.add_argument("--cols", type=int, default=3)
    A.add_argument("-o", "--sortie", required=True)
    A.add_argument("--png")
    a = A.parse_args()
    racine = Path(a.racine).resolve()
    t = (racine / "donnees" / "donnees.js").read_text()
    D = json.loads(t[t.index("{"):t.rindex("}") + 1])
    fps = D.get("fps", 30)
    images = lire_images(a.images)
    instants = {n: f"{math.ceil(round(n / fps, 9) * 1e6) / 1e6:.6f}" for n in images}
    tmp = None
    if a.png:
        dossier = Path(a.png).resolve()
        if dossier.exists():
            shutil.rmtree(dossier)
    else:
        tmp = tempfile.mkdtemp(prefix="zoom-")
        dossier = Path(tmp)
    subprocess.run(["flock", VERROU, HF, "snapshot", str(racine), "--no-end", "--at", ",".join(instants.values()),
                    "-o", str(dossier), "--describe", "false"], check=True, capture_output=True)
    dispo = {}
    for f in dossier.glob("*.png"):
        m = re.search(r"at-([0-9.]+)s", f.name)
        if m:
            dispo[float(m.group(1))] = f
    try:
        police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        police = ImageFont.load_default()
    vignettes = []
    for n in images:
        tv = float(instants[n])
        f = min(dispo, key=lambda x: abs(x - tv))
        im = Image.open(dispo[f]).convert("RGB")
        if a.boite:
            im = im.crop(tuple(int(v) for v in a.boite.split(",")))
        if a.echelle != 1:
            im = im.resize((int(im.width * a.echelle), int(im.height * a.echelle)), Image.LANCZOS)
        vignettes.append((n, tv, im))
    w, h = vignettes[0][2].size
    cols = min(a.cols, len(vignettes))
    rows = (len(vignettes) + cols - 1) // cols
    feuille = Image.new("RGB", (cols * (w + 12) + 12, rows * (h + 36) + 12), (255, 255, 255))
    d = ImageDraw.Draw(feuille)
    for i, (n, tv, im) in enumerate(vignettes):
        x, y = 12 + (i % cols) * (w + 12), 12 + (i // cols) * (h + 36)
        feuille.paste(im, (x, y + 24))
        d.text((x, y + 2), f"image {n} · {tv:.3f} s", fill=(38, 32, 25), font=police)
    feuille.save(a.sortie)
    if tmp:
        shutil.rmtree(tmp)
    print(f"{len(vignettes)} image(s) → {a.sortie}")


if __name__ == "__main__":
    main()
