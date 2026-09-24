# Critique de l'original « Une nuit chez Vokio » (plombier)

Fichier examiné : `/root/vokio-uploads/videos/ux-210926/film-plombier/une-nuit-chez-vokio.mp4`
(38,2 s, 1080x1920, 60 i/s, muet). Images clés regardées : 1,8 · 4 · 7,2 · 8,2 · 13 · 18,5 · 20 · 21 · 22,5 · 26 · 31 · 36 s.
Le même gabarit (`monter.py` + `profils.py`) produit les trois autres films : chaque constat ci-dessous
vaut pour eux, sauf mention contraire. Grilles appliquées : design-critique, accessibility-review, ux-copy.
Lecture sur téléphone : 1080 px = 390 pt, donc un texte sous 36 px est illisible.

---

## Design Critique : « Une nuit chez Vokio », démo de l'application en 9:16

### Overall Impression
Le récit est juste et la matière est la bonne (de vraies cartes de app.vokio.fr, sur un fond de nuit
qui les fait ressortir). La plus grosse marge de progrès est la lisibilité : l'interface est montrée
trop petite, l'écran final empile sept éléments à la fois et le texte de l'agenda se lit à 31 px.

### Usability
| Finding | Severity | Recommendation |
|---------|----------|----------------|
| Agenda affiché à 900 px de large : horaires et motifs des rendez-vous à ~31 px, sous le seuil de lecture | Critique | Appliquer la règle du dossier (« un composant à la fois, à trois fois sa taille ») : agrandir l'agenda de 30 %, recadré sur la colonne du jour |
| Écran final : mot-symbole, trois arguments, prix, bouton et adresse visibles ensemble (7 éléments) | Critique | Une information à la fois : les arguments passent l'un après l'autre dans la même place, l'état final ne garde que mot-symbole, prix, appel à l'action |
| Le « bouton » Entendez-le vous-même ressemble à un bouton qu'on ne peut pas toucher : chrome factice, et il ne dit pas où aller | Modéré | Appel à l'action typographique, fusionné avec l'adresse : « Entendez-le vous-même sur vokio.fr » |
| Numéro de téléphone lisible sur la carte dépliée (« Rappeler 06 39 98 01 42 ») et en titre d'une rangée | Modéré | Retirer le bloc Rappeler et la ligne-numéro des captures (précédent : `monter_appel_reel.py`), sans rien ajouter à l'image |
| Première seconde et demie : seulement « 23:07 » dans le noir, l'accroche n'arrive qu'à 1,5 s | Mineur | Avancer l'accroche : elle doit être lisible avant la fin de la 2e seconde |

### Visual Hierarchy
- **What draws the eye first** : l'heure 23:07 à l'ouverture (juste), puis sur chaque plan le titre serif,
  avant la carte (juste). Sur l'écran final, rien ne domine : le prix et les puces se disputent le regard.
- **Reading flow** : titre, puis carte, de haut en bas, lisible. Mais l'état « Camille répond à votre place »
  reste en haut pendant 35 s : il devient du bruit que l'œil doit sauter à chaque plan.
- **Emphasis** : le solaire est employé partout (deux-points de l'heure, chute de chaque titre, point
  d'état vert, puces, prix en orange) : il ne signale plus rien. La charte le réserve à « l'agent agit »,
  une fois par plan.

### Consistency
| Element | Issue | Recommendation |
|---------|-------|----------------|
| Couleur | Solaire sur les quatre titres alors que deux captures portent déjà leur propre solaire (liseré du résumé, créneaux de l'agenda) : deux solaires par plan | Chute des titres en italique ivoire quand la capture porte le solaire, en solaire sinon |
| Couleur | Prix « sans engagement » en orange `#E5701F` : couleur hors rôle (ni agent, ni action) | Italique encre, le contraste vient de la forme |
| Profondeur | Ombres portées de 160 px sous chaque carte : la charte Plein Jour exclut l'ombre | Filet de 1 px, lueur de fond unique et très basse |
| Mono capitales | Deux usages sur l'écran final (« VOKIO.FR » + étiquettes des captures ailleurs), et l'état en mono tenu sur tous les plans | Un seul usage de mono capitales par écran : l'état à l'ouverture seulement |
| Mouvement | Toutes les entrées identiques (fondu + montée de 110 à 180 px) | Grammaire par nature : lignes qui montent de sous leur masque pour le texte, insertion en tête de liste, dépliage, panoramique, lever du jour pour la fin |

### Accessibility
- **Color contrast** : échecs mesurés sur l'état (4,39:1 pour 26 px), l'adresse vokio.fr (3,48:1), « sans engagement »
  (2,99:1), les rangées estompées à 38 % (2,6 à 3,3:1). Détail dans l'audit ci-dessous.
- **Touch targets** : sans objet dans une vidéo ; le faux bouton laisse croire le contraire.
- **Text readability** : mention légale à 21 px, état à 26 px, adresse à 28 px, agenda à ~31 px, métadonnées d'appel à ~34 px : sous le seuil de 36 px.

### What Works Well
- La démonstration est vraie : chaque image vient de l'application, rien n'est dessiné.
- Le récit en cinq temps tient en une phrase et chaque titre dit une seule chose.
- Le passage final au clair marque bien la fin de la nuit.
- Aucun texte important sous y = 1500, aucun tiret cadratin.

### Priority Recommendations
1. **Lisibilité d'abord** : tout texte à 36 px ou plus. Agenda agrandi de 30 %, carte dépliée à pleine taille (plus de réduction),
   mention légale et état à 36 px. C'est ce qui fait qu'une démo se lit sur un téléphone au lieu de se deviner.
2. **Contraste AA partout** : état en ivoire (14,3:1), mention en pierre éclaircie (7,4:1 sur la nuit, 5,2:1 sur le clair),
   « sans engagement » en encre, rangées de contexte à 62 % au lieu de 38 %.
3. **Une information à la fois, sans chrome factice** : écran final réduit à trois éléments (les arguments défilent un par un),
   bouton remplacé par un appel à l'action typographique qui dit où aller, état de la ligne limité à l'ouverture.

---

## Accessibility Audit : « Une nuit chez Vokio »
**Standard:** WCAG 2.1 AA | **Date:** 24/09/2026

### Summary
**Issues found:** 8 | **Critical:** 2 | **Major:** 4 | **Minor:** 2

### Findings

#### Perceivable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 1 | Texte de l'agenda à ~31 px sur un 1080 px (≈ 11 pt lus) | 1.4.4 Resize text (lisibilité) | Critique | Agrandir l'agenda de 30 % |
| 2 | Mention « Établissement de démonstration… » à 21 px, pierre sur nuit 4,39:1 | 1.4.3 Contrast | Critique | 36 px, pierre éclaircie `#B5AFA4` (7,4:1), puis `#6E685F` sur le clair (5,2:1) |
| 3 | État « Camille répond à votre place » 26 px, `#8A857C` sur `#262019` = 4,39:1 | 1.4.3 Contrast | Majeur | Ivoire, 36 px |
| 4 | « vokio.fr » 28 px, `#8A857C` sur `#FBF9F2` = 3,48:1 | 1.4.3 Contrast | Majeur | Fusionné dans l'appel à l'action, encre 13,8:1 |
| 5 | « sans engagement. » `#E5701F` sur `#FBF9F2` = 2,99:1 (grand texte, seuil 3:1) | 1.4.3 Contrast | Majeur | Italique encre |
| 6 | Rangées d'appel estompées à 38 % : 2,6 à 3,3:1 | 1.4.3 Contrast | Majeur | 62 % ; elles sortent dès que l'appel se déplie |
| 7 | Métadonnées des cartes (« dim. 20 sept., 23:07 · 2 min ») à ~34 px | 1.4.4 | Mineur | Carte dépliée à pleine taille (plus de réduction à 94 %) |
| 8 | Film muet : aucune piste à décrire, le texte à l'écran porte tout le récit | 1.2.1 Audio-only / Video-only | Mineur | Conforme tant que chaque information passe par le texte, ce qui est le cas |

#### Operable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 1 | Faux bouton « Entendez-le vous-même » : cible qui n'en est pas une | 2.5.5 Target Size (attente trompée) | Mineur | Appel à l'action typographique |

#### Understandable
| # | Issue | WCAG Criterion | Severity | Recommendation |
|---|-------|---------------|----------|----------------|
| 1 | L'appel à l'action ne dit pas où agir (l'adresse est deux lignes plus bas, en gris) | 3.3.2 Labels or instructions | Mineur | « Entendez-le vous-même sur vokio.fr » |

#### Robust
Sans objet pour une vidéo muette sans interaction.

### Color Contrast Check
| Element | Foreground | Background | Ratio | Required | Pass? |
|---------|-----------|------------|-------|----------|-------|
| Titres | `#F4F1E8` | `#262019` | 14,27:1 | 3:1 | Oui |
| Chute des titres (solaire) | `#EFA424` | `#262019` | 7,68:1 | 3:1 | Oui |
| État de la ligne | `#8A857C` | `#262019` | 4,39:1 | 4,5:1 | Non |
| Mention (nuit) | `#8A857C` | `#262019` | 4,39:1 | 4,5:1 | Non |
| Arguments | `#2F281F` | `#FBF9F2` | 13,80:1 | 4,5:1 | Oui |
| « sans engagement. » | `#E5701F` | `#FBF9F2` | 2,99:1 | 3:1 | Non |
| vokio.fr | `#8A857C` | `#FBF9F2` | 3,48:1 | 4,5:1 | Non |
| Rangées à 38 % | `#1f1b15` mêlé | `#746f68` | 3,32:1 | 4,5:1 | Non |

### Keyboard Navigation / Screen Reader
Sans objet : vidéo sociale sans interaction ni lecteur d'écran.

### Priority Fixes
1. **Agenda et mention lisibles** : touche tout spectateur sur téléphone, bloque la preuve (« le rendez-vous est déjà posé » doit se lire).
2. **Contrastes de l'état, du prix et de l'adresse** : améliore la lecture en plein jour et sur écran bas de gamme.
3. **Faux bouton retiré** : nice to have, supprime une attente de tap impossible.

---

## UX Copy : textes affichés et appel à l'action

Contexte : Reel de 38 s, muet, vu par un artisan ou un commerçant qui fait défiler ; il ne connaît ni Vokio ni « Camille ».
Ton : calme, concret, vouvoiement. Contraintes : faits identiques, aucune promesse nouvelle, pas de tiret cadratin, pas de numéro.

### Recommended Copy
**Appel à l'action** : Entendez-le vous-même sur vokio.fr
**Mention** : Établissement fictif, captures réelles de app.vokio.fr

Les autres textes sont gardés mot pour mot : chacun dit une seule chose, commence par l'essentiel
et parle au spectateur (« vous dormez », « votre espace », « vous n'avez rien raté »).

### Alternatives
| Option | Copy | Tone | Best For |
|--------|------|------|----------|
| A | Entendez-le vous-même sur vokio.fr | Invitation directe, dit où aller | Retenu : garde le verbe d'origine, ajoute la destination |
| B | Écoutez un vrai appel sur vokio.fr | Plus concret | Si la page d'accueil garde l'appel jouable en premier écran |
| C | Entendez-le vous-même (+ vokio.fr en dessous) | Original | Deux éléments pour une seule action |

Mention :
| Option | Copy | Tone | Best For |
|--------|------|------|----------|
| A | Établissement fictif, captures réelles de app.vokio.fr | Sobre | Retenu : tient sur une ligne à 36 px |
| B | Établissement de démonstration, données fictives · captures réelles de app.vokio.fr | Original | Illisible à 21 px, deux lignes à 36 px |

### Rationale
L'appel à l'action d'origine est bien un verbe, mais il ne dit pas où agir : l'adresse vit deux lignes plus bas,
en gris, en mono capitales. Les fusionner fait une seule action complète et libère une place sur l'écran final.
La mention garde le mot « fictif » et les deux faits (l'établissement n'existe pas, les captures sont réelles) ;
« de démonstration » et « données fictives » disaient deux fois la même chose.
« Camille » n'est pas présenté : on le garde, parce que l'état se lit dans la continuité de l'accroche
(« Vous dormez. » puis « Camille répond à votre place ») et que l'ajout d'un titre (« votre assistante ») serait une précision nouvelle.

### Localization Notes
« Entendez-le » renvoie au service (le « le » est l'agent) : à ne pas traduire littéralement.
« Coup de feu » (restaurant) est un idiome de métier, à garder tel quel.
