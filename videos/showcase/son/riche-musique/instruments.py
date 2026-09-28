#!/usr/bin/env python3
"""Timbres de la variante « musique » (27/09) : synthèse numpy à 48 kHz, déterministe (graines fixes), aucun échantillon.

Chaque fonction rend un son MONO (ndarray float64), crête ~1 sauf mention ; la partition (mix_riche_musique.py) le place,
le panoramique et lui donne son niveau. Les hauteurs sont en MIDI (A4 = 69 = 440 Hz, tempérament égal).

    marimba(m, duree, vel)       lame de bois (partiels 1 · 3,93 · 9,24), maillet feutré
    harpe(m, duree, vel)         corde pincée additive (spectre de pincement, décroissance par partiel)
    verre(m, duree, vel)         barre de verre (partiels 1 · 2,756 · 5,404 : la matière du point et du ré)
    cordes(notes, t, poids)      ensemble à cordes (table d'onde en dents de scie à bande limitée, 3 voix par note)
    basse(m, duree)              pincée additive (harmoniques 1 à 8, la fondamentale ne porte que ~17 % de l'énergie) :
                                 les harmoniques portent la note sur un haut-parleur de téléphone
    grosse_caisse(vel, grave)    feutrée : corps 110 Hz → f_fin (la basse de l'accord), « toc » 300 → 240 Hz, maillet 4-6 kHz
    coeur(vel)                   battement feutré passe-bas 600 Hz + tapotement 330 Hz et 600-1 500 Hz
    shaker(vel, graine)          bruit 5-13 kHz, 25 ms
    cymbale_inverse(duree)       souffle de cymbale qui monte (bruit au-dessus de 4 kHz, enveloppe inversée)
    miroitement(duree)           queue de cymbale douce après l'arrivée
"""
import numpy as np

import labo
import signature as S

SR = labo.SR


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=np.float64) - 69) / 12)


def _t(duree):
    return np.arange(int(round(duree * SR))) / SR


def _attaque(y, ms):
    k = max(1, int(ms * SR / 1000))
    y[:k] *= S.rampe_cos(k)
    return y


def _fin(y, ms=30):
    k = min(len(y) // 3, int(ms * SR / 1000))
    if k > 0:
        y[-k:] *= S.rampe_cos(k)[::-1]
    return y


def marimba(m, duree=1.2, vel=0.7, graine=0):
    """Lame de marimba : partiels 1 · 3,93 · 9,24 (accord des lames 1:4:10), le fondamental prolongé par le résonateur.
    vel (0-1) règle la brillance (poids des partiels hauts) ; maillet = bruit 1,5 ms passe-bas 3 kHz."""
    f = float(hz(m))
    t = _t(duree)
    tau0 = 0.55 * (440.0 / f) ** 0.45
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / tau0)
    for r, a, tau in ((3.93, 0.22, 0.10), (9.24, 0.07, 0.035)):
        if f * r < 16000:
            y += a * (0.4 + 0.8 * vel) * np.sin(2 * np.pi * f * r * t + 0.3) * np.exp(-t / tau)
    g = np.random.default_rng(700 + graine)
    k = int(0.0015 * SR)
    bruit = g.standard_normal(k) * np.hanning(k + 2)[1:-1]
    a = 1 - np.exp(-2 * np.pi * 3000 / SR)
    x = 0.0
    for i in range(k):
        x += a * (bruit[i] - x); bruit[i] = x
    y[:k] += 0.35 * vel * bruit / (np.max(np.abs(bruit)) + 1e-12)
    y = _attaque(y, 0.8)
    return _fin(y / np.max(np.abs(y)), 40)


def harpe(m, duree=2.0, vel=0.7, graine=0, position=0.18, brillance=1.0):
    """Corde pincée additive : a_k = |sin(π·k·p)|/k^1,6, τ_k = τ1/(1 + 0,0009·k²·f/200) ; légère inharmonicité ;
    au plus 7 kHz. Plus vel est haut, plus le pincement garde d'aigus."""
    f = float(hz(m))
    t = _t(duree)
    tau1 = 1.6 * (220.0 / f) ** 0.5
    y = np.zeros_like(t)
    rng = np.random.default_rng(900 + graine)
    K = int(min(24, 7000 // f))
    for k in range(1, K + 1):
        fk = f * k * np.sqrt(1 + 0.00008 * k * k)
        a = abs(np.sin(np.pi * k * position)) / k ** (1.6 - 0.4 * vel * brillance)
        tau = tau1 / (1 + 0.0009 * k * k * f / 200)
        y += a * np.sin(2 * np.pi * fk * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t / tau)
    y = _attaque(y, 1.5)
    return _fin(y / np.max(np.abs(y)), 60)


def verre(m, duree=1.6, vel=0.7, graine=0, echelle_tau=1.0):
    """Barre de verre (la matière du point : partiels 1 · 2,756 · 5,404, comme le ré et les touchers) :
    τ 0,9 · 0,28 · 0,10 s (× echelle_tau), maillet 2 ms 2-6 kHz."""
    f = float(hz(m))
    t = _t(duree)
    y = np.zeros_like(t)
    for r, a, tau in ((1.0, 1.0, 0.9), (2.756, 0.30 * (0.6 + 0.6 * vel), 0.28), (5.404, 0.10 * (0.5 + vel), 0.10)):
        if f * r < 18000:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau * echelle_tau))
    y = _attaque(y, 0.5)
    y /= np.max(np.abs(y))
    mm = S.maillet(0.002, 2000, 6000, 40 + graine) * S.gain(-24)
    y[:len(mm)] += mm * vel
    return _fin(y / np.max(np.abs(y)), 60)


_TABLES = {}


def _table_scie(f, fmax=5200.0, L=4096):
    """Une période de dent de scie à bande limitée (harmoniques ≤ fmax), avec une pente douce (cordes feutrées)."""
    K = max(1, int(fmax // f))
    cle = (K, L)
    if cle not in _TABLES:
        ph = np.arange(L) / L * 2 * np.pi
        w = np.zeros(L)
        for k in range(1, K + 1):
            w += np.sin(k * ph) / k * (1 / np.sqrt(1 + (k / 12.0) ** 2))
        _TABLES[cle] = w / np.max(np.abs(w))
    return _TABLES[cle]


def voix_corde(f, t, graine, desaccord_cents=0.0, vibrato=True, chrono=None):
    """Une voix d'ensemble : table de scie lue par un accumulateur de phase, vibrato 5,2 Hz ± 4 cents qui entre en
    0,6 s, dérive lente ± 3 cents, phase propre.
    chrono (outils/chronologie.py, 28/09) : une note TENUE à travers une insertion de temps garde son horloge du film
    d'avant (vers_base) ; dans la mesure insérée, sa dérive, son vibrato et sa phase font chacun un nombre entier de
    cycles (vibrato ±0,16 Hz, hauteur ±1,4 cent au plus, pendant la mesure) : la note continue sans raccord, et après
    l'insertion elle redonne exactement celle d'avant, décalée. Sans insertion, ou avant le pivot : à l'octet près."""
    rng = np.random.default_rng(graine)
    n = len(t)
    if chrono:
        tt = chrono.vers_base(t); tt = tt - tt[0]
        r1, q1 = rng.uniform(0.07, 0.13), rng.uniform(0, 6.3)
        cents = desaccord_cents + 3.0 * np.sin(2 * np.pi * r1 * tt + 2 * np.pi * chrono.cycles_entiers(r1, t) + q1)
        if vibrato:
            r2, q2 = rng.uniform(4.8, 5.6), rng.uniform(0, 6.3)
            cents = cents + 4.0 * np.clip(tt / 0.6, 0, 1) * np.sin(2 * np.pi * r2 * tt + 2 * np.pi * chrono.cycles_entiers(r2, t) + q2)
        fi = chrono.phase_entiere(f * 2 ** (cents / 1200), int(round(t[0] * SR)))
    else:
        tt = t - t[0]
        cents = desaccord_cents + 3.0 * np.sin(2 * np.pi * rng.uniform(0.07, 0.13) * tt + rng.uniform(0, 6.3))
        if vibrato:
            cents = cents + 4.0 * np.clip(tt / 0.6, 0, 1) * np.sin(2 * np.pi * rng.uniform(4.8, 5.6) * tt + rng.uniform(0, 6.3))
        fi = f * 2 ** (cents / 1200)
    ph = rng.uniform(0, 1) + np.concatenate([[0.0], np.cumsum(fi[:-1])]) / SR
    tab = _table_scie(f)
    L = len(tab)
    x = (ph % 1.0) * L
    i0 = x.astype(np.int64)
    fr = x - i0
    return tab[i0 % L] * (1 - fr) + tab[(i0 + 1) % L] * fr


# harmoniques de la basse (amplitude relative ; la fondamentale ne porte que ~17 % de l'énergie) : sur un haut-parleur
# de téléphone (rien sous 250 Hz), un mi2 à 82 Hz s'entend par ses harmoniques 4 à 8 (330-660 Hz) ; en pleine bande, la
# fondamentale est là, et l'oreille la reconstruit de toute façon (fondamentale absente)
HARM_BASSE = (0.55, 0.75, 0.62, 0.50, 0.40, 0.28, 0.20, 0.14)


def basse(m, duree, attaque_ms=10, relache_ms=90, harmoniques=HARM_BASSE, sustain=0.72, decroissance=0.35, coupure=1400.0):
    """Basse « pincée » additive (relecture 27/09, défaut 3 : la version tanh(1,8) perdait 12 dB sur un téléphone, sa
    fondamentale coûtait à la voix sans s'y entendre) : harmoniques HARM_BASSE, phases fixes, chacune avec sa décroissance
    (les aiguës s'éteignent plus vite vers un sustain plus bas : le pincement), légère saturation tanh(1,3), passe-bas à un
    pôle à `coupure`. Enveloppe générale : attaque, décroissance vers sustain en `decroissance` s, relâche en cosinus."""
    f = float(hz(m))
    t = _t(duree)
    y = np.zeros_like(t)
    for k, a in enumerate(harmoniques, start=1):
        if k * f > 5000:
            break
        s_k = sustain ** (1 + 0.35 * (k - 1))
        env_k = s_k + (1 - s_k) * np.exp(-t / (decroissance / (1 + 0.25 * (k - 1))))
        y += a * np.sin(2 * np.pi * k * f * t + 0.7 * k) * env_k
    y = np.tanh(1.3 * y / np.max(np.abs(y))) / np.tanh(1.3)
    y = S.ffmpeg_filtre(y, f"lowpass=f={coupure:g}:p=1")
    y = _attaque(y, attaque_ms)
    return _fin(y / np.max(np.abs(y)), relache_ms)


def grosse_caisse(vel=0.7, grave=False, graine=0, drive=3.0, toc_db=-6.0, maillet_db=-12.0, corps=0.7, f_fin=49.0,
                  chute=0.020):
    """Grosse caisse feutrée : corps (sinus dont la fréquence tombe de 110 Hz à f_fin, τ `chute`, amplitude τ 0,19 s) à
    `corps`, saturé tanh(drive) ; un « toc » (sinus 300 Hz → 240 Hz, τ 30 ms) à `toc_db` ; un clic de 1 ms ; un maillet
    4-6 kHz de 4 ms à `maillet_db` (None : sans). Relecture 27/09, défaut 3 : le corps seul perdait 19 dB sur un
    téléphone ; le toc et le maillet sont ce qu'un petit haut-parleur restitue. grave : plus long, sans toc.
    f_fin : la note où le corps se pose ; la partition la prend sur la basse de l'accord (mix_riche_musique.note_du_corps).
    Deuxième relecture 27/09, défaut 4 : le glissando grave (+6 Hz·exp(−t/0,3)) posait l'énergie un demi-ton trop haut
    (la#1 sous le ré, sol#1 sous « -tion ») ; il est retiré, et la chute de 110 Hz se resserre de τ 35 à 20 ms : le pic
    spectral tombe à ±0,3 demi-ton de f_fin (controle_musique.py, H)."""
    d = 0.9 if grave else 0.5
    t = _t(d)
    f = f_fin + (110 - f_fin) * np.exp(-t / chute)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / (0.34 if grave else 0.19))
    y = corps * np.tanh(drive * y) / np.tanh(drive)
    if toc_db is not None and not grave:
        ft = 240 + 60 * np.exp(-t / 0.02)
        y += S.gain(toc_db) * np.sin(2 * np.pi * np.cumsum(ft) / SR) * np.exp(-t / 0.030)
    g = np.random.default_rng(300 + graine)
    k = int(0.001 * SR)
    y[:k] += 0.08 * vel * g.standard_normal(k)
    y = _attaque(y, 0.6)
    y /= np.max(np.abs(y))
    if maillet_db is not None:
        mm = S.maillet(0.004, 4000, 6000, 320 + graine) * S.gain(maillet_db) * (0.6 + 0.4 * vel)
        y[:len(mm)] += mm
    return _fin(y / np.max(np.abs(y)), 40)


def coeur(vel=0.5, graine=0):
    """Battement feutré (s1) : grosse caisse douce (corps seul, posé sur la1 comme la quinte ; saturé tanh 4 pour ses
    harmoniques 150-500 Hz ; sans toc ni maillet) passée deux fois en passe-bas à 600 Hz, « lub » puis « dub » 0,26 s
    plus tard à −7 dB, chacun avec un
    tapotement feutré : sinus 330 Hz (τ 35 ms) à −6 dB et bruit 600-1 500 Hz (τ 10 ms) à −14 dB. Relecture 27/09,
    défaut 6 : passé à 140 Hz, le cœur disparaissait sur un téléphone (−72,7 LUFS) ; le tapotement est ce qui passe."""
    # chute τ 35 ms gardée (le cœur n'a jamais eu de glissando grave : son pic est déjà à 55,3 Hz, la1)
    k1 = grosse_caisse(vel, graine=graine, drive=4.0, toc_db=None, maillet_db=None, corps=1.0, f_fin=55.0, chute=0.035)
    y = np.zeros(int(0.9 * SR))
    y[:len(k1)] += k1
    i = int(0.26 * SR)
    k2 = grosse_caisse(vel, graine=graine + 1, drive=4.0, toc_db=None, maillet_db=None, corps=1.0, f_fin=55.0,
                       chute=0.035)[:len(y) - i]
    y[i:i + len(k2)] += k2 * S.gain(-7)
    y = S.ffmpeg_filtre(y, "lowpass=f=600,lowpass=f=600")
    y /= np.max(np.abs(y))
    tt = _t(0.12)
    g = np.random.default_rng(610 + graine)
    for i0, g_ in ((0, 0.0), (i, -7.0)):
        tap = S.gain(-6) * np.sin(2 * np.pi * 330 * tt) * np.exp(-tt / 0.035)
        b = S.passe_bande(g.standard_normal(len(tt) + 4096), 600, 1500, front=150.0)[2048:2048 + len(tt)]
        tap += S.gain(-14) * b / np.max(np.abs(b)) * np.exp(-tt / 0.010)
        tap = _attaque(tap, 1.0) * S.gain(g_)
        y[i0:i0 + len(tap)] += tap
    return _fin(y / np.max(np.abs(y)), 60)


def shaker(vel=0.6, graine=0, duree=0.09):
    """Coup de shaker : bruit 5-13 kHz, attaque 6 ms, décroissance τ 22 ms (grains un peu différents à chaque coup)."""
    n = int(duree * SR)
    g = np.random.default_rng(500 + graine)
    b = S.passe_bande(g.standard_normal(n + 4096), 5000, 13000, front=800.0)[2048:2048 + n]
    t = np.arange(n) / SR
    env = np.exp(-t / (0.018 + 0.010 * vel))
    k = int(0.006 * SR)
    env[:k] *= S.rampe_cos(k)
    y = b * env
    return _fin(y / np.max(np.abs(y)), 10)


def cymbale_inverse(duree=1.5, graine=0):
    """Souffle de cymbale inversé : bruit passe-haut 4 kHz (léger pic à 7 kHz), queue exponentielle τ 0,5 s lue à
    l'envers ; la crête est au dernier échantillon (l'instant visé)."""
    n = int(duree * SR)
    g = np.random.default_rng(600 + graine)
    b = S.passe_bande(g.standard_normal(n + 8192), 4000, 15000, front=1500.0)[4096:4096 + n]
    b += 0.5 * S.passe_bande(g.standard_normal(n + 8192), 6000, 8500, front=800.0)[4096:4096 + n]
    t = np.arange(n) / SR
    y = (b * np.exp(-t / (0.32 * duree)))[::-1]
    k = int(0.004 * SR)
    y[-k:] *= S.rampe_cos(k)[::-1]
    return y / np.max(np.abs(y))


def miroitement(duree=2.5, graine=0):
    """Queue de cymbale douce après l'arrivée : bruit 6-14 kHz, attaque 30 ms, τ 0,8 s."""
    n = int(duree * SR)
    g = np.random.default_rng(650 + graine)
    b = S.passe_bande(g.standard_normal(n + 8192), 6000, 14000, front=1200.0)[4096:4096 + n]
    t = np.arange(n) / SR
    env = np.exp(-t / 0.8)
    k = int(0.03 * SR)
    env[:k] *= S.rampe_cos(k)
    return _fin(b * env / np.max(np.abs(b * env)), 200)
