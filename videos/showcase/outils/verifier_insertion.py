#!/usr/bin/env python3
"""Prouver qu'une insertion de temps (son/dialogue.py, INSERTIONS) n'a rien déplacé d'autre que ce qu'elle décale.

    python3 outils/verifier_insertion.py --ref git:a6d3d8e
    python3 son/dialogue.py --avant /dev/shm/ref && \
    python3 outils/verifier_insertion.py --ref git:a6d3d8e --wav-ref /dev/shm/ref/dialogue.wav   (+ preuve à l'échantillon)
    python3 outils/verifier_insertion.py --ref git:a6d3d8e --mots-ref ancien-mots.json --json r.json

Lit son/dialogue.json (champ "insertions", extraits "insertion"/"insertions"/"decalage_echantillons") et
/opt/vokio-ads/videos/showcase-iphone/donnees/mots.json (ou --mots), et les compare à la révision de référence :
  - EXTRAITS : ceux qui existaient ont les mêmes bords source ; leur entrée film vaut l'ancienne + Σ des insertions
    qu'ils ont reçues (au µs près, et en échantillons entiers) ; les extraits nés d'une insertion sont listés.
  - MOTS : chaque mot d'un extrait ancien est identique (texte, début, fin, voyelle, image, source) s'il n'a pas glissé,
    ou décalé EXACTEMENT du glissement de son extrait (secondes ±1 µs, images entières) ; les syllabes aussi. Le champ
    « source » peut gagner la mention « (relevé translaté de … s avec l'extrait) ». Les mots nouveaux sont listés.
  - WAV (--wav-ref, le dialogue.wav de la référence, qui n'est pas dans git) : identique à l'échantillon avant le premier
    extrait nouveau, et égal à la référence décalée de Σ échantillons après le dernier extrait nouveau (une insertion à
    la fois : pour plusieurs, comparer étape par étape).
Code 1 si une différence non expliquée apparaît. Rien n'est écrit hors de --json. Aucune écoute : des mesures.
Mots de référence : ceux de la révision, sauf --mots-ref (utile quand le mots.json commité n'avait pas été relancé après
une retouche des bords : le 28/09, celui de a6d3d8e datait du 27/09 09:23, avant la retouche du soir, et différait déjà
sur « parfait. » fin 24,95 → 24,93 ; pour une référence propre : copier outils/mots.py et les caches son/transcription-*.json
dans /dev/shm/ref/{outils,son}, y mettre le dialogue --avant, lancer mots.py là, puis --mots-ref /dev/shm/ref/donnees/mots.json).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
RACINE = Path(__file__).resolve().parents[1]
DEPOT = Path("/opt/vokio-ads")
MOTS_IPHONE = Path("/opt/vokio-ads/videos/showcase-iphone/donnees/mots.json")
SR, FPS = 48000, 30


def lire_ref(spec, chemin_depot):
    if spec.startswith("git:"):
        txt = subprocess.run(["git", "-C", str(DEPOT), "show", f"{spec[4:]}:{chemin_depot}"], capture_output=True,
                             text=True, check=True).stdout
        return json.loads(txt)
    return json.loads(Path(spec).read_text())


def wav_i32(p):
    import numpy as np
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-f", "s32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(b, dtype="<i4").reshape(-1, 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", required=True, help="git:<révision> ou dossier contenant son/dialogue.json")
    ap.add_argument("--dialogue", default=str(RACINE / "son" / "dialogue.json"))
    ap.add_argument("--mots", default=str(MOTS_IPHONE))
    ap.add_argument("--mots-ref", help="mots.json de référence (défaut : celui de la révision --ref)")
    ap.add_argument("--wav-ref", help="dialogue.wav de la référence (preuve à l'échantillon)")
    ap.add_argument("--json")
    A = ap.parse_args()

    dia = json.loads(Path(A.dialogue).read_text())
    if A.ref.startswith("git:"):
        dref = lire_ref(A.ref, "videos/showcase/son/dialogue.json")
        mref = json.loads(Path(A.mots_ref).read_text()) if A.mots_ref else lire_ref(A.ref, "videos/showcase-iphone/donnees/mots.json")
    else:
        dref = json.loads((Path(A.ref) / "son" / "dialogue.json").read_text())
        mref = json.loads(Path(A.mots_ref or Path(A.ref) / "donnees" / "mots.json").read_text())
    mots = json.loads(Path(A.mots).read_text())
    ins = {i["id"]: i for i in dia.get("insertions", [])}
    erreurs, rapport = [], {"insertions": list(ins), "extraits": {}, "mots": {}, "syllabes": {}}

    # 1. extraits
    ancien = {e["id"]: e for e in dref["extraits"]}
    glisse = {}
    for e in dia["extraits"]:
        if e["id"] not in ancien:
            assert e.get("insertion") in ins, f"{e['id']} : nouvel extrait sans « insertion »"
            rapport["extraits"][e["id"]] = {"nouveau": e["insertion"], "film": [e["film_in"], e["film_out"]]}
            continue
        o = ancien[e["id"]]
        n = sum(ins[i]["echantillons"] for i in e.get("insertions", []))
        attendu = o["film_in"] + n / SR
        ok = (e["source_in"], e["source_out"]) == (o["source_in"], o["source_out"]) and abs(e["film_in"] - attendu) < 1e-6
        if "decalage_echantillons" in e:
            ok &= e["decalage_echantillons"] == int(round(o["decalage_film_moins_source"] * SR)) + n
        glisse[e["id"]] = n
        rapport["extraits"][e["id"]] = {"glisse_echantillons": n, "film_in": [o["film_in"], e["film_in"]], "ok": ok}
        if not ok:
            erreurs.append(f"extrait {e['id']} : bords ou décalage inattendus")

    # 2. mots et syllabes
    nm = {(w["extrait"], w["rang"]): w for w in mots["mots"]}
    nouveaux = [f"{k[0]}#{k[1]} {w['texte']}" for k, w in nm.items() if k[0] not in ancien]
    for w in mref["mots"]:
        k = (w["extrait"], w["rang"])
        x = nm.get(k)
        if x is None:
            erreurs.append(f"mot disparu {k}")
            continue
        n = glisse.get(k[0], 0)
        d, di = n / SR, n / (SR // FPS)
        pb = []
        for c in ("debut", "fin", "voyelle"):
            if (c in w) != (c in x) or (c in w and abs(x[c] - w[c] - d) > 1e-6):
                pb.append(f"{c} {w.get(c)} → {x.get(c)}")
        if abs(di - round(di)) < 1e-9 and x["image"] != w["image"] + round(di):
            pb.append(f"image {w['image']} → {x['image']}")
        if x["texte"] != w["texte"] or x["source"].split(" (relevé translaté")[0] != w["source"].split(" (relevé translaté")[0]:
            pb.append("texte ou source")
        cle = "identiques" if n == 0 else f"décalés de {n} éch. ({d:.6f} s, {di:g} images)"
        r = rapport["mots"].setdefault(k[0], {"attendu": cle, "mots": 0, "ecarts": []})
        r["mots"] += 1
        if pb:
            r["ecarts"].append(f"#{k[1]} {w['texte']} : " + " ; ".join(pb))
            erreurs.append(f"mot {k[0]}#{k[1]} {w['texte']} : " + " ; ".join(pb))
    for k, v in mref.get("syllabes", {}).items():
        x = mots["syllabes"].get(k)
        ex = next((e for e in dref["extraits"] if e["film_in"] - 1e-6 <= v["debut"] <= e["film_out"] + 1e-6), None)
        d = glisse.get(ex["id"], 0) / SR if ex else 0
        ok = x is not None and all(abs(x[c] - v[c] - d) < 1e-6 for c in ("debut", "voyelle") if c in v)
        rapport["syllabes"][k] = {"glisse_s": round(d, 6), "ok": ok}
        if not ok:
            erreurs.append(f"syllabe {k}")
    rapport["mots_nouveaux"] = nouveaux

    # 3. wav
    if A.wav_ref:
        import numpy as np
        old, new = wav_i32(A.wav_ref), wav_i32(dia["fichier"])
        nouv = [e for e in dia["extraits"] if e["id"] not in ancien]
        a = int(round(min(e["film_in"] for e in nouv) * SR))
        b = int(round(max(e["film_out"] for e in nouv) * SR))
        n = len(new) - len(old)
        avant = bool(np.array_equal(new[:a], old[:a]))
        apres = bool(np.array_equal(new[b:], old[b - n:]))
        rapport["wav"] = {"echantillons_ajoutes": int(n), "identique_avant_s": a / SR, "identique_avant": avant,
                          "decale_apres_s": b / SR, "decale_apres": apres}
        if not (avant and apres):
            erreurs.append("wav : différence hors des extraits nouveaux")

    for k, r in rapport["mots"].items():
        print(f"{k:5s} {r['mots']:3d} mots {r['attendu']:38s} {'ok' if not r['ecarts'] else 'ÉCARTS : ' + ' | '.join(r['ecarts'])}")
    print("mots nouveaux :", ", ".join(nouveaux) or "aucun")
    for k, r in rapport["syllabes"].items():
        print(f"syllabe {k} : glisse {r['glisse_s']:+.6f} s {'ok' if r['ok'] else 'ÉCART'}")
    if "wav" in rapport:
        w = rapport["wav"]
        print(f"wav : +{w['echantillons_ajoutes']} éch. ; identique avant {w['identique_avant_s']:.3f} s : {w['identique_avant']} ; "
              f"décalé après {w['decale_apres_s']:.3f} s : {w['decale_apres']}")
    print("\n".join("✗ " + e for e in erreurs) or "insertion propre : rien d'autre n'a bougé")
    if A.json:
        Path(A.json).write_text(json.dumps(rapport | {"erreurs": erreurs}, ensure_ascii=False, indent=1))
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
