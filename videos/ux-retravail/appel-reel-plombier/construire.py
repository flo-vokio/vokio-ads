#!/usr/bin/env python3
"""Retravail HyperFrames de « L'appel réel » plombier.

Écrit index.html (composition HyperFrames autonome) à partir de la SOURCE de
vérité de l'original : les COUPES, ECRITURE et film() de
/opt/vokio-site-repo/design/videos/ux-vertical/monter_appel_reel.py sont
importés tels quels (lecture seule), puis comparés aux valeurs réellement
injectées dans l'index.html de l'original. Si un seul instant diffère, on
s'arrête : chaque mot du résumé doit s'écrire au même instant que dans le
film d'origine.

    construire.py            écrit index.html
"""
import json
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/opt/vokio-site-repo/design/videos/ux-vertical")
sys.path.insert(0, "/opt/vokio-site-repo/design/videos")
import monter_appel_reel as O                                  # noqa: E402

ORIG_HTML = "/root/vokio-uploads/videos/ux-210926/appel-reel-plombier/index.html"
MESURES = O.MESURES

# ── Les instants, recalculés exactement comme l'original ──────────────────
fin_parole = O.film(O.FIN_PAROLE)
T = dict(
    etatIn=300, carteIn=O.film(0.58) - 300, t1In=O.film(0.58) + 900,
    pastilleIn=O.film(O.PASTILLE), t2In=O.film(O.PASTILLE) + 200,
    t3In=O.film(42.6), t4In=O.film(58.8),
    finEcriture=O.film(O.ECRITURE[-1][1]), finParole=fin_parole,
    t5In=fin_parole + 300,
    agendaIn=fin_parole + 2600, impactIn=fin_parole + 5800,
    clairIn=fin_parole + 9000, finIn=fin_parole + 9400, fin=fin_parole + 12400,
)
ECRITURE = [[O.film(a), O.film(b), de, vers] for a, b, de, vers in O.ECRITURE]

# contrôle contre ce que l'original a réellement rendu
src = open(ORIG_HTML, encoding="utf-8").read()
T_orig = json.loads(re.search(r"const T = (\{.*?\});", src).group(1))
E_orig = json.loads(re.search(r"const ECRITURE = (\[.*?\]);", src).group(1))
if T_orig != T or E_orig != ECRITURE:
    sys.exit(f"désaccord avec l'original :\n{T}\n{T_orig}\n{ECRITURE}\n{E_orig}")

# ── Géométrie : la carte réelle à 960 px de large ─────────────────────────
mes = json.load(open(MESURES))
CARTE_W = 960
RASTER_W, RASTER_H = 1044, 934           # carte-pleine-sans-lien.png (×3, sans Rappeler ni lien)
k = CARTE_W / RASTER_W
kp = 3 * k
MOTS = [{"x": round(m["x"] * kp, 1), "y": round(m["y"] * kp, 1),
         "w": round(m["w"] * kp, 1), "h": round(m["h"] * kp, 1)} for m in mes["mots"]]
CARTE_H = round(RASTER_H * k)
c = mes["chip"]
PAST = dict(x=round((c["x"] - 2) * kp, 1), y=round((c["y"] - 2) * kp, 1), w=round((c["w"] + 4) * kp, 1))
CUR_H = round((mes["mots"][0]["h"] + 4) * kp)

AG_W = 960
AG_K = AG_W / 1050                        # agenda-jour.png fait 1050 px de large
# le bloc « M. Estève » dans agenda-jour.png (px d'image) : x 183→993, y 561→711
AG_FOYER = (round((183 + 993) / 2 * AG_K), round((561 + 711) / 2 * AG_K))

FIN_S = T["fin"] / 1000

HTML = open(os.path.join(ICI, "gabarit.tpl"), encoding="utf-8").read()
for cle, val in {
    "__FIN_S__": f"{FIN_S:.3f}",
    "__AUDIO_S__": "75.136",
    "__CARTE_W__": str(CARTE_W), "__CARTE_H__": str(CARTE_H),
    "__PAST_X__": str(PAST["x"]), "__PAST_Y__": str(PAST["y"]), "__PAST_W__": str(PAST["w"]),
    "__CUR_H__": str(CUR_H),
    "__AG_W__": str(AG_W), "__AG_FX__": str(AG_FOYER[0]), "__AG_FY__": str(AG_FOYER[1]),
    "__T__": json.dumps(T), "__MOTS__": json.dumps(MOTS), "__ECRITURE__": json.dumps(ECRITURE),
}.items():
    if cle not in HTML:
        sys.exit(f"{cle} absent du gabarit")
    HTML = HTML.replace(cle, val)
open(os.path.join(ICI, "index.html"), "w", encoding="utf-8").write(HTML)
print(f"index.html : {FIN_S:.2f} s, carte {CARTE_W}×{CARTE_H}, {len(MOTS)} mots, "
      f"écriture identique à l'original ({len(ECRITURE)} phrases)")
