#!/usr/bin/env python3
"""Accroche « Votre téléphone sonne. » (1,9 s) enchaînée en fondu devant la pub 24 h chez Vokio doublée (20/10/2026).

    /root/.pwtest/bin/python /opt/vokio-ads/videos/ux-retravail/24h-chez-vokio/accroche/fabriquer.py [source.mp4]

Source par défaut : /root/vokio-uploads/videos/24h/24h-chez-vokio-9x16-voix.mp4 (la vidéo publiée, jamais modifiée).
Fondu enchaîné image ET son de 0,4 s entre l'accroche et le film (v1 coupait sec, jugé brutal par Florian le 20/10). Sortie : rendus/ à côté de ce script : accroche.mp4 (seule) et 24h-chez-vokio-9x16-voix-accroche.mp4 (accroche + film).
Image : index.html filmé à 30 i/s par window.poser(t). Son : petit motif de marimba synthétisé ici (notes douces qui
s'éteignent seules ; la trille électronique de la v1 était désagréable), seul sur la piste jusqu'au fondu.
"""
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

ICI = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1] if len(sys.argv) > 1 else "/root/vokio-uploads/videos/24h/24h-chez-vokio-9x16-voix.mp4")
RENDUS = ICI / "rendus"
DUREE, IPS, FE = 1.9, 30, 48000
SONNERIES = [0.0, 0.8]     # départ de chaque sonnerie (vibrations de index.html : 0-0,55 et 0,8-1,2)
FONDU = 0.4   # fondu enchaîné sur les 0,4 dernières secondes de l'accroche ; la voix du film démarre à 0,54 s, après
CHROMIUM = "/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").is_file() else None


def sonnerie():
    """Motif de marimba : quatre notes montantes (sol, si, ré, sol), attaque feutrée, extinction naturelle, léger écho."""
    t = np.arange(int(DUREE * FE)) / FE
    son = np.zeros_like(t)
    for a in SONNERIES:
        for k, f in enumerate((784.0, 987.8, 1174.7, 1568.0)):
            u = t - (a + 0.11 * k)
            m = u >= 0
            env = np.minimum(1, u[m] / 0.004)
            son[m] += env * (np.sin(2 * np.pi * f * u[m]) * np.exp(-u[m] / 0.16)
                             + 0.18 * np.sin(2 * np.pi * 4 * f * u[m]) * np.exp(-u[m] / 0.03)) * (0.9 if k < 3 else 1.0)
    d = int(0.07 * FE)
    son[d:] += 0.18 * son[:-d]
    son *= 10 ** (-23 / 20) / np.sqrt(np.mean(son[np.abs(son) > 1e-3] ** 2))   # ≈ -23 dBFS efficace, sous le film (-16)
    return np.clip(son, -0.98, 0.98)


def main():
    RENDUS.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir="/dev/shm") as d:
        d = Path(d)
        with sync_playwright() as p:
            nav = p.chromium.launch(executable_path=CHROMIUM, args=["--disable-gpu", "--font-render-hinting=none"])
            pg = nav.new_page(viewport={"width": 1080, "height": 1920})
            pg.goto((ICI / "index.html").as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(300)
            for i in range(round(DUREE * IPS)):
                pg.evaluate(f"window.poser({i / IPS})")
                pg.screenshot(path=str(d / f"{i:04d}.png"))
            nav.close()
        s = (np.repeat(sonnerie()[:, None], 2, axis=1) * 32767).astype("<i2")
        with wave.open(str(d / "sonnerie.wav"), "wb") as w:
            w.setnchannels(2), w.setsampwidth(2), w.setframerate(FE), w.writeframes(s.tobytes())
        acc = RENDUS / "accroche.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(IPS), "-i", str(d / "%04d.png"),
                        "-i", str(d / "sonnerie.wav"), "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                        "-pix_fmt", "yuv420p", "-r", str(IPS), "-c:a", "aac", "-b:a", "256k", "-ar", str(FE),
                        "-ac", "2", "-shortest", str(acc)], check=True)
        sortie = RENDUS / "24h-chez-vokio-9x16-voix-accroche.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(acc), "-i", str(SOURCE), "-filter_complex",
                        "[1:v]fps=30,format=yuv420p,setsar=1,settb=1/30[v1];[0:v]fps=30,format=yuv420p,setsar=1,settb=1/30[v0];"
                        f"[v0][v1]xfade=transition=fade:duration={FONDU}:offset={DUREE - FONDU:.2f}[v];"
                        "[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];[0:a]aformat=channel_layouts=stereo[a0];"
                        f"[a0][a1]acrossfade=d={FONDU}:c1=qsin:c2=qsin[a]",
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(sortie)],
                       check=True)
    print(sortie)


if __name__ == "__main__":
    main()
