# vokio-ads

Pubs Vokio en motion design, rendues par [HyperFrames](https://hyperframes.heygen.com) :
une composition HTML dont la timeline se déplace image par image, encodée en MP4.

## La règle d'or

Toute commande passe par l'enveloppe, jamais `npx hyperframes` en direct :

```bash
/opt/vokio-ads/bin/hf <commande>
```

La machine tourne sous Node 20 pour le reste de ses services et HyperFrames
exige Node 22. L'enveloppe met `/opt/node22` en tête de PATH pour elle seule et
pointe `HYPERFRAMES_PYTHON` vers le venv qui porte Kokoro. `/usr/bin/node` ne
bouge pas.

---

## Décliner dans un nouveau métier

C'est le geste courant. Une commande :

```bash
outils/decliner.py restaurant
```

Elle crée `videos/vokio-restaurant/`, substitue les chaînes, régénère la voix
off, recale les sous-titres sur les nouveaux horodatages, assemble et rend le
MP4. Compter trois minutes.

### L'ordre des étapes, et pourquoi c'est cet ordre-là

La moitié des défauts payés dans ce dépôt venaient d'une étape juste, placée au
mauvais endroit. Aucune ne s'était plainte : elles produisaient un film faux.

| # | étape | pourquoi là |
| --- | --- | --- |
| 1 | copie du gabarit | `renders`, `snapshots` et les trois fichiers de métadonnées audio sont exclus : un reste de montage précédent ferait croire à une voix produite |
| 2 | substitution des chaînes, puis **recopie de `SCRIPT.md` dans le storyboard** | voir « un texte en double » plus bas |
| 3 | synthèse de la voix off | lit `SCRIPT.md`, déjà traduit |
| 4 | **contrôle « voix off complète »** | `audio.mjs` sort en 0 même quand rien n'a été synthétisé |
| 5 | `recaler_mots.py` | impose les mots du script aux minutages de Whisper |
| 6 | tempo par voix, puis ancres | **jamais avant 5** : les mots n'existent dans `audio_meta.json` qu'une fois que 5 les y a écrits |
| 7 | reconstruction de l'accroche et de la salutation | l'accroche se découpe sur les horodatages définitifs, donc après 6 |
| 8 | **`langue.py --strict`** | après 7, sinon l'accroche à l'écran parle encore le métier source ; avant 9, pour qu'un mot du mauvais métier ne coûte pas un encodage |
| 9 | `monter.sh --rendre` | |

Un métier = un `metiers/<code>.json`. **Ne jamais partir d'une fiche
existante** : `outils/nouveau_metier.py <code>` sort un gabarit à la bonne
forme et sans aucune valeur, pour la raison expliquée plus bas. Les champs :

| clé | ce que c'est |
| --- | --- |
| `accroche` | la première réplique, plan 01. **Prononcée**, et découpée mot à mot à l'écran. |
| `etablissement` | le commerce fictif. Plans 03 et 05. |
| `demande_client` | ce que dit l'appelant, plan 03. |
| `motif` | le motif du rendez-vous, plans 04 et 05. Court : il tient sur une ligne de carte. |
| `confrere` | ce que portent les deux rangs de la liste, plan 02. « Artisan suivant », « Restaurant suivant »… |
| `client_nom`, `adresse` | la fiche du rendez-vous. |
| `jour`, `jour_texte` | le jour affiché, en capitales sur l'agenda et en toutes lettres sur le reçu. |
| `rail` | les **cinq** étiquettes d'heures de l'agenda. Le rendez-vous se pose toujours sur la troisième + 30 min, donc la géométrie ne bouge jamais : un restaurant peut travailler à midi et un plombier à 8 h. |
| `heure_appel`, `heure_sms` | l'horodatage de la pastille d'appel et des deux reçus. |
| `lexique` | **le vocabulaire de la verticale**. Un restaurant ne dit pas « rendez-vous », il dit « réservation ». |

### Le lexique : des phrases, jamais des mots

`lexique` porte des **phrases entières** et c'est délibéré. « le rendez-vous »
devient « la réservation » : le genre change. « Rendez-vous confirmé » devient
« Réservation confirmée » : l'accord change. Substituer le mot « rendez-vous »
par « réservation » produirait des fautes dans les deux cas.

C'est la même discipline que les prompts de l'agent vocal, où aucun mot de
métier n'est écrit en dur. Une pub qui parle de rendez-vous à un restaurateur
sonne comme un logiciel générique, ce que Vokio n'est pas.

Le lexique traverse `SCRIPT.md`, donc il change la voix off, donc il change
les sous-titres : tout se régénère seul. Les deux fiches doivent déclarer les
**mêmes clés**, sinon le script s'arrête.

**Chaque substitution est comptée.** Si une chaîne attendue n'est pas trouvée le
bon nombre de fois, le script s'arrête au lieu d'écrire un film à moitié
traduit. C'est le seul garde-fou qui tienne quand les plans évoluent : le jour
où quelqu'un retouche un plan, la déclinaison échoue bruyamment au lieu de
sortir un MP4 faux.

Deux phrases ne sont pas de simples substitutions, et le script les reconstruit :

- **l'accroche du plan 01** est un `<span>` par mot, chacun révélé sur le mot
  réellement prononcé. Une nouvelle accroche n'a ni le même nombre de mots ni
  le même minutage : les spans, leur répartition sur deux lignes et leur table
  de temps sont refaits à partir de la voix qui vient d'être produite ;
- **la salutation du plan 03** est découpée pareil, mais elle n'est pas
  prononcée : ses temps sont répartis sur la même fenêtre.

---

## Les trois projets, et lequel on livre

| dossier | ce que c'est |
| --- | --- |
| `videos/vokio-promo/` | **le gabarit, qu'on ne livre pas.** C'est lui que `decliner.py` copie |
| `videos/vokio-plombier/` | une déclinaison, comme les autres depuis le 23/09 |
| `videos/vokio-restaurant/` | une déclinaison |

Le plombier a longtemps été le gabarit **et** un film livrable à la fois. Tant
qu'il l'était, il ne passait pas les contrôles de langue qu'il imposait aux
autres : on ne vérifie pas une traduction contre elle-même. Le gabarit est
désormais neutre et le plombier se produit comme n'importe quel métier.

Refaire un film sans rien décliner :

```bash
cd videos/vokio-plombier
./monter.sh            # sous-titres, musique, assemblage, transitions, contrôle
./monter.sh --rendre   # et le MP4
```

Le nom de sortie suit le champ `metier:` du storyboard, donc une déclinaison
n'écrase jamais une autre. Les MP4 se livrent **par le Drive de Florian ou en
SSH**, jamais par un lien public. Une seule version par métier sur le Drive :
trois restaurants côte à côte ont déjà fait croire à un défaut de montage qui
n'existait pas.

## La musique

`assets/musique.mp3` est un silence de 30 s : la piste existe et se valide déjà.

```bash
./poser_musique.sh ~/mon-morceau.wav
./monter.sh --rendre
```

Le script le normalise à -26 LUFS avec fondus, pour qu'il passe **sous** la voix.

## La voix off

Deux moteurs, un seul point de décision : `outils/voix.py`. **Si le coffre
contient une clé ElevenLabs dédiée aux pubs, la voix vient d'ElevenLabs ;
sinon elle vient de Kokoro, en local.** Aucun script d'assemblage n'écrit le
nom d'un moteur en dur, tous appellent `voix.choisir()`. La bascule ne
demande donc pas de modifier une ligne de code, et le retrait de la clé ne
casse pas le montage.

```bash
outils/voix.py                  # ce qui serait utilisé, et pourquoi
outils/voix.py --catalogue      # les voix du compte
```

Le choix d'une voix a sa section plus bas, « Choisir une voix, c'est
l'écouter ».

**Déposer la clé** (en SSH, jamais en conversation ni par un outil) :

```bash
install -m 600 /dev/null /root/.secrets/vokio-ads-elevenlabs
read -rs K && printf '%s' "$K" > /root/.secrets/vokio-ads-elevenlabs; unset K
```

`read -rs` n'affiche rien et ne laisse rien dans l'historique du shell, au
contraire d'un `echo sk_... >`.

Il faut une clé **dédiée**, pas celle de production : cette dernière sait
synthétiser mais n'a pas `voices_read`, donc impossible de parcourir le
catalogue pour choisir une voix ; et sa consommation est surveillée au titre
du coût par appel client, une pub qui s'y mélange fausse le suivi. Droits
nécessaires sur la nouvelle clé : **Text to Speech** et **Voices: read**.

### Le modèle et la direction de voix

Le moteur écrivait `eleven_multilingual_v2` **en dur** et n'envoyait aucun
`voice_settings`. La direction écrite dans `SCRIPT.md` ne décorait donc que le
document. `voix.json` porte maintenant les deux :

```json
"modele": "eleven_multilingual_v2",
"reglages": { "stability": 0.30, "style": 0.55, "speed": 1.12 }
```

Le compte accepte aussi `eleven_v3`, plus expressif, mais qui **ignore la
vitesse** : mesuré sur la même phrase, v2 raccourcit de 9,6 % à `speed 1.12`,
v3 de 1,5 %. Tant que le débit est le sujet, rester sur v2.

Chaque ligne était aussi synthétisée **isolément**, donc l'intonation repartait
de zéro à chaque plan : six annonces bout à bout, ce qui s'entend exactement
comme une machine. Le moteur reçoit désormais la ligne d'avant et celle
d'après, qu'il ne prononce pas mais qui lui donnent la cadence. La continuité
s'arrête à un changement de voix : donner à la signature le texte du narrateur
lui ferait imiter sa cadence.

### Deux voix dans le même film

`voix.json` porte la distribution : une voix par défaut pour le corps du film,
et des exceptions plan par plan.

```json
"voice":    "FFXYdAYPzn8Tw8KiHZqg",                 // Ingrid, le récit
"par_plan": { "6": "LFtQZWdaqmvamcTNGpwl" }         // Lucie · Narration, la signature
```

Le dernier plan dit « Vokio. Ne ratez plus un seul appel. » La signature de
marque n'est pas dite par la même bouche que le récit : c'est ce qui la fait
entendre comme une signature et non comme une phrase de plus.

Le moteur ne résolvait qu'une voix pour tout le film ; la rustine « une voix
par plan » lui fait lire `HF_VOICE_BY_LINE`. Le journal de montage écrit la
voix réellement employée sur chaque ligne d'exception, pour que la
distribution soit un fait vérifiable et pas une intention. Elle l'a été : un
film livré a été cru muet d'une de ses voix, et c'est le journal plus le
`voice_id` de `audio_engine_meta.json` qui ont tranché, pas l'oreille.

**Trois « Lucie » traînent dans le compte.** `LFtQZWdaqmvamcTNGpwl`
(« Lucie · Narration ») n'a rien à voir avec `YxrwjAKoUKULGd0g8K9Y`
(« Lucie · Support Agent »), la voix des agents qui décrochent au téléphone.
Vérifier l'identifiant, jamais le prénom.

### Choisir une voix, c'est l'écouter

Les étiquettes du catalogue ne disent rien du timbre réel. Le seul protocole
qui tienne : faire dire à plusieurs voix **le texte du film**, bout à bout,
et écouter.

```bash
outils/voix.py --bibliotheque --genre female --cherche narration
outils/voix.py --essai "<le texte du film>" --sur ID,ID,ID    # comparer
outils/voix.py --essai "<texte>" --modele eleven_v3 \
               --reglages '{"speed":1.12}' --etiquette d-v3-x1.12
outils/voix.py --retenir <id>
```

`--etiquette` n'est pas un confort : sans elle, deux réglages de la même voix
sur le même modèle écrivent le **même nom de fichier** et la deuxième prise
écrase la première en silence. C'est arrivé.

Les prises atterrissent dans `essais/`, hors dépôt et régénérables. Ce qui a
été écarté, pour ne pas y revenir : **Yariq** (voix masculine, jugée « cheap et
très IA »), **Manon** et **Lucie · Narration** en voix de corps (justes mais sans
élan). **Ingrid** a été retenue, avec une réserve de Florian qui vaut
consigne : *« lent et robotique »*. D'où la direction de voix, la continuité
entre les lignes, et le débit, ci-dessous. Les trois traitaient la même plainte.

Une voix de la **bibliothèque publique** doit d'abord entrer dans le compte.
`outils/voix.py --ajouter <id> --nom "<nom>"` sait le faire, mais la clé n'a
pas le droit `voices_write` : l'API refuse, et c'est Florian qui l'ajoute d'un
clic depuis l'interface. Une fois ajoutée, elle est utilisable normalement.

### Le débit d'une voix, et le calage sur l'image

```json
"tempo_par_voix":  { "FFXYdAYPzn8Tw8KiHZqg": 1.15 },
"ancres_par_plan": { "4": {"mot": -1, "a": 2.70}, "6": {"mot": 0, "a": 0.76} }
```

`tempo_par_voix` accélère **après** la synthèse. Le réglage `speed` de l'API
plafonne et vaut pour la requête entière : il ne sait pas accélérer une voix
sans toucher à l'autre. `atempo` conserve la hauteur, et les horodatages des
mots se divisent par le même facteur.

`ancres_par_plan` vise **un mot et un instant de l'animation**, jamais un
silence écrit en dur. Une amorce fixe se démode dès qu'on change de voix ou de
débit, et personne ne le voit avant de regarder le film. L'indice de mot vaut
pour tous les métiers, la phrase ayant la même forme partout, alors que le mot
change : `-1` désigne « le rendez-vous » chez le plombier et « la réservation »
au restaurant. Le monteur posant chaque voix au début de son plan sans
décalage possible, l'attente va dans le fichier son.

- plan 4 : le dernier mot se dit quand la carte se pose, à 2,70 s
- plan 6 : « Vokio » se dit quand le mot finit de s'écrire, à 0,76 s

Un mot ne peut être que **retardé**. Si la voix le dit déjà après son repère,
l'outil le signale au lieu de tricher.

**Les deux passent APRÈS `recaler_mots.py`, jamais avant.** À la sortie du
moteur, `audio_meta.json` porte les fichiers mais pas encore les mots. Placé
plus haut, le tempo accélérait bien les sons et ne divisait aucun horodatage :
les sous-titres auraient dérivé de 15 % en retard croissant, sans qu'aucun
contrôle ne bronche.

`voix.json` garde l'identifiant retenu. Il vaut `null` au départ, et
`voix.choisir()` **refuse de produire** tant qu'il vaut `null` alors qu'une
clé est présente : sans ce garde-fou le film sortirait avec la voix anglaise
par défaut d'ElevenLabs, sans la moindre erreur, et personne ne le verrait
avant l'écoute.

Le montage ne contient **aucune durée écrite en dur** : il se recale sur les
horodatages du nouveau fichier. `decliner.py --voix <id>` force une voix pour
un seul film, sans toucher au réglage.

`outils/recaler_mots.py` garde les minutages de Whisper et lui impose les mots
de `SCRIPT.md` : sans lui les sous-titres affichent « Vocuez au » pour
« Vokio » et perdent la ponctuation, qui commande leur découpage.

---

## La langue de la verticale

```bash
outils/langue.py restaurant          contrôles + relecture
outils/langue.py --toutes            toutes les fiches
```

Le film se décline par substitution, et c'est exactement le danger : le
mécanisme est fidèle. Il a produit **« Les mains dans le service »**, calqué
mot à mot sur « Les mains sous un évier » du plombier. La phrase passe tous
les contrôles techniques, se prononce parfaitement, et ne veut rien dire.

`outils/langue.py` vérifie ce qu'une machine peut vérifier :

- **les mots d'un autre métier** — un restaurant n'a pas d'« agenda » et ne
  prend pas de « rendez-vous ». Déclarés par fiche dans `vocabulaire.interdits`,
  avec le mot à dire à la place. **Bloquant** ;
- **les champs jamais réécrits**, identiques à la fiche de référence ;
- **les calques de structure** — un champ d'au moins quatre mots qui garde les
  deux premiers de la référence. C'est le contrôle qui aurait attrapé la
  phrase ci-dessus. Un calque voulu se déclare dans `_calques_admis` ;
- **le vocabulaire attendu**, qui doit apparaître quelque part.

Le contrôle ne relit que **ce qui se voit ou s'entend** : les répliques du
storyboard et le texte des compositions, balises et scripts retirés. Le
premier jet relisait les fichiers entiers et sortait soixante alertes sur
l'identifiant CSS `04-agenda` — une alerte qu'on apprend à ignorer ne protège
plus rien.

Et ce qu'une machine ne peut pas vérifier, c'est si une phrase *sonne juste*
dans un métier. D'où la **relecture** : l'outil imprime en un écran tout ce
que le film dit et tout ce qu'il montre. Ça se lit à voix haute.

### C'est un prérequis, pas un conseil

`decliner.py` l'appelle en `--strict` **après la reconstruction de l'accroche
et avant le rendu** : l'accroche à l'écran n'existe qu'une fois la voix faite,
et un mot du mauvais métier ne doit pas coûter un encodage pour se faire voir.
La relecture s'imprime **en entier**, à l'écran, à ce moment-là. C'est le
dernier instant où corriger coûte trois minutes au lieu d'une livraison.

Une fiche neuve ne peut pas passer entre les mailles :

```bash
outils/nouveau_metier.py coiffure    # gabarit où chaque valeur porte TODO
```

Le gabarit sort une fiche à la forme de la référence et **sans aucune de ses
valeurs**. Copier une fiche existante, ce serait repartir des mots d'un autre
métier, ce qui est précisément l'origine de « Les mains dans le service ».
`langue.py` refuse tant qu'il reste un `TODO`, et refuse aussi une fiche sans
`vocabulaire.interdits`, sans `vocabulaire.attendus`, ou à qui il manque une
clé de `lexique` / `lexique_notes`. **Un prérequis qui n'arrête pas le montage
n'est pas un prérequis, c'est un conseil.**

Quand `/opt/vokio-n8n/verticals/<code>.md` existe, le gabarit le signale : ce
fichier dit déjà comment le métier parle, c'est la meilleure source pour
remplir le vocabulaire.

Les codes métier sont ceux du produit (`verticals.code`), pour qu'une verticale
porte le même nom dans l'agent vocal et dans la pub.

### Les notes de conception suivent aussi le métier

Le storyboard décrit le film plan par plan. Rien de tout ça ne se voit ni ne
s'entend, mais **c'est le document que lit quiconque reprend le film** : un
storyboard de restaurant qui raconte une fuite sous un évier envoie la
personne suivante dans le mur.

`lexique_notes` porte ces phrases, mêmes clés d'une fiche à l'autre. Toujours
des phrases entières : « l'agenda » ne devient pas « le service » mot à mot,
il devient « le livre de réservations », et la préposition qui le précède
change avec lui. Les substitutions vont du plus spécifique au plus général,
sinon une tournure courte mange la longue qui la contient.

Deux réglages évitent les fausses alertes :

- `vocabulaire.toleres` — les citations et les **chemins de fichier** où le
  mot d'un autre métier est légitime. `references/agenda-reel.md` ne se
  traduit pas, sous peine de casser le chemin ;
- le contrôle de calque saute `lexique.*` et `lexique_notes.*`, qui sont
  **délibérément** parallèles d'un métier à l'autre.

Et `attendu = None` dans `remplacer()` veut dire « toutes les occurrences, au
moins une » : dans la prose, compter les occurrences d'un paragraphe
casserait la déclinaison à chaque virgule ajoutée au gabarit.

## Le piège du film muet

`audio.mjs` classe un échec de synthèse en « anomalie non fatale » et **sort
en 0**. Le 23/09 les six lignes ont échoué ensemble, parce que la voie
ElevenLabs exécute son extrait python en direct et tombait sur le python du
système, sans le paquet `elevenlabs` : Kokoro n'avait jamais rien vu, lui
passe par `npx hyperframes tts` qui lit `HYPERFRAMES_PYTHON` tout seul.

Deux garde-fous depuis, et il en fallait deux : la rustine
« interpréteur python imposé » supprime la cause, et `decliner.py` compte les
lignes produites contre les `voiceover:` du storyboard et **s'arrête** si le
compte n'y est pas. Le premier peut sauter à la prochaine mise à jour des
skills ; le second, non.

## Après toute mise à jour des skills

```bash
outils/rustines.py            # dit ce qui manque
outils/rustines.py --poser    # réapplique
```

**Huit** défauts des skills HyperFrames livrées sont corrigés dans
`.agents/skills/`, et `hyperframes skills update` les réécrirait.

| # | rustine | ce qui se passe sans elle |
| --- | --- | --- |
| 1 | shims media-use | deux fichiers réexportent un chemin du dépôt amont qui n'existe pas dans une installation normale |
| 2 | langue transmise au moteur | le moteur retombe sur « en », donc sur Whisper `small.en`, **qui traduit** : la ligne 3 est revenue un jour en « Thank you for watching and see you next week » |
| 3 | fr-fr contre fr | un seul champ `lang` alimente deux vocabulaires incompatibles, le phonémiseur veut `fr-fr` et Whisper veut `fr` |
| 4 | bande de sous-titres réglable | la bande occupe les 320 px du bas, zone interdite par la charte et couverte par l'interface de Reels |
| 5 | sous-titres : opt-out et regroupement | un plan dont le texte à l'écran **est** la phrase prononcée ne peut pas refuser la bande, et les groupes durent une demi-seconde |
| 6 | interpréteur python imposé | `HYPERFRAMES_PYTHON` est ignoré, ElevenLabs tombe sur le python du système et **échoue sur les six lignes** |
| 7 | voix par plan et continuité | une seule voix pour tout le film, et chaque ligne synthétisée isolément |
| 8 | modèle et direction de voix | `eleven_multilingual_v2` écrit en dur, aucun `voice_settings` envoyé |

**Cinq de ces huit ne se voient pas** : elles ne cassent rien, elles produisent
un film faux, muet ou robotique. C'est la raison d'être de `rustines.py`, qui
vérifie la présence de chacune avant de la reposer.

---

## Les pièges déjà payés

1. **Ne jamais lancer `audio.mjs sync-durations` sur ces projets.** Il écrase
   la durée d'un plan par celle de sa voix. Ici il ramènerait le film de 30,0 s
   à 18,8 s et supprimerait tous les silences, qui sont la moitié du montage.
2. **La langue doit descendre jusqu'au moteur**, sinon il traduit. Voir les
   rustines.
3. **Ce qui doit bouger ne bouge pas toujours.** Le moteur avance image par
   image : une valeur écrite depuis un `onUpdate` peut rester muette, et le
   plan sort figé sans qu'aucun contrôle ne s'en plaigne. Vérifier par **écart
   d'images** sur le MP4, pas dans le code.
4. **La bande de sous-titres par défaut est dans la zone interdite** (y 1600 à
   1920) : c'est là que Reels et TikTok dessinent leur interface, et la charte
   Vokio interdit tout texte important sous y=1500. `monter.sh` la remonte.
5. **Une erreur de lint désactive silencieusement les audits** de mise en page
   et de contraste : le rapport devient vert sans que rien n'ait tourné.
   `monter.sh` efface d'abord les fichiers de sonde que les ouvriers laissent
   à la racine, qui sont la cause habituelle.
6. **Un texte en double finit toujours par diverger.** Les répliques vivaient
   dans `SCRIPT.md` **et** dans `STORYBOARD.md`, et la déclinaison ne
   traduisait que la première. Le film parlait juste, la voix se fabriquant
   depuis `SCRIPT.md` ; mais le storyboard du restaurant racontait une fuite
   sous un évier depuis six montages, et c'est le document que lit la
   personne suivante. `decliner.py` recopie désormais `SCRIPT.md` dans le
   storyboard, et dit combien de répliques il a recopiées.
7. **Un traitement d'horodatage placé trop tôt ne se plaint pas.** Le tempo
   posé avant `recaler_mots.py` accélérait les sons sans diviser un seul
   horodatage : sous-titres en retard croissant de 15 %, zéro erreur. Tout ce
   qui touche aux minutages passe après lui. Voir le tableau des étapes.
8. **Le catalogue de voix ment sur les prénoms et les prises s'écrasent.**
   Trois « Lucie » sans rapport dans le compte, et deux réglages de la même
   voix produisaient le même nom de fichier d'essai. Identifiant, jamais
   prénom ; `--etiquette` sur chaque prise.

---

## Ce qui reste à faire

**Le 1:1 et le 16:9.** Les plans 02 et 04 sont écrits en pixels absolus pour un
cadre 1080x1920, les autres en unités relatives à la largeur. Changer de ratio
demande donc une passe de mise en page par plan, pas un drapeau de rendu :
`--resolution` n'accepte qu'un multiple entier du **même** ratio. Le travail
est réel et il n'est pas commencé.

**La musique et l'ambiance de salle.** Florian fournit les morceaux ; la piste
existe déjà en silence et se valide (voir plus haut).

**Le contraste des deux voix.** Ingrid et Lucie sont deux voix féminines.
Le risque, signalé et non tranché : que le changement s'entende comme un
raccord raté plutôt que comme une signature. Ça se juge à l'oreille, pas ici.

**Le ménage du Drive.** Sept films de restaurant et de plombier s'y
accumulent, la plupart périmés. Attendre le mot de Florian : ce sont ses
fichiers.

**Les métiers.** Deux fiches existent, `plombier` et `restaurant`. Chaque
nouvelle verticale passe par `nouveau_metier.py`, jamais par la copie d'une
fiche voisine.

## Les outils

| outil | ce qu'il fait |
| --- | --- |
| `bin/hf` | l'enveloppe Node 22. Toute commande HyperFrames passe par elle |
| `outils/decliner.py <metier>` | le geste courant : un métier, un MP4. `--voix <id>` force une voix pour ce film seulement, `--sans-rendu` s'arrête avant l'encodage, `--source <metier>` change le gabarit |
| `outils/nouveau_metier.py <code>` | un gabarit de fiche, toutes valeurs à `TODO` |
| `outils/langue.py <metier>` | le contrôle de langue et la relecture. `--toutes`, `--strict` (bloquant), `--sans-relecture` |
| `outils/voix.py` | le moteur, le catalogue, les essais, la distribution, le débit, les ancres |
| `outils/recaler_mots.py <projet>` | impose les mots de `SCRIPT.md` aux minutages de Whisper. `--ecrire` pour appliquer |
| `outils/rustines.py` | l'état des huit correctifs. `--poser` les réapplique |
| `outils/piste_musique.py` | déclare l'emplacement musique dans `audio_meta.json`. Le storyboard porte `music: none` pour que le moteur n'aille pas piocher dans un catalogue, donc l'assembleur n'écrirait aucune piste. `monter.sh` le relance après chaque régénération de la voix |

## Les fichiers d'un projet

| Fichier | Rôle |
| --- | --- |
| `BRIEF.md` | l'intention, et les règles éditoriales qui ne se négocient pas |
| `SCRIPT.md` | la narration verrouillée, une section par ligne parlée |
| `STORYBOARD.md` | les six plans, leurs durées, la séquence chronométrée de chacun, et le bloc `## Video direction` qui tient tout le film ensemble |
| `frame.md` | le système visuel : couleurs, rampe typographique, composants |
| `references/agenda-reel.md` | les mesures relevées sur le vrai agenda client |
| `compositions/frames/` | un fichier HTML par plan |
| `index.html` | le montage, écrit par l'assembleur, **jamais à la main** |
