#!/usr/bin/env python3
"""Bande son de la pub « Cette secrétaire n'existe pas » (04/10/2026), montée dans le VRAI appel plombier de la démo
(Camille, Plomberie Azur, fuite sous l'évier : /opt/vokio-site-repo/assets/appel-plombier.mp3, mots horodatés par Scribe
dans relais/plombier/alignement.json).

Le vrai appel reçoit des COUPES et un gain, rien d'autre (aucun filtre, compresseur ni limiteur sur la voix). Dessous :
une musique rythmée (ElevenLabs, 118 BPM, la majeur, son/musique-elevenlabs.wav, retour Florian du 04/10 « une musique
plus dynamique »), calée pour qu'un temps tombe sur le la de la signature, baissée sous la voix, coupée net au la ;
un toc discret à chaque ligne cochée ; la signature LONGUE la · sol · ré (comme le film long) : la quand le point
s'envole du bout du mot, sol au sommet au-dessus du ı, ré au contact.

Écrit : son/dialogue.wav, son/mix.wav (-14 LUFS, crête -1 dBTP, 48 kHz stéréo), donnees/montage.json (segments,
mots en temps film, instants des objets) que lit index.html via donnees/donnees.js.

  python3 son/monter.py
"""
import json
import os
import subprocess
import sys

import numpy as np

ICI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPEL = "/opt/vokio-site-repo/assets/appel-plombier.mp3"
ALIGN = "/opt/vokio-ads/videos/relais/plombier/alignement.json"
MUSIQUE = os.path.join(ICI, "son", "musique-elevenlabs.wav")
SIGNATURE = "/root/vokio-uploads/videos/showcase/point-solaire-signature-v2.wav"   # la à 0, sol à 0,240, ré à 0,600
SR = 48000

# (énoncé, premier mot, dernier mot, marge avant, marge après, silence avant) : le texte montré sera exactement ces mots
SEGMENTS = [
    ("A", 0, "Bonjour,", "Camille,", 0.10, 0.08, 0.00),
    ("B", 1, "j’ai", "là.", 0.07, 0.10, 0.30),
    ("C", 4, "D’accord,", "garde.", 0.07, 0.12, 0.34),
    ("D", 8, "Très", "Toulon.", 0.07, 0.12, 0.34),
    ("E", 10, "je", "l’évier", 0.05, 0.12, 0.30),
    ("F", 10, "C’est", "minutes.", 0.07, 0.14, 0.30),
    ("G", 11, "OK,", "beaucoup.", 0.07, 0.14, 0.36),
]


def lire(chemin, canaux=2):
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", chemin, "-f", "f32le", "-ac", str(canaux), "-ar", str(SR), "-"],
                          capture_output=True, check=True).stdout
    return np.frombuffer(brut, dtype=np.float32).reshape(-1, canaux).copy()


def ecrire(chemin, x):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", str(x.shape[1]), "-ar", str(SR), "-i", "-",
                    "-c:a", "pcm_s24le", chemin], input=x.astype(np.float32).tobytes(), check=True)


def mesure(chemin):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", chemin, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    bloc = r[r.rfind("Summary:"):]
    i = float(bloc.split("I:")[1].split("LUFS")[0])
    pk = float(bloc.split("Peak:")[1].split("dBFS")[0])
    return i, pk


def main():
    al = json.load(open(ALIGN))["enonces"]
    voix = lire(APPEL, 1)[:, 0]
    segs, mots, t = [], [], 0.0
    for nom, ie, w0, w1, av, ap, sil in SEGMENTS:
        ms = al[ie]["mots"]
        i0 = next(k for k, w in enumerate(ms) if w["texte"] == w0 and (nom != "F" or w["t"] > 55))
        i1 = next(k for k in range(i0, len(ms)) if ms[k]["texte"] == w1)
        s0, s1 = ms[i0]["t"] - av, ms[i1]["t1"] + ap
        t += sil
        segs.append({"nom": nom, "qui": al[ie]["qui"], "src": [round(s0, 3), round(s1, 3)], "film": [round(t, 3), round(t + s1 - s0, 3)]})
        for w in ms[i0:i1 + 1]:
            mots.append({"seg": nom, "qui": al[ie]["qui"], "texte": w["texte"], "t": round(t + w["t"] - s0, 3), "t1": round(t + w["t1"] - s0, 3)})
        t += s1 - s0
    fin_dialogue = t

    # ---- le reste du film, en temps film (les titres et la fin n'ont pas de voix)
    G = segs[-1]["film"][1]
    temps = {
        "titre_ia": round(G + 0.40, 3),          # « Camille est une IA. »
        "titre_ia_2": round(G + 1.15, 3),        # « Elle décroche quand vous ne pouvez pas. »
        "plume": round(G + 3.05, 3),             # le point écrit « Vokıo » sous la ligne de base (0,70 s, film long)
        "plume_fin": round(G + 3.75, 3),
        "la": round(G + 3.85, 3),                # le point s'envole du bout du mot
        "sol": round(G + 4.09, 3),               # sommet au-dessus du ı
        "re": round(G + 4.45, 3),                # contact : le point est le point du ı
        "cta": round(G + 5.05, 3),               # « Essayez-la… »
        "cta_2": round(G + 5.65, 3),             # vokio.fr · 59 €/mois
    }
    temps["point_i"] = temps["re"]
    duree = round(G + 8.6, 3)

    n = int(round(duree * SR))
    dia = np.zeros(n, dtype=np.float32)
    f = int(0.012 * SR)
    for s in segs:
        a, b = int(round(s["src"][0] * 16000 / 16000 * SR)), int(round(s["src"][1] * SR))
        # voix lue à 48 kHz : indices en temps source
        x = voix[a:b].copy()
        rampe = np.linspace(0, 1, f, dtype=np.float32)
        x[:f] *= rampe; x[-f:] *= rampe[::-1]
        o = int(round(s["film"][0] * SR))
        dia[o:o + len(x)] += x
    gain_voix = 10 ** (0.5 / 20)
    dia *= gain_voix

    # ---- musique : un temps sur le la (période mesurée 0,51 s), départ sur une attaque, coupée net au la
    mus = lire(MUSIQUE, 2)
    mono_m = mus.mean(axis=1)
    h = 480
    e = np.sqrt(np.convolve(mono_m ** 2, np.ones(h) / h, mode="same")[::h])
    attaques = np.maximum(0, np.diff(np.log(e + 1e-6)))
    t_b0 = float(np.argmax(attaques[:200] > 0.5 * attaques[:200].max())) * h / SR    # première attaque forte
    P = 60 / 117.6
    s0 = t_b0 + ((-temps["la"]) % P)
    o = int(s0 * SR)
    musique = np.zeros((n, 2), dtype=np.float32)
    m = min(n, len(mus) - o); musique[:m] = mus[o:o + m]
    coupe = int((temps["la"] - 0.03) * SR)
    rampe = int(0.03 * SR)
    musique[coupe:coupe + rampe] *= np.linspace(1, 0, rampe)[:, None]
    musique[coupe + rampe:] = 0
    env = np.full(n, 1.0, dtype=np.float32)
    for sg in segs:
        a, b = int((sg["film"][0] - 0.10) * SR), int((sg["film"][1] + 0.15) * SR)
        env[max(0, a):b] = 10 ** (-6 / 20)           # sous la voix : 6 dB plus bas que dans les respirations
    # sans voix (révélation, écriture du mot) : la musique passe devant, +5 dB
    env[int((segs[-1]["film"][1] + 0.2) * SR):int(temps["la"] * SR)] *= 10 ** (5 / 20)
    k = int(0.08 * SR); env = np.convolve(env, np.ones(k, dtype=np.float32) / k, mode="same")
    musique *= env[:, None] * 10 ** (-8.5 / 20)

    # ---- tocs des lignes cochées
    coches = coches_film(segs, mots)
    toc = np.zeros(n, dtype=np.float32)
    tt = np.arange(int(0.09 * SR)) / SR
    son_toc = (np.sin(2 * np.pi * 1320 * tt) * np.exp(-tt * 60) * 0.5 + np.sin(2 * np.pi * 660 * tt) * np.exp(-tt * 45) * 0.5).astype(np.float32)
    for c in coches:
        o = int(c["t"] * SR); m = min(len(son_toc), n - o); toc[o:o + m] += son_toc[:m]

    # ---- signature longue : le la à l'envol
    sig = lire(SIGNATURE, 2)
    sigpiste = np.zeros((n, 2), dtype=np.float32)
    o = int(temps["la"] * SR); m = min(len(sig), n - o)
    sigpiste[o:o + m] = sig[:m]

    mono = lambda x: np.stack([x, x], axis=1)
    mix = mono(dia) + musique + mono(toc) * 10 ** (-20 / 20) + sigpiste * 10 ** (-7 / 20)

    os.makedirs(f"{ICI}/donnees", exist_ok=True)
    ecrire(f"{ICI}/son/dialogue.wav", mono(dia))
    brut = f"/dev/shm/pub-secretaire-mix-brut.wav"
    ecrire(brut, mix)
    i, pk = mesure(brut)
    g = min(-14.0 - i, -1.2 - pk)      # -14 LUFS visé, mais la crête de la voix (non limitée) passe avant
    pics = {"voix": 20 * np.log10(np.abs(dia).max()), "musique": 20 * np.log10(np.abs(musique).max() + 1e-9),
            "signature": 20 * np.log10(np.abs(sigpiste).max() * 10 ** (-7 / 20) + 1e-9)}
    print("crêtes avant gain (dBFS) :", {k: round(v, 1) for k, v in pics.items()}, "gain", round(g, 1))
    if pk + g > -1.2:
        sys.exit(f"crête trop haute après gain : {pk + g:.1f} dBTP (gain voix seul, on ne limite pas la voix)")
    ecrire(f"{ICI}/son/mix.wav", mix * 10 ** (g / 20))
    i2, pk2 = mesure(f"{ICI}/son/mix.wav")
    os.remove(brut)

    montage = {"duree": duree, "fps": 30, "segments": segs, "mots": mots, "temps": temps, "coches": coches,
               "fin_dialogue": round(fin_dialogue, 3),
               "son": {"lufs": i2, "crete_dbfs": pk2, "gain_applique_db": round(g, 2)}}
    json.dump(montage, open(f"{ICI}/donnees/montage.json", "w"), ensure_ascii=False, indent=1)
    open(f"{ICI}/donnees/donnees.js", "w").write("window.MONTAGE = " + json.dumps(montage, ensure_ascii=False) + ";\n")
    print(f"durée {duree:.2f} s · {len(segs)} segments · {len(mots)} mots · mix {i2:.1f} LUFS, crête {pk2:.1f} dBFS")
    for s in segs:
        print(f"  {s['nom']} {s['qui']:8s} film {s['film'][0]:6.2f}-{s['film'][1]:6.2f}  ({' '.join(w['texte'] for w in mots if w['seg'] == s['nom'])})")
    print("  temps :", temps)


def coches_film(segs, mots):
    """Les lignes de la fiche se cochent quand l'agente l'a dit (le mot qui le prouve)."""
    def t_mot(seg, texte):
        return next(w["t"] for w in mots if w["seg"] == seg and w["texte"] == texte)
    return [
        {"texte": "Urgence repérée", "t": round(t_mot("C", "urgence."), 3)},
        {"texte": "Plombier de garde prévenu", "t": round(t_mot("C", "garde."), 3)},
        {"texte": "Adresse notée", "t": round(t_mot("D", "Toulon."), 3)},
        {"texte": "Bon geste conseillé", "t": round(t_mot("E", "robinet"), 3)},
        {"texte": "SMS envoyé au client", "t": round(t_mot("F", "SMS"), 3)},
    ]


if __name__ == "__main__":
    main()
