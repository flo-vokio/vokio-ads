#!/usr/bin/env python3
"""Bande son et minutage de la pub multi-métiers « Ils ont tous la même assistante » (04/10/2026).

  0 → 3 s  : cinq VRAIS décrochés de nos lignes de démo (le nom de l'établissement seul, coupé dans l'accueil de
             l'agente : relais/<métier>/alignement.json), enchaînés sur la musique ;
  ensuite  : la voix off (son/voix.py, ElevenLabs) ; chaque réplique part SUR UN TEMPS de la musique (120 BPM) ;
  fin      : la signature longue la · sol · ré (le point écrit Vokıo puis se pose sur le ı, comme le film long),
             la musique coupée net au la (calé sur un temps), puis la promesse et l'appel à l'action.

Voix (appels et voix off) : coupes + gain, aucun traitement. Écrit son/mix.wav et donnees/montage.json (+ donnees.js).
  python3 son/voix.py && python3 son/monter.py
"""
import json
import math
import os
import subprocess
import sys

import numpy as np

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELAIS = "/opt/vokio-ads/videos/relais"
APPELS = "/opt/vokio-site-repo/assets"
MUSIQUE = os.path.join(ICI, "son", "musique-elevenlabs.wav")
SIGNATURE = "/root/vokio-uploads/videos/showcase/point-solaire-signature-v2.wav"   # la à 0, sol 0,240, ré 0,600
SR = 48000
BEAT, KICK0 = 0.5, 0.08          # 120 BPM ; premier coup de grosse caisse du morceau (mesuré)

# accroche : (métier, étiquette, premier mot du nom, dernier mot du nom)
DECROCHES = [
    ("plombier", "Plombier", "Plomberie", "Azur !"),
    ("coiffure", "Coiffure", "Salon", "Marchand !"),
    ("garage", "Garage", "Garage", "Rond-Point !"),
    ("restaurant", "Restaurant", "La", "Halles."),
]
METIERS = ["Auto-école", "Barbier", "Boulangerie", "Chauffagiste", "Coiffure", "Dentiste", "Électricien", "Fleuriste",
           "Garage", "Institut de beauté", "Kiné", "Médecin", "Onglerie", "Opticien", "Ostéopathe", "Plombier",
           "Rénovation", "Restaurant", "Serrurier", "Toiletteur", "Traiteur", "Vétérinaire"]


def lire(chemin, canaux=2):
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", chemin, "-f", "f32le", "-ac", str(canaux), "-ar", str(SR), "-"],
                          capture_output=True, check=True).stdout
    return np.frombuffer(brut, dtype=np.float32).reshape(-1, canaux).copy()


def ecrire(chemin, x):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", str(x.shape[1]), "-ar", str(SR), "-i", "-",
                    "-c:a", "pcm_s24le", chemin], input=x.astype(np.float32).tobytes(), check=True)


def sonie(x):
    tmp = "/dev/shm/pub-metiers-mesure.wav"; ecrire(tmp, x if x.ndim == 2 else np.stack([x, x], 1))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", tmp, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    os.remove(tmp); b = r[r.rfind("Summary:"):]
    return float(b.split("I:")[1].split("LUFS")[0]), float(b.split("Peak:")[1].split("dBFS")[0])


def voix_off(rid, gain_db=0.0):
    """Voix off lue APRÈS une compression douce et un limiteur (voix de pub ; les VRAIS appels, eux, ne sont jamais traités)."""
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", f"{ICI}/son/voix/{rid}.wav", "-af",
                           "highpass=f=70,acompressor=threshold=-20dB:ratio=2:attack=10:release=150:makeup=1.5"
                           + f",volume={gain_db:.2f}dB,alimiter=limit=0.89:attack=5:release=80:level=disabled",
                           "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(brut, dtype=np.float32).copy()


def sur_temps(t):
    """Premier temps de la musique à partir de t (la grosse caisse tombe à 0 dans le film)."""
    return round(math.ceil(t / BEAT - 1e-6) * BEAT, 3)


def main():
    pistes = []          # (début film, signal mono, nature)
    mots, segs = [], []
    t = 0.0
    # ---- accroche (retour de Florian, 05/10) : plus de décrochés d'établissements (« ça parle à personne ») ;
    # la voix cite les métiers dès l'image 0, sur le mur des 22
    t = 0.0
    fin_accroche = 0.0

    # ---- voix off : v0 à v7 sont UNE prise continue (découpée au milieu des silences) : posées bout à bout, sans
    # attente ni recollage audible (retour de Florian 05/10 : « droit au but », mauvaise coupe entre deux répliques)
    vo = {}
    for rid in ["v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7"]:
        d = json.load(open(f"{ICI}/son/voix/{rid}.json"))
        t0 = 0.0 if rid == "v0" else round(t, 4)
        x = voix_off(rid)
        vo[rid] = {"debut": t0, "fin": round(t0 + d["duree"], 4)}
        segs.append({"nom": rid, "type": "voix", "film": [t0, round(t0 + d["duree"], 4)], "texte": d["texte"]})
        for w in d["mots"]:
            mots.append({"seg": rid, "texte": w["texte"], "t": round(t0 + w["t"], 3), "t1": round(t0 + w["t1"], 3)})
        pistes.append((t0, x, "voix:" + rid))
        t = t0 + d["duree"]

    # ---- signature : le la sur un temps, la plume 0,70 s avant + 0,10 de ı sans point
    la = sur_temps(t + 1.15)            # le point se pose sur « métier. », descend, écrit Vokıo (0,8 s), s'envole sur un temps
    T = {"plume": round(la - 0.80, 3), "plume_fin": round(la - 0.10, 3), "la": la, "sol": round(la + 0.24, 3), "re": round(la + 0.60, 3)}
    t = T["re"] + 0.3
    for rid in ["v8", "v9"]:          # v8 puis v9 bout à bout : « Créez votre espace gratuitement » d'une traite
        d = json.load(open(f"{ICI}/son/voix/{rid}.json"))
        t0 = round(t, 4)
        x = voix_off(rid)
        vo[rid] = {"debut": t0, "fin": round(t0 + d["duree"], 4)}
        segs.append({"nom": rid, "type": "voix", "film": [t0, round(t0 + d["duree"], 4)], "texte": d["texte"]})
        for w in d["mots"]:
            mots.append({"seg": rid, "texte": w["texte"], "t": round(t0 + w["t"], 3), "t1": round(t0 + w["t1"], 3)})
        pistes.append((t0, x, "voix:" + rid))
        t = t0 + d["duree"]
    duree = round(t + 2.2, 3)          # vokio.fr écrit (non dit) : le temps de le lire
    n = int(duree * SR)

    # ---- niveaux : voix off à -15 LUFS, appels à -16 (la voix de pub est devant)
    voix = np.zeros(n, dtype=np.float32)
    # une seule mesure pour toute la voix off (les répliques gardent leurs écarts naturels) ; les appels sur l'appel entier
    # gain de la voix off appliqué AVANT son dernier limiteur (crête bornée quelle que soit la voix choisie)
    i_vo, _ = sonie(np.concatenate([x for _, x, nat in pistes if nat.startswith("voix")]))
    pistes = [(t0, voix_off(nat.split(":")[1], -15.0 - i_vo) if nat.startswith("voix") else x, nat) for t0, x, nat in pistes]
    for t0, x, nat in pistes:
        if nat.startswith("voix"):
            g = 1.0
        else:
            i, _ = sonie(lire(f"{APPELS}/appel-{nat.split(':')[1]}.mp3", 1)[:, 0])
            g = 10 ** ((-15.5 - i) / 20)
        y = x.copy()
        o = int(round(t0 * SR)); voix[o:o + len(y)] += y[:max(0, min(len(y), n - o))] * g

    # ---- musique : grosse caisse sur 0, baissée sous les voix, coupée net au la, reprise douce après le ré
    mus = lire(MUSIQUE, 2)
    o = int((KICK0 - 0.005) * SR)
    musique = np.zeros((n, 2), dtype=np.float32)
    m = min(n, len(mus) - o); musique[:m] = mus[o:o + m]
    env = np.ones(n, dtype=np.float32)
    for t0, x, nat in pistes:
        a, b = int((t0 - 0.06) * SR), int((t0 + len(x) / SR + 0.12) * SR)
        env[max(0, a):b] = 10 ** (-7 / 20)
    k = int(0.06 * SR); env = np.convolve(env, np.ones(k, dtype=np.float32) / k, mode="same")
    c = int((T["la"] - 0.03) * SR); rp = int(0.03 * SR)
    env[c:c + rp] *= np.linspace(1, 0, rp); env[c + rp:] = 0
    rep = int((T["re"] + 0.35) * SR); fi = int(0.5 * SR)
    env[rep:rep + fi] = np.linspace(0, 1, fi) * 10 ** (-7 / 20) * 10 ** (-4 / 20)
    env[rep + fi:] = 10 ** (-7 / 20) * 10 ** (-4 / 20)
    ff = int(1.4 * SR); env[-ff:] *= np.linspace(1, 0, ff)
    musique *= env[:, None] * 10 ** (-9 / 20)

    sig = lire(SIGNATURE, 2)
    sp = np.zeros((n, 2), dtype=np.float32); o = int(T["la"] * SR); m = min(len(sig), n - o); sp[o:o + m] = sig[:m]
    mix = np.stack([voix, voix], 1) + musique + sp * 10 ** (-6 / 20)

    pc = lambda x: round(20 * np.log10(np.abs(x).max() + 1e-9), 1)
    print("crêtes : voix", pc(voix), "musique", pc(musique), "signature", pc(sp * 10 ** (-6 / 20)))
    i, pk = sonie(mix)
    # mastering : plus aucun VRAI appel dans ce film (voix off et musique seulement) ⇒ limiteur de bus léger pour
    # atteindre -14 LUFS sans écrêter (≈ 2 dB de réduction sur les seules crêtes)
    brut = "/dev/shm/pub-metiers-mix-brut.wav"; ecrire(brut, mix)
    g = -14.0 - i
    for _ in range(3):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brut, "-af", f"volume={g:.2f}dB,alimiter=limit=0.84:attack=5:release=80:level=disabled",
                        "-ar", str(SR), "-c:a", "pcm_s24le", f"{ICI}/son/mix.wav"], check=True)
        i2, pk2 = sonie(lire(f"{ICI}/son/mix.wav", 2))
        if abs(i2 + 14.0) < 0.15: break
        g += -14.0 - i2
    os.remove(brut)

    montage = {"duree": duree, "fps": 30, "segments": segs, "mots": mots, "temps": T, "voix": vo, "metiers": METIERS,
               "fin_accroche": round(fin_accroche, 3), "son": {"lufs": i2, "crete_dbfs": pk2}}
    json.dump(montage, open(f"{ICI}/donnees/montage.json", "w"), ensure_ascii=False, indent=1)
    open(f"{ICI}/donnees/donnees.js", "w").write("window.MONTAGE = " + json.dumps(montage, ensure_ascii=False) + ";\n")
    print(f"durée {duree:.2f} s · mix {i2:.1f} LUFS, crête {pk2:.1f} dBFS")
    for s in segs:
        print(f"  {s['nom']:11s} {s['film'][0]:6.2f}-{s['film'][1]:6.2f}  {s['texte']}")
    print("  signature", T)


if __name__ == "__main__":
    main()
