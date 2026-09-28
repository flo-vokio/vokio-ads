#!/usr/bin/env python3
"""Insérer du temps dans le film (une mesure, un échange de dialogue…) : décaler les FICHIERS qui portent des instants,
et PROUVER qu'un son refait n'a changé que là où il devait. La règle est celle de son/dialogue.json « insertions »
(outils/chronologie.py) : un instant t du film d'avant ≥ pivot devient t + durée insérée ; en échantillons entiers.

    python3 outils/inserer_temps.py recette son/recettes/hybride.json [--sortie autre.json]
          décale toutes les fenêtres de temps d'une recette de outils/mixer.py (duree, muets, silences, mono, miroir,
          automation, sidechain, mesures : sautes, zooms, differentiel, contre, voulus, arc) et note les insertions
          appliquées dans "insertions_appliquees" : IDEMPOTENT (une insertion déjà appliquée n'est pas rejouée)
    python3 outils/inserer_temps.py wav ANCIEN.wav NOUVEAU.wav [--format f32]
          un son du film d'avant → film actuel, SILENCE dans chaque mesure insérée (références de mesure, anciens stems)
    python3 outils/inserer_temps.py json ENTREE.json SORTIE.json --cles t fin de a
          décale les nombres rangés sous ces clés (scalaires ou listes), à toute profondeur (cues, repères…)
    python3 outils/inserer_temps.py donnees DOSSIER_DONNEES SORTIE
          données PROVISOIRES du film actuel (evenements, scenes, secousses, point-resolu ; le reste copié) : pour faire
          avancer le son avant que l'image n'ait refait les siennes (construire.py fait foi et les remplacera). Pendant
          une mesure insérée, le point est tenu à sa place du pivot, vitesse nulle.
    python3 outils/inserer_temps.py verifier NOUVEAU.wav ANCIEN.wav [--json r.json] [--seuil -90]
          la preuve : NOUVEAU = ANCIEN avant le pivot, = ANCIEN décalé de n échantillons après la mesure insérée ; donne
          où la différence dépasse --seuil dBFS (premier et dernier instant, crête), et la continuité du NOUVEAU à chaque
          bord de mesure insérée (crête de la dérivée seconde contre le reste du fichier, marche de niveau RMS 20 ms,
          marche 4-16 kHz) : pas de clic, pas de trou, pas de marche
          --compenser [--par 1.0] [--hors A:B …] (28/09, pour un MIX remasterisé : le gain de master change avec la
          durée) : un gain unique ajusté (moindres carrés AVANT le premier pivot, hors des fenêtres --hors), puis, par
          fenêtre de --par s, le résidu nouveau − gain × ancien RELATIF au signal (dB sous le nouveau) : « identique au
          gain de master près » se lit fenêtre par fenêtre
Options communes : --insertions son/dialogue.json (défaut) ; --pivot S --duree S pour une règle donnée à la main.
Rien n'est écrit hors de la sortie demandée (la recette elle-même pour « recette » sans --sortie).
"""
import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chronologie as CH  # noqa: E402

SR = CH.SR


def chrono(a):
    if a.pivot is not None:
        return CH.Chronologie([{"id": "manuel", "pivot_s": a.pivot, "s": a.duree, "images": int(round(a.duree * 30)),
                                "pivot_image": int(round(a.pivot * 30))}])
    return CH.charger(a.insertions)


def r6(x):
    return None if x is None else round(float(x), 6)


def dec(C, v):
    """Instant décalé, arrondi au µs, et VÉRIFIÉ à l'échantillon : round(t'·48 000) = round(t·48 000) + n exactement."""
    if C.decaler(v) == v:
        return v                                  # avant tout pivot : la valeur telle quelle (0 reste 0, pas 0.0)
    w = r6(C.decaler(v))
    i = int(round(float(v) * SR))
    assert int(round(w * SR)) == C.decaler_echantillon(i), (v, w, int(round(w * SR)), C.decaler_echantillon(i))
    return w


# ── recettes de outils/mixer.py ─────────────────────────────────────────────
def _fen(C, w):
    """[a, b, …] → a, b décalés (le reste gardé : px d'un zoom, raison d'un « voulu »)."""
    return [dec(C, w[0]), dec(C, w[1])] + list(w[2:])


def _fens(C, ws):
    return [_fen(C, w) for w in ws] if isinstance(ws, list) else ws


def decaler_recette(R, C):
    R = copy.deepcopy(R)
    deja = set(R.get("insertions_appliquees", []))
    a_faire = [i for i in C.ins if i["id"] not in deja]
    if not a_faire:
        return R, []
    C = CH.Chronologie([dict(i) for i in a_faire])
    journal = []

    def note(cle, avant, apres):
        if avant != apres:
            journal.append((cle, avant, apres))

    if R.get("duree"):
        v = dec(C, R["duree"]); note("duree", R["duree"], v); R["duree"] = v
    for p in R.get("pistes", []):
        for cle in ("muets", "miroir"):
            if isinstance(p.get(cle), list):
                v = _fens(C, p[cle]); note(f"pistes.{p['nom']}.{cle}", p[cle], v); p[cle] = v
        if isinstance(p.get("mono"), list):
            v = _fens(C, p["mono"]); note(f"pistes.{p['nom']}.mono", p["mono"], v); p["mono"] = v
        if p.get("automation"):
            v = [[dec(C, t), g] for t, g in p["automation"]]; note(f"pistes.{p['nom']}.automation", p["automation"], v)
            p["automation"] = v
    if R.get("silences"):
        v = _fens(C, R["silences"]); note("silences", R["silences"], v); R["silences"] = v
    M = R.get("mesures") or {}
    for cle in ("sautes", "zooms"):
        if M.get(cle):
            v = _fens(C, M[cle]); note(f"mesures.{cle}", M[cle], v); M[cle] = v
    if M.get("differentiel", {}).get("fenetres"):
        D = M["differentiel"]; v = _fens(C, D["fenetres"]); note("mesures.differentiel.fenetres", D["fenetres"], v)
        D["fenetres"] = v
    contre = M.get("contre")
    for k, c in enumerate(contre if isinstance(contre, list) else ([contre] if contre else [])):
        for cle in ("fenetres", "voulus"):
            if c.get(cle):
                v = _fens(C, c[cle]); note(f"mesures.contre[{k}].{cle}", c[cle], v); c[cle] = v
    if M.get("arc", {}).get("apres") is not None:
        v = dec(C, M["arc"]["apres"]); note("mesures.arc.apres", M["arc"]["apres"], v); M["arc"]["apres"] = v
    R["insertions_appliquees"] = sorted(deja | {i["id"] for i in a_faire})
    R.setdefault("insertions_note", "fenêtres de temps décalées par outils/inserer_temps.py recette (règle de son/dialogue.json "
                                    "« insertions ») ; les notes (texte) gardent les instants du film d'avant")
    return R, journal


# ── JSON quelconque ─────────────────────────────────────────────────────────
def decaler_json(d, C, cles):
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            if k in cles and isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = r6(C.decaler(v))
            elif k in cles and isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
                out[k] = [r6(C.decaler(x)) for x in v]
            else:
                out[k] = decaler_json(v, C, cles)
        return out
    if isinstance(d, list):
        return [decaler_json(x, C, cles) for x in d]
    return d


# ── données provisoires de l'image ──────────────────────────────────────────
def _ev(v, C):
    v = dict(v)
    if "t" in v:
        v["t"] = [r6(C.decaler(x)) for x in v["t"]] if isinstance(v["t"], list) else r6(C.decaler(v["t"]))
    for k in ("image", "images"):
        if k in v:
            v[k] = C.decaler_image(v[k])
    return v


def donnees(src, dst, C):
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    faits = []
    for f in sorted(src.iterdir()):
        if f.is_file():
            shutil.copyfile(f, dst / f.name)
    ev = json.loads((src / "evenements.json").read_text())
    ev = {k: (_ev(v, C) if isinstance(v, dict) else v) for k, v in ev.items()}
    ev["_provisoire"] = f"décalé par outils/inserer_temps.py donnees ({C}) : l'image (construire.py) fait foi"
    (dst / "evenements.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1)); faits.append("evenements.json")
    sc = json.loads((src / "scenes.json").read_text())
    for s in sc.values():
        d, f = s["debut"], s["fin"]
        s["debut"], s["fin"] = r6(C.decaler(d)), r6(C.decaler(f - 1e-6) + 1e-6)
        s["duree"] = r6(s["fin"] - s["debut"])
        s["image_debut"], s["image_fin"] = C.decaler_image(s["image_debut"]), C.decaler_image(s["image_fin"] - 1) + 1
        s["hote_start"] = r6(C.decaler(s["hote_start"])); s["hote_duration"] = r6(s["hote_duration"] + (s["duree"] - (f - d)))
    (dst / "scenes.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1)); faits.append("scenes.json")
    se = json.loads((src / "secousses.json").read_text())
    for k, s in se.items():
        if isinstance(s, dict) and "image0" in s:
            i0 = s["image0"]
            if C.decaler_image(i0) != i0:
                s["image0"] = C.decaler_image(i0)
                s["segments_s"] = [[r6(C.decaler(a)), r6(C.decaler(b))] for a, b in s["segments_s"]]
            else:
                assert all(C.decaler_image(i0 + j) == i0 + j for j in range(len(s.get("enveloppe", [])))), \
                    f"secousse {k} enjambe une insertion : à refaire par l'image"
    (dst / "secousses.json").write_text(json.dumps(se, ensure_ascii=False, indent=1)); faits.append("secousses.json")
    pr = json.loads((src / "point-resolu.json").read_text())
    im = pr["images"]
    for ins in C.ins:
        p = ins["pivot_image"]
        tenu = dict(im[p - 1])
        neuf = [dict(tenu, image=p + j, t=r6((p + j) / C.fps), v=0) for j in range(ins["images"])]
        apres = [dict(x, image=x["image"] + ins["images"], t=r6(x["t"] + ins["s"])) for x in im[p:]]
        im = im[:p] + neuf + apres
    pr["images"] = im
    (dst / "point-resolu.json").write_text(json.dumps(pr, ensure_ascii=False)); faits.append("point-resolu.json")
    return faits


# ── preuve ──────────────────────────────────────────────────────────────────
def db(x):
    return float(20 * np.log10(max(float(x), 1e-30)))


def rms_db(x):
    return db(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)) if len(x) else 0.0)


def lire(p):
    import sonlib as L
    return np.atleast_2d(L.lire(p).T).T.astype(np.float64)


def ecarts(d, t0, seuil_db):
    """(crête dBFS, premier instant, dernier instant où |d| dépasse le seuil) ; t0 = instant du premier échantillon."""
    e = np.abs(d).max(axis=1) if d.ndim > 1 else np.abs(d)
    if not len(e):
        return {"crete_dbfs": None}
    au_dela = np.flatnonzero(e > 10 ** (seuil_db / 20))
    r = {"crete_dbfs": round(db(e.max()), 1), "t_crete": round(t0 + float(np.argmax(e)) / SR, 4)}
    if len(au_dela):
        r.update({"premier_au_dela_s": round(t0 + au_dela[0] / SR, 4), "dernier_au_dela_s": round(t0 + au_dela[-1] / SR, 4)})
    return r


def continuite(x, t, ref_d2):
    """Au bord t (s) du NOUVEAU : crête de la dérivée seconde sur ±2 ms contre le 99,9e centile du fichier, marches RMS
    20 ms (large bande et 4-16 kHz) entre [t − 20 ms ; t] et [t ; t + 20 ms]."""
    import sonlib as L
    i = int(round(t * SR)); w = int(0.020 * SR); k = int(0.002 * SR)
    m = x.mean(axis=1)
    d2 = np.abs(np.diff(m, 2))
    hf = L.passe_bande(m[max(0, i - 4 * w):i + 4 * w], 4000.0, 16000.0)
    j = min(i, 4 * w)
    return {"t": round(t, 6),
            "derivee2_bord_sur_p999_db": round(db(d2[max(0, i - k):i + k].max()) - db(ref_d2), 1),
            "marche_rms_20ms_db": round(rms_db(m[i:i + w]) - rms_db(m[i - w:i]), 2),
            "marche_4_16k_db": round(rms_db(hf[j:j + w]) - rms_db(hf[j - w:j]), 2),
            "niveau_rms_20ms_dbfs": round(rms_db(m[i - w:i + w]), 1)}


def verifier(nouveau, ancien, C, seuil_db=-90.0):
    x, y = lire(nouveau), lire(ancien)
    n = C.total_echantillons
    assert len(x) == len(y) + n, (len(x), len(y), n)
    ins = C.ins[0] if len(C.ins) == 1 else None
    assert ins, "verifier : une insertion à la fois (la règle se compose, la preuve se lit mieux ainsi)"
    p = ins["pivot_echantillon"]
    avant = x[:p] - y[:p]
    apres = x[p + n:] - y[p:]
    m = x.mean(axis=1)
    ref_d2 = np.percentile(np.abs(np.diff(m, 2)), 99.9)
    z0, z1 = C.zones()[0]
    r = {"nouveau": str(nouveau), "ancien": str(ancien), "insertion": {k: ins[k] for k in ("id", "pivot_s", "s", "echantillons")},
         "longueurs": [len(x), len(y)], "seuil_dbfs": seuil_db,
         "avant_pivot": {"de": 0.0, "a": round(p / SR, 6), **ecarts(avant, 0.0, seuil_db)},
         "apres_insertion": {"de": round((p + n) / SR, 6), "a": round(len(x) / SR, 6), **ecarts(apres, (p + n) / SR, seuil_db)},
         "niveaux": {"ancien_rms_dbfs": round(rms_db(y), 1), "nouveau_rms_dbfs": round(rms_db(x), 1)},
         "bords": [continuite(x, z0, ref_d2), continuite(x, z1, ref_d2)],
         "mesure_inseree": {"de": round(z0, 6), "a": round(z1, 6), "rms_dbfs": round(rms_db(m[p:p + n]), 1),
                            "ancien_mesure_avant_rms_dbfs": round(rms_db(y[max(0, p - n):p].mean(axis=1)), 1)}}
    return r


def compenser(x, y, C, hors=(), par=1.0):
    """NOUVEAU x contre ANCIEN y placé dans le film nouveau (silence dans chaque mesure insérée), à un gain unique près
    (celui du master : il change avec la durée du film) : gain ajusté par moindres carrés sur les échantillons hors des
    fenêtres `hors` [(a, b) s, film nouveau] et des mesures insérées ; puis, par fenêtre de `par` s, le résidu
    x − g·y relatif au signal x (dB). Rend {gain_db, fenetres [[a, b, rms_nouveau_dbfs, residu_rel_db, zone]], pires}."""
    y2 = C.inserer(y)
    assert len(y2) == len(x), (len(y2), len(x))
    exclu = np.zeros(len(x), bool)
    for a, b in list(C.zones()) + [tuple(h) for h in hors]:
        exclu[int(round(a * SR)):int(round(b * SR))] = True
    k = ~exclu
    xm, ym = x.mean(axis=1), y2.mean(axis=1)
    p0 = int(round(C.ins[0]["pivot_s"] * SR)) if C.ins else len(x)
    ka = k.copy(); ka[p0:] = False                   # le gain de master se lit AVANT le premier pivot (rien d'autre n'y
    kp = k.copy(); kp[:p0] = False                   # change) ; celui d'après est donné pour information
    gain = lambda m: float(xm[m] @ ym[m]) / max(float(ym[m] @ ym[m]), 1e-30)   # noqa: E731
    g = gain(ka) if ka.any() else gain(k)
    g_apres = gain(kp) if kp.any() else None
    r = x - g * y2
    fen = []
    for i0 in range(0, len(x), int(round(par * SR))):
        i1 = min(len(x), i0 + int(round(par * SR)))
        a, b = i0 / SR, i1 / SR
        zone = "exclue" if exclu[i0:i1].mean() > 0.5 else ("partielle" if exclu[i0:i1].any() else "comparee")
        sx = rms_db(x[i0:i1].mean(axis=1))
        fen.append([round(a, 3), round(b, 3), round(sx, 1), round(rms_db(r[i0:i1].mean(axis=1)) - sx, 1), zone])
    comp = [f for f in fen if f[4] == "comparee" and f[2] > -90]
    return {"gain_db": round(db(abs(g)), 4), "gain_ajuste_sur": "avant le premier pivot, hors fenêtres exclues",
            "gain_apres_db (information)": None if g_apres is None else round(db(abs(g_apres)), 4),
            "ajuste_hors": [list(z) for z in C.zones()] + [list(h) for h in hors],
            "par_s": par, "fenetres": fen,
            "pires": sorted(comp, key=lambda f: -f[3])[:5],
            "residu_rel_median_db": round(float(np.median([f[3] for f in comp])), 1) if comp else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["recette", "wav", "json", "donnees", "verifier"])
    ap.add_argument("entrees", nargs="+")
    ap.add_argument("--insertions", default=str(CH.DIALOGUE))
    ap.add_argument("--pivot", type=float)
    ap.add_argument("--duree", type=float)
    ap.add_argument("--sortie")
    ap.add_argument("--cles", nargs="*", default=["t", "fin"])
    ap.add_argument("--json")
    ap.add_argument("--seuil", type=float, default=-90.0)
    ap.add_argument("--format", choices=["s24", "f32"], default="s24", help="wav : PCM 24 bits (défaut) ou flottant 32 bits")
    ap.add_argument("--compenser", action="store_true", help="verifier : au gain de master près, résidu par fenêtre")
    ap.add_argument("--par", type=float, default=1.0, help="verifier --compenser : largeur des fenêtres (s)")
    ap.add_argument("--hors", nargs="*", default=[], help="verifier --compenser : fenêtres A:B (s, film nouveau) exclues du gain")
    a = ap.parse_args()
    C = chrono(a)
    print(f"règle : {C}")
    if a.mode == "recette":
        src = Path(a.entrees[0])
        R, j = decaler_recette(json.loads(src.read_text()), C)
        for cle, av, ap_ in j:
            print(f"   {cle} : {av} → {ap_}")
        if not j:
            print("   rien à faire (insertions déjà appliquées)")
        cible = Path(a.sortie) if a.sortie else src
        cible.write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n")
        print(f"→ {cible}")
    elif a.mode == "wav":
        import sonlib as L
        x = L.lire(a.entrees[0])
        y = C.inserer(x)
        if a.format == "f32":
            import subprocess
            st = np.ascontiguousarray(np.atleast_2d(y.T).T.astype("<f4"))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(st.shape[1]),
                            "-i", "-", "-c:a", "pcm_f32le", str(a.entrees[1])], input=st.tobytes(), check=True)
        else:
            L.ecrire24(a.entrees[1], y)
        print(f"→ {a.entrees[1]} ({len(x) / SR:.6f} → {len(y) / SR:.6f} s, {a.format})")
    elif a.mode == "json":
        d = json.loads(Path(a.entrees[0]).read_text())
        Path(a.entrees[1]).write_text(json.dumps(decaler_json(d, C, set(a.cles)), ensure_ascii=False, indent=1))
        print(f"→ {a.entrees[1]} (clés {a.cles})")
    elif a.mode == "donnees":
        print("→", a.entrees[1], donnees(a.entrees[0], a.entrees[1], C))
    elif a.mode == "verifier":
        r = verifier(a.entrees[0], a.entrees[1], C, a.seuil)
        if a.compenser:
            r["au_gain_pres"] = compenser(lire(a.entrees[0]), lire(a.entrees[1]), C,
                                          [tuple(map(float, h.split(":"))) for h in a.hors], a.par)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        if a.json:
            Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
