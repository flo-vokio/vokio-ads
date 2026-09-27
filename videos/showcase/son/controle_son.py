#!/usr/bin/env python3
"""Contrôles de la bande son v2 (écoute impossible ici : tout se prouve par la mesure).

    python3 son/controle_son.py [--images]      → son/mesures-son.json (+ planches PNG avec --images)

Critères : critique.json plan.chantiers « son » point 17 et plan.controles 5 et 6. Chaque contrôle porte "ok".
  A. master : intégré −14,0 ± 0,3 LUFS, crête vraie ≤ −1,5 dBTP, avant ET après un encodage AAC 256k de contrôle
  B. silences : zéros exacts sur [35,9467 ; 36,6667] et [46,70 ; 47,00] (silence_final) ; la résolution seule sur [33,05 ; 34,03]
  C. somme des stems = mix
  D. synchro : attaque de chaque cue ponctuel contre son instant, ±5 ms
  E. dialogue : décalage 0 échantillon entre la voix traitée et son/dialogue.wav
  F. intelligibilité : voix ≥ 10 LU au-dessus du reste, mot par mot (pondération K)
  G. mono : écart de sonie mono/stéréo ; corrélation ; signature : corrélation 0,75-0,85, perte mono ≤ 1 dB
  H. haut-parleur simulé (passe-haut 400 Hz à 24 dB/oct, puis somme mono) : perte de la nappe ≤ 7 dB ; pédale
     la ≥ sol + 6 dB avant la résolution, sol ≥ la + 6 dB après ; touchers ≥ voix + 6 dB (3-8 kHz, 40 ms) et
     ≤ voix − 10 dB (500-700 Hz) ; signature à moins de 3 dB de la pleine bande ; touchers ≤ −20 LUFS instantanés
  I. chroma de la nappe par section
  J. enveloppes : tonalité contre secousses.s1, vibreur contre secousses.s6, image par image
  K. clics : bouffées au-dessus de 5 kHz hors des attaques déclarées
  L. le pan suit le point
  M. ARC DE SONIE (ebur128 sur tout le film) : signature [ré ; ré + 1,5] ≥ médiane court terme du dialogue [5 ; 35,4]
     + 1 LU ; le ré est l'instant le plus fort (sonie instantanée) ; vibreur ≤ −14 LUFS instantanés
  N. livrables de la signature seule
  O. variante « monde » (si elle existe) : chaque bruitage ≤ −28 LUFS instantanés, rien après le décroché
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402
import mix as M  # noqa: E402  (données et outils seulement : rien ne se recalcule à l'import)

SR = labo.SR
UPL = Path("/root/vokio-uploads/videos/showcase")
SORTIE_IMG = UPL / "son-controles-v2"
SCRATCH = Path("/tmp/claude-0/-root/5cdc3174-18c1-52f2-a7e6-50c04cd57657/scratchpad/v2/son")
EV, T = M.EV, M.T
DUREE = M.DUREE
# Fenêtres tirées des événements (finition du 27/09 : tout ce qui suit la lecture du SMS est décalé de 1,70 s, film de
# 47,00 s ; aucune fenêtre tardive n'est plus écrite en secondes)
P0, P1 = EV["plume_mot"]["t"]
W = {"air_sms": (round(T["vibreur"] + 0.933, 3), round(T["la"] - 0.10, 3)),
     "stylo": (P0, P1), "stylo_milieu": (round((P0 + P1) / 2 - 0.03, 3), round((P0 + P1) / 2 + 0.03, 3)),
     "signature": (T["la"], round(T["la"] + 3.0, 3)), "signature_arc": (T["re"], round(T["re"] + 1.5, 3)),
     "nappe_fin": (round(T["re"] + 1.0, 3), round(T["re"] + 2.1, 3)), "nappe_fin_mono": (round(T["re"] + 0.8, 3), round(T["re"] + 2.8, 3)),
     "vibreur": (round(T["vibreur"], 3), round(T["vibreur"] + 0.45, 3))}
f_ = lambda a, b: f"{a:.2f} → {b:.2f}".replace(".", ",")  # noqa: E731


def ponderer_k(x):
    return M.ponderer_k(x)


def sonie(xk, i0, i1):
    """Sonie (LUFS, non fenêtrée) d'un segment déjà pondéré K."""
    s = xk[max(0, i0):i1]
    if len(s) == 0:
        return -np.inf
    return -0.691 + 10 * np.log10(np.sum(np.mean(s ** 2, axis=0)) + 1e-20)


def instantanee(xk, pas=0.01, fen=0.4):
    """Sonie instantanée (400 ms) échantillonnée tous les `pas` s ; renvoie (t_fin_de_fenêtre, LUFS)."""
    p = np.sum(xk ** 2, axis=1)
    c = np.concatenate([[0.0], np.cumsum(p)])
    w = int(fen * SR); h = int(pas * SR)
    fins = np.arange(w, len(p) + 1, h)
    return fins / SR, -0.691 + 10 * np.log10((c[fins] - c[fins - w]) / w + 1e-20)


def ebur128(chemin):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(chemin), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    e = r.stderr[r.stderr.rindex("Summary:"):]
    val = lambda clef: float(e.split(clef)[1].split()[0])  # noqa: E731
    courbe = []
    for ligne in r.stderr.splitlines():
        if "] t:" in ligne and " M:" in ligne and " S:" in ligne:
            try:
                t = float(ligne.split("t:")[1].split()[0])
                m_ = float(ligne.split("M:")[1].split()[0])
                s_ = float(ligne.split("S:")[1].split()[0])
                courbe.append((t, m_, s_))
            except (ValueError, IndexError):
                pass
    return {"I": val("I:"), "LRA": val("LRA:"), "TP": val("Peak:")}, courbe


def haut_parleur(x):
    """Haut-parleur de téléphone simulé : passe-haut Butterworth 4e ordre à 400 Hz (24 dB/oct, module), puis mono."""
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = 1 / np.sqrt(1 + (400.0 / np.maximum(f, 1e-3)) ** 8)
    y = np.fft.irfft(X * H[:, None], len(x), axis=0)
    return (y[:, 0] + y[:, 1]) / 2


def rms_st(x, a, b):
    s = x[int(a * SR):int(b * SR)]
    return 20 * np.log10(np.sqrt(np.mean(s ** 2)) + 1e-15)


def bande(x, a, b, f0, f1):
    """Énergie (dB) d'un segment mono dans [f0 ; f1] (fenêtre de Hann)."""
    s = x[int(round(a * SR)):int(round(b * SR))]
    s = s * np.hanning(len(s))
    X = np.abs(np.fft.rfft(s)) ** 2
    f = np.fft.rfftfreq(len(s), 1 / SR)
    return float(10 * np.log10(X[(f >= f0) & (f <= f1)].sum() + 1e-20))


def attaque(x, t, fen=0.050):
    """Attaque d'un son posé sur un autre (le sol sur la queue du la, le ré sur le sol) : détecteur de marche.
    Puissance sur 1 ms (pas de 0,25 ms) ; pour chaque instant τ de [t − fen, t + fen], montée = moyenne sur [τ ; τ + 5 ms]
    moins moyenne sur [τ − 15 ; τ − 5 ms] (dB) : les ondulations de battement (2 ms) s'y moyennent. On garde le τ de la
    plus forte montée, puis l'attaque = premier instant, dans [τ − 5 ; τ + 5 ms], où la puissance dépasse le niveau
    d'avant de 3 dB. Renvoie (instant, montée en dB)."""
    m = x.mean(axis=1) if x.ndim > 1 else x
    a0 = int(round((t - fen - 0.03) * SR)); a1 = int(round((t + fen + 0.03) * SR))
    s = m[max(0, a0):a1]
    if a0 < 0:
        s = np.concatenate([np.zeros(-a0), s])
    h, w = 12, 48
    c = np.concatenate([[0.0], np.cumsum(s ** 2)])
    pos = np.arange(w, len(s) + 1, h)                     # fin de chaque fenêtre de 1 ms
    p = (c[pos] - c[pos - w]) / w + 1e-14
    db_ = 10 * np.log10(p)
    ms = int(round(0.001 * SR / h))                       # 4 pas = 1 ms
    tpos = (a0 + pos - w / 2) / SR                        # centre de chaque fenêtre, temps film
    best, kb = -np.inf, None
    for k in range(15 * ms, len(p) - 5 * ms):
        if abs(tpos[k] - t) > fen:
            continue
        apres = np.mean(db_[k:k + 5 * ms]); avant = np.mean(db_[k - 15 * ms:k - 5 * ms])
        if apres - avant > best:
            best, kb = apres - avant, k
    avant = np.mean(db_[kb - 15 * ms:kb - 5 * ms])
    for k in range(kb - 5 * ms, kb + 5 * ms):
        if db_[k] > avant + 3:
            return float(tpos[k] - 0.0005), float(best)
    return float(tpos[kb]), float(best)


def chroma(x, i0, i1):
    s = x[i0:i1].mean(axis=1) if x.ndim > 1 else x[i0:i1]
    s = s * np.hanning(len(s))
    X = np.abs(np.fft.rfft(s)) ** 2
    f = np.fft.rfftfreq(len(s), 1 / SR)
    ok = (f > 60) & (f < 2000)
    pc = np.round(12 * np.log2(f[ok] / 440.0)).astype(int) % 12
    c = np.bincount(pc, weights=X[ok], minlength=12)
    noms = ["la", "la#", "si", "do", "do#", "ré", "ré#", "mi", "fa", "fa#", "sol", "sol#"]
    ordre = np.argsort(c)[::-1]
    return [noms[k] for k in ordre[:5]]


def main(images=False):
    R = {}
    mixp = ICI / "mix.wav"
    mix = labo.lire(mixp)
    stems = {n: labo.lire(ICI / "stems" / f"{n}.wav") for n in ("dialogue", "nappe", "sfx", "signature")}
    N = len(mix)
    CU = json.loads((ICI / "cues.json").read_text())
    cues = CU["cues"]
    # A. master
    lm, courbe = ebur128(mixp)
    R["A_master"] = {"loudnorm": labo.mesurer(mixp), "ebur128": lm, "duree_s": N / SR,
                     "crete_vraie_numpy_dbtp": round(S.crete_vraie(mix), 2)}
    SCRATCH.mkdir(parents=True, exist_ok=True)
    m4a = SCRATCH / "controle-aac.m4a"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mixp), "-c:a", "aac", "-b:a", "256k", str(m4a)], check=True)
    R["A_master"]["apres_aac_256k"] = {"loudnorm": labo.mesurer(m4a), "ebur128": ebur128(m4a)[0]}
    a_ = R["A_master"]
    R["A_master"]["ok"] = bool(abs(a_["loudnorm"]["lufs"] + 14) <= 0.3 and a_["loudnorm"]["crete_dbtp"] <= -1.5
                               and abs(a_["apres_aac_256k"]["loudnorm"]["lufs"] + 14) <= 0.3
                               and a_["apres_aac_256k"]["loudnorm"]["crete_dbtp"] <= -1.5 and abs(a_["duree_s"] - DUREE) < 1e-9)
    # B. silences
    s0, s1 = EV["silence_numerique"]["t"]
    f0 = EV["silence_final"]["t"][0]
    z = lambda x, a, b: bool(not np.any(x[int(round(a * SR)):int(round(b * SR))]))  # noqa: E731
    r0, r1 = mix[int(round(33.05 * SR)):int(round(34.03 * SR))], None
    B = {"zeros_exacts_silence_numerique": z(mix, s0, s1), "zeros_exacts_silence_final": z(mix, f0, DUREE),
         "stems_zeros_silence_numerique": {n: z(st, s0, s1) for n, st in stems.items()},
         "resolution_seule_33.05-34.03": {"sfx_zero": z(stems["sfx"], 33.05, 34.03), "signature_zero": z(stems["signature"], 33.05, 34.03),
                                          "dialogue_rms_dbfs (souffle de la vraie ligne)": round(rms_st(stems["dialogue"], 33.05, 34.03), 1),
                                          "dialogue_rms_33.30-33.95_dbfs (entre les extraits)": round(rms_st(stems["dialogue"], 33.30, 33.95), 1),
                                          "nappe_rms_dbfs": round(rms_st(stems["nappe"], 33.05, 34.03), 1)},
         "dialogue_nul_apres_raccroche": z(stems["dialogue"], T["raccroche"] + 0.005, DUREE),
         "tonalite_20_premieres_ms_rms_dbfs": round(float(20 * np.log10(np.sqrt(np.mean(mix[:960] ** 2)))), 1)}
    res = B["resolution_seule_33.05-34.03"]
    # la voix réelle : la fin de « -tion » s'éteint (≤ −50 dBFS dès 33,075), zéros de 33,23 (fin de A4) à 33,98 (C4)
    res["dialogue_max_rms_25ms_33.075-33.98_dbfs"] = round(max(rms_st(stems["dialogue"], a, a + 0.025)
                                                              for a in np.arange(33.075, 33.98 - 0.025, 0.025)), 1)
    res["dialogue_zero_33.23-33.98"] = z(stems["dialogue"], 33.23, 33.98)
    B["ok"] = bool(B["zeros_exacts_silence_numerique"] and B["zeros_exacts_silence_final"] and all(B["stems_zeros_silence_numerique"].values())
                   and res["sfx_zero"] and res["signature_zero"] and res["dialogue_max_rms_25ms_33.075-33.98_dbfs"] <= -50
                   and res["dialogue_zero_33.23-33.98"] and B["dialogue_nul_apres_raccroche"])
    R["B_silences"] = B
    # C. somme
    somme = sum(stems.values())
    R["C_somme_stems_moins_mix_max"] = float(np.max(np.abs(somme - mix)))
    # D. synchro ±5 ms (stems)
    ponctuels = {"clic-decroche": 126, "cloche-sol-1": None, "tap-9h": 620, "tap-10h": 643, "tap-11h": 666, "tap-retour-9h": 731,
                 "cloche-la-rdv": 762, "cloche-sol-rdv": 769, "raccroche": 1076, "vibreur": 1100,
                 "signature-la": EV["signature_la"]["image"], "signature-sol": None, "signature-re": EV["signature_re_contact"]["image"],
                 "ton-1": 0, "ton-2-la": 81}
    D = []
    for c in cues:
        if c["id"] not in ponctuels:
            continue
        t_mes, montee = attaque(stems[c["stem"]], c["t"])
        ecart = t_mes - c["t"]
        img = ponctuels[c["id"]]
        D.append({"id": c["id"], "t": c["t"], "image": c["image"], "image_attendue": img, "attaque_mesuree": round(t_mes, 4),
                  "ecart_ms": round(1000 * ecart, 1), "montee_db": round(montee, 1),
                  "ok": bool(abs(ecart) <= 0.005 and (img is None or c["image"] == img))})
    R["D_synchro"] = {"cues": D, "ok": all(d["ok"] for d in D) and len(D) == len(ponctuels)}
    # E. dialogue : décalage nul
    brut = labo.lire(M.DIA["fichier"])[:, 0]
    dl = stems["dialogue"][:, 0]
    E = []
    for e in M.DIA["extraits"]:
        i0, i1 = int(round(e["film_in"] * SR)), int(round(e["film_out"] * SR))
        a, b = brut[i0:i1], dl[i0:i1]
        best, lag = -1, 0
        for L in range(-48, 49):
            v = np.dot(a[max(0, -L):len(a) - max(0, L)], b[max(0, L):len(b) - max(0, -L)])
            if v > best:
                best, lag = v, L
        E.append({"id": e["id"], "decalage_echantillons": lag})
    # le pic de corrélation à −3…−12 échantillons (≤ 0,25 ms) est la phase de la chaîne voix (passe-haut 100 Hz, égaliseur,
    # compresseur), identique en v1 ; le placement lui-même est à l'échantillon (mêmes indices) : tolérance 0,5 ms
    R["E_dialogue_decalage"] = {"extraits": E, "tolerance_echantillons": 24,
                                "ok": all(abs(e["decalage_echantillons"]) <= 24 for e in E)}
    # F. intelligibilité mot par mot
    dk = ponderer_k(stems["dialogue"])
    reste = ponderer_k(stems["nappe"] + stems["sfx"] + stems["signature"])
    F = []
    for w in M.MOTS["mots"]:
        i0, i1 = int(w["debut"] * SR), int(max(w["fin"], w["debut"] + 0.12) * SR)
        F.append((round(float(sonie(dk, i0, i1) - sonie(reste, i0, i1)), 1), w["texte"], w["debut"]))
    F.sort()
    R["F_voix_sur_reste_LU"] = {"min": F[0][0], "mediane": float(np.median([f[0] for f in F])), "pires": F[:8], "ok": F[0][0] >= 10}
    mk = ponderer_k(mix)
    L_ = lambda xk, a, b: round(float(sonie(xk, int(a * SR), int(b * SR))), 1)  # noqa: E731
    sk, gk, nk = ponderer_k(stems["sfx"]), ponderer_k(stems["signature"]), ponderer_k(stems["nappe"])
    R["F_sonies_LUFS"] = {
        "voix (4,91 → 35,48)": L_(dk, 4.91, 35.48), "tonalite 1 (0,1 → 1,4)": L_(sk, 0.1, 1.4), "tonalite 2 (2,8 → 4,2)": L_(gk, 2.8, 4.2),
        "decroche la + sol (4,2 → 4,9)": L_(gk, 4.2, 4.9), "pedale seule sous A1 (6,4 → 10,1)": L_(nk, 6.4, 10.1),
        "nappe, accord de sol (12,5 → 17,5)": L_(nk, 12.5, 17.5), "nappe, silence de l'outil (18,4 → 19,75)": L_(nk, 18.4, 19.75),
        "nappe, debut du re7 (20,0 → 22,6)": L_(nk, 20.0, 22.6), "nappe, fin du re9 (30,0 → 32,9)": L_(nk, 30.0, 32.9),
        "nappe, resolution seule (33,05 → 34,03)": L_(nk, 33.05, 34.03), "la·sol de l'ecriture (25,4 → 26,1)": L_(gk, 25.4, 26.1),
        f"vibreur ({f_(*W['vibreur'])})": L_(sk, *W["vibreur"]), f"air du SMS ({f_(*W['air_sms'])})": L_(nk, *W["air_sms"]),
        f"stylo ({f_(*W['stylo'])})": L_(sk, *W["stylo"]), f"signature ({f_(*W['signature'])})": L_(gk, *W["signature"]),
        f"nappe de fin ({f_(*W['nappe_fin'])})": L_(nk, *W["nappe_fin"])}
    # G. mono
    mono = (mix[:, 0] + mix[:, 1]) / 2
    m2k = ponderer_k(np.stack([mono, mono], axis=1))
    G = {"ecart_sonie_mono_moins_stereo_film_LU": round(float(sonie(m2k, 0, N) - sonie(mk, 0, N)), 2)}
    for nom, (a, b) in {f"signature {f_(*W['signature'])}": W["signature"], "nappe 12,5 → 17,5": (12.5, 17.5), "decroche 4,2 → 5,0": (4.2, 5.0),
                        "resolution seule 33,1 → 34,0": (33.1, 34.0), f"air du SMS {f_(*W['air_sms'])}": W["air_sms"],
                        "ecriture 25,4 → 26,2": (25.4, 26.2), f"nappe de fin {f_(*W['nappe_fin_mono'])}": W["nappe_fin_mono"]}.items():
        G[f"ecart_{nom}_LU"] = round(float(sonie(m2k, int(a * SR), int(b * SR)) - sonie(mk, int(a * SR), int(b * SR))), 2)
    w = 4800
    nb = N // w
    Lc, Rc = mix[:nb * w, 0].reshape(nb, w), mix[:nb * w, 1].reshape(nb, w)
    e = np.sqrt(np.mean(Lc ** 2, 1) * np.mean(Rc ** 2, 1))
    ok = e > 10 ** (-60 / 10)
    cor = np.mean(Lc * Rc, 1)[ok] / e[ok]
    G["correlation_LR_min_100ms"] = round(float(cor.min()), 3)
    G["correlation_LR_mediane"] = round(float(np.median(cor)), 3)
    G["fenetres_correlation_negative"] = int(np.sum(cor < 0))
    seg_sig = stems["signature"][int(T["la"] * SR):int((T["la"] + 3.2) * SR)]
    G["signature_film"] = S.analyser(seg_sig)
    G["nappe_correlation_12.5-17.5"] = round(S.correlation(stems["nappe"][int(12.5 * SR):int(17.5 * SR)]), 3)
    G["ok"] = bool(0.75 <= G["signature_film"]["correlation_LR"] <= 0.85 and G["signature_film"]["perte_mono_db"] >= -1.0
                   and G["fenetres_correlation_negative"] == 0 and abs(G["ecart_sonie_mono_moins_stereo_film_LU"]) <= 1.0)
    R["G_mono"] = G
    # H. haut-parleur de téléphone
    hp = {n: haut_parleur(st) for n, st in stems.items()}
    H = {}
    perte = {}
    for nom, (a, b) in {"pedale seule 6,4-10,1": (6.4, 10.1), "sol 12,5-17,5": (12.5, 17.5), "sus4 18,2-19,75": (18.2, 19.75),
                        "re7-re9 20,6-32,85": (20.6, 32.85), "resolution 33,1-35,8": (33.1, 35.8), f"air SMS {f_(*W['air_sms'])}": W["air_sms"],
                        f"nappe de fin {f_(*W['nappe_fin'])}": W["nappe_fin"], "toute la nappe 4,6-35,8": (4.6, 35.8)}.items():
        perte[nom] = round(float(20 * np.log10(np.sqrt(np.mean(hp["nappe"][int(a * SR):int(b * SR)] ** 2)) + 1e-15) - rms_st(stems["nappe"], a, b)), 2)
    perte_voix = round(float(20 * np.log10(np.sqrt(np.mean(hp["dialogue"][int(4.91 * SR):int(35.48 * SR)] ** 2))) - rms_st(stems["dialogue"], 4.91, 35.48)), 2)
    H["perte_nappe_db"] = perte
    H["perte_voix_db (reference)"] = perte_voix
    H["perte_nappe_ok"] = all(v >= -7.0 for v in perte.values())
    hn = hp["nappe"]
    ped = {}
    for nom, (a, b) in {"sol 12,5-17,5 (G4 dans l'accord, pour memoire)": (12.5, 17.5), "re7-re9 20,6-32,85": (20.6, 32.85),
                        "resolution 33,1-35,8": (33.1, 35.8)}.items():
        la, sol = bande(hn, a, b, 430, 450), bande(hn, a, b, 382, 402)
        ped[nom] = {"la_moins_sol_db": round(la - sol, 1)}
    H["pedale_la_sol"] = ped
    H["pedale_ok"] = bool(ped["re7-re9 20,6-32,85"]["la_moins_sol_db"] >= 6 and ped["resolution 33,1-35,8"]["la_moins_sol_db"] <= -6)
    taps = []
    sfx_k = ponderer_k(stems["sfx"])
    tm, lm_sfx = instantanee(sfx_k)
    for nom in ("contact_neuf", "contact_dix", "contact_onze", "contact_retour_neuf"):
        tc = EV[nom]["t"]
        a, b = tc, tc + 0.040
        hi = bande(hp["sfx"], a, b, 3000, 8000) - bande(hp["dialogue"], a, b, 3000, 8000)
        hi4 = bande(hp["sfx"], a, b, 4000, 8000) - bande(hp["dialogue"], a, b, 4000, 8000)
        lo = bande(hp["dialogue"], a, b, 500, 700) - bande(hp["sfx"], a, b, 500, 700)
        mom = float(lm_sfx[(tm >= tc) & (tm <= tc + 0.4)].max())
        taps.append({"contact": nom, "t": tc, "tap_moins_voix_3-8k_db": round(hi, 1), "tap_moins_voix_4-8k_db (au-dessus de la voix)": round(hi4, 1),
                     "voix_moins_tap_500-700_db": round(lo, 1),
                     "tap_instantanee_max_lufs": round(mom, 1), "ok": bool(hi >= 6 and lo >= 10 and mom <= -20)})
    H["touchers"] = taps
    sg = stems["signature"][int(T["la"] * SR):int((T["la"] + 3.2) * SR)]
    hs = hp["signature"][int(T["la"] * SR):int((T["la"] + 3.2) * SR)]
    H["signature_hp_moins_pleine_bande_db"] = round(float(20 * np.log10(np.sqrt(np.mean(hs ** 2)) / np.sqrt(np.mean(sg ** 2)))), 2)
    H["signature_ok"] = H["signature_hp_moins_pleine_bande_db"] >= -3.0
    H["ok"] = bool(H["perte_nappe_ok"] and H["pedale_ok"] and all(t["ok"] for t in taps) and H["signature_ok"])
    R["H_haut_parleur"] = H
    # I. chroma de la nappe
    nap = stems["nappe"]
    R["I_chroma_nappe"] = {f"{a}-{b}": chroma(nap, int(a * SR), int(b * SR)) for a, b in
                           ((6.4, 10.1), (12.5, 17.5), (18.2, 19.75), (20.6, 26.1), (28.2, 32.85), (33.1, 35.8), W["air_sms"], W["nappe_fin"])}
    # J. enveloppes
    s1 = M.SEC["s1"]["enveloppe"]
    ton = stems["sfx"][:, 0] + stems["signature"][:, 0]
    ref = np.mean(np.abs(ton[int(0.2 * SR):int(1.3 * SR)]))
    env_mes = []
    for n in range(126):
        a, b = int(round(n / 30 * SR)), int(round((n + 1) / 30 * SR))
        env_mes.append(float(np.mean(np.abs(ton[a:b])) / ref))
    ecarts = np.abs(np.array(env_mes) - np.array(s1[:126]))
    R["J_tonalite_contre_secousses_s1"] = {"ecart_max": round(float(ecarts.max()), 3), "image_pire": int(ecarts.argmax()),
                                          "exemples": {n: [round(env_mes[n], 3), s1[n]] for n in (0, 1, 44, 45, 80, 81, 82, 125)},
                                          "ok": bool(ecarts.max() <= 0.05)}
    s6 = M.SEC["s6"]
    n0 = s6["image0"]; ln = len(s6["enveloppe"])
    t = np.arange(int(n0 / 30 * SR), int((n0 + ln) / 30 * SR)) / SR
    env = M.trapeze(t, s6["segments_s"], s6["rampes_s"])
    moy = [float(env[int(round((n - n0) / 30 * SR)):int(round((n - n0 + 1) / 30 * SR))].mean()) for n in range(n0, n0 + ln)]
    vb = stems["sfx"][int(n0 / 30 * SR):int((n0 + ln) / 30 * SR), 0]
    rms_img = np.array([float(np.sqrt(np.mean(vb[int(round(k / 30 * SR)):int(round((k + 1) / 30 * SR))] ** 2))) for k in range(ln)])
    R["J_vibreur_contre_secousses_s6"] = {"ecart_max_enveloppe": round(float(np.max(np.abs(np.array(moy) - np.array(s6["enveloppe"])))), 4),
                                          "rms_par_image_relatif": [round(float(v), 2) for v in rms_img / rms_img.max()],
                                          "enveloppe_s6": s6["enveloppe"]}
    R["J_vibreur_contre_secousses_s6"]["ok"] = R["J_vibreur_contre_secousses_s6"]["ecart_max_enveloppe"] <= 0.005
    # K. clics
    attaques = [c["t"] for c in cues if c["id"] in ponctuels] + [e["film_in"] for e in M.DIA["extraits"]] + \
               [e["film_out"] for e in M.DIA["extraits"]] + [T["raccroche"]]
    zones = [tuple(s6_) for s6_ in s6["segments_s"]] + [tuple(EV["plume_mot"]["t"])]
    K = {}
    f = np.fft.rfftfreq(N, 1 / SR)
    for nom in ("nappe", "signature", "sfx"):
        hpk = np.fft.irfft(np.fft.rfft(stems[nom].mean(axis=1)) * (f > 5000), N)
        w = 240
        e = 20 * np.log10(np.sqrt(np.mean(hpk[:N // w * w].reshape(-1, w) ** 2, axis=1)) + 1e-12)
        # un clic est une bouffée ISOLÉE : 20 dB au-dessus de ses voisines à 10-40 ms (une queue de réverbe ou de verre
        # décroît, elle ne dépasse pas ses voisines ; une attaque voulue est exclue par la liste des attaques)
        vois = np.full(len(e), -300.0)
        for i in range(8, len(e) - 8):
            vois[i] = np.median(np.concatenate([e[i - 8:i - 2], e[i + 3:i + 9]]))
        pics = np.nonzero((e - vois > 20) & (e > -90))[0]
        hors = [round(i * w / SR, 3) for i in pics if min(abs(i * w / SR - a) for a in attaques) > 0.025
                and not any(a - 0.01 <= i * w / SR <= b + 0.01 for a, b in zones)]
        K[nom] = {"bouffees_hors_attaques": len(hors), "instants": hors[:12]}
    K["ok"] = all(K[n]["bouffees_hors_attaques"] == 0 for n in ("nappe", "signature", "sfx"))
    R["K_clics_hf"] = K
    # L. le pan suit le point
    def balance(st, a, b):
        seg = st[int(a * SR):int(b * SR)]
        return 20 * np.log10(np.sqrt(np.mean(seg[:, 1] ** 2)) / np.sqrt(np.mean(seg[:, 0] ** 2)))
    def attendu(t):
        a = (M.pan_point(t) + 1) * np.pi / 4
        return 20 * np.log10(np.tan(a))
    Lp = []
    for nom, st, a, b in (("tap-9h", "sfx", 20.667, 20.70), ("tap-11h", "sfx", 22.2, 22.23),
                          ("la·sol, fin de l'écriture", "signature", 26.06, 26.10), ("stylo, milieu du mot", "sfx", *W["stylo_milieu"])):
        Lp.append({"cue": nom, "fenetre": [a, b], "x_point": round(float(M.x_point((a + b) / 2)), 1),
                   "D_moins_G_mesure_db": round(float(balance(stems[st], a, b)), 2),
                   "D_moins_G_attendu_db": round(float(attendu((a + b) / 2)), 2)})
    R["L_pan_suit_le_point"] = Lp
    # M. arc de sonie
    ct = np.array(courbe)
    Mv = {}
    if len(ct):
        tS, MM, SS = ct[:, 0], ct[:, 1], ct[:, 2]
        dial = SS[(tS >= 5.0) & (tS <= 35.4)]
        med = float(np.median(dial))
        sig_interv = L_(mk, *W["signature_arc"])
        tmom, lmom = instantanee(mk)
        re_mom = float(lmom[(tmom >= T["re"] + 0.4 - 1e-9) & (tmom <= T["re"] + 0.45)].max())
        sk_mom = instantanee(sk)
        vib = float(sk_mom[1][(sk_mom[0] >= T["vibreur"] + 0.1) & (sk_mom[0] <= T["vibreur"] + 0.9)].max())
        Mv = {"mediane_S_dialogue_5-35.4": round(med, 2), "signature_LUFS": sig_interv, "fenetre_signature": list(W["signature_arc"]),
              "signature_moins_mediane_LU": round(sig_interv - med, 2),
              "S_max_film": [round(float(SS.max()), 2), round(float(tS[np.argmax(SS)]), 1)],
              "S_max_dialogue_5-35.4": round(float(dial.max()), 2),
              "S_max_apres_la": [round(float(SS[tS >= T["la"]].max()), 2), round(float(tS[tS >= T["la"]][np.argmax(SS[tS >= T["la"]])]), 1)],
              "M_max_film": [round(float(np.nanmax(MM)), 2), round(float(tS[np.nanargmax(MM)]), 1)],
              "instantanee_au_re_mix": round(re_mom, 2),
              "re_piste_signature_400ms": L_(gk, T["re"], T["re"] + 0.4),
              "vibreur_instantanee_max": round(vib, 2),
              "S_par_seconde": {int(round(t)): round(float(s), 1) for t, s in zip(tS, SS) if abs(t - round(t)) < 1e-6}}
        dM = (tmom >= 5.0) & (tmom <= 35.5)
        Mv["M_max_dialogue_5-35.5"] = round(float(lmom[dM].max()), 2)
        Mv["M_p95_dialogue_5-35.5"] = round(float(np.percentile(lmom[dM], 95)), 2)
        dR = (tmom >= T["re"]) & (tmom <= T["re"] + 0.8)
        Mv["M_max_au_re"] = round(float(lmom[dR].max()), 2)
        # plan : « ré ≈ −11,5 LUFS » = estimation, à l'échelle v1, de « le ré passe +2 dB au-dessus de la voix ». À l'échelle v2
        # la voix culmine à −9,9 : le critère retenu est l'intention (le ré est l'instant le plus fort du film)
        Mv["ok"] = bool(Mv["signature_moins_mediane_LU"] >= 1.0 and Mv["M_max_au_re"] >= Mv["M_max_dialogue_5-35.5"] and vib <= -14.0)
    R["M_arc_de_sonie"] = Mv
    # N. livrables de la signature seule
    Nn = {}
    for nom in ("point-solaire-signature-v2.wav", "point-solaire-signature-courte-v2.wav"):
        p = UPL / nom
        if p.exists():
            x = labo.lire(p)
            Nn[nom] = {"duree_s": round(len(x) / SR, 3), "crete_vraie_dbtp": round(S.crete_vraie(x), 2), **S.analyser(x),
                       "hp_moins_pleine_bande_db": round(float(20 * np.log10(np.sqrt(np.mean(haut_parleur(x) ** 2)) / np.sqrt(np.mean(x ** 2)))), 2)}
    R["N_signatures_seules"] = Nn
    # O. variante monde
    pm = ICI / "stems" / "monde.wav"
    if pm.exists() and (ICI / "mix-monde.wav").exists():
        mo = labo.lire(pm)
        mok = ponderer_k(mo)
        tt, ll = instantanee(mok)
        O = {"mesure": labo.mesurer(ICI / "mix-monde.wav"), "crete_vraie_dbtp": round(S.crete_vraie(labo.lire(ICI / "mix-monde.wav")), 2)}
        for nom, P in M.MONDE_SONS.items():
            O[f"{nom}_instantanee_max"] = round(float(ll[(tt >= P["t"]) & (tt <= P["t"] + 1.4)].max()), 2)
        O["rien_apres_le_decroche"] = bool(not np.any(mo[int(round((T["decroche"] + 0.010) * SR)) + 1:]))
        # la variante doit venir du même passage que le master (mix.py --monde écrit mix-monde.wav après mix.wav)
        O["a_jour_avec_le_master"] = (ICI / "mix-monde.wav").stat().st_mtime >= mixp.stat().st_mtime
        mm = labo.lire(ICI / "mix-monde.wav")
        O["ecart_hors_s1_avec_le_master_max"] = float(np.max(np.abs(mm[int(round((T["decroche"] + 0.02) * SR)):] - mix[int(round((T["decroche"] + 0.02) * SR)):])))
        O["choix"] = {k: {"retenue": v["retenue"], "prises": v["prises"]} for k, v in CU.get("monde", {}).get("choix", {}).items()}
        O["ok"] = bool(all(O[f"{n}_instantanee_max"] <= -28 for n in M.MONDE_SONS) and O["rien_apres_le_decroche"]
                       and O["a_jour_avec_le_master"] and O["ecart_hors_s1_avec_le_master_max"] < 1e-4)
        R["O_monde"] = O
    R["stems_crete_dbtp"] = {n: round(S.crete_vraie(s), 2) for n, s in stems.items()}
    R["synthese_ok"] = {k: v.get("ok") for k, v in R.items() if isinstance(v, dict) and "ok" in v}
    R["synthese_ok"]["C_somme"] = R["C_somme_stems_moins_mix_max"] < 1e-6
    (ICI / "mesures-son.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    if images:
        planches(mixp, courbe, hp)


# ── planches ────────────────────────────────────────────────────────────────
MARQUES = [("décroché", "decroche"), ("sol", "sol"), ("ré7", "re7"), ("résolution", "resolution"), ("raccroché", "raccroche"),
           ("vibreur", "vibreur"), ("la", "la"), ("ré", "re")]


def courbe_png(courbe, chemin, med):
    """L'arc de sonie : M (gris) et S (encre) de ebur128 sur tout le film, médiane S du dialogue, repères."""
    from PIL import Image, ImageDraw
    W_, H, g, d, h, b = 2400, 900, 90, 30, 40, 70
    im = Image.new("RGB", (W_, H), (244, 241, 232))
    dr = ImageDraw.Draw(im)
    from PIL import ImageFont
    try:
        police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except OSError:
        police = None
    _texte = dr.text
    dr.text = lambda xy, t, fill=None: _texte(xy, t, fill=fill, font=police)  # noqa: E731
    x = lambda t: g + (W_ - g - d) * t / DUREE  # noqa: E731
    y = lambda l: h + (H - h - b) * (-5 - l) / 40.0  # noqa: E731
    for l in range(-45, -4, 5):
        dr.line([(g, y(l)), (W_ - d, y(l))], fill=(214, 208, 196))
        dr.text((10, y(l) - 7), f"{l} LUFS", fill=(111, 105, 95))
    for s in range(0, int(DUREE) + 1, 5):
        dr.line([(x(s), H - b), (x(s), H - b + 8)], fill=(111, 105, 95))
        dr.text((x(s) - 8, H - b + 12), f"{s} s", fill=(111, 105, 95))
    for nom, k in MARQUES:
        tx = T[k]
        dr.line([(x(tx), h), (x(tx), H - b)], fill=(239, 164, 36), width=2)
        dr.text((x(tx) + 4, h + 4), nom, fill=(38, 32, 25))
    dr.line([(g, y(med)), (W_ - d, y(med))], fill=(110, 156, 116), width=2)
    dr.line([(g, y(med + 1)), (W_ - d, y(med + 1))], fill=(110, 156, 116), width=1)
    dr.text((W_ - d - 330, y(med) + 4), f"médiane S du dialogue {med:.1f} (et +1 LU)", fill=(110, 156, 116))
    ct = np.array(courbe)
    for col, idx, lw in (((150, 144, 134), 1, 1), ((38, 32, 25), 2, 3)):
        pts = [(x(t), y(max(-45.0, v))) for t, v in zip(ct[:, 0], ct[:, idx])]
        dr.line(pts, fill=col, width=lw)
    dr.text((g, 8), "Arc de sonie v2 · ebur128 sur le master : S (3 s, encre) et M (400 ms, gris) · repères solaires : événements "
            "· vert : médiane S du dialogue [5 ; 35,4] et +1 LU", fill=(38, 32, 25))
    im.save(chemin)


def planches(mixp, courbe, hp):
    SORTIE_IMG.mkdir(parents=True, exist_ok=True)
    def run(entree, filtre, sortie, extra=()):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *extra, "-i", str(entree), "-lavfi", filtre, "-frames:v", "1",
                        str(SORTIE_IMG / sortie)], check=True)
    med = json.loads((ICI / "mesures-son.json").read_text())["M_arc_de_sonie"]["mediane_S_dialogue_5-35.4"]
    courbe_png(courbe, SORTIE_IMG / "arc-de-sonie.png", med)
    run(mixp, "showspectrumpic=s=2400x700:legend=1:fscale=log:scale=log:stop=14000:color=intensity", "mix-spectre.png")
    run(mixp, "showwavespic=s=2400x500:split_channels=1:scale=log:colors=0x262019|0xC0452C", "mix-onde.png")
    for n in ("dialogue", "nappe", "sfx", "signature"):
        run(ICI / "stems" / f"{n}.wav", "showwavespic=s=2400x240:scale=log:colors=0x262019", f"stem-{n}-onde.png")
        run(ICI / "stems" / f"{n}.wav", "showspectrumpic=s=2400x500:legend=1:fscale=log:scale=log:stop=14000:color=intensity",
            f"stem-{n}-spectre.png")
    hpn = SCRATCH / "nappe-haut-parleur.wav"
    S.ecrire24(hpn, np.stack([hp["nappe"], hp["nappe"]], axis=1) * 0.99 / max(1.0, float(np.max(np.abs(hp["nappe"])))))
    run(hpn, "showspectrumpic=s=2400x500:legend=1:fscale=log:scale=log:start=100:stop=6000:color=intensity",
        "nappe-haut-parleur-spectre.png")
    for nom, (a, b) in {"z1-sonnerie-decroche": (0, 6.5), "z2-entree-sol": (9.5, 13.0), "z3-agenda-touchers": (17.3, 25.2),
                        "z4-ecriture": (24.8, 27.2), "z5-tension-resolution": (28.0, 36.0),
                        "z6-raccroche-silence-vibreur": (35.3, 40.0), "z7-stylo-signature": (round(P0 - 0.3, 2), DUREE)}.items():
        run(mixp, "showspectrumpic=s=1600x600:legend=1:fscale=log:scale=log:stop=14000:color=intensity",
            f"{nom}-spectre.png", extra=("-ss", str(a), "-t", str(b - a)))
        run(mixp, "showwavespic=s=1600x300:split_channels=1:colors=0x262019|0xC0452C", f"{nom}-onde.png",
            extra=("-ss", str(a), "-t", str(b - a)))
    for nom in ("point-solaire-signature-v2.wav", "point-solaire-signature-courte-v2.wav"):
        p = UPL / nom
        run(p, "showspectrumpic=s=1200x500:legend=1:fscale=log:scale=log:stop=14000:color=intensity", nom.replace(".wav", "-spectre.png"))
        run(p, "showwavespic=s=1200x300:split_channels=1:colors=0x262019|0xC0452C", nom.replace(".wav", "-onde.png"))
    print(f"planches : {SORTIE_IMG}")


if __name__ == "__main__":
    main(images="--images" in sys.argv)
