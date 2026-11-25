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

## 24/10 (suite) : accent du « À » qui dépassait
Avant leur entrée, les mots attendaient à yPercent 110 sous leur cache : l'accent du « À » (très haut sur la capitale) dépassait du cache, visible sous l'horloge. Départ passé à yPercent 160 partout (les deux films). Contrôle : aucun pixel sombre dans la zone des phrases 0,04 s avant chaque entrée.

## 24/10 (suite) : un seul son sur les étoiles
Retour Florian : « pas 5 sons, 1 son bien smooth qui monte, pas trop dans les aigus ». `montee()` : accord de fa majeur (fa4, la4, do5) qui glisse d'une quinte en 1,1 s, attaque lente, sommet à 1 s, queue 0,9 s ; fréquence dominante 390 → 520 Hz (les anciennes notes montaient à 1 400 Hz). Calé en niveau EFFICACE sur toute sa durée, 6 dB sous la musique (calé sur la crête au départ, il sortait 12 à 16 dB sous la musique : inaudible).

## 25/11/2026 : version 16:9 du film n° 1 (Capterra / GetApp / G2, lecteur YouTube)
`contents-16x9/` : RECOMPOSÉ pour le paysage (leçon du showcase : le 9:16 translaté valait 5,5/10). Même minutage à l'image près que `contents/`, seule la mise en page change : texte (horloge + phrase) en colonne gauche à x 150, objet (carte de l'app à l'échelle 0,8, bulle SMS, étoiles) en colonne droite à x 960, haut de carte aligné sur le haut de l'horloge (y 195) ; accroche sur deux lignes à 196 px ; fin en deux blocs (wordmark + « Réputation » à gauche sous le halo, promesse + prix + vokio.fr/avis à droite) ; mention en bas à 26 px.
Rendu : `flock /tmp/hf-rendu.lock bin/hf render videos/reputation/contents-16x9 --fps 30 -o /root/vokio-uploads/videos/reputation/reputation-clients-contents-16x9.mp4`, puis la bande son de la version Instagram COPIÉE telle quelle (même mix, -12,8 LUFS, crête -0,9 dBFS ; bruitages toujours synchrones puisque le minutage est identique) :
`ffmpeg -i reputation-clients-contents-16x9.mp4 -i reputation-clients-contents-9x16-musique.mp4 -map 0:v -map 1:a -c copy -shortest -movflags +faststart "Réputation 1 · Vos clients contents · 16x9 (musique).mp4"`.
Vignette YouTube 1280×720 = image à 1 s (accroche). Drive « Vokio · Réputation · pubs vidéo/16x9/ ». `flashs.py` : aucun. Faits revérifiés le 25/11 (19,99 €/mois Essentiel, 14 jours d'essai, SMS 2 h après, texte de lib/avis.ts, lien https://vokio.fr/a/) : rien à corriger.
⚠️ `hf snapshot` lance une analyse Gemini PAYANTE si GEMINI_API_KEY est posée : toujours `--describe false`.

## 25/11/2026 : film n° 3 « Le ticket » (`ticket/`)
Concept différent des n° 1 et 2 (texte serif + captures) : le fil rouge est le TICKET DE CAISSE thermique de l'Institut Camélia. 31,25 s (50 temps à 96 BPM), 9:16, sans voix off.
- **Minutage = `ticket/minutage.js`, en temps de musique** (un temps = 0,625 s), lu par l'image ET par `outils/salon.py` (via node). Changer un instant là déplace les deux.
- Plans : 0 accroche (ticket « INSTITUT CAMÉLIA / Marseille / mer. 25/11/2026 10:42 / Soin visage 45,00 € / TOTAL 45,00 € / Elle a adoré. », coupe à 2,5 s) · 3,1 s « Google ne le / sait pas encore. » · 6,25 s « À l'encaissement, son numéro. » + vraie capture (planche des films 1-2, numéro 06 39 98 41 78 tapé à la double croche) · 11,9 s « Deux heures plus tard, elle reçoit ce SMS. » (silhouette de téléphone sobre, texte réel de lib/avis.ts) · 15,6 s la semaine (6 tickets lun. → sam. qui glissent sur la pile, « Demande d'avis envoyée » ; compteur serif 47 → 48 → 50 → 53 → 56 avis, étoile à chaque palier) · 22,5 s chute (« Semaine du 23 au 28/11 / TOTAL DE LA SEMAINE / 9 nouveaux avis », coupe = drop à 25,0 s) · 26,25 s fin (wordmark, Réputation, « Une cliente part, une demande. », « 19,99 € par mois · 14 jours d'essai », vokio.fr/avis, « Établissement fictif »).
- ⚠️ Le brief disait « mar. 25/11 » : le 25/11/2026 est un MERCREDI, corrigé en « mer. ».
- Ticket : DejaVu Sans Mono Bold (police de reçu, distincte de la DA), 32 colonnes comme un rouleau de 58 mm, double hauteur pour les phrases (16 colonnes). Textures `outils/textures.py` (graines fixes) : papier (tuilage), masque de densité d'encre (stries verticales de tête usée + grain), comptoir uni. Le papier reste ATTACHÉ au rouleau (420 px cachés sous l'imprimante) jusqu'à la coupe, où la dentelure du bas apparaît au ras de la fente : sinon le bord coupé se voyait avant la coupe.
- Mouvement : une rangée par pas (0,075 s, power2.out), léger fléchissement du papier (0,3°) ; les gestes sonores démarrent 20 ms avant leur temps (`Ti`) pour que l'image du saut tombe sur le son. Toutes les valeurs absolues (jamais « += ») : seek dans n'importe quel ordre.
- Son : lit `outils/musique.py --prise 1` (ElevenLabs Music, Rhodes, contrebasse, balais, 96 BPM, fa majeur ; prise 0 écartée : accords qui s'éteignaient avant chaque mesure = 5 micro-coupures, balais à 10 s, silence dès 29,7 s). Prise 1 : tempo mesuré 96,0, phase 11 ms (recalée), aucune micro-coupure, aucune voix (Whisper : « Music playing »), accord final tenu jusqu'au bout (fondu 1 s). Beat du salon `outils/salon.py` (ElevenLabs Sound Effects, un tirage chacun) : imprimante = charleston, ciseaux = caisse claire (temps 2 et 4), tiroir-caisse = accent sur « Demander un avis », sonnette transposée do6-fa6-la6-do7 aux paliers, sèche-cheveux = montée 22,7 → 25 s coupée net, coupe du papier + grosse caisse synthétique = drop. Le lit passe dans un passe-bas qui s'ouvre (450 Hz → 9 kHz) pendant la montée : c'est ce qui fait éclater la chute.
- Mix : -14,2 LUFS, crête -1,4 dBTP (gain linéaire + alimiter doux). `outils/musique.py --controle son/mix.wav` : aucune micro-coupure.
- Synchro : `ticket/outils/synchro.py <rendu>` (début du geste à l'image contre attaque du son) : 26 événements sur 28 à ≤ 41 ms, moyenne 17 ms ; les deux restants (1,41 s et 3,13 s) sont des faux positifs de l'instrument (mouvement du pas précédent / ticket retiré dans la fenêtre).
- Crédits ElevenLabs : 714 → 2 647 (prise 0 : 965, prise 1 : 845, 7 bruitages : ~120).
- Refaire : copier `assets/fonts/*`, `assets/captures/saisie-planche.png` et les deux DejaVuSansMono(-Bold).ttf de /usr/share/fonts/truetype/dejavu dans `ticket/assets/`, `python3 ticket/outils/textures.py`, `python3 ticket/outils/salon.py`, puis `flock /tmp/hf-rendu.lock bin/hf render videos/reputation/ticket --fps 30 -o /dev/shm/ticket-muet.mp4`, `python3 outils/flashs.py` (aucun), `python3 ticket/outils/salon.py --livrer /dev/shm/ticket-muet.mp4 <sortie>`.
- Livré : `/root/vokio-uploads/videos/reputation/reputation-le-ticket-9x16.mp4` + `-couverture.png` (image à 2,4 s, accroche entière dans le 3:4) ; Drive « Réputation 3 · Le ticket · 9x16.mp4 », « … · couverture.png », Google Doc « … · légende ». Rien publié.
