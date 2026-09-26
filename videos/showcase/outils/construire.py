#!/usr/bin/env python3
"""Construit LA source de vérité partagée : donnees/donnees.js (window.DONNEES) + les .json jumeaux.

    python3 outils/construire.py          mesure (Chromium), calcule, écrit, résout le point, contrôle

Entrées (produites avant) :
  son/dialogue.json            (son/dialogue.py)       extraits du vrai appel, placés aux temps du film
  son/dialogue.wav                                      pour la progression voisée de A1 (s2)
  donnees/mots.json            (outils/mots.py)        mots horodatés, temps film
  donnees/agenda-geo.json      (outils/preparer_agenda.py)
  compositions/s1-sonnerie.html, s7-signature.html      la géométrie mesurée (le « . » de s1, #mot-pt de s7)
Sorties :
  donnees/mesures.json  voix-x.json  secousses.json  point.json  scenes.json  evenements.json
  donnees/donnees.js    (tout, en une affectation window.DONNEES = {...})
  donnees/point-resolu.json  (POINT.etat(n/30) évalué DANS Chromium par lib/point.js, pour le son en python)
Règle : tout temps d'animation calé sur la voix vient d'ici. Relancer après toute retouche de mots.json,
de la géométrie de s1/s7 ou de l'agenda.
"""
import json
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

PROJET = Path(__file__).resolve().parents[1]
DON = PROJET / "donnees"
PW = "/root/.pwtest/bin/python"
FPS = 30
DUREE = 43.5
IMAGES = int(round(DUREE * FPS))   # 1305 images : 0 … 1304 ; l'instant 43,5 = fin
SR = 48000

COULEURS = {"papier": "#F4F1E8", "encre": "#262019", "solaire": "#EFA424", "terracotta": "#C0452C",
            "vert": "#6E9C74", "gris": "#6F695F", "bulle": "#E9E3D6"}

SCENES = [  # id, début, fin (bible, plan_de_fabrication)
    ("s1-sonnerie", 0.0, 4.5), ("s2-voix", 4.5, 10.4), ("s3-ecoute", 10.4, 17.3),
    ("s4-agenda", 17.3, 25.2), ("s5-rendez-vous", 25.2, 31.35), ("s6-sms", 31.35, 36.9),
    ("s7-signature", 36.9, 43.5)]


def img(t):
    return int(round(t * FPS))


def a_img(t):
    """Arrondi à l'image (secondes film)."""
    return round(round(t * FPS) / FPS, 6)


def lire_json(nom):
    return json.loads((DON / nom).read_text())


def ecrire_json(nom, obj):
    (DON / nom).write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def navigateur(*args):
    r = subprocess.run([PW, str(PROJET / "outils" / "navigateur.py"), *args], capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise SystemExit(f"navigateur.py {args} : {r.stderr[-2000:]}")
    out = json.loads(r.stdout)
    if out.get("erreurs_page"):
        raise SystemExit(f"erreurs JS dans le banc : {out['erreurs_page']}")
    return out


def lire_wav_mono(chemin):
    with wave.open(str(chemin)) as w:
        n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
        b = w.readframes(n)
    assert sw == 3, "dialogue.wav doit être en 24 bits"
    a = np.frombuffer(b, dtype=np.uint8).reshape(-1, 3)
    x = (a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int32) << 16))
    x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(np.float64) / (1 << 23)
    return x.reshape(-1, ch).mean(axis=1)


# ─────────────────────────────────────────────────────────────────────────────
def voix_x(mots, dialogue):
    """s2 : x(t) = 106 + 868·V(t), V = temps voisé cumulé normalisé de A1 (10 ms > −40 dBFS, moyenne 150 ms)."""
    x = lire_wav_mono(PROJET / "son" / "dialogue.wav")
    w = SR // 100
    n = len(x) // w
    db = 20 * np.log10(np.sqrt((x[:n * w].reshape(n, w) ** 2).mean(axis=1)) + 1e-12)
    a1 = next(e for e in dialogue["extraits"] if e["id"] == "A1")
    m1 = [m for m in mots if m["extrait"] == "A1"]
    t0, t1 = a_img(m1[0]["debut"]), a_img(m1[-1]["fin"])
    k0, k1 = int(round(a1["film_in"] * 100)), int(round(a1["film_out"] * 100))
    v = np.zeros(n)
    v[k0:k1] = (db[k0:k1] > -40).astype(float)
    s = np.convolve(v, np.ones(15) / 15, mode="same")          # 150 ms centrés
    cum = np.concatenate([[0], np.cumsum(s * 0.01)])              # cum[k] = ∫ de 0 à k·10 ms

    def C(t):
        f = t * 100
        i = int(np.floor(f))
        return cum[i] + (cum[i + 1] - cum[i]) * (f - i)
    tot = C(t1) - C(t0)
    i0, i1 = img(t0), img(t1)
    V = [min(1.0, max(0.0, (C(k / FPS) - C(t0)) / tot)) for k in range(i0, i1 + 1)]
    X0, X1 = 106.0, 974.0
    return {
        "unite": "V sans unité 0 → 1 ; x en px film ; une valeur par image de image0 à image1 incluses",
        "definition": "V(t) = ∫ s de t0 à t / ∫ s de t0 à t1, s = voisement de A1 (fenêtres 10 ms > −40 dBFS dans son/dialogue.wav) lissé par moyenne glissante centrée de 150 ms ; x = 106 + 868·V",
        "t0": t0, "t1": t1, "image0": i0, "image1": i1, "x0": X0, "x1": X1, "y": 1000.0,
        "v": [round(u, 5) for u in V], "x": [round(X0 + (X1 - X0) * u, 3) for u in V],
    }


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
    # s1 : tonalité 440 Hz, 1,5 s on (0 → 1,5) puis 3,6 → 4,2 (à 4,2 elle devient cloche : le tremblement cesse)
    # ton-1 : fondus de 10 ms aux deux bouts ; ton-2 : fondu d'entrée de 10 ms, puis à 4,2 il ne coupe pas (il
    # s'ouvre en cloche) mais le tremblement, lui, s'arrête net : pas de rampe de sortie dans l'enveloppe visuelle.
    s1_seg = [(0.0, 1.5, 0.010, 0.010), (3.6, 4.2, 0.010, 0.0)]
    env1 = enveloppe_par_image(s1_seg, 0, 135)
    env1 = [0.0 if k >= 126 else v for k, v in enumerate(env1)]   # coupe nette au décroché (image 126)
    # s6 : vibreur, deux impulsions de 180 ms séparées de 90 ms, la 1re à l'image 998 exactement
    v0 = 998 / FPS
    s6_seg = [(v0, v0 + 0.18, 0.012, 0.025), (v0 + 0.27, v0 + 0.45, 0.012, 0.025)]
    env6 = enveloppe_par_image(s6_seg, 998, 15)
    return {
        "unite": "enveloppe 0 → 1 par image (moyenne sur l'image) ; décalage x = amplitude_px × enveloppe × motif",
        "s1": {"description": "tonalité d'attente 440 Hz (ton-1 0 → 1,5 s ; ton-2 3,6 → 4,2 s), fondus 10 ms ; 0 dès l'image 126 (décroché)",
               "image0": 0, "enveloppe": env1, "amplitude_px": 3.0, "motif": [0, 1, 0, -1], "phase_par_image_absolue": True,
               "segments_s": [[a, b] for a, b, _, _ in s1_seg], "rampes_s": [[fa, fr] for _, _, fa, fr in s1_seg],
               "frequence_hz": 7.5, "note": "motif de 4 images = 7,5 Hz, sous Nyquist du 30 i/s ; x(n) = 3·env(n)·[0,+1,0,−1][n mod 4]"},
        "s6": {"description": "vibreur du SMS : impulsions 33,2667 → 33,4467 et 33,5367 → 33,7167 s, attaque 12 ms, relâche 25 ms",
               "image0": 998, "enveloppe": env6, "amplitude_px": 2.0, "motif": [1, 0, -1, 0], "phase_par_image_absolue": False,
               "segments_s": [[round(a, 6), round(b, 6)] for a, b, _, _ in s6_seg], "rampes_s": [[fa, fr] for _, _, fa, fr in s6_seg],
               "frequence_hz": 7.5, "note": "x(n) = 2·env·[+1,0,−1,0][(n−998) mod 4] ; la silhouette de s6 ET #point lisent la même valeur (POINT.secousse('s6', t))"},
    }


def mot(mots, extrait, rang):
    m = next(w for w in mots if w["extrait"] == extrait and w["rang"] == rang)
    return m


def point(mots, agenda, mesures):
    s1c, s1d = mesures["s1"]["centre"], mesures["s1"]["diametre"]
    s7c, D = mesures["s7"]["centre"], mesures["s7"]["diametre"]
    XA = agenda["x_point"]
    H = agenda["heures"]
    Y9, Y10, Y11 = H["09:00"], H["10:00"], H["11:00"]
    bloc = agenda["bloc"]
    YC = bloc["centre_y"]
    XB0 = round(bloc["x0"] + D / 2, 2)                 # bord gauche du point = bord gauche du bloc
    XB1 = round(bloc["x1_visible"] - D / 2, 2)         # bord révélé = x + D/2 → l'image entière à la fin
    voy = lambda e, r: mot(mots, e, r).get("voyelle", mot(mots, e, r)["debut"])
    L9, L10, L11 = a_img(voy("A2A3", 6)), a_img(voy("A2A3", 8)), a_img(voy("A2A3", 11))
    R0 = a_img(mot(mots, "C3", 2)["debut"])            # « à (neuf heures) » de l'appelant
    m1 = [w for w in mots if w["extrait"] == "A1"]
    T0, T1 = a_img(m1[0]["debut"]), a_img(m1[-1]["fin"])
    S = 6 / FPS                                        # un saut = 6 images (0,2 s)
    k = lambda t, x, y, ease=None, arc=None, note=None: {k2: v for k2, v in (("t", round(t, 6)), ("image", img(t)), ("x", round(x, 3)),
                                                         ("y", round(y, 3)), ("ease", ease), ("arc", arc), ("note", note)) if v is not None}
    pos = [
        k(0.0, s1c["x"], s1c["y"], note="s1 : point final de « mains prises. » (mesuré), encre ; tremble avec la tonalité"),
        k(4.50, s1c["x"], s1c["y"]),
        k(4.95, 106, 1000, "power3.inOut", note="s2 : retour chariot vers le début de la ligne"),
        k(T0, 106, 1000, note="s2 : pendant [t0 ; t1] de pistes.voix, x = DONNEES.voixX (avance quand Élise parle)"),
        k(T1, 974, 1000, "none"),
        k(17.20, 974, 1000, note="s3 : écoute, immobile"),
        k(17.80, XA, Y9, "power3.inOut", note="s4 : attend sur la ligne 09:00 (l'agenda arrive dessous)"),
        k(L9 - S, XA, Y9, note="saut sur place sur « neuf »"),
        k(L9 - S + 0.08, XA, Y9 - 28, "power2.out"),
        k(L9, XA, Y9, "power2.in", note="contact 09:00 = attaque de la voyelle de « neuf »"),
        k(L10 - S, XA, Y9),
        k(L10, XA, Y10, "power3.out", {"dx": -18}, note="saut en arc vers 10:00, contact = voyelle de « dix »"),
        k(L11 - S, XA, Y10),
        k(L11, XA, Y11, "power3.out", {"dx": -18}, note="saut en arc vers 11:00, contact = voyelle de « onze »"),
        k(R0, XA, Y11, note="retour lent vers 09:00 au « à (neuf heures) » de l'appelant"),
        k(R0 + 0.4, XA, Y9, "power2.inOut"),
        k(25.20, XA, Y9, note="s5"),
        k(25.40, XB0, YC, "power3.out", note="se pose au bord gauche du bloc"),
        k(26.10, XB1, YC, "power2.inOut", note="la plume : le bloc se déroule derrière lui (bord révélé = x + D/2)"),
        k(30.95, XB1, YC),
        k(31.45, 200, 790, "power3.inOut", note="s6 : coin haut gauche de la bulle"),
        k(36.60, 200, 790, note="secousse du vibreur 998 → 1012 (pistes.secousses)"),
        k(37.10, s7c["x"], s7c["y"] - 90, "power3.inOut", note="s7 : 90 px au-dessus du futur ı"),
        k(37.70, s7c["x"], s7c["y"] - 90, note="immobilité, silence numérique"),
        k(38.00, s7c["x"], s7c["y"], "power3.out", note="contact sur le ı : image 1140"),
    ]
    for a, b in zip(pos, pos[1:]):
        assert b["t"] > a["t"], (a, b)
    return {
        "unite": "t en s film ; x, y = CENTRE du point en px film ; d = diamètre visible en px",
        "lecture": "entre deux clés : de la clé i à la clé i+1 avec l'ease de la clé i+1 (gsap.parseEase) ; arc.dx ajouté × 4p(1−p) ; avant la 1re / après la dernière : tenue. Évaluer avec POINT.etat(t) (lib/point.js), jamais à la main.",
        "diametre_disque": D,
        "position": pos,
        "taille": [{"t": 0.0, "d": s1d}, {"t": 4.20, "d": s1d}, {"t": 4.70, "d": D, "ease": "power3.out"}],
        "couleur": [{"t": 0.0, "c": COULEURS["encre"]}, {"t": 4.20, "c": COULEURS["encre"]},
                    {"t": 4.40, "c": COULEURS["solaire"], "ease": "none"}],
        "pistes": {"voix": {"t0": T0, "t1": T1, "source": "DONNEES.voixX"},
                   "secousses": [{"piste": "s1", "t0": 0.0, "t1": round(134 / FPS, 6)},
                                 {"piste": "s6", "t0": round(998 / FPS, 6), "t1": round(1012 / FPS, 6)}]},
        "reperes": {"x_agenda": XA, "y_09": Y9, "y_10": Y10, "y_11": Y11, "bloc_y": YC, "bloc_x_debut": XB0, "bloc_x_fin": XB1,
                    "s1": s1c, "s7": s7c, "s7_au_dessus": {"x": s7c["x"], "y": round(s7c["y"] - 90, 3)}},
    }


def evenements(mots, pt):
    pos = pt["position"]
    def cle(note_debut):
        return next(c for c in pos if c.get("note", "").startswith(note_debut))
    c9, c10, c11 = cle("contact 09:00"), cle("saut en arc vers 10:00"), cle("saut en arc vers 11:00")
    retour = cle("retour lent")
    ret_fin = pos[pos.index(retour) + 1]
    ecr0, ecr1 = cle("se pose au bord gauche"), cle("la plume")
    syl = lire_json("mots.json")["syllabes"]["confirmation_derniere_syllabe"]
    ev = {
        "decroche": 4.20, "saut_neuf_debut": c9["t"] - 0.2, "contact_neuf": c9["t"], "saut_dix_debut": c10["t"] - 0.2,
        "contact_dix": c10["t"], "saut_onze_debut": c11["t"] - 0.2, "contact_onze": c11["t"],
        "retour_debut": retour["t"], "contact_retour_neuf": ret_fin["t"],
        "ecriture_pose": ecr0["t"], "ecriture_debut": ecr0["t"], "ecriture_fin": ecr1["t"],
        "resolution_confirmation": a_img(syl["voyelle"]),
        "bulle_et_vibreur": round(998 / FPS, 6), "raccroche": 36.60, "silence_numerique": [36.68, 37.40],
        "signature_la": 37.40, "signature_sol": 37.64, "signature_re_contact": 38.00, "fin": DUREE,
    }
    out = {}
    for k, v in ev.items():
        if isinstance(v, list):
            out[k] = {"t": v, "images": [img(x) for x in v]}
        else:
            out[k] = {"t": round(v, 6), "image": img(v)}
    out["_note"] = ("Temps film. Les contacts du point (sauts) sont aux attaques de voyelle mesurées ; un bruitage de "
                    "contact se pose à l'échantillon round(t × 48000). ecriture_debut = le point quitte le bord gauche "
                    "du bloc (le « la » de cloche-la-rdv de la bible est à 25,40).")
    return out


def reperes(mots):
    """Les 12 repères d'écoute de la bible (contrôle 7), avec leur mot."""
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
        r("C4", 0, "Super"),
    ]


def main():
    DON.mkdir(exist_ok=True)
    # 1. géométrie mesurée dans Chromium
    g = navigateur("geometrie")
    mesures = {
        "unite": "px film ; mesuré dans le chrome-headless-shell de HyperFrames",
        "moteur": g["moteur"], "date": datetime.now().isoformat(timespec="seconds"),
        "s1": {"centre": g["s1"]["centre"], "diametre": g["s1"]["diametre"], "ligne_de_base": g["s1"]["ligne_de_base"],
               "lignes": g["s1"]["lignes"], "espaceur": g["s1"]["espaceur"], "glyphe_point": g["s1"]["glyphe_point"],
               "methode": g["s1"]["methode_centre"], "source": "compositions/s1-sonnerie.html #s1-espaceur"},
        "s7": {"centre": g["s7"]["centre"], "diametre": g["s7"]["diametre"], "mot_pt": g["s7"]["mot_pt"],
               "mot": g["s7"]["mot"], "ligne_de_base": g["s7"]["ligne_de_base"], "glyphe_i": g["s7"]["glyphe_i"],
               "methode": g["s7"]["methode_centre"], "source": "compositions/s7-signature.html #mot-pt"},
    }
    ecrire_json("mesures.json", mesures)

    # 2. données
    dialogue = json.loads((PROJET / "son" / "dialogue.json").read_text())
    mj = lire_json("mots.json")
    mots = mj["mots"]
    agenda = lire_json("agenda-geo.json")
    vx = voix_x(mots, dialogue)
    sec = secousses()
    pt = point(mots, agenda, mesures)
    scenes = {sid: {"debut": d, "fin": f, "duree": round(f - d, 3), "image_debut": img(d), "image_fin": img(f),
                    "fichier": f"compositions/{sid}.html", "hote": f"h-{sid}"} for sid, d, f in SCENES}
    ev = evenements(mots, pt)
    rep = reperes(mots)
    for nom, obj in (("voix-x.json", vx), ("secousses.json", sec), ("point.json", pt), ("scenes.json", scenes),
                     ("evenements.json", ev), ("reperes.json", rep)):
        ecrire_json(nom, obj)
    D = {
        "version": datetime.now().isoformat(timespec="seconds"),
        "film": "Le point sur le i", "fps": FPS, "duree": DUREE, "images": IMAGES,
        "taille": [1080, 1920], "couleurs": COULEURS,
        "scenes": scenes,
        "dialogue": {"fichier": "son/dialogue.wav", "conversation_id": dialogue["appel"]["conversation_id"],
                     "extraits": [{k: e[k] for k in ("id", "locuteur", "film_in", "film_out", "source_in", "source_out",
                                                     "original_in", "original_out", "texte")} for e in dialogue["extraits"]]},
        "mots": [{k: w[k] for k in ("texte", "cle", "debut", "fin", "image", "locuteur", "extrait", "rang")}
                 | ({"voyelle": w["voyelle"]} if "voyelle" in w else {}) for w in mots],
        "syllabes": mj["syllabes"],
        "reperes": rep,
        "voixX": vx,
        "secousses": sec,
        "agenda": agenda,
        "point": pt,
        "mesures": {"s1": mesures["s1"], "s7": mesures["s7"]},
        "evenements": ev,
        "geometrie": {
            "s2_ligne": {"y": 1000, "x0": 90, "x1": 990, "epaisseur": 3, "point_x0": 106, "point_x1": 974},
            "s6_bulle_coin": {"x": 200, "y": 790},
            "sous_titres_haut": {"lignes_de_base": [400, 468, 536], "note": "s4, s5 et s6 (bible) ; l'agenda commence à y = 580"},
        },
    }
    def ecrire_js():
        entete = ("/* donnees/donnees.js · GÉNÉRÉ par outils/construire.py (" + D["version"] + ") · NE PAS ÉDITER À LA MAIN.\n"
                  " * Source de vérité unique du film « Le point sur le i ». Temps en secondes FILM, positions en px film.\n"
                  " * Chargé en premier par index.html ; lu par lib/texte.js, lib/point.js et toutes les scènes. */\n")
        (DON / "donnees.js").write_text(entete + "window.DONNEES = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n")
    ecrire_js()

    # 3. le point, résolu image par image par lib/point.js dans Chromium
    r = navigateur("resoudre", str(IMAGES))
    res = [{"image": k, "t": round(k / FPS, 6), "x": x, "y": y, "d": d, "couleur": c, "dx": dx} for k, x, y, d, c, dx in r["images"]]
    ecrire_json("point-resolu.json", {"unite": "par image ; t en s film ; x, y centre en px ; d diamètre ; pan conseillé = 0,6 × (x − 540)/540",
                                      "moteur": r["moteur"], "images": res})

    # 3 bis. les pages de sous-titres de la bible, posées par TEXTE.poser (règle 8 prouvée, instants par mot)
    pg = navigateur("pages")["pages"]
    D["pages"] = [{"scene": p["scene"], "extrait": p["extrait"], "depuis": p["depuis"], "lignes": p["lignes"],
                   "mots": [{k: m[k] for k in ("texte", "rang", "t", "image", "local", "fin_voix")} for m in p["mots"]]} for p in pg]
    ecrire_json("pages.json", {"unite": "t = attaque du 1er mot dit de l'unité (s film) ; local = t arrondi à l'image − début de la scène ; fin_voix = fin du dernier mot dit (s film)",
                               "note": "DÉRIVÉ de mots.json par TEXTE.poser (lib/texte.js) : lecture seule. Une scène pose ses lignes avec TEXTE.poser(el, lignes, {extrait, depuis}).",
                               "pages": D["pages"]})
    ecrire_js()
    # appel.json (nom de la bible) : les extraits, le texte dit et les pages montrées, pour les contrôles
    ecrire_json("appel.json", {"note": "vue de son/dialogue.json + pages ; texte_dit = transcription d'origine, texte_montre = pages de la bible posées par TEXTE.poser (sous-suites prouvées)",
                               "extraits": [dict({k: e[k] for k in ("id", "locuteur", "source", "source_in", "source_out", "original_in", "original_out",
                                                                    "film_in", "film_out", "motif")},
                                                 texte_dit=e["texte"],
                                                 texte_montre=[" / ".join(p["lignes"]) for p in D["pages"] if p["extrait"] == e["id"]])
                                            for e in dialogue["extraits"]]})

    # 4. contrôles
    err = []
    def ecart(a, b):
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))
    e0 = ecart((res[0]["x"], res[0]["y"]), (mesures["s1"]["centre"]["x"], mesures["s1"]["centre"]["y"]))
    e1140 = ecart((res[1140]["x"], res[1140]["y"]), (mesures["s7"]["centre"]["x"], mesures["s7"]["centre"]["y"]))
    if e0 > 0.5: err.append(f"image 0 : écart {e0:.2f} px au point final de s1")
    if e1140 > 0.5: err.append(f"image 1140 : écart {e1140:.2f} px à #mot-pt")
    if abs(res[1140]["d"] - 30.8) > 0.3: err.append(f"image 1140 : diamètre {res[1140]['d']}")
    for nom, yl in (("contact_neuf", "y_09"), ("contact_dix", "y_10"), ("contact_onze", "y_11"), ("contact_retour_neuf", "y_09")):
        i = ev[nom]["image"]
        if abs(res[i]["y"] - pt["reperes"][yl]) > 0.5: err.append(f"{nom} image {i} : y {res[i]['y']} ≠ {pt['reperes'][yl]}")
    # Nyquist : aucune alternance à 2 images dans les décalages appliqués
    dxs = [p["dx"] for p in res]
    for k in range(2, len(dxs)):
        if dxs[k] != 0 and dxs[k - 1] != 0 and np.sign(dxs[k]) == -np.sign(dxs[k - 1]):
            err.append(f"alternance à 2 images en {k}")
            break
    print(f"image 0 : {res[0]['x']}, {res[0]['y']} (écart {e0:.3f} px) ; image 1140 : {res[1140]['x']}, {res[1140]['y']} "
          f"d {res[1140]['d']} (écart {e1140:.3f} px)")
    for nom in ("contact_neuf", "contact_dix", "contact_onze", "contact_retour_neuf", "ecriture_debut", "ecriture_fin",
                "bulle_et_vibreur", "signature_re_contact"):
        print(f"  {nom:22s} {ev[nom]['t']:8.4f} s  image {ev[nom]['image']}")
    print(f"voixX : images {vx['image0']} → {vx['image1']}, x {vx['x'][0]} → {vx['x'][-1]}")
    print("\n".join("⚠ " + e for e in err) or "contrôles : ok")
    print(f"→ {DON / 'donnees.js'} ({(DON / 'donnees.js').stat().st_size} o)")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
