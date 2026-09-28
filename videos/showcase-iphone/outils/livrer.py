#!/usr/bin/env python3
"""Livre un film : pose une bande son (wav) sur un MP4 déjà rendu, SANS re-rendre ni ré-encoder l'image : usage en une ligne :

    python3 outils/livrer.py image.mp4 mix.wav -o film.mp4 [--json livraison.json] [--si-identique]

  Vidéo COPIÉE (-c:v copy), audio AAC 256k 48 kHz stéréo, +faststart : l'encodage des livraisons (outils/rendre.py --son,
  outils/mixer.py --mp4). Contrôle et imprime : empreinte md5 du flux vidéo avant/après (identique, sinon code 1), sonie
  intégrée et crête vraie de l'AAC (ebur128, cible −14 LUFS, ≤ −1 dBTP), durées vidéo/audio (écart ≤ 1 image), md5 du wav.
  --json : écrit ce relevé (source, mix, md5, sonie). --si-identique : ne réécrit pas film.mp4 s'il porte déjà ce flux vidéo et
  un audio de même empreinte que celui que l'on produirait (idempotent, et rapide).
  N'écrit que -o (via un fichier partiel renommé) et --json ; le mix n'est jamais modifié (outils/mixer.py le fabrique).
Exemple (le 16:9 avec la bande son du 9:16 final) :
    python3 outils/livrer.py /root/vokio-uploads/videos/showcase/le-point-sur-le-i-16x9-image.mp4 \\
            /opt/vokio-ads/videos/showcase/son/hybride/mix-hybride.wav -o /root/vokio-uploads/videos/showcase/le-point-sur-le-i-16x9.mp4
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def md5_flux(mp4, flux):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", f"0:{flux}:0", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip().split("=")[-1]


def md5_fichier(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def sonie(mp4):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return {"LUFS": float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]), "crete_vraie_dBTP": float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])}


def durees(mp4):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(mp4)], capture_output=True, text=True,
                                  check=True).stdout)
    return {s["codec_type"]: float(s["duration"]) for s in j["streams"]}


def muxer(image, wav, sortie):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(image), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-shortest", str(sortie)],
                   check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image")
    ap.add_argument("wav")
    ap.add_argument("-o", "--sortie", required=True)
    ap.add_argument("--json")
    ap.add_argument("--si-identique", action="store_true")
    a = ap.parse_args()
    image, wav, sortie = Path(a.image).resolve(), Path(a.wav).resolve(), Path(a.sortie).resolve()
    if image == sortie:
        raise SystemExit("livrer.py : la sortie doit être un autre fichier que l'image source")
    v_src = md5_flux(image, "v")
    with tempfile.TemporaryDirectory(prefix="livrer-", dir="/dev/shm" if Path("/dev/shm").exists() else None) as t:
        essai = Path(t) / "film.mp4"
        muxer(image, wav, essai)
        a_essai = md5_flux(essai, "a")
        if a.si_identique and sortie.exists() and md5_flux(sortie, "v") == v_src and md5_flux(sortie, "a") == a_essai:
            print(f"{sortie} porte déjà cette image et cette bande son : rien à faire (--si-identique)")
        else:
            partiel = sortie.with_name("." + sortie.name + ".partiel")
            partiel.write_bytes(essai.read_bytes())
            os.replace(partiel, sortie)
    rel = {"sortie": str(sortie), "image_source": str(image), "mix": str(wav), "md5_mix": md5_fichier(wav),
           "md5_video_source": v_src, "md5_video_sortie": md5_flux(sortie, "v"), "md5_audio_sortie": md5_flux(sortie, "a")}
    rel["video_identique"] = rel["md5_video_source"] == rel["md5_video_sortie"]
    rel |= sonie(sortie)
    d = durees(sortie)
    rel["durees_s"] = d
    rel["ok"] = (rel["video_identique"] and abs(rel["LUFS"] + 14) <= 0.5 and rel["crete_vraie_dBTP"] <= -1.0
                 and abs(d.get("video", 0) - d.get("audio", 0)) <= 1 / 30 + 1e-3)
    print(json.dumps(rel, ensure_ascii=False, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(rel, ensure_ascii=False, indent=1))
    return 0 if rel["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
