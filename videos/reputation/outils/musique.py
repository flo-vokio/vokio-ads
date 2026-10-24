#!/usr/bin/env python3
"""Musique des pubs Vokio Réputation (version Instagram, 24/10/2026) : une prise ElevenLabs Music par film, dont les
sections suivent les plans du montage, puis mixage sur la vidéo muette.

    python3 /opt/vokio-ads/videos/reputation/outils/musique.py contents|planity [--prise k] [--mixer]

Sans --mixer : fabrique la prise (cache de labo.py : relancer ne recoûte rien), la copie dans ../son/<film>-k.wav et la mesure.
--mixer : pose la prise k sur le rendu muet → /root/vokio-uploads/videos/reputation/<nom>-musique.mp4
(normalisée à -14 LUFS intégrés, crête -1 dBTP, fondu final 1,2 s ; image copiée sans réencodage).
Même couleur pour les deux films : pop instrumentale chaleureuse, 100 BPM, pas de voix (demande de Florian : « juste de
musique et quelque chose de compréhensible sans besoin d'écouter une voix »).
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/opt/vokio-ads/videos/showcase/son")
import labo  # noqa: E402  (clé pub /root/.secrets/vokio-ads-elevenlabs, cache, mesures)

SON = ICI / "son"
SON.mkdir(exist_ok=True)
RENDUS = Path("/root/vokio-uploads/videos/reputation")
NOMS = {"contents": "reputation-clients-contents-9x16", "planity": "reputation-planity-google-9x16"}

GLOBAL_POS = ["warm modern instrumental pop", "100 BPM, steady tempo", "F major",
              "plucked guitar, felt piano, soft marimba, light claps and a gentle kick, warm bass",
              "bright, friendly, optimistic, confident", "clean social media background music", "instrumental"]
GLOBAL_NEG = ["vocals", "choir", "humming", "spoken word", "EDM drop", "heavy drums", "distorted guitar", "minor key",
              "trailer sounds", "tempo change", "sad"]

# (nom, durée ms, styles +, styles -) ; frontières = instants du montage (index.html de chaque film)
PLANS = {
    "contents": [
        ("Hook, a question hanging", 3000, ["sparse plucked guitar motif", "light and curious", "no drums yet"], ["drums"]),
        ("Typing at the counter", 5300, ["gentle groove starts", "soft kick and claps enter", "marimba pulse"], ["big drums"]),
        ("Request scheduled", 3450, ["groove settles", "warm bass joins"], ["crash cymbal"]),
        ("Two hours later, the text arrives", 6250, ["small lift", "piano chords join", "brighter, building softly"], ["drop"]),
        ("Five stars, the high point", 4000, ["fullest moment", "joyful", "all instruments together"], ["drop", "vocals"]),
        ("Nothing more to do, calm", 3300, ["relaxed", "drums thin out", "warm"], ["new instruments"]),
        ("Logo, resolution", 5700, ["resolves on the home chord", "final chord rings then fades out", "clean ending"],
         ["abrupt cut", "new melody"]),
    ],
    "planity": [
        ("Hook, a question hanging", 3100, ["sparse plucked guitar motif", "light and curious", "no drums yet"], ["drums"]),
        ("Comparing reviews", 5200, ["gentle groove starts", "soft kick and claps enter", "a little tension"], ["big drums"]),
        ("Typing after the appointment", 5100, ["groove settles", "marimba pulse", "warm bass joins"], ["crash cymbal"]),
        ("The text arrives", 4800, ["small lift", "piano chords join", "brighter"], ["drop"]),
        ("Five stars, the high point", 3500, ["fullest moment", "joyful", "all instruments together"], ["drop", "vocals"]),
        ("Reviews add up", 3500, ["confident, rising slightly", "energetic but soft"], ["new instruments"]),
        ("Logo, resolution", 5800, ["resolves on the home chord", "final chord rings then fades out", "clean ending"],
         ["abrupt cut", "new melody"]),
    ],
}


def corps(film, k):
    secs = list(PLANS[film])
    glob_pos, glob_neg = list(GLOBAL_POS), list(GLOBAL_NEG)
    if k >= 2:   # prise 2 (24/10) : la prise 1 s'effondrait presque au silence à 8,9 s puis repartait d'un coup à 9,6 s
        glob_pos.append("smooth continuous flow from start to end, gradual build, seamless transitions between sections")
        glob_neg += ["sudden breaks", "silent gaps", "stops", "breakdown", "drop out"]
        n, d, _, ng = secs[1]
        secs[1] = (n, d, ["groove enters gently and keeps flowing without interruption", "soft kick and claps", "marimba pulse"], ng)
    if k >= 1:   # prise 1 (24/10) : la prise 0 de « contents » s'éteignait à 26,5 s, 4 s de silence sur le logo
        n, d, _, _ = secs[-1]
        secs[-1] = (n, d, ["warm full band keeps playing", "lands on the home chord in the last two seconds",
                           "final chord held until the very end"], ["silence", "early fade out", "abrupt cut", "new melody"])
    assert sum(d for _, d, _, _ in secs) == 31000, film
    return {"composition_plan": {"positive_global_styles": glob_pos, "negative_global_styles": glob_neg,
                                 "sections": [{"section_name": n, "positive_local_styles": p, "negative_local_styles": ng,
                                               "duration_ms": d, "lines": []} for n, d, p, ng in secs]},
            "respect_sections_durations": True, "prise": k}


def prise(film, k):
    c = corps(film, k)
    envoi = {x: v for x, v in c.items() if x != "prise"}
    h = hashlib.sha256(json.dumps(["reputation", film, c], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:14]
    base = labo.CACHE / f"reputation-{film}{k}-{h}"
    wav = base.with_suffix(".wav")
    if not wav.exists():
        mp3 = base.with_suffix(".mp3")
        mp3.write_bytes(labo._post("/v1/music", envoi, timeout=900))
        labo._vers_wav(mp3, wav)
        base.with_suffix(".json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    dst = SON / f"{film}-{k}.wav"
    shutil.copyfile(wav, dst)
    (SON / f"{film}-{k}.json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    return dst


# Entrées trop brutales adoucies au mixage (retour Florian 24/10 « micro-coupure vers 9-10 s » sur la vidéo 1) :
# (film, prise) -> [(début, fin, gain de départ en dB)] : le gain remonte linéairement (en dB) jusqu'à 0 à la fin.
# Enveloppe de gain en dB, points (instant, dB) reliés linéairement, 0 dB hors enveloppe. Mesuré au centième le 24/10 sur
# contents-2 : la note s'éteint de 9,03 à 9,62 s (jusqu'à -36 dB), puis le rythme entre à -9 dB à 9,63 s. On remonte la
# queue de la note (+12 dB) et on fait entrer le rythme 8 dB plus bas, rendu à 0 dB à 10,15 s.
LISSAGES = {("contents", 2): [(9.35, 0.0), (9.62, 12.0), (9.63, -8.0), (10.15, 0.0)]}


def mixer(film, k):
    src = SON / f"{film}-{k}.wav"
    vol = "1"
    pts = LISSAGES.get((film, k), [])
    for (t0, g0), (t1, g1) in reversed(list(zip(pts, pts[1:]))):
        vol = f"if(between(t,{t0},{t1}),pow(10,({g0}+({g1 - g0})*(t-{t0})/{t1 - t0})/20),{vol})"
    muet = RENDUS / f"{NOMS[film]}.mp4"
    sortie = RENDUS / f"{NOMS[film]}-musique.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(muet), "-i", str(src), "-filter_complex",
                    f"[1:a]atrim=0:31,asetpts=PTS-STARTPTS,volume='{vol}':eval=frame,afade=t=out:st=29.8:d=1.2,"
                    "loudnorm=I=-14:TP=-1:LRA=11,aresample=48000[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                    "-movflags", "+faststart", str(sortie)], check=True)
    return sortie


def trous(wav, debut=1.0, fin=27.0):
    """Repère les « micro-coupures » : un creux d'au moins 0,25 s sous -28 dB suivi d'une remontée de plus de 18 dB
    (retour de Florian du 24/10, prise 1 de contents à 8,9-9,6 s). Renvoie [(début, fin, remontée en dB)]."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    w = 480
    db = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(w) / w, "valid")[::w]) + 1e-9)
    res, i = [], int(debut * 100)
    while i < int(fin * 100):
        if db[i] < -28:
            j = i
            while j < len(db) and db[j] < -28:
                j += 1
            if (j - i) >= 25 and j < len(db) and db[j:j + 10].max() - db[i:j].mean() > 18:
                res.append((i / 100, j / 100, round(float(db[j:j + 10].max() - db[i:j].mean()), 1)))
            i = j
        i += 1
    return res


if __name__ == "__main__":
    if "--controle" in sys.argv:
        for w in sys.argv[2:]:
            if not w.startswith("--"):
                print(w, "micro-coupures :", trous(w) or "aucune")
        sys.exit(0)
    film = sys.argv[1]
    k = int(sys.argv[sys.argv.index("--prise") + 1]) if "--prise" in sys.argv else 0
    if "--mixer" in sys.argv:
        print(mixer(film, k))
    else:
        w = prise(film, k)
        print(w, labo.mesurer(w))
