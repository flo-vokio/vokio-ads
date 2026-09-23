#!/usr/bin/env python3
"""Choisit le moteur de voix off, et aide à choisir la voix elle-même.

    outils/voix.py                  dit ce qui serait utilisé, et pourquoi
    outils/voix.py --catalogue      les voix du compte ElevenLabs
    outils/voix.py --bibliotheque   les voix publiques françaises, filtrables
    outils/voix.py --retenir <id>   inscrit la voix retenue dans voix.json
    outils/voix.py --essai          synthétise une phrase témoin par voix retenue

La règle, en une phrase : **si le coffre contient une clé ElevenLabs dédiée
aux pubs, la voix vient d'ElevenLabs ; sinon elle vient de Kokoro, en local.**
Aucun script d'assemblage n'écrit « kokoro » ou « elevenlabs » en dur, ils
appellent `choisir()`. Le jour où la clé est déposée, la bascule est faite
sans toucher à une ligne de code, et le jour où elle est retirée le montage
continue de tourner au lieu de casser.

Le secret se dépose EN SSH, jamais en conversation ni par un outil :

    install -m 600 /dev/null /root/.secrets/vokio-ads-elevenlabs
    read -rs K && printf '%s' "$K" > /root/.secrets/vokio-ads-elevenlabs; unset K

`read -rs` ne fait pas apparaître la clé à l'écran et ne la laisse pas dans
l'historique du shell, contrairement à un `echo sk_... >`.

Pourquoi une clé DÉDIÉE et pas celle de production : celle de production sait
synthétiser mais n'a pas le droit `voices_read`, donc impossible de parcourir
le catalogue pour choisir une voix ; et sa consommation est surveillée au
titre du coût par appel client, une pub qui s'y mélange fausse le suivi.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path("/opt/vokio-ads")
COFFRE = Path("/root/.secrets/vokio-ads-elevenlabs")
CONFIG = RACINE / "voix.json"
API = "https://api.elevenlabs.io"


def cle():
    """La clé du coffre, ou None. Jamais affichée, jamais journalisée."""
    if not COFFRE.is_file():
        return None
    k = COFFRE.read_text().strip()
    return k or None


def config():
    return json.loads(CONFIG.read_text()) if CONFIG.is_file() else {}


def choisir():
    """(provider, voice, env_supplémentaire) — le seul point de décision.

    Lève si la clé est là mais qu'aucune voix n'a été retenue : produire un
    film avec la voix anglaise par défaut d'ElevenLabs serait pire que de
    rester sur Kokoro, et ça passerait inaperçu jusqu'à l'écoute.
    """
    c, k = config(), cle()
    if not k:
        return "kokoro", c.get("kokoro", {}).get("voice", "ff_siwis"), {}
    v = c.get("elevenlabs", {}).get("voice")
    if not v:
        raise SystemExit(
            "Clé ElevenLabs déposée, mais aucune voix retenue.\n"
            "  outils/voix.py --bibliotheque   puis   outils/voix.py --retenir <id>")
    return "elevenlabs", v, {"ELEVENLABS_API_KEY": k}


def appeler(chemin, params=None):
    k = cle()
    if not k:
        raise SystemExit(f"Aucune clé dans {COFFRE}. Voir l'en-tête de ce fichier.")
    url = f"{API}{chemin}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"xi-api-key": k})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        corps = e.read().decode("utf-8", "replace")[:400]
        if e.code == 401:
            raise SystemExit(f"Clé refusée (401). {corps}")
        if e.code == 403:
            raise SystemExit(
                "Droit manquant sur la clé (403). Il faut « Voices: read » "
                f"en plus de « Text to Speech ».\n{corps}")
        raise SystemExit(f"ElevenLabs {e.code} : {corps}")


def ligne(v):
    lab = v.get("labels") or {}
    traits = " · ".join(filter(None, [
        lab.get("gender"), lab.get("age"), lab.get("accent"),
        lab.get("description"), lab.get("use_case")]))
    return f"  {v.get('voice_id','?'):<24} {v.get('name','?'):<22} {traits}"


def catalogue():
    d = appeler("/v2/voices", {"page_size": 100})
    vs = d.get("voices", [])
    print(f"{len(vs)} voix sur le compte :\n")
    for v in vs:
        print(ligne(v))


def bibliotheque(a):
    params = {"page_size": 60, "language": a.langue}
    if a.cherche:
        params["search"] = a.cherche
    if a.usage:
        params["use_cases"] = a.usage
    if a.genre:
        params["gender"] = a.genre
    d = appeler("/v1/shared-voices", params)
    vs = d.get("voices", [])
    print(f"{len(vs)} voix publiques (langue={a.langue}"
          + (f", usage={a.usage}" if a.usage else "")
          + (f", genre={a.genre}" if a.genre else "") + ") :\n")
    for v in vs:
        print(ligne(v))
    if not vs:
        print("  (aucune — élargir avec --usage '' ou --langue '')")


def retenir(vid):
    c = config()
    el = c.setdefault("elevenlabs", {})
    ancienne = el.get("voice")
    el["voice"] = vid
    CONFIG.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n")
    print(f"voix retenue : {ancienne or '(aucune)'} → {vid}")
    print("Le prochain decliner.py / monter.sh la prendra sans autre geste.")


def noms():
    """id → nom lisible, pour que les essais soient écoutables sans décodeur."""
    return {v["voice_id"]: v.get("name", v["voice_id"])
            for v in appeler("/v2/voices", {"page_size": 100}).get("voices", [])}


def essai(texte, ids=None):
    """Une prise par voix, dans essais/. Sert à choisir à l'oreille.

    Sans --sur, la voix retenue. Avec, autant de prises que d'identifiants :
    c'est la seule façon honnête de trancher, les étiquettes du catalogue
    (« narrative_story », « standard ») ne disent rien du timbre réel.
    """
    k = cle()
    if not k:
        raise SystemExit("Pas de clé : essai inutile, la voix serait Kokoro.")
    if not ids:
        ids = [choisir()[1]]
    modele = config().get("elevenlabs", {}).get("modele", "eleven_multilingual_v2")
    dossier = RACINE / "essais"
    dossier.mkdir(exist_ok=True)
    table = noms() if len(ids) > 1 else {}
    for v in ids:
        corps = json.dumps({"text": texte, "model_id": modele}).encode()
        req = urllib.request.Request(
            f"{API}/v1/text-to-speech/{v}", data=corps,
            headers={"xi-api-key": k, "Content-Type": "application/json"})
        lisible = re.sub(r"[^a-zA-Z0-9]+", "-", table.get(v, v)).strip("-").lower()
        out = dossier / (f"{lisible}-{v}.mp3" if lisible else f"{v}.mp3")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out.write_bytes(r.read())
        except urllib.error.HTTPError as e:
            print(f"  {v} : ElevenLabs {e.code} — "
                  f"{e.read().decode('utf-8','replace')[:200]}")
            continue
        print(f"{out}  ({out.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--catalogue", action="store_true")
    p.add_argument("--bibliotheque", action="store_true")
    p.add_argument("--retenir", metavar="ID")
    p.add_argument("--essai", nargs="?", const="Vokio décroche à votre place, "
                   "et dit tout de suite qui elle est.", metavar="TEXTE")
    p.add_argument("--langue", default="fr")
    p.add_argument("--usage", default="narrative_story")
    p.add_argument("--genre", default="")
    p.add_argument("--cherche", default="")
    p.add_argument("--sur", default="", metavar="ID,ID",
                   help="essaie plusieurs voix d'un coup, pour comparer")
    a = p.parse_args()

    if a.catalogue:
        catalogue()
    elif a.bibliotheque:
        bibliotheque(a)
    elif a.retenir:
        retenir(a.retenir)
    elif a.essai is not None:
        essai(a.essai, [i.strip() for i in a.sur.split(",") if i.strip()])
    else:
        k = cle()
        print(f"coffre  : {COFFRE} — {'clé présente' if k else 'vide'}")
        try:
            provider, v, _ = choisir()
            print(f"moteur  : {provider}\nvoix    : {v}")
        except SystemExit as e:
            print(f"moteur  : elevenlabs\nvoix    : AUCUNE\n\n{e}")
            sys.exit(1)
