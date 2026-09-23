---
format: 1080x1920
duration: 30s
message: "Un appel sans réponse, c'est un client chez le concurrent — Vokio décroche à votre place"
arc: Accroche → Problème → Vokio décroche → La réservation se pose → La preuve → CTA
audience: restaurateurs indépendants et petites équipes de salle
mode: collaborative
language: fr
metier: restaurant
music: none
---

## Video direction

Les invariants du film. Chaque plan en hérite ; les lignes `Scene` ne portent
que le delta.

**Palette** — `frame.md` fait foi, rien n'est inventé. Le papier `paper` est le
sol de tous les plans et ne change jamais. L'encre `ink` porte 100 % du texte :
le contraste vient de la taille, jamais de la couleur. Le solaire `sun` est
rationné à **un seul usage par plan** et il signale toujours la même chose,
*l'agent agit* : le halo de l'appel, la barre centrale de l'onde, le liseré de
le livre de réservations, la carte de la réservation, les pastilles des reçus, le point du i. Le
`ember` n'apparaît pas.

Une seule couleur négative dans tout le film, décidée le 23/09 : au plan 02,
sur le mot « pas. », la pastille d'appel bascule en **terracotta `#C0452C`**,
celle que l'espace client emploie déjà pour un créneau bloqué. Elle dure un
dixième de seconde et ne réapparaît jamais. Aucun fond sombre nulle part.

**Type** — par rôle, jamais par famille : `display` et `headline` pour ce qui
parle, `body` pour ce qui se lit, `micro-label` et `mono-data` pour les heures,
les horodatages et les étiquettes. Une seule capitale mono par écran.

**Grammaire du mouvement** — décélération longue, `power3` par défaut. Aucun
rebond, aucun dépassement, nulle part : ce film vend du calme, un `back.out`
le trahirait en une image. Modèle de révélation : **rien n'apparaît avant que
la voix ne le nomme**. À t=0 d'un plan, seul ce que la voix dit à cet instant
est à l'écran ; le reste attend son mot. Les minutages cités dans les `Scene`
sont les vrais horodatages de `audio_meta.json`, pas des estimations.

**Rythme** — les plans 03 et 06 sont les plus denses, les plans **05 et la fin
du 04** sont les temps de repos : contenu posé, plus rien qui bouge. Un plan
tenu immobile vaut mieux qu'un plan maintenu en vie de force.

**Durées** — les six durées sont délibérées et totalisent **30,0 s**, le format
d'un emplacement Reels. Chaque voix tient dans son plan avec de la marge ;
l'écart est le silence, et le silence est la moitié du montage.
**Ne jamais lancer `audio.mjs sync-durations` sur ce projet** : il écrase la
durée d'un plan par celle de sa voix, ce qui ramènerait le film à 18,8 s et
supprimerait tous les silences.

**Zone sûre** — rien d'important sous **y = 1380** (72 %). La bande de
sous-titres vit entre 1360 et 1490, au-dessus de la limite de conformité
y = 1500, et les 430 px du bas restent vides : c'est là que Reels et TikTok
posent leur propre interface.

**Liste noire** — pas de barre de navigation, pas d'onglet, pas de fenêtre de
navigateur, pas de curseur, pas de faux écran de téléphone. Pas de forme
décorative qui tienne lieu d'objet réel. Pas de dégradé bleu-violet. Et les
deux échecs de mouvement : le diaporama (tout posé dans les 25 % du début puis
figé) et l'économiseur d'écran (tout qui flotte en même temps sans raison).

## Frame 1 — Pris par le service

- type: hook
- blueprint: kinetic-type-beats
- scene: Deux constats en Instrument Serif, puis la pastille d'appel entrant qui se met à pulser
- duration: 4.2s
- transition_in: cut
- status: outline
- voiceover: "Pris par le service. Le téléphone sonne."
- asset_candidates: none
- handoff_out: pastille d'appel « Appel entrant · 02:07 » centrée x 50 % y 62 %, échelle 1, opacité 1, pulsation lente en cours
- persuasion: reconnaissance du moment
- beat: le monde d'avant
- blueprint: kinetic-type-beats (Adapt)
- focal: la pastille d'appel entrant
- roles: pastille = cutout · les deux lignes = supporting
- sfx: none
- captions: none
- src: compositions/frames/01-accroche.html

Adapt : on garde le principe des temps de texte qui se posent seuls sur un fond
nu, mais le dernier temps n'est pas un mot, c'est un objet. Le blueprint l'autorise
explicitement, et c'est ce qui empêche l'accroche de n'être qu'un carton de titre.

Scene 1 (0,00–1,35 s) : papier nu, rien d'autre. « Pris par le service. » se
révèle **mot à mot** (`dynamic-content-sequencing`) sur les mots réels — 0,04 /
0,19 / 0,54 / 0,77 / 0,90 — en `display`, décélération longue. Centré, tiers
supérieur, bloc à ~70 % de la largeur utile.

Scene 2 (1,35–2,60 s) : la première ligne descend d'un cran et passe en
`headline-sm` (échelle et position uniquement, pas de fondu croisé) ; « Le téléphone sonne. »
arrive sous elle en `display`, mot à mot sur 1,36 et 2,03. Deux lignes, deux
tailles : la hiérarchie se fait par l'échelle, pas par la couleur.

Scene 3 (2,60–4,20 s) : le texte se fige, plus une seule lettre ne bouge. La
pastille d'appel entrant entre au centre de la zone utile par une arrivée en
ressort **amorti** (`spring-pop-entrance`, réglage lisse, aucun dépassement),
halo solaire qui s'ouvre derrière elle en opacité et en échelle. Elle porte
« Appel entrant » en `micro-label` et « 02:07 » en `mono-data`, aucun numéro.
Le halo bat **exactement deux fois**, en tweens finis posés à la main entre
2,80 et 4,10 — jamais `repeat`, jamais `yoyo` — puis tient.
Trois objets à l'écran, pas un de plus.

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
- asset_candidates: none
- handoff_in: pastille d'appel au même x 50 % y 62 %, échelle 1, opacité 1, pulsation encore en cours à l'entrée ; elle s'éteint sur place, ne réapparaît pas
- persuasion: agitation de la douleur
- beat: le coût, sans le chiffrer
- blueprint: kinetic-type-beats (Adapt)
- focal: la liste des trois lignes
- roles: pastille héritée = supporting · liste = cutout
- sfx: none
- captions: none
- src: compositions/frames/02-probleme.html

Adapt : les temps de texte du blueprint deviennent des temps de **liste**. On
garde l'idée d'énoncés qui tombent un par un sur fond nu ; ce qui tombe ici,
ce sont des rangs.

Scene 1 (0,00–1,05 s) : la pastille est déjà là, héritée du plan précédent,
même place, halo encore vivant. « Vous ne décrochez pas. » se révèle mot à mot
au-dessus d'elle en `headline` sur 0,04 / 0,24 / 0,36. Sur « pas. » (0,95) le
halo **s'éteint d'un coup** et la pastille perd son solaire pour de l'encre
pâle. C'est la seule coupure sèche du film, et elle tombe sur le mot.

Scene 2 (0,95–1,38 s) : **l'échec**. Sur « pas. » l'encre de la pastille
bascule d'un coup en terracotta, en 0,10 s, sans décélération : une erreur ne
s'installe pas en douceur. Un voile négatif passe dessus, et la pastille
**descend** en se comprimant légèrement, puis s'efface. Elle ne remonte pas :
un appel perdu s'enfonce, il ne s'excuse pas. Tout est effacé à 1,38 s, juste
avant que le premier filet de la liste ne se trace.

Scene 2b (1,37–2,90 s) : trois rangs à filets s'écrivent un par un, calés sur
« client » (1,37), « appelle » (1,70), « suivant » (2,21). Le premier porte
« Vous » barré, les deux suivants « Restaurant suivant ». Aucun concurrent n'est
nommé : c'est « le suivant », et ça suffit.

Scene 3 (2,90–4,80 s) : sur « liste. » (2,89) le troisième rang s'allume en
solaire, seul usage du solaire dans ce plan. Puis plus rien : tenue immobile
jusqu'à 4,80, au plus un jitter très faible (`sine-wave-loop`, registre bas).
Le silence de 1,9 s après la phrase est le plan.

Le plan continue le précédent, il ne recommence pas : c'est le même appel qui
meurt à l'écran. La pastille perd sa pulsation, un filet horizontal la traverse,
et la liste défile d'un cran sous elle. Personne n'est nommé, aucun concurrent
n'est désigné : c'est « le suivant », et le vide à la place du nom fait le
travail. Aucun montant, aucun pourcentage.

## Frame 3 — Vokio décroche, et dit qui elle est

- type: feature_showcase
- blueprint: agent-progress-theater
- scene: Le fil de conversation se construit message par message, l'onde vocale bat quand l'agent parle
- duration: 5.4s
- transition_in: crossfade
- status: outline
- voiceover: "Vokio décroche à votre place, et dit tout de suite qui elle est."
- asset_candidates: assets/symbole-onde.svg
- handoff_out: aucun report. Le plan 04 repart sur un livre de réservations seul, pleine largeur (décision Florian du 23/09 : le fil a déjà été lu en entier ici, le relire en petit divise le regard)
- persuasion: le renversement
- beat: quelqu'un a décroché
- blueprint: agent-progress-theater (Adapt)
- focal: assets/symbole-onde.svg
- roles: onde = cutout · bulle agent = cutout · bulle client = supporting
- sfx: none
- src: compositions/frames/03-decroche.html

Adapt : on garde la signature du blueprint, un fil qui se construit message par
message jusqu'à la confirmation. Ce qui change, c'est qu'un appel n'a pas de
loader : le travail visible de la machine, ici, c'est l'onde vocale qui bat.
Elle remplace le théâtre de chargement, et elle est déjà notre symbole.

Scene 1 (0,00–1,00 s) : papier nu. Sur « Vokio » (0,04) les cinq barres du
symbole entrent depuis le centre en expansion vers l'extérieur
(`center-outward-expansion`) et se posent en haut de la zone utile. Sur
« décroche » (0,49) elles s'animent : hauteurs qui varient, barre centrale en
solaire, mouvement interne fini (`svg-icon-enrichment`). C'est le symbole qui
parle, pas une carte qui respire.

Scene 2 (1,00–2,40 s) : la bulle de l'agent se déplie sous l'onde
(`card-morph-anchor`, décélération longue). Son texte arrive en deux morceaux,
sur les mots : « Le Comptoir des Lices, bonjour. » sur 1,00–1,36, puis **« Je suis
l'assistante vocale de l'entreprise. »** sur 1,80–2,80. Cette seconde moitié
reçoit un `asr-keyword-glow` solaire qui s'allume exactement sur « qui elle
est » (2,45) et retombe. La mention de l'article 50 n'est pas un astérisque de
bas de cadre : c'est le mot que la voix désigne et que l'image allume.

Scene 3 (2,40–5,40 s) : l'onde ralentit et s'immobilise. La bulle du client
arrive en bas à droite, plus petite, « Une table pour quatre, demain midi. », entrée
simple entre 3,00 et 3,40. Puis tout tient jusqu'à 5,40. Seule l'onde garde un
jitter très faible : le reste est mort, et c'est voulu.

Le seul plan où la marque parle. Deux bulles arrivent, dans cet ordre : celle de
l'agent, puis celle du client. La première porte la mention légale, et elle est
**montrée, jamais prononcée** : « Le Comptoir des Lices, bonjour. Je suis l'assistante
vocale de l'entreprise. » Article 50 réglé par l'image, ce qui est aussi plus
convaincant qu'une voix off qui l'affirmerait. La deuxième est la vraie demande
entendue sur la démo du site : « Une table pour quatre, demain midi. »

L'onde vocale de marque bat pendant la bulle de l'agent et s'immobilise dès que
le client parle. C'est là qu'elle entre dans le film ; elle en ressortira au CTA.

## Frame 4 — La réservation se pose

- type: feature_showcase
- blueprint: panel-edit-live-sync
- scene: Le fil à gauche, le livre de réservations à droite ; la demande comprise fait apparaître un créneau réel
- duration: 6.0s
- transition_in: cut
- status: outline
- voiceover: "Elle comprend la demande, regarde votre service, pose la réservation."
- asset_candidates: none
- handoff_out: carte du créneau « jeudi 8 h 30 » posée x 62 % y 48 %, échelle 1, opacité 1, immobile
- persuasion: la preuve mécanique
- beat: ce n'est pas un répondeur
- blueprint: panel-edit-live-sync (Adapt)
- focal: la carte de réservation
- roles: fil hérité = supporting · grille du livre de réservations = background · carte = cutout
- sfx: none
- src: compositions/frames/04-agenda.html

Adapt : le couple panneau-surface du blueprint est ici conversation-réservations, et
le « contrôle manipulé » n'est pas un curseur mais la compréhension de l'agent.
La signature reste intacte : ce qui se passe à gauche modifie la droite **dans
le même temps**, et les deux restent visibles en permanence.

Toutes les mesures de la grille et de la carte viennent de `references/agenda-reel.md`,
relevées sur le vrai écran client. La plus importante : la réservation se pose
en **0,18 s, en `ease`, sans retombée**. Un ressort sur cet objet trahirait la
reconstruction d'un seul coup d'œil.

Scene 1 (0,00–0,95 s) : le livre de réservations seul, pleine largeur, marges de 72 px. Les
filets d'heures se tracent de haut en bas (`svg-path-draw`) sur « comprend la
demande, » (0,28–0,92). Le rail d'heures garde sa largeur, qui est une
constante de l'écran réel ; c'est la colonne du jour qui s'étire.

Scene 2 (0,95–2,70 s) : sur « regarde » (1,51) un liseré solaire descend la
colonne du jour (`viewport-change`, verrouillage doux sur la bande 8 h–10 h) et
s'arrête sur la ligne de 12:30 sur « service, » (2,18). Rien d'autre ne bouge
pendant ce temps : un seul objet en mouvement, c'est ce qui rend le geste
lisible.

Scene 3 (2,70–4,20 s) : sur « pose » (2,70) la carte se pose — translation
courte depuis le haut jusqu'à sa ligne, 0,18 s, `ease`, **aucun rebond**. Elle
porte « Mme Vasseur » en ligne 1 et « 12:30 · Table pour 4 » en ligne 2,
exactement la disposition du vrai écran. Sur « réservation. » (2,89) le liseré
s'éteint, la carte reste.

Scene 4 (4,20–6,00 s) : temps de repos. Le livre de réservations tient, immobile, 1,8 s.
Aucun re-push de caméra, aucune respiration. C'est le plan qui convainc, il a
besoin d'être lu, pas animé.

Le plan qui doit convaincre : ce n'est pas un répondeur, c'est un livre de réservations qui
bouge. Trois appuis calés sur les trois virgules de la phrase — comprend /
regarde / pose. Le couple gauche-droite reste visible en permanence, c'est le
lien entre les deux qui est le produit. Le créneau qui se pose est une vraie
heure ouvrable, pas une case qui clignote.

## Frame 5 — Les deux confirmations

- type: feature_showcase
- blueprint: comparison-split
- scene: Deux reçus entrent des deux bords : le SMS du client à gauche, le récapitulatif du restaurant à droite
- duration: 5.6s
- transition_in: cut
- status: outline
- voiceover: "Le client reçoit sa confirmation. Vous recevez le récapitulatif."
- asset_candidates: none
- persuasion: le reçu
- beat: les deux bouts de la chaîne
- blueprint: comparison-split (Reproduce)
- focal: les deux cartes
- roles: carte client = cutout · carte restaurant = cutout
- sfx: none
- src: compositions/frames/05-preuve.html

Reproduce : les créneaux du blueprint accueillent nos deux reçus sans rien
forcer. Deux objets de poids égal, un par bord, inclinaisons miroir, puis la
pastille de ponctuation sur le bord intérieur de chacun. La phrase a deux
moitiés symétriques, le plan aussi.

Scene 1 (0,00–1,05 s) : papier nu. Sur « Le client reçoit sa confirmation. »
(0,04–1,05) la carte de gauche entre depuis le bord gauche avec son inclinaison
`rotationY` miroir (`split-tilt-cards`, décélération longue) et se pose à plat.
C'est le SMS : « Réservation confirmée, vendredi 12 h 30. Le Comptoir des Lices. » avec
« 02:09 » en `mono-data`.

Scene 2 (1,05–2,90 s) : la carte de gauche tient, immobile. Le silence de la
voix entre 1,05 et 2,16 est tenu à l'écran, il n'est pas comblé. Sur « Vous »
(2,16) la carte de droite entre depuis le bord droit, inclinaison miroir de la
première : le récapitulatif restaurant, « Table pour 4 · quatre couverts, en terrasse »,
« jeudi 8 h 30 », « 02:09 ».

Scene 3 (2,90–4,30 s) : sur « récapitulatif. » (2,98) une pastille solaire se
pose sur le bord intérieur de chaque carte, « Client » à gauche, « Vous » à
droite, en `micro-label`. C'est la ponctuation du blueprint et le seul usage du
solaire du plan.

Scene 4 (4,30–5,60 s) : temps de repos, deuxième et dernier. Immobile.

La phrase a deux moitiés symétriques, le plan aussi. Deux objets de poids égal,
chacun entrant de son côté, chacun horodaté en Geist Mono. Rien ne bouge après.
C'est le plan de repos du film : la preuve n'a pas besoin d'être agitée.

## Frame 6 — Ne ratez plus un seul appel

- type: cta
- blueprint: logo-assemble-lockup
- scene: L'onde vocale se resserre, sa barre solaire monte et devient le point du i de Vokio
- duration: 4.0s
- transition_in: cut
- status: outline
- voiceover: "Vokio. Ne ratez plus un seul appel."
- asset_candidates: assets/symbole-onde.svg
- persuasion: l'adresse
- beat: le logo se termine
- blueprint: logo-assemble-lockup (Adapt)
- focal: assets/symbole-onde.svg
- roles: onde = cutout · wordmark = cutout · ligne d'adresse = supporting
- sfx: none
- captions: none
- src: compositions/frames/06-cta.html

Adapt : le blueprint demande que la marque **vienne à exister** à l'écran. On
garde ça entièrement, mais au lieu d'assembler un logo à partir de morceaux
quelconques, on le fait naître de l'objet qui a porté tout le film. Les cinq
barres de l'onde se réduisent à une, et cette barre devient le point du i. Le
mouvement n'appartient qu'à Vokio : aucune autre marque ne peut le faire.

Le point solaire se pose à **left 63,5 %** du glyphe, la valeur du site, pas
60,6 % : c'est une erreur déjà commise et corrigée ailleurs, elle ne se
recommence pas ici.

Scene 1 (0,00–0,75 s) : l'onde revient au centre, à la taille du plan 3, barres
encore vivantes. Sur « Ne ratez plus » (0,03–0,46) les quatre barres d'encre
s'abaissent et s'effacent **une par une, de l'extérieur vers l'intérieur**.

Scene 2 (0,75–1,60 s) : seule la barre solaire reste debout. Sur « un seul
appel. » (0,73–1,13) elle se contracte en point et monte se poser
(`card-morph-anchor`, décélération longue, aucun rebond) pendant que « Vokio »
s'écrit en `display` sous elle. Le i arrive **sans son point** ; le point vient
d'en haut et le complète. Les deux mouvements se croisent, ils ne se suivent pas.

Scene 3 (1,60–2,80 s) : « Ne ratez plus un seul appel. » se révèle en
`headline-sm` sous le wordmark, juste après la fin de la voix, décélération
longue.

Scene 4 (2,80–4,00 s) : une seule ligne `mono-data` apparaît dessous,
« vokio.fr · Votre numéro ne change pas », puis tout tient jusqu'à la dernière
image. Le point solaire reçoit **une** pulsation, finie, comme sur le site.
Trois blocs, rien d'autre, et la dernière seconde est parfaitement immobile.

Le seul mouvement de marque du film, et il n'appartient qu'à Vokio : les cinq
barres de l'onde vocale se resserrent, les quatre barres d'encre s'effacent, et
la barre centrale orange remonte se poser en point sur le i du mot Vokio. Le
logo n'arrive pas, il se termine.

Dessous, la phrase du brief puis l'adresse. « Votre numéro ne change pas » en
micro-label : c'est l'objection la plus fréquente, et elle tient en cinq mots.
Aucun numéro de téléphone.
