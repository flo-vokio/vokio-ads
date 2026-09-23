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
import subprocess
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


def choisir(force=None):
    """(provider, voice, env_supplémentaire) — le seul point de décision.

    `force` court-circuite le réglage, pour essayer une voix sur un film sans
    l'inscrire pour tous les autres.

    Lève si la clé est là, qu'aucune voix n'a été retenue et qu'aucune n'est
    forcée : produire un film avec la voix anglaise par défaut d'ElevenLabs
    serait pire que de rester sur Kokoro, et ça passerait inaperçu jusqu'à
    l'écoute.
    """
    c, k = config(), cle()
    if not k:
        return "kokoro", force or c.get("kokoro", {}).get("voice", "ff_siwis"), {}
    v = force or c.get("elevenlabs", {}).get("voice")
    if not v:
        raise SystemExit(
            "Clé ElevenLabs déposée, mais aucune voix retenue.\n"
            "  outils/voix.py --bibliotheque   puis   outils/voix.py --retenir <id>")
    return "elevenlabs", v, {"ELEVENLABS_API_KEY": k}


def distribution():
    """Les exceptions de voix, prêtes pour HF_VOICE_BY_LINE.

    Le moteur attend des identifiants de ligne à deux chiffres (« 06 ») ; on
    écrit le numéro de plan tel qu'on le lit dans le storyboard (« 6 »).
    """
    par = config().get("elevenlabs", {}).get("par_plan") or {}
    return {f"{int(k):02d}": v for k, v in par.items()}


def amorces():
    """Silence à poser AVANT la ligne, par numéro de plan (secondes)."""
    a = config().get("elevenlabs", {}).get("amorce_par_plan") or {}
    return {int(k): float(v) for k, v in a.items()}


def poser_amorces(projet, table, journal=print):
    """Décale des lignes de voix dans leur plan, et recale leurs mots.

    Le monteur pose chaque voix au DÉBUT de son plan, sans décalage possible :
    il n'existe pas de champ pour retarder une ligne. On met donc l'attente
    dans le fichier lui-même. Les horodatages des mots, eux, viennent de la
    transcription : ils doivent glisser d'autant, sinon les sous-titres du
    plan partent avec le décalage en moins.
    """
    if not table:
        return
    projet = Path(projet)
    meta_f = projet / "audio_meta.json"
    meta = json.loads(meta_f.read_text())
    for v in meta.get("voices", []):
        a = table.get(v.get("frame"))
        if not a:
            continue
        src = projet / v["path"]
        tmp = src.with_suffix(".amorce.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
             "-af", f"adelay={int(round(a * 1000))}:all=1", str(tmp)],
            check=True)
        tmp.replace(src)
        for w in v.get("words") or []:
            w["start"] = round(w["start"] + a, 3)
            w["end"] = round(w["end"] + a, 3)
        duree = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(src)], capture_output=True, text=True, check=True)
        v["duration_s"] = round(float(duree.stdout.strip()), 3)
        journal(f"· plan {v['frame']} : {a} s d'amorce, ligne à {v['duration_s']} s")
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def reglages_moteur():
    """Ce qui doit descendre au moteur de synthèse, en variables d'environnement.

    Le modèle et la direction de voix étaient écrits en dur dans l'extrait
    python du moteur. Ils sont maintenant des données de projet.
    """
    el = config().get("elevenlabs", {})
    env = {"HF_TTS_MODEL": el.get("modele", "eleven_multilingual_v2")}
    if el.get("reglages"):
        env["HF_TTS_SETTINGS"] = json.dumps(el["reglages"])
    return env


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


def ajouter(vid, nom=None):
    """Copie une voix de la bibliothèque publique vers le compte.

    Une voix partagée ne se synthétise pas directement : son identifiant est
    « introuvable » tant qu'elle n'est pas dans le compte. Il faut son
    propriétaire public, que seule la recherche connaît. Elle occupe ensuite
    un emplacement de voix du forfait, et se retire depuis le tableau de bord.
    """
    d = appeler("/v1/shared-voices", {"page_size": 100, "search": nom or ""})
    v = next((x for x in d.get("voices", []) if x.get("voice_id") == vid), None)
    if not v:
        for p in ({"page_size": 100, "language": "fr"}, {"page_size": 100}):
            d = appeler("/v1/shared-voices", p)
            v = next((x for x in d.get("voices", []) if x.get("voice_id") == vid), None)
            if v:
                break
    if not v:
        raise SystemExit(
            f"{vid} n'est ni dans le compte ni retrouvable dans la bibliothèque.\n"
            "Donne son nom : outils/voix.py --ajouter <id> --nom \"Lucie - Narration\"")
    corps = json.dumps({"new_name": v.get("name", vid)}).encode()
    req = urllib.request.Request(
        f"{API}/v1/voices/add/{v['public_owner_id']}/{vid}", data=corps,
        headers={"xi-api-key": cle(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            neuf = json.loads(r.read()).get("voice_id", vid)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs {e.code} : {e.read().decode('utf-8','replace')[:400]}")
    print(f"« {v.get('name')} » ajoutée au compte : {neuf}")
    if neuf != vid:
        print("  ⚠ l'identifiant dans le compte diffère de celui de la bibliothèque, "
              "c'est celui-ci qu'il faut retenir")
    return neuf


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


def essai(texte, ids=None, modele=None, reglages=None, etiquette=""):
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
    modele = modele or config().get("elevenlabs", {}).get("modele", "eleven_multilingual_v2")
    dossier = RACINE / "essais"
    dossier.mkdir(exist_ok=True)
    table = noms()  # toujours : un fichier d'essai doit se lire sans décodeur
    for v in ids:
        charge = {"text": texte, "model_id": modele}
        if reglages:
            charge["voice_settings"] = reglages
        corps = json.dumps(charge).encode()
        req = urllib.request.Request(
            f"{API}/v1/text-to-speech/{v}", data=corps,
            headers={"xi-api-key": k, "Content-Type": "application/json"})
        lisible = re.sub(r"[^a-zA-Z0-9]+", "-", table.get(v, v)).strip("-").lower()
        # Deux jeux de réglages sur la même voix et le même modèle donnaient le
        # MÊME nom de fichier : la deuxième prise écrasait la première en
        # silence. L'étiquette est ce qui distingue une comparaison d'un écrasement.
        suffixe = f"-{etiquette}" if etiquette else f"-{modele}" + ("-regle" if reglages else "")
        out = dossier / ((f"{lisible}-{v}" if lisible else v) + suffixe + ".mp3")
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
    p.add_argument("--ajouter", metavar="ID",
                   help="copie une voix de la bibliothèque publique vers le compte")
    p.add_argument("--nom", default="", help="nom de la voix, pour la retrouver")
    p.add_argument("--essai", nargs="?", const="Vokio décroche à votre place, "
                   "et dit tout de suite qui elle est.", metavar="TEXTE")
    p.add_argument("--langue", default="fr")
    p.add_argument("--usage", default="narrative_story")
    p.add_argument("--genre", default="")
    p.add_argument("--cherche", default="")
    p.add_argument("--sur", default="", metavar="ID,ID",
                   help="essaie plusieurs voix d'un coup, pour comparer")
    p.add_argument("--modele", default=None, help="eleven_v3, eleven_multilingual_v2…")
    p.add_argument("--etiquette", default="", metavar="NOM",
                   help="distingue deux prises de la même voix (sinon écrasement)")
    p.add_argument("--reglages", default="", metavar="JSON",
                   help='voice_settings, ex. \'{"stability":0.45,"style":0.3}\'')
    a = p.parse_args()

    if a.catalogue:
        catalogue()
    elif a.bibliotheque:
        bibliotheque(a)
    elif a.ajouter:
        ajouter(a.ajouter, a.nom)
    elif a.retenir:
        retenir(a.retenir)
    elif a.essai is not None:
        essai(a.essai, [i.strip() for i in a.sur.split(",") if i.strip()],
              a.modele, json.loads(a.reglages) if a.reglages else None, a.etiquette)
    else:
        k = cle()
        print(f"coffre  : {COFFRE} — {'clé présente' if k else 'vide'}")
        try:
            provider, v, _ = choisir()
            print(f"moteur  : {provider}\nvoix    : {v}")
        except SystemExit as e:
            print(f"moteur  : elevenlabs\nvoix    : AUCUNE\n\n{e}")
            sys.exit(1)
