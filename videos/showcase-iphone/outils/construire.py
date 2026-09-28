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
"""
import argparse
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mise_en_page  # noqa: E402

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
DON = RACINE / "donnees"              # sorties (le format)
ENTREES = Path(ARGS.entrees).resolve() if ARGS.entrees else PROJET
SRC = ENTREES / "donnees"             # entrées communes à tous les formats (mots.json)
DIALOGUE = ENTREES / "son" / "dialogue.json"
PW = "/root/.pwtest/bin/python"
FPS = 30
DUREE = 47.0
IMAGES = int(round(DUREE * FPS))   # 1410 images : 0 … 1409 ; l'instant 47,00 = fin
# Finition du 27/09 (arbitrages du réalisateur) : le SMS se lit (bulle entière ≥ 3,8 s) et la fin ne rogne rien :
# +1,70 s à partir de la descente du téléphone (39,30 → 41,00) et +0,30 s de tenue finale, soit 45,00 → 47,00.
DECALAGE_SMS = 1.70
DECALAGE_FIN = 0.30
SR = 48000

COULEURS = {"papier": "#F4F1E8", "encre": "#262019", "solaire": "#EFA424", "terracotta": "#C0452C",
            "vert": "#6E9C74", "gris": "#6F695F", "bulle": "#E9E3D6"}

# id, début, durée de l'hôte (data-start / data-duration de index.html, à l'identique)
HOTES = [("s1-sonnerie", 0.0, 4.6333), ("s2-voix", 4.6333, 5.7667), ("s3-ecoute", 10.40, 6.90),
         ("s4-agenda", 17.30, 7.8999), ("s5-rendez-vous", 25.20, 6.15), ("s6-sms", 31.35, 10.0499),
         ("s7-signature", 41.40, 5.60)]
# s4 : 7,8999 et non 7,9 (en flottant, 17,3 + 7,9 = 25,200000000000003 : l'hôte de s4 restait monté à l'image 756).
# s6 : 10,0499 et non 10,05, même raison (31,35 + 10,05 = 41,400000000000006). Fins NOMINALES : 25,20 et 41,40.
FINS_NOMINALES = {"s4-agenda": 25.20, "s6-sms": 41.40}

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
R_DISQUE = 22.0
ECART_MIN = 18.0
MARGE_ENCRE = 2.0         # distance minimale disque → boîte d'encre d'un mot visible
V_TRAJET = 100.0
V_CALME = 60.0            # préféré : le point quitte le mot plus tôt plutôt que de filer
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
    # s1 (plan E) : tonalité 440 Hz, 1,5 s on (0 → 1,5) puis 2e sonnerie 2,7 → 4,2 ; fondus de 10 ms ; à 4,2 la
    # 2e tonalité ne coupe pas (elle s'ouvre en cloche) : pas de rampe de sortie, le tremblement s'arrête net et
    # l'enveloppe est forcée à 0 dès l'image 126 (décroché). 139 valeurs : images 0 à 138.
    s1_seg = [(0.0, 1.5, 0.010, 0.010), (2.7, 4.2, 0.010, 0.0)]
    env1 = enveloppe_par_image(s1_seg, 0, 139)
    env1 = [0.0 if k >= 126 else v for k, v in enumerate(env1)]
    # s6 (plan E) : vibreur, deux impulsions de 180 ms séparées de 90 ms, la 1re à l'image 1100 exactement
    v0 = 1100 / FPS
    s6_seg = [(v0, v0 + 0.18, 0.012, 0.025), (v0 + 0.27, v0 + 0.45, 0.012, 0.025)]
    env6 = enveloppe_par_image(s6_seg, 1100, 15)
    return {
        "unite": "enveloppe 0 → 1 par image (moyenne sur l'image) ; dx = amplitude_x × enveloppe × motif_x ; dy = amplitude_y × enveloppe × motif_y",
        "s1": {"description": "tonalité d'attente 440 Hz (ton-1 0 → 1,5 s ; ton-2 2,7 → 4,2 s), attaques et relâche de ton-1 10 ms, "
                              "ton-2 sans relâche (il devient cloche) ; 0 dès l'image 126 (décroché)",
               "image0": 0, "enveloppe": env1,
               "amplitude_x": 6.0, "motif_x": [0, 1, 0, -1], "amplitude_y": 2.0, "motif_y": [1, 0, -1, 0],
               "amplitude_px": 6.0, "motif": [0, 1, 0, -1],
               "phase_par_image_absolue": True,
               "segments_s": [[a, b] for a, b, _, _ in s1_seg], "rampes_s": [[fa, fr] for _, _, fa, fr in s1_seg],
               "frequence_hz": 7.5,
               "note": "motif de 4 images = 7,5 Hz, sous Nyquist ; x(n) = 6·env(n)·[0,+1,0,−1][n mod 4], y(n) = 2·env(n)·[+1,0,−1,0][n mod 4] : "
                       "quadrature, le point décrit un losange ; amplitude_px / motif = alias v1 de l'axe x"},
        "s6": {"description": "vibreur du SMS : impulsions 36,6667 → 36,8467 et 36,9367 → 37,1167 s, attaque 12 ms, relâche 25 ms",
               "image0": 1100, "enveloppe": env6,
               "amplitude_x": 6.0, "motif_x": [1, 0, -1, 0], "amplitude_px": 6.0, "motif": [1, 0, -1, 0],
               "phase_par_image_absolue": False,
               "segments_s": [[round(a, 6), round(b, 6)] for a, b, _, _ in s6_seg], "rampes_s": [[fa, fr] for _, _, fa, fr in s6_seg],
               "frequence_hz": 7.5,
               "note": "x(n) = 6·env·[+1,0,−1,0][(n−1100) mod 4] ; le téléphone de s6 ET #point lisent la même valeur (POINT.secousse('s6', t))"},
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
}


def mouvement(A, B, forme):
    F = FORMES[forme]
    (x0, x1, ex), (y0, y1, ey) = F["x"], F["y"]
    fx, fy = ease(ex), ease(ey)

    def f(u):
        ux = cadre((u - x0) / (x1 - x0))
        uy = cadre((u - y0) / (y1 - y0))
        return (A[0] + (B[0] - A[0]) * fx(ux), A[1] + (B[1] - A[1]) * fy(uy))
    return f


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
    """T1 : s2 et s3 (images 139 → 516) ; T2 : s6, de la gouttière des heures à la bulle (images 933 → 1032)."""
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
            t1.aller(B, vis, forme, libre, n_min=n_min, raison=f"retour chariot, puis s2 « {m['texte']} »", v_max=140.0)
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
    for (ta, tb, dy, raison) in ((14.15, 14.30, 8.0, "tamis : hochement (bas)"), (14.30, 14.50, 0.0, "tamis : hochement (retour)"),
                                 (16.19, 16.49, -10.0, "hausse sur « disponibilités »")):
        t1.tenir(img(ta))
        t1.aller((L[0], L[1] + dy), img(tb), "droit", img(ta), n_min=img(tb) - img(ta), raison=raison)
    t1.tenir(516)
    # ── T2 ──
    XA, Y9 = agenda["x_point"], agenda["heures"]["09:00"]
    so5 = sorties[[p["_cle"] for p in pages if p["scene"] == "s5-rendez-vous"][-1]]
    f_gout = int(math.ceil((so5[0] + so5[1]) * FPS - 1e-6))          # 933 : le dernier sous-titre de s5 est sorti
    # FORMATS : en 16:9 le sous-titre n'est plus sur le chemin (il est à gauche, l'agenda à droite) : le point peut quitter la
    # gouttière plus tôt pour un geste plus calme (mise-en-page/s6-sms.json « depart_gouttiere_avance », images ; 9:16 : 0)
    f_gout -= int(MEP["s6"].get("depart_gouttiere_avance", 0))
    t2 = Trajet("s6", f_gout, (XA, Y9), boites)
    pa = [p for p in pages if p["scene"] == "s6-sms"][0]
    arrets6 = [m for m in pa["mots"] if m["texte"] in ARRETS_S6]
    assert [m["texte"] for m in arrets6] == ARRETS_S6
    prec = None
    for m in arrets6:
        B, vis = fin_mot(m), img(m["revele"]) + 1
        forme = "droit" if prec is None or prec["ligne"] == m["ligne"] else "descente"
        t2.aller(B, vis, forme, f_gout, n_min=6, raison=f"s6 « {m['texte']} »")
        prec = m
    so6 = sorties[pa["_cle"]]
    libre = int(math.ceil((so6[0] + so6[1]) * FPS - 1e-6))
    t2.aller(S_bulle, libre + 20, "droit", libre, n_min=20, raison="s6 : sous la queue de la bulle, où le SMS naîtra")
    return t1, t2, boites


ETIREMENT = {"seuil": 30, "pente": 90, "max": 0.25}   # long ≤ 1,25 (arbitrage 2 : plus de pilule de 92 px)


def point(mots, agenda, mesures, t1, t2, S_bulle):
    s1c, s1d = mesures["s1"]["centre"], mesures["s1"]["diametre"]
    M, D = mesures["s7"]["centre"], mesures["s7"]["diametre"]
    stylo = mesures["s7"]["stylo"]
    XA = agenda["x_point"]
    H = agenda["heures"]
    Y9, Y10, Y11 = H["09:00"], H["10:00"], H["11:00"]
    bloc = agenda["bloc"]
    BX0 = round(bloc["x0"] + D / 2, 3)
    BCY = bloc["centre_y"]
    BXF = bloc["x_fin"]
    SY = stylo["y"]
    P1x, P1y = s1c["x"], s1c["y"]
    dS = DECALAGE_SMS
    k = lambda n, t, x, y, ease=None, arc=None, note=None: {kk: v for kk, v in (
        ("n", n), ("t", demi(t)), ("image", round(demi(t) * FPS, 1)), ("x", round(x, 3)), ("y", round(y, 3)),
        ("ease", ease), ("arc", arc), ("note", note)) if v is not None}
    e1 = (t1.xs[-1], t1.ys[-1])
    pos = [
        k(1, 0.0, P1x, P1y, note="s1 : point final de « mains prises. » (mesuré) ; invisible (0 px) jusqu'à 0,8333, posé à 0,9667 (DONNEES.accroche.point), encre ; tremble avec la tonalité"),
        k(2, 4.5667, P1x, P1y, note="décroché à 126 (contraction), solaire à 127, gonfle jusqu'à 44 px à 4,60"),
        k(3, 4.6333, P1x + 10, P1y, "power2.out", note="anticipation : recul de 10 px vers la droite (137 → 139)"),
        k(4, 17.20, e1[0], e1[1], note="fin du trajet planifié s2-s3 (pistes.trajets[0], images 139 → 516)"),
        k(5, 17.80, XA, Y9, "bezier(.45,0,.15,1)", note="s4 : attend sur la ligne 09:00 (l'agenda monte dessous 18,37 → 19,07)"),
        k(6, 20.4333, XA, Y9, note="« neuf » : envol 613"),
        k(7, 20.5333, XA, Y9 - 36, "power2.out", note="sommet 616"),
        k(8, 20.6667, XA, Y9, "power2.in", note="contact 09:00, image 620 (voyelle de « neuf »)"),
        k(9, 21.1667, XA, Y9, note="« dix » : envol 635"),
        k(10, 21.2333, XA + 12, Y9 - 20, "power2.out", note="sommet 637, côté colonne (loin de l'encre de « 09:00 »)"),
        k(11, 21.4333, XA, Y10, "power2.in", {"dx": 14}, note="contact 10:00, image 643 (voyelle de « dix »)"),
        k(12, 21.9333, XA, Y10, note="« onze » : envol 658"),
        k(13, 22.0000, XA + 8, Y10 - 14, "power2.out", note="sommet 660, côté colonne"),
        k(14, 22.2000, XA, Y11, "power2.in", {"dx": 10}, note="contact 11:00, image 666 (voyelle de « onze »)"),
        k(15, 23.9667, XA, Y11, note="retour : envol 719 (« à » de l'appelant)"),
        k(16, 24.2333, XA, Y9 - 20, "bezier(.4,0,.4,1)", {"dx": 24}, note="sommet 727, en arc côté colonne"),
        k(17, 24.3667, XA, Y9, "power2.in", note="contact retour 09:00, image 731"),
        k(18, 25.2000, XA, Y9, note="s5"),
        k(19, 25.3667, BX0, BCY, "power2.inOut", note="plume posée au bord gauche du bloc (761)"),
        k(20, 25.3833, BX0, BCY, note="demi-image : le départ a une vitesse non nulle, le point bouge dès l'image 762 (le la)"),
        k(21, 26.1000, BXF, BCY, "power1.out", note="il écrit « 09:00 Florian » et s'arrête 14 px après l'encre de « Florian » (783)"),
        # arbitrage 5 : sitôt l'écriture finie, le point quitte le bloc (il ne reste pas collé à « Florian » comme une
        # pastille) : il lève la plume au-dessus du bloc, puis rejoint la gouttière des heures, aligné sur 09:00
        k(22, 787 / FPS, BXF, BCY - 60, "power2.out", note="lève la plume : 60 px au-dessus de la ligne du bloc (787), au-dessus de l'encre du bloc"),
        k(23, 801 / FPS, XA, Y9, "sine.inOut", note="dans la gouttière des heures, sur la ligne 09:00, là où il frappait les heures (801)"),
        k(24, 27.2500, XA, Y9),
        k(25, 821 / FPS, XA, Y9 + 6, "power2.in", note="hochement de 6 px sur la voyelle de « Florian » (27,355 → image 821), dans la gouttière"),
        k(26, 27.4833, XA, Y9, "power2.out"),
        k(27, t2.f0 / FPS, XA, Y9, note=f"il attend dans la gouttière jusqu'à la sortie du dernier sous-titre de s5 (image {t2.f0}) ; trajet s6 ensuite"),
        k(28, t2.f / FPS, S_bulle[0], S_bulle[1], note="fin du trajet s6 (pistes.trajets[1]) : sous la queue de la bulle, d'où le SMS naîtra"),
        k(29, 39.30 + dS, S_bulle[0], S_bulle[1], note="immobile ; secousse du vibreur 1100 → 1114 (pistes.secousses) ; version iPhone : part AVEC le téléphone (41,00, début de sa sortie ; le plan d'origine : « il quitte la bulle pendant que le téléphone s'en va »), l'iPhone restant opaque tant qu'il n'a pas bougé"),
        k(30, 39.8000 + dS, stylo["x0"], SY, "power2.inOut", dict(MEP["s6"]["depart_stylo_arc"]), note="s7 : départ du stylo, sous la ligne de base (ligne de base + 32) ; version iPhone : le point part de plus bas (394 px au lieu de 182), sur 15 images (1230 → 1245) en power2.inOut : pointe ≈ 75 px par image (v2 ≈ 68), dernier pas < 1 px (v2 0,2) : il se pose sur le stylo avant d'écrire, sans coude. Arc {dx −30, dy +80} (relecture du 27/09 : en ligne droite, il montait plus vite que la bulle et glissait sur le SMS encore lisible, de 1234 à 1240) : il sort par la gauche SOUS la bulle qui monte, longe le bord gauche du téléphone qui s'efface (jamais au-delà de son contour) et remonte au stylo ; ≥ 11 px de la bulle et de sa queue tant que le téléphone est visible (contrôlé par s6-sms.html et controles.py F4)"),
        k(31, 40.5000 + dS, stylo["x1"], SY, "sine.inOut", note="il écrit « Vokıo » (plume_mot) ; rond pendant l'écriture (etirement.sans)"),
        k(32, 40.5833 + dS, stylo["x1"], SY, note="demi-image : il bouge déjà à l'image du la"),
        k(33, 40.8333 + dS, M["x"], M["y"] - 110, "power1.out", {"dx": 40, "dy": -40}, note="sommet du bond, image du sol (montée balistique)"),
        k(34, 41.0000 + dS, M["x"], M["y"] - 114, "sine.inOut", note="suspension : il flotte encore de 4 px vers le haut"),
        k(35, 41.2000 + dS, M["x"], M["y"], "power2.in", note="contact sur le ı, image du ré"),
        k(36, DUREE, M["x"], M["y"], note="tenue jusqu'à la fin"),
    ]
    for a, b in zip(pos, pos[1:]):
        assert b["t"] > a["t"], (a, b)
    n_re = img(41.20 + dS)
    ecr = {620: (1.14, 0.88), 621: (1.06, 0.95), 622: (1.02, 0.98),
           643: (1.16, 0.86), 644: (1.07, 0.94), 645: (1.02, 0.98),
           666: (1.12, 0.90), 667: (1.05, 0.96), 668: (1.01, 0.99),
           731: (1.08, 0.93), 732: (1.03, 0.97),
           n_re: (1.18, 0.84), n_re + 1: (1.07, 0.94), n_re + 2: (1.02, 0.98)}
    d_ne = round(0.81 * s1d, 3)          # contraction du décroché (17/21 en v2)
    tp0, tp1 = ACCROCHE["point"]
    tr = [t1.sortie(), t2.sortie()]
    return {
        "unite": "t en s film ; x, y = CENTRE du point en px film ; d = diamètre en px ; sx, sy sans unité ; rot en degrés",
        "lecture": "entre deux clés : de la clé i à la clé i+1 avec l'ease de la clé i+1 (gsap.parseEase, ou bezier(x1,y1,x2,y2) résolu par Newton) ; "
                   "arc {dx, dy} ajouté × 4p(1−p) ; avant la 1re / après la dernière : tenue ; pendant un trajet (pistes.trajets), "
                   "position = échantillons du trajet (une valeur par image, interpolée). Évaluer avec POINT.etat(t) (lib/point.js), jamais à la main.",
        "diametre_disque": D,
        "position": pos,
        "taille": [{"t": 0.0, "d": 0.0}, {"t": tp0, "d": 0.0}, {"t": tp1, "d": s1d, "ease": "power3.out"},
                   {"t": demi(4.1667), "d": s1d}, {"t": 4.20, "d": d_ne, "ease": "none"},
                   {"t": demi(4.2333), "d": d_ne}, {"t": 4.60, "d": D, "ease": "power3.out"}],
        "couleur": [{"t": 0.0, "c": COULEURS["encre"]}, {"t": 4.20, "c": COULEURS["encre"]},
                    {"t": demi(4.2333), "c": COULEURS["solaire"], "ease": "none"}],
        "trajets": tr,
        "suiveur": {kk: v for kk, v in tr[0].items() if kk != "journal"} | {"definition": "alias v2 de trajets[0] (s2-s3)"},
        "pistes": {"trajets": [{"nom": t["nom"], "t0": t["t0"], "t1": t["t1"]} for t in tr],
                   "suiveur": {"t0": tr[0]["t0"], "t1": tr[0]["t1"], "source": "DONNEES.point.trajets[0]"},
                   "secousses": [{"piste": "s1", "t0": 0.0, "t1": round(138 / FPS, 6)},
                                 {"piste": "s6", "t0": round(1100 / FPS, 6), "t1": round(1114 / FPS, 6)}]},
        "ecrasements": {str(n): {"sx": a, "sy": b} for n, (a, b) in ecr.items()},
        "etirement": dict(ETIREMENT, sans=[[round(39.80 + dS, 6), round(40.50 + dS, 6)]],
                          definition="v = |pos(t + 1/60) − pos(t − 1/60)| en px PAR IMAGE (trajectoire sans secousse) ; si v > seuil et t hors "
                                     "des fenêtres « sans » : long = 1 + min(max ; (v − seuil)/pente), sx = long, sy = 1/√long, rot = atan2(vy, vx) ; "
                                     "sinon 1, 1, 0. max 0,25 : l'ellipse ne dépasse jamais 55 × 39 px. « sans » : l'écriture de « Vokıo » "
                                     "(plume_mot), le point y reste rond comme une plume. La table ecrasements (par image) est prioritaire, rot 0, centrée."),
        "reperes": {"P1": s1c, "A": {"x": XA, "y9": Y9, "y10": Y10, "y11": Y11},
                    "B": {"x0": BX0, "cy": BCY, "xf": BXF}, "S": {"x": S_bulle[0], "y": S_bulle[1]}, "M": M,
                    "stylo": stylo},
    }


def evenements(mots, pt, pages, t2):
    """Plan D, finition du 27/09. Temps film ; image = round(t × 30). Les instants calés sur la voix sont vérifiés
    contre mots.json. Tout ce qui suit la lecture du SMS est décalé de DECALAGE_SMS (1,70 s), la tenue finale de
    DECALAGE_FIN (0,30 s) en plus."""
    syl = lire_json("mots.json")["syllabes"]["confirmation_derniere_syllabe"]
    dS, dF = DECALAGE_SMS, DECALAGE_SMS + DECALAGE_FIN
    j6 = {j["vers"]: j for j in t2.journal}
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
        # rendez-vous
        "plume_pose": 761 / FPS, "ecriture_debut": 25.40, "ecriture_fin": 26.10, "suivi_bloc": [783 / FPS, 789 / FPS],
        "vers_gouttiere": [783 / FPS, 801 / FPS], "signe_florian": 27.35,
        "agenda_sort": [31.00, 31.35], "depart_gouttiere": t2.f0 / FPS,
        # SMS
        "voix_sms": [t2.f0 / FPS, j6["s6 « confirmation. »"]["arrivee"] / FPS],
        "resolution_confirmation": a_img(syl["voyelle"]),
        "depart_telephone": j6["s6 : sous la queue de la bulle, où le SMS naîtra"]["depart"] / FPS,
        "arrivee_bulle": t2.f / FPS,
        # FORMATS : un format peut faire monter le téléphone plus tard (mise-en-page/s6-sms.json « telephone_monte », variante
        # 16x9-centre : après le raccroché, le téléphone centré ne croise pas le dernier sous-titre) ; 9:16 : 35,10 → 35,60
        "telephone_monte": list(MEP["s6"].get("telephone_monte", [35.10, 35.60])),
        "raccroche": 1076 / FPS, "silence_numerique": [35.9467, 1100 / FPS],
        "bulle_et_vibreur": 1100 / FPS, "bulle_ouverte": 1114 / FPS, "telephone_sortie": [39.30 + dS, 39.70 + dS],
        "depart_stylo": 39.30 + dS,
        # signature
        "plume_mot": [39.80 + dS, 40.50 + dS], "signature_la": 40.60 + dS, "signature_sol": 40.84 + dS, "signature_re_contact": 41.20 + dS,
        "promesse": [41.80 + dS, 42.00 + dS], "offre": [42.70 + dS, 42.80 + dS], "silence_final": [44.70 + dF, 45.00 + dF], "fin": DUREE,
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
    # vérifications contre la voix et contre le plan
    attendu = {"decroche": 126, "lumiere": 127, "contact_neuf": 620, "contact_dix": 643, "contact_onze": 666, "contact_retour_neuf": 731,
               "plume_pose": 761, "ecriture_debut": 762, "ecriture_fin": 783, "signe_florian": 821,
               "resolution_confirmation": 989, "raccroche": 1076, "bulle_et_vibreur": 1100,
               "signature_la": 1269, "signature_sol": 1276, "signature_re_contact": 1287, "fin": 1410}
    for k, n in attendu.items():
        assert out[k]["image"] == n, (k, out[k], n)
    assert out["silence_numerique"]["images"] == [1078, 1100] and out["telephone_sortie"]["images"] == [1230, 1242]
    assert out["depart_stylo"]["image"] == out["telephone_sortie"]["images"][0], "version iPhone : le point part avec le téléphone"
    assert out["plume_mot"]["images"] == [1245, 1266] and out["suiveur"]["images"] == [139, 516]
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
    out["_note"] = ("Temps film ; image = round(t × 30), sauf signe_florian (27,35 = image 820,5 : image de la voyelle de « Florian », 821). "
                    "Un bruitage de contact se pose à l'échantillon round(t × 48000). Intervalles : {t: [début, fin], images: [...]}. "
                    "Finition du 27/09 : le téléphone n'entre qu'avec « Au revoir » (vide 1,07 s avant la bulle), la bulle entière se lit "
                    f"{out['telephone_sortie']['t'][0] - out['bulle_ouverte']['t']:.2f} s ; tout ce qui suit est décalé de {DECALAGE_SMS} s, la tenue finale "
                    f"de {DECALAGE_FIN} s en plus (film de 47,00 s). Alias v1 gardés : saut_*_debut (= envol), retour_debut, ecriture_pose.")
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
    stylo = {"x0": round(s7["mot"]["x0"] - 0.14 * w_vok - 26, 3), "x1": round(s7["mot"]["x1"] + 0.14 * w_o + 26, 3),
             "y": round(s7["ligne_de_base"] + 32, 3),
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
    assert abs(mesures["s7"]["diametre"] - 44) < 0.3, mesures["s7"]["diametre"]
    ecrire_json("mesures.json", mesures)

    # 2. données de base (sans pages ni suiveur) : écrites une première fois pour le banc des pages
    dialogue = json.loads(DIALOGUE.read_text())      # commun à tous les formats
    assert abs(dialogue["duree_s"] - DUREE) < 1e-9, f"son/dialogue.py doit être relancé ({DUREE:.2f} s)"
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
        "taille": [LARGEUR, HAUTEUR], "couleurs": COULEURS,
        "scenes": scenes,
        "dialogue": {"fichier": "son/dialogue.wav", "conversation_id": dialogue["appel"]["conversation_id"],
                     "extraits": [{k: e[k] for k in ("id", "locuteur", "film_in", "film_out", "source_in", "source_out",
                                                     "original_in", "original_out", "texte")} | {"decalage": e["decalage_film_moins_source"]}
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
                  " * Source de vérité unique du film « Le point sur le i » (v2, finition : 47,00 s, 1 410 images). Temps en secondes FILM,\n"
                  " * positions en px film. Chargé en premier par index.html ; lu par lib/texte.js, lib/point.js et toutes les scènes. */\n")
        (DON / "donnees.js").write_text(entete + "window.DONNEES = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n")
    ecrire_js()

    # 3. les pages v2, posées par TEXTE.poser avec le CSS du contrat de leur scène (règle 8 + encre + ligne de base)
    rp = navigateur("pages", str(DON / "styles-pages.json"))
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
    sorties = {"s3-ecoute#0": (15.10, 0.18), "s3-ecoute#1": (16.98, 0.18),
               "s4-agenda#0": (19.60, 5 / FPS), "s4-agenda#1": (23.10, 5 / FPS), "s4-agenda#2": (25.00, 5 / FPS),
               "s5-rendez-vous#0": (27.64, 0.16), "s5-rendez-vous#1": (29.20, 0.15), "s5-rendez-vous#2": (30.92, 0.18),
               "s6-sms#0": (33.70, 0.18), "s6-sms#1": (round((1076 - 0.5) / FPS, 6), 0.0)}
    s2p = [p for p in D["pages"] if p["scene"] == "s2-voix"]
    for i, p in enumerate(s2p):
        if i < len(s2p) - 1:
            fin_voix = p["mots"][-1]["fin_voix"]
            sorties[p["cle"]] = (round(math.ceil(fin_voix * FPS - 1e-6) / FPS, 6), 0.15)
        else:
            sorties[p["cle"]] = (10.10, 0.20)
    for p in D["pages"]:
        if p["scene"] in ("s2-voix", "s6-sms"):
            t_, d_ = sorties[p["cle"]]
            p["sortie"] = {"t": t_, "duree": d_, "note": "début de la sortie par les masques (s film) et durée ; lu par la scène"}
    for p in D["pages"]:
        p["_cle"] = p["cle"]

    # 4. les trajets planifiés (s2-s3, s6) puis le point
    P1 = (mesures["s1"]["centre"]["x"], mesures["s1"]["centre"]["y"])
    G6 = geometrie_iphone()
    S_bulle = (G6["point"]["x"], G6["point"]["y"])     # version iPhone : (168,99 ; 1282,93), 14 px sous la pointe de la queue
    t1, t2, boites = trajets(D["pages"], sorties, P1, STYLES["s3_texte"], agenda, S_bulle)
    for p in D["pages"]:
        p.pop("_cle", None)
    pt = point(mots, agenda, mesures, t1, t2, S_bulle)
    ev = evenements(mots, pt, D["pages"], t2)
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
    e0 = ecart((R[0]["x_sans"], R[0]["y_sans"]), P1)
    if e0 > 0.5: err.append(f"image 0 : écart {e0:.2f} px au point final de s1")
    n_pose = ev["point_pose"]["images"][1]
    if abs(R[n_pose]["d"] - mesures["s1"]["diametre"]) > 0.05 or R[0]["d"] > 1e-6:
        err.append(f"le point de s1 n'est pas invisible à l'image 0 et posé à l'image {n_pose} ({R[0]['d']} ; {R[n_pose]['d']})")
    M = (mesures["s7"]["centre"]["x"], mesures["s7"]["centre"]["y"])
    eRe = ecart((R[N_RE]["x"], R[N_RE]["y"]), M)
    if eRe > 0.5: err.append(f"image {N_RE} : écart {eRe:.2f} px à #mot-pt")
    for n in (N_RE, N_RE + 3):
        if abs(R[n]["d"] - 44) > 0.3: err.append(f"image {n} : diamètre {R[n]['d']}")
    if not (R[N_RE + 3]["sx"] == 1 and R[N_RE + 3]["sy"] == 1): err.append(f"image {N_RE + 3} : déformation {R[N_RE + 3]['sx']} / {R[N_RE + 3]['sy']}")
    A = pt["reperes"]["A"]
    for n, yl in ((620, A["y9"]), (643, A["y10"]), (666, A["y11"]), (731, A["y9"])):
        if abs(R[n]["y"] - yl) > 0.5: err.append(f"contact {n} : y {R[n]['y']} ≠ {yl}")
    pas = [0.0] + [ecart((res[k]["x_sans"], res[k]["y_sans"]), (res[k - 1]["x_sans"], res[k - 1]["y_sans"])) for k in range(1, len(res))]
    for n, vmin in ((620, 10), (643, 10), (666, 10), (N_RE, 10), (731, 5)):
        if pas[n] < vmin: err.append(f"contact {n} : dernier pas {pas[n]:.1f} px < {vmin}")
    for k in range(1, len(res)):
        lim = 150 if 137 <= k <= 150 else 130
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
    for n in sorted({0, 25, 27, 29, 126, 127, 137, 139, 141, 150, 516, 534, 613, 616, 619, 620, 643, 666, 730, 731, 761, 762, 783, 787, 801,
                     821, 933, 945, 962, 973, 1017, 1032, 1100, 1230, 1236, 1245, 1266, 1269, 1276, 1281, N_RE - 1, N_RE, N_RE + 3, IMAGES - 1}):
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
