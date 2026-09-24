#!/opt/vokio-site-repo/.venv/bin/python
"""Contrôle de synchronisation mot à mot : original contre retravail.

À chaque instant (multiple de 1/30 s, donc présent dans les deux films), on
décode l'image des deux vidéos, on repère le curseur solaire dans la carte et
on en déduit combien de mots du résumé sont écrits (partie fractionnaire =
avancée dans le mot en cours), à partir des positions réelles des mots
(appel-1-mesures.json). Les deux géométries sont différentes (carte de 900 px
à y=548 dans l'original, 960 px à y=440 ici), on ramène donc tout en points
de la carte. Tolérance : l'avancée que l'écriture fait en une image à 30 i/s.

    controle_synchro.py <original.mp4> <retravail.mp4>
"""
import json
import math
import subprocess
import sys

import numpy as np

MES = json.load(open("/root/vokio-uploads/videos/ux-210926/plans-plombier/appel-1-mesures.json"))
MOTS = MES["mots"]
T = {"carteIn": 1500, "finParole": 62790, "finEcriture": 57940}
ECRITURE = [[8560, 10060, 0, 3], [19830, 21230, 3, 6], [22870, 23570, 6, 8], [23770, 25570, 8, 14],
            [30120, 32120, 14, 18], [39470, 42070, 18, 26], [48940, 52740, 26, 35],
            [54740, 55540, 35, 37], [55840, 57940, 37, 46]]

GEO = {   # carte à l'écran : gauche, haut, largeur, hauteur, courbe du zoom lent
    "original": dict(x=90, y=548, w=900, h=952,
                     zoom=lambda p: 4*p**3 if p < .5 else 1 - (-2*p + 2)**3 / 2),
    "retravail": dict(x=60, y=440, w=960, h=859,
                      zoom=lambda p: -(math.cos(math.pi*p) - 1) / 2),
}


def image(video, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", video, "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(1920, 1080, 3).astype(int)


def mots_ecrits(im, g, t_ms):
    kp = 3 * g["w"] / 1044                         # px de carte par point
    p = min(max((t_ms - T["carteIn"]) / (T["finParole"] - T["carteIn"]), 0), 1)
    z = 1 + .02 * g["zoom"](p)
    cx, cy = g["x"] + g["w"] / 2, g["y"] + g["h"] / 2
    # zone du résumé à l'écran (hors liseré orange de la carte, x < 100 pt)
    def ecran(xc, yc):
        return cx + (xc - g["w"] / 2) * z, cy + (yc - g["h"] / 2) * z
    x0, _ = ecran(34 * kp, 0)
    _, y0 = ecran(0, 100 * kp)
    x1, y1 = ecran(330 * kp, 0)[0], ecran(0, 290 * kp)[1]
    zone = im[int(y0):int(y1), int(x0):int(x1)]
    d = np.abs(zone - np.array([239, 164, 36])).sum(axis=2)
    ys, xs = np.nonzero(d < 90)
    if len(xs) < 20:
        return None
    col = np.bincount(xs).argmax()
    sel = np.abs(xs - col) <= 4
    xc_ecran = x0 + xs[sel].mean()
    yt_ecran = y0 + ys[sel].min()
    # retour en px de carte, puis en points
    xc = (xc_ecran - cx) / z + g["w"] / 2
    yt = (yt_ecran - cy) / z + g["h"] / 2
    x_cur = (xc - 2 - 6) / kp                      # curseur : left = xCur + 6, large de 4 px
    y_mot = (yt + 2) / kp                          # top = m.y - 2
    ligne = [i for i, m in enumerate(MOTS) if abs(m["y"] - y_mot) < 6]
    if not ligne:
        return None
    for i in ligne:
        m = MOTS[i]
        if m["x"] - 1.5 <= x_cur <= m["x"] + m["w"] + 1.5:
            return i + min(max((x_cur - m["x"]) / m["w"], 0), 1)
    # curseur dans une espace (flou de mouvement de l'original) : le mot le plus proche
    i = min(ligne, key=lambda j: min(abs(x_cur - MOTS[j]["x"]), abs(x_cur - MOTS[j]["x"] - MOTS[j]["w"])))
    m = MOTS[i]
    if min(abs(x_cur - m["x"]), abs(x_cur - m["x"] - m["w"])) > 6:
        return None
    return i + min(max((x_cur - m["x"]) / m["w"], 0), 1)


def attendu(t):
    n = 0
    for a, b, de, vers in ECRITURE:
        if t >= b:
            n = vers
        elif t >= a:
            return de + (vers - de) * (t - a) / (b - a)
        else:
            break
    return n


def main(orig, retr):
    instants = []
    for a, b, de, vers in ECRITURE:
        for f in range(math.ceil(a / 1000 * 30) + 1, math.floor(b / 1000 * 30), 4):
            instants.append(f / 30)
    pire, lignes = 0.0, []
    for t in instants:
        tm = t * 1000
        # tolérance : ce que l'écriture avance en une image à cet instant
        seg = next(s for s in ECRITURE if s[0] <= tm <= s[1])
        tol = (seg[3] - seg[2]) / ((seg[1] - seg[0]) / 1000 * 30)
        no = mots_ecrits(image(orig, t), GEO["original"], tm)
        nr = mots_ecrits(image(retr, t), GEO["retravail"], tm)
        ok = no is not None and nr is not None and abs(no - nr) <= tol
        if no is not None and nr is not None:
            pire = max(pire, abs(no - nr) / tol)
        lignes.append((t, no, nr, attendu(tm), tol, ok))
        print(f"t={t:7.3f} s  original {no if no is None else round(no, 3)!s:>7}  "
              f"retravail {nr if nr is None else round(nr, 3)!s:>7}  théorie {attendu(tm):6.3f}  "
              f"tol {tol:.3f}  {'ok' if ok else 'ÉCART'}")
    n_ok = sum(1 for l in lignes if l[5])
    print(f"\n{n_ok}/{len(lignes)} instants dans la tolérance d'une image ; "
          f"pire écart = {pire:.2f} image")
    return 0 if n_ok == len(lignes) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
