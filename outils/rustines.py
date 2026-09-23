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
# ─────────────────────────────────────────────────────────────────────────────
@rustine("interpréteur python imposé", "media-use/audio/scripts/lib/python.mjs",
         "Le fichier sonde un `python3` nu dans le PATH et ignore "
         "HYPERFRAMES_PYTHON. Kokoro s'en sort parce qu'il passe par "
         "`npx hyperframes tts`, qui lit la variable lui-même ; ElevenLabs "
         "exécute son extrait python en direct et tombe sur le python du "
         "système, sans le paquet `elevenlabs`. Les six lignes échouent "
         "ensemble, audio.mjs les classe en « non-fatal » et SORT EN 0 : le "
         "montage continue sur un film muet sans qu'un garde-fou bronche.")
def python_impose(poser):
    p = S / "media-use/audio/scripts/lib/python.mjs"
    t = p.read_text()
    # On vise la LIGNE DE CODE, pas le commentaire qui la justifie : le
    # commentaire cite lui aussi HYPERFRAMES_PYTHON, et une détection posée
    # dessus se déclarerait satisfaite par sa propre explication.
    if "const impose = env.HYPERFRAMES_PYTHON;" in t:
        return []
    if not poser:
        return ["python.mjs"]
    av = """export function resolvePythonCommand(platform = process.platform, probe = defaultProbe) {
  const candidates ="""
    ap = """export function resolvePythonCommand(
  platform = process.platform,
  probe = defaultProbe,
  env = process.env,
) {
  // RUSTINE VOKIO - honorer HYPERFRAMES_PYTHON (voir outils/rustines.py).
  const impose = env.HYPERFRAMES_PYTHON;
  if (impose && probe(impose, ["--version"])) return [impose];
  const candidates ="""
    assert t.count(av) == 1, "ancrage de resolvePythonCommand introuvable"
    p.write_text(t.replace(av, ap))
    return ["python.mjs"]


# ─────────────────────────────────────────────────────────────────────────────
@rustine("voix par plan et continuité", "media-use/audio/scripts/audio.mjs",
         "Deux manques dans la même boucle. Le moteur résout UNE voix pour "
         "tout le film, alors qu'une pub a besoin d'une seconde voix sur la "
         "signature finale : il lit maintenant HF_VOICE_BY_LINE. Et il "
         "synthétise chaque ligne ISOLÉMENT, donc l'intonation repart de zéro "
         "à chaque plan et le film s'entend comme six annonces bout à bout ; "
         "on lui donne désormais la ligne d'avant et celle d'après, que "
         "l'API sait utiliser pour enchaîner sans les prononcer.")
def voix_par_plan(poser):
    p = S / "media-use/audio/scripts/audio.mjs"
    t = p.read_text()
    if "const VOIX_PAR_PLAN" in t:
        return []
    if not poser:
        return ["audio.mjs (moteur)"]
    av = """  const synthLine = async (line) => {
    const id = String(line.id);"""
    ap = """  // RUSTINE VOKIO - voix par plan + continuite (voir outils/rustines.py).
  const VOIX_PAR_PLAN = (() => {
    try {
      return JSON.parse(process.env.HF_VOICE_BY_LINE || "{}");
    } catch {
      // Un JSON casse ne doit pas faire tomber le film sur une voix muette :
      // on le signale et on retombe sur la voix unique.
      console.error("· HF_VOICE_BY_LINE illisible, ignore");
      return {};
    }
  })();
  const synthLine = async (line, rang) => {
    const id = String(line.id);
    const voixDuPlan = VOIX_PAR_PLAN[id] || VOIX_PAR_PLAN[String(Number(id))] || voiceId;
    if (voixDuPlan !== voiceId) console.error(`  line ${id}: voix ${voixDuPlan}`);
    // La continuite ne traverse pas un changement de voix : donner a la
    // signature le texte du narrateur precedent lui ferait imiter sa cadence.
    const memeVoix = (l) =>
      (VOIX_PAR_PLAN[String(l.id)] || VOIX_PAR_PLAN[String(Number(l.id))] || voiceId) ===
      voixDuPlan;
    const avant = rang > 0 && memeVoix(lines[rang - 1]) ? String(lines[rang - 1].text ?? "") : "";
    const apres =
      rang < lines.length - 1 && memeVoix(lines[rang + 1])
        ? String(lines[rang + 1].text ?? "")
        : "";"""
    assert t.count(av) == 1, "ancrage de synthLine introuvable"
    t = t.replace(av, ap)
    av2 = """    const { ok, words, error } = await synthesizeOne({
      provider: ttsProvider,
      text,
      voiceId,"""
    ap2 = """    const { ok, words, error } = await synthesizeOne({
      provider: ttsProvider,
      text,
      voiceId: voixDuPlan,
      contexte: { previous_text: avant, next_text: apres },"""
    assert t.count(av2) == 1, "ancrage de synthesizeOne introuvable"
    p.write_text(t.replace(av2, ap2))
    return ["audio.mjs (moteur)"]


# ─────────────────────────────────────────────────────────────────────────────
@rustine("modèle et direction de voix", "media-use/audio/scripts/lib/tts.mjs",
         "L'extrait python écrit `eleven_multilingual_v2` EN DUR et n'envoie "
         "aucun voice_settings. La direction de voix écrite dans SCRIPT.md "
         "(stability, style) ne décorait donc que le document, et le compte "
         "tournait sur une génération de modèle antérieure sans que personne "
         "l'ait choisi. Le modèle et les réglages viennent maintenant de "
         "HF_TTS_MODEL et HF_TTS_SETTINGS, et la ligne reçoit son contexte.")
def modele_et_reglages(poser):
    p = S / "media-use/audio/scripts/lib/tts.mjs"
    t = p.read_text()
    if "HF_TTS_MODEL" in t:
        return []
    if not poser:
        return ["tts.mjs (modèle)"]
    av = 'const ELEVENLABS_PY = `\nimport os, sys\nfrom elevenlabs.client import ElevenLabs\nfrom elevenlabs import save\nclient = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])\ntext = open(sys.argv[1]).read()\naudio = client.text_to_speech.convert(\n    text=text, voice_id=sys.argv[2],\n    model_id="eleven_multilingual_v2", output_format="mp3_44100_128",\n)\nsave(audio, sys.argv[3])\n`;'
    ap = 'const ELEVENLABS_PY = `\nimport os, sys, json\nfrom elevenlabs.client import ElevenLabs\nfrom elevenlabs import save\nclient = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])\ntext = open(sys.argv[1]).read()\ncontexte = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}\nkw = dict(\n    text=text, voice_id=sys.argv[2],\n    model_id=os.environ.get("HF_TTS_MODEL", "eleven_multilingual_v2"),\n    output_format="mp3_44100_128",\n)\nreglages = os.environ.get("HF_TTS_SETTINGS")\nif reglages:\n    kw["voice_settings"] = json.loads(reglages)\nfor cle in ("previous_text", "next_text"):\n    if contexte.get(cle):\n        kw[cle] = contexte[cle]\naudio = client.text_to_speech.convert(**kw)\nsave(audio, sys.argv[3])\n`;'
    assert t.count(av) == 1, "ancrage de ELEVENLABS_PY introuvable"
    t = t.replace(av, ap)
    av2 = '  lang = "en",\n  speed = 1.0,\n  wavAbs,\n  hyperframesDir,\n}) {'
    ap2 = '  lang = "en",\n  speed = 1.0,\n  wavAbs,\n  hyperframesDir,\n  contexte = null,\n}) {'
    assert t.count(av2) == 1, "ancrage de la signature introuvable"
    t = t.replace(av2, ap2)
    av3 = '    const { cmd, args } = pythonInvocation([\n      "-c",\n      ELEVENLABS_PY,\n      writeTmpText(text),\n      voiceId,\n      wavAbs,\n    ]);'
    ap3 = '    const { cmd, args } = pythonInvocation([\n      "-c",\n      ELEVENLABS_PY,\n      writeTmpText(text),\n      voiceId,\n      wavAbs,\n      JSON.stringify(contexte || {}),\n    ]);'
    assert t.count(av3) == 1, "ancrage de l'invocation introuvable"
    p.write_text(t.replace(av3, ap3))
    return ["tts.mjs (modèle)"]


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
