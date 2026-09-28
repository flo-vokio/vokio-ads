#!/usr/bin/env python3
"""Identité à l'image près d'un rendu : empreinte de CHAQUE image du film (pixels bruts), puis comparaison.

    python3 outils/identite.py empreindre <projet> <sortie.json> [--at 1.5,20.4] [--garder <chemin>]
    python3 outils/identite.py comparer <reference.json> <candidat.json> [--diff <dossier> --images <ref>,<cand>]
                                        [--decalage A:N …] [--voulu a-b,c-d]
    python3 outils/identite.py donnees <donnees_ref/> <donnees_cand/>     les JSON (et donnees.js) clé par clé
    python3 outils/identite.py mp4 <film.mp4> <sortie.json>               empreintes d'un MP4 déjà rendu (sans perte)
    python3 outils/identite.py extraire <révision> <dossier>              le projet tel qu'il était au commit (git archive), rendable
    python3 outils/identite.py prouver <projet> <révision> [--pas 0.5]     <projet> rend-il comme <révision> ? (snapshots, sans MP4)

  prouver    : extrait <révision> (dossier temporaire), prend les mêmes instants dans les deux projets par hf snapshot (un
               instant tous les --pas s + chaque instant de DONNEES.evenements, ~100 images pour 0,5 s) et les compare pixel à
               pixel (sha256 RGBA) ; code 0 si tout est identique. Le chemin court quand le disque manque pour un MP4 sans
               perte (l'empreinte complète de format.py --empreinte reste la preuve de référence, image par image).

  extraire   : écrit dans <dossier> le projet videos/showcase-iphone de <révision> (git archive) et y recopie les fichiers
               ignorés par git dont le rendu a besoin (assets/son/*.wav, depuis ce projet) : une RÉFÉRENCE à comparer quand
               le rendu MP4 est impossible (HyperFrames refuse de rendre sous 1 Gio libre ; hf snapshot, lui, passe) :
                 identite.py extraire aa4dd24 /tmp/…/ref && identite.py empreindre /tmp/…/ref ref.json --at 31.4,31.6,…
                 identite.py empreindre <copie 9:16> cand.json --at <mêmes instants> && identite.py comparer ref.json cand.json

  donnees    : compare deux dossiers donnees/ (chaque .json et window.DONNEES de donnees.js), clé par clé, en ignorant les
               horodatages (version, date) ; liste les clés AJOUTÉES (permises : les formats ajoutent), RETIRÉES et
               CHANGÉES (interdites pour le 9:16) ; code 1 s'il y a une clé retirée ou changée.

  empreindre : film entier (défaut) : rend <projet> (index.html) en MP4 SANS PERTE (hf render --crf 0, sous flock
               /tmp/hf-rendu.lock : la séquence PNG demande 11,7 Go de disque, le MP4 sans perte ~150 Mo), décode chaque image
               en RGB et en garde le md5 des pixels (ffmpeg -f framemd5, rien sur le disque) ; écrit <sortie.json> puis
               efface le MP4, sauf --garder <chemin.mp4>. Disque sous 1,2 Gio libres : le rendu se fait dans /dev/shm
               (outils/rendre.py, 28/09), HyperFrames ne refuse plus. Deux rendus du même projet
               donnent les mêmes empreintes (vérifié le 27/09) : toute différence vient du projet.
               --at t1,t2 : seulement ces instants, par hf snapshot (PNG RGBA exacts ; --garder <dossier> les garde).
  comparer   : compare deux fichiers d'empreintes image par image ; code 0 si tout est identique, 1 sinon (images différentes
               groupées en plages). --decalage A:N (répétable, 28/09) : le candidat est la référence où l'on a INSÉRÉ N images
               avant l'image A de la référence (outils/temps.py --decalages : « --decalage 758:92 » depuis l'échange du
               prénom) : l'image r de la référence est comparée à l'image r + Σ N du candidat, les images insérées ne sont
               comparées à rien ; --voulu a-b : plages de la RÉFÉRENCE où l'écart est voulu (rapportées, hors du code de sortie). --diff <dossier> --images <ref>,<cand> (les deux MP4 ou dossiers PNG gardés) : carte des
               écarts (max, nombre de pixels, boîte) de chaque image différente, en PNG.

Usage type (le 9:16 ne doit pas bouger quand on touche au système de formats) :
    python3 outils/identite.py empreindre . /tmp/…/ref-9x16.json          # AVANT la modification
    python3 outils/identite.py empreindre . /tmp/…/apres-9x16.json        # APRÈS
    python3 outils/identite.py comparer /tmp/…/ref-9x16.json /tmp/…/apres-9x16.json
Idempotent ; n'écrit rien dans le projet (le rendu va dans un dossier temporaire hors du projet).
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HF = "/opt/vokio-ads/bin/hf"
PROJET = Path(__file__).resolve().parents[1]
VERROU = "/tmp/hf-rendu.lock"
PAPIER = np.array([0xF4, 0xF1, 0xE8], dtype=np.int16)


def empreinte(png):
    im = Image.open(png).convert("RGBA")
    a = np.asarray(im)
    h = hashlib.sha256(a.tobytes()).hexdigest()
    rgb = a[:, :, :3].astype(np.int16)
    hors_papier = int((np.abs(rgb - PAPIER).max(axis=2) > 8).sum())
    return {"sha256": h, "taille": [im.width, im.height], "moyenne": round(float(rgb.mean()), 3), "hors_papier": hors_papier}


def cle_image(p):
    """Numéro d'image depuis le nom de fichier (frame_000123.png, frame-00-at-20.667s.png…)."""
    import re
    m = re.search(r"at-([0-9.]+)s", p.name)
    if m:
        return "t=" + m.group(1)
    nums = re.findall(r"\d+", p.stem)
    return str(int(nums[-1])) if nums else p.stem


def resume(rgb):
    x = rgb[::4, ::4].astype(np.int16)                     # une image sur 16 pixels : un résumé, pas une preuve (le sha256 l'est)
    return {"moyenne": round(float(x.mean()), 3), "hors_papier": int((np.abs(x - PAPIER).max(axis=2) > 8).sum()) * 16}


def taille_video(mp4):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(mp4)], capture_output=True, text=True, check=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def images_video(mp4):
    """Itère (n, tableau RGB) sur les images décodées d'un MP4, sans rien écrire."""
    w, h = taille_video(mp4)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(mp4), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    n, t = 0, w * h * 3
    while True:
        b = p.stdout.read(t)
        if len(b) < t:
            break
        yield n, np.frombuffer(b, dtype=np.uint8).reshape(h, w, 3)
        n += 1
    p.wait()


def empreintes_video(mp4):
    """md5 des pixels RGB de chaque image décodée (ffmpeg -f framemd5 : en C, 1 410 images en ~20 s au lieu de 3 min)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", "0:v:0", "-pix_fmt", "rgb24", "-f", "framemd5", "-"],
                       capture_output=True, text=True, check=True)
    out, n = {}, 0
    for ligne in r.stdout.splitlines():
        if ligne.startswith("#") or not ligne.strip():
            continue
        out[str(n)] = {"md5": ligne.split(",")[-1].strip()}
        n += 1
    return out


def empreindre(projet, sortie, at=None, garder=None):
    projet = Path(projet).resolve()
    env = None
    if at:
        tmp = Path(tempfile.mkdtemp(prefix="identite-", dir="/tmp"))
    else:           # le MP4 sans perte (~150 Mo) : en mémoire (/dev/shm) quand le disque a moins de 1,2 Gio (outils/rendre.py)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import rendre
        tmp, en_memoire = rendre.dossier_travail("/tmp/film.mp4")
        env = dict(__import__("os").environ, TMPDIR=str(tmp))
    try:
        if at:
            cmd = [HF, "snapshot", str(projet), "--no-end", "--at", at, "-o", str(tmp / "png"), "--describe", "false"]
        else:
            cmd = [HF, "render", str(projet), "--crf", "0", "-o", str(tmp / "film.mp4"), "--quiet"]
        r = subprocess.run(["flock", VERROU] + cmd, capture_output=True, text=True, timeout=3600, env=env)
        if r.returncode:
            raise SystemExit(f"rendu impossible ({' '.join(cmd)}) :\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}")
        images = {}
        if at:
            pngs = sorted((tmp / "png").rglob("*.png"))
            if not pngs:
                raise SystemExit(f"aucune image produite dans {tmp / 'png'} :\n{r.stdout[-2000:]}")
            for p in pngs:
                images[cle_image(p)] = empreinte(p) | {"fichier": p.name}
        else:
            images = empreintes_video(tmp / "film.mp4")
        out = {"projet": str(projet), "mode": "snapshot --at " + at if at else "render mp4 --crf 0", "nombre": len(images),
               "images": images}
        Path(sortie).parent.mkdir(parents=True, exist_ok=True)
        Path(sortie).write_text(json.dumps(out, ensure_ascii=False, indent=0))
        if garder:
            g = Path(garder)
            g.parent.mkdir(parents=True, exist_ok=True)
            if g.exists():
                shutil.rmtree(g) if g.is_dir() else g.unlink()
            shutil.move(str(tmp / ("png" if at else "film.mp4")), str(g))
        print(f"{len(images)} images empreintes → {sortie}" + (f" (gardé : {garder})" if garder else ""))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def plages(cles):
    nums = sorted(int(c) for c in cles if c.isdigit())
    autres = [c for c in cles if not c.isdigit()]
    out, debut, prec = [], None, None
    for n in nums:
        if debut is None:
            debut = prec = n
        elif n == prec + 1:
            prec = n
        else:
            out.append(f"{debut}-{prec}" if prec != debut else str(debut)); debut = prec = n
    if debut is not None:
        out.append(f"{debut}-{prec}" if prec != debut else str(debut))
    return out + autres


def comparer(ref, cand, diff=None, images=None, decalages=None, voulu=None):
    A, B = json.loads(Path(ref).read_text())["images"], json.loads(Path(cand).read_text())["images"]
    decs = sorted(decalages or [])
    voulu = voulu or []

    def vers_cand(c):                  # clé de la référence → clé du candidat (insertions de temps)
        if not (decs and c.isdigit()):
            return c
        r = int(c)
        return str(r + sum(n for a, n in decs if r >= a))
    corr = {c: vers_cand(c) for c in A}
    communes = sorted((c for c in A if corr[c] in B), key=lambda c: (not c.isdigit(), int(c) if c.isdigit() else 0, c))
    vues = {corr[c] for c in communes}
    inserees = sorted((k for k in B if k not in vues and k.isdigit()), key=int) if decs else []
    manquantes = sorted([c for c in A if corr[c] not in B] + [k for k in B if k not in vues and k not in inserees])
    cle = "md5" if all("md5" in A[c] and "md5" in B[corr[c]] for c in communes) else "sha256"
    diffs_tout = [c for c in communes if A[c].get(cle) != B[corr[c]].get(cle)]
    dans = lambda c: c.isdigit() and any(a <= int(c) <= b for a, b in voulu)
    diffs = [c for c in diffs_tout if not dans(c)]
    print(f"{len(communes)} images comparées ; {len(diffs)} différentes" + (f" (+ {len(diffs_tout) - len(diffs)} dans les plages voulues "
          + ", ".join(f"{a}-{b}" for a, b in voulu) + ")" if voulu else "") + f" ; {len(manquantes)} présentes d'un seul côté"
          + (f" ; {len(inserees)} images insérées du candidat non comparées ({', '.join(plages(inserees))})" if decs else ""))
    if diffs:
        print("images différentes (numéros de la référence) : " + ", ".join(plages(diffs)[:40]))
    if decs:
        bornes = sorted({0, max((int(c) for c in A if c.isdigit()), default=0) + 1} | {a for a, _ in decs}
                        | {x for a, b in voulu for x in (a, b + 1)})
        for b0, b1 in zip(bornes, bornes[1:]):
            L = [c for c in communes if c.isdigit() and b0 <= int(c) < b1]
            if L:
                nd = sum(1 for c in L if c in set(diffs_tout))
                print(f"    référence {L[0]}-{L[-1]} ↔ candidat {corr[L[0]]}-{corr[L[-1]]} : {len(L) - nd} identiques, {nd} différentes"
                      + (" (écart voulu)" if any(dans(c) for c in L) else ""))
    if manquantes:
        print("présentes d'un seul côté : " + ", ".join(manquantes[:20]))
    if diff and images and diffs:
        da, db = [Path(x) for x in images.split(",")]
        Path(diff).mkdir(parents=True, exist_ok=True)

        def lire(src, meta, c):
            if src.suffix == ".mp4":
                return next(a for n, a in images_video(src) if str(n) == c).astype(np.int16)
            return np.asarray(Image.open(src / meta[c]["fichier"]).convert("RGB")).astype(np.int16)
        for c in diffs[:60]:
            a, b = lire(da, A, c), lire(db, B, corr[c])
            d = np.abs(a - b).max(axis=2)
            ys, xs = np.nonzero(d)
            print(f"  image {c} : écart max {int(d.max())}, {len(xs)} pixels, boîte x {xs.min()}-{xs.max()} y {ys.min()}-{ys.max()}")
            Image.fromarray(np.clip(d * 8, 0, 255).astype(np.uint8)).save(Path(diff) / f"diff-{c}.png")
    return 0 if not diffs and not manquantes else 1


IGNOREES = {"version", "date"}
ENTREES = {"mots.json"}          # donnees/ de la source seulement (outils/mots.py) : construire.py --racine les y lit


def lire_donnees(f):
    t = f.read_text()
    if f.suffix == ".js":
        t = t[t.index("{"):t.rindex("}") + 1]
    return json.loads(t)


def ecarts(a, b, chemin=""):
    aj, re_, ch = [], [], []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in IGNOREES:
                continue
            if k not in b:
                re_.append(chemin + "." + k)
            else:
                x, y, z = ecarts(a[k], b[k], chemin + "." + k)
                aj += x; re_ += y; ch += z
        aj += [chemin + "." + k for k in b if k not in a and k not in IGNOREES]
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x0, y0) in enumerate(zip(a, b)):
            x, y, z = ecarts(x0, y0, f"{chemin}[{i}]")
            aj += x; re_ += y; ch += z
    elif a != b:
        ch.append(f"{chemin} : {json.dumps(a, ensure_ascii=False)[:80]} → {json.dumps(b, ensure_ascii=False)[:80]}")
    return aj, re_, ch


def donnees(da, db):
    da, db = Path(da), Path(db)
    mauvais = 0
    for f in sorted(list(da.glob("*.json")) + list(da.glob("*.js"))):
        g = db / f.name
        if not g.exists():
            if f.name in ENTREES:
                print(f"{f.name} : entrée commune aux formats (lue dans la source, non copiée)"); continue
            print(f"{f.name} : ABSENT du candidat"); mauvais += 1; continue
        aj, re_, ch = ecarts(lire_donnees(f), lire_donnees(g))
        etat = "identique" if not (aj or re_ or ch) else ("ajouts seulement" if not (re_ or ch) else "DIFFÉRENT")
        print(f"{f.name} : {etat}" + (f" ({len(aj)} clé(s) ajoutée(s) : {', '.join(aj[:12])}{' …' if len(aj) > 12 else ''})" if aj else ""))
        for x in re_[:10]:
            print(f"   retirée : {x}")
        for x in ch[:10]:
            print(f"   changée : {x}")
        mauvais += bool(re_ or ch)
    return 1 if mauvais else 0


def extraire(rev, dossier):
    dossier = Path(dossier).resolve()
    racine = Path(subprocess.run(["git", "-C", str(PROJET), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                                 check=True).stdout.strip())
    rel = PROJET.relative_to(racine)
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)
    arch = subprocess.run(["git", "-C", str(racine), "archive", rev, str(rel)], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "--strip-components", str(len(rel.parts)), "-C", str(dossier)], input=arch, check=True)
    for f in (PROJET / "assets" / "son").glob("*.wav"):
        (dossier / "assets" / "son").mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dossier / "assets" / "son" / f.name)
    print(f"{rel} @ {rev} → {dossier}")


def prouver(projet, rev, pas=0.5):
    projet = Path(projet).resolve()
    t = (projet / "donnees" / "donnees.js").read_text()
    D = json.loads(t[t.index("{"):t.rindex("}") + 1])
    inst = {round(k * pas, 4) for k in range(int(D["duree"] / pas))}
    for v in D["evenements"].values():
        if not isinstance(v, dict):
            continue
        for x in (v["t"] if isinstance(v.get("t"), list) else [v.get("t")]):
            if isinstance(x, (int, float)) and 0 <= x < D["duree"]:
                inst.add(round(x, 4))
    at = ",".join(str(x) for x in sorted(inst))
    tmp = Path(tempfile.mkdtemp(prefix="prouver-", dir="/tmp"))
    try:
        extraire(rev, tmp / "ref")
        empreindre(tmp / "ref", tmp / "ref.json", at=at)
        empreindre(projet, tmp / "cand.json", at=at)
        return comparer(tmp / "ref.json", tmp / "cand.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    a = sys.argv[1:]
    if a and a[0] == "prouver":
        pas = float(a[a.index("--pas") + 1]) if "--pas" in a else 0.5
        return prouver(a[1], a[2], pas)
    if a and a[0] == "extraire":
        extraire(a[1], a[2]); return 0
    if a and a[0] == "donnees":
        return donnees(a[1], a[2])
    if a and a[0] == "mp4":                      # empreintes d'un MP4 déjà rendu : identite.py mp4 <film.mp4> <sortie.json>
        im = empreintes_video(a[1])
        Path(a[2]).write_text(json.dumps({"projet": None, "mode": f"mp4 {a[1]}", "nombre": len(im), "images": im}, indent=0))
        print(f"{len(im)} images empreintes → {a[2]}")
        return 0
    if not a or a[0] not in ("empreindre", "comparer"):
        print(__doc__); return 2

    def opt(nom):
        if nom in a:
            i = a.index(nom); v = a[i + 1]; del a[i:i + 2]; return v
        return None
    if a[0] == "empreindre":
        at, garder = opt("--at"), opt("--garder")
        empreindre(a[1], a[2], at=at, garder=garder)
        return 0
    d, im = opt("--diff"), opt("--images")
    decs = []
    while "--decalage" in a:
        v = opt("--decalage")
        decs += [(int(x.split(":")[0]), int(x.split(":")[1])) for x in v.split(",") if x.strip()]
    v = opt("--voulu")
    voulu = [(int(x.split("-")[0]), int(x.split("-")[-1])) for x in (v or "").split(",") if x.strip()]
    return comparer(a[1], a[2], diff=d, images=im, decalages=decs, voulu=voulu)


if __name__ == "__main__":
    sys.exit(main())
