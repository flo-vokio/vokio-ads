# Critique de l'ORIGINAL « Le répondeur, ou Vokio »

Objet : /root/vokio-uploads/videos/ux-210926/duel-plombier/repondeur-ou-vokio.mp4 (20,8 s, 1080x1920, 60 i/s, muet).
Contexte : publicité verticale pour une campagne Meta à objectif « Appels » ; public : artisans, lu sur téléphone, souvent sans le son.
Base de lecture : 1080 px de large = 390 pt sur un téléphone, donc un texte de moins de 36 px est illisible.
Images examinées : 0,5 · 1,8 · 4,0 · 6,5 · 9,2 · 12 · 14,5 · 16,5 · 19,5 s, plus la couverture.

## Design Critique : Le répondeur, ou Vokio

### Overall Impression
L'idée est forte et se comprend en deux secondes : 23:07, un client appelle, deux issues. Le plus gros manque est la preuve elle-même : la fiche de l'application, qui est l'argument central, est affichée trop petite pour être lue sur un téléphone, et elle montre un numéro.

### Usability
| Finding | Severity | Recommendation |
|---------|----------|----------------|
| Le texte de la fiche (résumé de l'appel) fait environ 31 px à l'écran : la preuve « déjà traité » ne se lit pas sur un téléphone | 🔴 Critical | Afficher la capture à l'échelle 1:1 ou plus (texte à 36 px ou plus), recadrée sur la carte |
| La fiche affiche « Rappeler 06 39 98 01 42 » : un numéro à l'écran, interdit par la charte, qui en plus pousse à composer un numéro fictif | 🔴 Critical | Retirer la ligne de la capture (déjà fait en passe 1) |
| L'appel à l'action « Entendez-le vous-même » : on ne sait pas quoi faire (entendre quoi ? comment ?) ni ce qu'on va entendre | 🟡 Moderate | Un verbe d'action qui décrit le geste et annonce l'établissement fictif : « Appelez notre plombier fictif » |
| La mention « Établissement de démonstration, données fictives… » est à 21 px et à y = 1806, sous l'interface de Reels et TikTok : invisible en diffusion, alors qu'elle est la condition de conformité | 🟡 Moderate | La remonter au-dessus de y = 1500, à 36 px, en version courte qui garde « fictif » |
| « Le même appel, déjà traité. » reste abstrait : « traité » ne dit pas ce qui a été fait | 🟢 Minor | Reprendre le mot de la fiche elle-même : « intervention déjà calée » |

### Visual Hierarchy
- **What draws the eye first** : « 23:07 » en très grand, puis la carte du répondeur. C'est juste, l'heure installe la nuit.
- **Reading flow** : haut vers bas, sans conflit. Sur l'écran du répondeur, le verdict tombe pendant que le message reste affiché : deux informations en même temps, et l'œil revient à la carte au lieu de lire le verdict.
- **Emphasis** : trois capitales mono sur un seul écran (AVEC UN RÉPONDEUR, MESSAGE D'ACCUEIL, B I P), ce qui écrase la hiérarchie des étiquettes. Sur l'écran Vokio, la fiche est bien mise en avant, mais sa taille la dessert.

### Consistency
| Element | Issue | Recommendation |
|---------|-------|----------------|
| Fond | Fond sombre, alors que le film validé en Plein Jour interdit « aucun fond sombre nulle part » | Papier #F4F1E8 partout, écran final compris |
| Couleur solaire | Utilisée à la fois pour les deux-points de 23:07, pour « Il appelle le suivant. » (échec) et pour « déjà traité. » (succès) : le soleil veut dire « l'agent agit », il ne peut pas marquer l'échec | Soleil réservé à Vokio (une fois par plan) ; l'échec en terracotta #C0452C |
| Mono capitales | Trois usages sur l'écran du répondeur | Un seul usage par écran (l'étiquette du camp) |
| Bouton final | Pilule arrondie, alors que la charte demande 0 arrondi | Rectangle à angles droits |
| Étiquettes | « AVEC UN RÉPONDEUR » et « AVEC VOKIO » sont deux éléments distincts, alors qu'ils disent la même chose | Une seule étiquette qui bascule d'une issue à l'autre |

### Accessibility
- **Color contrast** : voir le tableau ci-dessous. Deux échecs : les gris « pierre » sur la carte sombre (3,43:1) et le « même quand vous ne pouvez pas » orange sur ivoire (2,99:1).
- **Touch targets** : sans objet, c'est une vidéo. Le bouton peint à l'écran ne se touche pas, il renvoie au bouton de la publicité.
- **Text readability** : sous le seuil de 36 px, on trouve l'étiquette du camp (28), « Message d'accueil » (24), « B I P » (30), le texte de la fiche (~31), « vokio.fr » (28) et la mention (21).

### What Works Well
- Le récit « même appel, deux issues » se suit sans le son, et la durée est juste pour une publicité.
- La preuve vient d'une vraie capture de app.vokio.fr, pas d'une interface inventée.
- Le verdict « Il a raccroché. Il appelle le suivant. » est court, concret, et dit ce que coûte le répondeur.

### Priority Recommendations
1. **Rendre la fiche lisible** : c'est la preuve du film. Capture recadrée sur la carte et affichée à l'échelle 1:1 environ (texte à 36 px ou plus), plus un verdict qui reprend le mot de la fiche : « Le même appel, intervention déjà calée. »
2. **Un appel à l'action qui dit quoi faire et ce qu'on va entendre** : « Appelez notre plombier fictif », dans un bouton à angles droits, avec « vokio.fr » à 36 px.
3. **Aucun texte sous 36 px, contraste AA, une info à la fois** : étiquettes à 36 px, un seul usage mono par écran, mention « fictif » remontée au-dessus de y = 1500 à 36 px ; le message du répondeur sort avant que le verdict n'entre.

## Accessibility Audit : Le répondeur, ou Vokio
**Standard :** WCAG 2.1 AA | **Date :** 24/09/2026

### Summary
**Issues found :** 6 | **Critical :** 1 | **Major :** 3 | **Minor :** 2

### Findings

#### Perceivable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 1 | Texte de la fiche à ~31 px, illisible sur un téléphone | 1.4.4 Resize text (lecture mobile) | 🔴 Critical | Capture à 1:1 environ, texte à 36 px ou plus |
| 2 | Mention à 21 px sous y = 1500, masquée par l'interface de Reels | 1.4.4 / 1.3.1 | 🟡 Major | Remonter à y < 1500, 36 px |
| 3 | « Message d'accueil » et « B I P » en #8A857C sur #3B3226 : 3,43:1 pour du texte de 24 et 30 px | 1.4.3 Contrast | 🟡 Major | Passer à 4,5:1 minimum (#6F695F sur papier : 4,81:1) |
| 4 | « même quand vous ne pouvez pas. » #E5701F sur #FBF9F2 : 2,99:1, sous le seuil de 3:1 pour du grand texte | 1.4.3 Contrast | 🟡 Major | Encre #262019 en italique (14,27:1) |
| 5 | « vokio.fr » à 28 px, #8A857C sur #FBF9F2 : 3,48:1 | 1.4.3 Contrast | 🟢 Minor | 36 px et #6F695F (4,81:1) |

#### Operable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| · | Sans objet : vidéo sans interaction ; le seul geste est le bouton natif de la publicité | 2.1.1 | · | · |

#### Understandable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 6 | L'appel à l'action ne dit pas quelle action faire | 3.3.2 Labels or instructions | 🟢 Minor | « Appelez notre plombier fictif » |

#### Robust
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| · | Sans objet (fichier vidéo). Le texte de la publicité Meta doit reprendre le message, pour les lecteurs d'écran | 1.1.1 | · | Prévoir une légende de publication qui dit le récit |

### Color Contrast Check
| Element | Foreground | Background | Ratio | Required | Pass? |
|---------|-----------|------------|-------|----------|-------|
| 23:07, verdicts | #F4F1E8 | #262019 | 14,27:1 | 3:1 | ✅ |
| « Il appelle le suivant. » | #EFA424 | #262019 | 7,68:1 | 3:1 | ✅ |
| Étiquette du camp (texte) | #F4F1E8 | #262019 | 14,27:1 | 4.5:1 | ✅ |
| Message d'accueil (citation) | #CFC9BC | #3B3226 | 7,62:1 | 4.5:1 | ✅ |
| « Message d'accueil », « B I P » | #8A857C | #3B3226 | 3,43:1 | 4.5:1 | ❌ |
| Mention (écrans sombres) | #8A857C | #262019 | 4,39:1 | 4.5:1 | ❌ |
| Mention (écran final) | #8A857C | #FBF9F2 | 3,48:1 | 4.5:1 | ❌ |
| « même quand vous ne pouvez pas. » | #E5701F | #FBF9F2 | 2,99:1 | 3:1 | ❌ |
| « vokio.fr » | #8A857C | #FBF9F2 | 3,48:1 | 4.5:1 | ❌ |
| Bouton | #F4F1E8 | #262019 | 14,27:1 | 4.5:1 | ✅ |
| Fiche : résumé (capture) | #4A453D | #EFECE3 | 8,04:1 | 4.5:1 | ✅ |

### Keyboard Navigation
Sans objet (vidéo).

### Screen Reader
| Element | Announced As | Issue |
|---------|-------------|-------|
| Vidéo entière | Rien : le texte est incrusté dans l'image | La légende de publication doit porter le message |

### Priority Fixes
1. **Fiche lisible** : touche tout le monde sur téléphone, et c'est la preuve du film.
2. **Contrastes et tailles au seuil** (36 px, 4,5:1) : améliore la lecture sans le son, pour tous.
3. **Mention remontée au-dessus de l'interface de Reels** : la conformité « fictif » doit pouvoir se lire.

## UX Copy : textes affichés et appel à l'action

### Recommended Copy
**Ouverture** : « 23:07 » · « Un client appelle. » (inchangé, clair et concret)
**Étiquettes** : « Avec un répondeur » · « Avec Vokio » (inchangé)
**Message du répondeur** : « Message d'accueil » · « « Bonjour, je ne suis pas disponible pour le moment, je vous rappellerai dès que possible. » » · « B I P » (inchangé : c'est le vrai message que tout le monde reconnaît)
**Verdict 1** : « Il a raccroché. Il appelle le suivant. » (inchangé : dit la perte sans chiffre)
**Verdict 2** : « Le même appel, intervention déjà calée. » (au lieu de « déjà traité. »)
**Signature** : « Votre ligne répond même quand vous ne pouvez pas. » (inchangé)
**Appel à l'action** : « Appelez notre plombier fictif » (au lieu de « Entendez-le vous-même »)
**Mention** : « Établissement fictif · captures réelles de app.vokio.fr » (au lieu de « Établissement de démonstration, données fictives · captures réelles de app.vokio.fr »)

### Alternatives
| Option | Copy | Tone | Best For |
|--------|------|------|----------|
| A | Appelez notre plombier fictif | direct, honnête | campagne « Appels » : annonce ce qu'on va entendre (règle Vokio) |
| B | Écoutez-la répondre | curiosité | diffusion organique, sans bouton d'appel |
| C | Entendez-le vous-même | original | à éviter : ni le geste ni l'objet ne sont dits |

| Option | Verdict 2 | Tone | Best For |
|--------|-----------|------|----------|
| A | Le même appel, intervention déjà calée. | concret | reprend le mot exact de la fiche affichée juste en dessous |
| B | Le même appel, déjà traité. | original | abstrait : « traité » ne dit pas ce qui a été fait |

### Rationale
Le film est vu sans le son et en moins de vingt secondes. Chaque texte doit dire un fait que l'image confirme. « Intervention déjà calée » est le terme exact de la fiche (« Intervention calée ce matin 8 h 30 ») : même mot pour la même chose, aucun fait ajouté. L'appel à l'action commence par un verbe, décrit le geste réel de la campagne (appeler) et annonce l'établissement fictif, comme le veut la règle de Florian (toujours dire ce que la personne va entendre). La mention raccourcie garde « fictif » et tient à 36 px sur une ligne.

### Localization Notes
Vouvoiement partout. « Calée » est familier et courant chez les artisans (un rendez-vous calé) ; il vient de la fiche du produit. Pour une autre verticale, « plombier » et « intervention » suivent le lexique du métier (voir vokio-ads/README, le lexique par phrases entières).
