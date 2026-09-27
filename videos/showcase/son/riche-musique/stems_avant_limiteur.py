#!/usr/bin/env python3
"""Stems du master validé AVANT son limiteur (27/09, relecture de la variante « musique », défaut 4).

    python3 son/riche-musique/stems_avant_limiteur.py

Pourquoi : son/stems/*.wav contiennent le gain du master ET la courbe de SON limiteur (mix.py : st × G × g_lim). Les
remasteriser avec la musique limitait deux fois les attaques de la signature (le sol et le ré sortaient 0,5 à 1 dB plus
bas que dans le master validé). Ce script refait, EN MÉMOIRE, les étapes 1 à 4 de mix.main() (dialogue, nappe, sfx,
signature, raccroché, silences), sans rien écrire dans son/ ; il remasterise la somme pour retrouver G et g_lim, VÉRIFIE
que st × G × g_lim redonne son/stems/*.wav (écart ≤ 2e-6, soit la quantification 24 bits), puis écrit dans
son/riche-musique/stems-avant-limiteur/ :
    dialogue.npy  sfx.npy  signature.npy  nappe.npy     st × G (gain du master validé, SANS sa courbe de limiteur)
    g_lim_valide.npy                                     la courbe du limiteur du master validé (pour les comparaisons)
    info.json                                            G, réduction max, écarts de reconstruction
Ne touche ni son/mix.wav, ni son/stems/, ni assets/son/mix.wav.
"""
import json
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
SON = ICI.parent
sys.path.insert(0, str(SON))
import labo  # noqa: E402
import signature as S  # noqa: E402
import mix as MX  # noqa: E402

SR = labo.SR
N = MX.N
SORTIE = ICI / "stems-avant-limiteur"


def refaire():
    dlg, _ = MX.dialogue()
    duck = MX.gain_ducking(dlg[:, 0])
    nap, _ = MX.nappe(duck)
    sfx, sig = np.zeros((N, 2)), np.zeros((N, 2))
    sfx, sig = MX.avant_la_coupe(sfx, sig)
    T, EV = MX.T, MX.EV
    s0, s1_ = EV["silence_numerique"]["t"]
    i_rac, i_s0, i_s1 = int(round(T["raccroche"] * SR)), int(round(s0 * SR)), int(round(s1_ * SR))
    coupe = np.ones(N)
    k = int(0.005 * SR)
    coupe[i_rac:i_rac + k] = S.rampe_cos(k)[::-1]
    coupe[i_rac + k:] = 0
    for st in (dlg, nap, sfx, sig):
        st *= coupe[:, None]
    rac = MX.raccroche() * S.gain(MX.NIV["raccroche"])
    sfx[i_rac:i_rac + len(rac)] += rac[:, None]
    sfx, sig, nap = MX.apres_la_coupe(sfx, sig, nap)
    fin = int(round(MX.FIN_SON * SR))
    for st in (dlg, nap, sfx, sig):
        st[fin:] = 0
    return {"dialogue": dlg, "nappe": nap, "sfx": sfx, "signature": sig}


def main():
    SORTIE.mkdir(exist_ok=True)
    st = refaire()
    somme = sum(st.values())
    _, G, g_lim, red = MX.masteriser(somme)
    info = {"gain_master_db": G, "reduction_limiteur_max_db": red, "ecart_max_contre_son_stems": {}}
    for k, v in st.items():
        fin = v * S.gain(G) * g_lim[:, None]
        ref = labo.lire(SON / "stems" / f"{k}.wav")
        e = float(np.max(np.abs(fin - ref)))
        info["ecart_max_contre_son_stems"][k] = e
        assert e < 2e-6, (k, e)
        np.save(SORTIE / f"{k}.npy", (v * S.gain(G)).astype(np.float64))
    np.save(SORTIE / "g_lim_valide.npy", g_lim)
    (SORTIE / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
