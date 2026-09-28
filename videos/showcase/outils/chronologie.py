#!/usr/bin/env python3
"""Chronologie des INSERTIONS DE TEMPS du showcase : la même règle pour l'image, le dialogue, la musique et les recettes.

La source unique est son/dialogue.json, clé "insertions" (écrite par son/dialogue.py, liste INSERTIONS) :
    [{"id": "prenom", "pivot_image": 758, "images": 92, "pivot_s": 25.266667, "s": 3.066667, "echantillons": 147200}]
Règle (dialogue.json "insertions_regle") : un instant t du film d'avant (47 s, commit a6d3d8e) devient t + Σ s des
insertions dont t ≥ pivot_s, appliquées dans l'ordre (chaque pivot est un instant du film d'avant CETTE insertion) ; en
images : image + Σ images des insertions dont image ≥ pivot_image ; en échantillons : i + Σ échantillons (entiers).

    import chronologie as CH
    C = CH.charger()                    # son/dialogue.json ; CH.charger(chemin) ou CH.Chronologie([...]) sinon
    C.decaler(t)                        # film d'avant → film actuel (scalaire ou tableau)
    C.decaler_echantillon(i)            # idem, en échantillons entiers (48 kHz) : exactement + 147 200 après le pivot
    C.vers_base(t)                      # film actuel → film d'avant ; DANS une mesure insérée : le pivot (le temps est
                                        # tenu : une automation lue à travers vers_base reste suspendue pendant l'insertion)
    C.decaler_fenetre([a, b])           # une fenêtre qui enjambe un pivot s'allonge de la durée insérée
    C.inserer(x)                        # un signal du film d'avant (n, …) → film actuel : silence dans chaque insertion
    C.texture(base, neuf)               # une TEXTURE (bruit, fond de pièce, de ligne, air) du film d'avant → film actuel :
                                        # base à l'octet hors des mesures, du neuf dedans, fondus à puissance constante
    C.vers_base_echantillon(i)          # film actuel → film d'avant, en échantillons (horloge d'un oscillateur)
    C.debuts_trames(n, pas, nfft)       # une grille de trames d'analyse alignée sur le film d'avant (mesures par trames)
    C.cycles_entiers(r, t), C.phase_entiere(fi, i0)
                                        # une voix TENUE à travers une insertion (cordes, verre frotté) : ses oscillations
                                        # y font un nombre entier de cycles ; après, elle redonne la voix d'avant, décalée
    C.zones()                           # [(début, fin)] des mesures insérées, en temps du film actuel

Sans insertion (dialogue.json sans la clé, ou liste vide), tout est l'identité : les scripts qui s'en servent redonnent
à l'octet ce qu'ils donnaient avant (preuve : riche-musique sur le film de 47 s, voir OUTILS.md).
Outil en ligne de commande pour les fichiers : outils/inserer_temps.py (wav, recette, json, verifier).

CÔTÉ IMAGE, LA MÊME RÈGLE : showcase-iphone/outils/temps.py (classe Insertions : image(), t(), base_image(), base_t(),
décalages de comparer_mp4.py). Les deux lisent son/dialogue.json « insertions » ; ils restent deux modules (chaque
projet garde ses preuves à l'octet sans dépendre de l'autre), mais leur accord se PROUVE, en une commande :
    python3 outils/chronologie.py                      résumé (insertions, zones, durée du film)
    python3 outils/chronologie.py --verifier-image [TEMPS.py]
          compare les deux modules sur toutes les images et tous les 1/300 s du film de base, aller et retour, pour la
          liste de son/dialogue.json ET pour une liste synthétique de trois insertions (ordre et pivots croisés) : code 1
          au premier désaccord. Seule différence VOULUE : dans une mesure insérée, vers_base() rend le pivot (le temps
          y est tenu, pour les automations de la musique), temps.py base_t() / base_image() rendent None (image insérée).
"""
import json
from pathlib import Path

import numpy as np

SR = 48000
DIALOGUE = Path(__file__).resolve().parent.parent / "son" / "dialogue.json"
TOL = 1e-9


class Chronologie:
    def __init__(self, insertions=(), fps=30):
        self.fps = fps
        self.ins = []
        for x in insertions or ():
            images = int(x["images"])
            p = x["pivot_image"] / fps if "pivot_image" in x else float(x["pivot_s"])
            s = images / fps if "images" in x else float(x["s"])
            n = int(x.get("echantillons", round(s * SR)))
            assert n == round(s * SR), (x, n, s * SR)
            self.ins.append({"id": x.get("id", "?"), "pivot_s": p, "s": s, "echantillons": n,
                             "pivot_image": x.get("pivot_image"), "images": images,
                             "pivot_echantillon": int(round(p * SR))})

    def __bool__(self):
        return bool(self.ins)

    def __repr__(self):
        return "Chronologie(" + ", ".join(f"{i['id']}: +{i['s']:.6f} s dès {i['pivot_s']:.6f}" for i in self.ins) + ")"

    @property
    def total_s(self):
        return sum(i["s"] for i in self.ins)

    @property
    def total_echantillons(self):
        return sum(i["echantillons"] for i in self.ins)

    # ── instants ────────────────────────────────────────────────────────────
    def decaler(self, t):
        """Film d'avant → film actuel. Scalaire, liste ou tableau ; None reste None."""
        if t is None:
            return None
        if isinstance(t, (list, tuple)):
            return type(t)(self.decaler(v) for v in t)
        a = np.asarray(t, dtype=np.float64)
        y = a.copy()
        for i in self.ins:
            y = np.where(y >= i["pivot_s"] - TOL, y + i["s"], y)
        return float(y) if a.ndim == 0 else y

    def decaler_echantillon(self, i):
        """Indice d'échantillon du film d'avant → film actuel, en entiers exacts."""
        k = np.asarray(i, dtype=np.int64)
        y = k.copy()
        for x in self.ins:
            y = np.where(y >= x["pivot_echantillon"], y + x["echantillons"], y)
        return int(y) if k.ndim == 0 else y

    def decaler_image(self, img):
        if img is None:
            return None
        if isinstance(img, (list, tuple)):
            return type(img)(self.decaler_image(v) for v in img)
        for x in self.ins:
            if img >= x["pivot_image"]:
                img += x["images"]
        return img

    def vers_base(self, t):
        """Film actuel → film d'avant. Dans une mesure insérée, l'instant rendu est le pivot (le temps y est tenu)."""
        a = np.asarray(t, dtype=np.float64)
        y = a.copy()
        for i in reversed(self.ins):
            p, s = i["pivot_s"], i["s"]
            y = np.where(y >= p + s - TOL, y - s, np.where(y >= p - TOL, p, y))
        return float(y) if a.ndim == 0 else y

    def vers_base_echantillon(self, i):
        """Indice d'échantillon du film actuel → film d'avant, en entiers exacts ; dans une mesure insérée : le pivot.
        Pour une horloge absolue (la phase d'un oscillateur) qui doit redonner après l'insertion le son d'avant décalé."""
        k = np.asarray(i, dtype=np.int64)
        y = k.copy()
        for x in reversed(self.ins):
            p, n = x["pivot_echantillon"], x["echantillons"]
            y = np.where(y >= p + n, y - n, np.where(y >= p, p, y))
        return int(y) if k.ndim == 0 else y

    def dans_insertion(self, t):
        """Vrai si l'instant t (film actuel) tombe dans une mesure insérée."""
        a = np.asarray(t, dtype=np.float64)
        m = np.zeros(a.shape, dtype=bool)
        for (d, f) in self.zones():
            m |= (a >= d - TOL) & (a < f - TOL)
        return bool(m) if a.ndim == 0 else m

    def zones(self):
        """[(début, fin)] de chaque mesure insérée, en temps du film ACTUEL (les pivots suivants la décalent)."""
        z = []
        for k, i in enumerate(self.ins):
            d = i["pivot_s"]
            for j in self.ins[k + 1:]:
                if d >= j["pivot_s"] - TOL:
                    d += j["s"]
            z.append((d, d + i["s"]))
        return z

    def progres(self, t):
        """(k, n) : pour chaque insertion, 0 avant sa mesure insérée, de 0 à 1 (linéaire) dedans, 1 après (temps actuel)."""
        a = np.atleast_1d(np.asarray(t, dtype=np.float64))
        return np.array([np.clip((a - d) / (f - d), 0.0, 1.0) for d, f in self.zones()]).reshape(len(self.ins), len(a))

    def cycles_entiers(self, r, t):
        """Phase supplémentaire (en cycles) d'une oscillation de fréquence r (Hz) qu'on lit à travers vers_base : dans
        chaque mesure insérée elle avance de round(r·s) cycles, régulièrement ; après, elle a pris un nombre ENTIER de
        cycles, donc sin(2π·r·vers_base(t) + 2π·cycles_entiers) redonne exactement l'oscillation d'avant, décalée."""
        pr = self.progres(t)
        return sum(round(r * i["s"]) * pr[k] for k, i in enumerate(self.ins)) if self.ins else np.zeros(np.size(t))

    def phase_entiere(self, fi, i0):
        """Fréquence instantanée fi (Hz, par échantillon, la note commence à l'échantillon absolu i0) → la même, mise à
        l'échelle DANS chaque mesure insérée que la note couvre entièrement, pour que la phase y avance d'un nombre entier
        de cycles (écart ≤ 0,5 cycle sur la mesure : 1,4 cent au plus à 196 Hz). Après l'insertion, cumsum(fi) redonne la
        phase d'avant à un entier près : la note continue, la même, décalée."""
        fi = np.array(fi, dtype=np.float64)
        for (d, f) in self.zones():
            z0, z1 = int(round(d * SR)) - i0, int(round(f * SR)) - i0
            if z0 > 0 and z1 < len(fi):
                c = fi[z0:z1].sum() / SR
                fi[z0:z1] *= round(c) / c
        return fi

    def decaler_fenetre(self, w):
        """[a, b, …] : a et b décalés (une fenêtre qui enjambe un pivot s'allonge) ; le reste de la liste est gardé."""
        return [self.decaler(w[0]), self.decaler(w[1])] + list(w[2:])

    # ── signaux ─────────────────────────────────────────────────────────────
    def inserer(self, x, remplir=0.0):
        """Signal du film d'avant (axe 0 = temps, 48 kHz) → film actuel : `remplir` (0 = silence) dans chaque insertion."""
        x = np.asarray(x)
        for i in self.ins:
            p = min(i["pivot_echantillon"], len(x))
            trou = np.full((i["echantillons"],) + x.shape[1:], remplir, dtype=x.dtype)
            x = np.concatenate([x[:p], trou, x[p:]])
        return x

    def texture(self, base, neuf, fondu=0.050, i0=0):
        """Une TEXTURE (bruit, fond de pièce, fond de ligne, air : un son stationnaire tiré au hasard ou d'une prise) à
        travers les insertions (28/09, mixeur final) : `base` est la texture du film d'avant (axe 0 = temps, commençant à
        l'échantillon i0 du film), `neuf(L, j)` rend L échantillons NEUFS du même spectre et du même niveau pour la j-ième
        insertion couverte (un tableau d'au moins Σ L échantillons est aussi accepté, consommé dans l'ordre). Rend la
        texture du film actuel : hors des mesures insérées, `base` À L'OCTET (décalée après chaque pivot) ; dans chaque
        mesure, le neuf, entré par un fondu à puissance constante de `fondu` s depuis la suite naturelle de base et sorti
        vers son amorce (le geste du verre frotté de riche-musique). Sans insertion couverte : `base` telle quelle.
        Pourquoi : une texture tirée sur la longueur du film change de réalisation dès le pivot quand le film s'allonge ;
        c'est inaudible, mais ce n'est plus le son validé décalé, et la preuve de continuité (inserer_temps.py verifier)
        ne le distingue pas d'un défaut."""
        x = np.asarray(base)
        X = int(round(fondu * SR))
        if callable(neuf):
            fab = neuf
        else:
            reserve, pos = np.asarray(neuf), [0]

            def fab(L, j):
                seg = reserve[pos[0]:pos[0] + L]
                assert len(seg) == L, "texture : réserve de neuf trop courte"
                pos[0] += L
                return seg
        for j, i in enumerate(self.ins):
            p, L = i["pivot_echantillon"] - i0, i["echantillons"]
            if not 0 < p < len(x):
                continue
            nv = np.array(fab(L, j), dtype=np.float64)
            assert len(nv) == L and nv.shape[1:] == x.shape[1:], (nv.shape, L, x.shape)
            k = min(X, p, len(x) - p, L // 2)
            if k:
                u = (np.arange(k) / k).reshape((k,) + (1,) * (x.ndim - 1))
                nv[:k] = x[p:p + k] * np.cos(np.pi / 2 * u) + nv[:k] * np.sin(np.pi / 2 * u)
                nv[-k:] = nv[-k:] * np.cos(np.pi / 2 * u) + x[p - k:p] * np.sin(np.pi / 2 * u)
            x = np.concatenate([x[:p], nv.astype(x.dtype, copy=False), x[p:]])
        return x

    def debuts_trames(self, n, pas, nfft=0):
        """Débuts (échantillons, film actuel de n échantillons) d'une grille de trames d'analyse au pas `pas`, ALIGNÉE SUR
        LE FILM D'AVANT : les trames k·pas du film d'avant, décalées par la règle (après une mesure insérée, chaque trame
        voit le même son qu'avant : mêmes mesures, mêmes décisions), et, dans chaque mesure insérée, sa propre grille depuis
        son début. Une insertion qui n'est pas un multiple du pas (147 200 = 613,3 × 240) décalerait sinon toute la grille
        d'après, et une mesure faite sur des trames (émergence d'un repère, porte d'une voix) changerait d'une fraction de
        trame. Sans insertion : np.arange(0, n − nfft + 1, pas), la grille de toujours."""
        fin = n - nfft
        if not self.ins:
            return np.arange(0, fin + 1, pas, dtype=np.int64)
        nb = n - self.total_echantillons
        d = [np.asarray(self.decaler_echantillon(np.arange(0, nb - nfft + 1, pas, dtype=np.int64)))]
        for a, b in self.zones_echantillons:
            d.append(np.arange(a, b, pas, dtype=np.int64))
        d = np.unique(np.concatenate(d))
        return d[(d >= 0) & (d <= fin)]

    @property
    def zones_echantillons(self):
        return [(int(round(d * SR)), int(round(f * SR))) for d, f in self.zones()]


def charger(chemin=DIALOGUE):
    """La chronologie de son/dialogue.json (ou d'un autre dialogue.json) ; l'identité si la clé est absente."""
    d = json.loads(Path(chemin).read_text()) if not isinstance(chemin, dict) else chemin
    return Chronologie(d.get("insertions", []), d.get("fps", 30))


# ── accord avec l'image (showcase-iphone/outils/temps.py) ────────────────────
TEMPS_IMAGE = Path(__file__).resolve().parents[2] / "showcase-iphone" / "outils" / "temps.py"
SYNTHETIQUE = [{"id": "a", "pivot_image": 758, "images": 92}, {"id": "b", "pivot_image": 300, "images": 23},
               {"id": "c", "pivot_image": 1300, "images": 115}]


def verifier_image(chemin_temps=TEMPS_IMAGE, dialogue=DIALOGUE, n_base=1410, fps=30):
    """Même règle des deux côtés ? Renvoie la liste des désaccords (vide = accord), cas par cas."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("temps_image", str(chemin_temps))
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    cas = {"son/dialogue.json": json.loads(Path(dialogue).read_text()).get("insertions", []),
           "synthétique (3 insertions)": SYNTHETIQUE}
    rapport = {}
    for nom, ins in cas.items():
        C, T = Chronologie(ins, fps), M.Insertions(ins, fps)
        bad = []
        for img in range(n_base + 1):
            if C.decaler_image(img) != T.image(img):
                bad.append(("image", img, C.decaler_image(img), T.image(img)))
        ts = np.arange(0, n_base * 300 + 1) / 300.0
        for t in ts:
            a, b = C.decaler(float(t)), T.t(float(t))
            if abs(a - b) > 1e-9:
                bad.append(("t", round(float(t), 6), a, b))
        n_cour = T.images(n_base)
        for img in range(n_cour + 1):
            tc = img / fps
            bi, bt = T.base_image(img), T.base_t(tc)
            dedans = bool(C.dans_insertion(tc))
            if (bi is None) != dedans or (bt is None) != dedans:
                bad.append(("inséré ?", img, dedans, bi, bt))
            elif not dedans and (abs(C.vers_base(tc) - bt) > 1e-9 or abs(C.vers_base(tc) - bi / fps) > 1e-9):
                bad.append(("retour", img, C.vers_base(tc), bi, bt))
        rapport[nom] = {"insertions": len(ins), "images_base": n_base, "images": n_cour,
                        "instants": len(ts), "desaccords": bad[:10], "n_desaccords": len(bad)}
    return rapport


def main():
    import argparse
    import sys
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dialogue", default=str(DIALOGUE))
    ap.add_argument("--verifier-image", nargs="?", const=str(TEMPS_IMAGE), metavar="TEMPS.py")
    a = ap.parse_args()
    C = charger(a.dialogue)
    if a.verifier_image:
        r = verifier_image(a.verifier_image, a.dialogue)
        for nom, x in r.items():
            etat = "accord" if not x["n_desaccords"] else f"{x['n_desaccords']} DÉSACCORDS {x['desaccords']}"
            print(f"{nom} : {x['insertions']} insertion(s), {x['images_base']} → {x['images']} images, "
                  f"{x['instants']} instants : {etat}")
        sys.exit(1 if any(x["n_desaccords"] for x in r.values()) else 0)
    print(C)
    print(f"zones (film actuel) : {[(round(d, 6), round(f, 6)) for d, f in C.zones()]} ; "
          f"+{C.total_s:.6f} s = +{C.total_echantillons} échantillons")


if __name__ == "__main__":
    main()
