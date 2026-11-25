#!/usr/bin/env python3
"""Bande son de « Le ticket » (Réputation n° 3, 25/11/2026) : un beat joué avec les SONS DU SALON, posé sur le lit
ElevenLabs Music (outils/musique.py), aux instants de minutage.js (la même source que l'image).

    python3 /opt/vokio-ads/videos/reputation/ticket/outils/salon.py              → son/percussions.wav, son/mix.wav + mesures
    python3 .../salon.py --livrer <muet.mp4> <sortie.mp4>                         → pose son/mix.wav sur le rendu muet

Les sons (ElevenLabs Sound Effects, un tirage chacun, cache labo : relancer ne recoûte rien) :
  imprimante thermique  → charleston : un grain de 0,1 s par avance de papier, et en contretemps dans le groove
  ciseaux               → caisse claire, sur les temps 2 et 4 dès que le geste commence
  tiroir-caisse         → accent, sur le toucher de « Demander un avis »
  sonnette du comptoir  → une note par palier du compteur d'avis, transposée en fa majeur (do6, fa6, la6, do7)
  sèche-cheveux         → montée avant la chute, coupée net sur le temps fort
  coupe du papier       → temps forts (fin de l'accroche, TOTAL), doublée d'une grosse caisse grave sur la chute
  papier qui glisse     → chaque ticket de la semaine qui se pose sur la pile
Synthèse : notification du SMS (celle des films 1 et 2), grosse caisse de la chute. Touches du clavier : le tirage déjà
en cache des films 1 et 2.
Le lit est recalé sur la grille (phase mesurée 11 ms), filtré en passe-bas qui s'ouvre pendant la montée (22,5 → 25 s)
pour que la chute éclate, coupé à 31,25 s avec un fondu d'une seconde sur l'accord tenu.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/opt/vokio-ads/videos/showcase/son")
sys.path.insert(0, str(ICI.parent / "outils"))
import labo  # noqa: E402
from bruitages import notification  # noqa: E402  (fa-do aigus, la notification des films 1 et 2)

SR = labo.SR
SON = ICI / "son"
LIT = SON / "lit-1.wav"
PHASE_LIT = 0.011            # mesurée par outils/musique.py --grille (prise 1)


def minutage():
    js = "global.window={};require(process.argv[1]);console.log(JSON.stringify(window.MINUTAGE))"
    return json.loads(subprocess.run(["node", "-e", js, str(ICI / "minutage.js")], capture_output=True, text=True,
                                     check=True).stdout)


M = minutage()
TPS = 60 / M["bpm"]
DUREE = M["duree_temps"] * TPS
T = lambda b: b * TPS  # noqa: E731

SFX = {
    "imprimante": ("thermal receipt printer printing a receipt, fast rhythmic mechanical buzzing line by line, close, dry room", 3.0),
    "coupe": ("receipt printer auto cutter cutting the paper, one sharp crisp mechanical snap, close, dry", 0.6),
    "ciseaux": ("single crisp snip of hairdresser scissors cutting hair, close, dry", 0.5),
    "sonnette": ("single ring of a small brass service bell on a shop counter, clean, natural decay", 1.5),
    "tiroir": ("cash register drawer sliding open with a short metallic chunk, close, dry", 0.8),
    "sechoir": ("hair dryer switched on, airflow rising in intensity and pitch, steady whoosh, close", 4.0),
    "papier": ("a paper receipt sliding across a wooden counter, soft short swish, close, dry", 0.6),
}
TOUCHE = ("single very soft tap on a smartphone touchscreen keyboard, dry, close, very short", 0.5)


def sfx(nom):
    t, d = SFX[nom] if nom in SFX else TOUCHE
    return labo.lire(labo.sfx(t, d, influence=0.6)).mean(axis=1)


def normal(s, pic_db=-1.0):
    p = np.max(np.abs(s)) or 1
    return s / p * 10 ** (pic_db / 20)


def fondus(s, a=0.002, r=0.02):
    s = s.copy()
    na, nr = int(a * SR), int(r * SR)
    s[:na] *= np.linspace(0, 1, na)
    s[-nr:] *= np.linspace(1, 0, nr)
    return s


def attaque(s, seuil=0.15):
    """Indice de la première attaque (le son posé à l'instant t a son attaque à t, pas son silence de tête)."""
    e = np.abs(s)
    return max(0, int(np.argmax(e > e.max() * seuil)) - int(0.002 * SR))


def grains_imprimante():
    """Grains de 0,1 s pris aux endroits les plus nets de la prise (attaque puis bourdon de tête)."""
    x = sfx("imprimante")
    env = np.sqrt(np.convolve(x ** 2, np.ones(240) / 240, "same"))
    res = []
    for t0 in (0.95, 1.30, 1.62, 1.98, 2.31, 2.62):
        i = int(t0 * SR)
        j = i + int(0.04 * SR)
        k = i + int(np.argmax(np.diff(env[i:j])))      # front montant le plus raide dans la fenêtre
        g = x[k:k + int(0.10 * SR)]
        g = g * np.exp(-np.linspace(0, 2.2, len(g)))   # un trait de tête, pas un ronflement
        res.append(normal(fondus(g, 0.001, 0.03)))
    return res


def transposer(s, rapport):
    """Hauteur × rapport par rééchantillonnage (la durée change d'autant : c'est une cloche, c'est naturel)."""
    n = int(len(s) / rapport)
    return np.interp(np.arange(n) * rapport, np.arange(len(s)), s)


def note_sonnette(f_cible):
    x = sfx("sonnette")
    x = x[attaque(x, 0.3):]
    spec = np.abs(np.fft.rfft(x[:int(0.5 * SR)]))
    fr = np.fft.rfftfreq(int(0.5 * SR), 1 / SR)
    f0 = fr[np.argmax(spec * (fr > 800))]
    return normal(fondus(transposer(x, f_cible / f0), 0.001, 0.1)), f0


def grosse_caisse():
    t = np.arange(int(0.6 * SR)) / SR
    f = 48 + 70 * np.exp(-t * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    clic = labo.bruit_rose(len(t), 4) * np.exp(-t * 180) * 6
    return normal(s + clic)


def lit():
    """Le lit : recalé sur la grille, coupé à la durée du film, montée en passe-bas qui s'ouvre jusqu'à la chute."""
    x = labo.lire(LIT)
    x = x[int(PHASE_LIT * SR):int(PHASE_LIT * SR) + int(DUREE * SR)]
    x = np.pad(x, ((0, int(DUREE * SR) - len(x)), (0, 0)))
    # passe-bas glissant par STFT (fenêtres de 2048, recouvrement 75 %) : coupure 450 Hz → 9 kHz, exponentielle,
    # de la sortie de la semaine jusqu'à 30 ms avant la chute ; gain -3 dB pendant la montée.
    t0, t1 = T(M["chute"]["sechoir"][0]), T(M["chute"]["coupe"]) - 0.03
    n, h = 2048, 512
    fen = np.hanning(n)
    i0, i1 = int((t0 - 0.2) * SR), int((t1 + 0.1) * SR)
    seg = x[i0:i1].copy()
    out = np.zeros_like(seg)
    norme = np.zeros(len(seg))
    fr = np.fft.rfftfreq(n, 1 / SR)
    for a in range(0, len(seg) - n, h):
        tc = (i0 + a + n / 2) / SR
        u = np.clip((tc - t0) / (t1 - t0), 0, 1)
        fc = 450 * (9000 / 450) ** (u ** 1.6) if tc >= t0 else 22000
        masque = 1 / np.sqrt(1 + (fr / fc) ** 8)          # passe-bas 4 pôles
        g = 10 ** (-3 * min(1, max(0, (tc - t0) / 0.3)) / 20) if tc < t1 else 1
        for c in (0, 1):
            out[a:a + n, c] += np.fft.irfft(np.fft.rfft(seg[a:a + n, c] * fen) * masque * g, n) * fen
        norme[a:a + n] += fen ** 2
    out /= np.maximum(norme, 1e-6)[:, None]
    # raccords en fondu enchaîné de 50 ms aux deux bouts, pour ne rien entendre d'autre que le filtre
    r = int(0.05 * SR)
    w = np.linspace(0, 1, r)[:, None]
    deb, fin = int(0.2 * SR), len(seg) - int(0.1 * SR)
    seg[deb:deb + r] = seg[deb:deb + r] * (1 - w) + out[deb:deb + r] * w
    seg[deb + r:fin - r] = out[deb + r:fin - r]
    seg[fin - r:fin] = out[fin - r:fin] * (1 - w) + seg[fin - r:fin] * w
    x[i0:i1] = seg
    # fondu final d'une seconde sur l'accord tenu
    nf = int(1.0 * SR)
    x[-nf:] *= np.linspace(1, 0, nf)[:, None] ** 1.5
    return x


def fabriquer():
    m = lit()
    mono = m.mean(axis=1)
    piste = np.zeros((int(DUREE * SR), 2))
    journal = []

    def niveau(t, d=0.3):
        i, k = int(t * SR), int(d * SR)
        z = mono[max(0, i - k):i + k]
        return 20 * np.log10(np.sqrt((z ** 2).mean()) + 1e-9)

    # Écarts réglés le 25/11 : le beat du salon doit s'entendre DEVANT le lit (premier jet à +4 dB : 15 à 18 dB efficaces
    # sous le lit, un simple décor)
    def poser(sig, t, nom, ecart_db, pan=0.0, plancher=-40.0):
        """Crête du son = niveau efficace du lit autour de t + écart (plancher : le lit peut être presque muet)."""
        sig = normal(sig)
        g = max(niveau(t), plancher) + ecart_db + 1.0
        a = attaque(sig)
        labo.placer(piste, sig[a:], t, gain_db=g, pan=pan)
        journal.append((round(t, 3), nom))

    G = grains_imprimante()
    nimp = [0]

    def imprimante(t, ecart, pan=0.0):
        nimp[0] += 1
        poser(G[nimp[0] % len(G)] * (0.85 + 0.15 * (nimp[0] % 3) / 2), t, "imprimante", ecart, pan)

    # 1 · l'imprimante qui imprime vraiment (avances de papier visibles à l'image)
    for cle in ("ticket1", "ticket2", "chute"):
        for b, _ in M[cle]["avances"]:
            imprimante(T(b), 9.0)
    # 2 · l'imprimante en charleston, en contretemps, pendant le groove (le geste, le SMS, la semaine) ;
    #     double croche sur la dernière mesure de la semaine : le rythme accélère
    for k in range(M["plans"]["geste"] * 2 + 1, M["plans"]["chute"] * 2, 2):
        imprimante(T(k / 2), 3.0, pan=0.25)
    for k in range(32 * 4, 36 * 4):
        if k % 2:
            imprimante(T(k / 4), 0.0, pan=-0.2)
    # 3 · les ciseaux en caisse claire, temps 2 et 4, du geste à la chute
    cis = sfx("ciseaux")
    cis = normal(fondus(cis[attaque(cis):][:int(0.16 * SR)], 0.001, 0.04))
    for b in range(M["plans"]["geste"] + 1, M["plans"]["chute"], 2):
        poser(cis, T(b), "ciseaux", 11.0)
    # 4 · le geste : touches, tiroir-caisse sur « Demander un avis »
    tou = sfx("touche")
    g = M["geste"]
    for n in range(14):
        poser(tou, T(g["numero"] + n * g["pas"]), "touche", 2.0, pan=0.1 if n % 2 else -0.1)
    for n in range(6):
        poser(tou, T(g["prenom"] + n * g["pas"]), "touche", 2.0, pan=0.1 if n % 2 else -0.1)
    poser(sfx("tiroir"), T(g["presse"]), "tiroir", 10.0)
    # 5 · le SMS
    poser(notification().mean(axis=1), T(M["sms"]["bulle"]), "notification", 5.0)
    # 6 · la semaine : papier qui glisse (finit sur le temps), sonnette en fa majeur à chaque palier
    pap = sfx("papier")
    pap = normal(pap[attaque(pap, 0.3):])
    for k, b in enumerate(M["semaine"]["tickets"]):
        poser(pap, T(b) - 0.42, "papier", 3.0, pan=0.3 if k % 2 == 0 else -0.3)
    notes = (1046.5, 1396.9, 1760.0, 2093.0)          # do6, fa6, la6, do7 : arpège montant de fa majeur
    for (b, _), f in zip(M["semaine"]["paliers"], notes):
        s, f0 = note_sonnette(f)
        poser(s, T(b), f"sonnette {f:.0f} Hz", 7.0)
    # 7 · la chute : sèche-cheveux en montée, coupé net sur la coupe du papier + grosse caisse
    a, b = M["chute"]["sechoir"]
    sec = sfx("sechoir")
    n = int((T(b) - T(a)) * SR)
    sec = sec[:n] * np.linspace(0.25, 1, n) ** 2
    sec[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
    labo.placer(piste, normal(sec), T(a), gain_db=niveau(T(b) - 0.5) + 3.0)
    journal.append((round(T(a), 3), "sèche-cheveux (montée)"))
    cou = sfx("coupe")
    poser(cou, T(M["ticket1"]["coupe"]), "coupe", 12.0)
    poser(cou, T(M["chute"]["coupe"]), "coupe (chute)", 11.0)
    poser(grosse_caisse(), T(M["chute"]["coupe"]), "grosse caisse (chute)", 9.0)
    poser(sfx("tiroir"), T(M["chute"]["coupe"]), "tiroir (chute)", 2.0)
    # 8 · la fin : une note grave de sonnette quand le point se pose sur le ı
    s, _ = note_sonnette(698.5)                        # fa5
    poser(s, T(M["fin"]["mot"]) + 0.85, "sonnette fa5 (point)", 4.0)

    labo.ecrire(SON / "percussions.wav", piste)
    mix = m + piste
    brut = SON / "mix-brut.wav"
    labo.ecrire(brut, mix / max(1.0, np.abs(mix).max() / 0.98))
    # sonie : gain linéaire vers -14 LUFS, puis limiteur doux pour tenir la crête sous -1 dBTP
    me = labo.mesurer(brut)
    gain = -14.0 - me["lufs"]
    sortie = SON / "mix.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(brut), "-af",
                    f"volume={gain:.2f}dB,alimiter=limit=0.84:attack=3:release=60:level=disabled",
                    "-ar", str(SR), "-c:a", "pcm_s16le", str(sortie)], check=True)
    (SON / "journal-sons.json").write_text(json.dumps(sorted(journal), ensure_ascii=False, indent=0))
    return sortie, me


def livrer(muet, sortie):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(muet), "-i", str(SON / "mix.wav"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                    "-movflags", "+faststart", str(sortie)], check=True)
    return sortie


if __name__ == "__main__":
    if "--livrer" in sys.argv:
        i = sys.argv.index("--livrer")
        print(livrer(sys.argv[i + 1], sys.argv[i + 2]))
        sys.exit(0)
    s, avant = fabriquer()
    print("avant sonie", avant)
    print(s, labo.mesurer(s))
