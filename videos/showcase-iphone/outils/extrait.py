#!/usr/bin/env python3
"""Tirer un extrait d'un film déjà rendu (bumper YouTube 6 s, teaser, boucle), son compris, sans re-rendre.

    python3 outils/extrait.py FILM.mp4 --de 41.2 --a 47 -o bumper.mp4 [--duree 6] [--fondu-entree 0.12]
                              [--fondu-sortie 0] [--lufs -14] [--tp -1] [--json rapport.json]

- coupe à l'image près [--de, --a[ (seek après décodage : pas de dérive d'image clé) ;
- --duree : complète en TENANT la dernière image (jamais d'image noire) et en prolongeant le son en silence ;
  refuse si l'extrait est déjà plus long que --duree (un bumper YouTube ne doit pas dépasser 6 s) ;
- son : fondu d'entrée (l'extrait commence en général au milieu de la musique), fondu de sortie optionnel,
  sonie ramenée à --lufs (deux passes loudnorm, crête ≤ --tp dBTP), AAC 256k 48 kHz stéréo ;
- vidéo réencodée en h264 High yuv420p bt709, CRF 16, 30 i/s, faststart ; même taille que la source ;
- rapport : durée, images, sonie et crête mesurées sur le fichier produit.
Idempotent : relancer avec les mêmes arguments redonne le même fichier.
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path


def sh(*c, capture=False):
    r = subprocess.run(list(map(str, c)), capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"échec : {' '.join(map(str, c))[:200]}\n{r.stderr[-800:]}")
    return r.stdout if capture else r


def sonie(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(f), "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    return float(m["input_i"]), float(m["input_tp"]), m


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("film"); p.add_argument("--de", type=float, required=True); p.add_argument("--a", type=float, required=True)
    p.add_argument("-o", "--sortie", required=True); p.add_argument("--duree", type=float)
    p.add_argument("--fondu-entree", type=float, default=0.12); p.add_argument("--fondu-sortie", type=float, default=0.0)
    p.add_argument("--lufs", type=float, default=-14.0); p.add_argument("--tp", type=float, default=-1.0)
    p.add_argument("--json")
    a = p.parse_args()
    longueur = a.a - a.de
    if a.duree and longueur > a.duree + 1e-6:
        sys.exit(f"l'extrait fait {longueur:.3f} s, plus que --duree {a.duree}")
    tenue = (a.duree - longueur) if a.duree else 0.0
    total = longueur + tenue
    with tempfile.TemporaryDirectory(dir="/dev/shm") as tmp:
        tmp = Path(tmp)
        # 1. son brut de l'extrait, fondus, silence de tenue
        af = [f"atrim=start={a.de}:end={a.a}", "asetpts=PTS-STARTPTS"]
        if a.fondu_entree:
            af.append(f"afade=t=in:st=0:d={a.fondu_entree}")
        if a.fondu_sortie:
            af.append(f"afade=t=out:st={longueur - a.fondu_sortie}:d={a.fondu_sortie}")
        af.append(f"apad=whole_dur={total}")
        brut = tmp / "brut.wav"
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", a.film, "-vn", "-af", ",".join(af), "-ar", 48000, "-ac", 2, brut)
        # 2. sonie en deux passes
        _, _, m = sonie(brut)
        f2 = (f"loudnorm=I={a.lufs}:TP={a.tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
        son = tmp / "son.wav"
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", brut, "-af", f2, "-ar", 48000, son)
        # 3. image : coupe à l'image, tenue de la dernière image, mux
        vf = f"trim=start={a.de}:end={a.a},setpts=PTS-STARTPTS,fps=30"
        if tenue > 0:
            vf += f",tpad=stop_mode=clone:stop_duration={tenue}"
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", a.film, "-i", son, "-map", "0:v", "-map", "1:a", "-vf", vf,
           "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", 16, "-preset", "slow",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:a", "aac", "-b:a", "256k", "-ar", 48000, "-ac", 2, "-t", f"{total:.3f}", "-movflags", "+faststart", a.sortie)
    d = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.sortie, capture=True))
    n = int(sh("ffprobe", "-v", "error", "-count_frames", "-select_streams", "v", "-show_entries", "stream=nb_read_frames",
               "-of", "csv=p=0", a.sortie, capture=True))
    i, tp, _ = sonie(a.sortie)
    rapport = {"sortie": a.sortie, "source": a.film, "de": a.de, "a": a.a, "tenue_s": round(tenue, 3),
               "duree_s": round(d, 3), "images": n, "lufs": i, "crete_dbtp": tp}
    print(json.dumps(rapport, ensure_ascii=False))
    if a.json:
        Path(a.json).write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
