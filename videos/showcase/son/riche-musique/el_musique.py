#!/usr/bin/env python3
"""Prises ElevenLabs Music pour la variante « musique » (27/09) : un composition_plan dont les sections suivent le film.

    python3 son/riche-musique/el_musique.py [k …]     fabrique les prises k (0, 1, …) ; en cache : relancer ne recoûte rien

Chaque prise : son/riche-musique/el/prise<k>.wav (48 kHz stéréo) + prise<k>.json (le corps envoyé).
Les frontières de section sont des instants du film (donnees/evenements.json), en ms depuis 0 :
  4 200 décroché · 10 200 accord d'écoute (C1 − 0,30) · 18 367 l'agenda monte (temps fort de la grille) ·
  25 500 écriture · 32 933 « -tion » (temps de la grille) · 35 933 silence du raccroché · 42 900 contact du ré · 47 000 fin.
Tempo demandé : 78 BPM (la grille du film est 78,26 BPM : un temps = 23 images, les trois touchers d'heures, le ré).
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
import labo  # noqa: E402

EL = ICI / "el"
EL.mkdir(exist_ok=True)

GLOBAL_POS = ["intimate cinematic pop score", "D major", "78 BPM, steady tempo, no tempo changes",
              "felt piano, celesta, soft pizzicato strings, warm string pad, light modern percussion",
              "clean airy mix that leaves room for a spoken dialogue", "hopeful, human, precise", "instrumental"]
GLOBAL_NEG = ["vocals", "choir", "humming", "spoken word", "EDM drop", "heavy drums", "distorted guitar", "minor key",
              "trailer braams", "risers with white noise", "tempo change"]


def sections(variante=0):
    s = [
        ("Phone ringing, held breath", 4200,
         ["almost silent", "low sustained A note drone", "very soft heartbeat pulse", "restrained suspense"],
         ["melody", "piano chords", "drums"]),
        ("Call answered, delicate entry", 6000,
         ["delicate entry", "a few single felt piano notes", "soft warm string pad", "very quiet"],
         ["drums", "bass", "fast notes"]),
        ("Listening", 8167,
         ["gentle empathetic pad", "sparse felt piano", "soft pizzicato starting quietly at the very end"],
         ["drums", "loud dynamics"]),
        ("Checking the agenda, the pulse rises", 7133,
         ["steady eighth-note pulse enters", "pizzicato and celesta arpeggios", "light shaker and a soft kick",
          "rising energy"], ["heavy drums", "crash cymbal"]),
        ("Booking confirmed, building", 7433,
         ["confident pulse", "warm round bass line", "strings join", "building towards a resolution"],
         ["drop", "vocals"]),
        ("Thanks, soft landing", 3000,
         ["soft landing on a G major chord", "texture thins out"], ["new instruments"]),
        ("Text message arrives, the lift", 6967,
         ["starts quiet after a short pause", "rising build-up on an A pedal", "strings crescendo", "anticipation",
          "no resolution yet"], ["drop", "big drums"]),
        ("Logo, full resolution", 4100,
         ["full warm D major chord", "everything resolves", "the final chord rings then fades out", "clean ending"],
         ["abrupt cut", "new melody"]),
    ]
    if variante == 1:     # prise 1 : même forme, plus de corps (marimba + contrebasse pizz), un peu moins de piano
        s[3] = (s[3][0], s[3][1], ["steady eighth-note marimba pulse enters", "pizzicato arpeggios", "soft kick and shaker",
                                   "rising energy"], s[3][3])
        s[4] = (s[4][0], s[4][1], ["confident pulse", "warm double bass pizzicato", "legato strings join",
                                   "building towards a resolution"], s[4][3])
    if variante == 2:     # prise 2 : plus électronique et moderne (pulse de synthé feutré)
        s[3] = (s[3][0], s[3][1], ["soft plucked synth pulse in eighth notes", "celesta arpeggio", "gentle electronic kick",
                                   "rising energy"], s[3][3])
    assert sum(d for _, d, _, _ in s) == 47000
    return [{"section_name": n, "positive_local_styles": p, "negative_local_styles": ng, "duration_ms": d, "lines": []}
            for n, d, p, ng in s]


def sections_accords():
    """Prises 3 et 4 : le plan harmonique de la partition numpy, mesure par mesure (78 BPM, une mesure = 3 067 ms),
    pour voir si le modèle tient un accord et un tempo imposés, et culmine sur le logo."""
    s = [
        ("Ring", 4200, ["near silence", "low sustained A drone", "soft heartbeat at 78 BPM"], ["melody", "chords"]),
        ("Answer", 4967, ["G major chord", "delicate warm strings entering softly"], ["drums", "D major"]),
        ("Listening", 6133, ["B minor chord, then E minor chord", "soft strings and a round bass"], ["drums"]),
        ("Question", 3067, ["A major chord, suspended fourth resolving to the third"], ["drums"]),
        ("Agenda pulse", 6133, ["G major chord, then B minor chord", "marimba eighth-note pulse at 78 BPM", "soft kick on 1 and 3"],
         ["heavy drums"]),
        ("Booking", 8433, ["G major, E minor, A major, one chord per bar", "pulse builds", "shaker sixteenth notes"], ["drop"]),
        ("Thanks, soft landing then stop", 3834, ["G major chord", "texture thins out", "ends in silence"], ["new instruments"]),
        ("Text message, the lift", 6133, ["A major chord then G major chord", "big crescendo", "rising harp arpeggios"],
         ["D major", "drop"]),
        ("Logo", 4100, ["D major chord", "the loudest and fullest moment of the whole piece", "warm full resolution",
                        "rings out"], ["fade in", "quiet ending"]),
    ]
    assert sum(d for _, d, _, _ in s) == 47000
    return [{"section_name": n, "positive_local_styles": p, "negative_local_styles": ng, "duration_ms": d, "lines": []}
            for n, d, p, ng in s]


def corps(k):
    sec = sections_accords() if k >= 3 else sections(k % 3)
    return {"composition_plan": {"positive_global_styles": GLOBAL_POS, "negative_global_styles": GLOBAL_NEG,
                                 "sections": sec},
            "respect_sections_durations": True, "prise": k}


def prise(k):
    c = corps(k)
    envoi = {x: v for x, v in c.items() if x != "prise"}
    h = hashlib.sha256(json.dumps(["musique-riche", c], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:14]
    base = labo.CACHE / f"musique-riche{k}-{h}"
    wav = base.with_suffix(".wav")
    if not wav.exists():
        mp3 = base.with_suffix(".mp3")
        mp3.write_bytes(labo._post("/v1/music", envoi, timeout=900))
        labo._vers_wav(mp3, wav)
        base.with_suffix(".json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    shutil.copyfile(wav, EL / f"prise{k}.wav")
    (EL / f"prise{k}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    return EL / f"prise{k}.wav"


if __name__ == "__main__":
    for a in (sys.argv[1:] or ["0"]):
        w = prise(int(a))
        print(w, labo.mesurer(w))
