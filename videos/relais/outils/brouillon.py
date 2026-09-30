#!/usr/bin/env python3
"""Brouillon de recette d'une page métier de vokio.fr : la carte de l'APPEL RÉEL (celle qui porte le `.lecteur`) + le relevé
Scribe de son audio, pour écrire <metier>/recette.json vite et juste : usage en une ligne :

    python3 outils/brouillon.py <metier> [--ecrire]

  Lit /opt/vokio-site-repo/<metier>/index.html (lecture seule) : eyebrow (.n), jour et heure (.t), phrase, audio du lecteur,
  prénom de l'agente, transcription de la page. Relève l'audio (Scribe, cache <metier>/cache/scribe.json), regroupe les mots
  par locuteur (et par silence de plus de 1,1 s : « Un instant. » devient un énoncé), puis affiche énoncés dits et
  paragraphes de la page côte à côte. --ecrire : pose <metier>/recette.json (énoncés dits, à compléter : situation, objets,
  boucle) s'il n'existe pas. Aussi en module : carte(metier), enonces_dits(metier), transcription_page(metier).
"""
import html as H
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
SITE = Path("/opt/vokio-site-repo")
sys.path.insert(0, str(ICI))


def _txt(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def carte(metier):
    page = (SITE / metier / "index.html").read_text() if metier not in ("coiffure", "restaurant", "auto-ecole") else (SITE / "index.html").read_text()
    if metier in ("coiffure", "restaurant", "auto-ecole"):
        i = page.index(f"appel-{metier}.mp3")
        a = page.rindex('<div class="temps-card">', 0, i)
    else:
        i = page.index('class="lecteur"')
        a = max(page.rindex('<div class="ec-card', 0, i), page.rindex('<div class="temps-card', 0, i) if '<div class="temps-card' in page[:i] else -1)
    b = page.index("</details>", i)
    bloc = page[a:b]
    g = lambda motif: (re.search(motif, bloc, re.S) or [None, ""])[1]
    paras = [(m.group(1), _txt(m.group(2)), _txt(m.group(3))) for m in
             re.finditer(r'<p class="(tr-vokio|tr-client)"><b>(.*?)</b>(.*?)</p>', bloc, re.S)]
    agente = next((p[1] for p in paras if p[0] == "tr-vokio"), "")
    return {"metier": metier, "eyebrow": _txt(g(r'<div class="n mono">(.*?)</div>')), "jour_heure": _txt(g(r'<div class="t">(.*?)</div>')),
            "phrase": _txt(g(r'</div>\s*<p>(.*?)</p>')), "audio": "/opt/vokio-site-repo" + g(r'data-src="([^"]+)"'),
            "agente": agente, "transcription": [{"qui": "agente" if p[0] == "tr-vokio" else "appelant", "texte": p[2]} for p in paras]}


def enonces_dits(metier, audio=None):
    from scribe import transcrire
    c = carte(metier)
    mots = transcrire(audio or c["audio"], RACINE / metier / "cache" / "scribe.json")
    agente_sp = mots[0].get("speaker_id")
    E, cur, sp, fin = [], [], None, 0
    for w in mots:
        s = w.get("speaker_id")
        if cur and (s != sp or w["start"] - fin > 1.1):
            E.append({"qui": "agente" if sp == agente_sp else "appelant", "texte": " ".join(x["text"] for x in cur).replace(" ?", " ?").replace(" !", " !"),
                      "t": round(cur[0]["start"], 2)})
            cur = []
        cur.append(w); sp = s; fin = w["end"]
    if cur:
        E.append({"qui": "agente" if sp == agente_sp else "appelant", "texte": " ".join(x["text"] for x in cur).replace(" ?", " ?").replace(" !", " !"),
                  "t": round(cur[0]["start"], 2)})
    for e in E:                                 # typographie du site : apostrophe courbe, points de suspension
        e["texte"] = e["texte"].replace("'", "’").replace("...", "…").replace(" ?", " ?").replace(" !", " !")
    return E


def transcription_page(metier):
    return carte(metier)["transcription"]


def main():
    m = sys.argv[1]
    c = carte(m)
    print(json.dumps({k: v for k, v in c.items() if k != "transcription"}, ensure_ascii=False, indent=1))
    E = enonces_dits(m, c["audio"])
    print("\n--- DIT (Scribe) ---")
    for k, e in enumerate(E):
        print(f"E{k:<2} {e['t']:6.2f} {e['qui']:8} {e['texte']}")
    print("\n--- PAGE ---")
    for p in c["transcription"]:
        print(f"   {p['qui']:8} {p['texte']}")
    f = RACINE / m / "recette.json"
    if "--ecrire" in sys.argv and not f.exists():
        R = {"_note": "Brouillon de outils/brouillon.py : énoncés DITS (Scribe), à relire ; compléter situation, objets, boucle.",
             "id": m, "carte": c["eyebrow"], "audio": c["audio"], "nom": f"relais-{m}", "agente": c["agente"],
             "jour_heure": c["jour_heure"], "phrase": c["phrase"],
             "enonces": [{"qui": e["qui"], "texte": e["texte"]} for e in E]}
        f.write_text(json.dumps(R, ensure_ascii=False, indent=2))
        print("\nécrit :", f)


if __name__ == "__main__":
    main()
