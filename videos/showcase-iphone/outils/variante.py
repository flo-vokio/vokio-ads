#!/usr/bin/env python3
"""Crée, modifie, liste ou retire une VARIANTE nommée de mise en page, sans éditer le JSON à la main : usage en une ligne :

    python3 outils/variante.py <scène> <variante> --poser cle.sous_cle=valeur [cle=valeur …] [--note "…"] | --retirer | --voir

  <scène> : mise-en-page/<scène>.json (s1-sonnerie, s6-sms, s7-signature, s3-ecoute, agenda, texte…) ; <variante> : son nom,
  préfixé du format qu'elle vise (16x9-haut, 16x9-grand…). Sans option : liste les variantes de la scène.
  --poser : chemin pointé dans l'entrée (telephone.x0=770, offre.corps=56, telephone_monte=[35.9,36.4]) ; la valeur est lue en
    JSON (nombre, liste, objet, true/false), sinon gardée en texte. Plusieurs clés d'un coup ; une clé déjà là est remplacée.
  --note : la note « _note » de la variante (le pourquoi, les mesures) ; --retirer : supprime la variante ; --voir : imprime
    la variante et la mise en page résolue du format AVEC elle (outils/mise_en_page.py charger, donc contrôlée).
  Écrit en forme compacte (mise_en_page.ecrire), puis recharge le format avec la variante : une clé incohérente (corps sous le
  minimum, iPhone mal dimensionné…) ARRÊTE avant d'écrire. Idempotent (même commande = même fichier). Le 9:16 n'est jamais
  touché : une variante ne s'applique que si on la nomme (format.py --variante <scène>=<nom>).
Recette d'une variante en quatre commandes :
    python3 outils/variante.py s6-sms 16x9-haut --poser telephone.x0=770 telephone.haut=20 --note "…"
    python3 outils/format.py 16x9 --variante s6-sms=16x9-haut --dossier /dev/shm/v --check --planche
    python3 outils/verifier_scene.py s6-sms --dossier /dev/shm/vs --variante s6-sms=16x9-haut --ref git:HEAD
    python3 outils/adopter_variante.py s6-sms 16x9-haut --go      (puis python3 outils/format.py 16x9 --check)
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mise_en_page as M  # noqa: E402


def valeur(txt):
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return txt


def poser(d, chemin, v):
    cles = chemin.split(".")
    for c in cles[:-1]:
        d = d.setdefault(c, {})
        if not isinstance(d, dict):
            raise SystemExit(f"variante.py : « {chemin} » traverse une valeur qui n'est pas un objet")
    d[cles[-1]] = v


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scene")
    ap.add_argument("variante", nargs="?")
    ap.add_argument("--poser", nargs="+", default=[])
    ap.add_argument("--note")
    ap.add_argument("--retirer", action="store_true")
    ap.add_argument("--voir", action="store_true")
    a = ap.parse_args()
    nom = a.scene if a.scene.endswith(".json") else a.scene + ".json"
    if not (M.DOSSIER / nom).exists():
        raise SystemExit(f"variante.py : mise-en-page/{nom} introuvable")
    d = M.lire(nom)
    V = d.get("variantes", {})
    if not a.variante:
        for k, v in V.items():
            print(f"{k} : {json.dumps(M.sans_notes(v), ensure_ascii=False)}")
        if not V:
            print("(aucune variante)")
        return 0
    fmt = a.variante.split("-")[0]
    if a.voir:
        if a.variante not in V:
            raise SystemExit(f"variante « {a.variante} » absente de {nom}")
        print(json.dumps(V[a.variante], ensure_ascii=False, indent=1))
        R = M.charger(fmt, {Path(nom).stem: a.variante})
        cle = M.SCENES.get(Path(nom).stem, Path(nom).stem)
        print(json.dumps(R.get(cle, R["scenes"].get(Path(nom).stem)), ensure_ascii=False, indent=1))
        return 0
    nouveau = copy.deepcopy(d)
    if a.retirer:
        if a.variante not in V:
            print(f"rien à faire : « {a.variante} » absente de {nom}")
            return 0
        del nouveau["variantes"][a.variante]
        if not nouveau["variantes"]:
            del nouveau["variantes"]
    else:
        if not a.poser and a.note is None:
            raise SystemExit("variante.py : rien à poser (--poser cle=valeur …, --note)")
        if fmt not in d:
            raise SystemExit(f"{nom} n'a pas d'entrée « {fmt} » : le préfixe de la variante doit nommer un format existant")
        var = nouveau.setdefault("variantes", {}).setdefault(a.variante, {})
        if a.note is not None:
            var["_note"] = a.note
            var = {"_note": var.pop("_note"), **var}
            nouveau["variantes"][a.variante] = var
        for p in a.poser:
            if "=" not in p:
                raise SystemExit(f"variante.py : « {p} » n'est pas de la forme cle=valeur")
            k, v = p.split("=", 1)
            poser(var, k, valeur(v))
    if nouveau == d:
        print(f"rien à faire : mise-en-page/{nom} déjà dans cet état")
        return 0
    ancien = (M.DOSSIER / nom).read_text()
    M.ecrire(nom, nouveau)
    try:
        if not a.retirer:
            M.charger(fmt, {Path(nom).stem: a.variante})
    except (AssertionError, SystemExit) as e:
        (M.DOSSIER / nom).write_text(ancien)
        raise SystemExit(f"variante.py : refusée, la mise en page résolue ne passe pas ({e}) ; fichier inchangé")
    print(f"mise-en-page/{nom} : variante « {a.variante} » " + ("retirée" if a.retirer else
          json.dumps(M.sans_notes(nouveau['variantes'][a.variante]), ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
