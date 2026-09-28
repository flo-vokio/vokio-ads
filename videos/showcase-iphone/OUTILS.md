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
- **Entrées figées** tant que l'équipe son n'a pas commité `son/dialogue.json` : ajouter `--entrees git:aa4dd24` à
  `format.py` et à `verifier_scene.py`.

## 1. Formats et mise en page

| Besoin | Commande |
|---|---|
| Voir la mise en page résolue d'un format (contrôlée) | `python3 outils/mise_en_page.py 16x9` |
| Lister les variantes d'une scène | `python3 outils/variante.py s6-sms` |
| Créer ou modifier une variante sans éditer le JSON | `python3 outils/variante.py s6-sms 16x9-haut --poser telephone.x0=770 telephone.haut=20 --note "pourquoi"` |
| Adopter une variante (elle devient l'entrée du format) | `python3 outils/adopter_variante.py s6-sms 16x9-haut` (essai), puis la même commande avec `--go` |
| Retirer une variante | `python3 outils/variante.py s6-sms 16x9-haut --retirer` |
| Construire le projet d'un format | `python3 outils/format.py 16x9 --entrees git:aa4dd24 --check --planche --vues 852,393` |
| Essayer une variante dans une copie jetable | `python3 outils/format.py 16x9 --variante s6-sms=16x9-haut --dossier /dev/shm/v --entrees git:aa4dd24 --check --planche` |
| Obtenir la fiche mesurée d'un format (le storyboard écrit) | `python3 outils/fiche_format.py formats/16x9 --9x16 .` |

Où sont les réglages :
- `mise-en-page/formats.json` : cadre, zones sûres, `corps_min`, `marge_laterale`, `passer_s`, `marge_zones`, `occupation` ;
- `texte.json` : sous-titres et mention ;
- `s1-sonnerie.json` : accroche et relance ;
- `s3-ecoute.json` : place d'écoute du point ;
- `agenda.json` : l'objet agenda de s4 et s5 ;
- `s6-sms.json` : l'iPhone, l'écart du point, l'arc de départ ;
- `s7-signature.json` : wordmark, promesse, offre.

Deux contraintes structurelles à connaître avant de proposer de « tout agrandir » :
- **Le wordmark ne grandit pas.** Son point de ı EST le point du film (0,11 em de 400 px, soit 44 px, le même disque de s1 à s7).
- **L'accroche reste plus étroite que le wordmark** (contrôle F7).

## 2. Données du film (construire)

L'ordre de reconstruction est : `son/dialogue.py` → `outils/mots.py` → `outils/preparer_agenda.py` → `outils/construire.py`.

| Besoin | Commande |
|---|---|
| Reconstruire les données du 9:16 (ce projet) | `python3 outils/construire.py` |
| Reconstruire les données d'un format | passer par `format.py`, qui appelle `preparer_agenda.py --format` puis `construire.py --format --racine` |
| Recaler les mots du dialogue (temps film) | `python3 outils/mots.py` |
| Mesurer dans Chromium (point de s1, #mot-pt de s7, pages) | `/root/.pwtest/bin/python outils/navigateur.py geometrie` |

## 3. Vérifier une retouche (du plus rapide au plus complet)

| Besoin | Commande | Durée |
|---|---|---|
| Règles de Florian sur le DOM : ≤ 3 éléments, corps, zones, marges, mono | `python3 outils/controle_format.py formats/16x9 --pas 3` | 10 s |
| Départ du point vers le stylo (s6 → s7), et balayage de son arc | `python3 outils/depart_point.py formats/16x9 --balayer=-80:80:10,0:240:10 --pas-max 101` | 2 s |
| Le point touche-t-il un texte ? | `/root/.pwtest/bin/python outils/heurts.py formats/16x9 s6-sms --permis "s7-signature:*:*"` | 10 s |
| Raccords entre scènes (hors du point) | `python3 outils/raccords.py formats/16x9 --autour s6-sms` | 1 min |
| Contrôles internes des scènes (`window.__*Controle`) | `/root/.pwtest/bin/python outils/controles_internes.py formats/16x9` | 30 s |
| L'encre de « Vokıo » suit-elle la plume ? | `python3 outils/plume.py formats/16x9` | 1 min |
| Une garde de scène se déclenche-t-elle ? | `python3 outils/sonder_garde.py formats/16x9 --attendu "zone interdite" --poser format.marge_laterale=200` | 1 min |
| Zoom sur des images précises | `python3 outils/zoom.py formats/16x9 --images 1233-1240 --boite 380,300,1180,1000 --echelle 0.5 -o z.png` | 10 s |
| Planche d'une scène aux instants clés | `python3 outils/revue_scene.py planche formats/16x9 s6-sms --vues 852,393` | 30 s |
| Comparer deux mises en page en mouvement, avec le son | `python3 outils/extrait_mouvement.py formats/16x9=A /dev/shm/v=B --de 33.5 --a 42.3 --sortie /dev/shm/ab.mp4 --zones` | 2 min |
| Tout pour UNE scène, dans les deux formats | `python3 outils/verifier_scene.py s6-sms --dossier /dev/shm/vs --ref git:aa4dd24 --entrees git:aa4dd24` | 5 à 10 min |
| Contrôles complets d'un rendu | `python3 outils/controles.py $UP/le-point-sur-le-i-16x9-image.mp4 --racine formats/16x9 --mix $SON/son/hybride/mix-hybride.wav --check formats/16x9/rapports/check.json` | 15 min |
| Occupation du cadre, scène par scène | `python3 outils/occupation.py film.mp4 --racine formats/16x9` | 20 s |

Lire le rapport de `controles.py` :
- « Tous les contrôles passent » et « N point(s) À VALIDER » sont deux choses distinctes. Un point À VALIDER est une décision
  de Florian, pas un échec.
- Au 28/09, deux points sont À VALIDER : l'horodatage iOS à 11 pt, et Y2, le produit dit avant « Passer ».
- Sans `--racine`, les contrôles portent sur le 9:16.
- `--mix` désigne la bande son que le MP4 doit porter. Sans cette option, c'est `son/mix.wav`, la bande classique.

## 4. Rendu et preuves

| Besoin | Commande |
|---|---|
| Rendre un format avec une bande son | `python3 outils/rendre.py formats/16x9 -o $UP/le-point-sur-le-i-16x9-image.mp4 --son $SON/son/hybride/mix-hybride.wav` |
| Rendre avec la piste du projet | `python3 outils/rendre.py formats/16x9 -o film.mp4 --son-du-projet` |
| Planches de relecture d'un MP4, zones dessinées | `python3 outils/planche_mp4.py film.mp4 -o /dev/shm/rel --pas 0.5 --zones formats/16x9` |
| Prouver que le 9:16 n'a pas bougé (preuve de référence, 1 410 images sans perte, 3 min) | `python3 outils/format.py 9x16 --dossier /dev/shm/c9 --entrees git:aa4dd24 --empreinte formats/empreintes-9x16.json` |
| Même chose au MP4 près (décodé image par image) | `python3 outils/rendre.py /dev/shm/c9 -o /dev/shm/c9.mp4 --son-du-projet && python3 outils/comparer_mp4.py $UP/le-point-sur-le-i-iphone.mp4 /dev/shm/c9.mp4` |
| Chemin court sans MP4 (environ 145 instants) | `python3 outils/identite.py prouver /dev/shm/c9 aa4dd24` |
| Comparer deux dossiers de données, clé par clé | `python3 outils/identite.py donnees donnees/ /dev/shm/c9/donnees/` |
| Réempreindre le 9:16 (seulement après un changement VOULU et commité) | `python3 outils/identite.py empreindre . formats/empreintes-9x16.json` |

## 5. Son (dans `$SON`, `cd /opt/vokio-ads/videos/showcase`)

| Besoin | Commande |
|---|---|
| Recouper le dialogue du vrai appel (coupes dans le vrai blanc) | `python3 son/dialogue.py` |
| Refaire les stems amont de toutes les couches sur ce dialogue (idempotent) | `python3 son/stems_amont.py` (variante iphone ; `--variante classique`) |
| Mixer une recette : stems, master −14 LUFS, mesures, planches | `python3 outils/mixer.py son/recettes/hybride.json` |
| Voir une recette modèle commentée | `python3 outils/mixer.py --modele` |
| Prouver un défaut entendu : il est dans 1 et 2, pas dans 3 | `python3 outils/ausculter.py differentiel 1=a.wav 2=b.wav --sans 3=c.wav --de 0 --a 15` |
| Accepter un nouveau mix : ce qu'il a et qu'aucune version validée n'a | `python3 outils/ausculter.py contre H=nouveau.wav --sans 3=valide.wav --mots /opt/vokio-ads/videos/showcase-iphone/donnees/mots.json` |
| Chaque petit son émerge-t-il du mix ? | `python3 outils/ausculter.py reperes son/hybride/stems --cues son/cues.json --ref son/stems-amont/iphone` |
| Vérifier les sautes et les trous du fond hors des mots | `python3 outils/ausculter.py trous a.wav --de 0 --a 15 --mots …/donnees/mots.json` |
| Voir un spectrogramme avec son profil | `python3 outils/ausculter.py planche a.wav b.wav --de 9.7 --a 10.8 --png p.png` |
| Fabriquer le fond de ligne tiré du vrai appel | `python3 outils/fond_ligne.py SOURCE.wav --zones 11.92:12.05 74.92:75.09 --sortie fond.wav --duree 47` |
| Mixer la bande classique du 9:16 et la contrôler | `python3 son/mix.py && python3 son/controle_son.py`, dans `showcase-iphone/`. Ce mix est la référence de `controles.py` sans `--mix` |

Au 28/09, la bande son retenue est le mix **hybride** : `son/hybride/mix-hybride.wav` (md5 c6158daf…), recette
`son/recettes/hybride.json`, mesures `son/hybride/mesures-hybride.json`.

Elle est calée sur les données du **9:16** : pans et air du point suivent sa trajectoire iPhone, et la plume suit l'encre lue
dans la vidéo iPhone. Le 16:9 porte la même bande, comme le veut la règle « même bande son ». Un mix propre au 16:9 demanderait
une variante `16x9` dans `stems_amont.py` (VARIANTES : données et vidéo du format).

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

Films au 28/09 :
- `le-point-sur-le-i-final.mp4` : 9:16, mix hybride ;
- `le-point-sur-le-i-16x9-image.mp4` : 16:9, même mix hybride, flux audio identique à l'octet près à celui du 9:16 final.

## 7. Recettes

**Faire une variante de mise en page et la livrer (cinq commandes)**
1. `python3 outils/variante.py s7-signature 16x9-grand --poser offre.corps=56 offre.interligne=68 offre.top=741 --note "…"`
2. `python3 outils/format.py 16x9 --variante s7-signature=16x9-grand --dossier /dev/shm/v --entrees git:aa4dd24 --check --planche`,
   puis regarder `/dev/shm/v/snapshots/planche.png` et lancer `python3 outils/controle_format.py /dev/shm/v`.
3. `python3 outils/adopter_variante.py s7-signature 16x9-grand --go`, puis récrire les `_note` de l'entrée, qui décrivent la géométrie.
4. `python3 outils/format.py 16x9 --entrees git:aa4dd24 --check --planche --vues 852,393`, puis
   `python3 outils/rendre.py formats/16x9 -o $UP/le-point-sur-le-i-16x9-image.mp4 --son $SON/son/hybride/mix-hybride.wav`.
5. `python3 outils/controles.py $UP/le-point-sur-le-i-16x9-image.mp4 --racine formats/16x9 --mix $SON/son/hybride/mix-hybride.wav --check formats/16x9/rapports/check.json`,
   puis la preuve du 9:16 (§ 4).

**Déplacer l'iPhone de s6 sans casser le départ du point**
1. Changer `telephone.x0` et `telephone.haut` dans une variante.
2. Construire une copie.
3. Lancer `depart_point.py <copie> --balayer=-80:80:10,0:240:10 --pas-max 101`.
4. Poser le meilleur arc avec `variante.py … --poser depart_stylo_arc='{"dx": 40, "dy": 90}'`, puis reconstruire.
5. Vérifier avec controles.py : F4 (bulle), Z2 (≥ `marge_zones` des zones interdites) et F2 (pas maximal).

**Ouvrir un nouveau format (1:1 prévu)**
1. Compléter l'entrée `1x1` de `formats.json` : retirer `prevu`, puis donner les zones.
2. Ajouter une entrée `1x1` dans chaque fichier de `mise-en-page/`. `mise_en_page.py 1x1` dit laquelle manque.
3. Lancer `format.py 1x1 --check --planche`. Le rapport `a-parametrer.json` doit rester vide.
4. Lancer `controle_format.py`, puis le rendu et `controles.py --racine formats/1x1`.

**Changer la bande son d'un film livré sans re-rendre**
1. Lancer `python3 outils/livrer.py $UP/<film>-image.mp4 <nouveau mix.wav> -o $UP/<film>.mp4`.
2. Relancer `controles.py … --mix <nouveau mix.wav>` : A1 contrôle le calage, et A2 relit les mesures du mix. Le script
   cherche ces mesures dans le `mesures*.json` voisin dont « wav » désigne ce fichier.
