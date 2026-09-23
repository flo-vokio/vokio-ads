#!/usr/bin/env python3
"""La sonnerie de la pub « sonnerie », synthétisée ici, et les maquettes sonores.

    outils/sonnerie_son.py              une sonnerie par durée de vide
    outils/sonnerie_son.py --apercus    + la bande son de chaque variante, sans image

Rien n'est téléchargé : la sonnerie est calculée (deux tons en trille, la
vibration du boîtier, une petite pièce), donc aucune question de droits, et on
sait au centième où commence chaque sonnerie. C'est ce qui cale le compteur
« 1 sonnerie… 2… 3… » : les débuts sont écrits dans `sonnerie-<V>s.json`, pas
retrouvés par détection dans un fichier qu'on n'a pas fait.

La sonnerie est construite À REBOURS depuis la bascule : la dernière commence
juste avant V et y est coupée net en pleine trille. C'est le « clic » du
storyboard. Avec un rythme fixe, la bascule tombait dans le silence entre deux
sonneries, et la coupure ne s'entendait plus.
"""
import argparse
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

RACINE = Path("/opt/vokio-ads")
PROJET = RACINE / "videos" / "vokio-sonnerie"
SR = 48000


def trille(duree, s):
    """Deux tons alternés vite : la sonnerie électronique la plus neutre, ni
    fixe à cloche ni mélodie de marque."""
    t = np.arange(int(duree * SR)) / SR
    f1, f2 = s["tons"]
    # alternance adoucie : un créneau à fronts de 3 ms, pas un carré qui claque
    alt = 0.5 + 0.5 * np.tanh(np.sin(2 * np.pi * s["trille_hz"] * t) * 12)
    ton = alt * np.sin(2 * np.pi * f1 * t) + (1 - alt) * np.sin(2 * np.pi * f2 * t)
    ton += 0.12 * (alt * np.sin(4 * np.pi * f1 * t) + (1 - alt) * np.sin(4 * np.pi * f2 * t))
    # la vibration du boîtier, sourde, sous la trille
    rng = np.random.default_rng(7)
    vib = np.sin(2 * np.pi * 165 * t) * (0.6 + 0.4 * rng.standard_normal(t.size).clip(-1, 1))
    vib = np.convolve(vib, np.ones(40) / 40, mode="same")
    return ton + s["vibration"] * vib


def enveloppe(n, attaque=0.008, relache=0.03):
    e = np.ones(n)
    a, r = int(attaque * SR), int(relache * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] = np.linspace(1, 0, r)
    return e


def piece(x):
    """Quelques réflexions courtes : le téléphone est posé quelque part, il ne
    sonne pas dans le vide absolu. Pas de réverbération qui traîne."""
    y = x.copy()
    for ms, g in [(11, 0.22), (17, 0.16), (29, 0.11), (43, 0.07), (61, 0.04)]:
        d = int(ms * SR / 1000)
        y[d:] += g * x[:-d]
    return y


def debuts(vide, s):
    n = max(2, round(vide / s["rythme_cible"]))
    fin = vide - s["coupe_apres"]
    return [round(s["premiere"] + i * (fin - s["premiere"]) / (n - 1), 3) for i in range(n)]


def sonnerie(vide, s):
    total = np.zeros(int(vide * SR))
    ons = debuts(vide, s)
    for i, d in enumerate(ons):
        gain = 10 ** (s["montee_db"] * i / 20)  # chaque sonnerie un peu plus fort
        for off, dur in s["motif"]:
            deb = int((d + off) * SR)
            if deb >= total.size:
                break
            bloc = trille(dur, s) * enveloppe(int(dur * SR))
            bloc = bloc[: total.size - deb]
            total[deb:deb + bloc.size] += gain * bloc
    total = piece(total)
    # la coupure : 5 ms, juste de quoi éviter un claquement numérique
    c = int(0.005 * SR)
    total[-c:] *= np.linspace(1, 0, c)
    return total / np.abs(total).max() * 0.7, ons


def ecrire_wav(chemin, x):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def lufs(f):
    out = subprocess.run(["ffmpeg", "-i", str(f), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(out.split("Integrated loudness:")[1].split("I:")[1].split("LUFS")[0])


def gain_vers(f, cible):
    """Un gain unique, mesuré. Pas `loudnorm` : en mode dynamique il compresse,
    et la montée voulue d'une sonnerie à l'autre (+1,5 dB chacune) tombait à
    +0,3 dB sans que rien ne le signale."""
    return cible - lufs(f)


def normaliser(src, dst, cible):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-af",
                    f"volume={gain_vers(src, cible):.2f}dB", "-ar", str(SR), str(dst)], check=True)


def fin_de_parole(mp3):
    """Fin réelle de la voix, pas du fichier : ElevenLabs laisse ~0,4 s de
    silence en queue, qui allongerait chaque film d'autant."""
    out = subprocess.run(["ffmpeg", "-i", str(mp3), "-af", "silencedetect=n=-40dB:d=0.12",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(l.split("silence_start: ")[1]) for l in out.splitlines() if "silence_start" in l]
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                         "format=duration", "-of", "csv=p=0", str(mp3)]))
    return starts[-1] if starts and dur - starts[-1] < 0.8 else dur


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apercus", action="store_true")
    a = p.parse_args()
    cfg = json.loads((PROJET / "variantes.json").read_text())
    s = cfg["sonnerie"]
    dossier = PROJET / "assets" / "sonnerie"
    for vide in cfg["vides"]:
        x, ons = sonnerie(vide, s)
        brut = dossier / f".brut-{vide}s.wav"
        ecrire_wav(brut, x)
        wav = dossier / f"sonnerie-{vide}s.wav"
        normaliser(brut, wav, s["lufs"])
        brut.unlink()
        (dossier / f"sonnerie-{vide}s.json").write_text(json.dumps(
            {"vide": vide, "debuts": ons, "coupe_a": vide}, indent=2) + "\n")
        print(f"{wav.relative_to(RACINE)}  sonneries à {ons}, coupée à {vide} s")

    if a.apercus:
        # Bande son seule, pour juger à l'oreille avant toute image :
        # sonnerie → coupure → voix → signature muette.
        ap = PROJET / ".media" / "apercus"
        ap.mkdir(parents=True, exist_ok=True)
        for vide in cfg["vides"]:
            for cle in cfg["phrases"]:
                voix = PROJET / "assets" / "voix" / f"{cle}.mp3"
                entree = vide + cfg["voix_apres_bascule"]
                gv = gain_vers(voix, cfg["voix_lufs"])
                fin = entree + fin_de_parole(voix) + 0.3 + cfg["signature_duree"]
                out = ap / f"sonnerie-{vide}s-{cle}.mp3"
                subprocess.run([
                    "ffmpeg", "-loglevel", "error", "-y",
                    "-i", str(dossier / f"sonnerie-{vide}s.wav"), "-i", str(voix),
                    "-filter_complex",
                    f"[1:a]aresample={SR},volume={gv:.2f}dB,adelay={int(entree * 1000)}:all=1[v];"
                    f"[0:a][v]amix=inputs=2:duration=longest:normalize=0,"
                    f"alimiter=limit=0.89:level=false,apad,"
                    f"atrim=0:{fin:.3f}[o]",
                    "-map", "[o]", "-ac", "2", "-ar", "48000", "-b:a", "192k", str(out)], check=True)
                print(f"{out.relative_to(RACINE)}  {fin:.2f} s")
