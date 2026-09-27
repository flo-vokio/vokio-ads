#!/usr/bin/env python3
"""Piste de dialogue du film « Le point sur le i » : les extraits du VRAI appel, placés aux temps du film.

    python3 son/dialogue.py            écrit son/dialogue.wav + son/dialogue.json, et contrôle chaque coupe

Source : l'appel du 18/09/2026 à 16:51:54 (Paris) sur la ligne de démonstration de la Clinique
vétérinaire du Port, conversation ElevenLabs conv_9401m2tg19wtfxn9cm727n4dtskz, 85 s.
  - originaux/veterinaire.mp3 : l'enregistrement brut (16 kHz mono).
  - montes/veterinaire.wav    : le même, décodé en PCM, avec UNE coupe (66,70 → 70,90 de l'original :
    « Je vérifie les disponibilités. » + « Un instant. »). Vérifié par corrélation (26/09) : identique à
    l'échantillon près avant 66,70, et montes = original − 4,20 après 70,90. Aucun autre blanc raboté.
On coupe dans montes (PCM, pas de second décodage MP3).

Règles :
  - on ne coupe QUE dans des blancs : énergie < −45 dBFS sur ±20 ms autour de chaque point (fenêtres 10 ms) ;
  - fondus de 15 ms en cosinus surélevé à chaque bord ;
  - aucun traitement : niveau d'origine, pas de normalisation, pas d'égalisation (la chaîne voix de la bible
    est le travail du sound designer, qui repart de ce fichier ou de dialogue.json) ;
  - 48 kHz stéréo (double mono), PCM 24 bits, durée = durée du film. Hors extraits : zéros numériques.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
PROJET = ICI.parent
MONTES = Path("/root/vokio-audios-metiers-180926/montes/veterinaire.wav")
ORIGINAL = Path("/root/vokio-audios-metiers-180926/originaux/veterinaire.json")
SR = 48000
DUREE_FILM = 47.0   # v2, finition du 27/09 : 47,00 s, 1 410 images (le SMS se lit, la fin tient)
FONDU = 0.015

# Décalage montes → original : 0 avant 66,70 ; +4,20 après 70,90 (montes).
def vers_original(t):
    return round(t + (4.20 if t >= 66.70 else 0.0), 3)

# Les sept extraits. source = secondes dans montes/veterinaire.wav ; film = source + decalage.
# texte = mots EXACTS dits dans l'extrait, pris dans la transcription d'origine (originaux/veterinaire.json).
EXTRAITS = [
    {"id": "A1", "locuteur": "agent", "tour_t": 0, "src_in": 0.70, "src_out": 5.80, "decalage": 4.21,
     "texte": "Bonjour, je suis Élise, l'assistante vocale de la Clinique vétérinaire du Port ! Comment puis-je vous aider ?",
     "motif": "Le décroché, en entier."},
    {"id": "C1", "locuteur": "appelant", "tour_t": 7, "src_in": 10.28, "src_out": 13.84, "decalage": 0.22,
     "texte": "mon chat, euh, Moka, euh, mange plus depuis hier",
     "motif": "On retire « Euh, oui, bonjour, j'vous appelle parce que » (fin 9,99) et « et il dort beaucoup, je trouve. » (début 14,01)."},
    {"id": "C2", "locuteur": "appelant", "tour_t": 34, "src_in": 34.76, "src_out": 37.16, "decalage": -20.16,
     "texte": "Euh, demain, vous avez des disponibilités ?",
     "motif": "Le triage saute (15,82 → 34,76) : « Je vois. Est-ce que Moka présente d'autres symptômes… », « Non, non, non, j'ai pas l'impression. », « Très bien. Dans ce cas… Quel jour vous conviendrait le mieux ? »."},
    {"id": "A2A3", "locuteur": "agent", "tour_t": 48, "src_in": 48.66, "src_out": 53.90, "decalage": -31.12,
     "texte": "Laissez-moi voir. Je peux vous proposer neuf heures, dix heures ou onze heures.",
     "motif": "D'un seul tenant, avec le VRAI silence de l'outil next_available_slots (49,49 → 50,95, 1,46 s). Sautés en amont : « Un instant. », validate_date, « Demain, c'est samedi dix-neuf septembre. Pour quelle heure… », « Bah le matin. ». Coupé avant « Le dernier créneau possible de la journée est onze heures trente. Qu'est-ce qui vous arrangerait ? » (54,01)."},
    {"id": "C3", "locuteur": "appelant", "tour_t": 58, "src_in": 58.80, "src_out": 60.54, "decalage": -35.56,
     "texte": "Euh, bah, à neuf heures, c'est parfait.",
     "motif": "Saute « Très bien. C'est pour quel prénom ? » et « C'est pour Florian. » (63,31 → 66,48)."},
    {"id": "A4", "locuteur": "agent", "tour_t": 71, "src_in": 67.24, "src_out": 74.30, "decalage": -41.07,
     "texte": "Parfait, je vous note ça pour Florian, pour une consultation vétérinaire, le samedi dix-neuf septembre à neuf heures. Vous recevrez un SMS de confirmation.",
     "motif": "La confirmation, en entier. Le montage du 18/09 avait déjà retiré la revérification (original 66,70 → 70,90)."},
    {"id": "C4", "locuteur": "appelant", "tour_t": 79, "src_in": 75.05, "src_out": 76.55, "decalage": -41.07,
     "texte": "Super, merci beaucoup. Au revoir.",
     "motif": "L'appelant raccroche : le « De rien, au revoir. » de l'agente (montes 79,23) saute. v2 : décalage −41,07, "
              "le même que A4 : C4 suit A4 après son VRAI blanc de 0,75 s (source 74,30 → 75,05) ; la v1 (−40,60) "
              "l'allongeait de 0,47 s pour loger le SMS pendant l'appel."},
]


def lire(chemin, sr):
    brut = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(chemin), "-af",
                           f"aresample={sr}:resampler=soxr:precision=28", "-f", "f32le", "-ac", "1", "-"],
                          capture_output=True, check=True).stdout
    return np.frombuffer(brut, dtype="<f4").astype(np.float64)


def niveau(sig, sr, t, w=0.010):
    a, b = int(round((t - w / 2) * sr)), int(round((t + w / 2) * sr))
    x = sig[max(0, a):max(0, b)]
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12) if len(x) else -240.0


def max_autour(sig, sr, t, r=0.020):
    return max(niveau(sig, sr, x) for x in np.arange(t - r, t + r + 1e-9, 0.005))


def main():
    orig = json.loads(ORIGINAL.read_text())
    assert orig["conversation_id"] == "conv_9401m2tg19wtfxn9cm727n4dtskz", orig["conversation_id"]
    tours = {(t["t"], t["role"]): t["message"] for t in orig["transcript"] if t["message"]}

    src16 = lire(MONTES, 16000)
    src = lire(MONTES, SR)
    piste = np.zeros(int(round(DUREE_FILM * SR)))
    n_f = int(round(FONDU * SR))
    rampe = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n_f))

    sortie, ok = [], True
    for e in EXTRAITS:
        role = "agent" if e["locuteur"] == "agent" else "user"
        dit = tours[(e["tour_t"], role)]
        # le texte de l'extrait doit être une sous-chaîne contiguë du tour d'origine (ou de deux tours pour A2A3)
        if e["id"] == "A2A3":
            dit = tours[(48, "agent")] + " " + tours[(50, "agent")]
        assert e["texte"] in dit, (e["id"], e["texte"], dit)

        a, b = int(round(e["src_in"] * SR)), int(round(e["src_out"] * SR))
        morceau = src[a:b].copy()
        morceau[:n_f] *= rampe
        morceau[-n_f:] *= rampe[::-1]
        film_in = round(e["src_in"] + e["decalage"], 3)
        film_out = round(e["src_out"] + e["decalage"], 3)
        i = int(round(film_in * SR))
        piste[i:i + len(morceau)] += morceau

        m_in, m_out = max_autour(src16, 16000, e["src_in"]), max_autour(src16, 16000, e["src_out"])
        blanc = m_in < -45 and m_out < -45
        ok &= blanc
        print(f"{e['id']:5s} source {e['src_in']:6.2f} → {e['src_out']:6.2f}  film {film_in:6.2f} → {film_out:6.2f}  "
              f"bords {m_in:6.1f} / {m_out:6.1f} dBFS  {'ok' if blanc else 'PAS DANS UN BLANC'}")
        sortie.append({
            "id": e["id"], "locuteur": e["locuteur"],
            "source": str(MONTES), "source_in": e["src_in"], "source_out": e["src_out"],
            "original_in": vers_original(e["src_in"]), "original_out": vers_original(e["src_out"]),
            "film_in": film_in, "film_out": film_out, "decalage_film_moins_source": e["decalage"],
            "fondu_s": FONDU, "texte": e["texte"], "tour_original_t": e["tour_t"], "motif": e["motif"],
            "bords_dbfs": [round(m_in, 1), round(m_out, 1)],
        })
    for x, y in zip(sortie, sortie[1:]):
        assert x["film_out"] <= y["film_in"], (x["id"], y["id"])

    # 48 kHz, stéréo double mono, 24 bits, niveau d'origine
    st = np.stack([piste, piste], axis=1).astype("<f4")
    wav = ICI / "dialogue.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(wav)], input=st.tobytes(), check=True)
    meta = {
        "fichier": str(wav), "sr": SR, "canaux": 2, "format": "pcm_s24le", "duree_s": DUREE_FILM,
        "niveau": "niveau d'origine de montes/veterinaire.wav, aucun gain, aucun filtre",
        "appel": {"conversation_id": orig["conversation_id"], "debut": "2026-09-18 16:51:54 Europe/Paris",
                  "duree_s": orig["call_duration_secs"], "etablissement": orig["etablissement"],
                  "brut": "/root/vokio-audios-metiers-180926/originaux/veterinaire.mp3",
                  "monte": str(MONTES),
                  "montes_vers_original": "original = montes avant 66,70 ; original = montes + 4,20 après (coupe 66,70 → 70,90 de l'original)"},
        "regle_de_coupe": "énergie < −45 dBFS sur ±20 ms (fenêtres 10 ms, 16 kHz) à chaque bord ; fondus 15 ms cosinus",
        "extraits": sortie,
    }
    (ICI / "dialogue.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(("toutes les coupes tombent dans un blanc" if ok else "ÉCHEC : une coupe hors blanc"), "→", wav)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
