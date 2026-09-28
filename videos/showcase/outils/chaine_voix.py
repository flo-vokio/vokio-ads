#!/usr/bin/env python3
"""Passer un dialogue.wav dans la chaîne voix de son/mix.py, SANS le reste du mix (ni image, ni stems amont).

    python3 outils/chaine_voix.py [--dialogue son/dialogue.json] -o /dev/shm/voix.wav
    python3 outils/ausculter.py mots brut=son/dialogue.wav chaine=/dev/shm/voix.wav \
        --mots /opt/vokio-ads/videos/showcase-iphone/donnees/mots.json --cles CP:2 C1:1 C4:0

Sert à juger un nouveau découpage du dialogue (un mot assez fort ? un gain de clip nécessaire ?) avant que l'image et
les stems ne soient refaits : son/stems_amont.py exige des données d'image à la même durée, pas cet outil. Même
traitement que mix.py dialogue(), par extrait : 0,2 s de marge, gain vers −23 LUFS, CHAINE_VOIX (lue dans mix.py, jamais
recopiée), bords de 3 ms, gain vers NIV["voix_lufs"] (lu dans mix.py). Sortie 48 kHz stéréo double mono, 24 bits.
Le 28/09 : « Florian » (CP) sort à −20,0 LUFS, dans la médiane des mots de l'appelant.
"""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
RACINE = Path(__file__).resolve().parents[1]
SR = 48000


def constantes_mix():
    """CHAINE_VOIX et NIV['voix_lufs'] lus dans le source de son/mix.py (sans l'importer : il charge les données du film)."""
    src = (RACINE / "son" / "mix.py").read_text()
    m = re.search(r"^CHAINE_VOIX = (\(.*?\))\n", src, re.S | re.M)
    chaine = ast.literal_eval(m.group(1))
    v = float(re.search(r'"voix_lufs":\s*(-?[0-9.]+)', src).group(1))
    return chaine, v


def lire(p):
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, dtype="<f4").astype(np.float64)


def lufs(sig):
    st = np.stack([sig, sig], axis=1).astype(np.float32)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "pipe:0",
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"], input=st.tobytes(), capture_output=True)
    e = r.stderr.decode()
    return float(json.loads(e[e.rindex("{"):e.rindex("}") + 1])["input_i"])


def filtre(sig, f):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", "-af", f,
                        "-f", "f32le", "-"], input=sig.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<f4").astype(np.float64)


def rampe(n):
    return 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dialogue", default=str(RACINE / "son" / "dialogue.json"))
    ap.add_argument("-o", "--sortie", required=True)
    A = ap.parse_args()
    chaine, cible = constantes_mix()
    D = json.loads(Path(A.dialogue).read_text())
    v = lire(D["fichier"])
    o = np.zeros(len(v))
    for e in D["extraits"]:
        i0, i1 = int(round(e["film_in"] * SR)), int(round(e["film_out"] * SR))
        pad = int(0.2 * SR)
        seg = np.zeros(i1 - i0 + 2 * pad)
        seg[pad:pad + i1 - i0] = v[i0:i1]
        I0 = lufs(seg[pad:-pad])
        seg *= 10 ** ((-23.0 - I0) / 20)
        seg = filtre(seg, chaine)[pad:pad + i1 - i0]
        k = int(0.003 * SR)
        seg[:k] *= rampe(k)
        seg[-k:] *= rampe(k)[::-1]
        I1 = lufs(seg)
        seg *= 10 ** ((cible - I1) / 20)
        o[i0:i1] = seg
        print(f"{e['id']:5s} {e['locuteur']:8s} origine {I0:6.2f} LUFS  gain total {(-23.0 - I0) + (cible - I1):+5.1f} dB")
    st = np.stack([o, o], axis=1).astype("<f4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", A.sortie], input=st.tobytes(), check=True)
    print("→", A.sortie)


if __name__ == "__main__":
    main()
