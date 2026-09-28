#!/usr/bin/env python3
"""Spatialisation d'un FORMAT dérivé (16:9, 1:1…) : les petits sons sont panoramiqués sur la trajectoire du point du
9:16 ; où l'image du format met-elle le point de l'autre côté ? Fenêtres « miroir » de la recette tirées des données,
et mesure D−G des stems contre le côté du point à l'image (28/09, échange du prénom).

    python3 outils/espace_format.py fenetres --format /opt/vokio-ads/videos/showcase-iphone/formats/16x9/donnees/point-resolu.json
          --de 17.3 --a 34.416667 [--ref …/showcase-iphone/donnees/point-resolu.json] [--fondu 0.05] [--min 0.2]
          [--recette son/recettes/hybride-16x9.json --pistes sfx,point,ecriture,objets [--poser]]
        → dans [de, a] : les plages où le format met le point du côté OPPOSÉ au 9:16 (« miroir ») et du MÊME côté
          (« tel quel ») ; une bascule tombe au passage du point de la référence par le milieu de son image (interpolé
          entre deux images : là, gauche = droite et l'échange est inaudible), le fondu de mixer.py (hors de la fenêtre)
          est centré sur ce passage. Une plage plus courte que --min s est fondue dans ses voisines. Avec --recette :
          compare aux fenêtres « miroir » des pistes (code 1 si elles diffèrent) ; --poser les y écrit (seules les
          fenêtres qui touchent [de, a] sont remplacées ; « mono » n'est pas touché).
    python3 outils/espace_format.py mesurer son/hybride-16x9/stems --format …/formats/16x9/donnees/point-resolu.json
          [--pistes sfx,point,ecriture,objets] [--pas 0.1] [--seuil -60] [--de 0 --a 50.07]
          [--instants 20.667,21.433,22.2,24.367 --duree 0.15] [--json r.json]
        → par tranche de --pas s où la piste est active (RMS ≥ --seuil dBFS) : D−G (dB) du son et côté du point à
          l'image (−1 gauche … +1 droite, point visible seulement) ; « contradiction » : son à plus de 1 dB du mauvais
          côté alors que le point est à plus de 15 % du milieu. --instants : D−G de chaque piste sur [t, t + duree]
          (les touchers de l'agenda). Code 1 s'il reste une contradiction.
Largeur d'image : lue dans showcase-iphone/mise-en-page/formats.json d'après le chemin (…/formats/<f>/… ; sinon 9x16),
ou --largeur / --largeur-ref. Rien n'est écrit hors de --json et de la recette avec --poser.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sonlib as L  # noqa: E402

IMAGE = Path("/opt/vokio-ads/videos/showcase-iphone")
REF_DEFAUT = IMAGE / "donnees/point-resolu.json"
PISTES_DEFAUT = ["sfx", "point", "ecriture", "objets"]


def largeur_de(chemin, forcee=None):
    if forcee:
        return float(forcee)
    m = re.search(r"formats/([0-9]+x[0-9]+)/", str(Path(chemin).resolve()))
    f = m.group(1) if m else "9x16"
    return float(json.loads((IMAGE / "mise-en-page/formats.json").read_text())[f]["largeur"])


def cote(images, W):
    """(t, côté −1…1 ou nan si le point est invisible) par image."""
    t = np.array([p["t"] for p in images], dtype=float)
    c = np.array([(p["x"] - W / 2) / (W / 2) if p.get("d", 0) > 0 else np.nan for p in images], dtype=float)
    return t, c


def r6(x):
    return round(float(x) + 0.0, 6)


def plages(ref, fmt, Wr, Wf, de, a, mini=0.2):
    """Plages [t0, t1, « miroir » | « tel quel »] couvrant [de, a], bornes au passage du point de référence par le milieu."""
    t, cr = cote(ref, Wr)
    _, cf = cote(fmt, Wf)
    idx = [i for i in range(len(t)) if de - 1e-9 <= t[i] <= a + 1e-9]
    etat = []
    for i in idx:
        if np.isnan(cr[i]) or np.isnan(cf[i]) or cr[i] * cf[i] == 0:
            etat.append(None)
        else:
            etat.append("miroir" if cr[i] * cf[i] < 0 else "tel quel")
    # images invisibles ou au milieu : l'état de la voisine précédente (sinon suivante)
    for k in range(len(etat)):
        if etat[k] is None and k > 0:
            etat[k] = etat[k - 1]
    for k in range(len(etat) - 2, -1, -1):
        if etat[k] is None:
            etat[k] = etat[k + 1]
    runs = []
    for k, i in enumerate(idx):
        if runs and runs[-1][2] == etat[k]:
            runs[-1][1] = k
        else:
            runs.append([k, k, etat[k]])

    def bascule(k):                           # entre idx[k-1] et idx[k] : où le côté de la référence passe par 0
        i0, i1 = idx[k - 1], idx[k]
        c0, c1 = cr[i0], cr[i1]
        if not np.isnan(c0) and not np.isnan(c1) and c0 != c1 and c0 * c1 <= 0:
            return t[i0] + (t[i1] - t[i0]) * (0 - c0) / (c1 - c0)
        return 0.5 * (t[i0] + t[i1])          # le côté du FORMAT a changé : à mi-chemin

    P = []
    for k0, k1, e in runs:
        t0 = de if not P else P[-1][1]
        t1 = a if k1 == len(idx) - 1 else bascule(k1 + 1)
        P.append([t0, t1, e])
    # une plage trop courte est fondue dans la précédente (ou la suivante)
    ok = False
    while not ok and len(P) > 1:
        ok = True
        for j, (t0, t1, e) in enumerate(P):
            if t1 - t0 < mini:
                v = j - 1 if j > 0 else j + 1
                lo, hi = min(P[v][0], t0), max(P[v][1], t1)
                P[v] = [lo, hi, P[v][2]]
                del P[j]
                ok = False
                break
    fus = []
    for p in P:
        if fus and fus[-1][2] == p[2]:
            fus[-1][1] = p[1]
        else:
            fus.append(list(p))
    return fus


def fenetres_miroir(P, de, a, fondu):
    """Fenêtres de mixer.py (fondu HORS de la fenêtre) : une bascule intérieure est au milieu de son fondu."""
    F = []
    for t0, t1, e in P:
        if e != "miroir":
            continue
        g = t0 if t0 <= de + 1e-9 else t0 + fondu / 2
        d = t1 if t1 >= a - 1e-9 else t1 - fondu / 2
        F.append([r6(g), r6(d)])
    return F


def poser(recette, pistes, F, de, a, ecrire):
    R = json.loads(Path(recette).read_text())
    ecarts = {}
    for p in R["pistes"]:
        if p["nom"] not in pistes:
            continue
        garde = [w for w in p.get("miroir", []) if w[1] < de - 1e-6 or w[0] > a + 1e-6]
        dedans = [w for w in p.get("miroir", []) if not (w[1] < de - 1e-6 or w[0] > a + 1e-6)]
        if [[r6(x), r6(y)] for x, y in dedans] != F:
            ecarts[p["nom"]] = {"recette": dedans, "donnees": F}
        if ecrire:
            p["miroir"] = sorted(garde + F)
    if ecrire:
        Path(recette).write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n")
    return ecarts


def db(x):
    return 20 * np.log10(max(float(x), 1e-12))


def mesurer(dossier, fmt, Wf, pistes, pas, seuil, de, a, instants, duree):
    t, cf = cote(fmt, Wf)
    fps = 1 / np.median(np.diff(t))

    def cote_a(tt):
        i = int(round(tt * fps))
        return float(cf[i]) if 0 <= i < len(cf) else float("nan")

    out = {"format": str(fmt), "largeur": Wf, "pistes": {}, "instants": {}}
    for nom in pistes:
        f = Path(dossier) / f"{nom}.wav"
        if not f.exists():
            continue
        x = L.stereo(L.lire(f))
        fin = min(a, len(x) / L.SR)
        lignes, contra = [], []
        for t0 in np.arange(de, fin - 1e-9, pas):
            seg = x[int(round(t0 * L.SR)):int(round((t0 + pas) * L.SR))]
            if not len(seg):
                continue
            l, r = np.sqrt((seg ** 2).mean(axis=0))
            niv = db(max(l, r))
            if niv < seuil:
                continue
            dg = db(r) - db(l)
            c = cote_a(t0 + pas / 2)
            q = {"t": r6(t0), "niveau_dbfs": round(niv, 1), "d_moins_g_db": round(dg, 2),
                 "cote_image": None if np.isnan(c) else round(c, 3)}
            q["contradiction"] = bool(not np.isnan(c) and abs(c) > 0.15 and abs(dg) > 1.0 and np.sign(dg) != np.sign(c))
            lignes.append(q)
            if q["contradiction"]:
                contra.append(q)
        out["pistes"][nom] = {"tranches_actives": len(lignes), "contradictions": contra, "tranches": lignes}
        for ti in instants:
            seg = x[int(round(ti * L.SR)):int(round((ti + duree) * L.SR))]
            l, r = np.sqrt((seg ** 2).mean(axis=0))
            if db(max(l, r)) < seuil:
                continue
            c = cote_a(ti + duree / 2)
            out["instants"].setdefault(f"{ti:g}", {})[nom] = {
                "d_moins_g_db": round(db(r) - db(l), 2), "niveau_dbfs": round(db(max(l, r)), 1),
                "cote_image": None if np.isnan(c) else round(c, 3)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fenetres")
    f.add_argument("--format", required=True)
    f.add_argument("--ref", default=str(REF_DEFAUT))
    f.add_argument("--de", type=float, required=True)
    f.add_argument("--a", type=float, required=True)
    f.add_argument("--fondu", type=float, default=0.05)
    f.add_argument("--min", type=float, default=0.2)
    f.add_argument("--largeur", type=float)
    f.add_argument("--largeur-ref", type=float)
    f.add_argument("--recette")
    f.add_argument("--pistes", default=",".join(PISTES_DEFAUT))
    f.add_argument("--poser", action="store_true")
    m = sp.add_parser("mesurer")
    m.add_argument("stems")
    m.add_argument("--format", required=True)
    m.add_argument("--largeur", type=float)
    m.add_argument("--pistes", default=",".join(PISTES_DEFAUT))
    m.add_argument("--pas", type=float, default=0.1)
    m.add_argument("--seuil", type=float, default=-60.0)
    m.add_argument("--de", type=float, default=0.0)
    m.add_argument("--a", type=float, default=1e9)
    m.add_argument("--instants", default="")
    m.add_argument("--duree", type=float, default=0.15)
    m.add_argument("--json")
    a = ap.parse_args()
    fmt = json.loads(Path(a.format).read_text())["images"]
    Wf = largeur_de(a.format, a.largeur)
    if a.cmd == "fenetres":
        ref = json.loads(Path(a.ref).read_text())["images"]
        Wr = largeur_de(a.ref, a.largeur_ref)
        P = plages(ref, fmt, Wr, Wf, a.de, a.a, a.min)
        for t0, t1, e in P:
            print(f"  {t0:10.6f} → {t1:10.6f}  {e}  ({t1 - t0:.3f} s)")
        F = fenetres_miroir(P, a.de, a.a, a.fondu)
        print(f"fenêtres « miroir » (fondu {a.fondu} s hors fenêtre, centré sur chaque bascule intérieure) : {json.dumps(F)}")
        if a.recette:
            ec = poser(a.recette, a.pistes.split(","), F, a.de, a.a, a.poser)
            if not ec:
                print("recette : conforme aux données")
            else:
                for k, v in ec.items():
                    print(f"recette, {k} : {v['recette']} ≠ données {v['donnees']}" + ("  → posé" if a.poser else ""))
                if not a.poser:
                    sys.exit(1)
        return
    inst = [float(v) for v in a.instants.split(",") if v.strip()]
    r = mesurer(a.stems, fmt, Wf, a.pistes.split(","), a.pas, a.seuil, a.de, a.a, inst, a.duree)
    n = 0
    for nom, v in r["pistes"].items():
        n += len(v["contradictions"])
        pires = sorted(v["contradictions"], key=lambda q: -abs(q["d_moins_g_db"]))[:6]
        print(f"  {nom:9s} {v['tranches_actives']:4d} tranches actives, {len(v['contradictions'])} contradiction(s)"
              + ("" if not pires else " : " + ", ".join(f"{q['t']:.2f} s D−G {q['d_moins_g_db']:+.1f} dB, point {q['cote_image']:+.2f}" for q in pires)))
    for ti, v in r["instants"].items():
        print(f"  {float(ti):7.3f} s : " + " | ".join(f"{k} D−G {q['d_moins_g_db']:+.1f} dB ({q['niveau_dbfs']:.0f} dBFS, point {q['cote_image'] if q['cote_image'] is not None else '—'})" for k, q in v.items()))
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(1 if n else 0)


if __name__ == "__main__":
    main()
