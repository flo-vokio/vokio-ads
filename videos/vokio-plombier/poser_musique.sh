#!/bin/bash
# Remplace l'emplacement musique par le vrai fichier de Florian.
#
#   ./poser_musique.sh ~/ma-musique.wav
#
# La piste est calibrée pour passer SOUS la voix : normalisée à -26 LUFS,
# entrée en fondu d'une seconde, sortie sur les deux dernières. Rien d'autre
# n'est touché ; il n'y a pas à retoucher index.html.
set -e
cd "$(dirname "$0")"
[ -f "$1" ] || { echo "usage : ./poser_musique.sh <fichier audio>"; exit 1; }
ffmpeg -y -v error -i "$1" \
  -af "atrim=0:30,loudnorm=I=-26:TP=-3:LRA=11,afade=t=in:st=0:d=1,afade=t=out:st=28:d=2" \
  -ar 44100 -ac 2 -c:a libmp3lame -b:a 192k assets/musique.mp3
echo "posé : $(ffprobe -v error -show_entries format=duration -of csv=p=0 assets/musique.mp3) s"
echo "relancer ./monter.sh --rendre"
