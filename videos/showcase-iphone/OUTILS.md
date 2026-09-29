# Boîte à outils du showcase « Le point sur le i » (mode d'emploi court)

Une commande par besoin. Le détail de chaque outil est dans son en-tête. Pour la liste à jour, lue dans ces en-têtes :
`python3 outils/index.py [motif]`.

Toutes les commandes se lancent depuis `/opt/vokio-ads/videos/showcase-iphone`, sauf mention contraire.
`SON=/opt/vokio-ads/videos/showcase` désigne le projet du son, `UP=/root/vokio-uploads/videos/showcase` les livrables.

## 0. Ce qu'il faut savoir avant de toucher à quoi que ce soit

- **Deux projets.** `showcase-iphone/` porte l'IMAGE : le 9:16, qui est la référence, et ses formats dans `formats/<f>/`.
  `showcase/son/` porte le SON : dialogue, stems, recettes, mixeur.
- **Le 9:16 ne bouge jamais sans preuve** (§ 4, « Prouver que le 9:16 n'a pas bougé »). Ce projet EST le 9:16.
- **`formats/<f>/` est généré.** On ne l'édite jamais. On édite `mise-en-page/*.json`, puis on relance `format.py`.
- **Même minutage dans tous les formats**, avec les mêmes événements et la même bande son. Seule la mise en page change.
- **Un seul rendu à la fois** sur le VPS : tout passe sous `flock /tmp/hf-rendu.lock`, que `rendre.py` et `zoom.py` prennent seuls.
- **Disque plein** (moins de 1,2 Gio libres) : `rendre.py` rend en mémoire (`/dev/shm`). Mettre les copies de travail dans
  `/dev/shm/<nom>`, jamais dans `/tmp`, qui est sur le disque.
- **Ne jamais lancer** `hf skills update` ni `audio.mjs sync-durations`.
- **Film de 50,07 s depuis l'échange du prénom (28/09)** : 1 502 images. Les entrées sont `son/dialogue.json` et
  `donnees/mots.json` COURANTS : plus de `--entrees git:aa4dd24` (le dialogue de 47 s n'a pas l'échange, `construire.py`
  le refuse). Les nombres en dur des outils et des scènes sont ceux du FILM DE BASE (47 s) : la règle des insertions
  (`son/dialogue.json` « insertions », `outils/temps.py`) les porte dans le film courant (+ 92 images dès l'image 758).
  `python3 outils/temps.py 941 36.6667` dit où tombe une image ou un instant du film de 47 s (§ 7, « Insérer du temps »).
  Un format se construit SANS `--entrees` : `format.py <f>` lit alors le dialogue et les mots de l'arbre de travail (c'est
  le chemin normal). `--entrees git:HEAD` fige ceux du dernier commit : ne l'utiliser qu'une fois le film de 50 s commité
  (HEAD = a6d3d8e = 47 s jusque-là, refusé). Même chose pour `verifier_scene.py` : `--entrees courant` avant ce commit.

## 1. Formats et mise en page

| Besoin | Commande |
|---|---|
| Voir la mise en page résolue d'un format (contrôlée) | `python3 outils/mise_en_page.py 16x9` |
| Lister les variantes d'une scène | `python3 outils/variante.py s6-sms` |
| Créer ou modifier une variante sans éditer le JSON | `python3 outils/variante.py s6-sms 16x9-haut --poser telephone.x0=770 telephone.haut=20 --note "pourquoi"` |
| Revenir, dans une variante, au défaut du 9:16 pour une clé (la clé est RETIRÉE à la fusion) | `python3 outils/variante.py s6-sms 16x9-x --poser telephone_monte=null` |
| Adopter une variante (elle devient l'entrée du format) | `python3 outils/adopter_variante.py s6-sms 16x9-haut` (essai), puis la même commande avec `--go` |
| Retirer une variante | `python3 outils/variante.py s6-sms 16x9-haut --retirer` |
| Construire le projet d'un format | `python3 outils/format.py 16x9 --check --planche --vues 852,393` |
| Essayer une variante dans une copie jetable | `python3 outils/format.py 16x9 --variante s6-sms=16x9-haut --dossier /dev/shm/v --check --planche` |
| Essayer un JEU de variantes (la variante de ce nom dans chaque fichier qui l'a : une recomposition entière) | `python3 outils/format.py 16x9 --variante '*=16x9-recompose' --dossier /dev/shm/v --check --planche` |
| Adopter un jeu (une commande par fichier) | `for s in texte s1-sonnerie s3-ecoute agenda s6-sms s7-signature; do python3 outils/adopter_variante.py $s 16x9-recompose --go; done` |
| Obtenir la fiche mesurée d'un format (le storyboard écrit) | `python3 outils/fiche_format.py formats/16x9 --9x16 /dev/shm/c9` (la référence doit être une copie du 9:16 construite par `format.py 9x16 --dossier /dev/shm/c9 …` : les données commitées du 9:16 n'ont pas DONNEES.geometrie.s1) |

Où sont les réglages :
- `mise-en-page/formats.json` : cadre, zones sûres, `corps_min`, `marge_laterale`, `passer_s`, `marge_zones`, `occupation` ;
- `texte.json` : sous-titres et mention ; « coupes » recoupe les lignes d'une page pour un format (mêmes mots, contrôlé ;
  16:9 : `s6-sms#1` en trois lignes, pour que le téléphone monte avec « Au revoir » sans croiser le sous-titre) ; le `x` de
  chaque style est libre (16:9 : l'appelant de s3 dans la colonne de droite, x 1000, champ-contrechamp) ;
- `s1-sonnerie.json` : accroche et relance ; « glisse » (`{"x_depart": "centre" | px, "t": [t0, t1], "ease"}`) pose l'accroche
  centrée puis la fait glisser à sa place avant la relance, le point (son « . ») avec elle (16:9 : 2,10 → 2,60) ;
- `s3-ecoute.json` : place d'écoute du point ;
- `agenda.json` : l'objet agenda de s4 et s5 ;
- `s6-sms.json` : l'iPhone, l'écart du point, l'arc de départ, la montée (`telephone_monte` : à éviter, le silence numérique
  doit rester un plan immobile, I2), la forme du premier geste depuis la gouttière des heures (`forme_depart_gouttiere`,
  « droit » par défaut ; 16:9 : « couloir », entre les étiquettes 09:00 et 10:00 de la capture, à `couloir_dy` px du milieu
  de leurs filets) ;
- `s7-signature.json` : wordmark, promesse, offre ; « une_ligne » pose les deux lignes de la promesse (ou de l'offre) côte à côte ;
  « bond » règle la hauteur du bond sur le ı (px du 9:16, défaut 110).

Trois échelles par format, relatives au 9:16 (`outils/mise_en_page.py`, recomposition du 28/09) :
- **Le disque du film de s1 à s6** : `formats.json` « echelle_point », 1 par défaut (44 px). L'agenda de s4-s5 est la vraie
  capture à 1:1 : sa gouttière des heures (65,6 px entre les étiquettes et la colonne) est faite pour 44 px. Un format qui grossit
  le disque doit aussi grossir l'agenda.
- **Le wordmark et son point de ı** : corps de s7 / 400. Le 16:9 le passe à 480 px depuis la 3e passe (point de ı de 52,8 px ;
  540 avant, 59,4 px, qui tassait le plan final ; à 600, le bond du 9:16 sortait du cadre) : le point grandit de 20 % en
  quittant le téléphone (41,00 → 41,50, DONNEES.point.taille), et le stylo, le bond et le diamètre final suivent. DONNEES.point
  porte alors `diametre_disque` (taille CSS de #point, la plus grande) et `diametre_film` (le disque de s1 à s6) : les scènes
  lisent `diametre_film || diametre_disque` pour leur rayon.
- **Les vitesses** : la plus grande de ces échelles et du texte de s2 (corps / 72) ; construire.py (V_TRAJET, étirement) et
  controles.py D4 (pas maximal) la suivent.
Dans le 9:16 les trois valent 1 et ses données restent identiques à l'octet. Chromium dessine #point dans une boîte de px
entiers : `lib/point.js` pose la boîte à `POINT.boite` = round(D0) et calcule l'échelle sur elle (un point de ı de 59,391 px
sortait sinon à 59). **L'accroche reste plus étroite que le wordmark**
(contrôle F7) : agrandir l'une, c'est agrandir l'autre.

## 2. Données du film (construire)

L'ordre de reconstruction est : `son/dialogue.py` → `outils/mots.py` → `outils/preparer_agenda.py` → `outils/construire.py`.

| Besoin | Commande |
|---|---|
| Reconstruire les données du 9:16 (ce projet) | `python3 outils/construire.py` |
| Reconstruire les données d'un format | passer par `format.py`, qui appelle `preparer_agenda.py --format` puis `construire.py --format --racine` |
| Recaler les mots du dialogue (temps film) | `python3 outils/mots.py` |
| Où tombe, dans le film courant, une image ou un instant du film de 47 s (et l'inverse) | `python3 outils/temps.py 941 36.6667` · `python3 outils/temps.py --inverse 1033` · `python3 outils/temps.py` (plages) |
| Mesurer dans Chromium (point de s1, #mot-pt de s7, pages) | `/root/.pwtest/bin/python outils/navigateur.py geometrie` |

## 3. Vérifier une retouche (du plus rapide au plus complet)

| Besoin | Commande | Durée |
|---|---|---|
| Règles de Florian sur le DOM : ≤ 3 éléments, corps, zones, marges, mono, aucun sous-titre sur le téléphone (E6) | `python3 outils/controle_format.py formats/16x9 --pas 3` | 10 s |
| Départ du point vers le stylo (s6 → s7), et balayage de son arc | `python3 outils/depart_point.py formats/16x9 --balayer=-80:80:10,0:240:10 --pas-max 101 --json a.json` | 2 s |
| Choisir l'arc balayé le plus propre (coude ≤ 15°, puis Σ opacité × hors du contour, puis pas) | voir la recette « Déplacer l'iPhone de s6 » (§ 7) | 1 s |
| Le point touche-t-il un texte, ou une étiquette d'heure de la capture ? | `/root/.pwtest/bin/python outils/heurts.py formats/16x9 s6-sms --permis "s7-signature:*:*" [--marge 12]` | 10 s |
| Pourquoi le planificateur a choisi ce départ (départs rejetés : pas trop grand, heurt avec quel mot ou quelle étiquette) | `CONSTRUIRE_REJETS=1 python3 outils/construire.py --format 16x9 --racine /dev/shm/v --variante '*=…'` | 3 s |
| Raccords entre scènes (hors du point) | `python3 outils/raccords.py formats/16x9 --autour s6-sms` | 1 min |
| Contrôles internes des scènes (`window.__*Controle`) | `/root/.pwtest/bin/python outils/controles_internes.py formats/16x9` | 30 s |
| L'encre de « Vokıo » suit-elle la plume ? | `python3 outils/plume.py formats/16x9` | 1 min |
| Une garde de scène se déclenche-t-elle ? | `python3 outils/sonder_garde.py formats/16x9 --attendu "zone interdite" --poser format.marge_laterale=200` | 1 min |
| Zoom sur des images précises | `python3 outils/zoom.py formats/16x9 --images 1233-1240 --boite 380,300,1180,1000 --echelle 0.5 -o z.png` | 10 s |
| Planche d'une scène aux instants clés | `python3 outils/revue_scene.py planche formats/16x9 s6-sms --vues 852,393` | 30 s |
| Comparer deux mises en page en mouvement, avec le son | `python3 outils/extrait_mouvement.py formats/16x9=A /dev/shm/v=B --de 33.5 --a 42.3 --sortie /dev/shm/ab.mp4 --zones` | 2 min |
| Tout pour UNE scène, dans les deux formats | `python3 outils/verifier_scene.py s6-sms --dossier /dev/shm/vs --ref git:HEAD` (le dernier commit du film de 50 s) | 5 à 10 min |
| Contrôles complets d'un rendu | `python3 outils/controles.py $UP/le-point-sur-le-i-16x9-image.mp4 --racine formats/16x9 --mix $SON/son/hybride/mix-hybride.wav --check formats/16x9/rapports/check.json` | 15 min |
| Après une insertion de temps, les données d'un format = celles d'avant portées par la règle ? (clé par clé ; « restée à l'ancienne valeur » = un temps propre au format oublié) | `python3 outils/donnees_decalees.py git:a6d3d8e:videos/showcase-iphone/formats/16x9/donnees formats/16x9/donnees --voulu 758-800 --ignorer cle` | 5 s |
| Occupation du cadre, scène par scène et par fenêtre de temps (image pleine ET série : largeur médiane et 1er quartile, barycentres horizontal et vertical médians ; seuils de `formats.json` occupation.par_scene et .fenetres) | `python3 outils/occupation.py film.mp4 --racine formats/16x9` | 20 s |

Lire le rapport de `controles.py` :
- « Tous les contrôles passent » et « N point(s) À VALIDER » sont deux choses distinctes. Un point À VALIDER est une décision
  de Florian, pas un échec.
- Au 28/09 (soir) : l'horodatage iOS à 11 pt est VALIDÉ par Florian ; il n'est plus « À VALIDER » mais rapporté en
  `DOM2-derogation` (ok tant qu'il ne déborde pas de son objet) et dans `derogations_validees`. Reste À VALIDER : Y2, le
  produit dit avant « Passer » (16:9 seulement ; le 9:16 n'a pas de bouton « Passer »).
- I2 (plan immobile pendant le silence numérique) : strict depuis la 3e passe du 16:9. Un téléphone qui monte pendant le silence
  (`telephone_monte` qui le recoupe) fait ÉCHOUER I2, même si le point ne bouge pas (la preuve sans perte à la source reste
  rapportée pour information).
- Z2 : le point à l'arrêt et les objets qui portent l'info à ≥ `marge_zones` des zones interdites ; là où le point ATTEND
  (tenue ≥ 0,5 s), à ≥ `marge_point_arret` (formats.json, 16:9 : 60) des zones interdites et à ≥ `marge_zones` des zones de
  PRUDENCE (encart de l'annonceur, bande du haut).
- O1 juge chaque scène à pleine composition ET sur la durée, et des fenêtres de temps (`occupation.par_scene` : largeur_min,
  barycentre, hauteur_min, largeur_mediane_min, largeur_q1_min, barycentre_median, bary_y_median ; `occupation.fenetres` :
  {nom: {"t": [t0, t1], seuils…}}, 16:9 : l'accroche posée de 0 à 2,1 s, la voix seule s2 + s3). Les seuils se posent d'après la
  RÈGLE (plan centré 0,5 ± 0,05, acte équilibré 0,5 ± 0,15, ligne de lecture 0,45 ± 0,15), jamais juste sous la mesure ; la note
  `occupation._note` de formats.json les justifie.
- Y2 rapporte aussi la part d'encre de chaque image autour du bouton « Passer » (passer_s − 0,5 → + 0,2) : le plancher
  d'encre est une décision de minutage (coupe de s1), donc une information, pas un échec.
- F8 compare l'agente et l'appelant dans chaque acte (s2-s3 voix seule, s4-s6 à côté de l'objet), qui peuvent avoir leurs corps.
- Sans `--racine`, les contrôles portent sur le 9:16.
- `--mix` désigne la bande son que le MP4 doit porter. Sans cette option, c'est `son/mix.wav`, la bande classique.

## 4. Rendu et preuves

| Besoin | Commande |
|---|---|
| Rendre un format avec une bande son | `python3 outils/rendre.py formats/16x9 -o $UP/le-point-sur-le-i-16x9-image.mp4 --son $SON/son/hybride/mix-hybride.wav` |
| Rendre avec la piste du projet | `python3 outils/rendre.py formats/16x9 -o film.mp4 --son-du-projet` |
| Planches de relecture d'un MP4, zones dessinées | `python3 outils/planche_mp4.py film.mp4 -o /dev/shm/rel --pas 0.5 --zones formats/16x9` |
| Prouver que le 9:16 n'a pas bougé (preuve de référence, 1 502 images sans perte, 4 min) | `python3 outils/format.py 9x16 --dossier /dev/shm/c9 --empreinte formats/empreintes-9x16.json` |
| Même chose au MP4 près (décodé image par image) | `python3 outils/rendre.py /dev/shm/c9 -o /dev/shm/c9.mp4 --son-du-projet && python3 outils/comparer_mp4.py $UP/le-point-sur-le-i-9x16-image.mp4 /dev/shm/c9.mp4` |
| Chemin court sans MP4 (environ 145 instants) | `python3 outils/identite.py prouver /dev/shm/c9 HEAD` |
| Prouver qu'une INSERTION de temps n'a décalé que ce qu'elle devait, sans perte (film de 47 s contre film courant) | `TMPDIR=/dev/shm/x python3 outils/identite.py empreindre . /dev/shm/x/courant.json` puis `python3 outils/identite.py comparer formats/empreintes-9x16-47s.json /dev/shm/x/courant.json $(python3 outils/temps.py --decalages) --voulu 758-800` |
| Même chose au MP4 près, contre le film livré de 47 s | `python3 outils/comparer_mp4.py $UP/versions-47s/le-point-sur-le-i-final.mp4 $UP/le-point-sur-le-i-9x16-image.mp4 $(python3 outils/temps.py --decalages) --voulu 758-800` |
| Prouver que le 16:9 n'a pas bougé (référence sans perte du 16:9 de 50,07 s, 28/09) | `python3 outils/format.py 16x9 --dossier /dev/shm/c16 --empreinte formats/empreintes-16x9.json` (ou `TMPDIR=/dev/shm/x python3 outils/identite.py empreindre formats/16x9 /dev/shm/x/b.json` puis `identite.py comparer formats/empreintes-16x9.json /dev/shm/x/b.json`) ; réempreindre après un changement VOULU : `identite.py empreindre formats/16x9 formats/empreintes-16x9.json` |
| Même chose après une INSERTION, pour un format (16:9), sans perte, contre le 16:9 de 47 s | `TMPDIR=/dev/shm/x python3 outils/identite.py empreindre formats/16x9 /dev/shm/x/b.json` puis `python3 outils/identite.py comparer formats/empreintes-16x9-47s.json /dev/shm/x/b.json $(python3 outils/temps.py --decalages) --voulu 758-800` (la référence de 47 s se refait par `identite.py extraire a6d3d8e /dev/shm/x/ref`, `cd /dev/shm/x/ref && python3 outils/format.py 16x9 --sans-construire`, puis `empreindre /dev/shm/x/ref/formats/16x9`) ; écarts chiffrés : `rendre.py … --crf 0` ou `empreindre … --garder a.mp4`, puis `comparer_mp4.py a.mp4 b.mp4 --decalage …` (PSNR, écart max par image) |
| Même chose au MP4 près, contre le 16:9 livré de 47 s | `python3 outils/comparer_mp4.py $UP/versions-47s/le-point-sur-le-i-16x9-image.mp4 $UP/le-point-sur-le-i-16x9-image.mp4 $(python3 outils/temps.py --decalages) --voulu 758-800` |
| Comparer deux dossiers de données, clé par clé | `python3 outils/identite.py donnees donnees/ /dev/shm/c9/donnees/` |
| Réempreindre le 9:16 (seulement après un changement VOULU et commité) | `python3 outils/identite.py empreindre . formats/empreintes-9x16.json` |

## 5. Son (dans `$SON`, `cd /opt/vokio-ads/videos/showcase`)

| Besoin | Commande |
|---|---|
| Recouper le dialogue du vrai appel (coupes dans le vrai blanc) | `python3 son/dialogue.py` (les DEUX copies, `$SON/son/` et `showcase-iphone/son/`, identiques ; code 1 si un bord dépasse une constante de l'image, CONTRAINTES_IMAGE lues dans le 9:16) |
| Le dialogue d'avant les insertions (film de 47 s, identique à l'octet à a6d3d8e) | `python3 son/dialogue.py --avant /dev/shm/ref` |
| Prouver qu'une insertion n'a décalé que ce qu'elle devait (extraits, mots, syllabes, wav à l'échantillon) | `python3 outils/verifier_insertion.py --ref git:a6d3d8e --wav-ref /dev/shm/ref/dialogue.wav` |
| La chaîne voix de mix.py seule (juger un mot réintégré avant de refaire les stems) | `python3 outils/chaine_voix.py -o /dev/shm/voix.wav` |
| Refaire les stems amont de toutes les couches sur ce dialogue (idempotent) | `python3 son/stems_amont.py` (variante iphone ; `--variante classique`) |
| La musique seule, sans la vidéo (+ couches de la partition et courbes de gain pour les preuves) | `python3 son/stems_amont.py --seulement musique [--couches /dev/shm/c]` |
| La règle des insertions de temps, pour tous (image, dialogue, musique, recettes) | `outils/chronologie.py` : `decaler`, `vers_base` (temps tenu dans la mesure insérée), `decaler_echantillon`, `inserer` ; lue dans `son/dialogue.json` « insertions » |
| Qu'un son généré redonne, après une insertion, le son validé DÉCALÉ (et non une autre réalisation) | `chronologie.texture(base, neuf)` pour une texture tirée sur la longueur du film (bruit, pièce, ligne, air : la base du film d'avant à l'octet, du neuf dans la mesure, fondus 50 ms ; appliqué au fond de ligne, à la pièce et à l'air du point) ; `vers_base_echantillon(i)` pour l'horloge d'un oscillateur (le vibreur de mix.py) ; `debuts_trames(n, pas, nfft)` pour une mesure faite par trames (la garde des repères : clé de recette `"insertions": "../dialogue.json"`). Sans insertion : l'identité, prouvée à l'octet sur le film de 47 s |
| Décaler toutes les fenêtres d'une recette du mixeur (idempotent : « insertions_appliquees ») | `python3 outils/inserer_temps.py recette son/recettes/hybride.json` |
| Un son du film d'avant dans le film actuel (silence dans la mesure insérée) | `python3 outils/inserer_temps.py wav ancien.wav nouveau.wav [--format f32]` ; dans une recette : `"references": {"nom": {"fichier": …, "insertions": "../dialogue.json"}}` |
| Des données provisoires du film actuel pour avancer le son avant l'image | `python3 outils/inserer_temps.py donnees donnees/ /dev/shm/donnees-prov` (construire.py fait foi) |
| Prouver qu'un son refait = l'ancien avant le pivot, = l'ancien décalé après, sans clic ni marche aux bords | `python3 outils/inserer_temps.py verifier nouveau.wav ancien.wav [--json r.json]` |
| Même preuve pour un MIX remasterisé (le gain de master change avec la durée) : au gain près, fenêtre par fenêtre | `python3 outils/inserer_temps.py verifier son/hybride/mix-hybride.wav $UP/versions-47s/point-solaire-bande-son-hybride.wav --compenser --par 1 --hors 24.9:31` (« au_gain_pres » : gain_db, résidu relatif par fenêtre, pires) |
| Refaire le MIX COMPLET du film d'avant avec le code actuel (non-régression à l'octet), puis comparer stem par stem | `python3 outils/bac_a_sable.py monter --commit a6d3d8e --dossier /dev/shm/x/base` → `… stems --dossier /dev/shm/x/base --video $UP/le-point-sur-le-i-iphone.mp4` (≈ 5 min, 2,1 Gio de mémoire : SEUL, jamais en parallèle d'un autre calcul lourd) → `… mixer --dossier /dev/shm/x/base --commit a6d3d8e` (redonne c6158daf…) → `… comparer /dev/shm/x/base/videos/showcase/son/stems-amont/iphone son/stems-amont/iphone --pas 1` (et `…/son/bac-hybride/stems son/hybride/stems`) |
| Refaire la musique du film d'AVANT une insertion avec le code actuel (non-régression), puis comparer couche par couche | `python3 outils/bac_a_sable.py monter --commit a6d3d8e --dossier /dev/shm/x/base` → `… musique --dossier /dev/shm/x/base --couches /dev/shm/x/bc` → `… comparer /dev/shm/x/bc /dev/shm/x/neuf --stems ancien.wav son/stems-amont/iphone/musique.wav` |
| Prouver que le son (`$SON/outils/chronologie.py`) et l'image (`outils/temps.py`) portent la même règle | `python3 outils/chronologie.py --verifier-image` (toutes les images et tous les 1/300 s, aller et retour, + une liste synthétique de 3 insertions ; code 1 au premier désaccord) |
| Mixer une recette : stems, master −14 LUFS, mesures, planches | `python3 outils/mixer.py son/recettes/hybride.json` |
| Fenêtres « miroir » d'un format tirées des données (où le format met le point du côté opposé au 9:16 ; bascules au passage du point du 9:16 par le milieu, fondu centré), comparées à la recette (code 1 si elles diffèrent), `--poser` pour les écrire | `python3 outils/espace_format.py fenetres --format /opt/vokio-ads/videos/showcase-iphone/formats/16x9/donnees/point-resolu.json --de 17.3 --a 34.416667 --recette son/recettes/hybride-16x9.json [--poser]` |
| D−G de chaque petit son contre le côté du point à l'image (contradiction : son à plus de 1 dB du mauvais côté, point à plus de 15 % du milieu ; code 1 s'il en reste), et D−G à des instants (touchers de l'agenda) | `python3 outils/espace_format.py mesurer son/hybride-16x9/stems --format …/formats/16x9/donnees/point-resolu.json --instants 20.667,21.433,22.2,24.367` |
| Voir une recette modèle commentée | `python3 outils/mixer.py --modele` |
| Prouver un défaut entendu : il est dans 1 et 2, pas dans 3 | `python3 outils/ausculter.py differentiel 1=a.wav 2=b.wav --sans 3=c.wav --de 0 --a 15` |
| Accepter un nouveau mix : ce qu'il a et qu'aucune version validée n'a | `python3 outils/ausculter.py contre H=nouveau.wav --sans 3=valide.wav --mots /opt/vokio-ads/videos/showcase-iphone/donnees/mots.json` |
| Chaque petit son émerge-t-il du mix ? | `python3 outils/ausculter.py reperes son/hybride/stems --cues son/cues.json --ref son/stems-amont/iphone` |
| Idem sur le film d'une insertion (repères du calcul amont, référence du 3 à ses propres fenêtres, trames alignées) | `python3 outils/ausculter.py reperes son/hybride/stems --cues son/stems-amont/iphone/cues-design.json --ref son/riche-design/stems --cues-ref son/riche-design/cues-design.json --insertions son/dialogue.json` (un repère absent de `--cues-ref`, né dans le film actuel, prend la cible par défaut : « sans réf. ») |
| Vérifier les sautes et les trous du fond hors des mots | `python3 outils/ausculter.py trous a.wav --de 0 --a 15 --mots …/donnees/mots.json` |
| Voir un spectrogramme avec son profil | `python3 outils/ausculter.py planche a.wav b.wav --de 9.7 --a 10.8 --png p.png` |
| Fabriquer le fond de ligne tiré du vrai appel | `python3 outils/fond_ligne.py SOURCE.wav --zones 11.92:12.05 74.92:75.09 --sortie fond.wav --duree 50.066667` (stems_amont.py l'appelle lui-même avec la durée et le raccroché des données) |
| Mixer la bande classique du 9:16 et la contrôler | `python3 son/mix.py --sans-copie /dev/shm/x && python3 son/controle_son.py`, dans `showcase-iphone/` (sans `--sans-copie`, mix.py réécrit `$UP/point-solaire-bande-son-v2.wav`, un livrable du 27/09). Ce mix est la référence de `controles.py` sans `--mix`, et la piste du projet HyperFrames (`assets/son/mix.wav`) |

Au 28/09 (soir, échange du prénom), la bande son retenue est le mix **hybride** de 50,066667 s : `son/hybride/mix-hybride.wav`
(md5 22274ae1…, 2 403 200 échantillons, −14,03 LUFS, −1,70 dBTP, LRA 7,0 ; celui de 47 s, c6158daf…, est dans
`$UP/versions-47s/`), recette `son/recettes/hybride.json`, mesures `son/hybride/mesures-hybride.json`, copie
`$UP/point-solaire-bande-son-hybride.wav` (la seule copie de la recette). Ce qui a changé : l'échange « Très bien. C'est pour
quel prénom ? » / « C'est pour Florian. » (25,47 → 28,79), le bruit de confort de l'appelant après « Florian. », la plume en deux
gestes (« 09:00 », puis « Florian » sous le nom), le la · sol qui signe le nom (28,693 · 28,933), une mesure de musique tenue.
Tout le reste est le mix validé : avant 25,27 s, identique au gain de master près (−0,040 dB : le master se règle sur la durée ;
résidu −91 dB, −60 dB autour du limiteur de 7,23 s) ; après la confirmation (31 → 50,07 s), identique DÉCALÉ de 147 200
échantillons au même gain près (résidu −61 à −88 dB ; aucune marche que le mix de 47 s n'a, `ausculter.py contre`). Preuves :
`$UP/controles-9x16/preuve-continuite-mix-hybride-47s-contre-50s.json`, `preuve-stems-*-47s-contre-50s.json`. Deux décisions
écrites dans la recette : la plume de « Florian » n'est pas remontée sous le nom dit (`par_repere` plume-nom, pose-plume-nom :
« exclu », avec la raison) ; la grille d'analyse de la garde suit l'insertion (`"insertions"`).

**La bande classique** (`showcase-iphone/son/mix.wav`, md5 d92ffe79…) a été refaite à 50,07 s le 28/09 pour la piste du
projet HyperFrames (`assets/son/mix.wav` : `hf check` ne signale plus d'audio de 47 s) et pour S1 de `controles.py` (ses stems
sfx et signature sont ceux du mix hybride). Elle n'est PAS livrable : `controle_son.py` passe tout sauf F (« pour » de 30,18 à
7,8 LU au-dessus de sa nappe de verre, qui n'est pas portée par la chronologie ; ≥ 10 exigés). Sa variante « monde » (47 s)
est rapportée périmée.

Elle est calée sur les données du **9:16** : pans et air du point suivent sa trajectoire iPhone, et la plume suit l'encre lue
dans la vidéo iPhone. Le 16:9 porte les mêmes stems, mixés par la recette dérivée `son/recettes/hybride-16x9.json` : petits sons
recentrés (mono) hors agenda, en miroir pendant l'agenda, là où le 16:9 met le point de l'autre côté (§ 7 YouTube,
`outils/espace_format.py`). Un mix propre au 16:9 (pans refaits sur sa trajectoire) demanderait une variante `16x9` dans
`stems_amont.py` (VARIANTES : données et vidéo du format).

**Attention.** `mixer.py --video … --mp4 …` réécrit la clé `mp4` des mesures de la recette. Pour un autre format, utiliser
`outils/livrer.py` (§ 6).

## 6. Livraison

| Besoin | Commande |
|---|---|
| Poser une bande son sur un MP4 déjà rendu : vidéo copiée, AAC 256k 48 kHz, sonie contrôlée | `python3 outils/livrer.py image.mp4 mix.wav -o film.mp4 [--json r.json] [--si-identique]` |
| Déposer sur le Drive de Florian | `python3 $SON/outils/mixer.py <recette> --drive "Vokio/…" --simuler`, puis la même commande sans `--simuler` |

Règles de livraison :
- −14 LUFS intégré, crête ≤ −1 dBTP, AAC 48 kHz stéréo, h264 à 30 i/s ;
- aucun lien public sur vokio.fr ;
- livrables dans `$UP`, contrôles dans `$UP/controles-<format>/` ;
- ni commit ni push depuis un sous-agent.

Films au 28/09 (fin de journée : l'échange du prénom, 50,07 s, 1 502 images) :
- `le-point-sur-le-i-final.mp4` (md5 cf1a76e1…) : LE FILM 9:16 de 50,07 s, l'image ci-dessous + le mix hybride de 50,07 s
  (`outils/livrer.py`, flux vidéo copié, AAC 256k : −14,1 LUFS, −1,7 dBTP) ; `controles.py … --mix $SON/son/hybride/mix-hybride.wav
  --check $UP/controles-9x16/check-hf.json` : 37 contrôles sur 37, aucun À VALIDER ; rapport, preuves du son et planches du mix
  (`son-planches/`, dont l'échange 24,5-31,5 s contre l'ancien décalé) dans `$UP/controles-9x16/` ;
- `le-point-sur-le-i-9x16-image.mp4` (md5 4b0849da…, 1 502 images) : le 9:16 de 50,07 s, IMAGE seule (sa piste provisoire
  est `son/dialogue.wav`, le vrai appel seul, au bon minutage) ;
- versions de 47 s gardées dans `$UP/versions-47s/` (`le-point-sur-le-i-final.mp4`, 16:9, bumpers, bandes son) ;
- `le-point-sur-le-i-16x9-image.mp4` (md5 4e73a607…, 1 502 images) : le 16:9 de 50,07 s, IMAGE seule, construit sur l'arbre de
  travail (`format.py 16x9 --check --planche`, sans `--entrees`) ; piste provisoire `son/dialogue.wav` (la piste du projet,
  `assets/son/mix.wav`, fait 50,07 s depuis le 28/09 au soir : la bande classique, non livrable) ; contrôles et
  preuves dans `$UP/controles-16x9/prenom/` ;
- `le-point-sur-le-i-16x9.mp4` (md5 0752b2b4…) : LE FILM 16:9 de 50,07 s, l'image ci-dessus + `$SON/son/hybride-16x9/mix-hybride-16x9.wav`
  (md5 05cde484…, −14,03 LUFS, −1,70 dBTP ; copie `$UP/point-solaire-bande-son-hybride-16x9.wav`) par `outils/livrer.py`
  (flux vidéo copié, −14,1 LUFS, −1,7 dBTP) ; `controles.py … --racine formats/16x9 --mix $SON/son/hybride-16x9/mix-hybride-16x9.wav
  --check formats/16x9/rapports/check.json` : tout passe, Y2 À VALIDER (inchangé) ; rapport, preuves du mix et des bumpers dans
  `$UP/controles-16x9/` (les contrôles du 16:9 de 47 s : `$UP/versions-47s/controles-16x9/`) ;
- `youtube/bumper-6s-9x16.mp4` et `youtube/bumper-6s-16x9.mp4` : 44,266667 → 50,066667 (§ 7 YouTube) ; couverture 16:9 et
  bannière inchangées (la couverture est l'image 49,966667 s du nouveau 16:9 au pixel près ; la bannière ne dépend d'aucun temps).

## 7. Recettes

**Insérer du temps dans le film (réplique réintégrée, plan allongé ; l'échange du prénom du 28/09)**
1. Son : une entrée dans `INSERTIONS` de `son/dialogue.py` (`{"id", "pivot_image", "images", "extraits"}`, pivot sur un temps
   de la grille de la musique, 23 images ; `images` = une mesure, 92, garde la musique sur la grille), les extraits réintégrés
   avec `"insertion": id` ; puis `python3 son/dialogue.py` dans les deux projets (copies identiques), `python3 outils/mots.py`
   (relevé Scribe complémentaire en cache), `python3 $SON/outils/verifier_insertion.py --ref git:<commit d'avant> …`.
2. Où tombe quoi : `python3 outils/temps.py` (plages), `python3 outils/temps.py 941 36.6667` (images ou instants du film de base).
3. Image : rien à décaler à la main. `construire.py` porte ses nombres du film de base par `B()` / `BI()` (hôtes de index.html
   compris : `poser_hotes`), les scènes par `TEXTE.decaler(n)`, `controles.py` par `BI` ; les temps de `mise-en-page/*.json`
   sont ceux du film COURANT (à porter à la main : `outils/temps.py 31.11`). Seule la scène que l'insertion COUPE demande un
   geste neuf, calé sur les nouveaux mots (modèle : `choregraphie_s5` de `construire.py`, et ses contrats dans
   `compositions/s5-rendez-vous.html`) ; les pages de sous-titres des nouvelles répliques s'ajoutent dans `outils/navigateur.py`
   PAGES, leurs sorties dans `par_page` de `construire.py` (clé : extrait, rang de départ), et une coupe propre à un format se
   recale sur le nouveau rang (`texte.json` « coupes »).
4. `python3 outils/preparer_agenda.py --sans-images` → `python3 outils/construire.py` → `/opt/vokio-ads/bin/hf check .` →
   `/root/.pwtest/bin/python outils/controles_internes.py .` → `python3 outils/controle_format.py . --pas 3` →
   `python3 outils/revue_scene.py planche . s5-rendez-vous --at 25.9,27.2,28.3,28.6,28.933333 --images /dev/shm/x/s5` (REGARDER).
5. Preuve, sans perte : `TMPDIR=/dev/shm/x python3 outils/identite.py empreindre . /dev/shm/x/courant.json`, puis
   `python3 outils/identite.py comparer formats/empreintes-9x16-47s.json /dev/shm/x/courant.json $(python3 outils/temps.py --decalages) --voulu 758-800`
   (les images d'avant la scène refaite : identiques ; celles d'après : identiques décalées ; les images insérées : à part).
   Au MP4 près : `python3 outils/comparer_mp4.py $UP/versions-47s/le-point-sur-le-i-final.mp4 <nouveau.mp4> $(python3 outils/temps.py --decalages) --voulu 758-800`.
   Au 28/09 (sans perte) : base 0-757 identiques (758/758) ; 801-1409 contre 893-1501 : 572 identiques, 37 à ≤ 25 niveaux sur
   quelques pixels (PSNR ≥ 71 dB : les instants décalés sont arrondis au µs, 92/30 s n'en est pas un nombre entier). Un mot pile
   sur une demi-image (« samedi », 29,45 s) s'arrondissait une image plus tard : `lib/texte.js` arrondit désormais un instant
   d'après l'insertion dans le film de base (versBase), à garder si on touche à TEXTE.image / aImage. Contre le MP4 livré (avec
   perte, GOP décalé) : PSNR ≥ 49 dB, ≤ 0,014 % de pixels à plus de 48 niveaux (le critère « chute » de 3 dB sous la médiane
   signale ces images : c'est le codec, la preuve est sans perte).
5 bis. Musique (dans `$SON`) : rien à décaler à la main. La partition (`son/riche-musique`) est écrite sur la grille du film de
   base et placée par `outils/chronologie.py` (tb(), arc tenu, notes tenues à phase entière dans la mesure insérée) ; un geste
   qui suit l'IMAGE et non la règle (le la · sol de la plume, `mix.py T["la_rdv"]`) se lit dans `evenements.json`. Puis
   `python3 outils/inserer_temps.py recette son/recettes/<r>.json` (chaque recette), `python3 son/stems_amont.py --seulement
   musique --couches /dev/shm/x/neuf`, puis le film d'avant : `python3 outils/bac_a_sable.py monter --commit <avant> --dossier
   /dev/shm/x/base` et `… musique --dossier /dev/shm/x/base --couches /dev/shm/x/bc` (il doit redonner à l'octet le stem
   validé), `… comparer /dev/shm/x/bc /dev/shm/x/neuf --stems <stem validé> son/stems-amont/iphone/musique.wav` et
   `python3 outils/inserer_temps.py verifier` (bords : clic, trou, marche). Au 28/09 : les 13
   couches identiques avant le pivot, 10 frappées identiques à l'octet après, résidu du stem 57 à 90 dB sous la musique (détecteurs de voix à blocs de 1 ms,
   instants au µs ; `prenom/preuve-musique.json` « reprise_verification »). Enfin `python3 outils/chronologie.py --verifier-image`.
6. Rendu : `python3 outils/rendre.py . -o $UP/le-point-sur-le-i-9x16-image.mp4 --son son/dialogue.wav --tmp shm` (1 502 images),
   puis le son (stems, mix) et `outils/livrer.py`.
6 bis. Son final (dans `$SON`, un calcul lourd à la fois : stems_amont ≈ 2,1 Gio) : `python3 son/stems_amont.py` (la plume lit
   la nouvelle vidéo) → `python3 outils/mixer.py son/recettes/hybride.json --planches /dev/shm/x` → preuves : `python3
   outils/inserer_temps.py verifier son/hybride/mix-hybride.wav $UP/versions-47s/point-solaire-bande-son-hybride.wav --compenser
   --hors 24.9:31`, `python3 outils/inserer_temps.py wav $UP/versions-47s/point-solaire-bande-son-hybride.wav /dev/shm/x/v47.wav`
   puis `python3 outils/ausculter.py contre H=son/hybride/mix-hybride.wav --sans V47=/dev/shm/x/v47.wav --de 29.24 --a 50.07
   --mots …/donnees/mots.json` (0 marche attendue hors de l'échange), stem par stem par `bac_a_sable.py stems / mixer / comparer`
   (§ 5) ; puis `outils/livrer.py $UP/le-point-sur-le-i-9x16-image.mp4 $SON/son/hybride/mix-hybride.wav -o
   $UP/le-point-sur-le-i-final.mp4 --json $UP/controles-9x16/livraison-final.json`, `hf check . --json` et `controles.py`
   (§ 3). Si une preuve montre un son « autre » après la mesure (pas le son validé décalé) : une texture, une horloge ou une
   grille de trames qui ne passe pas par la chronologie (§ 5, `texture`, `vers_base_echantillon`, `debuts_trames`).
7. Formats (le 16:9 du 28/09) : `python3 outils/format.py 16x9 --check --planche --vues 852,393` (sans `--entrees`), REGARDER la
   scène refaite dans le format (`revue_scene.py planche formats/16x9 s5-rendez-vous --at …`), `heurts.py formats/16x9 s5-rendez-vous`,
   `controle_format.py formats/16x9 --pas 1`, puis `donnees_decalees.py` (§ 3 : aucune valeur « restée à l'ancienne valeur »),
   le rendu (`rendre.py formats/16x9 -o $UP/le-point-sur-le-i-16x9-image.mp4 --son son/dialogue.wav --tmp shm`), `occupation.py`
   et les deux preuves du format (§ 4). Au 28/09 : aucune variante à retoucher, la chorégraphie de s5 tient dans le 16:9.
8. Son et livraison du format (dans `$SON`) : `python3 outils/inserer_temps.py recette son/recettes/hybride-16x9.json` (fenêtres
   décalées, idempotent), puis `python3 outils/espace_format.py fenetres --format …/formats/16x9/donnees/point-resolu.json --de 17.3
   --a 34.416667 --recette son/recettes/hybride-16x9.json` : une scène refaite peut mettre le point du MÊME côté dans les deux formats
   (au 28/09 : l'écriture de « Florian », 28,34 → 29,29), `--poser` coupe alors le miroir ; `python3 outils/mixer.py
   son/recettes/hybride-16x9.json --planches /dev/shm/x` (≈ 2,5 min, SEUL ; ses copies ne touchent pas le mix du 9:16 : md5
   avant/après), `espace_format.py mesurer son/hybride-16x9/stems …` (0 contradiction), `inserer_temps.py verifier
   son/hybride-16x9/mix-hybride-16x9.wav $UP/versions-47s/point-solaire-bande-son-hybride-16x9.wav --compenser --par 1 --hors 24.9:31` ;
   puis, dans ce projet, `python3 outils/format.py 16x9 --sans-construire --check` (la piste du projet du format suit
   `assets/son/mix.wav`, plus d'audio de 47 s), `outils/livrer.py $UP/le-point-sur-le-i-16x9-image.mp4
   $SON/son/hybride-16x9/mix-hybride-16x9.wav -o $UP/le-point-sur-le-i-16x9.mp4 --json $UP/controles-16x9/livraison-16x9.json`,
   `controles.py $UP/le-point-sur-le-i-16x9.mp4 $UP/controles-16x9 --racine formats/16x9 --mix $SON/son/hybride-16x9/mix-hybride-16x9.wav
   --check formats/16x9/rapports/check.json` et les bumpers (§ 7 YouTube).

**Faire une variante de mise en page et la livrer (cinq commandes)**
1. `python3 outils/variante.py s7-signature 16x9-grand --poser offre.corps=56 offre.interligne=68 offre.top=741 --note "…"`
2. `python3 outils/format.py 16x9 --variante s7-signature=16x9-grand --dossier /dev/shm/v --check --planche`,
   puis regarder `/dev/shm/v/snapshots/planche.png` et lancer `python3 outils/controle_format.py /dev/shm/v`.
3. `python3 outils/adopter_variante.py s7-signature 16x9-grand --go`, puis récrire les `_note` de l'entrée, qui décrivent la géométrie.
4. `python3 outils/format.py 16x9 --check --planche --vues 852,393`, puis
   `python3 outils/rendre.py formats/16x9 -o $UP/le-point-sur-le-i-16x9-image.mp4 --son $SON/son/hybride/mix-hybride.wav`.
5. `python3 outils/controles.py $UP/le-point-sur-le-i-16x9-image.mp4 --racine formats/16x9 --mix $SON/son/hybride/mix-hybride.wav --check formats/16x9/rapports/check.json`,
   puis la preuve du 9:16 (§ 4).

**Recomposer un format (la passe du 28/09 sur le 16:9)**
1. Poser un jeu de variantes du même nom dans chaque fichier concerné (`variante.py <fichier> 16x9-recompose --poser …`).
2. `format.py 16x9 --variante '*=16x9-recompose' --dossier /dev/shm/r --check`, puis des instantanés
   (`--sans-construire --snapshots t,t,… --images /dev/shm/r/sn`) ; recommencer jusqu'à la bonne image.
3. Rendre la copie (`rendre.py /dev/shm/r -o /dev/shm/r.mp4 --son …`), mesurer (`occupation.py /dev/shm/r.mp4 --racine /dev/shm/r`),
   fixer les seuils dans `formats.json` occupation.par_scene.
4. Balayer le départ vers le stylo (`depart_point.py /dev/shm/r --balayer=-160:200:10,-60:300:10 --json a.json`, puis choisir
   sous un coude maximal) et le poser dans la variante de s6.
5. Adopter le jeu (§ 1), réécrire les `_note` des entrées, reconstruire, rendre, `controles.py` sur les deux formats, preuve du 9:16.

**Déplacer l'iPhone de s6 sans casser le départ du point**
1. Changer `telephone.x0` et `telephone.haut` dans une variante.
2. Construire une copie.
3. Lancer `depart_point.py <copie> --balayer=-160:200:10,-60:300:10 --pas-max 101 --json /dev/shm/a.json`. Le tableau
   imprimé trie par Σ opacité × hors du contour et ne filtre pas le coude : garder les arcs sous un coude de 15°, par exemple
   `python3 -c "import json;L=[a for a in json.load(open('/dev/shm/a.json')) if a['bilan']['ecart_bulle_min']>=11 and a['bilan']['pas_max']<=101 and (a['bilan']['coude_max'] or 0)<=15];L.sort(key=lambda a:(a['bilan']['somme_o_hors'],a['bilan']['pas_max']));[print(a['arc'],a['bilan']) for a in L[:8]]"`.
4. Poser le meilleur arc avec `variante.py … --poser depart_stylo_arc='{"dx": 70, "dy": 90}'`, puis reconstruire.
5. Vérifier avec controles.py : F4 (bulle), Z2 (tenue ≥ `marge_point_arret` des zones interdites, ≥ `marge_zones` des
   zones de prudence) et F2 (pas maximal).

**Faire passer le point entre les étiquettes d'heure de la capture (3e passe du 16:9)**
Les heures « 09:00 », « 10:00 », « 11:00 » sont des pixels de la vraie capture : `construire.py` (etiquettes_capture) et
`heurts.py` les traitent comme des obstacles, qui montent et s'effacent avec l'agenda (agenda_sort). Si le premier geste de s6
les traverse :
1. `variante.py s6-sms 16x9-x --poser forme_depart_gouttiere=couloir couloir_dy=-40` (le couloir est au milieu des filets
   09:00 et 10:00 ; négatif = plus haut, l'agenda monte en sortant) ;
2. `CONSTRUIRE_REJETS=1 python3 outils/construire.py …` : départ choisi et départs rejetés (pas, heurt avec quelle étiquette) ;
   balayer couloir_dy et garder le départ le plus tôt (pas le plus petit) ;
3. `heurts.py <copie> s5-rendez-vous s6-sms --de 925 --a 950 --marge 12` : seule la tenue dans la gouttière (10,8 px de
   l'étiquette 09:00, voulue) doit rester.

**Ouvrir un nouveau format (1:1 prévu)**
1. Compléter l'entrée `1x1` de `formats.json` : retirer `prevu`, puis donner les zones.
2. Ajouter une entrée `1x1` dans chaque fichier de `mise-en-page/`. `mise_en_page.py 1x1` dit laquelle manque.
3. Lancer `format.py 1x1 --check --planche`. Le rapport `a-parametrer.json` doit rester vide.
4. Lancer `controle_format.py`, puis le rendu et `controles.py --racine formats/1x1`.

**Changer la bande son d'un film livré sans re-rendre**
1. Lancer `python3 outils/livrer.py $UP/<film>-image.mp4 <nouveau mix.wav> -o $UP/<film>.mp4`.
2. Relancer `controles.py … --mix <nouveau mix.wav>` : A1 contrôle le calage, et A2 relit les mesures du mix. Le script
   cherche ces mesures dans le `mesures*.json` voisin dont « wav » désigne ce fichier.

## 7. YouTube (28/09)

| Besoin | Commande |
|---|---|
| Bumper 6 s (ou teaser, boucle) tiré d'un film rendu, son compris, sans re-rendre : de 0,2 s avant la signature (s7) à la fin, soit `evenements.telephone_sortie.t[0] + 0.2` → `fin.t` ; film de 50,07 s : 44,266667 → 50,066667 (film de 47 s : 41,2 → 47) | `python3 outils/extrait.py $UP/le-point-sur-le-i-16x9.mp4 --de 44.266667 --a 50.066667 --duree 6 -o $UP/youtube/bumper-6s-16x9.mp4 --json $UP/youtube/bumper-6s-16x9.json` (9:16 : mêmes bornes depuis `$UP/le-point-sur-le-i-final.mp4`) ; `python3 outils/temps.py 41.2` porte une borne du film de base |
| Bannière d'accompagnement 300×60 (et aperçu ×2) | `python3 outils/banniere.py -o youtube/banniere-300x60.png` · `--echelle 2 -o youtube/banniere-600x120-apercu.png` |
| Textes de l'annonce Google Ads, longueurs vérifiées | `youtube/ANNONCE.md` |
| Bande son d'un format dont l'image contredit la spatialisation du 9:16 | recette dérivée avec `"mono": [[t0,t1],…]` ou `true` et `"miroir": [[t0,t1],…]` par piste (mixer.py) ; modèle : `$SON/son/recettes/hybride-16x9.json` (petits sons recentrés, miroir pendant l'agenda, où le point est à droite en 16:9). Les fenêtres « miroir » se tirent des données : `$SON/outils/espace_format.py fenetres … --recette … --poser`, puis `espace_format.py mesurer` sur les stems du mix (0 contradiction attendue) |

Films au 28/09 (soir, 50,07 s) : `le-point-sur-le-i-16x9.mp4` porte `son/hybride-16x9/mix-hybride-16x9.wav` : mono sur 0 → 17,3 et
34,416667 → 50,066667, miroir sur 17,3 → 28,311241 et 29,315115 → 34,416667 (touchers de l'agenda à droite : +4,1 / +3,2 / +3,4 /
+3,1 dB D−G, comme à 47 s). Entre les deux miroirs, l'écriture de « Florian » et le retour à la gouttière : les deux formats mettent
le point à droite, la plume reste donc telle quelle (+0,8 → +3,0 dB D−G ; le miroir d'un seul tenant l'aurait mise à gauche, −3 dB,
sous une plume à l'extrême droite). `espace_format.py mesurer` : 0 contradiction sur tout le film. Le 9:16 final garde
`mix-hybride.wav` (inchangé à l'octet par le mix du 16:9). Bumpers : mêmes 180 images que ceux du film de 47 s (PSNR ≥ 47 dB, codec),
même son (mix source identique à −56 dB au moins ; forme d'onde de l'AAC seule), −14,0 LUFS ; preuves :
`$UP/controles-16x9/comparer-bumpers-47s-contre-50s.json`, `preuve-continuite-mix-16x9-47s-contre-50s.json`, `espace-16x9-*.json`.

## 8. Version courte (pub Meta, 29/09)

| Besoin | Commande |
|---|---|
| Chercher des coupes possibles : bords dans un blanc du vrai appel ET longueur = mesures entières (92 images) | `python3 outils/court.py courts/9x16-court.json --verifier-seulement` (modifier « segments » et relancer ; code 1 si une coupe tombe dans un mot, n'est pas en mesures entières, ou si le texte dit n'est plus une sous-suite) |
| Construire le projet du format court (fin remontée : « vokio.fr » au-dessus de y 1250, sous la légende Reels) | `python3 outils/format.py 9x16 --variante s7-signature=9x16-court --variante s6-sms=9x16-court --dossier formats/9x16-court --check` |
| Rendre le long de ce format, sans perte | `python3 outils/rendre.py formats/9x16-court -o /dev/shm/c/longue.mp4 --son son/dialogue.wav --crf 0 --tmp shm` |
| Monter le court (image à l'image près, mix validé recoupé avec fondus de 50 ms, gain unique vers −14 LUFS, livrer.py, planche 1 i/s, table des coupes, mots au temps du court) | `python3 outils/court.py courts/9x16-court.json --image /dev/shm/c/longue.mp4` → `$UP/le-point-sur-le-i-court-9x16*.{mp4,wav,json,png}` |
| Écouter les coupes par la mesure | `python3 $SON/outils/ausculter.py trous $UP/le-point-sur-le-i-court-9x16-mix.wav --mots $UP/le-point-sur-le-i-court-9x16-mots.json` (comparer aux mêmes instants du long : ce qui existe déjà dans le long est hérité) |

Règles de la recette : la tête est libre (le court commence où l'on veut) ; chaque coupe interne retire k × 92 images, donc la
musique garde sa grille (même phase dans la mesure des deux côtés, la grosse caisse et le ré du logo retombent sur leurs temps) ;
seul l'accord peut changer au milieu d'une mesure (fondu de 50 ms). `controles.py` sur le court : les contrôles de minutage du
film long (D, S, V…) n'ont pas de sens après montage ; les contrôles de mise en page se jugent sur le LONG du format.
