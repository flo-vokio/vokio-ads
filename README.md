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

Pour ajouter un métier, copier `metiers/plombier.json`, changer les valeurs,
enregistrer sous `metiers/<nom>.json` :

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

## Refaire un film sans rien décliner

```bash
cd videos/vokio-promo
./monter.sh            # sous-titres, musique, assemblage, transitions, contrôle
./monter.sh --rendre   # et le MP4
```

Le nom de sortie suit le champ `metier:` du storyboard, donc une déclinaison
n'écrase jamais le film de référence.

## La musique

`assets/musique.mp3` est un silence de 30 s : la piste existe et se valide déjà.

```bash
./poser_musique.sh ~/mon-morceau.wav
./monter.sh --rendre
```

Le script le normalise à -26 LUFS avec fondus, pour qu'il passe **sous** la voix.

## La voix off

Provisoirement locale (Kokoro, voix `ff_siwis`), à remplacer par ElevenLabs.
Le montage ne contient **aucune durée écrite en dur** : il se recale sur les
horodatages du nouveau fichier. `decliner.py` accepte `--voix <id>`.

`outils/recaler_mots.py` garde les minutages de Whisper et lui impose les mots
de `SCRIPT.md` : sans lui les sous-titres affichent « Vocuez au » pour
« Vokio » et perdent la ponctuation, qui commande leur découpage.

---

## Après toute mise à jour des skills

```bash
outils/rustines.py            # dit ce qui manque
outils/rustines.py --poser    # réapplique
```

Cinq défauts des skills HyperFrames livrées sont corrigés dans
`.agents/skills/`, et `hyperframes skills update` les réécrirait. **Trois de
ces cinq ne se voient pas** : ils ne cassent rien, ils produisent un film faux.
Le plus vicieux fait retomber le moteur sur le modèle Whisper anglais, qui
*traduit* la voix française au lieu de la transcrire ; la ligne 3 est revenue
un jour en « Thank you for watching and see you next week ».

---

## Cinq pièges déjà payés

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

---

## Ce qui reste à faire

**Le 1:1 et le 16:9.** Les plans 02 et 04 sont écrits en pixels absolus pour un
cadre 1080x1920, les autres en unités relatives à la largeur. Changer de ratio
demande donc une passe de mise en page par plan, pas un drapeau de rendu :
`--resolution` n'accepte qu'un multiple entier du **même** ratio. Le travail
est réel et il n'est pas commencé.

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
