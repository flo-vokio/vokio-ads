#!/usr/bin/env python3
"""Captures et essais de la maquette d'intégration (maquette/index.html) à 320, 390, 768 et 1440 px : usage en une ligne :

    /root/.pwtest/bin/python3 outils/captures_maquette.py [--largeurs 320,390,768,1440] [--sortie maquette/captures]

  Sert la maquette comme le site (/ → maquette/index.html, /assets/relais/* → /root/vokio-uploads/videos/relais/,
  /assets/* → /opt/vokio-site-repo/assets/), sans serveur. Pour chaque largeur : capture de la section #relais et de la
  carte vidéo, débord horizontal de la page (scrollWidth), débord des enfants de la carte, puis les essais de comportement :
  rien ne se charge avant d'être visible, la boucle part muette à l'écran et s'arrête hors écran, le toucher lance la
  complète avec le son (le lecteur passe en « joue »), un 2e toucher met en pause, prefers-reduced-motion = poster fixe.
  Rapport : <sortie>/rapport.json ; code 1 si un essai échoue.
"""
import argparse
import asyncio
import json
import mimetypes
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ICI = Path(__file__).resolve().parent.parent
MAQ = ICI / "maquette" / "index.html"
RELAIS = Path("/root/vokio-uploads/videos/relais")
SITE = Path("/opt/vokio-site-repo")
ORIGINE = "http://maquette.vokio.local"


async def servir(route):
    url = route.request.url
    if not url.startswith(ORIGINE):
        return await route.abort()
    chemin = url[len(ORIGINE):].split("?")[0].split("#")[0]
    if chemin in ("", "/", "/index.html"):
        f = MAQ
    elif chemin.startswith("/assets/relais/"):
        f = RELAIS / chemin[len("/assets/relais/"):]
    else:
        f = SITE / chemin.lstrip("/")
        if f.is_dir():
            f = f / "index.html"
    if not f.exists():
        return await route.fulfill(status=404, body="")
    corps = f.read_bytes()
    typ = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
    if f.suffix == ".webm":
        typ = "video/webm"
    rng = route.request.headers.get("range")
    if rng and typ.startswith("video"):
        a, _, b = rng.replace("bytes=", "").partition("-")
        a = int(a); b = int(b) if b else len(corps) - 1
        return await route.fulfill(status=206, body=corps[a:b + 1], headers={
            "Content-Type": typ, "Accept-Ranges": "bytes", "Content-Range": f"bytes {a}-{b}/{len(corps)}",
            "Content-Length": str(b - a + 1)})
    await route.fulfill(status=200, body=corps, headers={"Content-Type": typ, "Accept-Ranges": "bytes"})


JS_MESURE = """() => {
  const res = {page_scroll: document.documentElement.scrollWidth, fenetre: innerWidth, cartes: {}, debords_carte: []};
  document.querySelectorAll('.rv').forEach((fig) => {
    const carte = fig.closest('.temps-card'), rc = carte.getBoundingClientRect(), rf = fig.getBoundingClientRect();
    const deb = [...carte.querySelectorAll('*')].filter(e => { const r = e.getBoundingClientRect();
        return r.width && (r.left < rc.left - 0.5 || r.right > rc.right + 0.5); }).map(e => e.className || e.tagName);
    res.cartes[fig.dataset.base.split('/').pop()] = {carte: [Math.round(rc.width), Math.round(rc.height)], video: [Math.round(rf.width), Math.round(rf.height)]};
    res.debords_carte.push(...deb.slice(0, 4));
  });
  return res;
}"""

JS_JOUENT = "() => [...document.querySelectorAll('.rv video')].filter(v => !v.paused).map(v => (v.currentSrc || '').split('/').pop())"


async def essai(b, w, sortie, reduit=False, cible="relais-coiffure"):
    S = f'.rv[data-base$="{cible}"]'
    ctx = await b.new_context(viewport={"width": w, "height": 900},
                              reduced_motion="reduce" if reduit else "no-preference")
    await ctx.route("**/*", servir)
    pg = await ctx.new_page()
    requetes = []
    pg.on("request", lambda r: requetes.append(r.url) if "/assets/relais/" in r.url else None)
    erreurs = []
    pg.on("pageerror", lambda e: erreurs.append(str(e)))
    await pg.goto(ORIGINE + "/", wait_until="networkidle")
    avant = [u for u in requetes if u.endswith((".mp4", ".webm"))]
    R = {"largeur": w, "reduit": reduit, "videos_chargees_avant_scroll": avant, "erreurs_js": erreurs}
    await pg.evaluate("document.querySelectorAll('.reveal').forEach(e => e.classList.add('on'))")
    await pg.locator(S).evaluate("e => e.scrollIntoView({block: 'center'})")
    await pg.wait_for_timeout(1800)
    R["mesure"] = await pg.evaluate(JS_MESURE)
    R["jouent_a_l_ecran"] = await pg.evaluate(JS_JOUENT)
    etat = ("() => { const f = document.querySelector('" + S.replace("'", "\\'") + "'), v = f.querySelector('video'); "
            "return {paused: v.paused, muted: v.muted, loop: v.loop, src: (v.currentSrc || '').split('/').pop(), t: +v.currentTime.toFixed(2), "
            "poster: v.poster.split('/').pop(), lecteur: f.closest('.temps-card').querySelector('.lecteur[data-video]').className}; }")
    R["a_l_ecran"] = await pg.evaluate(etat)
    if not reduit:
        await pg.locator("#relais").screenshot(path=str(sortie / f"relais-{w}.png"))
        for fig in await pg.locator(".rv").all():
            nom = (await fig.get_attribute("data-base")).split("/")[-1].replace("relais-", "")
            await fig.evaluate("e => e.closest('.temps-card').scrollIntoView({block: 'center'})")
            await pg.wait_for_timeout(900)
            await pg.locator(f'.temps-card:has(.rv[data-base$="{nom}"])').screenshot(path=str(sortie / f"carte-{nom}-{w}.png"))
    await pg.evaluate("window.scrollTo(0, 0)")
    await pg.wait_for_timeout(800)
    R["hors_ecran"] = await pg.evaluate(etat)
    await pg.locator(S).evaluate("e => e.scrollIntoView({block: 'center'})")
    await pg.wait_for_timeout(800)
    await pg.locator(S).click()
    await pg.wait_for_timeout(2500)
    R["apres_toucher"] = await pg.evaluate(etat)
    R["jouent_apres_toucher"] = await pg.evaluate(JS_JOUENT)
    if not reduit:
        await pg.locator(f'.temps-card:has({S})').screenshot(path=str(sortie / f"carte-{cible.replace('relais-', '')}-{w}-lecture.png"))
    await pg.locator(f'.temps-card:has({S}) .lecteur[data-video] .lec-btn').click()
    await pg.wait_for_timeout(400)
    R["apres_pause"] = await pg.evaluate(etat)
    # une seule voix : lancer l'appel d'une autre carte coupe celle-ci
    autre = pg.locator('.rv:not([data-base$="' + cible + '"])').first
    await pg.locator(S).click()
    await pg.wait_for_timeout(1200)
    await autre.evaluate("e => e.scrollIntoView({block: 'center'})")
    await autre.click()
    await pg.wait_for_timeout(1500)
    R["deux_appels"] = {"cible": await pg.evaluate(etat), "jouent": await pg.evaluate(JS_JOUENT)}
    await ctx.close()
    return R


def juger(R):
    ech = []
    m = R["mesure"]
    if m["page_scroll"] > m["fenetre"]:
        ech.append(f"débord horizontal de la page : {m['page_scroll']} > {m['fenetre']}")
    if m["debords_carte"]:
        ech.append(f"débords dans la carte : {m['debords_carte']}")
    if R["videos_chargees_avant_scroll"]:
        ech.append(f"vidéo chargée avant d'être visible : {R['videos_chargees_avant_scroll']}")
    if R["erreurs_js"]:
        ech.append(f"erreurs JS : {R['erreurs_js']}")
    e = R["a_l_ecran"]
    if R["reduit"]:
        if not e["paused"] or e["src"]:
            ech.append(f"mouvement réduit : la boucle ne doit pas partir ({e})")
    else:
        # plusieurs cartes entièrement visibles (bureau) : une seule boucle joue, la plus visible (à égalité, la première)
        joue = R["jouent_a_l_ecran"]
        if len(joue) != 1 or "boucle" not in joue[0]:
            ech.append(f"il doit jouer exactement une boucle muette : {joue}")
        elif (e["paused"] and len(R["mesure"]["cartes"]) < 2) or (not e["paused"] and (not e["muted"] or "boucle" not in e["src"])):
            ech.append(f"la boucle ne joue pas muette à l'écran ({e})")
        if not R["hors_ecran"]["paused"]:
            ech.append("la boucle continue hors écran")
    if len(R["jouent_a_l_ecran"]) > 1:
        ech.append(f"plusieurs vidéos jouent à la fois : {R['jouent_a_l_ecran']}")
    if len(R["deux_appels"]["jouent"]) != 1 or not R["deux_appels"]["cible"]["paused"]:
        ech.append(f"deux appels : {R['deux_appels']}")
    t = R["apres_toucher"]
    if t["paused"] or t["muted"] or "complete" not in t["src"] or "joue" not in t["lecteur"]:
        ech.append(f"le toucher ne lance pas la complète avec le son ({t})")
    if not R["apres_pause"]["paused"]:
        ech.append("le bouton du lecteur ne met pas en pause")
    return ech


async def principal(largeurs, sortie):
    sortie.mkdir(parents=True, exist_ok=True)
    rap, ko = [], 0
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        for w in largeurs:
            R = await essai(b, w, sortie)
            R["echecs"] = juger(R); ko += len(R["echecs"]); rap.append(R)
            print(w, "px :", "OK" if not R["echecs"] else R["echecs"], "|", R["mesure"]["cartes"])
        R = await essai(b, 390, sortie, reduit=True)
        R["echecs"] = juger(R); ko += len(R["echecs"]); rap.append(R)
        print("390 px, mouvement réduit :", "OK" if not R["echecs"] else R["echecs"])
        await b.close()
    (sortie / "rapport.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1))
    return ko


if __name__ == "__main__":
    A = argparse.ArgumentParser()
    A.add_argument("--largeurs", default="320,390,768,1440")
    A.add_argument("--sortie", default=str(ICI / "maquette" / "captures"))
    a = A.parse_args()
    sys.exit(1 if asyncio.run(principal([int(x) for x in a.largeurs.split(",")], Path(a.sortie))) else 0)
