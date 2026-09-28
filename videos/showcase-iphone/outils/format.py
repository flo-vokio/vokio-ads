#!/usr/bin/env python3
"""Produit un projet RENDABLE du film pour un format (16x9, 1x1…) sans dupliquer les scènes à la main.

    python3 outils/format.py 16x9 [--dossier D] [--variante s7-signature=16x9-x | --variante '*=16x9-x'] [--sans-construire]
                             [--check] [--snapshots 3.5,21,46.9 | --planche] [--rendu film.mp4] [--empreinte ref.json]

  1. copie la source (index.html, compositions/, lib/, assets/, outils/banc*.html) dans D (défaut formats/<format>/),
     en ne réécrivant que ce qui a changé (idempotent) et en retirant ce que la source n'a plus ; seules transformations,
     mécaniques et comptées (une règle qui ne trouve pas son motif ARRÊTE tout) : la taille du cadre dans index.html
     (data-width/data-height de la racine et des sept hôtes, viewport, html/body) et sur la racine de chaque scène ;
  2. calcule les données du format : outils/preparer_agenda.py --format puis outils/construire.py --format --racine D
     (mesures dans le moteur de HyperFrames, trajets du point, contrôles) → D/donnees/ ;
  3. signale les px du 9:16 restés en dur dans les scènes copiées (liste « à paramétrer ») ;
  4. options : --check (hf check, rapport D/rapports/check.json), --snapshots t,t (hf snapshot → D/snapshots/),
     --planche (snapshots aux images clés du storyboard + planche avec les zones sûres du format → D/snapshots/planche.png ;
     --images <dossier> pour les écrire ailleurs ; --vues 852,393 : la même planche à la taille réelle d'affichage, sans zones),
     --rendu film.mp4 (hf render, sous flock /tmp/hf-rendu.lock), --empreinte ref.json (rendu sans perte, empreintes
     image par image comparées à ref.json : outils/identite.py ; code 1 si une image diffère), --entrees git:HEAD (dialogue
     et mots du dernier commit au lieu de ceux, peut-être en chantier, du dossier son/ : le minutage du film reste figé).
     SANS --entrees (le chemin normal) : son/dialogue.json et donnees/mots.json de l'arbre de travail de ce projet (ceux
     qu'écrivent son/dialogue.py et outils/mots.py) ; c'est ainsi que le 16:9 de 50,07 s a été construit le 28/09, avant commit.
  --variante '*=<nom>' : un JEU, la variante de ce nom dans chaque fichier de mise-en-page/ qui l'a (outils/mise_en_page.py ; passé
  aussi à preparer_agenda.py, qui pose l'agenda du format).
  Le 9:16 EST ce projet (python3 outils/construire.py) ; « format.py 9x16 --dossier /dev/shm/x --empreinte
  formats/empreintes-9x16.json » reconstruit une copie de contrôle et prouve qu'elle rend le film à l'image près (1 502 images
  depuis l'échange du prénom du 28/09, ~4 min ; disque sous 1,2 Gio libres : le rendu passe par /dev/shm, outils/rendre.py). Chemin court sans MP4 :
  « python3 outils/identite.py prouver /dev/shm/x HEAD » (≈ 145 instants par snapshots, ~2 min).
Règle : on n'édite JAMAIS un fichier de D (il est régénéré) : on édite la source, mise-en-page/*.json ou la scène.
"""
import argparse
import filecmp
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mise_en_page  # noqa: E402

PROJET = Path(__file__).resolve().parents[1]
HF = "/opt/vokio-ads/bin/hf"
VERROU = "/tmp/hf-rendu.lock"
SOURCES = ["index.html", "compositions", "lib", "assets", "outils/banc.html", "outils/banc-film.html"]
IGNORER = {"__pycache__"}
REF = (1080, 1920)
# Images clés du storyboard (s film) : une par idée de scène, choisies sur DONNEES.evenements du film de 47,00 s (film de BASE),
# portées dans le film courant par outils/temps.py (son/dialogue.json « insertions » : + 3,066667 s après 25,2667 depuis
# l'échange du prénom) ; « s5 prénom attendu » est né de l'insertion (film courant : la plume en suspens pendant la question).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import temps  # noqa: E402
_T = temps.Insertions.depuis(PROJET / "son" / "dialogue.json")
PLANCHE = sorted([(nom, round(_T.t(t), 3)) for nom, t in
                  [("s1 accroche + relance", 3.5), ("s2 Élise, page 2", 7.0), ("s3 tamis fait", 14.8), ("s4 point sur 10:00", 21.5),
                   ("s5 bloc écrit", 26.6), ("s6 SMS ouvert", 38.0), ("s7 signature", 46.9)]]
                 + ([("s5 prénom attendu", 27.2)] if any(i["id"] == "prenom" for i in _T.liste) else []), key=lambda x: x[1])


def regles(W, H):
    """(fichier glob, motif, remplacement, nombre attendu par fichier : int exact ou '+' au moins un)."""
    if (W, H) == REF:
        return []
    return [
        ("index.html", 'data-width="1080" data-height="1920"', f'data-width="{W}" data-height="{H}"', 8),
        ("index.html", '<meta name="viewport" content="width=1080, height=1920">', f'<meta name="viewport" content="width={W}, height={H}">', 1),
        ("index.html", "html,body{width:1080px;height:1920px;", f"html,body{{width:{W}px;height:{H}px;", 1),
        ("compositions/*.html", 'data-width="1080" data-height="1920"', f'data-width="{W}" data-height="{H}"', 1),
    ]


# px du 9:16 qu'une scène ne devrait plus porter en dur (la géométrie vient de DONNEES.geometrie / DONNEES.format)
SUSPECTS = [
    (re.compile(r"\b(1080|1920)px"), "taille du cadre 9:16"),
    (re.compile(r"(?<![\d.])1500(?![\d.])"), "bas utile 9:16 (1500)"),
    (re.compile(r"(?<![\d.])1010(?![\d.])"), "marge droite 9:16 (1010)"),
    (re.compile(r"(left|top|right|bottom):\s*\d+(\.\d+)?px"), "position CSS en dur"),
]


def copier(dest, W, H):
    changes, retires = [], []
    R = regles(W, H)
    fichiers = []
    for s in SOURCES:
        p = PROJET / s
        if p.is_dir():
            fichiers += [f for f in p.rglob("*") if f.is_file() and not (set(f.relative_to(PROJET).parts) & IGNORER)]
        elif p.exists():
            fichiers.append(p)
    voulus = set()
    for f in fichiers:
        rel = f.relative_to(PROJET)
        voulus.add(rel)
        cible = dest / rel
        cible.parent.mkdir(parents=True, exist_ok=True)
        propres = [r for r in R if Path(rel).match(r[0])]
        if propres:
            t = f.read_text()
            for _, motif, remp, n in propres:
                c = t.count(motif)
                if c != n:
                    raise SystemExit(f"format.py : {rel} : « {motif} » trouvé {c} fois, {n} attendu(s) — la source a changé, "
                                     "mettre à jour regles() de outils/format.py")
                t = t.replace(motif, remp)
            if not cible.exists() or cible.read_text() != t:
                cible.write_text(t); changes.append(str(rel))
        elif not cible.exists() or not filecmp.cmp(f, cible, shallow=False):
            shutil.copy2(f, cible); changes.append(str(rel))
    for s in SOURCES:
        d = dest / s
        if d.is_dir():
            for f in d.rglob("*"):
                if f.is_file() and f.relative_to(dest) not in voulus:
                    f.unlink(); retires.append(str(f.relative_to(dest)))
    (dest / ".gitignore").write_text("# Projet de format GÉNÉRÉ par outils/format.py : seules les données du format se versionnent.\n"
                                     "/*\n!/.gitignore\n!/LISEZMOI.txt\n!/donnees/\n")
    (dest / "LISEZMOI.txt").write_text(
        "Projet GÉNÉRÉ par outils/format.py depuis videos/showcase-iphone : ne rien éditer ici, tout est réécrit.\n"
        "Éditer la source (compositions/, lib/, mise-en-page/*.json) puis relancer : python3 outils/format.py <format>\n"
        "Rendu : flock /tmp/hf-rendu.lock /opt/vokio-ads/bin/hf render <ce dossier> -o film.mp4 --quiet\n")
    return changes, retires


def sans_commentaires(t):
    """Blanchit les commentaires /* */ et <!-- --> (les sauts de ligne restent : numéros de ligne intacts)."""
    blanc = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r"<!--.*?-->", blanc, re.sub(r"/\*.*?\*/", blanc, t, flags=re.S), flags=re.S)


def a_parametrer(dest):
    """Les px du 9:16 restés en dur dans les scènes, hors commentaires et hors lignes marquées « repli 9:16 » (valeur de
    secours du CSS que le script réécrit d'après DONNEES.geometrie) : la liste de ce qui reste à paramétrer."""
    out = {}
    for f in sorted((dest / "compositions").glob("*.html")):
        brut = f.read_text().splitlines()
        for k, ligne in enumerate(sans_commentaires(f.read_text()).splitlines(), 1):
            if "repli 9:16" in brut[k - 1] or "repli" in brut[k - 1].split("//")[-1]:
                continue
            code = re.sub(r"//.*$", "", ligne)
            for rx, quoi in SUSPECTS:
                for m in rx.finditer(code):
                    out.setdefault(f.name, []).append(f"{k}: {quoi} « {m.group(0)} »")
    return out


def lancer(cmd, verrou=False, **kw):
    print("→ " + " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run((["flock", VERROU] if verrou else []) + [str(c) for c in cmd], **kw)
    return r


def planche(snaps, M, instants, sortie, largeur=640, avec_zones=True):
    """Planche des snapshots : chaque image réduite à `largeur` px ; zones sûres et marges dessinées si avec_zones."""
    from PIL import Image, ImageDraw, ImageFont
    dispo = {}
    for f in snaps.glob("*.png"):
        m = re.search(r"at-([0-9.]+)s", f.name)
        if m:
            dispo[float(m.group(1))] = f
    ims = []
    for nom, t in instants:
        proche = min(dispo, key=lambda x: abs(x - t)) if dispo else None
        if proche is None or abs(proche - t) > 0.02:
            print(f"planche : pas d'image à {t} s dans {snaps}"); continue
        im = Image.open(dispo[proche]).convert("RGB")
        dr = ImageDraw.Draw(im, "RGBA")
        for z in (M["format"]["zones"] if avec_zones else []):
            c = (192, 69, 44, 70) if z["sorte"] == "interdite" else (239, 164, 36, 45)
            dr.rectangle(z["boite"], fill=c, outline=c[:3] + (200,), width=3)
        m = M["format"]["marge_laterale"]
        if avec_zones:
            dr.line([(m, 0), (m, im.height)], fill=(38, 32, 25, 90), width=2)
            dr.line([(im.width - m, 0), (im.width - m, im.height)], fill=(38, 32, 25, 90), width=2)
        ims.append((nom, t, im))
    if not ims:
        return None
    k = largeur / ims[0][2].width
    w, h = int(ims[0][2].width * k), int(ims[0][2].height * k)
    cols = 2 if w > h else 4
    rows = (len(ims) + cols - 1) // cols
    try:
        police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        police = ImageFont.load_default()
    feuille = Image.new("RGB", (cols * (w + 16) + 16, rows * (h + 44) + 16), (255, 255, 255))
    d = ImageDraw.Draw(feuille)
    for i, (nom, t, im) in enumerate(ims):
        x, y = 16 + (i % cols) * (w + 16), 16 + (i // cols) * (h + 44)
        feuille.paste(im.resize((w, h), Image.LANCZOS), (x, y + 28))
        d.text((x, y + 4), f"{t:.2f} s · {nom}", fill=(38, 32, 25), font=police)
    feuille.save(sortie)
    return sortie


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("format")
    A.add_argument("--dossier")
    A.add_argument("--variante", action="append", default=[])
    A.add_argument("--sans-construire", action="store_true")
    A.add_argument("--check", action="store_true")
    A.add_argument("--snapshots")
    A.add_argument("--planche", action="store_true")
    A.add_argument("--vues", help="largeurs d'affichage réelles, ex. 852,393 (iPhone en paysage plein écran, fil en portrait, en "
                                  "points) : une planche SANS zones par largeur, planche-vue-<N>.png, pour juger la lisibilité")
    A.add_argument("--images", help="dossier des snapshots et de la planche (défaut : <dossier>/snapshots, vidé à chaque passe)")
    A.add_argument("--rendu")
    A.add_argument("--empreinte")
    A.add_argument("--entrees", help="entrées figées passées à construire.py : un dossier (son/dialogue.json, donnees/mots.json) ou "
                                     "git:<révision> (extraites du dépôt, ex. git:HEAD : le dialogue et les mots du dernier commit)")
    a = A.parse_args()
    var = dict(v.split("=", 1) for v in a.variante)
    M = mise_en_page.charger(a.format, var)
    W, H = M["format"]["largeur"], M["format"]["hauteur"]
    if a.format == "9x16" and not a.dossier:
        raise SystemExit("le 9:16 est ce projet (python3 outils/construire.py) ; pour une copie de contrôle : --dossier <dossier>")
    dest = Path(a.dossier).resolve() if a.dossier else PROJET / "formats" / a.format
    if dest == PROJET:
        raise SystemExit("--dossier ne peut pas être le projet source")
    dest.mkdir(parents=True, exist_ok=True)
    changes, retires = copier(dest, W, H)
    print(f"{dest} : {len(changes)} fichier(s) réécrit(s), {len(retires)} retiré(s)")
    code = 0
    if a.entrees and a.entrees.startswith("git:"):
        rev = a.entrees[4:] or "HEAD"
        fig = dest / ".entrees" / rev.replace("/", "_")
        rel = PROJET.relative_to(Path(subprocess.run(["git", "-C", PROJET, "rev-parse", "--show-toplevel"], capture_output=True,
                                                     text=True, check=True).stdout.strip()))
        for f in ("son/dialogue.json", "donnees/mots.json"):
            (fig / f).parent.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(["git", "-C", PROJET, "show", f"{rev}:{rel / f}"], capture_output=True, check=True)
            (fig / f).write_bytes(r.stdout)
        print(f"entrées figées ({rev}) : {fig}")
        a.entrees = str(fig)
    if not a.sans_construire:
        r = lancer([sys.executable, PROJET / "outils" / "preparer_agenda.py", "--format", a.format,
                    "--sortie", dest / "donnees" / "agenda-geo.json", "--sans-images"]
                   + sum((["--variante", v] for v in a.variante), []))
        if r.returncode:
            raise SystemExit("preparer_agenda.py a échoué")
        r = lancer([sys.executable, PROJET / "outils" / "construire.py", "--format", a.format, "--racine", dest]
                   + sum((["--variante", v] for v in a.variante), []) + (["--entrees", a.entrees] if a.entrees else []))
        if r.returncode:
            code = 1
            print("⚠ construire.py signale des contrôles en échec (voir ci-dessus) : données écrites quand même")
    if a.format != "9x16":
        reste = a_parametrer(dest)
        (dest / "rapports").mkdir(exist_ok=True)
        (dest / "rapports" / "a-parametrer.json").write_text(json.dumps(reste, ensure_ascii=False, indent=1))
        tot = sum(len(v) for v in reste.values())
        print(f"px du 9:16 restés en dur dans les scènes : {tot} ({', '.join(f'{k} {len(v)}' for k, v in reste.items()) or 'aucun'})"
              f" → {dest / 'rapports' / 'a-parametrer.json'}")
    if a.check:
        (dest / "rapports").mkdir(exist_ok=True)
        r = lancer([HF, "check", dest, "--json"], capture_output=True, text=True)
        (dest / "rapports" / "check.json").write_text(r.stdout)
        try:
            j = json.loads(r.stdout)
            print(f"hf check : ok={j.get('ok')} → {dest / 'rapports' / 'check.json'}")
        except json.JSONDecodeError:
            print(r.stdout[-2000:], r.stderr[-2000:])
        code = code or (0 if r.returncode == 0 else 1)
    at = a.snapshots
    if a.planche:
        at = ",".join(f"{t}" for _, t in PLANCHE)
    if at:
        sn = Path(a.images).resolve() if a.images else dest / "snapshots"
        if sn.exists():
            shutil.rmtree(sn)
        r = lancer([HF, "snapshot", dest, "--no-end", "--at", at, "-o", sn, "--describe", "false"], verrou=True)
        code = code or r.returncode
        if a.planche:
            inst = PLANCHE
        else:
            inst = [(f"t = {t}", float(t)) for t in at.split(",")]
        p = planche(sn, M, inst, sn / "planche.png")
        if p:
            print(f"planche : {p}")
        for v in (a.vues.split(",") if a.vues else []):
            p = planche(sn, M, inst, sn / f"planche-vue-{int(v)}.png", largeur=int(v), avec_zones=False)
            if p:
                print(f"planche vue {v} px : {p}")
    if a.rendu:     # outils/rendre.py : sous flock, et dans /dev/shm quand le disque a moins de 1,2 Gio libres
        r = lancer([sys.executable, PROJET / "outils" / "rendre.py", dest, "-o", Path(a.rendu).resolve()])
        code = code or r.returncode
    if a.empreinte:
        out = dest / "rapports" / "empreintes.json"
        (dest / "rapports").mkdir(exist_ok=True)
        r = lancer([sys.executable, PROJET / "outils" / "identite.py", "empreindre", dest, out])
        r = r.returncode or lancer([sys.executable, PROJET / "outils" / "identite.py", "comparer", a.empreinte, out]).returncode
        code = code or r
    return code


if __name__ == "__main__":
    sys.exit(main())
