#!/usr/bin/env python3
"""Outils de mesure de la variante « musique » : sonie court terme (ebur128), spectrogramme regardable, chroma, tempo.

    python3 son/riche-musique/mesures.py court  <wav>           courbe S (3 s) et M (0,4 s) par 0,1 s, maxima par scène
    python3 son/riche-musique/mesures.py spectro <wav> <png> [t0 t1] spectrogramme log-fréquence, repères du film
    python3 son/riche-musique/mesures.py chroma <wav> [t0 t1]    classes de hauteur (tonalité)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
SON = ICI.parent
DON = SON.parent / "donnees"
sys.path.insert(0, str(SON))
import labo  # noqa: E402

SR = labo.SR
NOMS = ["do", "do#", "ré", "ré#", "mi", "fa", "fa#", "sol", "sol#", "la", "la#", "si"]


def court_terme(chemin):
    """ebur128 de ffmpeg : liste (t, M, S) toutes les 0,1 s ; t = fin de la fenêtre."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(chemin), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    pts = []
    for m in re.finditer(r"t:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.]+|-inf)\s+S:\s*(-?[\d.]+|-inf)", r.stderr):
        t, M, S = m.groups()
        pts.append((float(t), float(M) if M != "-inf" else -120.0, float(S) if S != "-inf" else -120.0))
    I = re.search(r"Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS", r.stderr)
    tp = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return np.array(pts), (float(I.group(1)) if I else None), (float(tp.group(1)) if tp else None)


def scenes():
    return json.loads((DON / "scenes.json").read_text())


def rapport_court(chemin):
    pts, I, tp = court_terme(chemin)
    out = {"integre_lufs": I, "crete_vraie_dbtp": tp, "scenes": {}}
    for nom, s in scenes().items():
        m = (pts[:, 0] > s["debut"] + 0.05) & (pts[:, 0] <= s["fin"] + 0.05)
        if m.any():
            k = np.argmax(pts[m, 2])
            out["scenes"][nom] = {"S_max": round(float(pts[m, 2][k]), 1), "t_S_max": round(float(pts[m, 0][k]), 1),
                                  "M_max": round(float(pts[m, 1].max()), 1), "S_median": round(float(np.median(pts[m, 2])), 1)}
    k = np.argmax(pts[:, 2])
    out["S_max_film"] = {"t": round(float(pts[k, 0]), 1), "S": round(float(pts[k, 2]), 1)}
    return out, pts


def stft_db(x, nfft=4096, pas=480):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim > 1:
        x = x.mean(axis=1)
    w = np.hanning(nfft)
    nb = max(1, (len(x) - nfft) // pas + 1)
    idx = np.arange(nfft)[None, :] + pas * np.arange(nb)[:, None]
    X = np.fft.rfft(x[idx] * w, axis=1)
    return 20 * np.log10(np.abs(X) + 1e-9), np.fft.rfftfreq(nfft, 1 / SR), (np.arange(nb) * pas + nfft / 2) / SR


def spectro(chemin_ou_sig, png, t0=0.0, t1=None, fmin=40.0, fmax=16000.0, haut=520, px_par_s=40, reperes=True,
            titre=None, plancher=-100.0):
    """Spectrogramme log-fréquence en PNG (PIL), palette encre → solaire, repères du film en traits verticaux."""
    from PIL import Image, ImageDraw
    x = labo.lire(chemin_ou_sig) if isinstance(chemin_ou_sig, (str, Path)) else np.asarray(chemin_ou_sig)
    t1 = t1 or len(x) / SR
    seg = x[int(t0 * SR):int(t1 * SR)]
    S, f, t = stft_db(seg)
    S -= S.max()
    larg = int((t1 - t0) * px_par_s)
    lf = np.log(np.linspace(np.log(fmin), np.log(fmax), haut)[::-1])
    fy = np.exp(np.linspace(np.log(fmin), np.log(fmax), haut))[::-1]
    fi = np.clip(np.searchsorted(f, fy), 0, len(f) - 1)
    # chaque colonne de pixels prend la trame la plus FORTE de son intervalle (aucune colonne vide, aucune crête perdue)
    bords = np.searchsorted(t, (np.arange(larg + 1)) / px_par_s)
    img = np.full((haut, larg), plancher)
    for c in range(larg):
        a, b = bords[c], max(bords[c] + 1, bords[c + 1])
        a = min(a, len(t) - 1); b = min(b, len(t))
        img[:, c] = S[a:b][:, fi].max(axis=0)
    v = np.clip((img - plancher) / -plancher, 0, 1)
    # palette : papier sombre → encre → solaire
    c0 = np.array([38, 32, 25]); c1 = np.array([192, 69, 44]); c2 = np.array([239, 164, 36]); c3 = np.array([244, 241, 232])
    v3 = v[..., None]
    rgb = np.where(v3 < 0.5, c0 + (c1 - c0) * (v3 / 0.5), np.where(v3 < 0.8, c1 + (c2 - c1) * ((v3 - 0.5) / 0.3),
                                                                  c2 + (c3 - c2) * ((v3 - 0.8) / 0.2)))
    im = Image.fromarray(rgb.astype(np.uint8)).convert("RGB")
    im = im.crop((0, 0, larg, haut))
    d = ImageDraw.Draw(im)
    for hz in (100, 300, 1000, 3000, 10000):
        y = int(np.interp(np.log(hz), np.log(fy[::-1]), np.arange(haut)[::-1]))
        d.line([(0, y), (8, y)], fill=(200, 200, 200)); d.text((10, y - 6), f"{hz} Hz", fill=(200, 200, 200))
    if reperes:
        ev = json.loads((DON / "evenements.json").read_text())
        for nom in ("decroche", "contact_neuf", "contact_dix", "contact_onze", "contact_retour_neuf", "ecriture_debut",
                    "resolution_confirmation", "raccroche", "bulle_et_vibreur", "signature_la", "signature_re_contact", "fin"):
            e = ev[nom]["t"]
            e = e[0] if isinstance(e, list) else e
            if t0 <= e <= t1:
                xx = int((e - t0) * px_par_s)
                d.line([(xx, 0), (xx, 14)], fill=(110, 156, 116), width=2)
        for s in range(int(np.ceil(t0)), int(t1) + 1):
            xx = int((s - t0) * px_par_s)
            d.line([(xx, haut - 6), (xx, haut)], fill=(200, 200, 200))
            if s % 5 == 0:
                d.text((xx + 2, haut - 18), f"{s}s", fill=(200, 200, 200))
    if titre:
        d.text((40, 4), titre, fill=(244, 241, 232))
    im.save(png)
    return png


def chroma(x, t0=0.0, t1=None, fmin=60.0, fmax=2000.0):
    x = np.asarray(x)
    if x.ndim > 1:
        x = x.mean(axis=1)
    t1 = t1 or len(x) / SR
    nfft = 32768 if fmin < 100 else 8192          # basse : 1,5 Hz par case (ré2 73,4 Hz tombe entre do# et ré# à 8 192)
    S, f, _ = stft_db(x[int(t0 * SR):int(t1 * SR)], nfft=nfft, pas=2048)
    P = (10 ** (S / 20)) ** 2
    m = (f >= fmin) & (f <= fmax)
    classes = np.round(12 * np.log2(f[m] / 261.6256)).astype(int) % 12
    c = np.zeros(12)
    np.add.at(c, classes, P[:, m].sum(axis=0))
    return c / c.max()


def tonalite(c):
    """Corrélation aux profils de Krumhansl (majeur, mineur) : [(nom, r)] trié."""
    maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    mi = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    res = []
    for k in range(12):
        res.append((f"{NOMS[k]} majeur", float(np.corrcoef(np.roll(maj, k), c)[0, 1])))
        res.append((f"{NOMS[k]} mineur", float(np.corrcoef(np.roll(mi, k), c)[0, 1])))
    return sorted(res, key=lambda r: -r[1])


def enveloppe_attaques(x, pas=240):
    """Flux spectral (demi-onde) à 200 Hz de cadence : pour le tempo et les attaques."""
    x = np.asarray(x)
    if x.ndim > 1:
        x = x.mean(axis=1)
    S, f, t = stft_db(x, nfft=2048, pas=pas)
    fl = np.maximum(np.diff(S, axis=0), 0).sum(axis=1)
    return fl, t[1:]


def tempo(x, bpm_min=60, bpm_max=180):
    fl, t = enveloppe_attaques(x)
    fl = fl - fl.mean()
    ac = np.correlate(fl, fl, "full")[len(fl) - 1:]
    cad = 1 / (t[1] - t[0])
    lags = np.arange(len(ac)) / cad
    m = (lags >= 60 / bpm_max) & (lags <= 60 / bpm_min)
    k = np.argmax(ac[m])
    return 60 / lags[m][k]


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "court":
        r, pts = rapport_court(sys.argv[2])
        print(json.dumps(r, ensure_ascii=False, indent=1))
    elif cmd == "spectro":
        a = [float(v) for v in sys.argv[4:6]]
        spectro(sys.argv[2], sys.argv[3], *a)
    elif cmd == "chroma":
        x = labo.lire(sys.argv[2])
        a = [float(v) for v in sys.argv[3:5]]
        c = chroma(x, *a)
        print(" ".join(f"{n}:{v:.2f}" for n, v in zip(NOMS, c)))
        print(tonalite(c)[:4])
