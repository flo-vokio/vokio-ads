# vokio-ads

Pubs Vokio en motion design, rendues par [HyperFrames](https://hyperframes.heygen.com) :
une composition HTML dont la timeline se déplace image par image, encodée en MP4.

## La règle d'or

Toute commande passe par l'enveloppe, jamais `npx hyperframes` en direct :

```bash
/opt/vokio-ads/bin/hf <commande>
```

La machine tourne sous Node 20 pour le reste de ses services et HyperFrames
exige Node 22. L'enveloppe met `/opt/node22` en tête de PATH pour elle seule et
pointe `HYPERFRAMES_PYTHON` vers le venv qui porte Kokoro. `/usr/bin/node` ne
bouge pas.

## Le film de référence

`videos/vokio-promo/` : 30,0 s, 1080x1920, métier plombier.

| Fichier | Rôle |
| --- | --- |
| `BRIEF.md` | l'intention, et toutes les règles éditoriales qui ne se négocient pas |
| `SCRIPT.md` | la narration verrouillée, une section par ligne parlée |
| `STORYBOARD.md` | les six plans, leurs durées, et la séquence chronométrée de chacun |
| `frame.md` | le système visuel : couleurs, rampe typographique, composants |
| `references/agenda-reel.md` | les mesures relevées sur le vrai agenda client |
| `compositions/frames/` | un fichier HTML par plan |
| `index.html` | le montage, écrit par l'assembleur, jamais à la main |

## Refaire le film

```bash
cd videos/vokio-promo
./monter.sh            # sous-titres, assemblage, transitions, contrôle
./monter.sh --rendre   # et le MP4
```

## La musique

`assets/musique.mp3` est un silence de 30 s : la piste existe et se valide déjà.
Pour poser un vrai morceau :

```bash
cd videos/vokio-promo
./poser_musique.sh ~/mon-morceau.wav
./monter.sh --rendre
```

Le script le normalise à -26 LUFS avec fondus, pour qu'il passe **sous** la voix.

## La voix off

Provisoirement locale (Kokoro, voix `ff_siwis`), à remplacer par ElevenLabs.
Le montage ne contient **aucune durée écrite en dur** : il se recale sur les
horodatages du nouveau fichier.

```bash
cd videos/vokio-promo
node /opt/vokio-ads/.agents/skills/product-launch-video/scripts/audio.mjs \
  --script ./SCRIPT.md --storyboard ./STORYBOARD.md --hyperframes . \
  --out ./audio_meta.json --provider kokoro --voice ff_siwis
python3 /opt/vokio-ads/outils/recaler_mots.py . --ecrire
./monter.sh --rendre
```

La deuxième commande n'est pas optionnelle : Whisper entend « Vocuez au » pour
« Vokio » et perd la ponctuation, qui commande le découpage des sous-titres.
`recaler_mots.py` garde ses minutages et lui impose les mots de `SCRIPT.md`.

## Trois pièges déjà payés

1. **Ne jamais lancer `audio.mjs sync-durations` sur ce projet.** Il écrase la
   durée d'un plan par celle de sa voix. Ici il ramènerait le film de 30,0 s à
   18,8 s et supprimerait tous les silences, qui sont la moitié du montage.
2. **La langue doit descendre jusqu'au moteur.** Sans elle il retombe sur
   l'anglais, donc sur le modèle Whisper `small.en`, qui *traduit* au lieu de
   transcrire. Corrigé dans les skills vendues, mais c'est le premier endroit
   où regarder si une transcription revient en anglais.
3. **La bande de sous-titres par défaut est dans la zone interdite** (y 1600 à
   1920) : Reels et TikTok y dessinent leur interface, et la charte Vokio
   interdit tout texte important sous y=1500. `monter.sh` la remonte via
   `HF_CAPTION_BAND_TOP` et `HF_CAPTION_BAND_HEIGHT`.

## Décliner par métier

En préparation. Le storyboard porte déjà un champ `metier:`, et les chaînes
propres au métier sont isolées dans `SCRIPT.md` et dans les plans 03 à 05.
