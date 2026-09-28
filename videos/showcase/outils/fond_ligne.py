#!/usr/bin/env python3
"""Fond de ligne continu, tiré d'un VRAI appel : un bruit coloré par le spectre mesuré des passages où la porte de
l'appelant est ouverte sans voix, pour porter les jointures du dialogue (plus jamais de chute sur du silence numérique).

    python3 outils/fond_ligne.py SOURCE.wav --zones 11.92:12.05 74.92:75.09 [--bande 700 7000] [--png spectre.png]
        affiche le spectre moyen (tiers d'octave) des zones et, avec --png, le trace
    python3 outils/fond_ligne.py SOURCE.wav --zones … --sortie fond.wav --duree 50.066667 --de 4.2 --a 38.933333 --rms -60
        écrit le fond seul (mono dupliqué, float 32 bits) : fondu d'entrée 250 ms, coupe de 5 ms à la fin (film de
        50,07 s depuis l'échange du prénom : décroché 4,20, raccroché 38,933 ; 47 et 35,867 dans le film d'avant) ;
        son/stems_amont.py n'utilise pas cette ligne : il prend la durée et le raccroché dans les données
    from fond_ligne import spectre_zones, fond, niveau_bande, presence_porte, confort
        S = spectre_zones(x, [(a, b), …])                 (f, dB) : spectre moyen lissé au tiers d'octave
        y = fond(S, n, graine=7, bande=(700, 7000))        bruit mono (n,) à ce spectre, RMS 1
        niveau_bande(x, [(a, b), …], (2000, 8000))         niveau RMS (dBFS) des zones dans une bande
        p = presence_porte(voix, [(a, b), …], plancher_db, (2000, 8000))   porte ouverte, au pas de 1 ms, dans les tours
        g = confort(p, n, gain_db, relache=0.35)           gain (n,) du BRUIT DE CONFORT : il prend le relais quand la
                                                           porte se ferme (fondu enchaîné), puis décroît (pas de chute nette)
BRUIT DE CONFORT (la « saute » de 14,03, fin de « hier » : la porte VAD de l'appelant se ferme DANS la source, montes
13,795 → 13,845, −58 → −82 dBFS en 50 ms ; dans le film, −17 dB tenus dans 2-8 kHz). Comme le CNG d'une ligne VoIP :
un fond au spectre ET au niveau mesurés de la porte ouverte (moins un écart de 2 dB) prend le relais du vrai fond
quand la porte se ferme (fondu enchaîné de 10 ms, 15 ms avant la fermeture) et décroît ensuite en ~8,7/relache dB par
seconde au lieu de tomber. Il est NUL pendant la parole (la voix garde toute sa marge) : c'est le fond TOTAL qui reste
à niveau constant, il ne respire pas avec les mots.
Déterministe (graine), aucune écriture hors de --sortie et --png. Utilisé par son/stems_amont.py.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sonlib as L  # noqa: E402

SR = L.SR


def spectre_zones(x, zones, nfft=1024, pas=256, tiers=1 / 3):
    """Spectre de puissance moyen (Welch, Hann) des zones [(a, b)] en secondes, lissé en fractions d'octave.
    Renvoie (f, dB) sur la grille rfft de nfft."""
    m = L.mono(x)
    w = np.hanning(nfft)
    P, nb = np.zeros(nfft // 2 + 1), 0
    for a, b in zones:
        s = m[int(a * SR):int(b * SR)]
        for i in range(0, max(1, len(s) - nfft + 1), pas):
            fr = s[i:i + nfft]
            if len(fr) < nfft:
                fr = np.concatenate([fr, np.zeros(nfft - len(fr))])
            P += np.abs(np.fft.rfft(fr * w)) ** 2
            nb += 1
    P /= max(nb, 1)
    f = np.fft.rfftfreq(nfft, 1 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    Ps = np.empty_like(P)
    for k in range(len(f)):
        sel = np.abs(lf - lf[k]) <= tiers / 2
        Ps[k] = P[sel].mean()
    return f, 10 * np.log10(Ps + 1e-30)


def fond(S, n, graine=7, bande=(700.0, 7000.0), front=0.3):
    """Bruit blanc (graine) mis en forme par le spectre S = (f, dB) (interpolé), borné à `bande` (fronts cosinus de
    `front` octave), RMS 1. Une seule FFT de la longueur du film : pas de boucle audible."""
    f_s, db_s = S
    rng = np.random.default_rng(graine)
    M = 1 << (n - 1).bit_length()
    X = np.fft.rfft(rng.standard_normal(M))
    f = np.fft.rfftfreq(M, 1 / SR)
    amp = 10 ** (np.interp(f, f_s, db_s) / 20)
    lf = np.log2(np.maximum(f, 1e-3))
    if bande[0]:
        p = np.clip((lf - (np.log2(bande[0]) - front)) / (2 * front), 0, 1)
        amp *= 0.5 - 0.5 * np.cos(np.pi * p)
    if bande[1]:
        p = np.clip((lf - (np.log2(bande[1]) - front)) / (2 * front), 0, 1)
        amp *= 0.5 + 0.5 * np.cos(np.pi * p)
    y = np.fft.irfft(X * amp, M)[:n]
    return y / (np.sqrt(np.mean(y ** 2)) + 1e-20)


def niveau_bande(x, zones, bande=(2000.0, 8000.0)):
    """Niveau RMS (dBFS) de l'ensemble des zones [(a, b)] (s) dans la bande."""
    m = L.mono(x)
    e, k = 0.0, 0
    for a, b in zones:
        i, j = int(a * SR), int(b * SR)
        pad = int(0.2 * SR)
        s = L.passe_bande(m[max(0, i - pad):j + pad], *bande, front=0.15)[i - max(0, i - pad):][:j - i]
        e += float(np.sum(s * s)); k += len(s)
    return 10 * np.log10(e / max(k, 1) + 1e-24)


def presence_porte(voix, tours, plancher_db, bande=(2000.0, 8000.0), sous=8.0, ouvre=10.0, fen=0.010, hyst=2.0):
    """Porte de la voix OUVERTE, au pas de 1 ms (bool, len = durée en ms), seulement dans les tours [(a, b)] de ce
    locuteur. La PREMIÈRE ouverture d'un tour se fait sur la parole (RMS `fen` s dans la bande ≥ plancher + ouvre :
    jamais sur un souffle ou un fond baissé par un gain de clip) ; ensuite la porte se ferme sous plancher − sous et se
    rouvre dès plancher − sous + hyst (les micro-fermetures de la VAD entre deux syllabes)."""
    m = L.passe_bande(L.mono(voix), *bande, front=0.15)
    c = np.concatenate([[0.0], np.cumsum(m * m)])
    w, pas = int(fen * SR), SR // 1000
    k = np.arange(0, len(m) - w, pas)
    l = 10 * np.log10((c[k + w] - c[k]) / w + 1e-24)
    t = (k + w / 2) / SR
    dans = np.zeros(len(k), bool)
    for a, b in tours:
        dans |= (t >= a) & (t <= b)
    out = np.zeros(len(k), bool)
    for a, b in tours:
        idx = np.flatnonzero((t >= a) & (t <= b))
        parle, etat = False, False
        for i in idx:
            if not parle:
                parle = etat = l[i] >= plancher_db + ouvre
            elif etat:
                etat = l[i] >= plancher_db - sous
            else:
                etat = l[i] >= plancher_db - sous + hyst
            out[i] = etat
    return out


def confort(presence, n, gain_db, relache=0.35, attaque=0.005, remplace=True, anticipation=0.015, fondu=0.010):
    """Gain linéaire (n,) : 10^(gain_db/20) tant que presence (pas 1 ms) est vraie (montée en `attaque` s), puis
    décroissance exponentielle de constante `relache` s. 0 ailleurs.
    remplace=True : le confort REMPLACE le vrai fond au lieu de s'y ajouter. Nul tant que la porte est ouverte (la
    parole et son vrai fond sont là : la voix ne perd rien de sa marge), il prend le relais quand elle se ferme, en
    fondu enchaîné de `fondu` s commencé `anticipation` s avant la fermeture mesurée (hors ligne, on voit venir), puis
    décroît. Le fond total reste à son niveau au lieu de tomber de 30 dB en 30 ms."""
    g = 10 ** (gain_db / 20)
    ka, kr = 1 - np.exp(-0.001 / attaque), 1 - np.exp(-0.001 / relache)
    env = np.zeros(len(presence))
    v = 0.0
    for i, p in enumerate(presence):
        v += ((g - v) * ka) if p and v < g else (-v * kr if not p else 0.0)
        env[i] = v
    if remplace:
        k = int(round(anticipation * 1000))
        o = np.concatenate([presence[k:], np.zeros(k, bool)]).astype(float)       # la porte, vue `anticipation` plus tôt
        w = np.hanning(max(3, int(round(fondu * 1000)) + 2))[1:-1]
        o = np.clip(np.convolve(o, w / w.sum(), mode="same"), 0.0, 1.0)
        env *= 1.0 - o
    t_ms = (np.arange(len(env)) + 0.5) / 1000
    return np.interp(np.arange(n) / SR, t_ms, env, left=0.0, right=0.0)


def fenetre(n, de, a, fondu_in=0.25, coupe=0.005):
    """Enveloppe : 0 avant `de`, fondu cosinus d'entrée, 1, coupe cosinus de `coupe` s à `a`, 0 après."""
    t = np.arange(n) / SR
    e = np.clip((t - de) / fondu_in, 0, 1)
    e = 0.5 - 0.5 * np.cos(np.pi * e)
    k = (t >= a) & (t < a + coupe)
    e[k] *= 0.5 + 0.5 * np.cos(np.pi * (t[k] - a) / coupe)
    e[t >= a + coupe] = 0
    return e


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--zones", nargs="+", required=True, help="a:b en secondes dans la source")
    ap.add_argument("--bande", nargs=2, type=float, default=(700.0, 7000.0))
    ap.add_argument("--png")
    ap.add_argument("--sortie")
    ap.add_argument("--duree", type=float)
    ap.add_argument("--de", type=float, default=0.0)
    ap.add_argument("--a", type=float)
    ap.add_argument("--rms", type=float, default=-60.0, help="RMS du fond (dBFS) sur la fenêtre pleine")
    ap.add_argument("--graine", type=int, default=7)
    a = ap.parse_args()
    x = L.lire(a.source)
    zones = [tuple(float(v) for v in z.split(":")) for z in a.zones]
    f, d = spectre_zones(x, zones)
    for c in 125 * 2 ** np.arange(0, 7, 0.5):
        print(f"   {c:7.0f} Hz  {np.interp(c, f, d):7.1f} dB")
    if a.png:
        g = np.linspace(np.log(60), np.log(12000), 400)
        L.courbe_png([("spectre des zones", np.exp(g) / 100, np.interp(np.exp(g), f, d), L.ENCRE)], a.png, 0.6, 120,
                     float(d[(f > 60) & (f < 12000)].min()) - 3, float(d.max()) + 3, px_par_s=8,
                     titre="spectre moyen (abscisse : Hz / 100, échelle linéaire)", unite=" dB")
        print(a.png)
    if a.sortie:
        n = int(round(a.duree * SR))
        y = fond((f, d), n, a.graine, tuple(a.bande)) * L.gain(a.rms) * fenetre(n, a.de, a.a or a.duree)
        import subprocess
        st = np.stack([y, y], axis=1).astype("<f4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                        "-c:a", "pcm_f32le", a.sortie], input=st.tobytes(), check=True)
        print(a.sortie)


if __name__ == "__main__":
    main()
