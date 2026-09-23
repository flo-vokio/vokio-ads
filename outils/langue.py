#!/usr/bin/env python3
"""Relit une fiche métier avec les mots de son métier, et refuse les calques.

    outils/langue.py restaurant            relecture + contrôles
    outils/langue.py restaurant --strict   sort en erreur si un contrôle dur échoue
    outils/langue.py --toutes              passe toutes les fiches en revue

Pourquoi cet outil existe. Le film se décline par substitution : une fiche
métier remplace les chaînes d'une autre. Le mécanisme est fidèle, et c'est
exactement le danger. Il a produit « Les mains dans le service », calqué mot
à mot sur « Les mains sous un évier » du plombier. La phrase passe tous les
contrôles techniques, se prononce très bien, et ne veut rien dire.

Ce qu'une machine peut vérifier, elle le vérifie ici :

- **les mots d'un autre métier** : un restaurant ne prend pas de
  « rendez-vous » et n'a pas d'« agenda ». C'est mécanique, donc bloquant ;
- **les champs jamais réécrits**, identiques à la fiche de référence ;
- **les calques de structure** : un champ qui garde les premiers mots de la
  référence est presque toujours une traduction paresseuse. C'est le contrôle
  qui aurait attrapé « Les mains dans le service ».

Ce qu'une machine ne peut PAS vérifier, c'est si une phrase *sonne juste*
dans un métier. D'où la relecture : l'outil imprime, en un écran, tout ce que
le film dit et tout ce qu'il montre pour cette verticale. Ça se lit à voix
haute, et c'est là que « les mains dans le service » s'entend.

Les codes métier sont ceux du produit (`verticals.code`), pour qu'une
verticale porte le même nom dans l'agent vocal et dans la pub.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RACINE = Path("/opt/vokio-ads")
FICHES = RACINE / "metiers"
REFERENCE = "plombier"


def lire(nom):
    f = FICHES / f"{nom}.json"
    if not f.is_file():
        dispo = ", ".join(sorted(p.stem for p in FICHES.glob("*.json")))
        raise SystemExit(f"métier inconnu : {nom}\nDisponibles : {dispo}")
    return json.loads(f.read_text())


def champs(fiche, prefixe=""):
    """Tous les textes d'une fiche, aplatis. Les clés en « _ » sont des notes."""
    for k, v in fiche.items():
        if k.startswith("_"):
            continue
        chemin = f"{prefixe}{k}"
        if isinstance(v, str):
            yield chemin, v
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str):
                    yield f"{chemin}[{i}]", x
        elif isinstance(v, dict) and k != "vocabulaire":
            yield from champs(v, f"{chemin}.")


def textes_du_film(nom):
    """Uniquement ce qui se voit ou s'entend. Rien d'autre ne compte.

    Premier jet de cet outil : il relisait les fichiers en entier et sortait
    soixante alertes sur le mot « agenda » — l'identifiant CSS du plan 4, que
    personne ne lit jamais. Une alerte qu'on apprend à ignorer ne protège
    plus rien. On ne garde donc que les répliques du storyboard et le texte
    réellement posé dans les compositions, balises et scripts retirés.
    """
    p = RACINE / "videos" / f"vokio-{nom}"
    if not p.is_dir():
        return []
    out = []
    sb = p / "STORYBOARD.md"
    if sb.is_file():
        for i, d in enumerate(re.findall(r'voiceover: "(.*)"', sb.read_text()), 1):
            out.append((f"voix {i}", d))
    for h in sorted((p / "compositions/frames").glob("*.html")):
        x = h.read_text()
        for motif in (r"(?s)<script.*?</script>", r"(?s)<style.*?</style>",
                      r"(?s)<!--.*?-->", r"<[^>]+>"):
            x = re.sub(motif, " ", x)
        x = re.sub(r"\s+", " ", x).strip()
        if x:
            out.append((h.name, x))
    return out


def notes_du_projet(nom):
    """Les documents de travail : dérive de documentation, jamais bloquante."""
    p = RACINE / "videos" / f"vokio-{nom}"
    return [f for f in (p / "SCRIPT.md", p / "STORYBOARD.md") if f.is_file()]


def mots_interdits(fiche, nom):
    """Le vocabulaire d'un autre métier, dans la fiche et dans le film monté."""
    voc = (fiche.get("vocabulaire") or {}).get("interdits") or {}
    toleres = (fiche.get("vocabulaire") or {}).get("toleres") or []
    if not voc:
        return [], [f"{nom} n'a pas de vocabulaire interdit déclaré"]
    durs, doux = [], []
    vus = set()
    for mot, remede in voc.items():
        if mot == "TODO":
            continue          # fiche à peine créée : `complet` le dit mieux
        motif = re.compile(rf"\b{re.escape(mot)}\w*", re.I)
        for ou, texte in list(champs(fiche, "")) and \
                [(f"fiche · {c}", x) for c, x in champs(fiche, "")]:
            for m in set(motif.findall(texte)):
                if (ou, m) not in vus:
                    vus.add((ou, m))
                    durs.append(f"{ou} : « {m} » → dire « {remede} »")
        for ou, texte in textes_du_film(nom):
            for m in set(motif.findall(texte)):
                if any(c.lower() in texte.lower() for c in toleres):
                    continue
                if (ou, m) not in vus:
                    vus.add((ou, m))
                    durs.append(f"{ou} : « {m} » → dire « {remede} »")
        for f in notes_du_projet(nom):
            for i, ligne in enumerate(f.read_text().splitlines(), 1):
                if any(c.lower() in ligne.lower() for c in toleres):
                    continue
                for m in set(motif.findall(ligne)):
                    doux.append(f"{f.name}:{i} « {m} » — {ligne.strip()[:88]}")
    return durs, doux


def calques(fiche, ref, nom):
    """Champs non réécrits, et champs qui gardent l'ossature de la référence."""
    durs, doux = [], []
    admis = set(fiche.get("_calques_admis") or [])
    plats_ref = dict(champs(ref))
    for chemin, texte in champs(fiche):
        if chemin in admis or chemin in ("metier",):
            continue
        avant = plats_ref.get(chemin)
        if not avant or not isinstance(texte, str):
            continue
        if texte.strip() == avant.strip():
            durs.append(f"{chemin} : identique à {REFERENCE} (« {texte} »)")
            continue
        # Les lexiques sont DÉLIBÉRÉMENT parallèles : « le récapitulatif de
        # l'artisan » et « le récapitulatif du restaurant » partagent leurs
        # premiers mots parce que c'est la même phrase dans deux métiers. Le
        # contrôle de calque ne vise que la rédaction libre.
        if chemin.startswith(("lexique.", "lexique_notes.")):
            continue
        a = re.findall(r"\w+", avant.lower())
        b = re.findall(r"\w+", texte.lower())
        # Seulement sur de vraies phrases : « regarde votre agenda » devient
        # « regarde votre service », deux premiers mots identiques et pourtant
        # parfaitement juste. Le calque se repère sur des phrases plus longues.
        if len(a) >= 4 and len(b) >= 4 and a[:2] == b[:2]:
            durs.append(
                f"{chemin} : calque de {REFERENCE}, mêmes premiers mots\n"
                f"          {REFERENCE} : « {avant} »\n"
                f"          {nom} : « {texte} »")
    return durs, doux


def attendus(fiche, nom):
    """Le vocabulaire propre au métier doit apparaître quelque part."""
    voc = (fiche.get("vocabulaire") or {}).get("attendus") or []
    if not voc:
        return [], []
    tout = " ".join(t for _, t in champs(fiche)).lower()
    tout += " ".join(t for _, t in textes_du_film(nom)).lower()
    absents = [m for m in voc if m.lower() not in tout]
    return [], [f"aucune occurrence de « {m} »" for m in absents]


def complet(fiche, ref, nom):
    """La fiche déclare-t-elle tout ce qu'une verticale doit déclarer ?

    Sans ce contrôle, une fiche neuve sans bloc `vocabulaire` passait avec un
    simple avertissement : la verticale se montait, en silence, avec les mots
    du plombier. Un prérequis qui n'arrête pas le montage n'est pas un
    prérequis, c'est un conseil.
    """
    durs = []
    voc = fiche.get("vocabulaire") or {}
    if not voc.get("interdits"):
        durs.append("vocabulaire.interdits absent : quels mots d'un AUTRE métier "
                    "ne doivent jamais apparaître, et que dire à la place ?")
    if not voc.get("attendus"):
        durs.append("vocabulaire.attendus absent : quels mots propres à ce métier "
                    "doivent apparaître quelque part ?")
    for bloc in ("lexique", "lexique_notes"):
        manque = set(ref.get(bloc) or {}) - set(fiche.get(bloc) or {})
        if manque:
            durs.append(f"{bloc} : clés manquantes {sorted(manque)}")
    restes = [c for c, x in champs(fiche) if "TODO" in x]
    if restes:
        durs.append(f"{len(restes)} valeur(s) jamais écrite(s) : "
                    + ", ".join(restes[:12]) + (" …" if len(restes) > 12 else ""))
    return durs, []


def relecture(fiche, nom):
    print(f"\n── Relecture · {nom} ──────────────────────────────────────────")
    p = RACINE / "videos" / f"vokio-{nom}"
    sb = p / "STORYBOARD.md"
    if sb.is_file():
        dits = re.findall(r'voiceover: "(.*)"', sb.read_text())
        print("\nCe qui se dit :")
        for i, d in enumerate(dits, 1):
            print(f"  {i}. {d}")
    else:
        print(f"\n(pas de film monté dans {p.name}, seulement la fiche)")
    print("\nCe qui s'affiche :")
    for chemin, texte in champs(fiche):
        if chemin in ("metier",):
            continue
        print(f"  {chemin:<22} {texte}")
    print("\nÀ lire à voix haute. Une phrase qui se prononce bien peut ne rien")
    print("vouloir dire dans le métier : c'est le seul contrôle qui l'attrape.\n")


def passer(nom, strict, muet=False):
    fiche, ref = lire(nom), lire(REFERENCE)
    durs, doux = [], []
    for controle in (mots_interdits, attendus):
        d, s = controle(fiche, nom)
        durs += d
        doux += s
    if nom != REFERENCE:
        d, s = complet(fiche, ref, nom)
        durs += d
        doux += s
        d, s = calques(fiche, ref, nom)
        durs += d
        doux += s
    if durs:
        print(f"[BLOQUANT] {nom}")
        for x in durs:
            print(f"  · {x}")
    if doux:
        print(f"[à vérifier] {nom}")
        for x in doux:
            print(f"  · {x}")
    if not durs and not doux:
        print(f"[ok] {nom} — vocabulaire propre, aucun calque")
    if not muet:
        relecture(fiche, nom)
    if durs and strict:
        raise SystemExit(f"\n{nom} : {len(durs)} problème(s) de langue. "
                         "Corriger la fiche avant de monter.")
    return len(durs)


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("metier", nargs="?")
    a.add_argument("--toutes", action="store_true")
    a.add_argument("--strict", action="store_true")
    a.add_argument("--sans-relecture", action="store_true")
    a = a.parse_args()
    if a.toutes:
        total = sum(passer(p.stem, False, a.sans_relecture)
                    for p in sorted(FICHES.glob("*.json")))
        sys.exit(1 if total and a.strict else 0)
    if not a.metier:
        raise SystemExit("préciser un métier, ou --toutes")
    passer(a.metier, a.strict, a.sans_relecture)
