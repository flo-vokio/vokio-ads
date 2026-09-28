#!/usr/bin/env python3
"""Règles de Florian contrôlées sur le DOM d'un format, d'après SES zones sûres (DONNEES.format) : usage en une ligne :

    python3 outils/controle_format.py [<racine>] [--pas 3] [--dom dom.json] [--sortie rapport.json]

  <racine> : un projet rendable (défaut : ce projet, le 9:16 ; formats/16x9 pour le paysage). Monte le film dans le
  chrome-headless-shell de HyperFrames (outils/controles_dom.py --racine, une image sur --pas, défaut 3) ou relit --dom,
  puis vérifie, image par image (seuils lus dans DONNEES.format, jamais recopiés) :
    E1 ≤ 3 éléments simultanés (le point posé sur le ı de « Vokıo » EST le point du logo : un seul élément) ;
    E2 texte ≥ corps_min (9:16 36 px, 16:9 40 px) ; dérogation déclarée : l'horodatage d'iOS 11 pt (s6), « À VALIDER » ;
    E3 aucun texte AU REPOS (opaque, non translaté) dans une zone « interdite » du format (9:16 : interface Reels sous 1500 ;
       16:9 : 10 % du bas, bouton « Passer l'annonce ») ; zones « prudence » : signalées, non bloquantes ;
    E4 marges latérales au repos (x ≥ marge et x ≤ largeur − marge) ;
    E5 Geist Mono en capitales : aucun (la capture de l'agenda est une image, non comptée) ;
    E6 (3e passe du 16:9, 28/09) aucun sous-titre SUR le téléphone tant que les deux se voient : la boîte du corps de l'iPhone
       (DONNEES.geometrie.s6.telephone, translatée comme #s6-telephone) contre l'encre de chaque mot visible ; l'écart minimal
       est rapporté (en 16:9, le sous-titre de l'appelant est recoupé pour laisser monter le téléphone avec « Au revoir »).
  Écrit le rapport (défaut : <racine>/rapports/controle-format.json ; pour ce projet, rien n'est écrit sans --sortie) et,
  pour un projet de format, le relevé DOM <racine>/rapports/dom.json (boîtes d'encre lues par outils/fiche_format.py) ;
  code 1 si une règle bloquante échoue. Idempotent. Le contrôle du point (cadre, arrêts en zone interdite) est dans
  outils/construire.py ; le contrôle complet d'un rendu (son, synchro, MP4) reste outils/controles.py.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJET = Path(__file__).resolve().parents[1]
PW = "/root/.pwtest/bin/python"
MENTION_IOS = {"SMS", "Aujourd’hui", "16:55"}      # horodatage d'iOS au-dessus de la bulle, 11 pt réels (dérogation à valider)


def lire_donnees(racine):
    t = (racine / "donnees" / "donnees.js").read_text()
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def recoupe(b, z):
    return b[0] < z[2] and z[0] < b[2] and b[1] < z[3] and z[1] < b[3]


def main():
    a = sys.argv[1:]

    def opt(nom, defaut=None):
        if nom in a:
            i = a.index(nom); v = a[i + 1]; del a[i:i + 2]; return v
        return defaut
    pas, dom, sortie = int(opt("--pas", "3")), opt("--dom"), opt("--sortie")
    racine = Path(a[0]).resolve() if a else PROJET
    D = lire_donnees(racine)
    F = D.get("format") or {"nom": "9x16", "largeur": 1080, "hauteur": 1920, "corps_min": 36, "marge_laterale": 70,
                            "zones": [{"nom": "interface Reels / TikTok", "sorte": "interdite", "boite": [0, 1500, 1080, 1920]}]}
    W, H, m, cmin = F["largeur"], F["hauteur"], F["marge_laterale"], F["corps_min"]
    if dom:
        DOM = json.loads(Path(dom).read_text())
    else:
        with tempfile.TemporaryDirectory(prefix="controle-format-") as d:
            tmp = Path(d) / "dom.json"
            subprocess.run([PW, str(PROJET / "outils" / "controles_dom.py"), str(tmp), str(pas), "--racine", str(racine)],
                           check=True, stderr=subprocess.DEVNULL)
            DOM = json.loads(tmp.read_text())
            if racine != PROJET:
                (racine / "rapports").mkdir(exist_ok=True)
                (racine / "rapports" / "dom.json").write_text(tmp.read_text())
    ev = D.get("evenements", {})
    n_re = ev.get("signature_re_contact", {}).get("image", 10 ** 9)
    K = D["geometrie"]["s6"]["pt"]

    trop, comptes, petits, derog, interdits, prudence, marges, mono = [], {}, set(), set(), [], {}, set(), set()
    TEL = D["geometrie"]["s6"].get("telephone")
    sur_tel, ecart_tel = [], None
    for im in DOM["images"]:
        # E6 : le corps du téléphone (boîte, coins compris) contre l'encre des sous-titres visibles
        ob = next((o for o in im.get("objets", []) if o["nom"].startswith("telephone@") and o["opacite"] > 0.01), None)
        if TEL and ob:
            bt = [TEL["x0"] + ob["x"], TEL["haut"] + ob["y"], TEL["x0"] + TEL["largeur"] + ob["x"], TEL["haut"] + TEL["hauteur"] + ob["y"]]
            for t in im["textes"]:
                if t["element"] != "sous-titre" or t["opacite"] <= 0.01:
                    continue
                e_ = max(bt[0] - t["x1"], t["x0"] - bt[2], bt[1] - t["y1"], t["y0"] - bt[3])
                ecart_tel = e_ if ecart_tel is None else min(ecart_tel, e_)
                if e_ < 0:
                    sur_tel.append((im["image"], t["texte"][:30], round(e_, 1)))
        els = [e.split("@")[0] for e in im["elements"]]
        n = len(els) - (1 if im["image"] >= n_re and "mot" in els and "point" in els else 0)
        comptes[im["image"]] = n
        if n > 3:
            trop.append((im["image"], im["elements"]))
        for t in im["textes"]:
            if t["element"] == "telephone" and t["texte"] in MENTION_IOS and abs(t["corps"] - 11 * K) < 0.01:
                derog.add((t["texte"], round(t["corps"], 2))); continue
            if t["corps"] < cmin - 1e-6:
                petits.add((t["element"], t["texte"][:40], t["corps"]))
            if "Mono" in t["famille"] and re.search(r"[A-Z]", t["texte"]) and t["texte"] == t["texte"].upper():
                mono.add(t["texte"])
            if t["transforme"] or t["opacite"] <= 0.99:
                continue
            b = [t["x0"], t["y0"], t["x1"], t["y1"]]
            for z in F["zones"]:
                if recoupe(b, z["boite"]):
                    if z["sorte"] == "interdite":
                        interdits.append((im["image"], t["element"], t["texte"][:40], z["nom"], b))
                    else:
                        prudence.setdefault(z["nom"], set()).add((t["element"], t["texte"][:40]))
            if t["boite"]["x0"] < m - 0.5 or t["boite"]["x1"] > W - m + 0.5:
                marges.add((t["element"], t["texte"][:40], t["boite"]["x0"], t["boite"]["x1"]))
    reg = {
        "E1 éléments ≤ 3": {"ok": not trop and not DOM["erreurs_page"], "max": max(comptes.values()) if comptes else None,
                            "images_a_3": sum(1 for c in comptes.values() if c == 3), "depassements": trop[:10],
                            "erreurs_page": DOM["erreurs_page"][:5]},
        f"E2 corps ≥ {cmin}": {"ok": not petits, "trop_petits": sorted(petits)[:12],
                               "corps_vus": sorted({t["corps"] for im in DOM["images"] for t in im["textes"]}),
                               "a_valider": sorted(derog) and "horodatage iOS 11 pt (s6) : dérogation proposée le 27/09, À VALIDER par Florian"},
        "E3 zones interdites (texte au repos)": {"ok": not interdits, "textes": interdits[:12]},
        "E3b zones prudence (signalé)": {"ok": True, "textes": {k: sorted(v)[:8] for k, v in prudence.items()}},
        f"E4 marges {m} px": {"ok": not marges, "hors_marges": sorted(marges)[:12]},
        "E5 mono capitales": {"ok": not mono, "textes": sorted(mono)},
        "E6 aucun sous-titre sur le téléphone": {"ok": not sur_tel, "recouvrements": sur_tel[:10],
                                                 "ecart_min_px": None if ecart_tel is None else round(ecart_tel, 1)},
    }
    ok = all(v["ok"] for v in reg.values())
    rapport = {"racine": str(racine), "format": F["nom"], "taille": [W, H], "images_mesurees": len(DOM["images"]), "pas": pas,
               "ok": ok, "regles": reg}
    for k, v in reg.items():
        det = {x: y for x, y in v.items() if x != "ok" and y}
        print(f"{'ok ' if v['ok'] else 'NON'} {k} : {json.dumps(det, ensure_ascii=False, default=str)[:600]}")
    if sortie or racine != PROJET:
        s = Path(sortie) if sortie else racine / "rapports" / "controle-format.json"
        s.parent.mkdir(parents=True, exist_ok=True)
        s.write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=str))
        print(f"→ {s}")
    print(f"format {F['nom']} : {'ok' if ok else 'ÉCHEC'} ({len(DOM['images'])} images, une sur {pas})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
