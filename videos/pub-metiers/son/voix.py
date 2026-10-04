#!/usr/bin/env python3
"""Voix off de la pub multi-métiers (04/10/2026, Florian : « tu peux utiliser des voix de narration ou de pub »).
ElevenLabs, clé pub dédiée (/root/.secrets/vokio-ads-elevenlabs, jamais affichée), une requête PAR RÉPLIQUE avec
horodatage des caractères (with-timestamps) : on en tire les mots horodatés pour les sous-titres. Cache par contenu :
relancer ne refacture rien si le texte, la voix et les réglages n'ont pas changé.

  python3 son/voix.py            écrit son/voix/<id>.wav + son/voix/<id>.json (mots : texte, t, t1)
"""
import base64
import hashlib
import json
import os
import subprocess
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
VOIX = os.environ.get("VOIX", "BUJMBsQ3Oq4cEeWSb48y")          # Sébastien, voix française homme 35 ans (pub)
MODELE = "eleven_multilingual_v2"
REGLAGES = {"stability": 0.42, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True, "speed": 1.06}

REPLIQUES = [
    ("v1", "Aucun d'eux n'a décroché. C'est Vokio qui a répondu."),
    ("v2", "Vokio prend le rendez-vous dans votre agenda Google."),
    ("v3", "Confirme par SMS, et rappelle la veille."),
    ("v4", "Prend les commandes."),
    ("v5", "Gère les urgences, même à vingt-trois heures."),
    ("v6", "Et chaque appel vous attend, résumé, dans votre espace."),
    ("v7", "Plombier, coiffeur, garagiste, dentiste, restaurant… Vokio parle votre métier."),
    ("v8", "Vokio. Votre ligne répond, même quand vous ne pouvez pas."),
    ("v9", "Créez votre espace gratuitement, sur vokio point F R."),
]


def cle():
    return open("/root/.secrets/vokio-ads-elevenlabs").read().strip()


def generer(rid, texte):
    corps = {"text": texte, "model_id": MODELE, "voice_settings": REGLAGES}
    h = hashlib.sha256(json.dumps([VOIX, corps], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    dossier = os.path.join(ICI, "voix"); os.makedirs(dossier, exist_ok=True)
    brut = os.path.join(dossier, f"{rid}-{h}.json")
    if not os.path.exists(brut):
        r = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOIX}/with-timestamps?output_format=mp3_44100_192",
                                   data=json.dumps(corps).encode(), headers={"xi-api-key": cle(), "Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=120) as x:
            open(brut, "wb").write(x.read())
    d = json.load(open(brut))
    mp3 = os.path.join(dossier, f"{rid}.mp3")
    open(mp3, "wb").write(base64.b64decode(d["audio_base64"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le",
                    os.path.join(dossier, f"{rid}.wav")], check=True)
    os.remove(mp3)
    al = d["alignment"]
    cs, t0s, t1s = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    mots, cur = [], None
    for c, a, b in zip(cs, t0s, t1s):
        if c.isspace():
            if cur: mots.append(cur); cur = None
            continue
        if cur is None: cur = {"texte": c, "t": a, "t1": b}
        else: cur["texte"] += c; cur["t1"] = b
    if cur: mots.append(cur)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                os.path.join(dossier, f"{rid}.wav")], capture_output=True, text=True).stdout)
    json.dump({"id": rid, "texte": texte, "duree": dur, "mots": [{"texte": m["texte"], "t": round(m["t"], 3), "t1": round(m["t1"], 3)} for m in mots]},
              open(os.path.join(dossier, f"{rid}.json"), "w"), ensure_ascii=False, indent=1)
    return dur, mots


if __name__ == "__main__":
    for rid, texte in REPLIQUES:
        dur, mots = generer(rid, texte)
        print(f"{rid} {dur:5.2f} s  {' '.join(m['texte'] + '@' + format(m['t'], '.2f') for m in mots)}")
