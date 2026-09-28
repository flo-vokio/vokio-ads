#!/usr/bin/env python3
"""Prouve qu'une garde d'une scène se DÉCLENCHE : fausse une valeur de window.DONNEES dans une copie jetable, hf check, cherche l'erreur :

    python3 outils/sonder_garde.py <projet rendable> --attendu "zone interdite" [--poser format.marge_laterale=200]
                            [--ajouter 'format.zones={"nom":"TEST","sorte":"interdite","boite":[0,500,1920,560]}'] [--travail D] [--garder]

  <projet rendable> : une copie de format (outils/format.py … --dossier) ou le projet ; il n'est JAMAIS modifié : il est
  recopié dans --travail (défaut : un dossier temporaire), où donnees/donnees.js est réécrit avec les changements :
    --poser  chemin=json   remplace la valeur (chemin pointé, index de liste permis : pages.0.top=999)
    --ajouter chemin=json  ajoute un élément à la liste du chemin (ex. une zone interdite de test)
  puis lance « hf check <copie> --json » et cherche --attendu dans les erreurs d'exécution (runtime.findings). Code 0 si
  la garde a parlé (le message attendu est là), 1 sinon (garde muette, ou autre erreur) ; imprime les messages trouvés.
  Répétable, idempotent ; la copie est effacée à la fin sauf --garder. Usage type, un cas par appel :
    outils/sonder_garde.py formats/16x9 --ajouter 'format.zones={"nom":"TEST","sorte":"interdite","boite":[980,0,1100,1080]}' --attendu "le point entre"
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HF = "/opt/vokio-ads/bin/hf"
TETE = "window.DONNEES = "


def aller(D, chemin):
    parts = chemin.split(".")
    for p in parts[:-1]:
        D = D[int(p)] if isinstance(D, list) else D[p]
    return D, (int(parts[-1]) if isinstance(D, list) else parts[-1])


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("projet")
    A.add_argument("--attendu", required=True)
    A.add_argument("--poser", action="append", default=[])
    A.add_argument("--ajouter", action="append", default=[])
    A.add_argument("--travail")
    A.add_argument("--garder", action="store_true")
    a = A.parse_args()
    src = Path(a.projet).resolve()
    base = Path(a.travail).resolve() if a.travail else Path(tempfile.mkdtemp(prefix="sonde-"))
    copie = base / "copie"
    if copie.exists():
        shutil.rmtree(copie)
    shutil.copytree(src, copie, ignore=shutil.ignore_patterns("snapshots", "rapports", "*.mp4", ".entrees"))
    f = copie / "donnees" / "donnees.js"
    t = f.read_text()
    i = t.index(TETE) + len(TETE)
    D = json.loads(t[i:].rstrip().rstrip(";"))
    for kv in a.poser:
        k, v = kv.split("=", 1)
        o, c = aller(D, k)
        o[c] = json.loads(v)
    for kv in a.ajouter:
        k, v = kv.split("=", 1)
        o, c = aller(D, k)
        o[c].append(json.loads(v))
    f.write_text(t[:i] + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n")
    r = subprocess.run([HF, "check", copie, "--json"], capture_output=True, text=True)
    brut = r.stdout
    try:
        j = json.loads(brut[brut.index("{"):])
    except (ValueError, json.JSONDecodeError):
        print(brut[-2000:], r.stderr[-2000:]); return 1
    msgs = [x.get("message", "") for x in j.get("runtime", {}).get("findings", []) if x.get("severity") == "error"]
    for m in msgs:
        print("  " + m[:300])
    ok = any(a.attendu in m for m in msgs)
    print(("garde déclenchée" if ok else "GARDE MUETTE") + f" : « {a.attendu} » " + ("trouvé" if ok else "absent")
          + f" ({len(msgs)} erreur(s) d'exécution)")
    if not a.garder:
        shutil.rmtree(base if not a.travail else copie, ignore_errors=True)
    else:
        print(f"copie gardée : {copie}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
