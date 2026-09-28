#!/usr/bin/env python3
"""Rend un projet HyperFrames en MP4, même quand le disque est presque plein : usage en une ligne :

    python3 outils/rendre.py <racine> -o film.mp4 [--son mix.wav | --son-du-projet] [--crf 0] [--tmp auto|shm|disque] [--si-absent]

  <racine> : un projet rendable (ce projet = le 9:16, formats/16x9, une copie de outils/format.py --dossier).
  1. hf render <racine> sous flock /tmp/hf-rendu.lock (un rendu à la fois sur le VPS). HyperFrames refuse de rendre sous
     1 Gio libre, contrôlé À LA FOIS dans le dossier temporaire (os.tmpdir) et dans le dossier du fichier de sortie :
     --tmp auto (défaut) fait tout le rendu dans /dev/shm (mémoire, TMPDIR et sortie) quand le disque a moins de 1,2 Gio
     libres, puis déplace le MP4 à sa place (≈ 4 Mo ; ≈ 150 Mo en --crf 0) ; --tmp shm l'impose, --tmp disque l'interdit.
     Le dossier de travail est toujours effacé, même en cas d'échec.
  2. --son W.wav : remplace la piste audio, encodée comme les livraisons (flux vidéo COPIÉ, AAC 256k 48 kHz stéréo,
     +faststart) ; --son-du-projet : W = la piste <audio> de <racine>/index.html (la bande son du projet). Sans --son : la
     piste rendue par HyperFrames (AAC ~190k).
  3. imprime le relevé ffprobe (images, taille, i/s, durée, audio) ; code 1 si le rendu échoue.
  Idempotent (la sortie est réécrite ; --si-absent : rien à faire si elle existe déjà). N'écrit rien dans <racine>.
  En module : from rendre import rendre ; rendre(racine, sortie, crf=0) (utilisé par outils/identite.py empreindre).
Exemples :
    python3 outils/rendre.py formats/16x9 -o /root/vokio-uploads/videos/showcase/le-point-sur-le-i-16x9-image.mp4 --son-du-projet
    python3 outils/rendre.py /tmp/copie-9x16 -o /tmp/9x16.mp4 --son-du-projet
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HF = "/opt/vokio-ads/bin/hf"
VERROU = "/tmp/hf-rendu.lock"
SHM = Path("/dev/shm")
SEUIL = int(1.2 * 1024 ** 3)          # sous ce seuil de disque libre, le rendu passe en mémoire (HyperFrames exige 1 Gio)


def libre(p):
    p = Path(p)
    while not p.exists():
        p = p.parent
    return shutil.disk_usage(p).free


def dossier_travail(sortie, mode="auto"):
    """Dossier temporaire du rendu : sur /dev/shm si le disque manque (ou --tmp shm), sinon dans le temporaire du système."""
    en_memoire = mode == "shm" or (mode == "auto" and min(libre(tempfile.gettempdir()), libre(Path(sortie).parent)) < SEUIL)
    if en_memoire and libre(SHM) < 2 * 1024 ** 3:
        raise SystemExit(f"rendre.py : ni le disque ni /dev/shm n'ont assez de place ({libre(SHM) / 1e9:.1f} Go libres en mémoire)")
    return Path(tempfile.mkdtemp(prefix="hf-rendu-", dir=str(SHM) if en_memoire else None)), en_memoire


def piste_du_projet(racine):
    m = re.search(r'<audio[^>]*\ssrc="([^"]+)"', (Path(racine) / "index.html").read_text())
    if not m:
        raise SystemExit(f"rendre.py : pas de <audio src=…> dans {racine}/index.html")
    return Path(racine) / m.group(1)


def sonder(film):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(film)],
                       capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = [s for s in j["streams"] if s["codec_type"] == "audio"]
    return {"video": f'{v["codec_name"]} {v["width"]}×{v["height"]} {v["r_frame_rate"]} {v.get("nb_read_frames")} images '
                     f'{float(v["duration"]):.3f} s {v.get("pix_fmt")}',
            "audio": [f'{s["codec_name"]} {s["sample_rate"]} Hz {s["channels"]} canaux {float(s["duration"]):.3f} s '
                      f'{int(s.get("bit_rate", 0)) // 1000} kb/s' for s in a],
            "octets": int(j["format"]["size"])}


def rendre(racine, sortie, crf=None, son=None, tmp="auto", bavard=True):
    """Rend <racine> vers <sortie> (sous flock) ; son : chemin d'un .wav à muxer à la place de la piste rendue."""
    racine, sortie = Path(racine).resolve(), Path(sortie).resolve()
    sortie.parent.mkdir(parents=True, exist_ok=True)
    trav, en_memoire = dossier_travail(sortie, tmp)
    try:
        brut = trav / "rendu.mp4"
        env = dict(os.environ, TMPDIR=str(trav))
        cmd = ["flock", VERROU, HF, "render", str(racine), "-o", str(brut), "--quiet"] + (["--crf", str(crf)] if crf is not None else [])
        if bavard:
            print("→ " + " ".join(cmd) + (f"   (TMPDIR={trav}, en mémoire : disque plein)" if en_memoire else ""), flush=True)
        r = subprocess.run(cmd, env=env)
        if r.returncode or not brut.exists():
            raise SystemExit(f"rendre.py : hf render a échoué (code {r.returncode})")
        final = brut
        if son:
            final = trav / "final.mp4"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(brut), "-i", str(son), "-map", "0:v:0", "-map", "1:a:0",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                            str(final)], check=True)
        taille = final.stat().st_size
        if libre(sortie.parent) < taille + 50 * 1024 ** 2:
            raise SystemExit(f"rendre.py : pas la place d'écrire {taille / 1e6:.0f} Mo dans {sortie.parent}")
        tmp_sortie = sortie.with_name("." + sortie.name + ".partiel")
        shutil.copyfile(final, tmp_sortie)
        os.replace(tmp_sortie, sortie)
    finally:
        shutil.rmtree(trav, ignore_errors=True)
    return sortie


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("racine")
    A.add_argument("-o", "--sortie", required=True)
    A.add_argument("--son", help="piste .wav à muxer (AAC 256k 48 kHz, vidéo copiée)")
    A.add_argument("--son-du-projet", action="store_true", help="muxer la piste <audio> de index.html de la racine")
    A.add_argument("--crf", type=int)
    A.add_argument("--tmp", choices=["auto", "shm", "disque"], default="auto")
    A.add_argument("--si-absent", action="store_true")
    a = A.parse_args()
    if a.si_absent and Path(a.sortie).exists():
        print(f"{a.sortie} existe déjà : rien à faire (--si-absent)")
        return 0
    son = Path(a.son) if a.son else (piste_du_projet(a.racine) if a.son_du_projet else None)
    s = rendre(a.racine, a.sortie, crf=a.crf, son=son, tmp=a.tmp)
    print(json.dumps({"sortie": str(s), "son": str(son) if son else "piste rendue par HyperFrames"} | sonder(s), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
