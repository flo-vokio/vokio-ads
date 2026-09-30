# Vidéos des trois cartes « Le relais » (section #relais de vokio.fr) · 29/09, soir

Tout est préparé, rien n'est en production : ni commit, ni push. `/opt/vokio-site-repo` et `/opt/vokio-site` n'ont pas
été touchés (`git status` vide).

## Retours de Florian appliqués
1. **SMS en iPhone réaliste, dans Messages iOS**, repris du showcase : titane, boutons, Dynamic Island, barre d'état, en-tête
   iOS 26 (retour, avatar, « Vokio »), mention « SMS · Aujourd'hui 15:13 » en 11 pt (validée), bulle reçue avec sa queue et la
   date soulignée. L'échelle est de 1 pt = 3,06 px, pour que le SMS (17 pt) fasse **52 px** dans le 1080. À cette échelle,
   le téléphone est plus large que le cadre : on le voit **en gros plan**, bord gauche et boutons visibles, côté droit coupé.
   Même chose pour la coiffure et le restaurant (l'auto-école n'a pas de SMS).
   - Conséquence : quand l'iPhone occupe le cadre, la réplique dite à ce moment n'est pas sous-titrée. C'est « Super, merci. »
     (coiffure) et « Merci, au revoir. » (restaurant). L'outil le signale dans `controles.json` (`non_sous_titre`).
2. **AV1 abandonné** : H.264 seul, l'outil ne produit plus de WebM (sauf avec `--av1`).
3. **« Auto-école du Centre »** est écrit tel quel (Scribe entend « Stand »).
4. **Les transcriptions `<details>` de la maquette sont refaites sur le texte dit**, pour les trois appels :
   - coiffure : « Euh… disponibilités », « Parfait. » deux fois ;
   - restaurant : sans les « Un instant. » ni « Je vérifie les disponibilités. », absents de l'audio ;
   - auto-école : « du Centre ».

## Fichiers finaux (`/root/vokio-uploads/videos/relais/`)

| Carte | Boucle (muette, 10,00 s) | Complète (avec le son) | Posters 720×720 webp / jpg |
|---|---|---|---|
| Coiffure « Les mains prises » | `relais-coiffure-boucle.mp4` 401 Ko | `relais-coiffure-complete.mp4` 56,87 s · 1 870 Ko | boucle 12 / 25 Ko · complète 9 / 19 Ko |
| Restaurant « En plein service » | `relais-restaurant-boucle.mp4` 311 Ko | `relais-restaurant-complete.mp4` 43,93 s · 1 363 Ko | 12 / 26 Ko · 15 / 31 Ko |
| Auto-école « Après la fermeture » | `relais-auto-ecole-boucle.mp4` 469 Ko | `relais-auto-ecole-complete.mp4` 55,97 s · 1 880 Ko | 16 / 33 Ko · 20 / 37 Ko |

Caractéristiques communes :
- vidéo : H.264 High, yuv420p, 1080×1080, 30 i/s, +faststart ; boucles sans piste audio ;
- son des complètes : AAC 48 kHz, −16,1 / −16,2 / −16,1 LUFS, crête ≤ −4,0 dBTP ;
- le vrai appel ne reçoit qu'un gain (+0,4 à +0,5 dB) ; la signature courte v2 tombe quand le point se pose sur le ı.

## Contrôles (`<carte>/controles.json`)
- **Résultat** : 0 échec (coiffure 31 contrôles, restaurant 31, auto-école 29).
- **Relevé tous les 1/4 s** : ≤ 3 éléments, corps ≥ 52 px (seule dérogation : l'horodatage iOS de 11 pt, validé), marges,
  aucun « — », aucun numéro, jamais « Alauzet ».
- **Texte montré** : sous-suite du dit.
- **Fichiers** : codec, faststart, poids, durée, sonie, synchro.
- **Raccord des boucles** : écart de 0,20 à 0,22 entre la dernière et la première image, contre 0,28 à 0,44 pour deux images
  voisines.

## Critique chiffrée (≥ 8 partout)

| Carte | Lisibilité à 375 px sans le son (boucle) | Justesse et rythme (complète) |
|---|---|---|
| Coiffure | 8 | 8,5 |
| Restaurant | 8 | 8,5 |
| Auto-école | 8 | 8 |

- **Coiffure.** Le SMS devient une vraie preuve : Messages iOS en gros plan, texte en 52 px. La complète gagne en justesse.
  Elle reste à 8,5 et non 9 parce que « Super, merci. » n'est pas sous-titré sous l'iPhone.
- **Restaurant.**
  - Boucle : la poêle qui saute se lit comme une cuisine en service. « Ce serait pour six personnes. » puis
    « D'accord, c'est disponible. », puis le bloc « 20:00 Florian · Table pour 6 ».
  - Complète : elle ressemble à la coiffure, avec la même fin iPhone et « Merci, au revoir. » non sous-titré.
- **Auto-école.** Le résultat est une fiche d'appel et non un rendez-vous : moins spectaculaire, mais fidèle à l'appel (il
  rappellera). La carte se déplie avec sa première ligne ; le point attend à gauche de la fiche.
  - Défaut restant : au passage à « Pas de problème… » (48 s), le point traverse le titre « Appel de 19 h 18 » en 0,2 s.
- Planches contact : `<carte>/planche-boucle.png` et `<carte>/planche-complete.png`.

## Maquette (`maquette/index.html`) et captures (`maquette/captures/`)
- Trois cartes vidéo. La boucle ne part que si la carte est visible à 50 % au moins, et une seule à la fois : la plus visible.
  Sur bureau, les trois sont également visibles, c'est donc la première (restaurant) qui joue ; les deux autres montrent leur
  poster.
- `preload="none"` + poster, `playsinline`, et poster fixe avec `prefers-reduced-motion`.
- Au toucher, la complète part avec le son, et le lecteur de la carte devient son contrôle (lecture/pause, barre, 0:44 / 0:57
  / 0:56). Lancer un autre appel coupe le précédent, audio compris.
- Captures à 320, 390, 768 et 1440, plus lecture et mouvement réduit : aucun débord de page ni de carte, tous les essais sont
  OK (`captures/rapport.json`).

## Intégration : `maquette/blocs-relais-video.html`
Le fichier donne, prêts à coller et balisés `RELAIS-VIDEO` :
1. le CSS ;
2. les trois figures et les durées des lecteurs (`data-video`, temps affiché) ;
3. les transcriptions corrigées ;
4. les trois lignes à changer dans le script du lecteur audio existant ;
5. le JS ;
6. les fichiers à copier dans `/assets/relais/` : `relais-<carte>-{boucle,complete}.mp4` et
   `-{boucle,complete}-poster.webp` (les .jpg sont des posters de secours).

Après le report : `check_responsive.py`, puis `deployer.py` sur le go de Florian.

## Refaire une carte
`python3 outils/relais.py <carte>/recette.json`, puis
`python3 outils/maquette.py restaurant/recette.json coiffure/recette.json auto-ecole/recette.json` et
`/root/.pwtest/bin/python3 outils/captures_maquette.py`. Mode d'emploi : `OUTILS.md`.

## Retouche du 29/09 (soir) : la poêle du restaurant
- Le cuisinier fait sauter (`gabarit/situations/poele.svg` + `poele.js`, fonction pure du temps, période 1,25 s, 8 gestes
  par boucle de 10 s) :
  - anticipation (la poêle recule, pointe basse), coup sec vers l'avant et vers le haut (power2.out), retour avec un léger
    dépassement ;
  - trois aliments décalés (départs à 25 ms, arrivées à 44 ms d'écart), arcs balistiques avec recul vers la main, un tour
    sur eux-mêmes ;
  - étirement au départ et à l'arrivée, écrasement à l'atterrissage (base fixe), tassement juste avant le décollage ;
  - la poêle encaisse la réception ;
  - trois flammes solaires sur trois rythmes (0,5 / 0,3125 / 0,625 s), ravivées quand la poêle s'écarte du feu.
- Complète : l'avance passe de 0,8 à 1,3 s, pour que le geste entier soit vu avant « Bonjour » (44,43 s au lieu de 43,93).
- Planche image par image du geste : `restaurant/planche-geste.png`. Boucle 454 Ko, raccord 0,10 (médiane des voisines 0,29).
- Critique, lentille « animateur senior » : 8,5/10. Plus : les douze principes lisibles (anticipation, arcs, overlap,
  squash and stretch, follow-through). Moins : pas de traînée sur le coup, le manche sort du cadre à gauche (la main est hors
  champ, voulu), les flammes gardent une forme fixe (ondulation par échelle et inclinaison seulement).

## Deuxième retouche de la poêle : traînées et flammes vivantes
- Traits de vitesse (au trait, noir) : trois traits derrière le cul de la poêle pendant le coup sec (images 12-14 de la boucle),
  deux traits derrière chaque aliment à son décollage (4 images), qui poussent puis se rétractent vers l'avant.
- Smear au décollage : chaque aliment est étiré le long de sa vitesse (+95 % à la première image, retour en 0,1 s), puis
  étiré en proportion de sa vitesse (au plus +28 %), volume conservé ; aucun flou.
- Flammes : le tracé lui-même se déforme (ondes qui montent le long des flancs, pointe qui se tord, hauteur qui respire, cœur
  en léger retard) ; une flammèche se détache de chaque pointe toutes les 2,5 s (décalées), monte et s'éteint ; la pointe se
  rétracte en la lâchant. Périodes 0,3125 à 2,5 s : boucle parfaite (raccord 0,09).
- Réglages réutilisables : `gabarit/lib/fx.js` (FX.flamme, FX.traits, FX.etirer), objet `REGLAGES` de `situations/poele.js`.
- Complète : 44,433333 s exactement (1 333 images à 30 i/s). Boucle 471 Ko, complète 1 404 Ko.
- Critique « animateur senior » : 9/10 (voir la passation).

## Lot A · pages métier (29-30/09)
Onze cartes : plombier, serrurier, électricien, chauffagiste, garage, rénovation, vétérinaire, toiletteur, boulangerie
(nouvelles), coiffure et auto-école (reprises au niveau de la poêle).
- Recettes : `<metier>/recette.json` ; situations : `gabarit/situations/{cle,porte,disjoncteur,chaudiere,roue,marteau,chat,chien,
  rouleau,ciseaux-meches,pancarte}.{svg,js}`. Effets communs ajoutés à `gabarit/lib/fx.js` : `FX.tau`, `FX.cles`, `FX.EASE`,
  `FX.particules` (gouttes, poussière, étincelles), `FX.eclat`, `FX.chute`, `FX.pendule` (rétrocompatible).
- Outils : `outils/brouillon.py` (carte de la page + dit Scribe → brouillon de recette), `outils/planche_geste.py`,
  `outils/lot.py` (→ `LOT-A.json` : durée exacte, data-duree, transcription corrigée prête à coller, écarts avec la page).
- Posters de boucle : l'illustration au moment parlant du geste, contrôlée sans texte hors illustration (`poster_sans_texte`).
- Contrôles : 0 échec pour les onze. Toute réplique dite pendant l'iPhone n'est pas sous-titrée (liste dans LOT-A.json).
- Reprises après relecture des posters : plombier (sous l'évier : cuve, bonde, tuyau, goutte solaire), rénovation (marteau de
  charpentier canonique, clou qui ne traverse plus la planche), boulangerie (boule de pâte + rouleau + farine, nouvelle
  situation « rouleau »), toiletteur (ébrouement plus ample).
