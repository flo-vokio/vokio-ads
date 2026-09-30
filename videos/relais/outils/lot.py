#!/usr/bin/env python3
"""Fiche de passation d'un lot de cartes vidéo (intégration sur les pages métier) : usage en une ligne :

    python3 outils/lot.py LOT-A.json <metier> [<metier> …]

  Pour chaque métier (recette <metier>/recette.json, vidéos déjà livrées) : durée exacte de la complète (ffprobe), data-duree
  à poser, temps affiché du lecteur, fichiers livrés et leurs poids, transcription CORRIGÉE d'après l'audio (paragraphes
  tr-vokio / tr-client prêts à coller, même balisage que la page), et les écarts avec la transcription de la page (mot à mot,
  par paragraphe aligné). Réécrit seulement les métiers passés (les autres entrées du fichier sont gardées).
"""
import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
SORTIES = Path("/root/vokio-uploads/videos/relais")
sys.path.insert(0, str(ICI))


def duree(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True, check=True).stdout)


def mots(t):
    return re.findall(r"[\wÀ-ÿ’'-]+|[?!.,…:;]", t.replace("--", " "))


def ecarts(page, dit):
    """Écarts mot à mot entre la page et le dit (alignement global de toute la transcription)."""
    P = [(i, w) for i, p in enumerate(page) for w in mots(p["texte"])]
    Dd = [(i, w) for i, e in enumerate(dit) for w in mots(e["texte"])]
    k = lambda w: re.sub(r"[^\wÀ-ÿ]", "", w.lower().replace("’", "'"))
    sm = SequenceMatcher(None, [k(w) for _, w in P], [k(w) for _, w in Dd], autojunk=False)
    out = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            continue
        pa = " ".join(w for _, w in P[a0:a1]); di = " ".join(w for _, w in Dd[b0:b1])
        if not re.sub(r"[?!.,…:;\s]", "", pa + di):
            continue                      # ponctuation seule
        ctx = " ".join(w for _, w in Dd[max(0, b0 - 4):b0])
        out.append({"page": pa, "dit": di, "apres": ctx, "enonce": Dd[b0][0] if b0 < len(Dd) else None})
    return out


def entree(m):
    from brouillon import carte
    R = json.loads((RACINE / m / "recette.json").read_text())
    c = carte(m)
    fc = SORTIES / f"{R['nom']}-complete.mp4"
    d = duree(fc)
    ag = R.get("agente") or c["agente"]
    paras = [f'<p class="{"tr-vokio" if e["qui"] == "agente" else "tr-client"}"><b>{ag if e["qui"] == "agente" else "L’appelant"}</b>'
             f'{e.get("transcription", e["texte"])}</p>' for e in R["enonces"]]
    fichiers = {f.name: f.stat().st_size for f in sorted(SORTIES.glob(f"{R['nom']}-*"))}
    return {"carte": R["carte"], "jour_heure": c["jour_heure"], "audio": c["audio"],
            "duree_complete_s": round(d, 6), "data_duree": f"{d:.2f}", "temps_affiche": f"{round(d) // 60}:{round(d) % 60:02d}",
            "fichiers": fichiers, "transcription_corrigee": "\n".join(paras),
            "ecarts_avec_la_page": ecarts(c["transcription"], [{"qui": e["qui"], "texte": e.get("transcription", e["texte"])} for e in R["enonces"]]),
            "non_sous_titre": json.loads((RACINE / m / "controles.json").read_text())["detail"].get("complete", {}).get("non_sous_titre", {}).get("detail")
            if (RACINE / m / "controles.json").exists() else None}


def main():
    f = Path(sys.argv[1])
    f = f if f.is_absolute() else RACINE / f
    L = json.loads(f.read_text()) if f.exists() else {}
    for m in sys.argv[2:]:
        L[m] = entree(m)
        print(m, L[m]["data_duree"], f"{len(L[m]['ecarts_avec_la_page'])} écart(s)")
    f.write_text(json.dumps(L, ensure_ascii=False, indent=1))
    print("écrit :", f)


if __name__ == "__main__":
    main()
