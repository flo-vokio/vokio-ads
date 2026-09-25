#!/usr/bin/env python3
"""Doublage du message d'accueil du répondeur (25/09, demande de Florian).

    python3 sonoriser.py <voix>     voix = messagerie-marine (RETENUE le 25/09) | messagerie-jade | yariq-v2 | yariq | maxime | sebastien (prises dans assets/voix/)

Une seule piste, assets/voix/piste.wav, de la durée du film : le message
tel que synthétisé, sans effet (le filtre « ligne téléphonique » sonnait faux,
retiré le 25/09 à la demande de Florian), qui commence à DEBUT, puis le bip
(1 kHz) calé sur le trait #bip-ton. Les mots du message s'affichent à
l'instant où la voix les dit : les horodatages ElevenLabs sont recopiés dans
index.html entre les marqueurs MOTS-VOIX, jamais saisis à la main.
Pas de musique : Florian la pose dans TikTok / Instagram.
"""
import json, re, subprocess, sys
from pathlib import Path
ICI = Path(__file__).parent
V = ICI / "assets" / "voix"
# 25/09 : voix « Marine » retenue (5,25 s) ⇒ voix avancée à 3,75 s et bip décalé à 9,3 s
# (#bip-l, #bip-ton dans index.html suivent) ; la boîte sort toujours à 10,1 s.
DUREE, DEBUT, BIP, BIP_D = 27.4, 3.75, 9.3, 0.34
voix = sys.argv[1]
mots = json.loads((V / f"brut-{voix}.json").read_text())["mots"]
fin = DEBUT + mots[-1]["fin"]
assert fin + 0.3 < BIP, f"la voix ({fin:.2f} s) déborde sur le bip ({BIP} s)"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
    "-i", str(V / f"brut-{voix}.mp3"),
    "-f", "lavfi", "-i", f"sine=frequency=1000:duration={BIP_D}:sample_rate=44100",
    "-filter_complex",
    f"[0:a]adelay={int(DEBUT*1000)}:all=1,apad[v];"
    f"[1:a]volume=0.35,afade=t=in:d=0.01,afade=t=out:st={BIP_D-0.02}:d=0.02,adelay={int(BIP*1000)}:all=1,apad[b];"
    f"[v][b]amix=inputs=2:normalize=0,atrim=0:{DUREE},loudnorm=I=-16:TP=-1.5:LRA=11[o]",
    "-map", "[o]", "-ac", "2", "-ar", "44100", str(V / "piste.wav")], check=True)
# les instants d'apparition, un par mot affiché (« et » compris : 15 mots)
t = [round(DEBUT + m["debut"], 3) for m in mots]
html = (ICI / "index.html").read_text()
bloc = (f"/* MOTS-VOIX (généré par sonoriser.py, voix {voix}) */\n"
        f"  const MOTS_VOIX = {json.dumps(t)};\n"
        f"  // « et » ne se disent pas : le guillemet ouvrant sort avec le premier mot, le fermant avec le dernier\n"
        f"  let iv = 0;\n"
        f"  document.querySelectorAll(\"#boite-dit .d\").forEach(el => {{\n"
        f"    const dit = /[\\p{{L}}]/u.test(el.textContent);\n"
        f"    const t = MOTS_VOIX[Math.min(iv, MOTS_VOIX.length - 1)];\n"
        f"    if (dit) iv++;\n"
        f"    tl.fromTo(el, {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.2, ease: \"power2.out\" }}, t);\n"
        f"  }});\n"
        f"  /* fin MOTS-VOIX */")
avant = html
html = re.sub(r"/\* MOTS-VOIX.*?/\* fin MOTS-VOIX \*/", lambda _: bloc, html, flags=re.S)
if html == avant:
    ligne = re.search(r'  tl\.fromTo\("#boite-dit \.d".*\n', html).group(0)
    html = html.replace(ligne, "  " + bloc + "\n")
(ICI / "index.html").write_text(html)
print(f"{voix} : message {DEBUT:.2f} → {fin:.2f} s, bip {BIP} s, {len(t)} mots calés")
