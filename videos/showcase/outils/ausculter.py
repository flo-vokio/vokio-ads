#!/usr/bin/env python3
"""Ausculter des bandes son (wav ou mp4) et les comparer : sautes du fond, jointures du dialogue, mots, planches.

    python3 outils/ausculter.py sautes    A.wav B.wav … [--de 0 --a 15] [--mots donnees/mots.json] [--json r.json]
    python3 outils/ausculter.py jointures A.wav B.wav … --dialogue son/dialogue.json [--json r.json]
    python3 outils/ausculter.py raccords  A.wav B.wav … --dialogue son/dialogue.json --mots donnees/mots.json   (4-8 kHz)
    python3 outils/ausculter.py mots      A.wav B.wav … --mots donnees/mots.json --cles C1:0 C1:1   (« mon » et « chat »)
    python3 outils/ausculter.py planche   A.wav B.wav … --de 9.7 --a 10.8 --png p.png [--dialogue …] [--px 400]
    python3 outils/ausculter.py sonie     A.wav B.wav … --png arc.png [--evenements donnees/evenements.json]
    python3 outils/ausculter.py trous     A.wav B.wav … [--de 0 --a 15] [--mots donnees/mots.json] [--seuil 10]
    python3 outils/ausculter.py differentiel 1=a.wav 2=b.wav --sans 3=c.wav [--controle H=d.wav] [--de 0 --a 15] [--seuil 8]
                                   ce qui existe dans TOUS les fichiers (1, 2) et PAS dans --sans (3) : la preuve d'un défaut
    python3 outils/ausculter.py contre H=d.wav --sans 3=c.wav [2=b.wav …] [--de 0 --a 15] [--mots …] [--seuil 10]
                                   ce que le NOUVEAU mix a et qu'aucune version validée n'a : le critère d'acceptation
    python3 outils/ausculter.py reperes DOSSIER_STEMS --cues cues.json [--ref DOSSIER_STEMS_REF] [--cues-ref cues_ref.json]
                                   [--fmax 8000] [--cible 6] [--insertions son/dialogue.json]
                                   chaque petit son émerge-t-il du reste du mix (et autant que dans la référence) ?
Chaque fichier peut porter un nom : « nom=chemin » (sinon le nom du fichier).

SAUTE (définition mesurée) : une marche du FOND, |ΔL| ≥ --seuil dB (défaut 10) entre deux fenêtres de 20 ms
consécutives (pas de 10 ms), dans la bande 2-8 kHz (là où la ligne et le souffle se voient, et où la musique ne masque
rien) OU en large bande, EN DEHORS des mots (donnees/mots.json, ±40 ms) et au-dessus de −75 dBFS côté fort. Une voix
qui commence n'est pas une saute ; un fond qui s'arrête net sur du silence numérique en est une.
TROU (ce que l'oreille appelle une « saute ») : le fond TOMBE d'au moins --seuil dB (10) sous sa médiane des 150 ms
qui précèdent, en 30 ms au plus (une chute franche, pas un fondu), et RESTE au moins 6 dB sous cette référence pendant
≥ 60 ms, le début de la chute hors des mots (±40 ms). Profil RMS 20 ms au pas de 5 ms, bandes 2-8 kHz et large. On
donne la profondeur, la durée du trou et ce qui le referme (un mot, un son, rien avant la fin de la fenêtre).
Bandes de TROU : 30-100, 100-300, 2-8 kHz, 8-16 kHz et large (28/09 : avant, 2-8 kHz et large seulement).
DIFFÉRENTIEL : marches du profil 5 ms (RMS 10 ms) par bande (30-100, 100-300, 300-1 000 Hz, 1-2, 2-4, 4-8, 8-16, 2-8 kHz,
large ; 28/09 : les quatre bandes d'origine ne voyaient ni le grave ni l'extrême aigu), à deux échelles : « court » =
niveau 10 ms après − 10 ms avant ; « tenu » = moyenne 30-130 ms après − 20 ms avant (une chute refermée en 30 ms par un
autre son n'est pas tenue). Retenu : |marche| ≥ --seuil dans TOUS les fichiers positionnels, côté fort au-dessus de
--plancher (−70 dBFS dans la bande ; +12 dB en 30-100 Hz et +4 dB en 100-300 Hz, où le seuil d'audition est plus
haut), et au moins 5 dB plus faible (même sens, ±15 ms) dans le fichier --sans. --controle
montre la même marche dans un nouveau mix. Une marche vue dans plusieurs bandes à moins de 30 ms n'est listée qu'une fois.
CONTRE : l'inverse, pour accepter un nouveau mix : marches du fichier (|court| ET |tenu| ≥ --seuil, même sens, côté
fort > --plancher) dont AUCUNE référence --sans n'a l'équivalent (tenu au moins 5 dB plus faible dans chacune, ±15 ms).
REPÈRE : pour chaque son de --cues ({id, couche, t, fin}) dont la couche est un stem du dossier : puissance par bande
(40-150, 150-400, 400-1 000, 1-2 k, 2-4 k, 4-8 k, 8-16 kHz ; trames de 21 ms au pas de 5 ms) du stem et de la somme des
AUTRES stems, sur les trames de [t ; fin] (fin absente : t + 0,25 s ; 1,5 s au plus) où le stem est à moins de 10 dB de
son maximum dans la bande ; émergence = stem − reste. Verdict : la meilleure bande jusqu'à --fmax (8 kHz : ce qu'un
haut-parleur de téléphone rend) émerge d'au moins min(--cible, émergence du même repère dans --ref).
RACCORD : de la fin du dernier mot d'un extrait au début du premier mot du suivant, la plus forte chute et la plus
forte montée du fond dans 4-8 kHz (fenêtres de 20 ms voisines) et le plancher atteint : indépendant des bords exacts,
il compare deux montages (ancien et nouveau).
JOINTURE : pour chaque bord d'extrait (dialogue.json), niveau 2-8 kHz et large bande sur les 20 ms qui précèdent et les
20 ms qui suivent le bord (±5 ms de garde) : la marche que l'oreille entend au raccord.
Rien n'est écrit hors de --json et --png.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True          # ne pas semer de .pyc à côté des .pyc suivis par git
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sonlib as L  # noqa: E402

SR = L.SR


def charger(specs):
    out = []
    for s in specs:
        if "=" in s and Path(s.split("=", 1)[1]).exists():
            nom, chemin = s.split("=", 1)
        else:
            nom, chemin = Path(s).stem, s
        out.append((nom, L.lire(chemin)))
    return out


def niveaux_glissants(x, fen=0.020, pas=0.010, bande=None):
    """(t centre, dB) RMS sur des fenêtres de fen s tous les pas s, éventuellement dans une bande (f1, f2)."""
    m = L.mono(x)
    if bande:
        m = L.passe_bande(m, *bande, front=0.15)
    c = np.concatenate([[0.0], np.cumsum(m * m)])
    w, h = int(fen * SR), int(pas * SR)
    deb = np.arange(0, len(m) - w, h)
    e = (c[deb + w] - c[deb]) / w
    return (deb + w / 2) / SR, 10 * np.log10(e + 1e-24)


def masque_mots(t, mots, marge=0.040):
    hors = np.ones(len(t), bool)
    for w in mots:
        hors &= ~((t >= w["debut"] - marge) & (t <= w["fin"] + marge))
    return hors


def lire_mots(chemin):
    return json.loads(Path(chemin).read_text())["mots"] if chemin else []


def sautes(x, de=0.0, a=None, mots=(), seuil=10.0, plancher=-75.0):
    """Liste des marches du fond : [{t, bande, avant, apres, delta}] (fenêtres de 20 ms, pas de 10 ms)."""
    a = a or len(x) / SR
    seg = x[int(de * SR):int(a * SR)]
    res = []
    for nom, b in (("2-8 kHz", (2000, 8000)), ("large", None)):
        t, l = niveaux_glissants(seg, bande=b)
        t = t + de
        # fenêtre avant = [t-20ms, t], après = [t, t+20 ms] : indices i et i+2
        av, ap = l[:-2], l[2:]
        tt = t[1:-1]
        d = ap - av
        hors = masque_mots(tt - 0.010, mots) & masque_mots(tt + 0.010, mots)
        ok = (np.abs(d) >= seuil) & (np.maximum(av, ap) > plancher) & hors
        idx = np.flatnonzero(ok)
        # une marche = un groupe d'indices contigus ; on garde le plus grand |delta|
        groupes = np.split(idx, np.flatnonzero(np.diff(idx) > 2) + 1) if len(idx) else []
        for g in groupes:
            k = g[np.argmax(np.abs(d[g]))]
            res.append({"t": round(float(tt[k]), 3), "bande": nom, "avant_db": round(float(av[k]), 1),
                        "apres_db": round(float(ap[k]), 1), "delta_db": round(float(d[k]), 1)})
    return sorted(res, key=lambda r: (r["t"], r["bande"]))


def trous(x, de=0.0, a=None, mots=(), seuil=10.0, chute_max=0.030, duree_min=0.060, ref=0.150, pas=0.005,
          plancher=-75.0, bandes=None):
    """Trous du fond (voir TROU) : [{t, bande, ref_db, fond_db, profondeur_db, duree_s, referme}]."""
    a = a or len(x) / SR
    i0 = max(0, int((de - ref - 0.05) * SR))
    seg = x[i0:int(a * SR)]
    res = []
    nref, nch, ndur = int(round(ref / pas)), int(round(chute_max / pas)), int(round(duree_min / pas))
    for nom, bd in (bandes or BANDES_TROUS).items():
        t, l = niveaux_glissants(seg, fen=0.020, pas=pas, bande=bd)
        t = t + i0 / SR
        hors = masque_mots(t, mots)
        k = nref
        while k < len(l) - ndur:
            r = float(np.median(l[k - nref:k]))
            if t[k] < de or r < plancher or not hors[k]:
                k += 1
                continue
            # chute franche : on atteint r − seuil en ≤ chute_max
            j = k + np.flatnonzero(l[k:k + nch + 1] <= r - seuil)
            if not len(j):
                k += 1
                continue
            j = int(j[0])
            # durée du trou : tant que le fond reste ≥ 6 dB sous la référence
            fin = j
            while fin < len(l) and l[fin] <= r - 6.0:
                fin += 1
            if fin - j >= ndur:
                dans = [w for w in mots if w["debut"] - 0.040 <= t[fin - 1] + pas <= w["fin"] + 0.040] if fin < len(l) else []
                ferme = ("rien (fin de fenêtre)" if fin >= len(l) or t[fin] > a else
                         (f"mot « {dans[0]['texte']} »" if dans else "un son"))
                res.append({"t": round(float(t[j]), 3), "bande": nom, "ref_db": round(r, 1),
                            "fond_db": round(float(l[j:fin].min()), 1), "profondeur_db": round(float(l[j:fin].min()) - r, 1),
                            "duree_s": round(float(t[min(fin, len(t) - 1)] - t[j]), 3), "referme": ferme})
                k = fin
            else:
                k += 1
    return sorted(res, key=lambda r: (r["t"], r["bande"]))


BANDES_DIFF = {"30-100": (30, 100), "100-300": (100, 300), "0,3-1k": (300, 1000), "1-2k": (1000, 2000),
               "2-4k": (2000, 4000), "4-8k": (4000, 8000), "8-16k": (8000, 16000), "2-8k": (2000, 8000), "large": None}
# 28/09 (revue) : 100-500 / 0,5-2k / 2-8k / large ne voyaient pas la coupe de la quinte de la sonnerie (30-300 Hz) au
# décroché, que la tonalité (300-1 000 Hz) masque en large bande ; ni ce qui se passe au-dessus de 8 kHz
# le seuil d'audition monte dans le grave (ISO 226 : ≈ +40 dB à 50 Hz, +15 dB à 150 Hz contre 1 kHz) : le plancher du
# côté fort y est relevé d'autant (dB), pour ne pas lister les fluctuations d'un fond de pièce à −70 dBFS sous 100 Hz
PLANCHER_GRAVE = {"30-100": 12.0, "100-300": 4.0}
BANDES_TROUS = {"30-100": (30, 100), "100-300": (100, 300), "2-8 kHz": (2000, 8000), "8-16 kHz": (8000, 16000), "large": None}
BANDES_REPERES = ((40, 150), (150, 400), (400, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000))


def _marches(x, de, a, bande, pas=0.005):
    t, l = niveaux_glissants(x[int(max(0, de - 0.3) * SR):int(a * SR) + int(0.3 * SR)], fen=0.010, pas=pas, bande=bande)
    t = t + max(0, de - 0.3)
    l = np.maximum(l, -90.0)
    n = len(l)
    court = np.zeros(n); court[2:-2] = l[4:] - l[:-4]
    c = np.concatenate([[0.0], np.cumsum(10 ** (l / 10))])

    def moy(i, j):
        i, j = np.clip(i, 0, n), np.clip(j, 0, n)
        return 10 * np.log10(np.maximum((c[j] - c[i]) / np.maximum(j - i, 1), 1e-9))
    k = np.arange(n)
    avant, apres = moy(k - 4, k), moy(k + 6, k + 26)            # 20 ms avant ; 30-130 ms après
    tenu = apres - avant
    return t, l, court, tenu, avant, apres


def _regrouper(res, force, fen=0.030):
    """Une même marche vue dans plusieurs bandes ou échelles (à moins de fen s) : on garde la plus forte (clé force)
    et on note les bandes où elle se voit."""
    res = sorted(res, key=lambda r: r["t"])
    out, groupe = [], []
    for r in res + [None]:
        if r is not None and (not groupe or r["t"] - groupe[0]["t"] <= fen):
            groupe.append(r); continue
        if groupe:
            m = dict(max(groupe, key=force))
            m["bandes"] = sorted({g["bande"] for g in groupe},
                                 key=lambda b: list(BANDES_DIFF).index(b) if b in BANDES_DIFF else 99)
            out.append(m)
        groupe = [r] if r is not None else []
    return out


def differentiel(avec, sans, controle=None, de=0.0, a=15.0, seuil=8.0, ecart=5.0, mots=(), plancher=-70.0, bandes=None):
    """avec : [(nom, x)] qui ont le défaut ; sans : (nom, x) qui ne l'a pas ; controle : (nom, x) ou None. Une marche
    n'est retenue que si son côté fort dépasse `plancher` dBFS dans la bande, dans chaque fichier « avec »."""
    res = []
    for nb, bd in (bandes or BANDES_DIFF).items():
        P = {nom: _marches(x, de, a, bd) for nom, x in avec + [sans] + ([controle] if controle else [])}
        t = P[avec[0][0]][0]
        for echelle, j in (("court", 2), ("tenu", 3)):
            for sens in (-1, 1):
                ok = np.ones(len(t), bool)
                for nom, _ in avec:
                    ok &= (sens * P[nom][j] >= seuil) & (np.maximum(P[nom][4], P[nom][5]) > plancher + PLANCHER_GRAVE.get(nb, 0.0))
                ok &= (t >= de) & (t <= a)
                idx = np.flatnonzero(ok)
                for g in (np.split(idx, np.flatnonzero(np.diff(idx) > 3) + 1) if len(idx) else []):
                    k = g[np.argmax(sum(sens * P[nom][j][g] for nom, _ in avec))]
                    w = slice(max(0, k - 3), k + 4)
                    vs = sens * (sens * P[sans[0]][j][w]).max()
                    pire = min(abs(P[nom][j][k]) for nom, _ in avec)
                    if sens * vs > pire - ecart:
                        continue
                    r = {"t": round(float(t[k]), 3), "bande": nb, "echelle": echelle,
                         "mot": next((m["texte"] for m in mots if m["debut"] - 0.02 <= t[k] <= m["fin"] + 0.02), None)}
                    for nom, _ in avec:
                        r[nom] = round(float(P[nom][j][k]), 1)
                    r[sans[0]] = round(float(vs), 1)
                    if controle:
                        r[controle[0]] = round(float(sens * (sens * P[controle[0]][j][w]).max()), 1)
                    res.append(r)
    # une même marche vue dans plusieurs bandes / échelles : on garde la plus forte par 30 ms
    return _regrouper(res, lambda r: min(abs(r[n]) for n, _ in avec))


def contre(x, refs, de=0.0, a=15.0, seuil=10.0, ecart=5.0, plancher=-70.0, mots=(), bandes=None):
    """Marches de x absentes de TOUTES les références refs [(nom, y)] (voir CONTRE) : [{t, bande, court, tenu, avant_db,
    apres_db, <ref>: tenu de la réf., mot, bandes}]."""
    res = []
    for nb, bd in (bandes or BANDES_DIFF).items():
        t, _, court, tenu, av, ap = _marches(x, de, a, bd)
        R = {nom: _marches(y, de, a, bd) for nom, y in refs}
        for sens in (-1, 1):
            ok = ((sens * court >= seuil) & (sens * tenu >= seuil) & (np.maximum(av, ap) > plancher + PLANCHER_GRAVE.get(nb, 0.0))
                  & (t >= de) & (t <= a))
            idx = np.flatnonzero(ok)
            for g in (np.split(idx, np.flatnonzero(np.diff(idx) > 3) + 1) if len(idx) else []):
                k = g[np.argmax(sens * tenu[g])]
                w = slice(max(0, k - 3), k + 4)
                vr = {nom: float(sens * (sens * R[nom][3][w]).max()) for nom in R}
                if any(abs(tenu[k]) - max(0.0, sens * v) < ecart for v in vr.values()):
                    continue                      # une référence a la même marche (à ecart dB près) : pas propre à x
                r = {"t": round(float(t[k]), 3), "bande": nb, "court": round(float(court[k]), 1),
                     "tenu": round(float(tenu[k]), 1), "avant_db": round(float(av[k]), 1), "apres_db": round(float(ap[k]), 1),
                     "mot": next((m["texte"] for m in mots if m["debut"] - 0.04 <= t[k] <= m["fin"] + 0.04), None)}
                r.update({nom: round(v, 1) for nom, v in vr.items()})
                res.append(r)
    return _regrouper(res, lambda r: abs(r["tenu"]))


# ── repères : un petit son émerge-t-il de ce qui l'entoure ? ───────────────
def puissances_bandes(x, bandes=BANDES_REPERES, nfft=1024, pas=240, debuts=None):
    """Puissance par trame (Hann 21 ms, pas 5 ms) et par bande, moyenne des deux canaux (linéaire, 0 dB = sinus pleine
    échelle) : t (centres, s), P (trames, bandes). debuts (option, 28/09) : les débuts des trames en échantillons (une
    grille alignée sur le film d'avant une insertion de temps : chronologie.debuts_trames) au lieu de k·pas."""
    x = L.stereo(x)
    w = np.hanning(nfft)
    if debuts is not None:
        debuts = np.asarray(debuts, dtype=np.int64)
        f = np.fft.rfftfreq(nfft, 1 / SR)
        masques = [(f >= f1) & (f < f2) for f1, f2 in bandes]
        ref = (w.sum() / 2) ** 2 / 2
        P = np.zeros((len(debuts), len(bandes)))
        for i0 in range(0, len(debuts), 2000):
            k = debuts[i0:i0 + 2000]
            idx = np.arange(nfft)[None, :] + k[:, None]
            S = sum(np.abs(np.fft.rfft(x[idx, c] * w, axis=1)) ** 2 for c in range(2)) / 2 / ref
            P[i0:i0 + len(k)] = np.stack([S[:, m].sum(axis=1) for m in masques], axis=1)
        return (debuts + nfft / 2) / SR, P
    nb = max(1, (len(x) - nfft) // pas + 1)
    f = np.fft.rfftfreq(nfft, 1 / SR)
    masques = [(f >= f1) & (f < f2) for f1, f2 in bandes]
    ref = (w.sum() / 2) ** 2 / 2
    P = np.zeros((nb, len(bandes)))
    for i0 in range(0, nb, 2000):
        k = np.arange(i0, min(nb, i0 + 2000))
        idx = np.arange(nfft)[None, :] + pas * k[:, None]
        S = sum(np.abs(np.fft.rfft(x[idx, c] * w, axis=1)) ** 2 for c in range(2)) / 2 / ref
        P[k] = np.stack([S[:, m].sum(axis=1) for m in masques], axis=1)
    return (np.arange(nb) * pas + nfft / 2) / SR, P


def fenetre_repere(q, duree_defaut=0.25, duree_max=1.5):
    a = float(q["t"])
    b = float(q["fin"]) if q.get("fin") else a + duree_defaut
    return a, min(b, a + duree_max)


def trames_actives(t, Ps, a, b, actif_db=10.0):
    """Masque (trames, bandes) : trames de [a ; b] où le repère est à moins de actif_db de son maximum dans la bande."""
    dans = (t >= a) & (t <= b)
    m = np.zeros(Ps.shape, bool)
    if not dans.any():
        return m
    mx = Ps[dans].max(axis=0)
    m[dans] = Ps[dans] >= mx[None, :] * 10 ** (-actif_db / 10)
    return m & (mx[None, :] > 1e-14)


def somme_active(P, m):
    """Somme par bande de P (trames, bandes) sur le masque m (trames, bandes)."""
    return np.where(m, P, 0.0).sum(axis=0)


def emergences(Ps, Pr, m):
    """Émergence par bande (dB) du repère (Ps) contre le reste (Pr), sur les trames actives m ; −99 si le repère est
    absent de la bande."""
    s, r = somme_active(Ps, m), somme_active(Pr, m)
    return np.where(s > 1e-14, 10 * np.log10((s + 1e-30) / (r + 1e-30)), -99.0)


def _libelle(b):
    f1, f2 = b
    k = lambda f: f"{f / 1000:g}k" if f >= 1000 else f"{f:g}"          # noqa: E731
    return f"{k(f1)}-{k(f2)}"


def reperes(stems, cues, ref=None, ignorer=(), duree_defaut=0.25, duree_max=1.5, f_max=8000.0, cible_db=6.0,
            actif_db=10.0, bandes=BANDES_REPERES, cibles_par_id=None, cues_ref=None, debuts=None):
    """Voir REPÈRE. stems, ref : {couche: (n, 2)} ; cues : [{id, couche, t, fin?}] ; cues_ref (option) : les cues du film
    de la référence, la fenêtre de la référence est alors celle du même id (un film où du temps a été inséré). Renvoie
    [{id, couche, de, a, mix [dB par bande], ref [dB par bande], meilleure_mix, meilleure_ref (bande ≤ f_max), cible_db,
    ok}]."""
    par_id = {q["id"]: q for q in (cues_ref or [])}
    def tables(S, d=None):
        T = {k: puissances_bandes(v, bandes, debuts=d) for k, v in S.items()}
        tot = sum(p for _, p in T.values())
        return T, tot
    Tm, totm = tables(stems, debuts)          # debuts : la grille du film actuel (alignée sur le film d'avant)
    Tr, totr = tables(ref) if ref else (None, None)
    crit = [i for i, b in enumerate(bandes) if b[1] <= f_max]
    out = []
    for q in cues:
        if q["id"] in ignorer or q["couche"] not in stems:
            continue
        a, b = fenetre_repere(q, duree_defaut, duree_max)
        t, Ps = Tm[q["couche"]]
        m = trames_actives(t, Ps, a, b, actif_db)
        em = emergences(Ps, totm - Ps, m)
        r = {"id": q["id"], "couche": q["couche"], "de": round(a, 3), "a": round(b, 3), "bandes": [_libelle(x) for x in bandes],
             "mix": [round(float(v), 1) for v in em]}
        km = max(crit, key=lambda i: em[i])
        r["meilleure_mix"] = {"bande": _libelle(bandes[km]), "db": round(float(em[km]), 1)}
        cible = (cibles_par_id or {}).get(q["id"], cible_db)
        if Tr and q["couche"] in Tr and cues_ref is not None and q["id"] not in par_id:
            r["ref"], r["meilleure_ref"] = None, None     # né dans ce film (absent des cues de la référence) : pas de
            r["sans_reference"] = True                    # référence, la cible par défaut (avant : même fenêtre, −99 dB)
        elif Tr and q["couche"] in Tr:
            tr, Pr = Tr[q["couche"]]
            ar, br = fenetre_repere(par_id[q["id"]], duree_defaut, duree_max) if q["id"] in par_id else (a, b)
            mr = trames_actives(tr, Pr, ar, br, actif_db)
            er = emergences(Pr, totr - Pr, mr)
            kr = max(crit, key=lambda i: er[i])
            r["ref"] = [round(float(v), 1) for v in er]
            r["meilleure_ref"] = {"bande": _libelle(bandes[kr]), "db": round(float(er[kr]), 1)}
            cible = min(cible, float(er[kr]))
        r["cible_db"] = round(cible, 1)
        r["ok"] = bool(em[km] >= cible - 0.05)
        out.append(r)
    return out


def jointures(x, dialogue, garde=0.005, fen=0.020):
    """Marche au bord de chaque extrait (film_in, film_out) : niveaux 2-8 kHz et large bande de part et d'autre."""
    hb = L.passe_bande(L.mono(x), 2000, 8000, front=0.15)
    lx = L.mono(x)

    def lv(s, a, b):
        v = s[max(0, int(a * SR)):int(b * SR)]
        return float(10 * np.log10(np.mean(v * v) + 1e-24)) if len(v) else -240.0
    out = []
    for e in dialogue["extraits"]:
        for bord, t in (("in", e["film_in"]), ("out", e["film_out"])):
            r = {"extrait": e["id"], "bord": bord, "t": t}
            for nom, s in (("hf", hb), ("large", lx)):
                av, ap = lv(s, t - garde - fen, t - garde), lv(s, t + garde, t + garde + fen)
                r[f"{nom}_avant"], r[f"{nom}_apres"], r[f"{nom}_marche"] = round(av, 1), round(ap, 1), round(ap - av, 1)
            out.append(r)
    return out


def raccords(x, dialogue, mots, bande=(4000, 8000), fen=0.020, pas=0.010, marge=0.030, plancher=-90.0):
    """Pour chaque passage d'un extrait au suivant (dialogue.json), sur la zone qui va de la fin du dernier mot de
    l'un au début du premier mot de l'autre (mots.json, ±marge) : plus forte chute et plus forte montée entre deux
    fenêtres de 20 ms voisines dans la bande (4-8 kHz par défaut : la texture de la ligne, que la musique ne couvre
    pas), et niveau minimal de la zone. Indépendant de l'endroit exact des coupes : compare deux montages. Les niveaux
    sont bornés à `plancher` (−90 dB) : une « marche » entre deux silences inaudibles n'en est pas une."""
    t, l = niveaux_glissants(x, fen, pas, bande)
    l = np.maximum(l, plancher)
    ex = dialogue["extraits"]
    out = []
    for e1, e2 in zip(ex, ex[1:]):
        m1 = [w for w in mots if w["extrait"] == e1["id"]]
        m2 = [w for w in mots if w["extrait"] == e2["id"]]
        a = max(w["fin"] for w in m1) - marge
        b = min(w["debut"] for w in m2) + marge
        k = (t >= a) & (t <= b)
        lk = l[k]
        d = lk[2:] - lk[:-2] if len(lk) > 2 else np.zeros(1)
        out.append({"raccord": f"{e1['id']}→{e2['id']}", "de": round(a, 3), "a": round(b, 3),
                    "chute_max_db": round(float(d.min()), 1), "t_chute": round(float(t[k][1:-1][np.argmin(d)]), 3),
                    "montee_max_db": round(float(d.max()), 1), "t_montee": round(float(t[k][1:-1][np.argmax(d)]), 3),
                    "niveau_min_db": round(float(lk.min()), 1)})
    return out


def mots_niveaux(x, mots, cles):
    """Pour chaque clé « EXTRAIT:rang » : LUFS du mot (pondération K, sans porte) et niveau 1-4 kHz (dBFS RMS)."""
    xk = L.ponderer_k(x)
    hb = L.passe_bande(L.mono(x), 1000, 4000, front=0.15)
    out = {}
    for c in cles:
        ex, rg = c.split(":")
        w = next(m for m in mots if m["extrait"] == ex and m["rang"] == int(rg))
        a, b = w["debut"], w["fin"]
        s = hb[int(a * SR):int(b * SR)]
        out[f"{c} {w['cle']}"] = {"debut": a, "fin": b, "lufs": round(L.sonie(x, a, b, xk=xk), 2),
                                   "bande_1_4k_db": round(float(10 * np.log10(np.mean(s * s) + 1e-24)), 2),
                                   "crete_1_4k_db": round(float(L.db(np.abs(s).max())), 2)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sautes", "trous", "differentiel", "contre", "reperes", "jointures", "raccords", "mots",
                                    "planche", "sonie"])
    ap.add_argument("fichiers", nargs="+")
    ap.add_argument("--de", type=float, default=0.0)
    ap.add_argument("--a", type=float, default=None)
    ap.add_argument("--mots")
    ap.add_argument("--dialogue")
    ap.add_argument("--evenements")
    ap.add_argument("--cles", nargs="*", default=[])
    ap.add_argument("--seuil", type=float, default=10.0)
    ap.add_argument("--sans", nargs="+", help="differentiel : nom=fichier de la version SANS le défaut ; contre : les références")
    ap.add_argument("--plancher", type=float, default=-70.0, help="differentiel, contre : côté fort minimal (dBFS dans la bande)")
    ap.add_argument("--ecart", type=float, default=5.0)
    ap.add_argument("--cues", help="reperes : cues.json ({cues: [{id, couche, t, fin}]})")
    ap.add_argument("--ref", help="reperes : dossier des stems de référence")
    ap.add_argument("--cues-ref", help="reperes : cues du film de la référence (fenêtre par id, si du temps a été inséré)")
    ap.add_argument("--insertions", help="reperes : son/dialogue.json : trames alignées sur le film d'avant (comme mixer.py)")
    ap.add_argument("--ignorer", nargs="*", default=["fond-piece", "air-trajets"])
    ap.add_argument("--fmax", type=float, default=8000.0)
    ap.add_argument("--cible", type=float, default=6.0)
    ap.add_argument("--controle", help="differentiel : nom=fichier du nouveau mix à contrôler")
    ap.add_argument("--png")
    ap.add_argument("--px", type=float, default=100)
    ap.add_argument("--json")
    a = ap.parse_args()
    pistes = charger(a.fichiers) if a.cmd != "reperes" else []
    rapport = {}
    if a.cmd == "sautes":
        mots = lire_mots(a.mots)
        for nom, x in pistes:
            r = sautes(x, a.de, a.a, mots, a.seuil)
            rapport[nom] = r
            print(f"== {nom} : {len(r)} marche(s) du fond ≥ {a.seuil} dB hors mots")
            for s in r:
                print(f"   {s['t']:7.3f} s  {s['bande']:8s} {s['avant_db']:7.1f} → {s['apres_db']:7.1f}  ({s['delta_db']:+.1f} dB)")
    elif a.cmd == "trous":
        mots = lire_mots(a.mots)
        for nom, x in pistes:
            r = trous(x, a.de, a.a, mots, a.seuil)
            rapport[nom] = r
            print(f"== {nom} : {len(r)} trou(s) du fond (chute ≥ {a.seuil} dB en ≤ 30 ms, tenue ≥ 60 ms, hors mots)")
            for s_ in r:
                print(f"   {s_['t']:7.3f} s  {s_['bande']:8s} réf {s_['ref_db']:6.1f} → {s_['fond_db']:6.1f} dB "
                      f"({s_['profondeur_db']:+.1f})  pendant {s_['duree_s'] * 1000:4.0f} ms  refermé par {s_['referme']}")
    elif a.cmd == "differentiel":
        assert a.sans, "--sans nom=fichier obligatoire"
        mots = lire_mots(a.mots)
        sans = charger(a.sans[:1])[0]
        ctl = charger([a.controle])[0] if a.controle else None
        fin = a.a or min(len(x) for _, x in pistes) / SR
        r = differentiel(pistes, sans, ctl, a.de, fin, a.seuil, a.ecart, mots=mots, plancher=a.plancher)
        rapport = {"avec": [n for n, _ in pistes], "sans": sans[0], "controle": ctl[0] if ctl else None, "marches": r}
        noms = [n for n, _ in pistes] + [sans[0]] + ([ctl[0]] if ctl else [])
        print(f"== marches ≥ {a.seuil} dB dans {', '.join(noms[:len(pistes)])} et ≥ 5 dB plus faibles dans {sans[0]}"
              f" ({a.de:g}-{fin:g} s)")
        for m in r:
            print(f"   {m['t']:7.3f} s  {m['bande']:7s} {m['echelle']:5s}  " + "  ".join(f"{n} {m[n]:+6.1f}" for n in noms)
                  + f"   bandes {','.join(m['bandes'])}" + (f"   (dans le mot « {m['mot']} »)" if m["mot"] else ""))
    elif a.cmd == "contre":
        assert a.sans, "--sans nom=fichier … obligatoire"
        mots = lire_mots(a.mots)
        refs = charger(a.sans)
        for nom, x in pistes:
            fin = a.a or len(x) / SR
            r = contre(x, refs, a.de, fin, a.seuil, a.ecart, a.plancher, mots)
            rapport[nom] = r
            hors = [m for m in r if not m["mot"]]
            print(f"== {nom} contre {', '.join(n for n, _ in refs)} ({a.de:g}-{fin:g} s) : {len(hors)} marche(s) propres hors mots, "
                  f"{len(r) - len(hors)} dans les mots")
            for m in r:
                print(f"   {m['t']:7.3f} s  {m['bande']:7s} court {m['court']:+6.1f}  tenu {m['tenu']:+6.1f}  "
                      f"({m['avant_db']:6.1f} → {m['apres_db']:6.1f} dBFS)  " + "  ".join(f"{n} {m[n]:+6.1f}" for n, _ in refs)
                      + f"   bandes {','.join(m['bandes'])}" + (f"   (mot « {m['mot']} »)" if m["mot"] else ""))
    elif a.cmd == "reperes":
        import glob
        lire_d = lambda d: {Path(f).stem: L.lire(f) for f in sorted(glob.glob(f"{d}/*.wav"))}   # noqa: E731
        cues = json.loads(Path(a.cues).read_text())["cues"]
        cues_ref = json.loads(Path(a.cues_ref).read_text())["cues"] if a.cues_ref else None
        st_ = lire_d(a.fichiers[0])
        deb = None
        if a.insertions:                      # la grille des trames alignée sur le film d'avant (comme mixer.py)
            import chronologie as CH
            deb = CH.charger(a.insertions).debuts_trames(len(next(iter(st_.values()))), 240, 1024)
        r = reperes(st_, cues, lire_d(a.ref) if a.ref else None, a.ignorer, f_max=a.fmax, cible_db=a.cible,
                    cues_ref=cues_ref, debuts=deb)
        rapport = {"stems": a.fichiers[0], "ref": a.ref, "reperes": r}
        print(f"== {len(r)} repères, émergence de la meilleure bande ≤ {a.fmax:g} Hz (cible min({a.cible:g}, référence))")
        for q in r:
            ref_ = f"réf {q['meilleure_ref']['db']:+6.1f} ({q['meilleure_ref']['bande']:>8s})  " if q.get("meilleure_ref") else ("sans réf.           " if q.get("sans_reference") else "")
            print(f"   {q['id']:24s} {q['de']:6.2f}-{q['a']:5.2f} {q['couche']:9s} {ref_}mix {q['meilleure_mix']['db']:+6.1f} "
                  f"({q['meilleure_mix']['bande']:>8s})  {'ok' if q['ok'] else 'ENTERRÉ'}   8-16k : "
                  + (f"réf {q['ref'][-1]:+.1f} " if q.get("ref") else "") + f"mix {q['mix'][-1]:+.1f}")
    elif a.cmd == "jointures":
        dia = json.loads(Path(a.dialogue).read_text())
        for nom, x in pistes:
            r = jointures(x, dia)
            rapport[nom] = r
            print(f"== {nom}")
            for j in r:
                print(f"   {j['extrait']:5s} {j['bord']:3s} {j['t']:7.3f}  2-8 kHz {j['hf_avant']:7.1f} → {j['hf_apres']:7.1f} "
                      f"({j['hf_marche']:+6.1f})   large {j['large_avant']:7.1f} → {j['large_apres']:7.1f} ({j['large_marche']:+6.1f})")
    elif a.cmd == "raccords":
        dia = json.loads(Path(a.dialogue).read_text())
        mots = lire_mots(a.mots)
        for nom, x in pistes:
            r = raccords(x, dia, mots)
            rapport[nom] = r
            print(f"== {nom} (4-8 kHz, entre le dernier mot d'un extrait et le premier du suivant)")
            for j in r:
                print(f"   {j['raccord']:10s} {j['de']:7.3f} → {j['a']:7.3f}  chute {j['chute_max_db']:+6.1f} dB à {j['t_chute']:.3f}  "
                      f"montée {j['montee_max_db']:+6.1f} dB à {j['t_montee']:.3f}  plancher {j['niveau_min_db']:7.1f} dB")
    elif a.cmd == "mots":
        mots = lire_mots(a.mots)
        for nom, x in pistes:
            r = mots_niveaux(x, mots, a.cles)
            rapport[nom] = r
            print(f"== {nom}")
            for k, v in r.items():
                print(f"   {k:14s} {v['debut']:.3f}-{v['fin']:.3f}  {v['lufs']:7.2f} LUFS   1-4 kHz {v['bande_1_4k_db']:7.2f} dB")
    elif a.cmd == "planche":
        rep = []
        if a.dialogue:
            for e in json.loads(Path(a.dialogue).read_text())["extraits"]:
                rep += [(e["film_in"], e["id"]), (e["film_out"], "/")]
        if a.evenements:
            for k, v in json.loads(Path(a.evenements).read_text()).items():
                if isinstance(v, dict) and "t" in v:
                    rep.append((v["t"][0] if isinstance(v["t"], list) else v["t"], k[:10]))
        fin = a.a or min(len(x) for _, x in pistes) / SR
        print(L.planche(pistes, a.de, fin, a.png, reperes=rep, px_par_s=a.px))
    elif a.cmd == "sonie":
        cols = [L.ENCRE, L.SOLAIRE, L.TERRA, L.VERT, L.GRIS]
        series = []
        for k, (nom, x) in enumerate(pistes):
            t, s = L.sonie_courbe(x, 3.0)
            series.append((f"{nom} S", t, s, cols[k % len(cols)]))
            rapport[nom] = {"S_max": round(float(s.max()), 2), "t_S_max": round(float(t[np.argmax(s)]), 1), **L.mesure(x)}
            print(nom, rapport[nom])
        rep = []
        if a.evenements:
            ev = json.loads(Path(a.evenements).read_text())
            for k in ("decroche", "raccroche", "signature_re_contact"):
                if k in ev:
                    rep.append((ev[k]["t"], k[:9]))
        fin = a.a or max(len(x) for _, x in pistes) / SR
        if a.png:
            print(L.courbe_png(series, a.png, a.de, fin, -40, -6, px_par_s=20, reperes=rep, titre="sonie court terme (3 s)"))
    if a.json:
        Path(a.json).write_text(json.dumps(rapport, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
