#!/bin/bash
# Assemble le film à partir des plans déjà construits, puis contrôle.
# Rejouable : chaque étape réécrit sa sortie.
#
#   ./monter.sh            assemble et contrôle
#   ./monter.sh --rendre   assemble, contrôle, puis rend le MP4
set -e
cd "$(dirname "$0")"
S=/opt/vokio-ads/.agents/skills/product-launch-video/scripts

export PATH=/opt/node22/bin:$PATH
export HYPERFRAMES_PYTHON=/root/.venvs/hyperframes/bin/python
# La bande par défaut tombe entre y=1600 et y=1920 : c'est là que Reels et
# TikTok posent leur interface, et la charte Vokio interdit tout texte
# important sous y=1500. On la remonte.
export HF_CAPTION_BAND_TOP=1310
export HF_CAPTION_BAND_HEIGHT=190
# Un groupe par plan plutôt qu'un par bout de phrase : le sous-titre reste
# 4 à 5 s au lieu d'une demi-seconde, et le surlignage suit toujours la voix.
export HF_CAPTION_GROUP=frame

hf(){ npx --yes hyperframes@0.8.62 "$@"; }

# Les ouvriers de plan déposent des fichiers de sonde à la racine pendant qu'ils
# travaillent. Un second fichier racine portant data-composition-id est une
# ERREUR de lint, et une erreur de lint désactive les audits de mise en page et
# de contraste : le rapport devient vert sans que rien n'ait tourné.
rm -f _*.html _*.js

echo "· sous-titres"
node $S/captions.mjs build --storyboard ./STORYBOARD.md --audio-meta ./audio_meta.json \
     --hyperframes . --out ./caption_groups.json

echo "· emplacement musique"
python3 /opt/vokio-ads/outils/piste_musique.py .

echo "· assemblage"
node $S/assemble-index.mjs --storyboard ./STORYBOARD.md --hyperframes .

echo "· transitions"
node $S/transitions.mjs inject --storyboard ./STORYBOARD.md --hyperframes .
node $S/transitions.mjs verify --storyboard ./STORYBOARD.md --index ./index.html

echo "· contrôle"
hf check

if [ "$1" = "--rendre" ]; then
  echo "· rendu"
  hf render --skill=product-launch-video --quality looks --output renders/vokio-plombier-9x16.mp4
  ffprobe -v error -show_entries format=duration,size -of default=nw=1 renders/vokio-plombier-9x16.mp4
fi
