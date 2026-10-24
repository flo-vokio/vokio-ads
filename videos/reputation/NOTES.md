# Pubs Vokio Réputation (20/10/2026)

Deux films 9:16 de 31 s, muets, même recette que « 24 h chez Vokio » (Plein Jour, serif, vraies captures).

| Film | Dossier | Rendu |
|---|---|---|
| n° 1 « Vos clients contents ne laissent pas d'avis. » | `contents/` | `/root/vokio-uploads/videos/reputation/reputation-clients-contents-9x16.mp4` |
| n° 2 ciblage Planity « Vos clients réservent sur Planity. Les nouveaux vous cherchent sur Google. » | `planity/` | `/root/vokio-uploads/videos/reputation/reputation-planity-google-9x16.mp4` |

Drive : « Vokio · Réputation · pubs vidéo ».

## Refaire les captures
1. `python3 /root/vokio-deploy/pub-reputation-201026/espace.py --go` (espace de démo temporaire « Institut Camélia », offre Réputation Essentiel, 4 demandes passées SANS sms_events)
2. `/root/.pwtest/bin/python outils/filmer.py` (vraie app, session forgée 15 min, heure figée 21/10 10:42, envoi INTERCEPTÉ dans le navigateur : aucun SMS)
3. `python3 /root/vokio-deploy/pub-reputation-201026/espace.py --retour` TOUT DE SUITE (sinon les emails Réputation automatiques partent vers ce compte)
4. `python3 outils/preparer.py` (fabrique aussi `saisie-planche.png`, tous les états du formulaire en UNE image), puis copier `assets/captures/*-net.png`, `saisie-planche.png` et `assets/fonts` dans `contents/assets/` et `planity/assets/`

## Rendre
`flock /tmp/hf-rendu.lock /opt/vokio-ads/bin/hf render contents -o …` (idem `planity`), 1 min 30 chacun.

## Choix
- Numéro tapé : 06 39 98 41 78, tranche ARCEP réservée à la fiction.
- SMS : texte réel de `lib/avis.ts`, sauf « pour l'Institut Camélia » (demande de Florian ; l'app écrit « pour Institut Camélia »).
- Film n° 2 : fiches de comparaison fictives (DA, pas d'interface Google), aucune promesse d'intégration Planity (« sans changer de logiciel »).
- Doublage éventuel : les textes affichés servent de script ; recaler les images sur la voix comme pour 24 h.

## Contrôle obligatoire après rendu
`python3 outils/flashs.py <rendu>.mp4` : doit répondre « aucun ». Une image par état (img cachées puis montrées) donnait des images VIDES au rendu (retour Florian 21/10) ; doù
## Version Instagram avec musique (24/10/2026)
`outils/musique.py contents --prise 1` puis `--mixer` (idem `planity --prise 0`) : ElevenLabs Music, sections calées sur les plans, -14 LUFS visés, fondu final. Rendus `*-musique.mp4`. ⚠️ section >= 3 s exigée par l'API ; la prise 0 de contents s'éteignait à 26,5 s (4 s de silence sur le logo), d'où la prise 1 « final chord held until the very end ». Pas de voix vérifié par transcription (seul « [outro jingle] »). Crédits : 6 872 → 8 170. Couvertures = 1re image (accroche entière dans le recadrage 3:4 de la grille). Textes des posts : Google Doc du dossier Drive.

## 24/10 (suite) : retours de Florian
- Écran de fin aéré sur toute la hauteur (« ça fait groupé »).
- Mention « Établissement(s) fictif(s) » tout en bas (top 1840 ; masquée en partie par l'interface Reels, accepté).
- Micro-coupure musique vers 9-10 s (vidéo 1) : la prise 1 s'effondrait à -36 dB puis repartait d'un coup. Prise 2 (« seamless transitions ») + enveloppe de gain au mixage (`LISSAGES` : queue de note +12 dB, entrée du rythme -8 dB rendue à 0 dB à 10,15 s). Contrôle : `outils/musique.py --controle <wav>` (creux >= 0,25 s sous -28 dB suivi de +18 dB) ; il trouvait la coupure de la prise 1, rien sur le mix final.

## 24/10 (suite) : bruitages discrets
`outils/bruitages.py contents|planity` → `son/<film>-bruitages.wav`, ajouté sous la musique par `musique.py --mixer`. Touches du clavier, clic du bouton, glissement (ligne de Claire), notification synthétisée (fa-do aigus), 5 notes d'étoiles en fa majeur, tics du compteur (n° 2), scintillement du logo. Chaque bruitage calé sur le niveau de la musique à son instant (`ECARTS`). Synchro mesurée : attaques à 0-40 ms de l'image.
