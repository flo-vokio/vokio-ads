#!/usr/bin/env python3
"""Mots horodatés du dialogue (temps FILM), recalés sur le texte exact de l'appel.

    python3 outils/mots.py            écrit donnees/mots.json et affiche le tableau de contrôle

Sources, par ordre d'autorité croissante :
  1. `hf transcribe` (whisper small, fr) sur son/dialogue.wav : son/transcription-hf.json.
     Ordre et présence des mots seulement : il dérive de −1,3 à +0,2 s sur ce fichier.
  2. ElevenLabs Scribe v1 (fr, mots horodatés, clé PUB /root/.secrets/vokio-ads-elevenlabs) sur le
     même fichier : son/transcription-scribe.json (en cache, rappelé seulement s'il manque).
     Estimation de départ de chaque mot, ±50 ms en général.
  3. L'énergie de son/dialogue.wav, AUTORITÉ sur les bords :
     - « attaque » : un mot qui suit un blanc (≥ 40 ms sous −40 dBFS) prend l'attaque exacte
       (première fenêtre de 10 ms au-dessus de −40 dBFS) si elle est à ±100 ms de l'estimation ;
     - « creux » : sinon, le creux de la bande 400-2500 Hz le plus proche (−80/+60 ms, profondeur
       ≥ 5 dB) marque la consonne d'entrée du mot ;
     - « scribe » : sinon (voyelle contre voyelle), l'estimation Scribe est gardée.
  4. Corrections relevées à la main sur le spectre par bandes (REVUES ci-dessous), avec leur raison.
Le TEXTE est toujours celui de la transcription d'origine (son/dialogue.json), jamais celui d'un ASR.
"""
import difflib
import json
import re
import subprocess
import sys
import unicodedata
import urllib.request
import uuid
from pathlib import Path

import numpy as np

PROJET = Path(__file__).resolve().parents[1]
DIALOGUE = PROJET / "son" / "dialogue.json"
WAV = PROJET / "son" / "dialogue.wav"
HF_JSON = PROJET / "son" / "transcription-hf.json"
SCRIBE_JSON = PROJET / "son" / "transcription-scribe.json"
SORTIE = PROJET / "donnees" / "mots.json"
HF = "/opt/vokio-ads/bin/hf"
SR = 16000
FPS = 30

# Corrections à la main (extrait, rang) → (debut film, raison). Relevées le 26/09 sur le spectre par bandes
# (outils/spectre.py : 0-400 / 400-2500 / 2500-4000 Hz + périodicité, fenêtres 25 ms au pas de 10 ms).
# Rappel : la ligne téléphonique coupe au-dessus de 4 kHz, les /s/ /ʃ/ y sont presque invisibles.
REVUES = {
    ("A1", 1): (5.680, "frication du /ʒ/ dès 5,675 (2,5-4 kHz), avant le seuil RMS"),
    ("A1", 2): (5.810, "début du /s/ sourd"),
    ("A1", 3): (6.055, "creux de transition /i/ → /e/ après « suis »"),
    ("A1", 7): (7.475, "/l/ : léger creux de la bande médiane"),
    ("A1", 8): (7.590, "relâchement /kl/ sourd 7,59-7,68 (le seuil RMS ne voit que la voyelle à 7,69)"),
    ("A1", 9): (8.040, "/v/ après la tenue du /k/ final de « Clinique » (8,00-8,04) ; le creux 7,89 est son /n/"),
    ("C1", 1): (10.660, "/ʃ/ hors bande téléphone ; montée de la bande médiane (/a/) ; lu dans le groupe « mon chat, »"),
    ("C1", 2): (10.915, "voix craquée d'hésitation (périodicité 0,2-0,3) de 10,915 à 11,39"),
    ("C1", 3): (11.395, "murmure nasal /m/ 11,395-11,56 (graves forts, médiums effondrés) ; /k/ tenu 11,705-11,745"),
    ("C1", 5): (12.730, "murmure nasal /m/ 12,73-12,81"),
    ("C1", 6): (13.055, "relâchement du /p/ après sa tenue silencieuse 13,00-13,05"),
    ("C1", 8): (13.720, "/j/ puis /ɛ/ fort 13,745-13,87 ; 13,445-13,54 est le /pɥ/ sourd de « puis »"),
    ("A2A3", 1): (18.005, "/v/ 18,005-18,065"),
    ("A2A3", 2): (19.800, "frication faible du /ʒ/ dès 19,80"),
    ("A2A3", 3): (19.830, "relâchement /p/, voyelle à 19,836"),
    ("A2A3", 4): (19.925, "/v/ : creux 19,925-19,945"),
    ("A2A3", 5): (20.020, "tenue du /p/ 20,02-20,04 puis souffle 20,05-20,11"),
    ("A2A3", 6): (20.555, "murmure nasal /n/ 20,555-20,668 (0-400 Hz fort, 1-2,5 kHz effondré)"),
    ("A2A3", 7): (20.785, "liaison /v/ 20,785-20,855"),
    ("A2A3", 9): (21.570, "liaison /z/ 21,57-21,62"),
    ("A2A3", 11): (22.200, "voyelle contre voyelle /u/ → /ɔ̃/ : montée de la bande 400-1000 Hz de 22,19 à 22,24"),
    ("A2A3", 12): (22.370, "liaison /z/ 22,37-22,42"),
    ("C3", 1): (23.490, "tenue voisée du /b/ 23,49-23,58"),
    ("C3", 2): (23.970, "« bah, à » ne font qu'une voyelle (23,60-24,07) : frontière invisible, placée 0,12 s avant le /n/ de « neuf » (Scribe 24,00)"),
    ("C3", 3): (24.085, "/n/ 24,085-24,17"),
    ("C3", 4): (24.260, "liaison /v/ 24,26-24,31"),
    ("C3", 5): (24.405, "/s/ sourd 24,405-24,445"),
    ("C3", 6): (24.565, "tenue du /p/ 24,565-24,62"),
    ("A4", 1): (26.590, "/ʒ/ 26,595"),
    ("A4", 2): (26.695, "/v/ 26,695-26,74"),
    ("A4", 3): (26.785, "/n/"),
    ("A4", 4): (26.955, "relâchement du /t/ de « note » puis /s/ 26,955-27,035"),
    ("A4", 5): (27.115, "tenue du /p/ 27,115-27,17"),
    ("A4", 6): (27.250, "/f/ sourd 27,255-27,335 (le /ʁ/ de « pour » s'y dévoise)"),
    ("A4", 10): (28.695, "/v/ 28,695-28,75 (28,61 est le /sj/ de « -tion »)"),
    ("A4", 11): (29.380, "attaque après la pause de la virgule (29,30-29,37)"),
    ("A4", 12): (29.450, "/s/ hors bande téléphone : placé après le /lə/ (29,38-29,44)"),
    ("A4", 16): (30.555, "/n/ 30,555-30,60"),
    ("A4", 17): (30.675, "liaison /v/ 30,675-30,735"),
    ("A4", 22): (32.315, "tenue voisée du /d/ 32,315-32,36"),
    ("A4", 23): (32.435, "tenue sourde du /k/ 32,435-32,50"),
    ("C4", 1): (34.795, "/m/ 34,795-34,84"),
    ("C4", 2): (35.070, "tenue voisée du /b/ 35,075-35,12"),
    ("C4", 4): (35.710, "/ʁ/ 35,715"),
}
# Attaque de la voyelle (centre perceptif : l'instant où l'on « entend » le mot) des mots qui portent
# une synchro forte. Les sauts du point se posent sur ces instants.
VOYELLES = {
    ("A1", 0): 5.020,
    ("A2A3", 6): 20.672,
    ("A2A3", 8): 21.430,
    ("A2A3", 11): 22.205,
    ("C3", 2): 23.970,
    ("C3", 3): 24.180,
    ("A4", 0): 26.255,
    ("A4", 6): 27.355,
    ("A4", 12): 29.470,
    ("A4", 18): 31.400,
    ("A4", 21): 32.115,
    ("C4", 0): 34.515,
}
# Repères hors mots (secondes film).
REPERES_SYLLABES = {
    "confirmation_derniere_syllabe": {"debut": 32.815, "voyelle": 32.955,
                                      "raison": "« -tion » : /s/ sourd 32,815-32,94, puis /jɔ̃/ 32,955-33,04 (dernière bouffée d'énergie)"},
}


def cle(m):
    m = m.replace("’", "'").lower()
    m = unicodedata.normalize("NFD", m)
    m = "".join(c for c in m if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9'\-]", "", m).strip("'-")


# Équivalences ASR → texte exact (nombres écrits en chiffres, variantes d'orthographe entendues)
EQUIV = {"19": "dix-neuf", "mocha": "moka", "moca": "moka", "ben": "bah", "alice": "elise"}


def mots_exacts(texte):
    """Découpe le texte dit ; « ! » et « ? » isolés se collent au mot précédent (espace fine U+202F)."""
    sortie = []
    for tok in texte.split():
        if re.fullmatch(r"[!?;:]", tok) and sortie:
            sortie[-1] += " " + tok
        else:
            sortie.append(tok)
    return sortie


def lire(chemin):
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(chemin), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, dtype="<f4").astype(np.float64)


def rms_db(sig, hop=0.010):
    w = int(hop * SR)
    n = len(sig) // w
    x = sig[:n * w].reshape(n, w)
    return 20 * np.log10(np.sqrt((x ** 2).mean(axis=1)) + 1e-12)   # fenêtre k = [k·hop, (k+1)·hop)


def bande_db(sig, lo=400, hi=2500, hop=0.005, n=400):
    """Énergie de bande sur fenêtres de 25 ms, pas de 5 ms ; valeur k centrée en k·hop + 12,5 ms."""
    h = int(hop * SR)
    k = (len(sig) - n) // h
    idx = np.arange(n)[None, :] + h * np.arange(k)[:, None]
    P = np.abs(np.fft.rfft(sig[idx] * np.hanning(n), axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1 / SR)
    return 10 * np.log10(P[:, (f >= lo) & (f < hi)].sum(axis=1) + 1e-12)


def transcrire_hf():
    if not HF_JSON.exists():
        d = PROJET / "son" / "_hf"
        d.mkdir(exist_ok=True)
        subprocess.run([HF, "transcribe", str(WAV), "-d", str(d), "-m", "small", "-l", "fr", "--json"], check=True)
        (d / "transcript.json").rename(HF_JSON)
    return json.loads(HF_JSON.read_text())


def transcrire_scribe():
    if not SCRIBE_JSON.exists():
        mono = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WAV), "-ac", "1", "-ar", "16000", "-f", "wav", "-"],
                              capture_output=True, check=True).stdout
        b = uuid.uuid4().hex
        champ = lambda n, v: f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode()
        corps = (champ("model_id", "scribe_v1") + champ("language_code", "fra") + champ("timestamps_granularity", "word")
                 + champ("tag_audio_events", "false") + champ("diarize", "true")
                 + f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="dialogue.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
                 + mono + f"\r\n--{b}--\r\n".encode())
        cle_api = Path("/root/.secrets/vokio-ads-elevenlabs").read_text().strip()
        r = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=corps,
                                   headers={"xi-api-key": cle_api, "Content-Type": f"multipart/form-data; boundary={b}"})
        with urllib.request.urlopen(r, timeout=300) as x:
            SCRIBE_JSON.write_text(json.dumps(json.loads(x.read()), ensure_ascii=False, indent=1))
    return [w for w in json.loads(SCRIBE_JSON.read_text())["words"] if w["type"] == "word" and cle(w["text"])]


def main():
    dia = json.loads(DIALOGUE.read_text())
    sig = lire(WAV)
    db10 = rms_db(sig)
    voix = db10 > -40
    bd = bande_db(sig)
    hf = [w for w in transcrire_hf() if cle(w["text"])]
    sc = transcrire_scribe()

    ecrits_tous = []
    for e in dia["extraits"]:
        for q, m in enumerate(mots_exacts(e["texte"])):
            ecrits_tous.append({"texte": m, "cle": cle(m), "extrait": e["id"], "rang": q, "locuteur": e["locuteur"]})

    # Scribe → texte exact
    a = [EQUIV.get(cle(w["text"]), cle(w["text"])) for w in sc]
    b = [w["cle"] for w in ecrits_tous]
    est = [None] * len(b)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for k in range(j2 - j1):
                est[j1 + k] = sc[i1 + k]["start"]
    # mots que Scribe n'a pas rendus : interpolés dans leur extrait
    for j, w in enumerate(ecrits_tous):
        if est[j] is None:
            ex = next(x for x in dia["extraits"] if x["id"] == w["extrait"])
            g = next((est[q] for q in range(j - 1, -1, -1) if est[q] is not None and ecrits_tous[q]["extrait"] == w["extrait"]), ex["film_in"])
            d = next((est[q] for q in range(j + 1, len(b)) if est[q] is not None and ecrits_tous[q]["extrait"] == w["extrait"]), ex["film_out"])
            est[j] = (g + d) / 2
            w["scribe_absent"] = True

    lignes = []
    for j, w in enumerate(ecrits_tous):
        ex = next(x for x in dia["extraits"] if x["id"] == w["extrait"])
        t = est[j]
        source = "scribe"
        # 1. attaque après un blanc
        k0 = int(round(t / 0.010))
        att = [k for k in range(max(k0 - 10, 4), k0 + 11)
               if voix[k] and not voix[k - 4:k].any() and ex["film_in"] <= k * 0.010 <= ex["film_out"]]
        if att:
            k = min(att, key=lambda z: abs(z - k0))
            t, source = round(k * 0.010, 3), "attaque"
        else:
            # 2. creux de la bande 400-2500 Hz
            c0 = int(round((t - 0.0125) / 0.005))
            fen = range(c0 - 16, c0 + 13)
            mn = min(fen, key=lambda z: bd[z])
            g = bd[max(0, mn - 16):mn].max(initial=-200)
            d = bd[mn + 1:mn + 17].max(initial=-200)
            if min(g, d) - bd[mn] >= 5.0 and mn not in (fen.start, fen.stop - 1):
                t, source = round(mn * 0.005 + 0.0125, 3), "creux"
        if (w["extrait"], w["rang"]) in REVUES:
            t, raison = REVUES[(w["extrait"], w["rang"])]
            source = "revue : " + raison
        w["debut"] = round(t, 3)
        w["source"] = source
        w["scribe"] = round(est[j], 3)
        if (w["extrait"], w["rang"]) in VOYELLES:
            w["voyelle"] = VOYELLES[(w["extrait"], w["rang"])]

    # ordre strict dans chaque extrait
    for x, y in zip(ecrits_tous, ecrits_tous[1:]):
        if y["extrait"] == x["extrait"] and y["debut"] <= x["debut"]:
            y["debut"] = round(x["debut"] + 0.02, 3)
            y["source"] += " (poussé pour l'ordre)"
    # fins : dernière fenêtre voisée avant le mot suivant de l'extrait (ou la sortie de l'extrait)
    for j, w in enumerate(ecrits_tous):
        ex = next(x for x in dia["extraits"] if x["id"] == w["extrait"])
        suiv = ecrits_tous[j + 1] if j + 1 < len(ecrits_tous) and ecrits_tous[j + 1]["extrait"] == w["extrait"] else None
        borne = suiv["debut"] if suiv else ex["film_out"]
        ka, kb = int(round(w["debut"] / 0.010)), int(round(borne / 0.010))
        v = [k for k in range(ka, kb) if voix[k]]
        w["fin"] = round((v[-1] + 1) * 0.010, 3) if v else round(min(borne, w["debut"] + 0.06), 3)
        if suiv and suiv["debut"] - w["fin"] < 0.035:   # parole liée : la fin est l'entrée du suivant
            w["fin"] = suiv["debut"]
        w["image"] = int(round(w["debut"] * FPS))

    # contrôles de cohérence
    erreurs = []
    for x, y in zip(ecrits_tous, ecrits_tous[1:]):
        if y["debut"] < x["fin"] - 1e-6:
            erreurs.append(f"chevauchement : {x['texte']} → {y['texte']}")
    for w in ecrits_tous:
        d = w["fin"] - w["debut"]
        if d < 0.025 or d > 1.2:   # « Je » élidé de « Je peux » ([ʃpø]) dure 30 ms
            erreurs.append(f"durée {d:.2f} s : {w['texte']} ({w['extrait']} #{w['rang']})")
        ex = next(x for x in dia["extraits"] if x["id"] == w["extrait"])
        if not (ex["film_in"] <= w["debut"] < w["fin"] <= ex["film_out"] + 1e-6):
            erreurs.append(f"hors extrait : {w['texte']}")
        if w["source"] == "scribe":
            erreurs.append(f"(info) sans repère d'énergie, Scribe gardé : {w['texte']} ({w['extrait']} #{w['rang']})")

    sm = difflib.SequenceMatcher(None, [EQUIV.get(cle(x["text"]), cle(x["text"])) for x in hf], b, autojunk=False)
    ecarts = [hf[i]["start"] - ecrits_tous[j]["debut"] for a_, b_, n in sm.get_matching_blocks()
              for i, j in zip(range(a_, a_ + n), range(b_, b_ + n))]

    for w in ecrits_tous:
        print(f"{w['extrait']:5s} {w['rang']:2d} {w['texte']:18s} {w['debut']:6.3f} → {w['fin']:6.3f}  img {w['image']:4d}  "
              f"scribe {w['scribe']:6.2f} ({w['debut'] - w['scribe']:+.2f})  {w['source']}")
    print(f"\nhf transcribe : {len(ecarts)}/{len(b)} mots appariés, écart médian {np.median(ecarts):+.2f} s, "
          f"max {np.max(np.abs(ecarts)):.2f} s (indice d'ordre seulement)")
    print("\n".join("⚠ " + x for x in erreurs) or "cohérence : ok")
    SORTIE.parent.mkdir(exist_ok=True)
    SORTIE.write_text(json.dumps({
        "unite": "secondes FILM (t = 0 à l'image 0) ; image = round(debut × 30)",
        "methode": __doc__.strip().splitlines()[0] + " Texte exact de la transcription d'origine ; estimation ElevenLabs Scribe ; "
                   "bords par l'énergie de son/dialogue.wav ; corrections à la main sur le spectre (champ source).",
        "mots": [{k: w[k] for k in ("texte", "cle", "debut", "fin", "image", "locuteur", "extrait", "rang", "source", "scribe")
                  if k in w} | ({"voyelle": w["voyelle"]} if "voyelle" in w else {}) for w in ecrits_tous],
        "syllabes": REPERES_SYLLABES,
    }, ensure_ascii=False, indent=1))
    print(f"→ {SORTIE} ({len(ecrits_tous)} mots)")
    return 1 if [x for x in erreurs if not x.startswith("(info)")] else 0


if __name__ == "__main__":
    sys.exit(main())
