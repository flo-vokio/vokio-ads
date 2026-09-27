#!/usr/bin/env python3
"""Recadre les deux vraies captures de l'agenda (app.vokio.fr, colonne jour, ×3) à l'échelle du film.

    python3 outils/preparer_agenda.py        écrit assets/captures/agenda-avant.png, agenda-apres.png,
                                             bloc-florian.png et donnees/agenda-geo.json

Échelle (bible) : 3,6 px film par px CSS, constante, aucun zoom dans le film. Les captures sont à ×3 :
on les agrandit UNE fois de ×1,2 (Lanczos) ici, et le film les affiche pixel pour pixel.
Recadrage (px de la capture ×3) : x 24 → 804 (CSS 8 → 268 : étiquettes d'heure + début de colonne ;
la colonne est coupée à droite comme dans la bible), y 455 → 1135 (10 px CSS au-dessus du filet de
09:00, 8 px CSS sous le filet de 13:00). L'en-tête (« Samedi 26 Septembre », flèches), la bascule
JOUR/SEMAINE et la légende du bas sont hors cadre.
bloc-florian.png : même taille que agenda-avant.png, transparent partout sauf la boîte du bloc
« 09:00 Florian » (seule zone où avant et après diffèrent, contrôlé) : posé exactement sur l'agenda,
il se déroule par clip-path.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

PROJET = Path(__file__).resolve().parents[1]
CAP = PROJET / "assets" / "captures"
ECH_CAPTURE = 3.0          # px capture par px CSS
ECH_FILM = 3.6             # px film par px CSS (bible)
K = ECH_FILM / ECH_CAPTURE  # 1,2
X0, X1 = 24, 804           # px capture (largeur 780 → 936 px film : x 70 → 1006, marge droite 74 px)
Y0, Y1 = 455, 1135         # px capture (hauteur 680 → 816 px film)
POSE_X, POSE_Y = 70, 580   # coin haut gauche de l'image dans le film (px entiers : 1 px image = 1 px écran)


def charger(nom):
    return np.asarray(Image.open(CAP / nom).convert("RGB")).astype(np.int16)


def main():
    av, ap = charger("agenda-avant-brut.png"), charger("agenda-apres-brut.png")
    assert av.shape == ap.shape == (1380, 1050, 3), av.shape
    d = np.abs(av - ap).sum(axis=2) > 0
    ys, xs = np.nonzero(d)
    boite_cap = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)   # x0, y0, x1, y1 exclusifs
    print("différence avant/après limitée à", boite_cap, f"({d.sum()} px)")

    # filets d'heure : lignes de 3 px (1 px CSS) de couleur (230,224,209) dans la colonne, relevées en x = 600
    col = av[:, 600]
    filets = []
    y = 400
    while y < 1130:
        if abs(col[y] - col[y - 1]).sum() > 4 and col[y].sum() < col[y - 1].sum():
            y2 = y
            while abs(col[y2 + 1] - col[y]).sum() <= 4:
                y2 += 1
            filets.append((y + y2 + 1) / 2)   # centre continu (bord haut y, bord bas y2+1)
            y = y2 + 1
        y += 1
    assert len(filets) == 5, filets
    heures = ["09:00", "10:00", "11:00", "12:00", "13:00"]

    # étiquettes d'heure : encre (gris de l'app) à gauche de la colonne
    enc = (av[:, :170].sum(axis=2) < 520)
    lx = np.nonzero(enc.any(axis=0))[0]
    etiquettes = []
    for h, yf in zip(heures, filets):
        bande = enc[int(yf) - 20:int(yf) + 20]
        yy = np.nonzero(bande.any(axis=1))[0] + int(yf) - 20
        xx = np.nonzero(bande.any(axis=0))[0]
        etiquettes.append((h, int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1))
    # bord gauche de la colonne : premier x où la couleur de colonne commence (y au milieu de 10:00-11:00)
    ligne = av[720]
    col_x = next(x for x in range(150, 400) if tuple(ligne[x]) == (243, 236, 222))

    def fx(xc):  # px capture → px film
        return round(POSE_X + (xc - X0) * K, 2)

    def fy(yc):
        return round(POSE_Y + (yc - Y0) * K, 2)

    W, H = round((X1 - X0) * K), round((Y1 - Y0) * K)
    for nom_src, nom_dst in (("agenda-avant-brut.png", "agenda-avant.png"), ("agenda-apres-brut.png", "agenda-apres.png")):
        im = Image.open(CAP / nom_src).convert("RGB").crop((X0, Y0, X1, Y1)).resize((W, H), Image.LANCZOS)
        im.save(CAP / nom_dst, optimize=True)
    a2 = np.asarray(Image.open(CAP / "agenda-avant.png")).astype(np.int16)
    p2 = np.asarray(Image.open(CAP / "agenda-apres.png")).astype(np.int16)
    d2 = np.abs(a2 - p2).sum(axis=2) > 0
    ys2, xs2 = np.nonzero(d2)
    bx0, by0, bx1, by1 = int(xs2.min()) - 2, int(ys2.min()) - 2, int(xs2.max()) + 3, int(ys2.max()) + 3
    bx0, by0, bx1, by1 = max(0, bx0), max(0, by0), min(W, bx1), min(H, by1)
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[by0:by1, bx0:bx1, :3] = p2[by0:by1, bx0:bx1]
    rgba[by0:by1, bx0:bx1, 3] = 255
    Image.fromarray(rgba, "RGBA").save(CAP / "bloc-florian.png", optimize=True)
    # contrôle : avant + calque = après, au pixel près
    comp = a2.copy()
    comp[by0:by1, bx0:bx1] = p2[by0:by1, bx0:bx1]
    assert (comp == p2).all(), "le calque ne reconstitue pas l'après"
    print(f"agenda-avant.png / agenda-apres.png {W}×{H} ; calque bloc {bx0},{by0} → {bx1},{by1} (px image)")

    geo = {
        "unite": "px FILM (1080×1920), sauf mention ; y des filets = centre du filet de 3,6 px",
        "echelle_px_film_par_px_css": ECH_FILM,
        "source": {"avant": "assets/captures/agenda-avant-brut.png", "apres": "assets/captures/agenda-apres-brut.png",
                   "echelle_capture": ECH_CAPTURE, "recadrage_px_capture": [X0, Y0, X1, Y1],
                   "origine": "capture réelle de app.vokio.fr, vue jour (établissement fictif des Catalans, état du vrai samedi de la clinique du Port reproduit)"},
        "image": {"fichier": "assets/captures/agenda-avant.png", "apres": "assets/captures/agenda-apres.png",
                  "x": POSE_X, "y": POSE_Y, "largeur": W, "hauteur": H,
                  "droite": POSE_X + W, "bas": POSE_Y + H,
                  "css": f"position:absolute; left:{POSE_X}px; top:{POSE_Y}px; width:{W}px; height:{H}px (image affichée à 1:1, jamais redimensionnée)"},
        "heures": {h: fy(yf) for h, yf in zip(heures, filets)},
        "pas_heure": round((filets[1] - filets[0]) * K, 2),
        "etiquettes": {h: {"x0": fx(x0), "y0": fy(y0), "x1": fx(x1), "y1": fy(y1)} for h, x0, y0, x1, y1 in etiquettes},
        "colonne_x": fx(col_x),
        "x_point": round((fx(max(e[3] for e in etiquettes)) + fx(col_x)) / 2, 1),
        "bloc": {
            "fichier": "assets/captures/bloc-florian.png",
            "calque": "même taille et même position que l'image de l'agenda ; opaque seulement dans la boîte",
            "boite_px_image": [bx0, by0, bx1, by1],
            "x0": fx(boite_cap[0]), "y0": fy(boite_cap[1]), "x1_visible": POSE_X + W, "y1": fy(boite_cap[3]),
            "x1_reel_hors_cadre": fx(boite_cap[2]),
            "centre_y": round((fy(boite_cap[1]) + fy(boite_cap[3])) / 2, 2),
            "hauteur": round(fy(boite_cap[3]) - fy(boite_cap[1]), 2),
            "texte": "09:00 Florian",
            "rdv": "Consultation vétérinaire, samedi 19/09/2026 09:00, 20 min, créé le 18/09 à 16:53 (vrai rendez-vous de l'appel)",
        },
        "mention": {"lignes": ["Capture réelle de app.vokio.fr", "Établissement fictif de démonstration."],
                    "x": 90, "lignes_de_base": [1436, 1484], "police": "Geist 400, 36 px, #6F695F",
                    "note": "accrochée sous l'image (data-element=\"agenda\"), bas de boîte < 1500"},
    }
    (PROJET / "donnees").mkdir(exist_ok=True)
    (PROJET / "donnees" / "agenda-geo.json").write_text(json.dumps(geo, ensure_ascii=False, indent=1))
    print(json.dumps({k: geo[k] for k in ("heures", "pas_heure", "colonne_x", "x_point")}, ensure_ascii=False))
    print("bloc :", geo["bloc"]["x0"], geo["bloc"]["y0"], "→", geo["bloc"]["y1"], "centre", geo["bloc"]["centre_y"])
    print("étiquettes :", geo["etiquettes"]["09:00"], "hauteur encre", round(geo["etiquettes"]["09:00"]["y1"] - geo["etiquettes"]["09:00"]["y0"], 1))


if __name__ == "__main__":
    main()
