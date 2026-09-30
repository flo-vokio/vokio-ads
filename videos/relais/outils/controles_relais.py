#!/usr/bin/env python3
"""Contrôles d'une carte « Le relais » (étape « controles » de relais.py) : usage en une ligne :

    python3 outils/relais.py <carte>/recette.json controles

  DOM (Chromium, tous les 1/4 s) : ≤ 3 éléments simultanés, corps ≥ 52 px du cadre (≥ 12 px affichés à 264 px, la carte
  à 320 de large ; ≥ 18 px à 375), textes dans les marges, aucun « — », aucun numéro de téléphone, jamais « Alauzet »,
  pages = sous-suites contiguës des énoncés dits, aucune erreur interne du gabarit.
  Fichiers : H.264 yuv420p, +faststart (moov avant mdat), 30 i/s, poids ≤ cible, boucle SANS piste audio, complète avec.
  Boucle : raccord dernière image → première image, comparé aux écarts entre images voisines du film.
  Son (complète) : sonie −16 ± 0,5 LUFS, crête ≤ −1 dBTP, image et son de même durée.
  Rapport : <carte>/controles.json ; rend le nombre d'échecs.
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from relais import SORTIES, POIDS_MAX, FPS, mesurer, cle, mots_de, sonde_duree

TEL = re.compile(r"(\+33|0\d)([ . ]?\d{2}){4}")


def moov_avant_mdat(f):
    b = Path(f).read_bytes()[:2_000_000]
    i, j = b.find(b"moov"), b.find(b"mdat")
    return i >= 0 and (j < 0 or i < j)


def images(f, cote=270):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-vf", f"scale={cote}:{cote}", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, cote, cote).astype(np.float32)


def contigu(page, enonce):
    p, e = [cle(w) for w in page.split()], [cle(w) for w in enonce]
    p = [x for x in p if x]
    e = [x for x in e if x]
    return any(e[k:k + len(p)] == p for k in range(len(e) - len(p) + 1))


def controler(R, carte, shm, modes):
    rap, echecs = {}, []

    def ok(nom, cond, detail):
        rap.setdefault(mode, {})[nom] = {"ok": bool(cond), "detail": detail}
        if not cond:
            echecs.append(f"{mode} · {nom} : {detail}")

    for mode in modes:
        D = json.loads((carte / f"donnees-{mode}.json").read_text())
        tmp = shm / f"dom-{mode}.json"
        shm.mkdir(parents=True, exist_ok=True)
        subprocess.run(["/root/.pwtest/bin/python3", str(Path(__file__).with_name("apercu.py")), str(carte / mode),
                        "--pas", "0.25", "--json", str(tmp)], check=True, capture_output=True)
        J = json.loads(tmp.read_text())
        E, err, internes = J["instants"], J["erreurs"], J["internes"]
        trop = [(e["t"], e["elements"]) for e in E if e["n"] > 3]
        ok("trois_elements", not trop, f"max {max(e['n'] for e in E)} élément(s) ; dépassements : {trop[:5]}")
        cm = min(e["corps_min"] for e in E if e["corps_min"])
        ok("corps_min", cm >= 52, f"{cm} px du cadre = {cm * 264 / 1080:.1f} px à 264 px affichés, {cm * 375 / 1080:.1f} px à 375")
        hors = [(e["t"], e["hors_marges"]) for e in E if e["hors_marges"]]
        ok("marges", not hors, f"{hors[:3]}")
        tous = " ".join(sorted({x for e in E for x in e["textes"]}))
        ok("tiret_cadratin", "—" not in tous, "aucun « — »" if "—" not in tous else "« — » trouvé")
        ok("numero", not TEL.search(tous), "aucun numéro" if not TEL.search(tous) else TEL.search(tous).group(0))
        ok("nom_de_famille", "alauzet" not in tous.lower(), "jamais « Alauzet »")
        ok("erreurs_internes", not (err or internes.get("erreurs")), f"{err or internes.get('erreurs') or 'aucune'}")
        ens = [e["mots"] for e in D["enonces"]]
        mauvaises = []
        for p in internes["pages"]:
            if not any(contigu(p["texte"], [w["texte"] for w in m]) for m in ens):
                mauvaises.append(p["texte"])
        if mode == "boucle":        # la boucle est une sous-suite de l'appel dit : relais.py le vérifie à la construction
            src = [mots_de(e["texte"]) for e in R["enonces"]]
            from relais import sous_suite
            mauvaises = [p["texte"] for p in internes["pages"] if not any(sous_suite(p["texte"].split(), s) for s in src)]
        ok("sous_suite", not mauvaises, f"{len(internes['pages'])} pages, hors du dit : {mauvaises}")
        if internes.get("non_montres"):
            rap[mode]["non_sous_titre"] = {"ok": True, "detail": f"dit pendant l'iPhone, non sous-titré : {internes['non_montres']}"}
        der = sorted({d for e in E for d in e.get("derogations", [])})
        if der:
            rap[mode]["derogations"] = {"ok": True, "detail": f"{der}"}

        f = SORTIES / f"{R['nom']}-{mode}.mp4"
        pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(f)],
                                       capture_output=True, text=True, check=True).stdout)
        v = next(s for s in pr["streams"] if s["codec_type"] == "video")
        a = [s for s in pr["streams"] if s["codec_type"] == "audio"]
        taille = int(pr["format"]["size"])
        ok("codec", v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p" and v["r_frame_rate"] == "30/1",
           f'{v["codec_name"]} {v["pix_fmt"]} {v["width"]}×{v["height"]} {v["r_frame_rate"]}')
        ok("faststart", moov_avant_mdat(f), "moov en tête")
        ok("poids", taille <= POIDS_MAX[mode], f"{taille / 1000:.0f} Ko (cible ≤ {POIDS_MAX[mode] / 1000:.0f} Ko)")
        dv = float(v["duration"])
        ok("duree", abs(dv - D["duree"]) < 0.05, f"{dv:.3f} s (voulu {D['duree']:.3f})")
        webm = SORTIES / f"{R['nom']}-{mode}.webm"
        if webm.exists():
            rap[mode]["webm_av1"] = {"ok": True, "detail": f"{webm.stat().st_size / 1000:.0f} Ko"}
        if mode == "boucle":
            tp = float(R.get("poster_boucle", 0.6))
            tmp2 = shm / "dom-poster.json"
            subprocess.run(["/root/.pwtest/bin/python3", str(Path(__file__).with_name("apercu.py")), str(carte / mode),
                            "--at", f"{tp}", "--json", str(tmp2)], check=True, capture_output=True)
            ep = json.loads(tmp2.read_text())["instants"][0]
            ok("poster_sans_texte", not ep["textes_hors_situation"] and "situation" in ep["elements"],
               f"poster à {tp} s : éléments {ep['elements']}, texte hors illustration {ep['textes_hors_situation']}")
            ok("sans_audio", not a, "aucune piste audio" if not a else f"{len(a)} piste(s) audio")
            I = images(f)
            d = np.abs(np.diff(I, axis=0)).mean(axis=(1, 2))
            seam = np.abs(I[-1] - I[0]).mean()
            ref = float(np.percentile(d, 95))
            ok("raccord", seam <= max(ref, 0.5), f"écart dernière → première image {seam:.2f} ; voisines : médiane "
               f"{np.median(d):.2f}, p95 {ref:.2f}, max {d.max():.2f}")
        else:
            ok("audio", len(a) == 1, f"{a[0]['codec_name']} {a[0]['sample_rate']} Hz {a[0]['channels']} can. "
               f"{int(a[0].get('bit_rate', 0)) // 1000} kb/s" if a else "pas de piste audio")
            m = mesurer(f)
            ok("sonie", abs(m["lufs"] + 16) <= 0.5 and m["crete_dbtp"] <= -1.0, f"{m['lufs']} LUFS, crête {m['crete_dbtp']} dBTP")
            da = float(a[0]["duration"]) if a else 0
            ok("synchro", abs(da - dv) < 0.1, f"image {dv:.3f} s, son {da:.3f} s")
    (carte / "controles.json").write_text(json.dumps({"echecs": echecs, "detail": rap}, ensure_ascii=False, indent=1))
    for mode in rap:
        for k, x in rap[mode].items():
            print(f"  {'✓' if x['ok'] else '✗'} {mode:8} {k:18} {x['detail']}")
    print(f"{len(echecs)} échec(s)")
    return len(echecs)
