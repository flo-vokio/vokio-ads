#!/usr/bin/env python3
"""Signature sonore Vokio « la · sol · ré » (bible.signature_sonore), et les timbres du point.

    python3 son/signature.py      écrit les deux livrables seuls :
        /root/vokio-uploads/videos/showcase/point-solaire-signature.wav         (0,05 s + 2,9 s)
        /root/vokio-uploads/videos/showcase/point-solaire-signature-courte.wav  (0,9 s)
      48 kHz, 24 bits, stéréo, crête vraie −1 dBTP (suréchantillonnage ×4), compatibles mono (contrôlé).

    import signature as S       (depuis son/mix.py)
        S.note_la(...), S.note_sol(...), S.note_re(...), S.re_court(...)   → mono, crête 1
        S.signature(variante)   → (n, 2), le motif complet avec son espace (pan, réverbe, Haas)

Tout est calculé en numpy à 48 kHz, déterministe (graines fixes) : aucune banque de sons, aucun droit.
Les phases sont intégrées (cumsum de la fréquence instantanée) : aucun saut de phase nulle part.
"""
import sys
import wave
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import labo  # noqa: E402

SR = labo.SR
SORTIES = Path("/root/vokio-uploads/videos/showcase")

F_LA, F_SOL, F_RE = 440.0, 392.0, 587.33
PAN_I = 0.6 * (652.57 - 540) / 540          # abscisse du ı (mesures.s7.centre.x), recalculée dans mix.py


# ── outils ──────────────────────────────────────────────────────────────────
def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def gain(db_):
    return 10 ** (db_ / 20)


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
    """Passe-bande par masque FFT, fronts en cosinus de `front` Hz."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.zeros_like(f)
    m[(f >= f1) & (f <= f2)] = 1
    b = (f > f1 - front) & (f < f1)
    m[b] = 0.5 - 0.5 * np.cos(np.pi * (f[b] - (f1 - front)) / front)
    b = (f > f2) & (f < f2 + front)
    m[b] = 0.5 + 0.5 * np.cos(np.pi * (f[b] - f2) / front)
    return np.fft.irfft(X * m, n)


def maillet(duree, f1, f2, graine):
    """Transitoire de maillet : bruit blanc en passe-bande, fenêtré en Hann, crête 1."""
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
    y[-k:] *= rampe_cos(k)[::-1]
    return y


def panner(x, pan):
    """Mono → (n, 2), loi à puissance constante de labo.placer (centre = 1, 1). pan scalaire ou tableau."""
    a = (np.asarray(pan, dtype=np.float64) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1) * np.sqrt(2)


def humide(sig, secondes, graine=1, predelai=0.012):
    """Retour de réverbe SEUL (labo.reverbe avec mix = 1) : le direct n'est jamais atténué."""
    return labo.reverbe(sig, secondes, 1.0, graine=graine, predelai=predelai)


def ajouter(piste, sig, i):
    """Additionne sig (n, 2) dans piste à l'échantillon i (coupé au bord)."""
    j = min(len(piste), i + len(sig))
    if j > i >= 0:
        piste[i:j] += sig[:j - i]
    return piste


def crete_vraie(sig, facteur=4):
    """Crête vraie (dBTP) par suréchantillonnage FFT ×facteur, canal par canal."""
    sig = np.atleast_2d(sig.T).T
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


# ── les notes (mono, crête normalisée à 1) ──────────────────────────────────
def note_la(duree, tau=0.35, attaque=0.008, montee=0.060, indice=1.4, tau_indice=None, k_ligne=1.3):
    """la4 440 Hz : naît en sinus au timbre de la tonalité (tanh 1,3), puis s'ouvre en cloche FM 1:1.
    y = tanh(k·s)/tanh(k), s = sin(φ + I(τ)·sin φ), I(τ) = indice·min(τ/montee ; 1) [·exp(−max(τ−montee ; 0)/tau_indice)],
    k(τ) = k_ligne·(1 − min(τ/montee ; 1)) : la couleur de ligne s'efface pendant que la cloche s'ouvre."""
    n = int(round(duree * SR))
    t = np.arange(n) / SR
    phi = phase(F_LA, n)
    r = np.clip(t / montee, 0, 1)
    I = indice * r
    if tau_indice:
        I = I * np.exp(-np.maximum(t - montee, 0) / tau_indice)
    y = couleur_ligne(np.sin(phi + I * np.sin(phi)), k_ligne * (1 - r))
    env = np.exp(-t / tau)
    na = int(round(attaque * SR))
    env[:na] *= rampe_cos(na)
    return crete(finir(y * env), 0)


def note_sol(duree, tau=0.45, attaque=0.005, indice=1.2, tau_indice=0.25):
    """sol4 392 Hz, cloche FM 1:1 chaude : I(τ) = 1,2·exp(−τ/0,25), amplitude exp(−τ/tau)."""
    n = int(round(duree * SR))
    t = np.arange(n) / SR
    phi = phase(F_SOL, n)
    y = np.sin(phi + indice * np.exp(-t / tau_indice) * np.sin(phi))
    env = np.exp(-t / tau)
    na = int(round(attaque * SR))
    env[:na] *= rampe_cos(na)
    return crete(finir(y * env), 0)


def note_re(duree, echelle_tau=1.0, graine=11):
    """ré5 587,33 Hz, barre de verre : partiels 1 · 2,76 · 5,40 (amplitudes 1 · 0,35 · 0,12, τ 1,10 · 0,35 · 0,12 s),
    doublure à l'octave 1 174,66 Hz (0,30, τ 0,80 s), maillet de 2 ms en passe-bande 2-6 kHz à −26 dB sous la note."""
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


def re_court(duree=0.25, graine=5):
    """Le toucher du point : ré5 court et étouffé (587,33 Hz a 1 τ 0,09 s ; ×3,99 a 0,25 τ 0,03 s),
    attaque 1 ms, maillet de 1,5 ms en passe-bande 2-5 kHz à −18 dB."""
    n = int(round(duree * SR))
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * F_RE * t) * np.exp(-t / 0.09) + 0.25 * np.sin(2 * np.pi * F_RE * 3.99 * t) * np.exp(-t / 0.03)
    y[:48] *= rampe_cos(48)
    y /= np.max(np.abs(y))
    m = maillet(0.0015, 2000, 5000, graine) * gain(-18)
    y[:len(m)] += m
    fin = int(0.04 * SR)
    y[-fin:] *= rampe_cos(fin)[::-1]
    return crete(y, 0)


# ── le motif complet, avec son espace ───────────────────────────────────────
def signature(variante="longue", pan=PAN_I):
    """Renvoie (n, 2) : la à l'échantillon 0.
    longue : la 0 / sol 0,240 / ré 0,600, crêtes −16 / −17 / −15 dBFS, 2,9 s (1,9 s de notes + 1,0 s de queue).
    courte : la 0 / sol 0,120 / ré 0,300, queue de 0,6 s, 0,9 s en tout.
    Espace : pan à l'abscisse du ı, réverbe 1,6 s à 18 %, Haas de 18 ms sur le retour droit de la queue du ré (dès +80 ms)."""
    if variante == "longue":
        t_sol, t_re, total, rev, fondu = 0.240, 0.600, 2.9, 1.6, 0.6
        la = note_la(1.6, tau=0.35)
        sol = note_sol(1.8, tau=0.45)
        re_ = note_re(2.3)
    elif variante == "courte":
        t_sol, t_re, total, rev, fondu = 0.120, 0.300, 0.9, 1.0, 0.25
        la = note_la(0.6, tau=0.20)
        sol = note_sol(0.7, tau=0.26)
        re_ = note_re(0.6, echelle_tau=0.42)
    else:
        raise ValueError(variante)
    N = int(round(total * SR))
    sec = np.zeros((N + int(rev * SR) + 2048, 2))
    ajouter(sec, panner(la * gain(-16), pan), 0)
    ajouter(sec, panner(sol * gain(-17), pan), int(round(t_sol * SR)))
    i_re = int(round(t_re * SR))
    re_s = panner(re_ * gain(-15), pan)
    # tête (80 ms) et queue du ré, séparées par un fondu enchaîné de 20 ms : seule la queue reçoit le Haas
    k0, kf = int(0.070 * SR), int(0.020 * SR)
    w = np.ones(len(re_s)); w[k0 + kf:] = 0; w[k0:k0 + kf] = rampe_cos(kf)[::-1]
    tete, queue = re_s * w[:, None], re_s * (1 - w)[:, None]
    ajouter(sec, re_s, i_re)
    hum = np.zeros_like(sec)
    ajouter(hum, humide(sec - _place(tete + queue, i_re, len(sec)), rev, graine=21), 0)   # la + sol
    ajouter(hum, humide(_place(tete, i_re, len(sec)), rev, graine=22), 0)
    hq = humide(_place(queue, i_re, len(sec)), rev, graine=23)
    d = int(0.018 * SR)
    hq[:, 1] = np.concatenate([np.zeros(d), hq[:-d, 1]])                                   # Haas : droite + 18 ms
    ajouter(hum, hq, 0)
    out = (sec + 0.18 * hum)[:N]
    nf = int(fondu * SR)
    out[-nf:] *= rampe_cos(nf)[::-1, None]
    return out


def _place(sig, i, n):
    z = np.zeros((n, 2))
    return ajouter(z, sig, i)


def normaliser_tp(sig, cible=-1.0):
    tp = crete_vraie(sig)
    return sig * gain(cible - tp - 0.02)


def controle_mono(sig):
    """Écart de niveau (dB) entre la somme mono (L+R)/2 et la moyenne quadratique des deux canaux."""
    m = (sig[:, 0] + sig[:, 1]) / 2
    ref = np.sqrt((np.mean(sig[:, 0] ** 2) + np.mean(sig[:, 1] ** 2)) / 2)
    return 20 * np.log10(np.sqrt(np.mean(m ** 2)) / ref)


def livrer():
    SORTIES.mkdir(parents=True, exist_ok=True)
    longue = signature("longue")
    longue = np.vstack([np.zeros((int(0.05 * SR), 2)), longue])
    courte = signature("courte")
    rapport = {}
    for nom, sig in (("point-solaire-signature.wav", longue), ("point-solaire-signature-courte.wav", courte)):
        sig = normaliser_tp(sig, -1.0)
        chemin = ecrire24(SORTIES / nom, sig)
        mes = labo.mesurer(chemin)
        rapport[nom] = {"duree_s": round(len(sig) / SR, 3), "crete_vraie_dbtp_numpy": round(crete_vraie(sig), 2),
                        "mesure_ffmpeg": mes, "ecart_mono_db": round(controle_mono(sig), 2)}
        print(f"  {chemin}  {rapport[nom]}")
    return rapport


if __name__ == "__main__":
    livrer()
