#!/usr/bin/env python3
"""Index des outils du film (lu dans l'en-tête de chaque script, donc jamais périmé) : usage en une ligne :

    python3 outils/index.py [motif] [--complet]

  Pour chaque outils/*.py : son nom, la première ligne de son en-tête (ce qu'il fait) et sa ligne d'usage ; « motif » filtre
  (nom ou texte, sans casse) ; --complet imprime l'en-tête entier des outils retenus. Lecture seule.
Exemples : index.py · index.py rendu · index.py plume --complet
"""
import ast
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent


def entete(f):
    try:
        return ast.get_docstring(ast.parse(f.read_text())) or ""
    except SyntaxError:
        return ""


def main():
    a = sys.argv[1:]
    complet = "--complet" in a
    a = [x for x in a if x != "--complet"]
    motif = a[0].lower() if a else ""
    for f in sorted(ICI.glob("*.py")):
        doc = entete(f)
        if motif and motif not in f.name.lower() and motif not in doc.lower():
            continue
        lignes = [l for l in doc.splitlines() if l.strip()]
        quoi = lignes[0] if lignes else "(sans en-tête)"
        usage = next((l.strip() for l in lignes[1:] if f.name in l and ("python" in l or l.strip().startswith(("outils/", f.name)))), "")
        print(f"{f.name}\n    {quoi}" + (f"\n    {usage}" if usage else ""))
        if complet:
            print("\n".join("      " + l for l in doc.splitlines()[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
