#!/usr/bin/env python3
"""Contrôles de la bande son (écoute impossible ici : tout se prouve par la mesure).

    python3 son/controle_son.py [--images]      → son/mesures-son.json (+ planches PNG avec --images)

Contrôles (bible.controles 7, 11, 12, 13 et consigne de la mission) :
  A. master : intégré, crête vraie, LRA (loudnorm et ebur128), et après un encodage AAC 256k de contrôle
  B. silences numériques : 36,70 → 37,38 et 43,22 → 43,50 (RMS < −90 dBFS), tonalité présente dès 20 ms
  C. somme des stems = mix
  D. synchro : attaque de chaque cue ponctuel (plus forte montée d'enveloppe à ±50 ms) contre son instant, ±1 image
  E. dialogue : décalage 0 échantillon entre la voix traitée et son/dialogue.wav (corrélation, par extrait)
  F. intelligibilité : rapport voix / reste, pondéré K, mot par mot (mots.json)
  G. compatibilité mono : écart de sonie somme mono / stéréo, corrélation L/R par fenêtres de 100 ms
  H. haut-parleur de téléphone (300 Hz - 8 kHz) : crêtes des trois notes de la signature à 3 dB près
  I. chroma de la nappe (sol si ré, puis ré fa# la do, puis sol si ré)
  J. enveloppes : tonalité contre secousses.s1, vibreur contre secousses.s6, image par image
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
DON = PROJET / "donnees"
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402
import mix as M  # noqa: E402  (données et outils seulement : rien ne se recalcule à l'import)

SR = labo.SR
SORTIE_IMG = Path("/root/vokio-uploads/videos/showcase/son-controles")
SCRATCH = Path("/tmp/claude-0/-root/5cdc3174-18c1-52f2-a7e6-50c04cd57657/scratchpad")


def lire24(p):
    return labo.lire(p)


# ── pondération K (BS.1770) appliquée en fréquence ──────────────────────────
def _h(b, a, w):
    z = np.exp(-1j * w)
    return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)


def ponderer_k(x):
    n = len(x)
    Nf = 1 << (n - 1).bit_length()
    w = 2 * np.pi * np.fft.rfftfreq(Nf, 1 / SR) / SR
    H = _h([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], w) * \
        _h([1, -2, 1], [1, -1.99004745483398, 0.99007225036621], w)
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c], Nf) * np.abs(H), Nf)[:n] for c in range(x.shape[1])], axis=1)


def sonie(xk, i0, i1):
    """Sonie (LUFS) d'un segment déjà pondéré K."""
    s = xk[i0:i1]
    if len(s) == 0:
        return -np.inf
    return -0.691 + 10 * np.log10(np.sum(np.mean(s ** 2, axis=0)) + 1e-20)


def ebur128(chemin):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(chemin), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    e = r.stderr[r.stderr.rindex("Summary:"):]
    val = lambda clef: float(e.split(clef)[1].split()[0])  # noqa: E731
    return {"I": val("I:"), "LRA": val("LRA:"), "TP": val("Peak:")}


def attaque(x, t, fen=0.050):
    """Instant de la plus forte montée de l'enveloppe (RMS 2 ms, pas de 0,5 ms) dans [t − fen, t + fen]."""
    m = x.mean(axis=1) if x.ndim > 1 else x
    i0, i1 = int((t - fen - 0.01) * SR), int((t + fen + 0.01) * SR)
    s = m[max(0, i0):i1]
    if i0 < 0:                                   # avant l'image 0 : du silence
        s = np.concatenate([np.zeros(-i0), s])
    h, w = 24, 96
    c = np.concatenate([[0.0], np.cumsum(s ** 2)])
    pos = np.arange(w, len(s), h)
    env = 10 * np.log10((c[pos] - c[pos - w]) / w + 1e-14)
    d = env[4:] - env[:-4]                      # montée sur 2 ms
    k = int(np.argmax(d))
    # l'attaque = début de cette montée (fin de la fenêtre qui précède)
    return (i0 + pos[k] + h * 2) / SR, float(d[k])


def chroma(x, i0, i1):
    s = x[i0:i1].mean(axis=1)
    s = s * np.hanning(len(s))
    X = np.abs(np.fft.rfft(s)) ** 2
    f = np.fft.rfftfreq(len(s), 1 / SR)
    ok = (f > 60) & (f < 2000)
    pc = np.round(12 * np.log2(f[ok] / 440.0)).astype(int) % 12
    c = np.bincount(pc, weights=X[ok], minlength=12)
    noms = ["la", "la#", "si", "do", "do#", "ré", "ré#", "mi", "fa", "fa#", "sol", "sol#"]
    ordre = np.argsort(c)[::-1]
    return [noms[k] for k in ordre[:4]], {noms[k]: round(float(c[k] / c.max()), 3) for k in ordre[:6]}


def main(images=False):
    R = {}
    mixp = ICI / "mix.wav"
    mix = lire24(mixp)
    stems = {n: lire24(ICI / "stems" / f"{n}.wav") for n in ("dialogue", "nappe", "sfx", "signature")}
    N = len(mix)
    # A. master
    R["A_master"] = {"loudnorm": labo.mesurer(mixp), "ebur128": ebur128(mixp), "duree_s": N / SR,
                     "crete_vraie_numpy_dbtp": round(S.crete_vraie(mix), 2)}
    m4a = SCRATCH / "controle-aac.m4a"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mixp), "-c:a", "aac", "-b:a", "256k", str(m4a)], check=True)
    R["A_master"]["apres_aac_256k"] = {"loudnorm": labo.mesurer(m4a), "ebur128": ebur128(m4a)}
    # B. silences
    def rms_fen(a, b):
        s = mix[int(a * SR):int(b * SR)]
        return -np.inf if not np.any(s) else round(float(20 * np.log10(np.sqrt(np.mean(s ** 2)))), 1)
    R["B_silences"] = {"36.70-37.38": rms_fen(36.70, 37.38), "43.22-43.50": rms_fen(43.22, 43.50),
                       "zeros_exacts_36.68-37.40": bool(not np.any(mix[int(round(36.68 * SR)):int(round(37.40 * SR))])),
                       "zeros_exacts_43.20-43.50": bool(not np.any(mix[int(round(43.20 * SR)):])),
                       "seule_la_signature_37.40-38.00": {n: bool(not np.any(stems[n][int(round(37.40 * SR)):int(round(38.0 * SR))]))
                                                          for n in ("dialogue", "nappe", "sfx")},
                       "rien_apres_le_raccroche_hors_signature_et_nappe_de_fin": {
                           n: bool(not np.any(stems[n][int(round((36.6 + 0.08) * SR)):])) for n in ("dialogue", "sfx")},
                       "tonalite_20_premieres_ms_rms_dbfs": round(float(20 * np.log10(np.sqrt(np.mean(mix[:960] ** 2)))), 1)}
    # C. somme
    somme = sum(stems.values())
    R["C_somme_stems_moins_mix_max"] = float(np.max(np.abs(somme - mix)))
    # D. synchro
    cues = json.loads((ICI / "cues.json").read_text())["cues"]
    ponctuels = ["clic-decroche", "cloche-sol-1", "tap-9h", "tap-10h", "tap-11h", "tap-retour-9h", "cloche-la-rdv",
                 "cloche-sol-rdv", "vibreur", "raccroche", "signature-la", "signature-sol", "signature-re", "ton-1", "ton-2-la"]
    D = []
    for c in cues:
        if c["id"] not in ponctuels:
            continue
        st = stems[c["stem"]]
        t_mes, montee = attaque(st, c["t"])
        ecart = t_mes - c["t"]
        D.append({"id": c["id"], "t": c["t"], "image": c["image"], "attaque_mesuree": round(t_mes, 4),
                  "ecart_ms": round(1000 * ecart, 1), "ecart_images": round(ecart * 30, 2), "montee_db": round(montee, 1),
                  "ok": abs(ecart) <= 1 / 30})
    R["D_synchro"] = D
    # D bis : image par image contre point-resolu (contacts), et changement d'accord de la résolution
    t_res = json.loads((ICI / "cues.json").read_text())["nappe"]["t_res"]
    nap = stems["nappe"]
    avant, _ = chroma(nap, int((t_res - 0.6) * SR), int((t_res - 0.1) * SR))
    apres, _ = chroma(nap, int((t_res + 0.1) * SR), int((t_res + 0.6) * SR))
    R["D_resolution"] = {"t_voyelle": t_res, "image": round(t_res * 30), "chroma_avant": avant, "chroma_apres": apres}
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
    R["E_dialogue_decalage"] = E
    # F. intelligibilité mot par mot
    dk = ponderer_k(stems["dialogue"])
    reste = ponderer_k(stems["nappe"] + stems["sfx"] + stems["signature"])
    F = []
    for w in M.MOTS["mots"]:
        # fenêtre d'au moins 120 ms : sur 30 ms (« Je » de 19,80), on mesure l'attaque d'une fricative, pas le mot
        i0, i1 = int(w["debut"] * SR), int(max(w["fin"], w["debut"] + 0.12) * SR)
        F.append((round(float(sonie(dk, i0, i1) - sonie(reste, i0, i1)), 1), w["texte"], w["debut"]))
    F.sort()
    vals = [f[0] for f in F]
    R["F_voix_sur_reste_LU"] = {"min": F[0][0], "mediane": float(np.median(vals)), "pires": F[:6]}
    # sonie des éléments (pondérée K), par moments du film
    mk = ponderer_k(mix)
    def L(xk, a, b):
        return round(float(sonie(xk, int(a * SR), int(b * SR))), 1)
    sk, gk, nk = ponderer_k(stems["sfx"]), ponderer_k(stems["signature"]), ponderer_k(stems["nappe"])
    R["F_sonies_LUFS"] = {
        "voix_integree_approx (toutes voix, 4,91 → 35,95)": L(dk, 4.91, 35.95),
        "tonalite_1 (0,1 → 1,4)": L(sk, 0.1, 1.4), "tonalite_2 (3,7 → 4,2)": L(gk, 3.7, 4.2),
        "decroche la+sol (4,2 → 4,9)": L(gk, 4.2, 4.9),
        "nappe seule, silence de l'outil (18,5 → 19,7)": L(nk, 18.5, 19.7),
        "nappe sous la voix (20,0 → 22,6)": L(nk, 20.0, 22.6),
        "voix (20,0 → 22,6)": L(dk, 20.0, 22.6),
        "la·sol de l'écriture (25,4 → 26,1)": L(gk, 25.4, 26.1),
        "nappe, silence de réservation (25,0 → 26,2)": L(nk, 25.0, 26.2),
        "vibreur (33,27 → 33,72)": L(sk, 33.27, 33.72),
        "signature, 400 ms après le la (37,40 → 37,80)": L(gk, 37.40, 37.80),
        "signature, 400 ms après le ré (38,00 → 38,40)": L(gk, 38.0, 38.4),
        "nappe de fin (39 → 41,8)": L(nk, 39.0, 41.8),
        "mix, voix A4 (26,2 → 33,0)": L(mk, 26.2, 33.0)}
    # G. mono
    mono = (mix[:, 0] + mix[:, 1]) / 2
    mono2 = np.stack([mono, mono], axis=1)
    m2k = ponderer_k(mono2)
    G = {"ecart_sonie_mono_moins_stereo_film_LU": round(float(sonie(m2k, 0, N) - sonie(mk, 0, N)), 2)}
    for nom, (a, b) in {"signature 37,4 → 40,3": (37.4, 40.3), "nappe 6 → 17,5": (6, 17.5), "decroche 4,2 → 5,0": (4.2, 5.0),
                        "ecriture 25,4 → 26,2": (25.4, 26.2), "nappe de fin 39 → 43": (39, 43)}.items():
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
    R["G_mono"] = G
    # H. haut-parleur de téléphone
    tel = M.ffmpeg_filtre(mix, "highpass=f=300,lowpass=f=8000")
    H = {}
    for nom, t in (("la", M.EV["signature_la"]["t"]), ("sol", M.EV["signature_sol"]["t"]), ("re", M.EV["signature_re_contact"]["t"])):
        a, b = int(t * SR), int((t + 0.1) * SR)
        H[nom] = round(float(S.db(np.max(np.abs(tel[a:b]))) - S.db(np.max(np.abs(mix[a:b])))), 2)
    R["H_telephone_ecart_crete_db"] = H
    # I. chroma de la nappe
    R["I_chroma_nappe"] = {f"{a}-{b}": chroma(nap, int(a * SR), int(b * SR))[0] for a, b in
                           ((6.7, 17.5), (20.7, 32.8), (33.1, 36.5), (39.0, 41.8))}
    # J. enveloppes
    s1 = M.SEC["s1"]["enveloppe"]
    ref = np.mean(np.abs(stems["sfx"][int(0.2 * SR):int(1.3 * SR), 0]))     # tonalité établie (ton-1)
    env_mes = []
    for n in range(126):
        a, b = int(round(n / 30 * SR)), int(round((n + 1) / 30 * SR))
        seg = stems["sfx"][a:b, 0] if n < 90 else stems["signature"][a:b, 0]
        env_mes.append(float(np.mean(np.abs(seg)) / ref))
    ecarts = np.abs(np.array(env_mes) - np.array(s1[:126]))
    R["J_tonalite_contre_secousses_s1"] = {"ecart_max": round(float(ecarts.max()), 3), "image_pire": int(ecarts.argmax()),
                                          "exemples": {n: [round(env_mes[n], 3), s1[n]] for n in (0, 1, 44, 45, 107, 108, 109, 125)}}
    s6 = M.SEC["s6"]
    t = np.arange(int(998 / 30 * SR), int(1013 / 30 * SR)) / SR
    env = M.trapeze(t, s6["segments_s"], s6["rampes_s"])
    moy = [round(float(env[int(round((n - 998) / 30 * SR)):int(round((n - 997) / 30 * SR))].mean()), 4) for n in range(998, 1013)]
    R["J_vibreur_contre_secousses_s6"] = {"ecart_max": round(float(np.max(np.abs(np.array(moy) - np.array(s6["enveloppe"])))), 4)}
    vb = stems["sfx"][int(998 / 30 * SR):int(1013 / 30 * SR), 0]
    rms_img = [float(np.sqrt(np.mean(vb[int(round(k / 30 * SR)):int(round((k + 1) / 30 * SR))] ** 2))) for k in range(15)]
    rr = np.array(rms_img) / max(rms_img)
    R["J_vibreur_rms_par_image"] = [round(float(v), 2) for v in rr]
    # K. clics : bouffées au-dessus de 5 kHz, 25 dB au-dessus de la médiane locale, hors des attaques déclarées
    attaques = [c["t"] for c in cues if c["id"] in ponctuels] + [e["film_in"] for e in M.DIA["extraits"]] + \
               [e["film_out"] for e in M.DIA["extraits"]] + [M.EV["raccroche"]["t"]]
    K = {}
    f = np.fft.rfftfreq(N, 1 / SR)
    for nom in ("nappe", "signature", "sfx"):
        hp = np.fft.irfft(np.fft.rfft(stems[nom].mean(axis=1)) * (f > 5000), N)
        w = 240
        e = 20 * np.log10(np.sqrt(np.mean(hp[:N // w * w].reshape(-1, w) ** 2, axis=1)) + 1e-12)
        loc = np.array([np.median(e[max(0, i - 100):i + 100]) for i in range(len(e))])
        pics = np.nonzero((e - loc > 25) & (e > -90))[0]
        vib = M.SEC["s6"]["segments_s"]
        hors = [round(i * w / SR, 3) for i in pics if min(abs(i * w / SR - a) for a in attaques) > 0.025
                and not any(a - 0.01 <= i * w / SR <= b + 0.01 for a, b in vib)]      # le grésillement du vibreur est voulu
        K[nom] = {"bouffees_hors_attaques": len(hors), "instants": hors[:12]}
    R["K_clics_hf"] = K
    # L. le pan suit le point : balance G/D mesurée dans le stem contre la loi de labo.placer au x du point
    def balance(st, a, b):
        seg = st[int(a * SR):int(b * SR)]
        return 20 * np.log10(np.sqrt(np.mean(seg[:, 1] ** 2)) / np.sqrt(np.mean(seg[:, 0] ** 2)))
    def attendu(t):
        a = (M.pan_point(t) + 1) * np.pi / 4
        return 20 * np.log10(np.tan(a))
    Lp = []
    for nom, st, a, b in (("tap-9h", "sfx", 20.667, 20.72), ("tap-11h", "sfx", 22.2, 22.25),
                          ("clic+la au décroché", "signature", 4.27, 4.40), ("la·sol, début de l'écriture", "signature", 25.42, 25.46),
                          ("la·sol, fin de l'écriture", "signature", 26.06, 26.10), ("signature (ré)", "signature", 38.0, 38.1)):
        Lp.append({"cue": nom, "fenetre": [a, b], "x_point": round(float(M.x_point((a + b) / 2)), 1),
                   "D_moins_G_mesure_db": round(float(balance(stems[st], a, b)), 2),
                   "D_moins_G_attendu_db": round(float(attendu((a + b) / 2)), 2)})
    R["L_pan_suit_le_point"] = Lp
    # stems
    R["stems_crete_dbtp"] = {n: round(S.crete_vraie(s), 2) for n, s in stems.items()}
    (ICI / "mesures-son.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(R, ensure_ascii=False, indent=1, default=float))
    if images:
        planches(mixp)


def planches(mixp):
    SORTIE_IMG.mkdir(parents=True, exist_ok=True)
    def run(entree, filtre, sortie, extra=()):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *extra, "-i", str(entree), "-lavfi", filtre, "-frames:v", "1",
                        str(SORTIE_IMG / sortie)], check=True)
    run(mixp, "showspectrumpic=s=2400x700:legend=1:fscale=log:scale=log:stop=12000:color=intensity", "mix-spectre.png")
    run(mixp, "showwavespic=s=2400x500:split_channels=1:scale=log:colors=0x262019|0xC0452C", "mix-onde.png")
    for n in ("dialogue", "nappe", "sfx", "signature"):
        run(ICI / "stems" / f"{n}.wav", "showwavespic=s=2400x240:scale=log:colors=0x262019", f"stem-{n}-onde.png")
    for nom, (a, b) in {"z1-sonnerie-decroche": (0, 6), "z2-agenda-touchers": (17.3, 25.2), "z3-ecriture": (24.8, 27.2),
                        "z4-resolution-vibreur": (32.4, 36.9), "z5-silence-signature": (36.3, 43.5)}.items():
        run(mixp, "showspectrumpic=s=1600x600:legend=1:fscale=log:scale=log:stop=8000:color=intensity",
            f"{nom}-spectre.png", extra=("-ss", str(a), "-t", str(b - a)))
        run(mixp, "showwavespic=s=1600x300:split_channels=1:colors=0x262019|0xC0452C", f"{nom}-onde.png",
            extra=("-ss", str(a), "-t", str(b - a)))
    for nom in ("point-solaire-signature.wav", "point-solaire-signature-courte.wav"):
        p = Path("/root/vokio-uploads/videos/showcase") / nom
        run(p, "showspectrumpic=s=1200x500:legend=1:fscale=log:scale=log:stop=8000:color=intensity", nom.replace(".wav", "-spectre.png"))
        run(p, "showwavespic=s=1200x300:split_channels=1:colors=0x262019|0xC0452C", nom.replace(".wav", "-onde.png"))
    print(f"planches : {SORTIE_IMG}")


if __name__ == "__main__":
    main(images="--images" in sys.argv)
