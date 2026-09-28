#!/usr/bin/env python3
"""Occupation du cadre d'un MP4, image par image, et bilan par scène (plans-titres) : usage en une ligne :

    python3 outils/occupation.py film.mp4 [--racine formats/16x9] [--pas 0.5] [--de 0 --a 47] [--seuil 24] [--json r.json]

  Pour chaque image échantillonnée (l'image n = de·fps + k·pas·fps, exacte : les mêmes que controles.py O1) : boîte englobante de tout ce qui n'est pas le papier (x0 y0 x1 y1,
  px du cadre), part de la LARGEUR et part du cadre couvertes par cette boîte, part de pixels « non papier », barycentre
  horizontal (0 = bord gauche, 1 = bord droit), pixels solaires (le point) et leur boîte, pixels non papier dans chaque zone
  du format, mouvement (écart moyen avec l'image échantillonnée précédente, niveaux 0 à 255).
  --racine : un projet rendable (9:16 = ce projet, formats/16x9…) : zones lues dans SES données (DONNEES.format), bilan par
    scène (DONNEES.scenes) : pour chaque scène, l'image « pleine » (la plus large boîte d'encre) avec sa part de largeur et son
    barycentre, la plus grande part de la bande utile couverte (hauteur utile), et les seuils de DONNEES.format.occupation
    s'il y en a : par_scene {scène: largeur_min, barycentre [min, max], hauteur_min} (recomposition du 28/09), ou la forme
    commune des plans-titres (scenes, largeur_min, barycentre) ;
    sans --racine : zones de mise-en-page/formats.json choisies d'après la taille du film.
  3e passe du 16:9 (28/09) : la SÉRIE de chaque scène compte aussi (médiane et 1er quartile de la largeur, barycentre
    horizontal médian et ses quartiles, barycentre VERTICAL médian bary_y), et DONNEES.format.occupation.fenetres juge une
    fenêtre de temps (l'accroche de 0 à 2,1 s, la voix seule de s2 à s3) ; seuils par_scene étendus : largeur_mediane_min,
    largeur_q1_min, barycentre_median, bary_y_median (fonction juger). Les seuils se fixent d'après la RÈGLE (cadre équilibré,
    ligne de lecture au milieu), jamais juste sous la mesure.
  Même mesure que le contrôle O1 de outils/controles.py (fonction mesurer, importée par lui). Lecture seule, idempotent :
  rien n'est écrit hors de --json. Décodage ffmpeg en RGB à pleine taille.
  Promu le 28/09 depuis la revue DA YouTube (scratchpad final/da-youtube/occupation.py).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

PROJET = Path(__file__).resolve().parents[1]
PAPIER = np.array([0xF4, 0xF1, 0xE8], dtype=np.int16)
SOLAIRE = np.array([0xEF, 0xA4, 0x24], dtype=np.int16)


def mesurer(img, zones=(), seuil=24, utile=None):
    """img (H, W, 3) uint8 → dict : boite, part_largeur, part_hauteur (hauteur de la boîte / cadre), part_hauteur_utile (la boîte
    rognée à la bande utile [haut_utile, bas_utile], rapportée à sa hauteur : 9:16 0 → 1500, 16:9 72 → 972), part_boite,
    part_encre, bary_x, solaire, zones {nom: pixels}. utile = (haut, bas) ; défaut : le cadre entier."""
    H, W = img.shape[:2]
    hu, bu = utile if utile else (0, H)
    f = img.astype(np.int16)
    m = np.abs(f - PAPIER).max(axis=2) > seuil
    r = {}
    if m.any():
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        r.update(boite=[x0, y0, x1, y1], part_largeur=round((x1 - x0 + 1) / W, 3), part_hauteur=round((y1 - y0 + 1) / H, 3),
                 part_hauteur_utile=round(max(0, min(y1 + 1, bu) - max(y0, hu)) / (bu - hu), 3),
                 part_boite=round((x1 - x0 + 1) * (y1 - y0 + 1) / (W * H), 3),
                 part_encre=round(float(m.mean()), 4), bary_x=round(float(xs.mean()) / W, 3), bary_y=round(float(ys.mean()) / H, 3))
    else:
        r.update(boite=None, part_largeur=0.0, part_hauteur=0.0, part_hauteur_utile=0.0, part_boite=0.0, part_encre=0.0, bary_x=None,
                 bary_y=None)
    sol = np.abs(f - SOLAIRE).max(axis=2) < 40
    if sol.sum() > 30:
        ys, xs = np.nonzero(sol)
        r["solaire"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    for z in zones:
        bx0, by0, bx1, by1 = (int(v) for v in z["boite"])
        r.setdefault("zones", {})[z["nom"]] = int(m[by0:by1, bx0:bx1].sum())
    return r


def seuils_scene(occ, nom):
    """Les seuils d'occupation d'une scène : DONNEES.format.occupation.par_scene[nom] (recomposition du 28/09 : largeur_min,
    barycentre [min, max], hauteur_min), sinon les seuils communs des plans-titres (clés « scenes », « largeur_min »,
    « barycentre » : la forme du 28/09 matin) ; None si la scène n'a pas de seuil."""
    if nom in (occ.get("par_scene") or {}):
        return {k: v for k, v in occ["par_scene"][nom].items() if not k.startswith("_")}
    if nom in occ.get("scenes", []):
        return {"largeur_min": occ.get("largeur_min", 0), "barycentre": occ.get("barycentre", [0, 1])}
    return None


def _quantile(v, q):
    v = sorted(v)
    if not v:
        return None
    i = (len(v) - 1) * q
    a, b_ = int(np.floor(i)), int(np.ceil(i))
    return round(float(v[a] + (v[b_] - v[a]) * (i - a)), 3)


def _dans(v, bornes):
    return v is not None and bornes[0] <= v <= bornes[1]


def resume_serie(serie):
    """Médianes et premier quartile d'une série [(n, mesure)] (images avec encre) : ce que le spectateur voit LE PLUS SOUVENT,
    pas seulement l'image la plus pleine (3e passe du 16:9, 28/09 : O1 ne voyait ni les 2,9 s de moitié vide de s1, ni la voix
    seule calée en bas à gauche)."""
    L = [r["part_largeur"] for _, r in serie]
    X = [r["bary_x"] for _, r in serie if r.get("bary_x") is not None]
    Y = [r["bary_y"] for _, r in serie if r.get("bary_y") is not None]
    return {"echantillons": len(serie), "largeur_mediane": _quantile(L, 0.5), "largeur_q1": _quantile(L, 0.25),
            "bary_x_median": _quantile(X, 0.5), "bary_x_q1_q3": [_quantile(X, 0.25), _quantile(X, 0.75)],
            "bary_y_median": _quantile(Y, 0.5)}


def juger(b, S):
    """Seuils d'une scène ou d'une fenêtre (formats.json occupation) contre son bilan b. Clés (toutes facultatives) :
    largeur_min, barycentre [min, max], hauteur_min (image la plus pleine, forme du 28/09) ; largeur_mediane_min,
    largeur_q1_min, barycentre_median [min, max], bary_y_median [min, max] (la série, 3e passe). → (ok, [raisons d'échec])."""
    raisons = []
    if "largeur_min" in S and not (b.get("part_largeur") or 0) >= S["largeur_min"]:
        raisons.append(f"largeur {b.get('part_largeur')} < {S['largeur_min']}")
    if "barycentre" in S and "bary_x" in b and not _dans(b["bary_x"], S["barycentre"]):
        raisons.append(f"barycentre {b['bary_x']} hors {S['barycentre']}")
    if "hauteur_min" in S and not (b.get("hauteur_utile") or 0) >= S["hauteur_min"]:
        raisons.append(f"hauteur utile {b.get('hauteur_utile')} < {S['hauteur_min']}")
    if "largeur_mediane_min" in S and not (b.get("largeur_mediane") or 0) >= S["largeur_mediane_min"]:
        raisons.append(f"largeur médiane {b.get('largeur_mediane')} < {S['largeur_mediane_min']}")
    if "largeur_q1_min" in S and not (b.get("largeur_q1") or 0) >= S["largeur_q1_min"]:
        raisons.append(f"largeur 1er quartile {b.get('largeur_q1')} < {S['largeur_q1_min']}")
    if "barycentre_median" in S and not _dans(b.get("bary_x_median"), S["barycentre_median"]):
        raisons.append(f"barycentre médian {b.get('bary_x_median')} hors {S['barycentre_median']}")
    if "bary_y_median" in S and not _dans(b.get("bary_y_median"), S["bary_y_median"]):
        raisons.append(f"barycentre vertical médian {b.get('bary_y_median')} hors {S['bary_y_median']}")
    return not raisons, raisons


def bilan_scenes(images, scenes, occ, fps=30):
    """images : [(n, mesure)] ; scenes : DONNEES.scenes ; occ : DONNEES.format.occupation (ou {}) → {scène: bilan}.
    À pleine composition : l'image de la scène où la boîte d'encre est la plus large (part de la largeur, barycentre) ; la
    hauteur est la plus grande part de la bande utile couverte sur la scène (un objet qui monte, puis se pose). Sur la série
    (3e passe) : largeur médiane et 1er quartile, barycentre horizontal médian (et quartiles), barycentre vertical médian.
    occ « fenetres » {nom: {"t": [t0, t1], seuils…}} : les mêmes mesures sur une fenêtre de temps (l'accroche, la voix seule…),
    rapportées sous la clé « fenêtre : <nom> »."""
    out = {}
    for nom, s in scenes.items():
        serie = [(k, r) for k, r in images if s["image_debut"] <= k < s["image_fin"] and r.get("boite")]
        if not serie:
            continue
        k, r = max(serie, key=lambda x: x[1]["part_largeur"])
        kh, rh = max(serie, key=lambda x: x[1].get("part_hauteur_utile", 0))
        b = {"image_pleine": k, "part_largeur": r["part_largeur"], "bary_x": r["bary_x"], "boite": r["boite"],
             "hauteur_utile": rh.get("part_hauteur_utile"), "image_haute": kh} | resume_serie(serie) | {
             "serie": [(k_, r_["part_largeur"], r_["bary_x"], r_.get("part_hauteur_utile"), r_.get("bary_y")) for k_, r_ in serie]}
        S = seuils_scene(occ, nom)
        if S:
            b["seuils"] = S
            b["ok"], b["raisons"] = juger(b, S)
        out[nom] = b
    for nom, F in (occ.get("fenetres") or {}).items():
        if nom.startswith("_"):
            continue
        n0, n1 = int(round(F["t"][0] * fps)), int(round(F["t"][1] * fps))
        serie = [(k, r) for k, r in images if n0 <= k < n1 and r.get("boite")]
        if not serie:
            continue
        b = {"fenetre_s": F["t"]} | resume_serie(serie)
        S = {kk: v for kk, v in F.items() if kk != "t" and not kk.startswith("_")}
        if S:
            b["seuils"] = S
            b["ok"], b["raisons"] = juger(b, S)
        out[f"fenêtre : {nom}"] = b
    return out


def donnees(racine):
    js = (Path(racine) / "donnees" / "donnees.js").read_text()
    i = js.index("window.DONNEES = ") + len("window.DONNEES = ")
    return json.loads(js[i:js.rstrip().rindex(";")])


def taille(film):
    st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                    "-of", "json", str(film)], capture_output=True, text=True, check=True).stdout)["streams"][0]
    n, d = st["r_frame_rate"].split("/")
    return st["width"], st["height"], float(n) / float(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("film")
    ap.add_argument("--racine")
    ap.add_argument("--pas", type=float, default=0.5)
    ap.add_argument("--de", type=float, default=0.0)
    ap.add_argument("--a", type=float, default=None)
    ap.add_argument("--seuil", type=int, default=24, help="écart RGB max au papier (défaut 24)")
    ap.add_argument("--json")
    a = ap.parse_args()
    W, H, fps = taille(a.film)
    D = donnees(a.racine) if a.racine else None
    if D:
        fmt = D.get("format") or {}
        if fmt and (fmt["largeur"], fmt["hauteur"]) != (W, H):
            raise SystemExit(f"occupation.py : le film fait {W}×{H}, la racine {fmt['largeur']}×{fmt['hauteur']}")
    else:
        F = json.loads((PROJET / "mise-en-page" / "formats.json").read_text())
        fmt = next((v for k, v in F.items() if not k.startswith("_") and (v.get("largeur"), v.get("hauteur")) == (W, H)), {})
    zones = fmt.get("zones", [])
    utile = (fmt.get("haut_utile", 0), fmt.get("bas_utile", H))
    # images EXACTES n = n0, n0 + pas, … (filtre select sur le numéro d'image : les mêmes que controles.py O1, n % 15 == 0)
    k_pas = max(1, int(round(a.pas * fps)))
    n0 = int(np.ceil(a.de * fps - 1e-6))
    n1 = int(np.floor(a.a * fps + 1e-6)) if a.a is not None else 10 ** 9
    sel = f"select='between(n\\,{n0}\\,{n1})*not(mod(n-{n0}\\,{k_pas}))'"
    cmd = ["ffmpeg", "-v", "error", "-i", str(a.film), "-vf", sel, "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    res, prec, k = [], None, 0
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        n_img = n0 + k * k_pas
        r = {"t": round(n_img / fps, 3), "image": n_img} | mesurer(img, zones, a.seuil, utile)
        if prec is not None:
            r["mouvement"] = round(float(np.abs(img.astype(np.int16) - prec).mean()), 3)
        prec = img.astype(np.int16)
        res.append(r)
        k += 1
    p.wait()
    print("     t  image  larg.  haut.  bary   encre   boîte                  solaire")
    for r in res:
        print(f"{r['t']:6.2f} {r['image']:6d}  {r['part_largeur']:5.3f}  {r['part_hauteur_utile']:5.3f}  "
              f"{r['bary_x'] if r['bary_x'] is not None else '  -  ':>5}  {r['part_encre']:6.4f}  {str(r['boite']):22s} {r.get('solaire', '')}")
    sortie = {"film": str(a.film), "taille": [W, H], "pas": a.pas, "images": res}
    if D:
        B = bilan_scenes([(r["image"], r) for r in res], D["scenes"], fmt.get("occupation") or {}, fps=round(fps))
        sortie["scenes"] = B
        print("\n                              pleine : larg.  bary  haut. │ série : larg.méd  q1    bary méd  bary y méd │ seuils")
        f_ = lambda v, w=5: f"{v:{w}.3f}" if isinstance(v, (int, float)) else f"{'-':>{w}}"
        for nom, b in B.items():
            s = "" if "ok" not in b else ("ok" if b["ok"] else "ÉCHEC : " + " ; ".join(b["raisons"]))
            print(f"{nom[:28]:28s}  {f_(b.get('part_largeur'))}  {f_(b.get('bary_x'))}  {f_(b.get('hauteur_utile'))} │ "
                  f"{f_(b.get('largeur_mediane'), 8)}  {f_(b.get('largeur_q1'))}  {f_(b.get('bary_x_median'), 8)}  "
                  f"{f_(b.get('bary_y_median'), 10)} │ {s}")
    if a.json:
        Path(a.json).write_text(json.dumps(sortie, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
