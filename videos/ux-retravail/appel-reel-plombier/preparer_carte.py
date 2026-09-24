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

# L'agenda du lendemain, EN ENTIER (retour Florian 24/09 : « on ne le voit plus en
# entier »). La capture fait 2472 px de haut : pour que les trois rendez-vous
# tiennent dans le cadre à une taille lisible, on retire les heures vides (10 h,
# 13 h à 17 h), les onglets Jour/Semaine et l'aide du bas. Les étiquettes d'heure
# restantes disent le saut de temps. Rien n'est ajouté.
AG = [(0, 180), (460, 720), (930, 1230), (1990, 2240), (2440, 2472)]
im = Image.open(D + "agenda-jour.png").convert("RGB")
W = im.size[0]
out = Image.new("RGB", (W, sum(b - a for a, b in AG)))
y = 0
for a, b in AG:
    out.paste(im.crop((0, a, W, b)), (0, y)); y += b - a
out.save(D + "agenda-jour-entier.png")
print("agenda-jour-entier", out.size)
