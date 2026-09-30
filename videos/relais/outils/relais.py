#!/usr/bin/env python3
"""Vidéos des cartes « Le relais » de vokio.fr (boucle muette + appel complet sonorisé), d'UNE recette JSON : usage :

    python3 outils/relais.py <carte>/recette.json [etape …]      (défaut : tout)

  Étapes, dans l'ordre (chacune relit ce que la précédente a écrit ; idempotentes) :
    construire  relevé Scribe (cache <carte>/cache/scribe.json), alignement des énoncés DITS sur les mots horodatés, ancres
                « E<n>:mot » résolues, sous-suites contrôlées, puis deux projets HyperFrames rendables :
                <carte>/complete/ et <carte>/boucle/ (gabarit/index.html + donnees.js + polices), <carte>/donnees-*.json
    son         bande son de la complète (/dev/shm) : silence d'avance + le vrai appel (GAIN SEUL, aucun traitement) +
                signature courte posée quand le point se pose sur le ı ; sonie mesurée (−16 LUFS, crête ≤ −1 dBTP)
    rendre      hf render des deux projets (sans perte, en mémoire, sous flock ; outil rendre.py du showcase)
    encoder     H.264 yuv420p +faststart (poids visé : boucle ≤ 700 Ko, complète ≤ 3 Mo), WebM AV1 seulement avec --av1,
                posters webp + jpg, dans /root/vokio-uploads/videos/relais/
    controles   règles de Florian sur le DOM (≤ 3 éléments, corps ≥ plancher, marges, aucun « — », aucun numéro), poids,
                durées, raccord de la boucle, sonie ; rapport <carte>/controles.json (code 1 si un contrôle échoue)
    planche     planches contact des deux vidéos : <carte>/planche-boucle.png, <carte>/planche-complete.png
    purger      efface les intermédiaires de /dev/shm/relais-<id>/
  Options : --seulement boucle|complete (construire/rendre/encoder), --crf-h264 N, --crf-av1 N (sinon réglés au poids).

Recette : voir coiffure/recette.json (commentée par son « _note ») ; une autre carte = une autre recette, même outil.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
GABARIT = RACINE / "gabarit"
SORTIES = Path("/root/vokio-uploads/videos/relais")
SIGNATURE = Path("/root/vokio-uploads/videos/showcase/point-solaire-signature-courte-v2.wav")
sys.path.insert(0, "/opt/vokio-ads/videos/showcase-iphone/outils")
sys.path.insert(0, str(ICI))
FPS = 30
SR = 48000
CIBLE_LUFS = -16.0
POIDS_MAX = {"boucle": 700_000, "complete": 3_000_000}


# ---------------------------------------------------------------- texte
def cle(mot):
    s = unicodedata.normalize("NFD", mot.lower().replace("’", "'"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def mots_de(texte):
    """Mots affichables d'un énoncé : la ponctuation isolée (« ? », « ! », « : ») se colle au mot d'avant par une espace
    fine insécable, comme sur le site."""
    out = []
    for m in texte.split():
        if not cle(m) and out:
            out[-1] += " " + m
        else:
            out.append(m)
    return out


def aligner(enonces, scribe):
    """Temps (début, fin) de chaque mot de chaque énoncé, d'après les mots Scribe (alignement global des clés)."""
    A = [(i, j, cle(m)) for i, e in enumerate(enonces) for j, m in enumerate(mots_de(e["texte"]))]
    S = [w for w in scribe if cle(w["text"])]
    ka, ks = [a[2] for a in A], [cle(w["text"]) for w in S]
    t = [None] * len(A)
    sm = SequenceMatcher(None, ka, ks, autojunk=False)
    rapport = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and a1 - a0 == b1 - b0):
            for k in range(a1 - a0):
                t[a0 + k] = (S[b0 + k]["start"], S[b0 + k]["end"])
                if op == "replace":
                    rapport.append(f"apparié à l'oreille : « {A[a0 + k][2]} » ≈ Scribe « {ks[b0 + k]} »")
        elif op in ("replace", "delete"):
            rapport.append(f"non relevés par Scribe : {ka[a0:a1]} (Scribe : {ks[b0:b1]}) : temps interpolés")
        elif op == "insert":
            rapport.append(f"dits mais non montrés : {ks[b0:b1]}")
    # interpolation des trous
    for k in range(len(t)):
        if t[k] is None:
            g = next((t[x][1] for x in range(k - 1, -1, -1) if t[x]), 0.0)
            d = next((t[x][0] for x in range(k + 1, len(t)) if t[x]), g + 0.3)
            t[k] = (g + 0.02, min(g + 0.25, d))
    par = [[] for _ in enonces]
    for (i, j, _), tt in zip(A, t):
        par[i].append({"texte": mots_de(enonces[i]["texte"])[j], "t": round(tt[0], 3), "t1": round(tt[1], 3)})
    return par, rapport


def resoudre(ancre, enonces_mots, avance=0.0):
    """« E6:neuf », « E6:dix#2 », « E6:@3 », « E6:fin », « E6:debut », « E1:bien.+0.25 » ou un nombre → temps film."""
    if isinstance(ancre, (int, float)):
        return float(ancre)
    m = re.fullmatch(r"E(\d+):(.+?)(?:#(\d+))?([+-]\d+(?:\.\d+)?)?", ancre)
    if not m:
        raise SystemExit(f"ancre illisible : {ancre}")
    i, mot, rang, dec = int(m.group(1)), m.group(2), int(m.group(3) or 1), float(m.group(4) or 0)
    M = enonces_mots[i]
    if mot == "fin":
        t = M[-1]["t1"]
    elif mot == "debut":
        t = M[0]["t"]
    elif mot.startswith("@"):
        t = M[int(mot[1:])]["t"]
    else:
        trouves = [w for w in M if cle(w["texte"]) == cle(mot)]
        if len(trouves) < rang:
            raise SystemExit(f"ancre {ancre} : « {mot} » introuvable dans l'énoncé {i} ({[w['texte'] for w in M]})")
        t = trouves[rang - 1]["t"]
    return round(t + dec + avance, 3)


def index_mot(ancre, enonces_mots):
    """« E12:Vous » (ou « E12:Vous#2 ») → (12, rang du mot) : une page commence à ce mot (clé « coupes » d'un mode)."""
    m = re.fullmatch(r"E(\d+):(.+?)(?:#(\d+))?", ancre)
    i, mot, rang = int(m.group(1)), m.group(2), int(m.group(3) or 1)
    ks = [k for k, w in enumerate(enonces_mots[i]) if cle(w["texte"]) == cle(mot)]
    if len(ks) < rang:
        raise SystemExit(f"coupe {ancre} : mot introuvable")
    return i, ks[rang - 1]


def sous_suite(petit, grand):
    it = iter(cle(w) for w in grand)
    return all(any(c == x for x in it) for c in (cle(w) for w in petit))


# ---------------------------------------------------------------- construire
def donnees_mode(R, mode, mots_complete):
    M = R[mode]
    corps = {"agente": {"seul": 72, "objet": 64}, "appelant": {"seul": 86, "objet": 76}}
    for q, v in M.get("corps", {}).items():          # un nombre = même corps seul et avec objet
        corps[q] = {"seul": v, "objet": v} if isinstance(v, (int, float)) else corps[q] | v
    if mode == "complete":
        av = M.get("avance", 0.8)
        enonces = [{"qui": e["qui"], "mots": [dict(w, t=round(w["t"] + av, 3), t1=round(w["t1"] + av, 3)) for w in ws]}
                   for e, ws in zip(R["enonces"], mots_complete)]
        duree_voix = sonde_duree(R["audio"]) + av
    else:
        av = 0.0
        enonces = []
        for e in M["enonces"]:
            mots = mots_de(e["texte"])
            tt = e.get("temps") or [e["debut"] + k * e.get("pas", 0.22) for k in range(len(mots))]
            if len(tt) != len(mots):
                raise SystemExit(f"boucle : {len(mots)} mots, {len(tt)} temps : « {e['texte']} »")
            if "source" in e and not sous_suite(mots, mots_de(R["enonces"][e["source"]]["texte"])):
                raise SystemExit(f"boucle : « {e['texte']} » n'est pas une sous-suite de l'énoncé {e['source']}")
            enonces.append({"qui": e["qui"], "mots": [{"texte": w, "t": t, "t1": t + 0.2} for w, t in zip(mots, tt)]})
        duree_voix = None
    ref = [e["mots"] for e in enonces]
    r = lambda a: resoudre(a, ref)            # les temps des énoncés sont déjà des temps film
    D = {"mode": mode, "fps": FPS, "taille": 1080, "marge": 84, "corps": corps, "corps_min": 52,
         "situation": dict(M["situation"], objet=R.get("situation", "ciseaux")), "enonces": enonces}
    D["coupes"] = [list(index_mot(a, ref)) for a in M.get("coupes", [])]
    ag = M.get("agenda")
    if ag and R.get("agenda"):
        D["agenda"] = {"date": R["agenda"]["date"], "heures": R["agenda"]["heures"],
                       "entree": r(ag["entree"]), "sortie": r(ag["sortie"]),
                       "touches": [{"t": r(a), "heure": h} for a, h in ag.get("touches", [])],
                       "bloc": dict(R["agenda"]["bloc"], ouvre=r(ag["bloc"]["ouvre"]), t_nom=r(ag["bloc"]["nom"]),
                                    t_service=r(ag["bloc"]["service"]))}
    fi = M.get("fiche")
    if fi and R.get("fiche"):
        lignes = R["fiche"]["lignes"]
        if len(fi["lignes"]) != len(lignes):
            raise SystemExit("fiche : autant d'ancres que de lignes")
        D["fiche"] = {"titre": R["fiche"]["titre"], "entree": r(fi["entree"]), "sortie": r(fi["sortie"]),
                      "lignes": [{"texte": l, "t": r(a)} for l, a in zip(lignes, fi["lignes"])]}
    if M.get("sms") and R.get("sms"):
        D["sms"] = dict(R["sms"], entree=r(M["sms"]["entree"]), bulle=r(M["sms"]["bulle"]), sortie=r(M["sms"]["sortie"]))
    if mode == "complete":
        D["fin"] = {"entree": r(M["fin"]["entree"])}
        D["fin"]["point"] = round(D["fin"]["entree"] + 1.05, 3)   # le téléphone sort (0,4 s), le mot s'écrit, puis le point se pose
        D["duree"] = round(max(duree_voix, D["fin"]["point"] + 1.6) * FPS) / FPS
        D["texte_sortie"] = D["fin"]["entree"]
    else:
        D["duree"] = M["duree"]
        D["texte_sortie"] = r(M["texte_sortie"])
    D["avance"] = av
    return D


def sonde_duree(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


def projet(dossier, D):
    if dossier.exists():
        shutil.rmtree(dossier)
    shutil.copytree(GABARIT, dossier, ignore=shutil.ignore_patterns("*.md", "situations"))
    (dossier / "donnees.js").write_text("window.DONNEES = " + json.dumps(D, ensure_ascii=False, indent=1) + ";\n")
    sit = GABARIT / "situations" / f"{D['situation']['objet']}.svg"
    if not sit.exists():
        raise SystemExit(f"situation inconnue : {sit.name} (gabarit/situations/ : {[f.stem for f in sit.parent.glob('*.svg')]})")
    svg = re.sub(r"<!--.*?-->\s*", "", sit.read_text(), flags=re.S).strip()
    anim = sit.with_suffix(".js")
    if anim.exists():                         # l'animateur de la situation, inséré juste après son dessin
        svg += "\n    <script>\n" + anim.read_text() + "\n    </script>"
    html = (dossier / "index.html").read_text().replace("__DUREE__", f"{D['duree']:.6f}").replace("__SITUATION__", svg)
    (dossier / "index.html").write_text(html)


def construire(R, carte, modes):
    from scribe import transcrire
    scribe = transcrire(R["audio"], carte / "cache" / "scribe.json")
    mots, rapport = aligner(R["enonces"], scribe)
    for e, ws in zip(R["enonces"], mots):     # locuteur Scribe contre locuteur de la recette (information)
        pass
    (carte / "alignement.json").write_text(json.dumps({"rapport": rapport, "enonces": [
        {"qui": e["qui"], "mots": ws} for e, ws in zip(R["enonces"], mots)]}, ensure_ascii=False, indent=1))
    print("alignement :", *(rapport or ["tous les mots montrés sont relevés tels quels"]), sep="\n  ")
    for mode in modes:
        D = donnees_mode(R, mode, mots)
        (carte / f"donnees-{mode}.json").write_text(json.dumps(D, ensure_ascii=False, indent=1))
        projet(carte / mode, D)
        print(f"{mode} : {D['duree']:.3f} s, {round(D['duree'] * FPS)} images → {carte / mode}")


# ---------------------------------------------------------------- son
def lire_wav(f):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def ecrire_wav(f, x):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                    "-c:a", "pcm_f32le", str(f)], input=x.astype(np.float32).tobytes(), check=True)


def mesurer(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(f), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr[r.stderr.rfind("Summary:"):]
    g = lambda k: float(re.search(k + r":\s+(-?[\d.]+|-inf)", txt).group(1))
    return {"lufs": g("I"), "lra": g("LRA"), "crete_dbtp": g("Peak")}


def attaque(x, seuil_db=-30):
    """Premier échantillon au-dessus du seuil (enveloppe crête), en s."""
    e = np.abs(x).max(axis=1)
    k = np.argmax(e > 10 ** (seuil_db / 20))
    return k / SR


def son(R, carte, shm):
    D = json.loads((carte / "donnees-complete.json").read_text())
    voix = lire_wav(R["audio"])
    n = round(D["duree"] * SR)
    mix = np.zeros((n, 2), np.float32)
    a0 = round(D["avance"] * SR)
    mix[a0:a0 + len(voix)] = voix[: n - a0]
    shm.mkdir(parents=True, exist_ok=True)
    ecrire_wav(shm / "voix-seule.wav", mix)
    mv = mesurer(shm / "voix-seule.wav")
    gain = CIBLE_LUFS - mv["lufs"]
    if mv["crete_dbtp"] + gain > -1.0:
        gain = -1.0 - mv["crete_dbtp"]
        print(f"son : la crête limite le gain ({gain:+.2f} dB) : sonie sous la cible, AUCUN limiteur (le vrai appel n'est pas traité)")
    mix *= 10 ** (gain / 20)
    # signature : son attaque tombe sur l'instant où le point se pose sur le ı, 4 dB sous la sonie de la voix
    sig = lire_wav(SIGNATURE)
    ms = mesurer(SIGNATURE)
    g_sig = (CIBLE_LUFS - 4.0) - ms["lufs"]
    s0 = round((D["fin"]["point"] - attaque(sig)) * SR)
    fin_voix = a0 + len(voix)
    if s0 < fin_voix - round(0.05 * SR):
        # la signature ne recouvre la voix que dans le bruit de ligne de fin (après le dernier mot)
        dernier_mot = D["enonces"][-1]["mots"][-1]["t1"]
        if s0 / SR < dernier_mot + 0.3:
            raise SystemExit("son : la signature recouvrirait la parole")
    k1 = min(n, s0 + len(sig))
    mix[s0:k1] += sig[: k1 - s0] * 10 ** (g_sig / 20)
    # fondu de sortie de 40 ms du bruit de ligne sous la signature seulement si la voix déborde la durée
    ecrire_wav(shm / "mix-complete.wav", mix)
    m = mesurer(shm / "mix-complete.wav")
    corr = CIBLE_LUFS - m["lufs"]            # seconde passe : gain global seul, pour que le MIX soit à la cible
    if abs(corr) > 0.15 and m["crete_dbtp"] + corr <= -1.0:
        mix *= 10 ** (corr / 20)
        gain += corr
        g_sig += corr
        ecrire_wav(shm / "mix-complete.wav", mix)
        m = mesurer(shm / "mix-complete.wav")
    rap = {"voix_source": mv, "gain_voix_db": round(gain, 2), "signature": {"fichier": str(SIGNATURE), "gain_db": round(g_sig, 2),
           "debut_s": round(s0 / SR, 3), "attaque_s": round(D["fin"]["point"], 3)}, "mix": m,
           "traitement_de_la_voix": "gain seul (aucun filtre, compresseur ni limiteur)"}
    (carte / "son.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1))
    print(f"son : voix {mv['lufs']:.1f} LUFS → gain {gain:+.2f} dB ; mix {m['lufs']:.1f} LUFS, crête {m['crete_dbtp']:.1f} dBTP")


# ---------------------------------------------------------------- rendre / encoder
def rendre_modes(carte, shm, modes):
    from rendre import rendre
    for mode in modes:
        rendre(carte / mode, shm / f"{mode}-sans-perte.mp4", crf=0, tmp="shm")


def enc_h264(src, dst, crf, audio=None, gop=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-map", "0:v:0", "-c:v", "libx264", "-preset", "veryslow", "-tune", "animation", "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", "-r", str(FPS)]
    if gop:
        cmd += ["-g", str(gop)]
    if audio:
        cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "80k", "-ar", str(SR), "-ac", "2"]
    else:
        cmd += ["-an"]
    cmd += ["-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)
    return dst.stat().st_size


def enc_av1(src, dst, crf, audio=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src)]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-map", "0:v:0", "-c:v", "libsvtav1", "-preset", "5", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-svtav1-params", "tune=0", "-r", str(FPS)]
    if audio:
        cmd += ["-map", "1:a:0", "-c:a", "libopus", "-b:a", "48k", "-ar", str(SR), "-ac", "2"]
    else:
        cmd += ["-an"]
    subprocess.run(cmd + [str(dst)], check=True)
    return dst.stat().st_size


def encoder(R, carte, shm, modes, crf_h=None, crf_a=None, avec_av1=False):
    SORTIES.mkdir(parents=True, exist_ok=True)
    nom = R["nom"]
    bilan = {}
    for mode in modes:
        src = shm / f"{mode}-sans-perte.mp4"
        audio = shm / "mix-complete.wav" if mode == "complete" else None
        dst = SORTIES / f"{nom}-{mode}.mp4"
        # CRF le plus bas (meilleure image) qui tient le poids visé, à 10 % de marge
        essais = [crf_h] if crf_h else list(range(18, 36))
        for c in essais:
            p = enc_h264(src, dst, c, audio)
            if p <= POIDS_MAX[mode] * 0.9 or crf_h:
                break
        bilan[mode] = {"h264": {"fichier": str(dst), "crf": c, "octets": p}}
        if avec_av1:        # abandonné le 29/09 (gain 27-33 %) : seulement sur demande (--av1)
            dw = SORTIES / f"{nom}-{mode}.webm"
            essais = [crf_a] if crf_a else list(range(32, 56, 2))
            for c2 in essais:
                q = enc_av1(src, dw, c2, audio)
                if q <= p * 0.75 or crf_a:
                    break
            bilan[mode]["av1_webm"] = {"fichier": str(dw), "crf": c2, "octets": q}
        # posters (règle de Florian, 29/09) : celui de la BOUCLE = l'illustration du métier au moment le plus parlant du geste,
        # SANS AUCUN TEXTE (recette « poster_boucle » : instant de la boucle ; défaut 0,6 s) ; celui de la complète = sa
        # première image (recette « poster_complete » pour un autre instant)
        t_p = float(R.get("poster_boucle", 0.6)) if mode == "boucle" else float(R.get("poster_complete", 0.0))
        for ext, opt in (("webp", ["-c:v", "libwebp", "-quality", "78", "-compression_level", "6"]),
                         ("jpg", ["-q:v", "4"])):
            f = SORTIES / f"{nom}-{mode}-poster.{ext}"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t_p:.3f}", "-i", str(src), "-frames:v", "1",
                            "-vf", "scale=720:720:flags=lanczos"] + opt + [str(f)], check=True)
            bilan[mode][f"poster_{ext}"] = {"fichier": str(f), "octets": f.stat().st_size, "t": round(t_p, 3)}
        print(mode, json.dumps(bilan[mode], ensure_ascii=False))
    ancien = {k: {x: y for x, y in v.items() if x != "av1_webm" or avec_av1} for k, v in (json.loads((carte / "encodage.json").read_text()) if (carte / "encodage.json").exists() else {}).items()}
    (carte / "encodage.json").write_text(json.dumps(ancien | bilan, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------- planche
def planche(R, carte, modes):
    from PIL import Image, ImageDraw, ImageFont
    police = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 20) \
        if Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf").exists() else ImageFont.load_default()
    for mode in modes:
        f = SORTIES / f"{R['nom']}-{mode}.mp4"
        d = sonde_duree(f)
        pas = 0.5 if mode == "boucle" else 1.5
        instants = [round(k * pas, 3) for k in range(int(d / pas) + 1) if k * pas < d]
        c = 6 if mode == "boucle" else 8
        cote = 300
        L = math.ceil(len(instants) / c)
        P = Image.new("RGB", (c * (cote + 8) + 8, L * (cote + 34) + 8), (150, 150, 150))
        for k, t in enumerate(instants):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(f), "-frames:v", "1",
                                  "-vf", f"scale={cote}:{cote}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                 capture_output=True, check=True).stdout
            im = Image.frombytes("RGB", (cote, cote), raw)
            x, y = 8 + (k % c) * (cote + 8), 8 + (k // c) * (cote + 34)
            P.paste(im, (x, y + 26))
            ImageDraw.Draw(P).text((x + 2, y + 2), f"{t:5.1f} s", fill=(255, 255, 255), font=police)
        out = carte / f"planche-{mode}.png"
        P.save(out, optimize=True)
        print("planche :", out)


# ---------------------------------------------------------------- main
def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("recette")
    A.add_argument("etapes", nargs="*")
    A.add_argument("--seulement", choices=["boucle", "complete"])
    A.add_argument("--crf-h264", type=int)
    A.add_argument("--crf-av1", type=int)
    A.add_argument("--av1", action="store_true", help="produire aussi le WebM AV1 (abandonné par défaut)")
    a = A.parse_args()
    rec = Path(a.recette).resolve()
    R = json.loads(rec.read_text())
    carte = rec.parent
    shm = Path("/dev/shm") / f"relais-{R['id']}"
    modes = [a.seulement] if a.seulement else ["boucle", "complete"]
    etapes = a.etapes or ["construire", "son", "rendre", "encoder", "controles", "planche"]
    for e in etapes:
        print(f"== {e}", flush=True)
        if e == "construire":
            construire(R, carte, modes)
        elif e == "son":
            son(R, carte, shm)
        elif e == "rendre":
            rendre_modes(carte, shm, modes)
        elif e == "encoder":
            encoder(R, carte, shm, modes, a.crf_h264, a.crf_av1, a.av1)
        elif e == "controles":
            from controles_relais import controler
            if controler(R, carte, shm, modes):
                return 1
        elif e == "planche":
            planche(R, carte, modes)
        elif e == "purger":
            shutil.rmtree(shm, ignore_errors=True)
            print("purgé :", shm)
        else:
            raise SystemExit(f"étape inconnue : {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
