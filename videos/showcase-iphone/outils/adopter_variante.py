#!/usr/bin/env python3
"""Adopte une variante de mise en page : ses clés passent dans l'entrée du format, la variante disparaît : usage en une ligne :

    python3 outils/adopter_variante.py <scène> <variante> [--format 16x9] [--go]

  <scène> : le nom du fichier mise-en-page/<scène>.json (ex. s6-sms) ; <variante> : une clé de son bloc « variantes »
  (ex. 16x9-centre). --format : l'entrée qui la reçoit (défaut : le début du nom de la variante, « 16x9 » pour « 16x9-centre »).
  Sans --go : n'écrit rien, imprime les clés résolues qui changeraient (outils/mise_en_page.py charger, avant / après).
  Avec --go : fusion récursive de la variante dans l'entrée (la même que mise_en_page.fusion, les clés « _ » exceptées), sa
  note gardée dans l'entrée sous « _variante_adoptee » (datée), variante retirée (et « variantes » si vide), fichier réécrit en
  forme compacte (mise_en_page.ecrire) ; puis contrôle : la mise en page résolue du format SANS variante est exactement celle
  qu'on avait AVEC. Idempotent : une variante déjà adoptée (absente, clés déjà dans l'entrée) ne fait rien.
  Ensuite : reconstruire le format (python3 outils/format.py <format> --check : dialogue et mots de l'arbre de travail ;
  --entrees git:HEAD pour ceux du dernier commit) ; le 9:16 n'est jamais touché.
"""
import argparse
import copy
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mise_en_page as M  # noqa: E402


def aplatir(o, pre=""):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            out.update(aplatir(v, f"{pre}.{k}" if pre else k))
        return out
    return {pre: o}


def contient(entree, var):
    return all(k.startswith("_") or (isinstance(v, dict) and isinstance(entree.get(k), dict) and contient(entree[k], v))
               or entree.get(k) == v for k, v in var.items())


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("scene")
    A.add_argument("variante")
    A.add_argument("--format")
    A.add_argument("--go", action="store_true")
    a = A.parse_args()
    nom = a.scene + ".json"
    fmt = a.format or a.variante.split("-")[0]
    d = M.lire(nom)
    var = (d.get("variantes") or {}).get(a.variante)
    if var is None:
        print(f"{nom} : aucune variante « {a.variante} » (déjà adoptée ou retirée) ; rien à faire")
        return 0
    if fmt not in d:
        raise SystemExit(f"{nom} n'a pas d'entrée « {fmt} » (--format)")
    if contient(d[fmt], var):
        print(f"{nom} : l'entrée « {fmt} » contient déjà toutes les clés de « {a.variante} »")
    avant = M.sans_notes(M.charger(fmt)["scenes"][a.scene])
    voulu = M.sans_notes(M.charger(fmt, {a.scene: a.variante})["scenes"][a.scene])
    fa, fv = aplatir(avant), aplatir(voulu)
    diff = sorted(k for k in set(fa) | set(fv) if fa.get(k) != fv.get(k))
    print(f"{nom} [{fmt}] ← variante « {a.variante} » : {len(diff)} clé(s) résolue(s) changent")
    for k in diff:
        print(f"  {k} : {json.dumps(fa.get(k), ensure_ascii=False)} → {json.dumps(fv.get(k), ensure_ascii=False)}")
    if not a.go:
        print("(essai : rien d'écrit ; --go pour adopter)")
        return 0
    n = copy.deepcopy(d)
    n[fmt] = M.fusion(n[fmt], var)
    if var.get("_note"):
        n[fmt]["_variante_adoptee"] = f"« {a.variante} », adoptée le {datetime.date.today():%d/%m/%Y} : {var['_note']}"
    del n["variantes"][a.variante]
    if not n["variantes"]:
        del n["variantes"]
    M.ecrire(nom, n)
    apres = M.sans_notes(M.charger(fmt)["scenes"][a.scene])
    if apres != voulu:
        M.ecrire(nom, d)
        raise SystemExit("contrôle échoué : la mise en page résolue diffère de la variante ; fichier restauré")
    print(f"→ mise-en-page/{nom} réécrit ; « {fmt} » résout désormais comme « {a.variante} ». Reconstruire : "
          f"python3 outils/format.py {fmt} --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
