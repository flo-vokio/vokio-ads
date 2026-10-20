#!/usr/bin/env python3
"""Filme l'écran « Demandes d'avis » de la VRAIE application (app.vokio.fr), dans l'espace de démo temporaire
« Institut Camélia » créé par /root/vokio-deploy/pub-reputation-201026/espace.py.

    /root/.pwtest/bin/python /opt/vokio-ads/videos/reputation/outils/filmer.py [--page]

Sortie : ../assets/captures/*.png, chaque composant photographié seul à 3× (largeur d'écran 390 → 1170 px).
  saisie-00.png … : le formulaire, champ vide, puis un caractère de plus à chaque image (numéro puis prénom)
  saisie-presse.png : bouton enfoncé ; saisie-note.png : formulaire vidé + « C'est noté… »
  liste-avant.png / liste-apres.png : « Dernières demandes » avant et après la saisie
  entete.png : titre et phrase d'explication
--page : une capture de la page entière (repérage).

SÉCURITÉ : l'envoi du formulaire (POST /api/avis) est intercepté dans le navigateur et reçoit une réponse fabriquée ;
toute autre écriture vers l'API est refusée. Rien n'atteint le serveur, aucun SMS ne peut partir.
L'heure du navigateur est figée au mardi 21/10/2026 10:42 (Paris) : le SMS « partira à 12:42 ».
Numéro tapé : 06 39 98 41 78, tranche réservée par l'ARCEP aux œuvres de fiction (06 39 98 xx xx).
"""
import base64
import hashlib
import hmac
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ICI = Path(__file__).resolve().parent.parent
SORTIE = ICI / "assets" / "captures"
EMAIL = "florian.alauzet+pub-reputation@vokio.fr"
MAINTENANT = "2026-10-21T08:42:00Z"          # 10:42 à Paris
ENVOI = "2026-10-21T10:42:00Z"               # 12:42 à Paris
NUMERO, PRENOM = "06 39 98 41 78", "Claire"
CHROMIUM = "/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").is_file() else None


def psql(sql):
    return subprocess.run(["docker", "exec", "vokio_db", "psql", "-U", "vokio_admin", "-d", "vokio", "-Atc", sql],
                          capture_output=True, text=True, check=True).stdout.strip()


def jeton(mid, uid):
    """JWT HS256 identique à lib/session.ts (même méthode que avis-061026/acces.py), valable 15 min."""
    b64 = lambda o: base64.urlsafe_b64encode(json.dumps(o, separators=(",", ":")).encode()).rstrip(b"=").decode()
    secret = next(l.split("=", 1)[1].strip() for l in open("/opt/vokio-client/.env") if l.startswith("SESSION_SECRET="))
    now = int(time.time())
    corps = b64({"alg": "HS256"}) + "." + b64({"merchantId": mid, "email": EMAIL, "sub": uid, "iat": now, "exp": now + 900})
    sig = base64.urlsafe_b64encode(hmac.new(secret.encode(), corps.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return corps + "." + sig


def main():
    l = psql(f"SELECT m.id || '|' || mu.id FROM merchant_users mu JOIN merchants m ON m.id = mu.merchant_id "
             f"WHERE mu.email = '{EMAIL}' AND m.is_demo")
    if not l:
        sys.exit("espace absent : lancer espace.py --go")
    mid, uid = l.split("|")
    SORTIE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=CHROMIUM, args=["--disable-gpu", "--font-render-hinting=none"])
        ctx = nav.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, locale="fr-FR",
                              timezone_id="Europe/Paris", color_scheme="light", has_touch=True, is_mobile=True)
        ctx.add_cookies([{"name": "vokio_client_session", "value": jeton(mid, uid), "domain": "app.vokio.fr",
                          "path": "/", "secure": True, "httpOnly": True, "sameSite": "Lax"}])
        envois = []

        def api(route):
            r = route.request
            if r.method == "POST" and r.url.rstrip("/").endswith("/api/avis"):
                envois.append(r.post_data)
                route.fulfill(status=200, content_type="application/json", body=json.dumps({"demande": {
                    "id": "film-claire", "prenom": PRENOM, "phone_fin": "78", "send_at": ENVOI,
                    "created_at": MAINTENANT, "statut": "programme"}}))
            elif r.method in ("POST", "PUT", "PATCH", "DELETE"):
                route.abort()
            else:
                route.continue_()
        ctx.route("**/api/**", api)
        pg = ctx.new_page()
        pg.clock.set_fixed_time(MAINTENANT)
        pg.goto("https://app.vokio.fr/avis", wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.add_style_tag(content="*,*::before,*::after{transition:none!important;animation:none!important;caret-color:transparent!important}")
        pg.wait_for_timeout(500)
        if "--page" in sys.argv:
            pg.screenshot(path=str(SORTIE / "page.png"), full_page=True)
            print(SORTIE / "page.png")
            return
        form = pg.locator("main form").first
        liste = pg.locator("main ul.card-v").first
        tel = form.locator("input[type=tel]")
        pre = form.locator("input[type=text]")
        pg.locator("main h1").first.evaluate("e => e.parentElement.id = 'film-entete'")
        pg.locator("#film-entete").screenshot(path=str(SORTIE / "entete.png"))
        liste.screenshot(path=str(SORTIE / "liste-avant.png"))
        tel.blur() if False else pg.evaluate("document.activeElement && document.activeElement.blur()")
        n = 0
        form.screenshot(path=str(SORTIE / f"saisie-{n:02d}.png"))
        for champ, texte in ((tel, NUMERO), (pre, PRENOM)):
            champ.focus()
            for c in texte:
                champ.press_sequentially(c)
                n += 1
                form.screenshot(path=str(SORTIE / f"saisie-{n:02d}.png"))
        pg.evaluate("document.activeElement && document.activeElement.blur()")
        form.screenshot(path=str(SORTIE / "saisie-pleine.png"))
        bouton = form.locator("button[type=submit]")
        bouton.evaluate("b => b.style.filter = 'brightness(.93)'")
        form.screenshot(path=str(SORTIE / "saisie-presse.png"))
        bouton.evaluate("b => b.style.filter = ''")
        bouton.click()
        pg.wait_for_timeout(800)
        pg.evaluate("document.activeElement && document.activeElement.blur()")
        form.screenshot(path=str(SORTIE / "saisie-note.png"))
        liste.screenshot(path=str(SORTIE / "liste-apres.png"))
        print("captures :", n + 6, "· envois interceptés :", envois)
        nav.close()


if __name__ == "__main__":
    main()
