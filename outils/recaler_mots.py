#!/usr/bin/env python3
"""Recale les mots transcrits sur le texte réellement écrit.

Whisper donne des horodatages justes et des mots parfois faux : il entend
« Vocuez au » là où le script dit « Vokio », et il perd la ponctuation, qui
commande pourtant le découpage des sous-titres. On garde donc ses minutages et
on lui impose les mots de SCRIPT.md.

L'alignement est fait par `difflib` sur les mots normalisés. Quand n mots
entendus répondent à m mots écrits, on répartit leur durée cumulée au prorata
de la longueur de chaque mot écrit : un mot long dure plus longtemps qu'un mot
court, ce qui suffit pour un sous-titre.

    recaler_mots.py <projet>            montre ce qui changerait
    recaler_mots.py <projet> --ecrire   applique
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path


def normaliser(m):
    m = unicodedata.normalize("NFD", m.lower())
    m = "".join(c for c in m if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", m)


def lignes_du_script(texte):
    """Les lignes parlées sont les blocs indentés, une par « (Frame N) »."""
    lignes, frame = {}, None
    for l in texte.splitlines():
        t = re.match(r"^##\s+Ligne\s+\d+.*\(Frame\s+(\d+)\)", l.strip())
        if t:
            frame = int(t.group(1))
            continue
        if frame and l.startswith("    ") and l.strip():
            lignes.setdefault(frame, []).append(l.strip())
    return {f: " ".join(v) for f, v in lignes.items()}


def repartir(mots_ecrits, debut, fin):
    """Étale des mots écrits sur une fenêtre de temps, au prorata des lettres."""
    poids = [max(1, len(normaliser(m))) for m in mots_ecrits]
    total = sum(poids)
    sortie, t = [], debut
    for m, p in zip(mots_ecrits, poids):
        d = (fin - debut) * p / total
        sortie.append({"text": m, "start": round(t, 3), "end": round(t + d, 3)})
        t += d
    return sortie


def recaler(entendus, phrase):
    ecrits = phrase.split()
    a = [normaliser(w["text"]) for w in entendus]
    b = [normaliser(w) for w in ecrits]
    sortie = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                sortie.append({"text": ecrits[j1 + k],
                               "start": entendus[i1 + k]["start"],
                               "end": entendus[i1 + k]["end"]})
        elif op == "delete":
            continue  # mot entendu qui n'existe pas : son temps ira au voisin
        elif j2 > j1:
            if i2 > i1:                       # remplacement : on tient la fenêtre
                debut, fin = entendus[i1]["start"], entendus[i2 - 1]["end"]
            else:                             # insertion : on se glisse sans durée
                debut = sortie[-1]["end"] if sortie else entendus[0]["start"]
                fin = entendus[i1]["start"] if i1 < len(entendus) else debut
                if fin <= debut:
                    fin = debut + 0.12 * (j2 - j1)
            sortie.extend(repartir(ecrits[j1:j2], debut, fin))
    for k in range(1, len(sortie)):           # jamais de chevauchement
        if sortie[k]["start"] < sortie[k - 1]["end"]:
            sortie[k]["start"] = sortie[k - 1]["end"]
        if sortie[k]["end"] < sortie[k]["start"]:
            sortie[k]["end"] = sortie[k]["start"]
    for k, w in enumerate(sortie):
        w["id"] = f"w{k}"
    return sortie


a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
a.add_argument("projet")
a.add_argument("--ecrire", action="store_true")
a = a.parse_args()

projet = Path(a.projet)
meta_f = projet / "audio_meta.json"
meta = json.loads(meta_f.read_text())
phrases = lignes_du_script((projet / "SCRIPT.md").read_text())

change = 0
for v in meta["voices"]:
    phrase = phrases.get(v["frame"])
    if not phrase:
        print(f"frame {v['frame']} : aucune ligne dans SCRIPT.md, laissée telle quelle", file=sys.stderr)
        continue
    avant = " ".join(w["text"] for w in v.get("words", []))
    v["words"] = recaler(v.get("words", []), phrase)
    apres = " ".join(w["text"] for w in v["words"])
    if avant != apres:
        change += 1
        print(f"frame {v['frame']}\n  entendu : {avant}\n  écrit   : {apres}")

if a.ecrire:
    meta_f.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"\n{change} ligne(s) recalée(s) → {meta_f}")
else:
    print(f"\n{change} ligne(s) seraient recalées. Relancer avec --ecrire.")
