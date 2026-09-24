# Le répondeur, ou Vokio · retravail HyperFrames

- **Papier Plein Jour au lieu du fond sombre.** Le film validé (vokio-promo) ne connaît aucun fond sombre ; l'opposition passe désormais par l'atmosphère : le répondeur sur papier nu, sans halo ni mouvement ambiant, Vokio sur un halo solaire qui naît derrière la fiche puis remonte derrière le mot final.
- **Une seule étiquette de camp qui bascule.** « Avec un répondeur » sort par le haut, « Avec Vokio » entre par le bas au même endroit, la pastille passe du gris au vert : même appel, deux issues, dit par un raccord plutôt que par deux écrans juxtaposés.
- **Le répondeur joue son message.** Le message d'accueil s'écrit mot à mot au rythme d'une voix, le bip est un trait de tonalité qui file puis se coupe, puis le message sort avant que le verdict n'entre à sa place (une info à la fois). Plus de carte sombre : une règle fine et du texte, et la mono capitale n'est plus utilisée que pour l'étiquette du camp.
- **Qui parle = typographie, une couleur par camp.** Le répondeur parle en Geist, le récit en Instrument Serif ; « Il appelle le suivant. » passe sur sa propre ligne en terracotta (la seule couleur négative du système), et le soleil n'apparaît qu'une fois par plan : le trait sous « intervention déjà calée. », puis le point du i.
- **La fiche réelle se déplie.** Capture d'origine (appel-1-ouvert.png), révélée de haut en bas puis poussée lentement (1 à 1,035) ; la ligne « Rappeler 06 39 98 01 42 » est retirée par découpe de l'image (aucun numéro à l'écran). Depuis la passe 2, la carte est recadrée (marges latérales et pied) et affichée à l'échelle 1:1 environ : le résumé passe de ~31 px à ~37 px, donc lisible sur un téléphone.
- **Mouvement.** Montées de mots par masque de ligne en power3.out (power4 pour l'heure), sorties en power3.in plus courtes que les entrées, aucun rebond ; les deux-points de 23:07 battent comme une horloge.

## Passe 2 (24/09) : critique design, accessibilité et rédaction

Détail dans CRITIQUE.md. Trois recommandations prioritaires, toutes appliquées :
1. **Fiche lisible** : capture recadrée et affichée à 1000 px de large (texte du résumé ~37 px au lieu de ~31), verdict rendu concret.
2. **Appel à l'action précis** : verbe + ce qu'on va entendre, bouton à angles droits (charte, annulé en passe 3), « vokio.fr » à 36 px.
3. **Rien sous 36 px, contraste AA, une info à la fois** : étiquette du camp, « Message d'accueil », « B I P », « vokio.fr » et mention à 36 px ; mention remontée de y = 1806 à y = 1456 (hors interface Reels) ; le message du répondeur sort avant le verdict. `hf check` : 62/62 textes au contraste AA.

### Textes changés (avant → après, raison)
- « Le même appel, déjà traité. » → « Le même appel, intervention déjà calée. » · « traité » ne dit pas ce qui a été fait ; « intervention calée » est le mot exact de la fiche affichée dessous, aucun fait ajouté.
- « Entendez-le vous-même » → « Appelez notre plombier fictif » · un appel à l'action commence par le geste (appeler, l'objectif de la campagne) et annonce l'établissement fictif, règle Vokio « dire ce que la personne va entendre ».
- « Établissement de démonstration, données fictives · captures réelles de app.vokio.fr » → « Établissement fictif · captures réelles de app.vokio.fr » · version courte pour tenir sur une ligne à 36 px, « fictif » conservé.

Tous les autres textes sont inchangés, mot pour mot.

## Passe 3 (24/09) : retours de Florian

- **Le répondeur ralenti pour se lire à voix haute** (0,3 s par mot + 1 s de tenue). Le message d'accueil s'écrit à 0,3 s par mot (3,8 à 8,6 s) et reste jusqu'à 10,1 s ; le bip entre à 8,8 s et tient 1,3 s ; « Il a raccroché. Il appelle le suivant. » (7 mots) entre à 10,55 s et reste jusqu'à 14,2 s (3,65 s pour 3,1 s demandées). Tout ce qui suit est décalé de 6,6 s, sans autre changement de rythme. **Durée : 20,8 s → 27,4 s.**
- **Le résumé de la fiche réécrit en calque texte sur la carte vide**, même méthode que appel-reel-plombier : `assets/captures/carte-vide.png` (le paragraphe effacé à la couleur du fond de la carte, rgb 239,236,227), puis le texte en HTML, police Geist, corps 42,35 px et interlignage 68,4 px relevés sur la capture (43,04 / 69,51 px à l'échelle affichée), couleur rgb(78,73,66) mesurée sur les glyphes. Avec le texte d'origine, le calque retombe sur les mêmes coupures de ligne que la capture, à 2 px près. Espaces insécables avant « : », dans « 8 h 30 » et dans « SMS de ».
- **Cohérence des dates vérifiée** : appel le dim. 20 sept. à 23:07 (le 20/09/2026 est bien un dimanche), durée 2 min, intervention le lendemain lundi à 8 h 30, SMS de confirmation envoyé ; l'ouverture « 23:07 » concorde. Le verdict « intervention déjà calée » reste juste.
- **Bouton d'appel en pilule bien arrondie** (border-radius 999px), à la demande de Florian, qui annule la consigne d'angles droits de la passe 2.

### Texte changé (passe 3)
- Résumé de la fiche : « Intervention calée ce matin 8 h 30 » → « Intervention calée demain matin 8 h 30 » · l'appel a lieu à 23:07, l'intervention est donc le lendemain matin ; « ce matin » était faux. Le reste du résumé est identique mot pour mot.
