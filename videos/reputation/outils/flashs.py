#!/usr/bin/env python3
"""Détecte les flashs d'une image : une image isolée qui diffère de ses deux voisines alors que ces voisines se ressemblent.

    python3 /opt/vokio-ads/videos/reputation/outils/flashs.py film.mp4 [autre.mp4 ...]

Né du retour de Florian du 21/10/2026 (« le champ scintille ») : des images de formulaire pas encore décodées sortaient
VIDES au rendu HyperFrames. Validé sur les anciennes versions (3 et 4 flashs trouvés), 0 après la planche unique.
À lancer sur tout rendu qui fait alterner des images.
"""
import subprocess
import sys

import numpy as np

W, H = 270, 480
for f in sys.argv[1:]:
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", f, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    v = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.int16)
    flashs = []
    for i in range(1, len(v) - 1):
        a, b, c = (np.abs(v[i] - v[i - 1]).mean(), np.abs(v[i] - v[i + 1]).mean(), np.abs(v[i - 1] - v[i + 1]).mean())
        if a > 2 and b > 2 and c < 0.5 * min(a, b):
            flashs.append((i, round(i / 30, 2)))
    print(f.split("/")[-1], len(v), "images, flashs :", flashs or "aucun")
