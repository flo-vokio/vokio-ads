# Chantier « prénom » (28/09/2026) · journal de reprise

Décision de Florian : remettre l'échange « Très bien. C'est pour quel prénom ? » / « C'est pour Florian. ».
Tout ce qui suit l'échange est décalé d'une mesure : 92 images = 3,066667 s = 147 200 échantillons à 48 kHz.
Film : 47,00 s (1 410 images) → 50,066667 s (1 502 images). Référence 47 s : commit a6d3d8e.

## Monteur son (dialogue.py, mots.py)

- [en cours] 28/09 17:10 : lecture de dialogue.py, mots.py, OUTILS.md, BRIEF.md. Intermédiaires dans /dev/shm/prenom/.
- [fait] 17:40 : son/dialogue.py (showcase ET copie identique showcase-iphone/son/dialogue.py, qui écrit la copie lue par
  mots.py et construire.py). Mécanisme générique INSERTIONS (pivot_image, images, extraits nés de l'insertion), décalages
  en échantillons entiers, `decalage_effectif()`, `decaler(t)`, dialogue.json porte "insertions", "images", "fps",
  "duree_base_s" et par extrait "decalage_base", "decalage_echantillons", "insertions", "insertion".
  Insertion « prenom » : pivot image 758 (25,2667 s, un temps de la grille), 92 images, 147 200 éch.
  Extraits AP (agent, 63,24 → 65,00, film 25,47 → 27,23) et CP (appelant, 65,74 → 66,56, film 27,97 → 28,79),
  même décalage −37,77 (le vrai silence question → réponse, 1,19 s, est gardé). A4 → 29,236667, C4 → 36,856667.
  Preuves : sans insertion le code redonne l'ancien dialogue.wav à l'octet (md5 97ff1808…) ; nouveau dialogue.wav
  (md5 2544f895…, 2 403 200 éch.) = ancien jusqu'à 25,47, = ancien décalé de 147 200 éch. après 28,79, rien d'autre entre.
  Les 3 CONTRAINTES_IMAGE passent (elles ne visent que C2, A2A3, C3, non décalés).
- [fait] 18:05 : showcase-iphone/outils/mots.py généralisé (repère du relevé via lire_decale : un extrait qui glisse de n
  échantillons garde ses mots au µs près ; relevé Scribe complémentaire pour les extraits ajoutés, en cache dans
  showcase-iphone/son/transcription-scribe-complements.json ; REVUES AP#0,1,2,4,5 et CP#0,1,2, VOYELLES CP#2,
  REPERES_SYLLABES florian_flo/ri/an). Preuves : sur le film de 47 s, sortie identique à l'octet à l'ancien mots.py
  (md5 e0e12218…) ; sur le nouveau dialogue, 51 mots A1-C3 identiques, 29 mots A4-C4 décalés de 3,066667 s (±1 µs) et
  de +92 images exactement. Écart préexistant : le mots.json commité (27/09 09:23) n'avait pas été relancé après la
  retouche des bords du 27/09 au soir : « parfait. » fin 24,95 → 24,93, champs scribe de « mon »/« chat » (info).
- [fait] 18:25 : VOYELLES de tous les mots de AP/CP ; copies synchronisées dans le projet son (showcase/outils/mots.py,
  showcase/son/transcription-scribe-complements.json, showcase/donnees/mots.json : stems_amont.py exige mots.json
  identique entre variantes). mots.json md5 398e7b5b… dans les deux projets.
- [fait] son brut de l'échange : bords AP/CP dans le vrai blanc (−78,3 dBFS aux quatre bords) ; jointures à la chaîne voix
  ≤ −84,8 dBFS côté voix ; l'entrée de CP a la signature de celle de C4 (validée) : la porte s'ouvre sur la montée du /s/
  de « C'est » (28,02) ; la pause interne de AP (25,94, « Très bien. » → « C'est », 280 ms) est la vraie pause de l'agente,
  même signature que celles de A1 (5,475 ; 8,74). « Florian » (CP) à la chaîne voix : −20,0 LUFS, 1-4 kHz −35,2 dB,
  dans la médiane de l'appelant (chat −19,1, demain −18,9, neuf −20,5, Super −18,5) : AUCUN gain de clip.
- [fait] outils réutilisables (projet son) :
  * `python3 son/dialogue.py --avant /dev/shm/ref` : le dialogue d'avant les insertions (md5 97ff1808…, = a6d3d8e) ;
  * `python3 outils/verifier_insertion.py --ref git:a6d3d8e --wav-ref /dev/shm/ref/dialogue.wav [--mots-ref …]` :
    extraits, mots, syllabes, wav à l'échantillon ; code 1 si autre chose a bougé (ici : « insertion propre ») ;
  * `python3 outils/chaine_voix.py -o /dev/shm/voix.wav` : la chaîne voix de mix.py seule (constantes lues dans mix.py),
    pour juger un mot avant que l'image et les stems soient refaits.
  Lignes proposées pour OUTILS.md § 5 (je n'édite pas showcase-iphone) : les trois commandes ci-dessus, et « Allonger le
  film : une entrée dans INSERTIONS de son/dialogue.py (pivot sur un temps de la grille), les extraits nés avec
  "insertion": id, puis dialogue.py → mots.py → verifier_insertion.py ».
- VALEURS pour l'image : film 50,066667 s = 1 502 images ; règle « image ≥ 758 du film de 47 s → + 92 » (dialogue.json
  "insertions"). Mots nouveaux (début / voyelle / fin, image du début) : Très 25,515/25,585/25,66 (765) ; bien. 25,66/25,77/
  25,90 (770) ; C'est 26,105/26,215/26,277 (783) ; pour 26,277/26,32/26,40 (788) ; quel 26,40/26,46/26,585 (792) ;
  prénom ? 26,585/26,675/26,94 (798) ; C'est 28,06/28,125/28,195 (842) ; pour 28,195/28,21/28,295 (846) ;
  Florian. 28,295/28,395/28,70 (849). Syllabes (mots.json "syllabes") : Flo 28,295 · 28,395 · 28,475 ; ri 28,475 · 28,515 ·
  28,58 ; an 28,58 · 28,60 · 28,70. Le /f/ de Florian encadre le temps 850 (28,333) de la grille. signe_florian (voyelle
  de « Florian, » de A4) : 30,421667, image 913 (= 821 + 92). « Parfait, » 29,306667 (879). « -tion » 36,021667.
  Blancs : « parfait. » → « Très » 0,585 s ; « prénom ? » → « C'est » 1,12 s (vrai silence, latence médiane de
  l'appelant sur l'appel : 1,19 s) ; « Florian. » → « Parfait, » 0,607 s.
- À faire ailleurs : image (construire.py DUREE 1502/30, par_ligne {"C2","C3","C4"} → + "CP" si l'appelant s'affiche par
  ligne, pages de texte de AP/CP, s5 : plume en suspens puis écriture sous la voix) ; son (stems_amont.py ne code aucun
  extrait en dur, prendra AP/CP ; exige scenes.json/secousses.json identiques entre variantes ; musique : une mesure
  insérée sur le temps 758 garde la grille). CONTRAINTES_IMAGE : les 3 passent, aucune en attente (elles visent C2, A2A3,
  C3, non décalés) ; à ajouter quand l'image aura nommé ses constantes de s5 (même forme : bord de AP/CP ≤ constante).
- Intermédiaires de /dev/shm/prenom purgés (tout est régénérable : --avant, mots.py).

## Compositeur / monteur musique (riche-musique, stems amont, recettes)

- [fait] 28/09 17:45 : lecture de riche-musique (mix_riche_musique.py, instruments.py, el_musique.py), stems_amont.py,
  recettes hybride*.json, mixer.py. NATURE : partition numpy déterministe (instruments.py), AUCUNE prise ElevenLabs retenue
  (el/ = plans et évaluation seulement) ; stems_amont ne lit la musique d'aucun fichier : riche-musique.fabriquer() la
  recalcule en mémoire (ducking et rattrapages sur le dialogue) et l'écrit dans son/stems-amont/iphone/musique.wav.
  Choix : écrire la mesure dans la partition (pas de montage audio) : tb(n) passe par la chronologie des insertions de
  dialogue.json (temps de base ≥ 25,2667 → + 3,066667), les voix tenues (cordes, pédale) durent une mesure de plus, l'arc
  du bus est tenu pendant la mesure insérée. Intermédiaires : /dev/shm/prenom/musique/.
- (Réordonné le 28/09 au soir : les entrées ci-dessous, de 18:40 à la fin, étaient écrites en fin de fichier, mêlées
  à celles du réalisateur.)
- [fait] 18:40 : outils/chronologie.py (NOUVEAU, la règle de dialogue.json « insertions » pour tous : decaler, vers_base
  avec temps TENU dans la mesure insérée, decaler_echantillon, inserer) ; riche-musique/mix_riche_musique.py : tb() à
  travers la chronologie, T0 pris sur le ré ramené au film d'avant et posé sur son image, arc_bus tenu pendant la mesure
  insérée, seuil « t0 > 36 » → « t0 > T_RAC », règle ARRET_TEMPS (32, 34) dans reponses() (+2 dB au plus dans les pauses de
  l'arrêt composé), controle_plume() ; mix.py et riche-musique : détecteur de voix à blocs de 1 ms rembourré (2 403 200 éch.
  n'est pas un multiple de 48 : mix.py PLANTAIT sur le film de 50,07 s) ; riche-design : STYLO_RETIRE, lecture du SMS
  (38-41) et saut vers le ı (42,2-42,6) à travers la chronologie ; stems_amont.py : --seulement musique [--couches D],
  cues-design.json + cues-musique.json écrits par le calcul complet, VARIANTES iphone relatif à PROJET, garde
  EV_A_L_IMPORT (arrêt si showcase/donnees et la variante diffèrent sur un instant lu à l'import).
- [fait] preuves de non-régression (bac à sable /dev/shm/prenom/musique/base = a6d3d8e + code modifié) : musique 47 s
  identique À L'OCTET au stem actuel (md5 6ff25d2c…) ; mixer.py modifié sur la recette 47 s : mix-hybride.wav identique à
  l'octet (md5 c6158daf…).
- [fait] musique 50,07 s dans le bac à sable « nouveau » (données PROVISOIRES : outils/inserer_temps.py donnees, règle des
  insertions ; écriture_debut provisoire 28,4667) : preuve par couches (inserer_temps.py verifier) : avant le pivot, 12 couches
  sur 13 nulles à l'octet (pédale −115,6 dBFS, réverbe −129,6) ; après la mesure insérée, toutes les couches frappées
  identiques à l'octet décalées de 147 200 éch. (basse : sauf la queue de 41 ms de la note du temps 32, qui sonne AVANT la
  mesure insérée) ; cordes, pédale, réverbe : mêmes notes, mêmes poids, oscillateurs continus (pas de raccord). Stem :
  identique sous −90 dBFS jusqu'à 25,0215 s (fin de « parfait. » : l'ancienne réponse de +2 dB de la plume n'a plus lieu,
  la question arrive 0,515 s après) ; bords 25,2667 et 28,3333 : dérivée 2e −44 / −49 dB sous le p99,9, marche RMS 20 ms
  −0,72 / −0,11 dB. Arc tenu à 0,8947 dB (ancien au pivot 0,8946). Pouls repris à 29,099 (temps 38 = 34 d'avant).
- [fait] recettes hybride.json et hybride-16x9.json : outils/inserer_temps.py recette (vérifié à l'échantillon, idempotent),
  références lues à travers les insertions, garde_reperes.cues = ../stems-amont/iphone/cues-design.json +
  cues_reference = ../riche-design/cues-design.json (mixer.py et ausculter.py : fenêtre de référence par id), voulu
  « mesure insérée » dans contre. OUTILS.md § 5 : 6 lignes ; fond_ligne.py : exemple 50,07 s.
- [fait] 19:30 : VOIX TENUES À PHASE ENTIÈRE (instruments.voix_corde chrono=, RM.verre_frotte, chronologie.cycles_entiers /
  phase_entiere) : dans la mesure insérée, dérive, vibrato, trémolo et phase des cordes et de la pédale font un nombre entier
  de cycles (vibrato ±0,16 Hz, hauteur ≤ 1,4 cent, pendant 3 s) ; le frottement du verre = le bruit d'avant avec un bruit neuf
  inséré (fondus 50 ms). Résultat : APRÈS la mesure insérée, cordes −97,9 dBFS, pédale −180,6 dBFS de l'ancien décalé (avant :
  −12 dB, une autre réalisation) ; avant le pivot, TOUTES les couches nulles à l'octet (pédale comprise).
- [fait] données de l'image arrivées (réalisateur, 16:27 UTC) : showcase/donnees ← evenements, scenes, secousses du 9:16
  (identiques exigées par stems_amont) + point-resolu du classique décalé (inserer_temps.py donnees) ; stems_amont VARIANTES
  iphone vidéo = le-point-sur-le-i-9x16-image.mp4. Musique refaite sur les VRAIES données (python3 son/stems_amont.py
  --seulement musique) : son/stems-amont/iphone/musique.wav md5 719d8db5… (50,066667 s, −19,49 LUFS, crête −1,7 dBFS).
- [fait] trois défauts trouvés par un calcul complet de stems_amont + mixer.py en bac à sable (/dev/shm, rien installé) :
  (1) riche-design ecriture() « grain de plume trop court » (plume_pose → ecriture_fin = 3,57 s d'un seul tenant) : ECRITS en
  DEUX gestes quand l'image a ecriture_nom (« 09:00 » plume_pose → heure_ecrite ; « Florian » ecriture_nom, bord révélé
  850/854/858, mesuré stable 21,1/18,1/21,0 px), vokio par la chronologie ; cues plume-nom / pose-plume-nom ;
  (2) le la · sol de la plume (mix.py, à ecriture_debut) tombait sur « bien. » : 8,2 LU, le pire mot du film, et le lit se
  creusait de 12 dB pour rien (rattrapage impossible) → mix.py T["la_rdv"] : sol sur ecriture_fin (28,933, la dernière
  lettre de « Florian »), la 0,24 s avant ; RM.rattrapages : si le lit ne peut pas sauver un mot, il ne lui coûte pas plus
  de 1 LU (jamais atteint à 47 s) ; copies synchronisées : showcase-iphone/son/mix.py (identique), controles.py (attendus du
  la · sol), controle_son.py des deux projets (images attendues lues dans les données) ;
  (3) son/dialogue.py --avant plantait (contrainte AP/CP absente du film d'avant) : corrigé dans les deux copies (identiques).
  Mix hybride d'essai : −14,03 LUFS, arc 1,52 LU, marge K min 10,5 LU (« dix », comme à 47 s), mots de l'échange 17,0-27,8 LU,
  19 repères dont 0 enterré ; restent 3 marches « contre » non voulues hors musique (38,575 ligne/pièce, 40,19 fin du vibreur,
  42,165 pièce) : pour l'agent du son final.
- [fait] non-régression finale (bac à sable a6d3d8e + tout le code) : les 10 stems amont du film de 47 s identiques À L'OCTET
  (avec la vidéo de 47 s) ; mixer.py sur la recette de 47 s : mix-hybride.wav identique à l'octet. Preuves chiffrées :
  prenom/preuve-musique.json. Ancien stem musique : $UP/versions-47s/stems-amont-musique-47s.wav (md5 6ff25d2c…).
- À FAIRE (agent du son final) : python3 son/stems_amont.py (4,5 min, passe en bac à sable) puis mixer.py des deux
  recettes ; sorties.planches des recettes pointent vers le scratchpad /tmp (utiliser --planches /dev/shm/…) ;
  controle_son.py garde des fenêtres du film de 47 s (33,05-34,03, 25,4-26,1, 4,91-35,48…) pour la bande classique ;
  les bruits de ligne et de pièce sont retirés sur la longueur du film (une autre réalisation après l'insertion, inaudible).
- Intermédiaires /dev/shm/prenom/musique purgés.
- [fait] 28/09 20:20 UTC, REPRISE (2e agent compositeur, après la coupure de 17:46) : tout vérifié, rien refait.
  * Stem : son/stems-amont/iphone/musique.wav recalculé sur le code actuel (mix_riche_musique.py retouché à 17:45, APRÈS le
    calcul de 17:39) : md5 719d8db5… identique ; musique.json : empreinte à jour. Non-régression rejouée : code actuel + données
    a6d3d8e → stem 47 s md5 6ff25d2c… (identique à l'octet au stem validé).
  * Preuve fine (prenom/preuve-musique.json « reprise_verification ») : couches, courbes de gain (pas de 16 éch.) et stem,
    l'ancien décalé de 147 200 éch. : avant le pivot, les 13 couches nulles (réverbe −325 dBFS) ; après la mesure, 10 couches
    frappées nulles à l'octet (la basse dès 28,374 : la queue de 41 ms de sa note du temps 32 a sonné avant la mesure), cordes
    ≤ −97,5 dBFS, pédale ≤ −136, réverbe : queue des notes tenues jusqu'à 30,5 s, puis ≤ −110. Stem : avant le pivot, identique jusqu'à 25,02 (ensuite la
    réponse de +2 dB de l'ancienne pause de la plume n'a plus lieu : « Très » arrive 0,585 s après « parfait. ») ; après la
    mesure : −14 dB sous la musique sur 28,33-30 (la voix y a changé : « Florian », la · sol, « Parfait, »), −42 dB sur 30-31,
    puis 57 à 90 dB sous la musique (crête −72,1 dBFS à 35,9 s). Causes mesurées, toutes des écarts de gain ≤ 0,0083 dB :
    détecteurs de voix à blocs de 1 ms (147 200 éch. = 3 066,67 ms), instants de evenements.json au µs (signature, clairière :
    ≤ 0,001 dB), cordes tenues à phase entière. Inaudible ; l'annuler demanderait de changer la cadence du détecteur, donc le
    film de 47 s (fin de la preuve à l'octet) : écarté.
  * Jointures 25,2667 / 28,3333 : dérivée 2e −44 / −50 dB sous le p99,9 (médiane naturelle du stem −43), marches RMS 20 ms
    −0,73 / +0,48 dB (naturel : médiane 0,50, p90 1,44), 4-16 kHz −0,70 / −2,79 dB (médiane 0,91, p90 5,63) ; ausculter.py
    sautes 22-32 s --mots : aucune marche aux bords (une seule, 30,82, un coup de shaker qui existe à 27,75 dans le film de 47 s).
  * Repères : 164 attaques et 84 cues de la partition à t (avant le pivot) ou t + 3,066667 ; silences du raccroché et de fin à
    +147 200 éch. exactement ; « -tion » (tb(43) = 36,000, sa voyelle 36,022), ré (tb(56) = 45,967), fin (49,767) : les nouveaux instants.
    L'arrêt composé (le lit seul, dernier coup : shaker 24,886) couvre 24,50 → 29,10 : « Très bien. », la question, le vrai
    silence, « C'est pour Florian. » ; le pouls reprend au temps 38 (29,099), 0,21 s avant « Parfait, » (0,21 s à 47 s aussi).
  * L'écriture : « 09:00 » (762 → 777) sous « Très bien. » : la plume seule (riche-design, premier geste), aucune note (le la ·
    sol y tombait sur « bien. », 8,2 LU, et dirait le motif deux fois). « Florian » (848 → 868) : le la · sol le signe, sol sur
    la dernière lettre (image 868, 28,933), la 0,24 s avant (28,693, la fin de « Florian. ») ; choix confirmé, calé sur l'IMAGE
    et non sur la grille (la double-croche 37,75 tombe à 28,908, 25 ms plus tôt ; le motif ne vit pas sur la grille, au logo non
    plus) : le sol est une anacrouse du temps 38, où le pouls revient (0,166 s après, « ok » de controle_plume, marge 0,10).
  * Outils : outils/chronologie.py a une CLI (résumé ; --verifier-image : accord prouvé avec showcase-iphone/outils/temps.py sur
    1 411 images et 423 001 instants, aller et retour, + une liste synthétique de 3 insertions) et renvoie à temps.py dans son
    en-tête (temps.py renvoyait déjà à chronologie.py) ; les deux restent séparés, chaque projet garde ses preuves à l'octet.
    chronologie.py ajouté aux empreintes de stems_amont.py et de mixer.py (il n'y était pas : une retouche de la règle
    n'aurait rien fait recalculer). NOUVEAU outils/bac_a_sable.py (le geste que deux agents ont fait à la main) : « monter »
    (code actuel + données d'un commit + dialogue d'avant, chemin du wav corrigé), « musique » (stems_amont --seulement musique
    dans le bac à sable : redonne 6ff25d2c…, testé), « comparer » (couches, gains, stem, fenêtre par fenêtre, pour toute liste
    d'insertions : redonne les chiffres ci-dessus, testé). OUTILS.md (9:16) : § 5 deux lignes, § 7 étape « 5 bis » (musique).
  * Réglages NON décalés, hors de la chaîne hybride (à porter par la chronologie si l'une de ces variantes renaît à 50 s) :
    riche-design halo() (fenêtres de mesure 33-35,5, 38-41, 45,3 : stems_amont ne refait pas le halo) ;
    riche-musique/controle_musique.py (13 lignes) et riche-design/controle_design.py (23 lignes) : contrôles des variantes 2 et 3
    de 47 s ; son/controle_son.py : bande classique (déjà noté).
  * Pour l'agent du son final, en plus : cues-design.json (lu par garde_reperes des deux recettes) n'existe qu'après le calcul
    complet de stems_amont ; les recettes copient vers $UP/point-solaire-bande-son-hybride(-16x9).wav (les 47 s sont dans
    $UP/versions-47s/) ; stems_amont refait la musique à l'identique (il ne lit pas musique.wav, il le recalcule).
  * Intermédiaires /dev/shm/prenom/musique (bac à sable a6d3d8e, couches, gains) purgés.

## Réalisateur motion design du 9:16 (showcase-iphone : construire.py, s5, formats)

- [en cours] 28/09 18:00 : lecture de OUTILS.md, construire.py, s4 à s7, lib, mise-en-page, dialogue.json (insertions).
  Choix de mise en scène (liberté de Florian) : le point écrit « 09:00 » sous « Très bien. » (l'heure est acquise), LÈVE la
  plume au-dessus du créneau pendant « C'est pour quel prénom ? » (il attend, immobile : « 09:00 » se lit en entier, le
  nom manque), la repose sur « C'est pour » et écrit « Florian » sous Flo·ri·an ; le sous-titre de l'appelant « C'est
  pour Florian. » paraît mot à mot (le nom paraît avec sa voix et sous la plume) ; le hochement de « je vous note ça pour
  Florian » devient la confirmation, inchangé et décalé de 92 images. Tout le reste : film de 47 s décalé de 92 images.
  Mécanisme : outils/temps.py (la règle des insertions, lue dans son/dialogue.json) ; construire.py écrit les constantes
  du film de base et les porte par B() / BI() ; TEXTE.decaler() côté scènes.
- [fait] 18:40 : outils/temps.py (NOUVEAU : la règle des insertions, CLI + module ; --decalages donne « --decalage 758:92 ») ;
  lib/texte.js TEXTE.decaler / decalerT ; construire.py (B(), BI(), hotes(), borne_debut(), poser_hotes() qui réécrit les
  hôtes de index.html, choregraphie_s5(), SORTIE_QUESTION 27,84 / SORTIE_REPONSE 29,08, sorties des pages par (extrait,
  depuis), ATTENDU_BASE porté par BI + ATTENDU_PRENOM) ; preparer_agenda.py (bloc.heure_encre, bloc.florian_lettres) ;
  navigateur.py PAGES (+ AP « Très bien. | C’est pour quel prénom ? » haut_agente, + CP « C’est pour Florian. »
  haut_appelant) ; s5 (5 pages, l'appelant mot à mot, contrats plume levée / encre sous la voix), s6 (TEXTE.decaler), s7
  (commentaires) ; index.html (hôtes posés : s5 25.2/9.216666, s6 34.416667/10.0499, s7 44.466666/5.6, racine et audio
  50.066666 = ceil × 30 = 1502 images) ; mise-en-page/agenda.json t_haut_min 34,176667 ; texte.json 16x9 coupes
  s5-rendez-vous#4 (était #2) + #0 « Très bien. / C’est pour / quel prénom ? » (en deux lignes : 3 px de l'agenda) ;
  son/dialogue.py (les DEUX copies, identiques) : CONTRAINTES_IMAGE + AP/SORTIE_QUESTION et CP/SORTIE_REPONSE, lues dans
  le projet du 9:16 (IMAGE_9X16) depuis les deux copies ; relancé dans les deux projets : code 0, dialogue.wav md5
  2544f895… inchangé. format.py PLANCHE portée par temps.py (+ « s5 prénom attendu » 27,2).
  Nouveaux gestes (images) : plume posée 761, « 09:00 » 762 → 777, levée 777 → 787 (72 px, disque ≥ 9 px au-dessus du
  bloc), en suspens 787 → 842, reposée 842 → 848, « Florian » 848 → 861 à 13,0 px/image puis 868 (sine.out), jet du bloc
  868 → 874, levée 872, gouttière 886, hochement 913. Point résolu : images 0-757 identiques au film de 47 s ; base ≥ 801
  = nouveau + 92 (écarts ≤ 0,001 px d'arrondi, v seul à 801).
  Contrôles : construire.py ok ; hf check ok (avertissements : taille des fichiers, audio de 47 s du projet) ;
  controles_internes ok ; controle_format ok (E1 max 3 éléments) ; 16:9 construit dans /dev/shm (format.py --check ok).
- [en cours] 18:45 : rendus (sans perte nouveau + a6d3d8e extrait, pour la preuve ; livrable 9:16 image).
- [fait] 19:05 : 16:9 construit dans /dev/shm/prenom/f169 (format.py 16x9 --check : ok ; controle_format ok, E6 125 px ;
  controles_internes ok). Coupe 16:9 ajoutée (texte.json) : « Très bien. / C’est pour / quel prénom ? » (en deux lignes, la
  question finissait à 1097, 3 px de l'agenda). L'agent du 16:9 n'a qu'à lancer `format.py 16x9 --check --planche` puis le rendu.
  controles.py : BI (temps.py, D.insertions) sur CLES et la planche des vues, I3 et D8 lus dans les événements, V1 lit
  decalage_base (construire.py publie decalage_base et insertion dans DONNEES.dialogue.extraits). OUTILS.md : § 0 (film de
  50,07 s, plus de --entrees git:aa4dd24), § 2 temps.py, § 4 preuves décalées, § 5 lignes du monteur son, § 6 films,
  § 7 recette « Insérer du temps dans le film ». En-têtes de format.py, verifier_scene.py, variante.py mis à jour.
  Rendus relancés en mémoire (TMPDIR=/dev/shm/prenom/tmp ; le premier écrivait dans /tmp, arrêté et nettoyé).
- [fait] 19:25 : première preuve sans perte (a6d3d8e rendu à neuf = formats/empreintes-9x16.json, 1 410/1 410) : base 0-757
  identiques ; 801-1409 : 565 identiques, 39 à ≤ 25 niveaux (arrondi au µs des instants décalés : 92/30 s n'est pas un
  nombre entier de µs ; PSNR ≥ 71 dB), et 5 VRAIES (883-887) : « samedi » (29,45 s = 883,5 images, pile une demi-image)
  s'arrondissait une image plus tard (Math.round sur 32,516667). Corrigé dans lib/texte.js : image() / aImage() et
  TEXTE.reveler (aImagePlus) arrondissent un instant d'après l'insertion DANS LE FILM DE BASE (versBase : l'instant d'origine
  au µs, + les images insérées) ; identité stricte sans insertion. pages.json inchangé. Rendus relancés.
  formats/empreintes-9x16-47s.json (NOUVEAU) : l'empreinte sans perte du film de 47 s (a6d3d8e), la référence des preuves
  d'insertion.
- [fait] 19:45 : LIVRABLE $UP/le-point-sur-le-i-9x16-image.mp4 : 1 502 images, 50,067 s, h264 1080×1920 30 i/s, md5
  4b0849da5c665ad1c6cdca7d4a138759 ; piste provisoire = son/dialogue.wav (le vrai appel seul, au bon minutage : la bande
  classique assets/son/mix.wav fait encore 47 s) ; à poser sur le mix hybride refait par outils/livrer.py.
  PREUVES (rapports dans $UP/controles-9x16/) :
  * sans perte (identite.py comparer formats/empreintes-9x16-47s.json nouveau --decalage 758:92 --voulu 758-800) : base 0-757 =
    nouveau 0-757 identiques (758/758) ; sans décalage, 0-761 identiques (les 4 images 758-761, avant la 1re lettre de 09:00,
    sont les mêmes) ; base 758-800 ↔ 850-892 : la scène refaite (voulu) ; base 801-1409 ↔ 893-1501 : 572 identiques au bit, 37 à
    ≤ 25 niveaux sur quelques pixels (PSNR ≥ 71,4 dB), arrondi au µs des instants décalés (s5 fin 937-942, s6 959-969,
    C4 1019-1034, bulle 1103-1106, départ et écriture de Vokıo 1235-1274) ; 0 hors tolérance (comparer_mp4 sans perte : ok).
  * au codec près contre $UP/versions-47s/le-point-sur-le-i-final.mp4 : 0-757 : 757 identiques + 1 conforme ; 801-1409 : 47
    identiques, 390 conformes, 172 signalés par le seul critère « chute » (PSNR ≥ 49,4 dB, ≤ 0,014 % de pixels > 48 niveaux) :
    le GOP décalé de 92 images, pas l'image.
  * a6d3d8e rendu à neuf = formats/empreintes-9x16.json d'avant (1 410/1 410) : la référence est saine.
  * controles.py sur le livrable (--mix son/dialogue.wav) : TOUS les contrôles image passent (D1-D8, DOM1-5, V1, I1-I6,
    F1-F8, Z1-Z2, S2), 1 À VALIDER (horodatage iOS, inchangé) ; échecs attendus du SON seul (A1 sonie du dialogue nu −21,4
    LUFS, S1 stems de 47 s, A2 pas de mesures, L1 débit audio 115 kb/s) : à refaire avec le mix de 50 s.
  * copie 9:16 reconstruite par format.py 9x16 : identite.py donnees = identique partout (les sources redonnent les données).
  formats/empreintes-9x16.json RÉÉCRIT (1 502 images, l'état du 28/09, à committer avec) ; formats/empreintes-9x16-47s.json.
  Intermédiaires de /dev/shm/prenom (les miens) purgés ; /dev/shm/prenom/musique (compositeur) non touché.

## Mixeur de la bande son finale du 9:16 et livraison

- [en cours] 28/09 20:23 UTC : lecture du journal, OUTILS.md, skill vokio-video. Intermédiaires dans /dev/shm/prenom/mix/.
- [fait] 20:28 : son/stems_amont.py complet (variante iphone, vidéo 9:16 de 50 s) ; confort de l'appelant autour de CP :
  la ligne prend le relais à la fermeture de sa porte (28,65 → 29,2, −52 → −66 dBFS dans 2-8 kHz), porte ouverte 7,26 s
  (6,94 à 47 s). musique.wav inchangé (719d8db5).
- [fait] 20:33 : mixer.py hybride.json (planches /dev/shm) : −14,03 LUFS, −1,70 dBTP ; « Florian. » −12,33 LUFS (Moka
  −12,60, demain −11,29), marge K 17,9 LU. Copie $UP/point-solaire-bande-son-hybride.wav (seule copie de la recette).
- [fait] preuve de continuité : l'ancien mix (47 s) REFAIT À L'OCTET dans un bac à sable (bac_a_sable.py stems + mixer,
  NOUVELLES commandes : c6158daf) ; comparaison stem par stem (bac_a_sable.py comparer) : après la confirmation, des
  textures tirées sur la longueur du film avaient changé de réalisation (ligne, pièce, air du point) et le vibreur de
  phase (horloge absolue) : inaudible mais pas « le son validé décalé ».
- [en cours] 20:48 : correction à la source, générique : chronologie.texture() (base à l'octet hors des mesures, neuf
  dedans, fondus 50 ms) et vers_base_echantillon() ; appliqués à fond_ligne (stems_amont), riche-design ambiance
  (chaine_film) et bruit_module(film=True) (air du point), mix.py vibreur (les deux copies, identiques). Non-régression
  47 s dans le bac à sable + nouveau calcul en cours.
- [fait] mixer.py / ausculter.py reperes : un repère ABSENT de cues_reference (né dans le film actuel : plume-nom,
  pose-plume-nom) n'a plus de référence lue à la même fenêtre (−99 dB, garde inopérante) mais la cible par défaut ;
  recettes hybride.json et hybride-16x9.json : par_repere plume-nom / pose-plume-nom « exclu » avec la raison (sous le nom
  dit par l'appelant, la voix d'abord ; +51 dB en 8-16 kHz ; seule après le mot).
- [fait] inserer_temps.py verifier --compenser [--par] [--hors] : la preuve au gain de master près, fenêtre par fenêtre.
- [fait] 20:58 : stems amont refaits avec la correction (texture, vibreur) : après la confirmation, 7 stems sur 10 identiques
  À L'OCTET décalés (ambiance sauf 1 échantillon à −53 dBFS au bord du silence numérique ; sfx −97,6 dBFS ; objets −115 ;
  point −82 à −111 ; ecriture −72 à 44,3 s, l'encre lue dans la nouvelle vidéo) ; ligne −61 à −64 dBFS sur C4 (porte VAD du
  confort au pas de 1 ms : 147 200 n'est pas un multiple de 48, même classe que les détecteurs de la musique) ; musique
  inchangée (719d8db5). NON-RÉGRESSION : code actuel + données a6d3d8e = les 10 stems amont du film de 47 s À L'OCTET.
  (Un premier essai en parallèle du mixeur a été tué par manque de mémoire : stems_amont ≈ 2,1 Gio, un calcul lourd à la fois.)
- [fait] 21:05 : la garde des repères décidait autrement après l'échange (assise-i +4,5 dB au lieu de +3,0, plume-vokio
  +4,0 au lieu de +3,5) : ses trames de 5 ms (240 éch.) n'étaient plus alignées (147 200 = 613,3 × 240). NOUVEAU :
  chronologie.debuts_trames() (grille du film d'avant, décalée ; grille propre dans la mesure) ; ausculter.puissances_bandes
  (debuts=) et reperes(debuts=, --insertions) ; mixer.py : clé de recette « insertions » (hybride.json, hybride-16x9.json :
  ../dialogue.json), dans l'empreinte. Décisions redevenues celles du film validé, repère par repère.
- [fait] 21:08 : MIX FINAL son/hybride/mix-hybride.wav md5 22274ae12082cfd988d1fa5f43b3d441 (50,066667 s, −14,03 LUFS,
  −1,70 dBTP, LRA 7,0, arc 1,52 LU, marge K min 10,5 LU, 19 repères dont 0 enterré + plume-nom / pose-plume-nom exclus avec
  raison) ; copie $UP/point-solaire-bande-son-hybride.wav (seule copie de la recette). Non-régression : bac à sable a6d3d8e +
  tout le code → mix de 47 s c6158daf À L'OCTET. Continuité (inserer_temps.py verifier --compenser) : gain de master −0,040 dB
  (avant ET après) ; avant 25,27 : résidu −91 dB (−60 dB à 7-8 s, le limiteur de 7,226) ; après la confirmation (31-50 s) :
  −61 à −88 dB (45-47 s : limiteur de 45,99, 1,27 dB au lieu de 1,31 ; 36-37 s : ligne de C4, pas de 1 ms ; musique ≤ −49 dBFS
  crête, résidu accepté du compositeur). ausculter contre V47 (ancien décalé) : 0 marche avant 25,27 et après 29,24 ; toutes
  les nouveautés de trous/sautes sont dans l'échange (fins de mots, silence réel, plume levée, pose sur « 09:00 »).
  « Florian. » −12,33 LUFS (Moka −12,60, demain −11,29), 1-4 kHz −27,6 dB, marge K 17,9 LU : aucun gain de clip.
- [fait] 21:10 : LIVRÉ $UP/le-point-sur-le-i-final.mp4 md5 cf1a76e19ecf6429eaa43eea8f5fd77d (livrer.py : flux vidéo copié
  28b8068b…, −14,1 LUFS, −1,7 dBTP) ; relevé $UP/controles-9x16/livraison-final.json.
- [fait] bande classique showcase-iphone/son/mix.wav refaite à 50,07 s (md5 d92ffe79…, mix.py --sans-copie NOUVEAU : le
  livrable du 27/09 $UP/point-solaire-bande-son-v2.wav n'est pas réécrit) → assets/son/mix.wav, son/stems, son/cues.json ;
  controle_son.py porté (Bt(), fenêtres de la voix lues dans dialogue.json, tolérance de durée ½ échantillon, variante monde
  périmée rapportée) : tout passe sauf F (« pour » 30,18 : 7,8 LU sur la nappe de verre, non portée par la chronologie) :
  NON LIVRABLE, écrit dans OUTILS.md. Copies synchronisées : son/controle_son.py et son/mix.py identiques dans les deux projets.
- [fait] 21:15 : hf check (0 erreur, 3 avertissements de taille ; plus d'audio de 47 s) → $UP/controles-9x16/check-hf.json ;
  controles.py final --mix hybride --check : 37 contrôles sur 37, 0 À VALIDER (horodatage iOS VALIDÉ : DOM2-derogation) ; S1
  écart max 3,92 ms ; A1 −14,1 LUFS, −1,7 dBTP, résidu AAC −58,4 dB, calage 0 éch. Rapport de l'image seule gardé :
  controles-image-seule-piste-provisoire.json. Preuves et planches du mix : $UP/controles-9x16/ (preuve-continuite-…,
  preuve-stems-amont-…, preuve-stems-mix-…, son-planches/ dont echange-prenom-24,5-31,5.png).
- [fait] OUTILS.md § 3 (À VALIDER), § 5 (7 lignes : texture/horloge/trames, preuve --compenser, bac à sable complet, reperes
  --insertions, bande classique), paragraphe du mix de 50 s, § 6 (film final), § 7 étape 6 bis (son final).

## Agent du 16:9 YouTube (formats/16x9 : reconstruction, rendu image, preuve)

- [en cours] 28/09 20:25 UTC : lecture de OUTILS.md, format.py, mise-en-page/*.json. Entrées : format.py SANS --entrees lit
  son/dialogue.json et donnees/mots.json de l'arbre de travail (construire.py : ENTREES = PROJET par défaut) : c'est le bon
  chemin tant que le film de 50 s n'est pas commité (git:HEAD = a6d3d8e = 47 s, refusé). Temps propres au 16:9 dans
  mise-en-page : t_haut_min 34,176667 (porté), glisse 2,10 → 2,60 et fenêtres d'occupation 0-2,1 / 4,63-17,3 (avant le
  pivot, inchangés). stems_amont.py (agent du son) tourne en parallèle : je ne touche ni son/ ni les données du 9:16.
- [fait] 20:40 : `format.py 16x9 --check --planche --vues 852,393` SANS --entrees (arbre de travail) : construire ok, hf check ok,
  0 px du 9:16 en dur ; s5 regardée (planche + recadrages 1:1) : plume levée à y 272 (9,5 px au-dessus du bloc, 40 px sous la
  mention), rien à corriger par variante. heurts.py s5 marge 0 : aucun ; film entier marge 0 : seul le ı de s7 (permis) ;
  marge 12 : la tenue dans la gouttière (09:00, 1,2 px, voulue, déjà là à 47 s). controle_format --pas 1 : ok, E1 max 3, E6
  125,4 px. controles_internes ok. NOUVEL OUTIL outils/donnees_decalees.py (données d'avant portées par la règle, clé par
  clé ; « restée à l'ancienne valeur » = le défaut cherché) : 16:9 de a6d3d8e contre formats/16x9 : 0 valeur restée ;
  evenements, scenes, reperes, secousses conformes ; écarts expliqués (appel.json = bords du dialogue du 27/09 au soir, que
  le 16:9 de 47 s n'avait pas, construit sur --entrees git:aa4dd24, identiques au 9:16 ; « parfait. » fin_voix 24,95 → 24,93 ;
  v de l'image 893 = 801 + 92, voisine de la scène refaite ; coupes #2 → #4). Rapport : $UP/controles-16x9/prenom/.
- [fait] 20:45 : rendu $UP/le-point-sur-le-i-16x9-image.mp4 (1 502 images, 50,067 s) ; piste provisoire son/dialogue.wav
  (assets/son/mix.wav, la piste du projet, fait encore 47 s : --son-du-projet aurait posé une voix décalée de 3 s après l'échange).
- [fait] 20:57 : occupation.py sur le rendu : les 7 scènes et les 2 fenêtres aux seuils de formats.json (s5 : largeur 0,924,
  hauteur 0,876, bary y médian 0,334). PREUVE contre le 16:9 de 47 s :
  * sans perte : 16:9 de a6d3d8e rendu à neuf (identite.py extraire a6d3d8e, format.py 16x9 --sans-construire) contre le
    nouveau, --decalage 758:92 --voulu 758-800 : base 0-757 = 0-757 identiques au bit (758/758) ; 758-800 : la scène refaite
    (voulu) ; 801-1409 ↔ 893-1501 : 522 identiques au bit, 87 à ≤ 23 niveaux sur quelques pixels (surtout 5 ; PSNR ≥ 69,4 dB,
    0 pixel > 48 niveaux) : l'arrondi au µs des instants décalés, même nature que les 37 du 9:16 (le 16:9 en a plus : plus
    grands objets en mouvement). Deux rendus de chaque = mêmes empreintes. NOUVELLES références : formats/empreintes-16x9.json
    (50,07 s) et formats/empreintes-16x9-47s.json (a6d3d8e), à committer : la prochaine preuve du 16:9 n'aura plus à extraire.
  * au MP4 près contre $UP/versions-47s/le-point-sur-le-i-16x9-image.mp4 : 0-757 identiques au bit (758/758) ; 801-1409 :
    1 identique, 481 conformes, 127 signalés par le seul critère « chute » (PSNR ≥ 52,1 dB, médiane 60,8 ; ≤ 0,0025 % de
    pixels > 48 niveaux) : le GOP décalé.
  * controles.py sur le livrable (--mix son/dialogue.wav) : TOUS les contrôles image passent (D1-D8, DOM1-5, V1, I1-I6,
    F1-F8, Z1-Z2 : plume en suspens 788-841 à 178 px de la bande du haut et 486 px de « Passer » ; O1, S2, Y1) ; Y2 À VALIDER
    (inchangé) ; échecs attendus du SON seul (A1 −21,4 LUFS, S1 stems de 47 s, A2 pas de mesures, L1 audio 115 kb/s).
  Rapports : $UP/controles-16x9/prenom/ (donnees-decalees, occupation, sans-perte, comparer-mp4-47s, controles/, planches).
- [fait] outils et doc : outils/donnees_decalees.py (NOUVEAU) ; verifier_scene.py --entrees courant (arbre de travail) ;
  consignes « --entrees … » périmées retirées de variante.py, adopter_variante.py ; en-tête de format.py (sans --entrees =
  arbre de travail) ; OUTILS.md § 0, § 3, § 4 (preuves du 16:9, empreintes-16x9*.json), § 6 (films), § 7 étape 7 (formats).
  Aucune variante touchée : la chorégraphie de s5 tient dans le 16:9 telle quelle. Ni mix 16:9 ni livrer.py (étape suivante).
  Intermédiaires /dev/shm/prenom (les miens) purgés ; /dev/shm/prenom/mix (agent du son) non touché.

## Livraison 16:9 et YouTube (mix 16:9, livrer, contrôles, bumpers, doc, empreinte du 9:16)

- [en cours] 28/09 21:30 UTC : lecture du journal, OUTILS.md, skill. Intermédiaires dans /dev/shm/prenom/l16/. md5 d'avant
  (9:16 : mix-hybride.wav 22274ae1…, stems, film final cf1a76e1…) relevés dans /dev/shm/prenom/l16/md5-avant.txt.
- [fait] 21:25 : fenêtres de la recette 16:9 vérifiées contre les données (point-resolu du 9:16 et du 16:9) : dans 17,3 → 34,416667,
  le 16:9 met le point de l'autre côté SAUF 28,336 → 29,290 (écriture de « Florian » et retour à la gouttière : 9:16 x 552-740,
  16:9 x 1582-1770, tous deux à droite). Le miroir d'un seul tenant mettait la plume du nom à GAUCHE (−0,8 → −3,0 dB D−G) sous une
  plume à l'extrême droite (le film de 47 s avait le même défaut, 25,58 → 26,46, sur l'ancienne écriture d'un seul geste).
  NOUVEL OUTIL $SON/outils/espace_format.py : `fenetres` (plages miroir / tel quel tirées des deux trajectoires, bascule au passage
  du point du 9:16 par le milieu, fondu de mixer.py centré dessus ; --recette compare, --poser écrit) et `mesurer` (D−G de chaque
  stem contre le côté du point à l'image, contradictions, --instants). Recette hybride-16x9.json : miroir [[17.3, 28.311241],
  [29.315115, 34.416667]] sur sfx, point, ecriture, objets (mono inchangé), description complétée. Avant 25,27 : identique.
- [fait] 21:32 : mixer.py son/recettes/hybride-16x9.json --planches /dev/shm/prenom/l16/planches (2 min 20, 1,6 Gio) :
  mix-hybride-16x9.wav md5 05cde484b0974a4e3188241aa9a5f023 (= $UP/point-solaire-bande-son-hybride-16x9.wav), −14,03 LUFS,
  −1,70 dBTP, LRA 7,0, mono −0,11 LU, corrélation min 0,69, 19 repères dont 0 enterré (plume-nom, pose-plume-nom exclus), marge K
  min 10,5 LU ; limiteur max −2,33 dB à 29,325. 9:16 NON TOUCHÉ : mix-hybride.wav, sa copie $UP, mesures et 9 stems md5 identiques
  avant/après. espace_format.py mesurer (16:9) : 0 contradiction sur tout le film ; touchers +4,1 / +3,2 / +3,4 / +3,1 dB D−G
  (= 47 s) ; plume de « Florian » +0,8 → +3,0 dB (droite, comme l'image). Continuité contre le 16:9 de 47 s (inserer_temps.py
  verifier --compenser --par 1 --hors 24.9:31) : gain −0,050 dB avant ET après, résidu −89,5 dB avant 25 s (−57,9 à 7-8 s, le
  limiteur), −59 à −87 dB après 31 s (même classe que le 9:16). La marche « contre » non voulue 38,575 (1-2k, −11,1) est celle du
  9:16 (ligne/pièce, déjà signalée), pas propre au 16:9.
- [fait] 21:35 : format.py 16x9 --sans-construire --check (la copie du format avait encore l'ancien assets/son/mix.wav de 47 s :
  « Audio bande-son 47 s ») : 1 fichier réécrit (le wav), données/index/scènes du 16:9 inchangés (md5), hf check 0 erreur,
  3 avertissements de taille, plus d'audio de 47 s. Anciens contrôles du 16:9 de 47 s déplacés dans $UP/versions-47s/controles-16x9/.
- [fait] 21:35 : LIVRÉ $UP/le-point-sur-le-i-16x9.mp4 (livrer.py : flux vidéo fbece438… copié, −14,1 LUFS, −1,7 dBTP, 50,067 s),
  relevé $UP/controles-16x9/livraison-16x9.json. controles.py … --racine formats/16x9 --mix hybride-16x9 --check : 39 ok, 0 échec,
  Y2 À VALIDER (inchangé), A1 −14,1 LUFS / −1,7 dBTP / résidu AAC −59,3 dB / calage 0 ; rapport $UP/controles-16x9/controles.json.
- [fait] 21:39 : bumpers (extrait.py, qui redonne À L'OCTET l'ancien bumper 16:9 depuis l'ancien film : 70deca54…) : bornes
  44,266667 → 50,066667 (= 41,2 → 47 + 3,066667 ; 0,2 s avant s7 → fin ; evenements telephone_sortie, signature_la/sol/re, promesse,
  offre, silence_final tous à +3,066667) ; $UP/youtube/bumper-6s-9x16.mp4 0d5828cb… (−14,04 LUFS, −3,18 dBTP) et
  bumper-6s-16x9.mp4 7b32a40a… (−14,03 LUFS, −3,13 dBTP), 6,00 s, 180 images. Contre les anciens : mêmes images (PSNR min 49,1 / 47,0,
  médiane 55,7 / 56,7 ; les 3-4 premières sous le critère « chute », GOP de la source) ; son décalage 0, gain −0,01 dB, mix source
  identique à −56/−75 dB, écart de forme d'onde = AAC. Preuve $UP/controles-16x9/comparer-bumpers-47s-contre-50s.json.
- [fait] couverture 16:9 : l'instantané sans perte à 49,966667 s du nouveau 16:9 = le PNG livré AU PIXEL (inchangée) ; bannière :
  régénérée dans /dev/shm, identique au pixel (aucun temps) ; ANNONCE.md : aucune durée, inchangé.
- [fait] OUTILS.md : § 5 (espace_format.py, deux lignes ; paragraphe du 16:9 : recette dérivée), § 6 (film 16:9, bumpers,
  couverture), § 7 étape 8 (son et livraison d'un format), § 7 YouTube (bornes des bumpers, fenêtres de la recette, mesures).
- [fait] 21:55 : empreinte sans perte du 9:16 refaite (identite.py empreindre ., TMPDIR /dev/shm, sous flock) : 1 502 images,
  0 différente de formats/empreintes-9x16.json (déjà réécrite à 16:38 avec le film de 50 s par l'agent de l'image) : le 9:16 n'a
  pas bougé depuis. Fichier gardé tel quel (sa « note » faite main n'est pas réécrite par l'outil), clé « reverifiee » ajoutée.
- Livrables : $UP/le-point-sur-le-i-16x9.mp4 0752b2b40dbfb81bd1434eb832c4798d, $UP/point-solaire-bande-son-hybride-16x9.wav
  05cde484…, $UP/youtube/bumper-6s-9x16.mp4 0d5828cb…, bumper-6s-16x9.mp4 7b32a40a… (+ .json). À committer : $SON/outils/
  espace_format.py (NOUVEAU), son/recettes/hybride-16x9.json, son/hybride-16x9/ (mix, stems, mesures), showcase-iphone/OUTILS.md,
  formats/empreintes-9x16.json, ce journal. Rien en prod, aucun commit, aucun Drive. /dev/shm/prenom/l16 purgé.
