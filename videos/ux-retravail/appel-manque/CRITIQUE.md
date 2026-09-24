# Critique de l'original · « Ce que coûte un appel manqué » (plombier)

Source : `/root/vokio-uploads/videos/ux-210926/manque-plombier/appel-manque-plombier.mp4`,
11 images extraites (0,5 / 1,5 / 3,0 / 4,3 / 5,0 / 6,5 / 7,5 / 8,3 / 9,0 / 10,5 / 11,6 s).
Lecture téléphone : 1080 px = 390 pt, tout texte sous 36 px est illisible.

## Design Critique : appel-manque-plombier (original du 22/09)

### Overall Impression
Le récit en trois temps (l'heure, le prix, la réponse) est net et le chiffre qui monte est un bon crochet. Le point faible : les deux premières secondes ne disent pas qu'il s'agit d'un appel, et tout ce qui est petit (étiquette, mention, adresse) est illisible sur un téléphone.

### Usability
| Finding | Severity | Recommendation |
|---------|----------|----------------|
| À 2 s on lit « 23:07 · Un chauffe-eau qui lâche. » sans savoir que c'est un appel : le mot « appel » n'arrive qu'à 3,8 s, en 28 px | 🔴 Critical | Poser « Un appel manqué » dès la première image, en en-tête des plans 1 et 2 |
| La mention « Montant illustratif · établissement fictif de démonstration » est à y = 1806, sous l'interface Reels/TikTok, en 21 px : masquée ET illisible | 🔴 Critical | La remonter au-dessus de y = 1500, 36 px minimum, texte raccourci pour tenir sur une ligne |
| L'adresse « vokio.fr », seule action possible, est en 30 px gris pierre | 🟡 Moderate | 40 px, encre pleine |
| « établissement fictif » alors qu'aucun établissement n'est nommé dans ce film | 🟢 Minor | « exemple fictif » : le mot fictif reste, la mention colle à ce qui est montré |

### Visual Hierarchy
- **What draws the eye first** : l'heure en 230 px, puis le chiffre solaire. Juste pour l'heure, mais sans contexte elle ne dit rien.
- **Reading flow** : haut gauche, descendant ; bon. Le plan 3 centré casse volontairement l'axe, c'est la réponse.
- **Emphasis** : le solaire sert au deux-points et au montant perdu. Dans la charte Plein Jour le solaire veut dire « l'agent agit » : une perte en solaire envoie le signal inverse.

### Consistency
| Element | Issue | Recommendation |
|---------|-------|----------------|
| Couleur | Fond noir sur 70 % du film, alors que la charte Plein Jour ne connaît pas de fond sombre | Parchemin assombri d'un cran pour la « nuit », papier du jour pour la réponse |
| Couleur | Solaire sur la perte (deux-points, montant), orange #E5701F en texte (« 59 € par mois. ») | Solaire réservé au point du i de Vokio ; tout le texte en encre |
| Typographie | Deux mono capitales dans le même film, bien séparées par plan : conforme | Garder |

### Accessibility
- **Color contrast** (mesuré) : ivoire/noir 14,3:1 ✅ ; étiquette et mention pierre/noir 4,4:1 ❌ ; mention sur clair #9A948A/#FBF9F2 2,9:1 ❌ ; « vokio.fr » 3,5:1 ❌ ; « 59 € par mois. » #E5701F/#FBF9F2 3,0:1 (texte large, limite) ⚠️.
- **Touch targets** : sans objet (vidéo).
- **Text readability** : mention 21 px, étiquette 28 px, adresse 30 px, toutes sous le seuil de 36 px. Film muet : le texte porte 100 % du sens, aucun sous-titre à prévoir.

### What Works Well
- Trois temps, une idée par temps, jamais plus de trois objets.
- Le compteur qui monte puis se pose : le montant se « ressent » avant d'être lu.
- « Par un autre plombier. » : la chute tient en quatre mots.

### Priority Recommendations
1. **Dire « appel manqué » dès la première image** : en-tête persistant des plans 1 et 2, pour que l'heure se lise comme l'heure d'un appel raté.
2. **Tout texte à 36 px minimum et au-dessus de y = 1500** : mention 36 px à y = 1440, étiquette et adresse 40 px.
3. **Contraste AA partout** : encre pleine (ou 80 %) sur papier, 7,7:1 minimum ; plus de gris pierre ni d'orange en texte.

## Accessibility Audit : appel-manque-plombier
**Standard :** WCAG 2.1 AA | **Date :** 24/09/2026

### Summary
**Issues found :** 5 | **Critical :** 2 | **Major :** 2 | **Minor :** 1

### Findings

#### Perceivable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 1 | Mention 2,9:1 à 4,4:1 selon le fond | 1.4.3 Contrast | 🔴 Critical | Encre 80 % : 7,7:1 sur parchemin, 8,3:1 sur papier |
| 2 | Mention, étiquette, adresse sous 36 px (illisibles sur téléphone) | 1.4.4 (lisibilité, adapté vidéo) | 🔴 Critical | 36 à 40 px |
| 3 | Adresse vokio.fr 3,5:1 | 1.4.3 Contrast | 🟡 Major | Encre pleine, 14,3:1 |
| 4 | Mention masquée par l'interface de la plateforme (y = 1806) | 1.4.10 (équivalent : contenu occulté) | 🟡 Major | y = 1440 |

#### Operable / Robust
Sans objet : vidéo muette sans interaction.

#### Understandable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 5 | Contexte « appel » absent des 3,8 premières secondes | 3.3.2 Labels (adapté) | 🟢 Minor | En-tête dès 0,1 s |

### Color Contrast Check
| Element | Foreground | Background | Ratio | Required | Pass? |
|---------|-----------|------------|-------|----------|-------|
| Texte principal (orig.) | #F4F1E8 | #262019 | 14,3:1 | 4.5:1 | ✅ |
| Étiquette / mention (orig.) | #8A857C | #262019 | 4,4:1 | 4.5:1 | ❌ |
| Mention sur clair (orig.) | #9A948A | #FBF9F2 | 2,9:1 | 4.5:1 | ❌ |
| vokio.fr (orig.) | #8A857C | #FBF9F2 | 3,5:1 | 4.5:1 | ❌ |
| 59 € par mois. (orig.) | #E5701F | #FBF9F2 | 3,0:1 | 3:1 (large) | ⚠️ |
| Texte principal (retravail) | #262019 | #ECE6D6 | 12,9:1 | 4.5:1 | ✅ |
| Mention (retravail) | #262019 à 80 % | #ECE6D6 / #F4F1E8 | 7,7 / 8,3:1 | 4.5:1 | ✅ |
| Texte sur le halo (retravail) | #262019 | ~#F0DDB8 | 12,1:1 | 4.5:1 | ✅ |

### Priority Fixes
1. **Mention lisible et visible** : c'est la seule protection légale du montant, elle doit se lire.
2. **Adresse lisible** : c'est la seule action proposée.
3. **Contexte dès la première image** : améliore la compréhension pour tous, lecteurs lents compris.

## UX Copy : textes affichés

### Recommended Copy
**En-tête** : Un appel manqué (inchangé, avancé au début)
**Situation / chute / réponse** : inchangées (« Un chauffe-eau qui lâche. », « Le chauffe-eau remplacé. Par un autre plombier. », « Vokio décroche. 59 € par mois. »)
**Mention** : Montant illustratif · exemple fictif
**Appel à l'action** : vokio.fr (inchangé)

### Alternatives
| Option | Copy | Tone | Best For |
|--------|------|------|----------|
| A | vokio.fr | sobre | retenu : aucune promesse, aucun mot de métier |
| B | Découvrez vokio.fr | incitatif | si Florian veut un verbe en tête (pattern CTA) |
| C | Écoutez-la sur vokio.fr | incitatif | écarté : suppose une démo audio sur la page, capacité non vérifiée ici |

### Rationale
Les textes du récit sont déjà clairs, concis et au bon registre : on n'y touche pas. Le pattern CTA
(verbe d'abord) plaiderait pour B, mais la consigne interdit toute promesse nouvelle et la vignette
est une signature de marque plus qu'un bouton : l'adresse seule, rendue lisible, suffit. La mention
raccourcie tient sur une ligne en 36 px et dit exactement ce qui est fictif ici (l'exemple), le film
ne montrant aucun établissement.

### Localization Notes
« 23:07 » garde la graphie d'horloge de téléphone (la norme typographique française serait
« 23 h 07 ») : l'heure doit se lire comme celle d'un journal d'appels. Espace fine insécable
(U+2009) dans « 1 200 » et « 14 000 ». Vouvoiement sans objet (aucune adresse directe au lecteur).
