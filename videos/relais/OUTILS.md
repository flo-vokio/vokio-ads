# Vidéos des cartes « Le relais » : mode d'emploi court

Tout se lance depuis `/opt/vokio-ads/videos/relais`. Une carte = un dossier = UNE recette JSON.

| Besoin | Commande |
|---|---|
| Tout refaire pour une carte (données, son, rendu, encodage, contrôles, planches) | `python3 outils/relais.py <carte>/recette.json` |
| Une étape seulement | `python3 outils/relais.py <carte>/recette.json construire` (ou `son`, `rendre`, `encoder`, `controles`, `planche`, `purger`) |
| Une seule des deux vidéos | `… --seulement boucle` (ou `complete`) ; WebM AV1 (abandonné) : `… encoder --av1` |
| Regarder sans rendre (instants, nombre d'éléments, corps) | `/root/.pwtest/bin/python3 outils/apercu.py <carte>/boucle -o /dev/shm/a.png --pas 0.5` |
| Brouillon de recette d'une page métier (carte de l'appel réel + dit Scribe, écrit la recette si absente) | `python3 outils/brouillon.py <metier> --ecrire` |
| Planche du geste, image par image (depuis la boucle livrée) | `python3 outils/planche_geste.py <carte>/recette.json --de 0.1 --a 1.4 --pas 2 --cadre x,y,l,h` |
| Fiche de passation d'un lot (durée exacte, data-duree, transcription corrigée, écarts avec la page) | `python3 outils/lot.py LOT-A.json <metier> …` |
| Mots horodatés d'un appel (Scribe, en cache) | `python3 outils/scribe.py <audio.mp3> <carte>/cache/scribe.json` |
| Maquette d'intégration (copie de l'accueil, le site n'est jamais touché) + blocs à reporter (`maquette/blocs-relais-video.html`) | `python3 outils/maquette.py restaurant/recette.json coiffure/recette.json auto-ecole/recette.json` |
| Captures et essais de la maquette (320, 390, 768, 1440, mouvement réduit) | `/root/.pwtest/bin/python3 outils/captures_maquette.py` |

- **Recette** : `coiffure/recette.json` est le modèle (voir sa `_note`). Énoncés = texte DIT ; ancres `E<n>:mot`
  (`#2` deuxième occurrence, `fin`, `debut`, `@3`, `+0.3`). Objets : `agenda` (heures, bloc), `sms`, `fiche` (appel sans
  rendez-vous), `situation` = un fichier de `gabarit/situations/` (`ciseaux`, `poele`, `ferme`).
- **Gabarit** : `gabarit/index.html` (un seul timeline GSAP, fonction pure du temps). `<carte>/boucle/` et
  `<carte>/complete/` sont GÉNÉRÉS : ne jamais les éditer.
- **Effets réutilisables** (`gabarit/lib/fx.js`, chargé par toutes les cartes) : `FX.flamme` (tracé déformé par ondes montantes, torsion de la pointe, cœur clair, flammèche qui se détache), `FX.traits` (2-3 traits de vitesse sur quelques images), `FX.etirer` (smear le long de la vitesse), `FX.fenetre`. Réglages par défaut dans `FX.DEFAUTS`, surchargés par situation (objet `REGLAGES` en tête de `situations/<nom>.js`). Périodes : diviseurs de 10 s.
- **Temps du geste** : `FX.tau(t, mode)` ; dans la boucle, t ≥ 5 s devient t − 10 : la fin de la boucle montre l'AVANT du geste (ambiance périodique), qui rejoint l'image 0 sans saut ; le geste lui-même tient entre τ = 0,1 et 1,3 s (visible dans la boucle ET dans la complète, dont la situation dure 1,3 s).
- **Posters** : `poster_boucle` (instant de la boucle : l'illustration au moment parlant, contrôlée sans texte hors illustration), `poster_complete` (défaut 0 : la première image).
- **Situation animée** : un `gabarit/situations/<nom>.js` à côté du SVG définit `window.SITUATION_ANIM(t, periode, mode)` (fonction pure du temps, périodique) ; modèle : `poele.js` (anticipation, arcs, rotation, étirement et écrasement, flammes). `data-periode` sur `#objet`, un `style` inline peut recadrer l'objet.
- **Nouvelle situation** : un SVG `viewBox 0 0 600 600`, `id="objet"`, les pièces qui bougent portent
  `data-rot="angle_min angle_max"` et `data-pivot="x y"` (mouvement périodique : la boucle se raccorde seule).
- **SMS** : iPhone réaliste (Messages iOS du showcase), 1 pt = 3,06 px (SMS 52 px), en gros plan ; recette `sms` : `texte`, `souligne`, `heure` ; mode complète : `entree`, `bulle`, `sortie` (ancres) ; les répliques dites pendant l'iPhone ne sont pas sous-titrées (rapportées).
- **Son** : le vrai appel reçoit un GAIN seul (−16 LUFS), la signature courte se pose quand le point se pose sur le ı.
- **Livrables** : `/root/vokio-uploads/videos/relais/` ; rendus de travail dans `/dev/shm/relais-<id>/` (`purger`).
- Jamais `hf skills update` ni `audio.mjs sync-durations`. Rendu sous flock (outil `rendre.py` du showcase).
