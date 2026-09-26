#!/usr/bin/env python3
"""Bande son complète du showcase « Le point sur le i » (bible.cues_son + bible.signature_sonore).

    python3 son/mix.py

Entrées (jamais de temps en dur qui contredise les données) :
  son/dialogue.wav + son/dialogue.json      le vrai appel du 18/09, placé aux temps du film, niveau d'origine
  donnees/evenements.json                   décroché, contacts du point, écriture, bulle, raccroché, signature
  donnees/secousses.json                    enveloppes s1 (tonalité) et s6 (vibreur) : l'image lit la même donnée
  donnees/mots.json                         attaques des mots (changements d'accord) et dernière syllabe de « confirmation »
  donnees/point-resolu.json                 x du point à chaque image : pan = 0,6 × (x − 540)/540
  donnees/mesures.json                      abscisse du ı (pan de la signature)
Sorties :
  son/stems/dialogue.wav  nappe.wav  sfx.wav  signature.wav   (48 kHz, 24 bits, stéréo, gain de master compris :
                                                               leur somme redonne mix.wav à l'arrondi près)
  son/mix.wav  +  assets/son/mix.wav (lu par index.html)  +  /root/vokio-uploads/videos/showcase/point-solaire-bande-son.wav
  son/cues.json                             chaque cue réellement posé : instant, échantillon, source de l'instant, niveau, pan

Master : un seul gain (−14 LUFS intégrés) et un limiteur à crête vraie (suréchantillonnage ×4, anticipation 1,5 ms),
sans loudnorm dynamique, qui écraserait le silence numérique. Plafond −1,5 dBTP : marge pour l'encodage AAC.

Choix de sound design (voir aussi cues.json) :
- Deux mondes, deux bandes passantes. Tout ce qui est DANS l'appel garde sa bande téléphone (la preuve, sans débruitage).
  Tout ce qui est le film (le point, le téléphone à l'écran, la marque) est en pleine bande : on ne les confond pas.
- Aucun bruitage réaliste dans les blancs de l'appel : un papier ou un feutre dans le silence de next_available_slots
  ou de la réservation se lirait comme une secrétaire qui feuillette un agenda papier, soit le contraire du produit,
  et ce serait un son qui prétend être dans le vrai appel. Les bruitages ElevenLabs de la bible sont donc écartés.
  Le geste d'écriture est porté par le « la · sol » qui voyage avec le point.
- Tout son émis par le point est attaché au point : son pan suit x image par image (interpolé à l'échantillon),
  queues de cloche comprises. La voix reste mono au centre, la nappe large et fixe.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
DON = PROJET / "donnees"
STEMS = ICI / "stems"
UPLOADS = Path("/root/vokio-uploads/videos/showcase")
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402

SR = labo.SR
LUFS_CIBLE = -14.0
PLAFOND_DBTP = -1.5


def J(chemin):
    return json.loads(Path(chemin).read_text())


EV = J(DON / "evenements.json")
SEC = J(DON / "secousses.json")
MOTS = J(DON / "mots.json")
SCENES = J(DON / "scenes.json")
PR = J(DON / "point-resolu.json")["images"]
MES = J(DON / "mesures.json")
DIA = J(ICI / "dialogue.json")

DUREE = max(s["fin"] for s in SCENES.values())
assert abs(DUREE - EV["fin"]["t"]) < 1e-9
N = int(round(DUREE * SR))
FIN_SON = DUREE - 0.30               # bible « silence-final » : zéros numériques sur les 0,30 s finales (boucle TikTok)

# niveaux avant master (dBFS crête sauf mention) : bible.cues_son, ajustés par l'écoute aux mesures (voir NOTES_NIVEAU)
NIV = {
    "ton": -23.0,            # bible −18 : à −18, la tonalité sortait à −10,8 LUFS, 3 LU AU-DESSUS de la voix (mesuré) ;
                             # à −23 elle est à ≈ −16 LUFS : présente, sans dicter le volume de celui qui écoute
    "ligne_rms": -56.0,
    "clic": -32.0,
    "sol_decroche": -25.0,   # bible −20 : suit la tonalité (le sol reste 2 dB sous le la, comme dans la bible)
    "tap": -30.0, "tap_retour": -34.0,
    "la_rdv": -26.0, "sol_rdv": -26.0,
    "vibreur": -19.0,        # bible −22 : masqué par la nappe qui gonfle à la résolution (mesuré −23 LUFS) ; +3 dB
    "raccroche": -24.0,
    "nappe_rms": -32.0, "nappe_fin_rms": -34.0,
    "voix_lufs": -20.0,
    "signature_decalage_db": -1.5,   # bible −16/−17/−15 : le ré sortait à −12,2 LUFS, 2 LU au-dessus de la voix ;
                                     # −1,5 dB le pose au niveau de la voix (le silence qui précède fait le reste)
}

CUES = []


def cue(id_, stem, t, source, fabrication, niveau, pan=None, **extra):
    d = {"id": id_, "stem": stem, "t": round(float(t), 6), "echantillon": int(round(t * SR)),
         "image": int(round(t * 30)), "source_instant": source, "fabrication": fabrication,
         "niveau_avant_master": niveau}
    if pan is not None:
        d["pan"] = pan
    d.update(extra)
    CUES.append(d)


def mot(extrait, rang):
    return next(w for w in MOTS["mots"] if w["extrait"] == extrait and w["rang"] == rang)


# ── le point : x à l'échantillon, pan ───────────────────────────────────────
_T_IMG = np.array([p["t"] for p in PR])
_X_IMG = np.array([p["x"] for p in PR])


def x_point(t):
    return np.interp(t, _T_IMG, _X_IMG)


def pan_point(t):
    return 0.6 * (x_point(t) - 540.0) / 540.0


def temps(i0, n):
    return (i0 + np.arange(n)) / SR


def poser_mobile(piste, mono, t0, niveau_db, rev=None, pan_fn=pan_point, graine=31):
    """Place un son mono du point, attaché au point : pan(t) = pan_fn(t) à chaque échantillon.
    rev = (secondes, mix) : retour de réverbe seul ajouté au direct (le direct n'est jamais atténué)."""
    i0 = int(round(t0 * SR))
    sig = mono * S.gain(niveau_db)
    st = S.panner(sig, pan_fn(temps(i0, len(sig))))
    S.ajouter(piste, st, i0)
    if rev:
        S.ajouter(piste, rev[1] * S.humide(st, rev[0], graine=graine), i0)
    return piste


def trapeze(t, segments, rampes, forme="lineaire"):
    """Enveloppe trapèze des segments de secousses.json (mêmes rampes, même fonction que outils/construire.py)."""
    a = np.zeros_like(t)
    for (d, f), (fa, fr) in zip(segments, rampes):
        m = (t >= d) & (t < f)
        e = np.ones(m.sum())
        if fa:
            e = np.minimum(e, (t[m] - d) / fa)
        if fr:
            e = np.minimum(e, (f - t[m]) / fr)
        e = np.clip(e, 0, 1)
        if forme == "cos":                   # même moyenne sur chaque image quand la rampe tient dans une image
            e = 0.5 - 0.5 * np.cos(np.pi * e)
        a[m] = e
    return a


# ── ffmpeg en tuyau (float 32, aucune quantification) ───────────────────────
def ffmpeg_filtre(sig, filtre):
    sig = np.asarray(sig, dtype=np.float32)
    canaux = 1 if sig.ndim == 1 else sig.shape[1]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", str(canaux),
                        "-i", "pipe:0", "-af", filtre, "-f", "f32le", "-ar", str(SR), "-ac", str(canaux), "pipe:1"],
                       input=sig.tobytes(), capture_output=True, check=True)
    out = np.frombuffer(r.stdout, dtype="<f4").astype(np.float64)
    out = out.reshape(-1, canaux) if canaux > 1 else out
    if len(out) < len(sig):
        out = np.concatenate([out, np.zeros((len(sig) - len(out),) + out.shape[1:])])
    return out[:len(sig)]


def loudnorm_mesure(sig):
    """{'I', 'TP', 'LRA'} par loudnorm (2 décimales) sur un signal (n,2) ou mono (compté en double mono)."""
    sig = np.asarray(sig, dtype=np.float32)
    if sig.ndim == 1:
        sig = np.stack([sig, sig], axis=1)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "pipe:0",
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"], input=sig.tobytes(), capture_output=True)
    e = r.stderr.decode()
    m = json.loads(e[e.rindex("{"):e.rindex("}") + 1])
    return {"I": float(m["input_i"]), "TP": float(m["input_tp"]), "LRA": float(m["input_lra"])}


# ── 1. DIALOGUE : le vrai appel, chaîne commune à toutes les voix ───────────
CHAINE_VOIX = ("highpass=f=100,equalizer=f=2800:t=q:w=1.2:g=2,"
               "acompressor=threshold=-24dB:ratio=2.5:attack=5:release=90")


def dialogue():
    brut = labo.lire(DIA["fichier"])
    assert len(brut) == N, (len(brut), N)
    v = brut[:, 0].copy()
    out = np.zeros(N)
    rapports = []
    for e in DIA["extraits"]:
        i0, i1 = int(round(e["film_in"] * SR)), int(round(e["film_out"] * SR))
        pad = int(0.2 * SR)
        seg = np.zeros(i1 - i0 + 2 * pad)
        seg[pad:pad + i1 - i0] = v[i0:i1]
        I0 = loudnorm_mesure(seg[pad:-pad])["I"]
        seg *= S.gain(-23.0 - I0)                                  # même niveau d'entrée pour le compresseur
        seg = ffmpeg_filtre(seg, CHAINE_VOIX)[pad:pad + i1 - i0]
        # bords : le fichier a déjà ses fondus de 15 ms dans des blancs ; on tue les traînées de filtre (3 ms)
        k = int(0.003 * SR)
        seg[:k] *= S.rampe_cos(k); seg[-k:] *= S.rampe_cos(k)[::-1]
        I1 = loudnorm_mesure(seg)["I"]
        seg *= S.gain(NIV["voix_lufs"] - I1)
        I2 = loudnorm_mesure(seg)["I"]
        out[i0:i1] = seg
        rapports.append({"id": e["id"], "lufs_origine": I0, "lufs_final": I2})
        cue(f"voix-{e['id']}", "dialogue", e["film_in"], f"son/dialogue.json extraits.{e['id']}.film_in",
            f"vrai appel, montes {e['source_in']} → {e['source_out']} s ; {CHAINE_VOIX} ; gain vers {NIV['voix_lufs']} LUFS",
            f"{I2:.2f} LUFS intégrés", pan=0.0, fin=e["film_out"], texte=e["texte"])
    return np.stack([out, out], axis=1), rapports


# ── 2. DUCKING : la nappe s'efface sous toute voix ──────────────────────────
def gain_ducking(voix_mono, seuil=-40.0, profondeur=-6.0, attaque=0.030, relache=0.250, anticipation=0.080, tenue=0.120):
    """Suiveur d'enveloppe sur le stem voix (RMS 10 ms), seuil −40 dBFS, −6 dB, attaque 30 ms, relâche 250 ms.
    En plus de la bible : anticipation de 80 ms (la nappe est déjà basse à l'attaque du premier mot après un long
    blanc : sans elle, le « Je » de 19,80 sortait 10 LU SOUS la nappe, mesuré) et tenue de 120 ms
    (pas de respiration dans les micro-blancs entre deux mots)."""
    w = 480
    c = np.concatenate([[0.0], np.cumsum(voix_mono ** 2)])
    idx = np.clip(np.arange(N) + w // 2, 0, N); jdx = np.clip(np.arange(N) - w // 2, 0, N)
    rms = np.sqrt(np.maximum(c[idx] - c[jdx], 0) / w)
    dessus = (20 * np.log10(rms + 1e-12) > seuil).reshape(-1, 48).any(axis=1)      # cadence 1 ms
    m = len(dessus)
    la, te = int(anticipation * 1000), int(tenue * 1000)
    cs = np.concatenate([[0], np.cumsum(dessus)])
    a = np.arange(m)
    anticipe = (cs[np.clip(a + la + 1, 0, m)] - cs[a]) > 0
    cs2 = np.concatenate([[0], np.cumsum(anticipe)])
    tenu = (cs2[a + 1] - cs2[np.clip(a - te, 0, m)]) > 0
    cible = np.where(tenu, profondeur, 0.0)
    ka, kr = 1 - np.exp(-1 / (attaque * 1000)), 1 - np.exp(-1 / (relache * 1000))
    g = np.zeros(m); x = 0.0
    for i in range(m):
        x += (cible[i] - x) * (ka if cible[i] < x else kr)
        g[i] = x
    g_ech = np.interp(np.arange(N) / SR, (np.arange(m) + 0.5) / 1000, g)
    return S.gain(g_ech)


# ── 3. NAPPE : additive, accordée en sol, suspendue jusqu'à « confirmation » ─
NOTES = {"G2": 98.00, "D3": 146.83, "F#3": 185.00, "G3": 196.00, "A3": 220.00, "B3": 246.94, "C4": 261.63, "D4": 293.66}


def poids_notes(t, plan):
    """Poids de chaque note au cours du temps. plan = [(debut, fondu, {note: poids}, forme)] ;
    fondus enchaînés à puissance constante (a² = a_avant²·cos² + a_après²·sin²), les notes communes ne bougent pas."""
    w = {k: np.zeros_like(t) for k in NOTES}
    avant = {}
    for (t0, d, accord, forme) in plan:
        p = np.clip((t - t0) / d, 0, 1)
        s = np.sin(np.pi * p / 2) ** 2 if forme == "puissance" else (0.5 - 0.5 * np.cos(np.pi * p)) ** 2
        for k in NOTES:
            a0, a1 = avant.get(k, 0.0), accord.get(k, 0.0)
            ici = t >= t0
            w[k][ici] = np.sqrt(a0 ** 2 * (1 - s[ici]) + a1 ** 2 * s[ici])
        avant = accord
    return w


def synthese_pad(t, poids, fc, graine):
    """Chaque note : partiels 1..6 d'amplitude k^−1,5, deux copies à ±3 cents (pan ∓0,35), LFO 0,1 Hz ±1 dB à phase
    propre, passe-bas à un pôle à fc(t) appliqué partiel par partiel (|H| = 1/√(1 + (f/fc)²))."""
    g = np.random.default_rng(graine)
    out = np.zeros((len(t), 2))
    for nom, f in NOTES.items():
        a = poids[nom]
        if not np.any(a > 0):
            g.random(20)
            continue
        lfo = S.gain(1.0 * np.sin(2 * np.pi * 0.1 * t + g.uniform(0, 2 * np.pi)))
        for cents, pan in ((-3, -0.35), (3, 0.35)):
            fn = f * 2 ** (cents / 1200)
            mono = np.zeros(len(t))
            for k in range(1, 7):
                fk = fn * k
                mono += k ** -1.5 / np.sqrt(1 + (fk / fc) ** 2) * np.sin(2 * np.pi * fk * t + g.uniform(0, 2 * np.pi))
            out += S.panner(mono * a * lfo, pan) / np.sqrt(2)
    return out


def chorus(x, in_gain=0.6, out_gain=0.9, delais=(0.050, 0.060), decroissances=(0.4, 0.32), vitesses=(0.25, 0.4),
           profondeurs=(0.002, 0.0023)):
    """Chorus de la bible (ffmpeg chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|2.3), refait en numpy avec des retards
    FRACTIONNAIRES (interpolation linéaire) : le filtre ffmpeg lit des retards entiers, et chaque saut d'un échantillon
    laissait un clic large bande à −60 dBFS dans la nappe (mesuré, 15 clics). Même modulation sur les deux canaux :
    un essai en quadrature élargissait l'image mais donnait une corrélation L/R négative (−0,35) sur la nappe seule."""
    n = len(x)
    t = np.arange(n) / SR
    y = in_gain * x.copy()
    for d, dec, v, p in zip(delais, decroissances, vitesses, profondeurs):
        for c, ph in ((0, 0.0), (1, 0.0)):
            pos = np.arange(n) - (d + p * (0.5 + 0.5 * np.sin(2 * np.pi * v * t + ph))) * SR
            i = np.floor(pos).astype(np.int64)
            fr = pos - i
            ok = i >= 0
            i0 = np.clip(i, 0, n - 1); i1 = np.clip(i + 1, 0, n - 1)
            y[:, c] += dec * np.where(ok, x[i0, c] * (1 - fr) + x[i1, c] * fr, 0.0)
    return y * out_gain


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.asarray(x) ** 2)) + 1e-12)


def nappe(duck):
    t_entree = mot("A1", 0)["debut"] + 0.10                 # 0,10 s après « Bonjour »
    t_sus4 = mot("A2A3", 0)["debut"]                       # « Laissez-moi voir »
    t_d7 = mot("A2A3", 2)["debut"]                         # « Je peux vous proposer »
    syl = MOTS["syllabes"]["confirmation_derniere_syllabe"]
    t_res = syl["voyelle"]                                 # la voyelle de « -tion », centre perceptif
    assert abs(round(t_res * 30) - EV["resolution_confirmation"]["image"]) <= 0
    t_bulle = EV["bulle_et_vibreur"]["t"]
    t_rac = EV["raccroche"]["t"]
    d_res = 0.12
    plan = [(t_entree, 1.5, {"G2": 1, "D3": 1, "G3": 1, "B3": 1}, "cos"),
            (t_sus4, 0.6, {"D3": 1, "G3": 1, "A3": 1, "D4": 1}, "puissance"),
            (t_d7, 0.8, {"D3": 1, "F#3": 1, "A3": 1, "C4": 1}, "puissance"),
            (t_res - d_res / 2, d_res, {"G2": 1, "G3": np.sqrt(2), "B3": 1}, "puissance")]
    i0, i1 = int(round((t_entree - 0.05) * SR)), int(round(t_rac * SR)) + int(0.4 * SR)
    t = temps(i0, i1 - i0)
    fc = np.full(len(t), 1800.0)
    p = np.clip((t - t_bulle) / 1.5, 0, 1)
    fc += 700.0 * (0.5 - 0.5 * np.cos(np.pi * p))            # le timbre s'ouvre quand la bulle s'ouvre
    sec = synthese_pad(t, poids_notes(t, plan), fc, graine=7)
    # gonflement de la résolution : +3 dB en 0,3 s, retour en 1,2 s
    u = t - t_res
    gdb = np.where((u >= 0) & (u < 0.3), 3 * (0.5 - 0.5 * np.cos(np.pi * u / 0.3)), 0.0)
    v = (u >= 0.3) & (u < 1.5)
    gdb[v] = 3 * (0.5 + 0.5 * np.cos(np.pi * (u[v] - 0.3) / 1.2))
    sec *= S.gain(gdb)[:, None]
    pad = np.zeros((int(0.2 * SR), 2))
    ch = chorus(np.vstack([sec, pad]))
    humide = labo.reverbe(ch, 3.0, 0.35, graine=41)
    piste = np.zeros((N, 2))
    S.ajouter(piste, humide, i0)
    # niveau : RMS −32 dBFS seule, mesurée sur l'accord d'accueil établi (avant atténuation)
    a, b = int(round((t_entree + 2.0) * SR)), int(round((t_sus4 - 0.1) * SR))
    piste *= S.gain(NIV["nappe_rms"] - rms_db(piste[a:b]))
    niveau_mesure = rms_db(piste[a:b])
    piste *= duck[:, None]
    for nom, (t0, d, acc, _) in zip(("accueil sol", "ré sus4", "ré7", "résolution sol"), plan):
        cue(f"nappe-{nom.replace(' ', '-')}", "nappe", t0, {
            "accueil sol": "mots A1[0].debut + 0,10", "ré sus4": "mots A2A3[0].debut (« Laissez-moi »)",
            "ré7": "mots A2A3[2].debut (« Je »)",
            "résolution sol": "mots.syllabes.confirmation_derniere_syllabe.voyelle − 0,06 (fondu centré sur la voyelle)"}[nom],
            f"accord {'·'.join(acc)} ; fondu {d} s", f"RMS {NIV['nappe_rms']} dBFS seule, −6 dB sous la voix")
    cue("nappe-ouverture", "nappe", t_bulle, "evenements.bulle_et_vibreur", "passe-bas 1 800 → 2 500 Hz en 1,5 s", "")
    return piste, {"t_entree": t_entree, "t_sus4": t_sus4, "t_d7": t_d7, "t_res": t_res, "rms_accueil": niveau_mesure}


def nappe_fin():
    t0 = EV["signature_re_contact"]["t"]
    f0, f1 = FIN_SON - 1.40, FIN_SON
    i0 = int(round(t0 * SR))
    t = temps(i0, int(round((FIN_SON - t0) * SR)))
    plan = [(t0, 0.8, {"G2": 1, "D3": 1, "G3": 1, "B3": 1, "D4": 1}, "cos")]
    sec = synthese_pad(t, poids_notes(t, plan), np.full(len(t), 2500.0), graine=8)
    ch = chorus(np.vstack([sec, np.zeros((int(0.2 * SR), 2))]))
    humide = labo.reverbe(ch, 3.0, 0.35, graine=42)
    piste = np.zeros((N, 2))
    S.ajouter(piste, humide, i0)
    tt = np.arange(N) / SR
    p = np.clip((tt - f0) / (f1 - f0), 0, 1)
    piste *= (0.5 + 0.5 * np.cos(np.pi * p))[:, None]       # fondu de sortie en cosinus, après la réverbe
    piste[tt >= f1] = 0
    a, b = int(round((t0 + 1.0) * SR)), int(round(f0 * SR))
    piste *= S.gain(NIV["nappe_fin_rms"] - rms_db(piste[a:b]))
    cue("nappe-fin", "nappe", t0, "evenements.signature_re_contact", "sol majeur G2·D3·G3·B3·D4, attaque 0,8 s, "
        f"fondu cosinus {f0:.2f} → {f1:.2f}", f"RMS {NIV['nappe_fin_rms']} dBFS")
    return piste


# ── 4. SFX : la ligne, le décroché, les touchers, le vibreur, le raccroché ──
def tonalite(t, seg, rampe):
    """Tonalité française : 440 Hz, tanh(1,3·x)/tanh(1,3) (couleur de ligne)."""
    return S.couleur_ligne(np.sin(2 * np.pi * 440.0 * t), 1.3) * trapeze(t, [seg], [rampe], forme="cos")


def clic(duree=0.030, f_sourd=180.0, d_sourd=0.025, graine=51):
    """Clic de prise de ligne : 2 ms de bruit blanc en Hann → passe-bas à un pôle à 3 kHz ; + 180 Hz sous une
    fenêtre demi-sinus de 25 ms, 2 dB plus bas."""
    n = int(round(duree * SR))
    g = np.random.default_rng(graine)
    k = int(0.002 * SR)
    b = g.standard_normal(k) * np.hanning(k + 2)[1:-1]
    a = 1 - np.exp(-2 * np.pi * 3000 / SR)
    y = np.zeros(n); x = 0.0
    for i in range(n):
        x += a * ((b[i] if i < k else 0.0) - x)
        y[i] = x
    y /= np.max(np.abs(y))
    m = int(round(d_sourd * SR))
    ts = np.arange(m) / SR
    s = np.sin(2 * np.pi * f_sourd * ts) * np.sin(np.pi * ts / d_sourd)
    y[:m] += s / np.max(np.abs(s)) * S.gain(-2)
    return y / np.max(np.abs(y))


def raccroche():
    """Le raccroché, 80 ms : la même matière que le décroché (la ligne), transitoire à l'instant exact,
    suivie d'un sourd de 30 ms à 120 Hz. Rien après : la ligne est partie."""
    y = clic(duree=0.080, f_sourd=120.0, d_sourd=0.030, graine=52)
    k = int(0.010 * SR)
    y[-k:] *= S.rampe_cos(k)[::-1]
    return y


def vibreur(t, env):
    """Vibreur du téléphone à l'écran (pleine bande : il n'est pas dans l'appel). Moteur en dent de scie 165 Hz à bande
    limitée (1/k, ≤ 6 kHz) → passe-bas un pôle 1 kHz (module et phase par harmonique), + 330 Hz à 30 %,
    modulation (1 + 0,3·sin 2π·32t), grésillement de boîtier (bruit blanc 1,5-4 kHz, 0,25 × RMS moteur)."""
    f0, fc = 165.0, 1000.0
    m = np.zeros(len(t))
    for k in range(1, int(6000 / f0) + 1):
        fk = f0 * k
        m += -(2 / np.pi) / k / np.sqrt(1 + (fk / fc) ** 2) * np.sin(2 * np.pi * fk * t - np.arctan(fk / fc))
    m /= np.max(np.abs(m))
    m += 0.3 * np.sin(2 * np.pi * 330.0 * t)
    m *= 1 + 0.3 * np.sin(2 * np.pi * 32.0 * t)
    m *= env
    g = np.random.default_rng(61)
    br = S.passe_bande(g.standard_normal(len(t)), 1500, 4000, front=200)
    br /= np.sqrt(np.mean(br ** 2))
    br *= 0.25 * np.sqrt(np.mean(m[env > 0.99] ** 2)) * env
    return m + br


def sfx_et_signature():
    sfx = np.zeros((N, 2))
    sig = np.zeros((N, 2))
    s1 = SEC["s1"]
    (a0, a1), (b0, b1) = s1["segments_s"]
    ra, rb = s1["rampes_s"]
    t_dec = EV["decroche"]["t"]
    assert abs(b1 - t_dec) < 1e-9, "la 2e tonalité doit s'ouvrir au décroché"
    # 4.1 tonalité n° 1 (0 → 1,5 s), mono au centre, dans sfx
    i0, i1 = int(round(a0 * SR)), int(round(a1 * SR))
    t = temps(i0, i1 - i0)
    ton1 = tonalite(t, (a0, a1), ra) * S.gain(NIV["ton"])
    sfx[i0:i1] += ton1[:, None]
    cue("ton-1", "sfx", a0, "secousses.s1.segments_s[0]", "440 Hz, tanh(1,3x)/tanh(1,3), fondus 10 ms en cosinus "
        "(même moyenne par image que secousses.s1)", f"{NIV['ton']} dBFS crête", pan=0.0, fin=a1)
    # 4.2 la ligne froide : bruit rose 300-3 400 Hz, coupé net en 2 ms au décroché
    n = int(round(t_dec * SR))
    br = S.passe_bande(labo.bruit_rose(n, graine=3), 300, 3400, front=50)
    br *= S.gain(NIV["ligne_rms"] - rms_db(br))
    k = int(0.002 * SR); br[-k:] *= S.rampe_cos(k)[::-1]
    k = int(0.005 * SR); br[:k] *= S.rampe_cos(k)
    sfx[:n] += br[:, None]
    cue("souffle-ligne", "sfx", 0.0, "0 → evenements.decroche", "bruit rose graine 3, passe-bande 300-3 400 Hz, coupe 2 ms",
        f"RMS {NIV['ligne_rms']} dBFS", pan=0.0, fin=t_dec)
    # 4.3 tonalité n° 2 qui devient le la : même oscillateur (phase absolue continue), s'ouvre en cloche au décroché
    i0 = int(round(b0 * SR)); n = int(round((t_dec + 1.3 - b0) * SR))
    t = temps(i0, n)
    phi = 2 * np.pi * 440.0 * t
    tau = np.maximum(t - t_dec, 0)
    r = np.clip(tau / 0.060, 0, 1)
    I = 1.4 * r * np.exp(-np.maximum(tau - 0.060, 0) / 0.5)
    y = S.couleur_ligne(np.sin(phi + I * np.sin(phi)), 1.3 * (1 - r))
    env = np.where(t < t_dec, trapeze(t, [(b0, t_dec + 10)], [(rb[0], 0)], forme="cos"), np.exp(-tau / 0.45))
    k = int(0.25 * SR); env[-k:] *= S.rampe_cos(k)[::-1]
    y = y * env * S.gain(NIV["ton"])
    w = np.clip((t - t_dec) / 0.060, 0, 1); w = 0.5 - 0.5 * np.cos(np.pi * w)
    st = S.panner(y, pan_point(t) * w)                       # pan 0 (la ligne), puis glissé en 60 ms vers le point
    S.ajouter(sig, st, i0)
    envoi = np.clip((t - t_dec) / 0.020, 0, 1)                # envoi en réverbe ouvert en 20 ms : pas de front raide
    queue = st * (0.5 - 0.5 * np.cos(np.pi * envoi))[:, None]
    S.ajouter(sig, 0.12 * S.humide(queue, 1.2, graine=32), i0)
    cue("ton-2-la", "signature", b0, "secousses.s1.segments_s[1] ; ouverture = evenements.decroche",
        "même oscillateur 440 Hz ; dès le décroché y = sin(φ + I(τ)·sin φ), I = 1,4·min(τ/0,06 ; 1)·exp(−max(τ−0,06 ; 0)/0,5), "
        "amplitude exp(−τ/0,45), la couleur tanh s'efface en 60 ms ; réverbe 1,2 s à 12 % sur la queue",
        f"{NIV['ton']} dBFS crête", pan=f"0 puis point ({pan_point(t_dec):+.3f} au décroché, suit le retour chariot)",
        ouverture=t_dec)
    # 4.4 clic de décroché
    poser_mobile(sfx, clic(), t_dec, NIV["clic"])
    cue("clic-decroche", "sfx", t_dec, "evenements.decroche", "bruit 2 ms Hann → passe-bas 3 kHz + 180 Hz / 25 ms",
        f"{NIV['clic']} dBFS crête", pan=round(float(pan_point(t_dec)), 3))
    # 4.5 sol du décroché (2e note du motif) : même écart que la signature (sol − la)
    d_sol = EV["signature_sol"]["t"] - EV["signature_la"]["t"]
    d_re = EV["signature_re_contact"]["t"] - EV["signature_la"]["t"]
    assert abs(d_sol - 0.24) < 1e-6 and abs(d_re - 0.60) < 1e-6, (d_sol, d_re)
    t_sol1 = t_dec + d_sol
    poser_mobile(sig, S.note_sol(1.6, tau=0.5), t_sol1, NIV["sol_decroche"], rev=(1.2, 0.15), graine=33)
    cue("cloche-sol-1", "signature", t_sol1, "evenements.decroche + (signature_sol − signature_la)",
        "sol4 392 Hz FM 1:1, indice 1,2·exp(−τ/0,25), amplitude exp(−τ/0,5), attaque 5 ms, réverbe 1,2 s à 15 %",
        f"{NIV['sol_decroche']} dBFS crête", pan=f"suit le point ({pan_point(t_sol1):+.3f} puis retour chariot vers {pan_point(5.0):+.3f})")
    # 4.6 les touchers du point sur les heures : ré court étouffé, à l'échantillon du contact
    for nom, niv, lib in (("contact_neuf", NIV["tap"], "tap-9h"), ("contact_dix", NIV["tap"], "tap-10h"),
                          ("contact_onze", NIV["tap"], "tap-11h"), ("contact_retour_neuf", NIV["tap_retour"], "tap-retour-9h")):
        tc = EV[nom]["t"]
        poser_mobile(sfx, S.re_court(), tc, niv, rev=(0.8, 0.12), graine=34)
        cue(lib, "sfx", tc, f"evenements.{nom}", "ré5 587,33 Hz (τ 0,09) + ×3,99 (τ 0,03), maillet 1,5 ms 2-5 kHz à −18 dB, "
            "réverbe 0,8 s à 12 %", f"{niv} dBFS crête", pan=round(float(pan_point(tc)), 3))
    # 4.7 le la · sol de l'écriture du rendez-vous : ils voyagent avec la plume
    t_ecr = EV["ecriture_debut"]["t"]
    poser_mobile(sig, S.note_la(1.2, tau=0.35), t_ecr, NIV["la_rdv"], rev=(1.2, 0.15), graine=35)
    cue("cloche-la-rdv", "signature", t_ecr, "evenements.ecriture_debut", "la4 440 Hz, sinus qui s'ouvre en cloche FM 1:1 "
        "(indice 0 → 1,4 en 60 ms), τ 0,35 s, attaque 8 ms, réverbe 1,2 s à 15 %", f"{NIV['la_rdv']} dBFS crête",
        pan=f"suit la plume {pan_point(t_ecr):+.3f} → {pan_point(EV['ecriture_fin']['t']):+.3f}")
    poser_mobile(sig, S.note_sol(1.4, tau=0.45), t_ecr + d_sol, NIV["sol_rdv"], rev=(1.2, 0.15), graine=36)
    cue("cloche-sol-rdv", "signature", t_ecr + d_sol, "evenements.ecriture_debut + (signature_sol − signature_la)",
        "sol4 392 Hz FM 1:1, τ 0,45 s", f"{NIV['sol_rdv']} dBFS crête",
        pan=f"suit la plume ({pan_point(t_ecr + d_sol):+.3f} à l'attaque)")
    # 4.8 vibreur : l'enveloppe EST secousses.s6 (mêmes segments, mêmes rampes linéaires que l'image)
    s6 = SEC["s6"]
    v0, v1 = s6["segments_s"][0][0], s6["segments_s"][-1][1]
    assert abs(round(v0 * 30) - EV["bulle_et_vibreur"]["image"]) == 0
    i0 = int(round(v0 * SR)); n = int(round((v1 - v0 + 0.01) * SR))
    t = temps(i0, n)
    env = trapeze(t, s6["segments_s"], s6["rampes_s"])
    vb = vibreur(t, env)
    vb = vb / np.max(np.abs(vb)) * S.gain(NIV["vibreur"])
    sfx[i0:i0 + n] += vb[:, None]
    cue("vibreur", "sfx", v0, "secousses.s6.segments_s (= evenements.bulle_et_vibreur)",
        "dent de scie 165 Hz à bande limitée → passe-bas 1 kHz + 330 Hz 30 %, AM 32 Hz, grésillement 1,5-4 kHz ; "
        "enveloppe trapèze 12/25 ms identique à secousses.s6", f"{NIV['vibreur']} dBFS crête", pan=0.0,
        segments=s6["segments_s"])
    return sfx, sig


def signature_film(sig):
    t_la = EV["signature_la"]["t"]
    pan_i = 0.6 * (MES["s7"]["centre"]["x"] - 540) / 540
    x_contact = x_point(EV["signature_re_contact"]["t"])
    assert abs(x_contact - MES["s7"]["centre"]["x"]) < 0.01
    motif = S.signature("longue", pan=pan_i) * S.gain(NIV["signature_decalage_db"])
    S.ajouter(sig, motif, int(round(t_la * SR)))
    o = NIV["signature_decalage_db"]
    for nom, clef, niv in (("signature-la", "signature_la", -16 + o), ("signature-sol", "signature_sol", -17 + o),
                           ("signature-re", "signature_re_contact", -15 + o)):
        cue(nom, "signature", EV[clef]["t"], f"evenements.{clef}", "son/signature.py (le même rendu que le livrable seul)",
            f"{niv} dBFS crête", pan=round(pan_i, 4))
    return sig


# ── 5. MASTER : un gain, un limiteur à crête vraie ──────────────────────────
def filtre_min(a, w):
    """Minimum glissant centré de largeur impaire w (van Herk / Gil-Werman)."""
    h = w // 2
    p = np.concatenate([np.ones(h), a, np.ones(h + w)])
    nb = -(-len(p) // w)
    p = np.concatenate([p, np.ones(nb * w - len(p))]).reshape(nb, w)
    pre = np.minimum.accumulate(p, axis=1).ravel()
    suf = np.minimum.accumulate(p[:, ::-1], axis=1)[:, ::-1].ravel()
    i = np.arange(len(a))
    return np.minimum(suf[i], pre[i + w - 1])


def crete_os(x, facteur=4):
    n = len(x)
    M = 1 << (n - 1).bit_length()
    pk = np.zeros(n)
    for c in range(x.shape[1]):
        y = np.fft.irfft(np.fft.rfft(x[:, c], M), M * facteur) * facteur
        pk = np.maximum(pk, np.abs(y[:n * facteur]).reshape(n, facteur).max(axis=1))
    return pk


def gain_limiteur(x, plafond_db=PLAFOND_DBTP, anticipation=0.0015, relache=0.060):
    c = S.gain(plafond_db)
    r = np.minimum(1.0, c / np.maximum(crete_os(x), 1e-12))
    if r.min() >= 1:
        return np.ones(len(x)), 0.0
    L = int(anticipation * SR); w = 2 * L + 1
    m = filtre_min(r, w)
    cs = np.concatenate([[0.0], np.cumsum(np.concatenate([np.ones(L), m, np.ones(L)]))])
    g = (cs[w:] - cs[:-w]) / w            # moyenne des minimums voisins : g(n) ≤ r(n) partout
    a = 1 - np.exp(-1 / (relache * SR))
    out = g.copy()
    idx = np.nonzero(g < 1)[0]
    if len(idx):
        # la récursion de relâche ne sert qu'autour des réductions : on la parcourt sur ces zones seulement
        fin = min(len(g), idx[-1] + int(10 * relache * SR))
        x_ = out[idx[0] - 1] if idx[0] > 0 else 1.0
        gg = g[idx[0]:fin]
        oo = np.empty_like(gg)
        for i in range(len(gg)):
            v = gg[i]
            x_ = v if v < x_ else x_ + (v - x_) * a
            oo[i] = x_
        out[idx[0]:fin] = oo
    return out, 20 * np.log10(out.min())


def main():
    STEMS.mkdir(exist_ok=True)
    print("1. dialogue")
    dlg, rap_voix = dialogue()
    for r in rap_voix:
        print(f"   {r['id']:5s} {r['lufs_origine']:7.2f} → {r['lufs_final']:7.2f} LUFS")
    print("2. ducking + nappe")
    duck = gain_ducking(dlg[:, 0])
    nap, info_nappe = nappe(duck)
    print("3. sfx + signature")
    sfx, sig = sfx_et_signature()
    # 5. le raccroché : au même échantillon, la nappe et toutes les queues coupées en 5 ms, DÉFINITIVEMENT (la réverbe
    #    de 3 s de la nappe ne doit pas revenir après le silence) ; puis silence numérique. Ce qui vient après
    #    (signature, nappe de fin) est ajouté seulement ensuite.
    t_rac = EV["raccroche"]["t"]
    s0, s1_ = EV["silence_numerique"]["t"]
    i_rac, i_s0, i_s1 = int(round(t_rac * SR)), int(round(s0 * SR)), int(round(s1_ * SR))
    coupe = np.ones(N)
    k = int(0.005 * SR)
    coupe[i_rac:i_rac + k] = S.rampe_cos(k)[::-1]
    coupe[i_rac + k:] = 0
    for st in (dlg, nap, sfx, sig):
        st *= coupe[:, None]
    sig = signature_film(sig)
    nap += nappe_fin()
    assert not np.any(nap[i_rac + k:int(round(EV["signature_re_contact"]["t"] * SR))]), "rien dans la nappe avant le ré"
    rac = raccroche() * S.gain(NIV["raccroche"])
    assert i_rac + len(rac) <= i_s0, "le raccroché doit finir avant le silence numérique"
    sfx[i_rac:i_rac + len(rac)] += rac[:, None]
    cue("raccroche", "sfx", t_rac, "evenements.raccroche", "numpy, même matière que le clic de décroché : transitoire "
        "2 ms → passe-bas 3 kHz + 120 Hz / 30 ms ; nappe et queues coupées en 5 ms au même échantillon",
        f"{NIV['raccroche']} dBFS crête", pan=0.0)
    cue("silence-numerique", "tous", s0, "evenements.silence_numerique", "zéros numériques sur toutes les pistes",
        "exactement 0", fin=s1_)
    fin = int(round(FIN_SON * SR))
    for st in (dlg, nap, sfx, sig):
        st[fin:] = 0
    cue("silence-final", "tous", FIN_SON, "fin − 0,30 s (bible silence-final)", "zéros numériques jusqu'à la fin",
        "exactement 0", fin=DUREE)
    stems = {"dialogue": dlg, "nappe": nap, "sfx": sfx, "signature": sig}
    somme = dlg + nap + sfx + sig
    print("4. master")
    G = LUFS_CIBLE - loudnorm_mesure(somme)["I"]
    for it in range(6):
        x = somme * S.gain(G)
        g_lim, red = gain_limiteur(x)
        y = x * g_lim[:, None]
        m = loudnorm_mesure(y)
        print(f"   passe {it}: gain {G:+.2f} dB, réduction max {red:.2f} dB → {m['I']:.2f} LUFS, {m['TP']:.2f} dBTP")
        if abs(m["I"] - LUFS_CIBLE) <= 0.04:
            break
        G += LUFS_CIBLE - m["I"]
    mix = y
    # stems au gain du master ET avec la même courbe du limiteur : leur somme = mix.wav
    for nom, st in stems.items():
        S.ecrire24(STEMS / f"{nom}.wav", st * S.gain(G) * g_lim[:, None])
    S.ecrire24(ICI / "mix.wav", mix)
    shutil.copyfile(ICI / "mix.wav", PROJET / "assets" / "son" / "mix.wav")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ICI / "mix.wav", UPLOADS / "point-solaire-bande-son.wav")
    # niveau final de chaque cue ponctuel (crête dans le stem final, sur 0,3 s après l'attaque)
    finals = {nom: st * S.gain(G) * g_lim[:, None] for nom, st in stems.items()}
    for c in CUES:
        niv = c["niveau_avant_master"]
        if c["stem"] in ("sfx", "signature") and niv.endswith("dBFS crête"):
            # crête propre du cue dans le master : niveau + gain de master + gain de la loi de pan (canal le plus fort)
            p = c["pan"] if isinstance(c.get("pan"), (int, float)) else float(pan_point(c["t"]))
            a = (p + 1) * np.pi / 4
            c["crete_propre_finale_dbfs"] = round(float(niv.split()[0]) + G + 20 * np.log10(np.sqrt(2) * max(np.cos(a), np.sin(a))), 1)
            i = c["echantillon"]
            seg = finals[c["stem"]][max(0, i - int(0.005 * SR)):i + int(0.1 * SR)]
            c["crete_stem_100ms_dbfs"] = round(float(S.db(np.max(np.abs(seg)))), 1)   # notes voisines et réverbe comprises
        elif c["stem"] == "dialogue":
            i, j = c["echantillon"], int(round(c["fin"] * SR))
            c["crete_finale_dbfs"] = round(float(S.db(np.max(np.abs(finals["dialogue"][i:j])))), 1)
            c["lufs_final"] = round(float(niv.split()[0]) + G, 2)
    red_db = -20 * np.log10(g_lim)
    actif = {"part_du_temps_reduction_sup_0.5_db": round(float(np.mean(red_db > 0.5)), 4),
             "part_du_temps_reduction_sup_1_db": round(float(np.mean(red_db > 1.0)), 4),
             "part_du_temps_reduction_sup_2_db": round(float(np.mean(red_db > 2.0)), 5)}
    print(f"   limiteur : {actif}")
    rapport = {"gain_master_db": round(G, 3), "reduction_limiteur_max_db": round(red, 2), "plafond_dbtp": PLAFOND_DBTP,
               "limiteur_activite": actif,
               "voix": rap_voix, "nappe": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in info_nappe.items()},
               "niveaux_avant_master": NIV, "cues": sorted(CUES, key=lambda c: c["t"])}
    (ICI / "cues.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1))
    print(f"   mix : {ICI / 'mix.wav'}  ({labo.mesurer(ICI / 'mix.wav')})")


if __name__ == "__main__":
    main()
