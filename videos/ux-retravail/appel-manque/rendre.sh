#!/bin/bash
# Rend un ou plusieurs métiers : ./rendre.sh [metier ...] (sans argument : les huit).
# Un métier = metiers/<code>.json, une seule composition index.html.
set -euo pipefail
cd "$(dirname "$0")"
DEST=/root/vokio-uploads/videos/ux-retravail
mkdir -p "$DEST" renders
LISTE=("$@"); [ ${#LISTE[@]} -eq 0 ] && LISTE=($(ls metiers | sed 's/\.json$//'))
for m in "${LISTE[@]}"; do
  out="$DEST/appel-manque-$m-hyperframes.mp4"
  flock /tmp/hf-rendu.lock timeout 900 /opt/vokio-ads/bin/hf render . \
    --variables-file "metiers/$m.json" --strict-variables --fps 30 -o "$out" --quiet >"renders/$m.log" 2>&1
  # couverture : même instant que l'original (6,5 s : le chiffre posé, la ligne dessous lisible)
  ffmpeg -y -loglevel error -ss 6.5 -i "$out" -frames:v 1 "$DEST/appel-manque-$m-hyperframes-couverture.png"
  echo "$m $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out") s, pistes audio: $(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$out" | wc -l)"
done
rm -rf renders .hyperframes 2>/dev/null || true
