#!/usr/bin/env python3
"""Piste de dialogue du film « Le point sur le i » : les extraits du VRAI appel, placés aux temps du film.

    python3 son/dialogue.py            écrit son/dialogue.wav + son/dialogue.json, et contrôle chaque coupe (code 1 si une
                                       coupe sort du vrai blanc ou si un bord dépasse ce qu'exige l'image)
    python3 son/dialogue.py --avant D  écrit dans D le dialogue du film d'avant les insertions (47 s ; identique à l'octet au
                                       dialogue.wav de a6d3d8e, md5 97ff1808…) : la référence de outils/verifier_insertion.py

Source : l'appel du 18/09/2026 à 16:51:54 (Paris) sur la ligne de démonstration de la Clinique
vétérinaire du Port, conversation ElevenLabs conv_9401m2tg19wtfxn9cm727n4dtskz, 85 s.
  - originaux/veterinaire.mp3 : l'enregistrement brut (16 kHz mono).
  - montes/veterinaire.wav    : le même, décodé en PCM, avec UNE coupe (66,70 → 70,90 de l'original :
    « Je vérifie les disponibilités. » + « Un instant. »). Vérifié par corrélation (26/09) : identique à
    l'échantillon près avant 66,70, et montes = original − 4,20 après 70,90. Aucun autre blanc raboté.
On coupe dans montes (PCM, pas de second décodage MP3).

Règles (révision du 27/09 au soir, retour de Florian : « deux sautes de son au début » et « on n'entend pas bien le mon ») :
  - LE VRAI BLANC. La voix de l'appelant passe par une porte (VAD) : entre deux phrases la source tombe sur un plancher de
    −81/−82 dBFS (RMS 5 ms, 48 kHz), le vrai blanc. L'ancienne règle (< −45 dBFS à ±20 ms) laissait couper dans des
    queues à −55/−63 dBFS : la chaîne voix de mix.py (compresseur + gain de sonie) les remonte de ~25 dB, et le fondu de
    15 ms les faisait tomber net sur du silence numérique (la « saute » : 10,01 fin de « aider ? », 14,06 fin de « hier »,
    35,48 fin de « Au revoir » ; 33,98 entrée de « Super » sur la porte déjà ouverte).
    Désormais : TOUTE la rampe d'entrée et les 10 dernières ms de la rampe de sortie sont ≤ −70 dBFS (RMS 5 ms), et
    la rampe de sortie couvre la décroissance naturelle de la queue. Une seule exception, déclarée dans l'extrait
    ("blanc_out_dbfs") : A2A3, où l'agente enchaîne deux phrases sans que la porte se ferme (queue à −69/−79 dBFS), et
    C3, dont la sortie ne peut pas dépasser 25,00 (s4-agenda.html exige SORTIE_CHOIX ≥ C3.film_out) : queue à −67 dBFS,
    rampe de 80 ms. Les visuels lisent film_out de A2A3 (≤ 23,10) et de C3 (≤ 25,00), film_in de C2 (≤ 15,10).
    Les mots ne bougent pas : seul le bord s'allonge dans le blanc (même décalage film − source, donc film_in plus tôt ou
    film_out plus tard).
  - fondus en cosinus surélevé : 40 ms à l'entrée, 60 à 120 ms à la sortie (champ par extrait) ;
  - un seul traitement, déclaré : des gains de clip doux (champ "gains", rampes de 30 ms) : « mon » de
    « mon chat » (+4 dB) : murmure nasal court, 3 à 5 dB sous « chat » dans 300-2 000 Hz à la source ; après la chaîne
    voix de mix.py (dont le compresseur reprend ~2,6 dB), « mon » finit 1,35 LU au-dessus de « chat » dans le mix
    hybride (−10,1 contre −11,5 LUFS, +1,3 dB dans 1-4 kHz ; avant : −11,6 contre −11,1, −0,5 LU). Mesuré à la
    chaîne voix : +3 dB donnerait +0,9 LU, +2,5 dB +0,7 LU (outils/ausculter.py mots … --cles C1:0 C1:1) ; l'inspiration qui précède « Super » (C4), −6 dB. Sinon niveau
    d'origine, pas de normalisation, pas d'égalisation ;
  - 48 kHz stéréo (double mono), PCM 24 bits, durée = durée du film. Hors extraits : zéros numériques (le fond de ligne
    qui porte les jointures est un stem à part : son/stems_amont.py, outils/fond_ligne.py).

Insertions de temps (28/09, retour de Florian : « mon prénom est noté alors que je ne l'ai pas donné, ça fait bizarre ») :
  - le film de 47,00 s sautait « Très bien. C'est pour quel prénom ? » / « C'est pour Florian. ». L'échange revient (AP,
    CP) et TOUT ce qui suit glisse d'une mesure exacte de la grille du film (78,26 BPM, 4 temps de 23 images) :
    92 images = 3,066667 s = 147 200 échantillons à 48 kHz. Le film passe à 50,066667 s (1 502 images).
  - UN SEUL ENDROIT : la liste INSERTIONS ci-dessous. Chaque extrait garde son décalage du film de 47 s ("decalage") ;
    le décalage effectif lui ajoute les insertions qui le précèdent, en ÉCHANTILLONS entiers (aucun arrondi à la ms :
    A4 glisse de 147 200 échantillons, pas de 147 216). Un extrait né d'une insertion ("insertion": id) est placé
    directement dans le film allongé ; les insertions suivantes le décalent comme les autres.
  - dialogue.json porte "insertions" (image et temps du pivot dans le film d'avant, images, s, échantillons) et, par
    extrait, "decalage_base", "decalage_echantillons", "insertions" : l'image (outils/construire.py) et le son
    (stems_amont.py, mix.py) lisent la même donnée. Règle de conversion d'un instant t du film d'avant :
    t' = t + Σ images/30 des insertions dont t ≥ pivot (pivot = pivot_image / 30).
  - Autre insertion un jour : ajouter une entrée à INSERTIONS (pivot sur un temps de la grille : la musique reste sur la
    grille) et ses extraits avec "insertion": id. Rien d'autre à retoucher ici.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
MONTES = Path("/root/vokio-audios-metiers-180926/montes/veterinaire.wav")
ORIGINAL = Path("/root/vokio-audios-metiers-180926/originaux/veterinaire.json")
SR = 48000
FPS = 30
DUREE_BASE = 47.0   # v2, finition du 27/09 : 47,00 s, 1 410 images (le SMS se lit, la fin tient) ; commit a6d3d8e

# Insertions de temps, dans l'ordre du film. pivot_image = image du film D'AVANT l'insertion à partir de laquelle tout
# glisse de "images" images. Une mesure de la grille = 92 images (temps forts connus : 551, 643, 735, 827).
INSERTIONS = [
    {"id": "prenom", "pivot_image": 758, "images": 92, "extraits": ["AP", "CP"],
     "motif": "L'échange du prénom (retour de Florian du 28/09). Pivot 758 (25,2667 s) : un temps de la grille (735 + 23), "
              "après la fin de C3 (25,00, SORTIE_CHOIX de s4) et le début de s5 (25,20), avant A4 (26,17). Entre 25,2667 "
              "et 26,17 il n'y avait, dans le film de 47 s, que la plume (25,367) et l'écriture de « Florian » "
              "(25,40 → 26,10), que l'image remet en scène sous la voix de l'appelant. Tout le reste glisse d'une mesure."},
]
ECH_PAR_IMAGE = SR // FPS     # 1 600


def ech_insertion(ins):
    return ins["images"] * ECH_PAR_IMAGE


DUREE_FILM = DUREE_BASE + sum(i["images"] for i in INSERTIONS) / FPS   # 50,066667 s
IMAGES_FILM = int(round(DUREE_BASE * FPS)) + sum(i["images"] for i in INSERTIONS)   # 1 502
FONDU_IN, FONDU_OUT = 0.040, 0.060
BLANC_DBFS = -70.0  # vrai blanc : plancher de la porte à −81/−82 dBFS, marge de 11 dB
FONDU_GAIN = 0.030


# Décalage montes → original : 0 avant 66,70 ; +4,20 après 70,90 (montes).
def vers_original(t):
    return round(t + (4.20 if t >= 66.70 else 0.0), 3)


# Les neuf extraits. src = secondes dans montes/veterinaire.wav ; film = src + decalage + insertions qui précèdent
# (décalages du film de 47 s inchangés : les mots ne bougent pas, ils glissent d'une mesure après l'échange du prénom).
# texte = mots EXACTS dits dans l'extrait, pris dans la transcription d'origine.
# "avant" = les bords de la v2 (27/09 matin), gardés pour la trace. "insertion" = extrait né de cette insertion : son
# "decalage" vaut dans le film allongé par elle.
EXTRAITS = [
    {"id": "A1", "locuteur": "agent", "tour_t": 0, "src_in": 0.70, "src_out": 6.10, "decalage": 4.21,
     "fondu_out": 0.120, "avant": [0.70, 5.80],
     "texte": "Bonjour, je suis Élise, l'assistante vocale de la Clinique vétérinaire du Port ! Comment puis-je vous aider ?",
     "motif": "Le décroché, en entier. Sortie à 6,10 (et non 5,80, en pleine queue de « aider ? » à −63 dBFS) : la queue "
              "décroît jusqu'au plancher, rampe de 120 ms."},
    {"id": "C1", "locuteur": "appelant", "tour_t": 7, "src_in": 10.20, "src_out": 13.86, "decalage": 0.22,
     "fondu_out": 0.060, "avant": [10.28, 13.84],
     "gains": [{"mot": "mon", "src": [10.335, 10.425], "db": 4.0,
                "raison": "« mon » : murmure nasal /mɔ̃/ de 90 ms (10,335 → 10,425), 3 à 5 dB sous « chat » dans 300-2 000 Hz ; "
                          "retour de Florian 27/09 : on ne l'entend pas bien"}],
     "texte": "mon chat, euh, Moka, euh, mange plus depuis hier",
     "motif": "On retire « Euh, oui, bonjour, j'vous appelle parce que » (fin 9,99, souffle 10,10-10,19) et « et il dort beaucoup, "
              "je trouve. » (bouffée 13,87). Entrée à 10,20, dans le vrai blanc après le souffle (porte fermée jusqu'à 10,33) ; "
              "sortie à 13,86, avant la bouffée de « et »."},
    {"id": "C2", "locuteur": "appelant", "tour_t": 34, "src_in": 34.72, "src_out": 37.20, "decalage": -20.16,
     "avant": [34.76, 37.16],
     "texte": "Euh, demain, vous avez des disponibilités ?",
     "motif": "Le triage saute (15,82 → 34,72) : « Je vois. Est-ce que Moka présente d'autres symptômes… », « Non, non, non, j'ai pas l'impression. », « Très bien. Dans ce cas… Quel jour vous conviendrait le mieux ? ». Entrée à 34,72 : la porte s'ouvre à 34,78."},
    {"id": "A2A3", "locuteur": "agent", "tour_t": 48, "src_in": 48.66, "src_out": 53.975, "decalage": -31.12,
     "fondu_out": 0.075, "avant": [48.66, 53.90],
     "blanc_out_dbfs": -66.0,          # exception déclarée : aucune porte fermée entre les deux phrases de l'agente
     "texte": "Laissez-moi voir. Je peux vous proposer neuf heures, dix heures ou onze heures.",
     "motif": "D'un seul tenant, avec le VRAI silence de l'outil next_available_slots (49,49 → 50,95, 1,46 s). Sautés en amont : « Un instant. », validate_date, « Demain, c'est samedi dix-neuf septembre. Pour quelle heure… », « Bah le matin. ». Coupé avant « Le dernier créneau possible de la journée est onze heures trente. Qu'est-ce qui vous arrangerait ? » (53,99) : pas de vrai blanc entre les deux phrases, la rampe de 75 ms suit la queue jusqu'à −75 dBFS."},
    {"id": "C3", "locuteur": "appelant", "tour_t": 58, "src_in": 58.76, "src_out": 60.56, "decalage": -35.56,
     "fondu_out": 0.080, "avant": [58.80, 60.54],
     "blanc_out_dbfs": -66.0,          # exception déclarée : la sortie est bornée à 25,00 par l'image (s4-agenda.html)
     "texte": "Euh, bah, à neuf heures, c'est parfait.",
     "motif": "Sortie à 60,56 (film 25,00), là où la queue de « parfait. » rejoint le plancher : pas plus tard, car s4-agenda.html (SORTIE_CHOIX, 25,00) exige que le choix ne sorte pas avant la fin de C3. Suivi, depuis le 28/09, de l'échange du prénom (AP, CP) ; le film de 47 s le sautait (63,31 → 66,48)."},
    # ── L'échange du prénom, remis le 28/09 (insertion « prenom ») : deux extraits, un par locuteur (qui parle =
    # typographie), le MÊME décalage : le vrai silence entre la question et la réponse est gardé tel quel (voix de
    # l'agente jusqu'à 64,71, appelant dès 65,90 : 1,19 s, la latence médiane de cet appelant sur tout l'appel, de 0,99 à
    # 1,99 s). Décalage −37,77 : les deux blancs autour de l'échange s'égalisent (fin de « parfait. » 24,93 → « Très »
    # 25,53 : 0,60 s ; fin de « Florian. » 28,71 → « Parfait, » 29,307 : 0,60 s), le rythme des autres tours du film
    # (0,59 à 0,75 s).
    {"id": "AP", "locuteur": "agent", "tour_t": 63, "src_in": 63.24, "src_out": 65.00, "decalage": -37.77,
     "insertion": "prenom", "fondu_out": 0.120,
     "texte": "Très bien. C'est pour quel prénom ?",
     "motif": "La question, en entier, « Très bien. » compris (l'accusé de réception naturel de « c'est parfait. », et sans lui il "
              "faudrait entrer à 63,82 dans une respiration de l'agente à −70/−72 dBFS, sans porte fermée). Entrée à 63,24 : "
              "plancher jusqu'à 63,28, la voix part à 63,29. Sortie à 65,00 : la queue de « prénom ? » décroît de 64,71 "
              "(−34 dBFS) au plancher (64,97) ; rampe de 120 ms, comme A1."},
    {"id": "CP", "locuteur": "appelant", "tour_t": 65, "src_in": 65.74, "src_out": 66.56, "decalage": -37.77,
     "insertion": "prenom", "fondu_out": 0.060,
     "texte": "C'est pour Florian.",
     "motif": "La réponse, en entier. Entrée à 65,74, dans le vrai blanc (porte fermée jusqu'à 65,785) : la porte s'ouvre sur la "
              "montée du /s/ de « C'est » (65,79 → 65,89, −74 à −53 dBFS, 2,5-4 kHz dominant ; 14 dB sous l'inspiration de C4 "
              "dans 2,4-4,5 kHz), gardée telle quelle, sans gain : c'est le début du mot. Sortie à 66,56 : « Florian. » "
              "s'éteint à 66,51 et la porte se ferme (plancher dès 66,515) ; rampe de 60 ms dans le plancher, qui ne touche pas "
              "la fin du /ɑ̃/. Avant la coupe du montage du 18/09 (66,70). Niveau : « Florian » sort de la chaîne voix de "
              "mix.py à −20,0 LUFS (1-4 kHz −35,2 dB), dans la médiane des mots de l'appelant (« chat » −19,1, « demain » "
              "−18,9, « neuf » −20,5, « Super » −18,5) : aucun gain de clip."},
    {"id": "A4", "locuteur": "agent", "tour_t": 71, "src_in": 67.24, "src_out": 74.33, "decalage": -41.07,
     "fondu_out": 0.080, "avant": [67.24, 74.30],
     "texte": "Parfait, je vous note ça pour Florian, pour une consultation vétérinaire, le samedi dix-neuf septembre à neuf heures. Vous recevrez un SMS de confirmation.",
     "motif": "La confirmation, en entier. Le montage du 18/09 avait déjà retiré la revérification (original 66,70 → 70,90). "
              "28/09 : glisse d'une mesure avec l'insertion « prenom » (décalage effectif −38,003333, film 29,2367) ; « pour "
              "Florian » y devient une confirmation du prénom que l'appelant vient de donner."},
    {"id": "C4", "locuteur": "appelant", "tour_t": 79, "src_in": 74.86, "src_out": 76.72, "decalage": -41.07,
     "fondu_out": 0.120, "avant": [75.05, 76.55],
     "gains": [{"mot": "souffle avant « Super »", "src": [74.915, 75.070], "db": -6.0,
                "raison": "la porte s'ouvre sur une inspiration (2,4-4,5 kHz, −34,6 dBFS après la chaîne voix) : gardée, "
                          "car elle amène « Super » sans saute, mais 6 dB plus bas"}],
     "texte": "Super, merci beaucoup. Au revoir.",
     "motif": "L'appelant raccroche : le « De rien, au revoir. » de l'agente (montes 79,23) saute. v2 : décalage −41,07, "
              "le même que A4 : C4 suit A4 après son VRAI blanc. Entrée à 74,86 : la porte s'ouvre à 74,915 (fond de la ligne "
              "de l'appelant, 185 ms avant « Super ») ; l'ancienne entrée (75,05) tombait dessus. Sortie à 76,72 (queue de "
              "« revoir. » jusqu'à 76,70), avant le raccroché du film (35,867 = 76,937 dans le film de 47 s ; 38,933 depuis "
              "l'insertion « prenom », qui décale C4 d'une mesure comme A4)."},
]


def lire(chemin, sr):
    brut = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(chemin), "-af",
                           f"aresample={sr}:resampler=soxr:precision=28", "-f", "f32le", "-ac", "1", "-"],
                          capture_output=True, check=True).stdout
    return np.frombuffer(brut, dtype="<f4").astype(np.float64)


def profil5(sig):
    """RMS 5 ms (dBFS) de la source, fenêtres jointives."""
    n = int(0.005 * SR)
    k = len(sig) // n
    return 20 * np.log10(np.sqrt(np.mean(sig[:k * n].reshape(k, n) ** 2, axis=1)) + 1e-12)


def max_sur(p, a, b):
    i, j = int(np.floor(a / 0.005)), int(np.ceil(b / 0.005))
    return float(p[i:max(j, i + 1)].max())


def rampe(n):
    return 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))


def gain_de_clip(n, i0, g, sr=SR):
    """Courbe de gain (n,) : 1 partout, g.db sur [a ; b] (s relatives au début du morceau), rampes de FONDU_GAIN dehors."""
    t = np.arange(n) / sr + i0
    a, b = g["src"]
    f = FONDU_GAIN
    p = np.zeros(n)
    p[(t >= a) & (t <= b)] = 1
    m = (t >= a - f) & (t < a); p[m] = 0.5 - 0.5 * np.cos(np.pi * (t[m] - (a - f)) / f)
    m = (t > b) & (t <= b + f); p[m] = 0.5 + 0.5 * np.cos(np.pi * (t[m] - b) / f)
    return 1 + (10 ** (g["db"] / 20) - 1) * p


# Ce que l'image exige des bords (compositions/*.html, « exiger(SORTIE ≥ e.film_… − EPS) ») : lu dans le HTML, vérifié à
# chaque exécution, pour qu'une recoupe ne casse jamais le rendu quand donnees/ sera régénéré par outils/construire.py.
# (fichier, constante, extrait, bord) : la constante de l'IMAGE qu'un bord du son ne doit pas dépasser. Fichier : dans
# compositions/ du projet de l'image de référence (le 9:16, videos/showcase-iphone, depuis les deux copies de ce script),
# ou un chemin relatif à ce projet (« outils/construire.py » : les sorties de pages de s5 y sont des données, 28/09).
CONTRAINTES_IMAGE = [
    ("s3-ecoute.html", "SORTIE_C1", "C2", "film_in"),
    ("s4-agenda.html", "SORTIE_CRENEAUX", "A2A3", "film_out"),
    ("s4-agenda.html", "SORTIE_CHOIX", "C3", "film_out"),
    # l'échange du prénom (28/09) : la question et la réponse sortent de l'écran après que la voix s'est tue
    ("outils/construire.py", "SORTIE_QUESTION", "AP", "film_out"),
    ("outils/construire.py", "SORTIE_REPONSE", "CP", "film_out"),
]
IMAGE_9X16 = ICI.parents[1] / "showcase-iphone"   # l'image de référence (le 9:16), vue des deux copies de ce script


def contraintes_image(sortie):
    """Vérifie bord ≤ constante de l'image (surImage = première image ≥ t, à 30 i/s). Renvoie la liste des écarts."""
    import math
    import re
    res = []
    for fichier, cst, ex, bord in CONTRAINTES_IMAGE:
        html = (IMAGE_9X16 / fichier if "/" in fichier else IMAGE_9X16 / "compositions" / fichier).read_text()
        m = re.search(rf"^\s*(?:const )?{cst}\s*=\s*(surImage\()?\s*([0-9.]+)", html, re.M)
        assert m, f"{cst} introuvable dans {fichier}"
        v = float(m.group(2))
        if m.group(1):
            v = math.ceil(v * 30 - 1e-6) / 30
        e_ = next((e for e in sortie if e["id"] == ex), None)
        if e_ is None:
            continue                      # --avant : un extrait né d'une insertion (AP, CP) n'existe pas dans le film d'avant
        b = e_[bord]
        res.append({"image": f"{fichier} {cst}", "valeur": round(v, 4), "extrait": ex, "bord": bord, "t": b,
                    "ok": b <= v + 1e-4})
    return res


def decalage_effectif(e):
    """(décalage film − source en ÉCHANTILLONS, ids des insertions appliquées). Les insertions s'appliquent dans l'ordre :
    un extrait est décalé par une insertion si son entrée, dans le film d'avant cette insertion, est au pivot ou après ;
    un extrait né d'une insertion ("insertion": id) n'est décalé que par les insertions suivantes."""
    d = int(round(e["decalage"] * SR))
    assert abs(d - e["decalage"] * SR) < 1e-6, (e["id"], "décalage hors de la grille des échantillons")
    ne = e.get("insertion")
    assert ne is None or any(i["id"] == ne for i in INSERTIONS), (e["id"], ne)
    vivant, appliquees = ne is None, []
    for ins in INSERTIONS:
        if not vivant:
            vivant = ins["id"] == ne
            continue
        if int(round(e["src_in"] * SR)) + d >= ins["pivot_image"] * ECH_PAR_IMAGE:
            d += ech_insertion(ins)
            appliquees.append(ins["id"])
    return d, appliquees


def decaler(t):
    """Instant du film de 47 s (DUREE_BASE) → instant du film actuel (s). Pour l'image : même règle, lue dans dialogue.json."""
    for ins in INSERTIONS:
        if t >= ins["pivot_image"] / FPS - 1e-9:
            t += ins["images"] / FPS
    return t


def main():
    orig = json.loads(ORIGINAL.read_text())
    assert orig["conversation_id"] == "conv_9401m2tg19wtfxn9cm727n4dtskz", orig["conversation_id"]
    tours = {(t["t"], t["role"]): t["message"] for t in orig["transcript"] if t["message"]}

    src = lire(MONTES, SR)
    p = profil5(src)
    piste = np.zeros(int(round(DUREE_FILM * SR)))

    sortie, ok = [], True
    for e in EXTRAITS:
        role = "agent" if e["locuteur"] == "agent" else "user"
        dit = tours[(e["tour_t"], role)]
        if e["id"] == "A2A3":
            dit = tours[(48, "agent")] + " " + tours[(50, "agent")]
        assert e["texte"] in dit, (e["id"], e["texte"], dit)

        f_in, f_out = e.get("fondu_in", FONDU_IN), e.get("fondu_out", FONDU_OUT)
        a, b = int(round(e["src_in"] * SR)), int(round(e["src_out"] * SR))
        morceau = src[a:b].copy()
        for g in e.get("gains", []):
            morceau *= gain_de_clip(len(morceau), e["src_in"], g)
        n_i, n_o = int(round(f_in * SR)), int(round(f_out * SR))
        morceau[:n_i] *= rampe(n_i)
        morceau[-n_o:] *= rampe(n_o)[::-1]
        d, appliquees = decalage_effectif(e)
        i = a + d                                                       # échantillon exact (aucun arrondi à la ms)
        assert i >= 0 and i + len(morceau) <= len(piste), (e["id"], "hors du film")
        film_in, film_out = round(i / SR, 6), round((b + d) / SR, 6)
        piste[i:i + len(morceau)] += morceau

        b_in = max_sur(p, e["src_in"], e["src_in"] + f_in)             # toute la rampe d'entrée
        b_out = max_sur(p, e["src_out"] - 0.010, e["src_out"])          # les 10 dernières ms de la rampe de sortie
        blanc = b_in <= BLANC_DBFS and b_out <= e.get("blanc_out_dbfs", BLANC_DBFS)
        ok &= blanc
        print(f"{e['id']:5s} source {e['src_in']:6.3f} → {e['src_out']:6.3f}  film {film_in:6.3f} → {film_out:6.3f}  "
              f"rampes {f_in * 1000:3.0f}/{f_out * 1000:3.0f} ms  bords {b_in:6.1f} / {b_out:6.1f} dBFS  "
              f"{'vrai blanc' if blanc else 'HORS DU VRAI BLANC'}"
              + "".join(f"  gain {g['mot']} {g['db']:+.1f} dB" for g in e.get("gains", [])))
        sortie.append({
            "id": e["id"], "locuteur": e["locuteur"],
            "source": str(MONTES), "source_in": e["src_in"], "source_out": e["src_out"],
            "original_in": vers_original(e["src_in"]), "original_out": vers_original(e["src_out"]),
            "film_in": film_in, "film_out": film_out, "decalage_film_moins_source": round(d / SR, 6),
            "decalage_base": e["decalage"], "decalage_echantillons": d, "insertions": appliquees,
            "insertion": e.get("insertion"),
            "fondu_s": f_in, "fondu_in_s": f_in, "fondu_out_s": f_out,
            "gains": [dict(g, film=[round(g["src"][0] + d / SR, 6), round(g["src"][1] + d / SR, 6)],
                           fondu_s=FONDU_GAIN) for g in e.get("gains", [])],
            "bords_avant_v2_source": e.get("avant"),
            "texte": e["texte"], "tour_original_t": e["tour_t"], "motif": e["motif"],
            "bords_dbfs": [round(b_in, 1), round(b_out, 1)],
        })
    for x, y in zip(sortie, sortie[1:]):
        assert x["film_out"] < y["film_in"], (x["id"], y["id"])
    img = contraintes_image(sortie)
    for c in img:
        print(f"image : {c['extrait']}.{c['bord']} = {c['t']:.3f} ≤ {c['image']} = {c['valeur']:.3f}  {'ok' if c['ok'] else 'CASSE LE RENDU'}")
    ok &= all(c["ok"] for c in img)

    # 48 kHz, stéréo double mono, 24 bits, niveau d'origine (sauf le gain de clip déclaré)
    st = np.stack([piste, piste], axis=1).astype("<f4")
    wav = ICI / "dialogue.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(wav)], input=st.tobytes(), check=True)
    meta = {
        "fichier": str(wav), "sr": SR, "canaux": 2, "format": "pcm_s24le", "duree_s": DUREE_FILM,
        "fps": FPS, "images": IMAGES_FILM, "echantillons": len(piste), "duree_base_s": DUREE_BASE,
        "insertions": [dict(ins, pivot_s=round(ins["pivot_image"] / FPS, 6), s=round(ins["images"] / FPS, 6),
                            echantillons=ech_insertion(ins)) for ins in INSERTIONS],
        "insertions_regle": ("instant t du film d'avant (47 s, commit a6d3d8e) → t + Σ s des insertions dont t ≥ pivot_s, "
                             "appliquées dans l'ordre ; en images : image + Σ images des insertions dont image ≥ pivot_image"),
        "niveau": "niveau d'origine de montes/veterinaire.wav, aucun filtre ; un seul gain de clip déclaré (extraits[].gains)",
        "appel": {"conversation_id": orig["conversation_id"], "debut": "2026-09-18 16:51:54 Europe/Paris",
                  "duree_s": orig["call_duration_secs"], "etablissement": orig["etablissement"],
                  "brut": "/root/vokio-audios-metiers-180926/originaux/veterinaire.mp3",
                  "monte": str(MONTES),
                  "montes_vers_original": "original = montes avant 66,70 ; original = montes + 4,20 après (coupe 66,70 → 70,90 de l'original)"},
        "regle_de_coupe": (f"vrai blanc : RMS 5 ms (48 kHz) ≤ {BLANC_DBFS:.0f} dBFS sur toute la rampe d'entrée et sur les 10 "
                           "dernières ms de la rampe de sortie (plancher de la porte : −81/−82 dBFS) ; rampes cosinus, "
                           f"{FONDU_IN * 1000:.0f} ms à l'entrée, 60 à 120 ms à la sortie ; décalages inchangés (les mots ne bougent pas), "
                           "sauf les insertions de temps (\"insertions\"), qui décalent en échantillons entiers tout ce qui suit"),
        "extraits": sortie,
        "contraintes_image": img,
    }
    (ICI / "dialogue.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(("toutes les coupes tombent dans le vrai blanc" if ok else "ÉCHEC : une coupe hors du vrai blanc"), "→", wav)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--avant":
        # Le dialogue du film d'AVANT toute insertion (47 s), écrit ailleurs : la référence des preuves à l'échantillon
        # (outils/verifier_insertion.py --wav-ref DOSSIER/dialogue.wav). Même code, mêmes extraits, sans les nés d'une insertion.
        ICI = Path(sys.argv[2])
        ICI.mkdir(parents=True, exist_ok=True)
        EXTRAITS = [e for e in EXTRAITS if not e.get("insertion")]
        INSERTIONS = []
        DUREE_FILM, IMAGES_FILM = DUREE_BASE, int(round(DUREE_BASE * FPS))
    elif len(sys.argv) > 1:
        sys.exit(__doc__)
    main()
