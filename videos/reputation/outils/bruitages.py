#!/usr/bin/env python3
"""Bruitages discrets des pubs Vokio Réputation (24/10/2026, demande de Florian : « un peu de sound design subtil,
par exemple quand on met les étoiles, le clic quand on envoie le SMS »).

    python3 /opt/vokio-ads/videos/reputation/outils/bruitages.py contents|planity

Sortie : ../son/<film>-bruitages.wav (31 s, stéréo 48 kHz), que outils/musique.py --mixer ajoute sous la musique.
Sources : ElevenLabs Sound Effects pour le toucher de clavier, le clic et le glissement (cache labo : relancer ne
recoûte rien) ; SYNTHÈSE ici pour la notification, les étoiles (notes de fa majeur, la tonalité de la musique), les tics
du compteur et le scintillement du logo. Aucun son de marque (pas de sonnerie ni de notification d'iPhone).
Les instants viennent des index.html (montre(), entrées des plans) : les changer ensemble.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/opt/vokio-ads/videos/showcase/son")
import labo  # noqa: E402

SR = labo.SR
SON = Path(__file__).resolve().parent.parent / "son"
DUREE = 31.0


def normal(sig, pic_db=-1.0):
    sig = np.asarray(sig, dtype=np.float64)
    p = np.max(np.abs(sig)) or 1
    return sig / p * 10 ** (pic_db / 20)


def el(texte, duree):
    s = labo.lire(labo.sfx(texte, duree, influence=0.6))
    # coupe le silence de tête (les prises EL démarrent parfois avec du blanc) et adoucit la fin
    env = np.abs(s).max(axis=1)
    i = int(np.argmax(env > env.max() * 0.05))
    s = s[max(0, i - int(0.003 * SR)):]
    f = min(len(s), int(0.03 * SR))
    s[-f:] *= np.linspace(1, 0, f)[:, None]
    return normal(s)


def notification():
    """Deux notes de cloche douces, fa puis do aigus, la seconde un peu plus longue."""
    a = labo.cloche(1396.9, 0.9, brillance=0.6, decroissance=5.0)
    b = labo.cloche(2093.0, 1.4, brillance=0.5, decroissance=3.5)
    s = np.zeros(int(1.6 * SR))
    s[:len(a)] += a
    k = int(0.13 * SR)
    s[k:k + len(b)] += b * 0.9
    return normal(labo.reverbe(np.stack([s, s], 1), secondes=1.2, mix=0.18))


def note_etoile(f):
    s = labo.cloche(f, 1.2, brillance=0.7, decroissance=4.0)
    h = labo.cloche(2 * f, 0.6, brillance=0.3, decroissance=7.0)
    s[:len(h)] += 0.25 * h
    return normal(labo.reverbe(np.stack([s, s], 1), secondes=1.4, mix=0.22))


def montee():
    """Un seul son doux qui monte sur les étoiles (retour Florian 24/10 : « pas 5 sons, 1 son bien smooth qui monte, mais
    pas trop dans les aigus ») : accord de fa majeur (fa4, la4, do5) qui glisse d'une quinte en 1,1 s (courbe douce),
    attaque lente, sommet vers 1,0 s puis queue de 0,9 s ; peu d'harmoniques, léger chorus, réverbe. Sommet vers 790 Hz."""
    d = 2.0
    t = np.arange(int(d * SR)) / SR
    glis = np.clip(t / 1.1, 0, 1)
    glis = glis * glis * (3 - 2 * glis)                    # départ et arrivée en douceur
    rapport = 2 ** (7 / 12 * glis)                          # une quinte au total
    env = np.where(t < 1.0, (t / 1.0) ** 1.6, np.exp(-(t - 1.0) / 0.35))
    s = np.zeros_like(t)
    for f0, g in ((349.2, 1.0), (440.0, 0.7), (523.3, 0.55)):
        for dec in (-0.25, 0.25):                             # deux voix un peu désaccordées : chorus
            f = f0 * rapport * 2 ** (dec / 1200 * 8)
            ph = 2 * np.pi * np.cumsum(f) / SR
            s += g * (np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph))
    s *= env
    return normal(labo.reverbe(np.stack([s, s * 0.98], 1), secondes=1.6, mix=0.25))


def tic():
    """Petit tic sec de compteur : bruit filtré très court."""
    n = int(0.03 * SR)
    b = np.random.default_rng(3).standard_normal(n) * np.exp(-np.linspace(0, 9, n))
    b = np.convolve(b, np.ones(6) / 6, "same")
    return normal(b)


def scintillement():
    s = np.zeros(int(1.8 * SR))
    for k, f in enumerate((2093.0, 2637.0, 3136.0)):
        c = labo.cloche(f, 1.4, brillance=0.4, decroissance=4.5) * (0.8 ** k)
        i = int(0.06 * k * SR)
        s[i:i + len(c)] += c[:len(s) - i]
    return normal(labo.reverbe(np.stack([s, s], 1), secondes=1.6, mix=0.3))


# fa majeur pentatonique montant : fa5, la5, do6, ré6, fa6
NOTES_ETOILES = (698.5, 880.0, 1046.5, 1174.7, 1396.9)

TEMPS = {
    "contents": dict(
        touches=[4.35 + 0.09 * (n - 1) for n in range(1, 15)] + [5.85 + 0.1 * (n - 15) for n in range(15, 21)],
        clic=7.0, glisse=[10.0], notif=13.1, etoiles=[19.45 + 0.17 * k for k in range(5)], tics=[], logo=26.45),
    "planity": dict(
        touches=[9.6 + 0.075 * (n - 1) for n in range(1, 15)] + [10.85 + 0.085 * (n - 15) for n in range(15, 21)],
        clic=11.8, glisse=[], notif=14.4, etoiles=[19.5 + 0.17 * k for k in range(5)],
        tics=[23.0 + 0.28 * k for k in range(5)], logo=26.45),
}


# Prise de musique retenue par film (outils/musique.py) : chaque bruitage est calé sur SON niveau à cet instant.
MUSIQUE = {"contents": SON / "contents-2.wav", "planity": SON / "planity-0.wav"}
# Écart visé (dB) entre la crête du bruitage et le niveau efficace de la musique autour de l'instant (± 0,15 s) :
# discret mais audible (mesuré le 24/10 : à gain fixe, le clic sortait à +12 dB sur la vidéo 1, les touches à -11 sur la 2).
ECARTS = {"touche": -6.0, "clic": 3.0, "glisse": -3.0, "notif": 3.0, "etoile": 0.0, "tic": -5.0, "logo": -2.0}


def fabriquer(film):
    T = TEMPS[film]
    piste = np.zeros((int(DUREE * SR), 2))
    mus = labo.lire(MUSIQUE[film]).mean(axis=1)

    def niveau(t):
        i, d = int(t * SR), int(0.15 * SR)
        z = mus[max(0, i - d):i + d]
        return 20 * np.log10(np.sqrt((z ** 2).mean()) + 1e-9)

    def poser(sig, t, genre, pan=0.0):
        sig = normal(sig)       # crête à -1 dBFS
        labo.placer(piste, sig, t, gain_db=niveau(t) + ECARTS[genre] + 1.0, pan=pan)
    touche = el("single very soft tap on a smartphone touchscreen keyboard, dry, close, very short", 0.5)
    clic = el("soft satisfying UI button click, clean, short, modern app", 0.5)
    glisse = el("very soft short airy whoosh, subtle swipe, clean", 0.7)
    for k, t in enumerate(T["touches"]):
        poser(touche * (0.85 + 0.15 * ((k * 7) % 3) / 2), t, "touche", pan=0.12 if k % 2 else -0.12)
    poser(clic, T["clic"], "clic")
    for t in T["glisse"]:
        poser(glisse, t - 0.08, "glisse")
    poser(notification(), T["notif"], "notif")
    poser(montee(), T["etoiles"][0] - 0.05, "etoile")       # un seul son pour les 5 étoiles (24/10)
    for t in T["tics"]:
        poser(tic(), t, "tic")
    poser(scintillement(), T["logo"], "logo")
    sortie = SON / f"{film}-bruitages.wav"
    labo.ecrire(sortie, piste)
    return sortie


if __name__ == "__main__":
    print(fabriquer(sys.argv[1]))
