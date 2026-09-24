# Critique de l'original · « L'appel réel » plombier

Film examiné : /root/vokio-uploads/videos/ux-210926/appel-reel-plombier/appel-reel-plombier.mp4
(75,18 s, 1080x1920, 60 i/s, AAC mono 16 kHz). Onze images extraites à 1 · 3 · 9,5 · 23,5 · 33 ·
44,5 · 58 · 64 · 67 · 70,5 · 74 s. Lecture sur téléphone : 1080 px = 390 pt, donc tout texte
sous 36 px est illisible.

Hors du périmètre des recommandations, par consigne : le texte du résumé qui s'écrit mot à mot
(il colle à l'enregistrement) et la synchronisation.

## Design Critique : L'appel réel (plombier)

### Overall Impression
Le concept est le plus fort de la série : on entend un vrai appel pendant que la vraie carte se
remplit, la preuve et la démonstration dans le même plan. Le gros levier est la lisibilité sur
téléphone : la moitié des textes secondaires sont trop petits, et la fin empile quatre éléments,
dont un bouton qu'on ne peut pas toucher.

### Usability
| Finding | Severity | Recommendation |
|---------|----------|----------------|
| Le lien « Voir la fiche client → » de la capture a l'air cliquable, dans une vidéo où rien ne l'est | 🟡 Moderate | Retirer la bande de la capture, par le même geste que le bloc « Rappeler » (recoller haut et bas, rien d'ajouté) |
| La fin montre une pilule noire « Entendez-le vous-même » : forme de bouton, non touchable, et l'adresse est à part dessous | 🔴 Critical | Une seule ligne d'action qui porte sa destination : « Entendez-le vous-même sur vokio.fr », sans forme de bouton |
| La mention « fictif » (20 px) et le libellé d'état (26 px) sont sous le seuil de lecture | 🔴 Critical | Mention et état à 36 px minimum |
| La mention est à y = 1792, sous l'interface Reels/TikTok qui la recouvre | 🟡 Moderate | La remonter au-dessus de y = 1500 |
| Le film ne dit pas qui est Camille avant 70 s (carte d'impact) | 🟢 Minor | Non appliqué : l'ouverture dure 1,5 s, pas la place d'une précision sans perdre la lecture |

### Visual Hierarchy
- **What draws the eye first** : la moitié orange de chaque titre. Pas le bon élément : la preuve
  est la carte qui s'écrit, et l'orange y est aussi (curseur, liseré), donc deux points solaires
  se disputent l'œil à chaque plan.
- **Reading flow** : état → titre → carte, de haut en bas, correct. La carte descend jusqu'à
  y = 1500 et la moitié basse (séparateur, lien, vide) ne porte rien.
- **Emphasis** : le solaire colore la moitié de sept titres, il ne signale donc plus « l'agent agit ».

### Consistency
| Element | Issue | Recommendation |
|---------|-------|----------------|
| Fond | Fond sombre #262019, alors que Plein Jour et le film validé du 23/09 disent « aucun fond sombre nulle part » | Sol papier #F4F1E8 avec un halo solaire discret, fin en clair #FBF9F2 |
| Couleur du texte | Titres en ivoire + italique solaire ; prix de fin en #E5701F (ember, absent de la charte vidéo) | Texte 100 % encre, le contraste vient de la taille et de l'italique |
| Solaire | Sur chaque titre, le curseur, le point du i | Rationné : le curseur qui écrit (l'agent agit) et le point du i à la fin |
| Mono capitales | État en mono capitales, alors que la carte réelle porte déjà « RÉSUMÉ DE L'APPEL » et « URGENCE » en mono | État en Geist, casse normale : un seul usage mono par écran, celui du produit |
| Fin | Quatre éléments (mot, prix, bouton, adresse) contre trois au maximum | Mot, prix, ligne d'action |
| Ombres | Ombres portées de 160 px sur les cartes | Filet de 1 px encre à 16 %, la seule bordure de la charte |

### Accessibility
- **Color contrast** : ivoire sur noir 14,3:1 ✅ ; solaire sur noir 7,7:1 ✅ ; mention pierre #8A857C
  sur noir 4,39:1 ❌ (4,5 requis) ; à la fin, prix ember sur ivoire 2,99:1 ❌ et adresse pierre sur
  ivoire 3,48:1 ❌.
- **Touch targets** : sans objet (vidéo), mais deux affordances trompeuses (lien, pilule).
- **Text readability** : titres 76 px ✅ ; résumé de la carte ~39 px ✅ ; état 26 px ❌ ; mention
  20 px ❌ ; adresse de fin 28 px ❌ ; heures de l'agenda ~33 px ❌.

### What Works Well
- L'écriture mot à mot au rythme de la parole, avec la pastille URGENCE posée sur le mot : c'est
  la preuve, elle ne se discute pas.
- Aucun numéro à l'écran, mention « fictif » présente, interface réelle et non réinventée.
- Un seul titre à la fois, des titres courts qui racontent l'appel sans le paraphraser.

### Priority Recommendations
1. **Tout lire sur un téléphone** : état et mention à 36 px, carte élargie à 960 px (résumé à ~41 px,
   agenda agrandi de 7 %), mention remontée au-dessus de y = 1500, bande morte de la carte retirée.
2. **Supprimer les fausses affordances et tenir trois éléments** : lien « Voir la fiche client »
   retiré, pilule-bouton remplacée par une ligne d'action qui porte l'adresse.
3. **Revenir à la charte Plein Jour** : sol papier, texte encre, solaire réservé à l'agent qui agit
   (curseur, point du i), filets au lieu d'ombres ; les contrastes en échec disparaissent avec.

## Accessibility Audit : L'appel réel (plombier)
**Standard :** WCAG 2.1 AA | **Date :** 24/09/2026

### Summary
**Issues found :** 7 | **Critical :** 2 | **Major :** 3 | **Minor :** 2

### Findings

#### Perceivable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 1 | Mention 20 px à 4,39:1 sur noir | 1.4.3 Contrast | 🔴 Critical | #716D66 sur papier (4,56:1), 36 px |
| 2 | Prix de fin #E5701F sur ivoire, 2,99:1 | 1.4.3 Contrast | 🟡 Major | Encre sur ivoire (15,3:1), italique pour l'accent |
| 3 | Adresse de fin pierre sur ivoire 3,48:1, 28 px | 1.4.3 Contrast | 🟡 Major | Fusionnée dans la ligne d'action en encre, 44 px |
| 4 | Libellé d'état 26 px | Lisibilité mobile (seuil 36 px du brief, hors WCAG) | 🔴 Critical | 36 px |
| 5 | L'appel n'est pas sous-titré ; la plupart des Reels se regardent sans le son | 1.2.2 Captions | 🟡 Major | Non appliqué : la carte qui s'écrit tient lieu de transcription, un sous-titre ajouterait un quatrième élément |

#### Understandable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 6 | Pilule en forme de bouton non actionnable | 3.2.4 Consistent identification | 🟢 Minor | Ligne de texte simple |
| 7 | Lien souligné non actionnable dans la capture | 3.2.4 Consistent identification | 🟢 Minor | Bande retirée de la capture |

### Color Contrast Check
| Element | Foreground | Background | Ratio | Required | Pass? |
|---------|-----------|------------|-------|----------|-------|
| Titres (original) | #F4F1E8 | #262019 | 14,27:1 | 3:1 | ✅ |
| Accent de titre (original) | #EFA424 | #262019 | 7,68:1 | 3:1 | ✅ |
| Mention (original) | #8A857C | #262019 | 4,39:1 | 4,5:1 | ❌ |
| Prix, accent (original) | #E5701F | #FBF9F2 | 2,99:1 | 3:1 | ❌ |
| Adresse de fin (original) | #8A857C | #FBF9F2 | 3,48:1 | 4,5:1 | ❌ |
| Titres (retravail) | #262019 | #F4F1E8 | 14,27:1 | 3:1 | ✅ |
| Mention (retravail) | #716D66 | #F4F1E8 | 4,56:1 | 4,5:1 | ✅ |
| Résumé de la carte (capture) | #4A463F | #EFECE3 | 7,94:1 | 4,5:1 | ✅ |

### Priority Fixes
1. **Mention et état lisibles** : ce sont les deux textes qui disent que l'appel est réel et
   l'établissement fictif ; illisibles, ils ne protègent plus rien.
2. **Contrastes de la fin** : le prix et l'adresse sont les deux informations qu'on retient.
3. **Fausses affordances** : lien et pilule.

## UX Copy : textes du film (hors résumé de la carte)

### Recommended Copy
**Ligne d'action (fin)** : Entendez-le vous-même sur vokio.fr
**Titre du lendemain** : Le lendemain, l'intervention est dans votre agenda.
**Mention** : Établissement fictif de démonstration. / Appel réel, captures réelles de app.vokio.fr

### Alternatives
| Option | Copy | Tone | Best For |
|--------|------|------|----------|
| A | Entendez-le vous-même sur vokio.fr | direct, vouvoiement | fin de ce film : reprend le verbe d'ouverture « Écoutez » |
| B | Essayez-le vous-même sur vokio.fr | incitatif | si la page d'arrivée porte un bouton d'appel |
| C | Entendez-le vous-même | inchangé | seulement si l'adresse reste visible à côté (un quatrième élément) |

### Rationale
- La ligne d'action commence par un verbe et nomme sa destination : un bouton qui ne se touche
  pas ne sert à rien, une adresse qu'on retient, si. Elle fusionne deux éléments en un.
- « votre agenda » au lieu de « l'agenda » : même fait, mais c'est l'agenda du commerçant qui
  regarde ; les autres titres parlent déjà à « vous ».
- La mention garde « Établissement fictif de démonstration » mot pour mot ; « sur une ligne de
  démonstration » est déjà dit par l'état en tête d'écran pendant tout l'appel.
- Titres conservés : courts, concrets, au présent, chacun nomme un fait de l'appel.

### Localization Notes
Aucune (film en français seul). Pas de tiret cadratin, vouvoiement partout.
