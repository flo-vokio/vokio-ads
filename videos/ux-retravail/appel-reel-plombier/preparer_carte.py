#!/opt/vokio-site-repo/.venv/bin/python
"""Retire de la carte réelle la bande « Voir la fiche client » (un lien qui a
l'air cliquable dans une vidéo où rien ne l'est), par le même geste que
l'original pour le bloc « Rappeler » : on recolle le haut et le bas, rien
n'est ajouté à l'image. Les mots du résumé sont au-dessus de la coupe, leurs
positions ne bougent pas."""
from PIL import Image
D = "assets/plans/"
Y0, Y1 = 830, 1000          # lignes unies de part et d'autre du séparateur et du lien
for n in ("carte-vide", "carte-pleine"):
    im = Image.open(D + n + ".png").convert("RGB")
    W, H = im.size
    haut, bas = im.crop((0, 0, W, Y0)), im.crop((0, Y1, W, H))
    out = Image.new("RGB", (W, haut.height + bas.height))
    out.paste(haut, (0, 0)); out.paste(bas, (0, haut.height))
    out.save(D + n + "-sans-lien.png")
    print(n, out.size)
