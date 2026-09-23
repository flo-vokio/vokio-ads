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
    """Substitution comptée. Une occurrence manquante arrête tout."""
    t = chemin.read_text()
    for av, ap, attendu in paires:
        n = t.count(av)
        if n != attendu:
            raise SystemExit(
                f"{chemin.name} : « {av[:48]} » trouvé {n} fois, {attendu} attendu(es).\n"
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


def lancer(cmd, cwd, titre):
    print(f"· {titre}")
    r = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f"échec : {titre}")
    return r.stdout


a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
a.add_argument("metier")
a.add_argument("--source", default="plombier")
a.add_argument("--sans-rendu", action="store_true")
a.add_argument("--voix", default="ff_siwis")
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
remplacer(projet / "SCRIPT.md", [
    (src["accroche"], cible["accroche"], 1),
    (src["etablissement"], cible["etablissement"], 1),
    (src["demande_client"], cible["demande_client"], 1),
    (src["jour"], cible["jour"], 1),
])
remplacer(projet / "STORYBOARD.md", [(f"metier: {src['metier']}", f"metier: {cible['metier']}", 1)])
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
    (src["jour_texte"], typo_fr(cible["jour_texte"]), 2),
    (src["etablissement"], cible["etablissement"], 1),
    (src["motif"], cible["motif"], 1),
    (src["adresse"], cible["adresse"], 1),
    (src["heure_sms"], cible["heure_sms"], 2),
])
print("· chaînes substituées")

# ── La voix, puis les mots recalés dessus ────────────────────────────────────
lancer(["node", str(RACINE / ".agents/skills/product-launch-video/scripts/audio.mjs"),
        "--script", "./SCRIPT.md", "--storyboard", "./STORYBOARD.md", "--hyperframes", ".",
        "--out", "./audio_meta.json", "--provider", "kokoro", "--voice", a.voix],
       projet, "voix off")
lancer(["python3", str(RACINE / "outils/recaler_mots.py"), str(projet), "--ecrire"],
       projet, "mots recalés sur le script")

# ── Les deux phrases découpées en mots ───────────────────────────────────────
meta = json.loads((projet / "audio_meta.json").read_text())
l1 = next(v for v in meta["voices"] if v["frame"] == 1)
n = rebatir_accroche(projet, cible["accroche"], [w["start"] for w in l1["words"]])
m = rebatir_salutation(projet, f'{cible["etablissement"]}, bonjour.')
print(f"· accroche rebâtie ({n} mots, sur la voix) · salutation rebâtie ({m} mots)")

# ── Montage ──────────────────────────────────────────────────────────────────
sortie = lancer(["./monter.sh"] + ([] if a.sans_rendu else ["--rendre"]), projet, "montage")
for l in sortie.splitlines():
    if "error(s)" in l or "rendered in" in l or "WCAG" in l:
        print("   " + l.strip())
print(f"\n{projet}/renders/" if not a.sans_rendu else f"\n{projet} prêt, rendu non lancé")
