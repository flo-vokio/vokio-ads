# Chantier « retravail HyperFrames » (24/09/2026) · brief commun à tous les agents

## Le but
Florian veut COMPARER : les vidéos prêtes à publier (fabriquées les 21-22/09 avec notre
chaîne maison, HTML + capture Playwright) contre une version refaite avec les skills
HyperFrames de motion design installés le 22/09 au soir. La comparaison doit porter sur
le SEUL savoir-faire visuel : mise en page, mouvement, rythme, transitions, typographie.

Donc, pour chaque film, on garde à l'identique :
- le récit, les textes à l'écran (mot pour mot), l'ordre des plans ;
- la durée (± 0,3 s) et le format 1080x1920, 30 i/s ;
- le son : si l'original est muet, le retravail est muet ; s'il a une piste audio, on
  réutilise EXACTEMENT cette piste (extraite de l'original par ffmpeg), rien de régénéré ;
- les images d'interface : ce sont de vraies captures de app.vokio.fr, on les réutilise
  (dossiers de /root/vokio-uploads/videos/ux-210926/). Jamais d'interface réinventée.

## Avant d'écrire une ligne
1. Lire le skill `/hyperframes` puis `hyperframes-core`, `hyperframes-animation`,
   `hyperframes-creative` (dans /opt/vokio-ads/.agents/skills/ ; ne JAMAIS lancer
   `skills update`, huit rustines locales seraient écrasées).
2. Lire /opt/vokio-ads/README.md (règle d'or : toujours `/opt/vokio-ads/bin/hf`, jamais
   `npx hyperframes` nu ; jamais `audio.mjs sync-durations`).
3. Lire la DA : /opt/vokio-ads/videos/vokio-promo/frame.md (Plein Jour) et
   /opt/vokio-ads/videos/vokio-promo/STORYBOARD.md pour le ton du film validé.
4. Regarder l'original : extraire 6-8 images (`ffmpeg -ss … -frames:v 1`) et lire le
   script qui l'a monté (dans /opt/vokio-site-repo/design/videos/ux-vertical/).

## Règles de Florian, non négociables
- Trois éléments simultanés à l'écran au maximum ; une info à la fois.
- Aucun chrome d'interface factice (pas de faux téléphone, pas de fausse barre d'état).
- Mono capitales : un seul usage par écran. Qui-parle = typographie.
- Jamais de tiret cadratin « — » dans un texte affiché.
- Aucun texte important sous y = 1500 (interface Reels/TikTok), rien sous y = 1380 de préférence.
- Aucun numéro de téléphone à l'écran. La mention « fictif » reste si l'original l'a.
- Décélération power3, pas de rebond ni de dépassement. Le soleil #EFA424 veut dire
  « l'agent agit », une fois par plan.

## Où travailler
- Projet : /opt/vokio-ads/videos/ux-retravail/<slug>/ (créé par vous). Ne touchez à RIEN
  d'autre : ni les autres projets de vokio-ads, ni /opt/vokio-site-repo, ni les originaux.
- Pas de git commit, pas de Drive, pas de publication, aucune écriture en production.
- ⚠️ Machine : 4 cœurs, 7 Go, ~6 Go de disque. Plusieurs agents tournent en parallèle.
  TOUT rendu passe par le verrou commun :
      flock /tmp/hf-rendu.lock /opt/vokio-ads/bin/hf render …
  Supprimez vos images intermédiaires et caches de rendu après chaque film.

## Ce que vous livrez
- /root/vokio-uploads/videos/ux-retravail/<nom-original>-hyperframes.mp4
  (<nom-original> = nom du MP4 d'origine sans extension), vérifié avec ffprobe
  (durée, taille, présence ou absence d'audio identique à l'original) ;
- /root/vokio-uploads/videos/ux-retravail/<nom-original>-hyperframes-couverture.png
  (même cadrage que la couverture d'origine) ;
- /opt/vokio-ads/videos/ux-retravail/<slug>/NOTES.md : 3 à 6 puces, ce qui change par
  rapport à l'original et pourquoi (en français, sans tiret cadratin).
- Contrôle visuel obligatoire avant de déclarer fini : extraire des images du rendu à
  plusieurs instants et les REGARDER (texte coupé, chevauchement, plan vide, frame noire).

Rapport final : chemins livrés, durées mesurées, ce qui change, tout écart au brief.

## AJOUT du 24/09 : les skills de design UX (prioritaire sur « textes identiques »)
Ce que Florian appelle « les nouveaux skills d'UX design », ce sont ceux du plugin
design installé le 23/09 :
  /root/.claude/plugins/synced/2d2a6b64-315c-470b-b117-5409907df571_5830dd0e-d656-44ab-aabc-19b906e4e578/design/skills/
  design-critique · accessibility-review · ux-copy · design-system
Lisez les quatre SKILL.md. Méthode, pour chaque film :
1. Extraire 6 à 10 images clés de l'ORIGINAL et les regarder.
2. Appliquer la grille design-critique (première impression 2 s, hiérarchie, ordre de
   lecture, cohérence avec la charte Plein Jour) + accessibility-review (contraste WCAG AA
   mesuré, taille de texte lue sur un téléphone : 1080 px = 390 pt, donc tout texte
   < 36 px est illisible) + ux-copy sur chaque texte affiché et sur l'appel à l'action.
   Écrire le résultat dans <projet>/CRITIQUE.md, au format de sortie du skill, en français.
3. Appliquer les recommandations prioritaires dans la version HyperFrames.
4. Les textes PEUVENT changer si ux-copy le justifie, avec ces bornes : faits identiques
   (montants, heures, métier, noms fictifs, « fictif »), jamais de tiret cadratin,
   vouvoiement, aucune promesse ni capacité nouvelle, aucun chiffre ajouté. Chaque texte
   changé est listé dans NOTES.md : avant → après, et la raison.
Le rapport final résume les 3 recommandations prioritaires et ce qui a été appliqué.
