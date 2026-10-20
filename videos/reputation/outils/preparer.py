#!/usr/bin/env python3
"""Recadre les captures de filmer.py pour le montage : on garde l'INTÉRIEUR des cartes (la bordure et les coins
arrondis de .card-v sont redessinés en CSS, comme dans 24 h chez Vokio : la capture d'un élément embarque les coins
de la page, d'où un coin carré visible).

    python3 /opt/vokio-ads/videos/reputation/outils/preparer.py

Bordure .card-v = 1 px × 3 = 3 px. Séparateurs de la liste mesurés le 20/10 : liste-apres 207-209 (ligne de Claire,
plus haute à cause du bouton « Annuler »), puis tous les 183 px ; liste-avant tous les 183 px.
"""
from pathlib import Path

from PIL import Image

C = Path(__file__).resolve().parent.parent / "assets" / "captures"
B = 3


def interieur(src, dst, haut=None):
    im = Image.open(C / src)
    w, h = im.size
    im.crop((B, B, w - B, (haut if haut else h - B))).save(C / dst)


for f in sorted(C.glob("saisie-*.png")):
    if not f.stem.endswith("-net"):
        interieur(f.name, f.stem + "-net.png")
interieur("liste-avant.png", "liste-avant-net.png")
interieur("liste-apres.png", "ligne-claire-net.png", haut=210)     # la ligne de Claire et son séparateur
# les quatre lignes suivantes, prises dans liste-apres (sans les coins du haut de la carte : la jointure ne se voit pas)
im = Image.open(C / "liste-apres.png")
im.crop((B, 210, im.width - B, im.height - B)).save(C / "lignes-suite-net.png")
print("ok", len(list(C.glob("*-net.png"))))
