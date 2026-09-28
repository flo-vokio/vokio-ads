#!/usr/bin/env python3
"""L'encre suit-elle la plume ? L'écriture de « Vokıo » (s7) mesurée image par image, dans n'importe quel format : usage :

    python3 outils/plume.py <racine> [--mp4 film.mp4] [--images D] [--json r.json] [--bord 40] [--tol 3] [--reprendre]

<racine> : un projet rendable (ce projet = le 9:16, formats/16x9, ou une copie de outils/format.py --dossier, variante
comprise). Tout vient de SES données (donnees/donnees.js, donnees/point-resolu.json) : plume_mot, ligne de base, boîte
de #mot (DONNEES.mesures.s7), x du stylo image par image (le maximum de x_sans atteint depuis le départ, la loi de
compositions/s7-signature.html). Aucun chiffre d'un format n'est écrit ici.

  1. images : hf snapshot (sous flock /tmp/hf-rendu.lock) de la dernière image avant la plume jusqu'à 3 images après son
     arrivée ; --mp4 : les mêmes images décodées d'un film déjà rendu (au codec près) ;
  2. dans la bande du mot (haut de #mot → ligne de base + 8, sous laquelle court le point), l'ENCRE de chaque colonne
     (couverture 0 → 1 du gris papier vers le gris encre ; pixels solaires exclus : le point n'est pas de l'encre),
     comparée au mot fini (arrivée + 3 images) :
       avant   dernière image avant la plume : rien d'écrit (encre < 1 % du mot fini) ;
       devant  aucune encre au-delà de la plume + --tol (le mot ne s'écrit pas avant le point : ≤ 2 % de celle du mot fini
               dans cette partie) ; c'est ce qui casse quand le masque n'est pas dans les coordonnées de #s7-fin ;
       derrière  tout est écrit avant [xp − --bord − --tol] (≥ 97 %) ;
       bord    la bande [xp − --bord ; xp] à moitié encrée (0,2 → 0,8 du mot fini), quand elle est tout entière dans
               l'encre du mot (DONNEES.geometrie.s7.segments, encre_x0 → encre_x1) : le bord doux de l'encre
               (arbitrage 7 de la finition), pas un volet franc ;
       arrivée  à la fin de plume_mot, le mot entier (≥ 99 %).
  3. planche : chaque image, la plume (trait solaire) et le bord d'encre attendu (trait gris) → <D>/plume.png ; le
     rapport JSON (--json, défaut <D>/plume.json) ; code 1 si une règle échoue.
--reprendre : relit les snapshots de <D>/png (mêmes instants) au lieu de les refaire (règle retouchée, images inchangées).
Idempotent ; n'écrit que dans --images (défaut <scratch>/plume-<nom de la racine>, vidé à chaque passe) et --json.
Exemple : plume.py formats/16x9 · plume.py /tmp/x/fC (variante s7-signature=16x9-C) · plume.py . --mp4 <film 9:16 livré>
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revue_scene as RS  # noqa: E402


def couverture(img, y0, y1):
    """Encre par colonne dans la bande [y0, y1) : Σ (papier − gris) / (papier − encre), pixels solaires exclus."""
    a = np.asarray(img)[y0:y1, :, :3].astype(np.float32)
    g = a @ np.array([0.299, 0.587, 0.114], np.float32)
    papier = float(np.median(g[:, :40]))                      # bord gauche de la bande : papier nu
    encre = 38.0                                              # #262019, l'encre de la DA
    c = ((papier - g) / max(1.0, papier - encre)).clip(0, 1)
    c[(a[:, :, 0] - a[:, :, 2]) > 40] = 0                     # le point solaire (et ses bords fondus) n'écrit pas
    return c.sum(axis=0)


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("racine")
    A.add_argument("--mp4")
    A.add_argument("--images")
    A.add_argument("--json")
    A.add_argument("--bord", type=float, default=40.0, help="largeur du bord d'encre (L_ENCRE de la scène, px)")
    A.add_argument("--tol", type=float, default=3.0)
    A.add_argument("--reprendre", action="store_true", help="réutiliser les snapshots de <D>/png d'une passe précédente")
    a = A.parse_args()
    R = Path(a.racine).resolve()
    D = RS.donnees(R)
    fps, EV, G7, M7 = D["fps"], D["evenements"], D["geometrie"]["s7"], D["mesures"]["s7"]
    RES = json.loads((R / "donnees" / "point-resolu.json").read_text())["images"]
    n0, n1 = EV["plume_mot"]["images"]
    ref = n1 + 3
    ks = list(range(n0 - 1, n1 + 1)) + [ref]
    dossier = Path(a.images).resolve() if a.images else Path(tempfile.gettempdir()) / f"plume-{R.name}"
    dossier.mkdir(parents=True, exist_ok=True)
    if a.mp4:
        brut = RS.images_mp4(a.mp4, set(ks))
        IM = {k: Image.fromarray(brut[k]) for k in ks}
    else:
        png = dossier / "png"
        vus = {}
        for f in png.glob("frame-*-at-*.png") if a.reprendre else []:
            m = re.match(r"frame-(\d+)-at-([0-9.]+)s\.png$", f.name)
            if m and int(m.group(1)) < len(ks) and abs(float(m.group(2)) - RS.temps(ks[int(m.group(1))], fps)) < 6e-4:
                vus[ks[int(m.group(1))]] = f
        S = vus if len(vus) == len(ks) else RS.snapshots(R, [(k, RS.temps(k, fps), "") for k in ks], png)
        IM = {k: Image.open(S[k]).convert("RGB") for k in ks}
    y0, y1 = int(M7["mot"]["y0"]), int(G7["ligne_de_base"]) + 8
    Pf = couverture(IM[ref], y0, y1)
    tot_f = float(Pf.sum())
    X = np.arange(Pf.size)
    SEG = G7["segments"].values()
    e0, e1 = min(s["encre_x0"] for s in SEG), max(s["encre_x1"] for s in SEG)   # encre du mot (mesurée par construire.py)

    def part(P, m):
        f = float(Pf[m].sum())
        return (float(P[m].sum()) / f) if f > 50 else None

    lignes, echecs = [], []
    for k in ks[:-1]:
        P = couverture(IM[k], y0, y1)
        l = {"image": k, "t": round(k / fps, 3)}
        if k < n0:
            l["avant"] = round(float(P.sum()) / tot_f, 4)
            if l["avant"] > 0.01:
                echecs.append(f"image {k} : {l['avant']:.1%} du mot déjà écrit avant la plume")
        elif k >= n1:
            l["arrivee"] = round(float(P.sum()) / tot_f, 4)
            if l["arrivee"] < 0.99:
                echecs.append(f"image {k} : le mot n'est écrit qu'à {l['arrivee']:.1%} à l'arrivée de la plume")
        else:
            xp = max(RES[j]["x_sans"] for j in range(n0, k + 1))
            l["xp"] = round(xp, 1)
            dedans = e0 <= xp - a.bord and xp <= e1            # le bord entier dans l'encre du mot (sinon il n'y a rien à fondre)
            dev, der, bord = (part(P, X > xp + a.tol), part(P, X < xp - a.bord - a.tol),
                              part(P, (X >= xp - a.bord) & (X <= xp)) if dedans else None)
            l.update({"devant": None if dev is None else round(dev, 3), "derriere": None if der is None else round(der, 3),
                      "bord": None if bord is None else round(bord, 3)})
            if dev is not None and dev > 0.02:
                echecs.append(f"image {k} : encre DEVANT la plume (x > {xp + a.tol:.0f}) : {dev:.1%} du mot fini")
            if der is not None and der < 0.97:
                echecs.append(f"image {k} : derrière la plume, {der:.1%} seulement de l'encre (x < {xp - a.bord - a.tol:.0f})")
            if bord is not None and not 0.2 <= bord <= 0.8:
                echecs.append(f"image {k} : bord d'encre {bord:.2f} (attendu 0,2 → 0,8, un dégradé et non un volet)")
        lignes.append(l)
    # planche : la bande du mot, la plume (solaire) et le bord d'encre attendu (gris)
    cases = []
    for l in lignes:
        im = IM[l["image"]].copy()
        dr = ImageDraw.Draw(im, "RGBA")
        if "xp" in l:
            dr.line([(l["xp"], y0 - 30), (l["xp"], y1 + 60)], fill=(239, 164, 36, 255), width=3)
            dr.line([(l["xp"] - a.bord, y0 - 30), (l["xp"] - a.bord, y1 + 60)], fill=(38, 32, 25, 140), width=2)
        x_a, x_b = max(0, int(M7["mot"]["x0"]) - 120), min(im.width, int(M7["mot"]["x1"]) + 120)
        im = im.crop((x_a, max(0, y0 - 40), x_b, min(im.height, y1 + 80)))
        titre = f"{l['image']} · " + " · ".join(f"{c} {l[c]}" for c in ("avant", "devant", "derriere", "bord", "arrivee")
                                                if l.get(c) is not None)
        cases.append((titre, [im]))
    RS.feuille(cases, dossier / "plume.png", largeur=520, cols=3)
    ok = not echecs
    rap = {"racine": str(R), "source": a.mp4 or "hf snapshot", "plume_mot": [n0, n1], "bande_y": [y0, y1],
           "reference": ref, "bord": a.bord, "tol": a.tol, "ok": ok, "echecs": echecs, "images": lignes,
           "planche": str(dossier / "plume.png")}
    (Path(a.json) if a.json else dossier / "plume.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1))
    for l in lignes:
        print("  " + " · ".join(f"{c} {v}" for c, v in l.items()))
    print(("ok  " if ok else "NON ") + f"l'encre suit la plume ({len(lignes)} images, {R.name}) → {dossier / 'plume.png'}")
    for e in echecs:
        print("   ✗ " + e)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
