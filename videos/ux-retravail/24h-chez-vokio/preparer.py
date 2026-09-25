#!/usr/bin/env python3
"""Prépare les quatre cartes de « 24 h chez Vokio » (25/09).

Source : assets/captures/<metier>-brut.png, la carte « appel déplié » filmée dans
app.vokio.fr (plans.py) après garnir_24h.py (/root/vokio-deploy/24h-vokio-250926/).

1. Coupe tout ce qui suit le résumé (filet, « Rappeler 06 … », lien vers la fiche) et
   recolle le bas arrondi de la boîte : aucun numéro à l'écran, trois lignes de moins.
2. Efface le paragraphe du résumé à la couleur du fond de la boîte (carte vide) :
   le texte est réécrit en HTML par-dessus, pour pouvoir souligner la phrase clé.
3. Écrit cartes.json : hauteur de chaque carte et position de la première ligne,
   relevées sur les pixels, jamais saisies.
"""
import json
from pathlib import Path
from PIL import Image

ICI = Path(__file__).parent
CAP = ICI / "assets" / "captures"
FOND_BOITE = (239, 236, 227)


def grappes(im):
    """Rangées d'encre regroupées : [(y0, y1, x0, x1)]."""
    W, H = im.size
    px = im.load()
    out, cur = [], None
    for y in range(H):
        xs = [x for x in range(70, 1000) if sum(px[x, y]) < 600]
        if xs and cur is None:
            cur = [y, y, min(xs), max(xs)]
        elif xs:
            cur[1], cur[2], cur[3] = y, min(cur[2], min(xs)), max(cur[3], max(xs))
        elif cur:
            out.append(tuple(cur)); cur = None
    return out


res = {}
for m in ["institut_beaute", "restaurant", "veterinaire", "plombier"]:
    im = Image.open(CAP / f"{m}-brut.png").convert("RGB")
    W, H = im.size
    g = grappes(im)
    # les lignes du résumé : après l'étiquette « RÉSUMÉ DE L'APPEL » (y≈270-291),
    # corps ~37 px, pas de 68-69 px ; la suivante qui décroche de plus de 100 px est « Rappeler »
    corps = [c for c in g if c[0] > 330 and 30 <= c[1] - c[0] <= 42]
    lignes = [corps[0]]
    for c in corps[1:]:
        if c[0] - lignes[-1][0] > 100:
            break
        lignes.append(c)
    y_prem, y_der = lignes[0][0], lignes[-1][1]
    # bas de la boîte : premier y, sous le lien, où la colonne x=500 quitte le fond de boîte
    px = im.load()
    bb = next(y for y in range(y_der + 200, H) if px[500, y] != FOND_BOITE and px[500, y - 1] == FOND_BOITE)
    coupe_haut = y_der + 44            # un peu d'air sous la dernière ligne
    bas = im.crop((0, bb - 36, W, H))  # l'arrondi du bas de la boîte et la marge
    vide = im.crop((0, 0, W, coupe_haut)).copy()
    # efface le paragraphe
    for y in range(y_prem - 14, coupe_haut):
        for x in range(96, 962):
            vide.putpixel((x, y), FOND_BOITE)
    out = Image.new("RGB", (W, vide.height + bas.height))
    out.paste(vide, (0, 0)); out.paste(bas, (0, vide.height))
    out.save(CAP / f"{m}-vide.png")
    res[m] = dict(largeur=W, hauteur=out.height, y_premiere_ligne=y_prem,
                  x_texte=min(c[2] for c in lignes), lignes=len(lignes))
    print(m, res[m])
(ICI / "cartes.json").write_text(json.dumps(res, indent=1) + "\n")
