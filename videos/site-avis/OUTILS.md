# Films de vokio.fr/avis/ (06/10/2026)

Deux animations carrées pour vokio.fr/avis/. **Sur le site, ce ne sont PAS des vidéos** (07/10/2026) : la composition elle-même est copiée dans `assets/avis/films/<film>/` et jouée EN DIRECT par sa timeline GSAP, dans un cadre mis à l'échelle. C'est le principe des animations de l'accueil. Un iPhone en économie d'énergie refusait la lecture automatique des MP4. Les MP4 restent utiles pour les réseaux sociaux.

**Mise à jour sur le site :** copier `<film>/index.html`, `lib/` et `fonts/` dans un NOUVEAU dossier (`films/<film>-v2/`, cache de 30 jours sur /assets/), avec `<meta name="robots" content="noindex">`, puis changer le `src` de l'iframe dans avis/index.html. Le pilote de la page lit `window.__pub.pret` et `window.__timelines[id]`, et prend les chapitres du film d'étapes à 0, 4 et 8 s.

Les films :

| Film | Ce qu'il montre | Durée |
|---|---|---|
| `sms` | l'iPhone des pubs : le SMS arrive, toucher sur le lien, feuille d'avis, 5 étoiles, « Merci, votre avis est publié » | 7 s |
| `etapes` | « Comment ça marche » en 3 chapitres de 4 s : la saisie, 12:30 → 14:30, le SMS et les étoiles | 12 s |

Les chapitres du film `etapes` sont calés sur les 3 cartes de la page (0, 4, 8 s, voir `window.__avis`). La page allume la carte du chapitre en cours ; un clic sur une carte ramène le film à son chapitre.

| Besoin | Commande (depuis ce dossier) |
|---|---|
| Modifier un film | éditer `gabarits/<film>.src.html` (jamais `<film>/index.html`), puis `python3 construire.py` |
| Regarder sans rendre | `/root/.pwtest/bin/python3 apercu.py sms --instants 0,2,3.9` (planche dans /dev/shm, plus les erreurs internes) |
| Vérifier | `/opt/vokio-ads/bin/hf lint sms` · `/opt/vokio-ads/bin/hf snapshot sms --at 3.9 --no-end -o /dev/shm/s` |
| Rendre | `cd ../showcase-iphone && python3 outils/rendre.py ../site-avis/sms -o /root/vokio-uploads/videos/site-avis/avis-sms-brut.mp4` |
| Version web | `ffmpeg -i …-brut.mp4 -vf "scale=960:960:flags=lanczos,format=yuv420p" -c:v libx264 -preset slow -crf 26 -an -movflags +faststart avis-sms-vN.mp4`, plus une affiche en webp ; sur le site, sous `assets/avis/` avec un NOUVEAU suffixe `-vN` (cache de 30 jours) |

**L'iPhone** est repris tel quel de `../pub-secretaire/gabarit.html`, qui reste la source unique, par la même extraction que `../pub-metiers/construire.py`.

**Pièges payés le 06/10 :**
1. **Ne pas ranger un gabarit dans le dossier rendu.** HyperFrames prend pour une entrée tout `.html` qui porte `data-composition-id` (lint `multiple_root_compositions`). Les gabarits vivent dans `gabarits/`.
2. **Ne pas tuer une animation après l'avoir créée.** Supprimer l'entrée et la sortie du téléphone avec `tl.getChildren(…).kill()` donnait un aperçu Chromium juste, mais un MP4 entièrement VIDE. On ne les crée pas du tout : `ft` filtre `#sms` le temps d'injecter la pièce.
3. **Les états discrets** (texte tapé, bouton) passent par UN pilote, fonction pure du temps, juste quel que soit le sens du seek. Pas de paires de `tl.call`.
4. **Les contrôles intégrés mesurent dans le DOM** : « Publier » doit rester hors du fondu bas, et la feuille ne doit pas couvrir la bulle. Les estimations à la main étaient fausses de quelques pixels.
