# film-demo · ce qui change par rapport à l'original (monter.py, 21/09)

Une seule composition (`index.html`) pour les quatre métiers ; un fichier de données par métier
(`profils/<metier>.json`, écrit par `preparer.py` depuis `profils.py`, la source unique) ; rendu par
`./rendre.sh <metier>…`. Critique préalable de l'original : `CRITIQUE.md`.

- **Lisibilité sur téléphone (critique, reco 1).** Tout texte ajouté fait 36 px ou plus ; l'agenda est
  agrandi de 30 % (ses horaires passaient à ~31 px) ; la carte dépliée n'est plus réduite ; la mention
  passe de 21 à 36 px, l'état de la ligne de 26 à 36 px.
- **Contraste AA (reco 2).** État en ivoire (14,3:1 au lieu de 4,39:1), mention éclaircie (7,4:1 la nuit,
  5,2:1 au clair), « sans engagement » en italique encre au lieu de l'orange (2,99:1), rangées de contexte
  à 62 % au lieu de 38 %. Le solaire ne sert plus qu'à « l'agent agit », une fois par plan : le point de
  l'état, la chute des titres 1 et 4 (les titres 2 et 3 restent ivoire, leur capture porte déjà le
  solaire), le point du ı.
- **Une information à la fois, sans chrome factice (reco 3).** L'état de la ligne ne vit plus que dans
  l'ouverture (il restait 35 s en haut) ; l'impact montre ses deux cartes l'une après l'autre ; l'écran
  final passe de sept éléments simultanés à trois (les arguments défilent un par un dans la même place,
  puis prix, puis appel à l'action) ; le faux bouton est remplacé par une ligne typographique sous un filet.
- **Le mouvement dit ce que fait l'application.** Le texte monte de sous son masque, ligne par ligne
  (la phrase, puis sa chute) ; le nouvel appel entre en tête de liste et pousse les anciens d'une rangée ;
  la carte se déplie vers le bas au lieu d'être remplacée ; l'agenda glisse dans la journée ; la fin se lève
  par le bas comme le jour. Décélération power3 partout, aucun rebond ; ombres supprimées (filet 1 px),
  une seule lueur de fond très basse.
- **Numéros retirés des captures.** Le bloc « Rappeler 06 39 98 … » de la carte dépliée est coupé et la
  ligne-numéro de la rangée « Renseignement » est retirée, lignes restantes recentrées (précédent :
  `monter_appel_reel.py`). Rien n'est ajouté à l'image.
- **Textes changés** (tout le reste est mot pour mot) :
  - mention : « Établissement de démonstration, données fictives · captures réelles de app.vokio.fr »
    → « Établissement fictif, captures réelles de app.vokio.fr ». Raison : tenir sur une ligne à 36 px ;
    « de démonstration » et « données fictives » disaient deux fois la même chose, « fictif » reste.
  - appel à l'action : « Entendez-le vous-même » + « VOKIO.FR » (deux éléments) → « Entendez-le vous-même
    sur vokio.fr » (un seul). Raison ux-copy : le verbe d'origine, plus la destination ; une place libérée.
  - minutage : l'accroche arrive à 1,0 s au lieu de 1,5 s, pour être lue avant la fin de la 2e seconde.

## Retours de Florian du 24/09 (deuxième passe)
- **Agenda montré en entier, sans défilement, texte à 36 px** (méthode appel-reel-plombier, troisième
  passe). Plombier, vétérinaire, institut : la vraie capture est recollée sans les tranches horaires
  vides (`preparer.py`, `recoller_agenda`). Chaque rendez-vous garde son étiquette d'heure, les heures
  vides sont retirées et les étiquettes restantes montrent le saut (plombier : 12:00 puis 18:00). La
  marge droite vide, les onglets Jour/Semaine et l'aide du bas sont retirés, rien n'est ajouté. L'image
  est affichée à 1,1 fois la capture : le texte des rendez-vous (11 px dans l'application) fait 36,3 px.
  Pour tenir entre le titre et 1400 px, on descend un palier à la fois :
  - vétérinaire : une rangée vide gardée comme respiration entre 11 h 30 et 16 h ;
  - plombier : sans respiration, sinon la journée ne tient pas ;
  - institut : sans respiration, et les demi-heures vides au-dessus et au-dessous des rendez-vous sont
    retirées aussi. Ses étiquettes 11:00, 12:00 puis 14:00 sont donc plus serrées que l'heure pleine.
  Restaurant (dernière retouche, 24/09) : recadré sur 19 h à 23 h et sur les DEUX premières colonnes
  de réservations (M. Aubert, Mme Dumas, Mme Perrot), la troisième est hors cadre. Rien d'ajouté.
  Échelle 1,28 : texte des rendez-vous à 42,3 px (il était à ≈ 31 px, et non 37 comme annoncé à la
  deuxième passe, erreur de mesure : le texte fait 11 px dans l'application).
- **Arguments de fin : retour au principe de l'original.** Ils s'ajoutent un par un en liste, chacun
  avec son point solaire, puis la liste s'efface et laisse place au prix et à l'appel à l'action.
- **Résumé de l'appel en calque texte**, méthode de `monter_appel_reel.py` : la capture dépliée est
  coupée autour du paragraphe (haut, une rangée de fond, bas), le texte est réécrit en Geist 14 px ×
  2,586 (36,2 px), interligne 1,625, encre `#262019` à 80 %, largeur 274 pt comme dans l'application.
  Rien d'autre n'est retouché.
- **Résumés changés dans le film** (heure de l'appel contre jour du rendez-vous) :
  - plombier : « Intervention calée ce matin 8 h 30 » → « Intervention calée demain matin 8 h 30 ».
    L'appel est le dimanche 20 à 23:07, le rendez-vous le lundi 21 à 8 h 30 (visible dans l'agenda).
  - restaurant : « une table pour 4 samedi 20 h 30 » → « une table pour 4 mercredi 20 h 30 ».
    La réservation posée dans les données de démonstration est le mercredi.
  - vétérinaire et institut : inchangés, déjà cohérents (« demain 9 h » pour un appel à 22:14 la veille ;
    « jeudi 17 h » pour un appel du lundi).
- **Titres remplacés** (texte de Florian, source `profils.py` et `profils_institut.py`) :
  - vétérinaire t1 : « Personne ne raccroche, même après 20 heures. » → « Après 20 heures, la clinique répond encore. »
  - institut t1 : « Vous finissez le soin. L'appel est pris. » → « Pendant le soin, l'appel est pris. »
  - institut t4 : « À la fermeture, la semaine est pleine. » → « Vous fermez, et votre semaine est déjà réservée. »
  - restaurant t4 : « Au coup de feu suivant, la salle est déjà pleine. » → « Au service suivant, vos tables sont déjà réservées. »
  Un titre qui prendrait trois lignes voit son corps baisser jusqu'à tenir en deux (jamais sous 64 px) :
  c'est le cas de l'institut t4, autour de 74 px.
- **Source corrigée** (`/opt/vokio-site-repo/design/videos/ux-vertical/profils.py`, non committé) :
  chaque résumé nomme désormais le jour du rendez-vous réellement posé dans `rdv`. Plombier : Mme Bonnet
  (mardi 8 h), Mme Dumas (mercredi 15 h). Vétérinaire : M. Aubert (lundi 11 h 30), Mme Ferrer (lundi 10 h),
  M. Osman (mardi 14 h), Mme Teil (lundi 16 h), Mme Dumas (mardi 9 h 30). Restaurant : M. Chevalier
  (mercredi 20 h 30), Mme Perrot (demain 20 h), M. Marchal (mardi 20 h), M. Teil (mardi midi),
  Mme Fontaine (jeudi 20 h 30), M. Lambert (vendredi 19 h 30). Institut : rien à corriger.

## Écarts connus
- 30 i/s comme le demande le brief, alors que les originaux sont à 60 i/s.
- La mention reste à y = 1428 (une ligne, au-dessus de 1500 mais sous 1380) : plus haut, elle chevaucherait la carte dépliée.
- Agenda : restaurant à 42,3 px, les trois autres à 36,3 px. Le titre 4 du restaurant (« Au service suivant, vos tables
  sont déjà réservées. ») accompagne les cartes d'impact, pas l'agenda : il reste vrai (9 rendez-vous pris ce mois-ci).
- Restaurant : la rangée « Mme Perrot · Table pour 2 ce soir 21… » est une capture, non retouchée ; l'agenda
  montre Mme Perrot à 20:00. La source est corrigée (« demain 20 h »), l'image le sera à la prochaine capture.
- Restaurant : la table de M. Chevalier est le mercredi, l'agenda filmé est celui du lundi soir : le titre
  « Et elle apparaît dans le cahier du soir » n'y montre pas sa table.
- Plombier : la capture du film raconte M. Lefèvre à 23:07, mais l'appel n° 1 de `profils.py` est
  désormais celui de l'appel réel (M. Estève, 19:52). Une nouvelle capture du film plombier montrerait 19:52
  sous un film qui dit 23:07.
- Le glyphe de l'apostrophe du Geist embarqué est courbe (’), celui de la capture est droit (').
- Le linter signale 5 avertissements « nested_structure_needs_subcomposition » (présentation dans Studio) : la composition reste monolithique pour qu'un seul fichier de variables pilote tout le film.
