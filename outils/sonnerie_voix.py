#!/usr/bin/env python3
"""Voix de la pub « sonnerie » : une prise par phrase, horodatée mot par mot.

    outils/sonnerie_voix.py            synthétise ce qui manque, liste le reste
    outils/sonnerie_voix.py --refaire  ignore le cache

Lit `videos/vokio-sonnerie/variantes.json` : voix, modèle, réglages et
phrases viennent de là, rien n'est écrit ici.

Les horodatages viennent d'ElevenLabs (`/with-timestamps`), caractère par
caractère, regroupés ici en mots. Pas de Whisper : la phrase est connue, il
n'y a rien à transcrire, donc rien à recaler.

Le cache porte sur tout ce qui change le son : texte, voix, modèle, réglages,
graine. Changer l'un des cinq refait la prise ; sinon elle est réutilisée, et une
phrase coûte une seule synthèse quel que soit le nombre de rendus.

La graine (`graines` dans variantes.json) rend une prise reproductible : sans
elle, ElevenLabs tire au sort, et la même phrase est revenue une fois en 2,8 s
et une fois en 3,4 s, avec 1,3 s de silence après « bonjour ! ». Sur un film
de 10 s, c'est la différence entre tenir le format et le rater.
"""
import argparse
import base64
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import voix  # noqa: E402  la clé et l'API, un seul endroit

PROJET = voix.RACINE / "videos" / "vokio-sonnerie"
SORTIE = PROJET / "assets" / "voix"


def empreinte(texte, v, graine=None):
    brut = json.dumps([texte, v["id"], v["modele"], v.get("reglages"), graine],
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(brut.encode()).hexdigest()[:12]


def mots(al):
    """Caractères horodatés → mots. La ponctuation reste collée à son mot :
    c'est elle que le sous-titre affiche."""
    sortie, cour = [], None
    for c, d, f in zip(al["characters"], al["character_start_times_seconds"],
                       al["character_end_times_seconds"]):
        if c.isspace():
            if cour:
                sortie.append(cour)
            cour = None
            continue
        if cour is None:
            cour = {"mot": c, "debut": d, "fin": f}
        else:
            cour["mot"] += c
            cour["fin"] = f
    if cour:
        sortie.append(cour)
    # « bonjour ! » : l'espace française isole la ponctuation haute, qui
    # s'afficherait seule en sous-titre. Elle rejoint son mot, espace fine.
    colle = []
    for m in sortie:
        if colle and all(not ch.isalnum() for ch in m["mot"]):
            colle[-1]["mot"] += "\u202f" + m["mot"]
            colle[-1]["fin"] = m["fin"]
        else:
            colle.append(m)
    sortie = colle
    for m in sortie:
        m["debut"], m["fin"] = round(m["debut"], 3), round(m["fin"], 3)
    return sortie


def duree(f):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(f)]).strip())


def synthetiser(cle_phrase, texte, v, refaire=False, graine=None):
    h = empreinte(texte, v, graine)
    mp3, meta = SORTIE / f"{cle_phrase}.mp3", SORTIE / f"{cle_phrase}.json"
    if not refaire and meta.is_file() and json.loads(meta.read_text()).get("empreinte") == h:
        return json.loads(meta.read_text()), False
    k = voix.cle()
    if not k:
        raise SystemExit(f"Aucune clé dans {voix.COFFRE}.")
    charge = {"text": texte, "model_id": v["modele"]}
    if v.get("reglages"):
        charge["voice_settings"] = v["reglages"]
    if graine is not None:
        charge["seed"] = graine
    req = urllib.request.Request(
        f"{voix.API}/v1/text-to-speech/{v['id']}/with-timestamps"
        "?output_format=mp3_44100_192",
        data=json.dumps(charge).encode(),
        headers={"xi-api-key": k, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            rep = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{cle_phrase} : ElevenLabs {e.code} · "
                         f"{e.read().decode('utf-8', 'replace')[:300]}")
    SORTIE.mkdir(parents=True, exist_ok=True)
    mp3.write_bytes(base64.b64decode(rep["audio_base64"]))
    liste = mots(rep["alignment"])
    # Garde-fou : la prise doit dire la phrase, mot pour mot.
    attendu = texte.split()
    if " ".join(m["mot"] for m in liste).replace("\u202f", " ").split() != attendu:
        raise SystemExit(f"{cle_phrase} : l'alignement ne rend pas la phrase.\n"
                         f"  attendu {attendu}\n  obtenu  {[m['mot'] for m in liste]}")
    info = {"texte": texte, "voix": v["id"], "modele": v["modele"], "graine": graine,
            "reglages": v.get("reglages"), "empreinte": h,
            "duree": round(duree(mp3), 3), "mots": liste}
    meta.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
    return info, True


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--refaire", action="store_true")
    a = p.parse_args()
    cfg = json.loads((PROJET / "variantes.json").read_text())
    for cle_phrase, texte in cfg["phrases"].items():
        info, neuf = synthetiser(cle_phrase, texte, cfg["voix"], a.refaire,
                                 cfg.get("graines", {}).get(cle_phrase))
        derniere = info["mots"][-1]["fin"]
        print(f"{'synthèse' if neuf else 'cache   '}  {cle_phrase:<9} "
              f"{info['duree']:.2f} s (dernier mot fini à {derniere:.2f} s)  « {texte} »")
        print("            " + "  ".join(f"{m['mot']}@{m['debut']:.2f}" for m in info["mots"]))
