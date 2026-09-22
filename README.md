# vokio-ads

Pubs Vokio en motion design, rendues par [HyperFrames](https://hyperframes.heygen.com)
(composition HTML seekable -> MP4). Une composition, plusieurs métiers, trois formats.

## Lancer une commande

Toujours par l'enveloppe, jamais `npx hyperframes` directement :

```bash
/opt/vokio-ads/bin/hf <commande>
```

Le VPS tourne sous Node 20 pour le reste de la machine et HyperFrames exige Node 22.
L'enveloppe met `/opt/node22` en tête de PATH pour elle seule et pointe
`HYPERFRAMES_PYTHON` vers le venv qui porte Kokoro. `/usr/bin/node` ne bouge pas.

## Le projet

`videos/vokio-promo/` : la pub de référence, 30 s, verticale 1080x1920.

## Chaîne son

Voix off provisoire locale, puis calage des sous-titres sur l'audio réel :

```bash
bin/hf tts videos/vokio-promo/SCRIPT.txt --voice ff_siwis --output videos/vokio-promo/assets/voix.wav
bin/hf transcribe videos/vokio-promo/assets/voix.wav --model small --language fr
```

`--language fr` n'est pas optionnel : sans lui le modèle par défaut (`small.en`)
traduit silencieusement le français en anglais.

La musique n'est pas générée ici : la piste est un emplacement vide que Florian
remplit lui-même.
