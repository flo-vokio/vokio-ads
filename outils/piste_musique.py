#!/usr/bin/env python3
"""Déclare l'emplacement musique dans audio_meta.json.

Le storyboard porte `music: none`, ce qui est juste : on ne veut pas que le
moteur aille chercher un morceau dans un catalogue, Florian fournit le sien.
Mais du coup l'assembleur n'écrit aucune piste 11, et il n'y aurait nulle part
où déposer le fichier.

Ce script ajoute la piste dans audio_meta.json, d'où l'assembleur la reprend
naturellement. Il est à relancer après chaque régénération de la voix, qui
réécrit ce fichier : monter.sh s'en charge.

    piste_musique.py <projet> [--volume 0.18]
"""
import argparse
import json
import subprocess
from pathlib import Path

a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
a.add_argument("projet")
a.add_argument("--fichier", default="assets/musique.mp3")
a.add_argument("--volume", type=float, default=0.18)
a = a.parse_args()

projet = Path(a.projet)
piste = projet / a.fichier
if not piste.is_file():
    raise SystemExit(f"{piste} absent : créer l'emplacement avant (voir poser_musique.sh)")

duree = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(piste)],
    capture_output=True, text=True, check=True).stdout.strip())

f = projet / "audio_meta.json"
meta = json.loads(f.read_text())
meta["bgm"] = {"path": a.fichier, "volume": a.volume, "query": None, "duration_s": round(duree, 3)}
meta["bgm_pending"] = False
f.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
print(f"piste musique déclarée : {a.fichier} · {duree:.2f} s · volume {a.volume}")
