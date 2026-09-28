#!/usr/bin/env python3
"""Fiche de mise en page d'un format, tirée de SES données (le storyboard écrit, vérifiable, jamais recopié) : usage en une ligne :

    python3 outils/fiche_format.py [<racine>] [--json fiche.json] [--9x16 <racine_ref>]

  <racine> : projet rendable (défaut : ce projet, le 9:16 ; formats/16x9 pour le paysage), après outils/format.py.
  Lit <racine>/donnees/donnees.js (DONNEES.format, .geometrie, .pages, .point, .evenements) et imprime, scène par scène,
  où sont la typo, l'agenda, l'iPhone, le wordmark et le point (px du cadre, corps/interligne, lignes de base, boîtes
  d'encre mesurées), les zones du format que chaque boîte recoupe (interdite / prudence) et les places du point.
  --json : la même fiche en JSON (défaut <racine>/rapports/fiche.json pour un projet de format ; rien pour ce projet).
  --9x16 <racine_ref> : ajoute, pour chaque boîte, la valeur du 9:16 en regard (colonne « 9:16 »).
  Boîtes d'encre des textes non paginés (relance, mentions, promesse, offre, textes de l'iPhone) : MESURÉES dans
  <racine>/rapports/dom.json (écrit par outils/controle_format.py <racine>) ; sans ce relevé, estimées et marquées « estimée ».
  Les zones d'un OBJET (agenda, iPhone) sont informatives : un objet peut déborder d'une zone si rien d'important n'y est.
Idempotent, lecture seule (hors --json). Sert de contrat aux agents de scène : toute valeur citée vient d'ici.
"""
import json
import sys
from pathlib import Path

PROJET = Path(__file__).resolve().parents[1]


def lire(racine):
    t = (racine / "donnees" / "donnees.js").read_text()
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def r1(v):
    return round(float(v), 1)


def zones(F, b):
    out = []
    for z in F["zones"]:
        a = z["boite"]
        if b[0] < a[2] and a[0] < b[2] and b[1] < a[3] and a[1] < b[3]:
            out.append(("INTERDITE " if z["sorte"] == "interdite" else "prudence ") + z["nom"])
    if b[0] < F["marge_laterale"] - 0.5 or b[2] > F["largeur"] - F["marge_laterale"] + 0.5:
        out.append("hors marges latérales")
    return out


def encres(racine):
    """{(élément, scène): boîte d'encre au repos (union sur le film)} depuis rapports/dom.json, ou {}."""
    f = racine / "rapports" / "dom.json"
    if not f.exists():
        return {}
    out = {}
    for im in json.loads(f.read_text())["images"]:
        for t in im["textes"]:
            if t["transforme"] or t["opacite"] <= 0.99:
                continue
            scene = next((e.split("@")[1] for e in im["elements"] if e.startswith(t["element"] + "@")), None)
            k = (t["element"], scene)
            b = out.get(k)
            out[k] = [t["x0"], t["y0"], t["x1"], t["y1"]] if b is None else \
                [min(b[0], t["x0"]), min(b[1], t["y0"]), max(b[2], t["x1"]), max(b[3], t["y1"])]
    return out


def fiche(D, ENC=None):
    ENC = ENC or {}
    F = D.get("format") or {"nom": "9x16", "largeur": D["taille"][0], "hauteur": D["taille"][1], "marge_laterale": 70,
                            "corps_min": 36, "zones": [{"nom": "interface Reels / TikTok", "sorte": "interdite", "boite": [0, 1500, 1080, 1920]}]}
    G, S, EV = D["geometrie"], D["scenes"], D["evenements"]
    out = {"format": F["nom"], "cadre": [F["largeur"], F["hauteur"]], "marge_laterale": F["marge_laterale"],
           "corps_min": F["corps_min"], "zones": F["zones"], "scenes": {}}

    def boite(nom, b, cle=None, objet=False, **kw):
        """cle = (élément, scène) du relevé DOM : la boîte d'encre mesurée remplace l'estimée b."""
        mes = ENC.get(cle) if cle else None
        b = mes or b
        z = zones(F, b)
        return dict({"nom": nom + (" [objet]" if objet else "") + ("" if mes or not cle else " [estimée]"),
                     "boite": [r1(x) for x in b], "zones": [("objet : " + x) for x in z] if objet else z}, **kw)

    def pages_de(sc):
        res = []
        for p in D["pages"]:
            if p["scene"] != sc:
                continue
            x0 = min(l["x0"] for l in p["largeurs"]); x1 = max(l["encre_x1"] for l in p["largeurs"])
            st = G["s2_texte"] if p["style"] == "s2_texte" else G["s3_texte"] if p["style"] == "s3_texte" else \
                G["sous_titres_haut"]["agente" if "agente" in p["style"] else "appelant"]
            y0 = p["lignes_de_base"][0] - st["corps"] * 0.75
            y1 = p["lignes_de_base"][-1] + st["corps"] * 0.25
            res.append(boite("page « " + " / ".join(p["lignes"])[:60] + " »", [x0, y0, x1, y1], extrait=p["extrait"],
                             lignes_de_base=p["lignes_de_base"], corps=st["corps"], sortie=(p.get("sortie") or {}).get("t")))
        return res

    def temps(sc):
        s = S[sc]
        return f"{s['debut']:.2f} → {s['fin']:.2f} s (images {s['image_debut']} → {s['image_fin'] - 1})"

    m1 = D["mesures"]["s1"]
    g1 = G["s1"]
    out["scenes"]["s1-sonnerie"] = {"temps": temps("s1-sonnerie"), "boites": [
        boite("accroche « Vous avez les mains prises. » Instrument Serif " + f"{g1['phrase']['corps']}/{g1['phrase']['interligne']}",
              [m1["lignes"][0]["x0"], m1["lignes"][0]["ligne_de_base"] - 0.75 * g1["phrase"]["corps"],
               max(l["x1"] for l in m1["lignes"]), m1["lignes"][-1]["ligne_de_base"] + 0.25 * g1["phrase"]["corps"]],
              lignes_de_base=[l["ligne_de_base"] for l in m1["lignes"]]),
        boite(f"relance italique gris {g1['relance']['corps']}/{g1['relance']['interligne']} (boîte CSS, ligne de base = top + 64)",
              [g1["relance"]["x"], g1["relance"]["top"], g1["relance"]["x"] + 540, g1["relance"]["top"] + 2 * g1["relance"]["interligne"]], cle=("relance", "s1-sonnerie"),
              lignes_de_base=[g1["relance"]["top"] + 64, g1["relance"]["top"] + 64 + g1["relance"]["interligne"]]),
        boite("« . » = le point du film (centre)", [m1["centre"]["x"] - 22, m1["centre"]["y"] - 22, m1["centre"]["x"] + 22, m1["centre"]["y"] + 22],
              centre=[r1(m1["centre"]["x"]), r1(m1["centre"]["y"])]),
    ]}
    out["scenes"]["s2-voix"] = {"temps": temps("s2-voix"), "texte": {k: G["s2_texte"][k] for k in ("x", "corps", "interligne", "lignes_de_base", "x_max")},
                                "boites": pages_de("s2-voix")}
    m3 = G["s3_texte"]["mention"]
    out["scenes"]["s3-ecoute"] = {"temps": temps("s3-ecoute"), "ecoute": G["s3_texte"]["ecoute"], "boites": pages_de("s3-ecoute") + [
        boite(f"mention « {m3['texte']} » Geist {m3['corps']}/{m3['interligne']} gris",
              [m3["x"], m3["lignes_de_base"][0] - 0.75 * m3["corps"], m3["x"] + 0.5 * m3["corps"] * len(m3["texte"]), m3["lignes_de_base"][0] + 0.25 * m3["corps"]], cle=("mention", "s3-ecoute"),
              lignes_de_base=m3["lignes_de_base"])]}
    A = G["agenda"]
    im = A["image"]
    ag = [boite("agenda : vraie capture 1 px = 1 px (déborde à droite)", [im["x"], im["y"], min(im["x"] + im["largeur"], F["largeur"]), im["y"] + im["hauteur"]], objet=True,
                filets={h: r1(y) for h, y in A["heures"].items()}, x_point=r1(A["x_point"]), y_depart=A["y_depart"], y_sortie=A["y_sortie"]),
          boite("bloc « 09:00 Florian » (s5)", [A["bloc"]["x0"], A["bloc"]["y0"], A["bloc"]["x_fin"], A["bloc"]["y1"]]),
          boite(f"mention de l'agenda Geist {A['mention']['corps']}/{A['mention']['interligne']} gris",
                [A["mention"]["x"], A["mention"]["lignes_de_base"][0] - 0.75 * A["mention"]["corps"],
                 A["mention"]["x"] + 0.52 * A["mention"]["corps"] * max(len(l) for l in A["mention"]["lignes"]),
                 A["mention"]["lignes_de_base"][-1] + 0.25 * A["mention"]["corps"]], cle=("agenda", "s4-agenda"), lignes_de_base=A["mention"]["lignes_de_base"])]
    out["scenes"]["s4-agenda"] = {"temps": temps("s4-agenda"), "boites": pages_de("s4-agenda") + ag}
    out["scenes"]["s5-rendez-vous"] = {"temps": temps("s5-rendez-vous"), "boites": pages_de("s5-rendez-vous") + ag,
                                       "haut_min": A["haut_min"], "t_haut_min": A["t_haut_min"]}
    s6 = G["s6"]
    T, E, B = s6["telephone"], s6["ecran"], s6["bulle"]
    out["scenes"]["s6-sms"] = {"temps": temps("s6-sms"), "echelle_px_par_pt": s6["pt"], "boites": pages_de("s6-sms") + [
        boite("iPhone 16 Pro (corps ; sort du cadre par le bas)", [T["x0"], T["haut"], T["x1"], min(T["bas"], F["hauteur"])], objet=True),
        boite("textes de l'écran (barre d'état, nom, horodatage, SMS)", [T["x0"], T["haut"], T["x1"], B["bas"]], cle=("telephone", "s6-sms")),
        boite(f"bulle du SMS (Inter 17 pt = {r1(B['corps_px'])} px)", [B["x0"], B["haut"], B["x1"], B["bas"]]),
        boite("le point sous la queue (attente, éclosion)", [s6["point"]["x"] - 22, s6["point"]["y"] - 22, s6["point"]["x"] + 22, s6["point"]["y"] + 22],
              centre=[r1(s6["point"]["x"]), r1(s6["point"]["y"])]),
    ], "entree_sortie": {"y_entree": s6.get("y_entree"), "y_sortie": s6.get("y_sortie"), "depart_stylo_arc": s6.get("depart_stylo_arc")}}
    s7 = G["s7"]
    fin, pr, of = s7["fin"], s7["promesse"], s7["offre"]
    out["scenes"]["s7-signature"] = {"temps": temps("s7-signature"), "boites": [
        boite(f"wordmark « Vokıo » Instrument Serif {fin['corps']} (ligne de base {s7['ligne_de_base']})",
              [s7["mot"]["x0"], s7["ligne_de_base"] - 0.72 * fin["corps"], s7["mot"]["x1"], s7["ligne_de_base"] + 0.05 * fin["corps"]]),
        boite("point du ı (#mot-pt)", [s7["mot_pt_centre"]["x"] - 22, s7["mot_pt_centre"]["y"] - 22, s7["mot_pt_centre"]["x"] + 22, s7["mot_pt_centre"]["y"] + 22],
              centre=[r1(s7["mot_pt_centre"]["x"]), r1(s7["mot_pt_centre"]["y"])]),
        boite(f"promesse {pr['corps']}/{pr['interligne']} (2 lignes, centrée)", [pr["left"], pr["top"], F["largeur"] - pr["right"], pr["top"] + 2 * pr["interligne"]], cle=("promesse", "s7-signature")),
        boite(f"offre {of['corps']}/{of['interligne']} (2 lignes, centrée)", [of["left"], of["top"], F["largeur"] - of["right"], of["top"] + 2 * of["interligne"]], cle=("offre", "s7-signature")),
    ], "stylo": {"y": s7["stylo_y"], "x0": r1(s7["stylo_x0"]), "x1": r1(s7["stylo_x1"])}}
    out["point"] = [{"t": k["t"], "x": r1(k["x"]), "y": r1(k["y"]), "note": k.get("note", "")[:110]} for k in D["point"]["position"]]
    out["evenements"] = {k: v.get("t") for k, v in EV.items() if isinstance(v, dict) and "t" in v}
    return out


def imprimer(f, ref=None):
    print(f"FORMAT {f['format']} · cadre {f['cadre'][0]} × {f['cadre'][1]} · marges {f['marge_laterale']} · corps ≥ {f['corps_min']} px")
    for z in f["zones"]:
        print(f"  zone {z['sorte']:9s} {z['boite']} {z['nom']}")
    for sc, s in f["scenes"].items():
        extra = {k: v for k, v in s.items() if k not in ("temps", "boites")}
        print(f"\n{sc} · {s['temps']}" + (f" · {json.dumps(extra, ensure_ascii=False)}" if extra else ""))
        lr = ref["scenes"][sc]["boites"] if ref else []
        rb = {b["nom"]: b for b in lr}
        for i, b in enumerate(s["boites"]):
            det = {k: v for k, v in b.items() if k not in ("nom", "boite", "zones")}
            r = rb.get(b["nom"]) or (lr[i] if len(lr) == len(s["boites"]) else None)    # même rang : même boîte
            print(f"  {b['nom']}\n      boîte {b['boite']}" + (f"   (9:16 : {r['boite']})" if r else "")
                  + (f"  {json.dumps(det, ensure_ascii=False)}" if det else "")
                  + (f"\n      zones : {' ; '.join(b['zones'])}" if b["zones"] else ""))
    print("\nplaces du point (DONNEES.point.position) :")
    for k in f["point"]:
        print(f"  {k['t']:7.3f} s  ({k['x']:7.1f} ; {k['y']:7.1f})  {k['note']}")


def main():
    a = sys.argv[1:]

    def opt(nom):
        if nom in a:
            i = a.index(nom); v = a[i + 1]; del a[i:i + 2]; return v
        return None
    js, ref = opt("--json"), opt("--9x16")
    racine = Path(a[0]).resolve() if a else PROJET
    f = fiche(lire(racine), encres(racine))
    imprimer(f, fiche(lire(Path(ref).resolve()), encres(Path(ref).resolve())) if ref else None)
    if js or racine != PROJET:
        s = Path(js) if js else racine / "rapports" / "fiche.json"
        s.parent.mkdir(parents=True, exist_ok=True)
        s.write_text(json.dumps(f, ensure_ascii=False, indent=1))
        print(f"\n→ {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
