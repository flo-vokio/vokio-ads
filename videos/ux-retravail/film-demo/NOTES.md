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

## Écarts connus
- 30 i/s comme le demande le brief, alors que les originaux sont à 60 i/s.
- La mention reste à y = 1428 (une ligne, au-dessus de 1500 mais sous 1380) : plus haut, elle chevaucherait la carte dépliée.
- Restaurant : l'agenda agrandi coupe la troisième colonne de réservations au bord droit (« M. F… 20:3… »). C'est le prix de la lisibilité, aucun autre métier n'est concerné.
- Le linter signale 5 avertissements « nested_structure_needs_subcomposition » (présentation dans Studio) : la composition reste monolithique pour qu'un seul fichier de variables pilote tout le film.
