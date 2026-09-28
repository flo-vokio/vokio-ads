#!/usr/bin/env python3
"""Insertions de temps du film (28/09) : LA règle qui porte un instant du film de base dans le film courant.

    python3 outils/temps.py                        résumé : insertions, durée, correspondance des images du film de base
    python3 outils/temps.py 941 36.6667 1242        porte des images (entiers) et des instants (décimaux, s) du film de base
    python3 outils/temps.py --inverse 1033 34.5     l'inverse : image ou instant du film courant → film de base (« inséré » dedans)
    python3 outils/temps.py --decalages             les options à passer à outils/comparer_mp4.py et outils/identite.py comparer
                                                    pour comparer un rendu du film de base à un rendu du film courant
    [--dialogue son/dialogue.json]                  (défaut : son/dialogue.json de ce projet, écrit par son/dialogue.py)

UNE SOURCE : son/dialogue.json « insertions », écrite par son/dialogue.py (liste INSERTIONS : c'est là, et seulement là,
qu'on allonge le film). Chaque insertion {id, pivot_image, images} dit : « à partir de l'image pivot_image du film d'avant
elle, tout glisse de `images` images ». Elles s'appliquent dans l'ordre (le pivot d'une insertion est lu dans le film déjà
allongé par les précédentes), comme son/dialogue.py decaler() : l'image et le son suivent donc la même règle.
Le film de base est celui de 47,00 s (1 410 images, commit a6d3d8e) : les nombres en dur de outils/construire.py, des scènes
(TEXTE.decaler, lib/texte.js) et des outils sont ceux de ce film ; ce module les porte dans le film courant.

En module :
    from temps import Insertions
    T = Insertions.depuis("son/dialogue.json")    # ou Insertions([{"id": "prenom", "pivot_image": 758, "images": 92}])
    T.image(941) → 1033 ; T.t(36.6667) → 39.7333… (float exact, à arrondir par l'appelant) ; T.images(1410) → 1502
    T.base_image(1033) → 941 ; T.base_image(800) → None (image insérée) ; T.plages(1410) → [(0, 757, 0), (758, 1409, 850)]
    T.decalages() → ["758:92"] (format de comparer_mp4.py --decalage et identite.py comparer --decalage)
Côté son, la même règle (et ses variantes en échantillons, fenêtres, voix tenues) : $SON/outils/chronologie.py et
$SON/outils/inserer_temps.py (recettes, wav, json) ; les deux lisent son/dialogue.json, ils ne peuvent pas diverger.
Lecture seule, idempotent.
"""
import argparse
import json
import sys
from pathlib import Path

FPS = 30
PROJET = Path(__file__).resolve().parents[1]


class Insertions:
    def __init__(self, liste, fps=FPS):
        self.fps = fps
        self.liste = [{"id": i.get("id", f"insertion {k}"), "pivot_image": int(i["pivot_image"]), "images": int(i["images"])}
                      for k, i in enumerate(liste or [])]
        for i in self.liste:
            assert i["images"] > 0 and i["pivot_image"] >= 0, i

    @classmethod
    def depuis(cls, dialogue_json):
        d = json.loads(Path(dialogue_json).read_text())
        return cls(d.get("insertions", []), d.get("fps", FPS))

    def __bool__(self):
        return bool(self.liste)

    # film de base → film courant
    def image(self, n):
        for i in self.liste:
            if n >= i["pivot_image"]:
                n += i["images"]
        return n

    def t(self, t):
        for i in self.liste:
            if t >= i["pivot_image"] / self.fps - 1e-9:
                t += i["images"] / self.fps
        return t

    def images(self, n_base):
        """Nombre d'images du film courant pour un film de base de n_base images."""
        return n_base + sum(i["images"] for i in self.liste)

    # film courant → film de base
    def base_image(self, n):
        """Image du film de base montrée à l'image n du film courant ; None si n est dans une insertion."""
        for i in reversed(self.liste):
            if n >= i["pivot_image"] + i["images"]:
                n -= i["images"]
            elif n >= i["pivot_image"]:
                return None
        return n

    def base_t(self, t):
        for i in reversed(self.liste):
            p, d = i["pivot_image"] / self.fps, i["images"] / self.fps
            if t >= p + d - 1e-9:
                t -= d
            elif t >= p - 1e-9:
                return None
        return t

    def plages(self, n_base):
        """[(base_debut, base_fin incluse, courant_debut)] : les images du film de base qui se retrouvent telles quelles."""
        out, a = [], 0
        bornes = sorted({self._pivot_base(k) for k in range(len(self.liste))} | {n_base})
        for b in bornes:
            if b > a:
                out.append((a, b - 1, self.image(a)))
            a = max(a, b)
        return out

    def _pivot_base(self, k):
        """Pivot de la k-ième insertion, en image du film de base."""
        n = self.liste[k]["pivot_image"]
        for i in reversed(self.liste[:k]):
            if n >= i["pivot_image"] + i["images"]:
                n -= i["images"]
            elif n >= i["pivot_image"]:
                n = i["pivot_image"]
        return n

    def decalages(self):
        """Options « A:N » (A = image du film de base, N = images insérées juste avant elle), dans l'ordre du film de base."""
        par_pivot = {}
        for k, i in enumerate(self.liste):
            a = self._pivot_base(k)
            par_pivot[a] = par_pivot.get(a, 0) + i["images"]
        return [f"{a}:{n}" for a, n in sorted(par_pivot.items())]

    def resume(self, n_base=1410):
        n = self.images(n_base)
        return {"insertions": self.liste, "images_base": n_base, "images": n, "duree_s": round(n / self.fps, 6),
                "plages": [{"base": [a, b], "courant": [c, c + b - a]} for a, b, c in self.plages(n_base)],
                "decalages": self.decalages()}


def analyser_decalages(options):
    """« 758:92 » (répétable) → [(758, 92)], trié ; pour comparer_mp4.py et identite.py."""
    out = []
    for o in options or []:
        for morceau in str(o).split(","):
            if morceau.strip():
                a, n = morceau.split(":")
                out.append((int(a), int(n)))
    return sorted(out)


def correspondance(decalages, n_ref, n_cand):
    """Paires (image de référence, image du candidat) quand le candidat = la référence où l'on a inséré des images :
    (a, n) = « à partir de l'image a de la référence, le candidat a n images de plus ». Renvoie (paires, images insérées
    du candidat, images de la référence sans correspondant)."""
    paires, cumul, k = [], 0, 0
    for r in range(n_ref):
        while k < len(decalages) and r >= decalages[k][0]:
            cumul += decalages[k][1]
            k += 1
        c = r + cumul
        if c < n_cand:
            paires.append((r, c))
    vus = {c for _, c in paires}
    inserees = [c for c in range(n_cand) if c not in vus]
    sans = [r for r in range(n_ref) if r + sum(n for a, n in decalages if r >= a) >= n_cand]
    return paires, inserees, sans


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("valeurs", nargs="*")
    A.add_argument("--inverse", action="store_true")
    A.add_argument("--decalages", action="store_true")
    A.add_argument("--dialogue", default=str(PROJET / "son" / "dialogue.json"))
    A.add_argument("--images-base", type=int, default=1410)
    a = A.parse_args()
    T = Insertions.depuis(a.dialogue)
    if a.decalages:
        print(" ".join(f"--decalage {d}" for d in T.decalages()) or "(aucune insertion)")
        return 0
    if not a.valeurs:
        print(json.dumps(T.resume(a.images_base), ensure_ascii=False, indent=1))
        return 0
    for v in a.valeurs:
        entier = "." not in v
        x = int(v) if entier else float(v)
        if a.inverse:
            y = T.base_image(x) if entier else T.base_t(x)
            print(f"{v} → " + ("inséré" if y is None else (str(y) if entier else f"{y:.6f}")))
        else:
            print(f"{v} → " + (str(T.image(x)) if entier else f"{T.t(x):.6f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
