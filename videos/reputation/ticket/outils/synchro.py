#!/usr/bin/env python3
"""Synchro son/image mesurée de « Le ticket » : pour chaque événement de minutage.js, première image en mouvement
(différence d'images) contre attaque du son dans son/percussions.wav. Écart visé < 40 ms (une image = 33 ms).

    python3 /opt/vokio-ads/videos/reputation/ticket/outils/synchro.py <rendu.mp4>
"""
import subprocess
import sys

import numpy as np

sys.path.insert(0, "/opt/vokio-ads/videos/showcase/son")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import labo  # noqa: E402
from salon import M, T, SON  # noqa: E402

W, H = 270, 480
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-vf", f"scale={W}:{H},format=gray", "-f",
                      "rawvideo", "-"], capture_output=True).stdout
v = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
# zones (en px du film 1080×1920) où chaque événement se voit : sans elles, un ticket qui glisse sur la pile au même
# moment qu'un palier du compteur se faisait passer pour lui
ZONES = {"palier": (200, 560), "SMS": (820, 1400)}
dd = np.abs(np.diff(v, axis=0))
def diffs(zone):
    a, b = (int(z * H / 1920) for z in zone)
    return np.concatenate([[0], dd[:, a:b].mean(axis=(1, 2))])
d = diffs((0, 1920))
dz = {k: diffs(z) for k, z in ZONES.items()}
ev = [("avance de papier", T(b)) for k in ("ticket1", "ticket2", "chute") for b, _ in M[k]["avances"]]
ev += [("coupe", T(M["ticket1"]["coupe"])), ("coupe (chute)", T(M["chute"]["coupe"])),
       ("Demander un avis", T(M["geste"]["presse"])), ("SMS", T(M["sms"]["bulle"]))]
ev += [("palier", T(b)) for b, _ in M["semaine"]["paliers"]]
x = np.abs(labo.lire(SON / "percussions.wav").mean(axis=1))
ecarts = []
for n, t in sorted(ev, key=lambda e: e[1]):
    # on cherche dans [t - 0,1 ; t + 0,13] : le pas du papier, pas le balancement résiduel du pas d'avant.
    # Une image n porte l'état de l'instant n/30 ; le mouvement commencé à t se voit à la première image après t.
    i0 = max(1, int(round((t - 0.1) * 30)))
    seg = dz.get(n, d)[i0:i0 + 8]
    # début du geste : première image qui atteint 40 % du changement maximal de la fenêtre (un fondu ou un roulement
    # culmine plus tard, mais il COMMENCE avec le son)
    ti = (i0 + int(np.argmax(seg >= 0.4 * seg.max()))) / 30 if seg.max() > 0.05 else None
    i = max(0, int((t - 0.05) * labo.SR))
    z = x[i:i + int(0.12 * labo.SR)]
    ta = (i + int(np.argmax(z > z.max() * 0.3))) / labo.SR
    e = None if ti is None else round((ta - ti) * 1000)
    if e is not None:
        ecarts.append(abs(e))
    print(f"{n:18s} prévu {t:6.3f}  image {ti if ti is None else f'{ti:6.3f}'}  son {ta:6.3f}  écart {e} ms")
print(f"{len(ecarts)} événements, écart max {max(ecarts)} ms, moyen {np.mean(ecarts):.0f} ms")
