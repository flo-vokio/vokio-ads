# 24 h chez Vokio (25/09) · v2 généraliste de « Une nuit chez Vokio »

Brief de Florian : nuit multi-métiers, 24 h sur 24, pub 20-25 s, muet (musique posée dans
l'app), horloge qui tourne, une capture par appel, fin logo + promesse + « Essayez-le vous-même ».

- **Récit** : 10:42 institut (mains prises) · 12:48 restaurant (coup de feu) · 22:14 vétérinaire
  (clinique fermée) · 23:07 plombier (vous dormez) · bilan « Chaque appel décroché. Chaque
  rendez-vous posé. » avec les quatre en-têtes du même jour · fin. 24,4 s.
- **Captures réelles, même jour** : les quatre espaces de démo ont été regarnis par
  `/root/vokio-deploy/24h-vokio-250926/garnir_24h.py --go` (appels filmés le jeu. 24 sept. aux
  heures du film), filmés par `plans.py`, puis remis comme profils.py (`--retour --go`).
  Les bruts sont dans assets/captures/<metier>-brut.png : **ne pas refilmer sans regarnir**.
- **preparer.py** coupe le filet, « Rappeler 06 … » et le lien (aucun numéro à l'écran), efface le
  paragraphe du résumé ; le texte est réécrit en HTML (Geist 42 / 68,25, rgb 78,73,66) pour
  souligner la phrase clé d'un trait solaire. Retours à la ligne vérifiés contre la capture ;
  le plombier a les siens forcés (l'app coupe « Intervention | calée »).
- **Aucun zoom sur les cartes** (leçon du répondeur : le texte remis en page sautille).
- **Horloge** : quatre bandes 0-9 ×3, chaque chiffre roule toujours vers l'avant.

## Passe 2 (26/09) : retours de Florian

« L'animation des rendez-vous n'est pas la plus réussie, trop de mouvement, on ne remarque pas
les détails. » Reprise fidèle à app.vokio.fr :
- **la ligne d'appel repliée d'abord** (vraie capture `appel-1`, avec son aperçu tronqué),
  qui entre calmement et se laisse lire ;
- **puis elle s'ouvre comme dans l'app** : chevron redessiné en SVG qui pivote de 180°,
  aperçu qui disparaît d'un coup (group-open:hidden, un fondu superposait les deux lignes),
  volet qui se déplie vers le bas en 0,8 s ;
- **le résumé s'écrit pendant l'ouverture**, mot à mot (0,045 s par mot), à l'intérieur du volet :
  le volet a fini avant le texte, l'œil se pose sur la fin de l'écriture ; puis le trait solaire.
- **Rythme** : 6 s par appel au lieu de 4 (1 à 2 s de lecture après le trait), film de 32,4 s.
- Captures `replie` refilmées le 26/09 avec le même regarnissage (garnir_24h.py), espaces remis.

## Passe 3 (26/09) : le cadre de la carte

- Coins carrés visibles : la capture d'un <details> embarque les coins arrondis de la carte parente. Le cadre est redessiné en CSS (rayon 48 px, bordure 3 px, échelle ×3 de .card-v) et la carte ENTIÈRE grandit à l'ouverture (hauteur animée), bordure comprise.
- En-tête plus sombre que le volet : c'était la teinte de survol (clic Playwright). Refilmé souris sortie ; même défaut corrigé dans app.vokio.fr sur mobile (survol collant iOS, /root/vokio-deploy/survol-appels-260926/).
- Captures refilmées le 26/09 : les fiches affichent ven. 25 sept. (même jour pour les quatre).
