#!/usr/bin/env python3
"""Extrait EN MOUVEMENT d'un ou plusieurs projets rendables, côte à côte, avec la bande son, sans MP4 plein film : usage :

    python3 outils/extrait_mouvement.py <racine>=<étiquette> [<racine2>=<étiquette2> …] --de 33.5 --a 42.3 --sortie x.mp4
                                        [--echelle 0.5] [--empiler h|v] [--zones] [--ralenti 4] [--sans-son] [--travail D]
    python3 outils/extrait_mouvement.py <racine>=<étiquette> … --instants 35.6,36.4,38,41.233 --sortie planche.png [--zones]

  Pour comparer deux mises en page d'une scène (ex. le 16:9 par défaut et une variante) quand hf render est impossible
  (HyperFrames refuse de rendre sous 1 Gio libre) ou trop long (le film entier pour 8 s utiles) :
   1. hf snapshot de CHAQUE image de [--de, --a] dans chaque racine (sous flock /tmp/hf-rendu.lock, instants arrondis vers le
      haut comme revue_scene.py : l'image exacte du rendu), réduites à --echelle puis les PNG effacés aussitôt (≈ 100 ko par
      image 16:9 le temps d'une racine : le disque ne gonfle pas) ;
   2. assemblage côte à côte (--empiler h, défaut) ou l'une sous l'autre (v), un bandeau d'étiquette au-dessus de chaque
      vue (l'étiquette, puis « image n · t s ») ; --zones : les zones sûres du format (mise-en-page/formats.json, d'après la
      taille du cadre ; terracotta = interdite, solaire = prudence) ;
   3. H.264 yuv420p CRF 18 à la cadence du film, avec la bande son de la 1re racine (assets/son/mix.wav, coupée à la même
      fenêtre) ; --ralenti N : chaque image tenue N fois, sans son (pour juger un départ de 15 images).
  --instants t,t,… (au lieu de --de/--a) : une PLANCHE PNG, une ligne par instant (l'image qui le contient), les vues côte à
      côte ; mêmes bandeaux, mêmes zones.
  --travail D : dossier des images (défaut : un dossier temporaire, effacé à la fin). Idempotent : --sortie est réécrit.
  Exemple : extrait_mouvement.py formats/16x9=A /tmp/x/fC=variante --de 33.5 --a 42.3 --sortie /tmp/x/s6-A-C.mp4 --zones
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revue_scene as RS  # noqa: E402

PROJET = Path(__file__).resolve().parents[1]
BANDEAU = 44


def zones_du_cadre(w, h):
    F = json.loads((PROJET / "mise-en-page" / "formats.json").read_text())
    for k, v in F.items():
        if isinstance(v, dict) and v.get("largeur") == w and v.get("hauteur") == h:
            return v.get("zones", []), v.get("marge_laterale")
    return [], None


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("vues", nargs="+", help="<racine>=<étiquette>")
    A.add_argument("--de", type=float)
    A.add_argument("--a", type=float)
    A.add_argument("--instants")
    A.add_argument("--sortie", required=True)
    A.add_argument("--echelle", type=float, default=0.5)
    A.add_argument("--empiler", choices=["h", "v"], default="h")
    A.add_argument("--zones", action="store_true")
    A.add_argument("--ralenti", type=int, default=1)
    A.add_argument("--sans-son", action="store_true")
    A.add_argument("--travail")
    a = A.parse_args()
    vues = []
    for v in a.vues:
        r, _, lab = v.partition("=")
        vues.append((Path(r).resolve(), lab or Path(r).name))
    D0 = RS.donnees(vues[0][0])
    fps = D0["fps"]
    if a.instants:
        ks = sorted({int(math.floor(float(t) * fps + 1e-6)) for t in a.instants.split(",")})
    elif a.de is not None and a.a is not None:
        ks = list(range(int(math.floor(a.de * fps + 1e-6)), int(math.floor(a.a * fps + 1e-6)) + 1))
    else:
        raise SystemExit("--de et --a (extrait MP4) ou --instants (planche PNG)")
    n0, n1 = ks[0], ks[-1]
    liste = [(k, RS.temps(k, fps), "") for k in ks]
    tmp = Path(a.travail) if a.travail else Path(tempfile.mkdtemp(prefix="extrait-"))
    tmp.mkdir(parents=True, exist_ok=True)
    reduites = []
    for i, (racine, lab) in enumerate(vues):
        D = RS.donnees(racine)
        if D["fps"] != fps:
            raise SystemExit(f"{racine} : {D['fps']} i/s ≠ {fps}")
        print(f"→ {lab} : {len(liste)} images ({n0} → {n1}) de {racine}", flush=True)
        S = RS.snapshots(racine, liste, tmp / f"png-{i}")
        dos = tmp / f"v{i}"
        dos.mkdir(exist_ok=True)
        zones, marge = (None, None)
        for k, p in S.items():
            im = Image.open(p).convert("RGB")
            if a.zones:
                if zones is None:
                    zones, marge = zones_du_cadre(*im.size)
                dr = ImageDraw.Draw(im, "RGBA")
                for z in zones:
                    c = (192, 69, 44, 60) if z["sorte"] == "interdite" else (239, 164, 36, 40)
                    dr.rectangle(z["boite"], fill=c, outline=c[:3] + (170,), width=3)
            im = im.resize((int(im.width * a.echelle) // 2 * 2, int(im.height * a.echelle) // 2 * 2), Image.LANCZOS)
            im.save(dos / f"{k:05d}.png")
        shutil.rmtree(tmp / f"png-{i}")
        reduites.append((dos, lab))
    P = RS.police(22)
    comp = tmp / "comp"
    comp.mkdir(exist_ok=True)
    for k, t, _ in liste:
        ims = [Image.open(d / f"{k:05d}.png") for d, _ in reduites]
        w, h = ims[0].size
        if a.empiler == "h":
            F = Image.new("RGB", (w * len(ims) + 8 * (len(ims) - 1), h + BANDEAU), (255, 255, 255))
        else:
            F = Image.new("RGB", (w, (h + BANDEAU) * len(ims)), (255, 255, 255))
        dr = ImageDraw.Draw(F)
        for j, (im, (_, lab)) in enumerate(zip(ims, reduites)):
            x, y = (j * (w + 8), 0) if a.empiler == "h" else (0, j * (h + BANDEAU))
            F.paste(im, (x, y + BANDEAU))
            dr.text((x + 10, y + 10), f"{lab}  ·  image {k}  ·  {t:.3f} s", fill=(38, 32, 25), font=P)
        W2, H2 = F.size[0] // 2 * 2, F.size[1] // 2 * 2
        F.crop((0, 0, W2, H2)).save(comp / f"{k:05d}.png")
    for d, _ in reduites:
        shutil.rmtree(d)
    sortie = Path(a.sortie).resolve()
    sortie.parent.mkdir(parents=True, exist_ok=True)
    if a.instants:
        ims = [Image.open(comp / f"{k:05d}.png") for k, _, _ in liste]
        F = Image.new("RGB", (ims[0].width, sum(i.height for i in ims) + 8 * (len(ims) - 1)), (255, 255, 255))
        y = 0
        for im in ims:
            F.paste(im, (0, y))
            y += im.height + 8
        F.save(sortie)
        if not a.travail:
            shutil.rmtree(tmp)
        print(f"→ {sortie} (planche, {len(ims)} instants × {len(vues)} vues)")
        return 0
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(fps / a.ralenti), "-start_number", str(n0),
           "-i", str(comp / "%05d.png")]
    son = vues[0][0] / "assets" / "son" / "mix.wav"
    avec_son = not a.sans_son and a.ralenti == 1 and son.exists()
    if avec_son:
        cmd += ["-ss", f"{n0 / fps:.6f}", "-t", f"{(n1 - n0 + 1) / fps:.6f}", "-i", str(son), "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-r", str(fps), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(sortie)]
    subprocess.run(cmd, check=True)
    if not a.travail:
        shutil.rmtree(tmp)
    print(f"→ {sortie} ({sortie.stat().st_size // 1024} ko, {len(liste)} images{', avec son' if avec_son else ''}"
          f"{f', ralenti ×{a.ralenti}' if a.ralenti > 1 else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
