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
2. **Appel à l'action précis** : verbe + ce qu'on va entendre, bouton à angles droits (charte), « vokio.fr » à 36 px.
3. **Rien sous 36 px, contraste AA, une info à la fois** : étiquette du camp, « Message d'accueil », « B I P », « vokio.fr » et mention à 36 px ; mention remontée de y = 1806 à y = 1456 (hors interface Reels) ; le message du répondeur sort avant le verdict. `hf check` : 62/62 textes au contraste AA.

### Textes changés (avant → après, raison)
- « Le même appel, déjà traité. » → « Le même appel, intervention déjà calée. » · « traité » ne dit pas ce qui a été fait ; « intervention calée » est le mot exact de la fiche affichée dessous, aucun fait ajouté.
- « Entendez-le vous-même » → « Appelez notre plombier fictif » · un appel à l'action commence par le geste (appeler, l'objectif de la campagne) et annonce l'établissement fictif, règle Vokio « dire ce que la personne va entendre ».
- « Établissement de démonstration, données fictives · captures réelles de app.vokio.fr » → « Établissement fictif · captures réelles de app.vokio.fr » · version courte pour tenir sur une ligne à 36 px, « fictif » conservé.

Tous les autres textes sont inchangés, mot pour mot.
