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
REGLAGES = {"stability": 0.55, "similarity_boost": 0.8, "style": 0.25, "use_speaker_boost": True, "speed": 1.05}   # plus stable : une intonation suivie

# Retour Florian 05/10 : intonation sans continuité (« Prend les commandes » sonnait surpris) ⇒ UNE seule génération
# pour tout le texte (une seule courbe d'intonation), découpée ensuite réplique par réplique sur les temps des caractères ;
# les répliques v2 à v6 forment une seule phrase qui s'enchaîne.
REPLIQUES = [
    ("v0", "Plombier, coiffeur, garagiste, dentiste, restaurant…"),
    ("v1", "Quand vous ne pouvez pas décrocher, c'est Vokio qui répond."),
    ("v2", "Il prend le rendez-vous dans votre agenda Google,"),
    ("v3", "le confirme par SMS, et rappelle votre client la veille."),
    ("v4", "Il prend aussi les commandes,"),
    ("v5", "gère les urgences, même à vingt-trois heures,"),
    ("v6", "et chaque appel vous attend, résumé, dans votre espace."),
    ("v7", "Vokio parle votre métier."),
    ("v8", "Vokio. Votre ligne répond, même quand vous ne pouvez pas."),
    ("v9", "Créez votre espace gratuitement, sur vokio point F R."),
]


def cle():
    return open("/root/.secrets/vokio-ads-elevenlabs").read().strip()


def generer_tout():
    texte = " ".join(t for _, t in REPLIQUES)
    corps = {"text": texte, "model_id": MODELE, "voice_settings": REGLAGES}
    h = hashlib.sha256(json.dumps([VOIX, corps], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    dossier = os.path.join(ICI, "voix"); os.makedirs(dossier, exist_ok=True)
    brut = os.path.join(dossier, f"tout-{h}.json")
    if not os.path.exists(brut):
        r = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOIX}/with-timestamps?output_format=mp3_44100_192",
                                   data=json.dumps(corps).encode(), headers={"xi-api-key": cle(), "Content-Type": "application/json"})
        with urllib.request.urlopen(r, timeout=300) as x:
            open(brut, "wb").write(x.read())
    d = json.load(open(brut))
    mp3 = os.path.join(dossier, "tout.mp3"); wav = os.path.join(dossier, "tout.wav")
    open(mp3, "wb").write(base64.b64decode(d["audio_base64"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s24le", wav], check=True)
    os.remove(mp3)
    al = d["alignment"]
    cs, t0s, t1s = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    # chaque caractère du texte joint appartient à une réplique : on la retrouve par la position
    bornes, pos = [], 0
    for rid, t in REPLIQUES:
        bornes.append((rid, pos, pos + len(t))); pos += len(t) + 1
    assert "".join(cs) == texte, "l'alignement ne rend pas le texte envoyé"
    mots = {rid: [] for rid, _ in REPLIQUES}
    cur = None
    for k, (c, a, b) in enumerate(zip(cs, t0s, t1s)):
        rid = next(r for r, p0, p1 in bornes if p0 <= k < p1 + 1)
        if c.isspace():
            if cur: mots[cur[0]].append(cur[1]); cur = None
            continue
        if cur is None: cur = (rid, {"texte": c, "t": a, "t1": b})
        else: cur[1]["texte"] += c; cur[1]["t1"] = b
    if cur: mots[cur[0]].append(cur[1])
    import numpy as np
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-f", "f32le", "-ac", "1", "-ar", "48000", "-"],
                                     capture_output=True, check=True).stdout, dtype=np.float32)
    ids = [r for r, _ in REPLIQUES]
    sortie = []
    for q, rid in enumerate(ids):
        ms = mots[rid]
        a = max(0.0, ms[0]["t"] - 0.06)
        b = ms[-1]["t1"] + 0.16
        if q + 1 < len(ids):
            b = min(b, mots[ids[q + 1]][0]["t"] - 0.04)
        y = x[int(a * 48000):int(b * 48000)].copy()
        f = int(0.012 * 48000); r = np.linspace(0, 1, f, dtype=np.float32); y[:f] *= r; y[-f:] *= r[::-1]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "1", "-ar", "48000", "-i", "-", "-c:a", "pcm_s24le",
                        os.path.join(dossier, f"{rid}.wav")], input=y.tobytes(), check=True)
        json.dump({"id": rid, "texte": dict(REPLIQUES)[rid], "duree": round(len(y) / 48000, 3),
                   "mots": [{"texte": m["texte"], "t": round(m["t"] - a, 3), "t1": round(m["t1"] - a, 3)} for m in ms]},
                  open(os.path.join(dossier, f"{rid}.json"), "w"), ensure_ascii=False, indent=1)
        sortie.append((rid, len(y) / 48000, ms, a))
    return sortie


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
    for rid, dur, ms, a in generer_tout():
        print(f"{rid} {dur:5.2f} s  {' '.join(m['texte'] + '@' + format(m['t'] - a, '.2f') for m in ms)}")
