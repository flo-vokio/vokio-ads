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
    if k >= 1:   # prise 1 (24/10) : la prise 0 de « contents » s'éteignait à 26,5 s, 4 s de silence sur le logo
        n, d, _, _ = secs[-1]
        secs[-1] = (n, d, ["warm full band keeps playing", "lands on the home chord in the last two seconds",
                           "final chord held until the very end"], ["silence", "early fade out", "abrupt cut", "new melody"])
    assert sum(d for _, d, _, _ in secs) == 31000, film
    return {"composition_plan": {"positive_global_styles": GLOBAL_POS, "negative_global_styles": GLOBAL_NEG,
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


def mixer(film, k):
    src = SON / f"{film}-{k}.wav"
    muet = RENDUS / f"{NOMS[film]}.mp4"
    sortie = RENDUS / f"{NOMS[film]}-musique.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(muet), "-i", str(src), "-filter_complex",
                    "[1:a]atrim=0:31,asetpts=PTS-STARTPTS,afade=t=out:st=29.8:d=1.2,"
                    "loudnorm=I=-14:TP=-1:LRA=11,aresample=48000[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                    "-movflags", "+faststart", str(sortie)], check=True)
    return sortie


if __name__ == "__main__":
    film = sys.argv[1]
    k = int(sys.argv[sys.argv.index("--prise") + 1]) if "--prise" in sys.argv else 0
    if "--mixer" in sys.argv:
        print(mixer(film, k))
    else:
        w = prise(film, k)
        print(w, labo.mesurer(w))
