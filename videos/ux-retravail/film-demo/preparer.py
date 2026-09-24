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
3. Prépare le résumé en calque texte (méthode de monter_appel_reel.py) :
   la carte dépliée est coupée en trois, le haut (en-tête et étiquette), un fond
   d'une rangée, le bas (lien vers la fiche) ; le paragraphe est réécrit en HTML,
   Geist 14 px × 3, interlignage 1,625, encre à 80 %, comme dans l'application.
4. Recadre l'agenda sur la plage horaire qui contient TOUS ses rendez-vous :
   on le montre en entier, on ne le fait plus défiler.
5. Écrit profils/<metier>.json : les textes du film, lus dans profils.py (la
   source unique), plus les géométries des plans à l'écran.
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


# Le résumé du film plombier vient d'une capture antérieure à l'appel réel du
# 22/09 (l'appel n° 1 de profils.py raconte désormais cet enregistrement). On
# reprend donc le texte de la capture, corrigé : l'appel est à 23:07, le
# rendez-vous est le lendemain matin (« demain matin », pas « ce matin »).
RESUME_CAPTURE = {
    "plombier": "M. Lefèvre a une fuite sous l'évier, l'arrivée d'eau est coupée. Le geste "
                "d'urgence lui a été donné au téléphone. Intervention calée demain matin 8 h 30, "
                "adresse notée : 14 rue Sainte, Marseille 8e. SMS de confirmation envoyé.",
}
PT = 3                 # la capture est prise à 3 px par point CSS
DECALAGE_ENCRE = 18    # du haut de la boîte du paragraphe au haut de l'encre de sa 1re ligne (mesuré)
INTERLIGNE = 22.75 * PT


def bandes(im, x0=110, x1=940, y0=230):
    """Rangées d'encre (texte sombre) de la carte, regroupées en lignes."""
    px = im.load()
    W, H = im.size
    encre = [y for y in range(y0, H) if any(sum(px[x, y][:3]) < 450 for x in range(x0, x1, 2))]
    out, s, p = [], None, None
    for y in encre:
        if s is None or y > p + 2:
            if s is not None:
                out.append((s, p))
            s = y
        p = y
    out.append((s, p))
    return out


def decouper_resume(im, dest):
    """Coupe la carte dépliée autour du paragraphe du résumé."""
    b = bandes(im)
    etiquette, lignes = b[0], [x for x in b[1:] if x[1] - x[0] > 25]
    # le lien « Voir la fiche client » est la dernière bande haute ; le paragraphe est avant
    lignes = [x for x in lignes if x[0] < b[-1][0] - 100]
    haut_p = lignes[0][0] - DECALAGE_ENCRE
    n = len(lignes)
    bas_p = round(haut_p + n * INTERLIGNE)
    W, H = im.size
    im.crop((0, 0, W, haut_p)).save(f"{dest}/ouvert-haut.png")
    im.crop((0, haut_p - 8, W, haut_p - 7)).save(f"{dest}/ouvert-fond.png")
    im.crop((0, bas_p, W, H)).save(f"{dest}/ouvert-bas.png")
    return haut_p, n, H - bas_p


def cadrer_agenda(im):
    """La plage horaire qui contient tous les rendez-vous, étiquettes d'heure comprises."""
    px = im.load()
    W, H = im.size
    creneau = lambda p: 236 <= p[0] <= 246 and 214 <= p[1] <= 228 and 175 <= p[2] <= 192   # noqa: E731
    rangs = [y for y in range(H) if sum(creneau(px[x, y]) for x in range(150, W - 20, 6)) > 4]
    haut, bas = min(rangs), max(rangs)
    # les étiquettes d'heure (colonne de gauche) : on garde celle d'avant et celle d'après
    heures = [y for y in range(H) if any(sum(px[x, y][:3]) < 450 for x in range(15, 140, 2))]
    lab, s, p = [], None, None
    for y in heures:
        if s is None or y > p + 2:
            if s is not None:
                lab.append((s + p) // 2)
            s = y
        p = y
    lab.append((s + p) // 2)
    avant = max([c for c in lab if c < haut - 10] or [haut])
    apres = min([c for c in lab if c > bas + 10] or [bas])
    return max(0, avant - 45), min(H, apres + 45)


# le restaurant garde son cadrage de la passe précédente (demande du 24/09)
AGENDA_RECOLLE = {"plombier", "veterinaire", "institut_beaute"}
ECHELLE_AGENDA = 1.1        # 11 px CSS × 3 × 1,1 = 36,3 px : le texte des rendez-vous à 36 px
LARGEUR_AGENDA = 909        # 909 px de capture × 1,1 = 1000 px à l'écran (on retire la marge droite vide)
BUDGET_AGENDA = 940 / ECHELLE_AGENDA   # hauteur de capture qui tient entre le titre et 1400 px


def recoller_agenda(im):
    """Méthode appel-reel-plombier : la vraie capture recollée SANS les tranches vides.

    Une rangée = une heure, de son étiquette à la suivante. On garde chaque rangée qui
    porte un rendez-vous, avec son étiquette ; on retire les heures vides, en gardant une
    seule rangée comme respiration quand plusieurs séparent deux rendez-vous, puis, si ça
    ne tient toujours pas à 36 px, sans respiration, puis en retirant aussi les
    demi-heures vides au-dessus et au-dessous des rendez-vous (l'étiquette reste). Les
    étiquettes d'heure restantes montrent le saut. Rien n'est ajouté, onglets et aide
    retirés."""
    px = im.load()
    W, H = im.size
    creneau = lambda p: 236 <= p[0] <= 246 and 214 <= p[1] <= 228 and 175 <= p[2] <= 192   # noqa: E731
    plein = [sum(creneau(px[x, y]) for x in range(150, W - 20, 6)) > 4 for y in range(H)]
    # étiquettes d'heure (colonne de gauche), sous les onglets
    encre = [y for y in range(400, H) if any(sum(px[x, y][:3]) < 450 for x in range(15, 140, 2))]
    lab, s0, p0 = [], None, None
    for y in encre:
        if s0 is None or y > p0 + 2:
            if s0 is not None:
                lab.append((s0 + p0) // 2)
            s0 = y
        p0 = y
    lab.append((s0 + p0) // 2)
    lab = [c for c in lab if c < H - 150]           # l'aide du bas n'est pas une heure
    M = 25                                          # demi-hauteur d'une étiquette
    rangs = [(lab[i] - M, lab[i + 1] - M) for i in range(len(lab) - 1)]
    # une rangée est occupée si un rendez-vous commence ou passe SOUS son étiquette
    # (un rendez-vous qui finit pile à l'heure ne déborde pas sur la rangée suivante)
    occupe = [any(plein[y] for y in range(a + M + 4, b)) for a, b in rangs]
    i0 = occupe.index(True)
    i1 = len(occupe) - 1 - occupe[::-1].index(True)

    def niveau(n):
        garde = []
        i = i0
        while i <= i1:
            if occupe[i]:
                garde.append(rangs[i]); i += 1; continue
            j = i
            while not occupe[j]:
                j += 1
            if n == 0:
                garde.append(rangs[i])             # une seule rangée de respiration
            i = j
        if n < 2:
            if i1 + 1 < len(lab):                  # l'étiquette qui ferme la dernière heure
                c = lab[i1 + 1]
                garde.append((c - M, c + M))
            return garde
        # niveau 2 : dans chaque rangée gardée, on retire la partie vide qui ne porte ni
        # étiquette ni rendez-vous (au moins 30 px)
        fin = []
        for a, b in garde:
            y = a
            while y < b:
                if plein[y] or y < a + 2 * M:
                    y0 = y
                    while y < b and (plein[y] or y < a + 2 * M):
                        y += 1
                    fin.append((max(a, y0 - 12), min(b, y + 12)))
                else:
                    y += 1
        # fusion
        fin.sort(); out = [list(fin[0])]
        for a, b in fin[1:]:
            if a <= out[-1][1] + 30:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return [tuple(x) for x in out]

    for n in (0, 1, 2):
        tranches = niveau(n)
        if sum(b - a for a, b in tranches) <= BUDGET_AGENDA:
            break
    h = sum(b - a for a, b in tranches)
    out = Image.new("RGB", (min(W, LARGEUR_AGENDA), h))
    y = 0
    for a, b in tranches:
        out.paste(im.crop((0, a, min(W, LARGEUR_AGENDA), b)), (0, y))
        y += b - a
    return out, n, tranches


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
            haut_p, n_lignes, h_bas = decouper_resume(im, dest)
        if nom == "agenda-jour" and metier in AGENDA_RECOLLE:
            im, niv, tr = recoller_agenda(im)
            print(f"  {metier}: agenda recollé, niveau {niv}, {len(tr)} tranches {tr}, {im.size}")
        elif nom == "agenda-jour":
            y0, y1 = cadrer_agenda(im)
            im = im.crop((0, y0, im.width, y1))
            print(f"  {metier}: agenda recadré {y0}–{y1} ({y1 - y0} px)")
        if nom == "appel-3":
            im, bande = retirer_numero(im)
            print(f"  {metier}: numéro retiré, rangées {bande}")
        im.save(f"{dest}/{nom}.png", optimize=True)
        hauteurs[nom] = round(im.height * LARGEUR / im.width)
    f = PROFILS[metier]["film"]
    resume = RESUME_CAPTURE.get(metier, PROFILS[metier]["appels"][0][8])
    k = LARGEUR / 1044
    profil = {
        "metier": metier,
        "heure": f["heure"], "accroche": f["accroche"], "etat": f["etat"],
        "t1": f["t1"], "t2": f["t2"], "t3": f["t3"], "t4": f["t4"],
        "arg1": f["args"][0], "arg2": f["args"][1], "arg3": f["args"][2],
        "resume": resume,
        "hHaut": round(haut_p * k, 2), "hBas": round(h_bas * k, 2),
        "lignesCapture": n_lignes,
        "agendaW": Image.open(f"{dest}/agenda-jour.png").width, "agendaHsrc": Image.open(f"{dest}/agenda-jour.png").height,
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
