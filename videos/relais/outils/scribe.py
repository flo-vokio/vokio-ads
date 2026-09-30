#!/usr/bin/env python3
"""Mots horodatés d'un vrai appel (ElevenLabs Scribe v1, fr), en cache à côté de la recette : usage en une ligne :

    python3 outils/scribe.py <audio.mp3> <cache.json>

  Appelé par relais.py (étape « transcrire ») ; n'appelle l'API que si le cache manque. Clé PUB uniquement :
  /root/.secrets/vokio-ads-elevenlabs (jamais imprimée). Même appel que showcase-iphone/outils/mots.py (appeler_scribe).
"""
import json
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

CLE = Path("/root/.secrets/vokio-ads-elevenlabs")


def appeler(mono_wav: bytes) -> dict:
    b = uuid.uuid4().hex
    champ = lambda n, v: f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode()
    corps = (champ("model_id", "scribe_v1") + champ("language_code", "fra") + champ("timestamps_granularity", "word")
             + champ("tag_audio_events", "false") + champ("diarize", "true")
             + f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="appel.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
             + mono_wav + f"\r\n--{b}--\r\n".encode())
    r = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=corps,
                               headers={"xi-api-key": CLE.read_text().strip(),
                                        "Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(r, timeout=300) as x:
        return json.loads(x.read())


def transcrire(audio, cache):
    cache = Path(cache)
    if not cache.exists():
        mono = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-f", "wav", "-"],
                              capture_output=True, check=True).stdout
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(appeler(mono), ensure_ascii=False, indent=1))
    return [w for w in json.loads(cache.read_text())["words"] if w.get("type") == "word"]


if __name__ == "__main__":
    for w in transcrire(sys.argv[1], sys.argv[2]):
        print(f'{w["start"]:7.3f} {w["end"]:7.3f} {w.get("speaker_id", "?"):>10} {w["text"]}')
