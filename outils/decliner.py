#!/usr/bin/env python3
"""Décline le film de référence dans un autre métier, en une commande.

    outils/decliner.py restaurant            prépare et rend
    outils/decliner.py restaurant --sans-rendu   s'arrête avant l'encodage

Le principe : `metiers/plombier.json` décrit le film de référence, chaîne par
chaîne. Un autre fichier du même dossier décrit les mêmes clés pour un autre
métier. Le script substitue l'un par l'autre, régénère la voix, recale les
sous-titres sur les nouveaux horodatages, puis assemble.

Ce qui n'est PAS une substitution bête, et pourquoi :

- L'accroche du plan 01 est découpée en un `<span>` par mot, chacun révélé sur
  le mot réellement prononcé. Une nouvelle accroche n'a ni le même nombre de
  mots ni le même minutage : le script reconstruit les spans ET leur table de
  temps à partir de la voix qu'il vient de produire.
- La salutation du plan 03 est découpée pareil, mais ses temps ne viennent pas
  de la voix (elle n'est pas prononcée) : ils sont répartis sur la même fenêtre.
- Le rail d'heures de l'agenda est une liste : le rendez-vous se pose toujours
  sur la troisième étiquette + 30 min, donc la géométrie ne bouge jamais, même
  si le restaurant travaille à midi et le plombier à 8 h.

Toute substitution est comptée. Si une chaîne attendue n'est pas trouvée le
bon nombre de fois, le script s'arrête au lieu d'écrire un film à moitié
traduit : c'est le seul garde-fou qui tienne quand les plans évoluent.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import voix  # le choix du moteur vit là, pas ici

# Sans ça, les `print` du script sortent par blocs quand la sortie est
# redirigée, et la relecture imprimée par langue.py apparaît AVANT les étapes
# qui l'ont précédée : un journal qui ment sur l'ordre des choses.
sys.stdout.reconfigure(line_buffering=True)

RACINE = Path("/opt/vokio-ads")
REF = RACINE / "videos/vokio-promo"
ENV = {"PATH": "/opt/node22/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
       "HYPERFRAMES_PYTHON": "/root/.venvs/hyperframes/bin/python", "HOME": "/root"}


def typo_fr(s):
    """Espaces insécables là où le français les impose.

    « vendredi 12 h 30 » se coupait entre « 12 h » et « 30 » en fin de ligne
    sur le reçu du plan 05. Une heure ne se coupe pas, et un espace fine
    insécable devant les deux-points non plus.
    """
    s = re.sub(r"(\d)\s+h\s+(\d)", "\\1\u00a0h\u00a0\\2", s)
    s = re.sub(r"(\d)\s+h\b", "\\1\u00a0h", s)
    return s


def lire(nom):
    f = RACINE / "metiers" / f"{nom}.json"
    if not f.is_file():
        dispo = ", ".join(sorted(p.stem for p in (RACINE / "metiers").glob("*.json")))
        raise SystemExit(f"métier inconnu : {nom}\nDisponibles : {dispo}")
    return json.loads(f.read_text())


def remplacer(chemin, paires):
    """Substitution comptée. Une occurrence manquante arrête tout.

    `attendu = None` veut dire « toutes les occurrences, au moins une ». C'est
    pour la prose : dans les notes de conception un même mot revient un nombre
    de fois qui change à chaque relecture du gabarit, et compter les
    occurrences d'un paragraphe reviendrait à casser la déclinaison à chaque
    virgule ajoutée. Le « au moins une » garde le garde-fou qui compte : une
    tournure disparue du gabarit s'arrête toujours ici.
    """
    t = chemin.read_text()
    for av, ap, attendu in paires:
        n = t.count(av)
        if (attendu is None and n == 0) or (attendu is not None and n != attendu):
            raise SystemExit(
                f"{chemin.name} : « {av[:48]} » trouvé {n} fois, "
                f"{'au moins 1' if attendu is None else attendu} attendu(es).\n"
                "Le gabarit a changé depuis le dernier passage : mettre à jour decliner.py.")
        t = t.replace(av, ap)
    chemin.write_text(t)


def couper_en_deux(mots):
    """Équilibre une phrase sur deux lignes, au plus près en nombre de signes."""
    if len(mots) < 2:
        return mots, []
    total = sum(len(m) for m in mots)
    acc, coupe = 0, 1
    for i in range(1, len(mots)):
        acc += len(mots[i - 1])
        if acc >= total / 2:
            coupe = i
            break
    return mots[:coupe], mots[coupe:]


def rebatir_accroche(projet, phrase, temps):
    """Plan 01 : les spans de la ligne 1 et leur table de temps, refaits.

    Un mot, un span, un horodatage. Le découpage en deux rangs est recalculé :
    « Les mains / sous un évier. » n'a pas la même coupe que « Les mains dans
    le service. »
    """
    f = projet / "compositions/frames/01-accroche.html"
    t = f.read_text()
    mots = phrase.split()
    r1, r2 = couper_en_deux(mots)

    def span(i, mot):
        return ('          <span class="f01-w" data-layout-allow-overlap '
                f'id="01-accroche-l1-w{i}">{mot}</span>')

    rangs = []
    i = 0
    for rang in (r1, r2):
        if not rang:
            continue
        corps = "\n".join(span(i + k, m) for k, m in enumerate(rang))
        rangs.append(f'        <span class="f01-row">\n{corps}\n        </span>')
        i += len(rang)
    bloc = "\n".join(rangs)

    ouvre = t.index('<span class="f01-measure">',
                    t.index('    <div class="f01-line f01-line-1"')) + len('<span class="f01-measure">')
    ferme = t.index("      </span>\n    </div>", ouvre)
    t = t[:ouvre] + "\n" + bloc + "\n" + t[ferme:]

    lignes = [f'        {{ id: "01-accroche-l1-w{k}", at: {temps[k]:.2f} }},'
              for k in range(min(len(mots), len(temps)))]
    deb = t.index('        { id: "01-accroche-l1-w0", at:')
    fin = t.index('        { id: "01-accroche-l2-w0", at:')
    t = t[:deb] + "\n".join(lignes) + "\n" + t[fin:]
    f.write_text(t)
    return len(mots)


def rebatir_salutation(projet, phrase):
    """Plan 03 : la salutation de l'agent, découpée en mots, temps répartis."""
    f = projet / "compositions/frames/03-decroche.html"
    t = f.read_text()
    mots = phrase.split()
    gab = '<span class="f03-decroche-w1">__MOT__</span>'
    neuf = " ".join(g.replace("__MOT__", m) for g, m in zip([gab] * len(mots), mots))
    deb = t.index('<div class="f03-decroche-say f03-decroche-l1">') + len(
        '<div class="f03-decroche-say f03-decroche-l1">')
    fin = t.index("</div>", deb)
    t = t[:deb] + neuf + t[fin:]
    f.write_text(t)
    return len(mots)


def aligner_storyboard(projet):
    """Recopie les répliques de SCRIPT.md dans le storyboard.

    Elles y étaient en double, et la déclinaison n'en traduisait qu'une : le
    film parlait bien restaurant, parce que la voix se fabrique depuis
    SCRIPT.md, mais son storyboard racontait encore une fuite sous un évier.
    Personne ne l'a vu pendant six montages. Le document qui sert de référence
    à toute l'équipe ne peut pas être celui qui ment.
    """
    s = (projet / "SCRIPT.md").read_text()
    dits = {}
    for bloc in re.split(r"\n## ", s)[1:]:
        m = re.search(r"\(Frame (\d+)\)", bloc)
        if not m:
            continue
        lignes = [l[4:].strip() for l in bloc.splitlines()
                  if l.startswith("    ") and l.strip()]
        if lignes:
            dits[int(m.group(1))] = " ".join(lignes)
    sb = projet / "STORYBOARD.md"
    texte, plan, n = sb.read_text(), 0, 0
    sorties = []
    for ligne in texte.splitlines():
        m = re.match(r"^## Frame (\d+)", ligne)
        if m:
            plan = int(m.group(1))
        if re.match(r"^\s*-\s*voiceover:", ligne) and plan in dits:
            sorties.append(f'- voiceover: "{dits[plan]}"')
            n += 1
        else:
            sorties.append(ligne)
    sb.write_text("\n".join(sorties) + ("\n" if texte.endswith("\n") else ""))
    return n


def lancer(cmd, cwd, titre, env_plus=None, echo=None):
    """`echo` remonte les lignes du sous-processus qui comptent pour nous.

    Le moteur audio journalise sur la sortie d'erreur, qu'on avale en cas de
    succès. Or la voix réellement employée par ligne ne s'y lit que là : sans
    ce filtre, « une voix par plan » resterait une affirmation invérifiable
    dans le journal de montage.
    """
    print(f"· {titre}")
    r = subprocess.run(cmd, cwd=cwd, env={**ENV, **(env_plus or {})},
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f"échec : {titre}")
    if echo:
        for l in (r.stdout + r.stderr).splitlines():
            if re.search(echo, l):
                print("  " + l.strip())
    return r.stdout


a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
a.add_argument("metier")
a.add_argument("--source", default="plombier")
a.add_argument("--sans-rendu", action="store_true")
a.add_argument("--voix", default=None, help="force une voix ; par défaut celle de voix.json")
a = a.parse_args()

src, cible = lire(a.source), lire(a.metier)
projet = RACINE / f"videos/vokio-{cible['metier']}"

if projet.exists():
    shutil.rmtree(projet)
shutil.copytree(REF, projet, ignore=shutil.ignore_patterns(
    "renders", "snapshots", ".media", "capture", "audio_meta.json",
    "audio_engine_meta.json", "caption_groups.json"))
print(f"· projet {projet.name} créé depuis {REF.name}")

# ── Les chaînes entières ─────────────────────────────────────────────────────
F = projet / "compositions/frames"
lex_src, lex_cible = src.get("lexique", {}), cible.get("lexique", {})
if set(lex_src) != set(lex_cible):
    raise SystemExit(f"lexiques incompatibles : {sorted(set(lex_src) ^ set(lex_cible))}")

remplacer(projet / "SCRIPT.md", [
    (lex_src["doc_creneau"], lex_cible["doc_creneau"], 1),
    (lex_src["doc_titre"], lex_cible["doc_titre"], 1),
    (lex_src["doc_recap"], lex_cible["doc_recap"], 1),
    (lex_src["vo_agenda"], lex_cible["vo_agenda"], 1),
    (lex_src["vo_pose"], lex_cible["vo_pose"], 1),
    (src["accroche"], cible["accroche"], 1),
    (src["etablissement"], cible["etablissement"], 1),
    (src["demande_client"], cible["demande_client"], 1),
    # Plus de substitution du jour ici : sa seule occurrence dans SCRIPT.md
    # était celle du créneau, que `doc_creneau` traduit désormais en entier.
    # Le compteur l'a signalé au premier passage, comme prévu.
])
# Les notes de conception du storyboard décrivent le film plan par plan. Elles
# ne s'entendent ni ne se voient, mais c'est le document que lit quiconque
# reprend le film : un storyboard de restaurant qui raconte une fuite sous un
# évier envoie la personne suivante dans le mur. Du plus spécifique au plus
# général, sinon une tournure courte mange la longue qui la contient.
notes_src, notes_cible = src.get("lexique_notes", {}), cible.get("lexique_notes", {})
if set(notes_src) != set(notes_cible):
    raise SystemExit(f"notes incompatibles : {sorted(set(notes_src) ^ set(notes_cible))}")
ordre = ["n_sms", "n_recap_contenu", "n_carte_client", "n_recap_de", "n_recap_carte",
         "n_mot_surface", "n_mot_pose", "n_carte", "n_carte_focal",
         "n_surface_seule", "n_surface_grille", "n_surface_couple",
         "n_surface_preuve", "n_surface_tient", "n_surface",
         "n_titre_pose", "n_pose_min", "n_audience", "n_ligne_heure"]
if set(ordre) != set(notes_src):
    raise SystemExit(f"ordre des notes à revoir : {sorted(set(ordre) ^ set(notes_src))}")
remplacer(projet / "STORYBOARD.md",
          [(f"metier: {src['metier']}", f"metier: {cible['metier']}", 1)]
          + [(notes_src[k], notes_cible[k], None) for k in ordre]
          + [(src["accroche"].rstrip("."), cible["accroche"].rstrip("."), None),
             (src["demande_client"].rstrip("."), cible["demande_client"].rstrip("."), None),
             (src["confrere"], cible["confrere"], None),
             (src["client_nom"], cible["client_nom"], None),
             (src["etablissement"], cible["etablissement"], None)])
remplacer(F / "01-accroche.html", [(src["heure_appel"], cible["heure_appel"], 1)])
remplacer(F / "02-probleme.html", [(src["heure_appel"], cible["heure_appel"], 1),
                                   (src["confrere"], cible["confrere"], 2)])
remplacer(F / "03-decroche.html", [(src["demande_client"], cible["demande_client"], 1)])
remplacer(F / "04-agenda.html", [
    (src["client_nom"], cible["client_nom"], 1),
    (f'>{src["rail"][2][:2]}:30</span> · {src["motif"]}',
     f'>{cible["rail"][2][:2]}:30</span> · {cible["motif"]}', 1),
    (f'>{src["jour"]}</div>', f'>{cible["jour"]}</div>', 1),
])
# Le rail ne peut PAS passer par des substitutions en chaîne : si la cible
# commence à 10:00 et que la source finit à 10:00, le deuxième remplacement
# retrouve ce que le premier vient d'écrire. On vise chaque étiquette par son
# identifiant, en une seule passe.
rail_f = F / "04-agenda.html"
rail_t = rail_f.read_text()
for i, h in enumerate(cible["rail"]):
    motif = re.compile(r'(id="04-agenda-hour-%d"[^>]*>)[^<]*(</div>)' % i)
    rail_t, n = motif.subn(lambda m: m.group(1) + h + m.group(2), rail_t)
    if n != 1:
        raise SystemExit(f"04-agenda.html : étiquette d'heure {i} introuvable ({n} fois)")
rail_f.write_text(rail_t)
remplacer(F / "05-preuve.html", [
    (lex_src["sms_confirme"], lex_cible["sms_confirme"], 1),
    (f'>{lex_src["badge_client"]}<', f'>{lex_cible["badge_client"]}<', 1),
    (src["jour_texte"], typo_fr(cible["jour_texte"]), 2),
    (src["etablissement"], cible["etablissement"], 1),
    (src["motif"], cible["motif"], 1),
    (src["adresse"], cible["adresse"], 1),
    (src["heure_sms"], cible["heure_sms"], 2),
])
n = aligner_storyboard(projet)
print(f"· chaînes substituées · {n} réplique(s) recopiée(s) dans le storyboard")

# ── La voix, puis les mots recalés dessus ────────────────────────────────────
moteur, voix_id, env_voix = voix.choisir(force=a.voix)
# La distribution ne vaut que pour ElevenLabs : les identifiants de voix de
# Kokoro n'ont rien à voir, et une exception posée sur le repli local
# produirait une ligne dans une voix inexistante.
repartition = voix.distribution() if moteur == "elevenlabs" and not a.voix else {}
if repartition:
    env_voix = {**env_voix, "HF_VOICE_BY_LINE": json.dumps(repartition)}
if moteur == "elevenlabs":
    env_voix = {**env_voix, **voix.reglages_moteur()}
titre = f"voix off ({moteur} · {voix_id}"
titre += f" · plan(s) {', '.join(sorted(repartition))} à part)" if repartition else ")"
lancer(["node", str(RACINE / ".agents/skills/product-launch-video/scripts/audio.mjs"),
        "--script", "./SCRIPT.md", "--storyboard", "./STORYBOARD.md", "--hyperframes", ".",
        "--out", "./audio_meta.json", "--provider", moteur, "--voice", voix_id],
       projet, titre, env_voix, echo=r"line \d+: voix ")

# audio.mjs classe un échec de synthèse en « anomalie non fatale » et SORT EN
# 0. Le 23/09, les six lignes ont échoué ensemble (mauvais interpréteur python)
# et rien n'a bronché : sans ce contrôle, un film MUET traverse tout le
# montage, passe la vérification, et se livre.
attendu = len(re.findall(r"^\s*-?\s*voiceover:", (projet / "STORYBOARD.md").read_text(), re.M))
produit = json.loads((projet / "audio_meta.json").read_text()).get("voices", [])
if len(produit) != attendu:
    raise SystemExit(
        f"voix off incomplète : {len(produit)} ligne(s) produite(s) sur {attendu}.\n"
        f"Le moteur était « {moteur} », voix « {voix_id} ».\n"
        "Relancer outils/rustines.py, puis la synthèse à la main pour voir l'erreur.")
print(f"· voix off complète ({attendu} lignes)")
lancer(["python3", str(RACINE / "outils/recaler_mots.py"), str(projet), "--ecrire"],
       projet, "mots recalés sur le script")

# APRÈS le recalage, jamais avant : à la sortie du moteur, audio_meta.json
# porte les fichiers mais pas encore les mots, que recaler_mots y écrit. Placé
# plus haut, le tempo accélérait bien les sons et ne divisait aucun
# horodatage — les sous-titres auraient dérivé de 15 % en retard croissant,
# sans qu'aucun contrôle ne bronche.
if moteur == "elevenlabs":
    # Quelle voix a servi sur quel plan : le tempo se règle par voix, pas par
    # plan, puisque c'est « la partie d'Ingrid » qu'on accélère.
    attribution = {n: repartition.get(f"{n:02d}", voix_id) for n in range(1, 40)}
    voix.poser_tempo(projet, attribution)
    voix.poser_ancres(projet, voix.ancres())

# ── Les deux phrases découpées en mots ───────────────────────────────────────
meta = json.loads((projet / "audio_meta.json").read_text())
l1 = next(v for v in meta["voices"] if v["frame"] == 1)
n = rebatir_accroche(projet, cible["accroche"], [w["start"] for w in l1["words"]])
m = rebatir_salutation(projet, f'{cible["etablissement"]}, bonjour.')
print(f"· accroche rebâtie ({n} mots, sur la voix) · salutation rebâtie ({m} mots)")

# ── La langue du métier, avant le rendu ──────────────────────────────────────
# Après la reconstruction de l'accroche, pas avant : elle se cale sur les
# horodatages de la voix, donc à l'écran elle parle encore plombier jusqu'ici.
# Et avant monter.sh, pour qu'un mot du mauvais métier ne coûte pas un rendu.
# La relecture s'imprime en entier, et volontairement à l'écran plutôt que
# dans un journal : c'est le seul contrôle qu'aucune machine ne sait faire, et
# il tombe juste avant le rendu, au dernier moment où corriger coûte trois
# minutes au lieu d'une livraison.
print("· langue du métier")
if subprocess.run(["python3", str(RACINE / "outils/langue.py"), a.metier, "--strict"],
                  cwd=projet, env=ENV).returncode != 0:
    raise SystemExit("échec : langue du métier")

# ── Montage ──────────────────────────────────────────────────────────────────
sortie = lancer(["./monter.sh"] + ([] if a.sans_rendu else ["--rendre"]), projet, "montage")
for l in sortie.splitlines():
    if "error(s)" in l or "rendered in" in l or "WCAG" in l:
        print("   " + l.strip())
print(f"\n{projet}/renders/" if not a.sans_rendu else f"\n{projet} prêt, rendu non lancé")
