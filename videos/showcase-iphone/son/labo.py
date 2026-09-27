#!/usr/bin/env python3
"""Labo son du showcase (26/09) : un seul endroit pour fabriquer le son, avec cache.

    from labo import *
    sfx("soft modern phone ring, close, dry", 1.5)        -> Path wav 48 kHz stéréo (ElevenLabs, en cache)
    musique(prompt=..., ms=40000) / musique(plan={...})   -> Path wav (ElevenLabs Music, en cache)
    ecrire("x.wav", signal)                               -> numpy (n,) ou (n,2), 48 kHz, float -1..1
    lire("x.wav") -> np.ndarray (n,2) float
    extrait(src, t0, t1) -> np.ndarray, un morceau d'un vrai appel (secondes)
    Synthèse : sinus, cloche(f, d), enveloppe(n, a, d, s, r), bruit_rose(n), reverbe(sig, secondes, mix)
    normaliser_lufs(src, dst, lufs=-14, tp=-1)            -> loudnorm deux passes

Clé : /root/.secrets/vokio-ads-elevenlabs (clé PUB, jamais la clé de prod).
Le cache (son/cache/) est indexé par le hash de la requête : relancer ne recoûte rien.
"""
import hashlib, json, subprocess, urllib.request, urllib.error, wave
from pathlib import Path
import numpy as np

SR = 48000
ICI = Path(__file__).parent
CACHE = ICI / "cache"; CACHE.mkdir(exist_ok=True)
CLE = Path("/root/.secrets/vokio-ads-elevenlabs")


def _cle():
    return CLE.read_text().strip()


def _post(chemin, corps, timeout=300):
    r = urllib.request.Request("https://api.elevenlabs.io" + chemin, data=json.dumps(corps).encode(),
                               headers={"xi-api-key": _cle(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as x:
            return x.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs {chemin} {e.code} : {e.read()[:400]!r}")


def _vers_wav(mp3, wav):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(SR), "-ac", "2",
                    "-c:a", "pcm_s16le", str(wav)], check=True)


def _cache(genre, corps):
    h = hashlib.sha256(json.dumps([genre, corps], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:14]
    return CACHE / f"{genre}-{h}"


def sfx(texte, duree=None, influence=0.5):
    """Bruitage ElevenLabs. duree 0,5 à 22 s (None = libre)."""
    corps = {"text": texte, "prompt_influence": influence}
    if duree:
        corps["duration_seconds"] = float(duree)
    base = _cache("sfx", corps)
    wav = base.with_suffix(".wav")
    if not wav.exists():
        mp3 = base.with_suffix(".mp3")
        mp3.write_bytes(_post("/v1/sound-generation", corps))
        _vers_wav(mp3, wav)
        base.with_suffix(".json").write_text(json.dumps(corps, ensure_ascii=False, indent=1))
    return wav


def plan_musique(prompt, ms):
    return json.loads(_post("/v1/music/plan", {"prompt": prompt, "music_length_ms": int(ms)}))


def musique(prompt=None, ms=None, plan=None):
    """Musique ElevenLabs : soit prompt + ms, soit un composition_plan complet."""
    corps = {"composition_plan": plan} if plan else {"prompt": prompt, "music_length_ms": int(ms)}
    base = _cache("musique", corps)
    wav = base.with_suffix(".wav")
    if not wav.exists():
        mp3 = base.with_suffix(".mp3")
        mp3.write_bytes(_post("/v1/music", corps, timeout=600))
        _vers_wav(mp3, wav)
        base.with_suffix(".json").write_text(json.dumps(corps, ensure_ascii=False, indent=1))
    return wav


def lire(chemin):
    """N'importe quel fichier son → (n, 2) float 48 kHz."""
    brut = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(chemin), "-f", "f32le", "-ac", "2",
                           "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(brut, dtype="<f4").reshape(-1, 2).astype(np.float64)


def ecrire(chemin, sig):
    sig = np.asarray(sig, dtype=np.float64)
    if sig.ndim == 1:
        sig = np.stack([sig, sig], axis=1)
    pic = np.max(np.abs(sig)) if sig.size else 0
    if pic > 1:
        print(f"  ⚠ {chemin} écrête ({pic:.2f}), ramené à 0,99")
        sig = sig / pic * 0.99
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((sig * 32767).astype("<i2").tobytes())
    return Path(chemin)


def extrait(src, t0, t1, fondu=0.02):
    s = lire(src)[int(t0 * SR):int(t1 * SR)].copy()
    n = int(fondu * SR)
    if n and len(s) > 2 * n:
        r = np.linspace(0, 1, n)[:, None]
        s[:n] *= r; s[-n:] *= r[::-1]
    return s


# ── synthèse ────────────────────────────────────────────────────────────────
def t_(duree):
    return np.arange(int(duree * SR)) / SR


def sinus(f, duree, phase=0.0):
    return np.sin(2 * np.pi * f * t_(duree) + phase)


def enveloppe(n, a=0.005, d=0.1, s=0.6, r=0.3):
    """ADSR en secondes (s = niveau de maintien), longueur totale n échantillons."""
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    S = max(0, n - A - D - R)
    e = np.concatenate([np.linspace(0, 1, A, endpoint=False), np.linspace(1, s, D, endpoint=False),
                        np.full(S, s), np.linspace(s, 0, R)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def cloche(f, duree=2.0, brillance=1.0, decroissance=3.0):
    """Cloche FM douce (rapport 1:1.4, indice qui décroît) : attaque nette, queue longue."""
    t = t_(duree)
    indice = brillance * 2.2 * np.exp(-t * decroissance * 1.6)
    mod = np.sin(2 * np.pi * f * 1.4 * t) * indice
    return np.sin(2 * np.pi * f * t + mod) * np.exp(-t * decroissance)


def bruit_rose(n, graine=0):
    g = np.random.default_rng(graine)
    b = g.standard_normal(n)
    f = np.fft.rfft(b); k = np.arange(len(f)); k[0] = 1
    return np.fft.irfft(f / np.sqrt(k), n) / 20


def reverbe(sig, secondes=1.8, mix=0.25, graine=1, predelai=0.012):
    """Réverbe par convolution sur une réponse impulsionnelle synthétique stéréo (bruit à décroissance exp.)."""
    sig = np.asarray(sig, dtype=np.float64)
    if sig.ndim == 1:
        sig = np.stack([sig, sig], axis=1)
    n = int(secondes * SR); t = np.arange(n) / SR
    g = np.random.default_rng(graine)
    ir = g.standard_normal((n, 2)) * np.exp(-6.9 * t / secondes)[:, None]
    ir = np.vstack([np.zeros((int(predelai * SR), 2)), ir]); ir /= np.sqrt((ir ** 2).sum(axis=0))
    L = len(sig) + len(ir) - 1; N = 1 << (L - 1).bit_length()
    humide = np.stack([np.fft.irfft(np.fft.rfft(sig[:, c], N) * np.fft.rfft(ir[:, c], N), N)[:L] for c in (0, 1)], axis=1)
    sec = np.vstack([sig, np.zeros((L - len(sig), 2))])
    return sec * (1 - mix) + humide * mix


def placer(piste, sig, debut, gain_db=0.0, pan=0.0):
    """Ajoute sig dans piste (n,2) à debut secondes, gain en dB, pan -1..1 (loi à puissance constante)."""
    sig = np.asarray(sig, dtype=np.float64)
    if sig.ndim == 1:
        sig = np.stack([sig, sig], axis=1)
    g = 10 ** (gain_db / 20)
    a = (pan + 1) * np.pi / 4
    sig = sig * g * np.array([np.cos(a), np.sin(a)]) * np.sqrt(2)
    i = int(debut * SR); j = min(len(piste), i + len(sig))
    if j > i:
        piste[i:j] += sig[:j - i]
    return piste


def normaliser_lufs(src, dst, lufs=-14, tp=-1.0, lra=11):
    f = f"loudnorm=I={lufs}:TP={tp}:LRA={lra}"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", f + ":print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    f2 = (f + f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", f2, "-ar", str(SR), str(dst)], check=True)
    return Path(dst)


def mesurer(chemin):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(chemin), "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    return {"lufs": float(m["input_i"]), "crete_dbtp": float(m["input_tp"]), "lra": float(m["input_lra"])}
