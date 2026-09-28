#!/usr/bin/env python3
"""Revue d'UNE scène image par image dans un projet rendable (9:16 ou copie de format) : usage en une ligne :

    python3 outils/revue_scene.py <instants|planche|identite|mp4> <racine> <scène> [<référence>] [options]

  instants <racine> <scène>                  les instants clés de la scène, à l'image près, tirés de <racine>/donnees
                                              (DONNEES.scenes, .evenements) : raccords d'entrée et de sortie (image d'avant,
                                              1re, 2e ; avant-dernière, dernière, 1re et 2e de la scène suivante), chaque
                                              événement qui tombe dans la scène (début et fin d'une plage), une grille --pas ;
                                              imprime le tableau et la liste --at prête à coller.
  planche  <racine> <scène>                  hf snapshot (sous flock /tmp/hf-rendu.lock) à ces instants → --images D, puis
                                              planche.png avec les zones sûres du format (mise-en-page/formats.json) et
                                              planche-vue-<N>.png sans zones pour --vues 852,393 (lisibilité réelle).
  identite <racine> <scène> <réf>            la scène rend-elle À L'IMAGE PRÈS comme <réf> (un projet rendable, ou git:<rév>
                                              extrait par outils/identite.py) ? sha256 des pixels RGBA de chaque instant ;
                                              carte des écarts (PNG) des images qui diffèrent ; code 1 si une image diffère.
  mp4      <racine> <scène> <film.mp4>        la scène ressemble-t-elle, au codec près, aux images d'un MP4 déjà livré (avec
                                              perte, H.264 4:2:0) ? PSNR, écart moyen, part de pixels à plus de --fort niveaux
                                              et boîte de ces pixels par image ; planche des pires (MP4 | projet | écart ×4) ;
                                              code 1 si une image passe sous --psnr, tombe de plus de --chute dB sous le PSNR
                                              médian de la scène (le bruit du codec est régulier, un écart réel ne l'est pas :
                                              une image de décalage sur s1 coûte 5 à 21 dB) ou dépasse --part.

  Options : --pas S (grille, défaut 0,5 s ; 0 = aucune) · --toutes (CHAQUE image de la scène, plus les raccords) ·
            --at t,t (instants imposés, en s, à la place des instants clés) · --plus t,t (ajoutés aux instants clés) · --images D (défaut <scratch>/revue-<scène>, vidé à chaque passe) ·
            --vues 852,393 · --psnr 38 · --chute 3 · --fort 48 · --part 0.0002 · --json rapport.json
  Exemples : revue_scene.py planche formats/16x9 s1-sonnerie --vues 852,393 --images /tmp/x/s1
             revue_scene.py identite /tmp/x/c9 s1-sonnerie git:aa4dd24 --toutes
             revue_scene.py mp4 /tmp/x/c9 s1-sonnerie /root/vokio-uploads/videos/showcase/le-point-sur-le-i-iphone.mp4 --toutes
  Un instant = ceil(image / fps, 6 décimales) : jamais avant l'image (un hôte qui finit à 4,6333 est démonté à l'image 139,
  comme au rendu). Idempotent ; n'écrit que dans --images et --json (jamais dans <racine> ni dans la source).
"""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mise_en_page  # noqa: E402

PROJET = Path(__file__).resolve().parents[1]
HF = "/opt/vokio-ads/bin/hf"
VERROU = "/tmp/hf-rendu.lock"
SCRATCH = Path(tempfile.gettempdir())


def donnees(racine):
    t = (Path(racine) / "donnees" / "donnees.js").read_text()
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def temps(image, fps):
    """Instant d'une image, arrondi VERS LE HAUT au millionième : jamais avant l'image."""
    return math.ceil(image / fps * 1e6 - 1e-6) / 1e6


def instants(D, scene, pas=0.5, toutes=False, at=None, plus=None):
    """[(image, t, étiquette)] triés, sans doublon d'image. at : remplace tout ; plus : s'ajoute aux instants clés."""
    fps, S = D["fps"], D["scenes"]
    if scene not in S:
        raise SystemExit(f"scène inconnue : {scene} (connues : {', '.join(S)})")
    sc = S[scene]
    a, b = sc["image_debut"], sc["image_fin"]                 # b exclu : 1re image de la scène suivante
    n_film = int(round(D["duree"] * fps))
    lab = {}

    def ajouter(k, nom):
        if 0 <= k < n_film:
            lab.setdefault(k, [])
            if nom not in lab[k]:
                lab[k].append(nom)
    if at:
        for t in at:
            ajouter(int(round(float(t) * fps)), f"imposé {t}")
    else:
        for k, nom in [(a - 1, "raccord : dernière de la scène d'avant"), (a, "1re image"), (a + 1, "2e image"),
                       (b - 2, "avant-dernière"), (b - 1, "dernière image"), (b, "raccord : 1re de la suivante"),
                       (b + 1, "2e de la suivante")]:
            ajouter(k, nom)
        for nom, v in (D.get("evenements") or {}).items():
            if not isinstance(v, dict):
                continue
            ims = v.get("images") if "images" in v else [v.get("image")]
            ims = ims if isinstance(ims, list) else [ims]
            for i, k in enumerate(ims):
                if isinstance(k, int) and a - 1 <= k <= b + 1:
                    ajouter(k, nom + ("" if len(ims) == 1 else (" (début)" if i == 0 else " (fin)")))
        if pas and pas > 0:
            k = 0
            while a + k * pas * fps < b:
                ajouter(a + int(round(k * pas * fps)), f"grille {pas} s")
                k += 1
        if toutes:
            for k in range(a, b):
                ajouter(k, "")
        for t in (plus or []):
            ajouter(int(round(float(t) * fps)), f"ajouté {t}")
    return [(k, temps(k, fps), " · ".join(x for x in lab[k] if x)) for k in sorted(lab)]


def snapshots(racine, liste, dossier):
    """hf snapshot aux instants de `liste` → {image: png}. Sous le verrou des rendus."""
    dossier = Path(dossier)
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)
    at = ",".join(f"{t:.6f}" for _, t, _ in liste)
    cmd = ["flock", VERROU, HF, "snapshot", str(Path(racine).resolve()), "--no-end", "--at", at, "-o", str(dossier),
           "--describe", "false"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if r.returncode:
        raise SystemExit(f"hf snapshot a échoué :\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    # hf nomme frame-<rang>-at-<t arrondi au millième>s.png (il positionne, lui, le temps exact) : rang, puis contrôle du millième
    import re
    par_rang = {}
    for f in dossier.glob("frame-*-at-*.png"):
        m = re.match(r"frame-(\d+)-at-([0-9.]+)s\.png$", f.name)
        if m:
            par_rang[int(m.group(1))] = (float(m.group(2)), f)
    out = {}
    for i, (k, t, _) in enumerate(liste):
        if i not in par_rang or abs(par_rang[i][0] - t) > 0.0006:
            raise SystemExit(f"pas d'image n° {i} à {t} s dans {dossier} (trouvé : {par_rang.get(i)})")
        out[k] = par_rang[i][1]
    return out


def police(n=18):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", n)
    except OSError:
        return ImageFont.load_default()


def feuille(cases, sortie, largeur=480, zones=None, marge=None, cols=None):
    """cases = [(titre, [PIL.Image, …])] : une ligne par case si plusieurs images, sinon une grille."""
    if not cases:
        return None
    w0, h0 = cases[0][1][0].size
    k = largeur / w0
    w, h = int(w0 * k), int(h0 * k)
    par_case = max(len(ims) for _, ims in cases)
    if cols is None:
        cols = par_case if par_case > 1 else (3 if w > h else 6)
    grille = par_case == 1
    n_lignes = (len(cases) + cols - 1) // cols if grille else len(cases)
    F = Image.new("RGB", (cols * (w + 12) + 12, n_lignes * (h + 40) + 12), (255, 255, 255))
    d = ImageDraw.Draw(F)
    P = police(16)
    for i, (titre, ims) in enumerate(cases):
        for j, im in enumerate(ims):
            col, lig = (i % cols, i // cols) if grille else (j, i)
            x, y = 12 + col * (w + 12), 12 + lig * (h + 40)
            im = im.convert("RGB")
            if zones is not None:
                dr = ImageDraw.Draw(im, "RGBA")
                for z in zones:
                    c = (192, 69, 44, 70) if z["sorte"] == "interdite" else (239, 164, 36, 45)
                    dr.rectangle(z["boite"], fill=c, outline=c[:3] + (200,), width=3)
                if marge:
                    dr.line([(marge, 0), (marge, im.height)], fill=(38, 32, 25, 90), width=2)
                    dr.line([(im.width - marge, 0), (im.width - marge, im.height)], fill=(38, 32, 25, 90), width=2)
            F.paste(im.resize((w, h), Image.LANCZOS), (x, y + 26))
            if j == 0:
                d.text((x, y + 4), titre[:int(cols * (w + 12) / 9) if not grille else int(w / 8.5)], fill=(38, 32, 25), font=P)
    F.save(sortie)
    return sortie


def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA"))


def carte_ecart(a, b, sortie):
    """PNG : le candidat assombri, pixels différents en terracotta ; renvoie max, nombre, boîte."""
    dif = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    ys, xs = np.nonzero(dif)
    info = {"max": int(dif.max()), "pixels": int(len(xs)),
            "boite": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None}
    if sortie is not None:
        base = (b[:, :, :3].astype(np.float32) * 0.35 + 165).clip(0, 255).astype(np.uint8)
        base[dif > 0] = (192, 69, 44)
        Image.fromarray(base).save(sortie)
    return info


def images_mp4(mp4, voulues):
    """{image: tableau RGB} des images `voulues` d'un MP4 (décodé depuis le début, arrêt à la dernière voulue)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(mp4)], capture_output=True, text=True, check=True)
    w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    fin = max(voulues) + 1
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(mp4), "-frames:v", str(fin), "-vf",
                          "scale=in_color_matrix=auto:in_range=auto:out_range=full", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-"], stdout=subprocess.PIPE)
    out, n, t = {}, 0, w * h * 3
    while n < fin:
        buf = p.stdout.read(t)
        if len(buf) < t:
            break
        if n in voulues:
            out[n] = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 3).copy()
        n += 1
    p.stdout.close()
    p.wait()
    return out


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("action", choices=["instants", "planche", "identite", "mp4"])
    A.add_argument("racine")
    A.add_argument("scene")
    A.add_argument("reference", nargs="?")
    A.add_argument("--pas", type=float, default=0.5)
    A.add_argument("--toutes", action="store_true")
    A.add_argument("--at")
    A.add_argument("--plus")
    A.add_argument("--images")
    A.add_argument("--vues")
    A.add_argument("--psnr", type=float, default=38.0)
    A.add_argument("--chute", type=float, default=3.0)
    A.add_argument("--fort", type=int, default=48)
    A.add_argument("--part", type=float, default=0.0002)
    A.add_argument("--json")
    a = A.parse_args()
    racine = Path(a.racine).resolve()
    D = donnees(racine)
    nom_format = (D.get("format") or {}).get("nom") or "9x16"
    L = instants(D, a.scene, a.pas, a.toutes, a.at.split(",") if a.at else None, a.plus.split(",") if a.plus else None)
    images = Path(a.images).resolve() if a.images else SCRATCH / f"revue-{a.scene}"
    rapport = {"racine": str(racine), "format": nom_format, "scene": a.scene, "action": a.action,
               "instants": [{"image": k, "t": t, "quoi": q} for k, t, q in L]}
    code = 0

    if a.action == "instants":
        for k, t, q in L:
            print(f"  image {k:5d}  t {t:10.6f}  {q}")
        print("--at " + ",".join(f"{t:.6f}" for _, t, _ in L))

    elif a.action == "planche":
        M = mise_en_page.charger(nom_format)
        S = snapshots(racine, L, images / "png")
        cases = [(f"{t:.3f} s · im. {k}" + (f" · {q}" if q else ""), [Image.open(S[k])]) for k, t, q in L]
        p = feuille(cases, images / "planche.png", 480, M["format"]["zones"], M["format"]["marge_laterale"])
        print(f"planche ({len(L)} images, zones du {nom_format}) : {p}")
        rapport["planche"] = str(p)
        for v in (a.vues.split(",") if a.vues else []):
            p = feuille(cases, images / f"planche-vue-{int(v)}.png", int(v), None, None, cols=2)
            print(f"planche vue {v} px : {p}")
            rapport[f"planche_vue_{int(v)}"] = str(p)

    elif a.action == "identite":
        if not a.reference:
            raise SystemExit("identite : <réf> manquante (un projet rendable ou git:<révision>)")
        tmp = None
        ref = a.reference
        if ref.startswith("git:"):
            tmp = Path(tempfile.mkdtemp(prefix="revue-ref-", dir=str(SCRATCH)))
            subprocess.run([sys.executable, str(PROJET / "outils" / "identite.py"), "extraire", ref[4:], str(tmp / "ref")],
                           check=True)
            ref = tmp / "ref"
        try:
            Sa = snapshots(racine, L, images / "candidat")
            Sb = snapshots(Path(ref), L, images / "reference")
            diffs = []
            for k, t, q in L:
                x, y = rgba(Sb[k]), rgba(Sa[k])
                if x.shape != y.shape or hashlib.sha256(x.tobytes()).digest() != hashlib.sha256(y.tobytes()).digest():
                    info = carte_ecart(x, y, images / f"ecart-{k:05d}.png") if x.shape == y.shape else {"taille": "différente"}
                    diffs.append({"image": k, "t": t, "quoi": q} | info)
            rapport["differentes"] = diffs
            rapport["identiques"] = len(L) - len(diffs)
            print(f"{a.scene} : {len(L) - len(diffs)}/{len(L)} images identiques à {a.reference} (sha256 RGBA)")
            for d in diffs:
                print(f"  ✗ image {d['image']} ({d['t']:.4f} s, {d['quoi']}) : {d}")
            code = 1 if diffs else 0
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    elif a.action == "mp4":
        if not a.reference:
            raise SystemExit("mp4 : <film.mp4> manquant")
        S = snapshots(racine, L, images / "candidat")
        V = images_mp4(a.reference, {k for k, _, _ in L})
        res = []
        for k, t, q in L:
            if k not in V:
                res.append({"image": k, "t": t, "quoi": q, "absente_du_mp4": True}); code = 1; continue
            c = rgba(S[k])[:, :, :3].astype(np.int16)
            v = V[k].astype(np.int16)
            if c.shape != v.shape:
                raise SystemExit(f"tailles différentes : projet {c.shape[1]}×{c.shape[0]}, MP4 {v.shape[1]}×{v.shape[0]}")
            d = np.abs(c - v)
            mse = float((d.astype(np.float64) ** 2).mean())
            psnr = 99.0 if mse == 0 else 10 * math.log10(255 ** 2 / mse)
            fort = d.max(axis=2) > a.fort
            ys, xs = np.nonzero(fort)
            e = {"image": k, "t": t, "quoi": q, "psnr": round(psnr, 2), "ecart_moyen": round(float(d.mean()), 3),
                 "part_forte": round(float(fort.mean()), 6),
                 "boite_forte": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None}
            res.append(e)
        ps = [e["psnr"] for e in res if "psnr" in e]
        med = sorted(ps)[len(ps) // 2] if ps else 0
        for e in res:
            if "psnr" in e:
                e["ok"] = e["psnr"] >= a.psnr and e["psnr"] >= med - a.chute and e["part_forte"] <= a.part
        rapport["images"] = res
        rapport["psnr_median"] = med
        mauvais = [e for e in res if not e.get("ok")]
        print(f"{a.scene} contre {Path(a.reference).name} : {len(res) - len(mauvais)}/{len(res)} images conformes au codec près "
              f"(PSNR ≥ {a.psnr} dB et ≥ médian − {a.chute} dB, ≤ {a.part:.2%} de pixels à plus de {a.fort} niveaux) ; "
              f"PSNR min {min(ps):.2f}, médian {med:.2f} dB")
        for e in mauvais:
            print(f"  ✗ {e}")
        pires = sorted([e for e in res if "psnr" in e], key=lambda e: e["psnr"])[:4]
        cases = []
        for e in pires:
            k = e["image"]
            c = rgba(S[k])[:, :, :3]
            dif = (np.abs(c.astype(np.int16) - V[k].astype(np.int16)).max(axis=2) * 4).clip(0, 255).astype(np.uint8)
            cases.append((f"im. {k} · {e['t']:.3f} s · PSNR {e['psnr']} dB · MP4 | projet | écart ×4",
                          [Image.fromarray(V[k]), Image.fromarray(c), Image.fromarray(255 - dif)]))
        p = feuille(cases, images / "pires.png", 360)
        print(f"planche des pires : {p}")
        rapport["planche_pires"] = str(p)
        code = 1 if mauvais else 0

    if a.json:
        Path(a.json).write_text(json.dumps(rapport, ensure_ascii=False, indent=1))
        print(f"rapport : {a.json}")
    return code


if __name__ == "__main__":
    sys.exit(main())
