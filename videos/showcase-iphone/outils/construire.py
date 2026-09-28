#!/usr/bin/env python3
"""Construit LA source de vérité partagée (v2) : donnees/donnees.js (window.DONNEES) + les .json jumeaux.

    python3 outils/construire.py          mesure (Chromium), calcule, écrit, résout le point, contrôle (9:16, donnees/)
    python3 outils/construire.py --format 16x9 [--racine formats/16x9] [--variante s7-signature=16x9-C] [--entrees D]
                                          même chose pour un autre format, dans un projet rendable produit par
                                          outils/format.py (qui l'appelle : c'est le chemin normal) ; --entrees D : lire
                                          son/dialogue.json et donnees/mots.json dans D (entrées figées, format.py --entrees git:REV)

FORMATS (27/09) : la mise en page vient de mise-en-page/*.json (outils/mise_en_page.py), une entrée par format ; le
minutage, la voix, les événements et le son sont COMMUNS. --racine = le projet où mesurer (servi à Chromium) et où écrire
<racine>/donnees/ ; les entrées communes (son/dialogue.json, donnees/mots.json) sont lues dans CE projet-ci.
DONNEES.format et DONNEES.geometrie portent tout ce qu'une scène doit savoir du cadre (plus de px en dur dans les scènes).
Pour le 9:16 (défaut), les sorties sont identiques à celles d'avant les formats (contrôle : outils/identite.py).

Ordre de reconstruction : son/dialogue.py → outils/mots.py → outils/preparer_agenda.py → outils/construire.py.
Entrées (produites avant) :
  son/dialogue.json            (son/dialogue.py)       extraits du vrai appel, placés aux temps du film (47,00 s depuis la finition)
  donnees/mots.json            (outils/mots.py)        mots horodatés, temps film
  donnees/agenda-geo.json      (outils/preparer_agenda.py, v2 : échelle 4,5, image en (70 ; 590))
  compositions/s1-sonnerie.html, s7-signature.html      géométrie mesurée (le « . » de s1, #mot-pt de s7 à 400 px)
Sorties :
  donnees/mesures.json  secousses.json  point.json  scenes.json  evenements.json  reperes.json  pages.json
  donnees/appel.json  donnees/styles-pages.json
  donnees/donnees.js    (tout, en une affectation window.DONNEES = {...})
  donnees/point-resolu.json  (POINT.etat(n/30) évalué DANS Chromium par lib/point.js, pour le son en python)
Règle : tout temps d'animation calé sur la voix vient d'ici. Relancer après toute retouche de mots.json,
de la géométrie de s1/s7, des contrats de texte ou de l'agenda. Plan : critique.json, plan.chantiers[0].
3e passe du 16:9 (28/09) : les étiquettes d'heure de la capture (09:00, 10:00, 11:00 : des pixels, pas des mots) sont des
obstacles du trajet s6 (etiquettes_capture, qui suivent la sortie de l'agenda) ; forme « couloir » pour le premier geste depuis
la gouttière (mise-en-page/s6-sms.json forme_depart_gouttiere, couloir_dy) ; glissement de l'accroche de s1
(s1-sonnerie.json « glisse », GLISSE : clés 1.1 et 1.2 du point, DONNEES.geometrie.s1.glisse) ; CONSTRUIRE_REJETS=1 imprime,
pour chaque geste planifié, le départ choisi et les départs rejetés (pas trop grand, heurt avec quel mot ou quelle étiquette).

INSERTIONS DE TEMPS (28/09, l'échange du prénom : le film passe de 47,00 s à 50,066667 s, 1 502 images) : la règle est UNE
donnée, son/dialogue.json « insertions » (écrite par son/dialogue.py, liste INSERTIONS), lue par outils/temps.py. Tous les
nombres en dur de ce fichier (instants, images, attendus) sont ceux du FILM DE BASE (47,00 s, 1 410 images, commit a6d3d8e) :
B(t) et BI(n) les portent dans le film courant (+ 92 images à partir de l'image 758), hôtes de index.html compris
(hotes(), poser_hotes() : index.html est réécrit s'il diverge). Seuls échappent à la règle les gestes NÉS d'une insertion :
choregraphie_s5() (le point écrit « 09:00 », attend le prénom plume levée, écrit « Florian » sous la voix), calée sur les
mots de AP et CP, en temps du film courant. Allonger encore le film : une entrée dans INSERTIONS de son/dialogue.py (pivot
sur un temps de la grille), puis dialogue.py → mots.py → construire.py ; rien à retoucher ici, sauf une scène dont
l'insertion coupe un geste (outils/temps.py dit où tombe chaque image). DECALAGE_SMS et DECALAGE_FIN (27/09) sont l'ancienne
forme du même geste, fondue dans le film de base.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mise_en_page  # noqa: E402
import temps  # noqa: E402

PROJET = Path(__file__).resolve().parents[1]
_ARGS = argparse.ArgumentParser(description="Construit donnees/ (window.DONNEES) pour un format.")
_ARGS.add_argument("--format", default="9x16")
_ARGS.add_argument("--racine", default=None, help="projet rendable où mesurer et écrire donnees/ (défaut : ce projet en 9x16, formats/<format> sinon)")
_ARGS.add_argument("--variante", action="append", default=[], help="<scène>=<nom> : variante de mise-en-page/<scène>.json")
_ARGS.add_argument("--entrees", default=None, help="dossier où lire son/dialogue.json et donnees/mots.json (défaut : ce projet) ; "
                                                   "sert aux contrôles d'identité avec des entrées figées (git show)")
ARGS = _ARGS.parse_args(sys.argv[1:] if __name__ == "__main__" else [])
FORMAT = ARGS.format
RACINE = Path(ARGS.racine).resolve() if ARGS.racine else (PROJET if FORMAT == "9x16" else PROJET / "formats" / FORMAT)
MEP = mise_en_page.charger(FORMAT, dict(v.split("=", 1) for v in ARGS.variante))
LARGEUR, HAUTEUR = MEP["format"]["largeur"], MEP["format"]["hauteur"]
# RECOMPOSITION (28/09) : trois échelles par format, relatives au 9:16 (outils/mise_en_page.py) ; chaque constante en px suit
# la géométrie qu'elle mesure. kp / km / kv rendent la valeur du 9:16 TELLE QUELLE quand leur échelle vaut 1 (entiers compris) :
# donnees/ du 9:16 reste identique à l'octet (outils/identite.py).
#   K_POINT (kp) : le disque du film de s1 à s6 (formats.json « echelle_point », 1 par défaut : 44 px) : écart à l'encre, sauts sur
#                  les heures, levée de plume, hochements (l'agenda reste la capture 1:1 : sa gouttière est faite pour 44 px) ;
#   K_MOT   (km) : le wordmark de s7 (corps / 400) et son point de ı (0,11 em) : stylo, bond, diamètre final. Quand K_MOT ≠ K_POINT,
#                  le point change de taille en quittant le téléphone (départ du stylo → pose du stylo, 41,00 → 41,50) ;
#   K_VIT   (kv) : les vitesses (V_TRAJET, V_CALME, retour chariot, étirement, pas maximal) : les distances à parcourir grandissent
#                  avec le texte de s2 (corps / 72) et avec le wordmark ; la plus grande des échelles du format.
K_POINT = mise_en_page.echelle_point(MEP)
K_MOT = mise_en_page.echelle_mot(MEP)
K_VIT = max(K_POINT, K_MOT, MEP["texte"]["styles"]["s2_texte"]["corps"] / 72)


def _k(k):
    return (lambda v: v) if k == 1 else (lambda v: round(v * k, 4))


kp, km, kv = _k(K_POINT), _k(K_MOT), _k(K_VIT)
DON = RACINE / "donnees"              # sorties (le format)
ENTREES = Path(ARGS.entrees).resolve() if ARGS.entrees else PROJET
SRC = ENTREES / "donnees"             # entrées communes à tous les formats (mots.json)
DIALOGUE = ENTREES / "son" / "dialogue.json"
PW = "/root/.pwtest/bin/python"
FPS = 30
# INSERTIONS DE TEMPS (28/09) : le film de base (47,00 s, 1 410 images) allongé par son/dialogue.json « insertions »
TEMPS = temps.Insertions.depuis(DIALOGUE)
IMAGES_BASE = 1410


def tronque(v, k=6):
    """v tronqué à k décimales (jamais au-dessus de v) : une durée ou un début d'hôte ne déborde pas sur l'image suivante."""
    return math.floor(round(v * 10 ** k, 3)) / 10 ** k


def B(t):
    """Instant du film de base → film courant (float exact ; arrondir à la sortie)."""
    return TEMPS.t(t)


def BI(n):
    """Image du film de base → film courant."""
    return TEMPS.image(n)


IMAGES = TEMPS.images(IMAGES_BASE)   # 1502 images : 0 … 1501
# durée déclarée à HyperFrames (index.html, timeline de la racine) : il rend ceil(durée × 30) images ; 1502/30 = 50,0666…67
# arrondi au µs (50,066667) en rendrait 1 503 : tronquée au µs, 50,066666 (47,0 pour le film de base)
DUREE = tronque(IMAGES / FPS)
# Finition du 27/09 (arbitrages du réalisateur) : le SMS se lit (bulle entière ≥ 3,8 s) et la fin ne rogne rien :
# +1,70 s à partir de la descente du téléphone (39,30 → 41,00) et +0,30 s de tenue finale, soit 45,00 → 47,00.
DECALAGE_SMS = 1.70
DECALAGE_FIN = 0.30
SR = 48000

COULEURS = {"papier": "#F4F1E8", "encre": "#262019", "solaire": "#EFA424", "terracotta": "#C0452C",
            "vert": "#6E9C74", "gris": "#6F695F", "bulle": "#E9E3D6"}

# id, début, durée de l'hôte (data-start / data-duration de index.html, à l'identique)
# FILM DE BASE (47,00 s) ; hotes() les porte dans le film courant (s5 s'allonge de l'échange du prénom, s6 et s7 glissent)
HOTES_BASE = [("s1-sonnerie", 0.0, 4.6333), ("s2-voix", 4.6333, 5.7667), ("s3-ecoute", 10.40, 6.90),
              ("s4-agenda", 17.30, 7.8999), ("s5-rendez-vous", 25.20, 6.15), ("s6-sms", 31.35, 10.0499),
              ("s7-signature", 41.40, 5.60)]
# s4 : 7,8999 et non 7,9 (en flottant, 17,3 + 7,9 = 25,200000000000003 : l'hôte de s4 restait monté à l'image 756).
# s6 : 10,0499 et non 10,05, même raison (31,35 + 10,05 = 41,400000000000006). Fins NOMINALES : 25,20, 31,35 et 41,40.
FINS_NOMINALES_BASE = {"s4-agenda": 25.20, "s5-rendez-vous": 31.35, "s6-sms": 41.40}


def borne_debut(t):
    """Début d'hôte porté : la valeur à 6 décimales qui garde la même première image (image = round(t × 30), et HyperFrames
    monte l'hôte aux images n telles que n/30 ≥ début) : tronquée d'abord (44,466666 pour 1334/30 : arrondie, 44,466667,
    ferait manquer l'image 1334), arrondie si la troncature change d'image (un début à la demi-image : 34,416667)."""
    premiere = math.ceil(t * FPS - 1e-6)
    for v in (tronque(t), round(t, 6)):
        if img(v) == img(t) and math.ceil(v * FPS - 1e-6) == premiere:
            return v
    raise SystemExit(f"hôte : aucun début à 6 décimales ne garde les images de {t}")


def hotes():
    """HOTES du film courant : [(id, data-start, data-duration)], et les fins nominales. Un hôte que l'insertion ne coupe pas
    garde sa durée ; celui qu'elle coupe (s5) gagne les images insérées (durée tronquée au µs)."""
    out, fins = [], {}
    for sid, d, h in HOTES_BASE:
        d2 = d if abs(B(d) - d) < 1e-9 else borne_debut(B(d))
        ajout = (B(d + h) - (d + h)) - (B(d) - d)
        h2 = h if abs(ajout) < 1e-9 else tronque(h + ajout)
        out.append((sid, d2, h2))
        if sid in FINS_NOMINALES_BASE:      # la fin nominale = le début porté de la scène suivante (bout à bout, au µs)
            f_ = FINS_NOMINALES_BASE[sid]
            fins[sid] = f_ if abs(B(f_) - f_) < 1e-9 else borne_debut(B(f_))
    return out, fins

# Contrats de texte (plan J). top = ligne de base − décalage mesuré dans Chromium (styles-pages.json).
# FORMATS : les valeurs viennent de mise-en-page/texte.json (entrée du format) ; le dictionnaire ci-dessous est la
# RÉFÉRENCE 9:16, gardé pour mémoire et contrôlé égal à texte.json["9x16"] (une seule vérité).
STYLES_9X16 = {
    "s2_texte": {"famille": '"Geist",sans-serif', "style": "normal", "graisse": 400, "corps": 72, "interligne": 84,
                 "x": 90, "lignes_de_base": [874, 958, 1042]},
    # l'appelant en Instrument Serif italique 64/72 (finition du 27/09, 96/104 avant) : la hauteur d'x de cette italique
    # vaut 0,516 em (glyphe « x », fontTools ; 49,5 px à 96 px, soit 30 % AU-DESSUS de l'agente en v2, et encore 41,3 px à
    # 80 px) ; à 64 px, 33,0 px : l'agente (Geist 72, 38,2 px) la dépasse de 16 %, elle parle enfin plus fort (plan.direction)
    "s3_texte": {"famille": '"Instrument Serif",serif', "style": "italic", "graisse": 400, "corps": 64, "interligne": 72,
                 "x": 90, "lignes_de_base": [874, 946, 1018]},
    "haut_agente": {"famille": '"Geist",sans-serif', "style": "normal", "graisse": 400, "corps": 72, "interligne": 84,
                    "x": 90, "lignes_de_base": [330, 414, 498]},
    "haut_appelant": {"famille": '"Instrument Serif",serif', "style": "italic", "graisse": 400, "corps": 64, "interligne": 72,
                      "x": 90, "lignes_de_base": [350, 422]},
    "mention": {"famille": '"Geist",sans-serif', "style": "normal", "graisse": 400, "corps": 36, "interligne": 48,
                "x": 90, "lignes_de_base": [330]},
}
STYLES = {k: dict(v) for k, v in MEP["texte"]["styles"].items()}
if FORMAT == "9x16":
    assert STYLES == STYLES_9X16, "mise-en-page/texte.json[9x16] s'écarte de la référence 9:16 de construire.py"
LARGEUR_MAX_S2 = MEP["texte"]["largeur_max_s2"]   # garde-fou : le disque (encre + 18 + 22 = +40 px, voir s2-voix.html ECART) reste avant x_max_point (9:16 : 850, 1010)
LARGEUR_MAX = MEP["texte"]["largeur_max"]         # 9:16 : marges de 70 à 1010 : x 90 + 920 = 1010
X_MAX_POINT = MEP["texte"]["x_max_point"]         # bord droit que le disque ne passe pas dans s2 (9:16 : 1010)

# L'accroche de s1 (finition du 27/09) : mot à mot par le masque de ligne, dès l'image 0 ; le « . » (#point) se pose
# en dernier. Lu par compositions/s1-sonnerie.html ET par DONNEES.point.taille (une seule donnée).
ACCROCHE = {"debut": 0.0, "pas": 0.10, "duree": 0.50, "depart_yPercent": 80, "ease": "power3.out", "lisible": 0.90,
            "avance_images": 1, "point": [round(25 / FPS, 6), round(29 / FPS, 6)],
            "note": "5 mots, le k-ième part à debut + k·pas − avance_images/30 (yPercent 80 → 0 dans son masque de ligne, fondu "
                    "power2.out sur 30 % du geste : à l'image 0, « Vous » monte déjà ; jamais un point de i seul) ; entière à 0,87 s ; "
                    "le point passe de 0 à son diamètre de naissance de l'image 25 à 29"}

# Trajets planifiés du point (finition du 27/09, arbitrage 4) : il ne passe JAMAIS sous une lettre. Il se tient à droite
# de l'encre du dernier mot révélé (ECART_MIN au bord du disque) et ANTICIPE : il glisse vers la fin du mot suivant et y
# est arrivé à l'image où ce mot paraît ; les mots courts qu'il ne peut pas précéder calmement sont franchis (ils
# paraissent derrière lui). Vitesse de pointe ≤ V_TRAJET px par image.
R_DISQUE = kp(22.0)       # 9:16 : 22 ; FORMATS : 22 × K_POINT (le disque du film de s1 à s6)
ECART_MIN = kp(18.0)
MARGE_ENCRE = kp(2.0)     # distance minimale disque → boîte d'encre d'un mot visible
V_TRAJET = kv(100.0)      # px par image × K_VIT
V_CALME = kv(60.0)        # préféré : le point quitte le mot plus tôt plutôt que de filer
ARRETS_S2 = ["Bonjour,", "Élise,", "l’assistante", "vocale", "Clinique", "vétérinaire", "Port.", "Comment", "puis-je", "aider\u202f?"]
ARRETS_S6 = ["recevrez", "SMS", "confirmation."]
ECOUTE_DY = 118.0         # s3 (9:16) : le point écoute 118 px sous la dernière ligne de base de la parole, aligné sur x = 90 + 22
ECOUTE = MEP["s3"]["ecoute"]  # FORMATS : la place d'écoute {x, y, forme} (mise-en-page/s3-ecoute.json)

# VERSION iPHONE (27/09, demande de Florian : « un screenshot de téléphone plus réaliste type iPhone ») : en s6, le SMS
# arrive dans un iPhone 16 Pro (titane naturel) ouvert sur l'app Messages d'iOS 26, mode clair. La règle « aucun chrome
# factice » est levée pour CET objet, à la demande explicite de Florian. Tout est donné en points iOS (402 × 874 pt, écran
# de l'iPhone 16 Pro) et converti par PT_ECRAN : écran de 854 px de large, soit 2,1244 px par point ; le corps 17 pt du
# SMS fait 36,1 px dans le film (règle ≥ 36). Mesures relevées sur la photo de presse Apple d'iOS 26 (Messages) :
# marges, bouton retour, avatar, pastille du nom, forme de la queue des bulles. Le texte du SMS est la formulation
# corrigée du gabarit (« à 09:00, Clinique vétérinaire du Port. », au lieu de « à 09:00 chez Clinique vétérinaire du Port. »),
# coupé comme iOS le coupe : au plus long, mot à mot, dans 255 pt de texte (contrôlé par la scène).
# FORMATS : le corps, l'écran et l'échelle viennent de mise-en-page/s6-sms.json (9:16 : 82 / 470 / 916 × 1917, 854 px d'écran) ;
# l'interface d'iOS (bulle, en points) est commune.
_S6 = MEP["s6"]
PT_ECRAN = _S6["ecran_largeur_px"] / _S6["ecran"]["largeur_pt"]
IPHONE = {
    "telephone": dict(_S6["telephone"]),
    "ecran": dict(_S6["ecran"]),
    "bulle": {"gauche_pt": 16, "haut_pt": 194, "rayon_pt": 20, "padding_pt": [9.5, 13, 9.5, 15], "corps_pt": 17,
              "interligne_pt": 22, "texte_max_pt": 255, "queue_pointe_pt": [9.0, 7.1], "fond": "#E9E9EB", "texte": "#000000",
              # ligne la plus longue (« samedi 19 septembre à 09:00, »), mesurée DANS la scène (chrome-headless-shell de HyperFrames,
              # Inter 400 17 pt, approche −0,013 em, l'approche d'Inter à cette taille) : la scène la remesure à chaque chargement
              # (queue_pointe_pt : pointe de la queue depuis le coin bas gauche, relevée au pixel sur la photo de presse)
              "police": "Inter 400, 17 pt, approche −0,013 em, opsz 17", "largeur_texte_pt": 232.57,
              "lignes": ["Bonjour Florian, votre", "rendez-vous est confirmé :", "Consultation vétérinaire, le",
                         "samedi 19 septembre à 09:00,", "Clinique vétérinaire du Port.", "Démo Vokio, RDV fictif."]},
    "ecart_point": _S6["ecart_point"],   # px entre la pointe de la queue et le haut du disque (v2 : 14 px sous la queue)
}


def geometrie_iphone():
    """Géométrie de s6 (version iPhone) en px film, dérivée d'IPHONE. Lue par compositions/s6-sms.html, qui la recontrôle."""
    T, B = IPHONE["telephone"], IPHONE["bulle"]
    k = PT_ECRAN
    ex0, eh = T["x0"] + T["bord_cote"], T["haut"] + T["bord_haut"]
    ew, eH = IPHONE["ecran"]["largeur_pt"] * k, IPHONE["ecran"]["hauteur_pt"] * k
    assert abs(ew - (T["largeur"] - 2 * T["bord_cote"])) < 1e-6 and abs(eH + 2 * T["bord_haut"] - T["hauteur"]) < 0.5
    bx0, bh = ex0 + B["gauche_pt"] * k, eh + B["haut_pt"] * k
    bH = (B["padding_pt"][0] + B["padding_pt"][2] + len(B["lignes"]) * B["interligne_pt"]) * k
    bW = (B["padding_pt"][3] + B["largeur_texte_pt"] + B["padding_pt"][1]) * k
    qx, qy = bx0 + B["queue_pointe_pt"][0] * k, bh + bH + B["queue_pointe_pt"][1] * k
    r3 = lambda v: round(v, 3)
    point = (r3(bx0 + R_DISQUE), r3(qy + IPHONE["ecart_point"] + R_DISQUE))
    return {
        "modele": "iPhone 16 Pro (titane naturel), iOS 26, app Messages en mode clair : l'objet vrai qui porte le SMS",
        "pt": round(k, 6),
        "telephone": dict(T, x1=T["x0"] + T["largeur"], bas=T["haut"] + T["hauteur"]),
        "ecran": dict(IPHONE["ecran"], x0=ex0, haut=eh, largeur=r3(ew), hauteur=r3(eH), x1=r3(ex0 + ew)),
        "bulle": dict(B, x0=r3(bx0), x1=r3(bx0 + bW), largeur=r3(bW), haut=r3(bh), hauteur=r3(bH), bas=r3(bh + bH), corps_px=r3(B["corps_pt"] * k),
                      interligne_px=r3(B["interligne_pt"] * k), queue_pointe={"x": r3(qx), "y": r3(qy)}),
        "point": {"x": point[0], "y": point[1],
                  "note": f"le point attend {IPHONE['ecart_point']} px sous la pointe de la queue de la bulle, bord gauche du disque "
                          "au bord gauche de la bulle ; la forme grise de la bulle éclot depuis lui, le texte et la mention « SMS / Aujourd’hui 16:55 » "
                          "montent en fondu dès que le disque a couvert la boîte du texte"},
    }


def img(t):
    return int(math.floor(t * FPS + 0.5 + 1e-9))       # arrondi au plus proche, .5 vers le haut (comme Math.round)


def a_img(t):
    """Arrondi à l'image (secondes film)."""
    return round(img(t) / FPS, 6)


def demi(t):
    """Arrondi à la demi-image (les clés du plan données à 4 décimales : 4,6333 = 139/30 ; 25,3833 = 761,5/30)."""
    return round(math.floor(t * FPS * 2 + 0.5) / 2 / FPS, 6)


HOTES, FINS_NOMINALES = hotes()     # le film courant (index.html : poser_hotes)


def poser_hotes():
    """index.html de la racine : data-start / data-duration des sept hôtes, durée de la racine et de la bande son = HOTES et
    DUREE du film courant. Réécrit seulement ce qui diverge (et le dit) : une insertion de temps ne demande aucune retouche
    à la main de index.html (28/09). Idempotent."""
    f = RACINE / "index.html"
    html = avant = f.read_text()
    nombre = lambda v: str(int(v)) if float(v).is_integer() else f"{v:.6f}".rstrip("0").rstrip(".")
    changes = []
    motifs = [(rf'(<div id="h-{sid}"[^>]*?data-start=")([\d.]+)(" data-duration=")([\d.]+)(")', (d, h)) for sid, d, h in HOTES]
    for motif, (d, h) in motifs:
        m = re.search(motif, html)
        assert m, f"index.html : hôte introuvable ({motif[:40]})"
        if (m.group(2), m.group(4)) != (nombre(d), nombre(h)):
            changes.append(f"{m.group(0)[9:30]} {m.group(2)}/{m.group(4)} → {nombre(d)}/{nombre(h)}")
            html = html[:m.start()] + m.group(1) + nombre(d) + m.group(3) + nombre(h) + m.group(5) + html[m.end():]
    for motif in (r'(id="root"[^>]*?data-duration=")([\d.]+)(")', r'(<audio id="bande-son"[^>]*?data-duration=")([\d.]+)(")'):
        m = re.search(motif, html)
        assert m, f"index.html : {motif[:30]} introuvable"
        if m.group(2) != nombre(DUREE):
            changes.append(f"{motif[1:14]} {m.group(2)} → {nombre(DUREE)}")
            html = html[:m.start()] + m.group(1) + nombre(DUREE) + m.group(3) + html[m.end():]
    if html != avant:
        f.write_text(html)
        print(f"{f} : hôtes du film courant posés ({'; '.join(changes)})")


def lire_json(nom):
    """Lit donnees/<nom> : mots.json (entrée commune) dans ce projet, le reste dans les données du format."""
    return json.loads(((SRC if nom == "mots.json" else DON) / nom).read_text())


def ecrire_json(nom, obj):
    (DON / nom).write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def navigateur(*args):
    r = subprocess.run([PW, str(PROJET / "outils" / "navigateur.py"), *args, "--racine", str(RACINE), "--taille", f"{LARGEUR}x{HAUTEUR}"],
                       capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise SystemExit(f"navigateur.py {args} : {r.stderr[-3000:]}")
    out = json.loads(r.stdout)
    if out.get("erreurs_page"):
        raise SystemExit(f"erreurs JS dans le banc ({args[0]}) : {out['erreurs_page']}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
def enveloppe_par_image(segments, i0, n_img):
    """Moyenne, sur chaque image [n/30, (n+1)/30), d'une enveloppe trapèze.
    segments = [(début, fin, attaque, relâche)] en secondes (rampes linéaires ; 0 = coupe nette)."""
    t = np.arange(int((i0 + n_img) / FPS * SR) + 1) / SR
    a = np.zeros_like(t)
    for (d, f, fondu_a, fondu_r) in segments:
        m = (t >= d) & (t < f)
        e = np.ones(m.sum())
        e = np.minimum(e, (t[m] - d) / fondu_a if fondu_a else 1)
        e = np.minimum(e, (f - t[m]) / fondu_r if fondu_r else 1)
        a[m] = np.clip(e, 0, 1)
    out = []
    for k in range(i0, i0 + n_img):
        s0, s1 = int(round(k / FPS * SR)), int(round((k + 1) / FPS * SR))
        out.append(round(float(a[s0:s1].mean()), 4))
    return out


def secousses():
    # RECOMPOSITION (28/09) : les amplitudes suivent la taille de ce qui tremble (9:16 : 6 et 2 px, inchangées) : en s1 le « . »
    # de l'accroche (corps de l'accroche / 150), en s6 le téléphone (px par point iOS / celui du 9:16, 854 / 402)
    k1 = MEP["s1"]["phrase"]["corps"] / 150
    k6 = PT_ECRAN / (854 / 402)
    a = lambda v, k: v if k == 1 else round(v * k, 3)
    # s1 (plan E) : tonalité 440 Hz, 1,5 s on (0 → 1,5) puis 2e sonnerie 2,7 → 4,2 ; fondus de 10 ms ; à 4,2 la
    # 2e tonalité ne coupe pas (elle s'ouvre en cloche) : pas de rampe de sortie, le tremblement s'arrête net et
    # l'enveloppe est forcée à 0 dès l'image 126 (décroché). 139 valeurs : images 0 à 138.
    s1_seg = [(0.0, 1.5, 0.010, 0.010), (2.7, 4.2, 0.010, 0.0)]
    env1 = enveloppe_par_image(s1_seg, 0, 139)
    env1 = [0.0 if k >= 126 else v for k, v in enumerate(env1)]
    # s6 (plan E) : vibreur, deux impulsions de 180 ms séparées de 90 ms, la 1re à l'image 1100 exactement (film de base ;
    # 1192 depuis l'échange du prénom)
    n6 = BI(1100)
    v0 = n6 / FPS
    s6_seg = [(v0, v0 + 0.18, 0.012, 0.025), (v0 + 0.27, v0 + 0.45, 0.012, 0.025)]
    env6 = enveloppe_par_image(s6_seg, n6, 15)
    return {
        "unite": "enveloppe 0 → 1 par image (moyenne sur l'image) ; dx = amplitude_x × enveloppe × motif_x ; dy = amplitude_y × enveloppe × motif_y",
        "s1": {"description": "tonalité d'attente 440 Hz (ton-1 0 → 1,5 s ; ton-2 2,7 → 4,2 s), attaques et relâche de ton-1 10 ms, "
                              "ton-2 sans relâche (il devient cloche) ; 0 dès l'image 126 (décroché)",
               "image0": 0, "enveloppe": env1,
               "amplitude_x": a(6.0, k1), "motif_x": [0, 1, 0, -1], "amplitude_y": a(2.0, k1), "motif_y": [1, 0, -1, 0],
               "amplitude_px": a(6.0, k1), "motif": [0, 1, 0, -1],
               "phase_par_image_absolue": True,
               "segments_s": [[a, b] for a, b, _, _ in s1_seg], "rampes_s": [[fa, fr] for _, _, fa, fr in s1_seg],
               "frequence_hz": 7.5,
               "note": "motif de 4 images = 7,5 Hz, sous Nyquist ; x(n) = 6·env(n)·[0,+1,0,−1][n mod 4], y(n) = 2·env(n)·[+1,0,−1,0][n mod 4] : "
                       "quadrature, le point décrit un losange ; amplitude_px / motif = alias v1 de l'axe x"},
        "s6": {"description": "vibreur du SMS : impulsions " + " et ".join(f"{a:.4f} → {b:.4f}".replace(".", ",") for a, b, _, _ in s6_seg)
                              + " s, attaque 12 ms, relâche 25 ms",
               "image0": n6, "enveloppe": env6,
               "amplitude_x": a(6.0, k6), "motif_x": [1, 0, -1, 0], "amplitude_px": a(6.0, k6), "motif": [1, 0, -1, 0],
               "phase_par_image_absolue": False,
               "segments_s": [[round(a, 6), round(b, 6)] for a, b, _, _ in s6_seg], "rampes_s": [[fa, fr] for _, _, fa, fr in s6_seg],
               "frequence_hz": 7.5,
               "note": f"x(n) = 6·env·[+1,0,−1,0][(n−{n6}) mod 4] ; le téléphone de s6 ET #point lisent la même valeur (POINT.secousse('s6', t))"},
    }


def mot(mots, extrait, rang):
    return next(w for w in mots if w["extrait"] == extrait and w["rang"] == rang)


def voyelle(mots, e, r):
    m = mot(mots, e, r)
    return m.get("voyelle", m["debut"])


# ─────────────────────────────────────────────────────────────────────────────
# Eases de GSAP (mêmes formules que gsap.parseEase ; GSAP : power1 = quadratique, power2 = cubique, power3 = quartique)
def ease(nom):
    if nom in (None, "none", "linear"):
        return lambda p: p
    if nom == "sine.inOut":
        return lambda p: -(math.cos(math.pi * p) - 1) / 2
    if nom == "sine.out":
        return lambda p: math.sin(p * math.pi / 2)
    if nom == "sine.in":
        return lambda p: 1 - math.cos(p * math.pi / 2)
    k = {"power1": 2, "power2": 3, "power3": 4, "power4": 5}[nom.split(".")[0]]
    sens = nom.split(".")[1]
    if sens == "in":
        return lambda p: p ** k
    if sens == "out":
        return lambda p: 1 - (1 - p) ** k
    return lambda p: (2 ** (k - 1)) * p ** k if p < 0.5 else 1 - ((-2 * p + 2) ** k) / 2


def cadre(v):
    return min(1.0, max(0.0, v))


FORMES = {
    # fenêtres (fraction du temps du mouvement) et eases, par axe
    "droit": {"x": (0.0, 1.0, "sine.inOut"), "y": (0.0, 1.0, "sine.inOut")},
    "retour": {"x": (0.0, 1.0, "power2.inOut"), "y": (0.0, 1.0, "power2.inOut")},
    # changement de ligne : le point descend d'abord (il quitte la ligne lue par la droite), puis glisse à gauche
    # dans la bande de la ligne suivante, encore vide
    "descente": {"x": (0.15, 1.0, "sine.inOut"), "y": (0.0, 0.40, "sine.inOut")},
    # 3e passe du 16:9 (28/09, revue Florian : la « descente » passait sur l'étiquette « 10:00 » de la capture) : sortie de la
    # gouttière des heures PAR LE COULOIR entre deux étiquettes. y va d'abord à la hauteur du couloir (COULOIR_Y), s'y tient
    # pendant que x franchit la colonne des étiquettes, puis rejoint le mot ; x part à 10 % du geste.
    "couloir": {"x": (0.10, 1.0, "sine.inOut"), "y": (0.0, 0.30, "sine.inOut"), "y2": (0.50, 1.0, "sine.inOut")},
}
COULOIR_Y = None      # posé par trajets() (milieu des filets 09:00 et 10:00 + mise-en-page/s6-sms.json « couloir_dy »)


def mouvement(A, B, forme):
    F = FORMES[forme]
    (x0, x1, ex), (y0, y1, ey) = F["x"], F["y"]
    fx, fy = ease(ex), ease(ey)
    if "y2" in F:                     # deux temps en y : A → couloir, tenue, couloir → B
        (z0, z1, ez), fz, YC = F["y2"], ease(F["y2"][2]), COULOIR_Y

        def f(u):
            ux = cadre((u - x0) / (x1 - x0))
            y = A[1] + (YC - A[1]) * fy(cadre((u - y0) / (y1 - y0)))
            y += (B[1] - YC) * fz(cadre((u - z0) / (z1 - z0)))
            return (A[0] + (B[0] - A[0]) * fx(ux), y)
        return f

    def f(u):
        ux = cadre((u - x0) / (x1 - x0))
        uy = cadre((u - y0) / (y1 - y0))
        return (A[0] + (B[0] - A[0]) * fx(ux), A[1] + (B[1] - A[1]) * fy(uy))
    return f


def etiquettes_capture(agenda, f0, f1):
    """Les étiquettes d'heure de la VRAIE capture (pixels de agenda-avant.png, pas des mots du DOM) comme obstacles du point,
    image par image de f0 à f1 : leur boîte d'encre (agenda-geo.json « etiquettes », visibles) suit la sortie de l'agenda
    (evenements.agenda_sort 31,00 → 31,35 : y = −y_sortie × power3.in(p), opacité 1 − p, comme s5-rendez-vous.html) ; une
    étiquette cesse d'être un obstacle sous 20 % d'opacité (contraste < 1,2:1 sur le papier). 3e passe du 16:9 (28/09)."""
    AS0, AS1 = B(31.00), B(31.35)     # film de base (evenements.agenda_sort)
    YS = MEP["agenda"]["y_sortie"]
    e4 = ease("power3.in")
    out = []
    for n in range(f0, f1 + 1):
        p = cadre((n / FPS - AS0) / (AS1 - AS0))
        if 1 - p < 0.20:
            continue
        dy = -YS * e4(p)
        for h, b in agenda["etiquettes"].items():
            if b.get("visible"):
                out.append({"texte": f"étiquette {h} de la capture", "page": "capture", "vis": n, "fin": n + 1,
                            "x0": b["x0"], "x1": b["x1"], "y0": b["y0"] + dy, "y1": b["y1"] + dy})
    return out


def boites_mots(pages, sorties):
    """Boîtes d'encre de chaque unité posée, avec sa fenêtre de visibilité [vis ; fin[ en images (vis = première image
    où elle se voit, la révélation partant à revele = attaque − 1 image) ; les unités révélées ligne par ligne (C2, C3, C4)
    prennent l'instant de la première unité de leur ligne."""
    par_ligne = {"C2", "C3", "C4"}
    out = []
    for ip, p in enumerate(pages):
        so = sorties.get(p["_cle"])
        fin = IMAGES + 1 if so is None else int(math.ceil((so[0] + so[1]) * FPS - 1e-6))
        premiers = {}
        for m in p["mots"]:
            premiers.setdefault(m["ligne"], m)
        for m in p["mots"]:
            rev = premiers[m["ligne"]]["revele"] if p["extrait"] in par_ligne else m["revele"]
            out.append({"texte": m["texte"], "page": p["_cle"], "vis": img(rev) + 1, "fin": fin,
                        "x0": m["encre_x0"], "x1": m["encre_x1"],
                        "y0": m["ligne_de_base"] - m["encre_haut"], "y1": m["ligne_de_base"] + m["encre_bas"]})
    return out


def r_effectif(v):
    """Demi-grand axe du point dessiné à la vitesse v (px par image) : étirement plafonné (lib/point.js)."""
    if v <= ETIREMENT["seuil"]:
        return R_DISQUE
    return R_DISQUE * (1 + min(ETIREMENT["max"], (v - ETIREMENT["seuil"]) / ETIREMENT["pente"]))


def heurts(xs, ys, f0, boites, frames):
    """Images de frames où le disque (étirement compris) approche à moins de MARGE_ENCRE d'une boîte d'encre visible."""
    out = []
    for n in frames:
        k = n - f0
        cx, cy = xs[k], ys[k]
        v = 0.0
        if 0 < k < len(xs) - 1:
            v = math.hypot(xs[k + 1] - xs[k - 1], ys[k + 1] - ys[k - 1]) / 2
        r = r_effectif(v) + MARGE_ENCRE
        for b in boites:
            if not (b["vis"] <= n < b["fin"]):
                continue
            dx = max(b["x0"] - cx, 0.0, cx - b["x1"])
            dy = max(b["y0"] - cy, 0.0, cy - b["y1"])
            if math.hypot(dx, dy) < r:
                out.append((n, b["texte"], round(math.hypot(dx, dy), 1)))
    return out


class Trajet:
    """Un trajet du point, échantillonné image par image (lib/point.js l'interpole linéairement entre deux images).
    Tenues et mouvements (forme, départ, arrivée) ; chaque mouvement est vérifié : vitesse de pointe, et aucun heurt
    avec l'encre visible (boîtes de boites_mots) à aucune image."""

    def __init__(self, nom, f0, pos, boites):
        self.nom, self.f0, self.boites = nom, f0, boites
        self.xs, self.ys = [pos[0]], [pos[1]]
        self.journal = []

    @property
    def f(self):
        return self.f0 + len(self.xs) - 1

    @property
    def pos(self):
        return (self.xs[-1], self.ys[-1])

    def tenir(self, jusqu_a):
        while self.f < jusqu_a:
            self.xs.append(self.xs[-1]); self.ys.append(self.ys[-1])

    def essai(self, depart, arrivee, B, forme):
        A = self.pos
        f = mouvement(A, B, forme)
        N = arrivee - depart
        xs = [A[0]] * (depart - self.f) + [f(k / N)[0] for k in range(1, N + 1)]
        ys = [A[1]] * (depart - self.f) + [f(k / N)[1] for k in range(1, N + 1)]
        X, Y = self.xs + xs, self.ys + ys
        pas = max(math.hypot(X[k] - X[k - 1], Y[k] - Y[k - 1]) for k in range(len(self.xs), len(X)))
        return xs, ys, pas, X, Y

    def aller(self, B, arrivee, forme, libre, n_min=6, raison="", v_max=None):
        """Mouvement vers B, arrivé à l'image `arrivee` : départ le plus TARD possible (le point tient la fin du mot qu'il
        ponctue) qui respecte la vitesse de pointe et ne heurte aucune encre visible ; jamais avant `libre`.
        Le mouvement occupe les images depart + 1 … arrivee (à l'image depart, le point est encore à sa place)."""
        v_max = V_TRAJET if v_max is None else v_max
        tot = max(self.f, libre)
        rejets = []
        # deux passes : d'abord un geste CALME (≤ V_CALME) au départ le plus tard possible ; sinon, le départ qui donne le
        # geste le plus lent (≤ v_max), quitte à ne pas s'arrêter sur le mot précédent
        essais = [(d, min(V_CALME, v_max)) for d in range(arrivee - n_min, tot - 1, -1)] + \
                 [(d, v_max) for d in sorted(range(tot, arrivee - n_min + 1),
                                             key=lambda d: self.essai(d, arrivee, B, forme)[2])]
        for depart, vlim in essais:
            xs, ys, pas, X, Y = self.essai(depart, arrivee, B, forme)
            if pas > vlim:
                rejets.append((depart, "pas", round(pas, 1)))
                continue
            h = heurts(X + [X[-1]], Y + [Y[-1]], self.f0, self.boites, range(self.f, arrivee + 1))
            if h:
                rejets.append((depart, "heurt", h[:2]))
                continue
            A = self.pos
            if os.environ.get("CONSTRUIRE_REJETS"):      # diagnostic : pourquoi ce départ et pas un plus calme
                print(f"  {raison} : départ {depart} ; rejets {rejets[:10]}", file=sys.stderr)
            self.xs += xs; self.ys += ys
            self.journal.append({"vers": raison, "depart": depart, "arrivee": arrivee, "forme": forme, "pas_max": round(pas, 1),
                                 "de": [round(A[0], 2), round(A[1], 2)], "a": [round(B[0], 2), round(B[1], 2)]})
            return depart
        print("rejets :", rejets[:12], file=sys.stderr)
        raise SystemExit(f"trajet {self.nom} : aucun mouvement possible vers {raison} ({B}) arrivé à {arrivee} "
                         f"(depuis {self.pos} à {self.f}, libre {libre})")

    def sortie(self):
        return {"nom": self.nom, "image0": self.f0, "image1": self.f, "t0": round(self.f0 / FPS, 6), "t1": round(self.f / FPS, 6),
                "x": [round(v, 3) for v in self.xs], "y": [round(v, 3) for v in self.ys], "journal": self.journal}


def fin_mot(m):
    return (round(m["encre_x1"] + ECART_MIN + R_DISQUE, 3), round(m["ligne_de_base"] - R_DISQUE, 3))


def trajets(pages, sorties, P1, geo_s3, agenda, S_bulle):
    """T1 : s2 et s3 (images 139 → 516) ; T2 : s6, de la gouttière des heures à la bulle (images 933 → 1032 du film de base,
    1025 → 1124 depuis l'échange du prénom : son départ suit la sortie du dernier sous-titre de s5, une donnée)."""
    boites = boites_mots(pages, sorties)
    pg = {p["_cle"]: p for p in pages}
    # ── T1 ──
    t1 = Trajet("s2-s3", 139, (P1[0] + 10, P1[1]), boites)
    s2 = [p for p in pages if p["scene"] == "s2-voix"]
    arrets = []
    for ip, p in enumerate(s2):
        for m in p["mots"]:
            if m["texte"] in ARRETS_S2:
                arrets.append((ip, m))
    assert [m["texte"] for _, m in arrets] == ARRETS_S2, [m["texte"] for _, m in arrets]
    prec = None
    for ip, m in arrets:
        B, vis = fin_mot(m), img(m["revele"]) + 1
        if prec is None:
            forme, libre, n_min = "retour", 139, 11          # le retour chariot : sur la ligne de base de « mains prises. »
            t1.aller(B, vis, forme, libre, n_min=n_min, raison=f"retour chariot, puis s2 « {m['texte']} »", v_max=kv(140.0))
            prec = (ip, m)
            continue
        elif prec[0] != ip:
            so = sorties[s2[prec[0]]["_cle"]]
            forme, libre, n_min = "droit", int(math.ceil((so[0] + so[1]) * FPS - 1e-6)), 5   # page suivante : la page lue est sortie
        elif prec[1]["ligne"] != m["ligne"]:
            forme, libre, n_min = "descente", 0, 8
        else:
            forme, libre, n_min = "droit", 0, 6
        t1.aller(B, vis, forme, libre, n_min=n_min, raison=f"s2 « {m['texte']} »")
        prec = (ip, m)
    # vers la place d'écoute de s3, quand la dernière page de s2 est sortie
    so = sorties[s2[-1]["_cle"]]
    libre = int(math.ceil((so[0] + so[1]) * FPS - 1e-6))
    L = (ECOUTE["x"], ECOUTE["y"])
    if FORMAT == "9x16":
        assert L == (geo_s3["x"] + R_DISQUE, geo_s3["lignes_de_base"][-1] + ECOUTE_DY), "s3-ecoute.json[9x16] ≠ 90 + 22 ; 1018 + 118"
    t1.aller(L, libre + 16, ECOUTE.get("forme", "descente"), libre, n_min=16, raison="s3 : place d'écoute")
    # s3 : le hochement du tamis (14,15 → 14,30 → 14,50) et la hausse sur « disponibilités » (16,19 → 16,49), tenue jusqu'à 17,20
    for (ta, tb, dy, raison) in ((14.15, 14.30, kp(8.0), "tamis : hochement (bas)"), (14.30, 14.50, 0.0, "tamis : hochement (retour)"),
                                 (16.19, 16.49, kp(-10.0), "hausse sur « disponibilités »")):
        t1.tenir(img(ta))
        t1.aller((L[0], L[1] + dy), img(tb), "droit", img(ta), n_min=img(tb) - img(ta), raison=raison)
    t1.tenir(516)
    # ── T2 ──
    XA, Y9 = agenda["x_point"], agenda["heures"]["09:00"]
    so5 = sorties[[p["_cle"] for p in pages if p["scene"] == "s5-rendez-vous"][-1]]
    f_gout = int(math.ceil((so5[0] + so5[1]) * FPS - 1e-6))          # 933 (film de base) : le dernier sous-titre de s5 est sorti
    # FORMATS : en 16:9 le sous-titre n'est plus sur le chemin (il est à gauche, l'agenda à droite) : le point peut quitter la
    # gouttière plus tôt pour un geste plus calme (mise-en-page/s6-sms.json « depart_gouttiere_avance », images ; 9:16 : 0)
    f_gout -= int(MEP["s6"].get("depart_gouttiere_avance", 0))
    # 3e passe du 16:9 (28/09) : les étiquettes d'heure de la capture sont des obstacles du trajet s6 tant qu'elles se voient
    # (le planificateur ne connaissait que les sous-titres : la « descente » passait sur « 10:00 » sans que rien ne le voie)
    global COULOIR_Y
    COULOIR_Y = round((agenda["heures"]["09:00"] + agenda["heures"]["10:00"]) / 2 + MEP["s6"].get("couloir_dy", 0), 3)
    t2 = Trajet("s6", f_gout, (XA, Y9), boites + etiquettes_capture(agenda, f_gout, f_gout + 60))
    pa = [p for p in pages if p["scene"] == "s6-sms"][0]
    arrets6 = [m for m in pa["mots"] if m["texte"] in ARRETS_S6]
    assert [m["texte"] for m in arrets6] == ARRETS_S6
    prec = None
    # FORMATS (recomposition du 28/09) : la forme du premier geste, de la gouttière des heures au premier mot de s6
    # (mise-en-page/s6-sms.json « forme_depart_gouttiere », « droit » par défaut, celui du 9:16). En 16:9 les sous-titres sont
    # À GAUCHE de l'agenda : en ligne droite, le point repassait sur l'étiquette « 09:00 » qui s'efface (controles.py F4,
    # image 934) ; « descente » le fait d'abord descendre sous la rangée des étiquettes, puis glisser vers le mot.
    forme0 = MEP["s6"].get("forme_depart_gouttiere", "droit")
    for m in arrets6:
        B, vis = fin_mot(m), img(m["revele"]) + 1
        forme = forme0 if prec is None else ("droit" if prec["ligne"] == m["ligne"] else "descente")
        t2.aller(B, vis, forme, f_gout, n_min=6, raison=f"s6 « {m['texte']} »")
        prec = m
    so6 = sorties[pa["_cle"]]
    libre = int(math.ceil((so6[0] + so6[1]) * FPS - 1e-6))
    t2.aller(S_bulle, libre + 20, "droit", libre, n_min=20, raison="s6 : sous la queue de la bulle, où le SMS naîtra")
    return t1, t2, boites


ETIREMENT = {"seuil": kv(30), "pente": kv(90), "max": 0.25}   # long ≤ 1,25 (arbitrage 2 : plus de pilule de 92 px) ; px par image × K_VIT


GLISSE = None         # {"dx", "t": [t0, t1], "ease"} : glissement de l'accroche de s1 (main(), d'après mise-en-page/s1-sonnerie.json « glisse »)

# L'ÉCHANGE DU PRÉNOM (28/09, retour de Florian : « mon prénom est noté alors que je ne l'ai pas donné ») : le point écrit ce
# qu'il entend, quand il l'entend. « Très bien. » : il écrit « 09:00 » (l'heure est acquise) ; « C'est pour quel prénom ? » :
# il LÈVE la plume au-dessus du créneau et attend, immobile (« 09:00 » se lit en entier, le nom manque) ; « C'est pour » : il
# la repose là où il l'a levée ; « Florian. » : il écrit le nom à vitesse constante, l'encre de chaque syllabe sous sa voix.
LEVEE_QUESTION = 72.0     # px (× K_POINT) au-dessus de la ligne du bloc : le disque reste ≥ 9 px au-dessus du bloc (au-dessus du créneau)
LEVER_IMAGES = 10         # la plume se lève en 10 images (sine.inOut) : un geste calme, pas un sursaut
SORTIE_QUESTION = 27.84   # « Très bien. | C'est pour quel prénom ? » sort 27,84 → 28,00 (son/dialogue.py CONTRAINTES_IMAGE : ≥ AP.film_out)
SORTIE_REPONSE = 29.08    # « C'est pour Florian. » sort 29,08 → 29,24, avant « Parfait, » (29,30) (≥ CP.film_out)


def choregraphie_s5(mots, agenda):
    """Les gestes de s5 nés de l'insertion « prenom » (images et instants du film COURANT, calés sur les mots de AP et CP et
    sur l'encre mesurée du bloc : agenda-geo.json heure_encre, florian_encre ; mots.json syllabes florian_*)."""
    bl = agenda["bloc"]
    heure, fl = bl["heure_encre"], bl["florian_encre"]
    syl = lire_json("mots.json")["syllabes"]
    ap = [w for w in mots if w["extrait"] == "AP"]
    cp = [w for w in mots if w["extrait"] == "CP"]
    assert [w["cle"] for w in ap] == ["tres", "bien", "c'est", "pour", "quel", "prenom"] and [w["cle"] for w in cp] == ["c'est", "pour", "florian"], \
        "son/dialogue.json : l'échange du prénom (AP, CP) attendu"
    flo, an = syl["florian_flo"], syl["florian_an"]
    BCY = bl["centre_y"]
    # la plume attend dans le blanc entre « 09:00 » et « Florian » : bord révélé (x + R) au milieu du blanc
    x_att = round((heure["x1"] + fl["x0"]) / 2 - R_DISQUE, 3)
    n_heure = img(ap[1]["fin"])                          # « bien. » fini : « 09:00 » est écrit (777)
    n_leve = n_heure + LEVER_IMAGES                      # plume levée (787)
    n_desc = img(cp[0]["debut"])                         # « C'est » de la réponse : il repose la plume (842)
    # « Florian » à vitesse constante : le bord révélé passe le début d'encre du F au début de « Flo », la fin d'encre du n à
    # la fin de « an » (mots.json syllabes, relevés à la main sur le spectre)
    v = (fl["x1"] - fl["x0"]) / ((an["fin"] - flo["debut"]) * FPS)                    # px par image
    t_pose = demi(flo["debut"] - (fl["x0"] - (x_att + R_DISQUE)) / (v * FPS))        # plume reposée (848)
    t_n = demi(an["fin"])                                                             # l'encre du n est écrite (861)
    x_n = round(fl["x1"] - R_DISQUE, 3)
    v_ecr = (x_n - x_att) / ((t_n - t_pose) * FPS)
    # puis il glisse jusqu'à 14 px après l'encre (x_fin) en sine.out, sans à-coup (vitesse de départ = v_ecr) : image entière
    n_fin = int(round(t_n * FPS + (math.pi / 2) * (bl["x_fin"] - x_n) / v_ecr))
    assert n_heure < n_leve < n_desc < t_pose * FPS < t_n * FPS < n_fin, (n_heure, n_leve, n_desc, t_pose, t_n, n_fin)
    return {"x_attente": x_att, "y_levee": round(BCY - kp(LEVEE_QUESTION), 3), "n_heure": n_heure, "n_leve": n_leve,
            "n_desc": n_desc, "t_pose": t_pose, "t_n": t_n, "x_n": x_n, "n_fin": n_fin, "v_ecriture": round(v_ecr, 3),
            "n_levee_fin": n_fin + 4, "n_gouttiere": n_fin + 18}


def point(mots, agenda, mesures, t1, t2, S_bulle):
    s1c, s1d = mesures["s1"]["centre"], mesures["s1"]["diametre"]
    M, D = mesures["s7"]["centre"], mesures["s7"]["diametre"]
    # le disque du film (s1 → s6) et le point du ı (#mot-pt, D) : les mêmes en 9:16 ; sinon le point prend la taille du ı en
    # quittant le téléphone (départ du stylo → pose du stylo), sans changer aucun instant
    D_FILM = D if K_MOT == K_POINT else float(kp(44.0))
    stylo = mesures["s7"]["stylo"]
    XA = agenda["x_point"]
    H = agenda["heures"]
    Y9, Y10, Y11 = H["09:00"], H["10:00"], H["11:00"]
    bloc = agenda["bloc"]
    BX0 = round(bloc["x0"] + D_FILM / 2, 3)
    BCY = bloc["centre_y"]
    BXF = bloc["x_fin"]
    SY = stylo["y"]
    # hauteur du bond sur le ı au-dessus du point de #mot-pt, en px du 9:16 (× K_MOT) : mise-en-page/s7-signature.json « bond »
    # (défaut 110, celui du 9:16) ; un format serré en hauteur l'abaisse pour que le sommet reste loin du bord du cadre
    BOND = MEP["s7"].get("bond", 110)
    P1x, P1y = s1c["x"], s1c["y"]
    dS = DECALAGE_SMS
    C5 = choregraphie_s5(mots, agenda)
    n_hoche = img(voyelle(mots, "A4", 6))          # voyelle de « Florian » dite par l'agente : 821 du film de base, 913
    k = lambda n, t, x, y, ease=None, arc=None, note=None: {kk: v for kk, v in (
        ("n", n), ("t", demi(t)), ("image", round(demi(t) * FPS, 1)), ("x", round(x, 3)), ("y", round(y, 3)),
        ("ease", ease), ("arc", arc), ("note", note)) if v is not None}
    e1 = (t1.xs[-1], t1.ys[-1])
    # 3e passe du 16:9 (28/09, revue YouTube : la moitié droite du cadre restait vide 2,9 s) : un format peut poser l'accroche
    # CENTRÉE puis la faire glisser à sa place avant la relance (mise-en-page/s1-sonnerie.json « glisse », GLISSE résolu par
    # main()) ; le point, qui est le « . » de « prises », glisse avec elle (même instants, même ease). 9:16 : aucune clé ajoutée.
    gl = GLISSE
    dxg = gl["dx"] if gl else 0
    pos = [
        k(1, 0.0, P1x + dxg, P1y, note="s1 : point final de « mains prises. » (mesuré) ; invisible (0 px) jusqu'à 0,8333, posé à 0,9667 (DONNEES.accroche.point), encre ; tremble avec la tonalité"),
    ] + ([k(1.1, gl["t"][0], P1x + dxg, P1y, note="s1 : l'accroche centrée commence à glisser vers sa place (DONNEES.geometrie.s1.glisse)"),
          k(1.2, gl["t"][1], P1x, P1y, gl["ease"], note="s1 : l'accroche est à sa place, avant la relance ; le point est son « . »")] if gl else []) + [
        k(2, 4.5667, P1x, P1y, note="décroché à 126 (contraction), solaire à 127, gonfle jusqu'à 44 px à 4,60"),
        k(3, 4.6333, P1x + kp(10), P1y, "power2.out", note="anticipation : recul de 10 px vers la droite (137 → 139)"),
        k(4, 17.20, e1[0], e1[1], note="fin du trajet planifié s2-s3 (pistes.trajets[0], images 139 → 516)"),
        k(5, 17.80, XA, Y9, "bezier(.45,0,.15,1)", note="s4 : attend sur la ligne 09:00 (l'agenda monte dessous 18,37 → 19,07)"),
        k(6, 20.4333, XA, Y9, note="« neuf » : envol 613"),
        k(7, 20.5333, XA, Y9 - kp(36), "power2.out", note="sommet 616"),
        k(8, 20.6667, XA, Y9, "power2.in", note="contact 09:00, image 620 (voyelle de « neuf »)"),
        k(9, 21.1667, XA, Y9, note="« dix » : envol 635"),
        k(10, 21.2333, XA + kp(12), Y9 - kp(20), "power2.out", note="sommet 637, côté colonne (loin de l'encre de « 09:00 »)"),
        k(11, 21.4333, XA, Y10, "power2.in", {"dx": kp(14)}, note="contact 10:00, image 643 (voyelle de « dix »)"),
        k(12, 21.9333, XA, Y10, note="« onze » : envol 658"),
        k(13, 22.0000, XA + kp(8), Y10 - kp(14), "power2.out", note="sommet 660, côté colonne"),
        k(14, 22.2000, XA, Y11, "power2.in", {"dx": kp(10)}, note="contact 11:00, image 666 (voyelle de « onze »)"),
        k(15, 23.9667, XA, Y11, note="retour : envol 719 (« à » de l'appelant)"),
        k(16, 24.2333, XA, Y9 - kp(20), "bezier(.4,0,.4,1)", {"dx": kp(24)}, note="sommet 727, en arc côté colonne"),
        k(17, 24.3667, XA, Y9, "power2.in", note="contact retour 09:00, image 731"),
        k(18, 25.2000, XA, Y9, note="s5"),
        k(19, 25.3667, BX0, BCY, "power2.inOut", note="plume posée au bord gauche du bloc (761)"),
        k(20, 25.3833, BX0, BCY, note="demi-image : le départ a une vitesse non nulle, le point bouge dès l'image 762 (le la)"),
        # L'ÉCHANGE DU PRÉNOM (28/09, choregraphie_s5) : clés 21 à 21.5, en temps du film courant
        k(21, C5["n_heure"] / FPS, C5["x_attente"], BCY, "power1.out",
          note=f"il écrit « 09:00 » sous « Très bien. » et s'arrête dans le blanc qui précède « Florian » ({C5['n_heure']})"),
        k(21.1, C5["n_leve"] / FPS, C5["x_attente"], C5["y_levee"], "sine.inOut",
          note=f"l'agente demande le prénom : il lève la plume au-dessus du créneau ({C5['n_leve']}) ; « 09:00 » se lit en entier"),
        k(21.2, C5["n_desc"] / FPS, C5["x_attente"], C5["y_levee"],
          note=f"en suspens, immobile, jusqu'à « C'est » de la réponse ({C5['n_desc']})"),
        k(21.3, C5["t_pose"], C5["x_attente"], BCY, "sine.inOut", note="il repose la plume là où il l'avait levée"),
        k(21.4, C5["t_n"], C5["x_n"], BCY, "none",
          note=f"il écrit « Florian » à vitesse constante ({C5['v_ecriture']} px par image) : l'encre de Flo·ri·an paraît sous sa voix"),
        k(21.5, C5["n_fin"] / FPS, BXF, BCY, "sine.out", note=f"il s'arrête 14 px après l'encre de « Florian » ({C5['n_fin']})"),
        # arbitrage 5 : sitôt l'écriture finie, le point quitte le bloc (il ne reste pas collé à « Florian » comme une
        # pastille) : il lève la plume au-dessus du bloc, puis rejoint la gouttière des heures, aligné sur 09:00
        k(22, C5["n_levee_fin"] / FPS, BXF, BCY - kp(60), "power2.out",
          note=f"lève la plume : 60 px au-dessus de la ligne du bloc ({C5['n_levee_fin']}), au-dessus de l'encre du bloc"),
        k(23, C5["n_gouttiere"] / FPS, XA, Y9, "sine.inOut",
          note=f"dans la gouttière des heures, sur la ligne 09:00, là où il frappait les heures ({C5['n_gouttiere']})"),
        # la suite : le film de base (instants portés par B)
        k(24, B(27.2500), XA, Y9),
        k(25, n_hoche / FPS, XA, Y9 + kp(6), "power2.in",
          note=f"hochement de 6 px sur la voyelle de « Florian » que l'agente répète (image {n_hoche}), dans la gouttière : il confirme le nom écrit"),
        k(26, B(27.4833), XA, Y9, "power2.out"),
        k(27, t2.f0 / FPS, XA, Y9, note=f"il attend dans la gouttière jusqu'à la sortie du dernier sous-titre de s5 (image {t2.f0}) ; trajet s6 ensuite"),
        k(28, t2.f / FPS, S_bulle[0], S_bulle[1], note="fin du trajet s6 (pistes.trajets[1]) : sous la queue de la bulle, d'où le SMS naîtra"),
        k(29, B(39.30 + dS), S_bulle[0], S_bulle[1], note="immobile ; secousse du vibreur 1100 → 1114 (pistes.secousses) ; version iPhone : part AVEC le téléphone (41,00, début de sa sortie ; le plan d'origine : « il quitte la bulle pendant que le téléphone s'en va »), l'iPhone restant opaque tant qu'il n'a pas bougé"),
        k(30, B(39.8000 + dS), stylo["x0"], SY, "power2.inOut", dict(MEP["s6"]["depart_stylo_arc"]), note="s7 : départ du stylo, sous la ligne de base (ligne de base + 32) ; version iPhone : le point part de plus bas (394 px au lieu de 182), sur 15 images (1230 → 1245) en power2.inOut : pointe ≈ 75 px par image (v2 ≈ 68), dernier pas < 1 px (v2 0,2) : il se pose sur le stylo avant d'écrire, sans coude. Arc {dx −30, dy +80} (relecture du 27/09 : en ligne droite, il montait plus vite que la bulle et glissait sur le SMS encore lisible, de 1234 à 1240) : il sort par la gauche SOUS la bulle qui monte, longe le bord gauche du téléphone qui s'efface (jamais au-delà de son contour) et remonte au stylo ; ≥ 11 px de la bulle et de sa queue tant que le téléphone est visible (contrôlé par s6-sms.html et controles.py F4)"),
        k(31, B(40.5000 + dS), stylo["x1"], SY, "sine.inOut", note="il écrit « Vokıo » (plume_mot) ; rond pendant l'écriture (etirement.sans)"),
        k(32, B(40.5833 + dS), stylo["x1"], SY, note="demi-image : il bouge déjà à l'image du la"),
        k(33, B(40.8333 + dS), M["x"], M["y"] - km(BOND), "power1.out", {"dx": km(40), "dy": km(-40)}, note="sommet du bond, image du sol (montée balistique)"),
        k(34, B(41.0000 + dS), M["x"], M["y"] - km(BOND + 4), "sine.inOut", note="suspension : il flotte encore de 4 px vers le haut"),
        k(35, B(41.2000 + dS), M["x"], M["y"], "power2.in", note="contact sur le ı, image du ré"),
        k(36, DUREE, M["x"], M["y"], note="tenue jusqu'à la fin"),
    ]
    for a, b in zip(pos, pos[1:]):
        assert b["t"] > a["t"], (a, b)
    n_re = img(B(41.20 + dS))
    ecr = {620: (1.14, 0.88), 621: (1.06, 0.95), 622: (1.02, 0.98),
           643: (1.16, 0.86), 644: (1.07, 0.94), 645: (1.02, 0.98),
           666: (1.12, 0.90), 667: (1.05, 0.96), 668: (1.01, 0.99),
           731: (1.08, 0.93), 732: (1.03, 0.97),
           n_re: (1.18, 0.84), n_re + 1: (1.07, 0.94), n_re + 2: (1.02, 0.98)}
    d_ne = round(0.81 * s1d, 3)          # contraction du décroché (17/21 en v2)
    croissance = [] if D_FILM == D else [{"t": demi(B(39.30 + dS)), "d": D_FILM},
                                         {"t": demi(B(39.80 + dS)), "d": D, "ease": "power2.inOut"}]
    tp0, tp1 = ACCROCHE["point"]
    tr = [t1.sortie(), t2.sortie()]
    return {
        "unite": "t en s film ; x, y = CENTRE du point en px film ; d = diamètre en px ; sx, sy sans unité ; rot en degrés",
        "lecture": "entre deux clés : de la clé i à la clé i+1 avec l'ease de la clé i+1 (gsap.parseEase, ou bezier(x1,y1,x2,y2) résolu par Newton) ; "
                   "arc {dx, dy} ajouté × 4p(1−p) ; avant la 1re / après la dernière : tenue ; pendant un trajet (pistes.trajets), "
                   "position = échantillons du trajet (une valeur par image, interpolée). Évaluer avec POINT.etat(t) (lib/point.js), jamais à la main.",
        "diametre_disque": max(D, D_FILM),
        **({} if D_FILM == D else {"diametre_film": D_FILM,
                                   "note_diametres": "diametre_disque = taille CSS de #point (la plus grande, 1:1 au repos sur le ı) ; "
                                                     "diametre_film = le disque de s1 à s6 (rayon des trajets et des gardes des scènes) ; "
                                                     "le point grandit de l'un à l'autre de 41,00 à 41,50 (DONNEES.point.taille)"}),
        "position": pos,
        "taille": [{"t": 0.0, "d": 0.0}, {"t": tp0, "d": 0.0}, {"t": tp1, "d": s1d, "ease": "power3.out"},
                   {"t": demi(4.1667), "d": s1d}, {"t": 4.20, "d": d_ne, "ease": "none"},
                   {"t": demi(4.2333), "d": d_ne}, {"t": 4.60, "d": D_FILM, "ease": "power3.out"}] + croissance,
        "couleur": [{"t": 0.0, "c": COULEURS["encre"]}, {"t": 4.20, "c": COULEURS["encre"]},
                    {"t": demi(4.2333), "c": COULEURS["solaire"], "ease": "none"}],
        "trajets": tr,
        "suiveur": {kk: v for kk, v in tr[0].items() if kk != "journal"} | {"definition": "alias v2 de trajets[0] (s2-s3)"},
        "pistes": {"trajets": [{"nom": t["nom"], "t0": t["t0"], "t1": t["t1"]} for t in tr],
                   "suiveur": {"t0": tr[0]["t0"], "t1": tr[0]["t1"], "source": "DONNEES.point.trajets[0]"},
                   "secousses": [{"piste": "s1", "t0": 0.0, "t1": round(138 / FPS, 6)},
                                 {"piste": "s6", "t0": round(BI(1100) / FPS, 6), "t1": round(BI(1114) / FPS, 6)}]},
        "ecrasements": {str(n): {"sx": a, "sy": b} for n, (a, b) in ecr.items()},
        "etirement": dict(ETIREMENT, sans=[[round(B(39.80 + dS), 6), round(B(40.50 + dS), 6)]],
                          definition="v = |pos(t + 1/60) − pos(t − 1/60)| en px PAR IMAGE (trajectoire sans secousse) ; si v > seuil et t hors "
                                     "des fenêtres « sans » : long = 1 + min(max ; (v − seuil)/pente), sx = long, sy = 1/√long, rot = atan2(vy, vx) ; "
                                     "sinon 1, 1, 0. max 0,25 : l'ellipse ne dépasse jamais 55 × 39 px. « sans » : l'écriture de « Vokıo » "
                                     "(plume_mot), le point y reste rond comme une plume. La table ecrasements (par image) est prioritaire, rot 0, centrée."),
        "reperes": {"P1": s1c, "A": {"x": XA, "y9": Y9, "y10": Y10, "y11": Y11},
                    "B": {"x0": BX0, "cy": BCY, "xf": BXF, "x_attente": C5["x_attente"], "y_levee": C5["y_levee"]},
                    "S": {"x": S_bulle[0], "y": S_bulle[1]}, "M": M,
                    "stylo": stylo},
    }


def evenements(mots, pt, pages, t2, agenda):
    """Plan D, finition du 27/09. Temps film ; image = round(t × 30). Les instants calés sur la voix sont vérifiés
    contre mots.json. Tout ce qui suit la lecture du SMS est décalé de DECALAGE_SMS (1,70 s), la tenue finale de
    DECALAGE_FIN (0,30 s) en plus. 28/09 : les instants en dur sont ceux du film de base, portés par B() ; ceux de
    l'échange du prénom viennent de choregraphie_s5() (film courant)."""
    syl = lire_json("mots.json")["syllabes"]["confirmation_derniere_syllabe"]
    dS, dF = DECALAGE_SMS, DECALAGE_SMS + DECALAGE_FIN
    j6 = {j["vers"]: j for j in t2.journal}
    C5 = choregraphie_s5(mots, agenda)
    n_fin = C5["n_fin"]
    ev = {
        # accroche, décroché et retour chariot
        "accroche": [ACCROCHE["debut"], ACCROCHE["lisible"]], "point_pose": ACCROCHE["point"],
        "decroche": 4.20, "lumiere": demi(4.2333), "anticipation": [demi(4.5667), demi(4.6333)],
        "suiveur": [demi(4.6333), 17.20],
        # écoute et agenda
        "tamis_fondu": [13.95, 14.20], "tamis_resserrage": [14.15, 14.50],
        "depart_agenda": 17.20, "arrivee_agenda": 17.80, "agenda_monte": [18.37, 19.07],
        "saut_neuf_envol": 613 / FPS, "saut_neuf_sommet": 616 / FPS, "contact_neuf": 620 / FPS,
        "saut_dix_envol": 635 / FPS, "saut_dix_sommet": 637 / FPS, "contact_dix": 643 / FPS,
        "saut_onze_envol": 658 / FPS, "saut_onze_sommet": 660 / FPS, "contact_onze": 666 / FPS,
        "retour_envol": 719 / FPS, "retour_sommet": 727 / FPS, "contact_retour_neuf": 731 / FPS,
        # rendez-vous : l'échange du prénom (choregraphie_s5, film courant), puis le film de base porté par B()
        "plume_pose": 761 / FPS, "ecriture_debut": 25.40, "heure_ecrite": C5["n_heure"] / FPS,
        "plume_levee": [C5["n_heure"] / FPS, C5["n_leve"] / FPS], "plume_suspendue": [C5["n_leve"] / FPS, C5["n_desc"] / FPS],
        "plume_reposee": [C5["n_desc"] / FPS, C5["t_pose"]], "ecriture_nom": [C5["t_pose"], n_fin / FPS],
        "ecriture_fin": n_fin / FPS, "suivi_bloc": [n_fin / FPS, (n_fin + 6) / FPS],
        "vers_gouttiere": [n_fin / FPS, C5["n_gouttiere"] / FPS], "signe_florian": B(27.35),
        "agenda_sort": [B(31.00), B(31.35)], "depart_gouttiere": t2.f0 / FPS,
        # SMS
        "voix_sms": [t2.f0 / FPS, j6["s6 « confirmation. »"]["arrivee"] / FPS],
        "resolution_confirmation": a_img(syl["voyelle"]),
        "depart_telephone": j6["s6 : sous la queue de la bulle, où le SMS naîtra"]["depart"] / FPS,
        "arrivee_bulle": t2.f / FPS,
        # FORMATS : un format peut faire monter le téléphone plus tard (mise-en-page/s6-sms.json « telephone_monte », variante
        # 16x9-centre : après le raccroché, le téléphone centré ne croise pas le dernier sous-titre) ; 9:16 : 35,10 → 35,60
        # (mise-en-page/*.json : temps du film COURANT, tels qu'on les voit ; le défaut, 35,10 → 35,60, est du film de base)
        "telephone_monte": list(MEP["s6"]["telephone_monte"]) if MEP["s6"].get("telephone_monte") else [B(35.10), B(35.60)],
        "raccroche": BI(1076) / FPS, "silence_numerique": [B(35.9467), BI(1100) / FPS],
        "bulle_et_vibreur": BI(1100) / FPS, "bulle_ouverte": BI(1114) / FPS, "telephone_sortie": [B(39.30 + dS), B(39.70 + dS)],
        "depart_stylo": B(39.30 + dS),
        # signature
        "plume_mot": [B(39.80 + dS), B(40.50 + dS)], "signature_la": B(40.60 + dS), "signature_sol": B(40.84 + dS),
        "signature_re_contact": B(41.20 + dS),
        "promesse": [B(41.80 + dS), B(42.00 + dS)], "offre": [B(42.70 + dS), B(42.80 + dS)],
        "silence_final": [B(44.70 + dF), B(45.00 + dF)], "fin": DUREE,
    }
    ev["saut_neuf_debut"], ev["saut_dix_debut"], ev["saut_onze_debut"] = ev["saut_neuf_envol"], ev["saut_dix_envol"], ev["saut_onze_envol"]
    ev["retour_debut"], ev["ecriture_pose"] = ev["retour_envol"], ev["plume_pose"]
    images_forcees = {"signe_florian": img(voyelle(mots, "A4", 6))}   # 27,35 × 30 = 820,5 : l'image est celle de la voyelle (27,355 → 821)
    out = {}
    for k, v in ev.items():
        if isinstance(v, list):
            out[k] = {"t": [round(x, 6) for x in v], "images": [img(x) for x in v]}
        else:
            out[k] = {"t": round(v, 6), "image": images_forcees.get(k, img(v))}
    # vérifications contre la voix et contre le plan : images du FILM DE BASE (47,00 s), portées par BI (un seul endroit) ;
    # celles de l'échange du prénom, nées de l'insertion, en images du film courant (ATTENDU_PRENOM)
    ATTENDU_BASE = {"decroche": 126, "lumiere": 127, "contact_neuf": 620, "contact_dix": 643, "contact_onze": 666,
                    "contact_retour_neuf": 731, "signe_florian": 821,
                    "resolution_confirmation": 989, "raccroche": 1076, "bulle_et_vibreur": 1100,
                    "signature_la": 1269, "signature_sol": 1276, "signature_re_contact": 1287, "fin": 1410}
    # la plume se pose et commence à écrire aux images du film de base (761, 762) : l'insertion part de l'image 758, mais
    # choregraphie_s5 garde ces deux gestes où ils étaient et écrit « 09:00 » sous « Très bien. »
    ATTENDU_PRENOM = {"plume_pose": 761, "ecriture_debut": 762, "heure_ecrite": 777, "ecriture_fin": 868}
    attendu = {k: BI(n) for k, n in ATTENDU_BASE.items()} | ATTENDU_PRENOM
    for k, n in attendu.items():
        assert out[k]["image"] == n, (k, out[k], n)
    assert out["plume_suspendue"]["images"] == [787, 842] and out["vers_gouttiere"]["images"] == [868, 886], (out["plume_suspendue"], out["vers_gouttiere"])
    assert out["silence_numerique"]["images"] == [BI(1078), BI(1100)] and out["telephone_sortie"]["images"] == [BI(1230), BI(1242)]
    assert out["depart_stylo"]["image"] == out["telephone_sortie"]["images"][0], "version iPhone : le point part avec le téléphone"
    assert out["plume_mot"]["images"] == [BI(1245), BI(1266)] and out["suiveur"]["images"] == [139, 516]
    # l'échange du prénom : la plume attend levée pendant la question, le nom s'écrit sous sa voix, le hochement le confirme
    ap = [w for w in mots if w["extrait"] == "AP"]
    fs = lire_json("mots.json")["syllabes"]
    assert out["plume_suspendue"]["t"][0] <= ap[5]["debut"] and out["plume_suspendue"]["t"][1] >= ap[5]["fin"], "la plume n'attend pas levée pendant « prénom ? »"
    assert abs(out["ecriture_nom"]["t"][0] - fs["florian_flo"]["debut"]) <= 1.5 / FPS, "« Florian » ne commence pas avec « Flo »"
    assert out["signe_florian"]["image"] > out["vers_gouttiere"]["images"][1], "le hochement précède le retour dans la gouttière"
    assert img(voyelle(mots, "A2A3", 6)) == 620 and img(voyelle(mots, "A2A3", 8)) == 643 and img(voyelle(mots, "A2A3", 11)) == 666
    assert img(mot(mots, "C3", 2)["debut"]) == 719, "le retour part sur le « à » de l'appelant"
    c4 = [w for w in mots if w["extrait"] == "C4"]
    assert c4[-1]["fin"] < out["raccroche"]["t"], "le raccroché doit suivre « Au revoir »"
    assert out["telephone_monte"]["t"][0] >= c4[-2]["debut"] - 0.05, "le téléphone n'entre qu'avec « Au revoir »"
    assert out["bulle_et_vibreur"]["t"] - out["telephone_monte"]["t"][1] <= 1.2 + 1e-9, "téléphone vide plus de 1,2 s avant la bulle"
    assert out["telephone_sortie"]["t"][0] - out["bulle_ouverte"]["t"] >= 3.8 - 1e-9, "bulle entière lisible moins de 3,8 s"
    assert abs((ev["signature_sol"] - ev["signature_la"]) - 0.24) < 1e-9 and abs((ev["signature_re_contact"] - ev["signature_la"]) - 0.60) < 1e-9
    a1 = [w for w in mots if w["extrait"] == "A1"]
    assert a1[-1]["fin"] <= 10.10, a1[-1]
    out["_note"] = ("Temps film ; image = round(t × 30), sauf signe_florian (image de la voyelle de « Florian » dite par l'agente : "
                    f"{out['signe_florian']['image']}). "
                    "Un bruitage de contact se pose à l'échantillon round(t × 48000). Intervalles : {t: [début, fin], images: [...]}. "
                    "Finition du 27/09 : le téléphone n'entre qu'avec « Au revoir » (vide 1,07 s avant la bulle), la bulle entière se lit "
                    f"{out['telephone_sortie']['t'][0] - out['bulle_ouverte']['t']:.2f} s ; tout ce qui suit est décalé de {DECALAGE_SMS} s, la tenue finale "
                    f"de {DECALAGE_FIN} s en plus (film de base de 47,00 s). 28/09, l'échange du prénom (son/dialogue.json « insertions ») : "
                    f"tout ce qui suit l'image 758 du film de base glisse de 92 images (film de {IMAGES / FPS:.6f} s, {IMAGES} images) ; "
                    "heure_ecrite, plume_levee, plume_suspendue, plume_reposee, ecriture_nom : le point écrit « 09:00 », attend le prénom plume "
                    "levée, puis écrit « Florian » sous la voix de l'appelant. Alias v1 gardés : saut_*_debut (= envol), retour_debut, ecriture_pose.")
    return out


def reperes(mots):
    """Les repères d'écoute (contrôle de synchro), avec leur mot."""
    def r(e, rang, nom):
        m = mot(mots, e, rang)
        return {"nom": nom, "extrait": e, "texte": m["texte"], "debut": m["debut"], "voyelle": m.get("voyelle"),
                "image": m["image"], "locuteur": m["locuteur"]}
    syl = lire_json("mots.json")["syllabes"]["confirmation_derniere_syllabe"]
    return [
        r("A1", 0, "Bonjour"), r("A2A3", 6, "neuf"), r("A2A3", 8, "dix"), r("A2A3", 11, "onze"),
        r("C3", 2, "à neuf (appelant)"), r("A4", 0, "Parfait"), r("A4", 6, "Florian"), r("A4", 12, "samedi"),
        r("A4", 18, "Vous recevrez"), r("A4", 21, "SMS"),
        {"nom": "dernière syllabe de confirmation", "extrait": "A4", "texte": "-tion", "debut": syl["debut"],
         "voyelle": syl["voyelle"], "image": img(syl["debut"]), "locuteur": "agent"},
        r("C4", 0, "Super"), r("C4", 3, "Au revoir"),
    ]


def geometrie_mise_en_page():
    """La part de DONNEES.geometrie qui ne dépend d'aucune mesure : le cadre et les boîtes CSS des scènes (s1, s7). Écrite
    AVANT les mesures (donnees.js provisoire) : s1 et s7 se posent d'après elle dans le banc de mesure."""
    s1, s7 = MEP["s1"], MEP["s7"]
    return {
        "cadre": {"format": FORMAT, "largeur": LARGEUR, "hauteur": HAUTEUR, "marge_laterale": MEP["format"]["marge_laterale"],
                  "haut_utile": MEP["format"]["haut_utile"], "bas_utile": MEP["format"]["bas_utile"], "corps_min": MEP["format"]["corps_min"]},
        "s1": {"phrase": dict(s1["phrase"]), "relance": dict(s1["relance"])},
        "s7": {"fin": dict(s7["fin"]), "promesse": dict(s7["promesse"]), "offre": dict(s7["offre"])},
    }


def donnees_provisoires():
    """donnees.js minimal pour le banc de mesure d'un projet neuf (formats/…) : les scènes s1 et s7 s'y montent sans
    erreur (DONNEES.scenes, mots, accroche, secousses, geometrie de mise en page) ; les sections calculées plus loin
    (point, événements, pages) manquent : s1 et s7 le savent (« complet » faux) et ne posent que leur géométrie."""
    dialogue = json.loads(DIALOGUE.read_text())
    mj = lire_json("mots.json")
    scenes = {}
    for sid, d, h in HOTES:
        fin = FINS_NOMINALES.get(sid, round(d + h, 6))
        scenes[sid] = {"debut": d, "fin": fin, "duree": round(fin - d, 4), "image_debut": img(d), "image_fin": img(fin),
                       "hote": f"h-{sid}", "hote_start": d, "hote_duration": h, "fichier": f"compositions/{sid}.html"}
    P = {"version": "provisoire (mesures en cours)", "fps": FPS, "duree": DUREE, "images": IMAGES, "taille": [LARGEUR, HAUTEUR],
         "format": MEP["format"], "couleurs": COULEURS, "scenes": scenes,
         "mots": [{k: w[k] for k in ("texte", "cle", "debut", "fin", "image", "locuteur", "extrait", "rang")}
                  | ({"voyelle": w["voyelle"]} if "voyelle" in w else {}) for w in mj["mots"]],
         "syllabes": mj["syllabes"], "secousses": secousses(), "accroche": ACCROCHE, "geometrie": geometrie_mise_en_page(),
         "insertions": TEMPS.liste,
         "dialogue": {"extraits": [{"id": e["id"]} for e in dialogue["extraits"]]}}
    (DON / "donnees.js").write_text("/* donnees/donnees.js PROVISOIRE (outils/construire.py, mesures en cours) */\nwindow.DONNEES = "
                                    + json.dumps(P, ensure_ascii=False, separators=(",", ":")) + ";\n")


def main():
    DON.mkdir(parents=True, exist_ok=True)
    if RACINE != PROJET or not (DON / "donnees.js").exists():
        donnees_provisoires()           # projet de format neuf : le banc de mesure a besoin de DONNEES.scenes et de la mise en page
    elif FORMAT == "9x16":
        pass                            # 9:16 : le banc mesure avec les données en place, exactement comme avant les formats
    # 1. géométrie mesurée dans Chromium (s1 : le « . » ; s7 : #mot-pt à 400 px)
    g = navigateur("geometrie")
    s7 = g["s7"]
    segs = s7["segments"]
    w_vok = segs["mot-a"]["boite"]["l"]
    w_o = segs["mot-o"]["boite"]["l"]
    stylo = {"x0": round(s7["mot"]["x0"] - 0.14 * w_vok - km(26), 3), "x1": round(s7["mot"]["x1"] + 0.14 * w_o + km(26), 3),
             "y": round(s7["ligne_de_base"] + km(32), 3),
             "definition": "x0 = bord gauche de #mot − 0,14 × largeur de « Vok » − 26 ; x1 = bord droit de #mot + 0,14 × largeur du « o » + 26 ; "
                           "y = ligne de base + 32 (le centre du point passe sous la ligne de base)"}
    mesures = {
        "unite": "px film ; mesuré dans le chrome-headless-shell de HyperFrames",
        "moteur": g["moteur"], "date": datetime.now().isoformat(timespec="seconds"),
        "s1": {"centre": g["s1"]["centre"], "diametre": g["s1"]["diametre"], "ligne_de_base": g["s1"]["ligne_de_base"],
               "lignes": g["s1"]["lignes"], "espaceur": g["s1"]["espaceur"], "glyphe_point": g["s1"]["glyphe_point"],
               "methode": g["s1"]["methode_centre"], "source": "compositions/s1-sonnerie.html #s1-espaceur"},
        "s7": {"centre": s7["centre"], "diametre": s7["diametre"], "mot_pt": s7["mot_pt"], "mot": s7["mot"],
               "segments": {k: {"x0": v["boite"]["x0"], "x1": v["boite"]["x1"], "largeur": v["boite"]["l"], "texte": v["texte"],
                                "encre_x0": round(v["encre_x0"], 3), "encre_x1": round(v["encre_x1"], 3)} for k, v in segs.items()},
               "ligne_de_base": s7["ligne_de_base"], "glyphe_i": s7["glyphe_i"], "stylo": stylo,
               "methode": s7["methode_centre"], "source": f"compositions/s7-signature.html #mot-pt (Instrument Serif {MEP['s7']['fin']['corps']} px, top {MEP['s7']['fin']['top']})"},
    }
    b_s2 = STYLES["s2_texte"]["lignes_de_base"][0]
    assert abs(mesures["s1"]["lignes"][1]["ligne_de_base"] - b_s2) < 0.51, (f"« mains prises. » doit rester sur la ligne de base {b_s2} (celle de s2) : "
                                                                          "mise-en-page/s1-sonnerie.json (top) ou texte.json (s2_texte)", mesures["s1"]["lignes"])
    assert abs(mesures["s1"]["lignes"][1]["x0"] - STYLES["s2_texte"]["x"]) < 0.51, ("l'accroche doit partir du x de s2", mesures["s1"]["lignes"])
    b7 = MEP["s7"]["fin"].get("ligne_de_base", 860 if FORMAT == "9x16" else None)
    assert b7 is None or abs(mesures["s7"]["ligne_de_base"] - b7) < 0.51, (f"s7 : ligne de base mesurée {mesures['s7']['ligne_de_base']} ≠ {b7} attendue "
                                                                          "(mise-en-page/s7-signature.json : top, ligne_de_base)")
    print(f"s1 : « . » en {mesures['s1']['centre']} ; s7 : ligne de base {mesures['s7']['ligne_de_base']}, #mot-pt en {mesures['s7']['centre']}")
    assert abs(mesures["s7"]["diametre"] - km(44)) < km(0.3), (mesures["s7"]["diametre"], km(44))
    ecrire_json("mesures.json", mesures)

    # 2. données de base (sans pages ni suiveur) : écrites une première fois pour le banc des pages
    dialogue = json.loads(DIALOGUE.read_text())      # commun à tous les formats
    assert dialogue.get("images", int(round(dialogue["duree_s"] * FPS))) == IMAGES and abs(dialogue["duree_s"] - IMAGES / FPS) < 1e-6, \
        f"son/dialogue.py doit être relancé ({IMAGES} images, {IMAGES / FPS:.6f} s)"
    poser_hotes()                                    # index.html : les hôtes du film courant (28/09, insertions de temps)
    mj = lire_json("mots.json")
    mots = mj["mots"]
    agenda = lire_json("agenda-geo.json")
    assert agenda.get("version") == 2 and agenda["echelle"] == 4.5, "outils/preparer_agenda.py v2 doit être relancé"
    assert agenda["image"]["x"] == MEP["agenda"]["x"] and agenda["image"]["y"] == MEP["agenda"]["y"], \
        f"{DON / 'agenda-geo.json'} n'est pas celui du format {FORMAT} : outils/preparer_agenda.py --format {FORMAT} --sortie …"
    sec = secousses()
    scenes = {}
    for sid, d, h in HOTES:
        fin = FINS_NOMINALES.get(sid, round(d + h, 6))
        scenes[sid] = {"debut": d, "fin": fin, "duree": round(fin - d, 4), "image_debut": img(d), "image_fin": img(fin),
                       "hote": f"h-{sid}", "hote_start": d, "hote_duration": h, "fichier": f"compositions/{sid}.html"}
    ecrire_json("styles-pages.json", STYLES)
    D = {
        "version": datetime.now().isoformat(timespec="seconds"),
        "film": "Le point sur le i", "revision": "v2", "fps": FPS, "duree": DUREE, "images": IMAGES,
        # 28/09 : la règle des insertions de temps (son/dialogue.json, outils/temps.py ; TEXTE.decaler côté scènes)
        "insertions": TEMPS.liste, "images_base": IMAGES_BASE, "duree_base": IMAGES_BASE / FPS,
        "taille": [LARGEUR, HAUTEUR], "couleurs": COULEURS,
        "scenes": scenes,
        "dialogue": {"fichier": "son/dialogue.wav", "conversation_id": dialogue["appel"]["conversation_id"],
                     "extraits": [{k: e[k] for k in ("id", "locuteur", "film_in", "film_out", "source_in", "source_out",
                                                     "original_in", "original_out", "texte")} | {"decalage": e["decalage_film_moins_source"]}
                                  | ({"decalage_base": e["decalage_base"]} if "decalage_base" in e else {})
                                  | ({"insertion": e["insertion"]} if e.get("insertion") else {})
                                  for e in dialogue["extraits"]]},
        "mots": [{k: w[k] for k in ("texte", "cle", "debut", "fin", "image", "locuteur", "extrait", "rang")}
                 | ({"voyelle": w["voyelle"]} if "voyelle" in w else {}) for w in mots],
        "syllabes": mj["syllabes"],
        "secousses": sec,
        "agenda": agenda,
        "mesures": {"s1": mesures["s1"], "s7": mesures["s7"]},
        "accroche": ACCROCHE,
        "format": MEP["format"] | ({"variantes": MEP["variantes"]} if MEP.get("variantes") else {}),
        "geometrie": geometrie_mise_en_page(),
    }

    def ecrire_js():
        entete = ("/* donnees/donnees.js · GÉNÉRÉ par outils/construire.py (" + D["version"] + ") · NE PAS ÉDITER À LA MAIN.\n"
                  f" * Source de vérité unique du film « Le point sur le i » (v2, finition ; échange du prénom : {IMAGES / FPS:.6f} s, {IMAGES} images). Temps en secondes FILM,\n"
                  " * positions en px film. Chargé en premier par index.html ; lu par lib/texte.js, lib/point.js et toutes les scènes. */\n")
        (DON / "donnees.js").write_text(entete + "window.DONNEES = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n")
    ecrire_js()

    # 3. les pages v2, posées par TEXTE.poser avec le CSS du contrat de leur scène (règle 8 + encre + ligne de base)
    # FORMATS (recomposition du 28/09) : les coupes de lignes propres au format (texte.json « coupes », mêmes mots)
    coupes = {k: v for k, v in (MEP["texte"].get("coupes") or {}).items()}
    if coupes:
        ecrire_json("coupes.json", coupes)
    elif (DON / "coupes.json").exists():
        (DON / "coupes.json").unlink()
    rp = navigateur("pages", str(DON / "styles-pages.json"), *([str(DON / "coupes.json")] if coupes else []))
    pg, decal = rp["pages"], rp["decalages"]
    for nom, css in STYLES.items():
        css["decalage_ligne_de_base"] = decal[nom]
        css["top"] = round(css["lignes_de_base"][0] - decal[nom], 3)
    err = []
    for p in pg:
        for il, (yb, yc) in enumerate(zip(p["lignes_de_base"], STYLES[p["style"]]["lignes_de_base"])):
            if abs(yb - yc) > 0.51:
                err.append(f"page {p['scene']} « {p['lignes'][il]} » : ligne de base {yb} ≠ {yc}")
        for il, l in enumerate(p["largeurs"]):
            w = l["x1"] - l["x0"]
            lim = LARGEUR_MAX_S2 if p["scene"] == "s2-voix" else LARGEUR_MAX
            if w > lim + 1e-6:
                err.append(f"page {p['scene']} « {p['lignes'][il]} » : {w:.1f} px > {lim}")
    D["pages"] = [{"scene": p["scene"], "extrait": p["extrait"], "depuis": p["depuis"], "lignes": p["lignes"], "style": p["style"],
                   "top": p["top"], "lignes_de_base": p["lignes_de_base"],
                   "largeurs": [{k: round(v, 3) for k, v in l.items()} | {"largeur": round(l["x1"] - l["x0"], 3)} for l in p["largeurs"]],
                   "mots": [{k: (round(m[k], 3) if isinstance(m[k], float) and k in ("x0", "x1", "encre_x0", "encre_x1", "ligne_de_base",
                                                                                    "encre_haut", "encre_bas") else m[k])
                             for k in ("texte", "ligne", "rang", "t", "image", "local", "revele", "fin_voix", "x0", "x1",
                                       "encre_x0", "encre_x1", "ligne_de_base", "encre_haut", "encre_bas")} for m in p["mots"]]} for p in pg]
    # Sorties des pages (s film, durée) : LUES par s2 et s6 (sortie = donnée), recopiées des scènes pour s3, s4 et s5
    # (le planificateur du point en a besoin ; controles.py vérifie sur le MP4 qu'aucune encre ne touche le point).
    # s2 : une page sort dès que la voix de son dernier mot s'est tue (première image après), en 0,15 s ; la dernière
    # de 10,10 à 10,30. Le point peut alors changer de page sans passer sous une lettre qui s'enfonce.
    rang = {}
    for p in D["pages"]:
        k = rang.get(p["scene"], 0); rang[p["scene"]] = k + 1
        p["cle"] = f"{p['scene']}#{k}"
    # 28/09 : repérées par (extrait, rang de départ), plus par leur rang dans la scène (l'échange du prénom ajoute deux pages en
    # tête de s5) ; instants du film de base portés par B(), ceux de l'échange en temps du film courant.
    par_page = {("C1", 0): (15.10, 0.18), ("C2", 1): (16.98, 0.18),
                ("A2A3", 0): (19.60, 5 / FPS), ("A2A3", 2): (23.10, 5 / FPS), ("C3", 2): (25.00, 5 / FPS),
                ("AP", 0): (SORTIE_QUESTION, 0.16), ("CP", 0): (SORTIE_REPONSE, 0.16),
                # (B() exact, sans arrondi au µs : 33,986667 + 0,18 = 1025,00001 images, et le planificateur partait à 1026)
                ("A4", 0): (B(27.64), 0.16), ("A4", 7): (B(29.20), 0.15), ("A4", 11): (B(30.92), 0.18),
                ("A4", 18): (B(33.70), 0.18), ("C4", 0): (round((BI(1076) - 0.5) / FPS, 6), 0.0)}
    sorties = {p["cle"]: par_page[(p["extrait"], p["depuis"])] for p in D["pages"] if (p["extrait"], p["depuis"]) in par_page}
    sans_sortie = [p["cle"] for p in D["pages"] if p["scene"] != "s2-voix" and p["cle"] not in sorties]
    assert not sans_sortie, f"pages sans sortie (par_page) : {sans_sortie}"
    s2p = [p for p in D["pages"] if p["scene"] == "s2-voix"]
    for i, p in enumerate(s2p):
        if i < len(s2p) - 1:
            fin_voix = p["mots"][-1]["fin_voix"]
            sorties[p["cle"]] = (round(math.ceil(fin_voix * FPS - 1e-6) / FPS, 6), 0.15)
        else:
            sorties[p["cle"]] = (10.10, 0.20)
    for p in D["pages"]:
        if p["scene"] in ("s2-voix", "s5-rendez-vous", "s6-sms"):
            t_, d_ = sorties[p["cle"]]
            p["sortie"] = {"t": t_, "duree": d_, "note": "début de la sortie par les masques (s film) et durée ; lu par la scène"}
    for p in D["pages"]:
        p["_cle"] = p["cle"]

    # 4. les trajets planifiés (s2-s3, s6) puis le point
    P1 = (mesures["s1"]["centre"]["x"], mesures["s1"]["centre"]["y"])
    # 3e passe du 16:9 : le glissement de l'accroche (mise-en-page/s1-sonnerie.json « glisse » : {"x_depart": "centre" | px,
    # "t": [t0, t1], "ease"}) ; « centre » : le bloc d'encre (lignes mesurées, « . » compris) centré dans le cadre au départ
    global GLISSE
    G_ = MEP["s1"].get("glisse")
    if G_:
        L_ = mesures["s1"]["lignes"]
        bx0 = min(l["x0"] for l in L_)
        bx1 = max(max(l["x1"] for l in L_), P1[0] + mesures["s1"]["diametre"] / 2)
        dxg = round((LARGEUR - (bx1 - bx0)) / 2 - bx0) if G_["x_depart"] == "centre" else round(G_["x_depart"] - MEP["s1"]["phrase"]["x"])
        t0g, t1g = (demi(v) for v in G_["t"])
        assert ACCROCHE["point"][1] <= t0g < t1g < 2.6667 - 1e-9, "s1 glisse : après la pose du « . » (0,9667), fini avant la relance (2,6667)"
        GLISSE = {"dx": dxg, "t": [t0g, t1g], "ease": G_.get("ease", "power3.inOut"),
                  "bloc_encre": [round(bx0, 1), round(bx1, 1)],
                  "note": "x(t) = x + dx × (1 − ease(u)), u = (t − t0)/(t1 − t0) borné à [0, 1] : #s1-phrase (s1-sonnerie.html) et le point (clés 1.1, 1.2)"}
    G6 = geometrie_iphone()
    S_bulle = (G6["point"]["x"], G6["point"]["y"])     # version iPhone : (168,99 ; 1282,93), 14 px sous la pointe de la queue
    t1, t2, boites = trajets(D["pages"], sorties, P1, STYLES["s3_texte"], agenda, S_bulle)
    for p in D["pages"]:
        p.pop("_cle", None)
    pt = point(mots, agenda, mesures, t1, t2, S_bulle)
    ev = evenements(mots, pt, D["pages"], t2, agenda)
    rep = reperes(mots)
    ST = STYLES
    geometrie = {
        "s2_texte": dict(ST["s2_texte"], largeur_max=LARGEUR_MAX_S2,
                         css=f"position:absolute; left:{ST['s2_texte']['x']}px; top:{ST['s2_texte']['top']}px; margin:0; font:400 {ST['s2_texte']['corps']}px/{ST['s2_texte']['interligne']}px \"Geist\"; letter-spacing:0; white-space:nowrap"),
        "s3_texte": dict(ST["s3_texte"], largeur_max=LARGEUR_MAX,
                         css=f"position:absolute; left:{ST['s3_texte']['x']}px; top:{ST['s3_texte']['top']}px; margin:0; font:italic 400 {ST['s3_texte']['corps']}px/{ST['s3_texte']['interligne']}px \"Instrument Serif\"; letter-spacing:0",
                         mention=dict(ST["mention"], texte="Appel réel sur une ligne de démonstration, raccourci.", couleur=COULEURS["gris"],
                                      largeur_max=MEP["texte"]["mention_largeur_max"])),
        "sous_titres_haut": {
            "agente": dict(ST["haut_agente"], css=f"position:absolute; left:{ST['haut_agente']['x']}px; top:{ST['haut_agente']['top']}px; font:400 {ST['haut_agente']['corps']}px/{ST['haut_agente']['interligne']}px \"Geist\""),
            "appelant": dict(ST["haut_appelant"], css=f"position:absolute; left:{ST['haut_appelant']['x']}px; top:{ST['haut_appelant']['top']}px; font:italic 400 {ST['haut_appelant']['corps']}px/{ST['haut_appelant']['interligne']}px \"Instrument Serif\""),
            "note": "s4, s5 et s6 ; l'agenda commence à y = 590 (image), son étiquette 09:00 à 641" if FORMAT == "9x16" else
                    f"s4, s5 et s6 ; l'agenda (image) en ({agenda['image']['x']} ; {agenda['image']['y']}), son filet 09:00 à {agenda['heures']['09:00']}"},
        "s6": G6,
        "s7": {"corps": MEP["s7"]["fin"]["corps"], "top": MEP["s7"]["fin"]["top"], "ligne_de_base": mesures["s7"]["ligne_de_base"], "stylo_y": stylo["y"],
               "stylo_x0": stylo["x0"], "stylo_x1": stylo["x1"], "mot": {"x0": s7["mot"]["x0"], "x1": s7["mot"]["x1"]},
               "segments": mesures["s7"]["segments"], "mot_pt_centre": mesures["s7"]["centre"], "diametre": mesures["s7"]["diametre"],
               "masque_depart": "inset(-30% 114% -30% -14%)", "masque_ouvert": "inset(-30% -14% -30% -14%)"},
        "agenda": {"image": {k: agenda["image"][k] for k in ("x", "y", "largeur", "hauteur", "droite_visible")},
                   "mention": dict(agenda["mention"], decalage_ligne_de_base=STYLES["mention"]["decalage_ligne_de_base"],
                                   top=round(agenda["mention"]["lignes_de_base"][0] - STYLES["mention"]["decalage_ligne_de_base"], 3),
                                   top_dans_l_objet=round(agenda["mention"]["lignes_de_base"][0] - STYLES["mention"]["decalage_ligne_de_base"] - agenda["image"]["y"], 3),
                                   left_dans_l_objet=agenda["mention"]["x"] - agenda["image"]["x"]),
                   "bloc": {k: agenda["bloc"][k] for k in ("x0", "y0", "y1", "centre_y", "hauteur", "texte_x1", "x_fin")},
                   "x_point": agenda["x_point"], "heures": {h: agenda["heures"][h] for h in ("09:00", "10:00", "11:00")},
                   "note": "détail complet dans DONNEES.agenda (agenda-geo.json v2) ; l'objet agenda (image + mention) est posé en (image.x ; image.y)"},
    }
    # FORMATS (27/09) : ce que les scènes lisaient en px en dur. Ajouts seulement : les clés ci-dessus ne changent pas.
    GM = geometrie_mise_en_page()
    geometrie["cadre"] = GM["cadre"]
    geometrie["s1"] = dict(GM["s1"], lignes_de_base=[l["ligne_de_base"] for l in mesures["s1"]["lignes"]],
                           note="boîtes CSS de #s1-phrase et #s1-relance (left = x, top, font-size = corps, line-height = interligne)")
    if GLISSE:
        geometrie["s1"]["glisse"] = GLISSE
    geometrie["s2_texte"]["x_max"] = X_MAX_POINT
    geometrie["sous_titres_haut"]["conteneur"] = {"largeur": MEP["texte"]["conteneur_sous_titres"][0],
                                                  "hauteur": MEP["texte"]["conteneur_sous_titres"][1],
                                                  "note": "boîte de #s4-texte, #s5-texte, #s6-texte en (0 ; 0)"}
    geometrie["s3_texte"]["ecoute"] = dict(ECOUTE)
    MA = MEP["agenda"]
    geometrie["agenda"].update({
        "boite": {"x": agenda["image"]["x"], "y": agenda["image"]["y"], "largeur": agenda["image"]["largeur"], "hauteur": MA["boite_hauteur"],
                  "note": "la boîte de l'objet (#s4-agenda, #s5-agenda) : image en (0 ; 0) dedans ; la mention en (left_dans_l_objet ; top_dans_l_objet), "
                          "négatif = au-dessus de l'image"},
        "y_depart": MA["y_depart"], "y_sortie": MA["y_sortie"], "haut_min": MA["haut_min"], "t_haut_min": MA["t_haut_min"]})
    geometrie["agenda"]["mention"].update({"corps": STYLES["mention"]["corps"], "interligne": STYLES["mention"]["interligne"],
                                          "couleur": COULEURS["gris"]})
    geometrie["s6"].update({"y_entree": MEP["s6"]["y_entree"], "y_sortie": MEP["s6"]["y_sortie"],
                            "depart_stylo_arc": dict(MEP["s6"]["depart_stylo_arc"])})
    geometrie["s7"].update(GM["s7"])
    # toutes les entrées de mise-en-page/*.json du format, telles quelles (clés libres des scènes : lues par leur composition)
    geometrie["mise_en_page"] = MEP["scenes"]
    D.update({"reperes": rep, "point": pt, "evenements": ev, "geometrie": geometrie})
    for nom, obj in (("secousses.json", sec), ("point.json", pt), ("scenes.json", scenes), ("evenements.json", ev),
                     ("reperes.json", rep), ("styles-pages.json", STYLES)):
        ecrire_json(nom, obj)
    ecrire_json("pages.json", {"unite": "t = attaque du 1er mot dit de l'unité (s film) ; revele = t arrondi à l'image − 1 image (instant du tween de révélation) ; "
                                        "local = t arrondi à l'image − début de la scène ; fin_voix = fin du dernier mot dit (s film) ; "
                                        "x0/x1 = boîte de l'unité (avance), encre_x0/encre_x1 = bords d'encre, ligne_de_base (px film)",
                               "note": "DÉRIVÉ de mots.json par TEXTE.poser (lib/texte.js), avec le CSS de DONNEES.geometrie : lecture seule.",
                               "pages": D["pages"]})
    ecrire_json("appel.json", {"note": "vue de son/dialogue.json + pages ; texte_dit = transcription d'origine, texte_montre = pages v2 posées par TEXTE.poser (sous-suites prouvées)",
                               "extraits": [dict({k: e[k] for k in ("id", "locuteur", "source", "source_in", "source_out", "original_in", "original_out",
                                                                    "film_in", "film_out", "motif")},
                                                 texte_dit=e["texte"],
                                                 texte_montre=[" / ".join(p["lignes"]) for p in D["pages"] if p["extrait"] == e["id"]])
                                            for e in dialogue["extraits"]]})
    vieux = DON / "voix-x.json"
    if vieux.exists():
        vieux.unlink()                                  # v2 : voixX supprimé (remplacé par le suiveur)
    ecrire_js()

    # 5. le point, résolu image par image par lib/point.js dans Chromium
    r = navigateur("resoudre", str(IMAGES))
    res = [{"image": k, "t": round(k / FPS, 6), "x": x, "y": y, "d": d, "couleur": c, "dx": dx, "dy": dy, "x_sans": xs, "y_sans": ys,
            "sx": sx, "sy": sy, "rot": rot, "v": v} for k, x, y, d, c, dx, dy, xs, ys, sx, sy, rot, v in r["images"]]
    ecrire_json("point-resolu.json", {"unite": "par image ; t en s film ; x, y centre dessiné en px (secousses comprises) ; x_sans, y_sans sans secousse ; "
                                               "d diamètre ; sx, sy, rot déformation ; v vitesse en px par image ; pan conseillé = 0,6 × (x − 540)/540",
                                      "moteur": r["moteur"], "images": res})

    # 6. contrôles bloquants (plan K, finition du 27/09)
    def ecart(a, b):
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))
    R = {e["image"]: e for e in res}
    assert len(res) == IMAGES + 1
    N_RE = ev["signature_re_contact"]["image"]
    e0 = ecart((R[0]["x_sans"], R[0]["y_sans"]), (P1[0] + (GLISSE["dx"] if GLISSE else 0), P1[1]))
    if e0 > 0.5: err.append(f"image 0 : écart {e0:.2f} px au point final de s1")
    n_pose = ev["point_pose"]["images"][1]
    if abs(R[n_pose]["d"] - mesures["s1"]["diametre"]) > 0.05 or R[0]["d"] > 1e-6:
        err.append(f"le point de s1 n'est pas invisible à l'image 0 et posé à l'image {n_pose} ({R[0]['d']} ; {R[n_pose]['d']})")
    M = (mesures["s7"]["centre"]["x"], mesures["s7"]["centre"]["y"])
    eRe = ecart((R[N_RE]["x"], R[N_RE]["y"]), M)
    if eRe > 0.5: err.append(f"image {N_RE} : écart {eRe:.2f} px à #mot-pt")
    for n in (N_RE, N_RE + 3):
        if abs(R[n]["d"] - km(44)) > km(0.3): err.append(f"image {n} : diamètre {R[n]['d']}")
    if not (R[N_RE + 3]["sx"] == 1 and R[N_RE + 3]["sy"] == 1): err.append(f"image {N_RE + 3} : déformation {R[N_RE + 3]['sx']} / {R[N_RE + 3]['sy']}")
    A = pt["reperes"]["A"]
    for n, yl in ((620, A["y9"]), (643, A["y10"]), (666, A["y11"]), (731, A["y9"])):
        if abs(R[n]["y"] - yl) > 0.5: err.append(f"contact {n} : y {R[n]['y']} ≠ {yl}")
    pas = [0.0] + [ecart((res[k]["x_sans"], res[k]["y_sans"]), (res[k - 1]["x_sans"], res[k - 1]["y_sans"])) for k in range(1, len(res))]
    for n, vmin in ((620, kp(10)), (643, kp(10)), (666, kp(10)), (N_RE, km(10)), (731, kp(5))):
        if pas[n] < vmin: err.append(f"contact {n} : dernier pas {pas[n]:.1f} px < {vmin}")
    for k in range(1, len(res)):
        lim = kv(150) if 137 <= k <= 150 else kv(130)
        if pas[k] > lim: err.append(f"pas de {pas[k]:.1f} px à l'image {k} (> {lim})")
    s0, s1_ = ev["silence_numerique"]["images"]
    for k in range(s0 + 1, s1_):
        if ecart((res[k]["x"], res[k]["y"]), (res[k - 1]["x"], res[k - 1]["y"])) >= 0.05:
            err.append(f"le point bouge à l'image {k} (silence numérique {s0}-{s1_ - 1})")
    if pas[516] >= 0.5: err.append(f"trajet s2-s3 non arrêté à 516 ({pas[516]:.3f} px)")
    # étirement plafonné : aucune ellipse au-delà de long = 1,25 ; rond pendant l'écriture du mot
    smax = max(e["sx"] for e in res if str(e["image"]) not in pt["ecrasements"])
    if smax > 1 + ETIREMENT["max"] + 1e-6: err.append(f"étirement {smax} > {1 + ETIREMENT['max']}")
    p0, p1_ = ev["plume_mot"]["images"]
    if any(R[n]["sx"] != 1 for n in range(p0, p1_ + 1)): err.append("le point s'étire pendant l'écriture de « Vokıo »")
    # aucune encre visible sous le point (positions RÉSOLUES par lib/point.js, boîtes d'encre des pages et leurs fenêtres)
    xs_all, ys_all = [e["x_sans"] for e in res], [e["y_sans"] for e in res]
    h_all = heurts(xs_all, ys_all, 0, boites, range(1, IMAGES))
    if h_all: err.append(f"le point touche une encre visible : {h_all[:6]} ({len(h_all)} images)")
    # à l'arrêt après un mot, écart ≥ ECART_MIN entre le bord du disque et l'encre du dernier mot révélé de sa ligne
    for T_ in (t1, t2):
        for j in T_.journal:
            if j["vers"].startswith(("s2 « ", "s6 « ", "retour chariot")):
                m_txt = j["vers"].split("« ")[1].rstrip(" »")
                mm = next(m for p in D["pages"] for m in p["mots"] if m["texte"] == m_txt and p["scene"] in ("s2-voix", "s6-sms"))
                g = j["a"][0] - R_DISQUE - mm["encre_x1"]
                if g < ECART_MIN - 0.01: err.append(f"« {m_txt} » : écart {g:.1f} px < {ECART_MIN}")
    # Nyquist : aucune alternance à 2 images (secousses et trajectoire)
    for axe in ("dx", "dy"):
        s = [p[axe] for p in res]
        for k in range(1, len(s)):
            if s[k] != 0 and s[k - 1] != 0 and np.sign(s[k]) == -np.sign(s[k - 1]):
                err.append(f"alternance à 2 images ({axe}) en {k}")
                break
    for axe in ("x_sans", "y_sans"):
        v = np.diff([p[axe] for p in res])
        for k in range(2, len(v)):
            if min(abs(v[k]), abs(v[k - 1]), abs(v[k - 2])) > 0.5 and np.sign(v[k]) == -np.sign(v[k - 1]) == np.sign(v[k - 2]):
                err.append(f"alternance à 2 images ({axe}) vers {k + 1}")
                break
    # FORMATS : le point reste dans le cadre, et ne s'arrête jamais (≥ 8 images immobiles) dans une zone interdite du format
    # (9:16 : l'interface Reels sous 1500 ; 16:9 : les 10 % du bas et le bouton « Passer l'annonce »)
    arret = 0
    for k, e in enumerate(res):
        r_ = e["d"] / 2 * max(e["sx"], e["sy"])
        if e["d"] > 0 and (e["x"] - r_ < 0 or e["x"] + r_ > LARGEUR or e["y"] - r_ < 0 or e["y"] + r_ > HAUTEUR):
            err.append(f"le point sort du cadre à l'image {k} ({e['x']:.0f} ; {e['y']:.0f})"); break
    for k, e in enumerate(res):
        arret = arret + 1 if k and pas[k] < 0.5 else 0
        if arret == 8 and e["d"] > 0:
            b = [e["x"] - e["d"] / 2, e["y"] - e["d"] / 2, e["x"] + e["d"] / 2, e["y"] + e["d"] / 2]
            z = mise_en_page.zones_touchees(MEP, b)
            if z:
                err.append(f"le point s'arrête à l'image {k - 7} en ({e['x']:.0f} ; {e['y']:.0f}) dans la zone « {z[0]} » ({FORMAT})")
    print(f"image 0 : ({R[0]['x']}, {R[0]['y']}) sans secousse ({R[0]['x_sans']}, {R[0]['y_sans']}), écart {e0:.3f} px, d {R[0]['d']}")
    print(f"image {N_RE} : ({R[N_RE]['x']}, {R[N_RE]['y']}) d {R[N_RE]['d']} sx/sy {R[N_RE]['sx']}/{R[N_RE]['sy']} (écart {eRe:.3f} px à #mot-pt {M})")
    # images du film de base (portées par BI), et celles de l'échange du prénom (film courant)
    for n in sorted({BI(k) for k in (0, 25, 27, 29, 126, 127, 137, 139, 141, 150, 516, 534, 613, 616, 619, 620, 643, 666, 730, 731,
                                     821, 933, 945, 962, 973, 1017, 1032, 1100, 1230, 1236, 1245, 1266, 1269, 1276, 1281)}
                    | {761, 762, 777, 787, 842, 848, 861, 868, 872, 886, N_RE - 1, N_RE, N_RE + 3, IMAGES - 1}):
        e = R[n]
        print(f"  {n:5d}  x {e['x']:8.2f}  y {e['y']:8.2f}  d {e['d']:6.2f}  {e['couleur']}  pas {pas[n]:6.1f}  sx/sy {e['sx']:.3f}/{e['sy']:.3f}  rot {e['rot']:7.1f}")
    print(f"pas max {max(pas):.1f} px (image {int(np.argmax(pas))}) ; hors 137-150 : {max(p for k, p in enumerate(pas) if not 137 <= k <= 150):.1f}")
    for T_ in (t1, t2):
        print(f"trajet {T_.nom} : images {T_.f0} → {T_.f}")
        for j in T_.journal:
            print(f"    {j['depart']:5d} → {j['arrivee']:5d}  {j['forme']:8s} pas max {j['pas_max']:6.1f}  {j['vers']}")
    print("\n".join("⚠ " + e for e in err) or "contrôles : ok")
    print(f"→ {DON / 'donnees.js'} ({(DON / 'donnees.js').stat().st_size} o)")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
