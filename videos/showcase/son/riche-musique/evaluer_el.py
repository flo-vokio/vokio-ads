#!/usr/bin/env python3
"""Évaluation des prises ElevenLabs Music contre la partition du film (27/09) : peut-on s'en servir comme lit ?

    python3 son/riche-musique/evaluer_el.py      → son/riche-musique/el/evaluation.json + planche PNG (scratchpad)

Pour chaque prise : tempo (autocorrélation du flux spectral, global et par section) ; calage sur la grille du film
(meilleur décalage des temps forts, part de l'énergie d'attaque qui tombe à ±40 ms d'un temps) ; accord par mesure
(part du chroma 60-2 000 Hz dans les notes de l'accord prévu par mix_riche_musique.ACCORDS) ; basse par mesure ;
arc (sonie court terme : maximum, sonie du logo contre le maximum, sonie de la sonnerie).
"""
import json
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parent))
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import mesures as ME  # noqa: E402
import mix_riche_musique as R  # noqa: E402

SR = labo.SR
NOTES_ACCORD = {"Gadd9": {7, 11, 2, 9}, "Gmaj9": {7, 11, 2, 6, 9}, "Bm7": {11, 2, 6, 9}, "Em9": {4, 7, 11, 2, 6},
                "Asus4": {9, 2, 4}, "A": {9, 1, 4}, "G": {7, 11, 2}, "D": {2, 6, 9}}
# classes : do=0 … si=11 (ME.NOMS)


def calage_grille(x):
    fl, t = ME.enveloppe_attaques(x)
    fl = np.maximum(fl - np.median(fl), 0)
    meilleur = (0, 0)
    for dec in np.arange(-0.38, 0.38, 0.005):
        temps = R.tb(np.arange(0, 62)) + dec
        pres = np.zeros_like(t, dtype=bool)
        for tb_ in temps:
            pres |= np.abs(t - tb_) <= 0.040
        part = fl[pres].sum() / (fl.sum() + 1e-12)
        if part > meilleur[0]:
            meilleur = (part, dec)
    # part attendue au hasard : 80 ms sur 766,7 ms
    return {"part_attaques_sur_les_temps": round(float(meilleur[0]), 3), "hasard": round(0.080 / R.BEAT, 3),
            "meilleur_decalage_s": round(float(meilleur[1]), 3)}


def main():
    res = {}
    for k in range(5):
        w = ICI / "el" / f"prise{k}.wav"
        if not w.exists():
            continue
        x = labo.lire(w)[:R.N]
        r = {"tempo_global_bpm": round(float(ME.tempo(x)), 1)}
        r["tempo_par_tiers"] = [round(float(ME.tempo(x[int(a * SR):int(b * SR)])), 1) for a, b in ((0, 16), (16, 32), (32, 47))]
        r["grille"] = calage_grille(x)
        mes = []
        for kk in range(1, 15):
            a, b = R.tb(4 * kk), R.tb(4 * kk + 4)
            if kk == 11:
                b = R.T_RAC
            b = min(b, 46.7)
            nom = R.accord_a((a + b) / 2)[1]
            c = ME.chroma(x, a, b)
            cb = ME.chroma(x, a, b, fmin=35, fmax=160)
            dans = sum(c[j] for j in NOTES_ACCORD[nom]) / c.sum()
            mes.append({"mesure": kk, "accord_prevu": nom, "part_chroma_dans_l_accord": round(float(dans), 2),
                        "basse_entendue": ME.NOMS[int(np.argmax(cb))], "classes": [ME.NOMS[j] for j in np.argsort(-c)[:3]]})
        r["mesures"] = mes
        r["accord_moyen"] = round(float(np.mean([m["part_chroma_dans_l_accord"] for m in mes])), 2)
        rap, pts = ME.rapport_court(w)
        s7 = pts[(pts[:, 0] >= 43.5) & (pts[:, 0] <= 46.5), 2]
        s1 = pts[(pts[:, 0] >= 1.0) & (pts[:, 0] <= 4.2), 1]
        r["arc"] = {"S_max": rap["S_max_film"], "S_logo_max": round(float(s7.max()), 1),
                    "logo_moins_max_LU": round(float(s7.max() - rap["S_max_film"]["S"]), 1),
                    "M_sonnerie_max": round(float(s1.max()), 1)}
        r["tonalite_globale"] = ME.tonalite(ME.chroma(x))[:2]
        res[f"prise{k}"] = r
    # référence : la partition numpy, sur le même test
    x = labo.lire(R.STEMS_OUT / "musique.wav")
    mes = []
    for kk in range(1, 15):
        a, b = R.tb(4 * kk), min(R.tb(4 * kk + 4), 46.7)
        if kk == 11:
            b = R.T_RAC
        nom = R.accord_a((a + b) / 2)[1]
        c = ME.chroma(x, a, b)
        mes.append(round(float(sum(c[j] for j in NOTES_ACCORD[nom]) / c.sum()), 2))
    res["reference_numpy"] = {"accord_moyen": round(float(np.mean(mes)), 2), "grille": calage_grille(x)}
    (ICI / "el" / "evaluation.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for k, v in res.items():
        print(k, {a: b for a, b in v.items() if a != "mesures"})
    from PIL import Image
    ims = []
    for k in (3, 4):
        png = R.IMG / f"el-prise{k}.png"
        ME.spectro(ICI / "el" / f"prise{k}.wav", png, titre=f"EL prise {k} (plan harmonique imposé)", px_par_s=30, haut=300)
        ims.append(Image.open(png))
    ims.append(Image.open(ME.spectro(R.STEMS_OUT / "musique.wav", R.IMG / "ref-musique.png", titre="partition numpy (stem musique)",
                                     px_par_s=30, haut=300)))
    W = max(i.width for i in ims); H = sum(i.height + 8 for i in ims)
    o = Image.new("RGB", (W, H)); y = 0
    for i in ims:
        o.paste(i, (0, y)); y += i.height + 8
    o.save(R.IMG / "el-planche-2.png")


if __name__ == "__main__":
    main()
