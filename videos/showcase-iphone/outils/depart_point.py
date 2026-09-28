#!/usr/bin/env python3
"""Départ du point vers le stylo (s6 → s7) image par image, et balayage de son arc : usage en une ligne :

    python3 outils/depart_point.py <racine> [--arc dx,dy] [--balayer dx0:dx1:pas,dy0:dy1:pas] [--garder 12] [--json r.json]

  <racine> : un projet rendable (ce projet = le 9:16, formats/16x9, ou une copie de format.py --dossier, variante comprise).
  Relit SES données (donnees/donnees.js), puis évalue le point avec LE MÊME code que le film (lib/point.js et GSAP de la
  racine, dans node) et le téléphone avec la même loi que compositions/s6-sms.html (sortie −y_sortie en power3.in sur
  DONNEES.evenements.telephone_sortie, opaque FONDU_SORTIE images puis sine.inOut ; FONDU_SORTIE lu dans la scène).
  De l'image depart_stylo à l'arrivée au stylo (clé suivante de DONNEES.point.position), pour chaque image :
    centre (x ; y), rayon visible, pas (px par image), coude (degrés entre deux pas), translation et opacité du téléphone,
    écart à la bulle et à sa queue (même mesure que IPHONE.controlerDepart, lib/iphone.js), et où est le disque :
    « écran » (sur le verre, à droite du bord de l'écran), « bord » (il chevauche le cadre ou le contour du corps),
    « papier » (tout entier à gauche du contour) ; « hors » = part du disque au-delà du contour (0 → 1).
  Bilan d'un arc : écart minimal à la bulle (IPHONE.controlerDepart, le contrôle du film), pas maximal, coude maximal,
    Σ opacité × hors (le point vu au-delà du contour d'un téléphone encore visible : 0 = « jamais au-delà de son contour »),
    Σ opacité × [bord] (le temps passé à cheval sur le cadre, pondéré), image et opacité de la sortie du contour.
  --arc dx,dy : remplace l'arc du départ (clé d'arrivée au stylo) sans rien reconstruire (défaut : celui des données).
  --balayer : grille d'arcs ; garde ceux qui passent les contraintes (--marge px de la bulle, défaut 11 ; --pas-max, défaut
    95), triés par Σ o·hors puis Σ o·bord puis coude ; imprime les --garder premiers, et le tableau du meilleur.
  --json : écrit le bilan (et les images) de chaque arc évalué.
Lecture seule (n'écrit que --json). Après choix : reporter l'arc dans mise-en-page/s6-sms.json (« depart_stylo_arc » de
l'entrée du format ou de la variante), reconstruire (outils/format.py), le film le contrôle (s6-sms.html, controles.py F4).
"""
import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

JS = r"""
const fs = require("fs"), vm = require("vm");
const [racine, arcsJson, fondu] = process.argv.slice(2);
const G = require(racine + "/lib/vendor/gsap.min.js");
const arcs = JSON.parse(arcsJson);
function contexte(arc) {
  const ctx = { console: console, gsap: G.gsap || G.default }; ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(racine + "/donnees/donnees.js", "utf8"), ctx);
  const D = ctx.DONNEES, pos = D.point.position, EV = D.evenements;
  const i = pos.findIndex(function (k) { return Math.abs(k.t - EV.depart_stylo.t) < 1e-4; });
  if (i < 0 || i + 1 >= pos.length) throw new Error("clé du départ vers le stylo introuvable");
  if (arc) pos[i + 1].arc = { dx: arc[0], dy: arc[1] };
  vm.runInContext(fs.readFileSync(racine + "/lib/point.js", "utf8"), ctx);
  vm.runInContext(fs.readFileSync(racine + "/lib/iphone.js", "utf8"), ctx);
  return { ctx: ctx, D: D, depart: pos[i], arrivee: pos[i + 1] };
}
function distanceRect(px, py, x0, y0, x1, y1, r) {
  const qx = Math.abs(px - (x0 + x1) / 2) - ((x1 - x0) / 2 - r), qy = Math.abs(py - (y0 + y1) / 2) - ((y1 - y0) / 2 - r);
  return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
}
const out = [];
for (const arc of arcs) {
  const C = contexte(arc), P = C.ctx.POINT, IP = C.ctx.IPHONE, D = C.D, EV = D.evenements, FPS = D.fps;
  const G6 = D.geometrie.s6, TEL = G6.telephone, ECR = G6.ecran, BU = G6.bulle, K = G6.pt;
  const YS = G6.y_sortie != null ? G6.y_sortie : 300;
  const TS = EV.telephone_sortie.t, DS = TS[1] - TS[0];
  const TF0 = +(TS[0] + (+fondu) / FPS).toFixed(6), DF = TS[1] - TF0;
  const eS = P.ease("power3.in"), eF = P.ease("sine.inOut");
  const enImage = function (n) { return +(n / FPS).toFixed(6); };
  function etat(t) {          // la loi de sortie de compositions/s6-sms.html (etatTel), après l'entrée
    if (t <= TS[0]) return { y: 0, o: 1 };
    if (t < TS[1]) { const u = (t - TS[0]) / DS, v = Math.max(0, (t - TF0) / DF); return { y: -YS * eS(u), o: 1 - eF(Math.min(1, v)) }; }
    return { y: -YS, o: 0 };
  }
  const n0 = EV.depart_stylo.image, n1 = Math.round(C.arrivee.t * FPS);
  const lignes = []; let prec = null, dirPrec = null;
  for (let n = n0; n <= n1; n++) {
    const t = enImage(n), e = P.etat(t), tel = etat(t);
    const r = e.d / 2 * Math.max(e.sx, e.sy);
    const dB = distanceRect(e.x, e.y, BU.x0, BU.haut + tel.y, BU.x1, BU.bas + tel.y, BU.rayon_pt * K);
    const dQ = distanceRect(e.x, e.y, BU.x0 + 8 * K, BU.bas + tel.y - 1, BU.x0 + 24 * K, BU.queue_pointe.y + tel.y + 0.5, 0);
    const pas = prec ? Math.hypot(e.x - prec.x, e.y - prec.y) : 0;
    let coude = null;
    if (prec && pas > 2) {
      const d = Math.atan2(e.y - prec.y, e.x - prec.x) * 180 / Math.PI;
      if (dirPrec != null) { coude = Math.abs(((d - dirPrec + 540) % 360) - 180); }
      dirPrec = d;
    }
    const hors = Math.min(1, Math.max(0, (TEL.x0 - (e.x - r)) / (2 * r)));
    const ou = e.x - r >= ECR.x0 ? "écran" : (e.x + r <= TEL.x0 ? "papier" : "bord");
    lignes.push({ n: n, t: t, x: +e.x.toFixed(1), y: +e.y.toFixed(1), r: +r.toFixed(1), pas: +pas.toFixed(1),
                  coude: coude == null ? null : +coude.toFixed(1), tel_y: +tel.y.toFixed(1), tel_o: +tel.o.toFixed(3),
                  ecart_bulle: tel.o > 0.01 ? +(Math.min(dB, dQ) - r).toFixed(1) : null, ou: ou, hors: +hors.toFixed(2),
                  bord_gauche_contour: +(e.x - TEL.x0).toFixed(1) });
    prec = e;
  }
  const echecs = [];
  const pire = IP.controlerDepart(G6, etat, n0, EV.telephone_sortie.images[1], enImage, function (ok, msg) { if (!ok) echecs.push(msg); });
  const vis = lignes.filter(function (l) { return l.tel_o > 0.01; });
  const sortie = lignes.find(function (l) { return l.hors > 0; });
  out.push({ arc: arc || C.arrivee.arc || null, de: [C.depart.x, C.depart.y], vers: [C.arrivee.x, C.arrivee.y], images: [n0, n1],
             contour_x: TEL.x0, ecran_x: ECR.x0, bulle_x0: BU.x0,
             bilan: { ecart_bulle_min: +pire.toFixed(1), echecs_controlerDepart: echecs.length,
                      pas_max: Math.max.apply(null, lignes.map(function (l) { return l.pas; })),
                      coude_max: Math.max.apply(null, lignes.map(function (l) { return l.coude || 0; })),
                      somme_o_hors: +vis.reduce(function (s, l) { return s + l.tel_o * l.hors; }, 0).toFixed(2),
                      somme_o_bord: +vis.reduce(function (s, l) { return s + (l.ou === "bord" ? l.tel_o : 0); }, 0).toFixed(2),
                      sortie_contour: sortie ? { image: sortie.n, tel_o: sortie.tel_o } : null },
             lignes: lignes });
}
process.stdout.write(JSON.stringify(out));
"""


def evaluer(racine, arcs):
    racine = Path(racine).resolve()
    h = (racine / "compositions" / "s6-sms.html").read_text()
    m = re.search(r"const FONDU_SORTIE = (\d+)", h)
    if not m:
        raise SystemExit("FONDU_SORTIE introuvable dans compositions/s6-sms.html : la loi du téléphone a changé, relire la scène")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(JS)
    r = subprocess.run(["node", f.name, str(racine), json.dumps(arcs), m.group(1)], capture_output=True, text=True)
    Path(f.name).unlink()
    if r.returncode:
        raise SystemExit("node : " + r.stderr[-3000:])
    return json.loads(r.stdout)


def plage(s):
    a, b, p = (float(v) for v in s.split(":"))
    n = int(round((b - a) / p))
    return [round(a + i * p, 3) for i in range(n + 1)]


def tableau(res):
    print(f"de ({res['de'][0]} ; {res['de'][1]}) vers ({res['vers'][0]} ; {res['vers'][1]}), images {res['images'][0]} → "
          f"{res['images'][1]}, arc {res['arc']} ; contour du corps x {res['contour_x']}, bord de l'écran x {res['ecran_x']}, "
          f"bulle x0 {res['bulle_x0']:.1f}")
    print("   n       x       y   pas  coude  tél y  tél o  bulle   où      hors  x−contour")
    for l in res["lignes"]:
        print(f"{l['n']:5d} {l['x']:7.1f} {l['y']:7.1f} {l['pas']:5.1f} {'' if l['coude'] is None else l['coude']:>6} "
              f"{l['tel_y']:6.1f} {l['tel_o']:6.3f} {'' if l['ecart_bulle'] is None else l['ecart_bulle']:>6}   {l['ou']:<7} "
              f"{l['hors']:4.2f} {l['bord_gauche_contour']:8.1f}")
    b = res["bilan"]
    print(f"bilan : écart bulle min {b['ecart_bulle_min']} px ({b['echecs_controlerDepart']} échec(s) du contrôle du film, ≥ 6), "
          f"pas max {b['pas_max']}, coude max {b['coude_max']}°, Σ o·hors {b['somme_o_hors']}, Σ o·bord {b['somme_o_bord']}, "
          f"sortie du contour {b['sortie_contour']}")


def main():
    A = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    A.add_argument("racine")
    A.add_argument("--arc")
    A.add_argument("--balayer")
    A.add_argument("--marge", type=float, default=11)
    A.add_argument("--pas-max", type=float, default=95)
    A.add_argument("--garder", type=int, default=12)
    A.add_argument("--json")
    a = A.parse_args()
    if a.balayer:
        gx, gy = (plage(s) for s in a.balayer.split(","))
        res = evaluer(a.racine, [[dx, dy] for dx in gx for dy in gy])
        ok = [r for r in res if r["bilan"]["ecart_bulle_min"] >= a.marge and r["bilan"]["pas_max"] <= a.pas_max]
        ok.sort(key=lambda r: (r["bilan"]["somme_o_hors"], r["bilan"]["somme_o_bord"], r["bilan"]["coude_max"]))
        print(f"{len(res)} arcs évalués, {len(ok)} passent (écart bulle ≥ {a.marge} px, pas ≤ {a.pas_max} px)")
        print("    dx     dy   bulle   pas  coude  Σo·hors  Σo·bord  sortie du contour")
        for r in ok[:a.garder]:
            b = r["bilan"]
            print(f"{r['arc'][0]:6.0f} {r['arc'][1]:6.0f} {b['ecart_bulle_min']:7.1f} {b['pas_max']:5.1f} {b['coude_max']:6.1f} "
                  f"{b['somme_o_hors']:8.2f} {b['somme_o_bord']:8.2f}  {b['sortie_contour']}")
        if ok:
            print()
            tableau(ok[0])
    else:
        arc = [float(v) for v in a.arc.split(",")] if a.arc else None
        res = evaluer(a.racine, [arc])
        tableau(res[0])
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
