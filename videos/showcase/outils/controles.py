#!/usr/bin/env python3
"""Contrôles objectifs du film v2 (critique.json plan.controles et chantier « contrôles et rendu »), sur le MP4
RENDU, sur le DOM du même moteur et sur les données. Tous les instants viennent de DONNEES (donnees/donnees.js,
généré par outils/construire.py) : aucun numéro d'image recopié à la main.

    python3 outils/controles.py [film.mp4] [dossier_sortie] [--check rapport-hf-check.json ...]

Par défaut : /root/vokio-uploads/videos/showcase/le-point-sur-le-i.mp4 → …/showcase/controles-v2/.
Rien n'est écrit dans le projet (sorties dans le dossier de contrôle). Aucune lecture réseau ni base de données
(la preuve en base est un relevé en lecture seule fait à la main, recopié dans le rapport avec sa date).

  D   données (point-resolu.json, evenements) : images, sol − la, ré − la, point sur le « . » et sur #mot-pt,
      contacts sur les filets, vitesse avant contact, pas maximal, immobilité 1078-1099, suiveur à l'arrêt, alternances
  HF  rapports hf check fournis par --check (le script ne lance pas hf check lui-même)
  DOM éléments ≤ 3, textes (corps, bas, marges), mono en capitales, durée de lecture des pages, sous-suite, interdits
  V   vérité : mention, prénoms, texte du SMS contre la v1, SMS après le raccroché, C4 à son vrai décalage, preuve
  S   synchro son et image sur les stems (±5 ms) et sur le MP4 ; mots à ±1 image de leur attaque (MP4)
  A   audio du MP4 : sonie, crête vraie, zéros, tonalité ; rappel des contrôles du chantier son (son/mesures-son.json)
  I   image (MP4) : point aux images clés, solaire hors du point, ı sans point, x ≤ 1010 en s2, pas d'image brune ;
      planches (1 i/s, 1 i/0,5 s, images clés, pelures d'oignon, vue téléphone 393 px)
  L   livraison (ffprobe)
  F   finition du 27/09 (arbitrages du réalisateur) : accroche en mouvement dès l'image 0, aucun filé ni saut d'objet
      (≤ 90 px par image en sortie), étirement ≤ 1,25, SMS lisible ≥ 3,8 s et téléphone vide ≤ 1,2 s, aucune encre sous le
      point (s2, s6), point hors du bloc après l'écriture, marge de l'agenda ≥ 70, « Vokıo » à l'encre (bord doux),
      accroche moins large que le wordmark, l'agente plus forte que l'appelant (hauteur d'x)
"""
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJET = Path(__file__).resolve().parents[1]
args = [a for a in sys.argv[1:]]
CHECKS = []
while "--check" in args:
    i = args.index("--check")
    CHECKS.append(Path(args[i + 1]))
    del args[i:i + 2]
FILM = Path(args[0]) if len(args) > 0 else Path("/root/vokio-uploads/videos/showcase/le-point-sur-le-i.mp4")
SORTIE = Path(args[1]) if len(args) > 1 else FILM.parent / "controles-v2"
SORTIE.mkdir(parents=True, exist_ok=True)
POLICE = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
rapport = {"film": str(FILM)}
echecs = []


def note(cle, ok, detail):
    rapport.setdefault("controles", {})[cle] = {"ok": bool(ok), "detail": detail}
    print(("[ok]    " if ok else "[ÉCHEC] ") + cle + " : " + (detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False, default=str)[:700]))
    if not ok:
        echecs.append(cle)


def lire_json(p):
    return json.loads((PROJET / p).read_text())


_js = (PROJET / "donnees" / "donnees.js").read_text()
_i = _js.index("window.DONNEES = ") + len("window.DONNEES = ")
D = json.loads(_js[_i:_js.rstrip().rindex(";")])
W, H = D["taille"]
FPS, N_IMAGES, DUREE = D["fps"], D["images"], D["duree"]
EV = D["evenements"]
C = D["couleurs"]
hexrgb = lambda h: np.array([int(h[k:k + 2], 16) for k in (1, 3, 5)], float)
PAPIER, SOLAIRE, ENCRE = hexrgb(C["papier"]), hexrgb(C["solaire"]), hexrgb(C["encre"])
RESOLU = {e["image"]: e for e in lire_json("donnees/point-resolu.json")["images"]}
AG = D["agenda"]
M7 = D["mesures"]["s7"]["centre"]
M1 = D["mesures"]["s1"]["centre"]
FILETS = {"contact_neuf": AG["heures"]["09:00"], "contact_dix": AG["heures"]["10:00"],
          "contact_onze": AG["heures"]["11:00"], "contact_retour_neuf": AG["heures"]["09:00"]}
IM = lambda nom: EV[nom]["image"]
IMS = lambda nom: EV[nom]["images"]
T = lambda nom: EV[nom]["t"]
N_RE = IM("signature_re_contact")
N_POSE = IMS("point_pose")[1]          # finition : le point de l'accroche est posé (15,75 px) à l'image 29, invisible à 0

# ═════════════════════════════ D. Données ═════════════════════════════
sc = D["scenes"]
index_html = (PROJET / "index.html").read_text()
hotes_html = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(
    r'data-composition-id="([^"]+)" data-composition-src="[^"]+"\s+data-start="([\d.]+)" data-duration="([\d.]+)"', index_html)}
racine = re.search(r'id="root"[^>]*data-duration="([\d.]+)"', index_html)
audio = re.search(r'<audio[^>]*data-duration="([\d.]+)"', index_html)
hotes_ok = all(abs(hotes_html[k][0] - v["hote_start"]) < 1e-9 and abs(hotes_html[k][1] - v["hote_duration"]) < 1e-9 for k, v in sc.items()) \
    and len(hotes_html) == len(sc) == 7
bout_a_bout = all(abs(a["fin"] - b["debut"]) < 1e-6 for a, b in zip(list(sc.values()), list(sc.values())[1:]))
d_sol, d_re = round(T("signature_sol") - T("signature_la"), 6), round(T("signature_re_contact") - T("signature_la"), 6)
note("D1 images, scènes, intervalles", N_IMAGES == int(round(DUREE * FPS)) and float(racine.group(1)) == DUREE and float(audio.group(1)) == DUREE
     and hotes_ok and bout_a_bout and len(RESOLU) == N_IMAGES + 1 and abs(d_sol - 0.24) < 1e-6 and abs(d_re - 0.60) < 1e-6,
     {"images": N_IMAGES, "duree": DUREE, "root/audio": [racine.group(1), audio.group(1)], "hotes = scenes.json": hotes_ok,
      "bout_a_bout": bout_a_bout, "sol-la": d_sol, "re-la": d_re,
      "scenes": {k: [v["image_debut"], v["image_fin"] - 1] for k, v in sc.items()}})

e0, eP, eR, eF = RESOLU[0], RESOLU[N_POSE], RESOLU[N_RE], RESOLU[N_RE + 3]
ecart0 = float(np.hypot(eP["x_sans"] - M1["x"], eP["y_sans"] - M1["y"]))
ecartR = float(np.hypot(eR["x"] - M7["x"], eR["y"] - M7["y"]))
note("D2 point sur le « . » (posé à l'image 29, invisible à 0), sur #mot-pt (ré) et rond ensuite",
     ecart0 <= 0.5 and e0["d"] == 0 and abs(eP["d"] - D["mesures"]["s1"]["diametre"]) <= 0.05 and ecartR <= 0.5 and abs(eF["d"] - 44) <= 0.3
     and eF["sx"] == 1 and eF["sy"] == 1,
     {"image0_diametre": e0["d"], f"image{N_POSE}_sans_secousse": [eP["x_sans"], eP["y_sans"]], f"image{N_POSE}_diametre": eP["d"],
      "point_du_s1": [M1["x"], M1["y"]], "ecart_px": round(ecart0, 3),
      f"image{N_RE}": [eR["x"], eR["y"]], "mot_pt": [M7["x"], M7["y"]], "ecart_re_px": round(ecartR, 3),
      f"image{N_RE + 3}": {"d": eF["d"], "sx": eF["sx"], "sy": eF["sy"]}})

pas = {n: float(np.hypot(RESOLU[n]["x_sans"] - RESOLU[n - 1]["x_sans"], RESOLU[n]["y_sans"] - RESOLU[n - 1]["y_sans"])) for n in range(1, N_IMAGES)}
contacts = {}
for nom, yf in FILETS.items():
    n = IM(nom)
    contacts[nom] = {"image": n, "y": RESOLU[n]["y"], "filet": yf, "ecart": round(RESOLU[n]["y"] - yf, 3),
                     "pas_entrant_px": round(pas[n], 2), "v_image_precedente": RESOLU[n - 1]["v"]}
ok_c = all(abs(c["ecart"]) <= 0.5 for c in contacts.values()) and all(
    c["pas_entrant_px"] >= (5 if nom == "contact_retour_neuf" else 10) for nom, c in contacts.items())
note("D3 contacts sur les filets, vitesse avant contact", ok_c, contacts)

a0, a1 = IMS("anticipation")[0], 150
pas_hors = max(v for n, v in pas.items() if not (a0 <= n <= a1))
pas_cr = max(v for n, v in pas.items() if a0 <= n <= a1)
n_hors = max((n for n in pas if not (a0 <= n <= a1)), key=lambda n: pas[n])
note("D4 pas maximal", pas_hors <= 130 and pas_cr <= 150,
     {"max_hors_retour_chariot": [round(pas_hors, 1), n_hors], "max_retour_chariot_137_150": round(pas_cr, 1)})

s0, s1 = IM("raccroche") + 2, IMS("silence_numerique")[1] - 1        # 1078 → 1099
imm = max(abs(RESOLU[n][k] - RESOLU[s0][k]) for n in range(s0, s1 + 1) for k in ("x", "y", "d", "sx", "sy"))
n516 = IMS("suiveur")[1]
v516 = pas[n516]        # dernier pas du suiveur (515 → 516) ; v (différence centrée) voit déjà le départ vers l'agenda
note("D5 immobile pendant le silence numérique, suiveur à l'arrêt", imm < 1e-6 and v516 <= 0.01,
     {f"ecart_max_{s0}_{s1}": imm, f"pas_{n516 - 1}_{n516}_px": round(v516, 5), "v_centree_516 (départ vers l'agenda compris)": RESOLU[n516]["v"],
      "vitesse_finale_du_suiveur (construire.py)": D["point"]["suiveur"].get("_v_fin_px_par_image", "non exportée")})


def alternances(cle):
    out = []
    for n in range(2, N_IMAGES - 1):
        d1 = RESOLU[n][cle] - RESOLU[n - 1][cle]
        d2 = RESOLU[n + 1][cle] - RESOLU[n][cle]
        d0 = RESOLU[n - 1][cle] - RESOLU[n - 2][cle]
        if min(abs(d0), abs(d1), abs(d2)) > 0.5 and d0 * d1 < 0 and d1 * d2 < 0:
            out.append(n)
    return out

alt = {k: alternances(k) for k in ("x_sans", "y_sans", "x", "y")}
note("D6 aucune alternance à 2 images", not any(alt.values()), {k: v[:12] for k, v in alt.items()})

ECR = D["point"]["ecrasements"]
sx_max = max((RESOLU[n]["sx"], n) for n in range(N_IMAGES) if str(n) not in ECR)
p0_, p1_ = IMS("plume_mot")
ronds = all(RESOLU[n]["sx"] == 1 and RESOLU[n]["sy"] == 1 for n in range(p0_, p1_ + 1))
note("D7 étirement plafonné à 1,25 (plus de pilule), point rond pendant l'écriture de « Vokıo »",
     sx_max[0] <= 1.25 + 1e-6 and ronds,
     {"sx_max_hors_ecrasements": sx_max[0], "image": sx_max[1], "ellipse_max_px": [round(44 * sx_max[0], 1), round(44 / np.sqrt(sx_max[0]), 1)],
      f"rond_de_{p0_}_a_{p1_}": ronds})

XA, Y9 = AG["x_point"], AG["heures"]["09:00"]
g0_, g1_ = IMS("vers_gouttiere")
gout = [n for n in range(g1_, IM("depart_gouttiere") + 1) if not (abs(RESOLU[n]["x_sans"] - XA) < 0.01 and abs(RESOLU[n]["y_sans"] - Y9) <= 6.01)]
dessus = [n for n in range(g0_ + 1, g1_ + 1) if RESOLU[n]["x_sans"] + 22 > AG["bloc"]["florian_encre"]["x0"] - 200
          and RESOLU[n]["x_sans"] - 22 < AG["bloc"]["florian_encre"]["x1"] + 2 and RESOLU[n]["y_sans"] + 22 * max(1, RESOLU[n]["sx"]) > AG["bloc"]["florian_encre"]["y0"] - 2]
note("D8 après l'écriture, le point quitte le bloc par-dessus son encre et attend dans la gouttière des heures (09:00)",
     not gout and not dessus,
     {"gouttiere": [XA, Y9], "images": [g1_, IM("depart_gouttiere")], "hors_gouttiere": gout[:8], "sur_l_encre_du_bloc": dessus[:8],
      "image_821": [RESOLU[821]["x_sans"], RESOLU[821]["y_sans"]]})

# ═════════════════════════════ HF. Rapports hf check ═════════════════════════════
hf = {}
for p in CHECKS:
    r = json.loads(p.read_text())
    hf[p.name] = {k: {"ok": r[k].get("ok"), "erreurs": r[k].get("errorCount"), "avertissements": r[k].get("warningCount"),
                      "infos": r[k].get("infoCount"), "controles": r[k].get("checked"), "passes": r[k].get("passed"),
                      "constats": [f.get("message", f.get("code")) for f in r[k].get("findings", [])][:6]}
                  for k in ("lint", "runtime", "layout", "motion", "contrast")}
    hf[p.name]["transitions"] = len(r["layout"].get("transitionSamples", []))
ok_hf = bool(hf) and all(v[k]["erreurs"] == 0 and (k != "contrast" or v[k]["controles"] == v[k]["passes"])
                         for v in hf.values() for k in ("lint", "runtime", "layout", "motion", "contrast"))
note("HF hf check (rapports fournis)", ok_hf, hf or "aucun rapport fourni (--check) : non vérifié par ce script")

# ═════════════════════════════ DOM ═════════════════════════════
dom_json = SORTIE / "dom.json"
subprocess.run(["/root/.pwtest/bin/python", str(PROJET / "outils" / "controles_dom.py"), str(dom_json)], check=True,
               stderr=subprocess.DEVNULL)
DOM = json.loads(dom_json.read_text())
trop, comptes = [], {}
for im in DOM["images"]:
    els = [e.split("@")[0] for e in im["elements"]]
    n = len(els)
    if im["image"] >= N_RE and "mot" in els and "point" in els:
        n -= 1      # le point posé sur le ı EST le point du logo : un seul élément
    comptes[im["image"]] = n
    if n > 3:
        trop.append((im["image"], im["elements"]))
note("DOM1 éléments simultanés ≤ 3 (toutes les images)", not trop and not DOM["erreurs_page"] and len(DOM["images"]) == N_IMAGES,
     trop[:10] or {"images": len(DOM["images"]), "max": max(comptes.values()), "images_a_3": sum(1 for c in comptes.values() if c == 3),
                   "erreurs_page": DOM["erreurs_page"]})

petits, bas, marges, mono = set(), [], set(), set()
for im in DOM["images"]:
    for t in im["textes"]:
        if t["corps"] < 36:
            petits.add((t["element"], t["texte"], t["corps"]))
        if "Mono" in t["famille"] and re.search(r"[A-Z]", t["texte"]) and t["texte"] == t["texte"].upper():
            mono.add(t["texte"])
        au_repos = not t["transforme"] and t["opacite"] > 0.99
        if au_repos and t["y1"] >= 1500 and t["y0"] < H:
            bas.append((im["image"], t["element"], t["texte"], t["y1"]))
        if au_repos and (t["boite"]["x0"] < 70 - 0.5 or t["boite"]["x1"] > 1010 + 0.5):
            marges.add((t["element"], t["texte"], t["boite"]["x0"], t["boite"]["x1"]))
max_bas = max((t["boite"]["y1"] for im in DOM["images"] for t in im["textes"] if not t["transforme"] and t["opacite"] > .99), default=0)
ep = AG["etiquettes_police"]
lab_ok = ep["corps_px_film"] >= 45 and ep["capitales"] == 0
note("DOM2 textes (corps ≥ 36, bas < 1500 et marges 70-1010 au repos, 0 mono en capitales) ; étiquettes de la capture",
     not petits and not bas and not marges and not mono and lab_ok,
     {"corps<36": sorted(petits)[:8], "bas>=1500 au repos": bas[:8], "hors marges": sorted(marges)[:8], "mono capitales": sorted(mono),
      "bas maximal au repos": max_bas, "corps vus": sorted({t["corps"] for im in DOM["images"] for t in im["textes"]}),
      "etiquettes_capture": {"corps_px_film": ep["corps_px_film"], "hauteur_encre_chiffres": ep["hauteur_encre_chiffres"],
                             "capitales": ep["capitales"]}})

# durée de lecture de chaque page posée par TEXTE.poser
lectures, courtes = [], []
for pg in DOM["pages"]:
    vus = [im["image"] for im in DOM["images"] if im["poses"][pg["index"]] > 0]
    if not vus:
        continue
    runs, deb, prec = [], vus[0], vus[0]
    for n in vus[1:] + [None]:
        if n is None or n != prec + 1:
            runs.append((deb, prec))
            deb = n
        prec = n if n is not None else prec
    plus_court = min(b - a + 1 for a, b in runs)
    lectures.append({"scene": pg["scene"], "extrait": pg["extrait"], "texte": " | ".join(pg["lignes"]), "visible": runs,
                     "s": round(plus_court / FPS, 2)})
    if plus_court < 0.6 * FPS:
        courtes.append(lectures[-1])
note("DOM3 chaque page visible ≥ 0,6 s", not courtes, courtes or lectures)

# sous-suite (données) : chaque page de DONNEES.pages est une sous-suite des mots dits de son extrait
def cle(m):
    m = m.replace("’", "'").lower()
    m = "".join(c for c in unicodedata.normalize("NFD", m) if unicodedata.category(c) != "Mn")
    return re.sub(r"^['\-]+|['\-]+$", "", re.sub(r"[^a-z0-9'\-]", "", m))

fautes = []
for p in D["pages"]:
    dits = [w["cle"] for w in D["mots"] if w["extrait"] == p["extrait"]]
    k = p.get("depuis", 0)
    for ligne in p["lignes"]:
        for u in ligne.replace("\u00a0", " ").replace("\u202f", " ").split(" "):
            c = cle(u)
            if not c:
                continue
            while k < len(dits) and dits[k] != c:
                k += 1
            if k >= len(dits):
                fautes.append(f'{p["extrait"]} « {u} »')
                break
            k += 1
sans_blanc = lambda s: re.sub(r"[\s\u00a0\u202f]", "", s)     # l'espace fine est rendue par un <span> vide (.tx-fine)
pages_dom = {(pg["extrait"], sans_blanc(" | ".join(pg["lignes"]))) for pg in DOM["pages"] if pg["extrait"]}
pages_don = {(p["extrait"], sans_blanc(" | ".join(p["lignes"]))) for p in D["pages"]}
note("DOM4 sous-suite du texte dit (données et DOM)", not fautes and pages_dom <= pages_don and ("C4", sans_blanc("Super, merci beaucoup. | Au revoir.")) in pages_dom,
     fautes or {"pages": len(D["pages"]), "pages_du_dom_hors_donnees": sorted(pages_dom - pages_don)})

# interdits : fichiers (lib/vendor exclu) et textes rendus
fichiers = [PROJET / "index.html"] + sorted((PROJET / "compositions").glob("*.html")) + sorted((PROJET / "donnees").glob("*.json")) \
    + [PROJET / "donnees" / "donnees.js", PROJET / "lib" / "texte.js", PROJET / "lib" / "point.js"]
tel = re.compile(r"(?<![0-9.:])(?:\+33 ?[1-9]|0[1-9])(?:[ .]?[0-9]{2}){4}(?![0-9])")
trouves = []
for f in fichiers:
    t = f.read_text()
    for motif, nom in (("—", "cadratin"), ("Alauzet", "Alauzet")):
        if motif in t:
            trouves.append(f"{f.name}: {nom} ×{t.count(motif)}")
    for m in tel.finditer(t):
        trouves.append(f"{f.name}: numéro « {m.group(0)} »")
textes_vus = {t["texte"] for im in DOM["images"] for t in im["textes"]}
for t in textes_vus:
    if "—" in t or "Alauzet" in t or tel.search(t):
        trouves.append(f"rendu : « {t} »")
note("DOM5 interdits (—, Alauzet, numéro)", not trouves, trouves or f"0 cadratin, 0 Alauzet, 0 numéro dans {len(fichiers)} fichiers et {len(textes_vus)} textes rendus")

# ═════════════════════════════ V. Vérité ═════════════════════════════
MENTION = ["Capture réelle de app.vokio.fr", "Établissement fictif de démonstration."]
ment = {pg["scene"]: pg["lignes"] for pg in DOM["pages"] if pg["scene"] in ("s4-agenda", "s5-rendez-vous") and not pg["extrait"]}
majuscules = sorted({m for t in textes_vus for m in re.findall(r"\b[A-ZÀ-Ý][a-zà-ÿ]+", t)})


def texte_bulle(chemin):
    h = Path(chemin).read_text()
    p = re.search(r'<p id="s6-bulle">(.*?)</p>', h, re.S).group(1)
    return " ".join(re.sub(r"<[^>]+>", "", s) for s in re.findall(r'<span class="s6-l">(.*?)</span>', p))

sms_v2, sms_v1 = texte_bulle(PROJET / "compositions" / "s6-sms.html"), texte_bulle(PROJET / "v1" / "compositions" / "s6-sms.html")
bulle_vue = [im["image"] for im in DOM["images"] if any(t["id"] == "s6-bulle" or "votre rendez-vous" in t["texte"] for t in im["textes"])]
ex = {e["id"]: e for e in D["dialogue"]["extraits"]}
preuve = {
    "capture": AG["preuve"],
    "base_lecture_seule": {
        "releve": "27/09/2026 vers 07:10 (heure de Paris), BEGIN READ ONLY … ROLLBACK, à la main, une seule fois (non rejoué par ce script)",
        "rendez_vous": "068432f8-3472-42a0-8081-293839d06246 | Florian | 2026-09-19 09:00 | 20 min | Consultation vétérinaire | "
                       "statut completed | créé le 2026-09-18 16:53:29 | Clinique vétérinaire du Port | is_demo = true",
        "sms_events": "confirmation | sent | 2026-09-18 16:55:10 (corps non conservé en base)",
    },
}
ok_v = (ment.get("s4-agenda") == MENTION and ment.get("s5-rendez-vous") == MENTION and sms_v2 == sms_v1
        and bulle_vue and min(bulle_vue) >= IM("bulle_et_vibreur") > IM("raccroche")
        and abs(ex["C4"]["decalage"] - ex["A4"]["decalage"]) < 1e-9 and abs(ex["C4"]["decalage"] + 41.07) < 0.005)
note("V1 vérité (mention, SMS identique à la v1, SMS après le raccroché, C4 à −41,07)", ok_v,
     {"mention": ment, "sms_identique_v1": sms_v2 == sms_v1, "sms": sms_v2,
      "bulle_visible_des_l_image": min(bulle_vue) if bulle_vue else None, "raccroche": IM("raccroche"),
      "decalages_A4_C4": [ex["A4"]["decalage"], ex["C4"]["decalage"]],
      "mots_a_majuscule_rendus": majuscules, "preuve": preuve})

# ═════════════════════════════ MP4 : décodage image par image ═════════════════════════════
def couverture(img, n, marge=4.0):
    """Barycentre et diamètre équivalent du point sur l'image n (luminance, dans l'ellipse attendue élargie)."""
    e = RESOLU[n]
    cible = hexrgb(e["couleur"])
    r = e["d"] / 2 * max(e["sx"], e["sy"], 1) + marge
    x0, x1 = int(np.floor(e["x"] - r)), int(np.ceil(e["x"] + r)) + 1
    y0, y1 = int(np.floor(e["y"] - r)), int(np.ceil(e["y"] + r)) + 1
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = (xx + .5 - e["x"]) ** 2 + (yy + .5 - e["y"]) ** 2 <= r * r
    luma = np.array([0.299, 0.587, 0.114])
    pix = img[y0:y1, x0:x1].astype(float) @ luma
    yp, yc = PAPIER @ luma, cible @ luma
    alpha = np.clip((yp - pix) / (yp - yc), 0, 1) * m
    s = alpha.sum()
    if s < 1:
        return None
    return {"x": float((alpha * (xx + .5)).sum() / s), "y": float((alpha * (yy + .5)).sum() / s), "d": float(2 * np.sqrt(s / np.pi)),
            "attendu": [e["x"], e["y"], e["d"]]}


def masque_point(n, marge):
    """Ellipse du point dessiné (étirement, écrasement, rotation) élargie de marge px, sur le cadre entier (booléen)."""
    e = RESOLU[n]
    r = e["d"] / 2
    th = np.radians(e["rot"])
    R = r * max(e["sx"], e["sy"], 1) + marge + 2
    x0, x1 = max(0, int(e["x"] - R)), min(W, int(e["x"] + R) + 2)
    y0, y1 = max(0, int(e["y"] - R)), min(H, int(e["y"] + R) + 2)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = xx + .5 - e["x"], yy + .5 - e["y"]
    u = (dx * np.cos(th) + dy * np.sin(th)) / (r * e["sx"] + marge)
    v = (-dx * np.sin(th) + dy * np.cos(th)) / (r * e["sy"] + marge)
    m = np.zeros((H, W), bool)
    m[y0:y1, x0:x1] = u * u + v * v <= 1
    return m


mots_dom = DOM["mots"]
for w in mots_dom:
    w["serie"] = {}
CLES = sorted({0, 1, 5, 12, 26, 29, 126, 127, 137, 139, 150, 165, 199, 241, 255, 300, 430, 516, 534, 555, 616, 620, 643, 666, 705, 731,
               762, 783, 787, 795, 801, 821, 935, 945, 973, 1017, 1037, 1054, 1065, 1076, 1100, 1105, 1114, 1150, 1230, 1238,
               1245, 1250, 1255, 1260, 1266, 1276, 1287, 1290, 1311, 1340, N_IMAGES - 1}
              | {IM(k) for k in ("decroche", "lumiere", "depart_agenda", "arrivee_agenda", "contact_neuf", "contact_dix", "contact_onze",
                                 "contact_retour_neuf", "ecriture_debut", "ecriture_fin", "signe_florian", "arrivee_bulle", "raccroche",
                                 "bulle_et_vibreur", "signature_la", "signature_sol", "signature_re_contact")}
              | {IMS("suivi_bloc")[1], IMS("telephone_sortie")[0], IMS("plume_mot")[1], N_RE + 3, IMS("promesse")[1], N_IMAGES - 1})
PELURES = {"137-150": (137, 150), f"{IM('depart_agenda')}-{IM('arrivee_agenda')}": (IM("depart_agenda"), IM("arrivee_agenda")),
           f"{IMS('vers_gouttiere')[0]}-{IMS('vers_gouttiere')[1]}": tuple(IMS("vers_gouttiere")),
           f"{IM('depart_gouttiere')}-{IMS('voix_sms')[1]}": (IM("depart_gouttiere"), IMS("voix_sms")[1]),
           f"{IM('depart_telephone')}-{IM('arrivee_bulle')}": (IM("depart_telephone"), IM("arrivee_bulle")),
           f"{IM('signature_la')}-{IM('signature_sol')}": (IM("signature_la"), IM("signature_sol"))}
pelures = {k: None for k in PELURES}
RACCORDS = [v["image_debut"] for v in list(sc.values())[1:]]
autour = {b + k for b in RACCORDS for k in range(-3, 3)}
IMAGES_POINT = {N_POSE, N_RE, N_RE + 3} | {IM(k) for k in FILETS} | {IM(k) - 1 for k in FILETS} | set(range(IM("raccroche") + 2, IMS("silence_numerique")[1]))
# finition : aucune encre sous le point dans ses trajets de lecture (s2, s6) ; accroche ; SMS ; marge ; écriture du mot
TRAJ = [(t["image0"], t["image1"]) for t in D["point"]["trajets"]]
anneau_encre, accroche_diff, sms_encre, tel_haut, marge_agenda, encre_mot = [], [], {}, {}, None, {}
REF_SMS = IMS("telephone_sortie")[0] - 1        # la bulle entière, au repos, dernière image avant la sortie
BULLE = D["geometrie"]["s6"]["bulle"]
Z_SMS = (int(BULLE["x0"]) + 30, int(BULLE["haut"]) + 26, int(BULLE["x1"]) - 30, int(BULLE["haut"]) + 350 - 26)
SIL = D["geometrie"]["s6"]["silhouette"]
img_sms_ref = None
gardees, points = {}, {}
solaire_hors, i_avec_point, s2_droite, brun, immobile = [], [], [], {}, []
BLOC = AG["bloc"]
ref_imm = None
diffs, prec = [], None
MOT_PT = (M7["x"], M7["y"])
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(FILM), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
n = 0
taille = W * H * 3
while True:
    buf = proc.stdout.read(taille)
    if len(buf) < taille:
        break
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    f = img.astype(np.int16)
    sol = (np.abs(f[..., 0] - 239) < 40) & (np.abs(f[..., 1] - 164) < 40) & (np.abs(f[..., 2] - 36) < 40)
    gris = img.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    # mots : encre (gris < 201) dans la boîte de repos, HORS point (couleur solaire ou ellipse du point + 3 px)
    actifs = [w for w in mots_dom if w["image"] - 14 <= n <= w["image"] + 20]
    if actifs:
        exclu = sol | masque_point(n, 3)
        for w in actifs:
            x0, y0 = int(w["x0"]) - 2, int(w["y0"]) - 2
            x1, y1 = int(np.ceil(w["x1"])) + 2, int(np.ceil(w["y1"])) + 14
            w["serie"][n] = int(((gris[y0:y1, x0:x1] < 201) & ~exclu[y0:y1, x0:x1]).sum())
    if n in IMAGES_POINT:
        points[n] = couverture(img, n)
    # solaire hors du point (bloc admis de 762 à 941, dans sa boîte)
    if sol.any():
        hors = sol & ~masque_point(n, 3)
        if IM("ecriture_debut") <= n <= IMS("agenda_sort")[1]:
            hors[max(0, int(BLOC["y0"]) - 2 - 272):int(np.ceil(BLOC["y1"])) + 3, int(BLOC["x0"]) - 2:int(BLOC["x1_visible"]) + 2] = False
        k = int(hors.sum())
        if k:
            ys, xs = np.nonzero(hors)
            solaire_hors.append((n, k, int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
    # le ı sans point de la fin d'écriture au ré
    if IMS("plume_mot")[1] <= n < N_RE:
        yy, xx = np.ogrid[int(MOT_PT[1]) - 22:int(MOT_PT[1]) + 23, int(MOT_PT[0]) - 22:int(MOT_PT[0]) + 23]
        m = (xx + .5 - MOT_PT[0]) ** 2 + (yy + .5 - MOT_PT[1]) ** 2 <= 20 ** 2
        k = int((sol[int(MOT_PT[1]) - 22:int(MOT_PT[1]) + 23, int(MOT_PT[0]) - 22:int(MOT_PT[0]) + 23] & m).sum())
        if k:
            i_avec_point.append((n, k))
    # finition : encre dans l'anneau du point (bord du disque + 4 px) pendant les trajets de lecture (s2, s6)
    if any(a <= n <= b for a, b in TRAJ) and RESOLU[n]["d"] > 40:
        e = RESOLU[n]
        m_in = masque_point(n, 1)
        m_out = masque_point(n, 5)
        k = int(((gris < 150) & m_out & ~m_in & ~sol).sum()) + int(((gris < 150) & m_in & ~sol).sum())
        if k:
            anneau_encre.append((n, k))
    # finition : l'accroche bouge dès l'image 0 (encre de la zone de la phrase, image à image)
    if n <= 40:
        z = gris[500:900, 60:1020]
        accroche_diff.append((n, int((z < 150).sum())))
    # finition : la bulle se lit (encre de sa zone de texte comparée à l'image de référence) ; le téléphone au repos
    if IM("bulle_et_vibreur") - 2 <= n <= IMS("telephone_sortie")[1]:
        zb = (gris[Z_SMS[1]:Z_SMS[3], Z_SMS[0]:Z_SMS[2]] < 110)
        sms_encre[n] = zb
    if IMS("telephone_monte")[0] - 2 <= n <= IM("bulle_et_vibreur"):
        col = gris[int(SIL["haut"]) - 3:int(SIL["haut"]) + 4, 400:680]
        tel_haut[n] = float((col < 120).mean())
    if n == IM("contact_retour_neuf"):
        row = img[900].astype(int)
        marge_agenda = next(x for x in range(0, 200) if np.abs(row[x] - PAPIER).max() > 6)
    if IMS("plume_mot")[0] <= n <= IMS("plume_mot")[1] or n == IMS("plume_mot")[1] + 3:
        encre_mot[n] = (gris[560:870, 150:960] < 200).astype(np.uint8) * (255 - gris[560:870, 150:960]).astype(np.int16)
    # s2 : le point ne passe jamais au-delà de x = 1010
    if sc["s2-voix"]["image_debut"] <= n < sc["s2-voix"]["image_fin"] and sol.any():
        s2_droite.append((n, int(np.nonzero(sol.any(axis=0))[0].max()) + 1))
    # décroché : aucune image brune (cœur du point : encre OU solaire)
    if IM("decroche") - 1 <= n <= IM("lumiere") + 1:
        e = RESOLU[n]
        cy, cx = int(e["y"]), int(e["x"])
        coeur = img[cy - 4:cy + 5, cx - 4:cx + 5].reshape(-1, 3).astype(float)
        dE = np.abs(coeur - ENCRE).max(axis=1)
        dS = np.abs(coeur - SOLAIRE).max(axis=1)
        brun[n] = {"moyenne": [round(v, 1) for v in coeur.mean(axis=0)], "encre": int((dE < 30).sum()), "solaire": int((dS < 30).sum()),
                   "ni_l_un_ni_l_autre": int(((dE >= 30) & (dS >= 30)).sum()), "attendu": e["couleur"]}
    # immobilité du point pendant le silence numérique (au pixel, autour du point)
    if s0 <= n <= s1:
        e = RESOLU[n]
        zone = img[int(e["y"]) - 40:int(e["y"]) + 41, int(e["x"]) - 40:int(e["x"]) + 41].astype(np.int16)
        if ref_imm is None:
            ref_imm = zone
        immobile.append((n, int(np.abs(zone - ref_imm).max())))
    # pelures d'oignon (plus sombre = min de luminance, en couleur)
    for k_, (a, b) in PELURES.items():
        if a <= n <= b:
            pelures[k_] = img.copy() if pelures[k_] is None else np.where((gris < pelures[k_].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32))[..., None], img, pelures[k_])
    petit = gris[::4, ::4]
    if prec is not None:
        diffs.append((n, float(np.abs(petit - prec).mean())))
    prec = petit
    if n in CLES or n in autour or n % 15 == 0:
        gardees[n] = img.copy()
    n += 1
proc.wait()
rapport["images_decodees"] = n

# ── I. Point et image ──
def ecart(n):
    p = points.get(n)
    if not p:
        return None
    return {"x": round(p["x"], 2), "y": round(p["y"], 2), "d": round(p["d"], 2),
            "dx": round(p["x"] - p["attendu"][0], 2), "dy": round(p["y"] - p["attendu"][1], 2)}

g0, gR, gF = ecart(N_POSE), ecart(N_RE), ecart(N_RE + 3)
gc = {k: {"contact": ecart(IM(k)), "avant": ecart(IM(k) - 1), "filet": FILETS[k]} for k in FILETS}
for k, v in gc.items():
    v["deplacement_px"] = None if not (v["contact"] and v["avant"]) else round(float(np.hypot(v["contact"]["x"] - v["avant"]["x"], v["contact"]["y"] - v["avant"]["y"])), 2)
ok_i1 = (g0 and abs(g0["dx"]) <= .5 and abs(g0["dy"]) <= .5
         and gR and abs(gR["x"] - M7["x"]) <= .5 and abs(gR["y"] - M7["y"]) <= .5
         and gF and abs(gF["d"] - 44) <= .3
         and all(v["contact"] and abs(v["contact"]["y"] - v["filet"]) <= .5 and v["deplacement_px"] and v["deplacement_px"] > 1 for v in gc.values()))
note("I1 point sur le MP4 (0, ré, rond, contacts, déplacement avant contact)", ok_i1,
     {f"image{N_POSE} (posé, dessiné, secousse comprise)": g0, f"image{N_RE}": gR, "mot_pt": [M7["x"], M7["y"]], f"image{N_RE + 3}": gF, "contacts": gc})
cs = [points[k] for k in range(s0, s1 + 1) if points.get(k)]
etendue = None if not cs else round(max(max(c["x"] for c in cs) - min(c["x"] for c in cs), max(c["y"] for c in cs) - min(c["y"] for c in cs)), 3)
note("I2 point immobile sur le silence numérique (MP4 : barycentre à 0,1 px, écart de pixels au bruit du codec)",
     etendue is not None and etendue <= 0.1 and max(v for _, v in immobile) <= 8,
     {"images": [s0, s1], "etendue_barycentre_px": etendue, "ecart_max_niveaux_zone_81px": max(v for _, v in immobile) if immobile else None})
note("I3 aucun pixel solaire hors du point (bloc admis de 762 à 941)", not solaire_hors, solaire_hors[:12] or "aucun")
note("I4 le ı sans point de la fin d'écriture au ré", not i_avec_point,
     i_avec_point[:10] or f"aucun pixel solaire sur le point du ı de {IMS('plume_mot')[1]} à {N_RE - 1}")
xmax_s2 = max((x for _, x in s2_droite), default=None)
note("I5 point jamais au-delà de x = 1010 en s2", xmax_s2 is not None and xmax_s2 <= 1010,
     {"x_max_pixel_solaire": xmax_s2, "image": max(s2_droite, key=lambda z: z[1])[0] if s2_droite else None})
note("I6 aucune image brune au décroché", all(v["ni_l_un_ni_l_autre"] <= 4 for v in brun.values())
     and brun[IM("decroche")]["encre"] > 40 and brun[IM("lumiere")]["solaire"] > 40, brun)

# ═════════════════════════════ F. Finition du 27/09 (arbitrages du réalisateur) ═════════════════════════════
# F1 l'accroche bouge dès l'image 0
dif = dict(diffs)
# (de 1 à 20 : les mots montent ; au-delà, « prises » finit sa décélération à moins d'un pixel par image et le point se pose)
immobiles = [k for k in range(1, 21) if dif.get(k, 0) < 0.02]
encre0 = accroche_diff[0][1] if accroche_diff else 0
encre_fin = dict(accroche_diff).get(27, 0)
note("F1 accroche en mouvement dès l'image 0 (chaque image de 1 à 20 change), entière à 0,90 s", encre0 > 300 and not immobiles
     and encre_fin > 0.95 * max(c for _, c in accroche_diff),
     {"encre_image0_px": encre0, "images_sans_changement_1_20": immobiles, "encre_image27_sur_max": round(encre_fin / max(c for _, c in accroche_diff), 3),
      "encre_par_image": [c for _, c in accroche_diff[:30:3]], "ecart_moyen_1_26": [round(dif.get(k, 0), 3) for k in range(1, 27, 5)]})
# F2 aucun filé, aucun saut d'objet
filtres = sorted({(o["nom"], o["filtre"]) for im in DOM["images"] for o in im.get("objets", []) if o["filtre"] not in ("none", "")})
sauts = {}
for nom in ("agenda@s4-agenda", "agenda@s5-rendez-vous", "telephone@s6-sms"):
    serie = [(im["image"], o) for im in DOM["images"] for o in im.get("objets", []) if o["nom"] == nom]
    pire = (0.0, None)
    for (n1, a), (n2, b) in zip(serie, serie[1:]):
        if n2 == n1 + 1 and a["opacite"] > 0.01 and b["opacite"] > 0.01:
            d_ = float(np.hypot(b["x"] - a["x"], b["y"] - a["y"]))
            if d_ > pire[0]:
                pire = (round(d_, 1), n2)
    sauts[nom] = pire
note("F2 aucun filé d'obturateur, objets nets : ≤ 95 px par image (≤ 90 en sortie), étirement ≤ 1,25 (D7)",
     not filtres and all(v[0] <= 95 for v in sauts.values()) and all(v[1] is not None for v in sauts.values()),
     {"filtres_vus": filtres or "aucun", "pas_max_px_image": sauts})
# F3 le SMS se lit ; le téléphone ne reste pas vide
ref = sms_encre.get(REF_SMS)
lisible = []
if ref is not None and ref.sum():
    for n_, zb in sorted(sms_encre.items()):
        if n_ <= REF_SMS:
            lisible.append((n_, float((zb & ref).sum() / ref.sum()), float((zb & ~ref).sum() / ref.sum())))
pleines = [n_ for n_, r_, x_ in lisible if r_ >= 0.97 and x_ <= 0.03]
duree_sms = (max(pleines) - min(pleines) + 1) / FPS if pleines else 0
repos = [n_ for n_, v in sorted(tel_haut.items()) if v >= 0.8]
vide = (IM("bulle_et_vibreur") - min(repos)) / FPS if repos else None
note("F3 bulle entière lisible ≥ 3,8 s ; téléphone vide ≤ 1,2 s avant la bulle ; bulle après le raccroché",
     duree_sms >= 3.8 - 1e-6 and vide is not None and vide <= 1.2 + 1e-6 and pleines and min(pleines) > IM("raccroche"),
     {"bulle_entiere_images": [min(pleines), max(pleines)] if pleines else None, "duree_lisible_s": round(duree_sms, 2),
      "telephone_au_repos_des": min(repos) if repos else None, "vide_avant_bulle_s": None if vide is None else round(vide, 2),
      "raccroche": IM("raccroche"), "bulle": IM("bulle_et_vibreur")})
# F4 aucune encre sous le point pendant qu'il lit (s2, s6)
note("F4 aucune encre sous le point ni à moins de 4 px de son bord pendant ses trajets de lecture (s2-s3, s6)", not anneau_encre,
     {"trajets": TRAJ, "images_touchees": anneau_encre[:12] or "aucune"})
# F5 marge de l'agenda
note("F5 bord gauche de l'agenda ≥ 70 px (règle 5)", marge_agenda is not None and marge_agenda >= 70,
     {"premiere_colonne_non_papier_y900": marge_agenda, "image": IM("contact_retour_neuf")})
# F6 « Vokıo » s'écrit à l'encre : bord doux derrière la plume
fin_mot = encre_mot.get(IMS("plume_mot")[1] + 3)
doux = []
if fin_mot is not None:
    prof_f = fin_mot.sum(axis=0).astype(float)
    for n_ in range(IMS("plume_mot")[0], IMS("plume_mot")[1]):
        xp = max(RESOLU[k]["x_sans"] for k in range(IMS("plume_mot")[0], n_ + 1)) - 150
        a_, b_ = int(xp - 40), int(xp)
        if a_ < 60 or b_ > 720:
            continue
        prof = encre_mot[n_].sum(axis=0).astype(float)
        bande_f = prof_f[a_:b_].sum()
        if bande_f < 1000:
            continue
        doux.append((n_, round(float(prof[a_:b_].sum() / bande_f), 2),
                     round(float(prof[max(0, a_ - 60):a_ - 10].sum() / max(1.0, prof_f[max(0, a_ - 60):a_ - 10].sum())), 2)))
ok_doux = bool(doux) and all(0.2 <= r1 <= 0.8 and r2 >= 0.9 for _, r1, r2 in doux)
note("F6 « Vokıo » s'écrit comme de l'encre : dégradé derrière la plume (la bande [xp − 40 ; xp] à moitié encrée, pleine avant)",
     ok_doux, {"images (n, bande, avant)": doux[:14]})
# F7 l'accroche est moins large que le wordmark final
def boite_encre(img_, y0, y1):
    g_ = img_.astype(np.float32)[y0:y1] @ np.array([0.299, 0.587, 0.114], np.float32)
    ys_, xs_ = np.nonzero(g_ < 120)
    return (int(xs_.min()), int(xs_.max()), int(ys_.min()) + y0, int(ys_.max()) + y0) if len(xs_) else None
b_acc = boite_encre(gardees[N_POSE], 450, 950) if N_POSE in gardees else None
b_mot = boite_encre(gardees[N_IMAGES - 1], 540, 880)
note("F7 l'accroche (0,90 s) est moins large que le wordmark final : le plan-titre est le plus grand objet du film",
     b_acc and b_mot and (b_acc[1] - b_acc[0]) < (b_mot[1] - b_mot[0]),
     {"accroche_x0_x1_y0_y1": b_acc, "wordmark_x0_x1_y0_y1": b_mot,
      "largeurs": [None if not b_acc else b_acc[1] - b_acc[0], None if not b_mot else b_mot[1] - b_mot[0]]})
# F8 l'agente parle plus fort que l'appelant (hauteur d'x des polices, aux corps du contrat)
def hx(police, corps):
    """Hauteur d'x (OS/2 sxHeight) au corps donné : fontTools n'existe que dans le python de Playwright."""
    # le glyphe « x » (BoundsPen) : l'OS/2 sxHeight de l'italique est faux (0,51 em annoncé, 0,516 dessiné… et la mesure
    # d'encre à l'œil de la revue donnait 0,40 : seul le dessin du glyphe fait foi)
    code = ("import sys; from fontTools.ttLib import TTFont; from fontTools.pens.boundsPen import BoundsPen; f = TTFont(sys.argv[1]); "
            "g = f.getGlyphSet(); p = BoundsPen(g); g[f.getBestCmap()[ord('x')]].draw(p); "
            "print(p.bounds[3] * float(sys.argv[2]) / f['head'].unitsPerEm)")
    r = subprocess.run(["/root/.pwtest/bin/python", "-c", code, str(PROJET / "assets" / "fonts" / police), str(corps)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())
G_ = D["geometrie"]
hx_a = hx("Geist-Regular.woff2", G_["sous_titres_haut"]["agente"]["corps"])
hx_c = hx("InstrumentSerif-Italic.woff2", G_["sous_titres_haut"]["appelant"]["corps"])
note("F8 hauteur d'x de l'agente ≥ 1,15 × celle de l'appelant", hx_a >= 1.15 * hx_c and G_["s3_texte"]["corps"] == G_["sous_titres_haut"]["appelant"]["corps"],
     {"agente_Geist": [G_["sous_titres_haut"]["agente"]["corps"], round(hx_a, 1)], "appelant_Instrument_Serif_italique": [G_["sous_titres_haut"]["appelant"]["corps"], round(hx_c, 1)],
      "rapport": round(hx_a / hx_c, 3)})

# ── planches ──
def planche(nums, fichier, colonnes, echelle, source=None):
    source = source or gardees
    fnt = ImageFont.truetype(POLICE, max(12, int(80 * echelle)))
    w, h = int(W * echelle), int(H * echelle)
    lignes = (len(nums) + colonnes - 1) // colonnes
    P = Image.new("RGB", (colonnes * (w + 6) + 6, lignes * (h + 6) + 6), (150, 150, 150))
    d = ImageDraw.Draw(P)
    for i, k in enumerate(nums):
        if k not in source:
            continue
        x, y = 6 + (i % colonnes) * (w + 6), 6 + (i // colonnes) * (h + 6)
        P.paste(Image.fromarray(source[k]).resize((w, h), Image.LANCZOS), (x, y))
        d.text((x + 6, y + 4), f"{k} · {k / FPS:.2f}s", font=fnt, fill=(192, 69, 44))
    P.save(fichier)
    return str(fichier)

pl = {"1 image / s": planche(list(range(0, N_IMAGES, 30)), SORTIE / "planche-1s.png", 9, 0.2),
      "1 image / 0,5 s": planche(list(range(0, N_IMAGES, 15)), SORTIE / "planche-0,5s.png", 10, 0.2),
      "images clés": planche(sorted(CLES), SORTIE / "planche-cles.png", 8, 0.25),
      "vue téléphone 393 px": planche([12, 127, 300, 430, 600, 705, 821, 973, 1150, N_RE, N_IMAGES - 1], SORTIE / "vue-telephone-393.png", 6, 393 / W)}
for b in RACCORDS:
    pl[f"raccord-{b}"] = planche(list(range(b - 3, b + 3)), SORTIE / f"raccord-{b}.png", 6, 0.3)
for k, im in pelures.items():
    if im is not None:
        Image.fromarray(im).save(SORTIE / f"pelure-{k}.png")
        pl[f"pelure {k}"] = str(SORTIE / f"pelure-{k}.png")
rapport["planches"] = pl
rapport["raccords_diff"] = {b: [(k, round(m, 2)) for (k, m) in diffs if b - 3 <= k <= b + 2] for b in RACCORDS}

# ── S2. Mots à ±1 image de leur attaque (MP4) ──
PAR_LIGNE = {"C2", "C3", "C4"}      # l'appelant monte ligne par ligne, d'un bloc, au premier mot dit de chaque ligne
meneurs = {}
for w in mots_dom:
    if w["extrait"] in PAR_LIGNE:
        k = (w["scene"], w["extrait"], round(w["y0"]))
        if k not in meneurs or w["rang"] < meneurs[k]["rang"]:
            meneurs[k] = w
sync = []
for w in mots_dom:
    s = w["serie"]
    if not s:
        continue
    ks = sorted(s)
    haut = max([s[k] for k in ks if w["image"] <= k <= w["image"] + 12] or [1]) or 1
    derniere_vide = None
    for k in ks:
        if k > w["image"] + 8:
            break
        if s[k] < 0.03 * haut:
            derniere_vide = k
    apparait = derniere_vide + 1 if derniere_vide is not None else None
    porte = w["extrait"] in PAR_LIGNE and meneurs[(w["scene"], w["extrait"], round(w["y0"]))] is not w
    sync.append({"mot": w["texte"], "extrait": w["extrait"], "rang": w["rang"], "par_ligne": porte, "image_attaque": w["image"],
                 "image_apparition": apparait, "ecart_images": None if apparait is None else apparait - w["image"]})
individuels = [x for x in sync if not x["par_ligne"]]
mauvais = [x for x in individuels if x["ecart_images"] is None or abs(x["ecart_images"]) > 1]
rapport["synchro_mots"] = sync
note("S2 mots à ±1 image de leur attaque (MP4)", not mauvais,
     {"mots_mesures": len(individuels), "hors_tolerance": mauvais[:8],
      "ecarts_images": {str(e): sum(1 for x in individuels if x["ecart_images"] == e) for e in sorted({x["ecart_images"] for x in individuels if x["ecart_images"] is not None})},
      "portes_par_leur_ligne": [(x["mot"], x["image_attaque"], x["image_apparition"]) for x in sync if x["par_ligne"]]})

# ═════════════════════════════ A et S1. Audio ═════════════════════════════
SR = 48000


def ebur(chemin):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(chemin), "-map", "0:a", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    return (float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1]),
            float(re.findall(r"LRA:\s+(-?[\d.]+) LU", r)[-1]))


def pcm(chemin):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(chemin), "-map", "0:a", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2)


def db(x):
    return float(20 * np.log10(x + 1e-12))

I_, tp, lra = ebur(FILM)
A = pcm(FILM)
M = pcm(PROJET / "son" / "mix.wav")
SN, SF = T("silence_numerique"), T("silence_final")
z1 = A[int(round((SN[0] + 0.004) * SR)):int(round((SN[1] - 0.007) * SR))]
z2 = A[int(round(SF[0] * SR)):int(round(SF[1] * SR))]
ton = float(np.sqrt(np.mean(A[:int(0.02 * SR)].astype(np.float64) ** 2)))
seg_m = M[4 * SR:8 * SR, 0].astype(np.float64)
best = max(((dec, float(A[4 * SR + dec:4 * SR + dec + len(seg_m), 0].astype(np.float64) @ seg_m)) for dec in range(-2400, 2401)
            if len(A[4 * SR + dec:4 * SR + dec + len(seg_m)]) == len(seg_m)), key=lambda z: z[1])
n_ = min(len(A), len(M))
residu = db(np.sqrt(np.mean((A[:n_] - M[:n_]).astype(np.float64) ** 2))) if best[0] == 0 else None
ok_a = abs(I_ + 14) <= 0.5 and tp <= -1.0 and db(np.abs(z1).max()) < -90 and db(np.abs(z2).max()) < -90 and db(ton) > -40 and best[0] == 0
note("A1 audio du MP4 (−14 ± 0,5 LUFS, ≤ −1 dBTP, zéros, tonalité, calage sur mix.wav)", ok_a,
     {"LUFS": I_, "crete_vraie_dBTP": tp, "LRA": lra, "plan.controles 6 (±0,3 ; ≤ −1,5)": abs(I_ + 14) <= 0.3 and tp <= -1.5,
      f"zeros_{SN[0] + 0.004:.2f}-{SN[1] - 0.007:.2f}": {"crete_dBFS": round(db(np.abs(z1).max()), 1), "part_zero_exact": round(float((z1 == 0).mean()), 4)},
      f"zeros_{SF[0]:.2f}-{SF[1]:.2f}": {"crete_dBFS": round(db(np.abs(z2).max()), 1), "part_zero_exact": round(float((z2 == 0).mean()), 4)},
      "tonalite_20ms_dB": round(db(ton), 1), "decalage_mp4_mix_echantillons": best[0],
      "residu_aac_dB": None if residu is None else round(residu, 1), "duree_audio_s": round(len(A) / SR, 4)})


def attaque_seuil(x, t, avant=0.05):
    """Premier échantillon au-dessus de −40 dBFS (ou 12 dB au-dessus du fond qui précède) après t − 50 ms."""
    m = np.abs(x).max(axis=1)
    fond = np.sqrt(np.mean(m[max(0, int((t - 0.20) * SR)):max(1, int((t - avant) * SR))] ** 2) + 1e-20)
    seuil = max(10 ** (-40 / 20), fond * 10 ** (12 / 20))
    i0 = max(0, int((t - avant) * SR))
    k = np.nonzero(m[i0:i0 + int(0.2 * SR)] > seuil)[0]
    return None if not len(k) else (i0 + int(k[0])) / SR


sys.path.insert(0, str(PROJET / "son"))
import signature as SIG      # générateurs déterministes des notes (son/signature.py) : références du filtre adapté
REF = {"sol": SIG.note_sol(0.15), "re": SIG.note_re(0.15)}


def attaque_adaptee(x, t, note, fenetre=0.010):
    """Attaque d'une note qui entre pendant que la précédente sonne : filtre adapté (corrélation normalisée de la
    somme L + R avec la note seule, générée par son/signature.py) sur t ± fenetre. Ambiguïté possible d'une période
    (2,55 ms pour le sol, 1,70 ms pour le ré) : on rend le meilleur décalage et les deux suivants."""
    ref = REF[note] if REF[note].ndim == 1 else REF[note].mean(axis=1)
    s = x.astype(np.float64).sum(axis=1)
    i, k = int(round(t * SR)), int(round(fenetre * SR))
    rr = float(ref @ ref)
    sc_ = []
    for lag in range(-k, k + 1):
        seg = s[i + lag:i + lag + len(ref)]
        sc_.append((float(seg @ ref) / np.sqrt(float(seg @ seg) * rr + 1e-30), lag))
    sc_.sort(reverse=True)
    return (i + sc_[0][1]) / SR, [(round(c, 4), round(l / SR * 1000, 2)) for c, l in sc_[:3]]


CUES = {c["id"]: c for c in json.loads((PROJET / "son" / "cues.json").read_text())["cues"]}
STEMS = {s: pcm(PROJET / "son" / "stems" / f"{s}.wav") for s in ("sfx", "signature", "nappe")}
T_SOL_ECR = round(T("ecriture_debut") + d_sol, 6)
attendus = [  # (nom, id du cue, instant attendu lu dans DONNEES, détecteur)
    ("décroché", "clic-decroche", T("decroche"), None),
    ("toucher 09:00", "tap-9h", T("contact_neuf"), None),
    ("toucher 10:00", "tap-10h", T("contact_dix"), None),
    ("toucher 11:00", "tap-11h", T("contact_onze"), None),
    ("retour 09:00", "tap-retour-9h", T("contact_retour_neuf"), None),
    ("écriture, la", "cloche-la-rdv", T("ecriture_debut"), None),
    ("écriture, sol", "cloche-sol-rdv", T_SOL_ECR, "sol"),
    ("raccroché", "raccroche", T("raccroche"), None),
    ("vibreur", "vibreur", T("bulle_et_vibreur"), None),
    ("signature, la", "signature-la", T("signature_la"), None),
    ("signature, sol", "signature-sol", T("signature_sol"), "sol"),
    ("signature, ré", "signature-re", T("signature_re_contact"), "re"),
]
mes = {}
for nom, cid, t, bande in attendus:
    c = CUES.get(cid)
    st = STEMS.get(c["stem"]) if c else None
    cand = None
    if st is None:
        ta = None
    elif bande:
        ta, cand = attaque_adaptee(st, t, bande)
    else:
        ta = attaque_seuil(st, t)
    mes[nom] = {"cue": cid, "stem": c["stem"] if c else None, "cue_t": c["t"] if c else None, "attendu_s": round(t, 6),
                "image_attendue": int(round(t * FPS)), "mesure_s": None if ta is None else round(ta, 5),
                "ecart_ms": None if ta is None else round((ta - t) * 1000, 2),
                "methode": ("filtre adapté " + str(cand)) if cand else "seuil −40 dBFS / fond + 12 dB"}
for nom, t, bande in (("signature la, sur le MP4", T("signature_la"), None), ("signature ré, sur le MP4", T("signature_re_contact"), "re")):
    cand = None
    if bande:
        ta, cand = attaque_adaptee(A, t, bande)
    else:
        ta = attaque_seuil(A, t)
    mes[nom] = {"stem": "mp4", "attendu_s": t, "mesure_s": None if ta is None else round(ta, 5),
                "ecart_ms": None if ta is None else round((ta - t) * 1000, 2), "methode": ("filtre adapté " + str(cand)) if cand else "seuil"}
ok_s1 = all(v["ecart_ms"] is not None and abs(v["ecart_ms"]) <= 5 and (v.get("cue_t") is None or abs(v["cue_t"] - v["attendu_s"]) < 1e-5)
            for v in mes.values())
note("S1 synchro son et image (±5 ms, stems et MP4 ; cues posés aux instants de DONNEES)", ok_s1, mes)

SON = json.loads((PROJET / "son" / "mesures-son.json").read_text())
rapport["son_mesures_du_chantier_son"] = SON.get("synthese_ok")
hp = SON["H_haut_parleur"]
arc = SON["M_arc_de_sonie"]
sig = SON["G_mono"]["signature_film"]
res = SON["B_silences"]["resolution_seule_33.05-34.03"]
detail_son = {
    "voix_sur_reste_LU_min": SON["F_voix_sur_reste_LU"]["min"],
    "signature_moins_mediane_LU": arc["signature_moins_mediane_LU"], "instantanee_au_re_LUFS": arc["instantanee_au_re_mix"],
    "M_max_au_re": arc["M_max_au_re"], "M_max_dialogue": arc["M_max_dialogue_5-35.5"], "S_max_apres_la": arc["S_max_apres_la"],
    "S_max_dialogue": arc["S_max_dialogue_5-35.4"],
    "hp_perte_nappe_db": hp["perte_nappe_db"], "hp_pedale_ok": hp["pedale_ok"],
    "hp_touchers_3-8k_db": {t["contact"]: t["tap_moins_voix_3-8k_db"] for t in hp["touchers"]},
    "hp_signature_db": hp["signature_hp_moins_pleine_bande_db"],
    "signature_correlation": sig["correlation_LR"], "signature_perte_mono_db": sig["perte_mono_db"],
    "resolution_seule": res.get("sfx_zero") and res.get("signature_zero"), "clics": SON["K_clics_hf"],
}
ok_son = (SON["F_voix_sur_reste_LU"]["min"] >= 10 and arc["signature_moins_mediane_LU"] >= 1 and hp["pedale_ok"]
          and all(t["tap_moins_voix_3-8k_db"] >= 6 for t in hp["touchers"])
          and max(-v for v in hp["perte_nappe_db"].values()) <= 7 and hp["signature_hp_moins_pleine_bande_db"] >= -3
          and 0.75 <= sig["correlation_LR"] <= 0.85 and sig["perte_mono_db"] >= -1 and detail_son["resolution_seule"]
          and SON["K_clics_hf"].get("ok", True) and arc["M_max_au_re"] >= arc["M_max_dialogue_5-35.5"]
          and arc["S_max_apres_la"][0] >= arc["S_max_dialogue_5-35.4"])
# Critère du ré : l'intention du plan (« le ré passe au-dessus de la voix », estimée à ≈ −11,5 LUFS à l'échelle v1) ; à
# l'échelle v2 la voix culmine vers −10 LUFS instantanés : on exige que le ré soit l'instant le plus fort du film (sonie
# instantanée) et que la fin passe au-dessus du pic du dialogue en sonie court terme (demande de la revue Florian).
note("A2 son (plan.controles 6, relu dans son/mesures-son.json ; ré = instant le plus fort)", ok_son, detail_son)

# ═════════════════════════════ L. Livraison ═════════════════════════════
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(FILM)],
                               capture_output=True, text=True).stdout)
v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
a = [s for s in pr["streams"] if s["codec_type"] == "audio"]
flux = {"video": f'{v["codec_name"]} {v["width"]}x{v["height"]} {v["r_frame_rate"]} {v.get("nb_read_frames")} images {float(v["duration"]):.3f} s {v.get("pix_fmt")}',
        "audio": [f'{s["codec_name"]} {s["sample_rate"]} Hz {s["channels"]} canaux {float(s["duration"]):.3f} s {int(s.get("bit_rate", 0)) // 1000} kb/s' for s in a],
        "format": f'{float(pr["format"]["duration"]):.3f} s'}
note("L1 flux (ffprobe)", v["codec_name"] == "h264" and v["width"] == W and v["height"] == H and v["r_frame_rate"] == "30/1"
     and int(v.get("nb_read_frames", 0)) == N_IMAGES and abs(float(v["duration"]) - DUREE) <= 0.02 and len(a) == 1
     and a[0]["codec_name"] == "aac" and a[0]["sample_rate"] == "48000" and a[0]["channels"] == 2
     and int(a[0].get("bit_rate", 0)) // 1000 >= 192 and n == N_IMAGES, flux)   # encodé en -b:a 256k (nominal) ; le débit moyen mesuré baisse sur les silences

rapport["echecs"] = echecs
(SORTIE / "controles.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=str))
print(f"\n{len(echecs)} échec(s) : {echecs}" if echecs else "\nTous les contrôles passent.")
print(f"rapport : {SORTIE / 'controles.json'}")
