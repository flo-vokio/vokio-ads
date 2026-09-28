#!/usr/bin/env python3
"""Vérifie UNE scène dans le 9:16 ET dans un format, en une commande, après une retouche : usage en une ligne :

    python3 outils/verifier_scene.py <scène> --dossier D [--format 16x9] [--ref git:HEAD] [--entrees git:HEAD] [--mp4 film.mp4]
                                     [--variante <scène>=<nom>] [--vite] [--sans-controle] [--sans-9x16] [--plus t,t]
                                     [--etapes 9x16,format,raccords,controle,heurts,internes,plume]
                                     [--permis "scène:élément:texte"]

  Enchaîne les outils existants, sans rien écrire dans la source ni dans formats/ (tout va dans D) :
   1. 9:16  copie de contrôle D/c9 (format.py 9x16 --dossier D/c9 --entrees E), puis revue_scene.py identite D/c9 <scène> <réf>
            --toutes : CHAQUE image de la scène et ses raccords, au sha256 des pixels près (échec si une image diffère) ;
            --mp4 <film 9:16 livré> : en plus, revue_scene.py mp4 (au codec près : PSNR, part de pixels forts).
   2. format  copie D/f<format> (format.py <format> --dossier … --entrees E --check [--variante]) : hf check, px du 9:16 restés en
            dur dans le fichier de la scène (rapports/a-parametrer.json) ; planche de la scène aux instants clés, avec les zones
            sûres, et vues 852 / 393 px (revue_scene.py planche) → D/planche-<format>/.
   3. raccords  dans chaque format, écart pixel entre la dernière image de la scène d'avant et la 1re de la scène, puis entre la
            dernière de la scène et la 1re de la suivante (pixels, boîte ; le point qui bouge est normal, un objet qui saute ne
            l'est pas) ; le raccord du format est comparé à celui du 9:16 (même nature d'écart attendue) → D/raccords-<f>.png.
   4. contrôles  controle_format.py D/f<format> (E1 ≤ 3 éléments, E2 corps, E3 zones interdites, E4 marges, E5 mono) sur tout le
            film, une image sur 3 (≈ 1 min ; --sans-controle pour sauter) ; fiche_format.py : la section de la scène.
   5. heurts  heurts.py dans chaque format : le disque du point ne touche l'encre d'aucun mot visible, image par image, dans la
            scène (≈ 10 s) ; heurts voulus déclarés dans PERMIS (le point part du « . » de « prises », il écrit « Vokıo ») et
            --permis « scène:élément:texte » en plus.
   6. internes  controles_internes.py sur les deux copies : chaque window.__<scène>Controle a mesuré (jamais « mesure: false »),
            aucun écart > 0,5 px, aucune erreur de page (ce que hf check ne voit pas).
   7. plume  (s7-signature seulement) plume.py dans chaque format : l'encre de « Vokıo » suit la plume (rien devant, tout derrière,
            bord doux, mot entier à l'arrivée).
   8. bilan  D/bilan.json (D/bilan-partiel.json si --etapes en saute) + tableau imprimé ; code 0 si tout passe, 1 sinon.
  Réf. et entrées : git:HEAD par défaut (le 9:16 tel que commité, dialogue et mots du commit) ; tant que l'équipe son n'a pas
  commité son dialogue, passer --ref git:aa4dd24 --entrees git:aa4dd24. --vite : identité aux instants clés seulement.
  --etapes : n'en relancer que certaines (les copies D/c9 et D/f<format> d'une passe précédente sont réutilisées).
  Exemple : verifier_scene.py s5-rendez-vous --dossier /tmp/x/s5 --ref git:aa4dd24 --entrees git:aa4dd24 \\
                              --mp4 /root/vokio-uploads/videos/showcase/le-point-sur-le-i-iphone.mp4
Idempotent (D est réécrit) ; les hf snapshot passent sous flock /tmp/hf-rendu.lock (revue_scene.py).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import revue_scene as RS  # noqa: E402

PROJET = Path(__file__).resolve().parents[1]
PY = sys.executable
PW = "/root/.pwtest/bin/python"          # playwright (heurts.py, controles_internes.py)
OUT = PROJET / "outils"
ETAPES = "9x16,format,raccords,controle,heurts,internes,plume"
# heurts VOULUS du point avec un mot, présents dans la référence 9:16 : il part du « . » de « mains prises. » (s1, 1,8 px,
# images 132 à 136) et il écrit « Vokıo » puis se pose sur le ı (s7). Tout autre heurt fait échouer l'étape.
PERMIS = ["s1-sonnerie:*:prises*", "s7-signature:*:*"]


def lancer(cmd, journal):
    """Lance cmd, écrit sa sortie dans journal, renvoie (code, dernières lignes)."""
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    Path(journal).write_text("$ " + " ".join(str(c) for c in cmd) + "\n" + r.stdout + "\n" + r.stderr)
    fin = [ln for ln in (r.stdout + "\n" + r.stderr).strip().splitlines() if ln.strip()][-6:]
    return r.returncode, fin


def raccords(racine, scene, dossier):
    """Écarts pixel aux deux raccords de la scène : [{quoi, images, pixels, max, boite, png}]."""
    D = RS.donnees(racine)
    fps, sc = D["fps"], D["scenes"][scene]
    a, b = sc["image_debut"], sc["image_fin"]
    n_film = int(round(D["duree"] * fps))
    paires = [("entrée", a - 1, a)] + ([("sortie", b - 1, b)] if b < n_film else [])
    ks = sorted({k for _, x, y in paires for k in (x, y) if k >= 0})
    S = RS.snapshots(racine, [(k, RS.temps(k, fps), "") for k in ks], Path(dossier) / "png")
    out = []
    for quoi, x, y in paires:
        if x < 0:
            continue
        ia, ib = RS.rgba(S[x]), RS.rgba(S[y])
        png = Path(dossier) / f"ecart-{quoi}-{x}-{y}.png"
        info = RS.carte_ecart(ia, ib, png)
        out.append({"quoi": quoi, "images": [x, y], "pixels": info["pixels"], "max": info["max"], "boite": info["boite"],
                    "png": str(png), "avant": str(S[x]), "apres": str(S[y])})
    return out


def section_fiche(texte, scene):
    lignes, dedans = [], False
    for ln in texte.splitlines():
        if ln.startswith(scene + " "):
            dedans = True
        elif dedans and ln and not ln.startswith(" "):
            break
        if dedans:
            lignes.append(ln)
    return lignes


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("scene")
    A.add_argument("--dossier", required=True)
    A.add_argument("--format", default="16x9")
    A.add_argument("--ref", default="git:HEAD")
    A.add_argument("--entrees", default="git:HEAD")
    A.add_argument("--mp4")
    A.add_argument("--variante", action="append", default=[])
    A.add_argument("--plus", help="instants ajoutés à la planche du format (s, séparés par des virgules)")
    A.add_argument("--vite", action="store_true")
    A.add_argument("--sans-controle", action="store_true")
    A.add_argument("--sans-9x16", action="store_true")
    A.add_argument("--etapes", default=ETAPES)
    A.add_argument("--permis", action="append", default=[], help="heurt voulu en plus de PERMIS (fnmatch scène:élément:texte)")
    a = A.parse_args()
    E = set(a.etapes.split(","))
    if a.sans_9x16:
        E.discard("9x16")
    if a.sans_controle:
        E.discard("controle")
    D = Path(a.dossier).resolve()
    D.mkdir(parents=True, exist_ok=True)
    c9, fx = D / "c9", D / f"f{a.format}"
    etapes = []

    def note(nom, ok, **det):
        etapes.append({"etape": nom, "ok": bool(ok)} | det)
        print(f"{'ok ' if ok else 'NON'} {nom}" + (f" : {det.get('resume')}" if det.get("resume") else ""), flush=True)

    # 1. le 9:16 ne bouge pas
    if "9x16" in E:
        code, fin = lancer([PY, OUT / "format.py", "9x16", "--dossier", c9, "--entrees", a.entrees], D / "c9.log")
        note("9:16 copie de contrôle", code == 0, resume=fin[-1] if fin else "", journal=str(D / "c9.log"))
        cmd = [PY, OUT / "revue_scene.py", "identite", c9, a.scene, a.ref, "--images", D / "identite-9x16",
               "--json", D / "identite-9x16.json"] + ([] if a.vite else ["--toutes"])
        code, fin = lancer(cmd, D / "identite-9x16.log")
        note(f"9:16 identique à {a.ref}", code == 0, resume=next((ln for ln in fin if "identiques" in ln), fin[-1] if fin else ""),
             rapport=str(D / "identite-9x16.json"))
        if a.mp4:
            cmd = [PY, OUT / "revue_scene.py", "mp4", c9, a.scene, a.mp4, "--images", D / "mp4-9x16", "--json", D / "mp4-9x16.json"] \
                + ([] if a.vite else ["--toutes"])
            code, fin = lancer(cmd, D / "mp4-9x16.log")
            note(f"9:16 conforme à {Path(a.mp4).name} (codec)", code == 0,
                 resume=next((ln for ln in fin if "conformes" in ln), fin[-1] if fin else "")[:220],
                 rapport=str(D / "mp4-9x16.json"), pires=str(D / "mp4-9x16" / "pires.png"))

    # 2. le format : construction, hf check, px en dur, planche
    if "format" in E:
        etape_format(a, D, fx, note)
    # 3. raccords, dans les deux formats
    R = {}
    if "raccords" in E:
        R = etape_raccords(a, D, c9, fx, note)
    # 4. contrôles du format et fiche de la scène
    if "controle" in E:
        code, fin = lancer([PY, OUT / "controle_format.py", fx, "--sortie", D / f"controle-{a.format}.json"],
                           D / f"controle-{a.format}.log")
        note(f"{a.format} règles de Florian (controle_format.py, film entier)", code == 0, resume=fin[-1] if fin else "",
             rapport=str(D / f"controle-{a.format}.json"))
    copies = ([("9x16", c9)] if (c9 / "donnees" / "donnees.js").exists() else []) + \
        ([(a.format, fx)] if (fx / "donnees" / "donnees.js").exists() else [])
    # 5. le point ne touche aucun texte (heurts voulus : PERMIS)
    if "heurts" in E:
        for nom, racine in copies:
            code, fin = lancer([PW, OUT / "heurts.py", racine, a.scene, "--json", D / f"heurts-{nom}.json"]
                               + sum((["--permis", m] for m in PERMIS + a.permis), []), D / f"heurts-{nom}.log")
            note(f"{nom} heurts du point avec les textes", code == 0,
                 resume="; ".join(ln.strip() for ln in fin if "HEURT" in ln or "aucun heurt" in ln or "permis" in ln)[:300],
                 rapport=str(D / f"heurts-{nom}.json"))
    # 6. contrôles internes des scènes (mesure faite, écarts ≤ 0,5 px)
    if "internes" in E and copies:
        code, fin = lancer([PW, OUT / "controles_internes.py"] + [r for _, r in copies] + ["--json", D / "internes.json"],
                           D / "internes.log")
        note("contrôles internes des scènes (" + ", ".join(n for n, _ in copies) + ")", code == 0,
             resume="; ".join(fin[-3:])[:300], rapport=str(D / "internes.json"))
    # 7. l'encre suit la plume (s7)
    if "plume" in E and a.scene.startswith("s7"):
        for nom, racine in copies:
            code, fin = lancer([PY, OUT / "plume.py", racine, "--images", D / f"plume-{nom}", "--json", D / f"plume-{nom}.json"],
                               D / f"plume-{nom}.log")
            note(f"{nom} l'encre suit la plume", code == 0, resume=fin[-1] if fin else "", planche=str(D / f"plume-{nom}" / "plume.png"))
    r = subprocess.run([PY, OUT / "fiche_format.py", fx, "--json", D / f"fiche-{a.format}.json"]
                       + (["--9x16", c9] if (c9 / "donnees" / "donnees.js").exists() else []), capture_output=True, text=True)
    fiche = section_fiche(r.stdout, a.scene)
    (D / f"fiche-{a.scene}.txt").write_text("\n".join(fiche) + "\n")

    ok = all(e["ok"] for e in etapes)
    bilan = {"scene": a.scene, "format": a.format, "ref": a.ref, "entrees": a.entrees, "variantes": a.variante, "ok": ok,
             "etapes_lancees": sorted(E), "etapes": etapes, "raccords": R, "fiche": fiche}
    complet = E >= set(ETAPES.split(","))
    fb = D / ("bilan.json" if complet else "bilan-partiel.json")     # une passe partielle n'écrase pas le bilan complet
    fb.write_text(json.dumps(bilan, ensure_ascii=False, indent=1, default=str))
    print("\n".join(fiche))
    print(f"\n{a.scene} : {'TOUT PASSE' if ok else 'ÉCHEC'} ({sum(e['ok'] for e in etapes)}/{len(etapes)} étapes) → {fb}")
    print(f"à regarder : {D / f'planche-{a.format}' / 'planche.png'} · " + " · ".join(str(D / f"raccords-{n}.png") for n in R))
    return 0 if ok else 1


def etape_format(a, D, fx, note):
    cmd = [PY, OUT / "format.py", a.format, "--dossier", fx, "--entrees", a.entrees, "--check"] \
        + sum((["--variante", v] for v in a.variante), [])
    code, fin = lancer(cmd, D / f"f{a.format}.log")
    note(f"{a.format} construit + hf check", code == 0, resume=next((ln for ln in fin if "hf check" in ln), fin[-1] if fin else ""),
         journal=str(D / f"f{a.format}.log"))
    fichier = next((f.name for f in (PROJET / "compositions").glob(a.scene + "*.html")), a.scene + ".html")
    try:
        reste = json.loads((fx / "rapports" / "a-parametrer.json").read_text()).get(fichier, [])
    except (OSError, json.JSONDecodeError):
        reste = ["rapport a-parametrer.json illisible"]
    note(f"{a.format} aucun px du 9:16 en dur dans {fichier}", not reste, resume="; ".join(reste[:6]) or "aucun", reste=reste)
    cmd = [PY, OUT / "revue_scene.py", "planche", fx, a.scene, "--vues", "852,393", "--images", D / f"planche-{a.format}",
           "--json", D / f"planche-{a.format}.json"] + (["--plus", a.plus] if a.plus else [])
    code, fin = lancer(cmd, D / f"planche-{a.format}.log")
    note(f"{a.format} planche de la scène", code == 0, resume=str(D / f"planche-{a.format}" / "planche.png"))


def etape_raccords(a, D, c9, fx, note):
    R = {}
    for nom, racine in ([("9x16", c9)] if (c9 / "donnees" / "donnees.js").exists() else []) + [(a.format, fx)]:
        R[nom] = raccords(racine, a.scene, D / f"raccords-{nom}")
        cases = [(f"{nom} · {r['quoi']} {r['images'][0]} → {r['images'][1]} · {r['pixels']} px · avant | après | écart",
                  [Image.open(r["avant"]), Image.open(r["apres"]), Image.open(r["png"])]) for r in R[nom]]
        if cases:                                   # une planche par format : feuille() prend la taille de la 1re image
            RS.feuille(cases, D / f"raccords-{nom}.png", 420 if nom == "9x16" else 560)
    for r in R[a.format]:
        ref = next((x for x in R.get("9x16", []) if x["quoi"] == r["quoi"]), None)
        meme_nature = ref is None or (r["pixels"] == 0) == (ref["pixels"] == 0)
        note(f"{a.format} raccord {r['quoi']} {r['images'][0]} → {r['images'][1]}", meme_nature,
             resume=f"{r['pixels']} px, boîte {r['boite']}" + (f" (9:16 : {ref['pixels']} px, boîte {ref['boite']})" if ref else ""),
             raccord=r, raccord_9x16=ref)
    return R


if __name__ == "__main__":
    sys.exit(main())
