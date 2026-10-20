#!/usr/bin/env python3
"""Accroche « Votre téléphone sonne. » (1,6 s) collée devant la pub 24 h chez Vokio doublée (20/10/2026).

    /root/.pwtest/bin/python /opt/vokio-ads/videos/ux-retravail/24h-chez-vokio/accroche/fabriquer.py [source.mp4]

Source par défaut : /root/vokio-uploads/videos/24h/24h-chez-vokio-9x16-voix.mp4 (la vidéo publiée, jamais modifiée).
Le film perd ses 0,3 premières secondes (fond vide, avant la voix). Sortie : rendus/ à côté de ce script : accroche.mp4 (seule) et 24h-chez-vokio-9x16-voix-accroche.mp4 (accroche + film).
Image : index.html filmé à 30 i/s par window.poser(t). Son : sonnerie électronique neutre synthétisée ici (pas de
sonnerie de marque), seule sur la piste ; la musique et la voix démarrent à la coupe.
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
DUREE, IPS, FE = 1.6, 30, 48000
SONNERIES = [(0.0, 0.62), (0.82, 1.6)]     # mêmes bornes que index.html
ROGNE = 0.3   # début du film retiré : 0,3 s de fond vide avant l'horloge (la voix démarre à 0,54 s, intacte)
CHROMIUM = "/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").is_file() else None


def sonnerie():
    """Trille électronique : deux notes qui alternent 24 fois par seconde, harmoniques douces, attaque nette."""
    t = np.arange(int(DUREE * FE)) / FE
    son = np.zeros_like(t)
    for a, b in SONNERIES:
        m = (t >= a) & (t < b)
        u = t[m] - a
        f = np.where((np.floor(u * 24) % 2) == 0, 1320.0, 1660.0)
        phase = 2 * np.pi * np.cumsum(f) / FE
        onde = np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase)
        env = np.minimum(1, u / 0.008) * np.minimum(1, (b - t[m]) / 0.015)
        son[m] = onde * env
    son *= 10 ** (-19 / 20) / np.sqrt(np.mean(son[son != 0] ** 2))   # ≈ -19 dBFS efficace, au niveau du film (-16)
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
                        f"[1:v]trim=start={ROGNE},setpts=PTS-STARTPTS,fps=30,format=yuv420p,setsar=1[v1];[0:v]setsar=1[v0];"
                        f"[1:a]atrim=start={ROGNE},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,aresample=48000,aformat=channel_layouts=stereo[a1];[0:a]aformat=channel_layouts=stereo[a0];"
                        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(sortie)],
                       check=True)
    print(sortie)


if __name__ == "__main__":
    main()
