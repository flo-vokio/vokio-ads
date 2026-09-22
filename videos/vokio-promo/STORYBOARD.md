---
format: 1080x1920
duration: 30s
message: "Un appel sans réponse, c'est un client chez le concurrent — Vokio décroche à votre place"
arc: Accroche → Problème → Vokio décroche → Le rendez-vous se pose → La preuve → CTA
audience: artisans et commerçants TPE, métiers de terrain
mode: collaborative
language: fr
metier: plombier
---

## Frame 1 — Les mains sous un évier

- type: hook
- blueprint: kinetic-type-beats
- scene: Deux constats en Instrument Serif, puis la pastille d'appel entrant qui se met à pulser
- duration: 3.2s
- transition_in: cut
- status: outline
- voiceover: "Les mains sous un évier. Le téléphone sonne."
- asset_candidates: aucun visuel capturé — composition typographique + la pastille d'appel reconstruite aux tokens de marque
- handoff_out: pastille d'appel « Appel entrant · 02:07 » centrée x 50 % y 62 %, échelle 1, opacité 1, pulsation lente en cours
- src: compositions/frames/01-accroche.html

Ouvrir sur le moment, pas sur le produit. La première ligne est reprise mot pour
mot de la page d'accueil (« les mains dans la couleur, sous un évier, sur un
échafaudage ») : c'est la phrase que Florian a écrite lui-même pour décrire ses
clients, elle est à sa place ici. Le deuxième temps n'est pas un texte mais un
objet : la pastille d'appel entrant qui apparaît et pulse. Aucun numéro lisible.

## Frame 2 — Vous ne décrochez pas

- type: pain_point
- blueprint: kinetic-type-beats
- scene: La pastille d'appel s'éteint, un filet la barre, le nom glisse vers le suivant de la liste
- duration: 4.8s
- transition_in: cut
- status: outline
- voiceover: "Vous ne décrochez pas. Le client appelle le suivant sur la liste."
- asset_candidates: aucun visuel capturé — la pastille héritée de Frame 1, un filet 1 px, une liste en Geist Mono
- handoff_in: pastille d'appel au même x 50 % y 62 %, échelle 1, opacité 1, pulsation encore en cours à l'entrée ; elle s'éteint sur place, ne réapparaît pas
- src: compositions/frames/02-probleme.html

Le plan continue le précédent, il ne recommence pas : c'est le même appel qui
meurt à l'écran. La pastille perd sa pulsation, un filet horizontal la traverse,
et la liste défile d'un cran sous elle. Personne n'est nommé, aucun concurrent
n'est désigné : c'est « le suivant », et le vide à la place du nom fait le
travail. Aucun montant, aucun pourcentage.

## Frame 3 — Vokio décroche, et dit qui elle est

- type: feature_showcase
- blueprint: agent-progress-theater
- scene: Le fil de conversation se construit message par message, l'onde vocale bat quand l'agent parle
- duration: 6.0s
- transition_in: crossfade
- status: outline
- voiceover: "Vokio décroche à votre place, et dit tout de suite qui elle est."
- asset_candidates: assets/symbole-onde.svg (les cinq barres du symbole Vokio, barre centrale solaire)
- handoff_out: fil de conversation calé à gauche, dernière bulle client visible en bas ; l'onde vocale reste allumée sous le fil, x 50 % y 84 %, échelle 1, opacité 1
- src: compositions/frames/03-decroche.html

Le seul plan où la marque parle. Deux bulles arrivent, dans cet ordre : celle de
l'agent, puis celle du client. La première porte la mention légale, et elle est
**montrée, jamais prononcée** : « Plomberie Azur, bonjour. Je suis l'assistante
vocale de l'entreprise. » Article 50 réglé par l'image, ce qui est aussi plus
convaincant qu'une voix off qui l'affirmerait. La deuxième est la vraie demande
entendue sur la démo du site : « J'ai une fuite sous l'évier. »

L'onde vocale de marque bat pendant la bulle de l'agent et s'immobilise dès que
le client parle. C'est là qu'elle entre dans le film ; elle en ressortira au CTA.

## Frame 4 — Le rendez-vous se pose

- type: feature_showcase
- blueprint: panel-edit-live-sync
- scene: Le fil à gauche, l'agenda à droite ; la demande comprise fait apparaître un créneau réel
- duration: 6.0s
- transition_in: cut
- status: outline
- voiceover: "Elle comprend la demande, regarde votre agenda, pose le rendez-vous."
- asset_candidates: agenda de app.vokio.fr à capturer par lien magique (décision ouverte, voir Notes) — sinon reconstruction aux tokens de frame.md
- handoff_in: fil de conversation au même calage qu'en sortie de Frame 3, il glisse vers la gauche sans se recomposer
- handoff_out: carte du créneau « jeudi 8 h 30 » posée x 62 % y 48 %, échelle 1, opacité 1, immobile
- src: compositions/frames/04-agenda.html

Le plan qui doit convaincre : ce n'est pas un répondeur, c'est un agenda qui
bouge. Trois appuis calés sur les trois virgules de la phrase — comprend /
regarde / pose. Le couple gauche-droite reste visible en permanence, c'est le
lien entre les deux qui est le produit. Le créneau qui se pose est une vraie
heure ouvrable, pas une case qui clignote.

## Frame 5 — Les deux confirmations

- type: feature_showcase
- blueprint: comparison-split
- scene: Deux reçus entrent des deux bords : le SMS du client à gauche, le récapitulatif de l'artisan à droite
- duration: 6.0s
- transition_in: cut
- status: outline
- voiceover: "Le client reçoit sa confirmation. Vous recevez le récapitulatif."
- asset_candidates: aucun visuel capturé — deux cartes aux tokens de frame.md, texte repris de la démo réelle du site
- src: compositions/frames/05-preuve.html

La phrase a deux moitiés symétriques, le plan aussi. Deux objets de poids égal,
chacun entrant de son côté, chacun horodaté en Geist Mono. Rien ne bouge après.
C'est le plan de repos du film : la preuve n'a pas besoin d'être agitée.

## Frame 6 — Ne ratez plus un seul appel

- type: cta
- blueprint: logo-assemble-lockup
- scene: L'onde vocale se resserre, sa barre solaire monte et devient le point du i de Vokio
- duration: 4.0s
- transition_in: crossfade
- status: outline
- voiceover: "Ne ratez plus un seul appel."
- asset_candidates: assets/symbole-onde.svg ; wordmark reconstruit selon le site (point solaire à left 63,5 %)
- src: compositions/frames/06-cta.html

Le seul mouvement de marque du film, et il n'appartient qu'à Vokio : les cinq
barres de l'onde vocale se resserrent, les quatre barres d'encre s'effacent, et
la barre centrale orange remonte se poser en point sur le i du mot Vokio. Le
logo n'arrive pas, il se termine.

Dessous, la phrase du brief puis l'adresse. « Votre numéro ne change pas » en
micro-label : c'est l'objection la plus fréquente, et elle tient en cinq mots.
Aucun numéro de téléphone.
