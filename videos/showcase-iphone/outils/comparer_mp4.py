#!/usr/bin/env python3
"""Deux MP4 du même film sont-ils les mêmes images ? Comparaison IMAGE PAR IMAGE, au bit près puis au codec près : usage :

    python3 outils/comparer_mp4.py <reference.mp4> <candidat.mp4> [--json r.json] [--pires planche.png] [--seuil 38] [--chute 3]
                                   [--fort 48] [--part 0.0002] [--n-pires 6]

  Décode les deux films en RGB (ffmpeg, en flux : rien sur le disque) et compare chaque image n à l'image n :
    identiques  md5 des pixels égaux (même rendu, même encodeur : c'est la preuve la plus forte) ;
    au codec    sinon : PSNR ≥ --seuil dB, pas plus de --chute dB sous le PSNR médian du film, au plus --part des pixels
                (0,02 %) à plus de --fort niveaux d'écart (un objet déplacé d'un pixel dépasse, le bruit du codec non).
  Mêmes nombres d'images et même taille exigés. Imprime le bilan (identiques, conformes, hors tolérance groupées en plages),
  écrit --json (chaque image : md5 égal, PSNR, part de pixels forts) et --pires (planche des images les moins fidèles :
  référence | candidat | écart × 4). Code 0 si toutes les images sont identiques ou conformes, 1 sinon. Lecture seule, idempotent.
Exemple (le 9:16 ne bouge pas) :
    python3 outils/rendre.py /tmp/copie-9x16 -o /dev/shm/c9.mp4 && \\
    python3 outils/comparer_mp4.py /root/vokio-uploads/videos/showcase/le-point-sur-le-i-iphone.mp4 /dev/shm/c9.mp4
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def taille(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        str(mp4)], capture_output=True, text=True, check=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def flux(mp4, w, h):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def plages(nums):
    out = []
    for n in sorted(nums):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [f"{a}" if a == b else f"{a}-{b}" for a, b in out]


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("reference")
    A.add_argument("candidat")
    A.add_argument("--json")
    A.add_argument("--pires")
    A.add_argument("--seuil", type=float, default=38.0)
    A.add_argument("--chute", type=float, default=3.0)
    A.add_argument("--fort", type=int, default=48)
    A.add_argument("--part", type=float, default=0.0002)
    A.add_argument("--n-pires", type=int, default=6)
    a = A.parse_args()
    (wr, hr), (wc, hc) = taille(a.reference), taille(a.candidat)
    if (wr, hr) != (wc, hc):
        raise SystemExit(f"tailles différentes : {wr}×{hr} contre {wc}×{hc}")
    images, garde = [], {}
    fr, fc = flux(a.reference, wr, hr), flux(a.candidat, wc, hc)
    n = 0
    for ir, ic in zip(fr, fc):
        egal = hashlib.md5(ir.tobytes()).digest() == hashlib.md5(ic.tobytes()).digest()
        if egal:
            images.append({"image": n, "identique": True, "psnr": None, "part_forte": 0.0, "ecart_max": 0})
        else:
            d = np.abs(ir.astype(np.int16) - ic.astype(np.int16))
            mse = float((d.astype(np.float64) ** 2).mean())
            psnr = 99.0 if mse == 0 else float(10 * np.log10(255 ** 2 / mse))
            fort = float((d.max(axis=2) > a.fort).mean())
            images.append({"image": n, "identique": False, "psnr": round(psnr, 2), "part_forte": round(fort, 6),
                           "ecart_max": int(d.max())})
            if a.pires:
                garde[n] = (ir.copy(), ic.copy())
                if len(garde) > 4 * a.n_pires:            # ne garder en mémoire que les pires
                    pire = sorted(garde, key=lambda k: images[k]["psnr"])[:2 * a.n_pires]
                    garde = {k: garde[k] for k in pire}
        n += 1
    reste_r, reste_c = sum(1 for _ in fr), sum(1 for _ in fc)
    psnrs = [x["psnr"] for x in images if x["psnr"] is not None]
    med = float(np.median(psnrs)) if psnrs else None
    hors = [x["image"] for x in images if not x["identique"] and (x["psnr"] < a.seuil or x["psnr"] < med - a.chute
                                                                   or x["part_forte"] > a.part)]
    ident = sum(1 for x in images if x["identique"])
    ok = not hors and reste_r == 0 and reste_c == 0 and n > 0
    bilan = {"reference": str(a.reference), "candidat": str(a.candidat), "taille": [wr, hr], "images": n,
             "images_en_trop": {"reference": reste_r, "candidat": reste_c}, "identiques": ident,
             "conformes_au_codec": n - ident - len(hors), "hors_tolerance": plages(hors),
             "psnr": {"min": min(psnrs) if psnrs else None, "median": med, "max": max(psnrs) if psnrs else None},
             "part_forte_max": max((x["part_forte"] for x in images), default=0),
             "criteres": {"seuil_db": a.seuil, "chute_db": a.chute, "fort_niveaux": a.fort, "part_max": a.part}, "ok": ok}
    print(json.dumps({k: v for k, v in bilan.items()}, ensure_ascii=False))
    print(("ok  " if ok else "NON ") + f"{ident}/{n} images identiques au bit près, {n - ident - len(hors)} conformes au codec, "
          f"{len(hors)} hors tolérance" + (f" ({', '.join(plages(hors)[:12])})" if hors else ""))
    if a.json:
        Path(a.json).write_text(json.dumps(bilan | {"par_image": images}, ensure_ascii=False))
    if a.pires and garde:
        from PIL import Image
        pires = sorted(garde, key=lambda k: images[k]["psnr"])[:a.n_pires]
        k = 480 / max(wr, hr)
        w, h = int(wr * k), int(hr * k)
        P = Image.new("RGB", (3 * w + 16, len(pires) * (h + 8) + 8), (150, 150, 150))
        for i, m in enumerate(pires):
            ir, ic = garde[m]
            d = np.clip(np.abs(ir.astype(np.int16) - ic.astype(np.int16)) * 4, 0, 255).astype(np.uint8)
            for j, x in enumerate((ir, ic, d)):
                P.paste(Image.fromarray(x).resize((w, h), Image.LANCZOS), (4 + j * (w + 4), 8 + i * (h + 8)))
        P.save(a.pires)
        print(f"pires images ({', '.join(str(m) for m in pires)}) : {a.pires}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
