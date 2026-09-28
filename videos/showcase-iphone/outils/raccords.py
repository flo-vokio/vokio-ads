#!/usr/bin/env python3
"""Raccords entre scènes À L'IMAGE PRÈS, hors du point, dans un projet rendable (9:16 ou copie de format) : usage en une ligne :

    python3 outils/raccords.py <racine> [--paires s4-agenda:s5-rendez-vous,… | --autour s4-agenda] [--exiger A:B,…]
                               [--seuil 2] [--marge 3] [--images D] [--json rapport.json]

  Pour chaque paire de scènes consécutives (défaut : toutes, dans l'ordre de DONNEES.scenes ; --paires pour choisir),
  prend par hf snapshot (sous flock /tmp/hf-rendu.lock) la DERNIÈRE image de A (image_fin − 1) et la PREMIÈRE de B
  (image_fin de A) ; --autour S : les deux raccords de S (avec la scène d'avant et celle d'après), efface des deux le disque du point racine aux deux instants (POINT.etat, lib/point.js exécuté
  dans node avec GSAP de lib/vendor ; rayon d × max(sx, sy) / 2 + --marge px), puis compare les pixels RGB restants :
  écart max, nombre de pixels à plus de --seuil niveaux, boîte de ces pixels. Planche <D>/raccord-<A>-<B>.png :
  A | B | écarts × 8 (point effacé en gris). Imprime une ligne par paire ; code 1 si une paire de --exiger
  (« mêmes pixels » promis par les scènes, ex. s4-agenda:s5-rendez-vous) a un pixel hors seuil.
  Lecture seule sur <racine> ; n'écrit que --images (défaut : dossier temporaire effacé) et --json. Idempotent.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HF = "/opt/vokio-ads/bin/hf"
VERROU = "/tmp/hf-rendu.lock"

JS_POINT = r"""
global.window = global; global.self = global;
const fs = require("fs"), path = require("path"), R = process.argv[1];   // node -e : argv = [node, arg1, arg2]
require(path.join(R, "lib/vendor", fs.readdirSync(path.join(R, "lib/vendor")).find(f => /gsap/.test(f))));
require(path.join(R, "donnees/donnees.js")); require(path.join(R, "lib/point.js"));
const ts = JSON.parse(process.argv[2]);
console.log(JSON.stringify(ts.map(t => POINT.etat(t))));
"""


def ceil6(n, fps):
    return math.ceil(round(n / fps, 9) * 1e6) / 1e6


def lire_donnees(racine):
    t = (racine / "donnees" / "donnees.js").read_text()
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def masque_point(shape, etats, marge):
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    m = np.zeros((h, w), bool)
    for e in etats:
        if e["d"] <= 0:
            continue
        r = e["d"] * max(e.get("sx") or 1, e.get("sy") or 1) / 2 + marge
        m |= (xx - e["x"]) ** 2 + (yy - e["y"]) ** 2 <= r * r
    return m


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("racine")
    A.add_argument("--paires")
    A.add_argument("--autour")
    A.add_argument("--exiger", default="")
    A.add_argument("--seuil", type=int, default=2)
    A.add_argument("--marge", type=float, default=3.0)
    A.add_argument("--images")
    A.add_argument("--json")
    a = A.parse_args()
    racine = Path(a.racine).resolve()
    D = lire_donnees(racine)
    fps = D.get("fps", 30)
    ordre = sorted(D["scenes"], key=lambda s: D["scenes"][s]["debut"])
    if a.paires:
        paires = [tuple(p.split(":")) for p in a.paires.split(",")]
    elif a.autour:
        if a.autour not in ordre:
            raise SystemExit(f"scène inconnue : {a.autour}")
        i = ordre.index(a.autour)
        paires = [(ordre[j], ordre[j + 1]) for j in (i - 1, i) if 0 <= j < len(ordre) - 1]
    else:
        paires = list(zip(ordre, ordre[1:]))
    exiger = {tuple(p.split(":")) for p in a.exiger.split(",") if p}
    for p in set(paires) | exiger:
        for s in p:
            if s not in D["scenes"]:
                raise SystemExit(f"scène inconnue : {s}")
    paires = list(dict.fromkeys(paires + sorted(exiger - set(paires))))
    images = {}
    for pa, pb in paires:
        n = D["scenes"][pa]["image_fin"]
        if D["scenes"][pb]["image_debut"] != n:
            raise SystemExit(f"{pa} → {pb} : scènes non consécutives ({n} ≠ {D['scenes'][pb]['image_debut']})")
        images[(pa, pb)] = (n - 1, n)
    instants = sorted({ceil6(n, fps) for ab in images.values() for n in ab})
    r = subprocess.run(["node", "-e", JS_POINT, str(racine), json.dumps(instants)], capture_output=True, text=True, check=True)
    etats = dict(zip(instants, json.loads(r.stdout)))
    tmp = None
    if a.images:
        dossier = Path(a.images).resolve()
        if dossier.exists():
            shutil.rmtree(dossier)
        dossier.mkdir(parents=True)
    else:
        tmp = tempfile.mkdtemp(prefix="raccords-")
        dossier = Path(tmp)
    png = dossier / "png"
    subprocess.run(["flock", VERROU, HF, "snapshot", str(racine), "--no-end", "--at", ",".join(f"{t:.6f}" for t in instants),
                    "-o", str(png), "--describe", "false"], check=True, capture_output=True)
    dispo = {}
    for f in png.glob("*.png"):
        m = re.search(r"at-([0-9.]+)s", f.name)
        if m:
            dispo[float(m.group(1))] = f
    try:
        police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except OSError:
        police = ImageFont.load_default()
    rapport, code = [], 0
    for (pa, pb), (na, nb) in images.items():
        ta, tb = ceil6(na, fps), ceil6(nb, fps)
        ia = np.asarray(Image.open(dispo[min(dispo, key=lambda x: abs(x - ta))]).convert("RGB")).astype(np.int16)
        ib = np.asarray(Image.open(dispo[min(dispo, key=lambda x: abs(x - tb))]).convert("RGB")).astype(np.int16)
        m = masque_point(ia.shape, [etats[ta], etats[tb]], a.marge)
        ecart = np.abs(ia - ib).max(axis=2)
        ecart[m] = 0
        hors = ecart > a.seuil
        n_hors = int(hors.sum())
        boite = None
        if n_hors:
            ys, xs = np.nonzero(hors)
            boite = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        exige = (pa, pb) in exiger
        ok = not (exige and n_hors)
        code = code or (0 if ok else 1)
        vis = np.clip(ecart * 8, 0, 255).astype(np.uint8)
        vis_rgb = np.stack([vis] * 3, axis=2)
        vis_rgb[m] = (128, 128, 128)
        k = 480 / ia.shape[1]
        w, h = int(ia.shape[1] * k), int(ia.shape[0] * k)
        feuille = Image.new("RGB", (3 * w + 48, h + 48), (255, 255, 255))
        for i, im in enumerate([ia.astype(np.uint8), ib.astype(np.uint8), vis_rgb]):
            feuille.paste(Image.fromarray(im).resize((w, h), Image.LANCZOS), (12 + i * (w + 12), 36))
        ImageDraw.Draw(feuille).text((12, 8), f"{pa} image {na} | {pb} image {nb} | écarts × 8 (point effacé) : "
                                              f"max {int(ecart.max())}, {n_hors} px > {a.seuil}", fill=(38, 32, 25), font=police)
        sortie = dossier / f"raccord-{pa}-{pb}.png"
        feuille.save(sortie)
        ligne = {"paire": f"{pa}:{pb}", "images": [na, nb], "ecart_max": int(ecart.max()), "pixels_hors_seuil": n_hors,
                 "boite": boite, "exige": exige, "ok": ok, "planche": str(sortie) if a.images else None,
                 "point": [[round(etats[ta]["x"], 2), round(etats[ta]["y"], 2)], [round(etats[tb]["x"], 2), round(etats[tb]["y"], 2)]]}
        rapport.append(ligne)
        print(f"  {'ok   ' if ok else 'ÉCART'} {pa} {na} → {pb} {nb} : écart max {ligne['ecart_max']:3d}, "
              f"{n_hors:7d} px > {a.seuil}{'  boîte ' + str(boite) if boite else ''}{'  (exigé identique)' if exige else ''}")
    if a.json:
        Path(a.json).write_text(json.dumps({"racine": str(racine), "seuil": a.seuil, "marge": a.marge, "paires": rapport},
                                           ensure_ascii=False, indent=1))
        print(f"→ {a.json}")
    if tmp:
        shutil.rmtree(tmp)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
