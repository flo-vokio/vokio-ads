#!/usr/bin/env python3
"""Agenda v2 : recadre les deux vraies captures de app.vokio.fr (vue jour, 4,5 px par px CSS) sans
les rééchantillonner, et écrit la géométrie en px FILM.

    python3 outils/preparer_agenda.py     écrit assets/captures/agenda-avant.png, agenda-apres.png,
                                          bloc-florian.png et donnees/agenda-geo.json (v2)
    python3 outils/preparer_agenda.py --format 16x9 --sortie formats/16x9/donnees/agenda-geo.json --sans-images [--variante s=n | *=n]
                                          la géométrie d'un autre format (pose et mention : mise-en-page/agenda.json) ;
                                          les recadrages PNG sont communs à tous les formats (--sans-images : non réécrits)

Entrées (prises par la session principale le 27/09, aucune écriture en production) :
  assets/captures/agenda-avant-v2-brut.png   1575 × 2070 : « main .card-v » entière, dsf 4,5, viewport 390 px
  assets/captures/agenda-apres-v2-brut.png   la même carte avec le bloc « 09:00 Florian »
  assets/captures/agenda-avant-v2-geo.json   relevé DOM en px CSS (étiquettes, carte)
  assets/captures/agenda-apres-v2-geo.json   idem + boîte du bloc, boîte de « Florian », style du bloc
L'espace est celui de la démonstration fictive des Catalans, remis dans l'état EXACT du rendez-vous réel
de la Clinique vétérinaire du Port (samedi, 09:00-13:00, « 09:00 Florian », Consultation vétérinaire,
20 min) : l'en-tête de la capture dit « Samedi 26 Septembre », il est hors cadre.

Règles (plan v2, chantier « assets/captures ») :
  - échelle 4,5 px film par px CSS = échelle de la capture : AUCUN rééchantillonnage, 1 px capture = 1 px film ;
  - recadrage en x : la carte entière (bordure comprise), 1575 px ; posée en x = 70 (marge de 70 px), elle déborde du cadre
    à droite (le film la coupe à 1080) comme un objet plein cadre, au lieu d'une coupe nette ;
  - recadrage en y : de (filet 09:00 − 16 px CSS) à (filet 11:00 + 30 px CSS), arrondi au pixel ; posée
    en y = 590, d'où des filets à 661,75 / 895,75 / 1129,75 (nominal 662 / 896 / 1130) ;
  - en-tête, flèches, AUJOURD'HUI (seules capitales en mono de la capture), bascule JOUR/SEMAINE et texte
    d'aide sous 13:00 : hors cadre (contrôlé) ;
  - bloc-florian.png : même taille, même position que agenda-avant.png, transparent hors de la boîte du bloc,
    découpé dans la capture « après » ; contrôle : avant + calque = après, au pixel près.
Tous les relevés d'encre sont faits sur les pixels (les boîtes DOM sont gardées à côté, en « dom »).
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mise_en_page  # noqa: E402

PROJET = Path(__file__).resolve().parents[1]
CAP = PROJET / "assets" / "captures"
_A = argparse.ArgumentParser()
_A.add_argument("--format", default="9x16")
_A.add_argument("--sortie", default=None, help="chemin de agenda-geo.json (défaut : donnees/agenda-geo.json de ce projet)")
_A.add_argument("--sans-images", action="store_true", help="ne réécrit pas les recadrages PNG (communs aux formats)")
_A.add_argument("--variante", action="append", default=[], help="<scène>=<nom> (ou *=<nom>, un jeu) : la même que construire.py")
ARGS = _A.parse_args(sys.argv[1:] if __name__ == "__main__" else [])
MEP = mise_en_page.charger(ARGS.format, dict(v.split("=", 1) for v in ARGS.variante))
ECH = 4.5                        # px capture = px film par px CSS
# 9:16 : (70 ; 590) : coin haut gauche de l'image dans le film (entiers : 1 px image = 1 px écran) ;
# x = 70 (finition 27/09) : la carte respecte la marge latérale de 70 px (règle 5), 62 la débordait de 8 px.
# FORMATS : la pose vient de mise-en-page/agenda.json, la largeur visible = celle du cadre.
POSE_X, POSE_Y = MEP["agenda"]["x"], MEP["agenda"]["y"]
DROITE_VISIBLE = MEP["format"]["largeur"]
LARGEUR_CADRE, HAUTEUR_CADRE = MEP["format"]["largeur"], MEP["format"]["hauteur"]
MENTION_GEO = MEP["agenda"]["mention"]
# RECOMPOSITION (28/09) : le point du film suit le wordmark du format (mise_en_page.echelle_point) ; 9:16 : valeurs telles quelles
K_POINT = mise_en_page.echelle_point(MEP)
KP = (lambda v: v) if K_POINT == 1 else (lambda v: v * K_POINT)
STYLE_MENTION = MEP["texte"]["styles"]["mention"]      # la mention de l'agenda a le style de la mention de s3
PAPIER_CARTE = np.array([244, 241, 232])   # fond de la carte (rgb), relevé
ENCRE_ETIQ = np.array([108, 103, 95])      # text-faint des étiquettes, relevé
FOND_BLOC = np.array([240, 222, 188])      # fond du bloc (rgba(239,164,36,.2) sur la colonne), relevé
ENCRE_BLOC = np.array([38, 32, 25])        # « Florian » (text-noir), relevé
HEURES = ["09:00", "10:00", "11:00", "12:00", "13:00"]
MENTION = ["Capture réelle de app.vokio.fr", "Établissement fictif de démonstration."]


def charger(nom):
    return np.asarray(Image.open(CAP / nom).convert("RGB")).astype(np.int16)


def filets(img, x):
    """Filets d'heure (1 px CSS = 4,5 px) : bords continus d'après la couverture des rangées d'antialiasing."""
    col = img[:, x].astype(float).sum(axis=1)
    fond = float(img[int(1100), x].astype(float).sum())      # colonne entre 10:00 et 11:00 (vide)
    trait = col.min()
    sortie = []
    y = 600
    while y < 1700:
        if col[y] < fond - 6:
            y1 = y
            while col[y1 + 1] < fond - 6:
                y1 += 1
            plein = min(col[y:y1 + 1])
            # couverture des rangées de bord, rapportée au fond VOISIN (papier de la carte au-dessus du
            # filet 09:00, colonne ailleurs) : la rangée y est couverte en partie par le bas, y1 par le haut
            cov = lambda k, ref: max(0.0, min(1.0, (col[ref] - col[k]) / (col[ref] - plein)))
            haut = y + (1 - cov(y, y - 1))
            bas = y1 + cov(y1, y1 + 1)
            if y1 - y >= 3:
                sortie.append({"haut": round(haut, 2), "bas": round(bas, 2), "centre": round((haut + bas) / 2, 2),
                               "epaisseur": round(bas - haut, 2)})
            y = y1 + 1
        y += 1
    return sortie, trait


def couverture(zone, fond, encre):
    return np.clip((fond.sum() - zone.astype(float).sum(axis=2)) / float(fond.sum() - encre.sum()), 0, 1)


def boite_encre(cov, seuil=0.06):
    """Boîte d'encre sous-pixel : [x0, y0, x1, y1] (x1, y1 exclusifs, fraction de couverture comprise)."""
    cm, rm = cov.max(axis=0), cov.max(axis=1)
    c, r = np.nonzero(cm > seuil)[0], np.nonzero(rm > seuil)[0]
    return [c.min() + 1 - cm[c.min()], r.min() + 1 - rm[r.min()], c.max() + cm[c.max()], r.max() + rm[r.max()]]


def main():
    av, ap = charger("agenda-avant-v2-brut.png"), charger("agenda-apres-v2-brut.png")
    geo_av = json.loads((CAP / "agenda-avant-v2-geo.json").read_text())
    geo_ap = json.loads((CAP / "agenda-apres-v2-geo.json").read_text())
    assert av.shape == ap.shape == (2070, 1575, 3), av.shape
    assert geo_ap["echelle"] == geo_av["echelle"] == ECH

    # 1. différence avant / après : limitée à la boîte du bloc
    d = np.abs(av - ap).sum(axis=2) > 0
    ys, xs = np.nonzero(d)
    diff = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    b_dom = geo_ap["bloc"]
    b_cap = [b_dom["x0"] * ECH, b_dom["y0"] * ECH, b_dom["x1"] * ECH, b_dom["y1"] * ECH]
    assert b_cap[0] - 2 <= diff[0] and diff[2] <= b_cap[2] + 2 and b_cap[1] - 2 <= diff[1] and diff[3] <= b_cap[3] + 2, \
        f"la différence avant/après {diff} déborde de la boîte DOM du bloc {b_cap}"
    print(f"différence avant/après : {diff} ({int(d.sum())} px), boîte DOM du bloc {b_cap}")

    # 2. filets (dans la colonne, x = 1000 px capture) et bord gauche de la colonne
    F, _ = filets(av, 1000)
    assert len(F) == 5, F
    pas = [round(b["centre"] - a["centre"], 2) for a, b in zip(F, F[1:])]
    assert all(abs(p - 52 * ECH) < 0.6 for p in pas), pas               # 52 px CSS par heure
    ligne = av[1100].astype(float).sum(axis=1)
    fond_carte, fond_col = float(PAPIER_CARTE.sum()), float(av[1100, 1000].astype(float).sum())
    x = next(k for k in range(150, 600) if ligne[k] < fond_carte - 1)
    col_x_cap = x + (ligne[x] - fond_col) / (fond_carte - fond_col)      # bord continu
    col_x_cap = round(float(col_x_cap), 2)
    # bords de la carte (bordure 1 px CSS)
    carte_x0_cap, carte_x1_cap = 0.0, 1575.0

    # 3. recadrage en y (entiers) : filet 09:00 − 16 px CSS → filet 11:00 + 30 px CSS
    Y0 = int(round(F[0]["centre"] - 16 * ECH))
    Y1 = int(round(F[2]["centre"] + 30 * ECH))
    X0, X1 = 0, 1575
    W, H = X1 - X0, Y1 - Y0

    # contrôles de cadre : l'en-tête et la bascule sont au-dessus, le texte d'aide en dessous
    fond_haut = np.abs(av[:, 300:1500].astype(int) - PAPIER_CARTE).sum(axis=2) > 6
    au_dessus = [k for k in range(0, int(F[0]["haut"]) - 1) if fond_haut[k].any()]
    bas_chrome = max(k for k in au_dessus if k < int(F[0]["haut"]) - 60)   # dernier rang de la bascule
    assert bas_chrome < Y0, f"la bascule JOUR/SEMAINE (bas {bas_chrome}) entre dans le cadre (Y0 {Y0})"
    aide = min(k for k in range(int(F[4]["bas"]) + 2, 2070) if (np.abs(av[k, 60:1500].astype(int) - PAPIER_CARTE).sum(axis=1) > 60).any())
    assert Y1 < F[3]["haut"] and Y1 < aide, (Y1, F[3], aide)
    # étiquette 12:00 hors cadre
    etq12_y0 = geo_av["etiquettes"]["12:00"]["y0"] * ECH
    assert Y1 <= etq12_y0, (Y1, etq12_y0)

    def fx(xc):
        return round(POSE_X + (xc - X0), 2)

    def fy(yc):
        return round(POSE_Y + (yc - Y0), 2)

    for src, dst, arr in (("agenda-avant-v2-brut.png", "agenda-avant.png", av), ("agenda-apres-v2-brut.png", "agenda-apres.png", ap)):
        if not ARGS.sans_images:
            Image.open(CAP / src).convert("RGB").crop((X0, Y0, X1, Y1)).save(CAP / dst, optimize=True)
    a2 = np.asarray(Image.open(CAP / "agenda-avant.png")).astype(np.int16)
    p2 = np.asarray(Image.open(CAP / "agenda-apres.png")).astype(np.int16)
    assert a2.shape == (H, W, 3)
    d2 = np.abs(a2 - p2).sum(axis=2) > 0
    ys2, xs2 = np.nonzero(d2)
    bx0, by0, bx1, by1 = max(0, int(xs2.min()) - 2), max(0, int(ys2.min()) - 2), min(W, int(xs2.max()) + 3), min(H, int(ys2.max()) + 3)
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[by0:by1, bx0:bx1, :3] = p2[by0:by1, bx0:bx1]
    rgba[by0:by1, bx0:bx1, 3] = 255
    if not ARGS.sans_images:
        Image.fromarray(rgba, "RGBA").save(CAP / "bloc-florian.png", optimize=True)
    else:
        assert (np.asarray(Image.open(CAP / "bloc-florian.png")) == rgba).all(), "bloc-florian.png n'est plus à jour (relancer sans --sans-images)"
    comp = a2.copy()
    comp[by0:by1, bx0:bx1] = p2[by0:by1, bx0:bx1]
    assert (comp == p2).all(), "le calque ne reconstitue pas l'après"
    hors = d2.copy()
    hors[by0:by1, bx0:bx1] = False
    assert not hors.any(), "différence avant/après hors de la boîte du calque"
    print(f"agenda-avant.png / agenda-apres.png {W}×{H} (recadrage capture x {X0}→{X1}, y {Y0}→{Y1}) ; "
          f"calque bloc {bx0},{by0} → {bx1},{by1} (px image)")

    # 4. étiquettes : boîtes d'encre (pixels) et boîtes DOM
    etiq = {}
    for h, f in zip(HEURES, F):
        y0z = int(f["centre"]) - 45
        z = av[y0z:y0z + 90, 5:270]
        b = boite_encre(couverture(z, PAPIER_CARTE, ENCRE_ETIQ))
        e = {"x0": b[0] + 5, "y0": b[1] + y0z, "x1": b[2] + 5, "y1": b[3] + y0z}
        dom = geo_av["etiquettes"][h]
        etiq[h] = {"encre": {"x0": fx(e["x0"]), "y0": fy(e["y0"]), "x1": fx(e["x1"]), "y1": fy(e["y1"])},
                   "dom": {"x0": fx(dom["x0"] * ECH), "y0": fy(dom["y0"] * ECH), "x1": fx(dom["x1"] * ECH), "y1": fy(dom["y1"] * ECH)},
                   "visible": Y0 <= e["y0"] and e["y1"] <= Y1}
    visibles = [h for h in HEURES if etiq[h]["visible"]]
    assert visibles == ["09:00", "10:00", "11:00"], visibles
    encre_droite = max(etiq[h]["encre"]["x1"] for h in visibles)
    col_x = fx(col_x_cap)
    x_point = round((encre_droite + col_x) / 2, 2)

    # 5. le bloc et « Florian » (encre relevée sur les pixels de l'après)
    zb = ap[int(b_cap[1]) + 10:int(b_cap[3]) - 4, int(b_cap[0]) + 200:int(b_cap[0]) + 700]
    cb = couverture(zb, FOND_BLOC, ENCRE_BLOC)
    cb[cb < 0.55] = 0          # seul le noir de « Florian » ; « 09:00 » est à 70 % d'opacité (gris)
    fb = boite_encre(cb, seuil=0.5)
    ox, oy = int(b_cap[0]) + 200, int(b_cap[1]) + 10
    florian = {"x0": fx(fb[0] + ox), "y0": fy(fb[1] + oy), "x1": fx(fb[2] + ox), "y1": fy(fb[3] + oy)}
    fl_dom = geo_ap["florian"]
    assert abs((fb[2] + ox) - fl_dom["x1"] * ECH) < 8, (fb[2] + ox, fl_dom)   # encre ≈ avance DOM − approche
    # 5 bis (28/09, l'échange du prénom) : l'encre de « 09:00 » (70 % d'opacité : couverture ≈ 0,7, la bordure du bloc ≈ 0,2)
    # et les colonnes d'encre de chaque lettre de « Florian » : le point écrit l'heure, s'arrête dans le blanc qui les sépare
    # (plume levée pendant la question), puis écrit le nom sous sa voix (construire.py, choregraphie_s5)
    ohx = int(b_cap[0]) + 20
    ch = couverture(ap[int(b_cap[1]) + 10:int(b_cap[3]) - 4, ohx:int(fb[0] + ox) - 2], FOND_BLOC, ENCRE_BLOC)
    ch[ch < 0.35] = 0
    hb = boite_encre(ch, seuil=0.35)
    heure = {"x0": fx(hb[0] + ohx), "y0": fy(hb[1] + oy), "x1": fx(hb[2] + ohx), "y1": fy(hb[3] + oy)}
    cmf = cb.max(axis=0)
    cols = np.nonzero(cmf > 0.5)[0]
    runs = [[cols[0], cols[0]]]
    for c in cols[1:]:
        if c == runs[-1][1] + 1:
            runs[-1][1] = c
        else:
            runs.append([c, c])
    assert len(runs) == len("Florian"), f"« Florian » : {len(runs)} colonnes d'encre au lieu de 7 ({runs})"
    lettres = [{"lettre": l, "x0": fx(a + 1 - cmf[a] + ox), "x1": fx(b + cmf[b] + ox)} for l, (a, b) in zip("Florian", runs)]
    assert heure["x1"] < florian["x0"] - 10 and abs(lettres[0]["x0"] - florian["x0"]) < 1 and abs(lettres[-1]["x1"] - florian["x1"]) < 1, \
        (heure, florian, lettres)
    bloc = {
        "option": "A (découpé dans la vraie capture, calque raster)",
        "fichier": "assets/captures/bloc-florian.png",
        "calque": "même taille et même position que agenda-avant.png ; opaque seulement dans boite_px_image",
        "boite_px_image": [bx0, by0, bx1, by1],
        "x0": fx(b_cap[0]), "y0": fy(b_cap[1]), "x1_reel": fx(b_cap[2]), "y1": fy(b_cap[3]),
        "x1_visible": DROITE_VISIBLE, "hauteur": round(b_cap[3] - b_cap[1], 2),
        "centre_y": round((fy(b_cap[1]) + fy(b_cap[3])) / 2, 2),
        "texte": "09:00 Florian", "texte_x1": florian["x1"],
        "x_fin": round(florian["x1"] + KP(14) + KP(22), 2),     # 14 px après l'encre + le rayon (× échelle du point du format)
        "florian_encre": florian,
        "heure_encre": heure,
        "florian_lettres": lettres,
        "florian_dom": {k: fx(fl_dom[k] * ECH) if k[0] == "x" else fy(fl_dom[k] * ECH) for k in ("x0", "y0", "x1", "y1")},
        "style": dict(geo_ap["bloc_style"], corps_px_css=11, corps_px_film=49.5,
                      note="rgba(239,164,36,.2) sur la colonne, bordure 1 px CSS = 4,5 px film ; « 09:00 » à 70 % d'opacité, « Florian » encre text-noir"),
        "rdv": "Consultation vétérinaire, samedi 09:00, 20 min, « 09:00 Florian » : l'état exact du vrai rendez-vous de la Clinique vétérinaire du Port (samedi 19/09/2026, créé le 18/09 à 16:53:29), reproduit dans l'espace fictif des Catalans",
    }

    F_film = [{"heure": h, "haut": fy(f["haut"]), "bas": fy(f["bas"]), "centre": fy(f["centre"]), "epaisseur": f["epaisseur"],
               "visible": Y0 <= f["haut"] and f["bas"] <= Y1} for h, f in zip(HEURES, F)]
    date_prise = datetime.fromtimestamp(os.path.getmtime(CAP / "agenda-apres-v2-brut.png")).isoformat(timespec="seconds")
    geo = {
        "version": 2,
        "unite": f"px FILM ({LARGEUR_CADRE}×{HAUTEUR_CADRE}) ; 1 px capture = 1 px film (aucun rééchantillonnage) ; y des filets = centre du filet de 4,5 px",
        "echelle": ECH, "echelle_px_film_par_px_css": ECH,
        "source": {"avant": "assets/captures/agenda-avant-v2-brut.png", "apres": "assets/captures/agenda-apres-v2-brut.png",
                   "releves_dom": ["assets/captures/agenda-avant-v2-geo.json", "assets/captures/agenda-apres-v2-geo.json"],
                   "echelle_capture": ECH, "recadrage_px_capture": [X0, Y0, X1, Y1],
                   "carte_px_css": geo_av["carte"]},
        "image": {"fichier": "assets/captures/agenda-avant.png", "apres": "assets/captures/agenda-apres.png",
                  "x": POSE_X, "y": POSE_Y, "largeur": W, "hauteur": H, "droite": POSE_X + W, "bas": POSE_Y + H,
                  "droite_visible": DROITE_VISIBLE,
                  "css": f"position:absolute; left:{POSE_X}px; top:{POSE_Y}px; width:{W}px; height:{H}px (1:1, jamais redimensionnée ; déborde à droite, le cadre la coupe à {DROITE_VISIBLE} : data-layout-allow-overflow)"},
        "carte": {"x0": fx(carte_x0_cap), "x1": fx(carte_x1_cap), "bordure_px": ECH,
                  "note": f"bord gauche de la carte (bordure 1 px CSS comprise) en x = {POSE_X}" + (" (marge latérale de 70 px)" if POSE_X == 70 else "")
                          + " ; bord droit hors cadre"},
        "heures": {f["heure"]: f["centre"] for f in F_film},
        "filets": F_film,
        "pas_heure": round(F[1]["centre"] - F[0]["centre"], 2),
        "etiquettes": {h: dict(etiq[h]["encre"], dom=etiq[h]["dom"], visible=etiq[h]["visible"]) for h in HEURES},
        "etiquettes_police": {"famille": "mono de l'app (font-mono)", "corps_px_css": 10, "corps_px_film": 10 * ECH,
                              "couleur": "#6C675F (text-faint)", "hauteur_encre_chiffres": round(etiq["09:00"]["encre"]["y1"] - etiq["09:00"]["encre"]["y0"], 2),
                              "capitales": 0},
        "colonne_x": col_x,
        "x_point": x_point,
        "x_point_calcul": f"(bord droit d'encre des étiquettes {encre_droite} + colonne_x {col_x}) / 2",
        "bloc": bloc,
        "mention": {"lignes": MENTION, "x": MENTION_GEO["x"], "lignes_de_base": list(MENTION_GEO["lignes_de_base"]),
                    "police": f"Geist 400, {STYLE_MENTION['corps']} px, interlignage {STYLE_MENTION['interligne']} px, #6F695F",
                    "note": ("accrochée sous l'image" if MENTION_GEO["lignes_de_base"][0] > POSE_Y else "accrochée au-dessus de l'image")
                            + f" (data-element=\"agenda\"), solidaire ; bas de boîte < {MEP['format']['bas_utile']}"},
        "preuve": {"en_tete_dom": "Samedi 26 Septembre",
                   "note_en_tete": "en-tête de l'espace fictif des Catalans au moment de la prise, hors cadre ; l'espace a été remis dans l'état exact du rendez-vous du Port",
                   "etablissement_capture": "espace fictif de démonstration des Catalans (vétérinaire), app.vokio.fr",
                   "etablissement_appel": "Clinique vétérinaire du Port (établissement fictif de démonstration)",
                   "etat_reproduit": "samedi, plage 09:00-13:00, bloc « 09:00 Florian », Consultation vétérinaire, 20 min",
                   "date_de_prise": date_prise, "dsf": ECH, "viewport_css": [390, None],
                   "ecriture_production": "aucune"},
        "controles": {"echelle_sans_reechantillonnage": True, "avant_plus_calque_egal_apres": True,
                      "difference_hors_bloc_px": 0, "chrome_hors_cadre": {"bas_bascule_px_capture": int(bas_chrome), "Y0": Y0,
                                                                            "haut_texte_aide_px_capture": int(aide), "Y1": Y1},
                      "etiquettes_visibles": visibles, "corps_etiquettes_px": 10 * ECH},
    }
    sortie = Path(ARGS.sortie) if ARGS.sortie else PROJET / "donnees" / "agenda-geo.json"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    assert MENTION_GEO["lignes_de_base"][1] - MENTION_GEO["lignes_de_base"][0] == STYLE_MENTION["interligne"], \
        "agenda.json : l'écart des deux lignes de la mention ≠ interligne du style mention (texte.json)"
    def natif(o):   # numpy → types JSON
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return round(float(o), 3)
        raise TypeError(type(o))
    sortie.write_text(json.dumps(geo, ensure_ascii=False, indent=1, default=natif))
    print(f"→ {sortie}")
    print(json.dumps({k: geo[k] for k in ("heures", "pas_heure", "colonne_x", "x_point")}, ensure_ascii=False))
    print("bloc :", {k: bloc[k] for k in ("x0", "y0", "y1", "centre_y", "hauteur", "texte_x1", "x_fin")})
    print("étiquette 09:00 (encre) :", etiq["09:00"]["encre"])
    print("filets :", [(f["heure"], f["centre"], f["visible"]) for f in F_film])


if __name__ == "__main__":
    main()
