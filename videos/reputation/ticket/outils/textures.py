#!/usr/bin/env python3
"""Textures du ticket de caisse (« Le ticket », 25/11/2026), fabriquées une fois, déterministes (graines fixes).

    python3 /opt/vokio-ads/videos/reputation/ticket/outils/textures.py

assets/textures/papier.png : papier thermique blanc légèrement cassé, fibres très fines, et le TUILAGE : le papier sorti
    d'un rouleau garde une courbure, ses bords latéraux prennent un peu moins de lumière que le milieu.
assets/textures/encre.png  : masque de DENSITÉ de l'impression (luminance = opacité de l'encre). Une tête thermique
    usée laisse des colonnes plus pâles (stries verticales fines, continues sur toute la hauteur, car la tête ne bouge
    pas : c'est le papier qui défile), plus un grain de points. Posé en mask-image sur le texte imprimé.
assets/textures/comptoir.png : le comptoir, uni, sable chaud, grain à peine visible (rien de décoratif).
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

T = Path(__file__).resolve().parent.parent / "assets" / "textures"
T.mkdir(parents=True, exist_ok=True)
W, H = 880, 2400


def papier():
    g = np.random.default_rng(11)
    base = np.array([250, 248, 242], np.float32)
    fib = g.standard_normal((H // 2, W // 2)).astype(np.float32)
    fib = np.array(Image.fromarray(((fib * 18) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
                   .filter(ImageFilter.GaussianBlur(0.8)), np.float32) - 128
    x = np.linspace(-1, 1, W)
    tuilage = 1 - 0.035 * x ** 2 - 0.012 * x        # bords un peu plus sombres, lumière venant légèrement de gauche
    img = base[None, None, :] * tuilage[None, :, None] + fib[..., None] * 0.06
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(T / "papier.png")


def encre():
    g = np.random.default_rng(23)
    # stries : quelques colonnes pâles (éléments de tête fatigués), largeurs de 1 à 3 px, intensités variées
    col = np.ones(W, np.float32)
    for _ in range(14):
        c, l = g.integers(0, W), g.integers(1, 4)
        col[c:c + l] *= g.uniform(0.70, 0.90)
    # une dérive lente de densité sur la largeur (tête pas tout à fait plane) et sur la hauteur (chauffe)
    col *= 1 - 0.07 * np.sin(np.linspace(0, 2.4, W) + 0.5) ** 2
    lig = 1 - 0.05 * (np.sin(np.linspace(0, 9, H)) * 0.5 + 0.5)
    grain = g.uniform(0.86, 1.0, (H, W)).astype(np.float32)
    m = col[None, :] * lig[:, None] * grain
    m = (m / m.max() * 255).clip(0, 255).astype(np.uint8)
    # alpha = densité : le masque CSS (mask-image) lit le canal alpha
    Image.merge("LA", (Image.new("L", (W, H), 0), Image.fromarray(m, "L"))).save(T / "encre.png")


def comptoir():
    g = np.random.default_rng(5)
    w, h = 1080, 1920
    n = g.standard_normal((h // 4, w // 4)).astype(np.float32)
    n = np.array(Image.fromarray(((n * 20) + 128).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
                 .filter(ImageFilter.GaussianBlur(1.2)), np.float32) - 128
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    lum = 1 - 0.05 * x ** 2 - 0.04 * y               # une lumière douce venant du haut, sans vignette marquée
    base = np.array([232, 225, 211], np.float32)
    img = base * lum[..., None] + n[..., None] * 0.05
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(T / "comptoir.png")


if __name__ == "__main__":
    papier(); encre(); comptoir()
    print("ok", sorted(p.name for p in T.iterdir()))
