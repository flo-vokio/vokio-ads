#!/usr/bin/env python3
"""Prépare la fiche d'une nouvelle verticale, avec tous ses trous à remplir.

    outils/nouveau_metier.py coiffure

Pourquoi passer par un gabarit plutôt que copier une fiche existante : copier
une fiche, c'est repartir des mots d'un autre métier, et c'est exactement ce
qui a produit « Les mains dans le service » calqué sur « Les mains sous un
évier ». Le gabarit sort une fiche où chaque valeur à écrire porte `TODO`, et
`outils/langue.py` REFUSE de monter tant qu'il en reste un. Le prérequis ne
dépend donc pas de la mémoire de celui qui décline.

Le code du métier est celui du produit (`verticals.code`), le même que dans
`/opt/vokio-n8n/verticals/<code>.md` : une verticale porte un seul nom, de
l'agent vocal jusqu'à la pub. Ce fichier-là, quand il existe, est la
meilleure source pour le vocabulaire : il dit déjà comment le métier parle.
"""
import argparse
import json
from pathlib import Path

RACINE = Path("/opt/vokio-ads")
FICHES = RACINE / "metiers"
REFERENCE = "plombier"
REGLES_PRODUIT = Path("/opt/vokio-n8n/verticals")


def gabarit(ref):
    """Même forme que la référence, aucune de ses valeurs."""
    def vider(v):
        if isinstance(v, str):
            return "TODO"
        if isinstance(v, list):
            return ["TODO"] * len(v)
        if isinstance(v, dict):
            return {k: vider(x) for k, x in v.items()}
        return v

    f = {}
    for k, v in ref.items():
        if k.startswith("_"):
            f[k] = v          # les notes de la référence expliquent chaque clé
        elif k == "vocabulaire":
            f[k] = {"interdits": {"TODO": "TODO"}, "attendus": ["TODO"]}
        else:
            f[k] = vider(v)
    return f


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("code", help="code de la verticale, celui de verticals.code")
    a = a.parse_args()

    cible = FICHES / f"{a.code}.json"
    if cible.exists():
        raise SystemExit(f"{cible} existe déjà.")
    ref = json.loads((FICHES / f"{REFERENCE}.json").read_text())
    f = gabarit(ref)
    f["metier"] = a.code
    cible.write_text(json.dumps(f, ensure_ascii=False, indent=2) + "\n")

    print(f"{cible}\n")
    regles = REGLES_PRODUIT / f"{a.code}.md"
    if regles.is_file():
        print(f"Le produit connaît déjà cette verticale : {regles}")
        print("C'est la meilleure source pour le vocabulaire, elle dit comment")
        print("le métier parle. À lire AVANT de remplir la fiche.\n")
    else:
        print(f"Aucune règle produit pour « {a.code} » ({regles} absent).")
        print("La verticale n'existe peut-être pas encore côté agent vocal :")
        print("vérifier le code avant d'aller plus loin.\n")
    print("Ensuite :")
    print(f"  outils/langue.py {a.code}        dit ce qu'il reste à écrire")
    print(f"  outils/decliner.py {a.code}      refuse tant qu'il reste un TODO")
