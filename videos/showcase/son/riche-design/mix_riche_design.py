#!/usr/bin/env python3
"""Variante « SOUND DESIGN » de la bande son du showcase « Le point sur le i » (27/09) : la même vidéo, une bande son plus
riche, sans musique au premier plan. Un monde sonore autour de chaque geste du point.

    python3 son/riche-design/mix_riche_design.py            couches + mix + master + MP4 + cues
    python3 son/riche-design/mix_riche_design.py --sans-mp4 sans le muxage (réglages)
    python3 son/riche-design/controle_design.py             les mesures (ebur128 court terme, voix mot par mot, mono,
                                                            silences, synchro, pan) et les planches (spectrogrammes)

NE TOUCHE NI son/mix.wav NI assets/son/mix.wav : tout s'écrit dans son/riche-design/ et dans les deux livrables
    /root/vokio-uploads/videos/showcase/point-solaire-bande-son-design.wav
    /root/vokio-uploads/videos/showcase/le-point-sur-le-i-son-design.mp4     (vidéo copiée telle quelle, -c:v copy)

LA BASE. Les quatre stems du master actuel (son/stems/dialogue, nappe, sfx, signature : voix réelle, verre, tonalité,
touchers « ré courts », vibreur, raccroché, stylo, signature ; à l'échelle du master, leur somme redonne son/mix.wav) sont
gardés tels quels, À UNE EXCEPTION PRÈS : sur « Vokıo » (41,45 → 42,25), la plume de la variante REMPLACE le stylo du
master (seul son du stem sfx sur ce geste ; deux stylos pour un geste, c'était deux matières pour un objet). On y AJOUTE
cinq couches (stems/ de ce dossier), puis un seul gain de master et le limiteur à crête vraie de mix.py.

LES CINQ COUCHES (chaque instant vient de donnees/*.json ; chaque pan du point vient de point-resolu.json, 0,6·(x − 540)/540)
  1. ambiance  la pièce, fin d'après-midi : un fond d'air très bas (deux prises ElevenLabs de pièce calme, filtrées au-dessus
               de 120 Hz, décorrélées) et UN oiseau lointain par la fenêtre, à gauche, dans le blanc entre les deux
               tonalités. Pendant l'appel, le fond reste FIXE à −8 dB (pas de fond qui respire avec la voix) et aucun
               oiseau. Coupé net au raccroché avec tout le reste (le silence reste numérique), il se rouvre quand le
               vibreur se TAIT (fin de la 2e secousse, 37,117), à −44 LUFS court terme sur la lecture du SMS, puis
               s'efface sous la signature.
  2. point     la naissance (goutte d'encre, 0,83 s), l'éveil (le point devient solaire et gonfle, 4,23 → 4,60 : un souffle
               qui suit la croissance du diamètre, au-dessus de la ligne), l'AIR des trajets (bruit filtré dont le niveau
               et la brillance suivent la vitesse lue image par image, spatialisé à chaque échantillon sur x ; pendant
               l'appel, seulement les grands gestes et au-dessus de la ligne), l'ENVOL de chaque saut sur les heures
               (9 h · 10 h · 11 h · retour 9 h : un décollement de papier de 20 ms, 4,5-9 kHz ; le contact, lui, est le
               toucher du master), l'assise sur le ı (la goutte de la naissance, une image après le contact).
  3. ecriture  la plume sur le papier : le rendez-vous (25,40 → 26,10) et « Vokıo » (41,50 → 42,20). Le grain d'une prise
               ElevenLabs de plume, aplati (son rythme propre retiré), piloté par ce qu'on voit (vitesse du point × encre
               révélée au bord, lue dans la vidéo) ; la pose de la plume en goutte.
  4. objets    les transitions de scène : l'agenda qui monte (18,37, papier), le tamis des « euh » (13,95), l'agenda qui sort
               (31,00), le téléphone qui sort (41,00 ; il entre sous « Au revoir » : muet), le vibreur SUR BOIS (prise
               ElevenLabs ramenée sur le ré3 du vibreur de synthèse, enveloppe = secousses.s6, en phase avec le moteur).
               La bulle n'a AUCUN son propre : l'arrivée du SMS, c'est le vibreur.
  5. halo      la nappe harmonique qui s'élargit jusqu'à la signature : (a) la nappe de verre du master reçoit une composante
               latérale décorrélée dont la largeur monte de 0 (4,6 s) à 0,45 (le la, le ré), refermée à 0,30 dans le
               fondu final ; par bin, sa part en opposition avec le côté propre de la nappe est retirée (elle ne creuse
               jamais un canal) ; en mono elle disparaît sans rien retirer ; (b) un souffle accordé : du bruit filtré sur
               les octaves des notes de la nappe (mêmes accords, mêmes instants que mix.nappe, coupé au raccroché), de
               plus en plus de registres et des résonances plus larges ; dès la bulle, passe-bas 4 kHz et PLAFONNÉ par
               tiers d'octave 8 dB sous nappe + signature ; dès le la, creusé autour du ré6 et du scintillement de la
               signature : une ombre de la nappe, jamais sur la marque.

LA VOIX (le vrai appel) reste TOUJOURS devant : présence de la voix par le détecteur de mix.gain_ducking (fond, air et souffle
à −8 dB sous toute voix), puis rattrapage mot par mot : chaque mot garde au moins 10 dB d'avance dans la bande de la voix et
10 LU en sonie K sur tout le reste, et ne perd pas plus de 1 dB (bande de la voix) ni 2 LU (sonie K) sur le master (au-delà
de 16, la marge peut descendre jusqu'à 16 ; un mot que le master laisse lui-même sous 10,2 ne perd pas plus de 0,2).
LES DEUX MOMENTS FORTS : le silence du raccroché reste de zéros numériques sur toutes les couches, et la signature reste
l'instant le plus fort (sonie instantanée) ; l'ambiance s'efface pour elle, le halo reste sous elle.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
SON = ICI.parent
PROJET = SON.parent
sys.dont_write_bytecode = True        # les .pyc de son/__pycache__ sont suivis par git : ne pas les réécrire
sys.path.insert(0, str(SON))
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402
import mix as MX  # noqa: E402  (données et outils : rien ne se recalcule à l'import)
import bruitages as B  # noqa: E402

SR = labo.SR
N = MX.N
EV, T, DUREE, FIN_SON = MX.EV, MX.T, MX.DUREE, MX.FIN_SON
UPLOADS = Path("/root/vokio-uploads/videos/showcase")
VIDEO = UPLOADS / "le-point-sur-le-i.mp4"
SORTIE_MP4 = UPLOADS / "le-point-sur-le-i-son-design.mp4"
SORTIE_WAV = UPLOADS / "point-solaire-bande-son-design.wav"
STEMS_OUT = ICI / "stems"
CU = json.loads((SON / "cues.json").read_text())
G_MASTER = CU["gain_master_db"]                   # 7,84 dB : les stems d'entrée sont déjà à l'échelle du master
BASE = ("dialogue", "nappe", "sfx", "signature")
COUCHES = ("ambiance", "point", "ecriture", "objets", "halo")
STYLO_RETIRE = (41.45, 42.25)          # le stylo du master (cues.json « stylo », 41,50 → 42,20) : la plume le remplace
TT = np.arange(N) / SR
CUES = []

# ── niveaux : sonie instantanée maximale (400 ms, pondération K) de CHAQUE élément seul, dans le mix final ──────────
# repères du master : médiane court terme du dialogue −14,1 LUFS ; tonalité −17 ; nappe −27 à −33 ; air du SMS −30 ;
# stylo −39 ; vibreur −19 ; signature −9,2 au ré (l'instant le plus fort).
NIV = {
    "ambiance_court_terme": -50.0,     # fond seul, court terme (3 s) hors voix : on l'entend dans les blancs, jamais dessus
    "ambiance_sms": -44.0,             # fond seul, court terme sur la lecture du SMS (38 → 41) : 14 LU sous l'air du SMS
    "oiseau": -52.0,                   # UN oiseau lointain (instantanée max) : fond + oiseau ≥ 3 dB sous le master du blanc (revue :
                                       # à −40 il était le son le plus fort du blanc, +6,4 dB sur le master)
    "naissance": -29.0,                # la goutte d'encre, sous la tonalité n° 1 (−17) mais dans une autre bande
    "eveil": -37.0,                    # souffle de croissance 4,23 → 4,60, AU-DESSUS de la ligne (5 → 9 kHz)
    "air_max": -29.0,                  # l'air du trajet le plus rapide (le saut vers le ı, 127,8 px/image)
    "envol": -40.0, "envol_retour": -40.0,   # l'envol de chaque saut sur les heures : un décollement de papier 4,5-9 kHz
    "assise": -36.0,                   # la goutte sur le ı, une image après le contact, 27 LU sous le ré (−9,2)
    "plume": -27.0,                    # la plume, dans les deux blancs de la voix
    "pose_plume": -34.0,
    "papier_monte": -31.0, "papier_sort": -34.0, "tamis": -42.0,
    "tel_sort": -38.0,                 # le téléphone qui sort (glisse_telephone) ; il ENTRE sous « Au revoir » : muet
    "vibreur_bois": -23.0,             # niveau de départ de la prise seule (avant mise en phase)
    "vibreur_bois_somme_db": 2.0,      # moteur + bois = moteur + 2 dB (énergie) : plus de corps, pas plus fort
    "souffle_ref": -53.0,              # souffle accordé, court terme sur l'accord de sol (12,5 → 17,5), avant atténuation
}
DUCK_DB = -8.0                         # fond, air, souffle : sous toute voix (mix.gain_ducking : 30 / 250 ms, 80 ms d'avance)
PAN_FENETRE = -0.45                    # la fenêtre de la pièce est à gauche (l'oiseau)
LIGNE = (300.0, 4000.0)                # la bande de la ligne téléphonique (là où l'oreille range un son « dans l'appel »)
AU_DESSUS_LIGNE = 4500.0               # pendant l'appel, l'air et le souffle du point vivent au-dessus (la voix y est à −44 dB)
AIR_HAUT_DB = -3.0                     # à sonie K égale, un souffle tout en aigu s'entend plus qu'il ne pèse : −3 dB
V_GESTE_APPEL = 60.0                   # pendant l'appel, seuls les grands gestes du point (v_max ≥ 60 px/image) ont de l'air
HALO_DB = {"la": 4.0, "re": 8.0}    # souffle accordé : niveau relatif au la et au ré (2e revue 27/09 : à +7 / +16, il couvrait
                                    # la signature, au-dessus du scintillement et du ré6 dès 0,6 s après le ré)
PARTIELS_SIGNATURE = (1174.66, 2349.3)   # le ré6 et le scintillement de signature.py (COUCHES_RE.scint_hz) : dès le la, le
                                         # souffle se creuse autour (σ 50 cents) ; il ne se pose jamais sur la marque
SOUFFLE_PASSE_BAS = (4000.0, 2)          # dès la bulle, le souffle reste sous 4 kHz comme l'air du SMS du master (Butterworth)
BANDE_VOIX = (100.0, 3800.0)           # la bande réelle de la voix (VoIP : passe-haut 100 Hz, 61 % de l'énergie sous 300 Hz)


def cue(id_, couche, t, source, fabrication, niveau, pan=None, **extra):
    d = {"id": id_, "couche": couche, "t": round(float(t), 6), "echantillon": int(round(t * SR)), "image": int(round(t * 30)),
         "source_instant": source, "fabrication": fabrication, "niveau": niveau}
    if pan is not None:
        d["pan"] = pan
    d.update(extra)
    CUES.append(d)


# ── outils ─────────────────────────────────────────────────────────────────
def lissage(x, attaque, relache, pas=0.001):
    """Suiveur d'enveloppe à un pôle (attaque / relâche en s) sur une grille de 1 ms, rééchantillonné."""
    n = len(x)
    k = int(pas * SR)
    g = x[::k]
    ka, kr = 1 - np.exp(-pas / attaque), 1 - np.exp(-pas / relache)
    y = np.empty_like(g); v = 0.0
    for i in range(len(g)):
        v += (g[i] - v) * (ka if g[i] > v else kr)
        y[i] = v
    return np.interp(np.arange(n), np.arange(len(g)) * k, y)


def bruit_module(n, fc, largeur_oct, graine, nf=1024, pas=256):
    """Bruit blanc filtré par une cloche gaussienne en log-fréquence, centrée sur fc(t) (Hz, tableau de n valeurs),
    largeur à mi-hauteur largeur_oct (octaves, scalaire ou tableau) ; STFT Hann, énergie par trame normalisée (le niveau
    ne dépend pas de fc : il est donné ensuite par l'enveloppe)."""
    g = np.random.default_rng(graine)
    xp = g.standard_normal(n + 2 * nf)
    win = np.hanning(nf + 1)[:-1]
    nb = (len(xp) - nf) // pas + 1
    idx = np.arange(nb) * pas
    fr = np.lib.stride_tricks.sliding_window_view(xp, nf)[::pas][:nb] * win
    X = np.fft.rfft(fr, axis=1)
    f = np.fft.rfftfreq(nf, 1 / SR); f[0] = 1.0
    c = np.clip(idx + nf // 2 - nf, 0, n - 1)
    fcs = np.asarray(fc)[c]
    lo = np.broadcast_to(np.asarray(largeur_oct, dtype=float), (n,))[c] if np.ndim(largeur_oct) else np.full(nb, float(largeur_oct))
    sig = lo / 2.355
    m = np.exp(-0.5 * (np.log2(f[None, :] / fcs[:, None]) / sig[:, None]) ** 2)
    m /= np.sqrt(np.mean(m ** 2, axis=1, keepdims=True)) + 1e-12
    y = np.fft.irfft(X * m, nf, axis=1) * win
    out = np.zeros(len(xp))
    for j in range(nb):
        out[j * pas:j * pas + nf] += y[j]
    out = out[nf:nf + n] / 1.5 * np.sqrt(pas / nf * 4)
    return out / (np.sqrt(np.mean(out ** 2)) + 1e-12)


def momentanee_max(st):
    """Sonie instantanée maximale (LUFS) d'un signal (n,2) seul, bordé de 0,3 s de zéros."""
    st = np.asarray(st, dtype=np.float64)
    if st.ndim == 1:
        st = np.stack([st, st], axis=1)
    z = np.zeros((int(0.3 * SR), 2))
    return MX.sonie_instantanee_max(np.vstack([z, st, z]))


def au_niveau(st, cible):
    return st * S.gain(cible - momentanee_max(st))


def court_terme(st, a, b):
    """Sonie (LUFS) d'un segment, pondération K, non fenêtrée (comme la sonie court terme sur [a ; b])."""
    xk = MX.ponderer_k(st[int(a * SR):int(b * SR)])
    return float(-0.691 + 10 * np.log10(np.sum(np.mean(xk ** 2, axis=0)) + 1e-20))


def fondus(x, a=0.005, r=0.030):
    x = np.array(x, dtype=np.float64)
    ka, kr = int(a * SR), int(r * SR)
    sl = (slice(None),) if x.ndim == 1 else (slice(None), None)
    if ka:
        x[:ka] *= S.rampe_cos(ka)[sl]
    if kr:
        x[-kr:] *= S.rampe_cos(kr)[::-1][sl]
    return x


def poser(piste, st, t0):
    S.ajouter(piste, st, int(round(t0 * SR)))
    return piste


def mobile(mono, t0, pan_fn=MX.pan_point):
    """Son mono attaché au point : pan(t) = 0,6·(x(t) − 540)/540 à chaque échantillon."""
    i0 = int(round(t0 * SR))
    return S.panner(mono, pan_fn((i0 + np.arange(len(mono))) / SR))


def passe_haut(x, f):
    return S.ffmpeg_filtre(x, f"highpass=f={f},highpass=f={f}")


def passe_bas(x, f):
    return S.ffmpeg_filtre(x, f"lowpass=f={f},lowpass=f={f}")


def decorrele(x, graine, n_fir=2048):
    """Copie décorrélée (même spectre, phase aléatoire par bande : FIR passe-tout de 43 ms)."""
    g = np.random.default_rng(graine)
    ph = g.uniform(0, 2 * np.pi, n_fir // 2 + 1); ph[0] = 0; ph[-1] = 0
    h = np.fft.irfft(np.exp(1j * ph), n_fir)
    L = len(x) + n_fir - 1; M = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, M) * np.fft.rfft(h, M), M)[:len(x)]
    return y * np.sqrt(np.mean(x ** 2) / (np.mean(y ** 2) + 1e-20))


def cote_sans_perte(c, nap, nf=4096, pas=1024):
    """L'élargissement [c, −c] ne fait jamais baisser la nappe (contrôle X, 2e revue 27/09). Sur des notes tenues, la copie
    « décorrélée » par un passe-tout n'est qu'une rotation de phase de chaque partiel : là où elle tombe en opposition avec
    le côté propre de la nappe (G − D, sa réverbe), (G + c)² + (D − c)² < G² + D² et la variante sonnait jusqu'à 0,36 LU
    sous le master (lecture du SMS). Par trame STFT et par bin, on retire de c sa composante en opposition avec G − D
    (projection) : le terme croisé n'est jamais négatif, l'image s'ouvre sans rien creuser ; en mono, c s'annule toujours."""
    n = len(c)
    win = np.hanning(nf + 1)[:-1]

    def stft(x):
        xp = np.concatenate([np.zeros(nf), x, np.zeros(2 * nf)])
        nb = (len(xp) - nf) // pas + 1
        return np.fft.rfft(np.lib.stride_tricks.sliding_window_view(xp, nf)[::pas][:nb] * win, axis=1)
    C, Dd = stft(c), stft(nap[:, 0] - nap[:, 1])
    pr = np.real(C * np.conj(Dd))
    C = C - (np.minimum(pr, 0.0) / (np.abs(Dd) ** 2 + 1e-20)) * Dd
    y = np.fft.irfft(C, nf, axis=1) * win
    o = np.zeros((len(y) - 1) * pas + nf)
    for j in range(len(y)):
        o[j * pas:j * pas + nf] += y[j]
    return o[nf:nf + n] / 1.5


def largeur(mono, w, graine):
    """(n,2) = milieu ± w·côté décorrélé. En mono ((G + D)/2) il ne reste que le milieu : rien ne s'annule."""
    s = decorrele(mono, graine)
    return np.stack([mono + w * s, mono - w * s], axis=1)


def transitoire(x, avant=0.003, apres=0.180, graine_choix=None):
    """Le transitoire le plus net d'une prise : pic de l'enveloppe 2 ms, découpé de −avant à +apres, fondus."""
    m = x.mean(axis=1) if x.ndim > 1 else x
    w = int(0.002 * SR)
    e = np.convolve(m ** 2, np.ones(w) / w, mode="same")
    i = int(np.argmax(e))
    a, b = max(0, i - int(avant * SR)), min(len(m), i + int(apres * SR))
    return fondus(m[a:b], 0.001, 0.060), i / SR


def env_vitesse(t, puissance, v0=0.0, vref=None):
    v = MX.v_point(t)
    vref = vref or float(v.max())
    return np.clip((v - v0) / (vref - v0), 0, 1) ** puissance


# ── choix des prises (par la mesure : prises.json, bruitages.mesurer_prise) ─────────────────────────────────────
def prises(nom):
    return B.prises(nom)


def choisir(nom, cle, raison):
    lst = prises(nom)
    k, chemin, m = sorted(lst, key=lambda e: cle(e[2]))[0]
    CHOIX[nom] = {"retenue": k, "raison": raison, "mesures": {str(kk): mm for kk, _, mm in lst}}
    return labo.lire(chemin), k


CHOIX = {}


def voix_presente(dlg):
    """Gain de ducking (linéaire) : le détecteur de mix.py, seuil ramené à l'échelle du master."""
    return MX.gain_ducking(dlg[:, 0], seuil=-40.0 + G_MASTER, profondeur=DUCK_DB)


def coupe_film():
    """1 avant le raccroché, 5 ms de fondu cosinus (la même coupe que mix.py), zéros jusqu'à la fin du silence
    numérique ; 1 ensuite ; zéros dès FIN_SON."""
    c = np.ones(N)
    i_rac = int(round(T["raccroche"] * SR)); k = int(0.005 * SR)
    i_s1 = int(round(EV["silence_numerique"]["t"][1] * SR))
    c[i_rac:i_rac + k] = S.rampe_cos(k)[::-1]
    c[i_rac + k:i_s1] = 0
    c[int(round(FIN_SON * SR)):] = 0
    return c


def presence_voix(duck):
    """0 → 1 : la présence de la voix lue sur le gain de ducking (1 sans voix, −8 dB sous la voix)."""
    return np.clip((1 - duck) / (1 - S.gain(DUCK_DB)), 0, 1)


def hors_ligne_sous_voix(st, pv):
    """Règle de la variante (revue 27/09) : ce qu'on ajoute et qui sonne EN MÊME TEMPS que la voix réelle vit au-dessus de
    la ligne (> 4,5 kHz) ; dans les blancs, le son garde toute sa bande. Fondu par la présence de la voix."""
    if not np.any(pv > 1e-3):
        return st
    haut = passe_haut(st, AU_DESSUS_LIGNE)
    return (1 - pv)[:, None] * st + pv[:, None] * haut


def appel(rampe=0.060):
    """1 pendant l'appel (du décroché au raccroché), rampes cosinus de 60 ms ; 0 ailleurs (sonnerie, SMS, signature)."""
    return MX.fondu_cos(TT, T["decroche"], rampe) * (1 - MX.fondu_cos(TT, T["raccroche"], rampe))


# ── 1. AMBIANCE ─────────────────────────────────────────────────────────────
def sans_ronflement(x, f0=50.0, fmax=4000.0, sigma=0.8):
    """Retire les harmoniques du secteur (k·50 Hz jusqu'à fmax) : creux gaussiens de σ = 0,8 Hz sur la FFT de la prise
    entière (les raies sont stables, le bruit de pièce autour n'est pas touché)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones(len(f))
    for h in np.arange(f0, fmax + 1, f0):
        sel = np.abs(f - h) < 6 * sigma
        g[sel] *= 1 - np.exp(-0.5 * ((f[sel] - h) / sigma) ** 2)
    return np.fft.irfft(X * g, len(x))


def ambiance(duck):
    # le fond : les prises « pièce calme » (ambiance et oiseaux, 22 s chacune), filtrées au-dessus de 120 Hz (le
    # grondement sous 150 Hz y fait 95 % de l'énergie, c'est le micro, pas la pièce), classées par stationnarité
    cand = []
    for nom in ("ambiance", "oiseaux"):
        for k, chemin, m in prises(nom):
            x = passe_haut(labo.lire(chemin).mean(axis=1), 120)
            w = int(0.1 * SR)
            e = 10 * np.log10(np.convolve(x ** 2, np.ones(w) / w, mode="valid")[::w] + 1e-20)
            cand.append({"prise": f"{nom}-{k}", "chemin": chemin, "ecart_type_db": round(float(np.std(e)), 2),
                         "pic_sur_mediane_db": round(float(e.max() - np.median(e)), 1)})
    cand.sort(key=lambda d: (d["pic_sur_mediane_db"] > 8, d["ecart_type_db"]))
    A, Bb = cand[0], cand[1]
    CHOIX["ambiance_fond"] = {"retenues": [A["prise"], Bb["prise"]], "candidats": cand,
                              "raison": "les deux fonds les plus stationnaires (écart-type du niveau 100 ms), sans pic > 8 dB"}
    # les deux prises portent un ronflement secteur (raies EXACTES à 200, 400, 600, 1 000, 1 400 Hz…, jusqu'à 39 dB
    # au-dessus du bruit voisin, mesuré) : un bruit électrique, de ligne, pas une pièce ; il est retiré (creux de 0,8 Hz)
    a = sans_ronflement(passe_bas(passe_haut(labo.lire(A["chemin"]).mean(axis=1), 120), 9000))
    b = sans_ronflement(passe_bas(passe_haut(labo.lire(Bb["chemin"]).mean(axis=1), 120), 9000))
    a /= np.sqrt(np.mean(a ** 2)); b /= np.sqrt(np.mean(b ** 2))
    x = int(1.0 * SR)                                         # A, B, A…, fondus enchaînés à puissance constante de 1 s
    r = np.sin(np.pi / 2 * np.linspace(0, 1, x))

    def chaine(p, q):
        out, k = p.copy(), 1
        while len(out) < N:
            nxt = (q, p)[k % 2] if k > 1 else q
            nxt = nxt if k < 2 else np.roll(nxt, int(7.3 * SR))          # la reprise ne recommence pas au même endroit
            out = np.concatenate([out[:-x], out[-x:] * r[::-1] + nxt[:x] * r, nxt[x:]])
            k += 1
        return out[:N]
    mil = chaine(a, b)
    cot = chaine(b, a)                                        # B puis A : décorrélé du milieu
    fond = np.stack([mil + 0.6 * cot, mil - 0.6 * cot], axis=1)
    # courbe : entrée 0,4 s ; coupe au raccroché (coupe_film) ; la pièce se rouvre quand le téléphone se TAIT (fin de la
    # 2e secousse du vibreur, 37,117 : 2e revue 27/09, posée sur son début elle restait 35 LU sous le vibreur), en 0,6 s ;
    # s'efface sous la signature (du la au ré + 0,6 s)
    t_retour = MX.SEC["s6"]["segments_s"][-1][1]
    g = MX.fondu_cos(TT, 0.0, 0.4)
    g *= np.where(TT >= EV["bulle_et_vibreur"]["t"], MX.fondu_cos(TT, t_retour, 0.6), 1.0)
    g *= 1 - MX.fondu_cos(TT, T["la"], T["re"] + 0.6 - T["la"])
    # PENDANT L'APPEL, un niveau fixe (−8 dB, celui de sous la voix), pas un fond qui respire avec la voix : un bruit de
    # fond qui remonte dans chaque blanc de la parole et redescend dessous, c'est le « bruit de confort » d'une ligne VoIP,
    # il s'entendrait DANS l'appel. La pièce recule au décroché (0,5 s) et revient avec le vibreur.
    p_amb = MX.fondu_cos(TT, T["decroche"], 0.5) * (TT < T["raccroche"] + 0.5)
    fond *= (g * (1 - p_amb * (1 - S.gain(DUCK_DB))))[:, None]
    # niveau : court terme sur le blanc entre les deux tonalités (1,5 → 2,7 s), sans voix ; après le silence, court terme
    # sur la lecture du SMS (38 → 41 s), 14 LU sous l'air du SMS (2e revue 27/09 : à −50 elle y était 20 LU sous le master,
    # inaudible) ; la bascule tombe dans le silence numérique, où le fond est nul
    a0, a1 = SEC_S1[0][1], SEC_S1[1][0]
    avant = TT < EV["silence_numerique"]["t"][1]
    fond[avant] *= S.gain(NIV["ambiance_court_terme"] - court_terme(fond * avant[:, None], a0 + 0.1, a1 - 0.1))
    fond[~avant] *= S.gain(NIV["ambiance_sms"] - court_terme(fond * (~avant)[:, None], 38.0, 41.0))
    cue("fond-piece", "ambiance", 0.0, "0 → raccroché ; fin de la 2e secousse du vibreur (secousses.s6) → signature_re_contact + 0,6",
        f"{A['prise']} puis {Bb['prise']} (fondu 1 s), passe-haut 120 Hz, passe-bas 9 kHz, milieu ± 0,6 × côté décorrélé ; "
        f"−8 dB FIXES pendant tout l'appel (pas de fond qui respire avec la voix) ; la pièce se rouvre quand le vibreur se tait "
        f"({t_retour:.3f} s, fondu 0,6 s)", f"{NIV['ambiance_court_terme']} LUFS court terme dans le blanc des tonalités, "
        f"{NIV['ambiance_sms']} sur la lecture du SMS", pan="large, centré")
    # l'oiseau lointain : la prise au fond le plus bas, découpée en deux gestes (bouffées), à gauche, avec la distance
    ois, k = choisir("oiseau_loin", lambda m: (m["bouffees"] < 2, m["fond_db_sous_crete"]),
                     "au moins deux bouffées, le fond le plus bas")
    m = ois.mean(axis=1)
    m = passe_bas(passe_haut(m, 1200), 7000)
    w = int(0.01 * SR)
    e = 10 * np.log10(np.convolve(m ** 2, np.ones(w) / w, mode="same") + 1e-20)
    haut = e > e.max() - 18
    gestes, i = [], 0
    while i < len(haut):                                      # gestes = bouffées séparées de plus de 0,25 s
        if haut[i]:
            j = i
            while j < len(haut) and (haut[j] or np.any(haut[j:j + int(0.25 * SR)])):
                j += int(0.01 * SR)
            gestes.append((max(0, i - int(0.05 * SR)), min(len(m), j + int(0.10 * SR))))
            i = j
        else:
            i += int(0.005 * SR)
    oiseau = np.zeros((N, 2))
    # UN seul passage (revue 27/09) : le second, pendant la lecture du SMS, était le seul événement de ce blanc (il
    # attirait l'oreille là où le film demande de lire) et répétait la même prise au même pan ; après le silence, le
    # retour du fond de pièce suffit à rouvrir la pièce
    places = [(SEC_S1[0][1] + 0.18, "blanc entre les deux tonalités (secousses.s1 : 1,50 → 2,70)")]
    for (a, b), (t0, raison) in zip(gestes[:1], places):
        seg = fondus(m[a:b], 0.02, 0.08)
        st = labo.reverbe(S.panner(seg, PAN_FENETRE), 0.9, 0.30, graine=121)
        st = au_niveau(st, NIV["oiseau"])
        if t0 < SEC_S1[1][0]:
            assert t0 + (b - a) / SR < SEC_S1[1][0] + 0.25, "l'oiseau déborderait sur la 2e tonalité"
        poser(oiseau, st, t0)
        cue(f"oiseau-{len([c for c in CUES if c['id'].startswith('oiseau')]) + 1}", "ambiance", t0, raison,
            f"oiseau_loin prise {k}, geste {a / SR:.2f} → {b / SR:.2f} s, 1,2-7 kHz, réverbe 0,9 s à 30 %",
            f"{NIV['oiseau']} LUFS instantanés", pan=PAN_FENETRE)
    return fond + oiseau


# ── 2. LE POINT ─────────────────────────────────────────────────────────────
def point(duck):
    piste = np.zeros((N, 2))
    # 2.1 naissance : la goutte d'encre, le transitoire le plus net des prises « encre »
    cand = []
    for k, chemin, m in prises("encre"):
        x = labo.lire(chemin)
        tr, ti = transitoire(x, 0.003, 0.160)
        mm = x.mean(axis=1)
        w = int(0.002 * SR)
        e = 10 * np.log10(np.convolve(mm ** 2, np.ones(w) / w, mode="same") + 1e-20)
        X = np.abs(np.fft.rfft(tr * np.hanning(len(tr)))) ** 2; f = np.fft.rfftfreq(len(tr), 1 / SR)
        cand.append({"prise": k, "instant_s": round(ti, 3), "crete_sur_mediane_db": round(float(e.max() - np.median(e)), 1),
                     "centroide_hz": round(float((X * f).sum() / X.sum()), 0), "tr": tr})
    ok = [c for c in cand if 800 <= c["centroide_hz"] <= 7000] or cand
    best = max(ok, key=lambda c: c["crete_sur_mediane_db"])
    CHOIX["encre"] = {"retenue": best["prise"], "raison": "transitoire le plus net (crête − médiane, 2 ms), centroïde 0,8-7 kHz",
                      "candidats": [{k: v for k, v in c.items() if k != "tr"} for c in cand]}
    goutte = passe_haut(best["tr"], 250)
    goutte /= np.max(np.abs(goutte))
    GOUTTE[0] = goutte
    t_n = EV["point_pose"]["t"][0]
    n_bl = int(0.045 * SR); tb = np.arange(n_bl) / SR          # le corps de la goutte : 190 → 150 Hz, demi-sinus 45 ms
    blot = np.sin(2 * np.pi * (190 * tb - 440 * tb ** 2)) * np.sin(np.pi * tb / 0.045)
    d_etal = EV["point_pose"]["t"][1] - t_n                   # l'encre s'étale jusqu'à 15,75 px (4 images) : 3-7 kHz
    n_et = int((d_etal + 0.08) * SR); te = np.arange(n_et) / SR
    etal = S.passe_bande(np.random.default_rng(131).standard_normal(n_et), 3000, 7000, front=500) * np.exp(-te / 0.05)
    etal /= np.max(np.abs(etal))
    mono = np.zeros(max(len(goutte), n_et, n_bl)); mono[:len(goutte)] += goutte
    mono[:n_bl] += 0.35 * blot; mono[:n_et] += 0.18 * etal
    st = labo.reverbe(mobile(fondus(mono, 0.0005, 0.05), t_n), 0.6, 0.10, graine=132)
    poser(piste, au_niveau(st, NIV["naissance"]), t_n)
    cue("naissance", "point", t_n, "evenements.point_pose[0] (le point passe de 0 à 15,75 px en 4 images)",
        f"encre prise {best['prise']} (transitoire à {best['instant_s']} s), passe-haut 250 Hz + corps 190 → 150 Hz 45 ms + "
        "étalement 3-7 kHz τ 50 ms ; réverbe 0,6 s à 10 %", f"{NIV['naissance']} LUFS instantanés",
        pan=round(float(MX.pan_point(t_n)), 3))
    # 2.2 éveil : le point devient solaire (lumière 4,233) et gonfle jusqu'à 44 px (4,60) : souffle ∝ croissance
    t0, t1 = EV["lumiere"]["t"], T["pedale"]
    pr = MX.PR
    tp = np.array([p["t"] for p in pr]); dp = np.array([p["d"] for p in pr])
    i0 = int(round((t0 - 0.02) * SR)); n = int(round((t1 - t0 + 0.35) * SR))
    t = (i0 + np.arange(n)) / SR
    d = np.interp(t, tp, dp)
    croiss = np.clip(np.gradient(d) * SR, 0, None)
    croiss = lissage(croiss / croiss.max(), 0.02, 0.12)
    # l'éveil tombe juste après le décroché, avant « Bonjour » : un souffle dans la bande de la ligne s'y entendrait
    # comme quelqu'un qui respire dans le combiné (revue 27/09) ; il vit donc au-dessus de la ligne, 5 → 9 kHz
    fc = 5000 + 4000 * np.clip((d - 12.76) / (44 - 12.76), 0, 1)
    br = passe_haut(bruit_module(n, fc, 1.1, graine=141), AU_DESSUS_LIGNE) * croiss
    st = mobile(fondus(br, 0.005, 0.08), i0 / SR)
    poser(piste, au_niveau(st, NIV["eveil"]), i0 / SR)
    cue("eveil", "point", t0, "evenements.lumiere → point.json taille (44 px à 4,60)", "bruit filtré (cloche 1,1 oct.) dont le "
        "centre suit le diamètre (5 → 9 kHz), passe-haut 4,5 kHz (au-dessus de la ligne : on vient de décrocher), niveau ∝ "
        "vitesse de croissance du diamètre", f"{NIV['eveil']} LUFS instantanés", pan=round(float(MX.pan_point(t0)), 3))
    # 2.3 l'air des trajets : vitesse lue image par image (point-resolu.json, v en px/image, sans secousse)
    v = MX.v_point(TT)
    vmax = float(v.max())
    a = np.clip((v - 4.0) / (vmax - 4.0), 0, 1) ** 1.3
    for nom in ("ecriture", "plume_mot"):                     # la plume remplace l'air quand le point écrit
        p0, p1 = ((EV["plume_pose"]["t"], EV["ecriture_fin"]["t"]) if nom == "ecriture" else EV["plume_mot"]["t"])
        m = (TT >= p0 - 0.02) & (TT <= p1 + 0.02)
        a[m] = 0
    # PENDANT L'APPEL (revue 27/09) : un air dans la bande de la ligne (300-4 000 Hz) s'y range avec la voix réelle, comme
    # un souffle ou un bruit de ligne. (a) seuls les grands gestes (v_max ≥ 60 px/image) gardent leur air ; (b) cet air
    # passe au-dessus de la ligne (cloche centrée à max(2,5·fc, 5 kHz), passe-haut 4,5 kHz), où la voix est à −44 dB.
    # Hors de l'appel (sonnerie, SMS, saut vers le ı), la loi de départ reste.
    p_ap = appel()
    lent = np.zeros(N)
    gestes = []
    for tr0, tr1 in SEGMENTS_V:
        m = (TT >= tr0 - 0.05) & (TT <= tr1 + 0.15)
        vm = float(v[m].max())
        dans = bool(np.mean(p_ap[m]) > 0.5)
        if dans:
            gestes.append({"de": tr0, "a": tr1, "v_max": round(vm, 1), "air": vm >= V_GESTE_APPEL})
        if vm < V_GESTE_APPEL:
            lent[m] = 1.0
    a = a * (1 - p_ap * lent)
    a = lissage(a, 0.015, 0.080)
    fc = 1100 * 2 ** (2.4 * np.clip(v / vmax, 0, 1))
    fc = lissage(fc, 0.02, 0.08)
    air_bas = bruit_module(N, fc, 1.4, graine=151)
    air_haut = passe_haut(bruit_module(N, np.maximum(2.5 * fc, 5000.0), 1.0, graine=153), AU_DESSUS_LIGNE)
    # même sonie K pour les deux airs (là où l'air sonne), pour que le fondu de l'un à l'autre ne change pas le niveau
    w_ = a > 0.02
    kb = float(np.mean(MX.ponderer_k(air_bas[:, None])[w_] ** 2)); kh = float(np.mean(MX.ponderer_k(air_haut[:, None])[w_] ** 2))
    air_haut *= np.sqrt(kb / kh) * S.gain(AIR_HAUT_DB)
    air = (np.sqrt(1 - p_ap) * air_bas + np.sqrt(p_ap) * air_haut) * a
    st = S.panner(air, MX.pan_point(TT))
    st = st + 0.12 * S.humide(st, 0.6, graine=152)[:N]
    st *= duck[:, None]
    ref = (TT >= 42.2) & (TT <= 42.6)                         # le saut vers le ı, le trajet le plus rapide
    g = NIV["air_max"] - momentanee_max(st[ref])
    st *= S.gain(g)
    piste += st
    ech = []
    for tr0, tr1 in SEGMENTS_V:
        m = (TT >= tr0) & (TT <= tr1 + 0.1)
        ech.append({"de": tr0, "a": tr1, "v_max": round(float(v[m].max()), 1),
                    "instantanee_max_seule": round(momentanee_max(st[m]), 1)})
    cue("air-trajets", "point", 0.0, "point-resolu.json (v, x_sans) à chaque échantillon ; mix.EV décroché → raccroché",
        f"hors de l'appel : bruit filtré, cloche 1,4 oct. centrée à 1,1 kHz × 2^(2,4·v/{vmax:.1f}) ; PENDANT l'appel "
        "(décroché → raccroché, rampes 60 ms) : cloche 1 oct. centrée à max(2,5·fc, 5 kHz), passe-haut 4,5 kHz (au-dessus "
        f"de la ligne), même sonie K, et seulement sur les gestes à v_max ≥ {V_GESTE_APPEL:.0f} px/image ; niveau "
        f"((v − 4)/({vmax:.1f} − 4))^1,3, lissé 15/80 ms ; −8 dB sous la voix ; muet quand le point écrit ; réverbe 0,6 s à 12 %",
        f"{NIV['air_max']} LUFS instantanés au saut vers le ı", pan="0,6·(x − 540)/540 à chaque échantillon", trajets=ech,
        gestes_pendant_l_appel=gestes)
    # 2.4 les sauts sur les heures (2e revue 27/09). Le CONTACT est déjà sonorisé par le toucher du master (le ré court,
    # avec son contact 5-11 kHz) : un tic 10-15 kHz posé dessus n'était perçu que par une oreille jeune à fort volume
    # (4 dB au-dessus du seuil à 0 dBFS = 80 dB SPL ; perte de 20 dB à 10-12 kHz courante dès 45-50 ans). On sonorise donc
    # l'ENVOL de chaque saut, où rien ne masque : le point décolle du papier de l'agenda, un décollement de 20 ms pris dans
    # les transitoires de la prise de papier de l'agenda (la matière sur laquelle il se pose), passe-bande 4,5-9 kHz
    # (au-dessus de la ligne pendant la voix), un transitoire différent à chaque saut, panoramiqué sur x.
    tex = papiers()[0]
    y = S.passe_bande(np.concatenate([tex[1], np.zeros(8192)]), 4500, 9000, front=500)[:len(tex[1])]
    w = int(0.002 * SR)
    e = np.convolve(y ** 2, np.ones(w) / w, mode="same")
    pics = []
    e2 = e.copy()
    while len(pics) < 4:
        i = int(np.argmax(e2))
        if i > int(0.004 * SR) and i < len(y) - int(0.03 * SR):
            pics.append(i)
        e2[max(0, i - int(0.08 * SR)):i + int(0.08 * SR)] = 0
    for (nom, niv), i in zip((("saut_neuf_envol", NIV["envol"]), ("saut_dix_envol", NIV["envol"]),
                               ("saut_onze_envol", NIV["envol"]), ("retour_envol", NIV["envol_retour"])), sorted(pics)):
        tc = EV[nom]["t"]
        seg = fondus(y[i - int(0.002 * SR):i + int(0.018 * SR)], 0.001, 0.008)
        st = labo.reverbe(mobile(seg / np.max(np.abs(seg)), tc), 0.5, 0.08, graine=163)
        poser(piste, au_niveau(st, niv), tc)
        cue(f"envol-{nom.replace('_envol', '').replace('saut_', '')}", "point", tc, f"evenements.{nom} (le point quitte l'heure)",
            f"décollement de papier : transitoire de 20 ms de la prise de papier {tex[0]} (celle de l'agenda, à "
            f"{i / SR:.3f} s), passe-bande 4,5-9 kHz, réverbe 0,5 s à 8 % ; le contact, lui, est le toucher du master",
            f"{niv} LUFS instantanés", pan=round(float(MX.pan_point(tc)), 3))
    # 2.5 l'assise sur le ı (2e revue 27/09) : le sinus 73 Hz ne passait pas sur un haut-parleur (99,4 % de son énergie sous
    # 150 Hz). L'attaque du ré du master EST l'atterrissage (image 1 287) ; la variante y ajoute la goutte de la naissance
    # (le point est de l'encre : il naît et se pose en goutte), passe-haut 250 Hz, posée à l'image suivante, quand le point
    # se relâche (1,18 × 0,84 → 1,07 × 0,94), pour ne pas s'ajouter à l'attaque (le limiteur ne doit pas mordre, contrôle Z).
    tc = T["re"] + 1 / 30
    st = labo.reverbe(mobile(GOUTTE[0] * 1.0, tc), 0.6, 0.10, graine=164)
    poser(piste, au_niveau(st, NIV["assise"]), tc)
    cue("assise-i", "point", tc, "evenements.signature_re_contact + 1 image (1 288 : le point se relâche, 1,07 × 0,94)",
        "la goutte de la naissance (encre, passe-haut 250 Hz), réverbe 0,6 s à 10 %", f"{NIV['assise']} LUFS instantanés",
        pan=round(float(MX.pan_point(tc)), 3))
    return piste


# ── 3. L'ÉCRITURE ───────────────────────────────────────────────────────────
# La plume écrit CE QU'ON VOIT (revue 27/09 : avant, le rythme des coups de plume était celui de la prise ElevenLabs,
# corrélation 0,93 avec la prise, 0,16 à 0,29 avec la vitesse du point). À l'image, le point balaie la ligne et le texte
# apparaît derrière son bord : la plume frotte donc (a) à la vitesse du point et (b) plus fort là où le bord révèle de
# l'encre (les jambages de « 09:00 Florian », les fûts du V, du k, du ı, les flancs des o). On lit l'encre DANS la vidéo :
# profil de colonnes sombres sur l'image de fin d'écriture, bord révélé mesuré sur trois images intermédiaires.
ECRITS = {"rendez-vous": {"t": (EV["plume_pose"]["t"], EV["ecriture_fin"]["t"]), "image_fin": EV["ecriture_fin"]["image"] - 1,
                          "lignes": (650, 750), "x0": 330, "images_bord": (764, 768, 772), "decal": 0.15},
          "vokio": {"t": tuple(EV["plume_mot"]["t"]), "image_fin": EV["plume_mot"]["images"][1] + 1,
                    "lignes": (690, 880), "x0": 0, "images_bord": (1252, 1256, 1262), "decal": 1.00}}
PLANCHER_PAPIER = 0.25        # hors encre, la plume frotte encore le papier (−12 dB)


def image_video(n):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(VIDEO), "-vf", f"select=eq(n\\,{n})", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(1920, 1080, 3).astype(np.float64)


def colonnes_encre(n, lignes, x0):
    """Pixels d'encre par colonne (luminance < 160 : l'encre #262019 et le gris du 09:00 ; le point solaire, 171, et le
    fond du bloc en sont exclus), lignes [y0 ; y1[, colonnes ≥ x0."""
    a = image_video(n)[lignes[0]:lignes[1]]
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    c = (lum < 160).sum(axis=0).astype(np.float64)
    c[:x0] = 0
    return c


def rms_centre(x, duree):
    """Enveloppe RMS centrée (fenêtre de Hann de `duree` s, phase nulle : pas de retard, donc pas de dépassement)."""
    w = np.hanning(max(3, int(duree * SR)))
    w /= w.sum()
    return np.sqrt(np.convolve(x ** 2, w, mode="same") + 1e-20)


def grain_continu(tex, seuil_db=12.0):
    """Le grain de la plume SANS son rythme : les passages tenus de la prise (enveloppe 10 ms à moins de seuil_db de la
    crête), chacun aplati (÷ son RMS centré 5 ms), mis bout à bout (fondus 4 ms à puissance constante), puis aplatis encore
    (÷ RMS centré 20 ms) : le frottement du bec reste, les coups de la prise disparaissent. Enveloppes CENTRÉES : un
    suiveur causal dépassait à chaque raccord (un clic large bande, vu sur le spectrogramme)."""
    e = 20 * np.log10(rms_centre(tex, 0.010))
    haut = e > e.max() - seuil_db
    morceaux, i = [], 0
    while i < len(haut):
        if haut[i]:
            j = i
            while j < len(haut) and haut[j]:
                j += 1
            if j - i >= int(0.015 * SR):
                m = tex[i:j]
                env = rms_centre(m, 0.005)
                morceaux.append(m / np.maximum(env, 0.3 * np.median(env)))
            i = j
        else:
            i += 1
    x = int(0.004 * SR)
    r = np.sin(np.pi / 2 * np.linspace(0, 1, x))
    out = morceaux[0]
    for m in morceaux[1:]:
        out = np.concatenate([out[:-x], out[-x:] * r[::-1] + m[:x] * r, m[x:]])
    env = rms_centre(out, 0.020)
    out = out / np.maximum(env, 0.3 * np.median(env))
    return out / np.sqrt(np.mean(out ** 2)), len(morceaux)


def transitoires_max_db(x, court=0.001, long_=0.020):
    """Le plus fort écart entre la puissance sur 1 ms et la médiane glissante sur 20 ms (dB) : ~3-6 dB pour un bruit
    régulier, bien plus s'il y a un clic."""
    p1 = rms_centre(x, court) ** 2
    k = int(long_ * SR)
    med = np.array([np.median(p1[max(0, i - k):i + k]) for i in range(0, len(p1), int(0.001 * SR))])
    p1s = p1[::int(0.001 * SR)][:len(med)]
    return float(10 * np.log10(np.max(p1s / (med + 1e-20))))


def pilote_ecriture(nom, t):
    """Ce que la plume doit faire à chaque instant t : (v/vmax)·(plancher + (1 − plancher)·encre au bord révélé)."""
    E = ECRITS[nom]
    prof = colonnes_encre(E["image_fin"], E["lignes"], E["x0"])
    k = 7                                                     # largeur du bec, en px
    prof = np.convolve(prof, np.ones(k) / k, mode="same")
    prof = np.clip(prof / np.percentile(prof[prof > 0], 95), 0, 1)
    bords = []
    for n in E["images_bord"]:
        c = colonnes_encre(n, E["lignes"], E["x0"])
        bords.append(float(np.nonzero(c)[0].max()) - MX.x_point(n / 30))
    dec = float(np.median(bords))
    assert max(bords) - min(bords) < 4.0, f"bord révélé instable ({nom} : {bords})"
    v = MX.v_point(t)
    xe = MX.x_point(t) + dec
    encre = np.interp(xe, np.arange(len(prof)), prof)
    p0, p1 = E["t"]
    d = (v / v.max()) * (PLANCHER_PAPIER + (1 - PLANCHER_PAPIER) * encre) * ((t >= p0) & (t <= p1 + 0.01))
    return lissage(d, 0.002, 0.012), {"decalage_bord_px": round(dec, 1), "bords_mesures_px": [round(b_, 1) for b_ in bords],
                                     "image_profil": E["image_fin"], "colonnes_d_encre": int(np.sum(prof > 0.05))}


def ecriture():
    piste = np.zeros((N, 2))
    # le choix par la mesure : la prise qui donne le grain continu le plus long (passages à moins de 18 dB de la crête),
    # sans transitoire (≤ 6 dB au-dessus de la médiane 20 ms) ; son rythme propre ne compte plus, il est retiré
    cand = []
    for k, chemin, m in prises("plume"):
        x = labo.lire(chemin)
        tex = S.passe_bande(np.concatenate([x.mean(axis=1), np.zeros(8192)]), 1300, 13000, front=300)[:len(x)]
        g_, nbm = grain_continu(tex, 18.0)
        cand.append({"prise": k, "grain_s": round(len(g_) / SR, 3), "morceaux": nbm, "transitoire_max_db": round(transitoires_max_db(g_), 1),
                     "g": g_, "mesures": m})
    ok = [c for c in cand if c["transitoire_max_db"] <= 6.0] or cand
    best = max(ok, key=lambda c: c["grain_s"])
    grain, kp, nb_morceaux = best["g"], best["prise"], best["morceaux"]
    CHOIX["plume"] = {"retenue": kp, "raison": "le grain continu le plus long (passages à moins de 18 dB de la crête) sans "
                      "transitoire > 6 dB ; le rythme de la prise est retiré (grain aplati), c'est l'image qui le donne",
                      "candidats": [{k: v for k, v in c.items() if k != "g"} for c in cand]}
    departs = {"rendez-vous": 0.0, "vokio": 0.5}             # deux endroits différents du grain (fraction de la longueur libre)
    for nom, E in ECRITS.items():
        p0, p1 = E["t"]
        i0 = int(round((p0 - 0.03) * SR)); n = int(round((p1 - p0 + 0.10) * SR))
        t = (i0 + np.arange(n)) / SR
        e, info = pilote_ecriture(nom, t)
        libre = len(grain) - n
        assert libre > 0, "grain de plume trop court"
        j0 = int(departs[nom] * libre)
        seg = grain[j0:j0 + n]
        mono = fondus(seg * e, 0.002, 0.03)
        st = labo.reverbe(mobile(mono, i0 / SR), 0.5, 0.08, graine=171)
        poser(piste, au_niveau(st, NIV["plume"]), i0 / SR)
        PILOTES[nom] = (i0, e)
        cue(f"plume-{nom}", "ecriture", p0, f"evenements.{'plume_pose → ecriture_fin' if nom == 'rendez-vous' else 'plume_mot'} ; "
            f"image {info['image_profil']} (l'encre) ; images {list(E['images_bord'])} (le bord révélé)",
            f"plume prise {kp}, grain continu ({nb_morceaux} passages tenus, aplatis par RMS centrés), passe-bande 1,3-13 kHz ; niveau = "
            f"(v/vmax) × ({PLANCHER_PAPIER} + {1 - PLANCHER_PAPIER} × encre au bord révélé, x + {info['decalage_bord_px']} px), "
            "lissé 2/12 ms (la plume se tait quand le point s'arrête, frotte plus fort sur les fûts) ; réverbe 0,5 s à 8 %",
            f"{NIV['plume']} LUFS instantanés", pan=f"suit la plume {MX.pan_point(p0):+.3f} → {MX.pan_point(p1):+.3f}", fin=p1,
            pilote=info)
        # la pose : la même goutte que la naissance (le point EST l'encre)
        pose = p0
        st = mobile(GOUTTE[0] * 1.0, pose)
        poser(piste, au_niveau(st, NIV["pose_plume"]), pose)
        cue(f"pose-plume-{nom}", "ecriture", pose, "evenements.plume_pose" if nom == "rendez-vous" else "evenements.plume_mot[0]",
            "la goutte de la naissance", f"{NIV['pose_plume']} LUFS instantanés", pan=round(float(MX.pan_point(pose)), 3))
    return piste


PILOTES = {}


# ── 4. LES OBJETS : transitions de scène, bulle, vibreur sur bois ───────────
def glisse(tex, t0, t1, forme, niveau, pan, graine, queue=0.08, rev=0.6):
    """Frottement d'un objet qui se déplace de t0 à t1 : niveau ∝ vitesse^0,7 de son ease (GSAP power3 = quartique) :
    « out » vitesse ∝ (1 − p)³, « in » ∝ p³ × (1 − p)^0,5 (l'objet s'efface en sortant)."""
    n = int(round((t1 - t0 + queue) * SR))
    p = np.clip(np.arange(n) / SR / (t1 - t0), 0, 1)
    v = (1 - p) ** 3 if forme == "out" else p ** 3 * (1 - p) ** 0.5
    v = np.where(np.arange(n) / SR > t1 - t0, 0.0, v)
    e = lissage((v / v.max()) ** 0.7, 0.010, 0.050)
    j0 = int(np.random.default_rng(graine).uniform(0, max(1, len(tex) - n - 1)))
    seg = np.resize(tex[j0:], n) if len(tex) - j0 < n else tex[j0:j0 + n]
    st = labo.reverbe(S.panner(fondus(seg * e, 0.004, 0.03), pan), rev, 0.10, graine=graine)
    return au_niveau(st, niveau)


_PAPIERS = []


def papiers():
    """Les prises de papier, de la plus douce à la moins : pas de bosse grave, niveau le plus stable ; [(prise, texture)]."""
    if not _PAPIERS:
        pap = sorted(prises("papier"), key=lambda e: (e[2]["part_sous_150hz"] > 0.1, e[2]["stabilite_db"]))
        CHOIX["papier"] = {"ordre": [k for k, _, _ in pap], "raison": "pas de bosse grave (< 10 % sous 150 Hz), puis le niveau "
                           "le plus stable ; la 1re pour l'agenda qui monte (et les envols du point, qui décolle de ce papier), "
                           "la 2e pour sa sortie, la 3e pour le tamis", "mesures": {str(k): m for k, _, m in pap}}
        for k, chemin, m in pap:
            y = S.passe_bande(np.concatenate([labo.lire(chemin).mean(axis=1), np.zeros(8192)]), 900, 14000, front=300)
            y = y[:int(m["duree_utile_s"] * SR)]
            _PAPIERS.append((k, y / np.sqrt(np.mean(y ** 2))))
    return _PAPIERS


def objets(sfx):
    piste = np.zeros((N, 2))
    tx = papiers()
    am0, am1 = EV["agenda_monte"]["t"]
    poser(piste, glisse(tx[0][1], am0, am1, "out", NIV["papier_monte"], 0.04, 181), am0)
    cue("agenda-monte", "objets", am0, "evenements.agenda_monte (+520 → 0 px, power3.out) : le vrai silence de l'outil",
        f"papier prise {tx[0][0]}, 0,9-14 kHz, niveau ∝ vitesse^0,7", f"{NIV['papier_monte']} LUFS instantanés", pan=0.04, fin=am1)
    as0, as1 = EV["agenda_sort"]["t"]
    poser(piste, glisse(tx[1][1], as0, as1, "in", NIV["papier_sort"], 0.04, 182), as0)
    cue("agenda-sort", "objets", as0, "evenements.agenda_sort (0 → −270 px, power3.in, opacité 1 − p)",
        f"papier prise {tx[1][0]}", f"{NIV['papier_sort']} LUFS instantanés", pan=0.04, fin=as1)
    tf0 = EV["tamis_fondu"]["t"][0]; tr1 = EV["tamis_resserrage"]["t"][1]
    tam = S.passe_bande(np.concatenate([tx[2][1], np.zeros(8192)]), 4000, 14000, front=500)[:len(tx[2][1])]
    poser(piste, glisse(tam / np.sqrt(np.mean(tam ** 2)), tf0, tr1, "out", NIV["tamis"], -0.30, 183), tf0)
    cue("tamis", "objets", tf0, "evenements.tamis_fondu[0] → tamis_resserrage[1] (les « euh » s'effacent, les mots se resserrent)",
        f"papier prise {tx[2][0]}, 4-14 kHz (un grain fin)", f"{NIV['tamis']} LUFS instantanés", pan=-0.30, fin=tr1)
    # le téléphone (revue 27/09) : UNE matière. Il entre sous « Au revoir » (35,12 → 35,42) : rien ne l'y fait entendre
    # sans passer dans la ligne (les prises d'objet qui glisse n'ont aucune énergie au-dessus de 4,5 kHz, mesuré :
    # part_sur_4k5 = 0,000 à 0,003), donc la voix passe seule ; il SORT dans le blanc de la lecture (41,00) : la glisse
    # d'un téléphone sur un bureau, plus courte et pas plus forte que les autres transitions
    xg, kg = choisir("glisse_telephone", lambda m: (m["bouffees"] != 1, m["stabilite_db"]), "un seul geste, le plus régulier")
    g_ = S.passe_bande(np.concatenate([xg.mean(axis=1), np.zeros(8192)]), 250, 9000, front=100)[:len(xg)]
    ts0, ts1 = EV["telephone_sortie"]["t"]
    poser(piste, glisse(g_ / np.sqrt(np.mean(g_ ** 2)), ts0, ts1, "in", NIV["tel_sort"], 0.0, 185, queue=0.04, rev=0.4), ts0)
    cue("telephone-sort", "objets", ts0, "evenements.telephone_sortie (0 → −300 px, power3.in, opacité 1 − p)",
        f"glisse_telephone prise {kg}, 250 Hz-9 kHz, niveau ∝ vitesse^0,7, queue 40 ms, réverbe 0,4 s",
        f"{NIV['tel_sort']} LUFS instantanés", pan=0.0, fin=ts1)
    # la bulle (2e revue 27/09) : AUCUN son propre. Le souffle d'éclosion (bruit 0,9 → 4,5 kHz qui s'ouvrait avec le rayon)
    # était un « riser » d'interface sans source physique, la raison même du retrait de l'étincelle (règle 11), et il
    # remplissait le seul creux qui rythme le vibreur (36,85 → 36,94, juste après le silence numérique). L'arrivée du SMS,
    # c'est le vibreur et son bois ; la bulle se voit.
    # le vibreur sur bois : la prise la plus stable, ramenée sur ré3 (146,83 Hz, le moteur de synthèse), enveloppe s6
    xv, kv = choisir("vibreur_bois", lambda m: (m["stabilite_db"], m["fond_db_sous_crete"]), "la vibration la plus stable")
    mv = xv.mean(axis=1)
    a0, a1 = int(0.20 * SR), int(1.40 * SR)
    X = np.abs(np.fft.rfft(mv[a0:a1] * np.hanning(a1 - a0))); f = np.fft.rfftfreq(a1 - a0, 1 / SR)
    zone = (f > 80) & (f < 320)
    f0 = float(f[zone][np.argmax(X[zone])])
    rap = S.F_RE3 / f0
    src = mv[a0:a1]
    pos = np.arange(0, len(src) - 2, rap)
    mv2 = np.interp(pos, np.arange(len(src)), src)
    s6 = MX.SEC["s6"]
    v0, v1 = s6["segments_s"][0][0], s6["segments_s"][-1][1]
    n = int(round((v1 - v0 + 0.03) * SR))
    t = v0 + np.arange(n) / SR
    env = MX.trapeze(t, s6["segments_s"], s6["rampes_s"])
    tex = passe_haut(np.resize(mv2, n + 2048), 90)
    # EN PHASE avec le moteur : ramenée sur le même ré3, la prise s'annulait en partie avec le vibreur de synthèse du
    # master (mesuré : sfx seul −20,1 LUFS, sfx + bois −23,4 sur [36,67 ; 37,20]). Un bois couplé au moteur vibre avec
    # lui : on cherche le retard (0 à une période du ré3, pas de 0,05 ms) et la polarité qui maximisent l'énergie de la
    # somme avec le vibreur du stem sfx ; l'enveloppe s6 est posée APRÈS le retard (l'attaque reste à l'image 1100).
    i0 = int(round(v0 * SR))
    ref = sfx[i0:i0 + n].mean(axis=1)
    g0 = S.gain(NIV["vibreur_bois"] - momentanee_max(S.panner(tex[:n] * env, 0.0)))
    essais = []
    for d in np.arange(0, SR / S.F_RE3, 2.4):
        for pol in (1.0, -1.0):
            y = pol * g0 * np.interp(np.arange(n) + d, np.arange(len(tex)), tex) * env
            essais.append((float(np.sum((ref + y) ** 2)), d, pol, y))
    e_ref = float(np.sum(ref ** 2))
    e_best, d_best, pol_best, seg = max(essais, key=lambda e: e[0])
    e_pire = min(e[0] for e in essais)
    # gain final : l'énergie de la somme = celle du moteur + vibreur_bois_somme_db (racine de l'équation du 2e degré)
    ry, yy = float(np.dot(ref, seg)), float(np.dot(seg, seg))
    k = 10 ** (NIV["vibreur_bois_somme_db"] / 10)
    a_ = (-2 * ry + np.sqrt(4 * ry ** 2 + 4 * yy * (k - 1) * e_ref)) / (2 * yy)
    seg = seg * a_
    st = S.panner(seg, 0.0)
    st = st + 0.10 * S.humide(st, 0.4, graine=196)[:n]
    poser(piste, st, v0)
    CHOIX["vibreur_bois"]["mise_en_phase"] = {"retard_ms": round(1000 * d_best / SR, 3), "polarite": pol_best,
                                              "energie_somme_sur_moteur_db_au_depart": round(10 * np.log10(e_best / e_ref), 2),
                                              "energie_somme_sur_moteur_db": round(10 * np.log10(np.sum((ref + seg) ** 2) / e_ref), 2),
                                              "bois_seul_instantanee_lufs": round(momentanee_max(st), 1),
                                              "pire_essai_db": round(10 * np.log10(e_pire / e_ref), 2)}
    CHOIX["vibreur_bois"]["fondamentale_mesuree_hz"] = round(f0, 2)
    CHOIX["vibreur_bois"]["rapport_vers_re3"] = round(rap, 4)
    cue("vibreur-bois", "objets", v0, "secousses.s6.segments_s (= evenements.bulle_et_vibreur) : la même enveloppe que l'image",
        f"vibreur_bois prise {kv} (fondamentale {f0:.1f} Hz → ré3 146,83 Hz, rapport {rap:.3f}), passe-haut 90 Hz, "
        "enveloppe trapèze 12/25 ms de secousses.s6 ; mise en phase avec le moteur (retard "
        f"{1000 * d_best / SR:.2f} ms, polarité {pol_best:+.0f})", f"moteur + bois = moteur + {NIV['vibreur_bois_somme_db']} dB", pan=0.0,
        segments=s6["segments_s"])
    return piste


# ── 5. LE HALO : la nappe qui s'élargit, le souffle accordé ─────────────────
def plan_nappe():
    """Les accords de mix.nappe (mêmes instants, mêmes fondus : copie lisible du plan de mix.py, contrôlée par
    controle_design.py contre le chroma du stem nappe), puis l'air du SMS (G4 · D5) et l'accord de fin (mix.ACCORD_FIN)."""
    t_res, d_res = T["resolution"], MX.DEC["resolution_fondu"]
    return [(T["pedale"], 1.5, {"A4": 1}, "cos"),
            (T["sol"], 2.0, {"G2": 1, "D3": 1, "G4": 1, "B4": 1}, "cos"),
            (T["sus4"], 0.6, {"D3": 1, "A3": 1, "G4": 1, "D5": 1}, "puissance"),
            (T["re7"], 0.8, {"D3": 1, "A3": 1, "F#4": 1, "C5": 1}, "puissance"),
            (T["re9"], 2.0, {"D3": 1, "A3": 1, "F#4": 1, "C5": 1, "E4": 0.5}, "cos"),
            (t_res - d_res / 2, d_res, {"G2": 1, "D3": 1, "D4": 1, "G4": 1, "B4": 1}, "puissance"),
            (T["raccroche"], 0.005, {}, "cos"),     # revue 27/09 (2) : mix.py coupe tout au raccroché, DÉFINITIVEMENT ; le
                                                    # halo ne rapporte pas l'accord de l'appel après le silence
            (T["air_sms"], 0.8, {"G4": 1, "D5": 0.6}, "cos"),
            (T["re"], 0.8, dict(MX.ACCORD_FIN), "cos")]


def cles(points):
    """Courbe par morceaux en cosinus entre des (instant, valeur)."""
    y = np.full(N, points[0][1], dtype=float)
    for (t0, a), (t1, b) in zip(points[:-1], points[1:]):
        m = (TT >= t0) & (TT < t1)
        y[m] = a + (b - a) * MX.fondu_cos(TT[m], t0, t1 - t0)
    y[TT >= points[-1][0]] = points[-1][1]
    return y


def souffle_accorde(graine, poids, registres, sigma_cents, creux=None, passe_bas=None, nf=8192, pas=2048):
    """Bruit blanc filtré sur des résonances gaussiennes (largeur sigma_cents(t)) aux fréquences k·f de chaque note
    (k ∈ registres : {k: poids_k(t)}), pondérées par le poids de la note ; STFT Hann.
    creux = {"hz": [...], "sigma_cents": s, "alpha": (N,)} : creuse le masque autour de ces fréquences (1 − α·gauss) ;
    passe_bas = {"fc": Hz, "ordre": n, "alpha": (N,)} : passe-bas de Butterworth d'ordre n, fondu par α."""
    g = np.random.default_rng(graine)
    xp = g.standard_normal(N + 2 * nf)
    win = np.hanning(nf + 1)[:-1]
    nb = (len(xp) - nf) // pas + 1
    fr = np.lib.stride_tricks.sliding_window_view(xp, nf)[::pas][:nb] * win
    X = np.fft.rfft(fr, axis=1)
    f = np.fft.rfftfreq(nf, 1 / SR); f[0] = 1.0
    c = np.clip(np.arange(nb) * pas + nf // 2 - nf, 0, N - 1)
    sc = sigma_cents[c]
    m = np.zeros((nb, len(f)))
    lf = 1200 * np.log2(f)
    for nom, fn in MX.NOTES.items():
        wn = poids[nom][c]
        if not np.any(wn > 0):
            continue
        for k, wk in registres.items():
            wkc = wk[c] * wn
            actif = np.nonzero(wkc > 1e-4)[0]
            if not len(actif):
                continue
            d = (lf[None, :] - 1200 * np.log2(k * fn)) / sc[actif, None]
            m[actif] += wkc[actif, None] * np.exp(-0.5 * d ** 2) / np.sqrt(k)
    if creux is not None:
        a_c = creux["alpha"][c]
        for fx in creux["hz"]:
            dn = (lf - 1200 * np.log2(fx)) / creux["sigma_cents"]
            m *= 1 - a_c[:, None] * np.exp(-0.5 * dn ** 2)[None, :]
    if passe_bas is not None:
        b_c = passe_bas["alpha"][c]
        H = 1 / np.sqrt(1 + (f / passe_bas["fc"]) ** (2 * passe_bas["ordre"]))
        m *= (1 - b_c[:, None]) + b_c[:, None] * H[None, :]
    y = np.fft.irfft(X * m, nf, axis=1) * win
    out = np.zeros(len(xp))
    for j in range(nb):
        out[j * pas:j * pas + nf] += y[j]
    return out[nf:nf + N]


BANDES_PLAFOND = 1000.0 * 2 ** (np.arange(-2, 10) / 3)    # tiers d'octave 630 Hz → 8 kHz (le contrôle de la revue
                                                           # porte sur 1-8 kHz ; sous 1 kHz, les raies k = 2 à 740 et
                                                           # 880 Hz doublaient la nappe : le plafond descend à 630 Hz)
PLAFOND_DB = -8.0              # le souffle reste 8 dB sous (nappe + signature) dans chaque tiers d'octave (contrôle : −6)
PLAFOND_SCINT_DB = -12.0       # et 12 dB sous la signature seule dans le tiers d'octave du scintillement (contrôle : −10)


def _lisse(a, k, axe=1):
    """Moyenne glissante centrée de 2k + 1 trames (bords répliqués)."""
    if k <= 0:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axe] = (k, k)
    b = np.pad(a, pad, mode="edge")
    c = np.cumsum(b, axis=axe)
    c = np.concatenate([np.zeros_like(np.take(c, [0], axis=axe)), c], axis=axe)
    n = a.shape[axe]
    return (np.take(c, np.arange(2 * k + 1, 2 * k + 1 + n), axis=axe) - np.take(c, np.arange(0, n), axis=axe)) / (2 * k + 1)


def _min_glissant(a, k):
    b = np.pad(a, [(0, 0), (k, k)], mode="edge")
    return np.min(np.lib.stride_tricks.sliding_window_view(b, 2 * k + 1, axis=1), axis=2)


def plafond_spectral(st, ref, sig, alpha, nf=8192, pas=2048):
    """Le souffle ne dépasse jamais la nappe : dans chaque tiers d'octave de 630 Hz à 8 kHz, sa puissance (milieu, lissée
    ±0,1 s) reste PLAFOND_DB sous celle de nappe + signature (milieu, lissée ±0,1 s), et PLAFOND_SCINT_DB sous la
    signature seule dans le tiers d'octave du scintillement (2 349,3 Hz). Gain par bande : minimum glissant ±0,25 s puis
    moyenne ±0,1 s (il reste sous l'exigence à chaque trame, sans pomper), interpolé en log-fréquence, fondu par α(t).
    STFT Hann, 75 % de recouvrement ; le même gain sur G et D (l'image ne bouge pas). Renvoie (st plafonné, rapport)."""
    n = len(st)
    win = np.hanning(nf + 1)[:-1]
    f = np.fft.rfftfreq(nf, 1 / SR)

    def stft(x):
        xp = np.concatenate([np.zeros(nf), x, np.zeros(2 * nf)])
        nb = (len(xp) - nf) // pas + 1
        return np.fft.rfft(np.lib.stride_tricks.sliding_window_view(xp, nf)[::pas][:nb] * win, axis=1)
    XL, XR = stft(st[:, 0]), stft(st[:, 1])
    PH = np.abs((XL + XR) / 2) ** 2
    PR = np.abs(stft(ref.mean(axis=1))) ** 2
    PS = np.abs(stft(sig.mean(axis=1))) ** 2
    nb = XL.shape[0]
    tc = (np.arange(nb) * pas + nf // 2 - nf) / SR
    k_l, k_m = int(round(0.1 * SR / pas)), int(round(0.25 * SR / pas))
    bandes = [(c * 2 ** (-1 / 6), c * 2 ** (1 / 6), PR, PLAFOND_DB) for c in BANDES_PLAFOND]
    bandes.append((2349.3 * 2 ** (-1 / 6), 2349.3 * 2 ** (1 / 6), PS, PLAFOND_SCINT_DB))
    g_db = np.zeros((len(bandes), nb))
    for j, (lo, hi, P, cible) in enumerate(bandes):
        sel = (f >= lo) & (f < hi)
        ph = _lisse(PH[:, sel].sum(axis=1)[None, :], k_l)[0] + 1e-30
        pr = _lisse(P[:, sel].sum(axis=1)[None, :], k_l)[0] + 1e-30
        g_db[j] = np.minimum(0.0, cible + 10 * np.log10(pr / ph))
    g_db = _lisse(_min_glissant(g_db, k_m), k_l)
    g_db = np.maximum(g_db, -120.0) * np.interp(tc, np.arange(n) / SR, alpha)[None, :]
    # par bin : le gain de SA bande, étendue de 1/24 d'octave de chaque côté (là où deux bandes se recouvrent, le plus
    # sévère des deux : chaque bande tient son plafond) ; 0 dB sous 561 Hz, le gain de 8 kHz au-dessus
    G = np.zeros((nb, len(f)))
    ext = 2 ** (1 / 24)
    for j, (lo, hi, _, _) in enumerate(bandes):
        sel = (f >= lo / ext) & (f < hi * ext)
        G[:, sel] = np.minimum(G[:, sel], g_db[j][:, None])
    haut = f >= bandes[len(BANDES_PLAFOND) - 1][1] * ext
    G[:, haut] = np.minimum(G[:, haut], g_db[len(BANDES_PLAFOND) - 1][:, None])
    A = 10 ** (G / 20)
    out = []
    for X in (XL, XR):
        y = np.fft.irfft(X * A, nf, axis=1) * win
        o = np.zeros((nb - 1) * pas + nf)
        for j in range(nb):
            o[j * pas:j * pas + nf] += y[j]
        out.append(o[nf:nf + n] / 1.5)            # Σ Hann² à 75 % de recouvrement = 1,5
    rapport = {"attenuation_max_db_par_bande": {f"{c:.0f}": round(float(-g_db[j].min()), 1) for j, c in enumerate(BANDES_PLAFOND)},
               "attenuation_max_db_scintillement": round(float(-g_db[-1].min()), 1)}
    return np.stack(out, axis=1), rapport


def halo(nap, sig_, duck, coupe):
    # (a) la nappe du master s'élargit : milieu inchangé, + côté décorrélé × w(t)
    f0_fin = FIN_SON - MX.DEC["fin_fondu"]
    w = cles([(0.0, 0.0), (T["pedale"], 0.0), (T["sol"], 0.15), (EV["depart_agenda"]["t"], 0.25), (T["resolution"], 0.40),
              (T["raccroche"], 0.40), (EV["bulle_et_vibreur"]["t"], 0.42), (T["la"], 0.45), (T["re"], 0.45), (f0_fin, 0.45),
              (FIN_SON, 0.30), (DUREE, 0.30)])
    mil = nap.mean(axis=1)
    cote = passe_haut(decorrele(mil, 201), 250) * w * coupe * duck      # la basse reste au centre (mono), seule l'image
                                                                      # s'ouvre ; la largeur aussi s'efface sous la voix
    cote = cote_sans_perte(cote, nap) * coupe
    elarg = np.stack([cote, -cote], axis=1)
    cue("nappe-s-elargit", "halo", T["pedale"], "pédale (4,60) → sol → départ vers l'agenda → résolution → vibreur → la → ré",
        "côté décorrélé (FIR passe-tout à phase aléatoire, 43 ms) du milieu de la nappe du master, au-dessus de 250 Hz, × w : "
        "0 → 0,15 → 0,25 → 0,40 | 0,42 → 0,45 (la, ré), refermé à 0,30 dans le fondu final ; −8 dB sous la voix ; par bin, "
        "sa composante en opposition avec le côté propre de la nappe est retirée (il n'en creuse jamais un canal) ; en mono il "
        "disparaît (G + D = 2 × milieu)", "largeur, sans gain au milieu",
        pan="±w", cles_w={"4,60": 0.0, "10,20": 0.15, "17,20": 0.25, "32,96": 0.40, "36,67": 0.42, "42,30": 0.45, "42,90": 0.45,
                                    "45,30": 0.45, "46,70": 0.30})
    # (b) le souffle accordé : octaves des notes de la nappe, de plus en plus de registres, résonances qui s'ouvrent
    plan = plan_nappe()
    poids = MX.poids_notes(TT, plan)
    t_sms = EV["bulle_et_vibreur"]["t"]
    reg = {4: cles([(0, 1.0), (DUREE, 1.0)]),
           8: cles([(0, 0.0), (EV["depart_agenda"]["t"], 0.0), (T["re7"], 0.35), (T["resolution"], 0.45), (T["re"], 0.5), (DUREE, 0.5)]),
           2: cles([(0, 0.0), (t_sms, 0.0), (T["la"], 0.5), (T["re"], 1.0), (DUREE, 1.0)])}
    sig = cles([(0, 10.0), (T["resolution"], 16.0), (t_sms, 18.0), (T["re"], 30.0), (DUREE, 30.0)])
    creux = {"hz": PARTIELS_SIGNATURE, "sigma_cents": 50.0, "alpha": MX.fondu_cos(TT, T["la"] - 0.15, 0.30)}
    bas = {"fc": SOUFFLE_PASSE_BAS[0], "ordre": SOUFFLE_PASSE_BAS[1], "alpha": MX.fondu_cos(TT, t_sms - 0.15, 0.30)}
    m1 = souffle_accorde(211, poids, reg, sig, creux, bas)
    s1 = souffle_accorde(212, poids, reg, sig, creux, bas)
    wb = cles([(0, 0.25), (T["resolution"], 0.45), (t_sms, 0.45), (T["re"], 0.45), (f0_fin, 0.45), (FIN_SON, 0.35), (DUREE, 0.35)])
    st = np.stack([m1 + wb * s1, m1 - wb * s1], axis=1)
    # niveau relatif (dB) : monte avec le film, fleurit au ré, puis suit le fondu de la nappe de fin
    rel = cles([(0, -4.0), (T["pedale"], -4.0), (T["sol"], 0.0), (T["resolution"], 3.0), (T["raccroche"], 3.0), (t_sms, 2.0),
                (T["la"], HALO_DB["la"]), (T["re"], HALO_DB["re"]), (T["re"] + 0.6, HALO_DB["re"] - 1.0), (DUREE, HALO_DB["re"] - 1.0)])
    g = S.gain(rel) * MX.fondu_cos(TT, T["pedale"], 1.5)
    g *= 1 - MX.fondu_cos(TT, FIN_SON - MX.DEC["fin_fondu"], MX.DEC["fin_fondu"])
    # après le silence, le souffle repart de rien AVEC l'air du SMS (même fondu cosinus de 0,8 s que mix.air_sms) : la
    # STFT de 170 ms étalerait sinon son attaque avant celle de la nappe
    g *= np.where(TT >= T["raccroche"], MX.fondu_cos(TT, T["air_sms"], 0.8), 1.0)
    st *= (g * duck * coupe)[:, None]
    st *= S.gain(NIV["souffle_ref"] - court_terme(st, 12.5, 17.5))
    # dès la bulle (2e revue 27/09) : le souffle reste une ombre de la nappe, jamais au-dessus d'elle ni de la marque
    st, plaf = plafond_spectral(st, nap + sig_, sig_, MX.fondu_cos(TT, t_sms - 0.15, 0.30))
    st *= coupe[:, None]
    CHOIX["halo_plafond"] = plaf
    niv_mes = {"accord de sol 12,5 → 17,5": round(court_terme(st, 12.5, 17.5), 1),
               "résolution 33,0 → 35,5": round(court_terme(st, 33.0, 35.5), 1),
               "lecture du SMS 38 → 41": round(court_terme(st, 38.0, 41.0), 1),
               "signature 42,9 → 45,3": round(court_terme(st, T["re"], 45.3), 1),
               "fondu final 45,3 → 46,7": round(court_terme(st, 45.3, FIN_SON), 1)}
    cue("souffle-accorde", "halo", T["pedale"], "les accords de mix.nappe (plan_nappe, coupé au raccroché), l'air du SMS, "
        "l'accord de fin",
        "bruit blanc sur résonances gaussiennes aux octaves k·f des notes (k = 4 dès la pédale ; 8 dès le départ vers l'agenda ; "
        "2 dès le vibreur), largeur 10 → 30 cents ; milieu ± w·côté (w 0,25 → 0,45, refermé à 0,35 dans le fondu final) ; "
        f"niveau relatif −4 dB à la pédale, {HALO_DB['la']:+.0f} au la, {HALO_DB['re']:+.0f} au ré ; −8 dB sous la voix ; "
        "coupé au raccroché, il repart avec l'air du SMS (fondu 0,8 s) ; dès la bulle, passe-bas "
        f"{SOUFFLE_PASSE_BAS[0]:.0f} Hz (ordre {SOUFFLE_PASSE_BAS[1]}) ; dès le la, creusé (σ 50 cents) autour du ré6 et du "
        f"scintillement ({PARTIELS_SIGNATURE[0]} et {PARTIELS_SIGNATURE[1]} Hz) ; dès la bulle, PLAFONNÉ par tiers d'octave "
        f"(630 Hz-8 kHz) à {PLAFOND_DB:+.0f} dB sous nappe + signature, et à {PLAFOND_SCINT_DB:+.0f} dB sous la signature dans "
        "le tiers d'octave du scintillement : une ombre de la nappe, jamais sur la marque",
        f"{NIV['souffle_ref']} LUFS court terme sur l'accord de sol (12,5 → 17,5)", pan="large",
        souffle_court_terme_mesure=niv_mes)
    return elarg + st


# ── la voix d'abord : rattrapage mot par mot ────────────────────────────────
# Deux garanties par mot (revue 27/09 : la seule sonie K large bande pénalisait des éléments qui ne masquent rien, un
# tic à 12 kHz ou un poids à 60 Hz, et laissait passer ce qui masque vraiment) :
#   MASQUAGE, dans la bande réelle de la voix (100-3 800 Hz) : voix − reste ≥ max(10, min(marge master − 1, 16)) dB ;
#   PRÉSENCE, en sonie K : voix − reste ≥ max(10, min(marge master − 2, 16)) LU ;
#   et jamais plus de 0,2 sous la marge du master (un mot que le master laisse sous 10,2).
# Sinon toutes les couches ajoutées baissent ensemble sur le mot (±40 ms, rampes 30 ms), du gain le plus sévère des deux.
def marges(dk, reste_k):
    out = []
    for w in MX.MOTS["mots"]:
        i0, i1 = int(w["debut"] * SR), int(max(w["fin"], w["debut"] + 0.12) * SR)
        v = -0.691 + 10 * np.log10(np.sum(np.mean(dk[i0:i1] ** 2, axis=0)) + 1e-20)
        r = -0.691 + 10 * np.log10(np.sum(np.mean(reste_k[i0:i1] ** 2, axis=0)) + 1e-20)
        out.append((v - r, w, i0, i1, v, r))
    return out


def bande_voix(x):
    return S.passe_bande(x, BANDE_VOIX[0], BANDE_VOIX[1], front=50)


# Un mot que le MASTER laisse lui-même sous 10 (« confirmation. », 9,9 dB dans la bande de la voix) ne peut pas y remonter
# par des ajouts : il garde alors sa marge du master à 0,2 près (sinon le rattrapage coupait tout sous le mot).
CIBLES = {"bande": lambda m0: min(m0 - 0.2, max(10.0, min(m0 - 1.0, 16.0))),
          "K": lambda m0: min(m0 - 0.2, max(10.0, min(m0 - 2.0, 16.0)))}


def rattrapage(stems, design):
    """design : dict couche → (N,2). Garanties : voir plus haut (CIBLES). La baisse vise la couche RESPONSABLE : si la
    couche ajoutée la plus présente sur le mot peut à elle seule rendre la marge, elle seule baisse (le halo et le fond ne
    creusent pas pour un bruitage du point) ; sinon toutes les couches ajoutées baissent ensemble."""
    ancien = stems["nappe"] + stems["sfx"] + stems["signature"]
    esp = {"K": (MX.ponderer_k, MX.ponderer_k(stems["dialogue"]), MX.ponderer_k(ancien)),
           "bande": (bande_voix, bande_voix(stems["dialogue"]), bande_voix(ancien))}
    noms = list(design)
    gains = {n: np.ones(N) for n in noms}
    rapport = []

    def rampe(g, i0, i1):
        a, b = max(0, i0 - int(0.04 * SR)), min(N, i1 + int(0.04 * SR))
        ra = int(0.03 * SR)
        loc = np.ones(N)
        loc[a:b] = g
        loc[max(0, a - ra):a] = 1 - (1 - g) * S.rampe_cos(min(ra, a))
        loc[b:b + ra] = 1 - (1 - g) * S.rampe_cos(ra)[::-1][:len(loc[b:b + ra])]
        return loc

    for it in range(5):
        fait = 0
        par_mot = {}
        for k, (f, dv, anc) in esp.items():
            fl = {n: f(design[n] * gains[n][:, None]) for n in noms}
            nk = sum(fl.values())
            for (m0, w, i0, i1, v, r0), (m1, *_ ) in zip(marges(dv, anc), marges(dv, anc + nk)):
                cible = CIBLES[k](m0)
                if m1 >= cible - 0.02:
                    continue
                p_v = 10 ** ((v + 0.691) / 10); p0 = 10 ** ((r0 + 0.691) / 10)
                p_max = max(p_v * 10 ** (-cible / 10) - p0, 0.0) * 0.94       # 0,27 dB de marge (couplages, rampes)
                e = {n: float(np.sum(np.mean(fl[n][i0:i1] ** 2, axis=0))) for n in noms}
                top = max(e, key=e.get)
                reste = sum(e.values()) - e[top]
                if reste <= p_max and e[top] > 0:
                    cib, g = (top,), float(np.sqrt((p_max - reste) / e[top]))
                else:
                    tot = sum(e.values())
                    cib, g = tuple(noms), float(np.sqrt(p_max / tot)) if tot > 0 else 1.0
                g = min(g, 1.0)
                cle = (i0, i1)
                if cle not in par_mot or g < par_mot[cle][0]:
                    par_mot[cle] = (g, cib, w, k, m0, m1, cible)
        for (i0, i1), (g, cib, w, k, m0, m1, cible) in par_mot.items():
            loc = rampe(g, i0, i1)
            for n in cib:
                gains[n] = np.minimum(gains[n], loc * gains[n])
            fait += 1
            rapport.append({"passe": it, "mot": w["texte"], "debut": w["debut"], "critere": k, "marge_master": round(m0, 1),
                            "marge_avant": round(m1, 1), "cible": round(cible, 1), "couches": list(cib),
                            "gain_db": round(float(20 * np.log10(max(g, 1e-6))), 1)})
        if not fait:
            break
    tot = {n: design[n] * gains[n][:, None] for n in noms}
    finale = []
    s2 = sum(tot.values())
    M = {k: (marges(dv, anc), marges(dv, anc + f(s2))) for k, (f, dv, anc) in esp.items()}
    for j, w in enumerate(MX.MOTS["mots"]):
        finale.append({"mot": w["texte"], "debut": w["debut"],
                       **{f"marge_{k}_master": round(M[k][0][j][0], 1) for k in esp}, **{f"marge_{k}_design": round(M[k][1][j][0], 1) for k in esp}})
    return tot, gains, rapport, finale


# ── données dérivées ────────────────────────────────────────────────────────
SEC_S1 = MX.SEC["s1"]["segments_s"]
GOUTTE = [None]


def segments_vitesse(seuil=2.5):
    v = np.array([p["v"] for p in MX.PR]); t = np.array([p["t"] for p in MX.PR])
    on = v > seuil
    seg, i = [], 0
    while i < len(v):
        if on[i]:
            j = i
            while j < len(v) and on[j]:
                j += 1
            seg.append((round(float(t[i]), 3), round(float(t[j - 1]), 3)))
            i = j
        else:
            i += 1
    return seg


SEGMENTS_V = segments_vitesse()


def main(avec_mp4=True):
    STEMS_OUT.mkdir(exist_ok=True)
    print("0. base : les quatre stems du master")
    stems = {n: labo.lire(SON / "stems" / f"{n}.wav") for n in BASE}
    mixm = labo.lire(SON / "mix.wav")
    ecart = float(np.max(np.abs(sum(stems.values()) - mixm)))
    assert len(mixm) == N and ecart < 1e-4, f"les stems ne redonnent pas son/mix.wav ({ecart})"
    # sur « Vokıo », la plume REMPLACE le stylo du master (2e revue 27/09 : deux stylos pour un geste, le stylo du stem sfx
    # comblait les creux d'encre de la plume) ; c'est le seul son du stem sfx sur ce geste, nul avant et après
    a_s, b_s = STYLO_RETIRE
    autres = [c["id"] for c in CU["cues"] if (c.get("stem") == "sfx" or c.get("piste") == "sfx") and c["id"] != "stylo"
              and c["t"] < b_s and (c.get("fin") or c["t"] + 0.5) > a_s]
    assert not autres, f"d'autres sons du stem sfx tombent sur le mot : {autres}"
    i_a, i_b = int(round(a_s * SR)), int(round(b_s * SR))
    assert not np.any(stems["sfx"][i_a - int(0.05 * SR):i_a]) and not np.any(stems["sfx"][i_b:i_b + int(0.05 * SR)]), \
        "le stem sfx n'est pas nul aux bords de la fenêtre du stylo"
    stems["sfx"] = stems["sfx"].copy()
    stems["sfx"][i_a:i_b] = 0.0
    duck = voix_presente(stems["dialogue"])
    coupe = coupe_film()
    print("1. ambiance"); amb = ambiance(duck)
    print("2. point"); pt = point(duck)
    pv = presence_voix(duck)
    print("3. écriture"); ecr = hors_ligne_sous_voix(ecriture(), pv)
    print("4. objets"); obj = hors_ligne_sous_voix(objets(stems["sfx"]), pv)
    print("5. halo"); hal = halo(stems["nappe"], stems["signature"], duck, coupe)
    design = {"ambiance": amb, "point": pt, "ecriture": ecr, "objets": obj, "halo": hal}
    for k in design:
        design[k] = design[k] * coupe[:, None]
    print("6. la voix d'abord : rattrapage mot par mot")
    design, g_ratt, ratt, finale = rattrapage(stems, design)
    for r in ratt:
        print(f"   {r}")
    for k in ("bande", "K"):
        pire = min(finale, key=lambda d: d[f"marge_{k}_design"])
        print(f"   marge minimale ({k}) : {pire}")
    print("7. master : un gain, le limiteur à crête vraie de mix.py")
    somme = sum(stems.values()) + sum(design.values())
    mix, G, g_lim, red = MX.masteriser(somme)
    tous = {**stems, **design}
    finals = {k: v * S.gain(G) * g_lim[:, None] for k, v in tous.items()}
    for k, v in finals.items():
        S.ecrire24(STEMS_OUT / f"{k}.wav", v)
    S.ecrire24(ICI / "mix-design.wav", mix)
    shutil.copyfile(ICI / "mix-design.wav", SORTIE_WAV)
    m = labo.mesurer(ICI / "mix-design.wav")
    print(f"   {m}, gain {G:+.2f} dB (sur les stems déjà masterisés), réduction max {red:.2f} dB")
    red_db = -20 * np.log10(g_lim)
    mord = np.nonzero(red_db > 0.05)[0]
    instants_limiteur = sorted({round(float(i / SR), 2) for i in mord[::max(1, len(mord) // 40)]}) if len(mord) else []
    print(f"   le limiteur mord (> 0,05 dB) à : {instants_limiteur[:20]}")
    rapport = {"variante": "sound design", "base": "son/stems (master du 27/09, somme = son/mix.wav, écart max "
               f"{ecart:.1e})", "gain_supplementaire_db": round(G, 3), "reduction_limiteur_max_db": round(red, 2),
               "limiteur_part_du_temps_sup_1_db": round(float(np.mean(red_db > 1.0)), 4),
               "limiteur_instants_sup_0_05_db": instants_limiteur, "mesure": m,
               "base_modifiee": {"sfx": f"le stylo du master (41,50 → 42,20) est retiré sur [{STYLO_RETIRE[0]} ; {STYLO_RETIRE[1]}] : "
                                        "sur « Vokıo », la plume de la variante le remplace"},
               "niveaux": NIV, "duck_db": DUCK_DB, "choix_des_prises": CHOIX, "rattrapage_voix": ratt,
               "marges_voix_finales": finale, "cues": sorted(CUES, key=lambda c: c["t"])}
    (ICI / "cues-design.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=lambda o: str(o) if isinstance(o, Path) else float(o)))
    if avec_mp4:
        print("8. MP4 : la vidéo copiée telle quelle, la nouvelle piste son")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VIDEO), "-i", str(SORTIE_WAV), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(SORTIE_MP4)],
                       check=True)
        print(f"   {SORTIE_MP4}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-mp4", action="store_true")
    main(avec_mp4=not ap.parse_args().sans_mp4)
