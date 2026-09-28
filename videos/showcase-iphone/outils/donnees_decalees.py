#!/usr/bin/env python3
"""Données d'un projet après une INSERTION de temps = les données d'avant portées par la règle ? Clé par clé : usage en une ligne :

    python3 outils/donnees_decalees.py <donnees_ref/> <donnees_cand/> [--decalage A:N …] [--voulu a-b,c-d] [--ignorer k,…]
                                       [--fichiers evenements.json,…] [--tol-px 0.002] [--json r.json]

  <donnees_ref/> : les données du film de BASE (ex. le 16:9 de 47 s : git show a6d3d8e:…/formats/16x9/donnees, ou
  « git:a6d3d8e:videos/showcase-iphone/formats/16x9/donnees », extrait tout seul) ; <donnees_cand/> : celles du film courant.
  --decalage A:N (répétable ; défaut : son/dialogue.json « insertions », outils/temps.py) : N images insérées avant l'image A
  du film de base. La référence est PORTÉE par la règle (outils/temps.py), puis comparée au candidat :
    · instants (t, t0, t1, debut, fin, voyelle, revele, fin_voix, film_in, film_out, hote_start, segments_s, sans) → T.t ;
    · images (image, images, image0, image1, image_debut, image_fin, depart, arrivee, et les clés « 620 » d'un dict d'images) → T.image ;
    · durées (duree, hote_duration) : portées depuis leur début (debut, t ou hote_start du même objet) : une durée qui
      enjambe le pivot s'allonge des images insérées ;
    · tout le reste (géométrie : x, y, top, largeurs…) doit être IDENTIQUE (à --tol-px près pour les réels, défaut 0,002 :
      les px sont arrondis au millième, un rang d’arrondi de part et d’autre).
  Les listes d'objets s'apparient par clé (id, nom, (scene, extrait, depuis), image, depart, image0, t : la première que
  tous portent), sinon par rang. --voulu a-b : plages d'images du FILM DE BASE où l'écart est voulu (la scène refaite) :
  un objet dont un instant ou une image tombe dedans est rapporté « voulu », hors du code de sortie.
  Rapporte par fichier : valeurs portées (qui ont bougé comme la règle le veut), identiques, VOULUES, AJOUTÉES (clés ou
  objets du candidat seulement : permis, un format ou une insertion ajoutent), RETIRÉES, et CHANGÉES, dont celles RESTÉES
  À L'ANCIENNE VALEUR (le candidat a gardé le nombre de la référence alors que la règle le déplace : le défaut que cet outil
  cherche, un temps propre à un format oublié). Code 1 s'il reste une valeur retirée ou changée hors --voulu.
  --ignorer : noms de clés non comparés (défaut : version, date, n, local, note, _note, description, definition, unite,
  moteur, lecture ; « local » est relatif au début de la scène). Lecture seule, idempotent.
Exemple (le 16:9 après l'échange du prénom, 28/09) :
    python3 outils/donnees_decalees.py git:a6d3d8e:videos/showcase-iphone/formats/16x9/donnees formats/16x9/donnees \\
            --voulu 758-800 --ignorer cle
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import temps  # noqa: E402

PROJET = Path(__file__).resolve().parents[1]
TEMPS = {"t", "t0", "t1", "debut", "fin", "voyelle", "revele", "fin_voix", "film_in", "film_out", "hote_start", "segments_s", "sans"}
IMAGES = {"image", "images", "image0", "image1", "image_debut", "image_fin", "depart", "arrivee"}
DUREES = {"duree": ("debut", "t", "hote_start"), "hote_duration": ("hote_start",)}
IGNORER = {"version", "date", "n", "local", "note", "_note", "description", "definition", "unite", "moteur", "lecture"}
CLES_LISTE = [("id",), ("nom",), ("scene", "extrait", "depuis"), ("image",), ("depart",), ("image0",), ("t",)]
TOL_T, TOL_D = 2e-6, 1.2e-4


def nombre(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Portage:
    def __init__(self, T, voulu, ignorer, tol_px):
        self.T, self.voulu, self.ignorer, self.tol_px = T, voulu, ignorer, tol_px
        self.fps = T.fps

    def img(self, v):
        return self.T.image(v) if isinstance(v, int) else round(self.T.t(v / self.fps) * self.fps, 6)

    def dans_voulu(self, o):
        """un instant ou une image de l'objet (niveau 1, et listes de nombres) tombe dans une plage voulue du film de base"""
        vals = []
        for k, v in (o.items() if isinstance(o, dict) else []):
            for x in (v if isinstance(v, list) else [v]):
                if nombre(x):
                    if k in IMAGES:
                        vals.append(x)
                    elif k in TEMPS:
                        vals.append(x * self.fps)
        return any(a <= x <= b + 0.999 for x in vals for a, b in self.voulu)

    def porter(self, k, v, parent):
        """la valeur attendue dans le candidat pour la valeur v de la référence (clé k)"""
        if isinstance(v, list) and v and all(nombre(x) or isinstance(x, list) for x in v) and k in TEMPS | IMAGES:
            return [self.porter(k, x, parent) for x in v]
        if not nombre(v):
            return v
        if k in TEMPS:
            return self.T.t(v)
        if k in IMAGES:
            return self.img(v)
        if k in DUREES:
            for d in DUREES[k]:
                if nombre(parent.get(d)):
                    return self.T.t(parent[d] + v) - self.T.t(parent[d])
        return v

    def cle_liste(self, a, b):
        objs = [x for x in a + b]
        if not objs or not all(isinstance(x, dict) for x in objs):
            return None
        for c in CLES_LISTE:
            if all(all(k in x for k in c) for x in objs):
                return c
        return None

    def ident(self, x, c, porte):
        vals = tuple(x[k] for k in c)
        if porte:
            vals = tuple(self.porter(k, x[k], x) for k in c)
        return tuple(round(v, 4) if isinstance(v, float) else v for v in vals)

    def comparer(self, a, b, chemin, R, k=None, parent=None, voulu=False):
        if isinstance(a, dict) and isinstance(b, dict):
            voulu = voulu or self.dans_voulu(a)
            chiffres = bool(a) and all(x.isdigit() for x in a) and bool(b) and all(x.isdigit() for x in b)
            base = {}
            if chiffres:                       # dict indexé par image (« 620 » : {sx, sy}) : les clés sont des images
                base = {str(self.img(int(x))): int(x) for x in a}
                a = {str(self.img(int(x))): v for x, v in a.items()}
            for kk, va in a.items():
                if kk in self.ignorer:
                    continue
                v_ = voulu or (chiffres and any(p0 <= base[kk] <= p1 for p0, p1 in self.voulu))
                if kk not in b:
                    R["voulu" if v_ else "retire"].append(f"{chemin}.{kk}")
                else:
                    self.comparer(va, b[kk], f"{chemin}.{kk}", R, kk if not chiffres else "image", a, v_)
            R["ajoute"] += [f"{chemin}.{kk}" for kk in b if kk not in a and kk not in self.ignorer]
            return
        if isinstance(a, list) and isinstance(b, list) and not (k in TEMPS | IMAGES and all(nombre(x) for x in a + b)):
            c = self.cle_liste(a, b)
            if c:
                ib = {self.ident(x, c, False): x for x in b}
                vus = set()
                for x in a:
                    i = self.ident(x, c, True)
                    vx = voulu or self.dans_voulu(x)
                    if i in ib:
                        vus.add(i)
                        self.comparer(x, ib[i], f"{chemin}[{'/'.join(map(str, i))}]", R, None, None, vx)
                    else:
                        R["voulu" if vx else "retire"].append(f"{chemin}[{'/'.join(map(str, i))}]")
                R["ajoute"] += [f"{chemin}[{'/'.join(map(str, i))}]" for i in ib if i not in vus]
                return
            if len(a) == len(b):
                for n, (x, y) in enumerate(zip(a, b)):
                    self.comparer(x, y, f"{chemin}[{n}]", R, k, parent, voulu)
                return
            R["voulu" if voulu else "change"].append(f"{chemin} : longueur {len(a)} → {len(b)}")
            return
        attendu = self.porter(k, a, parent or {})
        if self.egal(attendu, b, k):
            R["porte" if not self.egal(a, b, k) else "identique"] += 1
            return
        txt = f"{chemin} : réf {self.court(a)}, attendu {self.court(attendu)}, candidat {self.court(b)}"
        if voulu:
            R["voulu"].append(txt)
        elif self.egal(a, b, k):
            R["reste"].append(txt)
        else:
            R["change"].append(txt)

    def egal(self, x, y, k):
        if isinstance(x, list) and isinstance(y, list):
            return len(x) == len(y) and all(self.egal(p, q, k) for p, q in zip(x, y))
        if nombre(x) and nombre(y):
            tol = TOL_T if k in TEMPS else TOL_D if k in DUREES else 1e-4 if k in IMAGES else self.tol_px
            return abs(x - y) <= tol
        return x == y

    @staticmethod
    def court(v):
        if isinstance(v, float):
            return f"{v:.6f}".rstrip("0").rstrip(".")
        return json.dumps(v, ensure_ascii=False)[:60]


def dossier(src, tmp):
    if not src.startswith("git:"):
        return Path(src)
    rev, chemin = src[4:].split(":", 1)
    top = subprocess.run(["git", "-C", PROJET, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    noms = subprocess.run(["git", "-C", top, "ls-tree", "--name-only", f"{rev}:{chemin}"], capture_output=True, text=True,
                          check=True).stdout.split()
    d = Path(tmp) / "ref"
    d.mkdir(parents=True, exist_ok=True)
    for n in noms:
        if n.endswith(".json"):
            (d / n).write_bytes(subprocess.run(["git", "-C", top, "show", f"{rev}:{chemin}/{n}"], capture_output=True,
                                               check=True).stdout)
    return d


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("ref")
    A.add_argument("cand")
    A.add_argument("--decalage", action="append", default=[])
    A.add_argument("--voulu", default="")
    A.add_argument("--ignorer", default="")
    A.add_argument("--fichiers", default="")
    A.add_argument("--tol-px", type=float, default=2e-3)
    A.add_argument("--json")
    a = A.parse_args()
    if a.decalage:
        T = temps.Insertions([{"id": f"--decalage {x}", "pivot_image": int(x.split(":")[0]), "images": int(x.split(":")[1])}
                              for x in a.decalage])
    else:
        T = temps.Insertions.depuis(PROJET / "son" / "dialogue.json")
    voulu = [tuple(int(x) for x in p.split("-")) for p in a.voulu.split(",") if p]
    P = Portage(T, voulu, IGNORER | {x for x in a.ignorer.split(",") if x}, a.tol_px)
    print(f"règle : {', '.join(T.decalages()) or 'aucune insertion'} ; voulu (film de base) : {a.voulu or 'rien'}")
    rapport, mauvais = {}, 0
    with tempfile.TemporaryDirectory(dir="/dev/shm") as tmp:
        dr, dc = dossier(a.ref, tmp), Path(a.cand)
        noms = [x for x in a.fichiers.split(",") if x] or sorted(f.name for f in dr.glob("*.json"))
        for n in noms:
            if not (dc / n).exists():
                print(f"{n} : ABSENT du candidat"); mauvais += 1; continue
            R = {"porte": 0, "identique": 0, "voulu": [], "ajoute": [], "retire": [], "change": [], "reste": []}
            P.comparer(json.loads((dr / n).read_text()), json.loads((dc / n).read_text()), n.removesuffix(".json"), R)
            bad = len(R["retire"]) + len(R["change"]) + len(R["reste"])
            mauvais += bool(bad)
            etat = "PAS CONFORME" if bad else "conforme"
            print(f"{n} : {etat} · {R['porte']} valeur(s) portée(s), {R['identique']} identique(s), {len(R['voulu'])} voulue(s), "
                  f"{len(R['ajoute'])} ajoutée(s), {len(R['retire'])} retirée(s), {len(R['change'])} changée(s), "
                  f"{len(R['reste'])} restée(s) à l'ancienne valeur")
            for cat, lib in (("reste", "RESTÉE"), ("change", "changée"), ("retire", "retirée")):
                for x in R[cat][:12]:
                    print(f"   {lib} : {x}")
                if len(R[cat]) > 12:
                    print(f"   … {len(R[cat]) - 12} de plus")
            rapport[n] = R
    if a.json:
        Path(a.json).write_text(json.dumps(rapport, ensure_ascii=False, indent=1))
    print("conforme : le candidat est la référence portée par la règle (hors voulu)" if not mauvais else
          f"{mauvais} fichier(s) pas conforme(s)")
    return 1 if mauvais else 0


if __name__ == "__main__":
    sys.exit(main())
