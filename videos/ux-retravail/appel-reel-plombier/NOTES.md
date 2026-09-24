# L'appel réel · plombier · retravail HyperFrames

- **Synchronisation intacte, par construction** : `construire.py` importe `COUPES`, `ECRITURE`
  et `film()` du script d'origine, recalcule les instants et s'arrête s'ils diffèrent d'un seul
  chiffre de ceux injectés dans l'index.html de l'original. L'écriture mot à mot est la même
  fonction du temps, pilotée par une horloge linéaire dans la timeline GSAP. La piste audio est
  celle de l'original, copiée sans réencodage.
- **Charte Plein Jour au lieu du fond sombre** : sol papier et halo solaire discret, texte 100 %
  encre (l'italique porte l'accent, plus la couleur), filets de 1 px au lieu des ombres. Le
  solaire ne sert plus qu'à l'agent qui agit : le curseur qui écrit, puis le point du i.
- **Lisible sur un téléphone** : carte élargie de 900 à 960 px (résumé à ~41 px), état et
  mention à 36 px, mention remontée de y = 1792 à y = 1404 (hors interface Reels). La bande
  « Voir la fiche client » est retirée de la capture (même geste que pour « Rappeler » : on
  recolle haut et bas, rien n'est ajouté) : un lien non touchable dans une vidéo trompe.
- **Mouvement** : chaque ligne de titre et chaque mot de l'ouverture sort de son propre masque
  (power3, sans rebond), la carte monte au lieu de glisser de 140 px, la pastille URGENCE se pose
  sans effet de ressort (0,88 → 1 au lieu de 0,6 → 1), l'agenda s'approche lentement du
  rendez-vous de M. Estève au lieu de défiler.
- **Fin à trois éléments** : mot Vokio, prix, une ligne d'action ; la pilule-bouton et l'adresse
  séparée sont fusionnées.
- **État sans capitales mono** : la carte réelle porte déjà « RÉSUMÉ DE L'APPEL » et « URGENCE »
  en mono ; l'état passe en Geist, casse normale (mêmes mots).

## Textes changés (avant → après, et pourquoi)

- Titre 6 : « Le lendemain, l'intervention est dans l'agenda. » → « Le lendemain,
  l'intervention est dans votre agenda. » Même fait ; c'est l'agenda du commerçant, les autres
  titres lui parlent déjà.
- Fin : « Entendez-le vous-même » (pilule) + « VOKIO.FR » (ligne à part) → « Entendez-le
  vous-même sur vokio.fr ». L'action nomme sa destination, et la fin passe de quatre à trois
  éléments.
- Mention : « Établissement fictif de démonstration, appel réel sur une ligne de démonstration »
  / « captures réelles de app.vokio.fr » → « Établissement fictif de démonstration. » / « Appel
  réel, captures réelles de app.vokio.fr ». Passée à 36 px, elle devait tenir sur deux lignes ;
  « ligne de démonstration » reste dit par l'état en tête d'écran pendant tout l'appel.
- Le résumé de la carte, les six autres titres, l'ouverture, le prix : inchangés.

## Contrôle de synchronisation (24/09)

`controle_synchro.py <original> <retravail>` repère le curseur dans les deux films à 123 instants
pris pendant l'écriture, et en déduit combien de mots sont écrits. Résultat dans
`controle_synchro.txt` : sur les 110 instants mesurables dans les deux films, tous sont dans la
tolérance d'une image (pire écart 0,60 image). Les 13 autres ne sont pas mesurables dans
l'original : son flou de mouvement dédouble le curseur quand il va vite. Cinq d'entre eux ont été
comparés à l'œil, image par image : le texte écrit est le même ; la pastille URGENCE apparaît à la même image (22,867 s et 23,0 s comparées). Piste audio : flux AAC identique
octet pour octet à l'original (même empreinte md5).
