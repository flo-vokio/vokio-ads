#!/usr/bin/env python3
"""Stems AMONT du showcase « Le point sur le i », recalculés EN MÉMOIRE sur le dialogue actuel (son/dialogue.json) par
les scripts validés (mix.py, riche-musique, riche-design), sans réécrire aucune de leurs sorties ni aucun livrable.

    python3 son/stems_amont.py                    variante iphone (données du point et vidéo de la version iPhone)
    python3 son/stems_amont.py --variante classique
    python3 son/stems_amont.py --force            recalcule même si les entrées n'ont pas changé

Sortie : son/stems-amont/<variante>/<stem>.wav (float 32 bits, 48 kHz, stéréo, 47,00 s) + stems-amont.json (empreinte des
entrées, provenance, mesures). Idempotent : si l'empreinte (sha256 des scripts, des données et du dialogue) n'a pas changé
et que tous les WAV sont là, rien n'est recalculé (≈ 0,5 s au lieu de plusieurs minutes).

ÉCHELLE COMMUNE : celle des stems du master validé, au gain de master de son/cues.json (7,84 dB), SANS limiteur. C'est
l'échelle d'entrée de riche-musique et de riche-design ; outils/mixer.py remasterise la somme (un gain, un limiteur).

LES STEMS
  dialogue   la voix réelle, chaîne voix de mix.py (−21 LUFS par extrait) : coupes dans le vrai blanc (son/dialogue.py)
  sfx        tonalité 1, souffle de la ligne (sonnerie), clic, touchers, vibreur, raccroché, stylo (mix.py, complet :
             c'est la recette qui retire le stylo sur « Vokıo » si la plume le remplace)
  signature  tonalité 2 → la ligne qui s'ouvre, cloches sol et la · sol, signature (mix.py)
  nappe      la nappe de verre (mix.py), ducking refait sur le nouveau dialogue
  musique    riche-musique.fabriquer() : lit + pouls, ducking lent, creux 1-4 kHz et rattrapages mot par mot refaits sur le
             NOUVEAU dialogue ; coupe au raccroché, fondu final ; UNE différence avec la version 2 (MUSIQUE ci-dessous,
             28/09) : au décroché, la quinte de la sonnerie sort en 0,35 s (rampe cosinus) au lieu de 40 ms, sous l'éveil du
             point et l'entrée du sol2 : la coupe de 40 ms laissait un trou de −27 dB en 30-300 Hz (4,225 s), la seule
             marche hors mots du mix hybride que le 3 n'a pas sur 0-15 s ; le cœur garde sa coupe de 40 ms
  ambiance, point, ecriture, objets
             les petits sons de riche-design, refaits sur le nouveau dialogue ; leurs marges de voix (rattrapage mot par
             mot) sont mesurées contre la MUSIQUE, comme dans le mix hybride ; variante iphone : trajectoire du point
             (air des trajets, pans) et encre de la plume lues dans les données et la vidéo iPhone. Le halo (côté
             décorrélé de la nappe de verre + souffle accordé sur ses accords) n'est pas refait : il n'existe que pour la
             nappe de verre, que la musique remplace.
  ligne      le fond de ligne (outils/fond_ligne.py), À L'ÉCHELLE DU DIALOGUE (gain 0 dans la recette), spectre mesuré sur
             deux passages de l'appelant porte ouverte sans voix (11,92-12,05 et 74,92-75,09 dans montes), 700-7 000 Hz :
             (a) un fond continu, RMS −66 dBFS, du décroché au raccroché (fondu d'entrée 250 ms, coupe de 5 ms au
             raccroché avec tout le reste) ; (b) + le BRUIT DE CONFORT de l'appelant (28/09) : au niveau MESURÉ de sa porte
             ouverte (dans 2-8 kHz, sur le stem dialogue, zones source hors gains de clip) moins 2 dB : nul pendant sa
             parole, il prend le relais quand sa porte VAD se ferme (fondu enchaîné de 10 ms) puis décroît en 0,35 s, au
             lieu de la chute de 30 ms de la porte (la « saute » de 14,03, fin de « hier »). Le gain de (b) se recalcule
             seul si le dialogue ou le fond changent.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True          # les .pyc de son/__pycache__ sont suivis par git : ne pas les réécrire
ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
OUTILS = PROJET / "outils"
for p in (ICI, ICI / "riche-musique", ICI / "riche-design", OUTILS):
    sys.path.insert(0, str(p))

SR = 48000
VARIANTES = {
    "classique": {"donnees": PROJET / "donnees", "video": Path("/root/vokio-uploads/videos/showcase/le-point-sur-le-i.mp4")},
    "iphone": {"donnees": Path("/opt/vokio-ads/videos/showcase-iphone/donnees"),
               "video": Path("/root/vokio-uploads/videos/showcase/le-point-sur-le-i-iphone.mp4")},
}
MONTES = Path("/root/vokio-audios-metiers-180926/montes/veterinaire.wav")
ZONES_LIGNE = [(11.92, 12.05), (74.92, 75.09)]     # appelant, porte ouverte sans voix (montes, s)
LIGNE = {"bande": (700.0, 7000.0), "rms_db": -66.0, "fondu_in": 0.25, "graine": 7,
         # bruit de confort de l'appelant : niveau apparié dans `apparier` sur sa porte ouverte, − ecart ; la porte s'ouvre
         # sur la parole (RMS 10 ms ≥ plancher + ouvre_db) et le reste tant que le fond tient (≥ plancher − sous_db), dans
         # ses tours ; relâche exponentielle (s)
         "confort": {"apparier": (2000.0, 8000.0), "ecart_db": -2.0, "ouvre_db": 10.0, "sous_db": 8.0, "relache": 0.35,
                     "remplace": True, "anticipation": 0.015, "fondu": 0.010}}
MUSIQUE = {"relache_quinte": 0.35}      # s (riche-musique.RELACHE_QUINTE ; 0,040 dans la version 2 livrée)
STEMS = ("dialogue", "sfx", "signature", "nappe", "musique", "ambiance", "point", "ecriture", "objets", "ligne")


def empreinte(variante):
    h = hashlib.sha256()
    fichiers = [ICI / "dialogue.json", ICI / "dialogue.wav", ICI / "mix.py", ICI / "signature.py", ICI / "labo.py",
                ICI / "cues.json", Path(__file__), OUTILS / "fond_ligne.py", OUTILS / "sonlib.py", MONTES]
    fichiers += sorted((ICI / "riche-musique").glob("*.py")) + sorted((ICI / "riche-design").glob("*.py"))
    fichiers += [ICI / "riche-design" / "prises.json"]
    fichiers += sorted(VARIANTES[variante]["donnees"].glob("*.json"))
    for f in fichiers:
        h.update(str(f.name).encode())
        h.update(f.read_bytes())
    h.update(json.dumps([ZONES_LIGNE, LIGNE, MUSIQUE, str(VARIANTES[variante]["video"])]).encode())
    return h.hexdigest()


def ecrire_f32(chemin, x):
    st = np.ascontiguousarray(np.asarray(x, dtype="<f4"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_f32le", str(chemin)], input=st.tobytes(), check=True)


def appliquer_variante(MX, RD, variante):
    """Les données du point (trajectoire, vitesse, taille) et la vidéo (encre de la plume) de la variante."""
    don = VARIANTES[variante]["donnees"]
    J = lambda n: json.loads((don / n).read_text())         # noqa: E731
    MX.PR = J("point-resolu.json")["images"]
    MX._T_IMG = np.array([p["t"] for p in MX.PR])
    MX._X_IMG = np.array([p["x_sans"] for p in MX.PR])
    MX._V_IMG = np.array([p["v"] for p in MX.PR])
    ev = J("evenements.json")
    diff = sorted(k for k in set(ev) | set(MX.EV) if ev.get(k) != MX.EV.get(k))
    MX.EV.clear(); MX.EV.update(ev)                        # même objet : RD.EV et les T des modules le voient
    pj = J("point.json")
    assert pj["taille"] == MX.POINTJ["taille"], "la taille du point diffère : T['pedale'] serait faux"
    MX.POINTJ = pj
    for k in ("scenes.json", "secousses.json", "mots.json"):
        assert (don / k).read_bytes() == (PROJET / "donnees" / k).read_bytes(), f"{k} diffère entre les variantes"
    RD.VIDEO = VARIANTES[variante]["video"]
    return diff


def fabriquer(variante):
    import mix as MX
    import stems_avant_limiteur as SAL
    import mix_riche_musique as RM
    import mix_riche_design as RD
    import fond_ligne as FL
    import sonlib as L
    diff_ev = appliquer_variante(MX, RD, variante)
    print(f"   variante {variante} : événements différents du classique : {diff_ev or 'aucun'}")
    G = json.loads((ICI / "cues.json").read_text())["gain_master_db"]
    t0 = time.time()
    print("1. base (mix.py) : dialogue, nappe, sfx, signature")
    base = {k: v * 10 ** (G / 20) for k, v in SAL.refaire().items()}
    print(f"   {time.time() - t0:.0f} s")
    print(f"2. musique (riche-musique.fabriquer, sur le nouveau dialogue ; quinte sortie en {MUSIQUE['relache_quinte']} s)")
    RM.RELACHE_QUINTE = MUSIQUE["relache_quinte"]
    R_ = RM.fabriquer({k: base[k] for k in ("dialogue", "sfx", "signature")}, couches=False)
    musique = R_["musique"]
    print(f"   {time.time() - t0:.0f} s ; rattrapages : {len(R_['journal_rat'])} mots, manques : {list(R_['manques']) or 'aucun'}")
    print("3. petits sons (riche-design), marges de voix contre la musique")
    sfx_sans_stylo = base["sfx"].copy()
    a_s, b_s = RD.STYLO_RETIRE
    sfx_sans_stylo[int(round(a_s * SR)):int(round(b_s * SR))] = 0.0
    st_d = {"dialogue": base["dialogue"], "nappe": musique, "sfx": sfx_sans_stylo, "signature": base["signature"]}
    duck = RD.voix_presente(st_d["dialogue"])
    coupe = RD.coupe_film()
    amb = RD.ambiance(duck)
    pt = RD.point(duck)
    pv = RD.presence_voix(duck)
    ecr = RD.hors_ligne_sous_voix(RD.ecriture(), pv)
    obj = RD.hors_ligne_sous_voix(RD.objets(st_d["sfx"]), pv)
    design = {"ambiance": amb, "point": pt, "ecriture": ecr, "objets": obj}
    for k in design:
        design[k] = design[k] * coupe[:, None]
    design, g_ratt, ratt, finale = RD.rattrapage(st_d, design)
    print(f"   {time.time() - t0:.0f} s ; rattrapage design : {len(ratt)} mots")
    print("4. fond de ligne (outils/fond_ligne.py)")
    src = L.lire(MONTES)
    S_ = FL.spectre_zones(src, ZONES_LIGNE)
    n = MX.N
    y = FL.fond(S_, n, graine=LIGNE["graine"], bande=LIGNE["bande"]) * L.gain(LIGNE["rms_db"])
    w_base = FL.fenetre(n, MX.T["decroche"], MX.T["raccroche"], fondu_in=LIGNE["fondu_in"])
    # (b) bruit de confort de l'appelant, apparié sur sa porte ouverte (film = source + décalage de l'extrait)
    C = LIGNE["confort"]
    dia = json.loads((ICI / "dialogue.json").read_text())["extraits"]
    zones_film = []
    for a_, b_ in ZONES_LIGNE:
        e = next((e for e in dia if e["source_in"] <= a_ and b_ <= e["source_out"]), None)
        gains = [g["src"] for g in (e or {}).get("gains", [])]
        if e and not any(g0 < b_ and a_ < g1 for g0, g1 in gains):     # pas une zone traitée par un gain de clip
            d = e["decalage_film_moins_source"]
            zones_film.append((round(a_ + d, 3), round(b_ + d, 3)))
    assert zones_film, "aucune zone de porte ouverte utilisable"
    plancher = FL.niveau_bande(base["dialogue"], zones_film, C["apparier"])
    fond_base = FL.niveau_bande(y[:, None] * np.ones((1, 2)), [(MX.T["decroche"] + 1.0, MX.T["raccroche"] - 0.5)], C["apparier"])
    g_conf = plancher + C["ecart_db"] - fond_base
    tours = [(e["film_in"], e["film_out"]) for e in dia if e["locuteur"] == "appelant"]
    pres = FL.presence_porte(base["dialogue"], tours, plancher, C["apparier"], C["sous_db"], C["ouvre_db"])
    coupe_rac = FL.fenetre(n, 0.0, MX.T["raccroche"], fondu_in=1e-6)
    env = np.maximum(w_base, FL.confort(pres, n, g_conf, C["relache"], remplace=C["remplace"],
                                        anticipation=C["anticipation"], fondu=C["fondu"]) * coupe_rac)
    y = y * env
    ligne = np.stack([y, y], axis=1)
    info_ligne = {"zones_film_porte_ouverte": zones_film, "plancher_porte_ouverte_db": round(plancher, 2),
                  "fond_base_db": round(fond_base, 2), "gain_confort_db": round(g_conf, 2),
                  "porte_ouverte_s": round(float(pres.sum()) / 1000, 3), "bande_apparier": C["apparier"]}
    print(f"   confort : porte ouverte {plancher:.1f} dB ({C['apparier'][0]:.0f}-{C['apparier'][1]:.0f} Hz, zones {zones_film}), "
          f"fond {fond_base:.1f} dB → gain {g_conf:+.1f} dB, porte ouverte {pres.sum() / 1000:.2f} s")
    s0, s1 = MX.EV["silence_numerique"]["t"]
    for k, v in list(design.items()) + [("ligne", ligne), ("musique", musique)] + list(base.items()):
        assert not np.any(v[int(round(s0 * SR)):int(round(s1 * SR))]), f"{k} : le silence du raccroché n'est pas nul"
    stems = {**base, "musique": musique, **design, "ligne": ligne}
    info = {"gain_master_valide_db": G, "variante": variante, "evenements_differents": diff_ev,
            "musique": {"rattrapages": len(R_["journal_rat"]), "manques": list(R_["manques"]), **MUSIQUE},
            "design": {"rattrapage": ratt, "marges_finales_min": {k: min(d[f"marge_{k}_design"] for d in finale)
                                                                   for k in ("bande", "K")}},
            "ligne": {"zones_source": ZONES_LIGNE, **LIGNE, **info_ligne}, "duree_calcul_s": round(time.time() - t0, 1)}
    return stems, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variante", choices=sorted(VARIANTES), default="iphone")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out = ICI / "stems-amont" / a.variante
    out.mkdir(parents=True, exist_ok=True)
    (ICI / "stems-amont" / ".gitignore").write_text("*.wav\n")
    emp = empreinte(a.variante)
    meta_f = out / "stems-amont.json"
    if not a.force and meta_f.exists():
        m = json.loads(meta_f.read_text())
        if m.get("empreinte") == emp and all((out / f"{k}.wav").exists() for k in STEMS):
            print(f"à jour (empreinte {emp[:12]}) : {out}")
            return
    stems, info = fabriquer(a.variante)
    import sonlib as L
    mesures = {}
    for k in STEMS:
        v = stems[k]
        ecrire_f32(out / f"{k}.wav", v)
        mesures[k] = {"crete_dbfs": round(float(L.db(np.abs(v).max())), 2) if np.any(v) else None,
                      "lufs": L.mesure(v)["I"] if np.any(v) else None}
        print(f"   {k:10s} crête {mesures[k]['crete_dbfs']} dBFS, {mesures[k]['lufs']} LUFS")
    meta = {"empreinte": emp, "echelle": "stems du master validé, gain de master compris, sans limiteur",
            "sr": SR, "format": "pcm_f32le stéréo", "stems": {k: str(out / f"{k}.wav") for k in STEMS},
            "mesures": mesures, **info}
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=float))
    print(f"→ {out}")


if __name__ == "__main__":
    main()
