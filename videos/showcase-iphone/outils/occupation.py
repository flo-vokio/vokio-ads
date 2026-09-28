#!/usr/bin/env python3
"""Occupation du cadre d'un MP4, image par image, et bilan par scène (plans-titres) : usage en une ligne :

    python3 outils/occupation.py film.mp4 [--racine formats/16x9] [--pas 0.5] [--de 0 --a 47] [--seuil 24] [--json r.json]

  Pour chaque image échantillonnée (l'image n = de·fps + k·pas·fps, exacte : les mêmes que controles.py O1) : boîte englobante de tout ce qui n'est pas le papier (x0 y0 x1 y1,
  px du cadre), part de la LARGEUR et part du cadre couvertes par cette boîte, part de pixels « non papier », barycentre
  horizontal (0 = bord gauche, 1 = bord droit), pixels solaires (le point) et leur boîte, pixels non papier dans chaque zone
  du format, mouvement (écart moyen avec l'image échantillonnée précédente, niveaux 0 à 255).
  --racine : un projet rendable (9:16 = ce projet, formats/16x9…) : zones lues dans SES données (DONNEES.format), bilan par
    scène (DONNEES.scenes) : pour chaque scène, l'image « pleine » (la plus large boîte d'encre) avec sa part de largeur et son
    barycentre, et les seuils DONNEES.format.occupation s'il y en a (scènes visées, largeur_min, barycentre [min, max]) ;
    sans --racine : zones de mise-en-page/formats.json choisies d'après la taille du film.
  Même mesure que le contrôle O1 de outils/controles.py (fonction mesurer, importée par lui). Lecture seule, idempotent :
  rien n'est écrit hors de --json. Décodage ffmpeg en RGB à pleine taille.
  Promu le 28/09 depuis la revue DA YouTube (scratchpad final/da-youtube/occupation.py).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

PROJET = Path(__file__).resolve().parents[1]
PAPIER = np.array([0xF4, 0xF1, 0xE8], dtype=np.int16)
SOLAIRE = np.array([0xEF, 0xA4, 0x24], dtype=np.int16)


def mesurer(img, zones=(), seuil=24):
    """img (H, W, 3) uint8 → dict : boite, part_largeur, part_boite, part_encre, bary_x, solaire, zones {nom: pixels}."""
    H, W = img.shape[:2]
    f = img.astype(np.int16)
    m = np.abs(f - PAPIER).max(axis=2) > seuil
    r = {}
    if m.any():
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        r.update(boite=[x0, y0, x1, y1], part_largeur=round((x1 - x0 + 1) / W, 3),
                 part_boite=round((x1 - x0 + 1) * (y1 - y0 + 1) / (W * H), 3),
                 part_encre=round(float(m.mean()), 4), bary_x=round(float(xs.mean()) / W, 3))
    else:
        r.update(boite=None, part_largeur=0.0, part_boite=0.0, part_encre=0.0, bary_x=None)
    sol = np.abs(f - SOLAIRE).max(axis=2) < 40
    if sol.sum() > 30:
        ys, xs = np.nonzero(sol)
        r["solaire"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    for z in zones:
        bx0, by0, bx1, by1 = (int(v) for v in z["boite"])
        r.setdefault("zones", {})[z["nom"]] = int(m[by0:by1, bx0:bx1].sum())
    return r


def bilan_scenes(images, scenes, occ):
    """images : [(n, mesure)] ; scenes : DONNEES.scenes ; occ : DONNEES.format.occupation (ou {}) → {scène: bilan}."""
    out = {}
    for nom, s in scenes.items():
        serie = [(k, r) for k, r in images if s["image_debut"] <= k < s["image_fin"] and r.get("boite")]
        if not serie:
            continue
        k, r = max(serie, key=lambda x: x[1]["part_largeur"])
        b = {"image_pleine": k, "part_largeur": r["part_largeur"], "bary_x": r["bary_x"], "boite": r["boite"],
             "serie": [(k_, r_["part_largeur"], r_["bary_x"]) for k_, r_ in serie]}
        if nom in occ.get("scenes", []):
            lo, hi = occ.get("barycentre", [0, 1])
            b["seuils"] = {"largeur_min": occ.get("largeur_min", 0), "barycentre": [lo, hi]}
            b["ok"] = r["part_largeur"] >= occ.get("largeur_min", 0) and lo <= r["bary_x"] <= hi
        out[nom] = b
    return out


def donnees(racine):
    js = (Path(racine) / "donnees" / "donnees.js").read_text()
    i = js.index("window.DONNEES = ") + len("window.DONNEES = ")
    return json.loads(js[i:js.rstrip().rindex(";")])


def taille(film):
    st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                    "-of", "json", str(film)], capture_output=True, text=True, check=True).stdout)["streams"][0]
    n, d = st["r_frame_rate"].split("/")
    return st["width"], st["height"], float(n) / float(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("film")
    ap.add_argument("--racine")
    ap.add_argument("--pas", type=float, default=0.5)
    ap.add_argument("--de", type=float, default=0.0)
    ap.add_argument("--a", type=float, default=None)
    ap.add_argument("--seuil", type=int, default=24, help="écart RGB max au papier (défaut 24)")
    ap.add_argument("--json")
    a = ap.parse_args()
    W, H, fps = taille(a.film)
    D = donnees(a.racine) if a.racine else None
    if D:
        fmt = D.get("format") or {}
        if fmt and (fmt["largeur"], fmt["hauteur"]) != (W, H):
            raise SystemExit(f"occupation.py : le film fait {W}×{H}, la racine {fmt['largeur']}×{fmt['hauteur']}")
    else:
        F = json.loads((PROJET / "mise-en-page" / "formats.json").read_text())
        fmt = next((v for k, v in F.items() if not k.startswith("_") and (v.get("largeur"), v.get("hauteur")) == (W, H)), {})
    zones = fmt.get("zones", [])
    # images EXACTES n = n0, n0 + pas, … (filtre select sur le numéro d'image : les mêmes que controles.py O1, n % 15 == 0)
    k_pas = max(1, int(round(a.pas * fps)))
    n0 = int(np.ceil(a.de * fps - 1e-6))
    n1 = int(np.floor(a.a * fps + 1e-6)) if a.a is not None else 10 ** 9
    sel = f"select='between(n\\,{n0}\\,{n1})*not(mod(n-{n0}\\,{k_pas}))'"
    cmd = ["ffmpeg", "-v", "error", "-i", str(a.film), "-vf", sel, "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    res, prec, k = [], None, 0
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        n_img = n0 + k * k_pas
        r = {"t": round(n_img / fps, 3), "image": n_img} | mesurer(img, zones, a.seuil)
        if prec is not None:
            r["mouvement"] = round(float(np.abs(img.astype(np.int16) - prec).mean()), 3)
        prec = img.astype(np.int16)
        res.append(r)
        k += 1
    p.wait()
    print("     t  image  larg.  bary   encre   boîte                  solaire")
    for r in res:
        print(f"{r['t']:6.2f} {r['image']:6d}  {r['part_largeur']:5.3f}  {r['bary_x'] if r['bary_x'] is not None else '  -  ':>5}  "
              f"{r['part_encre']:6.4f}  {str(r['boite']):22s} {r.get('solaire', '')}")
    sortie = {"film": str(a.film), "taille": [W, H], "pas": a.pas, "images": res}
    if D:
        B = bilan_scenes([(r["image"], r) for r in res], D["scenes"], fmt.get("occupation") or {})
        sortie["scenes"] = B
        print("\nscène            image pleine  largeur  barycentre  seuils")
        for nom, b in B.items():
            s = "" if "ok" not in b else (f"{'ok' if b['ok'] else 'ÉCHEC'} (≥ {b['seuils']['largeur_min']}, "
                                          f"{b['seuils']['barycentre'][0]}–{b['seuils']['barycentre'][1]})")
            print(f"{nom:16s} {b['image_pleine']:12d}  {b['part_largeur']:7.3f}  {b['bary_x']:10.3f}  {s}")
    if a.json:
        Path(a.json).write_text(json.dumps(sortie, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
