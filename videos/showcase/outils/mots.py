#!/usr/bin/env python3
"""Mots horodatés du dialogue (temps FILM), recalés sur le texte exact de l'appel.

    python3 outils/mots.py            écrit donnees/mots.json et affiche le tableau de contrôle

Sources, par ordre d'autorité croissante :
  1. `hf transcribe` (whisper small, fr) sur son/dialogue.wav : son/transcription-hf.json.
     Ordre et présence des mots seulement : il dérive de −1,3 à +0,2 s sur ce fichier.
  2. ElevenLabs Scribe v1 (fr, mots horodatés, clé PUB /root/.secrets/vokio-ads-elevenlabs) sur le
     même fichier : son/transcription-scribe.json (en cache, rappelé seulement s'il manque).
     Estimation de départ de chaque mot, ±50 ms en général.
  3. L'énergie de son/dialogue.wav, AUTORITÉ sur les bords :
     - « attaque » : un mot qui suit un blanc (≥ 40 ms sous −40 dBFS) prend l'attaque exacte
       (première fenêtre de 10 ms au-dessus de −40 dBFS) si elle est à ±100 ms de l'estimation ;
     - « creux » : sinon, le creux de la bande 400-2500 Hz le plus proche (−80/+60 ms, profondeur
       ≥ 5 dB) marque la consonne d'entrée du mot ;
     - « scribe » : sinon (voyelle contre voyelle), l'estimation Scribe est gardée.
  4. Corrections relevées à la main sur le spectre par bandes (REVUES ci-dessous), avec leur raison.
Le TEXTE est toujours celui de la transcription d'origine (son/dialogue.json), jamais celui d'un ASR.

Deux règles du 28/09 (insertion du prénom : un extrait peut glisser de 92 images, qui ne sont pas un multiple de 10 ms) :
  - REPÈRE DU RELEVÉ. Chaque extrait est analysé là où il était quand on l'a relevé : le wav est avancé de son glissement
    en échantillons à 48 kHz (lire_decale), puis analysé comme avant. Ses mots glissent EXACTEMENT avec lui (début, fin,
    voyelle, syllabes ; image + n si le glissement vaut n images entières). Sur un état sans glissement non multiple de
    10 ms, la sortie est identique à l'octet à celle d'avant (vérifié sur le film de 47 s).
  - RELEVÉ COMPLÉMENTAIRE. Un extrait absent de DECALAGES_RELEVES (ajouté après le relevé du 26/09) reçoit son propre
    relevé Scribe, fait sur lui seul (son/transcription-scribe-complements.json, appelé une fois) : les mots déjà relevés
    ne bougent pas. Ses corrections vont dans REVUES, VOYELLES, REPERES_SYLLABES comme les autres.
"""
import difflib
import json
import re
import subprocess
import sys
import unicodedata
import urllib.request
import uuid
from pathlib import Path

import numpy as np

PROJET = Path(__file__).resolve().parents[1]
DIALOGUE = PROJET / "son" / "dialogue.json"
WAV = PROJET / "son" / "dialogue.wav"
HF_JSON = PROJET / "son" / "transcription-hf.json"
SCRIBE_JSON = PROJET / "son" / "transcription-scribe.json"
SCRIBE_COMPL = PROJET / "son" / "transcription-scribe-complements.json"
SORTIE = PROJET / "donnees" / "mots.json"
HF = "/opt/vokio-ads/bin/hf"
SR = 16000
SR_DIALOGUE = 48000     # son/dialogue.wav : les glissements d'extraits se comptent en échantillons à 48 kHz
FPS = 30

# Décalages film − source de chaque extrait AU MOMENT des relevés (transcriptions en cache, REVUES, VOYELLES,
# syllabes : faits le 26/09 sur le dialogue v1). Si son/dialogue.py déplace un extrait (v2 : C4 passe de −40,60
# à −41,07), les mêmes échantillons audio sont ailleurs dans le film : chaque temps relevé est translaté de
# (décalage actuel − décalage du relevé) de son extrait. Les bords restent recalés sur l'énergie du wav actuel.
DECALAGES_RELEVES = {"A1": 4.21, "C1": 0.22, "C2": -20.16, "A2A3": -31.12, "C3": -35.56, "A4": -41.07, "C4": -40.60}

# Corrections à la main (extrait, rang) → (debut film, raison). Relevées le 26/09 sur le spectre par bandes
# (outils/spectre.py : 0-400 / 400-2500 / 2500-4000 Hz + périodicité, fenêtres 25 ms au pas de 10 ms).
# Rappel : la ligne téléphonique coupe au-dessus de 4 kHz, les /s/ /ʃ/ y sont presque invisibles.
REVUES = {
    ("A1", 1): (5.680, "frication du /ʒ/ dès 5,675 (2,5-4 kHz), avant le seuil RMS"),
    ("A1", 2): (5.810, "début du /s/ sourd"),
    ("A1", 3): (6.055, "creux de transition /i/ → /e/ après « suis »"),
    ("A1", 7): (7.475, "/l/ : léger creux de la bande médiane"),
    ("A1", 8): (7.590, "relâchement /kl/ sourd 7,59-7,68 (le seuil RMS ne voit que la voyelle à 7,69)"),
    ("A1", 9): (8.040, "/v/ après la tenue du /k/ final de « Clinique » (8,00-8,04) ; le creux 7,89 est son /n/"),
    ("C1", 1): (10.660, "/ʃ/ hors bande téléphone ; montée de la bande médiane (/a/) ; lu dans le groupe « mon chat, »"),
    ("C1", 2): (10.915, "voix craquée d'hésitation (périodicité 0,2-0,3) de 10,915 à 11,39"),
    ("C1", 3): (11.395, "murmure nasal /m/ 11,395-11,56 (graves forts, médiums effondrés) ; /k/ tenu 11,705-11,745"),
    ("C1", 5): (12.730, "murmure nasal /m/ 12,73-12,81"),
    ("C1", 6): (13.055, "relâchement du /p/ après sa tenue silencieuse 13,00-13,05"),
    ("C1", 8): (13.720, "/j/ puis /ɛ/ fort 13,745-13,87 ; 13,445-13,54 est le /pɥ/ sourd de « puis »"),
    ("A2A3", 1): (18.005, "/v/ 18,005-18,065"),
    ("A2A3", 2): (19.800, "frication faible du /ʒ/ dès 19,80"),
    ("A2A3", 3): (19.830, "relâchement /p/, voyelle à 19,836"),
    ("A2A3", 4): (19.925, "/v/ : creux 19,925-19,945"),
    ("A2A3", 5): (20.020, "tenue du /p/ 20,02-20,04 puis souffle 20,05-20,11"),
    ("A2A3", 6): (20.555, "murmure nasal /n/ 20,555-20,668 (0-400 Hz fort, 1-2,5 kHz effondré)"),
    ("A2A3", 7): (20.785, "liaison /v/ 20,785-20,855"),
    ("A2A3", 9): (21.570, "liaison /z/ 21,57-21,62"),
    ("A2A3", 11): (22.200, "voyelle contre voyelle /u/ → /ɔ̃/ : montée de la bande 400-1000 Hz de 22,19 à 22,24"),
    ("A2A3", 12): (22.370, "liaison /z/ 22,37-22,42"),
    ("C3", 1): (23.490, "tenue voisée du /b/ 23,49-23,58"),
    ("C3", 2): (23.970, "« bah, à » ne font qu'une voyelle (23,60-24,07) : frontière invisible, placée 0,12 s avant le /n/ de « neuf » (Scribe 24,00)"),
    ("C3", 3): (24.085, "/n/ 24,085-24,17"),
    ("C3", 4): (24.260, "liaison /v/ 24,26-24,31"),
    ("C3", 5): (24.405, "/s/ sourd 24,405-24,445"),
    ("C3", 6): (24.565, "tenue du /p/ 24,565-24,62"),
    ("A4", 1): (26.590, "/ʒ/ 26,595"),
    ("A4", 2): (26.695, "/v/ 26,695-26,74"),
    ("A4", 3): (26.785, "/n/"),
    ("A4", 4): (26.955, "relâchement du /t/ de « note » puis /s/ 26,955-27,035"),
    ("A4", 5): (27.115, "tenue du /p/ 27,115-27,17"),
    ("A4", 6): (27.250, "/f/ sourd 27,255-27,335 (le /ʁ/ de « pour » s'y dévoise)"),
    ("A4", 10): (28.695, "/v/ 28,695-28,75 (28,61 est le /sj/ de « -tion »)"),
    ("A4", 11): (29.380, "attaque après la pause de la virgule (29,30-29,37)"),
    ("A4", 12): (29.450, "/s/ hors bande téléphone : placé après le /lə/ (29,38-29,44)"),
    ("A4", 16): (30.555, "/n/ 30,555-30,60"),
    ("A4", 17): (30.675, "liaison /v/ 30,675-30,735"),
    ("A4", 22): (32.315, "tenue voisée du /d/ 32,315-32,36"),
    ("A4", 23): (32.435, "tenue sourde du /k/ 32,435-32,50"),
    ("C4", 1): (34.795, "/m/ 34,795-34,84"),
    ("C4", 2): (35.070, "tenue voisée du /b/ 35,075-35,12"),
    ("C4", 4): (35.710, "/ʁ/ 35,715"),
    # 28/09, l'échange du prénom (AP, CP ; décalage −37,77, relevé Scribe complémentaire) : spectre par bandes et LPC
    ("AP", 0): (25.515, "relâchement du /t/ 25,515 (1-2,5 kHz), /ʁ/ dévoisé jusqu'à 25,58, /ɛ/ voisé dès 25,585 (le seuil RMS ne voit que 25,54)"),
    ("AP", 1): (25.660, "tenue voisée du /b/ 25,66-25,71 (graves tenus, aigus effondrés), relâchement 25,715, /j/ 25,72-25,765"),
    ("AP", 2): (26.105, "/s/ 26,105-26,21 : la bande 2,5-4 kHz sort du souffle à 26,105 ; /ɛ/ voisé dès 26,215"),
    ("AP", 4): (26.400, "tenue sourde du /k/ 26,40-26,43, relâchement 26,435 (1-4 kHz)"),
    ("AP", 5): (26.585, "tenue du /p/ 26,585-26,593, relâchement 26,595"),
    ("CP", 0): (28.060, "/s/ faible (la ligne coupe au-dessus de 4 kHz) : 2,5-4 kHz à moins de 10 dB de son maximum (28,10) dès 28,06 ; la porte s'ouvre à 28,02 sur sa montée ; /ɛ/ voisé dès 28,125"),
    ("CP", 1): (28.195, "tenue du /p/ 28,195-28,205, relâchement 28,21 (l'attaque d'énergie 28,13 est le /ɛ/ de « C'est »)"),
    ("CP", 2): (28.295, "/f/ sourd 28,295-28,375 (le /ʁ/ de « pour » s'y dévoise, comme dans A4), /l/ voisé dès 28,375"),
}
# Attaque de la voyelle (centre perceptif : l'instant où l'on « entend » le mot) des mots qui portent
# une synchro forte. Les sauts du point se posent sur ces instants.
VOYELLES = {
    ("A1", 0): 5.020,
    ("A2A3", 6): 20.672,
    ("A2A3", 8): 21.430,
    ("A2A3", 11): 22.205,
    ("C3", 2): 23.970,
    ("C3", 3): 24.180,
    ("A4", 0): 26.255,
    ("A4", 6): 27.355,
    ("A4", 12): 29.470,
    ("A4", 18): 31.400,
    ("A4", 21): 32.115,
    ("C4", 0): 34.515,
    # 28/09, l'échange du prénom : toutes ses voyelles (l'image y cale la plume qui écoute, puis l'encre du nom)
    ("AP", 0): 25.585,          # « Très » : /ɛ/ voisé après /tʁ/ dévoisé
    ("AP", 1): 25.770,          # « bien. » : /ɛ̃/ après /bj/ (25,715-25,765)
    ("AP", 2): 26.215,          # « C'est » : /ɛ/ après le /s/
    ("AP", 3): 26.320,          # « pour » : /u/ après le relâchement du /p/ (26,30)
    ("AP", 4): 26.460,          # « quel » : /ɛ/ après le /k/ aspiré (26,435-26,455)
    ("AP", 5): 26.675,          # « prénom ? » : /e/ (F1 ≈ 500, F2 ≈ 2 070 Hz) après /pʁ/ dévoisé (26,595-26,665) ; /ɔ̃/ de « -nom » dès 26,775
    ("CP", 0): 28.125,          # « C'est » : /ɛ/ après le /s/ faible
    ("CP", 1): 28.210,          # « pour » : /u/ au relâchement du /p/
    ("CP", 2): 28.395,          # « Florian. » : /ɔ/ de « Flo » (voir REPERES_SYLLABES, florian_*)
}
# Repères hors mots (secondes film).
REPERES_SYLLABES = {
    "confirmation_derniere_syllabe": {"extrait": "A4", "debut": 32.815, "voyelle": 32.955,
                                      "raison": "« -tion » : /s/ sourd 32,815-32,94, puis /jɔ̃/ 32,955-33,04 (dernière bouffée d'énergie)"},
    # « Florian » dit par l'appelant (CP, 28/09) en trois temps, Flo·ri·an : l'image y écrit le nom sous la voix.
    # Relevé sur le spectre par bandes (0-400 / 400-1 000 / 1 000-2 500 / 2 500-4 000 Hz) et une LPC d'ordre 10 à 8 kHz,
    # fenêtres de 25 ms au pas de 5 ms. debut = entrée de la syllabe, voyelle = attaque de sa voyelle, fin = entrée de la suivante.
    "florian_flo": {"extrait": "CP", "texte": "Flo", "debut": 28.295, "voyelle": 28.395, "fin": 28.475,
                    "raison": "/f/ sourd 28,295-28,375, /l/ 28,375-28,39, /ɔ/ 28,395-28,47 (F1 640-760 Hz, F2 1 000-1 030 Hz)"},
    "florian_ri": {"extrait": "CP", "texte": "ri", "debut": 28.475, "voyelle": 28.515, "fin": 28.580,
                   "raison": "/ʁ/ 28,475-28,51 (F2 1 040 → 850 Hz, 2,5-4 kHz qui monte), /i/ 28,515-28,575 (F2 1 630-1 770 Hz, 2,5-4 kHz au plus haut)"},
    "florian_an": {"extrait": "CP", "texte": "an", "debut": 28.580, "voyelle": 28.600, "fin": 28.700,
                   "raison": "glissement /i/ → /ɑ̃/ dès 28,58 (F2 1 600 → 1 000 Hz jusqu'à 28,62), /ɑ̃/ 28,62-28,70 (F2 ≈ 1 000 Hz) ; "
                             "voix éteinte à 28,70 (fin du mot), queue jusqu'à 28,73"},
}


def cle(m):
    m = m.replace("’", "'").lower()
    m = unicodedata.normalize("NFD", m)
    m = "".join(c for c in m if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9'\-]", "", m).strip("'-")


# Équivalences ASR → texte exact (nombres écrits en chiffres, variantes d'orthographe entendues)
EQUIV = {"19": "dix-neuf", "mocha": "moka", "moca": "moka", "ben": "bah", "alice": "elise"}


def mots_exacts(texte):
    """Découpe le texte dit ; « ! » et « ? » isolés se collent au mot précédent (espace fine U+202F)."""
    sortie = []
    for tok in texte.split():
        if re.fullmatch(r"[!?;:]", tok) and sortie:
            sortie[-1] += " " + tok
        else:
            sortie.append(tok)
    return sortie


def lire(chemin):
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(chemin), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, dtype="<f4").astype(np.float64)


def rms_db(sig, hop=0.010):
    w = int(hop * SR)
    n = len(sig) // w
    x = sig[:n * w].reshape(n, w)
    return 20 * np.log10(np.sqrt((x ** 2).mean(axis=1)) + 1e-12)   # fenêtre k = [k·hop, (k+1)·hop)


def bande_db(sig, lo=400, hi=2500, hop=0.005, n=400):
    """Énergie de bande sur fenêtres de 25 ms, pas de 5 ms ; valeur k centrée en k·hop + 12,5 ms."""
    h = int(hop * SR)
    k = (len(sig) - n) // h
    idx = np.arange(n)[None, :] + h * np.arange(k)[:, None]
    P = np.abs(np.fft.rfft(sig[idx] * np.hanning(n), axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1 / SR)
    return 10 * np.log10(P[:, (f >= lo) & (f < hi)].sum(axis=1) + 1e-12)


def transcrire_hf():
    if not HF_JSON.exists():
        d = PROJET / "son" / "_hf"
        d.mkdir(exist_ok=True)
        subprocess.run([HF, "transcribe", str(WAV), "-d", str(d), "-m", "small", "-l", "fr", "--json"], check=True)
        (d / "transcript.json").rename(HF_JSON)
    return json.loads(HF_JSON.read_text())


def appeler_scribe(mono_wav):
    """ElevenLabs Scribe v1 (fr, mots horodatés, locuteurs) sur un wav mono 16 kHz (octets) : la réponse JSON."""
    b = uuid.uuid4().hex
    champ = lambda n, v: f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode()
    corps = (champ("model_id", "scribe_v1") + champ("language_code", "fra") + champ("timestamps_granularity", "word")
             + champ("tag_audio_events", "false") + champ("diarize", "true")
             + f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="dialogue.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
             + mono_wav + f"\r\n--{b}--\r\n".encode())
    cle_api = Path("/root/.secrets/vokio-ads-elevenlabs").read_text().strip()
    r = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=corps,
                               headers={"xi-api-key": cle_api, "Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(r, timeout=300) as x:
        return json.loads(x.read())


def transcrire_scribe():
    if not SCRIBE_JSON.exists():
        mono = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WAV), "-ac", "1", "-ar", "16000", "-f", "wav", "-"],
                              capture_output=True, check=True).stdout
        SCRIBE_JSON.write_text(json.dumps(appeler_scribe(mono), ensure_ascii=False, indent=1))
    return [w for w in json.loads(SCRIBE_JSON.read_text())["words"] if w["type"] == "word" and cle(w["text"])]


def releves_complementaires(dia):
    """Extraits ajoutés APRÈS le relevé Scribe du 26/09 (absents de DECALAGES_RELEVES ; 28/09 : AP et CP, l'échange du
    prénom) : un relevé Scribe par groupe d'extraits consécutifs, fait sur ce groupe seul (son/dialogue.wav de
    film_in − 0,15 s à film_out + 0,15 s, sans déborder sur les extraits voisins), en cache dans
    son/transcription-scribe-complements.json : {"releves": [{"extraits": {id: décalage film − source au relevé},
    "de", "a", "words": [temps FILM au relevé]}]}. Rappelé seulement pour un extrait qu'aucun relevé ne couvre."""
    cache = json.loads(SCRIBE_COMPL.read_text()) if SCRIBE_COMPL.exists() else {"releves": []}
    couverts = {i for r in cache["releves"] for i in r["extraits"]}
    ex = dia["extraits"]
    groupes, g = [], []
    for k, e in enumerate(ex):
        if e["id"] not in DECALAGES_RELEVES and e["id"] not in couverts:
            g.append(k)
        elif g:
            groupes.append(g)
            g = []
    if g:
        groupes.append(g)
    for g in groupes:
        a = ex[g[0]]["film_in"] - 0.15
        b = ex[g[-1]]["film_out"] + 0.15
        if g[0] > 0:
            a = max(a, ex[g[0] - 1]["film_out"])
        if g[-1] + 1 < len(ex):
            b = min(b, ex[g[-1] + 1]["film_in"])
        mono = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WAV), "-ss", f"{a:.6f}", "-t", f"{b - a:.6f}",
                               "-ac", "1", "-ar", "16000", "-f", "wav", "-"], capture_output=True, check=True).stdout
        r = appeler_scribe(mono)
        cache["releves"].append({
            "extraits": {ex[k]["id"]: ex[k]["decalage_film_moins_source"] for k in g}, "de": round(a, 6), "a": round(b, 6),
            "fichier": str(WAV), "texte": r.get("text"),
            "words": [dict(w, start=round(w["start"] + a, 3), end=round(w["end"] + a, 3)) for w in r["words"]]})
        SCRIBE_COMPL.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
        print("relevé Scribe complémentaire :", [ex[k]["id"] for k in g], f"{a:.2f} → {b:.2f} s")
    return cache["releves"]


def lire_decale(n):
    """son/dialogue.wav avancé de n échantillons à 48 kHz (n > 0 : ce qui est à t est lu à t − n/48 000), puis lu comme
    lire(WAV) : même décodage, même rééchantillonnage. Un extrait qui a glissé de n échantillons depuis son relevé se
    retrouve ainsi À L'ÉCHANTILLON PRÈS là où il était relevé, et son analyse (fenêtres de 10 ms, bande 5 ms) est celle du
    relevé : ses mots glissent exactement avec lui, même d'un nombre d'images qui n'est pas un multiple de 10 ms."""
    import tempfile
    brut = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(WAV), "-f", "s32le", "-"],
                          capture_output=True, check=True).stdout
    x = np.frombuffer(brut, dtype="<i4").reshape(-1, 2)
    y = np.zeros_like(x)
    if n >= 0:
        y[:len(x) - n] = x[n:]
    else:
        y[-n:] = x[:len(x) + n]
    racine = "/dev/shm" if Path("/dev/shm").is_dir() else None
    with tempfile.TemporaryDirectory(dir=racine) as d:
        tmp = Path(d) / "decale.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s32le", "-ar", str(SR_DIALOGUE), "-ac", "2", "-i", "-",
                        "-c:a", "pcm_s24le", str(tmp)], input=y.tobytes(), check=True)
        return lire(tmp)


def signe(v):
    """+3.066667, -0.47 : le glissement lisible, sans zéros inutiles."""
    return f"{v:+.6f}".rstrip("0").rstrip(".")


def analyse(sig):
    db10 = rms_db(sig)
    return db10, db10 > -40, bande_db(sig)


def main():
    dia = json.loads(DIALOGUE.read_text())
    releves = releves_complementaires(dia)
    dec_releve = dict(DECALAGES_RELEVES)
    for r in releves:
        dec_releve.update(r["extraits"])
    # Glissement de chaque extrait depuis son relevé. En échantillons (48 kHz) quand dialogue.json les donne : exact.
    glisse = {}
    for e in dia["extraits"]:
        if "decalage_echantillons" in e:
            glisse[e["id"]] = e["decalage_echantillons"] - int(round(dec_releve[e["id"]] * SR_DIALOGUE))
        else:
            glisse[e["id"]] = int(round((e["decalage_film_moins_source"] - dec_releve[e["id"]]) * SR_DIALOGUE))
    delta = {k: n / SR_DIALOGUE for k, n in glisse.items()}
    delta_aff = {k: round(v, 6) for k, v in delta.items()}
    if any(delta.values()):
        print("extraits déplacés depuis les relevés :", {k: v for k, v in delta_aff.items() if v})
    sig = lire(WAV)
    analyses = {0: analyse(sig)}            # chaque extrait est analysé dans le repère de SON relevé
    for n in sorted(set(glisse.values()) - {0}):
        analyses[n] = analyse(lire_decale(n))
    hf = [w for w in transcrire_hf() if cle(w["text"])]
    sc = transcrire_scribe()
    # relevés complémentaires insérés dans l'ordre du film (après les mots de l'extrait qui précède leur groupe)
    for r in releves:
        k0 = min(k for k, e in enumerate(dia["extraits"]) if e["id"] in r["extraits"])
        borne = -1e9
        if k0 > 0:
            prec = dia["extraits"][k0 - 1]
            borne = prec["source_out"] + dec_releve[prec["id"]]
        pos = next((q for q, w in enumerate(sc) if w["start"] >= borne), len(sc))
        sc[pos:pos] = [w for w in r["words"] if w["type"] == "word" and cle(w["text"])]

    ecrits_tous = []
    for e in dia["extraits"]:
        for q, m in enumerate(mots_exacts(e["texte"])):
            ecrits_tous.append({"texte": m, "cle": cle(m), "extrait": e["id"], "rang": q, "locuteur": e["locuteur"]})
    EX = {e["id"]: e for e in dia["extraits"]}
    # bords de chaque extrait dans le repère de son relevé
    bord_r = {k: (e["film_in"] - delta[k], e["film_out"] - delta[k]) for k, e in EX.items()}

    # Scribe → texte exact (temps dans le repère du relevé de chaque mot)
    a = [EQUIV.get(cle(w["text"]), cle(w["text"])) for w in sc]
    b = [w["cle"] for w in ecrits_tous]
    est = [None] * len(b)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for k in range(j2 - j1):
                est[j1 + k] = sc[i1 + k]["start"]
    # mots que Scribe n'a pas rendus : interpolés dans leur extrait
    for j, w in enumerate(ecrits_tous):
        if est[j] is None:
            r_in, r_out = bord_r[w["extrait"]]
            g = next((est[q] for q in range(j - 1, -1, -1) if est[q] is not None and ecrits_tous[q]["extrait"] == w["extrait"]), r_in)
            d = next((est[q] for q in range(j + 1, len(b)) if est[q] is not None and ecrits_tous[q]["extrait"] == w["extrait"]), r_out)
            est[j] = (g + d) / 2
            w["scribe_absent"] = True

    for j, w in enumerate(ecrits_tous):
        r_in, r_out = bord_r[w["extrait"]]
        db10, voix, bd = analyses[glisse[w["extrait"]]]
        t = est[j]
        source = "scribe"
        # 1. attaque après un blanc
        k0 = int(round(t / 0.010))
        att = [k for k in range(max(k0 - 10, 4), k0 + 11)
               if voix[k] and not voix[k - 4:k].any() and r_in <= k * 0.010 <= r_out]
        if att:
            k = min(att, key=lambda z: abs(z - k0))
            t, source = round(k * 0.010, 3), "attaque"
        else:
            # 2. creux de la bande 400-2500 Hz
            c0 = int(round((t - 0.0125) / 0.005))
            fen = range(c0 - 16, c0 + 13)
            mn = min(fen, key=lambda z: bd[z])
            g = bd[max(0, mn - 16):mn].max(initial=-200)
            d = bd[mn + 1:mn + 17].max(initial=-200)
            if min(g, d) - bd[mn] >= 5.0 and mn not in (fen.start, fen.stop - 1):
                t, source = round(mn * 0.005 + 0.0125, 3), "creux"
        if (w["extrait"], w["rang"]) in REVUES:
            t, raison = REVUES[(w["extrait"], w["rang"])]
            source = "revue : " + raison + (f" (relevé translaté de {signe(delta_aff[w['extrait']])} s avec l'extrait)" if glisse[w["extrait"]] else "")
        w["debut_r"] = round(t, 3)
        w["source"] = source
        w["scribe_r"] = est[j]

    # ordre strict dans chaque extrait
    for x, y in zip(ecrits_tous, ecrits_tous[1:]):
        if y["extrait"] == x["extrait"] and y["debut_r"] <= x["debut_r"]:
            y["debut_r"] = round(x["debut_r"] + 0.02, 3)
            y["source"] += " (poussé pour l'ordre)"
    # fins : dernière fenêtre voisée avant le mot suivant de l'extrait (ou la sortie de l'extrait)
    for j, w in enumerate(ecrits_tous):
        voix = analyses[glisse[w["extrait"]]][1]
        suiv = ecrits_tous[j + 1] if j + 1 < len(ecrits_tous) and ecrits_tous[j + 1]["extrait"] == w["extrait"] else None
        borne = suiv["debut_r"] if suiv else bord_r[w["extrait"]][1]
        ka, kb = int(round(w["debut_r"] / 0.010)), int(round(borne / 0.010))
        v = [k for k in range(ka, kb) if voix[k]]
        w["fin_r"] = round((v[-1] + 1) * 0.010, 3) if v else round(min(borne, w["debut_r"] + 0.06), 3)
        if suiv and suiv["debut_r"] - w["fin_r"] < 0.035:   # parole liée : la fin est l'entrée du suivant
            w["fin_r"] = suiv["debut_r"]
    # repère du relevé → temps du film : + le glissement exact de l'extrait (images : entières si le glissement l'est)
    for j, w in enumerate(ecrits_tous):
        dl, n = delta[w["extrait"]], glisse[w["extrait"]]
        dr = w.pop("debut_r")
        w["debut"] = round(dr + dl, 6)
        w["fin"] = round(w.pop("fin_r") + dl, 6)
        w["scribe"] = round(w.pop("scribe_r") + dl, 3)
        n_img = n / (SR_DIALOGUE / FPS)
        if n and abs(n_img - round(n_img)) < 1e-9:      # glissement d'un nombre entier d'images : image exacte
            w["image"] = int(round(dr * FPS)) + int(round(n_img))
        else:
            w["image"] = int(round(w["debut"] * FPS))
        if (w["extrait"], w["rang"]) in VOYELLES:
            w["voyelle"] = round(VOYELLES[(w["extrait"], w["rang"])] + dl, 6)

    # contrôles de cohérence
    erreurs = []
    for x, y in zip(ecrits_tous, ecrits_tous[1:]):
        if y["debut"] < x["fin"] - 1e-6:
            erreurs.append(f"chevauchement : {x['texte']} → {y['texte']}")
    for w in ecrits_tous:
        d = w["fin"] - w["debut"]
        if d < 0.025 or d > 1.2:   # « Je » élidé de « Je peux » ([ʃpø]) dure 30 ms
            erreurs.append(f"durée {d:.2f} s : {w['texte']} ({w['extrait']} #{w['rang']})")
        ex = EX[w["extrait"]]
        if not (ex["film_in"] - 1e-6 <= w["debut"] < w["fin"] <= ex["film_out"] + 1e-6):
            erreurs.append(f"hors extrait : {w['texte']}")
        if w["source"] == "scribe":
            erreurs.append(f"(info) sans repère d'énergie, Scribe gardé : {w['texte']} ({w['extrait']} #{w['rang']})")

    sm = difflib.SequenceMatcher(None, [EQUIV.get(cle(x["text"]), cle(x["text"])) for x in hf], b, autojunk=False)
    ecarts = [hf[i]["start"] + delta[ecrits_tous[j]["extrait"]] - ecrits_tous[j]["debut"] for a_, b_, n in sm.get_matching_blocks()
              for i, j in zip(range(a_, a_ + n), range(b_, b_ + n))
              if ecrits_tous[j]["extrait"] in DECALAGES_RELEVES]

    for w in ecrits_tous:
        print(f"{w['extrait']:5s} {w['rang']:2d} {w['texte']:18s} {w['debut']:9.6f} → {w['fin']:9.6f}  img {w['image']:4d}  "
              f"scribe {w['scribe']:6.2f} ({w['debut'] - w['scribe']:+.2f})  {w['source']}")
    print(f"\nhf transcribe : {len(ecarts)}/{len(b)} mots appariés, écart médian {np.median(ecarts):+.2f} s, "
          f"max {np.max(np.abs(ecarts)):.2f} s (indice d'ordre seulement)")
    print("\n".join("⚠ " + x for x in erreurs) or "cohérence : ok")
    SORTIE.parent.mkdir(exist_ok=True)
    syl = {}
    for k, v in REPERES_SYLLABES.items():
        dl = delta[v["extrait"]]
        syl[k] = {c: round(v[c] + dl, 6) for c in ("debut", "voyelle", "fin") if c in v} | {"raison": v["raison"]}
        if "texte" in v:
            syl[k] = {"texte": v["texte"], "extrait": v["extrait"]} | syl[k]
    SORTIE.write_text(json.dumps({
        "unite": "secondes FILM (t = 0 à l'image 0) ; image = round(debut × 30)",
        "methode": __doc__.strip().splitlines()[0] + " Texte exact de la transcription d'origine ; estimation ElevenLabs Scribe ; "
                   "bords par l'énergie de son/dialogue.wav ; corrections à la main sur le spectre (champ source).",
        "mots": [{k: w[k] for k in ("texte", "cle", "debut", "fin", "image", "locuteur", "extrait", "rang", "source", "scribe")
                  if k in w} | ({"voyelle": w["voyelle"]} if "voyelle" in w else {}) for w in ecrits_tous],
        "syllabes": syl,
        "decalages_depuis_releves": delta_aff,
    }, ensure_ascii=False, indent=1))
    print(f"→ {SORTIE} ({len(ecrits_tous)} mots)")
    return 1 if [x for x in erreurs if not x.startswith("(info)")] else 0


if __name__ == "__main__":
    sys.exit(main())
