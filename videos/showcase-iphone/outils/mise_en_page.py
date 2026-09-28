#!/usr/bin/env python3
"""Mise en page par format : lit mise-en-page/*.json (une entrée par format, variantes nommées), la valide et la fournit
à outils/construire.py, outils/preparer_agenda.py, outils/format.py.

    python3 outils/mise_en_page.py <format> [--variante <scène>=<nom> …]   la mise en page résolue (JSON), contrôlée
    python3 outils/mise_en_page.py --reformater                             remet mise-en-page/*.json en forme compacte

  from mise_en_page import charger
  M = charger("16x9", {"s7-signature": "16x9-C"})
  M = charger("16x9", {"*": "16x9-recompose"})   un JEU : la variante de ce nom dans chaque fichier qui l'a (format.py --variante '*=…')
  M["format"]        formats.json[<format>] + "nom"
  M["texte"]         texte.json[<format>]        (styles des sous-titres dits et de la mention, largeurs, x_max_point)
  M["s1"] M["s3"] M["agenda"] M["s6"] M["s7"]     les fichiers de scène, entrée <format> (variante appliquée par-dessus)
  M["scenes"]        TOUTES les entrées par nom de fichier (s1-sonnerie, agenda, texte… et tout mise-en-page/sN-*.json
                     ajouté par une scène, ex. s2-voix.json : facultatif) ; construire.py les recopie telles quelles dans
                     DONNEES.geometrie.mise_en_page.<nom> : une scène ajoute une clé de mise en page SANS toucher au python
Une variante est une entrée de « variantes » dans le fichier de la scène ; elle remplace les clés qu'elle donne (fusion
récursive) ; une clé posée à null est RETIRÉE (retour au défaut du 9:16). Un format « prevu » (1x1) sans entrée dans un fichier de scène lève une erreur explicite : la scène n'a pas
encore sa mise en page. Rien n'est écrit.
"""
import copy
import json
import sys
from pathlib import Path

PROJET = Path(__file__).resolve().parents[1]
DOSSIER = PROJET / "mise-en-page"
FICHIERS = {"texte": "texte.json", "s1": "s1-sonnerie.json", "s3": "s3-ecoute.json", "agenda": "agenda.json",
            "s6": "s6-sms.json", "s7": "s7-signature.json"}
SCENES = {"s1-sonnerie": "s1", "s3-ecoute": "s3", "agenda": "agenda", "s6-sms": "s6", "s7-signature": "s7", "texte": "texte"}


CORPS_WORDMARK_9X16 = 400     # le wordmark du 9:16 : son point de ı (0,11 em) fait 44 px, LE disque du film


def echelle_point(M):
    """Échelle du DISQUE du film de s1 à s6 dans le format M, relative au 9:16 (44 px) : formats.json « echelle_point »,
    1 par défaut. L'agenda de s4-s5 est la vraie capture à 1:1, sa gouttière des heures est faite pour un disque de 44 px :
    un format qui le grossit doit aussi grossir l'agenda (recomposition du 28/09). Lu par construire.py (rayon, écart à l'encre,
    sauts, levées, hochements), preparer_agenda.py (fin d'écriture du bloc) et controles.py."""
    return float(M["format"].get("echelle_point", 1.0))


def echelle_mot(M):
    """Échelle du WORDMARK de s7 dans le format M, relative au 9:16 : corps / 400. Son point de ı (0,11 em) est le point du film
    posé : 44 px × échelle. Quand elle diffère de echelle_point, le point grandit (ou rapetisse) en quittant le téléphone, pendant
    son vol vers le stylo (construire.py, DONNEES.point.taille) : le stylo, le bond et le diamètre final suivent le wordmark.
    9:16 : exactement 1.0 (ses formules restent identiques au bit près : outils/identite.py)."""
    return M["s7"]["fin"]["corps"] / CORPS_WORDMARK_9X16


def lire(nom):
    return json.loads((DOSSIER / nom).read_text())


def fusion(a, b):
    """b par-dessus a, récursivement ; une valeur null dans b RETIRE la clé de a (3e passe du 16:9 : une variante revient au
    défaut du 9:16, ex. « telephone_monte »: null)."""
    out = copy.deepcopy(a)
    for k, v in b.items():
        if k.startswith("_"):
            continue
        if v is None:
            out.pop(k, None)
            continue
        out[k] = fusion(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def sans_notes(o):
    if isinstance(o, dict):
        return {k: sans_notes(v) for k, v in o.items() if not k.startswith("_")}
    if isinstance(o, list):
        return [sans_notes(v) for v in o]
    return o


def compact(o, ind=0):
    """JSON lisible : un objet qui ne contient que des valeurs simples (ou des listes simples) tient sur une ligne."""
    sp = " " * ind
    simple = lambda v: not isinstance(v, (dict, list)) or (isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v))
    if isinstance(o, dict) and not all(simple(v) for v in o.values()):
        return "{\n" + ",\n".join(f"{sp} {json.dumps(k, ensure_ascii=False)}: {compact(v, ind + 1)}" for k, v in o.items()) + "\n" + sp + "}"
    if isinstance(o, list) and not all(simple(v) for v in o):
        return "[\n" + ",\n".join(f"{sp} {compact(v, ind + 1)}" for v in o) + "\n" + sp + "]"
    return json.dumps(o, ensure_ascii=False)


def ecrire(nom, d):
    """Écrit mise-en-page/<nom> en forme compacte (les outils qui modifient une mise en page passent par ici)."""
    (DOSSIER / nom).write_text(compact(d) + "\n")


def formats():
    return {k: v for k, v in lire("formats.json").items() if not k.startswith("_")}


def charger(fmt, variantes=None):
    F = formats()
    if fmt not in F:
        raise SystemExit(f"format inconnu « {fmt} » (connus : {', '.join(F)})")
    variantes = dict(variantes or {})
    M = {"format": dict(sans_notes(F[fmt]), nom=fmt), "scenes": {}}
    facultatifs = {f.stem: f.name for f in sorted(DOSSIER.glob("s[0-9]-*.json")) if f.name not in FICHIERS.values()}
    if "*" in variantes:           # un JEU de variantes : « *=16x9-recompose » = la variante de ce nom dans CHAQUE fichier qui l'a
        nom_jeu = variantes.pop("*")
        jeu = {Path(nom).stem: nom_jeu for nom in list(FICHIERS.values()) + list(facultatifs.values())
               if nom_jeu in lire(nom).get("variantes", {})}
        if not jeu:
            raise SystemExit(f"jeu de variantes « {nom_jeu} » : aucun fichier de mise-en-page/ ne l'a")
        for s, v in jeu.items():
            variantes.setdefault(s, v)
    for cle, nom in list(FICHIERS.items()) + list(facultatifs.items()):
        d = lire(nom)
        if fmt not in d:
            raise SystemExit(f"mise-en-page/{nom} n'a pas d'entrée « {fmt} » : la mise en page de ce format reste à écrire")
        e = sans_notes(d[fmt])
        scene = next((s for s, c in SCENES.items() if c == cle), cle)
        v = variantes.pop(scene, None) or variantes.pop(cle, None)
        if v:
            if v not in d.get("variantes", {}):
                raise SystemExit(f"variante « {v} » absente de mise-en-page/{nom}")
            e = fusion(e, sans_notes(d["variantes"][v]))
            M.setdefault("variantes", {})[scene] = v
        M[cle] = e
        M["scenes"][Path(nom).stem] = e
    if variantes:
        raise SystemExit(f"variantes non utilisées : {variantes}")
    verifier(M)
    return M


def verifier(M):
    """Cohérence interne (bloquante)."""
    F, T = M["format"], M["texte"]
    S = T["styles"]
    s1 = M["s1"]
    assert s1["phrase"]["x"] == S["s2_texte"]["x"], "s1 : l'accroche et le sous-titre de s2 doivent partir du même x (retour chariot)"
    for nom, st in S.items():
        assert st["corps"] >= F["corps_min"], f"texte.json {nom} : corps {st['corps']} < {F['corps_min']}"
        assert st["x"] >= F["marge_laterale"], f"texte.json {nom} : x {st['x']} dans la marge"
    ag = M["agenda"]
    assert isinstance(ag["x"], int) and isinstance(ag["y"], int), "agenda : pose en px ENTIERS (1 px capture = 1 px film)"
    assert len(ag["mention"]["lignes_de_base"]) == 2
    t6 = M["s6"]["telephone"]
    k = M["s6"]["ecran_largeur_px"] / M["s6"]["ecran"]["largeur_pt"]
    assert abs(t6["largeur"] - 2 * t6["bord_cote"] - M["s6"]["ecran_largeur_px"]) < 1e-6, "s6 : largeur ≠ écran + 2 bords"
    assert abs(M["s6"]["ecran"]["hauteur_pt"] * k + 2 * t6["bord_haut"] - t6["hauteur"]) < 0.5, "s6 : hauteur ≠ écran + 2 bords (0,5 px)"
    for cle in ("promesse", "offre"):
        assert M["s7"][cle]["corps"] >= F["corps_min"], f"s7 {cle} : corps < {F['corps_min']}"
    if F["nom"] == "9x16":
        assert echelle_point(M) == 1.0 and echelle_mot(M) == 1.0, "9:16 : le point du film fait 44 px, le wordmark 400 px"


def zones_touchees(M, boite, sortes=("interdite",)):
    """Zones du format (sortes données) que la boîte [x0, y0, x1, y1] recoupe."""
    out = []
    for z in M["format"]["zones"]:
        if z["sorte"] not in sortes:
            continue
        a = z["boite"]
        if boite[0] < a[2] and a[0] < boite[2] and boite[1] < a[3] and a[1] < boite[3]:
            out.append(z["nom"])
    return out


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 2
    if a[0] == "--reformater":
        for f in sorted(DOSSIER.glob("*.json")):
            ecrire(f.name, json.loads(f.read_text()))
            print(f"reformaté : {f.name}")
        return 0
    var = {}
    while "--variante" in a:
        i = a.index("--variante"); s, n = a[i + 1].split("="); var[s] = n; del a[i:i + 2]
    M = charger(a[0], var)
    print(json.dumps(M, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
