#!/usr/bin/env python3
"""Réapplique les correctifs apportés aux skills HyperFrames livrées.

Les skills vivent dans `.agents/skills/`, et `hyperframes skills update` les
réécrit. Sans ce script, une mise à jour ferait silencieusement revenir cinq
défauts qui ont coûté une soirée à trouver. Trois d'entre eux ne se voient
PAS : ils ne cassent rien, ils produisent un film faux.

    rustines.py            dit ce qui manque
    rustines.py --poser    réapplique

À lancer après tout `hyperframes skills update` ou toute réinstallation.
"""
import argparse
import shutil
import sys
from pathlib import Path

S = Path("/opt/vokio-ads/.agents/skills")
DIST = Path("/root/.npm/_npx")

RUSTINES = []


def rustine(nom, fichier, pourquoi):
    def deco(f):
        RUSTINES.append((nom, S / fichier, pourquoi, f))
        return f
    return deco


# ─────────────────────────────────────────────────────────────────────────────
@rustine("shims media-use", "media-use/scripts/resolve.mjs",
         "Deux fichiers de media-use réexportent un chemin du dépôt amont "
         "(packages/cli/src/…) qui n'existe pas dans une installation normale. "
         "Le moteur audio meurt sur ERR_MODULE_NOT_FOUND avant de démarrer.")
def shims(poser):
    dist = next(DIST.glob("*/node_modules/hyperframes/dist/skills"), None)
    manque = [f for f in ("media-use/scripts/resolve.mjs",
                          "media-use/scripts/lib/media-fetch.mjs")
              if "packages/cli/src" in (S / f).read_text()]
    if not manque or not poser:
        return manque
    if dist is None:
        raise SystemExit("paquet hyperframes introuvable dans le cache npx : "
                         "lancer une commande `bin/hf` d'abord")
    for f in manque:
        shutil.copy(dist / f, S / f)
    return manque


# ─────────────────────────────────────────────────────────────────────────────
@rustine("langue transmise au moteur", "product-launch-video/scripts/audio.mjs",
         "Le workflow ne transmet pas la langue du storyboard. Le moteur "
         "retombe sur « en », donc sur le modèle Whisper small.en, qui TRADUIT "
         "au lieu de transcrire : la ligne 3 est revenue en « Thank you for "
         "watching and see you next week ». Rien ne plante, le film est faux.")
def langue(poser):
    p = S / "product-launch-video/scripts/audio.mjs"
    t = p.read_text()
    if "    lang,\n    lines," in t:
        return []
    if not poser:
        return ["audio.mjs"]
    av = "  const request = {\n    provider,\n    speed,\n    lines,"
    ap = ('  const lang = String(g.language ?? g.extra?.language ?? "en").trim() || "en";\n'
          "  const request = {\n    provider,\n    speed,\n    lang,\n    lines,")
    assert t.count(av) == 1, "ancrage de la langue introuvable"
    p.write_text(t.replace(av, ap))
    return ["audio.mjs"]


# ─────────────────────────────────────────────────────────────────────────────
@rustine("fr-fr contre fr", "media-use/audio/scripts/lib/tts.mjs",
         "Un seul champ `lang` alimente deux vocabulaires incompatibles : le "
         "phonémiseur Kokoro veut fr-fr, Whisper veut fr. Passer l'un à "
         "l'autre échoue des deux côtés.")
def codes_langue(poser):
    p = S / "media-use/audio/scripts/lib/tts.mjs"
    t = p.read_text()
    if "versPhonemiseur(lang)" in t:
        return []
    if not poser:
        return ["tts.mjs"]
    carte = '''
const PHONEMIZER = {
  en: "en-us", "en-us": "en-us", "en-gb": "en-gb",
  fr: "fr-fr", "fr-fr": "fr-fr",
  es: "es", it: "it", hi: "hi", ja: "ja", zh: "zh",
  pt: "pt-br", "pt-br": "pt-br",
};
const versPhonemiseur = (l) => PHONEMIZER[String(l).toLowerCase()] ?? l;
const versISO = (l) => String(l).toLowerCase().split("-")[0];
'''
    paires = [
        ('  if (lang !== "en") args.push("--lang", lang);',
         '  if (versISO(lang) !== "en") args.push("--lang", versPhonemiseur(lang));'),
        ('  const model = lang === "en" ? "small.en" : "small";',
         '  const iso = versISO(lang);\n  const model = iso === "en" ? "small.en" : "small";'),
        ('  if (lang !== "en") args.push("--language", lang);',
         '  if (iso !== "en") args.push("--language", iso);'),
    ]
    for av, ap in paires:
        assert t.count(av) == 1, f"ancrage introuvable : {av[:40]}"
        t = t.replace(av, ap)
    i = t.rindex("\nimport ")
    j = t.index("\n", t.index(";", i))
    p.write_text(t[:j + 1] + carte + t[j + 1:])
    return ["tts.mjs"]


# ─────────────────────────────────────────────────────────────────────────────
@rustine("bande de sous-titres réglable", "product-launch-video/scripts/lib/dimensions.mjs",
         "La bande par défaut occupe les 320 px du bas du cadre. En 9:16 c'est "
         "là que Reels et TikTok dessinent leur interface, et la charte Vokio "
         "interdit tout texte important sous y=1500.")
def bande(poser):
    p = S / "product-launch-video/scripts/lib/dimensions.mjs"
    t = p.read_text()
    if 'entierEnv("HF_CAPTION_BAND_HEIGHT")' in t:
        return []
    if not poser:
        return ["dimensions.mjs"]
    av = """export function captionBand(height, safetyPx = 20) {
  const h = Number.isFinite(height) ? height : DEFAULT_DIMENSIONS.height;
  const bandHeight = Math.round(h * CAPTION_BAND_FRACTION);
  const bandTopY = h - bandHeight; // foreground must end at/above this y
  return { bandHeight, bandTopY, foregroundMaxY: bandTopY - safetyPx };
}"""
    ap = """function entierEnv(nom) {
  const v = parseInt(process.env[nom] ?? "", 10);
  return Number.isFinite(v) && v > 0 ? v : null;
}
export function captionBand(height, safetyPx = 20) {
  const h = Number.isFinite(height) ? height : DEFAULT_DIMENSIONS.height;
  const bandHeight = entierEnv("HF_CAPTION_BAND_HEIGHT") ?? Math.round(h * CAPTION_BAND_FRACTION);
  const bandTopY = entierEnv("HF_CAPTION_BAND_TOP") ?? h - bandHeight;
  return { bandHeight, bandTopY, foregroundMaxY: bandTopY - safetyPx };
}"""
    assert t.count(av) == 1, "ancrage de la bande introuvable"
    p.write_text(t.replace(av, ap))
    return ["dimensions.mjs"]


# ─────────────────────────────────────────────────────────────────────────────
@rustine("sous-titres : opt-out et regroupement", "product-launch-video/scripts/captions.mjs",
         "Deux manques. Un plan dont le texte à l'écran EST déjà la phrase "
         "prononcée n'a aucun moyen de refuser la bande (le seul réglage est "
         "tout ou rien). Et le découpage casse sur chaque virgule, ce qui "
         "produit des sous-titres d'une demi-seconde, illisibles quand l'image "
         "bouge en même temps.")
def sous_titres(poser):
    p = S / "product-launch-video/scripts/captions.mjs"
    t = p.read_text()
    manque = []
    if "plansSansSousTitre.has(v.frame)" not in t:
        manque.append("opt-out par plan")
    if "!parPlan && cur && cur.words.length" not in t:
        manque.append("regroupement par plan")
    if not manque or not poser:
        return manque

    if "plansSansSousTitre.has(v.frame)" not in t:
        av = """  // absolute word stream: frame start + frame-relative word timing.
  const words = [];
  for (const v of meta.voices) {
    const base = startByFrame.get(v.frame);
    if (base == null || !Array.isArray(v.words)) continue;"""
        ap = """  const SANS_SOUSTITRE = new Set(["none", "no", "off", "aucun", "skip", "-"]);
  const plansSansSousTitre = new Set(
    manifest.frames
      .filter((f) => SANS_SOUSTITRE.has(String(f.extra?.captions ?? "").trim().toLowerCase()))
      .map((f) => f.number),
  );
  if (plansSansSousTitre.size) {
    console.log(`  · sans sous-titre : plan(s) ${[...plansSansSousTitre].join(", ")}`);
  }

  // absolute word stream: frame start + frame-relative word timing.
  const words = [];
  for (const v of meta.voices) {
    if (plansSansSousTitre.has(v.frame)) continue;
    const base = startByFrame.get(v.frame);
    if (base == null || !Array.isArray(v.words)) continue;"""
        assert t.count(av) == 1, "ancrage de l'opt-out introuvable"
        t = t.replace(av, ap)

    if "!parPlan && cur && cur.words.length" not in t:
        t = t.replace("  const groups = [];\n  let cur = null;",
                      '  const parPlan = String(process.env.HF_CAPTION_GROUP ?? "").toLowerCase() === "frame";\n'
                      "  const groups = [];\n  let cur = null;", 1)
        t = t.replace("    const full = cur && cur.words.length >= cur.cap;",
                      "    const full = !parPlan && cur && cur.words.length >= cur.cap;", 1)
        t = t.replace("    if (SENT_END.test(w.text)) {",
                      "    if (!parPlan && SENT_END.test(w.text)) {", 1)
    p.write_text(t)
    return manque


# ─────────────────────────────────────────────────────────────────────────────
a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
a.add_argument("--poser", action="store_true")
a = a.parse_args()

total = 0
for nom, fichier, pourquoi, f in RUSTINES:
    manque = f(a.poser)
    if manque:
        total += 1
        etat = "POSÉE" if a.poser else "MANQUANTE"
        print(f"[{etat}] {nom}")
        print(f"         {pourquoi}")
    else:
        print(f"[ok]     {nom}")

if total == 0:
    print("\nToutes les rustines sont en place.")
elif a.poser:
    print(f"\n{total} rustine(s) réappliquée(s). Relancer un montage de contrôle.")
else:
    print(f"\n{total} rustine(s) manquante(s). Relancer avec --poser.")
    sys.exit(1)
