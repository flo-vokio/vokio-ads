#!/usr/bin/env python3
"""Contrôles de la variante « musique » (écoute impossible ici : tout se prouve par la mesure).

    python3 son/riche-musique/controle_musique.py [--images]   → son/riche-musique/mesures-musique.json (+ PNG)

  A. master : −14,0 ± 0,3 LUFS intégrés, crête vraie ≤ −1,0 dBTP (cible −1,5), sur le WAV ET sur la piste AAC du MP4
  B. silences : zéros exacts sur [35,9467 ; 36,6667] et [46,70 ; 47,00]
  C. somme des stems = mix
  F. intelligibilité : voix ≥ 10 LU au-dessus de TOUT le reste (musique + sfx + signature), mot par mot (pondération K),
     et, dans la bande 1-4 kHz, voix − musique par mot
  G. mono : écart de sonie mono/stéréo (film, sections), corrélation G/D par 100 ms
  M. arc : ebur128 court terme (3 s) sur tout le film ; le maximum doit tomber dans le logo (≥ 42,9) ; le ré est
     l'instant le plus fort du film (sonie instantanée 0,4 s, maximum dans [ré ; ré + 0,8]) ; signature
     [ré ; ré + 1,5] ≥ médiane du dialogue + 1 LU
  H. harmonie : chroma de la musique par mesure (classes dominantes, basse) ; la basse de chaque mesure est celle
     d'ACCORDS (« pas de basse » si l'énergie 35-160 Hz est à plus de 20 dB sous la médiane) ; aucune basse ré avant le logo
  P. MP4 : vidéo identique octet pour octet (hash du flux vidéo), durées, 48 kHz stéréo
  ─ ajoutés à la relecture du 27/09 ─
  R. rythme : sur [décroché ; raccroché], le gain dynamique du pouls (ducking, réponses, creux 1-4 kHz, plateau grave)
     ne varie jamais de plus de 1 dB en 50 ms (défaut 1) ; valeurs aux accents composés (temps 28, 32, 43)
  L. lit : dans les blancs de moins de 0,8 s, le tapis ne remonte pas de plus de 1,5 dB (défaut 8)
  T. téléphone : passe-haut 250 Hz (24 dB/oct) + passe-bas 8 kHz, sonie K ; musique contre la nappe validée par scène,
     sous les mots et dans les blancs ; logo ≥ nappe + 2 LU ; sonnerie ≥ −40 LUFS et ≤ sonnerie − 12 LU (défauts 3, 6)
  S. signature : clairière (signature − musique ≥ +15 LU sur le la et sur le sol) ; un seul limiteur (réduction sur
     [42,25 ; 43,2] ≤ celle du master validé + 0,5 dB ; signature à ±0,2 dB du master validé sur la, sol, ré) (défauts 2, 4)
  V. verre : sur [38,3 ; 39,3], verre ≥ marimba + 10 dB dans 600-1 000 Hz (défaut 5)
  ─ ajoutés ou durcis à la deuxième relecture du 27/09 ─
  S. plume (la 25,40 · sol 25,64) : aucune attaque de musique à ±120 ms de l'une ou l'autre note (toutes couches, basse
     comprise) ; signature − musique ≥ +18 dB dans les bandes 440 et 392 Hz (±1,5 %), et ≥ +6 LU en sonie K. Ré de
     marque : signature − musique ≥ +12 dB à 587 Hz sur [43,1 ; 44,1], ≥ +6 dB sur [44,1 ; 44,6], ≥ +6 dB à 1 175 Hz sur
     [43,1 ; 44,1] (défauts 1 et 3)
  R. lit : sur [décroché ; raccroché], son gain large + son creux 1-4 kHz ne baissent jamais de plus de 1,5 dB en 50 ms,
     et la courbe bornée ne dépasse jamais la courbe d'avant la borne (défaut 2)
  L. lit : remontée mesurée sur la courbe finale du lit (et non plus sur le détecteur)
  H. grosse caisse : pic 35-80 Hz de la couche sur [coup ; coup + 0,5 s] à ±0,3 demi-ton de la note visée, pour chaque
     coup ; la basse de la musique ENTIÈRE (35-160 Hz) est celle de l'accord, par segment d'accord d'au moins un temps, et
     H échoue sinon (défaut 4) ; F : marges des premiers mots après chaque vraie pause, au détail
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
SON = ICI.parent
sys.path.insert(0, str(SON))
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402
import mix as MX  # noqa: E402
import mesures as ME  # noqa: E402
import mix_riche_musique as R  # noqa: E402
import instruments as I  # noqa: E402

SR = labo.SR
N = MX.N
EV, T = MX.EV, MX.T
IMG = R.IMG


def K(x):
    return MX.ponderer_k(x)


def sonie(xk, i0, i1):
    s = xk[max(0, i0):i1]
    return -0.691 + 10 * np.log10(np.sum(np.mean(s ** 2, axis=0)) + 1e-20) if len(s) else -np.inf


def instantanee(xk, pas=0.01, fen=0.4):
    p = np.sum(xk ** 2, axis=1)
    c = np.concatenate([[0.0], np.cumsum(p)])
    w = int(fen * SR); h = int(pas * SR)
    fins = np.arange(w, len(p) + 1, h)
    return fins / SR, -0.691 + 10 * np.log10((c[fins] - c[fins - w]) / w + 1e-20)


def bande(x, f1, f2):
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = ((f >= f1) & (f <= f2)).astype(float)
    return np.fft.irfft(X * (m[:, None] if X.ndim > 1 else m), len(x), axis=0)


def attaque(x, t, fen=0.030):
    """Attaque d'une note posée sur la queue d'une autre : puissance sur 0,5 ms ; pour chaque τ de [t − fen ; t + fen],
    montée = moyenne dB sur [τ ; τ + 2 ms] − moyenne dB sur [τ − 6 ; τ − 1 ms] ; on garde le τ de plus forte montée, puis
    le premier instant de [τ − 2 ; τ + 2 ms] où la puissance dépasse de 3 dB le niveau d'avant."""
    h = 24
    a0 = int(round((t - fen - 0.01) * SR)); a1 = int(round((t + fen + 0.01) * SR))
    s_ = x[a0:a1]
    nb = len(s_) // h
    e = 10 * np.log10(np.mean(s_[:nb * h].reshape(nb, h) ** 2, axis=1) + 1e-14)
    best, bi = -1e9, 0
    for i in range(12, nb - 4):
        m = e[i:i + 4].mean() - e[i - 12:i - 2].mean()
        if m > best:
            best, bi = m, i
    avant = e[bi - 12:bi - 2].mean()
    j = bi - 4
    while j < bi + 4 and e[j] < avant + 3:
        j += 1
    ta = (a0 + j * h) / SR
    return {"attaque": round(ta, 4), "ecart_ms": round((ta - t) * 1000, 2), "montee_db": round(float(best), 1)}


def calage_note(x, t, gabarit, fen=0.030):
    """Calage d'une note grave qui succède à une autre (la basse) : le détecteur attaque(), sur la puissance par 0,5 ms,
    prend les passages à zéro de la note précédente pour des montées (un sol2 à 98 Hz creuse la puissance de 30 dB toutes
    les 5 ms) ; on cherche donc le décalage, sur [t − fen ; t + fen], qui maximise la corrélation normalisée entre la
    couche et la forme d'onde synthétisée de la note (ses 0,25 premières secondes). La basse étant monophonique (la note
    précédente s'éteint 12 ms après l'attaque), rien d'autre n'y corrèle."""
    L = len(gabarit)
    a = int(round((t - fen) * SR))
    seg = x[a:a + L + 2 * int(round(fen * SR))]
    c = np.correlate(seg, gabarit, mode="valid")
    e = np.sqrt(np.convolve(seg ** 2, np.ones(L), mode="valid")) * np.sqrt(np.sum(gabarit ** 2)) + 1e-20
    r = c / e
    k = int(np.argmax(r))
    ta = (a + k) / SR
    return {"attaque": round(ta, 4), "ecart_ms": round((ta - t) * 1000, 2), "correlation": round(float(r[k]), 3),
            "methode": "corrélation avec la forme d'onde de la note"}


def hash_video(chemin):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(chemin), "-map", "0:v", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def sonde(chemin):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(chemin)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def courbe_png(pts, png, reperes, titre):
    """Courbe S (3 s) et M (0,4 s) sur tout le film, scènes et repères, en PNG (PIL)."""
    from PIL import Image, ImageDraw
    W, H = 1410, 420
    im = Image.new("RGB", (W, H), (244, 241, 232))
    d = ImageDraw.Draw(im)
    x = lambda t: int(40 + (W - 60) * t / 47.0)  # noqa: E731
    y = lambda v: int(20 + (H - 60) * (-8 - v) / 32)  # noqa: E731  (−8 → −40 LUFS)
    for v in range(-8, -41, -4):
        d.line([(40, y(v)), (W - 20, y(v))], fill=(225, 220, 208))
        d.text((4, y(v) - 6), f"{v}", fill=(111, 105, 95))
    for nom, s in ME.scenes().items():
        d.line([(x(s["debut"]), 20), (x(s["debut"]), H - 40)], fill=(200, 194, 180))
        d.text((x(s["debut"]) + 3, H - 36), nom.split("-", 1)[1][:10], fill=(111, 105, 95))
    for nom, t in reperes.items():
        d.line([(x(t), 20), (x(t), 34)], fill=(110, 156, 116), width=2)
    pm = [(x(t), y(max(m, -40))) for t, m, s in pts if m > -60]
    ps = [(x(t), y(max(s, -40))) for t, m, s in pts if s > -60 and t >= 3.0]
    if len(pm) > 1:
        d.line(pm, fill=(200, 190, 170), width=1)
    if len(ps) > 1:
        d.line(ps, fill=(239, 164, 36), width=3)
    d.text((44, 2), titre + "   (orange : court terme 3 s ; gris : instantanée 0,4 s ; LUFS)", fill=(38, 32, 25))
    im.save(png)


def main(images=False):
    res = {}
    mixp = R.ICI / "mix-musique.wav"
    mix = labo.lire(mixp)
    st = {k: labo.lire(R.STEMS_OUT / f"{k}.wav") for k in ("dialogue", "sfx", "signature", "musique")}
    # A
    A = {"wav": labo.mesurer(mixp)}
    if R.SORTIE_MP4.exists():
        A["mp4_aac"] = labo.mesurer(R.SORTIE_MP4)
    A["ok"] = bool(abs(A["wav"]["lufs"] + 14) <= 0.3 and A["wav"]["crete_dbtp"] <= -1.0 and
                   ("mp4_aac" not in A or (abs(A["mp4_aac"]["lufs"] + 14) <= 0.3 and A["mp4_aac"]["crete_dbtp"] <= -1.0)))
    res["A_master"] = A
    # B
    s0, s1 = EV["silence_numerique"]["t"]
    B = {"silence_raccroche_max": float(np.max(np.abs(mix[int(round(s0 * SR)):int(round(s1 * SR))]))),
         "silence_final_max": float(np.max(np.abs(mix[int(round(MX.FIN_SON * SR)):])))}
    B["ok"] = B["silence_raccroche_max"] == 0.0 and B["silence_final_max"] == 0.0
    res["B_silences"] = B
    # C
    somme = sum(st.values())
    res["C_somme_moins_mix_max"] = float(np.max(np.abs(somme - mix)))
    # F
    dk = K(st["dialogue"])
    reste = st["sfx"] + st["signature"] + st["musique"]
    rk, mk_ = K(reste), K(st["musique"])
    dm = bande(st["dialogue"], 1000, 4000); mm = bande(st["musique"], 1000, 4000)
    F, Fm, Fb = [], [], []
    for w in MX.MOTS["mots"]:
        i0, i1 = int(w["debut"] * SR), int(max(w["fin"], w["debut"] + 0.12) * SR)
        F.append((round(float(sonie(dk, i0, i1) - sonie(rk, i0, i1)), 1), w["texte"], w["debut"]))
        Fm.append((round(float(sonie(dk, i0, i1) - sonie(mk_, i0, i1)), 1), w["texte"], w["debut"]))
        e_v = 10 * np.log10(np.mean(dm[i0:i1] ** 2) + 1e-20); e_m = 10 * np.log10(np.mean(mm[i0:i1] ** 2) + 1e-20)
        Fb.append((round(float(e_v - e_m), 1), w["texte"], w["debut"]))
    F.sort(); Fm.sort(); Fb.sort()
    res["F_intelligibilite"] = {"voix_sur_tout_le_reste_LU": {"min": F[0][0], "mediane": float(np.median([f[0] for f in F])), "pires": F[:8]},
                                "voix_sur_musique_seule_LU": {"min": Fm[0][0], "mediane": float(np.median([f[0] for f in Fm])), "pires": Fm[:6]},
                                "voix_sur_musique_1-4kHz_dB": {"min": Fb[0][0], "mediane": float(np.median([f[0] for f in Fb])), "pires": Fb[:6]},
                                "ok": bool(F[0][0] >= 10.0 and Fb[0][0] >= 12.0)}
    reprises = {}
    for a0, b0 in R.pauses_du_dialogue():
        for f_, fm_, fb_ in zip(sorted(F, key=lambda x: x[2]), sorted(Fm, key=lambda x: x[2]), sorted(Fb, key=lambda x: x[2])):
            if abs(f_[2] - b0) < 1e-6:
                reprises[f"{f_[1]} {b0:.2f}"] = {"voix_sur_tout_LU": f_[0], "voix_sur_musique_LU": fm_[0], "1-4kHz_dB": fb_[0]}
    for w in MX.MOTS["mots"]:
        if abs(w["debut"] - 5.0) < 1e-6:
            i = [x[2] for x in sorted(F, key=lambda x: x[2])].index(w["debut"])
            reprises[f"{w['texte']} 5.00 (après le décroché)"] = {"voix_sur_tout_LU": sorted(F, key=lambda x: x[2])[i][0],
                                                                "voix_sur_musique_LU": sorted(Fm, key=lambda x: x[2])[i][0],
                                                                "1-4kHz_dB": sorted(Fb, key=lambda x: x[2])[i][0]}
    res["F_intelligibilite"]["premiers_mots_apres_les_pauses"] = reprises
    # G
    mixk = K(mix)
    mono = (mix[:, 0] + mix[:, 1]) / 2
    monok = K(np.stack([mono, mono], axis=1))
    G = {"film_LU": round(float(sonie(monok, 0, N) - sonie(mixk, 0, N)), 2)}
    for nom, s in ME.scenes().items():
        a, b = int(s["debut"] * SR), int(min(s["fin"], MX.FIN_SON) * SR)
        G[nom] = round(float(sonie(monok, a, b) - sonie(mixk, a, b)), 2)
    mus = st["musique"]
    mmono = (mus[:, 0] + mus[:, 1]) / 2
    G["musique_seule_film_LU"] = round(float(sonie(K(np.stack([mmono, mmono], 1)), 0, N) - sonie(K(mus), 0, N)), 2)
    w = 4800; nb = N // w
    Lc, Rc = mix[:nb * w, 0].reshape(nb, w), mix[:nb * w, 1].reshape(nb, w)
    e = np.sqrt(np.mean(Lc ** 2, 1) * np.mean(Rc ** 2, 1)); ok = e > 1e-6
    cor = np.mean(Lc * Rc, 1)[ok] / e[ok]
    G["correlation_min_100ms"] = round(float(cor.min()), 3); G["correlation_mediane"] = round(float(np.median(cor)), 3)
    G["fenetres_negatives"] = int(np.sum(cor < 0))
    G["ok"] = bool(abs(G["film_LU"]) <= 1.0 and G["fenetres_negatives"] == 0 and all(abs(G[n]) <= 1.5 for n in ME.scenes()))
    res["G_mono"] = G
    # M
    rap, pts = ME.rapport_court(mixp)
    tS, MM, SS = pts[:, 0], pts[:, 1], pts[:, 2]
    dial = SS[(tS >= 5.0) & (tS <= 35.4)]
    tm, lm = instantanee(mixk)
    dM = (tm >= 5.0) & (tm <= 35.5)
    dR = (tm >= T["re"]) & (tm <= T["re"] + 0.8)
    Mv = {"S_max_film": rap["S_max_film"], "S_max_par_scene": {k: v["S_max"] for k, v in rap["scenes"].items()},
          "S_median_par_scene": {k: v["S_median"] for k, v in rap["scenes"].items()},
          "mediane_S_dialogue": round(float(np.median(dial)), 2), "S_max_dialogue": round(float(dial.max()), 2),
          "S_max_logo_moins_S_max_dialogue_LU": round(float(rap["S_max_film"]["S"] - dial.max()), 2),
          "signature_LUFS_re_re+1.5": round(float(sonie(mixk, int(T["re"] * SR), int((T["re"] + 1.5) * SR))), 2),
          "M_max_au_re": round(float(lm[dR].max()), 2), "M_max_dialogue": round(float(lm[dM].max()), 2),
          "M_max_film": [round(float(lm.max()), 2), round(float(tm[np.argmax(lm)]), 2)],
          "S_par_seconde": {int(round(t)): round(float(s), 1) for t, s in zip(tS, SS) if abs(t - round(t)) < 1e-6}}
    # la signature reste le sommet : l'instant le plus fort du film (0,4 s) tombe sur le ré, pas sur l'accord qui suit
    Mv["ok_instant_le_plus_fort_au_re"] = bool(T["re"] <= Mv["M_max_film"][1] <= T["re"] + 0.8)
    Mv["ok"] = bool(Mv["S_max_film"]["t"] >= T["re"] and Mv["M_max_au_re"] >= Mv["M_max_dialogue"]
                    and Mv["signature_LUFS_re_re+1.5"] >= Mv["mediane_S_dialogue"] + 1.0 and Mv["ok_instant_le_plus_fort_au_re"])
    res["M_arc"] = Mv
    # H
    H = {}
    dc = R.ICI / "couches"
    basse_couche = labo.lire(dc / "basse.wav") if (dc / "basse.wav").exists() else None
    mesures_ = [("s1 0-4,2", 0.3, 4.15)] + [(f"mesure {k}", R.tb(4 * k), R.tb(4 * k + 4)) for k in range(1, 15)]
    for nom, a, b in mesures_:
        a = max(a, R.T_DEC + 0.3) if nom == "mesure 1" else a
        b = min(b, R.T_RAC) if a < R.T_RAC < b else b
        if b > MX.FIN_SON:
            b = MX.FIN_SON
        c = ME.chroma(mus, a, b)
        cb_mus = ME.chroma(mus, a, b, fmin=35, fmax=160)
        # la basse est lue sur la couche basse (couches/basse.wav) : dans la musique entière, la queue de la grosse
        # caisse (corps posé sur sol1 ou la1) se mêle au registre de la basse
        src = mus if nom.startswith("s1") or not (dc / "basse.wav").exists() else basse_couche
        cb = ME.chroma(src, a, b, fmin=35, fmax=160)
        seg = src[int(a * SR):int(b * SR)].mean(axis=1)
        X = np.fft.rfft(seg); fq = np.fft.rfftfreq(len(seg), 1 / SR)
        e_basse = 10 * np.log10(np.mean(np.abs(X[(fq >= 35) & (fq <= 160)]) ** 2) + 1e-20)
        acc = R.accord_a((a + b) / 2)
        H[nom] = {"fenetre": [round(a, 3), round(b, 3)], "classes": [ME.NOMS[j] for j in np.argsort(-c)[:4]],
                  "basse": ME.NOMS[int(np.argmax(cb))], "basse_dans_la_musique_entiere": ME.NOMS[int(np.argmax(cb_mus))],
                  "accord_prevu": acc[1], "basse_prevue": ME.NOMS[acc[3] % 12],
                  "energie_35_160_db": round(float(e_basse), 1)}
    mes = {k: v for k, v in H.items() if k.startswith("mesure")}
    med = float(np.median([v["energie_35_160_db"] for v in mes.values()]))
    for v in mes.values():
        if v["energie_35_160_db"] < med - 20:
            v["basse"] = "pas de basse"
    avant = [v for k, v in mes.items() if v["fenetre"][1] <= R.tb(56) + 1e-6]
    H["ok_pas_de_basse_re_avant_logo"] = all(v["basse"] != "ré" for v in avant)
    H["ecarts_basse_prevue"] = {k: [v["basse"], v["basse_prevue"]] for k, v in mes.items() if v["basse"] != v["basse_prevue"]}
    H["ok_basse_de_chaque_mesure"] = not H["ecarts_basse_prevue"]
    # deuxième relecture, défaut 4 : la basse de la musique ENTIÈRE (grosse caisse comprise), par segment d'accord
    # (une mesure qui change d'accord est coupée à chaque changement), segments d'au moins un temps ; hors clairière
    # (temps 55 : rien n'y est joué à la basse, seul le souffle de ré majeur y monte vers le ré)
    seg_ok, segs = True, []
    bornes = sorted({round(x[0], 6) for x in R.ACCORDS} | {round(R.T_DEC + 0.3, 6), round(R.T_RAC, 6), round(MX.FIN_SON, 6)})
    for nom, a, b in mesures_[1:]:
        a = max(a, R.T_DEC + 0.3) if nom == "mesure 1" else a
        b = min(b, R.T_RAC) if a < R.T_RAC < b else min(b, MX.FIN_SON)
        coupes = [a] + [x for x in bornes if a < x < b] + [b]
        for a0, b0 in zip(coupes, coupes[1:]):
            acc = R.accord_a((a0 + b0) / 2)
            if b0 - a0 < R.BEAT - 1e-3 or acc[1] == "G/clairière":
                continue
            cb = ME.chroma(mus, a0, b0, fmin=35, fmax=160)
            lu = ME.NOMS[int(np.argmax(cb))]
            ok_ = lu == ME.NOMS[acc[3] % 12]
            seg_ok &= ok_
            segs.append({"mesure": nom, "segment": [round(a0, 3), round(b0, 3)], "accord": acc[1],
                         "basse_prevue": ME.NOMS[acc[3] % 12], "basse_dans_la_musique_entiere": lu, "ok": ok_})
    H["segments_musique_entiere"] = segs
    H["ok_basse_musique_entiere_par_segment"] = bool(seg_ok)
    gk = []
    cues_ = json.loads((R.ICI / "cues-musique.json").read_text())["cues"]
    if (dc / "grosse_caisse.wav").exists():
        gcx = labo.lire(dc / "grosse_caisse.wav").mean(axis=1)
        for c_ in cues_:
            if c_["couche"] != "grosse caisse" or "f_fin" not in c_:
                continue
            i0 = int(round(c_["t"] * SR)); n_ = int(0.5 * SR)
            s_ = gcx[i0:i0 + n_] * np.hanning(n_)
            X = np.abs(np.fft.rfft(s_, 1 << 18)) ** 2; fq = np.fft.rfftfreq(1 << 18, 1 / SR)
            m_ = (fq >= 35) & (fq <= 80)
            fp = float(fq[m_][np.argmax(X[m_])])
            gk.append({"t": c_["t"], "coup": c_["quoi"], "vise_hz": c_["f_fin"], "pic_hz": round(fp, 2),
                       "ecart_demi_tons": round(float(12 * np.log2(fp / c_["f_fin"])), 2)})
    H["grosse_caisse_hauteur"] = gk
    H["ok_grosse_caisse_accordee"] = bool(gk) and all(abs(g_["ecart_demi_tons"]) <= 0.3 for g_ in gk)
    H["ok"] = bool(H["ok_pas_de_basse_re_avant_logo"] and H["ok_basse_de_chaque_mesure"]
                   and H["ok_basse_musique_entiere_par_segment"] and H["ok_grosse_caisse_accordee"])
    res["H_harmonie"] = H
    # D. synchro : attaque des couches frappées contre leur instant de grille (couches/ écrites par --couches)
    D = []
    dc = R.ICI / "couches"
    if dc.exists():
        for couche, instants in (("marimba", [("contact_neuf", EV["contact_neuf"]["t"]), ("contact_dix", EV["contact_dix"]["t"]),
                                              ("contact_onze", EV["contact_onze"]["t"]), ("-tion (temps 43)", R.tb(43))]),
                                 ("grosse_caisse", [("contact_dix", EV["contact_dix"]["t"]), ("-tion (temps 43)", R.tb(43)),
                                                    ("contact du ré", T["re"])]),
                                 ("basse", [("decroche (sol2, attaque 0,6 s)", R.T_DEC), ("contact_dix", EV["contact_dix"]["t"]),
                                            ("contact du ré", T["re"])])):
            x = labo.lire(dc / f"{couche}.wav").mean(axis=1)
            for nom, t in instants:
                if couche == "basse":
                    m, d, att = {"contact_dix": (47, 1.5 * R.BEAT, 10), "contact du ré": (38, MX.FIN_SON - R.tb(56), 10)}.get(
                        nom, (43, R.tb(12) - R.T_DEC, 600))
                    g = I.basse(m, d, attaque_ms=att, relache_ms=110)[:int(0.25 * SR)]
                    D.append({"couche": couche, "repere": nom, "t": round(t, 4), **calage_note(x, t, g)})
                else:
                    D.append({"couche": couche, "repere": nom, "t": round(t, 4), **attaque(x, t)})
    # tolérance : ±5 ms pour ce qui frappe (marimba, grosse caisse) ; la basse, calée par corrélation, ±12 ms
    tol = {"marimba": 5.0, "grosse_caisse": 5.0, "basse": 12.0}
    res["D_synchro"] = {"attaques": D, "tolerances_ms": tol, "ok": bool(D) and all(abs(d["ecart_ms"]) <= tol[d["couche"]] for d in D)}
    # R, L : gains enregistrés par mix_riche_musique.py (1 kHz)
    gz = np.load(R.ICI / "gains-musique.npz")
    a_, b_ = int(R.T_DEC * 1000), int(R.T_RAC * 1000)
    def pente(x):
        y = x[a_:b_]
        return round(float(np.max(np.abs(y[50:] - y[:-50]))), 3)
    dyn = gz["pouls_dyn_db"] + gz["reponses_db"]
    Rr = {"pouls_ducking+reponses_dB_par_50ms": pente(dyn), "pouls_creux_1-4k_dB_par_50ms": pente(gz["pouls_bande_db"]),
          "pouls_plateau_grave_dB_par_50ms": pente(gz["pouls_grave_db"]),
          "lit_rattrapages_dB_par_50ms (le lit seul)": pente(gz["lit_rattrapage_db"]),
          "gain_du_pouls_aux_accents_dB (hors arc composé)": {f"temps {n}": round(float(dyn[int(R.tb(n) * 1000)]), 2) for n in (28, 32, 43)},
          "rattrapages_appliques_au_pouls": False}
    # deuxième relecture, défaut 2 : le lit (cordes, pédale, réverbe) ne replonge plus avant la voix
    def pire_baisse(x):
        y = x[a_:b_]; d_ = y[50:] - y[:-50]; i_ = int(np.argmin(d_))
        return {"db_par_50ms": round(float(d_[i_]), 2), "t": round((a_ + i_) / 1000, 3)}
    Rr["lit_large_pire_baisse"] = pire_baisse(gz["lit_db"])
    Rr["lit_large+creux_1-4k_pire_baisse"] = pire_baisse(gz["lit_db"] + gz["lit_bande_db"])
    Rr["lit_avant_borne_large+creux_1-4k_pire_baisse"] = pire_baisse(gz["lit_dyn_avant_borne_db"] + gz["lit_bande_avant_borne_db"])
    # part du lit qui suit la voix = lit_db − (arc composé + clairière + place à la signature)
    lit_dyn = gz["lit_db"] - gz["arc_db"] + gz["reponses_db"] - gz["clairiere_db"] - gz["signature_db"]
    Rr["lit_borne_jamais_au_dessus"] = bool(np.all(gz["lit_bande_db"] <= gz["lit_bande_avant_borne_db"] + 1e-4)
                                            and np.all(lit_dyn <= gz["lit_dyn_avant_borne_db"] + 1e-4))
    Rr["ok_lit"] = bool(Rr["lit_large+creux_1-4k_pire_baisse"]["db_par_50ms"] >= -1.5 and Rr["lit_borne_jamais_au_dessus"])
    Rr["ok"] = bool(max(Rr["pouls_ducking+reponses_dB_par_50ms"], Rr["pouls_creux_1-4k_dB_par_50ms"],
                        Rr["pouls_plateau_grave_dB_par_50ms"]) <= 1.0 and Rr["ok_lit"])
    res["R_rythme"] = Rr
    # la remontée du lit, lue sur sa courbe finale (large bande, part qui suit la voix, lit_dyn ci-dessus) : le plus
    # haut du blanc moins sa valeur au dernier mot
    tt = np.arange(len(lit_dyn)) / 1000
    mots = sorted(MX.MOTS["mots"], key=lambda w: w["debut"])
    blancs = [(x["fin"], y["debut"]) for x, y in zip(mots, mots[1:]) if y["debut"] > x["fin"]]
    Lb = []
    for a0, b0 in blancs:
        m = (tt >= a0) & (tt <= b0 + 0.15)
        if m.any():
            Lb.append({"blanc": [round(a0, 2), round(b0, 2)], "duree": round(b0 - a0, 2),
                       "remontee_du_lit_db": round(float(lit_dyn[m].max() - lit_dyn[int(a0 * 1000)]), 3)})
    courts = [x for x in Lb if x["duree"] < 0.8]
    res["L_lit"] = {"pire_blanc_court": max(courts, key=lambda x: x["remontee_du_lit_db"]) if courts else None,
                    "vraies_pauses": [x for x in Lb if x["duree"] >= 0.8],
                    "ok": all(x["remontee_du_lit_db"] <= 1.5 for x in courts)}
    # T : téléphone
    tel = lambda x: S.ffmpeg_filtre(x, "highpass=f=250,highpass=f=250,lowpass=f=8000")  # noqa: E731
    nappe = labo.lire(SON / "stems" / "nappe.wav")
    tm, tn, ts, tv = K(tel(mus)), K(tel(nappe)), K(tel(st["sfx"])), K(tel(st["dialogue"]))
    fk_m, fk_n = K(mus), K(nappe)
    secs = {"sonnerie": (0.3, 4.2), "voix+ecoute": (5.0, 17.2), "agenda": (17.2, 26.1), "rendez-vous": (26.1, 35.87),
            "sms": (36.67, 42.3), "logo": (42.9, 46.7)}
    Tt = {"sections": {}}
    for nom, (a0, b0) in secs.items():
        i0, i1 = int(a0 * SR), int(b0 * SR)
        Tt["sections"][nom] = {"musique_tel": round(float(sonie(tm, i0, i1)), 2), "nappe_validee_tel": round(float(sonie(tn, i0, i1)), 2),
                               "ecart_tel_LU": round(float(sonie(tm, i0, i1) - sonie(tn, i0, i1)), 2),
                               "musique_pleine": round(float(sonie(fk_m, i0, i1)), 2), "nappe_validee_pleine": round(float(sonie(fk_n, i0, i1)), 2)}
    dans = np.zeros(N, bool)
    for w in MX.MOTS["mots"]:
        dans[int(w["debut"] * SR):int(max(w["fin"], w["debut"] + 0.12) * SR)] = True
    ti = np.arange(N) / SR
    for nom in ("agenda", "rendez-vous"):
        a0, b0 = secs[nom]
        sel = (ti >= a0) & (ti < b0)
        for lab, m in (("sous_les_mots", sel & dans), ("dans_les_blancs", sel & ~dans)):
            pm, pn = np.mean(np.sum(tm[m] ** 2, 1)), np.mean(np.sum(tn[m] ** 2, 1))
            Tt["sections"][nom][f"ecart_tel_{lab}_LU"] = round(float(10 * np.log10(pm / pn)), 2)
    i0, i1 = int(0.3 * SR), int(4.2 * SR)
    Tt["sonnerie_sfx_tel"] = round(float(sonie(ts, i0, i1)), 2)
    i0, i1 = int(20.667 * SR), int(35.87 * SR)
    Tt["couches_tel_20.67-35.87 (niveau de couche, sans ducking)"] = {"voix": round(float(sonie(tv, i0, i1)), 1)}
    if dc.exists():
        for k in ("marimba", "basse", "grosse_caisse", "shaker"):
            Tt["couches_tel_20.67-35.87 (niveau de couche, sans ducking)"][k] = round(float(sonie(K(tel(labo.lire(dc / f"{k}.wav"))), i0, i1)), 1)
    so = Tt["sections"]["sonnerie"]["musique_tel"]
    Tt["ok_logo_2LU"] = bool(Tt["sections"]["logo"]["ecart_tel_LU"] >= 2.0)
    Tt["ok_sonnerie"] = bool(so >= -40.0 and so <= Tt["sonnerie_sfx_tel"] - 12.0)
    Tt["objectif_relecture_agenda_et_rdv_+3LU"] = {
        "tenu": bool(min(Tt["sections"]["agenda"]["ecart_tel_LU"], Tt["sections"]["rendez-vous"]["ecart_tel_LU"]) >= 3.0),
        "pourquoi": "sous les mots, chaque LU de musique en plus se prend sur la marge de la voix (contrôle F, déjà à "
                    "10,4 LU comme la nappe validée à 10,3) ; dans les blancs, la nappe validée remontait par son ducking "
                    "rapide (le défaut 8) : la musique ne le fait plus, elle s'avance seulement dans les vraies pauses"}
    Tt["ok"] = Tt["ok_logo_2LU"] and Tt["ok_sonnerie"]
    res["T_telephone"] = Tt
    # S : signature
    sig_v = labo.lire(SON / "stems" / "signature.wav")
    g_v = np.load(R.STEMS_AV / "g_lim_valide.npy")
    sk, mk2 = K(st["signature"]), K(mus)
    Sg = {"clairiere_signature_moins_musique_LU": {}, "signature_contre_validee_dB": {}}
    for nom, a0, b0 in (("temps 55 → la", R.tb(55), T["la"]), ("la", T["la"], T["sol_sig"]), ("sol", T["sol_sig"], T["re"]),
                        ("ré", T["re"], T["re"] + 0.5)):
        i0, i1 = int(a0 * SR), int(b0 * SR)
        Sg["clairiere_signature_moins_musique_LU"][nom] = round(float(sonie(sk, i0, i1) - sonie(mk2, i0, i1)), 1)
    for nom, a0, b0 in (("la", T["la"], T["sol_sig"]), ("sol", T["sol_sig"], T["re"]), ("ré 0-0,1 s", T["re"], T["re"] + 0.1),
                        ("ré 0,1-0,4 s", T["re"] + 0.1, T["re"] + 0.4)):
        i0, i1 = int(a0 * SR), int(b0 * SR)
        Sg["signature_contre_validee_dB"][nom] = round(float(20 * np.log10(np.sqrt(np.mean(st["signature"][i0:i1] ** 2)) /
                                                                           np.sqrt(np.mean(sig_v[i0:i1] ** 2)))), 2)
    gl_n = gz["g_lim"].astype(np.float64)
    a0, b0 = int(42.25 * 1000), int(43.2 * 1000)
    Sg["limiteur_reduction_max_42.25-43.2_dB"] = {"variante": round(float(-20 * np.log10(gl_n[a0:b0].min())), 2),
                                                  "master_valide": round(float(-20 * np.log10(g_v[::48][a0:b0].min())), 2)}
    Sg["ok_clairiere"] = bool(min(Sg["clairiere_signature_moins_musique_LU"]["la"], Sg["clairiere_signature_moins_musique_LU"]["sol"]) >= 15.0)
    Sg["ok_un_seul_limiteur"] = bool(Sg["limiteur_reduction_max_42.25-43.2_dB"]["variante"] <= Sg["limiteur_reduction_max_42.25-43.2_dB"]["master_valide"] + 0.5
                                     and all(abs(v) <= 0.2 for v in Sg["signature_contre_validee_dB"].values()))
    # deuxième relecture, défauts 1 et 3 : le la · sol de la plume, et la résonance du ré de marque
    def bande_etroite(x, a0, b0, fc, bw=0.015):
        i0, i1 = int(a0 * SR), int(b0 * SR)
        s_ = x[i0:i1].mean(axis=1) * np.hanning(i1 - i0)
        X = np.abs(np.fft.rfft(s_, 1 << 17)) ** 2; fq = np.fft.rfftfreq(1 << 17, 1 / SR)
        return 10 * np.log10(X[(fq >= fc * (1 - bw)) & (fq <= fc * (1 + bw))].sum() + 1e-30)

    def ecart(a0, b0, fc):
        return round(float(bande_etroite(st["signature"], a0, b0, fc) - bande_etroite(mus, a0, b0, fc)), 1)

    pl_la, pl_sol = R.T_PLUME_LA, R.T_PLUME_SOL
    plume = {"instants": [round(pl_la, 3), round(pl_sol, 3)],
             "bande_440_sur_la_dB": ecart(pl_la, pl_sol, 440.0), "bande_392_sur_sol_dB": ecart(pl_sol, pl_sol + 0.26, 392.0),
             "sonie_K_la_LU": round(float(sonie(sk, int(pl_la * SR), int(pl_sol * SR)) - sonie(mk2, int(pl_la * SR), int(pl_sol * SR))), 1),
             "sonie_K_sol_LU": round(float(sonie(sk, int(pl_sol * SR), int((pl_sol + 0.26) * SR))
                                           - sonie(mk2, int(pl_sol * SR), int((pl_sol + 0.26) * SR))), 1)}
    # attaques : trames de 2,5 ms ; montée ≥ 10 dB entre [τ − 20 ; τ − 2,5 ms] et [τ ; τ + 5 ms], à moins de 50 dB du
    # plus fort de la couche sur tout le film ; cherchées à ±120 ms de chaque note, dans chaque couche
    att = []
    if dc.exists():
        h = 120
        for fch in sorted(dc.glob("*.wav")):
            x = labo.lire(fch)
            e_ = np.sum(x[:len(x) // h * h].reshape(-1, h, 2) ** 2, axis=(1, 2)) / h
            ldb = 10 * np.log10(e_ + 1e-30); plafond = ldb.max()
            for p_ in (pl_la, pl_sol):
                j0, j1 = int((p_ - 0.12) * SR) // h, int((p_ + 0.12) * SR) // h
                for j in range(j0, j1):
                    apres = 10 * np.log10(np.mean(e_[j:j + 2]) + 1e-30); avant = 10 * np.log10(np.mean(e_[j - 8:j - 1]) + 1e-30)
                    if apres - avant >= 10 and apres >= plafond - 50:
                        att.append({"couche": fch.stem, "t": round(j * h / SR, 4), "montee_db": round(float(apres - avant), 1)})
                        break
    plume["attaques_de_musique_a_120ms"] = att
    # et dans la partition (toutes les notes posées, cues-musique.json « attaques ») : le détecteur ci-dessus ne voit pas
    # une note grave jouée legato
    notes_ = json.loads((R.ICI / "cues-musique.json").read_text()).get("attaques", [])
    plume["notes_de_la_partition_a_120ms"] = [a_ for a_ in notes_ if min(abs(a_["t"] - pl_la), abs(a_["t"] - pl_sol)) <= 0.12]
    plume["notes_posees_dans_le_registre"] = len(notes_)
    plume["ok"] = bool(not att and notes_ and not plume["notes_de_la_partition_a_120ms"] and plume["bande_440_sur_la_dB"] >= 18 and plume["bande_392_sur_sol_dB"] >= 18
                       and plume["sonie_K_la_LU"] >= 6 and plume["sonie_K_sol_LU"] >= 6)
    Sg["plume"] = plume
    re_ = {"587_sur_43.1-44.1_dB": ecart(43.1, 44.1, 587.33), "587_sur_44.1-44.6_dB": ecart(44.1, 44.6, 587.33),
           "1175_sur_43.1-44.1_dB": ecart(43.1, 44.1, 1174.66), "587_sur_42.9-43.1_dB": ecart(42.9, 43.1, 587.33)}
    re_["ok"] = bool(re_["587_sur_43.1-44.1_dB"] >= 12 and re_["587_sur_44.1-44.6_dB"] >= 6 and re_["1175_sur_43.1-44.1_dB"] >= 6)
    Sg["resonance_du_re"] = re_
    Sg["ok"] = Sg["ok_clairiere"] and Sg["ok_un_seul_limiteur"] and plume["ok"] and re_["ok"]
    res["S_signature"] = Sg
    # V : verre contre marimba
    if dc.exists():
        def bandE(x, a0, b0, f1, f2):
            s_ = x[int(a0 * SR):int(b0 * SR)].mean(axis=1)
            X = np.fft.rfft(s_); fq = np.fft.rfftfreq(len(s_), 1 / SR)
            return 10 * np.log10(np.sum(np.abs(X[(fq >= f1) & (fq <= f2)]) ** 2) + 1e-20)
        v_, m_ = labo.lire(dc / "verre.wav"), labo.lire(dc / "marimba.wav")
        Vv = {nom: round(float(bandE(v_, a0, b0, 600, 1000) - bandE(m_, a0, b0, 600, 1000)), 1)
              for nom, a0, b0 in (("38,3-39,3", 38.3, 39.3), ("la5", 38.3, 38.54), ("sol5", 38.54, 38.9), ("mi5", 38.9, 39.3))}
        res["V_verre_moins_marimba_600-1000_dB"] = {**Vv, "ok": bool(Vv["38,3-39,3"] >= 10.0)}
    # P
    if R.SORTIE_MP4.exists():
        pv, pr = sonde(R.SORTIE_MP4), sonde(R.VIDEO)
        a = [s for s in pv["streams"] if s["codec_type"] == "audio"][0]
        v = [s for s in pv["streams"] if s["codec_type"] == "video"][0]
        v0 = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
        P = {"hash_video_nouveau": hash_video(R.SORTIE_MP4), "hash_video_origine": hash_video(R.VIDEO),
             "video_images": v.get("nb_frames"), "video_duree": v.get("duration"), "origine_images": v0.get("nb_frames"),
             "audio": {k: a.get(k) for k in ("codec_name", "sample_rate", "channels", "bit_rate", "duration")}}
        # décalage de la piste audio du MP4 contre la piste d'origine (le dialogue est dans les deux), 5 → 35 s
        def piste_audio(ch):
            r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ch), "-map", "0:a", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                               capture_output=True, check=True)
            return np.frombuffer(r.stdout, dtype="<f4").astype(np.float64)
        an, ao = piste_audio(R.SORTIE_MP4), piste_audio(R.VIDEO)
        seg_n, seg_o = an[5 * SR:35 * SR], ao[5 * SR:35 * SR]
        L = 1 << (len(seg_n) * 2 - 1).bit_length()
        xc = np.fft.irfft(np.fft.rfft(seg_n, L) * np.conj(np.fft.rfft(seg_o, L)), L)
        lag = int(np.argmax(np.concatenate([xc[-2000:], xc[:2001]]))) - 2000
        P["decalage_audio_contre_origine_echantillons"] = lag
        P["echantillons_audio"] = [len(an), len(ao)]
        P["ok"] = (P["hash_video_nouveau"] == P["hash_video_origine"] and a["sample_rate"] == "48000" and a["channels"] == 2
                   and lag == 0)
        res["P_mp4"] = P
    res["synthese_ok"] = {k: v.get("ok") for k, v in res.items() if isinstance(v, dict) and "ok" in v}
    res["synthese_ok"]["C_somme"] = res["C_somme_moins_mix_max"] < 1e-5
    (ICI / "mesures-musique.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float))
    if images:
        IMG.mkdir(parents=True, exist_ok=True)
        rep = {k: (EV[k]["t"][0] if isinstance(EV[k]["t"], list) else EV[k]["t"]) for k in
               ("decroche", "contact_neuf", "contact_dix", "contact_onze", "ecriture_debut", "resolution_confirmation", "raccroche",
                "bulle_et_vibreur", "signature_la", "signature_re_contact")}
        courbe_png(pts, IMG / "arc-musique.png", rep, "variante musique")
        _, p0 = ME.rapport_court(SON / "mix.wav")
        courbe_png(p0, IMG / "arc-actuel.png", rep, "master actuel (nappe de verre)")
        # la même courbe au téléphone simulé (passe-haut 250 Hz 24 dB/oct, passe-bas 8 kHz), variante et master validé
        def pts_tel(x):
            xk = K(S.ffmpeg_filtre(x, "highpass=f=250,highpass=f=250,lowpass=f=8000"))
            p_ = np.sum(xk ** 2, axis=1); c_ = np.concatenate([[0.0], np.cumsum(p_)])
            h_ = int(0.1 * SR); fins = np.arange(h_, N + 1, h_)
            def fen(w_):
                d_ = np.maximum(fins - w_, 0)
                return -0.691 + 10 * np.log10((c_[fins] - c_[d_]) / w_ + 1e-20)
            return np.stack([fins / SR, fen(int(0.4 * SR)), fen(int(3 * SR))], axis=1)
        courbe_png(pts_tel(mix), IMG / "arc-musique-telephone.png", rep, "variante musique, téléphone simulé")
        courbe_png(pts_tel(labo.lire(SON / "mix.wav")), IMG / "arc-actuel-telephone.png", rep, "master validé, téléphone simulé")
        ME.spectro(mixp, IMG / "spectro-mix.png", titre="mix variante musique", px_par_s=30, haut=420)
        ME.spectro(R.STEMS_OUT / "musique.wav", IMG / "spectro-musique.png", titre="stem musique seul", px_par_s=30, haut=420)
        ME.spectro(mixp, IMG / "spectro-agenda.png", 17.0, 27.0, titre="agenda (17 → 27 s)", px_par_s=120, haut=460)
        ME.spectro(mixp, IMG / "spectro-fin.png", 35.0, 47.0, titre="SMS et logo (35 → 47 s)", px_par_s=110, haut=460)
    print(json.dumps(res["synthese_ok"], ensure_ascii=False))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", action="store_true")
    main(ap.parse_args().images)
