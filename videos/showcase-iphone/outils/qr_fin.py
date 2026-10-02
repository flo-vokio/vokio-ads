#!/usr/bin/env python3
"""Pose un QR code sur le carton de fin d'un film déjà rendu, et prolonge le dernier plan pour laisser le temps de scanner.

    python3 outils/qr_fin.py <film.mp4> <qr.png> -o <sortie.mp4> [--debut 48.0] [--fondu 0.5] [--prolonger 6]
        [--x droite|<px>] [--y bas|<px>] [--marge 96]

Usage prévu : version TÉLÉVISION d'une pub YouTube (on ne clique pas sur une télé, on scanne avec son téléphone).
Sur mobile un QR ne sert à rien : cette version va dans une campagne réservée aux écrans de télévision.

- Le film n'est jamais coupé ni recomposé : on ajoute seulement le QR et un arrêt sur la dernière image (`tpad` clone),
  le son est prolongé par du silence (`apad`).
- `--debut` : instant d'apparition du QR (s), à caler sur l'arrivée de l'offre (16:9 du showcase : 48,0 s).
- Position par défaut : coin bas droit, à `--marge` px des bords (96 px = zone sûre titre 5 % en 1080p).
- Le QR se fabrique à part, aux couleurs du film, en modules entiers (ex. 37 modules × 6 px = 222 px) :
      node -e "require('qrcode').toFile('qr.png', '<url avec utm>', {errorCorrectionLevel:'M', margin:0, scale:6,
               color:{dark:'#271d17ff', light:'#f4efe8ff'}}, e => { if (e) throw e })"
  (paquet npm `qrcode`, à installer dans un dossier jetable ; la marge blanche est le fond crème du film lui-même.)
- Contrôle obligatoire après rendu : décoder le QR sur une image EXTRAITE de la sortie (compression comprise),
  pas sur le PNG.
"""
import argparse, json, subprocess, sys


def duree(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", f]).decode().strip())


def taille(f):
    w, h = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", f]).decode().strip().split(",")
    return int(w), int(h)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("film"); p.add_argument("qr"); p.add_argument("-o", "--sortie", required=True)
    p.add_argument("--debut", type=float, default=48.0); p.add_argument("--fondu", type=float, default=0.5)
    p.add_argument("--prolonger", type=float, default=6.0)
    p.add_argument("--x", default="droite"); p.add_argument("--y", default="bas"); p.add_argument("--marge", type=int, default=96)
    a = p.parse_args()

    W, H = taille(a.film); qw, qh = taille(a.qr); d = duree(a.film)
    x = W - a.marge - qw if a.x == "droite" else int(a.x)
    y = H - a.marge - qh if a.y == "bas" else int(a.y)
    if not (0 <= x <= W - qw and 0 <= y <= H - qh):
        sys.exit(f"QR hors cadre : {x},{y} pour {qw}×{qh} dans {W}×{H}")
    if a.debut >= d:
        sys.exit(f"--debut {a.debut} au-delà du film ({d:.2f} s)")

    filtre = (f"[0:v]tpad=stop_mode=clone:stop_duration={a.prolonger}[v];"
              f"[1:v]format=rgba,fade=in:st={a.debut}:d={a.fondu}:alpha=1[q];"
              f"[v][q]overlay={x}:{y}:shortest=0:eof_action=repeat,format=yuv420p[vo];"
              f"[0:a]apad=pad_dur={a.prolonger}[ao]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.film,
           "-loop", "1", "-t", f"{d + a.prolonger:.3f}", "-i", a.qr,
           "-filter_complex", filtre, "-map", "[vo]", "-map", "[ao]",
           "-c:v", "libx264", "-profile:v", "high", "-crf", "16", "-preset", "slow", "-r", "30",
           "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
           "-t", f"{d + a.prolonger:.3f}", a.sortie]
    subprocess.run(cmd, check=True)
    recette = {"film": a.film, "qr": a.qr, "debut_s": a.debut, "fondu_s": a.fondu, "prolonger_s": a.prolonger,
               "position_px": [x, y], "taille_qr_px": [qw, qh], "duree_s": round(duree(a.sortie), 3)}
    json.dump(recette, open(a.sortie.rsplit(".", 1)[0] + ".json", "w"), ensure_ascii=False, indent=1)
    print("→", a.sortie, json.dumps(recette, ensure_ascii=False))


if __name__ == "__main__":
    main()
