#!/usr/bin/env python3
"""Signature sonore Vokio « la · sol · ré », v2 (critique.json plan.chantiers « son », points 2, 7 et 13), et les
timbres du point.

    python3 son/signature.py      écrit les deux livrables seuls :
        /root/vokio-uploads/videos/showcase/point-solaire-signature-v2.wav          (0,05 s + 3,2 s)
        /root/vokio-uploads/videos/showcase/point-solaire-signature-courte-v2.wav   (0,9 s)
      48 kHz, 24 bits, stéréo, crête vraie −1 dBTP (suréchantillonnage ×4). Les pans sont ceux du film (le point
      à chaque instant), donc le livrable seul est EXACTEMENT le motif du film.

    import signature as S       (depuis son/mix.py)
        S.ligne_qui_s_ouvre(...)   la « ligne qui s'ouvre » (décroché, écriture, signature) : mono + poids d'ouverture
        S.note_la(...), S.note_sol(...), S.note_re(...), S.couches_re(...), S.re_court(...)
        S.signature(variante, pan_fn)   → (n, 2), le motif complet avec son espace

Geste v2 : le la NAÎT dans la ligne (tonalité tanh 1,3 en bande téléphone 300-3 400 Hz pendant 90 ms), puis s'ouvre
en pleine bande de 90 à 250 ms (cloche FM 1:1 d'indice 1,4 + étincelle FM 1:3,5 qui n'existe que dans la voie
pleine bande). Le ré reçoit de l'air (6-12 kHz, un bruit par canal), un scintillement (2 349,3 / 2 350,0 Hz) et un
corps (ré3 saturé, passe-haut 100 Hz). Réverbe de queue 2,2 s à 22 %, graines séparées, Haas de 18 ms.

Tout est calculé en numpy à 48 kHz, déterministe (graines fixes) : aucune banque de sons, aucun droit.
Les filtres causaux (passe-haut du toucher et du corps) passent par ffmpeg en tuyau (float 32).
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
sys.path.insert(0, str(ICI))
import labo  # noqa: E402

SR = labo.SR
SORTIES = Path("/root/vokio-uploads/videos/showcase")

F_LA, F_SOL, F_RE = 440.0, 392.0, 587.33
F_RE6, F_RE3 = 1174.66, 146.83


# ── outils ──────────────────────────────────────────────────────────────────
def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def gain(db_):
    return 10 ** (np.asarray(db_, dtype=np.float64) / 20)


def rampe_cos(n):
    """Montée en cosinus surélevé de n échantillons (0 → 1)."""
    if n <= 0:
        return np.ones(0)
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)


def phase(freq, n):
    """Phase intégrée : freq scalaire ou tableau de n valeurs (Hz)."""
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    return 2 * np.pi * np.concatenate([[0.0], np.cumsum(f[:-1])]) / SR


def couleur_ligne(s, k):
    """Mise en forme de la tonalité française : tanh(k·s)/tanh(k), k → 0 = sinus pur."""
    k = np.maximum(np.asarray(k, dtype=np.float64), 1e-6)
    return np.tanh(k * s) / np.tanh(k)


def passe_bande(x, f1, f2, front=50.0):
    """Passe-bande par masque FFT (phase nulle), fronts en cosinus de `front` Hz."""
    n = len(x)
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.zeros_like(f)
    m[(f >= f1) & (f <= f2)] = 1
    b = (f > f1 - front) & (f < f1)
    m[b] = 0.5 - 0.5 * np.cos(np.pi * (f[b] - (f1 - front)) / front)
    b = (f > f2) & (f < f2 + front)
    m[b] = 0.5 + 0.5 * np.cos(np.pi * (f[b] - f2) / front)
    if X.ndim > 1:
        m = m[:, None]
    return np.fft.irfft(X * m, n, axis=0)


def ffmpeg_filtre(sig, filtre):
    """Filtre ffmpeg en tuyau (float 32 → float 64, aucune quantification) ; mono (n,) ou (n, c)."""
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


def maillet(duree, f1, f2, graine):
    """Transitoire : bruit blanc en passe-bande, fenêtré en Hann, crête 1."""
    g = np.random.default_rng(graine)
    n = int(round(duree * SR))
    b = passe_bande(g.standard_normal(4096), f1, f2, front=400.0)[1024:1024 + n]
    b = b * np.hanning(n + 2)[1:-1]
    return b / np.max(np.abs(b))


def crete(x, cible_db):
    return x / np.max(np.abs(x)) * gain(cible_db)


def finir(y, part=0.25, maxi=0.30):
    """Fondu de sortie en cosinus sur la fin du tampon : une note n'est jamais tronquée (sinon clic large bande)."""
    k = int(min(maxi * SR, part * len(y)))
    y[-k:] *= rampe_cos(k)[::-1] if y.ndim == 1 else rampe_cos(k)[::-1, None]
    return y


def panner(x, pan):
    """Mono → (n, 2), loi à puissance constante de labo.placer (centre = 1, 1). pan scalaire ou tableau."""
    a = (np.asarray(pan, dtype=np.float64) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1) * np.sqrt(2)


def humide(sig, secondes, graine=1, predelai=0.012):
    """Retour de réverbe SEUL (labo.reverbe avec mix = 1) : le direct n'est jamais atténué. Réponse stéréo à deux
    bruits indépendants (graine unique, un tirage par canal) : les retours gauche et droit sont décorrélés."""
    return labo.reverbe(sig, secondes, 1.0, graine=graine, predelai=predelai)


def ajouter(piste, sig, i):
    """Additionne sig (n, 2) dans piste à l'échantillon i (coupé aux deux bords)."""
    if i < 0:
        sig, i = sig[-i:], 0
    j = min(len(piste), i + len(sig))
    if j > i:
        piste[i:j] += sig[:j - i]
    return piste


def crete_vraie(sig, facteur=4):
    """Crête vraie (dBTP) par suréchantillonnage FFT ×facteur, canal par canal."""
    sig = np.atleast_2d(np.asarray(sig).T).T
    n = len(sig)
    N = 1 << (n - 1).bit_length()
    pic = 0.0
    for c in range(sig.shape[1]):
        X = np.fft.rfft(sig[:, c], N)
        y = np.fft.irfft(X, N * facteur) * facteur
        pic = max(pic, float(np.max(np.abs(y[:n * facteur]))))
    return 20 * np.log10(max(pic, 1e-12))


def ecrire24(chemin, sig):
    """WAV PCM 24 bits stéréo 48 kHz (labo.ecrire n'écrit que 16 bits)."""
    sig = np.asarray(sig, dtype=np.float64)
    if sig.ndim == 1:
        sig = np.stack([sig, sig], axis=1)
    pic = np.max(np.abs(sig)) if sig.size else 0
    if pic >= 1:
        raise SystemExit(f"{chemin} : crête {pic:.3f} ≥ 1, refus d'écrêter")
    q = np.round(sig * 8388607).astype("<i4")
    octets = q.reshape(-1).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR)
        w.writeframes(octets)
    return Path(chemin)


# ── 1. la « ligne qui s'ouvre » (point 2) ──────────────────────────────────
T_TEL, T_OUVERT = 0.090, 0.250          # 0 → 90 ms en bande téléphone ; fondu cosinus 90 → 250 ms vers la pleine bande


def poids_ouverture(tau):
    """0 dans la ligne (τ < 90 ms), fondu cosinus jusqu'à 1 à 250 ms (pleine bande). Sert aussi au pan : dans la
    ligne, le son est au centre (c'est le réseau) ; ouvert, il est au point."""
    p = np.clip((np.asarray(tau) - T_TEL) / (T_OUVERT - T_TEL), 0, 1)
    return 0.5 - 0.5 * np.cos(np.pi * p)


def ligne_qui_s_ouvre(n, i0=0, phi0=0.0, tau=0.35, attaque=0.008, indice=1.4, k_ligne=1.3,
                      etincelle=0.6, tau_etincelle=0.12, rapport_etincelle=3.5, f=F_LA):
    """Le la qui naît dans la ligne et s'ouvre. n échantillons, l'ouverture (τ = 0) à l'échantillon i0.
    - voie téléphone : tanh(k·sin φ)/tanh(k), passe-bande 300-3 400 Hz (masque FFT, fronts 50 Hz), crête ramenée à 1 ;
    - voie pleine bande : sin(φ + I·sin φ + Ie·sin(3,5·φ)), I = 1,4, Ie = 0,6·exp(−(τ − 0,09)/0,12) dès l'ouverture
      (l'étincelle : comptée depuis le DÉBUT de l'ouverture ; comptée depuis la naissance de la note, elle ne valait plus
      que 0,28 quand la voie pleine bande commence à s'entendre, et les partiels 2-8 kHz du geste ne sortaient pas) ;
    - y = (1 − w(τ))·téléphone + w(τ)·pleine bande, w = poids_ouverture ;
    - amplitude : 1 avant l'ouverture (l'appelant y pose sa propre enveloppe, la tonalité), exp(−τ/tau) après ;
      si i0 = 0, attaque en cosinus de `attaque` s (une note seule).
    φ = phi0 + 2π·f·i/SR : la phase continue celle de la tonalité quand on passe phi0 = 2π·440·t_début.
    Renvoie (y mono, w)."""
    pad = int(0.1 * SR)
    i = np.arange(-pad, n + pad)
    phi_ext = phi0 + 2 * np.pi * f * i / SR
    tel = passe_bande(couleur_ligne(np.sin(phi_ext), k_ligne), 300.0, 3400.0, front=50.0)[pad:pad + n]
    tel /= np.max(np.abs(tel[len(tel) // 4:3 * len(tel) // 4])) if n > 400 else np.max(np.abs(tel))
    phi = phi_ext[pad:pad + n]
    tau_ = (np.arange(n) - i0) / SR
    tp = np.maximum(tau_, 0)
    ie = etincelle * np.exp(-np.maximum(tp - T_TEL, 0) / tau_etincelle)
    plein = np.sin(phi + indice * np.sin(phi) + ie * np.sin(rapport_etincelle * phi))
    w = np.where(tau_ < 0, 0.0, poids_ouverture(tp))
    y = (1 - w) * tel + w * plein
    env = np.where(tau_ < 0, 1.0, np.exp(-tp / tau))
    if i0 == 0 and attaque:
        na = int(round(attaque * SR))
        env[:na] *= rampe_cos(na)
    return y * env, w


def note_la(duree, tau=0.35, attaque=0.008):
    """la4 440 Hz, la ligne qui s'ouvre, seule (écriture du rendez-vous, signature). Mono, crête 1.
    Renvoie (y, w) : w = poids d'ouverture (pan : centre dans la ligne, point une fois ouvert)."""
    n = int(round(duree * SR))
    y, w = ligne_qui_s_ouvre(n, 0, tau=tau, attaque=attaque)
    y = finir(y)
    return y / np.max(np.abs(y)), w


def note_sol(duree, tau=0.45, attaque=0.005, indice=1.2, tau_indice=0.25):
    """sol4 392 Hz, cloche FM 1:1 chaude (inchangée depuis la v1) : I(τ) = 1,2·exp(−τ/0,25), amplitude exp(−τ/tau)."""
    n = int(round(duree * SR))
    t = np.arange(n) / SR
    phi = phase(F_SOL, n)
    y = np.sin(phi + indice * np.exp(-t / tau_indice) * np.sin(phi))
    env = np.exp(-t / tau)
    na = int(round(attaque * SR))
    env[:na] *= rampe_cos(na)
    return crete(finir(y * env), 0)


def note_re(duree, echelle_tau=1.0, graine=11):
    """ré5 587,33 Hz, barre de verre (inchangée depuis la v1) : partiels 1 · 2,76 · 5,40 (amplitudes 1 · 0,35 · 0,12,
    τ 1,10 · 0,35 · 0,12 s), doublure à l'octave 1 174,66 Hz (0,30, τ 0,80 s), maillet de 2 ms 2-6 kHz à −26 dB."""
    n = int(round(duree * SR))
    t = np.arange(n) / SR
    y = np.zeros(n)
    for rapport, a, tau in ((1.0, 1.0, 1.10), (2.76, 0.35, 0.35), (5.40, 0.12, 0.12), (2.0, 0.30, 0.80)):
        y += a * np.sin(2 * np.pi * F_RE * rapport * t) * np.exp(-t / (tau * echelle_tau))
    y[:24] *= rampe_cos(24)                      # 0,5 ms : le maillet porte l'attaque, pas un clic numérique
    y /= np.max(np.abs(y))
    m = maillet(0.002, 2000, 6000, graine) * gain(-26)
    y[:len(m)] += m
    return crete(finir(y), 0)


# air : le plan dit « −30 dB sous la crête du ré » et vise « énergie au-dessus de 5 kHz vers −35 dB relatifs ».
# Mesuré sur le motif complet : air en CRÊTE à −30 dB → −43,3 dB au-dessus de 5 kHz ; en RMS à −30 dB → −31,3 dB.
# La cible mesurable prime : RMS à −34 dB sous la crête du ré (crête du bruit ≈ −24 dB) → ≈ −35 dB au-dessus de 5 kHz.
COUCHES_RE = {"air_db_rms": -34.0, "air_tau": 0.35, "air_bande": (6000.0, 12000.0), "air_graines": (91, 92),
              "scint_hz": (2349.3, 2350.0), "scint_a": 0.06, "scint_tau": 1.4,
              "corps_hz": F_RE3, "corps_db": -8.0, "corps_tau": 0.18, "corps_hp": 100.0}


def couches_re(duree, echelle_tau=1.0):
    """Les trois couches ajoutées au ré (point 13), relatives à la crête du ré = 1 :
    - air : deux bruits indépendants (graines 91 et 92), passe-bande 6-12 kHz, un par canal, exp(−τ/0,35), RMS −34 dB
      (voir COUCHES_RE : c'est ce niveau qui tient la cible de −35 dB d'énergie au-dessus de 5 kHz) ;
    - scintillement : 2 349,3 Hz à gauche, 2 350,0 Hz à droite (battement lent de 0,7 Hz), amplitude 0,06, τ 1,4 s ;
    - corps : ré3 146,83 Hz, tanh(2·sin)/tanh(2), τ 0,18 s, 8 dB sous la crête, passe-haut 100 Hz (causal).
    Renvoie (air_scint (n, 2) non panoramiqués, corps mono à panoramiquer avec le ré)."""
    C = COUCHES_RE
    n = int(round(duree * SR))
    t = np.arange(n) / SR
    k1 = int(0.001 * SR)
    air = np.zeros((n, 2))
    for c, graine in enumerate(C["air_graines"]):
        b = passe_bande(np.random.default_rng(graine).standard_normal(n + 8192), *C["air_bande"], front=400.0)[4096:4096 + n]
        b /= np.sqrt(np.mean(b ** 2))
        air[:, c] = b * np.exp(-t / (C["air_tau"] * echelle_tau)) * gain(C["air_db_rms"])
    air[:k1] *= rampe_cos(k1)[:, None]
    sc = np.stack([np.sin(2 * np.pi * C["scint_hz"][0] * t), np.sin(2 * np.pi * C["scint_hz"][1] * t)], axis=1)
    sc *= (C["scint_a"] * np.exp(-t / (C["scint_tau"] * echelle_tau)))[:, None]
    k2 = int(0.002 * SR)
    sc[:k2] *= rampe_cos(k2)[:, None]
    corps = couleur_ligne(np.sin(2 * np.pi * C["corps_hz"] * t), 2.0) * np.exp(-t / (C["corps_tau"] * echelle_tau))
    corps[:k2] *= rampe_cos(k2)
    corps = ffmpeg_filtre(corps, f"highpass=f={C['corps_hp']}")
    corps *= gain(C["corps_db"]) / np.max(np.abs(corps))
    out = finir(air + sc)
    return out, finir(corps)


def re_court(duree=0.20, graine=5, clair=False):
    """Le toucher du point v2 (point 7) : sorti de la bande de la voix.
    ré6 1 174,66 Hz (a 1, τ 0,07 s) + partiels de barre ×2,756 (a 0,35, τ 0,035) et ×5,404 (a 0,18, τ 0,015) ;
    attaque 0,5 ms ; contact de 3 ms (bruit 5-11 kHz, fenêtre de Hann) à −10 dB ; passe-haut 900 Hz du 2e ordre
    (causal, rien sous 1 kHz) ; fondu de sortie de 40 ms. Mono, crête 1.
    clair=True (finition du 27/09, arbitrage 8 : les touchers de « neuf » et « dix » ne sortaient pas de la voix sur un
    haut-parleur de téléphone) : le même ré6, mais un verre plus clair : ses partiels de barre passent devant
    (×2,756 : a 1,2, τ 0,070 ; ×5,404 : a 1,0, τ 0,050), plus le grain du verre, un bruit 5-9 kHz qui s'éteint en 30 ms
    (a 0,6 relatif à la crête), là où la voix téléphonique n'a presque plus rien ; contact de 3 ms à −6 dB. Réglé à la
    mesure (tap − voix sur 3-8 kHz au haut-parleur simulé, 40 ms après le contact : « dix » était à +1,6 dB)."""
    n = int(round(duree * SR))
    t = np.arange(n) / SR
    y = np.zeros(n)
    partiels = (((1.0, 1.0, 0.070), (2.756, 1.2, 0.070), (5.404, 1.0, 0.050)) if clair else
                ((1.0, 1.0, 0.070), (2.756, 0.35, 0.035), (5.404, 0.18, 0.015)))
    for rapport, a, tau in partiels:
        y += a * np.sin(2 * np.pi * F_RE6 * rapport * t) * np.exp(-t / tau)
    y[:24] *= rampe_cos(24)
    y /= np.max(np.abs(y))
    if clair:
        g = np.random.default_rng(1000 + graine)
        grain = passe_bande(g.standard_normal(n + 8192), 5000, 9000, front=500.0)[4096:4096 + n]
        grain /= np.max(np.abs(grain[:int(0.03 * SR)]))
        env = np.exp(-t / 0.030)
        env[:24] *= rampe_cos(24)
        y += 0.6 * grain * env
    m = maillet(0.003, 5000, 11000, graine) * gain(-6 if clair else -10)
    y[:len(m)] += m
    y = ffmpeg_filtre(np.concatenate([y, np.zeros(int(0.01 * SR))]), "highpass=f=900:poles=2")[:n]
    fin = int(0.04 * SR)
    y[-fin:] *= rampe_cos(fin)[::-1]
    return crete(y, 0)


# ── 2. le motif complet, avec son espace ───────────────────────────────────
VARIANTES = {
    # t_sol, t_re, total, réverbe (s), fondu de fin, durées et τ des notes, échelle des τ du ré et de ses couches
    "longue": dict(t_sol=0.240, t_re=0.600, total=3.2, rev=2.2, fondu=0.8, la=(1.6, 0.35), sol=(1.8, 0.45), re=2.6, e=1.0, q=0.40),
    "courte": dict(t_sol=0.120, t_re=0.300, total=0.9, rev=1.0, fondu=0.25, la=(0.6, 0.20), sol=(0.7, 0.26), re=0.6, e=0.42, q=0.52),
}
NIV_NOTES = {"la": -16.0, "sol": -17.0, "re": -15.0}      # crêtes propres (dBFS) avant le décalage de mix.py
REV_MIX = 0.22
HAAS = 0.018
# Largeur (écart au plan, voir le compte rendu) : avec les seules couches prescrites (réverbe 22 %, air, scintillement,
# Haas sur le retour), la corrélation G/D du motif vaut 0,958 (cible 0,75-0,85). Chaque note reçoit une composante
# latérale en QUADRATURE : G += k·H(note), D −= k·H(note), H = transformée de Hilbert (la même note déphasée de 90°,
# décorrélée d'elle-même). La somme mono (G + D)/2 est EXACTEMENT la note d'origine : aucun filtre en peigne. Le la
# s'élargit à mesure qu'il sort de la ligne (poids d'ouverture) ; le sol et le ré gardent leur tête (70 ms) au point
# et ouvrent leur queue : « la ligne s'ouvre, avec de la largeur ».
QUADRATURE = 0.40          # longue ; la courte (queues × 0,42, donc plus de tête) prend 0,52 (VARIANTES)


def hilbert(x, marge=4096):
    """Transformée de Hilbert (partie imaginaire du signal analytique, par FFT, avec marge de zéros)."""
    n = len(x)
    N = 1 << (n + 2 * marge - 1).bit_length()
    X = np.fft.fft(np.concatenate([np.zeros(marge), x]), N)
    h = np.zeros(N); h[0] = 1; h[1:N // 2] = 2; h[N // 2] = 1
    return np.imag(np.fft.ifft(X * h))[marge:marge + n]


def pan_du_point():
    """Pan du point dans le film, relatif au la : pan(τ) = 0,6·(x(t_la + τ) − 540)/540 (point-resolu.json)."""
    ev = json.loads((PROJET / "donnees" / "evenements.json").read_text())
    pr = json.loads((PROJET / "donnees" / "point-resolu.json").read_text())["images"]
    tt = np.array([p["t"] for p in pr]); xx = np.array([p["x_sans"] for p in pr])      # trajectoire, sans secousse
    t_la = ev["signature_la"]["t"]
    return lambda tau: 0.6 * (np.interp(t_la + np.asarray(tau), tt, xx) - 540.0) / 540.0


def signature(variante="longue", pan_fn=None):
    """Renvoie (n, 2) : la à l'échantillon 0.
    longue : la 0 / sol 0,240 / ré 0,600, crêtes −16 / −17 / −15 dBFS, 3,2 s ; courte : la 0 / sol 0,120 / ré 0,300, 0,9 s,
    tous les τ du ré et de ses couches × 0,42.
    Pan : pan_fn(τ) (τ relatif au la) échantillon par échantillon ; le la est au centre tant qu'il est dans la ligne,
    puis glisse vers le point pendant son ouverture (poids_ouverture). Par défaut : le point du film.
    Espace : réverbe de queue 2,2 s (courte 1,0 s) à 22 %, graines séparées (la + sol : 21, tête du ré : 22,
    queue du ré : 23), Haas de 18 ms sur le retour droit de la queue du ré (dès +80 ms), largeur en quadrature
    (QUADRATURE) sur cette même queue, neutre en mono."""
    V = VARIANTES[variante]
    pan_fn = pan_fn or pan_du_point()
    la, w_la = note_la(*V["la"])
    sol = note_sol(*V["sol"])
    re_ = note_re(V["re"], echelle_tau=V["e"])
    couches, corps = couches_re(V["re"], echelle_tau=V["e"])
    N = int(round(V["total"] * SR))
    sec = np.zeros((N + int(V["rev"] * SR) + 2048, 2))
    i_sol, i_re = int(round(V["t_sol"] * SR)), int(round(V["t_re"] * SR))
    tau_la = np.arange(len(la)) / SR
    la_g = la * gain(NIV_NOTES["la"])
    ajouter(sec, elargir(panner(la_g, w_la * pan_fn(tau_la)), la_g, w_la, V["q"]), 0)          # large quand il est ouvert
    sol_g = sol * gain(NIV_NOTES["sol"])
    ajouter(sec, elargir(panner(sol_g, pan_fn(V["t_sol"] + np.arange(len(sol)) / SR)), sol_g, 1 - fenetre_tete(len(sol)), V["q"]), i_sol)
    p_re = pan_fn(V["t_re"] + np.arange(len(re_)) / SR)
    g_re = gain(NIV_NOTES["re"])
    re_s = panner((re_ + corps) * g_re, p_re) + couches * g_re
    # tête (80 ms) et queue du ré, séparées par un fondu enchaîné de 20 ms : seule la queue reçoit le Haas et la largeur
    w = fenetre_tete(len(re_s))
    re_s = elargir(re_s, re_ * g_re, 1 - w, V["q"])
    tete, queue = re_s * w[:, None], re_s * (1 - w)[:, None]
    avant_re = sec.copy()
    ajouter(sec, re_s, i_re)
    hum = np.zeros_like(sec)
    ajouter(hum, humide(avant_re, V["rev"], graine=21), 0)                                     # la + sol
    ajouter(hum, humide(_place(tete, i_re, len(sec)), V["rev"], graine=22), 0)
    hq = humide(_place(queue, i_re, len(sec)), V["rev"], graine=23)
    d = int(HAAS * SR)
    hq[:, 1] = np.concatenate([np.zeros(d), hq[:-d, 1]])                                       # Haas : droite + 18 ms
    ajouter(hum, hq, 0)
    out = (sec + REV_MIX * hum)[:N]
    nf = int(V["fondu"] * SR)
    out[-nf:] *= rampe_cos(nf)[::-1, None]
    return out


def fenetre_tete(n):
    """1 sur la tête (70 ms), fondu cosinus de 20 ms, 0 ensuite : la tête d'une note reste au point."""
    k0, kf = int(0.070 * SR), int(0.020 * SR)
    w = np.ones(n); w[k0 + kf:] = 0; w[k0:k0 + kf] = rampe_cos(kf)[::-1]
    return w


def elargir(st, mono, poids, k=None):
    """Largeur neutre en mono : G += k·p·H(mono), D −= k·p·H(mono) ; (G + D)/2 du son direct inchangé."""
    lat = (QUADRATURE if k is None else k) * hilbert(mono) * poids
    st = st.copy()
    st[:, 0] += lat
    st[:, 1] -= lat
    return st


def _place(sig, i, n):
    z = np.zeros((n, 2))
    return ajouter(z, sig, i)


# ── 3. mesures de la signature (cibles du point 13) ────────────────────────
def correlation(sig):
    """Corrélation G/D à décalage nul : Σ L·R / √(Σ L² · Σ R²)."""
    return float(np.sum(sig[:, 0] * sig[:, 1]) / np.sqrt(np.sum(sig[:, 0] ** 2) * np.sum(sig[:, 1] ** 2)))


def controle_mono(sig):
    """Écart de niveau (dB) entre la somme mono (L+R)/2 et la moyenne quadratique des deux canaux."""
    m = (sig[:, 0] + sig[:, 1]) / 2
    ref = np.sqrt((np.mean(sig[:, 0] ** 2) + np.mean(sig[:, 1] ** 2)) / 2)
    return float(20 * np.log10(np.sqrt(np.mean(m ** 2)) / ref))


def energie_relative(sig, f0, f1=None):
    """Énergie (dB) dans [f0 ; f1] relative à l'énergie totale (deux canaux)."""
    X = np.abs(np.fft.rfft(sig, axis=0)) ** 2
    f = np.fft.rfftfreq(len(sig), 1 / SR)
    m = (f >= f0) & (f <= (f1 or SR / 2))
    return float(10 * np.log10(X[m].sum() / X.sum()))


def analyser(sig):
    return {"correlation_LR": round(correlation(sig), 3), "perte_mono_db": round(controle_mono(sig), 2),
            "energie_sup_5k_db_rel": round(energie_relative(sig, 5000), 1),
            "energie_sup_8k_db_rel": round(energie_relative(sig, 8000), 1)}


def normaliser_tp(sig, cible=-1.0):
    tp = crete_vraie(sig)
    return sig * gain(cible - tp - 0.02)


def livrer():
    SORTIES.mkdir(parents=True, exist_ok=True)
    longue = np.vstack([np.zeros((int(0.05 * SR), 2)), signature("longue")])
    courte = signature("courte")
    rapport = {}
    for nom, sig in (("point-solaire-signature-v2.wav", longue), ("point-solaire-signature-courte-v2.wav", courte)):
        sig = normaliser_tp(sig, -1.0)
        chemin = ecrire24(SORTIES / nom, sig)
        mes = labo.mesurer(chemin)
        rapport[nom] = {"duree_s": round(len(sig) / SR, 3), "crete_vraie_dbtp_numpy": round(crete_vraie(sig), 2),
                        "mesure_ffmpeg": mes, **analyser(sig)}
        print(f"  {chemin}  {rapport[nom]}")
    (ICI / "signature-v2.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1))
    return rapport


if __name__ == "__main__":
    livrer()
