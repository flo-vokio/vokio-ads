#!/usr/bin/env python3
"""Bibliothèque son commune (numpy + PIL + ffmpeg, sans scipy) : lire, écrire, mesurer, dessiner.

    import sys; sys.path.insert(0, "/opt/vokio-ads/videos/showcase/outils"); import sonlib as L
    x = L.lire("a.wav")                      (n, 2) float64, 48 kHz (tout format lisible par ffmpeg, MP4 compris)
    L.ecrire24("b.wav", x)                   PCM 24 bits, refuse d'écrêter
    L.mesure(x) -> {"I", "TP", "LRA"}        loudnorm de ffmpeg (intégré, crête vraie, plage)
    L.sonie_courbe(x, 3.0)                   sonie court terme (S, 3 s) ou momentanée (M, 0,4 s) toutes les 0,1 s, en numpy
    L.sonie(x, a, b)                         LUFS non fenêtré (pondération K) sur [a ; b] : pour comparer deux mots
    L.profil(x, 0.005)                       RMS par pas de 5 ms en dBFS (somme des deux canaux)
    L.bandes(x)                              énergie par bande d'octave, pas de 5 ms
    L.planche([(titre, x), ...], t0, t1, "p.png", reperes=[(t, "nom")])   spectrogrammes + profils empilés
    L.courbe_png([(nom, t, y, couleur)], "c.png", t0, t1, ymin, ymax)    courbes (sonie, limiteur…)
    L.egaliseur(x, [{"type": "cloche", "f": 3000, "g": -2, "q": 1}])      EQ à phase nulle ; L.passe_bande(x, f1, f2)
    L.presence(voix) + L.gain_suiveur(...)                                  détecteur de voix et ducking (1 ms)
    L.masteriser(somme, lufs=-14, plafond_db=-1.7)                          un gain + limiteur à crête vraie ×4
Aucun état, aucune écriture hors des chemins donnés. Utilisé par outils/mixer.py, outils/ausculter.py,
outils/fond_ligne.py et son/stems_amont.py.
"""
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000


# ── entrées / sorties ──────────────────────────────────────────────────────
def lire(chemin, sr=SR):
    """N'importe quel fichier son (wav, mp3, mp4…) → (n, 2) float64 à sr."""
    brut = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(chemin), "-vn", "-f", "f32le", "-ac", "2",
                           "-ar", str(sr), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(brut, dtype="<f4").reshape(-1, 2).astype(np.float64)


def ecrire24(chemin, sig, sr=SR):
    """WAV PCM 24 bits stéréo. Refuse une crête ≥ 1 (jamais d'écrêtage silencieux)."""
    sig = np.asarray(sig, dtype=np.float64)
    if sig.ndim == 1:
        sig = np.stack([sig, sig], axis=1)
    pic = float(np.max(np.abs(sig))) if sig.size else 0.0
    if pic >= 1:
        raise SystemExit(f"{chemin} : crête {pic:.3f} ≥ 1, refus d'écrêter")
    q = np.round(sig * 8388607).astype("<i4")
    octets = q.reshape(-1).view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(2); w.setsampwidth(3); w.setframerate(sr)
        w.writeframes(octets)
    return Path(chemin)


def mono(x):
    x = np.asarray(x, dtype=np.float64)
    return x.mean(axis=1) if x.ndim > 1 else x


def stereo(x):
    x = np.asarray(x, dtype=np.float64)
    return np.stack([x, x], axis=1) if x.ndim == 1 else x


# ── petites briques ────────────────────────────────────────────────────────
def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def gain(db_):
    return 10 ** (np.asarray(db_, dtype=np.float64) / 20)


def rampe_cos(n):
    """0 → 1 en cosinus surélevé sur n échantillons."""
    if n <= 0:
        return np.ones(0)
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)


def enveloppe_fenetres(n, fenetres, valeur, fondu, sr=SR, base=1.0):
    """Courbe (n,) qui vaut `base` partout et `valeur` sur chaque fenêtre [a, b], avec des fondus cosinus de `fondu` s
    DE CHAQUE CÔTÉ À L'EXTÉRIEUR de la fenêtre (la fenêtre entière est à la valeur pleine)."""
    t = np.arange(n) / sr
    poids = np.zeros(n)
    for a, b in fenetres:
        p = np.zeros(n)
        p[(t >= a) & (t <= b)] = 1.0
        if fondu > 0:
            m = (t >= a - fondu) & (t < a)
            p[m] = 0.5 - 0.5 * np.cos(np.pi * (t[m] - (a - fondu)) / fondu)
            m = (t > b) & (t <= b + fondu)
            p[m] = 0.5 + 0.5 * np.cos(np.pi * (t[m] - b) / fondu)
        poids = np.maximum(poids, p)
    return base + (valeur - base) * poids


def filtre_frequentiel(x, H, marge=0):
    """Applique un filtre à phase nulle défini par son module H(f) (f en Hz, tableau) par FFT, canal par canal."""
    x = np.asarray(x, dtype=np.float64)
    deux = x.ndim == 2
    X = x if deux else x[:, None]
    n = len(X)
    M = 1 << (n + marge - 1).bit_length()
    f = np.fft.rfftfreq(M, 1 / SR)
    h = H(f)
    Y = np.stack([np.fft.irfft(np.fft.rfft(X[:, c], M) * h, M)[:n] for c in range(X.shape[1])], axis=1)
    return Y if deux else Y[:, 0]


def passe_bande(x, f1=None, f2=None, front=0.25):
    """Passe-bande doux à phase nulle : fronts en cosinus sur ±front octave autour de f1 et f2 (None = ouvert)."""
    def H(f):
        h = np.ones_like(f)
        lf = np.log2(np.maximum(f, 1e-3))
        if f1:
            p = np.clip((lf - (np.log2(f1) - front)) / (2 * front), 0, 1)
            h *= 0.5 - 0.5 * np.cos(np.pi * p)
        if f2:
            p = np.clip((lf - (np.log2(f2) - front)) / (2 * front), 0, 1)
            h *= 0.5 + 0.5 * np.cos(np.pi * p)
        return h
    return filtre_frequentiel(x, H)


def egaliseur(x, bandes):
    """EQ simple à phase nulle. bandes = [{"type": "cloche"|"grave"|"aigu"|"passe_haut"|"passe_bas", "f": Hz,
    "g": dB (cloche, grave, aigu), "q": octaves de largeur (cloche, défaut 1), "front": octaves (défaut 0,5)}]."""
    if not bandes:
        return x

    def H(f):
        lf = np.log2(np.maximum(f, 1e-3))
        g = np.zeros_like(f)
        m = np.ones_like(f)
        for b in bandes:
            l0 = np.log2(b["f"])
            ty = b["type"]
            if ty == "cloche":
                w = b.get("q", 1.0) / 2
                g += b["g"] * np.exp(-0.5 * ((lf - l0) / (w / 1.1774)) ** 2)      # largeur à mi-hauteur = q octaves
            elif ty in ("grave", "aigu"):
                fr = b.get("front", 0.5)
                p = np.clip((lf - (l0 - fr)) / (2 * fr), 0, 1)
                s = 0.5 - 0.5 * np.cos(np.pi * p)
                g += b["g"] * (1 - s if ty == "grave" else s)
            elif ty in ("passe_haut", "passe_bas"):
                fr = b.get("front", 0.5)
                p = np.clip((lf - (l0 - fr)) / (2 * fr), 0, 1)
                s = 0.5 - 0.5 * np.cos(np.pi * p)
                m *= s if ty == "passe_haut" else 1 - s
            else:
                raise ValueError(f"EQ : type inconnu {ty}")
        return m * 10 ** (g / 20)
    return filtre_frequentiel(x, H)


def panner(x, pan):
    """Mono → stéréo à puissance constante, pan dans [-1, 1] (scalaire ou courbe)."""
    a = (np.asarray(pan) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1) * np.sqrt(2)


def balance(st, pan):
    """Stéréo → stéréo : balance à puissance constante (pan 0 = inchangé)."""
    if not pan:
        return st
    a = (pan + 1) * np.pi / 4
    return st * np.array([np.cos(a), np.sin(a)]) * np.sqrt(2)


# ── mesures ────────────────────────────────────────────────────────────────
def mesure(sig):
    """{'I', 'TP', 'LRA'} par loudnorm de ffmpeg sur un signal (n, 2) ou mono (compté en double mono), ou un chemin."""
    if isinstance(sig, (str, Path)):
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(sig), "-af", "loudnorm=print_format=json", "-f", "null", "-"]
        r = subprocess.run(cmd, capture_output=True)
    else:
        s = np.asarray(stereo(sig), dtype=np.float32)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "pipe:0",
                            "-af", "loudnorm=print_format=json", "-f", "null", "-"], input=s.tobytes(), capture_output=True)
    e = r.stderr.decode()
    m = json.loads(e[e.rindex("{"):e.rindex("}") + 1])
    return {"I": float(m["input_i"]), "TP": float(m["input_tp"]), "LRA": float(m["input_lra"])}


def ponderer_k(x):
    """Pondération K (BS.1770) appliquée en fréquence (module seul)."""
    def h(b, a, w):
        z = np.exp(-1j * w)
        return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)

    def H(f):
        w = 2 * np.pi * f / SR
        return np.abs(h([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], w)
                      * h([1, -2, 1], [1, -1.99004745483398, 0.99007225036621], w))
    return filtre_frequentiel(stereo(x), H)


def sonie_courbe(x, fen=3.0, pas=0.1, xk=None):
    """Sonie (LUFS, non fenêtrée) sur des fenêtres de `fen` s qui FINISSENT à t, toutes les `pas` s. fen 3 = S, 0,4 = M."""
    xk = ponderer_k(x) if xk is None else xk
    p = np.sum(xk ** 2, axis=1)
    c = np.concatenate([[0.0], np.cumsum(p)])
    w = int(fen * SR)
    fins = np.arange(int(pas * SR), len(p) + 1, int(pas * SR))
    deb = np.maximum(fins - w, 0)
    m = (c[fins] - c[deb]) / w
    return fins / SR, -0.691 + 10 * np.log10(m + 1e-20)


def sonie(x, a, b, xk=None):
    """LUFS d'un segment [a ; b] (s), pondération K, sans porte : pour comparer deux mots entre eux."""
    xk = ponderer_k(x) if xk is None else xk
    s = xk[int(a * SR):int(b * SR)]
    return float(-0.691 + 10 * np.log10(np.mean(np.sum(s ** 2, axis=1)) + 1e-20))


def crete_os(x, facteur=4):
    """Crête vraie par échantillon (sur-échantillonnage FFT ×facteur), max des canaux : (n,)."""
    x = stereo(x)
    n = len(x)
    M = 1 << (n - 1).bit_length()
    pk = np.zeros(n)
    for c in range(x.shape[1]):
        y = np.fft.irfft(np.fft.rfft(x[:, c], M), M * facteur) * facteur
        pk = np.maximum(pk, np.abs(y[:n * facteur]).reshape(n, facteur).max(axis=1))
    return pk


def crete_vraie_db(x):
    return float(db(crete_os(x).max()))


def profil(x, pas=0.005):
    """(t, dBFS RMS) par pas de `pas` s (t = début de la fenêtre), sur la moyenne des canaux."""
    m = mono(x)
    n = int(round(pas * SR))
    k = len(m) // n
    r = np.sqrt(np.mean(m[:k * n].reshape(k, n) ** 2, axis=1))
    return np.arange(k) * pas, 20 * np.log10(r + 1e-12)


BORDS_OCTAVES = (60, 250, 500, 1000, 2000, 4000, 8000, 16000)


def bandes(x, bords=BORDS_OCTAVES, nfft=1024, pas=240):
    """Énergie par bande (dB, 0 dB = sinus pleine échelle) : t (centres), E (trames, bandes)."""
    m = mono(x)
    w = np.hanning(nfft)
    nb = max(1, (len(m) - nfft) // pas + 1)
    idx = np.arange(nfft)[None, :] + pas * np.arange(nb)[:, None]
    P = np.abs(np.fft.rfft(m[idx] * w, axis=1)) ** 2
    f = np.fft.rfftfreq(nfft, 1 / SR)
    E = np.stack([P[:, (f >= a) & (f < b)].sum(axis=1) for a, b in zip(bords, bords[1:])], axis=1)
    ref = (w.sum() / 2) ** 2 / 2
    return (np.arange(nb) * pas + nfft / 2) / SR, 10 * np.log10(E / ref + 1e-20)


def correlation(st, fen=0.1):
    """Corrélation G/D par fenêtre (s) : (t, r) ; fenêtres quasi muettes ignorées (r = 1)."""
    n = int(fen * SR)
    k = len(st) // n
    g = st[:k * n, 0].reshape(k, n); d = st[:k * n, 1].reshape(k, n)
    num = (g * d).sum(axis=1); den = np.sqrt((g * g).sum(axis=1) * (d * d).sum(axis=1))
    r = np.where(den > 1e-9, num / np.maximum(den, 1e-20), 1.0)
    return np.arange(k) * fen, r


def zeros_exacts(x, a=0.0, b=None):
    """True si le signal est exactement nul (tous canaux) sur [a ; b]."""
    s = x[int(round(a * SR)):None if b is None else int(round(b * SR))]
    return bool(not np.any(s))


# ── dessins (PIL) ──────────────────────────────────────────────────────────
PAPIER = (244, 241, 232); ENCRE = (38, 32, 25); SOLAIRE = (239, 164, 36); TERRA = (192, 69, 44); VERT = (110, 156, 116)
GRIS = (111, 105, 95)


def _stft_db(x, nfft=2048, pas=240):
    x = mono(x)
    w = np.hanning(nfft)
    if len(x) < nfft:
        x = np.concatenate([x, np.zeros(nfft - len(x))])
    nb = max(1, (len(x) - nfft) // pas + 1)
    idx = np.arange(nfft)[None, :] + pas * np.arange(nb)[:, None]
    X = np.fft.rfft(x[idx] * w, axis=1)
    ref = w.sum() / 2
    return 20 * np.log10(np.abs(X) / ref + 1e-12), np.fft.rfftfreq(nfft, 1 / SR), (np.arange(nb) * pas + nfft / 2) / SR


def spectro_img(x, t0, t1, px_par_s=100, haut=300, fmin=40.0, fmax=16000.0, plancher=-110.0, plafond=-10.0):
    """Spectrogramme log-fréquence (dB ABSOLUS : même échelle de couleur pour toutes les pistes comparées)."""
    from PIL import Image
    seg = mono(x)[int(t0 * SR):int(t1 * SR)]
    S, f, t = _stft_db(seg)
    larg = max(1, int(round((t1 - t0) * px_par_s)))
    fy = np.exp(np.linspace(np.log(fmin), np.log(fmax), haut))[::-1]
    fi = np.clip(np.searchsorted(f, fy), 0, len(f) - 1)
    bords = np.searchsorted(t, np.arange(larg + 1) / px_par_s)
    img = np.full((haut, larg), plancher)
    for c in range(larg):
        a = min(bords[c], len(t) - 1); b = min(max(bords[c] + 1, bords[c + 1]), len(t))
        img[:, c] = S[a:b][:, fi].max(axis=0)
    v = np.clip((img - plancher) / (plafond - plancher), 0, 1)[..., None]
    c0 = np.array([20, 16, 12]); c1 = np.array(TERRA); c2 = np.array(SOLAIRE); c3 = np.array(PAPIER)
    rgb = np.where(v < 0.5, c0 + (c1 - c0) * (v / 0.5),
                   np.where(v < 0.8, c1 + (c2 - c1) * ((v - 0.5) / 0.3), c2 + (c3 - c2) * ((v - 0.8) / 0.2)))
    im = Image.fromarray(rgb.astype(np.uint8)).convert("RGB")
    return im, fy


def planche(pistes, t0, t1, png, reperes=(), px_par_s=100, haut_spectro=260, haut_profil=120, pas_profil=0.005,
            plancher_db=-100.0, fmin=40.0, fmax=16000.0, titre=None, haut_onde=0):
    """Planche comparative : pour chaque (titre, signal) un spectrogramme (échelle absolue commune), la forme d'onde
    (si haut_onde > 0 : min/max par colonne, ±1 pleine échelle) et un profil RMS à 5 ms (−100 → 0 dBFS).
    reperes = [(t, "nom")] tracés en traits verts sur toutes les bandes."""
    from PIL import Image, ImageDraw
    larg = int(round((t1 - t0) * px_par_s))
    marge_g, marge_h = 70, 26
    bloc = haut_spectro + (haut_onde + 4 if haut_onde else 0) + haut_profil + 30
    H = marge_h + bloc * len(pistes) + 24
    im = Image.new("RGB", (larg + marge_g + 10, H), PAPIER)
    d = ImageDraw.Draw(im)
    if titre:
        d.text((marge_g, 6), titre, fill=ENCRE)
    for k, (nom, x) in enumerate(pistes):
        y0 = marge_h + k * bloc
        d.text((marge_g, y0 + 2), nom, fill=ENCRE)
        sp, fy = spectro_img(x, t0, t1, px_par_s, haut_spectro, fmin, fmax)
        im.paste(sp, (marge_g, y0 + 16))
        for hz in (100, 300, 1000, 3000, 8000):
            yy = y0 + 16 + int(np.interp(np.log(hz), np.log(fy[::-1]), np.arange(haut_spectro)[::-1]))
            d.line([(marge_g - 6, yy), (marge_g, yy)], fill=GRIS)
            d.text((4, yy - 6), f"{hz if hz < 1000 else str(hz // 1000) + 'k'} Hz", fill=GRIS)
        yp = y0 + 16 + haut_spectro + 4
        if haut_onde:                                    # forme d'onde : min/max de chaque colonne de pixels
            d.rectangle([marge_g, yp, marge_g + larg, yp + haut_onde], outline=GRIS)
            m_ = mono(np.asarray(x))[int(t0 * SR):int(t1 * SR)]
            bords_ = np.linspace(0, len(m_), larg + 1).astype(int)
            mil = yp + haut_onde / 2
            for c in range(larg):
                seg_ = m_[bords_[c]:max(bords_[c + 1], bords_[c] + 1)]
                if len(seg_):
                    d.line([(marge_g + c, mil - float(np.clip(seg_.max(), -1, 1)) * haut_onde / 2),
                            (marge_g + c, mil - float(np.clip(seg_.min(), -1, 1)) * haut_onde / 2)], fill=ENCRE)
            d.text((4, yp + 2), "onde", fill=GRIS)
            yp += haut_onde + 4
        # profil
        d.rectangle([marge_g, yp, marge_g + larg, yp + haut_profil], outline=GRIS)
        for lv in (-20, -40, -60, -80):
            yy = yp + int((-lv) / -plancher_db * haut_profil)
            d.line([(marge_g, yy), (marge_g + larg, yy)], fill=(225, 220, 208))
            d.text((20, yy - 6), f"{lv}", fill=GRIS)
        tt, pp = profil(np.asarray(x)[int(t0 * SR):int(t1 * SR)], pas_profil)
        pts = [(marge_g + int(tv * px_par_s), yp + int(np.clip(-pv / -plancher_db, 0, 1) * haut_profil)) for tv, pv in zip(tt, pp)]
        if len(pts) > 1:
            d.line(pts, fill=ENCRE, width=1)
        for t, lab in reperes:
            if t0 <= t <= t1:
                xx = marge_g + int((t - t0) * px_par_s)
                d.line([(xx, y0 + 16), (xx, yp + haut_profil)], fill=VERT, width=1)
                if k == 0:
                    d.text((xx + 2, y0 + 16), str(lab), fill=PAPIER)
    ybas = H - 20
    for s in range(int(np.ceil(t0)), int(t1) + 1):
        xx = marge_g + int((s - t0) * px_par_s)
        d.line([(xx, ybas - 4), (xx, ybas)], fill=ENCRE)
        d.text((xx + 2, ybas + 2), f"{s}s", fill=ENCRE)
    Path(png).parent.mkdir(parents=True, exist_ok=True)
    im.save(png)
    return Path(png)


def courbe_png(series, png, t0, t1, ymin, ymax, px_par_s=20, haut=300, reperes=(), titre=None, unite=""):
    """Courbes superposées (sonie, réduction du limiteur…) : series = [(nom, t, y, (r, g, b))]."""
    from PIL import Image, ImageDraw
    larg = int(round((t1 - t0) * px_par_s))
    mg, mh = 60, 24
    im = Image.new("RGB", (larg + mg + 150, haut + mh + 30), PAPIER)
    d = ImageDraw.Draw(im)
    if titre:
        d.text((mg, 4), titre, fill=ENCRE)
    d.rectangle([mg, mh, mg + larg, mh + haut], outline=GRIS)
    pas = 5 if ymax - ymin > 20 else 1
    for lv in np.arange(np.ceil(ymin / pas) * pas, ymax + 1e-9, pas):
        yy = mh + int((ymax - lv) / (ymax - ymin) * haut)
        d.line([(mg, yy), (mg + larg, yy)], fill=(225, 220, 208))
        d.text((6, yy - 6), f"{lv:g}{unite}", fill=GRIS)
    for t, lab in reperes:
        if t0 <= t <= t1:
            xx = mg + int((t - t0) * px_par_s)
            d.line([(xx, mh), (xx, mh + haut)], fill=VERT)
            d.text((xx + 2, mh + 2), str(lab), fill=VERT)
    for k, (nom, t, y, col) in enumerate(series):
        m = (t >= t0) & (t <= t1)
        pts = [(mg + int((a - t0) * px_par_s), mh + int(np.clip((ymax - b) / (ymax - ymin), 0, 1) * haut)) for a, b in zip(t[m], y[m])]
        if len(pts) > 1:
            d.line(pts, fill=col, width=2)
        d.text((mg + larg + 8, mh + 14 * k), nom, fill=col)
    for s in range(int(np.ceil(t0)), int(t1) + 1, 5 if t1 - t0 > 20 else 1):
        xx = mg + int((s - t0) * px_par_s)
        d.text((xx, mh + haut + 4), f"{s}s", fill=ENCRE)
    Path(png).parent.mkdir(parents=True, exist_ok=True)
    im.save(png)
    return Path(png)


# ── dynamique : présence d'une voix, limiteur à crête vraie ────────────────
def presence(voix, seuil_db=-40.0, anticipation=0.080, tenue=0.120, fen=0.010):
    """Présence (0/1, cadence 1 ms) d'une voix : RMS glissant de fen s au-dessus du seuil, avancée de `anticipation`,
    tenue `tenue` après la fin. Renvoie (t_ms (m,), p (m,)) ; le lissage est fait par gain_suiveur()."""
    v = mono(voix)
    n = len(v)
    w = int(fen * SR)
    c = np.concatenate([[0.0], np.cumsum(v * v)])
    i = np.arange(n)
    rms = np.sqrt(np.maximum(c[np.clip(i + w // 2, 0, n)] - c[np.clip(i - w // 2, 0, n)], 0) / w)
    k = SR // 1000
    m = n // k
    dessus = (20 * np.log10(rms[:m * k] + 1e-12) > seuil_db).reshape(m, k).any(axis=1)
    la, te = int(anticipation * 1000), int(tenue * 1000)
    cs = np.concatenate([[0], np.cumsum(dessus)])
    a = np.arange(m)
    anticipe = (cs[np.clip(a + la + 1, 0, m)] - cs[a]) > 0
    cs2 = np.concatenate([[0], np.cumsum(anticipe)])
    tenu = (cs2[a + 1] - cs2[np.clip(a - te, 0, m)]) > 0
    return (a + 0.5) / 1000, tenu.astype(float)


def gain_suiveur(t_ms, cible_db, n, attaque=0.030, relache=0.250):
    """Suit une cible en dB (cadence 1 ms) avec une attaque (descente) et une relâche (remontée) à un pôle ; renvoie la
    courbe de gain LINÉAIRE à la cadence audio (n,)."""
    ka, kr = 1 - np.exp(-1 / (attaque * 1000)), 1 - np.exp(-1 / (relache * 1000))
    g = np.zeros(len(cible_db)); x = 0.0
    for i, c in enumerate(cible_db):
        x += (c - x) * (ka if c < x else kr)
        g[i] = x
    return gain(np.interp(np.arange(n) / SR, t_ms, g))


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


def gain_limiteur(x, plafond_db=-1.7, anticipation=0.0015, relache=0.060):
    """Limiteur à crête vraie (sur-échantillonnage ×4), anticipation et relâche exponentielle (le même que son/mix.py) :
    renvoie (courbe de gain (n,), réduction max en dB, négative)."""
    c = gain(plafond_db)
    r = np.minimum(1.0, c / np.maximum(crete_os(x), 1e-12))
    if r.min() >= 1:
        return np.ones(len(x)), 0.0
    La = int(anticipation * SR); w = 2 * La + 1
    m = filtre_min(r, w)
    cs = np.concatenate([[0.0], np.cumsum(np.concatenate([np.ones(La), m, np.ones(La)]))])
    g = (cs[w:] - cs[:-w]) / w
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
    return out, float(20 * np.log10(out.min()))


def masteriser(somme, lufs=-14.0, plafond_db=-1.7, tolerance=0.04, anticipation=0.0015, relache=0.060, G=None):
    """Un gain unique vers `lufs` intégrés puis le limiteur à crête vraie ; itère sur le gain (le limiteur retire un
    peu de sonie). G imposé : aucune itération. Renvoie (mix, G, courbe du limiteur, réduction max)."""
    iteratif = G is None
    if iteratif:
        G = lufs - mesure(somme)["I"]
    for _ in range(6):
        x = somme * gain(G)
        g_lim, red = gain_limiteur(x, plafond_db, anticipation, relache)
        y = x * g_lim[:, None]
        m = mesure(y)
        if not iteratif or abs(m["I"] - lufs) <= tolerance:
            break
        G += lufs - m["I"]
    return y, float(G), g_lim, red
