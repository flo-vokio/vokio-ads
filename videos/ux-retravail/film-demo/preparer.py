#!/usr/bin/env python3
"""Prépare un métier pour la composition film-demo.

    preparer.py <metier>       (plombier, veterinaire, restaurant, institut_beaute)
    preparer.py --tous

1. Recopie les plans d'interface qui ont servi au film d'origine
   (/root/vokio-uploads/videos/ux-210926/film-<metier>/plans/, captures réelles
   de app.vokio.fr) dans assets/<metier>/. Les originaux ne sont pas touchés.
2. Retire les numéros de téléphone (règle du brief, précédent de
   monter_appel_reel.py) : le bloc « Rappeler » de l'appel déplié est coupé,
   la ligne-titre « 06 39 98 … » de l'appel sans nom est retirée et les deux
   lignes restantes recentrées. Rien n'est ajouté à l'image.
3. Écrit profils/<metier>.json : les textes du film, mot pour mot, lus dans
   profils.py (la source unique), plus les hauteurs des plans à l'écran.
"""
import json
import os
import shutil
import sys

from PIL import Image

sys.path.insert(0, "/opt/vokio-site-repo/design/videos/ux-vertical")
from profils import PROFILS  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
SOURCE = "/root/vokio-uploads/videos/ux-210926/film-{}/plans"
LARGEUR = 900            # largeur d'un plan à l'écran, comme l'original
PLANS = ["appel-1", "appel-2", "appel-3", "appel-1-ouvert",
         "agenda-jour", "impact-rdv", "impact-nuit"]


def orange_fonce(p):
    r, g, b = p[:3]
    return r > 130 and g < 95 and b < 45


def couper_rappeler(im):
    """Coupe la bande « RAPPELER 06 … » de la carte dépliée."""
    W, H = im.size
    px = im.load()
    lignes = [y for y in range(H)
              if sum(orange_fonce(px[x, y]) for x in range(300, min(W, 1000), 2)) > 6]
    if not lignes:
        raise SystemExit("bloc Rappeler introuvable")
    a, b = min(lignes), max(lignes)
    y0, y1 = a - 30, b + 30
    haut, bas = im.crop((0, 0, W, y0)), im.crop((0, y1, W, H))
    out = Image.new("RGB", (W, haut.height + bas.height))
    out.paste(haut, (0, 0))
    out.paste(bas, (0, haut.height))
    return out, (a, b)


def retirer_numero(im):
    """Retire la ligne-titre (le numéro) d'une rangée d'appel sans nom."""
    W, H = im.size
    px = im.load()
    x0, x1 = 440, 920
    sombre = lambda p: p[0] < 90 and p[1] < 90 and p[2] < 90   # noqa: E731
    rangs = [y for y in range(H) if any(sombre(px[x, y]) for x in range(x0, x1, 2))]
    # le titre : premier bloc de rangées sombres
    t0 = rangs[0]
    t1 = t0
    while t1 + 1 in rangs or t1 + 2 in rangs:
        t1 += 1
    reste = [y for y in range(t1 + 4, H) if any(
        (px[x, y][0] < 170) for x in range(x0, x1, 2))]
    r0, r1 = reste[0] - 4, reste[-1] + 4
    fond = px[x0 + 4, 12]
    bloc = im.crop((x0, r0, x1, r1))
    out = im.copy()
    out.paste(fond, (x0, 18, x1, H - 6))
    haut_total = r1 - r0
    y = (H - haut_total) // 2
    out.paste(bloc, (x0, y))
    return out, (t0, t1)


def preparer(metier):
    src = SOURCE.format(metier)
    dest = os.path.join(ICI, "assets", metier)
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    hauteurs = {}
    for nom in PLANS:
        im = Image.open(f"{src}/{nom}.png").convert("RGB")
        if nom == "appel-1-ouvert":
            im, bande = couper_rappeler(im)
            print(f"  {metier}: Rappeler coupé, rangées {bande}")
        if nom == "appel-3":
            im, bande = retirer_numero(im)
            print(f"  {metier}: numéro retiré, rangées {bande}")
        im.save(f"{dest}/{nom}.png", optimize=True)
        hauteurs[nom] = round(im.height * LARGEUR / im.width)
    f = PROFILS[metier]["film"]
    ag = f.get("agenda", (560, 1160))
    profil = {
        "metier": metier,
        "heure": f["heure"], "accroche": f["accroche"], "etat": f["etat"],
        "t1": f["t1"], "t2": f["t2"], "t3": f["t3"], "t4": f["t4"],
        "arg1": f["args"][0], "arg2": f["args"][1], "arg3": f["args"][2],
        "pan0": f["pan"][0], "pan1": f["pan"][1],
        "agendaH": ag[1],
        "hRang": hauteurs["appel-2"], "hAppel": hauteurs["appel-1"],
        "hOuvert": hauteurs["appel-1-ouvert"],
        "hImpact": hauteurs["impact-rdv"], "hNuit": hauteurs["impact-nuit"],
    }
    chemin = os.path.join(ICI, "profils", f"{metier}.json")
    json.dump(profil, open(chemin, "w"), ensure_ascii=False, indent=2)
    print(f"  → {chemin}")


if __name__ == "__main__":
    cibles = (["plombier", "veterinaire", "restaurant", "institut_beaute"]
              if "--tous" in sys.argv else [a for a in sys.argv[1:] if not a.startswith("--")])
    for m in cibles:
        preparer(m)
