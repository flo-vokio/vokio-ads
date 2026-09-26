#!/usr/bin/env python3
"""Contrôles objectifs du film livré (bible.controles), sur le MP4 RENDU et sur le DOM du même moteur.

    python3 outils/controles.py [film.mp4] [dossier_sortie]

Par défaut : /root/vokio-uploads/videos/showcase/le-point-sur-le-i.mp4 → …/showcase/controles/.
Rien n'est écrit dans le projet (sorties dans le dossier de contrôle). Contrôles :
  1  flux (ffprobe) : h264 1080×1920 30 i/s 1 305 images 43,50 s ; aac 48 kHz stéréo
  2  planches : 1 image / 0,5 s (planche.png) ; images de la bible (planche-bible.png) ; raccords ±3 images
  3  éléments simultanés ≤ 3 (DOM, toutes les images ; le point posé sur le ı = le logo avec le mot)
  4  textes : corps ≥ 36 px, bas < 1 500, 70 ≤ x ≤ 1 010 au repos ; 0 mono en capitales
  5  sous-suite : chaque page est une sous-suite des mots dits de son extrait
  6  interdits : « — », « Alauzet », numéro de téléphone (index.html, compositions/, donnees/*.json)
  7  synchro : image d'apparition de chaque mot dit (MP4) contre son attaque (mots.json), ≤ 2 images ;
     attaques des cues du son dans l'audio du MP4 ; décalage audio MP4 / son/mix.wav
  8  géométrie du point sur le MP4 : images 0 et 1140 (≤ 0,5 px, diamètre 30,8 ± 0,3), contacts 620 / 643 / 666 / 731
  10 solaire : hors du point, aucun pixel solaire (ΔRVB < 40) ; bloc admis de 762 à 942
  11 audio du MP4 : −14 ± 0,5 LUFS, crête vraie ≤ −1 dBTP, silences < −90 dBFS, tonalité dès 20 ms
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJET = Path(__file__).resolve().parents[1]
FILM = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/root/vokio-uploads/videos/showcase/le-point-sur-le-i.mp4")
SORTIE = Path(sys.argv[2]) if len(sys.argv) > 2 else FILM.parent / "controles"
SORTIE.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1080, 1920, 30
PAPIER = np.array([244, 241, 232], float)
SOLAIRE = np.array([239, 164, 36], float)
ENCRE = np.array([38, 32, 25], float)
POLICE = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
rapport = {"film": str(FILM)}
echecs = []


def note(cle, ok, detail):
    rapport.setdefault("controles", {})[cle] = {"ok": bool(ok), "detail": detail}
    print(("[ok]    " if ok else "[ÉCHEC] ") + cle + " : " + (detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)[:600]))
    if not ok:
        echecs.append(cle)


def lire_json(p):
    return json.loads((PROJET / p).read_text())


D_SCENES = lire_json("donnees/scenes.json")
D_EV = lire_json("donnees/evenements.json")
RESOLU = {e["image"]: e for e in lire_json("donnees/point-resolu.json")["images"]}
MOTS = lire_json("donnees/mots.json")["mots"]
AGENDA = lire_json("donnees/agenda-geo.json")
MESURES = lire_json("donnees/mesures.json")

# ── 1. Flux ──
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(FILM)],
                               capture_output=True, text=True).stdout)
v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
a = [s for s in pr["streams"] if s["codec_type"] == "audio"]
flux = {"video": f'{v["codec_name"]} {v["width"]}x{v["height"]} {v["r_frame_rate"]} {v.get("nb_frames")} images {float(v["duration"]):.3f} s',
        "audio": [f'{s["codec_name"]} {s["sample_rate"]} Hz {s["channels"]} canaux {float(s["duration"]):.3f} s {int(s.get("bit_rate", 0)) // 1000} kb/s' for s in a],
        "debut_video": v.get("start_time"), "debut_audio": a[0].get("start_time") if a else None}
note("1 flux", v["codec_name"] == "h264" and v["width"] == W and v["height"] == H and v["r_frame_rate"] == "30/1"
     and int(v.get("nb_frames", 0)) == 1305 and abs(float(v["duration"]) - 43.5) <= 0.02 and len(a) == 1
     and a[0]["codec_name"] == "aac" and a[0]["sample_rate"] == "48000" and a[0]["channels"] == 2, flux)

# ── 6. Interdits textuels ──
fichiers = [PROJET / "index.html"] + sorted((PROJET / "compositions").glob("*.html")) + sorted((PROJET / "donnees").glob("*.json"))
tel = re.compile(r"(?<![0-9.])0[1-9]( ?[0-9]{2}){4}(?![0-9])")
trouves = []
for f in fichiers:
    t = f.read_text()
    for motif, nom in (("—", "cadratin"), ("Alauzet", "Alauzet")):
        if motif in t:
            trouves.append(f"{f.name}: {nom} ×{t.count(motif)}")
    for m in tel.finditer(t):
        trouves.append(f"{f.name}: numéro « {m.group(0)} »")
note("6 interdits", not trouves, trouves or f"0 cadratin, 0 Alauzet, 0 numéro dans {len(fichiers)} fichiers")

# ── 5. Sous-suite ──
def cle(m):
    import unicodedata
    m = m.replace("’", "'").lower()
    m = "".join(c for c in unicodedata.normalize("NFD", m) if unicodedata.category(c) != "Mn")
    return re.sub(r"^['\-]+|['\-]+$", "", re.sub(r"[^a-z0-9'\-]", "", m))

pages = lire_json("donnees/pages.json")
pages = pages["pages"] if isinstance(pages, dict) else pages
fautes = []
for p in pages:
    dits = [w["cle"] for w in MOTS if w["extrait"] == p["extrait"]]
    k = p.get("depuis", 0)
    for ligne in p["lignes"]:
        for u in ligne.replace("\u00a0", " ").replace("\u202f", " ").split(" "):
            c = cle(u)
            if not c:
                continue
            while k < len(dits) and dits[k] != c:
                k += 1
            if k >= len(dits):
                fautes.append(f'{p["extrait"]} « {u} »')
                break
            k += 1
note("5 sous-suite", not fautes, fautes or f"{len(pages)} pages, toutes sous-suites du texte dit")

# ── 3 et 4. DOM, toutes les images ──
dom_json = SORTIE / "dom.json"
subprocess.run(["/root/.pwtest/bin/python", str(PROJET / "outils" / "controles_dom.py"), str(dom_json)], check=True,
               stderr=subprocess.DEVNULL)
DOM = json.loads(dom_json.read_text())
T_LOGO = D_EV["signature_re_contact"]["image"]
trop, comptes = [], {}
for im in DOM["images"]:
    els = [e.split("@")[0] for e in im["elements"]]
    n = len(els)
    if im["image"] >= T_LOGO and "mot" in els and "point" in els:
        n -= 1      # le point posé sur le ı EST le point du logo : un seul élément (bible, élément 1 de s7)
    comptes[im["image"]] = n
    if n > 3:
        trop.append((im["image"], im["elements"]))
note("3 éléments ≤ 3", not trop and not DOM["erreurs_page"],
     trop[:10] or {"max": max(comptes.values()), "images_a_3": sum(1 for c in comptes.values() if c == 3),
                   "erreurs_page": DOM["erreurs_page"]})

petits, bas, marges, mono = set(), [], set(), set()
for im in DOM["images"]:
    for t in im["textes"]:
        if t["corps"] < 36:
            petits.add((t["element"], t["texte"], t["corps"]))
        if "Mono" in t["famille"] and re.search(r"[A-Z]", t["texte"]) and t["texte"] == t["texte"].upper():
            mono.add(t["texte"])
        au_repos = not t["transforme"] and t["opacite"] > 0.99
        if au_repos and t["y1"] >= 1500 and t["y0"] < H:
            bas.append((im["image"], t["element"], t["texte"], t["y1"]))
        if au_repos and (t["boite"]["x0"] < 70 - 0.5 or t["boite"]["x1"] > 1010 + 0.5):
            marges.add((t["element"], t["texte"], t["boite"]["x0"], t["boite"]["x1"]))
max_bas = max((t["boite"]["y1"] for im in DOM["images"] for t in im["textes"] if not t["transforme"] and t["opacite"] > .99), default=0)
note("4 textes", not petits and not bas and not marges and not mono,
     {"corps<36": sorted(petits)[:8], "bas>=1500 au repos": bas[:8], "hors marges": sorted(marges)[:8], "mono capitales": sorted(mono),
      "bas maximal au repos": max_bas,
      "corps vus": sorted({t["corps"] for im in DOM["images"] for t in im["textes"]})})

# ── MP4 : décodage image par image (RVB), mesures en flux ──
def disque(cx, cy, r):
    x0, x1 = int(np.floor(cx - r)), int(np.ceil(cx + r)) + 1
    y0, y1 = int(np.floor(cy - r)), int(np.ceil(cy + r)) + 1
    yy, xx = np.mgrid[y0:y1, x0:x1]
    return x0, y0, x1, y1, (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r, xx + 0.5, yy + 0.5


def centre_point(img, n):
    """Centre et diamètre du point sur l'image n : barycentre de la couverture (projection de chaque pixel
    entre le papier et la couleur attendue du point), dans un disque autour de la position attendue."""
    e = RESOLU[n]
    cible = np.array([int(e["couleur"][k:k + 2], 16) for k in (1, 3, 5)], float)
    r = max(12.5, e["d"] / 2 + 4)
    x0, y0, x1, y1, m, xx, yy = disque(e["x"], e["y"], r)
    # sur la LUMINANCE : le h264 4:2:0 étale la chrominance sur 2 px, pas la luminance (sinon diamètre +0,4 px)
    luma = np.array([0.299, 0.587, 0.114])
    pix = img[y0:y1, x0:x1].astype(float) @ luma
    yp, yc = PAPIER @ luma, cible @ luma
    alpha = np.clip((yp - pix) / (yp - yc), 0, 1) * m
    s = alpha.sum()
    if s < 1:
        return None
    return {"x": float((alpha * xx).sum() / s), "y": float((alpha * yy).sum() / s), "d": float(2 * np.sqrt(s / np.pi)),
            "attendu": [e["x"], e["y"], e["d"]]}


mots_dom = DOM["mots"]
for w in mots_dom:
    w["serie"] = {}
IMAGES_POINT = {0, 1, 3, 60, 125, 150, 299, 400, 516, 620, 643, 666, 731, 762, 783, 900, 998, 1000, 1002, 1020, 1122, 1135, 1140, 1200, 1304}
BIBLE = [0, 45, 90, 126, 150, 216, 300, 333, 432, 480, 540, 573, 626, 647, 675, 720, 762, 783, 870, 942, 960, 998, 1020, 1098, 1116, 1140, 1170, 1215, 1290]
RACCORDS = [135, 312, 519, 756, 941, 1107]
autour = {b + k for b in RACCORDS for k in range(-3, 4)}
gardees = {}
points = {}
solaire_hors = []
diffs = []
prec = None
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(FILM), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
n = 0
taille = W * H * 3
while True:
    buf = proc.stdout.read(taille)
    if len(buf) < taille:
        break
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    gris = img.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    # mots : encre dans la boîte de repos (élargie de 2 px, et de 14 px vers le bas : le mot monte de 16 px)
    for w in mots_dom:
        if w["image"] - 14 <= n <= w["image"] + 20:
            x0, y0 = int(w["x0"]) - 2, int(w["y0"]) - 2
            x1, y1 = int(np.ceil(w["x1"])) + 2, int(np.ceil(w["y1"])) + 14
            w["serie"][n] = int((gris[y0:y1, x0:x1] < 241 - 40).sum())
    # point
    if n in IMAGES_POINT or n in autour or (613 <= n <= 736) or (1128 <= n <= 1145) or (995 <= n <= 1013):
        points[n] = centre_point(img, n)
    # solaire hors du point
    f = img.astype(np.int16)
    msk = (np.abs(f[..., 0] - 239) < 40) & (np.abs(f[..., 1] - 164) < 40) & (np.abs(f[..., 2] - 36) < 40)
    e = RESOLU[n]
    if msk.any():
        ys, xs = np.nonzero(msk)
        hors = (xs + .5 - e["x"]) ** 2 + (ys + .5 - e["y"]) ** 2 > (e["d"] / 2 + 3) ** 2
        if 762 <= n <= 942:   # le bloc (sa teinte) est admis dans sa boîte
            B = AGENDA["bloc"]
            dans_bloc = (xs >= B["x0"] - 2) & (xs <= B["x1_visible"] + 2) & (ys >= B["y0"] - 2) & (ys <= B["y1"] + 2)
            hors &= ~dans_bloc
        if hors.sum():
            solaire_hors.append((n, int(hors.sum())))
    # différence avec l'image précédente (raccords)
    petit = gris[::4, ::4]
    if prec is not None:
        diffs.append((n, float(np.abs(petit - prec).mean()), int((np.abs(petit - prec) > 12).sum())))
    prec = petit
    if n in BIBLE or n in autour or n % 15 == 0 or n in (1140, 1122, 1129):
        gardees[n] = img.copy()
    n += 1
proc.wait()
rapport["images_decodees"] = n

# ── 2. Planches ──
def planche(nums, fichier, colonnes, echelle, titre=None):
    fnt = ImageFont.truetype(POLICE, 22)
    w, h = int(W * echelle), int(H * echelle)
    lignes = (len(nums) + colonnes - 1) // colonnes
    P = Image.new("RGB", (colonnes * (w + 6) + 6, lignes * (h + 6) + 6), (150, 150, 150))
    d = ImageDraw.Draw(P)
    for i, k in enumerate(nums):
        if k not in gardees:
            continue
        x, y = 6 + (i % colonnes) * (w + 6), 6 + (i // colonnes) * (h + 6)
        P.paste(Image.fromarray(gardees[k]).resize((w, h), Image.LANCZOS), (x, y))
        d.text((x + 6, y + 4), f"{k} · {k / 30:.2f}s", font=fnt, fill=(192, 69, 44))
    P.save(fichier)
    return str(fichier)

pl = {"planche": planche([k for k in range(0, 1305, 15)], SORTIE / "planche-0,5s.png", 10, 0.25),
      "bible": planche(BIBLE, SORTIE / "planche-bible.png", 10, 0.25)}
for b in RACCORDS:
    pl[f"raccord-{b}"] = planche(list(range(b - 3, b + 4)), SORTIE / f"raccord-{b}.png", 7, 0.3)
rapport["planches"] = pl

rac = {}
for b in RACCORDS:
    rac[b] = [(k, round(m, 2), c) for (k, m, c) in diffs if b - 3 <= k <= b + 3]
rapport["raccords_diff"] = rac

# ── 7. Synchro des mots ──
# L'appelant de C2 (s3) et de C3 (s4) s'écrit LIGNE PAR LIGNE, d'un bloc, au premier mot dit de chaque ligne
# (bible) : seul ce premier mot est comparé à son attaque ; les autres montent avec lui (rapportés à part).
PAR_LIGNE = {"C2", "C3"}
meneurs = {}
for w in mots_dom:
    if w["extrait"] in PAR_LIGNE:
        k = (w["scene"], w["extrait"], round(w["y0"]))
        if k not in meneurs or w["rang"] < meneurs[k]["rang"]:
            meneurs[k] = w
for w in mots_dom:
    w["porte_par_la_ligne"] = w["extrait"] in PAR_LIGNE and meneurs[(w["scene"], w["extrait"], round(w["y0"]))] is not w
sync = []
for w in mots_dom:
    s = w["serie"]
    if not s:
        continue
    ks = sorted(s)
    haut = max(s[k] for k in ks if w["image"] <= k <= w["image"] + 12) or 1
    derniere_vide = None
    for k in ks:
        if k > w["image"] + 8:
            break
        if s[k] < 0.03 * haut:
            derniere_vide = k
    apparait = derniere_vide + 1 if derniere_vide is not None else None
    ecart = None if apparait is None else apparait - w["image"]
    if w["porte_par_la_ligne"]:
        # le mot monte avec sa ligne : on mesure l'apparition de la ligne (encre dès le début de sa fenêtre)
        apparait = min((k for k in ks if s[k] >= 0.03 * haut), default=None) if derniere_vide is None else apparait
    sync.append({"mot": w["texte"], "extrait": w["extrait"], "rang": w["rang"], "par_ligne": w["porte_par_la_ligne"],
                 "attaque_s": w["debut"], "image_attaque": w["image"],
                 "image_apparition": apparait, "ecart_images": ecart,
                 "ecart_ms": None if apparait is None else round((apparait / 30 - w["debut"]) * 1000, 1)})
cles_bible = [("A1", 0), ("A2A3", 6), ("A2A3", 8), ("A2A3", 11), ("C3", 2), ("A4", 0), ("A4", 6), ("A4", 12), ("A4", 18), ("A4", 21), ("A4", 23)]
choisis = [x for x in sync if (x["extrait"], x["rang"]) in cles_bible]
individuels = [x for x in sync if not x["par_ligne"]]
mauvais = [x for x in individuels if x["ecart_images"] is None or abs(x["ecart_images"]) > 2]
rapport["synchro_mots"] = sync
note("7a mots à l'écran vs mots dits (≤ 2 images)", not mauvais and len(choisis) >= 6,
     {"mots_mesures": len(individuels), "hors_tolerance": mauvais[:6],
      "ecarts_images": {str(e): sum(1 for x in individuels if x["ecart_images"] == e) for e in sorted({x["ecart_images"] for x in individuels if x["ecart_images"] is not None})},
      "portes_par_leur_ligne (appelant, bible)": [(x["mot"], x["image_attaque"], x["image_apparition"]) for x in sync if x["par_ligne"]],
      "repères": [(x["mot"], x["image_attaque"], x["image_apparition"], x["ecart_ms"]) for x in choisis]})

# ── 8. Géométrie du point sur le MP4 ──
def ecart(n):
    p = points.get(n)
    if not p:
        return None
    return {"x": round(p["x"], 2), "y": round(p["y"], 2), "d": round(p["d"], 2),
            "dx": round(p["x"] - p["attendu"][0], 2), "dy": round(p["y"] - p["attendu"][1], 2)}

geo = {n: ecart(n) for n in (0, 620, 643, 666, 731, 783, 1000, 1140)}
H9, H10, H11 = AGENDA["heures"]["09:00"], AGENDA["heures"]["10:00"], AGENDA["heures"]["11:00"]
ok8 = (geo[0] and abs(geo[0]["dx"]) <= .5 and abs(geo[0]["dy"]) <= .5
       and geo[1140] and abs(geo[1140]["dx"]) <= .5 and abs(geo[1140]["dy"]) <= .5 and abs(geo[1140]["d"] - 30.8) <= .3
       and all(geo[k] and abs(geo[k]["y"] - hy) <= .5 for k, hy in ((620, H9), (643, H10), (666, H11), (731, H9))))
note("8 géométrie du point (MP4)", ok8, {**{str(k): v for k, v in geo.items()},
     "attendu_1140": [MESURES["s7"]["centre"]["x"], MESURES["s7"]["centre"]["y"], MESURES["s7"]["diametre"]],
     "filets": [H9, H10, H11]})
rapport["point_mesure"] = {str(k): ecart(k) for k in sorted(points)}

note("10 solaire hors du point", not solaire_hors, solaire_hors[:12] or "aucun pixel solaire hors du point (bloc admis de 762 à 942)")

# ── 11 et 7b. Audio du MP4 ──
def ebur(chemin):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(chemin), "-map", "0:a", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    lra = float(re.findall(r"LRA:\s+(-?[\d.]+) LU", r)[-1])
    return I, tp, lra


def pcm(chemin):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(chemin), "-map", "0:a", "-f", "f32le", "-ac", "2", "-ar", "48000", "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2)


I, tp, lra = ebur(FILM)
A = pcm(FILM)
M = pcm(PROJET / "son" / "mix.wav")
SR = 48000


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x.astype(np.float64) ** 2)) + 1e-12)

sil1 = rms_db(A[int(36.70 * SR):int(37.38 * SR)])
sil2 = rms_db(A[int(43.22 * SR):int(43.50 * SR)])
ton = rms_db(A[0:int(0.02 * SR)])
# décalage MP4 / mix.wav par intercorrélation (fenêtre 4,0 → 8,0 s, ±50 ms)
seg_m = M[int(4 * SR):int(8 * SR), 0].astype(np.float64)
best = None
for dec in range(-2400, 2401, 1):
    s0 = int(4 * SR) + dec
    seg_a = A[s0:s0 + len(seg_m), 0].astype(np.float64)
    if len(seg_a) < len(seg_m):
        continue
    c = float(seg_a @ seg_m)
    if best is None or c > best[1]:
        best = (dec, c)
decalage = best[0]
n_ = min(len(A), len(M))
residu = rms_db(A[:n_] - M[:n_]) if decalage == 0 else None


def lire_wav(chemin):
    return pcm(chemin)


def attaque_seuil(x, t, avant=0.05):
    """Bible, contrôle 7 : premier échantillon au-dessus de −40 dBFS (ou 12 dB au-dessus du fond qui précède)
    après t − 50 ms, sur une piste où l'attaque sort du silence."""
    m = np.abs(x).max(axis=1)
    fond = np.sqrt(np.mean(m[int((t - 0.20) * SR):int((t - avant) * SR)] ** 2) + 1e-20)
    seuil = max(10 ** (-40 / 20), fond * 10 ** (12 / 20))
    i0 = int((t - avant) * SR)
    k = np.nonzero(m[i0:i0 + int(0.2 * SR)] > seuil)[0]
    return None if not len(k) else (i0 + int(k[0])) / SR


def attaque_bande(x, t, f0, larg):
    """Attaque d'une note qui entre pendant que la précédente sonne encore : enveloppe de la seule bande
    f0 ± larg (FFT), premier instant où elle dépasse le fond + 20 % de la montée."""
    s = x[int((t - 0.4) * SR):int((t + 0.3) * SR)].mean(axis=1).astype(np.float64)
    F = np.fft.rfft(s)
    f = np.fft.rfftfreq(len(s), 1 / SR)
    F[(f < f0 - larg) | (f > f0 + larg)] = 0
    b = np.fft.irfft(F, len(s))
    k = int(0.003 * SR)
    env = np.sqrt(np.convolve(b ** 2, np.ones(k) / k, "same"))
    o = int(0.4 * SR)
    fond = env[o - int(0.3 * SR):o - int(0.06 * SR)].max()
    pic = env[o:o + int(0.12 * SR)].max()
    j = np.nonzero(env[o - int(0.06 * SR):] > fond + 0.2 * (pic - fond))[0]
    return None if not len(j) else (o - int(0.06 * SR) + int(j[0])) / SR + t - 0.4


ST_SFX = lire_wav(PROJET / "son" / "stems" / "sfx.wav")
ST_SIG = lire_wav(PROJET / "son" / "stems" / "signature.wav")
mesures_cues = [
    ("décroché (clic)", "sfx", D_EV["decroche"]["t"], attaque_seuil(ST_SFX, D_EV["decroche"]["t"])),
    ("toucher 09:00", "sfx", D_EV["contact_neuf"]["t"], attaque_seuil(ST_SFX, D_EV["contact_neuf"]["t"])),
    ("toucher 10:00", "sfx", D_EV["contact_dix"]["t"], attaque_seuil(ST_SFX, D_EV["contact_dix"]["t"])),
    ("toucher 11:00", "sfx", D_EV["contact_onze"]["t"], attaque_seuil(ST_SFX, D_EV["contact_onze"]["t"])),
    ("retour 09:00", "sfx", D_EV["contact_retour_neuf"]["t"], attaque_seuil(ST_SFX, D_EV["contact_retour_neuf"]["t"])),
    ("écriture (la)", "signature", D_EV["ecriture_debut"]["t"], attaque_seuil(ST_SIG, D_EV["ecriture_debut"]["t"])),
    ("écriture (sol)", "signature", D_EV["ecriture_debut"]["t"] + 0.24, attaque_bande(ST_SIG, D_EV["ecriture_debut"]["t"] + 0.24, 392, 30)),
    ("vibreur", "sfx", D_EV["bulle_et_vibreur"]["t"], attaque_seuil(ST_SFX, D_EV["bulle_et_vibreur"]["t"])),
    ("raccroché", "sfx", D_EV["raccroche"]["t"], attaque_seuil(ST_SFX, D_EV["raccroche"]["t"])),
    ("signature la", "signature", D_EV["signature_la"]["t"], attaque_seuil(ST_SIG, D_EV["signature_la"]["t"])),
    ("signature sol", "signature", D_EV["signature_sol"]["t"], attaque_bande(ST_SIG, D_EV["signature_sol"]["t"], 392, 30)),
    ("signature ré", "signature", D_EV["signature_re_contact"]["t"], attaque_bande(ST_SIG, D_EV["signature_re_contact"]["t"], 587.33, 40)),
    ("signature la, sur le MP4", "mp4", D_EV["signature_la"]["t"], attaque_seuil(A, D_EV["signature_la"]["t"])),
    ("signature ré, sur le MP4", "mp4", D_EV["signature_re_contact"]["t"], attaque_bande(A, D_EV["signature_re_contact"]["t"], 587.33, 40)),
]
mesure_cues = {}
for nom, piste, t, ta in mesures_cues:
    mesure_cues[nom] = {"piste": piste, "attendu_s": round(t, 4), "mesure_s": None if ta is None else round(ta, 4),
                        "ecart_ms": None if ta is None else round((ta - t) * 1000, 1),
                        "image_attendue": int(round(t * 30)), "image_du_son": None if ta is None else int(round(ta * 30))}
ok11 = abs(I + 14) <= 0.5 and tp <= -1.0 and sil1 < -90 and sil2 < -90 and ton > -40
note("11 audio du MP4", ok11, {"LUFS": I, "crete_vraie_dBTP": tp, "LRA": lra, "silence_36.70-37.38_dB": round(sil1, 1),
                               "silence_43.22-43.50_dB": round(sil2, 1), "tonalite_20ms_dB": round(ton, 1)})
ok7b = decalage == 0 and all(c["ecart_ms"] is not None and abs(c["ecart_ms"]) <= 33.4 for c in mesure_cues.values())
note("7b son : décalage et attaques des cues", ok7b, {"decalage_mp4_vs_mix_echantillons": decalage,
     "residu_aac_dB": None if residu is None else round(residu, 1), "cues": mesure_cues})

# le contact sur le ı, à l'image du ré
re_ = mesure_cues["signature ré, sur le MP4"]
p1140 = geo[1140]
p1139 = ecart(1139)
# atterrissage visible : première image où le point est à ≤ 0,5 px de sa position de contact (ease power3.out)
pose = next((k for k in range(1128, 1141) if points.get(k) and abs(points[k]["y"] - points[1140]["y"]) <= 0.5), None)
note("7c contact du point sur le ı = image du ré", p1140 is not None and abs(p1140["dx"]) <= .5 and abs(p1140["dy"]) <= .5
     and re_["image_du_son"] == 1140,
     {"ré_mesuré_s": re_["mesure_s"], "image_du_ré": re_["image_du_son"], "point_1140": p1140,
      "point_a_0,5px_des_l_image": pose,
      "y_1134_1140": [round(points[k]["y"], 2) for k in range(1134, 1141) if points.get(k)]})

rapport["echecs"] = echecs
(SORTIE / "controles.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=str))
print(f"\n{len(echecs)} échec(s) : {echecs}" if echecs else "\nTous les contrôles passent.")
print(f"rapport : {SORTIE / 'controles.json'}")
