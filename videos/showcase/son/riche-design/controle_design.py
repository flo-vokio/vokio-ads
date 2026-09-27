#!/usr/bin/env python3
"""Contrôles de la variante « SOUND DESIGN » (écoute impossible ici : tout se prouve par la mesure, contre le master).

    python3 son/riche-design/controle_design.py        → son/riche-design/mesures-design.json + planches PNG (scratchpad)

  A. livraison : −14 LUFS intégrés (± 0,3) et crête vraie ≤ −1 dBTP, sur le WAV ET sur la piste AAC du MP4 ; durée 47,00 s ;
     la vidéo du MP4 est OCTET POUR OCTET celle du film (md5 du flux vidéo)
  B. les deux moments forts, 1 : zéros numériques sur [35,9467 ; 36,6667] et [46,70 ; 47,00], sur le mix et chaque couche
  C. somme des stems = mix
  F. la voix, par mot, deux garanties (celles du rattrapage, D.CIBLES) : MASQUAGE dans la bande réelle de la voix
     (100-3 800 Hz : la voix VoIP descend à 100 Hz) ≥ max(10, min(master − 1, 16)) dB ; PRÉSENCE en sonie K
     ≥ max(10, min(master − 2, 16)) LU ; et jamais plus de 0,2 sous le master (un mot que le master laisse sous 10,2)
  G. mono : écart de sonie mono − stéréo (film et sections) ; corrélation G/D par 100 ms (aucune fenêtre négative)
  M. les deux moments forts, 2 (ebur128 court terme sur tout le film) : la signature [ré ; ré + 1,5] ≥ médiane S du
     dialogue + 1 LU, le ré reste l'instant le plus fort (sonie instantanée), et l'écart signature − médiane du
     dialogue n'est pas plus petit que dans le master (− 0,2 LU) ; ET en mono ET sur un haut-parleur de téléphone simulé
     (mono, 400 Hz-12 kHz) : le ré reste l'instant le plus fort, et l'écart signature − médiane ne perd pas plus de 0,2 LU
     sur le master (2e revue 27/09 : les anciens seuils « gagner 0,1 LU » et « couches ajoutées à moins de 12 dB sous le
     master pendant la signature » récompensaient ce qui couvre la marque ; ils sont remplacés par H)
  H. le halo reste une ombre de la nappe (milieu, tiers d'octave, fenêtres de 0,5 s) : ≤ (nappe + signature) − 6 dB de 1 à
     8 kHz, du la à la fin du son et sur la lecture du SMS ; ≤ signature − 10 dB dans le tiers d'octave du scintillement ;
     après le silence, ≥ 6 dB sous la nappe (il ne rapporte pas l'accord de l'appel)
  S. synchro : attaque de chaque bruitage ponctuel contre son instant (±5 ms), mesurée sur sa couche seule
  L. le pan suit le point (air des trajets, plume) : D − G mesuré contre la loi du pan
  N. niveaux : sonie instantanée maximale de chaque élément, seul, dans le mix final (contre NIV)
  X. rien ne s'annule : la sonie instantanée de la variante n'est nulle part sous celle du master (au gain de master près)
  V. la ligne : pendant l'appel, l'air des trajets met ≤ 20 % de son énergie dans la bande de la ligne (300-4 000 Hz),
     trajet par trajet ; et tout ce qui est ajouté pendant que la voix parle aussi (objets, écriture : ≤ 20 %)
  E. l'écriture suit l'image, sur CE QUI S'ENTEND (plume + ce qui reste du stem sfx) : corrélation de l'enveloppe 10 ms
     (dB) avec le pilote (vitesse × encre révélée, lu dans la vidéo) ≥ 0,7 sur les deux écritures (après la goutte de la
     pose), et articulation p90 − p10 de l'enveloppe 3-8 kHz ≥ 18 dB (un seul stylo : la plume remplace celui du master)
  Q. les gestes du titre s'entendent pour la cible (45-50 ans, téléphone à volume normal : 0 dBFS = 80 dB SPL, seuil de
     Terhardt + presbyacousie, +20 dB dès 8 kHz) : l'envol de chaque saut émerge de ≥ 6 dB du reste du mix dans un tiers
     d'octave de 4 à 16 kHz, ≥ 10 dB au-dessus du seuil ; l'assise sur le ı, pareil sur un haut-parleur simulé (1-12 kHz)
  O. un seul oiseau, lointain : sonie instantanée ≤ celle du master sur le blanc − 3 dB
  P. la pièce, pas la ligne : aucune raie du secteur (k·50 Hz, 150 Hz-3 kHz) à plus de 12 dB au-dessus du bruit voisin
  T. le téléphone : une seule matière (un seul son, la sortie), ≤ −38 LUFS instantanés, pas d'étincelle ; la bulle : aucun
     son propre (l'arrivée du SMS, c'est le vibreur)
  Z. le limiteur ne mord pas (≤ 0,1 dB)
Planches : spectrogrammes du master et de la variante (film entier et zooms), des couches ajoutées seules, et l'arc de
sonie (M et S) des deux, superposés.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
SON = ICI.parent
sys.dont_write_bytecode = True        # les .pyc de son/__pycache__ sont suivis par git : ne pas les réécrire
sys.path.insert(0, str(SON))
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402
import mix as MX  # noqa: E402
import controle_son as CS  # noqa: E402
import mix_riche_design as D  # noqa: E402

SR = labo.SR
EV, T, DUREE, FIN_SON = MX.EV, MX.T, MX.DUREE, MX.FIN_SON
IMG = Path("/tmp/claude-0/-root/5cdc3174-18c1-52f2-a7e6-50c04cd57657/scratchpad/variantes/son-design")
f_ = lambda a, b: f"{a:.2f} → {b:.2f}".replace(".", ",")  # noqa: E731


def md5_video(p):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-map", "0:v", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def sonie(xk, a, b):
    return CS.sonie(xk, int(round(a * SR)), int(round(b * SR)))


def main():
    R = {}
    mixp = ICI / "mix-design.wav"
    mix = labo.lire(mixp)
    master = labo.lire(SON / "mix.wav")
    N = len(mix)
    noms = D.BASE + D.COUCHES
    st = {n: labo.lire(ICI / "stems" / f"{n}.wav") for n in noms}
    ajout = sum(st[n] for n in D.COUCHES)
    CU = json.loads((ICI / "cues-design.json").read_text())
    # A. livraison
    IMG.mkdir(parents=True, exist_ok=True)
    m4a = IMG / "piste-mp4.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(D.SORTIE_MP4), "-map", "0:a", "-ar", "48000", str(m4a)], check=True)
    lw, courbe = CS.ebur128(mixp)
    lm, _ = CS.ebur128(m4a)
    lmaster, courbe_master = CS.ebur128(SON / "mix.wav")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(D.SORTIE_MP4)],
                               capture_output=True, text=True).stdout)
    A = {"wav": {"loudnorm": labo.mesurer(mixp), "ebur128": lw, "crete_vraie_numpy_dbtp": round(S.crete_vraie(mix), 2)},
         "mp4_aac": {"loudnorm": labo.mesurer(m4a), "ebur128": lm}, "master_ebur128": lmaster,
         "duree_wav_s": N / SR, "duree_mp4_s": dur,
         "md5_video_film": md5_video(D.VIDEO), "md5_video_variante": md5_video(D.SORTIE_MP4)}
    A["video_identique"] = A["md5_video_film"] == A["md5_video_variante"]
    A["ok"] = bool(abs(A["wav"]["loudnorm"]["lufs"] + 14) <= 0.3 and A["wav"]["loudnorm"]["crete_dbtp"] <= -1.0
                   and abs(A["mp4_aac"]["loudnorm"]["lufs"] + 14) <= 0.3 and A["mp4_aac"]["loudnorm"]["crete_dbtp"] <= -1.0
                   and A["mp4_aac"]["ebur128"]["TP"] <= -1.0 and abs(A["duree_wav_s"] - DUREE) < 1e-9 and A["video_identique"])
    R["A_livraison"] = A
    # B. silences
    s0, s1 = EV["silence_numerique"]["t"]
    f0 = EV["silence_final"]["t"][0]
    z = lambda x, a, b: bool(not np.any(x[int(round(a * SR)):int(round(b * SR))]))  # noqa: E731
    B = {"mix_silence_numerique": z(mix, s0, s1), "mix_silence_final": z(mix, f0, DUREE),
         "couches_silence_numerique": {n: z(st[n], s0, s1) for n in noms}, "couches_silence_final": {n: z(st[n], f0, DUREE) for n in noms},
         "premier_echantillon_non_nul_apres_le_silence_s": round(float(np.nonzero(np.any(mix[int(round(s1 * SR)) - 5:] != 0, axis=1))[0][0]
                                                                         + int(round(s1 * SR)) - 5) / SR, 6)}
    B["ok"] = bool(B["mix_silence_numerique"] and B["mix_silence_final"] and all(B["couches_silence_numerique"].values())
                   and all(B["couches_silence_final"].values()))
    R["B_silences"] = B
    # C. somme
    R["C_somme_stems_moins_mix_max"] = float(np.max(np.abs(sum(st.values()) - mix)))
    # F. la voix
    mstems = {n: labo.lire(SON / "stems" / f"{n}.wav") for n in D.BASE}
    reste_design = sum(st[n] for n in noms if n != "dialogue")
    reste_master = mstems["nappe"] + mstems["sfx"] + mstems["signature"]
    esp = {"K": MX.ponderer_k, "bande": D.bande_voix}
    Fm = {}
    for k, f in esp.items():
        dv, rd = f(st["dialogue"]), f(reste_design)
        dvm, rm = f(mstems["dialogue"]), f(reste_master)
        Fm[k] = [(sonie(dv, max(0, w["debut"]), max(w["fin"], w["debut"] + 0.12)) - sonie(rd, w["debut"], max(w["fin"], w["debut"] + 0.12)),
                  sonie(dvm, w["debut"], max(w["fin"], w["debut"] + 0.12)) - sonie(rm, w["debut"], max(w["fin"], w["debut"] + 0.12)))
                 for w in MX.MOTS["mots"]]
    Fl = []
    for j, w in enumerate(MX.MOTS["mots"]):
        d = {"mot": w["texte"], "debut": w["debut"]}
        for k in esp:
            md, mm = Fm[k][j]
            d.update({f"{k}_design": round(float(md), 1), f"{k}_master": round(float(mm), 1), f"{k}_perte": round(float(mm - md), 1),
                      f"{k}_cible": round(D.CIBLES[k](mm), 1)})
        d["ok"] = bool(all(d[f"{k}_design"] >= d[f"{k}_cible"] - 0.05 for k in esp))
        Fl.append(d)
    viol = [d for d in Fl if not d["ok"]]
    R["F_voix"] = {"bande_min_db": min(d["bande_design"] for d in Fl), "K_min_LU": min(d["K_design"] for d in Fl),
                   "bande_mediane": float(np.median([d["bande_design"] for d in Fl])),
                   "bande_mediane_master": float(np.median([d["bande_master"] for d in Fl])),
                   "K_mediane": float(np.median([d["K_design"] for d in Fl])), "K_mediane_master": float(np.median([d["K_master"] for d in Fl])),
                   "bande_perte_max_db": max(d["bande_perte"] for d in Fl), "K_perte_max_LU": max(d["K_perte"] for d in Fl),
                   "pires_bande": sorted(Fl, key=lambda d: d["bande_design"])[:6], "pires_K": sorted(Fl, key=lambda d: d["K_design"])[:6],
                   "plus_grosses_pertes_K": sorted(Fl, key=lambda d: -d["K_perte"])[:6],
                   "violations": viol, "ok": not viol}
    # G. mono
    mono = (mix[:, 0] + mix[:, 1]) / 2
    mk = MX.ponderer_k(mix); m2k = MX.ponderer_k(np.stack([mono, mono], axis=1))
    monom = (master[:, 0] + master[:, 1]) / 2
    mkm = MX.ponderer_k(master); m2km = MX.ponderer_k(np.stack([monom, monom], axis=1))
    sections = {"film": (0, DUREE), "sonnerie 0 → 4,2": (0, 4.2), "appel 4,9 → 35,5": (4.9, 35.5), "tension 20,6 → 32,9": (20.6, 32.9),
                "SMS 36,7 → 41,4": (36.7, 41.4), "écriture de Vokıo 41,5 → 42,2": (41.5, 42.2),
                "signature 42,3 → 45,3": (T["la"], T["la"] + 3.0), "fin 43,9 → 46,7": (43.9, 46.7)}
    G = {"ecart_mono_moins_stereo_LU": {k: {"design": round(sonie(m2k, a, b) - sonie(mk, a, b), 2),
                                             "master": round(sonie(m2km, a, b) - sonie(mkm, a, b), 2)} for k, (a, b) in sections.items()}}
    w = 4800
    nb = N // w
    def corr(x):
        Lc, Rc = x[:nb * w, 0].reshape(nb, w), x[:nb * w, 1].reshape(nb, w)
        e = np.sqrt(np.mean(Lc ** 2, 1) * np.mean(Rc ** 2, 1))
        ok = e > 10 ** (-60 / 10)
        c = np.mean(Lc * Rc, 1)[ok] / e[ok]
        return c, np.nonzero(ok)[0]
    c, idx = corr(mix)
    cm, _ = corr(master)
    G["correlation_min_100ms"] = round(float(c.min()), 3)
    G["correlation_min_a_s"] = round(float(idx[np.argmin(c)] * w / SR), 1)
    G["correlation_mediane"] = round(float(np.median(c)), 3)
    G["correlation_mediane_master"] = round(float(np.median(cm)), 3)
    G["fenetres_negatives"] = int(np.sum(c < 0))
    G["couches_ajoutees_perte_mono_db"] = {n: round(float(10 * np.log10(np.mean(((st[n][:, 0] + st[n][:, 1]) / 2) ** 2) /
                                                                          (np.mean(st[n] ** 2) + 1e-20) + 1e-20)), 2) for n in D.COUCHES}
    G["ok"] = bool(G["fenetres_negatives"] == 0 and abs(G["ecart_mono_moins_stereo_LU"]["film"]["design"]) <= 1.0
                   and all(abs(v["design"]) <= 2.0 for v in G["ecart_mono_moins_stereo_LU"].values()))
    R["G_mono"] = G
    # M. arc (ebur128 court terme)
    def arc(cb):
        ct = np.array(cb, dtype=float)
        ct[~np.isfinite(ct)] = -120.0
        tS, Ms, Ss = ct[:, 0], ct[:, 1], ct[:, 2]
        dlg = (tS >= 5.0) & (tS <= 35.4)
        med = float(np.median(Ss[dlg]))
        sig = (tS >= T["re"] + 0.4) & (tS <= T["re"] + 1.9)
        return {"mediane_S_dialogue": round(med, 2), "S_max_signature": round(float(Ss[sig].max()), 2),
                "signature_moins_mediane_LU": round(float(Ss[sig].max()) - med, 2),
                "M_max": [round(float(Ms.max()), 2), round(float(tS[np.argmax(Ms)]), 1)],
                "S_max": [round(float(Ss.max()), 2), round(float(tS[np.argmax(Ss)]), 1)],
                "S_par_seconde": {str(s): round(float(Ss[np.argmin(np.abs(tS - s))]), 1) for s in range(3, 48)}}
    Md, Mm = arc(courbe), arc(courbe_master)
    tm, lm_ = CS.instantanee(mk)
    i_max = int(np.argmax(lm_))
    tmm, lmm = CS.instantanee(mkm)
    M = {"design": Md, "master": Mm, "instantanee_max_design": [round(float(lm_[i_max]), 2), round(float(tm[i_max]), 2)],
         "instantanee_max_master": [round(float(lmm.max()), 2), round(float(tmm[np.argmax(lmm)]), 2)]}
    ok_st = bool(Md["signature_moins_mediane_LU"] >= 1.0 and Md["signature_moins_mediane_LU"] >= Mm["signature_moins_mediane_LU"] - 0.2
                 and T["re"] <= tm[i_max] <= T["re"] + 1.5)
    # en mono et sur un haut-parleur de téléphone simulé (mono, 400 Hz-12 kHz) : là où se regardent Reels et TikTok
    base_m = sum(mstems.values())
    ajout_ = ajout

    def ecoute(x, mode):
        m_ = x.mean(axis=1)
        if mode == "hp":
            m_ = S.passe_bande(m_, 400, 12000, front=200)
        return np.stack([m_, m_], axis=1)

    def arc_np(x):
        k = MX.ponderer_k(x); pw = np.sum(k ** 2, axis=1); c = np.concatenate([[0], np.cumsum(pw)])
        w3, w4, hop = 3 * SR, int(0.4 * SR), SR // 100
        t3 = np.arange(w3, len(pw), hop); s3 = -0.691 + 10 * np.log10((c[t3] - c[t3 - w3]) / w3 + 1e-20)
        t4 = np.arange(w4, len(pw), hop); s4 = -0.691 + 10 * np.log10((c[t4] - c[t4 - w4]) / w4 + 1e-20)
        t3 = t3 / SR; t4 = t4 / SR
        dlg = (t3 >= 5.0) & (t3 <= 35.4); sig = (t3 >= T["re"] + 0.4) & (t3 <= T["re"] + 1.9)
        d4 = (t4 >= 4.2) & (t4 <= 35.9); g4 = (t4 >= T["re"]) & (t4 <= FIN_SON)
        return {"mediane_S_dialogue": round(float(np.median(s3[dlg])), 2), "S_max_dialogue": round(float(s3[dlg].max()), 2),
                "S_max_signature": round(float(s3[sig].max()), 2),
                "signature_moins_mediane_LU": round(float(s3[sig].max() - np.median(s3[dlg])), 2),
                "M_max_signature_moins_M_max_appel": round(float(s4[g4].max() - s4[d4].max()), 2),
                "M_max_a_s": round(float(t4[np.argmax(s4)]), 2)}
    for mode in ("mono", "hp"):
        a_d, a_m = arc_np(ecoute(mix, mode)), arc_np(ecoute(master, mode))
        i0_, i1_ = int(T["re"] * SR), int(FIN_SON * SR)
        e_aj = float(np.mean(ecoute(ajout_, mode)[i0_:i1_, 0] ** 2)); e_ms = float(np.mean(ecoute(base_m, mode)[i0_:i1_, 0] ** 2))
        M[mode] = {"design": a_d, "master": a_m,
                   "gain_arc_LU": round(a_d["signature_moins_mediane_LU"] - a_m["signature_moins_mediane_LU"], 2),
                   "couches_ajoutees_sous_master_signature_db": round(10 * np.log10(e_aj / e_ms), 1)}
        # (2e revue 27/09 : le seuil « couches ajoutées ≥ −12 dB sous le master pendant la signature » récompensait ce qui
        # couvre la marque ; il est remplacé par les plafonds du halo, contrôle H ; le chiffre reste rapporté)
        # (et l'écart signature − médiane ne doit plus « gagner » 0,1 LU sur le master : exiger que la variante soit plus
        # forte à la signature, c'est ce qui avait fait monter le halo sur la marque ; il ne doit pas y perdre, ≥ −0,2 LU,
        # le critère du stéréo)
        M[mode]["ok"] = bool(a_d["M_max_signature_moins_M_max_appel"] > 0 and T["re"] <= a_d["M_max_a_s"] <= T["re"] + 1.5
                             and M[mode]["gain_arc_LU"] >= -0.2)
    M["ok"] = bool(ok_st and M["mono"]["ok"] and M["hp"]["ok"])
    R["M_arc"] = M
    # S. synchro (attaque mesurée sur la couche seule)
    Sy = []
    for c_ in CU["cues"]:
        if c_["id"] in ("naissance", "envol-neuf", "envol-dix", "envol-onze", "envol-retour", "assise-i", "pose-plume-rendez-vous",
                        "pose-plume-vokio", "vibreur-bois"):
            t_mes, montee = CS.attaque(st[c_["couche"]], c_["t"])
            Sy.append({"id": c_["id"], "t": c_["t"], "attaque_mesuree": round(t_mes, 4), "ecart_ms": round(1000 * (t_mes - c_["t"]), 1),
                       "montee_db": round(montee, 1), "ok": bool(abs(t_mes - c_["t"]) <= 0.005)})
    R["S_synchro"] = {"cues": Sy, "ok": all(s["ok"] for s in Sy)}
    # L. pan
    Lp = []
    def dg(x, a, b):
        s = x[int(a * SR):int(b * SR)]
        return 10 * np.log10((np.mean(s[:, 1] ** 2) + 1e-20) / (np.mean(s[:, 0] ** 2) + 1e-20))
    for nom, couche, (a, b) in (("air, suiveur 4,70", "point", (4.70, 4.90)), ("air, vers l'agenda", "point", (17.35, 17.6)),
                                ("air, vers 11 h", "point", (22.05, 22.18)), ("air, vers le téléphone", "point", (34.0, 34.4)),
                                ("air, saut vers le ı", "point", (42.32, 42.46)),
                                ("plume, début du rendez-vous", "ecriture", (25.42, 25.55)),
                                ("plume, fin du rendez-vous", "ecriture", (25.95, 26.08)),
                                ("plume, V de Vokıo", "ecriture", (41.55, 41.7)), ("plume, o de Vokıo", "ecriture", (42.0, 42.15))):
        tt = np.arange(int(a * SR), int(b * SR)) / SR
        p = MX.pan_point(tt)
        ang = (p + 1) * np.pi / 4
        att = 10 * np.log10(np.mean(np.sin(ang) ** 2) / np.mean(np.cos(ang) ** 2))
        Lp.append({"fenetre": nom, "x_point": round(float(MX.x_point((a + b) / 2)), 1), "D_moins_G_attendu_db": round(float(att), 2),
                   "D_moins_G_mesure_db": round(float(dg(st[couche], a, b)), 2)})
    R["L_pan"] = {"fenetres": Lp, "ok": all(abs(l["D_moins_G_attendu_db"] - l["D_moins_G_mesure_db"]) <= 2.0 for l in Lp)}
    # N. niveaux (seul, dans le mix final)
    Nv = {}
    for c_ in CU["cues"]:
        a = c_["t"]
        b = c_.get("fin", a + 0.6)
        if c_["couche"] in D.COUCHES and isinstance(b, (int, float)) and c_["id"] not in ("air-trajets", "fond-piece", "souffle-accorde",
                                                                                           "nappe-s-elargit"):
            seg = st[c_["couche"]][max(0, int((a - 0.02) * SR)):int((b + 0.25) * SR)]
            avec = [o["id"] for o in CU["cues"] if o["couche"] == c_["couche"] and o["id"] != c_["id"]
                    and o["id"] not in ("fond-piece", "souffle-accorde", "nappe-s-elargit", "air-trajets")
                    and o["t"] < b + 0.25 and o.get("fin", o["t"] + 0.6) > a - 0.02]
            Nv[c_["id"]] = {"t": a, "instantanee_max_lufs": round(D.momentanee_max(seg), 1), "voulu": c_["niveau"],
                            **({"mesure_avec": avec} if avec else {})}
    Nv["fond-piece (court terme, blanc 1,6 → 2,6)"] = round(D.court_terme(st["ambiance"], 1.6, 2.6), 1)
    Nv["fond-piece (court terme, SMS 38,0 → 41,0)"] = round(D.court_terme(st["ambiance"], 38.0, 41.0), 1)
    Nv["fond-piece (court terme sous la voix, 12,5 → 13,9)"] = round(D.court_terme(st["ambiance"], 12.5, 13.9), 1)
    t_ret = MX.SEC["s6"]["segments_s"][-1][1]
    Nv["fond-piece (court terme, pièce qui se rouvre 37,12 → 38,12)"] = round(D.court_terme(st["ambiance"], t_ret, t_ret + 1.0), 1)
    Nv["master (court terme, lecture du SMS 38,0 → 41,0)"] = round(D.court_terme(master, 38.0, 41.0), 1)
    Nv["halo (court terme, 12,5 → 17,5)"] = round(D.court_terme(st["halo"], 12.5, 17.5), 1)
    Nv["halo (court terme, SMS 37,6 → 42,2)"] = round(D.court_terme(st["halo"], 37.6, 42.2), 1)
    Nv["halo (court terme, fin 43,9 → 45,0)"] = round(D.court_terme(st["halo"], 43.9, 45.0), 1)
    Nv["couches ajoutées, sonie intégrée seules (film)"] = labo.mesurer(IMG / "ajout.wav") if S.ecrire24(IMG / "ajout.wav", ajout) else None
    R["N_niveaux"] = Nv
    # X. rien ne s'annule : sonie instantanée (400 ms, pas de 10 ms) de la variante contre le master, partout où le master
    #    sonne (> −60 LUFS) ; les couches ajoutées ne doivent jamais faire baisser le mix (interférences, phase), au gain
    #    de master près
    tm2, l_d = CS.instantanee(mk)
    _, l_m = CS.instantanee(mkm)
    g_sup = CU["gain_supplementaire_db"]
    actif = l_m > -60
    ec = (l_d - l_m)[actif]
    i_pire = int(np.argmin(ec))
    R["X_rien_ne_s_annule"] = {"ecart_min_LU": round(float(ec.min()), 2), "a_s": round(float(tm2[actif][i_pire]), 2),
                               "gain_de_master_db": g_sup, "part_des_fenetres_sous_master_moins_0.3": round(float(np.mean(ec < g_sup - 0.3)), 4),
                               "ok": bool(ec.min() >= g_sup - 0.3)}
    # V. la ligne
    def part_bande(x, a, b, lo, hi):
        seg = x[int(a * SR):int(b * SR)].mean(axis=1)
        X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2; f = np.fft.rfftfreq(len(seg), 1 / SR)
        return float(X[(f >= lo) & (f < hi)].sum() / (X.sum() + 1e-30))
    p_ap = D.appel()
    duck = D.voix_presente(mstems["dialogue"])
    pv = D.presence_voix(duck)
    contacts = [EV[k]["t"] for k in ("contact_neuf", "contact_dix", "contact_onze", "contact_retour_neuf")]
    Vt = []
    for a, b in D.SEGMENTS_V:
        b2 = b + 0.10
        if np.mean(p_ap[int(a * SR):int(b2 * SR)]) < 0.5:
            continue
        # ici l'air seul (les envols, 4,5-9 kHz, sont mesurés par Q) : on ôte les instants des contacts, comme avant
        segs = [(a, b2)]
        for c in contacts:
            segs = [(x0, x1) for (u0, u1) in segs for (x0, x1) in ((u0, min(u1, c - 0.03)), (max(u0, c + 0.25), u1)) if x1 - x0 > 0.04]
        for x0, x1 in segs:
            lv = sonie(MX.ponderer_k(st["point"][int(x0 * SR) - 1:int(x1 * SR) + 1]), 0, (int(x1 * SR) - int(x0 * SR)) / SR)
            if lv < -70:
                continue
            Vt.append({"de": round(x0, 3), "a": round(x1, 3), "sonie_point": round(lv, 1),
                       "voix_presente": round(float(np.mean(pv[int(x0 * SR):int(x1 * SR)])), 2),
                       "part_ligne": round(part_bande(st["point"], x0, x1, *D.LIGNE), 3)})
    Vo = []
    for n in ("objets", "ecriture", "ambiance"):
        x = st[n] * pv[:, None]
        e = np.mean(x ** 2, axis=1)
        if e.max() <= 0:
            continue
        on = np.nonzero(e > e.max() * 1e-4)[0]
        if len(on):
            Vo.append({"couche": n, "part_ligne_sous_la_voix": round(part_bande(x, 0, DUREE, *D.LIGNE), 3),
                       "sonie_sous_la_voix": round(D.court_terme(x, 0, DUREE), 1)})
    R["V_ligne"] = {"air_trajets_pendant_l_appel": Vt, "sous_la_voix": Vo,
                    "ok": bool(all(v["part_ligne"] <= 0.20 for v in Vt)
                               and all(v["part_ligne_sous_la_voix"] <= 0.20 for v in Vo if v["couche"] != "ambiance"))}
    # E. l'écriture suit l'image
    Ee = {}
    xp = labo.lire(ICI / "prises" / f"plume-prise{CU['choix_des_prises']['plume']['retenue']}.wav").mean(axis=1)
    def env10(sig):
        k = int(0.01 * SR); n = len(sig) // k
        return 10 * np.log10(np.mean(sig[:n * k].reshape(n, k) ** 2, axis=1) + 1e-20)
    for nom, E in D.ECRITS.items():
        p0, p1 = E["t"]
        p0 += 0.06                                            # après la goutte de la pose (un événement à part)
        i0 = int(round(p0 * SR)); n = int(round((p1 - p0) * SR))
        t = (i0 + np.arange(n)) / SR
        pil, info = D.pilote_ecriture(nom, t)
        ce_qui_s_entend = (st["ecriture"] + st["sfx"])[i0:i0 + n].mean(axis=1)      # la plume ET ce qui reste du master
        es = env10(ce_qui_s_entend); ep = env10(pil + 1e-4)
        e38 = env10(S.passe_bande(np.concatenate([ce_qui_s_entend, np.zeros(8192)]), 3000, 8000, front=100)[:n])
        e38p = env10(S.passe_bande(np.concatenate([st["ecriture"][i0:i0 + n].mean(axis=1), np.zeros(8192)]), 3000, 8000, front=100)[:n])
        et = env10(xp[int(E["decal"] * SR):int(E["decal"] * SR) + n]) if len(xp) > int(E["decal"] * SR) + n else ep * 0
        v = MX.v_point(t); ev = env10(v / v.max() + 1e-4)
        L = min(len(es), len(ep), len(et), len(ev))
        c = lambda u: round(float(np.corrcoef(es[:L], u[:L])[0, 1]), 2)  # noqa: E731
        Ee[nom] = {"corr_pilote": c(ep), "corr_vitesse_seule": c(ev), "corr_prise_brute": c(et),
                   "articulation_p90_moins_p10_3_8k_db": round(float(np.percentile(e38, 90) - np.percentile(e38, 10)), 1),
                   "articulation_plume_seule_db": round(float(np.percentile(e38p, 90) - np.percentile(e38p, 10)), 1),
                   "sfx_sur_le_geste_dbfs": round(float(10 * np.log10(np.mean(st["sfx"][i0:i0 + n] ** 2) + 1e-30)), 1), **info}
    gt = [c_["transitoire_max_db"] for c_ in CU["choix_des_prises"]["plume"]["candidats"] if c_["prise"] == CU["choix_des_prises"]["plume"]["retenue"]][0]
    R["E_ecriture"] = {**Ee, "grain_transitoire_max_db": gt,
                       "ok": bool(all(e["corr_pilote"] >= 0.7 and e["articulation_p90_moins_p10_3_8k_db"] >= 18.0 for e in Ee.values())
                                  and gt <= 6.0)}
    # Q. les gestes du titre s'entendent POUR LA CIBLE (2e revue 27/09) : des artisans de 45-50 ans, sur un téléphone à
    #    volume normal. 0 dBFS = 80 dB SPL ; seuil absolu de Terhardt relevé d'une presbyacousie de ~50 ans (ISO 7029
    #    simplifiée : +5 dB à 2 kHz, +12 à 4 kHz, +20 dB à 8 kHz et au-dessus).
    #    - l'envol de chaque saut : émergence de la couche point sur le reste du mix ≥ +6 dB dans au moins un tiers d'octave
    #      de 4 à 16 kHz, et ce tiers d'octave ≥ 10 dB au-dessus du seuil (relevé) ;
    #    - l'assise sur le ı, sur un haut-parleur de téléphone simulé (mono, 400 Hz-12 kHz) : la même chose de 1 à 12 kHz.
    CF = 1000 * 2 ** (np.arange(-14, 13) / 3)
    SPL_0DBFS = 80.0
    terhardt = lambda f: 3.64 * (f / 1000) ** -0.8 - 6.5 * np.exp(-0.6 * (f / 1000 - 3.3) ** 2) + 1e-3 * (f / 1000) ** 4  # noqa: E731
    presbyacousie = lambda f: np.interp(np.log2(f), np.log2([1000, 2000, 4000, 8000, 24000]), [0.0, 5.0, 12.0, 20.0, 20.0])  # noqa: E731
    seuil_abs = lambda f: terhardt(f) + presbyacousie(f)  # noqa: E731

    def bandes(x, a, b):
        seg = x[int(a * SR):int(b * SR)]
        seg = seg.mean(axis=1) if seg.ndim > 1 else seg
        w_ = np.hanning(len(seg))
        X = np.abs(np.fft.rfft(seg * w_)) ** 2 * 2 / (len(seg) * np.sum(w_ ** 2))     # puissance par bin (Parseval)
        f = np.fft.rfftfreq(len(seg), 1 / SR)
        return np.array([X[(f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-30 for c in CF])

    def s_entend(sig_, reste_, a, b, lo, hi):
        e, r = bandes(sig_, a, b), bandes(reste_, a, b)
        em = 10 * np.log10(e / r); lv = 10 * np.log10(e)
        sl = lv + SPL_0DBFS - seuil_abs(CF)
        j = [i for i, c in enumerate(CF) if lo <= c <= hi]
        i = max(j, key=lambda i: min(em[i] - 6, sl[i] - 10))          # la bande où il s'entend le mieux
        d = {"bande_hz": round(float(CF[i])), "emergence_db": round(float(em[i]), 1), "niveau_bande_dbfs": round(float(lv[i]), 1),
             "au_dessus_du_seuil_releve_db": round(float(sl[i]), 1)}
        d["audible"] = bool(d["emergence_db"] >= 6 and d["au_dessus_du_seuil_releve_db"] >= 10)
        return d
    Qc = {}
    for c_ in [c for c in CU["cues"] if c["id"].startswith("envol-")]:
        tc = c_["t"]
        q = s_entend(st["point"], mix - st["point"], tc - 0.003, tc + 0.035, 4000, 16000)
        baisse = [r for r in CU["rattrapage_voix"] if "point" in r["couches"] and r["debut"] - 0.1 <= tc <= r["debut"] + 0.5]
        q["baisse_pour_la_voix_db"] = min((r["gain_db"] for r in baisse), default=0.0)
        q["ok"] = bool(q["audible"] or q["baisse_pour_la_voix_db"] < -1.0)      # la voix d'abord : rapporté, pas compté
        Qc[c_["id"]] = q
    hp = lambda x: S.passe_bande(x.mean(axis=1), 400, 12000, front=200)  # noqa: E731
    ta = [c for c in CU["cues"] if c["id"] == "assise-i"][0]["t"]
    i0_, i1_ = int((ta - 0.5) * SR), int((ta + 0.5) * SR)
    p_hp = np.zeros(len(mix)); r_hp = np.zeros(len(mix))
    p_hp[i0_:i1_] = hp(st["point"][i0_:i1_]); r_hp[i0_:i1_] = hp((mix - st["point"])[i0_:i1_])
    Qc["assise-i (haut-parleur)"] = s_entend(p_hp, r_hp, ta - 0.003, ta + 0.060, 1000, 12000)
    Qc["assise-i (haut-parleur)"]["ok"] = Qc["assise-i (haut-parleur)"]["audible"]
    R["Q_gestes_du_titre"] = {**Qc, "hypothese": "0 dBFS = 80 dB SPL ; seuil de Terhardt + presbyacousie ~50 ans (+20 dB dès 8 kHz)",
                              "ok": all(q["ok"] for q in Qc.values())}
    # H. le halo reste une OMBRE de la nappe (2e revue 27/09 : à la signature il se posait sur le scintillement et le ré6,
    #    et tenait tout le spectre au-dessus de 1 kHz). Milieu (ce que jouent le mono et le haut-parleur ; le côté du halo
    #    est l'élargissement de la nappe elle-même), Welch 16 384 points, fenêtres de 0,5 s tous les 0,25 s :
    #    H1 : halo ≤ (nappe + signature) − 6 dB dans chaque tiers d'octave de 1 à 8 kHz, du la à la fin du son, et sur la
    #         lecture du SMS (air du SMS établi → la) ;
    #    H2 : halo ≤ signature − 10 dB dans le tiers d'octave du scintillement (2 349,3 Hz), du la à la fin du son ;
    #    (H1 et H2 : les bandes où le halo est sous −100 dBFS, −20 dB SPL, ne comptent pas) ;
    #    H3 : après le silence (36,667 → 37,6), l'enveloppe 50 ms du halo reste ≥ 6 dB sous celle de la nappe (là où il
    #         dépasse −90 dBFS) : il n'y rapporte pas l'accord de l'appel.
    def welch(x, a, b, n=16384):
        m_ = x[int(a * SR):int(b * SR)].mean(axis=1)
        w_ = np.hanning(n); P = 0; k = 0
        for j in range(0, len(m_) - n + 1, n // 4):
            P = P + np.abs(np.fft.rfft(m_[j:j + n] * w_)) ** 2; k += 1
        return np.fft.rfftfreq(n, 1 / SR), P * 2 / (max(k, 1) * n * np.sum(w_ ** 2))
    CH = 1000 * 2 ** (np.arange(0, 10) / 3)
    PLANCHER_H = -100.0          # dBFS par tiers d'octave : −20 dB SPL à 0 dBFS = 80 dB SPL (deux « riens » ne se comparent pas)
    ref_ = st["nappe"] + st["signature"]

    def plafonds(a0, a1):
        out = []
        for a in np.arange(a0, a1 - 0.5 + 1e-9, 0.25):
            f, Ph = welch(st["halo"], a, a + 0.5); _, Pr = welch(ref_, a, a + 0.5); _, Ps = welch(st["signature"], a, a + 0.5)
            bh = np.array([Ph[(f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-30 for c in CH])
            br = np.array([Pr[(f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-30 for c in CH])
            sc = (f >= 2349.3 * 2 ** (-1 / 6)) & (f < 2349.3 * 2 ** (1 / 6))
            ec = np.where(10 * np.log10(bh) > PLANCHER_H, 10 * np.log10(bh / br), -999.0)   # sous −100 dBFS : rien à entendre
            j = int(np.argmax(ec))
            out.append({"de": round(float(a), 2), "pire_bande_hz": int(CH[j]), "halo_moins_nappe_signature_db": round(float(ec[j]), 1),
                        "scint_halo_dbfs": round(float(10 * np.log10(Ph[sc].sum() + 1e-30)), 1),
                        "scint_halo_moins_signature_db": round(float(10 * np.log10((Ph[sc].sum() + 1e-30) / (Ps[sc].sum() + 1e-30))), 1)})
        return out
    h_sig = plafonds(T["la"], FIN_SON)
    h_sms = plafonds(T["air_sms"] + 0.9, T["la"])
    h1 = max(h["halo_moins_nappe_signature_db"] for h in h_sig + h_sms)
    h2l = [h for h in h_sig if h["scint_halo_dbfs"] > PLANCHER_H]
    h2 = max((h["scint_halo_moins_signature_db"] for h in h2l), default=-999.0)
    s0_, s1_ = EV["silence_numerique"]["t"][1], 37.6
    env50 = lambda x: np.array([10 * np.log10(np.mean(x[int(t * SR):int((t + 0.05) * SR)] ** 2) + 1e-30)  # noqa: E731
                                for t in np.arange(s0_, s1_, 0.05)])
    eh, en = env50(st["halo"].mean(axis=1)), env50(st["nappe"].mean(axis=1))
    ecote = env50((st["halo"][:, 0] - st["halo"][:, 1]) / 2)
    act = eh > -90
    h3 = float(np.max((eh - en)[act])) if np.any(act) else -999.0
    court = lambda x, a, b: round(D.court_terme(x, a, b), 1)  # noqa: E731
    R["H_halo"] = {"H1_pire_halo_moins_nappe_signature_db": h1, "H1_pire_fenetre": max(h_sig + h_sms, key=lambda h: h["halo_moins_nappe_signature_db"]),
                   "H2_pire_scintillement_halo_moins_signature_db": h2, "H2_fenetres_mesurees": len(h2l),
                   "H3_apres_silence_halo_moins_nappe_max_db": round(h3, 1),
                   "H3_cote_du_halo_moins_nappe_max_db": round(float(np.max((ecote - en)[ecote > -90])), 1) if np.any(ecote > -90) else None,
                   "fenetres_signature": h_sig, "fenetres_lecture_sms": h_sms,
                   "halo_court_terme": {"accord de sol 12,5 → 17,5": court(st["halo"], 12.5, 17.5),
                                        "lecture du SMS 38 → 41": court(st["halo"], 38.0, 41.0),
                                        "signature 42,9 → 45,3": court(st["halo"], T["re"], 45.3),
                                        "fondu 45,3 → 46,7": court(st["halo"], 45.3, FIN_SON)},
                   "ok": bool(h1 <= -6.0 and h2 <= -10.0 and h3 <= -6.0)}
    # O. l'oiseau
    ois = [c_ for c_ in CU["cues"] if c_["id"].startswith("oiseau")]
    a0, a1 = MX.SEC["s1"]["segments_s"][0][1], MX.SEC["s1"]["segments_s"][1][0]
    ctm, lam = CS.instantanee(MX.ponderer_k(st["ambiance"]))
    _, lms = CS.instantanee(MX.ponderer_k(master))
    m_ = (ctm - 0.4 >= a0) & (ctm <= a1)                  # fenêtres de 400 ms entièrement dans le blanc
    R["O_oiseau"] = {"passages": [o["t"] for o in ois], "ambiance_M_max_blanc": round(float(lam[m_].max()), 1),
                     "master_M_blanc_median": round(float(np.median(lms[m_])), 1),
                     "ok": bool(len(ois) == 1 and lam[m_].max() <= np.median(lms[m_]) - 3.0)}
    # P. la pièce, pas la ligne : aucune raie du secteur (k·50 Hz) dans le fond de pièce, sur tout le stem ambiance
    #    (les prises ElevenLabs en portaient jusqu'à +39 dB au-dessus du bruit voisin : un ronflement, un bruit de ligne)
    xa = st["ambiance"].mean(axis=1)
    wa = np.hanning(len(xa)); Xa = np.abs(np.fft.rfft(xa * wa)) * 2 / np.sum(wa); fa = np.fft.rfftfreq(len(xa), 1 / SR)
    La = 20 * np.log10(Xa + 1e-30)
    raies = {}
    for h in range(150, 3001, 50):
        sel = (fa > h - 1.5) & (fa < h + 1.5); ctx = (fa > h - 30) & (fa < h + 30) & ~((fa > h - 4) & (fa < h + 4))
        raies[h] = round(float(La[sel].max() - np.median(La[ctx])), 1)
    R["P_piece_sans_ronflement"] = {"pire_raie_db_sur_le_bruit_voisin": max(raies.values()),
                                    "a_hz": max(raies, key=raies.get), "seuil_db": 12.0,
                                    "ok": bool(max(raies.values()) <= 12.0)}
    # T. le téléphone
    tel = [c_ for c_ in CU["cues"] if c_["id"].startswith("telephone")]
    R["T_telephone"] = {"sons": [(c_["id"], c_["fabrication"][:40]) for c_ in tel],
                        "sortie_instantanee_max": R["N_niveaux"].get("telephone-sort", {}).get("instantanee_max_lufs"),
                        "etincelle": any(c_["id"] == "bulle-ouverte" for c_ in CU["cues"])}
    R["T_telephone"]["bulle_sons"] = [c_["id"] for c_ in CU["cues"] if c_["id"].startswith("bulle")]
    R["T_telephone"]["ok"] = bool(len(tel) == 1 and not R["T_telephone"]["etincelle"] and not R["T_telephone"]["bulle_sons"]
                                  and (R["T_telephone"]["sortie_instantanee_max"] or 0) <= -37.5)
    # Z. le limiteur
    R["Z_limiteur"] = {"reduction_max_db": CU["reduction_limiteur_max_db"], "instants": CU.get("limiteur_instants_sup_0_05_db"),
                       "ok": bool(abs(CU["reduction_limiteur_max_db"]) <= 0.1)}
    R["synthese_ok"] = {k: v["ok"] for k, v in R.items() if isinstance(v, dict) and "ok" in v}
    R["synthese_ok"]["C_somme"] = R["C_somme_stems_moins_mix_max"] < 1e-5
    (ICI / "mesures-design.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(R["synthese_ok"], ensure_ascii=False))
    planches(mixp, courbe, courbe_master)


MARQUES = [("naissance", 0.8333), ("décroché", T["decroche"]), ("agenda", EV["agenda_monte"]["t"][0]),
           ("9·10·11", EV["contact_neuf"]["t"]), ("plume", EV["ecriture_debut"]["t"]), ("résolution", T["resolution"]),
           ("raccroché", T["raccroche"]), ("bulle", T["vibreur"]), ("Vokıo", EV["plume_mot"]["t"][0]), ("ré", T["re"])]


def courbe_png(cd, cm, chemin):
    from PIL import Image, ImageDraw, ImageFont
    W_, H, g, d, h, b = 2400, 900, 90, 30, 50, 70
    im = Image.new("RGB", (W_, H), (244, 241, 232))
    dr = ImageDraw.Draw(im)
    try:
        police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        police = None
    x = lambda t: g + (W_ - g - d) * t / DUREE  # noqa: E731
    y = lambda l: h + (H - h - b) * (-5 - l) / 45.0  # noqa: E731
    for l in range(-50, -4, 5):
        dr.line([(g, y(l)), (W_ - d, y(l))], fill=(214, 208, 196))
        dr.text((10, y(l) - 7), f"{l} LUFS", fill=(111, 105, 95), font=police)
    for s in range(0, int(DUREE) + 1, 5):
        dr.line([(x(s), H - b), (x(s), H - b + 8)], fill=(111, 105, 95))
        dr.text((x(s) - 8, H - b + 12), f"{s} s", fill=(111, 105, 95), font=police)
    for nom, tx in MARQUES:
        dr.line([(x(tx), h), (x(tx), H - b)], fill=(239, 164, 36), width=1)
        dr.text((x(tx) + 4, h + 4), nom, fill=(38, 32, 25), font=police)
    for cb, col, lw, idx in ((cm, (150, 144, 134), 2, 2), (cd, (192, 69, 44), 3, 2), (cd, (230, 190, 170), 1, 1)):
        ct = np.array(cb)
        pts = [(x(t), y(max(-50.0, v))) for t, v in zip(ct[:, 0], ct[:, idx])]
        dr.line(pts, fill=col, width=lw)
    dr.text((g, 10), "Arc de sonie · ebur128 · gris : master, court terme S (3 s) · terracotta : sound design, S · rose : sound "
            "design, instantanée M (400 ms)", fill=(38, 32, 25), font=police)
    im.save(chemin)


def planches(mixp, cd, cm):
    def run(entree, filtre, sortie, extra=()):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *extra, "-i", str(entree), "-lavfi", filtre, "-frames:v", "1",
                        str(IMG / sortie)], check=True)
    courbe_png(cd, cm, IMG / "arc-de-sonie.png")
    sp = "showspectrumpic=s=2400x600:legend=1:fscale=log:scale=log:stop=16000:color=intensity"
    run(SON / "mix.wav", sp, "master-spectre.png")
    run(mixp, sp, "design-spectre.png")
    run(IMG / "ajout.wav", sp, "couches-ajoutees-spectre.png")
    for n in D.COUCHES:
        run(ICI / "stems" / f"{n}.wav", "showspectrumpic=s=2400x400:legend=1:fscale=log:scale=log:stop=16000:color=intensity:gain=2",
            f"couche-{n}-spectre.png")
    for nom, (a, b) in {"z1-naissance-sonnerie": (0, 5.2), "z2-suiveur": (4.5, 11), "z3-agenda-contacts": (17.0, 25.0),
                        "z4-plume-rendez-vous": (24.8, 27.0), "z5-sms-telephone": (30.8, 36.2), "z6-silence-bulle-vibreur": (35.5, 41.5),
                        "z7-vokio-signature": (41.0, DUREE)}.items():
        for src, tag in ((mixp, "design"), (SON / "mix.wav", "master"), (IMG / "ajout.wav", "ajout")):
            run(src, "showspectrumpic=s=1600x500:legend=1:fscale=log:scale=log:stop=16000:color=intensity",
                f"{nom}-{tag}.png", extra=("-ss", str(a), "-t", str(b - a)))
    # planches comparées : master / variante / couches ajoutées seules, l'une sous l'autre (les cmp-*.png d'avant la
    # 2e revue décrivaient l'ancienne version : elles sont refaites à chaque contrôle)
    from PIL import Image, ImageDraw, ImageFont
    try:
        police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except OSError:
        police = None

    def empiler(sources, sortie):
        ims = [Image.open(IMG / n).convert("RGB") for n, _ in sources]
        W_ = max(i.width for i in ims); H_ = sum(i.height + 34 for i in ims)
        out = Image.new("RGB", (W_, H_), (244, 241, 232)); y = 0
        dr = ImageDraw.Draw(out)
        for im, (_, titre) in zip(ims, sources):
            dr.text((12, y + 6), titre, fill=(38, 32, 25), font=police); y += 34
            out.paste(im, (0, y)); y += im.height
        out.save(IMG / sortie)
    empiler([("master-spectre.png", "MASTER (son/mix.wav)"), ("design-spectre.png", "VARIANTE SOUND DESIGN (mix-design.wav)"),
             ("couches-ajoutees-spectre.png", "COUCHES AJOUTÉES SEULES")], "cmp-film.png")
    for nom in ("z1-naissance-sonnerie", "z2-suiveur", "z3-agenda-contacts", "z4-plume-rendez-vous", "z5-sms-telephone",
                "z6-silence-bulle-vibreur", "z7-vokio-signature"):
        empiler([(f"{nom}-master.png", f"{nom} · MASTER"), (f"{nom}-design.png", f"{nom} · VARIANTE"),
                 (f"{nom}-ajout.png", f"{nom} · COUCHES AJOUTÉES")], f"cmp-{nom}.png")
    print(f"planches : {IMG}")


if __name__ == "__main__":
    main()
