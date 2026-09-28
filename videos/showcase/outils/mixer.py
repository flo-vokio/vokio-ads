#!/usr/bin/env python3
"""Mixeur générique piloté par une RECETTE JSON : pistes, gains, mutes, EQ, pan, sidechain sous la voix, garde de la
voix mot par mot, bus master (sonie, crête vraie, limiteur), sorties (wav + stems), mesures, planches, vidéo, Drive.

    python3 outils/mixer.py son/recettes/hybride.json                       mix + stems + mesures + planches
    python3 outils/mixer.py son/recettes/hybride.json --video in.mp4 --mp4 out.mp4   + muxage (flux vidéo copié, AAC 256k 48 kHz)
    python3 outils/mixer.py son/recettes/hybride.json --drive "Dossier/Sous-dossier" [--simuler]   + dépôt rclone
    python3 outils/mixer.py son/recettes/hybride.json --force                recalcule même si rien n'a changé
    python3 outils/mixer.py son/recettes/hybride.json --planches /tmp/p      planches ailleurs que dans la recette
    python3 outils/mixer.py --modele                                        imprime une recette modèle commentée
Idempotent : l'empreinte (recette + contenu des fichiers d'entrée) est inscrite dans le JSON des mesures ; si rien n'a
changé et que les sorties existent, le mix n'est pas recalculé (les options --video / --drive s'appliquent quand même).
Chemins de la recette : relatifs au dossier de la recette (ou absolus) ; "racine" préfixe les fichiers des pistes.

LA RECETTE (clés ; toutes optionnelles sauf "pistes")
  nom, description, sr (48000), duree (s, sinon la plus longue piste), racine
  pistes : [{nom, fichier, role ("voix" pour la piste de référence de la voix), gain_db, automation [[t, dB], …]
            (linéaire par morceaux, s'ajoute au gain), eq [{type cloche|grave|aigu|passe_haut|passe_bas, f, g, q, front}],
            pan (balance −1…1), muets [[a, b], …] + fondu_muet (s, 0 = coupe franche à l'échantillon), note}]
  sidechain : [{source, cibles [noms], profondeur_db, seuil_db (−40), attaque (0,03), relache (0,25), anticipation (0,08),
               tenue (0,12), bande [f1, f2] (optionnelle : creux dans cette bande seulement), note}]
  garde_voix : {voix, mots (mots.json), marge_lu (sonie K voix − reste, par mot), marge_bande_db + bande [f1, f2],
               cibles [noms à baisser], plancher_db (baisse max), perte_max_db (1 : si les pistes NON ciblées mangent
               déjà la marge, les cibles ne la réduisent pas de plus de 1 dB), duree_min (0,10 s : un mot plus court,
               « Je » de 30 ms, est mesuré sur 100 ms), actif_db (option : la marge se mesure sur les trames de 10 ms
               où la voix est à moins de actif_db de son maximum dans le mot, pas dans les blancs), rampe (s)} ;
               seules les cibles baissent
  garde_reperes : {cues (cues.json : [{id, couche, t, fin}]), reference (dossier des stems où ces sons ont été validés),
               cibles [pistes à creuser] (["musique"]), bande [f1, f2] ([3500, 16000] : le creux, dans cette bande
               seulement), cible_db (6), f_max (8000 : bandes du critère), plancher_db (−10), hausse_max_db (6 : la piste
               du repère peut monter d'autant sur sa fenêtre), poids_hausse (1,25 : coût d'un dB de hausse contre un dB
               de creux), marge_db (0,5 : visée au-dessus de la cible), avance (0,03 s), relache (0,15 s), au_mieux
               (false : hors d'atteinte, on ne fait rien plutôt qu'un creux inutile), ignorer [ids], par_repere {id: {mêmes
               clés, ou "exclu": "raison"}}, cues_reference (option : les cues du film de la référence ; l'émergence
               d'un repère dans la référence se mesure alors à SA fenêtre dans ce fichier, par id : un repère qui a
               bougé autrement que le reste garde sa vraie référence ; un repère ABSENT de ce fichier, né dans le film
               actuel (l'écriture du nom depuis l'échange du prénom), n'a pas de référence : cible_db par défaut)} :
               pour chaque repère, émergence par bande (outils/ausculter.py REPÈRE) ; si la
               meilleure bande ≤ f_max n'émerge pas de min(cible_db, émergence dans la référence), creux des cibles dans
               `bande` et/ou hausse du repère, au moindre coût, rampes cosinus ; AVANT la garde de la voix (la voix a le
               dernier mot)
  insertions : dialogue.json (option, 28/09) : les trames d'analyse de garde_reperes et de mesures.reperes sont posées sur
               la grille du film d'avant les insertions de temps (outils/chronologie.py debuts_trames) : après une mesure
               insérée, chaque repère est mesuré, et décidé, comme dans le film validé
  silences : [[a, b], …]   zéros numériques EXACTS imposés sur toutes les pistes, puis vérifiés
  master : {lufs (−14), plafond_dbtp (−1,7 : ≤ −1 dBTP après AAC), anticipation, relache}
  sorties : {wav, stems (dossier), mesures (json), planches (dossier), copies [chemins]}
  mesures : {references {nom: wav, ou nom: {fichier, insertions (dialogue.json)} : une référence du film d'avant lue à
             travers les insertions de temps, silence dans chaque mesure insérée (outils/chronologie.py)} (comparées au
             mix), dialogue (dialogue.json : jointures et raccords 4-8 kHz, avec
             mots_json), mots [« C1:0 »…],
             sautes [[de, a], …], evenements (evenements.json : repères), arc {apres: t, marge_lu}, zooms [[de, a, px]],
             differentiel {avec [noms de références qui ont le défaut], sans nom de la référence qui ne l'a pas,
             fenetres [[de, a], …], seuil (10)} : les marches qui existent dans « avec » et pas dans « sans »
             (outils/ausculter.py differentiel), et ce qu'en fait le mix : « résolue » si |mix| ≤ |sans| + 2 dB,
             contre {sans [noms de références], fenetres, seuil (10), ecart (5), plancher (−70), voulus [[de, a, raison]]}
             (ou une liste de tels blocs) :
             le CRITÈRE D'ACCEPTATION, marches du mix qu'aucune de ces références n'a (outils/ausculter.py contre),
             hors mots ; « voulue » si elle tombe dans une fenêtre de `voulus` (un son composé exprès),
             reperes {} (reprend garde_reperes ; mêmes clés pour changer) : émergence finale de chaque repère}
Si le dossier des pistes (racine) contient stems-amont.json, ses réglages (ligne, musique) sont recopiés dans le rapport
("amont") : une seule source pour les valeurs appliquées en amont (les notes de la recette n'en répètent aucune).
Aucune écriture hors des chemins de "sorties", de --mp4 et du Drive (--drive).
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sonlib as L  # noqa: E402
import ausculter as A  # noqa: E402
import chronologie as CH  # noqa: E402

MODELE = {
    "nom": "exemple", "description": "musique + voix, la musique se creuse sous la voix", "duree": 30.0,
    "racine": "stems",
    "pistes": [
        {"nom": "voix", "fichier": "voix.wav", "role": "voix", "gain_db": 0.0},
        {"nom": "musique", "fichier": "musique.wav", "gain_db": -3.0, "eq": [{"type": "cloche", "f": 2500, "g": -2, "q": 1.5}],
         "muets": [[12.0, 12.8]], "fondu_muet": 0.02},
    ],
    "sidechain": [{"source": "voix", "cibles": ["musique"], "profondeur_db": -6, "bande": [1000, 4000]}],
    "garde_voix": {"voix": "voix", "mots": "mots.json", "marge_lu": 10, "cibles": ["musique"], "plancher_db": -8},
    "silences": [[29.7, 30.0]],
    "master": {"lufs": -14.0, "plafond_dbtp": -1.7},
    "sorties": {"wav": "sortie/mix.wav", "stems": "sortie/stems", "mesures": "sortie/mesures.json", "planches": "sortie/planches"},
    "mesures": {"references": {"avant": "ancien-mix.wav", "sans défaut": "autre-mix.wav"}, "mots": ["C1:0", "C1:1"],
                "sautes": [[0, 15]], "zooms": [[0, 15, 100]],
                "differentiel": {"avec": ["avant"], "sans": "sans défaut", "fenetres": [[0, 15]], "seuil": 10}},
}


# ── lecture de la recette ──────────────────────────────────────────────────
def chemin(base, p):
    if p is None:
        return None
    q = Path(p)
    return q if q.is_absolute() else (base / q).resolve()


def charger_recette(fichier):
    R = json.loads(Path(fichier).read_text())
    base = Path(fichier).resolve().parent
    R["_base"] = base
    racine = chemin(base, R.get("racine", "."))
    for p in R["pistes"]:
        p["_fichier"] = chemin(racine, p["fichier"])
    return R


def empreinte(R, fichier):
    h = hashlib.sha256(Path(fichier).read_bytes())
    for p in R["pistes"]:
        h.update(p["_fichier"].read_bytes())
    m = R.get("mesures", {})
    for k in ("dialogue", "evenements"):
        if m.get(k):
            h.update(chemin(R["_base"], m[k]).read_bytes())
    if R.get("insertions"):
        h.update(chemin(R["_base"], R["insertions"]).read_bytes())
    if R.get("garde_voix", {}).get("mots"):
        h.update(chemin(R["_base"], R["garde_voix"]["mots"]).read_bytes())
    Gr = R.get("garde_reperes") or {}
    for cle in ("cues", "cues_reference"):
        if Gr.get(cle):
            h.update(chemin(R["_base"], Gr[cle]).read_bytes())
    if Gr.get("reference"):
        for f in sorted(chemin(R["_base"], Gr["reference"]).glob("*.wav")):
            h.update(f.name.encode()); h.update(str(f.stat().st_size).encode()); h.update(str(f.stat().st_mtime_ns).encode())
    for f in (Path(__file__), Path(L.__file__), Path(A.__file__), Path(CH.__file__)):
        h.update(f.read_bytes())
    return h.hexdigest()


# ── traitement par piste ───────────────────────────────────────────────────
def automation(n, points):
    t = np.arange(n) / L.SR
    tt = [a for a, _ in points]; vv = [b for _, b in points]
    return L.gain(np.interp(t, tt, vv))


def traiter_piste(p, n):
    x = L.stereo(L.lire(p["_fichier"]))
    if len(x) < n:
        x = np.concatenate([x, np.zeros((n - len(x), 2))])
    x = x[:n].copy()
    journal = []
    if p.get("gain_db"):
        x *= L.gain(p["gain_db"]); journal.append(f"gain {p['gain_db']:+.1f} dB")
    if p.get("automation"):
        x *= automation(n, p["automation"])[:, None]; journal.append(f"automation {len(p['automation'])} points")
    if p.get("eq"):
        x = L.egaliseur(x, p["eq"]); journal.append(f"EQ {len(p['eq'])} bandes")
    if p.get("pan"):
        x = L.balance(x, p["pan"]); journal.append(f"pan {p['pan']:+.2f}")
    # Spatialisation propre à un format (28/09) : une piste spatialisée pour le 9:16 peut contredire l'image
    # d'un autre format. « mono » : true ou [[t0, t1], …] recentre (L = R = (L+R)/2) ; « miroir » : [[t0, t1], …]
    # échange gauche et droite. Fenêtres en secondes, raccords en fondu de « fondu_espace » (défaut 0,03 s).
    for cle, op in (("mono", lambda y: np.repeat(y.mean(axis=1, keepdims=True), 2, axis=1)), ("miroir", lambda y: y[:, ::-1])):
        v = p.get(cle)
        if not v:
            continue
        fen = [[0.0, n / L.SR]] if v is True else v
        env = L.enveloppe_fenetres(n, fen, 1.0, p.get("fondu_espace", 0.03), base=0.0)   # poids 1 dans les fenêtres
        x = x * (1 - env[:, None]) + op(x) * env[:, None]
        journal.append(f"{cle} {'film entier' if v is True else v}")
    if p.get("muets"):
        f = p.get("fondu_muet", 0.0)
        env = L.enveloppe_fenetres(n, p["muets"], 0.0, f) if f > 0 else np.ones(n)
        if f <= 0:
            for a, b in p["muets"]:
                env[int(round(a * L.SR)):int(round(b * L.SR))] = 0.0
        x *= env[:, None]; journal.append(f"muets {p['muets']} (fondu {f * 1000:.0f} ms)")
    return x, journal


def sidechain(pistes, regle, n):
    src = pistes[regle["source"]]
    t_ms, p = L.presence(src, regle.get("seuil_db", -40.0), regle.get("anticipation", 0.080), regle.get("tenue", 0.120))
    g = L.gain_suiveur(t_ms, regle["profondeur_db"] * p, n, regle.get("attaque", 0.030), regle.get("relache", 0.250))
    for c in regle["cibles"]:
        x = pistes[c]
        if regle.get("bande"):
            b = L.passe_bande(x, *regle["bande"])
            pistes[c] = x - b + b * g[:, None]
        else:
            pistes[c] = x * g[:, None]
    return {"source": regle["source"], "cibles": regle["cibles"], "profondeur_db": regle["profondeur_db"],
            "bande": regle.get("bande"), "part_du_temps_actif": round(float(p.mean()), 3)}


def _p(xk, a, b, m=None):
    """Puissance moyenne de xk sur [a ; b] (s), sur les seuls échantillons où m (bool, longueur de la fenêtre) est vrai."""
    s = xk[int(a * L.SR):int(b * L.SR)]
    if not len(s):
        return 0.0
    e = np.sum(s * s, axis=1)
    if m is not None:
        e = e[m[:len(e)]] if m[:len(e)].any() else e
    return float(np.mean(e))


def _actifs(v, a, b, actif_db, fen=0.010):
    """Masque (échantillons de [a ; b]) des trames de `fen` s où la voix v (filtrée) est à moins de actif_db de sa trame
    la plus forte dans le mot : la marge se mesure là où la voix SONNE, pas dans les blancs que la fenêtre du mot
    enjambe (une porte VAD qui se ferme entre deux syllabes, où le bruit de confort prend le relais)."""
    s = v[int(a * L.SR):int(b * L.SR)]
    e = np.sum(s * s, axis=1)
    w = int(fen * L.SR)
    k = max(1, len(e) // w)
    tr = np.array([e[i * w:(i + 1) * w].mean() if len(e[i * w:(i + 1) * w]) else 0.0 for i in range(k)])
    ok = tr >= tr.max() * 10 ** (-actif_db / 10)
    m = np.repeat(ok, w)
    return np.concatenate([m, np.full(max(0, len(e) - len(m)), ok[-1])])[:len(e)]


def _poids(n, a, b, avance, relache):
    """(i0, i1, w) : w vaut 1 sur [a ; b], rampes cosinus de `avance` s avant et de `relache` s après, 0 ailleurs."""
    i0, i1 = max(0, int((a - avance) * L.SR)), min(n, int(np.ceil((b + relache) * L.SR)) + 1)
    t = np.arange(i0, i1) / L.SR
    w = np.ones(len(t))
    m = t < a
    w[m] = 0.5 - 0.5 * np.cos(np.pi * np.clip((t[m] - (a - avance)) / max(avance, 1e-6), 0, 1))
    m = t > b
    w[m] = 0.5 + 0.5 * np.cos(np.pi * np.clip((t[m] - b) / max(relache, 1e-6), 0, 1))
    return i0, i1, w


def lire_reference(base, v):
    """Une référence de mesure : un wav, ou {fichier, insertions} (un son du film d'avant, silence dans chaque mesure
    insérée : les fenêtres du film actuel y retombent sur le même contenu)."""
    if isinstance(v, dict):
        x = L.lire(chemin(base, v["fichier"]))
        return CH.charger(chemin(base, v["insertions"])).inserer(x) if v.get("insertions") else x
    return L.lire(chemin(base, v))


def debuts_insertions(R, n, pas=240, nfft=1024):
    """28/09 : "insertions" (option de la recette, chemin d'un dialogue.json) : la grille des trames d'analyse de la garde
    des repères et de leurs mesures est alignée sur le film d'avant (chronologie.debuts_trames) ; sans la clé : None, la
    grille de toujours."""
    return CH.charger(chemin(R["_base"], R["insertions"])).debuts_trames(n, pas, nfft) if R.get("insertions") else None


def lire_stems(dossier):
    return {f.stem: L.stereo(L.lire(f)) for f in sorted(Path(dossier).glob("*.wav"))}


def garde_reperes(pistes, Gr, n):
    """Chaque petit son (repère de cues.json) doit émerger du reste du mix dans sa meilleure bande ≤ f_max d'au moins
    min(cible_db, son émergence dans la référence) : sinon, creux des cibles dans `bande` (g ≤ 0, jusqu'à plancher_db) et/ou
    hausse de la piste du repère (h ≥ 0, jusqu'à hausse_max_db), au moindre coût |g| + poids_hausse·h (grille de 0,5 dB),
    sur [t − avance ; fin + relache] en cosinus. Renvoie le journal, repère par repère."""
    cues = json.loads(Path(Gr["_cues"]).read_text())["cues"]
    cues_ref = ({q["id"]: q for q in json.loads(Path(Gr["_cues_ref"]).read_text())["cues"]} if Gr.get("_cues_ref") else {})
    ign, par = set(Gr.get("ignorer", [])), Gr.get("par_repere", {})
    bandes = A.BANDES_REPERES
    D = Gr.get("_debuts")                    # la grille des trames (alignée sur le film d'avant une insertion)
    T = {k: A.puissances_bandes(v, bandes, debuts=D) for k, v in pistes.items()}
    tot = sum(P for _, P in T.values())
    Tr = totr = None
    if Gr.get("_ref"):
        ref = lire_stems(Gr["_ref"])
        Tr = {k: A.puissances_bandes(v, bandes) for k, v in ref.items()}
        totr = sum(P for _, P in Tr.values())
    cache = {}

    def dedans(c, f1, f2):                   # puissance de la cible c dans / hors de la bande du creux
        if (c, f1, f2) not in cache:
            xin = L.passe_bande(pistes[c], f1, f2)
            cache[(c, f1, f2)] = (A.puissances_bandes(xin, bandes, debuts=D)[1],
                                  A.puissances_bandes(pistes[c] - xin, bandes, debuts=D)[1])
        return cache[(c, f1, f2)]
    creux, hausses, journal = {}, {}, []
    for q in cues:
        if q["id"] in ign or q["couche"] not in pistes:
            continue
        o = {**{k: v for k, v in Gr.items() if k != "par_repere"}, **par.get(q["id"], {})}
        a, b = A.fenetre_repere(q, o.get("duree_defaut", 0.25), o.get("duree_max", 1.5))
        J = {"id": q["id"], "couche": q["couche"], "de": round(a, 3), "a": round(b, 3)}
        if o.get("exclu"):
            journal.append({**J, "exclu": o["exclu"]}); continue
        f1, f2 = o.get("bande", [3500.0, 16000.0])
        crit = [i for i, bd in enumerate(bandes) if bd[1] <= o.get("f_max", 8000.0)]
        cibles = [c for c in o.get("cibles", ["musique"]) if c in pistes and c != q["couche"]]
        t, Ps = T[q["couche"]]
        m = A.trames_actives(t, Ps, a, b, o.get("actif_db", 10.0))
        s_ = A.somme_active(Ps, m)[crit]
        si = sum(A.somme_active(dedans(c, f1, f2)[0], m) for c in cibles)[crit] if cibles else np.zeros(len(crit))
        so = sum(A.somme_active(dedans(c, f1, f2)[1], m) for c in cibles)[crit] if cibles else np.zeros(len(crit))
        sa = A.somme_active(np.maximum(tot - Ps - sum(T[c][1] for c in cibles), 0.0), m)[crit]
        cible = float(o.get("cible_db", 6.0))
        if Tr and q["couche"] in Tr and cues_ref and q["id"] not in cues_ref:
            # 28/09 : un repère NÉ dans le film actuel (l'écriture du nom depuis l'échange du prénom) n'a pas de référence ;
            # le lire à la même fenêtre dans le film de la référence mesurait un autre moment (−99 dB : aucune garde)
            J["ref_db"] = None
            J["sans_reference"] = "absent de cues_reference : cible par défaut"
        elif Tr and q["couche"] in Tr:
            tr, Pr = Tr[q["couche"]]
            ar, br = (A.fenetre_repere(cues_ref[q["id"]], o.get("duree_defaut", 0.25), o.get("duree_max", 1.5))
                      if q["id"] in cues_ref else (a, b))
            er = A.emergences(Pr, totr - Pr, A.trames_actives(tr, Pr, ar, br, o.get("actif_db", 10.0)))
            J["ref_db"] = round(float(max(er[i] for i in crit)), 1)
            cible = min(cible, J["ref_db"])

        def em(g, h):
            v = 10 ** (h / 10) * s_ / (10 ** (g / 10) * si + so + sa + 1e-30)
            k = int(np.argmax(v))
            return float(10 * np.log10(v[k] + 1e-30)), k
        e0, k0 = em(0.0, 0.0)
        J.update({"cible_db": round(cible, 1), "avant_db": round(e0, 1), "bande_critere": A._libelle(bandes[crit[k0]])})
        if e0 >= cible - 0.05:
            journal.append({**J, "action": "aucune"}); continue
        pl, hm, ph = float(o.get("plancher_db", -10.0)), float(o.get("hausse_max_db", 6.0)), float(o.get("poids_hausse", 1.25))
        marge = float(o.get("marge_db", 0.5))      # on vise un peu au-dessus : la garde de la voix et le limiteur passent après
        choix = None
        for g in np.arange(0.0, pl - 1e-9, -0.5):
            for h in np.arange(0.0, hm + 1e-9, 0.5):
                e, k = em(g, h)
                if e >= cible + marge:
                    cout = (-g + ph * h, h, -g)
                    if choix is None or cout < choix[0]:
                        choix = (cout, float(g), float(h), e, k)
                    break                     # à g fixé, la plus petite hausse suffit
        insuffisant = choix is None
        if insuffisant:                           # hors d'atteinte : rien (un creux inutile abîmerait la musique pour rien),
            e, k = em(pl, hm)                     # sauf "au_mieux" ; le journal dit ce qu'on atteindrait au maximum
            J["atteignable_db"] = round(e, 1)
            choix = (None, pl, hm, e, k) if o.get("au_mieux") else (None, 0.0, 0.0, e0, k0)
        _, g, h, e, k = choix
        J.update({"creux_db": g, "bande_creux": [f1, f2], "cibles": cibles, "hausse_db": h, "prevu_db": round(e, 1),
                  "bande_obtenue": A._libelle(bandes[crit[k]]), "insuffisant": insuffisant})
        av, rl = o.get("avance", 0.03), o.get("relache", 0.15)
        if g < 0 and cibles:
            cle = (tuple(cibles), float(f1), float(f2))
            c_ = creux.setdefault(cle, np.zeros(n))
            i0, i1, w = _poids(n, a, b, av, rl)
            c_[i0:i1] = np.minimum(c_[i0:i1], g * w)
        if h > 0:
            h_ = hausses.setdefault(q["couche"], np.zeros(n))
            i0, i1, w = _poids(n, a, b, av, rl)
            h_[i0:i1] = np.maximum(h_[i0:i1], h * w)
        journal.append(J)
    for (cibles, f1, f2), c_ in creux.items():
        lin = L.gain(c_)[:, None]
        for c in cibles:
            xin = L.passe_bande(pistes[c], f1, f2)
            pistes[c] = pistes[c] - xin + xin * lin
    for k, h_ in hausses.items():
        pistes[k] = pistes[k] * L.gain(h_)[:, None]
    return journal


def garde_voix(pistes, G_, n):
    """Mot par mot (mots.json) : sonie K et énergie dans la bande de la voix contre la somme de tout le reste. Si la
    marge manque, seules les cibles baissent sur le mot (±40 ms, rampes cosinus), du strict nécessaire, jamais sous
    plancher_db. Renvoie (journal des baisses, marges finales mot par mot)."""
    dmin = G_.get("duree_min", 0.10)
    mots = [dict(w, fin=max(w["fin"], w["debut"] + dmin)) for w in json.loads(Path(G_["_mots"]).read_text())["mots"]]
    voix = pistes[G_["voix"]]
    autres = [k for k in pistes if k != G_["voix"]]
    cibles = [k for k in G_["cibles"] if k in pistes]
    mk, mb = G_.get("marge_lu", 10.0), G_.get("marge_bande_db")
    bande = G_.get("bande", [1000, 4000])
    plancher = G_.get("plancher_db", -8.0)
    perte = G_.get("perte_max_db", 1.0)
    rampe, bord = G_.get("rampe", 0.030), 0.040
    filtres = {"K": L.ponderer_k, "bande": lambda x: L.passe_bande(x, *bande)}
    seuils = {"K": mk, "bande": mb}
    F = {c: {k: filtres[c](pistes[k]) for k in [G_["voix"]] + autres} for c in filtres if seuils[c] is not None}
    ad = G_.get("actif_db")                      # None : toute la fenêtre du mot (comportement d'origine)
    MQ = {c: [(_actifs(F[c][G_["voix"]], w["debut"], w["fin"], ad) if ad else None) for w in mots] for c in F}
    P = {c: {k: np.array([_p(F[c][k], w["debut"], w["fin"], MQ[c][i]) for i, w in enumerate(mots)]) for k in F[c]}
         for c in F}
    g_mot = np.zeros(len(mots))                  # dB, par mot, sur les cibles
    for c in F:
        pv = P[c][G_["voix"]]
        pc = sum(P[c][k] for k in cibles) if cibles else np.zeros(len(mots))
        pn = sum(P[c][k] for k in autres if k not in cibles) if len(autres) > len(cibles) else np.zeros(len(mots))
        # le reste permis : la marge voulue, OU, si les pistes non ciblées (touchers, signature…) la mangent déjà
        # seules, au plus perte_max_db de perte à cause des cibles (on ne creuse pas la musique pour rien)
        limite = np.maximum(pv / 10 ** (seuils[c] / 10), pn * 10 ** (perte / 10))
        besoin = (pc + pn > limite) & (pv > 0)
        g2 = np.ones(len(mots))
        ok = besoin & (pc > 0)
        g2[ok] = np.clip((limite[ok] - pn[ok]) / pc[ok], 10 ** (plancher / 10), 1.0)
        g_mot = np.minimum(g_mot, 10 * np.log10(g2))
    courbe = np.zeros(n)
    journal = []
    t = np.arange(n) / L.SR
    for w, g in zip(mots, g_mot):
        if g >= -0.05:
            continue
        a, b = w["debut"] - bord, w["fin"] + bord
        i0, i1 = int((a - rampe) * L.SR), int((b + rampe) * L.SR)
        tt = t[max(0, i0):i1]
        loc = np.ones(len(tt))
        m = tt < a; loc[m] = 0.5 - 0.5 * np.cos(np.pi * (tt[m] - (a - rampe)) / rampe)
        m = tt > b; loc[m] = 0.5 + 0.5 * np.cos(np.pi * (tt[m] - b) / rampe)
        courbe[max(0, i0):i1] = np.minimum(courbe[max(0, i0):i1], g * loc)
        journal.append({"mot": w["texte"], "t": w["debut"], "baisse_db": round(float(g), 2)})
    lin = L.gain(courbe)
    for k in cibles:
        pistes[k] = pistes[k] * lin[:, None]
    Fc = {c: {k: F[c][k] * lin[:, None] for k in cibles} for c in F}
    fin = []
    for i, w in enumerate(mots):
        r = {"mot": w["texte"], "t": w["debut"]}
        for c in F:
            pv = P[c][G_["voix"]][i]
            pr = sum(_p(Fc[c][k], w["debut"], w["fin"], MQ[c][i]) if k in cibles else P[c][k][i] for k in autres)
            pn = sum(P[c][k][i] for k in autres if k not in cibles)
            r[f"marge_{c}"] = round(float(10 * np.log10((pv + 1e-20) / (pr + 1e-20))), 1)
            if 10 * np.log10((pv + 1e-20) / (pn + 1e-20)) < seuils[c]:
                r[f"limite_{c}_par_non_cibles"] = True        # un son voulu (toucher, signature) tombe sur le mot
        fin.append(r)
    return journal, fin


def intervalles(g_lim, seuil_db=1.0):
    """[[de, a, réduction max (dB)], …] où le limiteur baisse de plus de seuil_db."""
    red = -20 * np.log10(np.maximum(g_lim, 1e-9))
    m = red > seuil_db
    if not m.any():
        return []
    i = np.flatnonzero(np.diff(np.concatenate([[0], m.astype(int), [0]])))
    return [[round(a / L.SR, 3), round(b / L.SR, 3), round(float(red[a:b].max()), 2)] for a, b in zip(i[::2], i[1::2])]


# ── le mix ─────────────────────────────────────────────────────────────────
def mixer(R):
    t0 = time.time()
    sr = R.get("sr", L.SR)
    assert sr == L.SR, "sonlib travaille à 48 kHz"
    longueurs = {p["nom"]: len(L.lire(p["_fichier"])) for p in R["pistes"]} if not R.get("duree") else {}
    n = int(round(R["duree"] * sr)) if R.get("duree") else max(longueurs.values())
    pistes, rapport = {}, {"pistes": {}, "sidechain": [], "garde_voix": None}
    for p in R["pistes"]:
        x, j = traiter_piste(p, n)
        pistes[p["nom"]] = x
        rapport["pistes"][p["nom"]] = {"fichier": str(p["_fichier"]), "traitements": j, "note": p.get("note")}
        print(f"   {p['nom']:10s} {', '.join(j) or 'tel quel'}")
    for r in R.get("sidechain", []):
        rapport["sidechain"].append(sidechain(pistes, r, n))
        print(f"   sidechain {r['source']} → {r['cibles']} {r['profondeur_db']} dB {r.get('bande') or 'large bande'}")
    if R.get("garde_reperes"):
        Gr = dict(R["garde_reperes"]); Gr["_cues"] = chemin(R["_base"], Gr["cues"])
        Gr["_cues_ref"] = chemin(R["_base"], Gr["cues_reference"]) if Gr.get("cues_reference") else None
        Gr["_ref"] = chemin(R["_base"], Gr["reference"]) if Gr.get("reference") else None
        Gr["_debuts"] = debuts_insertions(R, n)
        jr = garde_reperes(pistes, Gr, n)
        rapport["garde_reperes"] = jr
        act = [j for j in jr if j.get("action") != "aucune" and not j.get("exclu")]
        print(f"   garde des repères : {len(jr)} repères, {len(act)} action(s) : " + "; ".join(
            f"{j['id']} {j['avant_db']:+.1f}→{j['prevu_db']:+.1f} dB (cible {j['cible_db']:+.1f}) creux {j['creux_db']:+.1f} "
            f"hausse {j['hausse_db']:+.1f}" + (" INSUFFISANT" if j["insuffisant"] else "") for j in act)
            + "".join(f"; {j['id']} exclu" for j in jr if j.get("exclu")))
    if R.get("garde_voix"):
        G_ = dict(R["garde_voix"]); G_["_mots"] = chemin(R["_base"], G_["mots"])
        journal, fin = garde_voix(pistes, G_, n)
        mk = [f["marge_K"] for f in fin]; mb = [f.get("marge_bande", 99.0) for f in fin]
        libres = [f for f in fin if not f.get("limite_K_par_non_cibles") and not f.get("limite_bande_par_non_cibles")]
        rapport["garde_voix"] = {"baisses": journal, "marge_K_min_lu": min(mk), "marge_K_mediane_lu": float(np.median(mk)),
                                 "marge_bande_min_db": min(mb), "pire_mot": min(fin, key=lambda f: f["marge_K"]),
                                 "hors_sons_voulus": {"marge_K_min_lu": min(f["marge_K"] for f in libres),
                                                      "marge_bande_min_db": min(f.get("marge_bande", 99.0) for f in libres)},
                                 "mots_limites_par_non_cibles": [f["mot"] + f" ({f['t']:.2f})" for f in fin if f not in libres],
                                 "mots": fin}
        h = rapport["garde_voix"]["hors_sons_voulus"]
        print(f"   garde de la voix : {len(journal)} baisse(s) ; marge K min {min(mk):.1f} LU (médiane {np.median(mk):.1f}), "
              f"bande min {min(mb):.1f} dB ; hors mots où tombe un son voulu non ciblé "
              f"{rapport['garde_voix']['mots_limites_par_non_cibles']} : K min {h['marge_K_min_lu']:.1f} LU, bande min "
              f"{h['marge_bande_min_db']:.1f} dB")
    masque = np.ones(n)
    for a, b in R.get("silences", []):
        masque[int(round(a * sr)):int(round(b * sr))] = 0.0
    for k in pistes:
        pistes[k] *= masque[:, None]
    somme = sum(pistes.values())
    M = R.get("master", {})
    mix, G, g_lim, red = L.masteriser(somme, M.get("lufs", -14.0), M.get("plafond_dbtp", -1.7),
                                      anticipation=M.get("anticipation", 0.0015), relache=M.get("relache", 0.060))
    stems = {k: v * L.gain(G) * g_lim[:, None] for k, v in pistes.items()}
    rapport["master"] = {"gain_db": round(G, 3), "reduction_limiteur_max_db": round(red, 2),
                         "t_reduction_max": round(float(np.argmin(g_lim) / sr), 3),
                         "part_reduction_sup_1_db": round(float(np.mean(g_lim < L.gain(-1.0))), 5),
                         "intervalles_sup_1_db": intervalles(g_lim, 1.0)}
    print(f"   master : gain {G:+.2f} dB, limiteur {red:.2f} dB à {rapport['master']['t_reduction_max']} s ; > 1 dB : "
          f"{rapport['master']['intervalles_sup_1_db']}")
    amont = chemin(R["_base"], R.get("racine", ".")) / "stems-amont.json"
    if amont.exists():
        m_ = json.loads(amont.read_text())
        rapport["amont"] = {"fichier": str(amont), "empreinte": m_.get("empreinte"), "ligne": m_.get("ligne"),
                            "musique": m_.get("musique")}
    rapport["duree_calcul_s"] = round(time.time() - t0, 1)
    return mix, stems, g_lim, rapport


# ── mesures et planches ────────────────────────────────────────────────────
def mesurer(R, mix, stems, g_lim, rapport):
    sr = L.SR
    Ms = R.get("mesures", {})
    out = {"mix": L.mesure(mix)}
    out["crete_vraie_dbtp_numpy"] = round(L.crete_vraie_db(mix), 2)
    out["somme_stems_moins_mix"] = float(np.max(np.abs(sum(stems.values()) - mix)))
    mo = mix.mean(axis=1)
    out["mono_moins_stereo_lu"] = round(L.mesure(mo)["I"] - out["mix"]["I"], 2)
    t, r = L.correlation(mix)
    actif = L.profil(mix, 0.1)[1] > -60
    out["correlation_min"] = round(float(r[:len(actif)][actif[:len(r)]].min()), 2) if actif.any() else None
    out["silences"] = [{"de": a, "a": b, "zeros_exacts": L.zeros_exacts(mix, a, b)} for a, b in R.get("silences", [])]
    ts, S = L.sonie_courbe(mix, 3.0)
    tm, Mo = L.sonie_courbe(mix, 0.4)
    out["sonie_court_terme_max"] = {"t": round(float(ts[np.argmax(S)]), 1), "S": round(float(S.max()), 2)}
    out["sonie_momentanee_max"] = {"t": round(float(tm[np.argmax(Mo)]), 1), "M": round(float(Mo.max()), 2)}
    arc = Ms.get("arc")
    if arc:
        apres = arc["apres"]
        s_fin = float(S[ts >= apres].max()); s_avant = float(S[(ts < apres) & (ts > 3)].max())
        out["arc"] = {"S_max_apres": round(s_fin, 2), "S_max_avant": round(s_avant, 2), "ecart_lu": round(s_fin - s_avant, 2),
                      "sommet_sur_la_fin": bool(s_fin >= s_avant + arc.get("marge_lu", 0.0))}
    refs = {k: lire_reference(R["_base"], v) for k, v in Ms.get("references", {}).items()}
    comp = {"mix": mix, **refs}
    mots = A.lire_mots(chemin(R["_base"], Ms["mots_json"])) if Ms.get("mots_json") else []
    if Ms.get("mots") and mots:
        out["mots"] = {k: A.mots_niveaux(x, mots, Ms["mots"]) for k, x in comp.items()}
        if R.get("garde_voix"):
            v = stems[R["garde_voix"]["voix"]]
            out["mots"]["voix_seule"] = A.mots_niveaux(v, mots, Ms["mots"])
    if Ms.get("sautes"):
        out["sautes"] = {}
        for de, a in Ms["sautes"]:
            out["sautes"][f"{de}-{a}"] = {k: A.sautes(x, de, a, mots, Ms.get("seuil_saute", 10.0)) for k, x in comp.items()}
    D = Ms.get("differentiel")
    if D:
        out["differentiel"] = {}
        for de, a in D.get("fenetres", [[0, len(mix) / sr]]):
            r = A.differentiel([(k, refs[k]) for k in D["avec"]], (D["sans"], refs[D["sans"]]), ("mix", mix), de, a,
                               D.get("seuil", 10.0), mots=mots)
            for m in r:
                m["resolue"] = bool(abs(m["mix"]) <= abs(m[D["sans"]]) + 2.0)
            out["differentiel"][f"{de}-{a}"] = r
    C_ = Ms.get("contre")
    if C_:
        out["contre"] = {}
        for c in (C_ if isinstance(C_, list) else [C_]):
            refs_c = [(k, refs[k]) for k in c["sans"]]
            for de, a in c.get("fenetres", [[0, len(mix) / sr]]):
                r = A.contre(mix, refs_c, de, a, c.get("seuil", 10.0), c.get("ecart", 5.0), c.get("plancher", -70.0), mots)
                for m in r:
                    m["voulue"] = next((v[2] for v in c.get("voulus", []) if v[0] <= m["t"] <= v[1]), None)
                out["contre"][f"sans {' + '.join(c['sans'])} {de}-{a}"] = r
    if "reperes" in Ms and R.get("garde_reperes"):
        Gr = {**R["garde_reperes"], **(Ms["reperes"] or {})}
        cues = json.loads(chemin(R["_base"], Gr["cues"]).read_text())["cues"]
        cues_ref = (json.loads(chemin(R["_base"], Gr["cues_reference"]).read_text())["cues"]
                    if Gr.get("cues_reference") else None)
        ref_st = lire_stems(chemin(R["_base"], Gr["reference"])) if Gr.get("reference") else None
        exclus = {k for k, v in Gr.get("par_repere", {}).items() if v.get("exclu")}
        rr = A.reperes(stems, cues, ref_st, Gr.get("ignorer", []), f_max=Gr.get("f_max", 8000.0),
                       cible_db=Gr.get("cible_db", 6.0),
                       cibles_par_id={k: v["cible_db"] for k, v in Gr.get("par_repere", {}).items() if "cible_db" in v},
                       cues_ref=cues_ref, debuts=debuts_insertions(R, len(mix)))
        for q in rr:
            q["exclu"] = q["id"] in exclus
        out["reperes"] = rr
    if Ms.get("dialogue"):
        dia = json.loads(chemin(R["_base"], Ms["dialogue"]).read_text())
        out["jointures"] = {k: A.jointures(x, dia) for k, x in comp.items()}
        if mots:
            out["raccords_4_8k"] = {k: A.raccords(x, dia, mots) for k, x in comp.items()}
    rapport["mesures"] = out
    return comp, ts, S


def planches(R, comp, stems, ts, S, g_lim):
    dossier = R.get("_planches") or (chemin(R["_base"], R["sorties"].get("planches")) if R.get("sorties", {}).get("planches") else None)
    if not dossier:
        return []
    Ms = R.get("mesures", {})
    rep = []
    if Ms.get("evenements"):
        ev = json.loads(chemin(R["_base"], Ms["evenements"]).read_text())
        for k in ("decroche", "contact_neuf", "ecriture_debut", "raccroche", "bulle_et_vibreur", "signature_la", "signature_re_contact"):
            if k in ev:
                v = ev[k]["t"]; rep.append((v[0] if isinstance(v, list) else v, k[:12]))
    if Ms.get("dialogue"):
        for e in json.loads(chemin(R["_base"], Ms["dialogue"]).read_text())["extraits"]:
            rep += [(e["film_in"], e["id"]), (e["film_out"], "/")]
    faits = []
    fin = len(comp["mix"]) / L.SR
    faits.append(L.planche(list(comp.items()), 0, fin, dossier / "film.png", reperes=rep, px_par_s=36, haut_spectro=200,
                           haut_profil=80, haut_onde=50))
    for z in Ms.get("zooms", []):
        de, a, px = z
        faits.append(L.planche(list(comp.items()), de, a, dossier / f"zoom-{de:g}-{a:g}.png", reperes=rep, px_par_s=px,
                               haut_spectro=220, haut_profil=90, haut_onde=60))
    cols = [L.ENCRE, L.SOLAIRE, L.TERRA, L.VERT, L.GRIS]
    series = []
    for k, (nom, x) in enumerate(comp.items()):
        t, s = (ts, S) if nom == "mix" else L.sonie_courbe(x, 3.0)
        series.append((nom, t, s, cols[k % len(cols)]))
    faits.append(L.courbe_png(series, dossier / "arc-sonie.png", 0, fin, -40, -6, px_par_s=24, reperes=rep[:7],
                              titre="sonie court terme (3 s), LUFS"))
    red = -20 * np.log10(np.maximum(g_lim, 1e-9))
    tt = np.arange(0, len(red), 480) / L.SR
    faits.append(L.courbe_png([("réduction du limiteur (dB)", tt, -red[::480], L.TERRA)], dossier / "limiteur.png", 0, fin,
                              -4, 0.5, px_par_s=24, reperes=rep[:7], titre="limiteur : gain (dB)"))
    # stems : une planche par stem (spectre + profil), sur le film entier
    faits.append(L.planche([(k, v) for k, v in stems.items()], 0, fin, dossier / "stems.png", reperes=rep[:7], px_par_s=20,
                           haut_spectro=110, haut_profil=50))
    return [str(f) for f in faits]


# ── vidéo, Drive ───────────────────────────────────────────────────────────
def md5_video(mp4):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-map", "0:v", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip().split("=")[-1]


def muxer(video, wav, mp4):
    Path(mp4).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                    "-shortest", str(mp4)], check=True)
    info = {"mp4": str(mp4), "video_source": str(video), "md5_video_source": md5_video(video), "md5_video_mp4": md5_video(mp4)}
    info["video_identique"] = info["md5_video_source"] == info["md5_video_mp4"]
    info["aac"] = L.mesure(mp4)
    pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,sample_rate,duration,nb_frames",
                         "-of", "json", str(mp4)], capture_output=True, text=True, check=True)
    info["flux"] = json.loads(pr.stdout)["streams"]
    return info


def deposer(fichiers, dossier, simuler=False):
    faits = []
    for f in fichiers:
        cible = f"gdrive:{dossier}/{Path(f).name}"
        cmd = ["rclone", "copyto", str(f), cible]
        if simuler:
            print("   (simulation)", " ".join(f'"{c}"' if " " in c else c for c in cmd))
        else:
            subprocess.run(cmd, check=True)
            print(f"   déposé : {cible}")
        faits.append(cible)
    return {"cibles": faits, "simule": bool(simuler)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("recette", nargs="?")
    ap.add_argument("--modele", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--video")
    ap.add_argument("--mp4")
    ap.add_argument("--drive")
    ap.add_argument("--simuler", action="store_true", help="avec --drive : affiche les commandes rclone sans rien déposer")
    ap.add_argument("--planches", help="dossier des planches (remplace sorties.planches de la recette)")
    a = ap.parse_args()
    if a.modele:
        print(json.dumps(MODELE, ensure_ascii=False, indent=1)); return
    R = charger_recette(a.recette)
    if a.planches:
        R["_planches"] = Path(a.planches).resolve()
    So = R["sorties"]
    wav = chemin(R["_base"], So["wav"])
    mes_f = chemin(R["_base"], So["mesures"])
    emp = empreinte(R, a.recette)
    a_jour = (not a.force and wav.exists() and mes_f.exists() and json.loads(mes_f.read_text()).get("empreinte") == emp)
    if a_jour:
        print(f"à jour (empreinte {emp[:12]}) : {wav}")
        rapport = json.loads(mes_f.read_text())
    else:
        print(f"1. pistes ({R.get('nom')})")
        mix, stems, g_lim, rapport = mixer(R)
        print("2. sorties")
        L.ecrire24(wav, mix)
        if So.get("stems"):
            d = chemin(R["_base"], So["stems"]); d.mkdir(parents=True, exist_ok=True)
            for k, v in stems.items():
                L.ecrire24(d / f"{k}.wav", v)
        for c in So.get("copies", []):
            Path(c).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(wav, c)
        print("3. mesures")
        comp, ts, S = mesurer(R, mix, stems, g_lim, rapport)
        m = rapport["mesures"]
        print(f"   {m['mix']} ; S max {m['sonie_court_terme_max']} ; mono {m['mono_moins_stereo_lu']:+.2f} LU ; "
              f"corrélation min {m['correlation_min']} ; silences {[s['zeros_exacts'] for s in m['silences']]}")
        if m.get("arc"):
            print(f"   arc : {m['arc']}")
        for fen, r in m.get("differentiel", {}).items():
            hors_mots = [x for x in r if not x["mot"]]
            print(f"   différentiel {fen} s : {len(hors_mots)} marche(s) hors mots propres à {R['mesures']['differentiel']['avec']}, "
                  f"résolues {sum(x['resolue'] for x in hors_mots)} : "
                  + ", ".join(f"{x['t']:.2f} {x['bande']} {x['echelle']} mix {x['mix']:+.1f} ({R['mesures']['differentiel']['sans']} "
                              f"{x[R['mesures']['differentiel']['sans']]:+.1f})" for x in hors_mots))
        for fen, r in m.get("contre", {}).items():
            hors = [x for x in r if not x["mot"]]
            nv = [x for x in hors if not x["voulue"]]
            print(f"   contre, {fen} s : {len(hors)} marche(s) propres au mix hors mots, dont "
                  f"{len(nv)} non voulue(s) : " + ", ".join(f"{x['t']:.3f} {x['bande']} tenu {x['tenu']:+.1f}" for x in nv))
        if m.get("reperes"):
            ko = [q for q in m["reperes"] if not q["ok"] and not q["exclu"]]
            print(f"   repères : {len(m['reperes'])}, enterrés {len(ko)} : " + ", ".join(
                f"{q['id']} {q['meilleure_mix']['db']:+.1f} (cible {q['cible_db']:+.1f})" for q in ko)
                + "".join(f" ; {q['id']} exclu ({q['meilleure_mix']['db']:+.1f})" for q in m["reperes"] if q["exclu"]))
        print("4. planches")
        rapport["planches"] = planches(R, comp, stems, ts, S, g_lim)
        for p in rapport["planches"]:
            print(f"   {p}")
        rapport.update({"empreinte": emp, "recette": str(Path(a.recette).resolve()), "wav": str(wav)})
    if a.video:
        mp4 = Path(a.mp4) if a.mp4 else wav.with_suffix(".mp4")
        print("5. vidéo : flux copié, piste AAC 256k 48 kHz")
        rapport["mp4"] = muxer(a.video, wav, mp4)
        print(f"   {rapport['mp4']['mp4']} ; vidéo identique : {rapport['mp4']['video_identique']} ; AAC {rapport['mp4']['aac']}")
    if not a.drive:
        rapport.pop("drive", None)                  # pas de trace périmée d'un dépôt (ou d'une simulation) antérieur
    if a.drive:
        print("6. Drive")
        livre = Path(So["copies"][0]) if So.get("copies") else wav          # le nom livré, pas le fichier de travail
        fich = [livre] + ([Path(rapport["mp4"]["mp4"])] if rapport.get("mp4") else [])
        rapport["drive"] = deposer(fich, a.drive, a.simuler)
    mes_f.parent.mkdir(parents=True, exist_ok=True)
    mes_f.write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=float))
    print(f"→ {mes_f}")


if __name__ == "__main__":
    main()
