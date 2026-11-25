#!/usr/bin/env python3
"""Lit musical de « Le ticket » (Réputation n° 3, 25/11/2026) : UNE prise ElevenLabs Music dont les sections suivent
les plans, à 96 BPM en fa majeur (même tonalité que la montée d'étoiles des films n° 1 et 2).

    python3 /opt/vokio-ads/videos/reputation/ticket/outils/musique.py [--prise k]     → son/lit-k.wav + mesures
    python3 .../musique.py --grille son/lit-k.wav                                     → tempo et phase mesurés

Les percussions (sons du salon) ne sont PAS dans cette prise : outils/salon.py les fabrique et les pose sur la grille
exacte de l'image. Ici, seulement le lit : Rhodes, contrebasse, balais. Cache de labo.py : relancer ne recoûte rien.
Grille : un temps = 0,625 s, une mesure = 2,5 s ; film de 31,25 s = 50 temps.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/opt/vokio-ads/videos/showcase/son")
import labo  # noqa: E402

SON = ICI / "son"
SON.mkdir(exist_ok=True)
TEMPS = 0.625
DUREE_MS = 31250

GLOBAL_POS = ["warm organic instrumental neo-soul groove", "96 BPM, steady tempo, 4/4", "F major",
              "Rhodes electric piano, upright double bass, soft brushed drums",
              "intimate, warm, human, analog, played by real musicians", "instrumental"]
GLOBAL_NEG = ["vocals", "choir", "humming", "spoken word", "synth lead", "EDM", "trap hi-hats", "tempo change",
              "minor key", "distorted guitar", "trailer sounds", "silent gaps"]

# (nom, durée ms, styles +, styles -) ; frontières = instants du montage (index.html)
PLANS = [
    ("Receipt prints, intimate opening", 6250,
     ["Rhodes chords alone, soft and warm", "upright bass enters gently on the second bar", "no drums yet", "playful"],
     ["drums", "big"]),
    ("At the till, the gesture", 8750,
     ["soft brushed drums groove enters", "walking upright bass", "Rhodes comping", "relaxed and confident"],
     ["crash cymbal", "drop"]),
    ("The week builds", 6250,
     ["building energy", "brushes get busier", "warm piano joins the Rhodes", "rising, crescendo"],
     ["drop", "breakdown"]),
    ("Tension before the total", 3750,
     ["drums stop", "sustained Rhodes chord keeps ringing", "bass climbs upward step by step", "suspense, building to a big hit"],
     ["silence", "full drums"]),
    ("The total, full band and resolution", 6250,
     ["big warm hit on the first beat", "full band groove, joyful", "resolves on the home chord F major",
      "final chord held and ringing until the very end"],
     ["silence", "early fade out", "abrupt cut", "new melody"]),
]


def corps(k):
    secs, glob_pos, glob_neg = list(PLANS), list(GLOBAL_POS), list(GLOBAL_NEG)
    total = DUREE_MS
    if k >= 1:
        # prise 1 (25/11) : la prise 0 posait un accord par mesure qui s'éteignait AVANT la mesure suivante (creux sous
        # -28 dB toutes les 2,5 s dans l'intro), faisait entrer les balais à 10 s au lieu de 6,25 s et se taisait à
        # 29,7 s. On demande un lit continu, et 2,5 s de plus à la fin (coupées au mixage) pour que l'accord tienne.
        glob_pos.append("smooth continuous flow, sustained notes, seamless transitions between sections")
        glob_neg += ["stops", "drop out", "breaks between chords"]
        n, d, p, ng = secs[0]
        secs[0] = (n, d, ["legato Rhodes chords that ring continuously without any gap", "soft upright bass from the start",
                          "no drums yet", "playful, warm"], ["drums", "staccato stabs", "gaps"])
        n, d, p, ng = secs[1]
        secs[1] = (n, d, ["soft brushed drums groove enters right at the start of this section", "walking upright bass",
                          "Rhodes comping", "relaxed and confident"], ng)
        n, d, p, ng = secs[-1]
        secs[-1] = (n, d + 2500, p + ["band keeps playing to the very end, then one long final F major chord ringing"], ng)
        total += 2500
    assert sum(d for _, d, _, _ in secs) == total
    return {"composition_plan": {"positive_global_styles": glob_pos, "negative_global_styles": glob_neg,
                                 "sections": [{"section_name": n, "positive_local_styles": p, "negative_local_styles": ng,
                                               "duration_ms": d, "lines": []} for n, d, p, ng in secs]},
            "respect_sections_durations": True, "prise": k}


def prise(k):
    c = corps(k)
    envoi = {x: v for x, v in c.items() if x != "prise"}
    h = hashlib.sha256(json.dumps(["reputation-ticket", c], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:14]
    base = labo.CACHE / f"reputation-ticket{k}-{h}"
    wav = base.with_suffix(".wav")
    if not wav.exists():
        mp3 = base.with_suffix(".mp3")
        mp3.write_bytes(labo._post("/v1/music", envoi, timeout=900))
        labo._vers_wav(mp3, wav)
        base.with_suffix(".json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    dst = SON / f"lit-{k}.wav"
    shutil.copyfile(wav, dst)
    (SON / f"lit-{k}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    return dst


def enveloppe_attaques(wav, pas=0.005):
    """Flux spectral (attaques) à pas de 5 ms, en numpy seul."""
    x = labo.lire(wav).mean(axis=1)
    n, h = 2048, int(pas * labo.SR)
    fen = np.hanning(n)
    trames = np.lib.stride_tricks.sliding_window_view(x, n)[::h] * fen
    S = np.log1p(np.abs(np.fft.rfft(trames, axis=1)))
    flux = np.maximum(np.diff(S, axis=0), 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    return flux - np.convolve(flux, np.ones(40) / 40, "same"), pas, n / 2 / labo.SR


def grille(wav, t0=0.0, t1=31.0):
    """Tempo (autocorrélation) et phase des temps (repli de l'enveloppe d'attaques sur la période)."""
    f, pas, lat = enveloppe_attaques(wav)
    f = np.maximum(f, 0)
    a, b = int(t0 / pas), int(t1 / pas)
    z = f[a:b] - f[a:b].mean()
    ac = np.correlate(z, z, "full")[len(z) - 1:]
    lo, hi = int(0.5 / pas), int(0.75 / pas)
    per = (lo + np.argmax(ac[lo:hi])) * pas
    phases = np.arange(0, TEMPS, pas)
    score = [f[a:b][((np.arange(b - a) * pas + t0 - ph) % TEMPS) < pas * 2].mean() for ph in phases]
    ph = phases[int(np.argmax(score))] + lat
    return {"periode_s": round(per, 4), "bpm": round(60 / per, 2), "phase_s": round(ph % TEMPS, 3)}


if __name__ == "__main__":
    if "--grille" in sys.argv:
        w = sys.argv[sys.argv.index("--grille") + 1]
        for t0, t1 in ((0, 31), (0, 6.25), (6.25, 15), (15, 21.25), (25, 31)):
            print(f"{t0:>5}-{t1:<5}", grille(w, t0, t1))
        sys.exit(0)
    k = int(sys.argv[sys.argv.index("--prise") + 1]) if "--prise" in sys.argv else 0
    w = prise(k)
    print(w, labo.mesurer(w))
