#!/usr/bin/env python3
"""Une version complète de la pub par voix off (même image, même musique ; le minutage se recale sur chaque voix).
  python3 versions_voix.py clemence:LFo5X4P9PhYaOLBA9Hyh hugo:DbbNuBL7lf62XwY7arQb …
Sorties : /root/vokio-uploads/videos/pub-metiers/versions-voix/meme-assistante-<nom>.mp4 (+ planche de contrôle).
"""
import json, os, subprocess, sys
ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = "/root/vokio-uploads/videos/pub-metiers/versions-voix"
os.makedirs(SORTIE, exist_ok=True)
CTRL = r'''
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":1080,"height":1920})
    pg.goto("file://%s/index.html")
    for _ in range(100):
        if pg.evaluate("!!(window.__pub&&__pub.pret)"): break
        pg.wait_for_timeout(100)
    print(pg.evaluate("JSON.stringify(__pub.erreurs)")); b.close()
''' % ICI
for arg in sys.argv[1:]:
    nom, vid = arg.split(":")
    env = dict(os.environ, VOIX=vid)
    run = lambda *c, **k: subprocess.run(list(c), cwd=ICI, check=True, **k)
    run("python3", "son/voix.py", env=env, stdout=subprocess.DEVNULL)
    out = subprocess.run(["python3", "son/monter.py"], cwd=ICI, check=True, capture_output=True, text=True).stdout
    run("python3", "construire.py", stdout=subprocess.DEVNULL)
    err = subprocess.run(["/root/.pwtest/bin/python3", "-c", CTRL], capture_output=True, text=True, timeout=120).stdout.strip()
    if err != "[]":
        print(f"✗ {nom} : erreurs internes {err}"); continue
    mp4 = f"{SORTIE}/meme-assistante-{nom}.mp4"
    subprocess.run(["python3", "outils/rendre.py", ICI, "-o", mp4, "--son", f"{ICI}/son/mix.wav"],
                   cwd="/opt/vokio-ads/videos/showcase-iphone", check=True, capture_output=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4], capture_output=True, text=True).stdout.strip()
    print(f"✓ {nom} : {float(dur):.1f} s · {out.splitlines()[1]}", flush=True)
