#!/usr/bin/env python3
"""Bruitages ElevenLabs de la variante « SOUND DESIGN » (27/09) : le catalogue des prompts, les prises, leur mesure.

    python3 son/riche-design/bruitages.py            génère (ou relit du cache) toutes les prises, les mesure
                                                     → son/riche-design/prises/<nom>-prise<k>.wav + prises.json

Chaque bruitage a plusieurs prises (même prompt, numéro de prise dans la clé du cache : mix.prise_elevenlabs, clé PUB).
Le choix se fait par la mesure (voir choisir() dans mix_riche_design.py) : aucune prise n'est retenue « à l'oreille »,
on ne peut pas écouter ici. Mesures par prise : durée utile (au-dessus de crête − 30 dB), attaque, nombre de bouffées,
fond (médiane hors événement, relatif à la crête), centroïde spectral, stabilité de l'enveloppe (écart-type du niveau
RMS 20 ms sur la partie tenue, en dB), part d'énergie sous 150 Hz et au-dessus de 8 kHz.

Règle de fond : aucun prompt ne décrit une voix, un téléphone qui sonne, une musique ou un lieu de l'appel réel
(la clinique) : le monde sonore est celui du film (papier, encre, bois, une pièce calme en fin d'après-midi).
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
SON = ICI.parent
sys.dont_write_bytecode = True        # les .pyc de son/__pycache__ sont suivis par git : ne pas les réécrire
sys.path.insert(0, str(SON))
import labo  # noqa: E402
import mix as MX  # noqa: E402  (données et outils : rien ne se recalcule à l'import)

SR = labo.SR
PRISES = ICI / "prises"

# nom : texte (anglais : le modèle y est plus précis), durée (s), influence du prompt, nombre de prises
CATALOGUE = {
    "encre": dict(texte="a single tiny drop of ink landing on thick matte paper, extremely close microphone, one soft wet "
                        "tick, dry room, no reverb, no music, no voices", duree=0.6, influence=0.7, prises=4),
    "plume": dict(texte="a fountain pen nib writing quickly on thick textured cotton paper, very close microphone, fine "
                        "continuous scratching strokes, quiet room, no music, no voices", duree=2.0, influence=0.6, prises=4),
    "vibreur_bois": dict(texte="a smartphone vibrating face down on a solid wooden table, steady continuous buzz with a "
                               "slight wooden rattle, close, quiet room, no ringtone, no music, no voices", duree=2.0,
                         influence=0.7, prises=4),
    "ambiance": dict(texte="quiet room tone in a calm house in the late afternoon, window half open, very distant birds "
                           "outside, faint distant town hum, no voices, no music, no footsteps, no clock",
                     duree=22.0, influence=0.5, prises=3),
    "oiseaux": dict(texte="late afternoon heard from inside a calm quiet room, window open, a few distant birds chirping far "
                          "away outside, sparse gentle chirps, soft air, no voices, no music, no traffic, no wind noise",
                    duree=22.0, influence=0.6, prises=3),
    "oiseau_loin": dict(texte="a single small bird chirping a few times far away outside an open window, quiet sunny late "
                              "afternoon, soft and distant, no other sounds, no voices, no music", duree=4.0, influence=0.7,
                        prises=3),
    "papier": dict(texte="a single sheet of heavy paper sliding softly across a wooden desk, one gentle short swish, "
                         "close, dry, no music, no voices", duree=1.0, influence=0.7, prises=4),
    "glisse_objet": dict(texte="a small smooth object gliding gently across a felt covered wooden desk, one soft short "
                               "slide, close, dry, no music, no voices", duree=0.8, influence=0.7, prises=4),
    # le téléphone qui monte et qui sort (revue du 27/09) : UNE matière pour les deux gestes (avant : papier à l'entrée,
    # objet feutré à la sortie) ; il entre sous « Au revoir » : on garde sa part au-dessus de la ligne (> 4,5 kHz), il
    # faut donc une prise qui a du grain aigu (verre sur bois), mesuré par part_sur_4k5
    "glisse_telephone": dict(texte="a smartphone with a glass back sliding smoothly across a varnished wooden desk, one "
                                   "short soft slide with a fine glassy hiss, close microphone, dry, no music, no voices",
                             duree=0.8, influence=0.7, prises=4),
    "toucher_corps": dict(texte="a fingertip tapping once on a hardcover notebook lying on a wooden desk, soft muted knock, "
                                "close, dry, one single tap, no music", duree=0.5, influence=0.7, prises=4),
    "bulle": dict(texte="a delicate soft airy bloom, like a tiny soap bubble gently inflating then settling, subtle, no pop, "
                        "no music, no voices", duree=0.6, influence=0.6, prises=3),
}


def mesurer_prise(x):
    m = x.mean(axis=1)
    w = int(0.020 * SR)
    e = 10 * np.log10(np.convolve(m ** 2, np.ones(w) / w, mode="same") + 1e-14)
    em = float(e.max())
    utile = np.nonzero(e > em - 30)[0]
    haut = e > em - 15
    debuts = np.nonzero(haut & ~np.concatenate([[False], haut[:-1]]))[0]
    fins = np.nonzero(haut & ~np.concatenate([haut[1:], [False]]))[0]
    bouffees, derniere = 0, -10 ** 9
    for d, f in zip(debuts, fins):
        if d - derniere > int(0.030 * SR):
            bouffees += 1
        derniere = f
    reste = e[min(len(e) - 1, fins[-1] + int(0.3 * SR)):]
    fond = float(np.median(reste) - em) if len(reste) > int(0.05 * SR) else float(np.percentile(e, 10) - em)
    tenu = e[(e > em - 12)]
    X = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    tot = X.sum() + 1e-20
    return {"duree_s": round(len(m) / SR, 3), "crete_rms_db": round(em, 1),
            "attaque_s": round(float(utile[0] / SR), 4) if len(utile) else None,
            "duree_utile_s": round(float((utile[-1] - utile[0]) / SR), 3) if len(utile) else 0.0,
            "bouffees": int(bouffees), "fond_db_sous_crete": round(fond, 1),
            "tronquee": bool(np.max(e[:int(0.005 * SR)]) > em - 20),
            "centroide_hz": round(float((X * f).sum() / tot), 0),
            "stabilite_db": round(float(np.std(tenu)), 2) if len(tenu) > 10 else None,
            "part_sous_150hz": round(float(X[f < 150].sum() / tot), 3),
            "part_sur_4k5": round(float(X[f > 4500].sum() / tot), 3),
            "part_sur_8khz": round(float(X[f > 8000].sum() / tot), 3)}


def prises(nom):
    """Les prises d'un bruitage : [(k, chemin, mesures)], générées au besoin (cache)."""
    P = CATALOGUE[nom]
    out = []
    PRISES.mkdir(exist_ok=True)
    for k in range(P["prises"]):
        wav = MX.prise_elevenlabs(P["texte"], P["duree"], P["influence"], k)
        dst = PRISES / f"{nom}-prise{k + 1}.wav"
        if not dst.exists():
            shutil.copyfile(wav, dst)
        out.append((k + 1, dst, mesurer_prise(labo.lire(dst))))
    return out


def main():
    rapport = {}
    for nom in CATALOGUE:
        print(f"{nom} :")
        rapport[nom] = {"prompt": CATALOGUE[nom], "prises": []}
        for k, chemin, m in prises(nom):
            print(f"   prise {k} : {m}")
            rapport[nom]["prises"].append({"prise": k, "fichier": str(chemin), **m})
    (ICI / "prises.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
