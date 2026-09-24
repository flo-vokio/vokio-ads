#!/bin/bash
# Rend un ou plusieurs métiers : ./rendre.sh plombier veterinaire ...
# Chaque rendu passe par le verrou commun (4 cœurs partagés entre agents).
set -e
cd "$(dirname "$0")"
declare -A NOM=([plombier]=une-nuit-chez-vokio [veterinaire]=une-nuit-a-la-clinique
                [restaurant]=un-service-chez-vokio [institut_beaute]=une-fin-de-journee-a-l-institut)
SORTIE=/root/vokio-uploads/videos/ux-retravail
mkdir -p "$SORTIE" renders
for m in "$@"; do
  n=${NOM[$m]}
  flock /tmp/hf-rendu.lock /opt/vokio-ads/bin/hf render . --variables-file "profils/$m.json" \
      --strict-variables --fps 30 -o "renders/$m.mp4" --quiet > "renders/$m.log" 2>&1
  cp "renders/$m.mp4" "$SORTIE/$n-hyperframes.mp4"
  # couverture : même instant que l'original (livrer_film.py, INSTANT = 8.2)
  ffmpeg -loglevel error -y -ss 8.2 -i "$SORTIE/$n-hyperframes.mp4" -frames:v 1 "$SORTIE/$n-hyperframes-couverture.png"
  echo "$m → $SORTIE/$n-hyperframes.mp4"
done
