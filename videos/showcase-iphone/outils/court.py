#!/usr/bin/env python3
"""Monte une VERSION COURTE d'un film rendu (pub Meta, bumper long…) à partir d'une recette de segments, coupes en MESURES
ENTIÈRES dans les vrais blancs : usage en une ligne :

    python3 outils/court.py courts/9x16-court.json --image longue.mp4 [--mix mix.wav] [--sortie DOSSIER] [--verifier-seulement]

  Recette (courts/<nom>.json) : "segments" = [[image_debut, image_fin), …] dans le film COURANT (1 502 images) ; "racine" = le
  projet de format dont on lit les mots (donnees/mots.json) ; "mix" = la bande son du film long (défaut : le mix hybride) ;
  "fondu_ms" = fondu enchaîné à puissance constante centré sur chaque coupe ; "sortie" = nom du film livré.
  Règles contrôlées AVANT de fabriquer (code 1 sinon) :
    - chaque coupe interne retire un nombre ENTIER de mesures (92 images, 78,26 BPM : la musique reste sur sa grille, même
      phase dans la mesure des deux côtés ; seul le début du film, la tête, est libre) ;
    - chaque bord de coupe est dans un blanc du vrai appel : à ≥ "marge_mots_ms" du mot le plus proche (fondu compris) ;
    - le texte DIT du court = une sous-suite des mots du film long (on retire, on n'ajoute ni ne déplace rien).
  Fabrique (dans /dev/shm, puis --sortie) :
    1. <nom>-mix.wav : le mix long recoupé (échantillons du mix validé, aucune retouche : seuls les fondus de coupe), puis un
       GAIN linéaire unique vers −14 LUFS (ebur128) ; la crête vraie doit rester ≤ −1 dBTP (sinon code 1, rien de limité) ;
    2. <nom>-image.mp4 : les images des segments (sélection à l'image près dans le rendu long, sans perte de préférence),
       H.264 High crf 16 bt709 ; puis outils/livrer.py pose le mix (AAC 256k, faststart, sonie contrôlée) → <nom>.mp4 ;
    3. <nom>-montage.json : table des coupes (temps long ↔ court), mots gardés avec leur instant dans le court, mesures ;
       <nom>-mots.json : les mots au format de donnees/mots.json, temps du court (pour outils/ausculter.py --mots) ;
       <nom>-planche.png : une image par seconde.
  --verifier-seulement : n'imprime que le contrôle de la recette (instantané, pour chercher des coupes).
Idempotent. N'écrit rien dans le projet.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

PROJET = Path(__file__).resolve().parents[1]
SON = Path("/opt/vokio-ads/videos/showcase")
FPS = 30
SR = 48000
ECH = SR // FPS            # 1 600 échantillons par image
MESURE = 92                # images par mesure (4 temps de 23)


def sh(*c, capture=False):
    r = subprocess.run([str(x) for x in c], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"échec : {' '.join(map(str, c))}\n{r.stderr[-2000:]}")
    return r.stdout + r.stderr if capture else None


def sonie(chemin):
    out = sh("ffmpeg", "-hide_banner", "-nostats", "-i", chemin, "-af", "ebur128=peak=true", "-f", "null", "-", capture=True)
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)[-1])
    lra = float(re.findall(r"LRA:\s+(-?[\d.]+) LU", out)[-1])
    return i, tp, lra


def lire_wav(chemin):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(chemin), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def ecrire_wav(chemin, x):
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                        "-c:a", "pcm_s24le", str(chemin)], input=x.astype(np.float32).tobytes())
    if p.returncode:
        sys.exit("écriture wav impossible")


def verifier(rec, mots):
    seg = rec["segments"]
    marge = rec.get("marge_mots_ms", 60) / 1000 + rec.get("fondu_ms", 50) / 2000
    erreurs, coupes = [], []
    for (a0, a1), (b0, b1) in zip(seg, seg[1:]):
        retire = b0 - a1
        t_a, t_b = a1 / FPS, b0 / FPS
        c = {"de_image": a1, "a_image": b0, "de_s": round(t_a, 4), "a_s": round(t_b, 4), "images_retirees": retire,
             "mesures": retire / MESURE, "phase_dans_la_mesure": (a1 - 91) % MESURE}
        if retire <= 0 or retire % MESURE:
            erreurs.append(f"coupe {a1} → {b0} : {retire} images, pas un nombre entier de mesures ({MESURE})")
        for t, cote in ((t_a, "avant"), (t_b, "après")):
            proche = min(mots, key=lambda m: min(abs(m["debut"] - t), abs(m["fin"] - t)) if not (m["debut"] <= t <= m["fin"]) else -1)
            dedans = proche["debut"] - marge < t < proche["fin"] + marge
            ecart = 0.0 if proche["debut"] <= t <= proche["fin"] else min(abs(proche["debut"] - t), abs(proche["fin"] - t))
            c[f"mot_proche_{cote}"] = {"texte": proche["texte"], "ecart_ms": round(ecart * 1000)}
            if dedans:
                erreurs.append(f"coupe {a1} → {b0} ({cote}, {t:.3f} s) : à {ecart*1000:.0f} ms de « {proche['texte']} » "
                               f"(marge {marge*1000:.0f} ms, fondu compris)")
        coupes.append(c)
    for a, b in seg:
        if not 0 <= a < b:
            erreurs.append(f"segment {a}-{b} invalide")
    # mots gardés, temps du court
    garde, t0 = [], 0
    for a, b in seg:
        for m in mots:
            if a / FPS <= m["debut"] and m["fin"] <= b / FPS:
                garde.append(dict(m, debut_long=m["debut"], fin_long=m["fin"], debut=round(m["debut"] - a / FPS + t0 / FPS, 4),
                                  fin=round(m["fin"] - a / FPS + t0 / FPS, 4), image=int(round((m["debut"] - a / FPS) * FPS)) + t0))
            elif a / FPS < m["fin"] and m["debut"] < b / FPS:
                erreurs.append(f"segment {a}-{b} coupe le mot « {m['texte']} » ({m['debut']:.3f}-{m['fin']:.3f})")
        t0 += b - a
    ordre = [m["debut_long"] for m in garde]
    if ordre != sorted(ordre):
        erreurs.append("les mots gardés ne sont pas dans l'ordre du film long (le texte dit n'est plus une sous-suite)")
    return coupes, garde, t0, erreurs


def monter_son(rec, x):
    """Segments du mix long, fondus enchaînés à puissance constante centrés sur les coupes (aucun autre traitement)."""
    f = int(round(rec.get("fondu_ms", 50) / 1000 * SR)) // 2 * 2
    h = f // 2
    seg = rec["segments"]
    n = sum(b - a for a, b in seg) * ECH
    y = np.zeros((n + 2 * h, 2))
    pos = 0
    for k, (a, b) in enumerate(seg):
        i0, i1 = a * ECH, b * ECH
        premier, dernier = k == 0, k == len(seg) - 1
        j0 = i0 if premier else i0 - h
        j1 = i1 if dernier else i1 + h
        bloc = x[j0:j1].copy()
        if bloc.shape[0] < j1 - j0:
            bloc = np.vstack([bloc, np.zeros((j1 - j0 - bloc.shape[0], 2))])
        w = np.ones(bloc.shape[0])
        if premier:
            fi = int(rec.get("fondu_tete_ms", 10) / 1000 * SR)
            w[:fi] = np.sin(np.linspace(0, np.pi / 2, fi)) ** 2
        else:
            w[:f] = np.sin(np.linspace(0, np.pi / 2, f))
        if not dernier:
            w[-f:] = np.cos(np.linspace(0, np.pi / 2, f))
        o0 = pos + (0 if premier else -h) + h
        y[o0:o0 + bloc.shape[0]] += bloc * w[:, None]
        pos += (b - a) * ECH
    return y[h:h + n]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("recette")
    p.add_argument("--image", help="le rendu LONG (1 502 images) du projet de format, sans perte de préférence (rendre.py --crf 0)")
    p.add_argument("--mix")
    p.add_argument("--sortie", default="/root/vokio-uploads/videos/showcase")
    p.add_argument("--verifier-seulement", action="store_true")
    a = p.parse_args()
    rec_p = Path(a.recette)
    rec = json.loads(rec_p.read_text())
    racine = (PROJET / rec.get("racine", ".")).resolve() if not Path(rec.get("racine", ".")).is_absolute() else Path(rec["racine"])
    mp = racine / "donnees" / "mots.json"
    if not mp.exists():            # un format ne porte pas mots.json : même minutage dans tous les formats (OUTILS.md § 0)
        mp = PROJET / "donnees" / "mots.json"
    mots = json.loads(mp.read_text())["mots"]
    coupes, garde, n_img, erreurs = verifier(rec, mots)
    print(json.dumps({"coupes": coupes, "images": n_img, "duree_s": round(n_img / FPS, 3)}, ensure_ascii=False, indent=1))
    print("texte dit :", " ".join(m["texte"] for m in garde))
    if erreurs:
        print("\n".join("ÉCHEC " + e for e in erreurs))
        sys.exit(1)
    print("recette : ok")
    if a.verifier_seulement:
        return
    nom = rec["nom"]
    mix = Path(a.mix or rec.get("mix") or SON / "son/hybride/mix-hybride.wav")
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir="/dev/shm") as tmp:
        tmp = Path(tmp)
        # 1. son
        x = lire_wav(mix)
        y = monter_son(rec, x)
        brut = tmp / "brut.wav"
        ecrire_wav(brut, y)
        i0, tp0, _ = sonie(brut)
        g = rec.get("lufs", -14.0) - i0
        y2 = y * 10 ** (g / 20)
        son = tmp / f"{nom}-mix.wav"
        ecrire_wav(son, y2)
        i1, tp1, lra1 = sonie(son)
        print(f"son : recoupé {i0:.2f} LUFS / {tp0:.2f} dBTP → gain {g:+.2f} dB → {i1:.2f} LUFS, {tp1:.2f} dBTP, LRA {lra1}")
        if tp1 > rec.get("crete_max_dbtp", -1.0):
            sys.exit(f"ÉCHEC crête vraie {tp1} dBTP > {rec.get('crete_max_dbtp', -1.0)} : rien n'est limité ici, revoir la recette")
        # 2. image
        sel = "+".join(f"between(n\\,{s}\\,{e - 1})" for s, e in rec["segments"])
        img = tmp / f"{nom}-image.mp4"
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", a.image, "-an", "-vf", f"select='{sel}',setpts=N/{FPS}/TB",
           "-r", FPS, "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", 16, "-preset", "slow",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", img)
        nb = int(sh("ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries",
                    "stream=nb_read_frames", "-of", "csv=p=0", img, capture=True).split()[0])
        if nb != n_img:
            sys.exit(f"ÉCHEC image : {nb} images au lieu de {n_img}")
        film = tmp / rec["sortie"]
        liv = tmp / f"{nom}-livraison.json"
        sh(sys.executable, PROJET / "outils/livrer.py", img, son, "-o", film, "--json", liv)
        # 3. relevés
        t = 0
        for c, (s, e) in zip([None] + coupes, rec["segments"]):
            if c:
                c["instant_dans_le_court_s"] = round(t / FPS, 3)
            t += e - s
        (tmp / f"{nom}-mots.json").write_text(json.dumps({"unite": "s (temps du court)", "source": str(mp),
                                                          "mots": garde}, ensure_ascii=False, indent=1) + "\n")
        montage = {"recette": str(rec_p.resolve()), "image_longue": str(a.image), "mix_long": str(mix), "images": n_img,
                   "duree_s": round(n_img / FPS, 4), "segments": rec["segments"], "coupes": coupes,
                   "son": {"lufs_recoupe": i0, "gain_db": round(g, 3), "lufs": i1, "crete_dbtp": tp1, "lra": lra1},
                   "livraison": json.loads(liv.read_text()), "texte_dit": " ".join(m["texte"] for m in garde)}
        (tmp / f"{nom}-montage.json").write_text(json.dumps(montage, ensure_ascii=False, indent=1) + "\n")
        pl = tmp / f"{nom}-planche.png"
        cols = 8
        rangs = math.ceil(math.ceil(n_img / FPS) / cols)
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", film, "-vf",
           f"fps=1,scale=270:480,drawtext=text='%{{pts\\:hms}}':x=8:y=8:fontsize=18:fontcolor=0x6F695F,tile={cols}x{rangs}:padding=6:color=0xF4F1E8",
           "-frames:v", 1, pl)
        for f in tmp.iterdir():
            if f.name != "brut.wav":
                shutil.copy2(f, sortie / f.name)
    print(f"→ {sortie / rec['sortie']}")


if __name__ == "__main__":
    main()
