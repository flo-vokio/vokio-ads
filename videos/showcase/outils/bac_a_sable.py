#!/usr/bin/env python3
"""Bac à sable du FILM D'AVANT une insertion de temps, et preuve couche par couche de la musique refaite.

Pourquoi : pour prouver qu'une insertion (son/dialogue.json « insertions ») n'a changé la musique que là où elle le devait,
on refait la musique du film d'avant AVEC LE CODE ACTUEL (elle doit redonner à l'octet le stem validé : non-régression),
puis on compare ses couches et ses courbes de gain à celles du film actuel, l'ancien décalé de la règle (outils/chronologie.py).
Deux agents l'avaient monté à la main le 28/09 (l'échange du prénom) : voici le geste en trois commandes.

    python3 outils/bac_a_sable.py monter --commit a6d3d8e --dossier /dev/shm/x/base
          copie le code actuel du projet son (sans les sorties lourdes : stems, mix, prises ElevenLabs Music, rendus ; le
          cache des bruitages son/cache est copié, aucun appel payant), pose les DONNÉES du commit (showcase/donnees,
          showcase-iphone/donnees, son/dialogue.json), refait son/dialogue.wav du film d'avant (son/dialogue.py --avant) et
          pointe dialogue.json « fichier » dessus (sinon mix.py lirait le dialogue du film actuel)
    python3 outils/bac_a_sable.py musique --dossier /dev/shm/x/base --couches /dev/shm/x/base-couches
          stems_amont.py --seulement musique dans le bac à sable (≈ 2 min) : musique.wav + couches + gains.npz ; imprime le md5
          (à comparer au stem validé, ex. $UP/versions-47s/stems-amont-musique-47s.wav : 6ff25d2c…)
    python3 outils/bac_a_sable.py stems --dossier /dev/shm/x/base --video $UP/versions-47s/le-point-sur-le-i-final.mp4
          (28/09, mixeur final) stems_amont.py COMPLET dans le bac à sable (≈ 5 min, les 10 stems amont du film d'avant), la
          plume lisant l'encre dans --video (la vidéo du film d'avant : le 9:16 de 47 s ; sans --video, celle de la variante,
          donc du film actuel : faux)
    python3 outils/bac_a_sable.py mixer --dossier /dev/shm/x/base --commit a6d3d8e --recette son/recettes/hybride.json
          outils/mixer.py dans le bac à sable sur la recette DU COMMIT (git show), sorties (wav, stems, mesures, planches)
          ramenées dans le bac à sable et « copies » retirées (aucun livrable réécrit) ; imprime le md5 du mix (à comparer
          au mix validé, ex. $UP/versions-47s/point-solaire-bande-son-hybride.wav : c6158daf…). Puis `comparer` sur les
          dossiers de stems (…/son/stems-amont/iphone, …/son/hybride/stems) : l'écart stem par stem, fenêtre par fenêtre
    python3 outils/bac_a_sable.py comparer BASE_COUCHES NEUF_COUCHES [--stems ANCIEN.wav NOUVEAU.wav] [--pas 2] [--json r.json]
          NEUF_COUCHES = python3 son/stems_amont.py --seulement musique --couches … dans le projet ; pour chaque couche et
          chaque courbe de gain : écart avant le premier pivot, puis par fenêtre de --pas s du film actuel, l'ancien placé
          par chronologie.decaler_echantillon (toute liste d'insertions) ; les échantillons des mesures insérées sont hors
          comparaison (ils n'existent pas dans l'ancien)
Options communes : --insertions son/dialogue.json (défaut : celui du projet). Rien n'est écrit hors de --dossier / --json.
Exemple chiffré (28/09) : prenom/preuve-musique.json « reprise_verification ». Recette : showcase-iphone/OUTILS.md § 7, 5 bis.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
OUTILS = Path(__file__).resolve().parent
PROJET = OUTILS.parent                       # videos/showcase
DEPOT = PROJET.parent.parent                 # /opt/vokio-ads
sys.path.insert(0, str(OUTILS))
import chronologie as CH  # noqa: E402

SR = CH.SR
EXCLUS = ["son/stems-amont/", "son/hybride/", "son/hybride-16x9/", "son/riche-musique/couches/", "son/riche-musique/stems/",
          "son/riche-musique/stems-avant-limiteur/", "son/riche-musique/el/", "son/riche-design/stems/", "son/stems/",
          "prenom/", "assets/", "renders/", "node_modules/", "__pycache__/", "*.mp4", "son/mix.wav", "son/mix-monde.wav",
          "son/riche-musique/mix-musique.wav", "son/riche-design/mix-design.wav", "son/dialogue.wav"]


def git_show(commit, chemin):
    return subprocess.run(["git", "-C", str(DEPOT), "show", f"{commit}:{chemin}"], capture_output=True, check=True).stdout


def git_ls(commit, dossier):
    r = subprocess.run(["git", "-C", str(DEPOT), "ls-tree", "--name-only", commit, dossier + "/"], capture_output=True,
                       check=True, text=True)
    return [x for x in r.stdout.split("\n") if x]


def monter(commit, dossier):
    d = Path(dossier)
    sb = d / "videos" / "showcase"
    sb.mkdir(parents=True, exist_ok=True)
    subprocess.run(["rsync", "-a", "--delete"] + [f"--exclude={e}" for e in EXCLUS] + [f"{PROJET}/", f"{sb}/"], check=True)
    (d / "videos" / "showcase-iphone" / "donnees").mkdir(parents=True, exist_ok=True)
    poses = []
    for rel in ("videos/showcase/donnees", "videos/showcase-iphone/donnees"):
        for f in git_ls(commit, rel):
            (d / f).write_bytes(git_show(commit, f)); poses.append(f)
    dj = json.loads(git_show(commit, "videos/showcase/son/dialogue.json"))
    tmp = d / "_avant"
    tmp.mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-B", str(PROJET / "son" / "dialogue.py"), "--avant", str(tmp)], check=True,
                   stdout=subprocess.DEVNULL)
    wav = sb / "son" / "dialogue.wav"
    (tmp / "dialogue.wav").replace(wav)
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    dj["fichier"] = str(wav)
    (sb / "son" / "dialogue.json").write_text(json.dumps(dj, ensure_ascii=False, indent=1))
    md5 = hashlib.md5(wav.read_bytes()).hexdigest()
    print(f"bac à sable {sb} : code actuel, données de {commit} ({len(poses)} fichiers), dialogue d'avant md5 {md5}")
    print(f"ensuite : python3 {OUTILS / 'bac_a_sable.py'} musique --dossier {d} --couches {d}-couches")


def musique(dossier, couches):
    sb = Path(dossier) / "videos" / "showcase"
    cmd = [sys.executable, "-B", str(sb / "son" / "stems_amont.py"), "--seulement", "musique"]
    if couches:
        cmd += ["--couches", str(couches)]
    subprocess.run(cmd, check=True, cwd=str(sb))
    w = sb / "son" / "stems-amont" / "iphone" / "musique.wav"
    print(f"musique du film d'avant : {w}  md5 {hashlib.md5(w.read_bytes()).hexdigest()}")


def stems(dossier, video):
    sb = Path(dossier) / "videos" / "showcase"
    cmd = [sys.executable, "-B", str(sb / "son" / "stems_amont.py"), "--force"] + (["--video", str(video)] if video else [])
    subprocess.run(cmd, check=True, cwd=str(sb))
    out = sb / "son" / "stems-amont" / "iphone"
    for w in sorted(out.glob("*.wav")):
        print(f"  {w.stem:10s} md5 {hashlib.md5(w.read_bytes()).hexdigest()}")
    print(f"stems amont du film d'avant : {out}")


def mixer(dossier, commit, recette):
    """outils/mixer.py du bac à sable sur la recette du commit, sorties dans le bac à sable, sans copies."""
    sb = Path(dossier) / "videos" / "showcase"
    R = json.loads(git_show(commit, f"videos/showcase/{recette}"))
    rec = sb / recette
    dst = sb / "son" / f"bac-{R.get('nom', 'mix')}"
    so = R.setdefault("sorties", {})
    so.update({"wav": str(dst / "mix.wav"), "stems": str(dst / "stems"), "mesures": str(dst / "mesures.json"),
               "planches": str(dst / "planches")})
    so.pop("copies", None)
    # ce que le bac à sable n'a pas copié (stems validés de référence : EXCLUS) se lit dans le vrai projet, en lecture ;
    # un chemin absolu vers les données du dépôt pointe sur celles du commit, posées dans le bac à sable
    g = R.get("garde_reperes", {})
    for k in ("reference", "cues_reference"):
        if k in g and not (rec.parent / g[k]).exists():
            g[k] = str(((PROJET / recette).parent / g[k]).resolve())
    me = R.get("mesures", {})
    if str(me.get("evenements", "")).startswith(str(DEPOT) + "/"):
        me["evenements"] = str(Path(dossier) / Path(me["evenements"]).relative_to(DEPOT))
    rec.parent.mkdir(parents=True, exist_ok=True)
    f = rec.with_name(rec.stem + f"-{commit}.json")
    f.write_text(json.dumps(R, ensure_ascii=False, indent=1))
    subprocess.run([sys.executable, "-B", str(sb / "outils" / "mixer.py"), str(f), "--force"], check=True, cwd=str(sb))
    w = dst / "mix.wav"
    print(f"mix du film d'avant : {w}  md5 {hashlib.md5(w.read_bytes()).hexdigest()} ; stems : {dst / 'stems'}")


def db(x):
    return round(float(20 * np.log10(max(float(x), 1e-30))), 1)


def lire(p):
    import sonlib as L
    return np.atleast_2d(L.lire(p).T).T.astype(np.float64)


def correspondance(C, n_ancien, n_nouveau):
    """(indices anciens, indices nouveaux) des échantillons qui existent dans les deux films."""
    i = np.arange(n_ancien)
    j = np.asarray(C.decaler_echantillon(i))
    ok = j < n_nouveau
    return i[ok], j[ok]


def fenetres(C, duree, pas):
    p0 = C.ins[0]["pivot_s"] if C.ins else duree
    z = C.zones()
    bords = [0.0, p0] + [b for _, b in z]
    fen = [(0.0, p0, "avant le pivot")]
    t = max(b for _, b in z) if z else duree
    while t < duree - 1e-9:
        fen.append((t, min(duree, t + pas), None))
        t += pas
    return fen, bords


def comparer_signaux(C, x_old, x_new, fen, pas_ech=1):
    io, jn = correspondance(C, len(x_old) * pas_ech, len(x_new) * pas_ech)
    if pas_ech > 1:
        garde = (io % pas_ech == 0) & (jn % pas_ech == 0)
        io, jn = io[garde] // pas_ech, jn[garde] // pas_ech
    d = np.abs(x_new[jn] - x_old[io])
    if d.ndim > 1:
        d = d.max(axis=1)
    tn = jn * pas_ech / SR
    out = []
    for a, b, _ in fen:
        m = (tn >= a - 1e-9) & (tn < b - 1e-9)
        out.append(float(d[m].max()) if m.any() else None)
    return out


def comparer(base, neuf, stems, pas, sortie, insertions):
    C = CH.charger(insertions)
    assert C, "aucune insertion dans " + str(insertions)
    B, N = Path(base), Path(neuf)
    exemple = next(iter(sorted(N.glob("*.wav"))))
    duree = len(lire(exemple)) / SR
    fen, _ = fenetres(C, duree, pas)
    lab = [n or f"{a:.2f}-{b:.2f}" for (a, b, n) in fen]
    R = {"insertions": [dict(i) for i in C.ins], "fenetres_s": lab, "couches_crete_dbfs": {}, "gains_ecart_max": {}}
    print(f"{C} ; fenêtres : {', '.join(lab)}")
    print("couches (crête de l'écart, dBFS ; −600 = nul à l'octet)")
    for f in sorted(N.glob("*.wav")):
        if not (B / f.name).exists():
            continue
        v = [db(x) if x is not None else None for x in comparer_signaux(C, lire(B / f.name), lire(f), fen)]
        R["couches_crete_dbfs"][f.stem] = v
        print(f"  {f.stem:14s} " + " ".join(f"{x:7.1f}" if x is not None else "      -" for x in v))
    if (B / "gains.npz").exists() and (N / "gains.npz").exists():
        ga, gb = np.load(B / "gains.npz"), np.load(N / "gains.npz")
        pas_g = int(gb["pas"]) if "pas" in gb.files else 16
        if any(i["echantillons"] % pas_g for i in C.ins):
            print(f"  (gains : une insertion n'est pas un multiple de {pas_g} éch. : comparaison aux échantillons communs seulement)")
        print(f"courbes de gain (écart absolu max, dB ou 0-1 ; pas de {pas_g} éch.)")
        for k in gb.files:
            if k == "pas" or k not in ga.files:
                continue
            v = comparer_signaux(C, ga[k].astype(np.float64), gb[k].astype(np.float64), fen, pas_ech=pas_g)
            R["gains_ecart_max"][k] = [float(f"{x:.2e}") if x is not None else None for x in v]
            print(f"  {k:24s} " + " ".join(f"{x:8.1e}" if x is not None else "       -" for x in v))
    if stems:
        a, n = lire(stems[0]), lire(stems[1])
        v = comparer_signaux(C, a, n, fen)
        R["stem_crete_dbfs"] = [db(x) if x is not None else None for x in v]
        print("stem  " + " ".join(f"{db(x):7.1f}" if x is not None else "      -" for x in v))
    if sortie:
        Path(sortie).write_text(json.dumps(R, ensure_ascii=False, indent=1))
        print(f"→ {sortie}")
    return R


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    m = sp.add_parser("monter"); m.add_argument("--commit", required=True); m.add_argument("--dossier", required=True)
    u = sp.add_parser("musique"); u.add_argument("--dossier", required=True); u.add_argument("--couches")
    t = sp.add_parser("stems"); t.add_argument("--dossier", required=True); t.add_argument("--video")
    x = sp.add_parser("mixer"); x.add_argument("--dossier", required=True); x.add_argument("--commit", required=True)
    x.add_argument("--recette", default="son/recettes/hybride.json")
    c = sp.add_parser("comparer"); c.add_argument("base"); c.add_argument("neuf")
    c.add_argument("--stems", nargs=2, metavar=("ANCIEN", "NOUVEAU")); c.add_argument("--pas", type=float, default=2.0)
    c.add_argument("--json"); c.add_argument("--insertions", default=str(CH.DIALOGUE))
    a = ap.parse_args()
    if a.cmd == "monter":
        monter(a.commit, a.dossier)
    elif a.cmd == "musique":
        musique(a.dossier, a.couches)
    elif a.cmd == "stems":
        stems(a.dossier, a.video)
    elif a.cmd == "mixer":
        mixer(a.dossier, a.commit, a.recette)
    else:
        comparer(a.base, a.neuf, a.stems, a.pas, a.json, a.insertions)


if __name__ == "__main__":
    main()
