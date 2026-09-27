#!/usr/bin/env python3
"""Bande son v2 du showcase « Le point sur le i » (critique.json plan.chantiers « son » : UN ARC QUI MONTE VERS LA MARQUE).

    python3 son/mix.py            le master (sans la variante « monde »)
    python3 son/mix.py --monde    le master ET la variante « monde » (bruitages ElevenLabs en s1), fichier SÉPARÉ

Entrées (aucun instant en dur : chaque temps vient d'une donnée, ou d'un décalage nommé ci-dessous et documenté) :
  son/dialogue.wav + son/dialogue.json      le vrai appel du 18/09 placé aux temps v2 du film (C4 à son vrai blanc)
  donnees/evenements.json                   décroché, contacts, écriture, raccroché, silence, vibreur, plume, signature
  donnees/secousses.json                    enveloppes s1 (tonalité) et s6 (vibreur) : l'image lit la même donnée
  donnees/mots.json                         attaques des mots (accords) et voyelle de « -tion » (la résolution)
  donnees/point-resolu.json                 x (sans secousse) et vitesse du point à chaque image : pan = 0,6·(x − 540)/540
  donnees/point.json                        taille du point (la pédale naît quand il atteint 44 px)
Sorties :
  son/stems/dialogue.wav  nappe.wav  sfx.wav  signature.wav   (48 kHz, 24 bits, stéréo, gain de master et courbe du
                                                               limiteur compris : leur somme redonne mix.wav)
  son/mix.wav  +  assets/son/mix.wav (lu par index.html)  +  /root/vokio-uploads/videos/showcase/point-solaire-bande-son-v2.wav
  son/cues.json                             chaque cue posé : instant, échantillon, source de l'instant, niveau, pan
  (--monde) son/mix-monde.wav + son/stems/monde.wav + son/monde/*.wav (les 8 prises) +
            /root/vokio-uploads/videos/showcase/point-solaire-bande-son-monde-v2.wav

Doctrine (inchangée) : ce qui est DANS l'appel garde sa bande téléphone (la voix, la tonalité, la ligne) ; ce qui est le
film (le point, le téléphone à l'écran, la marque) est en pleine bande. v2 : la signature EST ce passage, « la ligne
s'ouvre ». Une seule matière pour la musique : le verre (frotté pour la nappe, frappé pour le point et le ré).
Master : un seul gain (−14 LUFS intégrés) et un limiteur à crête vraie ; aucun loudnorm dynamique (il écraserait le
silence numérique).
"""
import argparse
import hashlib
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
MONDE = ICI / "monde"
UPLOADS = Path("/root/vokio-uploads/videos/showcase")
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402

SR = labo.SR
LUFS_CIBLE = -14.0
PLAFOND_DBTP = -1.7          # plan : ≤ −1,5 dBTP APRÈS AAC 256k ; à −1,5 le contrôle AAC lisait −1,48 : marge de 0,2 dB


def J(chemin):
    return json.loads(Path(chemin).read_text())


EV = J(DON / "evenements.json")
SEC = J(DON / "secousses.json")
MOTS = J(DON / "mots.json")
SCENES = J(DON / "scenes.json")
PR = J(DON / "point-resolu.json")["images"]
POINTJ = J(DON / "point.json")
DIA = J(ICI / "dialogue.json")

DUREE = max(s["fin"] for s in SCENES.values())
assert abs(DUREE - EV["fin"]["t"]) < 1e-9
N = int(round(DUREE * SR))
FIN_SON = EV["silence_final"]["t"][0]          # 46,70 : zéros numériques jusqu'à 47,00 (boucle TikTok)

# niveaux avant master (dBFS crête sauf mention) : plan v2 (critique.json plan.chantiers « son »)
NIV = {
    "ton": -25.0,              # point 1 : −2 dB (la voix reste l'élément le plus fort, la tonalité ne dicte pas le volume)
    "ligne_rms": -56.0,
    "clic": -32.0,
    "sol_decroche": -27.0,     # point 1
    "tap": -22.0, "tap_retour": -26.0,     # point 7 ; finition : +5 dB et timbre clair (re_court(clair=True)) : les touchers
                                           # de « neuf » et « dix » sortent de la voix sur un haut-parleur de téléphone
    "la_rdv": -26.0, "sol_rdv": -26.0,     # point 8 (inchangés)
    "vibreur": -19.0,          # point 10
    "raccroche": -24.0,        # point 9
    "nappe_rms": -35.9,        # accord de sol établi, seul, avant atténuation : réglé par la marge de la voix (contrôle F
                               # ≥ 10 LU) ; à −32 (v1), le verre au-dessus de 300 Hz et la tension laissaient 7,4 LU
    "pedale_poids": 0.55,      # point 3 : ≈ −42 dBFS RMS seule, contrôlé dans cues.json
    "air_sms_rms": -40.0,      # point 11
    "stylo": -40.0,            # point 12
    "nappe_fin_rms": -25.5,    # point 14 (plan −31 ; finition −25,5 : la fin devient le moment le plus fort en sonie court terme) : réglé par l'arc (contrôle M, sonie sur [41,20 ; 42,70] ≥ médiane
                               # court terme du dialogue + 1 LU) : à −31 la fin restait 0,9 LU au-dessus, ré compris ;
                               # à −23,5 l'accord couvrait la queue du ré de 7 dB 1,2 s après le contact. À −27, l'accord
                               # rejoint le ré 0,8 s après le contact, puis fleurit
    "voix_lufs": -21.0,        # point 15 (−1 dB)
    "signature_decalage_db": 1.5,          # point 13 (au lieu de −1,5 ; finition : +1 dB, la signature passe au-dessus du pic du dialogue)
    "monde_momentane_lufs": -28.5,         # point 16 : ≤ −28 LUFS instantanés (dans le mix final)
}

# décalages nommés (le plan les donne par rapport à un événement ; aucune autre constante de temps)
DEC = {
    "sol_avant_C1": 0.30,          # point 4 : l'accord de sol entre 0,30 s avant l'extrait C1 (10,50 → 10,20)
    "pedale_fondu": 1.5,           # point 3 : 4,60 → 6,10
    "resolution_fondu": 0.12,      # points 3 et 4 : fondu centré sur la voyelle de « -tion »
    "air_sms_apres_vibreur": 0.053333,     # point 11 : 36,72 = bulle_et_vibreur + 1,6 image
    "air_sms_avant_la": 0.05,      # point 11 : −4 dB dès 40,55 = signature_la − 0,05
    "fin_fondu": 1.40,             # point 14 : fondu cosinus 45,30 → 46,70 (finition : film de 47,00 s)
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


def extrait(id_):
    return next(e for e in DIA["extraits"] if e["id"] == id_)


# ── les instants (tous tirés des données) ───────────────────────────────────
T = {
    "decroche": EV["decroche"]["t"],
    "pedale": POINTJ["taille"][-1]["t"],                   # 4,60 : le point atteint 44 px, la pédale naît
    "sol": extrait("C1")["film_in"] - DEC["sol_avant_C1"],  # 10,20
    "sus4": mot("A2A3", 0)["debut"],                       # 17,59 « Laissez-moi »
    "re7": mot("A2A3", 2)["debut"],                        # 19,80 « Je peux vous proposer »
    "re9": extrait("A4")["film_in"],                       # 26,17 « Parfait »
    "resolution": MOTS["syllabes"]["confirmation_derniere_syllabe"]["voyelle"],   # 32,955
    "raccroche": EV["raccroche"]["t"],
    "vibreur": EV["bulle_et_vibreur"]["t"],
    "la": EV["signature_la"]["t"], "sol_sig": EV["signature_sol"]["t"], "re": EV["signature_re_contact"]["t"],
}
T["air_sms"] = T["vibreur"] + DEC["air_sms_apres_vibreur"]
assert abs(round(T["resolution"] * 30) - EV["resolution_confirmation"]["image"]) == 0
assert abs(T["pedale"] - 4.60) < 1e-6 and abs(T["sol"] - 10.20) < 1e-6, (T["pedale"], T["sol"])

# ── le point : x (sans secousse) et vitesse à l'échantillon, pan ────────────
_T_IMG = np.array([p["t"] for p in PR])
_X_IMG = np.array([p["x_sans"] for p in PR])
_V_IMG = np.array([p["v"] for p in PR])


def x_point(t):
    return np.interp(t, _T_IMG, _X_IMG)


def v_point(t):
    return np.interp(t, _T_IMG, _V_IMG)


def pan_point(t):
    return 0.6 * (x_point(t) - 540.0) / 540.0


def temps(i0, n):
    return (i0 + np.arange(n)) / SR


def poser_mobile(piste, mono, t0, niveau_db, rev=None, pan_fn=pan_point, graine=31, poids_pan=None):
    """Place un son mono du point, attaché au point : pan(t) = pan_fn(t) [× poids_pan] à chaque échantillon.
    rev = (secondes, envoi) : retour de réverbe seul ajouté au direct."""
    i0 = int(round(t0 * SR))
    sig = mono * S.gain(niveau_db)
    p = pan_fn(temps(i0, len(sig)))
    if poids_pan is not None:
        p = p * poids_pan
    st = S.panner(sig, p)
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


ffmpeg_filtre = S.ffmpeg_filtre


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


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.asarray(x) ** 2)) + 1e-12)


def fondu_cos(t, t0, d):
    """0 → 1 en cosinus surélevé de t0 à t0 + d."""
    p = np.clip((t - t0) / d, 0, 1)
    return 0.5 - 0.5 * np.cos(np.pi * p)


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
        k = int(0.003 * SR)                                         # bords : on tue les traînées de filtre (3 ms)
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
def gain_ducking(voix_mono, seuil=-40.0, profondeur=-8.0, attaque=0.030, relache=0.250, anticipation=0.080, tenue=0.120):
    """Suiveur d'enveloppe sur le stem voix (RMS 10 ms), seuil −40 dBFS, attaque 30 ms, relâche 250 ms, anticipation
    80 ms, tenue 120 ms (v1). Profondeur −8 dB (v1 : −6) : la tension du ré7 (+3 dB, passe-bas qui s'ouvre, cinq voix)
    laissait « pour » (27,1 s) à 8,7 LU ; la nappe garde son niveau dans les blancs (le silence de l'outil)."""
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


# ── 3. NAPPE : verre frotté au-dessus de 300 Hz, pédale la puis sol, ré7 qui se tend ──
NOTES = {"G2": 98.00, "D3": 146.83, "G3": 196.00, "A3": 220.00, "B3": 246.94, "D4": 293.66, "E4": 329.63,
         "F#4": 369.99, "G4": 392.00, "A4": 440.00, "B4": 493.88, "C5": 523.25, "D5": 587.33}
SEUIL_VERRE = 196.0          # point 6 : notes ≥ 196 Hz en verre frotté ; G2 et D3 en additif doux
# Une voix par note (un verre par note, comme un harmonica de verre), placée dans le champ stéréo : la v1 doublait chaque
# note à ±3 cents panoramiqués à ∓0,35 ; en mono chaque note battait alors à pleine profondeur (1,4 Hz à 392 Hz) et les
# battements de l'accord de résolution passaient G/D en opposition (corrélation −0,25 à 33,6 s, mesurée). Les mouvements
# de la résolution restent du même côté : F#4 → G4 à gauche, C5 → B4 à droite, E4 → D4 un peu à droite ; basse au centre.
PAN_NOTES = {"G2": 0.0, "D3": 0.0, "G3": -0.20, "A3": -0.15, "B3": 0.20, "D4": 0.15, "E4": 0.15, "F#4": -0.30,
             "G4": -0.30, "A4": -0.40, "B4": 0.30, "C5": 0.30, "D5": 0.40}
POIDS_ADDITIF = 0.6          # G2 et D3 de la nappe à 0,6 (−4,4 dB) : ils ne passent pas sur un haut-parleur de
                             # téléphone (perte de la nappe, contrôle H) ; l'excitateur rend leurs harmoniques
K_ADDITIF = 12               # point 5 : partiels k ≤ 12
ATTAQUE_VERRE = 0.180


def poids_notes(t, plan):
    """Poids de chaque note au cours du temps. plan = [(debut, fondu, {note: poids}, forme)] ; fondus enchaînés
    (forme « puissance » : a² = a_avant²·cos² + a_après²·sin² ; « cos » : amplitude en cosinus), les notes communes
    ne bougent pas."""
    w = {k: np.zeros_like(t) for k in NOTES}
    avant = {}
    for (t0, d, accord, forme) in plan:
        p = np.clip((t - t0) / d, 0, 1)
        s = np.sin(np.pi * p / 2) ** 2 if forme == "puissance" else (0.5 - 0.5 * np.cos(np.pi * p)) ** 2
        ici = t >= t0
        for k in NOTES:
            a0, a1 = avant.get(k, 0.0), accord.get(k, 0.0)
            w[k][ici] = np.sqrt(a0 ** 2 * (1 - s[ici]) + a1 ** 2 * s[ici])
        avant = accord
    return w


def voix_additive(t, f, rng, rng_note):
    """Additif doux (G2, D3) : partiels 1..12 d'amplitude k^−1,5, LFO 0,1 Hz ±1 dB à phase propre (v1). Les phases des
    partiels viennent de la note (les deux copies à ±3 cents partent en phase), le LFO de la copie."""
    lfo = S.gain(1.0 * np.sin(2 * np.pi * 0.1 * t + rng.uniform(0, 2 * np.pi)))
    y = np.zeros(len(t))
    for k in range(1, K_ADDITIF + 1):
        y += k ** -1.5 * np.sin(2 * np.pi * f * k * t + rng_note.uniform(0, 2 * np.pi))
    return y * lfo


def voix_verre(t, f, rng, graine_bruit, ph0=None):
    """Verre frotté (harmonica de verre), point 6 :
    y = sin φ + 0,08·sin 2φ + 0,03·sin 3φ ; frottement = bruit rose en passe-bande [2f ; 6f] × (0,5 + 0,5·sin φ)²,
    à −32 dB sous la note (RMS) ; variation d'amplitude ±0,6 dB à 1,5 Hz, dérive de hauteur ±2 cents à 0,2 Hz, chacune
    à phase propre ; la phase est intégrée (aucun saut)."""
    ph0_, ph1, ph2 = rng.uniform(0, 2 * np.pi, 3)
    ph0 = ph0_ if ph0 is None else ph0
    cents = 2.0 * np.sin(2 * np.pi * 0.2 * t + ph1)
    fi = f * 2 ** (cents / 1200)
    phi = ph0 + 2 * np.pi * np.concatenate([[0.0], np.cumsum(fi[:-1])]) / SR
    y = np.sin(phi) + 0.08 * np.sin(2 * phi) + 0.03 * np.sin(3 * phi)
    n = len(t)
    br = S.passe_bande(labo.bruit_rose(n + 8192, graine=graine_bruit)[4096:4096 + n], 2 * f, 6 * f, front=max(20.0, f / 4))
    br *= (0.5 + 0.5 * np.sin(phi)) ** 2
    br *= S.gain(-32.0) * np.sqrt(np.mean(y ** 2)) / (np.sqrt(np.mean(br ** 2)) + 1e-12)
    am = S.gain(0.6 * np.sin(2 * np.pi * 1.5 * t + ph2))
    return (y + br) * am


def attaque_verre(w):
    """Attaque d'archet de 180 ms à chaque entrée d'une note (le poids part de 0)."""
    w = w.copy()
    na = int(ATTAQUE_VERRE * SR)
    on = w > 1e-9
    entrees = np.nonzero(on & ~np.concatenate([[False], on[:-1]]))[0]
    for i in entrees:
        j = min(len(w), i + na)
        w[i:j] *= S.rampe_cos(na)[:j - i]
    return w


def synthese(t, poids, graine, copies=None, additif=1.0):
    """Somme stéréo des notes : une voix par note, au pan de PAN_NOTES (copies = fonction nom → ((cents, pan), …) pour
    changer) ; on ne synthétise que là où la note sonne. Graines par note et par copie : le résultat ne dépend pas du
    découpage. additif : poids de G2/D3."""
    copies = copies or (lambda nom: ((0, PAN_NOTES[nom]),))
    out = np.zeros((len(t), 2))
    for ino, (nom, f) in enumerate(NOTES.items()):
        w = poids[nom] * (additif if f < SEUIL_VERRE else 1.0)
        actif = np.nonzero(w > 0)[0]
        if not len(actif):
            continue
        a, b = actif[0], actif[-1] + 1
        tt, ww = t[a:b], w[a:b]
        if f >= SEUIL_VERRE:
            ww = attaque_verre(ww)
        cp = copies(nom)
        for ic, (cents, pan) in enumerate(cp):
            rng = np.random.default_rng([graine, ino, ic])
            fc = f * 2 ** (cents / 1200)
            if f >= SEUIL_VERRE:
                mono = voix_verre(tt, fc, rng, graine_bruit=graine * 1000 + ino * 10 + ic)
            else:
                mono = voix_additive(tt, fc, rng, np.random.default_rng([graine, ino, 98]))
            out[a:b] += S.panner(mono * ww, pan) / np.sqrt(len(cp))
    return out


def passe_bas_variable(x, t, fc):
    """Passe-bas à un pôle |H| = 1/√(1 + (f/fc)²) dont la coupure suit fc(t) : STFT (Hann, 4 096 points, pas 1 024,
    reconstruction exacte quand fc est fixe). x (n, 2), t et fc de même longueur que x."""
    Nf, H = 4096, 1024
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(Nf) / Nf)
    n = len(x)
    xp = np.vstack([np.zeros((Nf, 2)), x, np.zeros((2 * Nf, 2))])
    nb = (len(xp) - Nf) // H + 1
    f = np.fft.rfftfreq(Nf, 1 / SR)
    y = np.zeros_like(xp)
    centres = np.clip(np.arange(nb) * H + Nf // 2 - Nf, 0, n - 1)
    fcs = fc[centres]
    for c in range(2):
        fr = np.lib.stride_tricks.sliding_window_view(xp[:, c], Nf)[::H][:nb] * win
        X = np.fft.rfft(fr, axis=1)
        X *= 1.0 / np.sqrt(1 + (f[None, :] / fcs[:, None]) ** 2)
        yf = np.fft.irfft(X, Nf, axis=1) * win
        for j in range(nb):
            y[j * H:j * H + Nf, c] += yf[j]
    return y[Nf:Nf + n] / 1.5


def pedale(t):
    """Point 3 : la queue du la du décroché passe (4,60 → 6,10, puissance constante) dans une voix A4 à 440 Hz,
    partiels 1-4 en k^−1,5, doublure ±3 cents (pan ∓0,35, seconde copie à −6 dB), passe-bas un pôle à 2,5 kHz, poids 0,55 ;
    tenue jusqu'à la
    résolution, où A4 descend sur G4 (392 Hz) dans le fondu de 0,12 s centré sur la voyelle ; G4 tenu jusqu'au raccroché.
    Hors du passe-bas variable de la nappe (fermé à 700 Hz, il en ferait un sinus : la tonalité)."""
    pA = np.clip((t - T["pedale"]) / DEC["pedale_fondu"], 0, 1)
    pr = np.clip((t - (T["resolution"] - DEC["resolution_fondu"] / 2)) / DEC["resolution_fondu"], 0, 1)
    wA = np.sin(np.pi / 2 * pA) * np.cos(np.pi / 2 * pr)
    wG = np.sin(np.pi / 2 * pr)
    out = np.zeros((len(t), 2))
    for ino, (f, w) in enumerate(((440.0, wA), (392.0, wG))):
        actif = np.nonzero(w > 0)[0]
        a, b = actif[0], actif[-1] + 1
        # doublure ±3 cents, la seconde copie à −6 dB : deux copies égales et opposées passent G/D en opposition à chaque
        # battement (1,5 Hz), et la pédale s'éteint en mono ; à −6 dB le chatoiement reste, la corrélation reste positive
        for ic, (cents, pan, amp) in enumerate(((-3, -0.35, 1.0), (3, 0.35, 0.5))):
            rng = np.random.default_rng([77, ino, ic])
            fc = f * 2 ** (cents / 1200)
            mono = np.zeros(b - a)
            for k in range(1, 5):
                mono += k ** -1.5 / np.sqrt(1 + (k * fc / 2500.0) ** 2) * np.sin(2 * np.pi * fc * k * t[a:b] + rng.uniform(0, 2 * np.pi))
            out[a:b] += S.panner(mono * w[a:b] * NIV["pedale_poids"] * amp, pan) / np.sqrt(1.25)
    return out


def chorus(x, in_gain=0.6, out_gain=0.9, delais=(0.050, 0.060), decroissances=(0.4, 0.32), vitesses=(0.25, 0.4),
           profondeurs=(0.002, 0.0023)):
    """Chorus de la bible (chorus=0.6:0.9:50|60:0.4|0.32:0.25|0.4:2|2.3), en numpy avec des retards fractionnaires
    (inchangé depuis la v1 : le filtre ffmpeg à retards entiers laissait des clics)."""
    n = len(x)
    t = np.arange(n) / SR
    y = in_gain * x.copy()
    for d, dec, v, p in zip(delais, decroissances, vitesses, profondeurs):
        for c in (0, 1):
            pos = np.arange(n) - (d + p * (0.5 + 0.5 * np.sin(2 * np.pi * v * t))) * SR
            i = np.floor(pos).astype(np.int64)
            fr = pos - i
            ok = i >= 0
            i0 = np.clip(i, 0, n - 1); i1 = np.clip(i + 1, 0, n - 1)
            y[:, c] += dec * np.where(ok, x[i0, c] * (1 - fr) + x[i1, c] * fr, 0.0)
    return y * out_gain


RHO_REVERBE_NAPPE = 0.5


def reverbe_nappe(sig, secondes, graine, mix=None, predelai=0.012, rho=RHO_REVERBE_NAPPE):
    """La réverbe de labo (bruit à décroissance exponentielle, énergie unité, prédélai 12 ms), mais avec une corrélation
    G/D de ρ = 0,5 entre les deux réponses : entièrement décorrélée, la réverbe de la nappe (envoi 55 % à la résolution)
    faisait perdre 2,0 dB à la résolution en mono (mesuré sur [33,1 ; 34,0]). Renvoie le retour seul, ou le mélange
    sec·(1 − mix) + retour·mix si mix est donné."""
    sig = np.asarray(sig, dtype=np.float64)
    n = int(secondes * SR); t = np.arange(n) / SR
    g = np.random.default_rng(graine)
    b = g.standard_normal((n, 2))
    b[:, 1] = rho * b[:, 0] + np.sqrt(1 - rho ** 2) * b[:, 1]
    ir = b * np.exp(-6.9 * t / secondes)[:, None]
    ir = np.vstack([np.zeros((int(predelai * SR), 2)), ir]); ir /= np.sqrt((ir ** 2).sum(axis=0))
    L = len(sig) + len(ir) - 1; Nf = 1 << (L - 1).bit_length()
    hum = np.stack([np.fft.irfft(np.fft.rfft(sig[:, c], Nf) * np.fft.rfft(ir[:, c], Nf), Nf)[:L] for c in (0, 1)], axis=1)
    if mix is None:
        return hum
    sec = np.vstack([sig, np.zeros((L - len(sig), 2))])
    return sec * (1 - mix) + hum * mix


def excitateur(x):
    """Point 6 : la nappe en passe-bas 250 Hz (24 dB/oct), normalisée, 0,12·tanh(3x), passe-haut 300 Hz (24 dB/oct),
    rajoutée : les harmoniques 2 et 3 de G2 et D3 recréent la basse sur un haut-parleur de téléphone."""
    lp = ffmpeg_filtre(x, "lowpass=f=250,lowpass=f=250")
    m = np.max(np.abs(lp))
    ex = 0.12 * m * np.tanh(3 * lp / m)
    ex = ffmpeg_filtre(ex, "highpass=f=300,highpass=f=300")
    return x + ex


def nappe(duck):
    t_res, d_res = T["resolution"], DEC["resolution_fondu"]
    plan = [(T["sol"], 2.0, {"G2": 1, "D3": 1, "G4": 1, "B4": 1}, "cos"),
            (T["sus4"], 0.6, {"D3": 1, "A3": 1, "G4": 1, "D5": 1}, "puissance"),
            (T["re7"], 0.8, {"D3": 1, "A3": 1, "F#4": 1, "C5": 1}, "puissance"),
            (T["re9"], 2.0, {"D3": 1, "A3": 1, "F#4": 1, "C5": 1, "E4": 0.5}, "cos"),
            (t_res - d_res / 2, d_res, {"G2": 1, "D3": 1, "D4": 1, "G4": 1, "B4": 1}, "puissance")]
    i0, i1 = int(round((T["pedale"] - 0.05) * SR)), int(round(T["raccroche"] * SR)) + int(0.4 * SR)
    t = temps(i0, i1 - i0)
    dry = synthese(t, poids_notes(t, plan), graine=7, additif=POIDS_ADDITIF)
    # point 5 : passe-bas qui se tend sur le ré7, puis se relâche à la résolution
    p = np.clip((t - T["re7"]) / (t_res - T["re7"]), 0, 1)
    fc = 700.0 + 2500.0 * p ** 2
    rel = fondu_cos(t, t_res, 1.2)
    fc = np.where(t >= t_res, 3200.0 - 1000.0 * rel, fc)
    dry = passe_bas_variable(dry, t, fc)
    dry += pedale(t)
    # rampe de +3 dB linéaire en dB sur le ré7 ; à la résolution, gonflement de +3 dB (0,3 s, retour en 1,2 s) et la rampe
    # se relâche avec lui (1,2 s) : c'est le relâchement de la tension, et la voix de C4 (« Super, merci ») retrouve sa marge
    u = t - t_res
    gdb = np.where(t < t_res, 3.0 * p, 3.0 * (1 - fondu_cos(t, t_res + 0.3, 1.2)))
    gdb += np.where((u >= 0) & (u < 0.3), 3 * (0.5 - 0.5 * np.cos(np.pi * u / 0.3)), 0.0)
    v = (u >= 0.3) & (u < 1.5)
    gdb[v] += 3 * (0.5 + 0.5 * np.cos(np.pi * (u[v] - 0.3) / 1.2))
    dry *= S.gain(gdb)[:, None]
    dry = excitateur(dry)
    pad = np.zeros((int(0.2 * SR), 2))
    ch = chorus(np.vstack([dry, pad]))
    tt = temps(i0, len(ch))
    # envoi en réverbe : 35 % (le mélange de la v1), 55 % en 0,3 s à la résolution, retour en 2 s
    uu = tt - t_res
    envoi = 0.35 + 0.20 * np.where(uu < 0.3, fondu_cos(tt, t_res, 0.3), 1 - fondu_cos(tt, t_res + 0.3, 2.0))
    humide = reverbe_nappe(ch * envoi[:, None], 3.0, graine=41)      # retour seul, longueur len(ch) + queue de 3 s
    humide[:len(ch)] += 0.65 * ch                                     # direct : 0,65 comme labo.reverbe(…, 0,35)
    piste = np.zeros((N, 2))
    S.ajouter(piste, humide, i0)
    # niveau : l'accord de sol établi, seul, avant atténuation
    a, b = int(round((T["sol"] + 2.3) * SR)), int(round((T["sus4"] - 0.1) * SR))
    G0 = NIV["nappe_rms"] - rms_db(piste[a:b])
    piste *= S.gain(G0)
    pa, pb = int(round((T["pedale"] + DEC["pedale_fondu"] + 0.3) * SR)), int(round((T["sol"] - 0.05) * SR))
    info = {"rms_accord_sol": round(rms_db(piste[a:b]), 2), "rms_pedale_seule": round(rms_db(piste[pa:pb]), 2),
            "fenetre_accord_sol": [a / SR, b / SR], "fenetre_pedale": [pa / SR, pb / SR],
            "fc_debut_re7": 700.0, "fc_resolution": 3200.0, "fc_apres": 2200.0}
    for k in ("re7", "resolution"):
        j = int(round((T[k] + (-0.5 if k == "resolution" else 1.0)) * SR))
        info[f"rms_{k}"] = round(rms_db(piste[j - SR // 4:j + SR // 4]), 2)
    piste *= duck[:, None]
    noms = ("accord-sol", "re-sus4", "re7", "re9", "resolution-sol")
    sources = {"accord-sol": "dialogue.json C1.film_in − 0,30", "re-sus4": "mots A2A3[0].debut (« Laissez-moi »)",
               "re7": "mots A2A3[2].debut (« Je peux vous proposer »)", "re9": "dialogue.json A4.film_in (« Parfait »)",
               "resolution-sol": "mots.syllabes.confirmation_derniere_syllabe.voyelle − 0,06 (fondu centré)"}
    for nom, (t0, d, acc, _) in zip(noms, plan):
        cue(f"nappe-{nom}", "nappe", t0, sources[nom], f"accord {' · '.join(f'{k}×{v:g}' for k, v in acc.items())} ; fondu {d} s",
            f"RMS {NIV['nappe_rms']} dBFS (accord de sol seul), −6 dB sous la voix")
    cue("pedale-la", "nappe", T["pedale"], "point.json taille (dernière clé : le point atteint 44 px)",
        "A4 440 Hz, partiels 1-4 k^−1,5, ±3 cents, passe-bas 2,5 kHz, poids 0,55 ; fondu à puissance constante avec la queue "
        "du la du décroché sur 1,5 s", f"RMS {info['rms_pedale_seule']} dBFS seule")
    cue("pedale-sol", "nappe", t_res - d_res / 2, "voyelle de « -tion » − 0,06", "A4 → G4 392 Hz en 0,12 s, tenu jusqu'au raccroché", "")
    cue("tension-re7", "nappe", T["re7"], "mots A2A3[2].debut → voyelle de « -tion »",
        "passe-bas fc = 700 + 2 500·p² (700 → 3 200 Hz), +3 dB linéaires en dB", "")
    cue("relache", "nappe", t_res, "voyelle de « -tion »", "fc 3 200 → 2 200 Hz en 1,2 s ; envoi 35 → 55 % en 0,3 s, retour en 2 s ; "
        "gonflement +3 dB (0,3 s / 1,2 s), la rampe de +3 dB se relâche avec lui", "")
    return piste, info


# Finition du 27/09 (arbitrage 8) : la nappe de fin tient sur un haut-parleur de téléphone. En v2 (G2 · D3 · G3 · B3 · D4
# + A4 + D5), tout son poids était sous 300 Hz : −11,8 dB au haut-parleur simulé, il ne restait que le ré. Revoicée plus
# haut, en ré majeur au-dessus de 290 Hz (D4 · F#4 · A4 + D5), le ré de la signature en est la fondamentale ; le G4 de
# l'air du SMS, qui s'y fond au contact, descend sur le F#4 (la quarte suspendue qui se résout) ; D3 seul reste en
# dessous, très bas (0,35), pour le corps en pleine bande.
ACCORD_FIN = {"D3": 0.35, "D4": 1.0, "F#4": 1.0, "A4": 0.8, "D5": 0.6}


def nappe_fin():
    """Point 14 (finition) : au contact du ré, D3 × 0,35 · D4 · F#4 · A4 × 0,8 · D5 × 0,6 ; attaque 0,8 s ; passe-bas qui
    s'ouvre de 800 à 5 000 Hz en 1,4 s ; fondu cosinus de FIN_SON − 1,40 à FIN_SON, puis zéros."""
    t0 = T["re"]
    f0, f1 = FIN_SON - DEC["fin_fondu"], FIN_SON
    i0 = int(round(t0 * SR))
    t = temps(i0, int(round((FIN_SON - t0) * SR)))
    plan = [(t0, 0.8, ACCORD_FIN, "cos")]
    sec = synthese(t, poids_notes(t, plan), graine=8, additif=POIDS_ADDITIF)
    sec = passe_bas_variable(sec, t, 800.0 + 4200.0 * fondu_cos(t, t0, 1.4))
    sec = excitateur(sec)
    ch = chorus(np.vstack([sec, np.zeros((int(0.2 * SR), 2))]))
    humide = reverbe_nappe(ch, 3.0, graine=42, mix=0.35)
    piste = np.zeros((N, 2))
    S.ajouter(piste, humide, i0)
    tt = np.arange(N) / SR
    piste *= (1 - fondu_cos(tt, f0, f1 - f0))[:, None]       # fondu de sortie en cosinus, après la réverbe
    piste[tt >= f1] = 0
    a, b = int(round((t0 + 1.0) * SR)), int(round(f0 * SR))
    piste *= S.gain(NIV["nappe_fin_rms"] - rms_db(piste[a:b]))
    cue("nappe-fin", "nappe", t0, "evenements.signature_re_contact", "D3×0,35×0,6 · D4 · F#4 · A4×0,8 · D5×0,6 (ré majeur au-dessus de 290 Hz), attaque 0,8 s, "
        f"passe-bas 800 → 5 000 Hz en 1,4 s ; fondu cosinus {f0:.2f} → {f1:.2f}", f"RMS {NIV['nappe_fin_rms']} dBFS")
    return piste


def air_sms():
    """Point 11 : G4 + D5 en verre (poids 1 et 0,6), fondu d'entrée de 0,8 s, passe-bas 4 kHz, réverbe 3 s à 40 % ;
    −4 dB sous la signature dès 40,55 ; fondu enchaîné de 0,8 s dans la nappe de fin au contact."""
    t0 = T["air_sms"]
    t_bas = T["la"] - DEC["air_sms_avant_la"]
    i0 = int(round(t0 * SR))
    fin = T["re"] + 0.8
    t = temps(i0, int(round((fin - t0) * SR)))
    poids = {k: np.zeros_like(t) for k in NOTES}
    ent = fondu_cos(t, t0, 0.8)
    poids["G4"], poids["D5"] = 1.0 * ent, 0.6 * ent
    # G4 un peu à gauche, D5 un peu à droite (plus serrés que dans la nappe) ; la largeur vient de la réverbe
    une = lambda nom: ((0, -0.15),) if nom == "G4" else ((0, 0.15),)  # noqa: E731
    sec = np.vstack([synthese(t, poids, graine=9, copies=une), np.zeros((int(0.1 * SR), 2))])
    X = np.fft.rfft(sec, axis=0); f = np.fft.rfftfreq(len(sec), 1 / SR)
    sec = np.fft.irfft(X / np.sqrt(1 + (f / 4000.0) ** 2)[:, None], len(sec), axis=0)
    hum = reverbe_nappe(np.vstack([sec, np.zeros((int(0.1 * SR), 2))]), 3.0, graine=43, mix=0.40)
    piste = np.zeros((N, 2))
    S.ajouter(piste, hum, i0)
    a, b = int(round((t0 + 1.0) * SR)), int(round((t_bas - 0.1) * SR))
    piste *= S.gain(NIV["air_sms_rms"] - rms_db(piste[a:b]))
    tt = np.arange(N) / SR
    g = S.gain(-4.0 * fondu_cos(tt, t_bas, 0.10)) * (1 - fondu_cos(tt, T["re"], 0.8))
    piste *= g[:, None]
    piste[tt >= fin] = 0
    cue("air-sms", "nappe", t0, "evenements.bulle_et_vibreur + 0,053 s", "G4 + D5×0,6 en verre, fondu 0,8 s, passe-bas 4 kHz, "
        "réverbe 3 s à 40 % ; −4 dB dès signature_la − 0,05 ; sortie en fondu enchaîné de 0,8 s au contact du ré",
        f"RMS {NIV['air_sms_rms']} dBFS", fin=fin)
    return piste


# ── 4. SFX et timbres du point ──────────────────────────────────────────────
def clic(duree=0.030, f_sourd=180.0, d_sourd=0.025, graine=51):
    """Clic de prise de ligne : 2 ms de bruit blanc en Hann → passe-bas à un pôle à 3 kHz ; + 180 Hz sous une
    fenêtre demi-sinus de 25 ms, 2 dB plus bas (v1)."""
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
    """Le raccroché, 80 ms : la même matière que le décroché, transitoire à l'instant exact, sourd de 30 ms à 120 Hz."""
    y = clic(duree=0.080, f_sourd=120.0, d_sourd=0.030, graine=52)
    k = int(0.010 * SR)
    y[-k:] *= S.rampe_cos(k)[::-1]
    return y


def vibreur(t, env):
    """Point 10 : moteur accordé en ré3 146,83 Hz, dent de scie à bande limitée (1/k, ≤ 6 kHz) → passe-bas un pôle
    1 kHz (module et phase par harmonique), + 293,66 Hz à 30 %, modulation (1 + 0,3·sin 2π·32t), grésillement de boîtier
    (bruit blanc 1,5-4 kHz, 0,25 × RMS moteur). Harmoniques 3 et 4 : 440,5 et 587,3 Hz, le la et le ré de la signature."""
    f0, fc = 146.83, 1000.0
    m = np.zeros(len(t))
    for k in range(1, int(6000 / f0) + 1):
        fk = f0 * k
        m += -(2 / np.pi) / k / np.sqrt(1 + (fk / fc) ** 2) * np.sin(2 * np.pi * fk * t - np.arctan(fk / fc))
    m /= np.max(np.abs(m))
    m += 0.3 * np.sin(2 * np.pi * 293.66 * t)
    m *= 1 + 0.3 * np.sin(2 * np.pi * 32.0 * t)
    m *= env
    g = np.random.default_rng(61)
    br = S.passe_bande(g.standard_normal(len(t)), 1500, 4000, front=200)
    br /= np.sqrt(np.mean(br ** 2))
    br *= 0.25 * np.sqrt(np.mean(m[env > 0.99] ** 2)) * env
    return m + br


def tonalite_tel(t0, n):
    """La tonalité française DANS la ligne : 440 Hz, tanh(1,3·x)/tanh(1,3), bande téléphone 300-3 400 Hz, crête 1,
    phase absolue 2π·440·t (la même qu'au décroché)."""
    y, _ = S.ligne_qui_s_ouvre(n, i0=n + 1, phi0=2 * np.pi * 440.0 * t0)
    return y


def avant_la_coupe(sfx, sig):
    """Tout ce qui sonne AVANT le raccroché (la coupe de 5 ms le borne) : sonnerie, décroché, touchers, écriture."""
    s1 = SEC["s1"]
    (a0, a1), (b0, b1) = s1["segments_s"]
    ra, rb = s1["rampes_s"]
    t_dec = T["decroche"]
    assert abs(b1 - t_dec) < 1e-9, "la 2e tonalité doit s'ouvrir au décroché"
    # 4.1 tonalité n° 1 (0 → 1,5 s), dans la ligne, mono au centre
    i0, i1 = int(round(a0 * SR)), int(round(a1 * SR))
    t = temps(i0, i1 - i0)
    ton1 = tonalite_tel(a0, i1 - i0) * trapeze(t, [(a0, a1)], [ra], forme="cos") * S.gain(NIV["ton"])
    sfx[i0:i1] += ton1[:, None]
    cue("ton-1", "sfx", a0, "secousses.s1.segments_s[0]", "440 Hz, tanh(1,3x)/tanh(1,3), bande 300-3 400 Hz, fondus 10 ms "
        "en cosinus (même moyenne par image que secousses.s1)", f"{NIV['ton']} dBFS crête", pan=0.0, fin=a1)
    # 4.2 le souffle de la ligne : bruit rose 300-3 400 Hz, gardé dans le blanc, coupé en 2 ms au décroché
    n = int(round(t_dec * SR))
    br = S.passe_bande(labo.bruit_rose(n, graine=3), 300, 3400, front=50)
    br *= S.gain(NIV["ligne_rms"] - rms_db(br))
    k = int(0.002 * SR); br[-k:] *= S.rampe_cos(k)[::-1]
    k = int(0.005 * SR); br[:k] *= S.rampe_cos(k)
    sfx[:n] += br[:, None]
    cue("souffle-ligne", "sfx", 0.0, "0 → evenements.decroche", "bruit rose graine 3, passe-bande 300-3 400 Hz, coupe 2 ms",
        f"RMS {NIV['ligne_rms']} dBFS", pan=0.0, fin=t_dec)
    # 4.3 tonalité n° 2 → la ligne qui s'ouvre (point 2), même oscillateur, puis fondu dans la pédale (point 3)
    i0 = int(round(b0 * SR))
    t_fin = T["pedale"] + DEC["pedale_fondu"]
    n = int(round((t_fin - b0) * SR))
    t = temps(i0, n)
    i_dec = int(round(t_dec * SR)) - i0
    y, w = S.ligne_qui_s_ouvre(n, i0=i_dec, phi0=2 * np.pi * 440.0 * b0, tau=0.45)
    env = np.where(t < t_dec, trapeze(t, [(b0, t_dec + 10)], [(rb[0], 0)], forme="cos"), 1.0)
    env *= np.cos(np.pi / 2 * np.clip((t - T["pedale"]) / DEC["pedale_fondu"], 0, 1))
    y = y * env * S.gain(NIV["ton"])
    st = S.panner(y, pan_point(t) * w)                       # au centre dans la ligne, au point une fois ouvert
    S.ajouter(sig, st, i0)
    envoi = np.clip((t - t_dec) / 0.020, 0, 1)
    queue = st * (0.5 - 0.5 * np.cos(np.pi * envoi))[:, None]
    S.ajouter(sig, 0.12 * S.humide(queue, 1.2, graine=32), i0)
    cue("ton-2-la", "signature", b0, "secousses.s1.segments_s[1] ; ouverture = evenements.decroche ; fondu = pédale",
        "même oscillateur 440 Hz ; la ligne qui s'ouvre (signature.ligne_qui_s_ouvre) : 0-90 ms bande téléphone, 90-250 ms "
        "fondu vers la cloche FM 1:1 (I 1,4) + étincelle 1:3,5 ; amplitude exp(−τ/0,45) ; fondu à puissance constante "
        f"vers la pédale {T['pedale']:.2f} → {t_fin:.2f} ; réverbe 1,2 s à 12 % sur la queue",
        f"{NIV['ton']} dBFS crête", pan=f"0 dans la ligne, puis le point ({pan_point(t_dec + 0.25):+.3f} ouvert)", ouverture=t_dec)
    # 4.4 clic de décroché
    poser_mobile(sfx, clic(), t_dec, NIV["clic"])
    cue("clic-decroche", "sfx", t_dec, "evenements.decroche", "bruit 2 ms Hann → passe-bas 3 kHz + 180 Hz / 25 ms",
        f"{NIV['clic']} dBFS crête", pan=round(float(pan_point(t_dec)), 3))
    # 4.5 sol du décroché : même écart que la signature (sol − la)
    d_sol = T["sol_sig"] - T["la"]
    d_re = T["re"] - T["la"]
    assert abs(d_sol - 0.24) < 1e-6 and abs(d_re - 0.60) < 1e-6, (d_sol, d_re)
    t_sol1 = t_dec + d_sol
    poser_mobile(sig, S.note_sol(1.6, tau=0.5), t_sol1, NIV["sol_decroche"], rev=(1.2, 0.15), graine=33)
    cue("cloche-sol-1", "signature", t_sol1, "evenements.decroche + (signature_sol − signature_la)",
        "sol4 392 Hz FM 1:1, indice 1,2·exp(−τ/0,25), amplitude exp(−τ/0,5), attaque 5 ms, réverbe 1,2 s à 15 %",
        f"{NIV['sol_decroche']} dBFS crête", pan=f"suit le point ({pan_point(t_sol1):+.3f} à l'attaque)")
    # 4.6 les touchers du point sur les heures : verre en ré6, hors de la bande de la voix (point 7)
    for i, (nom, niv, lib) in enumerate((("contact_neuf", NIV["tap"], "tap-9h"), ("contact_dix", NIV["tap"], "tap-10h"),
                                         ("contact_onze", NIV["tap"], "tap-11h"),
                                         ("contact_retour_neuf", NIV["tap_retour"], "tap-retour-9h"))):
        tc = EV[nom]["t"]
        poser_mobile(sfx, S.re_court(graine=5 + i, clair=True), tc, niv, rev=(0.8, 0.12), graine=34 + i)
        cue(lib, "sfx", tc, f"evenements.{nom}", "ré6 1 174,66 Hz (τ 0,07) + ×2,756 (a 1,2, τ 0,070) + ×5,404 (a 1,0, τ 0,050) + grain "
            "de verre 5-9 kHz (τ 30 ms), contact 3 ms 5-11 kHz à −6 dB, passe-haut 900 Hz 2e ordre, réverbe 0,8 s à 12 % (G/D décorrélés)",
            f"{niv} dBFS crête",
            pan=round(float(pan_point(tc)), 3))
    # 4.7 le la · sol de l'écriture du rendez-vous (point 8) : la ligne qui s'ouvre, puis le sol ; ils suivent la plume
    t_ecr = EV["ecriture_debut"]["t"]
    la, w_la = S.note_la(1.2, tau=0.35)
    poser_mobile(sig, la, t_ecr, NIV["la_rdv"], rev=(1.2, 0.15), graine=35, poids_pan=w_la)
    cue("cloche-la-rdv", "signature", t_ecr, "evenements.ecriture_debut", "la4 440 Hz, la ligne qui s'ouvre (0-90 ms bande "
        "téléphone, 90-250 ms vers la cloche FM 1:1 + étincelle), τ 0,35 s, attaque 8 ms, réverbe 1,2 s à 15 %",
        f"{NIV['la_rdv']} dBFS crête", pan=f"centre dans la ligne, puis la plume {pan_point(t_ecr + 0.25):+.3f} → "
        f"{pan_point(EV['ecriture_fin']['t']):+.3f}")
    poser_mobile(sig, S.note_sol(1.4, tau=0.45), t_ecr + d_sol, NIV["sol_rdv"], rev=(1.2, 0.15), graine=36)
    cue("cloche-sol-rdv", "signature", t_ecr + d_sol, "evenements.ecriture_debut + (signature_sol − signature_la)",
        "sol4 392 Hz FM 1:1, τ 0,45 s", f"{NIV['sol_rdv']} dBFS crête", pan=f"suit la plume ({pan_point(t_ecr + d_sol):+.3f})")
    return sfx, sig


def apres_la_coupe(sfx, sig, nap):
    """Tout ce qui sonne APRÈS le silence numérique : vibreur, air du SMS, stylo, signature, nappe de fin."""
    # 4.8 vibreur : l'enveloppe EST secousses.s6 (mêmes segments, mêmes rampes linéaires que l'image)
    s6 = SEC["s6"]
    v0, v1 = s6["segments_s"][0][0], s6["segments_s"][-1][1]
    assert round(v0 * 30) == EV["bulle_et_vibreur"]["image"] == s6["image0"]
    i0 = int(round(v0 * SR)); n = int(round((v1 - v0 + 0.01) * SR))
    t = temps(i0, n)
    env = trapeze(t, s6["segments_s"], s6["rampes_s"])
    vb = vibreur(t, env)
    vb = vb / np.max(np.abs(vb)) * S.gain(NIV["vibreur"])
    sfx[i0:i0 + n] += vb[:, None]
    cue("vibreur", "sfx", v0, "secousses.s6.segments_s (= evenements.bulle_et_vibreur, image 1100)",
        "moteur ré3 146,83 Hz, dent de scie à bande limitée → passe-bas 1 kHz + 293,66 Hz à 30 %, AM 32 Hz, grésillement "
        "1,5-4 kHz ; enveloppe trapèze 12/25 ms identique à secousses.s6", f"{NIV['vibreur']} dBFS crête", pan=0.0,
        segments=s6["segments_s"])
    # 4.9 l'air du SMS (nappe)
    nap += air_sms()
    # 4.10 le frottement du stylo pendant que le point écrit le mot (point 12)
    p0, p1 = EV["plume_mot"]["t"]
    i0 = int(round(p0 * SR)); n = int(round((p1 - p0) * SR))
    t = temps(i0, n)
    br = S.passe_bande(labo.bruit_rose(n + 8192, graine=71)[4096:4096 + n], 3000, 8000, front=300)
    br /= np.sqrt(np.mean(br ** 2))
    vit = v_point(t)
    y = br * vit / vit.max()
    k = int(0.005 * SR)
    y[:k] *= S.rampe_cos(k); y[-k:] *= S.rampe_cos(k)[::-1]
    y = y / np.max(np.abs(y))
    poser_mobile(sfx, y, p0, NIV["stylo"])
    cue("stylo", "sfx", p0, "evenements.plume_mot", "bruit rose graine 71, passe-bande 3-8 kHz, amplitude ∝ vitesse du point "
        f"(point-resolu, max {vit.max():.1f} px/image), fondus 5 ms", f"{NIV['stylo']} dBFS crête",
        pan=f"suit le point {pan_point(p0):+.3f} → {pan_point(p1):+.3f}", fin=p1)
    # 4.11 la signature : le motif de signature.py (le même rendu que les livrables seuls), aux pans du point
    o = NIV["signature_decalage_db"]
    motif = S.signature("longue") * S.gain(o)
    S.ajouter(sig, motif, int(round(T["la"] * SR)))
    for nom, clef, niv, tc in (("signature-la", "signature_la", -16 + o, T["la"]), ("signature-sol", "signature_sol", -17 + o, T["sol_sig"]),
                               ("signature-re", "signature_re_contact", -15 + o, T["re"])):
        cue(nom, "signature", tc, f"evenements.{clef}", "son/signature.py (le même rendu que les livrables seuls) ; ré : air 6-12 kHz, "
            "scintillement 2 349,3 / 2 350,0 Hz, corps ré3 saturé ; réverbe 2,2 s à 22 %, Haas 18 ms, largeur en quadrature",
            f"{niv} dBFS crête", pan=round(float(pan_point(tc + (0.25 if nom == 'signature-la' else 0.0))), 3))
    # 4.12 la nappe de fin
    nap += nappe_fin()
    return sfx, sig, nap


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


def masteriser(somme, G=None):
    """Un gain unique (−14 LUFS) puis le limiteur à crête vraie. G imposé : on garde le gain du master (A/B)."""
    iteratif = G is None
    if iteratif:
        G = LUFS_CIBLE - loudnorm_mesure(somme)["I"]
    for it in range(6):
        x = somme * S.gain(G)
        g_lim, red = gain_limiteur(x)
        y = x * g_lim[:, None]
        m = loudnorm_mesure(y)
        print(f"   passe {it}: gain {G:+.2f} dB, réduction max {red:.2f} dB → {m['I']:.2f} LUFS, {m['TP']:.2f} dBTP")
        if not iteratif or abs(m["I"] - LUFS_CIBLE) <= 0.04:
            break
        G += LUFS_CIBLE - m["I"]
    return y, G, g_lim, red


# ── 6. VARIANTE « MONDE » (point 16) : deux bruitages ElevenLabs en s1, hors du master ──
MONDE_SONS = {
    "aboiement": {"texte": "a single muffled dog bark heard through a closed door in a small veterinary clinic, distant, "
                           "one bark only, no voices, no music", "duree": 1.0, "influence": 0.7, "t": 0.55, "pan": -0.30},
    "loquet": {"texte": "a metal kennel cage latch closing once, small room, distant, no voices, no music",
               "duree": 0.8, "influence": 0.7, "t": 2.25, "pan": 0.25},
}


def prise_elevenlabs(texte, duree, influence, k):
    """Prise n° k d'un bruitage ElevenLabs (labo : clé pub, cache par requête + numéro de prise)."""
    corps = {"text": texte, "prompt_influence": influence, "duration_seconds": float(duree)}
    h = hashlib.sha256(json.dumps(["sfx-prise", corps, k], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:14]
    base = labo.CACHE / f"sfx-prise{k}-{h}"
    wav = base.with_suffix(".wav")
    if not wav.exists():
        mp3 = base.with_suffix(".mp3")
        mp3.write_bytes(labo._post("/v1/sound-generation", corps))
        labo._vers_wav(mp3, wav)
        base.with_suffix(".json").write_text(json.dumps({"prise": k, **corps}, ensure_ascii=False, indent=1))
    return wav


def evaluer_prise(x):
    """Une prise utilisable : un début qui n'est pas tronqué (la prise ne démarre pas déjà forte), un seul événement
    (bouffées à moins de 15 dB de la crête, fusionnées à 30 ms près), puis la crête la plus haute (meilleur rapport au
    bruit de la prise). Attaque = premier instant à moins de 20 dB de la crête (enveloppe RMS 10 ms)."""
    m = x.mean(axis=1)
    e = 10 * np.log10(np.convolve(m ** 2, np.ones(480) / 480, mode="same") + 1e-14)
    em = e.max()
    haut = e > em - 15
    debuts = np.nonzero(haut & ~np.concatenate([[False], haut[:-1]]))[0]
    fins = np.nonzero(haut & ~np.concatenate([haut[1:], [False]]))[0]
    bouffees = 0
    derniere = -10 ** 9
    for d, f in zip(debuts, fins):
        if d - derniere > int(0.030 * SR):
            bouffees += 1
        derniere = f
    i_att = int(np.nonzero(e > em - 20)[0][0])
    tronquee = bool(np.max(e[:int(0.005 * SR)]) > em - 20)
    # fond : niveau médian de la prise hors de l'événement (à plus de 0,3 s de la dernière bouffée), relatif à la crête
    reste = e[min(len(e) - 1, fins[-1] + int(0.3 * SR)):]
    fond = float(np.median(reste) - em) if len(reste) > int(0.05 * SR) else 0.0
    return {"bouffees": bouffees, "tronquee": tronquee, "fond_db_sous_crete": round(fond, 1), "crete_db": round(float(em), 1),
            "attaque_s": round(i_att / SR, 4)}


def monde(G):
    """Construit le stem « monde » AVANT master (sonie réglée sur l'échelle finale, gain G), choisit la meilleure des
    4 prises de chaque bruitage."""
    MONDE.mkdir(exist_ok=True)
    piste = np.zeros((N, 2))
    choix = {}
    for nom, P in MONDE_SONS.items():
        notes = []
        for k in range(4):
            wav = prise_elevenlabs(P["texte"], P["duree"], P["influence"], k)
            x = labo.lire(wav)
            shutil.copyfile(wav, MONDE / f"{nom}-prise{k + 1}.wav")
            notes.append({"prise": k + 1, "fichier": str(MONDE / f"{nom}-prise{k + 1}.wav"), **evaluer_prise(x)})
        # pas de début tronqué, une seule bouffée, puis le fond le plus bas (un événement sur du silence ; vérifié sur la
        # planche des 8 prises : l'aboiement 3 traîne un sifflement tenu, l'aboiement 4 aboie deux fois)
        best = sorted(notes, key=lambda d: (d["tronquee"], d["bouffees"], d["fond_db_sous_crete"]))[0]
        x = labo.lire(MONDE / f"{nom}-prise{best['prise']}.wav")
        x = ffmpeg_filtre(x, "highpass=f=200,lowpass=f=6000,equalizer=f=440:t=q:w=8:g=-12")
        x = labo.reverbe(x, 0.5, 0.25, graine=81)
        i_att = int(round(best["attaque_s"] * SR))
        i0 = int(round(P["t"] * SR)) - i_att
        mono = x.mean(axis=1)
        st = S.panner(mono, P["pan"])
        # sonie instantanée maximale (400 ms) ≤ −28 LUFS dans le mix final
        z = np.zeros((N, 2)); S.ajouter(z, st, i0)
        mmax = sonie_instantanee_max(z * S.gain(G))
        z *= S.gain(NIV["monde_momentane_lufs"] - mmax)
        piste += z
        choix[nom] = {"prises": notes, "retenue": best["prise"], "placee_a": P["t"], "pan": P["pan"],
                      "gain_db": round(float(NIV["monde_momentane_lufs"] - mmax), 2)}
    # coupe de 10 ms au décroché : rien du monde ne survit à la voix de l'agente
    i = int(round(T["decroche"] * SR)); k = int(0.010 * SR)
    piste[i:i + k] *= S.rampe_cos(k)[::-1, None]
    piste[i + k:] = 0
    return piste, choix


def ponderer_k(x):
    """Pondération K (BS.1770) en fréquence (module)."""
    def h(b, a, w):
        z = np.exp(-1j * w)
        return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)
    n = len(x)
    Nf = 1 << (n - 1).bit_length()
    w = 2 * np.pi * np.fft.rfftfreq(Nf, 1 / SR) / SR
    H = h([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], w) * \
        h([1, -2, 1], [1, -1.99004745483398, 0.99007225036621], w)
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c], Nf) * np.abs(H), Nf)[:n] for c in range(x.shape[1])], axis=1)


def sonie_instantanee_max(x, fen=0.4):
    xk = ponderer_k(x)
    p = np.sum(xk ** 2, axis=1)
    w = int(fen * SR)
    c = np.concatenate([[0.0], np.cumsum(p)])
    m = (c[w:] - c[:-w]) / w
    return float(-0.691 + 10 * np.log10(m.max() + 1e-20))


def main(avec_monde=False):
    STEMS.mkdir(exist_ok=True)
    print("1. dialogue")
    dlg, rap_voix = dialogue()
    for r in rap_voix:
        print(f"   {r['id']:5s} {r['lufs_origine']:7.2f} → {r['lufs_final']:7.2f} LUFS")
    print("2. ducking + nappe")
    duck = gain_ducking(dlg[:, 0])
    nap, info_nappe = nappe(duck)
    print(f"   {info_nappe}")
    print("3. sfx + signature (avant la coupe)")
    sfx, sig = np.zeros((N, 2)), np.zeros((N, 2))
    sfx, sig = avant_la_coupe(sfx, sig)
    # le raccroché (point 9) : au même échantillon, toutes les pistes coupées en 5 ms, DÉFINITIVEMENT ; puis zéros exacts
    t_rac = T["raccroche"]
    s0, s1_ = EV["silence_numerique"]["t"]
    i_rac, i_s0, i_s1 = int(round(t_rac * SR)), int(round(s0 * SR)), int(round(s1_ * SR))
    coupe = np.ones(N)
    k = int(0.005 * SR)
    coupe[i_rac:i_rac + k] = S.rampe_cos(k)[::-1]
    coupe[i_rac + k:] = 0
    for st in (dlg, nap, sfx, sig):
        st *= coupe[:, None]
    rac = raccroche() * S.gain(NIV["raccroche"])
    assert i_rac + len(rac) <= i_s0, "le raccroché doit finir avant le silence numérique"
    sfx[i_rac:i_rac + len(rac)] += rac[:, None]
    cue("raccroche", "sfx", t_rac, "evenements.raccroche", "même matière que le clic de décroché : transitoire 2 ms → passe-bas "
        "3 kHz + 120 Hz / 30 ms ; toutes les pistes coupées en 5 ms au même échantillon", f"{NIV['raccroche']} dBFS crête", pan=0.0)
    print("4. après le silence : vibreur, air du SMS, stylo, signature, nappe de fin")
    sfx, sig, nap = apres_la_coupe(sfx, sig, nap)
    for st in (dlg, nap, sfx, sig):
        assert not np.any(st[i_s0:i_s1]), "silence numérique non nul"
    cue("silence-numerique", "tous", s0, "evenements.silence_numerique", "zéros numériques sur toutes les pistes",
        "exactement 0", fin=s1_)
    fin = int(round(FIN_SON * SR))
    for st in (dlg, nap, sfx, sig):
        st[fin:] = 0
    cue("silence-final", "tous", FIN_SON, "evenements.silence_final", "zéros numériques jusqu'à la fin", "exactement 0", fin=DUREE)
    stems = {"dialogue": dlg, "nappe": nap, "sfx": sfx, "signature": sig}
    somme = dlg + nap + sfx + sig
    print("5. master")
    mix, G, g_lim, red = masteriser(somme)
    for nom, st in stems.items():
        S.ecrire24(STEMS / f"{nom}.wav", st * S.gain(G) * g_lim[:, None])
    S.ecrire24(ICI / "mix.wav", mix)
    shutil.copyfile(ICI / "mix.wav", PROJET / "assets" / "son" / "mix.wav")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ICI / "mix.wav", UPLOADS / "point-solaire-bande-son-v2.wav")
    finals = {nom: st * S.gain(G) * g_lim[:, None] for nom, st in stems.items()}
    for c in CUES:
        niv = c["niveau_avant_master"]
        if c["stem"] in ("sfx", "signature") and niv.endswith("dBFS crête"):
            i = c["echantillon"]
            seg = finals[c["stem"]][max(0, i - int(0.005 * SR)):i + int(0.1 * SR)]
            c["crete_stem_100ms_dbfs"] = round(float(S.db(np.max(np.abs(seg)))), 1)
        elif c["stem"] == "dialogue":
            i, j = c["echantillon"], int(round(c["fin"] * SR))
            c["crete_finale_dbfs"] = round(float(S.db(np.max(np.abs(finals["dialogue"][i:j])))), 1)
            c["lufs_final"] = round(float(niv.split()[0]) + G, 2)
    red_db = -20 * np.log10(g_lim)
    actif = {"part_du_temps_reduction_sup_0.5_db": round(float(np.mean(red_db > 0.5)), 4),
             "part_du_temps_reduction_sup_1_db": round(float(np.mean(red_db > 1.0)), 4),
             "part_du_temps_reduction_sup_2_db": round(float(np.mean(red_db > 2.0)), 5)}
    print(f"   limiteur : {actif}")
    rapport = {"version": "v2", "gain_master_db": round(G, 3), "reduction_limiteur_max_db": round(red, 2),
               "plafond_dbtp": PLAFOND_DBTP, "limiteur_activite": actif, "instants": {k: round(v, 6) for k, v in T.items()},
               "decalages_nommes": DEC, "voix": rap_voix, "nappe": info_nappe, "niveaux_avant_master": NIV,
               "cues": sorted(CUES, key=lambda c: c["t"])}
    if avec_monde:
        print("6. variante « monde » (hors master)")
        mo, choix = monde(G)
        y = (somme + mo) * S.gain(G)                    # même gain de master : l'A/B ne diffère que des bruitages
        g2, red2 = gain_limiteur(y)
        mixm = y * g2[:, None]
        S.ecrire24(STEMS / "monde.wav", mo * S.gain(G) * g2[:, None])
        S.ecrire24(ICI / "mix-monde.wav", mixm)
        shutil.copyfile(ICI / "mix-monde.wav", UPLOADS / "point-solaire-bande-son-monde-v2.wav")
        rapport["monde"] = {"choix": choix, "reduction_limiteur_max_db": round(red2, 2), "mesure": labo.mesurer(ICI / "mix-monde.wav"),
                            "fichier": str(ICI / "mix-monde.wav")}
        print(f"   {json.dumps(rapport['monde'], ensure_ascii=False)[:600]}")
    (ICI / "cues.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=float))
    print(f"   mix : {ICI / 'mix.wav'}  ({labo.mesurer(ICI / 'mix.wav')})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--monde", action="store_true", help="fabrique aussi la variante « monde » (fichier séparé)")
    main(avec_monde=ap.parse_args().monde)
