#!/usr/bin/env python3
"""Variante « MUSIQUE » de la bande son du showcase « Le point sur le i » (27/09) : une vraie musique originale qui porte
le film, construite sur la signature la · sol · ré, en ré majeur, calée sur la grille du film.

    python3 son/riche-musique/mix_riche_musique.py            partition + mix + master + MP4 (+ couches/ pour le contrôle)
    python3 son/riche-musique/mix_riche_musique.py --essai    rien n'est écrit hors de riche-musique/ (réglages)

NE TOUCHE NI son/mix.wav NI assets/son/mix.wav : tout s'écrit dans son/riche-musique/ et dans les deux livrables
    /root/vokio-uploads/videos/showcase/point-solaire-bande-son-musique.wav
    /root/vokio-uploads/videos/showcase/le-point-sur-le-i-son-musique.mp4   (vidéo copiée telle quelle, -c:v copy)

Entrées : les stems du master validé AVANT son limiteur (stems-avant-limiteur/*.npy, refaits en mémoire par
stems_avant_limiteur.py et vérifiés contre son/stems/*.wav : voix, tonalité, touchers « ré courts », vibreur, raccroché,
signature, au gain du master validé) et les données du film (donnees/*.json). La nappe de verre est remplacée par la
musique : même rôle, harmonie réécrite. Un seul limiteur, celui du nouveau master (relecture 27/09, défaut 4 : relire
son/stems/*.wav, qui portent déjà la courbe du limiteur validé, limitait deux fois les attaques du sol et du ré).

LA GRILLE. Un temps = 23 images = 0,766667 s (78,26 BPM), mesures de 4 temps, calée sur le contact du ré (42,90 = temps
56, premier temps de la mesure 14). Elle n'est pas plaquée : le film y tombe déjà. Les trois touchers d'heures sont les
temps 27, 28, 29 ; l'agenda monte au temps 24 (18,367) ; « -tion » tombe au temps 43 (32,933, voyelle à 32,955) ; le
film commence au temps 0 (−0,033 s). Toute position de note est un temps de la grille ou un événement du film.

L'IDÉE. Le motif la · sol cherche sa troisième note pendant tout le film. La basse le chante : la (la quinte de la
sonnerie, la tonalité à 440 Hz) · sol (le décroché : sol2 qui entre en 0,6 s avec les cordes) · si (le doute, mesure 3)
; puis la · sol · si encore sous l'agenda (mesures 5-7) ; la · sol à « confirmation » ; quand la plume écrit le
rendez-vous, la signature le dit une première fois (la 25,40 · sol 25,64) et la musique se tait pour lui, sans lui
donner de ré (deuxième relecture 27/09, défaut 1) ; pendant le SMS, le verre le rejoue, seul, avec une mauvaise fin (la
· sol · mi) ; et sur le logo, la basse descend la · sol · RÉ (mesures 12-13-14) pendant que la signature le dit en 0,6
s. L'accord de ré majeur (la tonique) n'est JAMAIS joué avant le logo : tout l'appel vit sur IV, V, vi, ii ; et dans la
mesure qui précède le logo, aucun ré n'est frappé (marimba en si4, montée de harpe sans ré). Sur le logo, ni les cordes
ni la harpe ne jouent ré5 ni ré6 (défaut 3) : la résonance du ré reste celle de la signature.

Les « ré courts » (touchers d'heures) restent tels quels ; ils deviennent des notes de la musique : le marimba entre
avec « neuf » en ré5, à l'unisson (octave) du toucher, et chaque toucher fait entrer un instrument (neuf : marimba ;
dix : basse rythmique + grosse caisse ; onze : shaker). Le vibreur (ré3) tombe sur l'accord de la sus4 qui le contient.
La grosse caisse est accordée sur la basse de l'accord (mi1 · sol1 · la1 · si1, ré2 au logo ; défaut 4).

L'ARC. Sonnerie : quinte sur la (la tonalité, avec la3 et mi4 qui passent sur un téléphone) et un cœur feutré à 78
battements (tapotements 330 Hz et 600-1 500 Hz), coupés tous deux en 40 ms au décroché (défaut 5). Décroché : les cordes
et la basse (sol2) entrent en 1,8 et 0,6 s sous le la · sol du stem signature, la pédale de la (verre frotté) prend le
relais de la ligne. L'agenda monte : quatre notes de harpe. Dans les trois vraies pauses de l'appel (18,4-19,8,
24,9-26,2, 33,0-34,0), la musique RÉPOND : le bus s'avance (jusqu'à +5 dB, rampes de 0,45 s), et la harpe répond à «
confirmation. » (temps 43,5) ; dans celle de « c'est parfait. », c'est la plume qui répond (la · sol) : le bus ne s'y
avance que de 2 dB, et c'est un arrêt. Neuf-dix-onze : le pouls entre et monte (+4 dB jusqu'à « -tion », doubles-croches
aux mesures 9-10, cymbale inversée vers « -tion ») ; un arrêt composé sous « c'est parfait » et la plume (ni grosse
caisse ni marimba sur les temps 32 à 33,5, ni shaker ni basse sur le 33,5, la basse du temps 32 éteinte à 25,31 ; tout
reprend au temps 34). « Super, merci » : le marimba se pose en noires (ré · si · la · sol). Raccroché : tout coupé en 5
ms, zéros. SMS (la levée) : le verre seul pour le motif (temps 50-51,5), puis crescendo et harpe qui monte ; au temps
55, la CLAIRIÈRE : plus rien n'est frappé, le bus tombe de 14 dB en 0,12 s, les cordes se réduisent à sol3 · si3, et le
la · sol de la signature sonne seul ; le souffle (ré majeur à l'envers, 0,35 s) et une cymbale inversée courte ne
partent qu'après le sol. Ré : ré majeur plein, arpège de harpe une double-croche après le ré, fondu 45,30 → 46,70,
zéros.

LA VOIX. Deux groupes : le LIT (cordes, pédale, réverbe : ce qui tient) et le POULS (tout ce qui frappe). Détecteurs de
présence de la voix (même principe que mix.gain_ducking) LENTS : le lit ne relâche que dans les vraies pauses (tenue
0,60 s : 18,4-19,8, 24,9-26,2, 33,0-34,0), et le pouls ne bouge jamais de plus de 1 dB en 50 ms (attaque τ 0,20 s,
anticipation 0,30 s). La part du lit qui suit la voix ne descend qu'à pente bornée, en anticipant (limiter_descente :
0,55 dB par 50 ms en large bande, 0,80 sur 1-4 kHz ; défaut 2) : le lit arrive au fond en fondu, pas en 50 ms. Lit : −7
dB sous la voix, −10 dB sur 1-4 kHz ; pouls : −3 dB, −10 dB sur 1-4 kHz et −6 dB sous 160 Hz (égaliseur dynamique STFT,
τ 0,55 s : le grave coûte à la voix en sonie sans s'entendre sur un téléphone). Puis rattrapages mot par mot SUR LE LIT
SEUL (voix ≥ 11 LU au-dessus de tout le reste, ≥ 12 dB sur 1-4 kHz, mesurés sur la somme des signaux, termes croisés
compris), rampes de 0,30 s, creux voisins de moins de 0,4 s fusionnés : le rythme n'est jamais touché par le fader,
l'arrangement lui fait de la place (« dix » plus léger, arrêt sous « c'est parfait », et toute note du pouls qui attaque
DANS un mot jouée à 0,8, sauf les notes composées sur un événement). Sous la · sol · ré, la musique s'efface de 11 dB, 8
ms avant chaque attaque, puis revient (τ 0,2 s après le la et le sol, 0,6 s après le ré) : le ré garde son attaque et
reste l'instant le plus fort.

LE TÉLÉPHONE. Les Reels s'écoutent sur un haut-parleur qui ne rend rien sous 250 Hz : la basse est additive (la
fondamentale ne porte que ~17 % de l'énergie, les harmoniques 3 à 8 portent la note), monophonique (chaque note s'éteint
12 ms après l'attaque de la suivante) ; la grosse caisse a un « toc » 300 → 240 Hz et un maillet 4-6 kHz, son corps est
accordé sur la basse de l'accord ; l'accord du logo s'ouvre vers le haut (la5 ajouté, ré5 retiré). Sous les mots, la
musique reste au niveau de la nappe validée : chaque LU de plus s'y prendrait sur la marge de la voix (voir
controle_musique.py, T).

L'ÉCHANGE DU PRÉNOM (28/09). Le film gagne une mesure (92 images, 147 200 échantillons) à l'image 758 (25,2667 s, le
temps 33) : la question de l'agente et la réponse de l'appelant. La partition reste écrite sur la grille du film d'avant
et se place par la chronologie de son/dialogue.json (outils/chronologie.py) : l'ARRÊT COMPOSÉ (temps 32 → 34 : ni grosse
caisse ni marimba, le lit seul) dure une mesure de plus (24,50 → 29,10), le sol majeur de la mesure 8 et la pédale de la
TIENNENT (leurs oscillations font un nombre entier de cycles dans la mesure insérée : pas de raccord, et après l'insertion
les notes redonnent celles d'avant, décalées), l'arc du bus est tenu, la pause « prénom ? » → « C'est pour Florian. » ne
lève le bus que de 2 dB (règle de l'arrêt, comme pour la plume), le pouls reprend au temps 38 (29,10), 0,14 s avant
« Parfait, » comme avant. Aucune note nouvelle. Le la · sol de la plume (stem signature, mix.py T["la_rdv"]) finit
l'écriture du nom (sol sur ecriture_fin, 28,933) : il tombe dans l'arrêt (controle_plume()).

ELEVENLABS MUSIC. Cinq prises à composition_plan dont les sections suivent le film (el_musique.py ; 3 et 4 avec le plan
harmonique imposé), évaluées par evaluer_el.py (el/evaluation.json) : tempo tenu à 77,9 BPM pour trois d'entre elles,
mais aucune ne tient les accords (43 à 68 % du chroma dans l'accord prévu, 87 % pour cette partition), la basse ne les
suit pas, et aucune ne culmine sur le logo. Non retenues : toute la musique est de la synthèse numpy (instruments.py).
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
sys.path.insert(0, str(SON))
sys.path.insert(0, str(ICI))
import labo  # noqa: E402
import signature as S  # noqa: E402
import mix as MX  # noqa: E402  (données et outils : rien ne se recalcule à l'import)
import instruments as I  # noqa: E402
import mesures as ME  # noqa: E402
sys.path.append(str(PROJET / "outils"))
import chronologie as CH  # noqa: E402

SR = labo.SR
N = MX.N
EV, T, DUREE = MX.EV, MX.T, MX.DUREE
FIN_SON = MX.FIN_SON
UPLOADS = Path("/root/vokio-uploads/videos/showcase")
VIDEO = UPLOADS / "le-point-sur-le-i.mp4"
SORTIE_MP4 = UPLOADS / "le-point-sur-le-i-son-musique.mp4"
SORTIE_WAV = UPLOADS / "point-solaire-bande-son-musique.wav"
STEMS_OUT = ICI / "stems"
STEMS_AV = ICI / "stems-avant-limiteur"          # stems du master validé, gain compris, SANS sa courbe de limiteur
IMG = Path("/tmp/claude-0/-root/5cdc3174-18c1-52f2-a7e6-50c04cd57657/scratchpad/variantes/musique")

# ── la grille ───────────────────────────────────────────────────────────────
BEAT = 23 / 30
# INSERTIONS DE TEMPS (28/09, l'échange du prénom) : la partition est ÉCRITE sur la grille du film d'avant (47 s) et
# PLACÉE dans le film actuel par la chronologie de son/dialogue.json (outils/chronologie.py, la même règle que l'image et
# le dialogue). Un temps n de la grille tombe à CHRONO.decaler(T0 + n·BEAT) : les temps d'avant le pivot ne bougent pas,
# ceux d'après glissent de la durée insérée (une mesure = 4 temps = 92 images : la grille reste la grille). T0 est pris
# sur le ré ramené au film d'avant et posé sur son image (1287 : 42,90 s) : les instants du JSON n'ont que 6 décimales
# (45,966667 − 3,0666667 = 42,9000003), et 3·10⁻⁷ s de trop sur T0 décalaient d'un échantillon quelques notes
# humanisées. Voir tb(), arc_bus() et reponses() ; sans insertion, tout est l'identité (42,90 est déjà sur l'image).
CHRONO = CH.charger(MX.DIA)
T0 = round(CHRONO.vers_base(EV["signature_re_contact"]["t"]) * 30) / 30 - 56 * BEAT


def tb(n):
    """Instant (film actuel) du temps n de la grille (n peut être fractionnaire : 0,5 = croche, 0,25 = double)."""
    return CHRONO.decaler(T0 + n * BEAT)


for _n, _nom in ((27, "contact_neuf"), (28, "contact_dix"), (29, "contact_onze"), (56, "signature_re_contact")):
    assert abs(tb(_n) - EV[_nom]["t"]) < 1e-4, (_nom, tb(_n), EV[_nom]["t"])
assert abs(tb(24) - EV["agenda_monte"]["t"][0]) < 0.005
assert abs(tb(43) - T["resolution"]) < 0.025
T_DEC, T_RAC, T_VIB = T["decroche"], T["raccroche"], T["vibreur"]
S0, S1 = EV["silence_numerique"]["t"]
# le la · sol de la plume (son/mix.py, cloche-la-rdv et cloche-sol-rdv : evenements.ecriture_debut, puis + l'écart
# signature_sol − signature_la) : 25,40 et 25,64 s, entre les temps 33 et 33,5. Deuxième relecture 27/09, défaut 1 : la
# partition l'ignorait ; c'est le motif, dit une première fois par la signature, et il ne reçoit pas sa troisième note
T_PLUME_LA = T["la_rdv"]          # mix.py : evenements.ecriture_debut, ou (28/09) le demi-temps après « Florian. »
T_PLUME_SOL = T["sol_rdv"]

CUES = []


def cue(couche, t, quoi, source, **extra):
    CUES.append({"couche": couche, "t": round(float(t), 4), "image": int(round(t * 30)), "quoi": quoi, "source": source, **extra})


# ── harmonie : un accord par mesure (parfois deux), jamais ré majeur avant le logo ──────────────────────────
# (instant, nom, voicing des cordes en MIDI {note: poids}, basse MIDI)
ACCORDS = [
    (T_DEC, "Gadd9", {55: 0.8, 59: 1.0, 62: 0.9}, 43),
    (tb(8), "Gmaj9", {59: 1.0, 62: 0.9, 66: 0.7}, 43),
    (tb(12), "Bm7", {54: 0.9, 59: 1.0, 62: 0.9}, 47),
    (tb(16), "Em9", {55: 0.8, 59: 1.0, 62: 0.9, 66: 0.6}, 40),
    (tb(20), "Asus4", {57: 0.9, 62: 1.0, 64: 0.8}, 45),
    (tb(22), "A", {57: 0.9, 61: 1.0, 64: 0.8}, 45),
    (tb(24), "G", {55: 0.8, 59: 1.0, 62: 0.9}, 43),
    (tb(28), "Bm7", {54: 0.9, 59: 1.0, 62: 0.9}, 47),
    # mesure 8 : sans sol4 (deuxième relecture 27/09, défaut 1 : les cordes doublaient à l'unisson le sol de la plume,
    # 25,64 s) ; le même voicing que la mesure 6
    (tb(32), "G", {55: 0.8, 59: 1.0, 62: 0.9}, 43),
    (tb(36), "Em9", {55: 0.8, 59: 1.0, 62: 0.9, 66: 0.6, 64: 0.4}, 40),
    (tb(40), "Asus4", {57: 0.9, 62: 1.0, 64: 0.8, 69: 0.5}, 45),
    (tb(42), "A", {57: 0.9, 61: 1.0, 64: 0.8, 69: 0.5}, 45),
    (tb(43), "Gadd9", {55: 0.8, 59: 1.0, 62: 0.9, 67: 0.5}, 43),
    (tb(48), "Asus4", {57: 0.9, 62: 1.0, 64: 0.8, 69: 0.7, 74: 0.5}, 45),
    (tb(50), "A", {57: 0.9, 61: 1.0, 64: 0.8, 69: 0.7, 73: 0.5, 76: 0.4}, 45),
    (tb(52), "G", {55: 0.9, 59: 1.0, 62: 0.9, 67: 0.8, 71: 0.6, 74: 0.5}, 43),
    # la clairière (temps 55) : sol3 · si3 seuls, à −9 dB ; ni ré (la note que le motif cherche) ni sol4 (l'unisson du
    # sol de la signature)
    (tb(55), "G/clairière", {55: 0.32, 59: 0.35}, 43),
    # ré majeur ouvert vers le haut (relecture 27/09, défaut 3) : ré3 et fa#3 allégés, la4 · fa#5 renforcés ; le grave
    # du logo, c'est la basse ; les cordes portent le plein là où un téléphone l'entend. Sans ré5 (deuxième relecture,
    # défaut 3 : à l'unisson du ré de la signature, il en absorbait la résonance) : son poids passe sur la4 et fa#5, et
    # ré4 descend de 1,0 à 0,75 (son harmonique 2 est à 587 Hz, le ré de la signature) ; la5 (880 Hz) entre à 0,45 : le
    # logo garde son plein au téléphone (contrôle T, ≥ nappe + 2 LU) sans rien remettre à 587 ni à 1 175 Hz
    (tb(56), "D", {50: 0.45, 54: 0.6, 57: 0.85, 62: 0.75, 66: 0.9, 69: 1.0, 78: 0.6, 81: 0.45}, 38),
]
# notes du marimba par accord (grave → aigu) ; motif de croches : indices dans cette liste
MARIMBA = {"G": [67, 71, 74, 69], "Gadd9": [67, 71, 74, 69], "Bm7": [66, 71, 74, 69], "Em9": [64, 67, 71, 74],
           "Asus4": [69, 74, 76, 81], "A": [69, 73, 76, 81]}
MOTIF_CROCHES = [2, 0, 2, 1, 3, 1, 2, 0]      # temps 1, 2, 4 sur l'indice 2 (ré5 sous G et Bm7 : l'octave des touchers)


def accord_a(t):
    a = ACCORDS[0]
    for x in ACCORDS:
        if x[0] <= t + 1e-6:
            a = x
    return a


def note_du_corps(t):
    """La note (MIDI) où se pose le corps de la grosse caisse frappée à l'instant t : la basse de l'accord, une octave
    plus bas tant qu'elle reste au-dessus de 40 Hz (mi1 41,2 · sol1 49,0 · la1 55,0 · si1 61,7), sinon la basse elle-même
    (ré2 73,4 Hz au logo, à l'unisson de la basse : ré1 36,7 Hz ne s'entend nulle part et coûte de la marge au ré).
    Deuxième relecture 27/09, défaut 4 : accordée sur sol1 partout, la grosse caisse posait un sol sous si mineur, mi
    mineur et la ; et son glissando grave la mettait un demi-ton trop haut."""
    m = accord_a(t + 0.01)[3]
    return m - 12 if float(I.hz(m - 12)) >= 40.0 else m


# ── outils de pose ──────────────────────────────────────────────────────────
def piste():
    return np.zeros((N, 2))


ATTAQUES = []          # toutes les notes posées (couche, instant) : le contrôle S y cherche ce qui frappe près de la plume
_COUCHE = [None]


def poser(p, mono, t, db=0.0, pan=0.0):
    if _COUCHE[0]:
        ATTAQUES.append({"couche": _COUCHE[0], "t": round(float(t), 4)})
    i = int(round(t * SR))
    S.ajouter(p, S.panner(np.asarray(mono) * S.gain(db), pan), i)
    return p


JIT = np.random.default_rng(2709)
VEL_SOUS_MOT = 0.80     # −1,9 dB : une note du pouls qui attaque DANS un mot est jouée plus doucement (le musicien joue
                        # sous la voix) ; les notes composées sur un événement (neuf, dix, onze, -tion, ré) ne bougent pas


def sous_un_mot(t, avant=0.03):
    """Vrai si l'instant t tombe dans un mot du dialogue (donnees/mots.json), 30 ms d'avance comprises."""
    return any(w["debut"] - avant <= t <= max(w["fin"], w["debut"] + 0.12) for w in MX.MOTS["mots"])


def humain(t, ms=3.0):
    return t + JIT.normal(0, ms / 1000)


def poids_plan(t, plan):
    """plan = [(t0, fondu, {note: poids})] : poids de chaque note au cours du temps, fondus enchaînés à puissance
    constante ; une note commune à deux accords ne bouge pas (a² = a0²·cos² + a1²·sin²)."""
    notes = sorted({k for _, _, acc in plan for k in acc})
    w = {k: np.zeros_like(t) for k in notes}
    avant = {}
    for (t0, d, acc) in plan:
        p = np.clip((t - t0) / d, 0, 1)
        s = np.sin(np.pi * p / 2) ** 2
        ici = t >= t0
        for k in notes:
            a0, a1 = avant.get(k, 0.0), acc.get(k, 0.0)
            w[k][ici] = np.sqrt(a0 ** 2 * (1 - s[ici]) + a1 ** 2 * s[ici])
        avant = acc
    return w


def fondu_cos(t, t0, d):
    return MX.fondu_cos(t, t0, d)


RELACHE_QUINTE = 0.040           # s : sortie de la quinte au décroché (voir drone_sonnerie ; stems_amont.py la règle)


# ── 1. couches ──────────────────────────────────────────────────────────────
def drone_sonnerie():
    """s1, tension retenue : quinte à vide la1 · mi2 · la2 · la3 · mi4 · mi5 (la = la tonalité, la dominante de ré), sinus +
    harmoniques 2 à 5 (−18, −14, −20, −26 dB), qui gonfle de 0 à 4,2 s (+7 dB) et respire au temps (± 1,2 dB, 1,3 Hz) ;
    coupée en 40 ms au décroché. Relecture 27/09 (défaut 6) : la1 de 1 à 0,6, la3 de 0,12 à 0,8, mi4 et mi5 ajoutés (0,55 et
    0,12), harmoniques 3 à 5 ajoutées : au-dessus de 250 Hz, la quinte existe aussi sur un haut-parleur de téléphone.
    RELACHE_QUINTE (28/09) : durée de la rampe cosinus de sortie au décroché ; 0,040 = la version 2 livrée, à l'échantillon
    près (la normalisation se fait toujours sur la version coupée en 40 ms) ; son/stems_amont.py la passe à 0,35 s pour le
    mix hybride (la coupe de 40 ms laissait un trou de −27 dB en 30-300 Hz entre la quinte et l'entrée du sol2)."""
    rel = float(RELACHE_QUINTE)
    t = np.arange(int(round((T_DEC + max(0.05, rel + 0.01)) * SR))) / SR
    y = np.zeros_like(t)
    harm = ((2, 0.12, 0.5), (3, S.gain(-14), 1.1), (4, S.gain(-20), 2.0), (5, S.gain(-26), 2.9))
    for m, a in ((33, 0.6), (40, 0.4), (45, 0.6), (57, 0.8), (64, 0.55), (76, 0.12)):
        f = float(I.hz(m))
        y += a * (np.sin(2 * np.pi * f * t) + sum(g_ * np.sin(2 * np.pi * h * f * t + ph) for h, g_, ph in harm))
    souffle = S.gain(-7 + 7 * np.clip(t / T_DEC, 0, 1) ** 1.5 + 1.2 * np.sin(2 * np.pi * (1 / BEAT) * (t - T0)))
    y *= souffle
    y[:int(0.4 * SR)] *= S.rampe_cos(int(0.4 * SR))
    k0 = int(round(T_DEC * SR)); k = int(0.040 * SR)
    ref = y[:int(round((T_DEC + 0.05) * SR))].copy()            # la version coupée en 40 ms : sa crête fixe le niveau
    ref[k0:k0 + k] *= S.rampe_cos(k)[::-1]
    ref[k0 + k:] = 0
    kr = int(rel * SR)
    y[k0:k0 + kr] *= S.rampe_cos(kr)[::-1]
    y[k0 + kr:] = 0
    p = piste()
    S.ajouter(p, S.panner(y / np.max(np.abs(ref)), 0.0), 0)
    cue("drone", 0.0, f"quinte la1 · mi2 · la2 · la3 · mi4, gonfle jusqu'au décroché, sortie en {rel * 1000:.0f} ms",
        "0 → evenements.decroche")
    return p


def coeur_sonnerie():
    """Battements feutrés sur les temps 1 à 5 (0,733 → 3,80), à 78 battements par minute : un cœur qui attend. Coupé
    au décroché comme la quinte, en 40 ms (deuxième relecture 27/09, défaut 5 : le « dub » du 5e battement, à 4,06 s,
    résonnait après le clic du décroché)."""
    _COUCHE[0] = "coeur"
    p = piste()
    for i, n in enumerate(range(1, 6)):
        t = tb(n)
        poser(p, I.coeur(0.5 + 0.08 * i, graine=i), t, db=-6 + 1.2 * i)
        cue("coeur", t, f"battement {i + 1}", f"grille, temps {n}")
    k0 = int(round(T_DEC * SR)); k = int(0.040 * SR)
    p[k0:k0 + k] *= S.rampe_cos(k)[::-1, None]
    p[k0 + k:] = 0
    cue("coeur", T_DEC, "coupé en 40 ms, zéros ensuite", "evenements.decroche")
    return p


def cordes():
    """Ensemble à cordes : trois voix par note (−7 / 0 / +7 cents), pan étalé par note, fondus enchaînés entre accords ;
    entrée délicate en 1,8 s au décroché, coupe au raccroché, retour en 1,2 s à la mesure 12, ré majeur en 0,5 s sur le
    ré. Passe-haut 90 Hz, passe-bas 2,6 kHz (feutré), puis 5,2 kHz sur la fin (le plein)."""
    t = np.arange(N) / SR
    plan = []
    for k, (t0, nom, voic, _) in enumerate(ACCORDS):
        fondu = 1.8 if k == 0 else (1.2 if nom == "Asus4" and t0 > T_RAC else
                                    (0.5 if nom == "D" else (0.3 if nom == "G/clairière" else 0.45)))
        if t0 > T_RAC and not any(p_[0] > T_RAC for p_ in plan):
            plan.append((T_RAC, 0.005, {}))       # le raccroché : l'accord s'arrête ; la mesure 12 repart de rien
        plan.append((t0, fondu, voic))
    w = poids_plan(t, plan)
    out = piste()
    for m, wm in w.items():
        act = np.nonzero(wm > 1e-6)[0]
        if not len(act):
            continue
        a, b = act[0], act[-1] + 1
        tt = t[a:b]
        f = float(I.hz(m))
        pan_note = np.clip((m - 60) / 18, -0.6, 0.6)
        for iv, (c, dp) in enumerate(((-7, -0.25), (0, 0.0), (7, 0.25))):
            v = I.voix_corde(f, tt, graine=[int(m), iv], desaccord_cents=c, chrono=CHRONO or None)
            out[a:b] += S.panner(v * wm[a:b] / np.sqrt(3), np.clip(pan_note + dp, -0.8, 0.8))
    lp_debut = MX.ffmpeg_filtre(out, "highpass=f=90,lowpass=f=2600,lowpass=f=4000")
    lp_fin = MX.ffmpeg_filtre(out, "highpass=f=90,lowpass=f=5200")
    ouv = fondu_cos(t, tb(52), BEAT * 4)[:, None]
    out = lp_debut * (1 - ouv) + lp_fin * ouv
    for (t0, nom, voic, _) in ACCORDS:
        cue("cordes", t0, f"{nom} : {' · '.join(str(m) for m in voic)}", "grille" if abs((t0 - T0) / BEAT - round((t0 - T0) / BEAT)) < 1e-6 else "evenements.decroche")
    return out


def verre_frotte(t, f, rng, graine_bruit):
    """mix.voix_verre (verre frotté : phase intégrée, dérive ±2 cents à 0,2 Hz, trémolo ±0,6 dB à 1,5 Hz, frottement de
    bruit rose en [2f ; 6f] modulé par la phase, −32 dB sous la note), lu à travers les insertions de temps (28/09) : la
    note est TENUE pendant chaque mesure insérée qu'elle couvre. Son horloge est celle du film d'avant ; dans la mesure,
    dérive, trémolo et phase font un nombre entier de cycles (chronologie.cycles_entiers, phase_entiere) ; le frottement
    est le bruit d'avant, dans lequel on insère un bruit neuf du même spectre, en fondus de 50 ms à puissance constante
    qui partent de sa suite naturelle et rejoignent son amorce : avant le pivot, la note d'avant à l'octet ; après, la
    même, décalée. Sans insertion couverte : mix.voix_verre tel quel."""
    i0, n = int(round(t[0] * SR)), len(t)
    zones = [(int(round(d * SR)) - i0, int(round(fz * SR)) - i0) for d, fz in CHRONO.zones()]
    zones = [(a, b) for a, b in zones if 0 < a and b < n]
    if not zones:
        return MX.voix_verre(t, f, rng, graine_bruit=graine_bruit)
    ph0, ph1, ph2 = rng.uniform(0, 2 * np.pi, 3)
    # la note du film d'avant, telle que mix.voix_verre la rend (même tirage, même longueur) : son bruit et sa norme
    nb = n - sum(b - a for a, b in zones)
    t0 = np.arange(i0, i0 + nb) / SR
    fi0 = f * 2 ** (2.0 * np.sin(2 * np.pi * 0.2 * t0 + ph1) / 1200)
    phi0 = ph0 + 2 * np.pi * np.concatenate([[0.0], np.cumsum(fi0[:-1])]) / SR
    y0 = np.sin(phi0) + 0.08 * np.sin(2 * phi0) + 0.03 * np.sin(3 * phi0)
    brut0 = S.passe_bande(labo.bruit_rose(nb + 8192, graine=graine_bruit)[4096:4096 + nb], 2 * f, 6 * f, front=max(20.0, f / 4))
    br0 = brut0 * (0.5 + 0.5 * np.sin(phi0)) ** 2
    norme = S.gain(-32.0) * np.sqrt(np.mean(y0 ** 2)) / (np.sqrt(np.mean(br0 ** 2)) + 1e-12)
    # la note du film actuel
    tb = CHRONO.vers_base(t)
    cents = 2.0 * np.sin(2 * np.pi * 0.2 * tb + 2 * np.pi * CHRONO.cycles_entiers(0.2, t) + ph1)
    fi = CHRONO.phase_entiere(f * 2 ** (cents / 1200), i0)
    phi = ph0 + 2 * np.pi * np.concatenate([[0.0], np.cumsum(fi[:-1])]) / SR
    y = np.sin(phi) + 0.08 * np.sin(2 * phi) + 0.03 * np.sin(3 * phi)
    X = int(0.050 * SR)
    u = np.arange(X) / X
    morceaux, k0, dern = [], 0, 0
    for j, (a, b) in enumerate(zones):
        k = a - dern + k0                         # indice, dans la note d'avant, du pivot de cette insertion
        L = b - a
        neuf = S.passe_bande(labo.bruit_rose(L + 8192, graine=graine_bruit + 1 + j)[4096:4096 + L], 2 * f, 6 * f,
                             front=max(20.0, f / 4))
        neuf *= np.sqrt(np.mean(brut0 ** 2)) / (np.sqrt(np.mean(neuf ** 2)) + 1e-12)
        neuf[:X] = brut0[k:k + X] * np.cos(np.pi / 2 * u) + neuf[:X] * np.sin(np.pi / 2 * u)
        neuf[-X:] = neuf[-X:] * np.cos(np.pi / 2 * u) + brut0[k - X:k] * np.sin(np.pi / 2 * u)
        morceaux += [brut0[k0:k], neuf]
        k0, dern = k, b
    morceaux.append(brut0[k0:])
    brut = np.concatenate(morceaux)
    br = brut * (0.5 + 0.5 * np.sin(phi)) ** 2 * norme
    am = S.gain(0.6 * np.sin(2 * np.pi * 1.5 * tb + 2 * np.pi * CHRONO.cycles_entiers(1.5, t) + ph2))
    return (y + br) * am


def pedale_la():
    """La tonalité devenue pédale (comme la v2) : la4 en verre frotté, qui prend le relais de la ligne qui s'ouvre
    (fondu 4,60 → 6,10, le même que la queue du la dans le stem signature), tenue jusqu'au raccroché : le la est une note
    de tous les accords de l'appel (9e de sol, 7e de si mineur, 11e de mi mineur, fondamentale de la)."""
    i0 = int(round(T["pedale"] * SR)); i1 = int(round(T_RAC * SR)) + int(0.01 * SR)
    t = np.arange(i0, i1) / SR
    rng = np.random.default_rng([77, 1])
    y = verre_frotte(t, 440.0, rng, graine_bruit=4401)
    w = np.sin(np.pi / 2 * np.clip((t - T["pedale"]) / MX.DEC["pedale_fondu"], 0, 1))
    p = piste()
    S.ajouter(p, S.panner(y * w, -0.1), i0)
    cue("pedale", T["pedale"], "la4 440 Hz en verre frotté, fondu 1,5 s, tenu jusqu'au raccroché", "point.json taille (44 px) = mix.T['pedale']")
    return p


def ligne_de_basse():
    """La basse chante le motif : la (drone) · sol (décroché) · si (mesure 3) ; mi · la · sol · si · sol · mi · la · sol ;
    puis la · sol · RÉ sur les mesures 12-13-14. Sol2 au décroché, entré en 0,6 s avec les cordes (relecture 27/09,
    défaut 7 : il était écrit mais jamais joué) ; notes longues jusqu'à « dix » ; ensuite motif rythmique (1er temps
    pointé, « et » du 2, 4e temps à la quinte ; mesure 8 : 1er temps court, sans « et » du 2, la plume passe seule) ;
    croches sur la mesure 13 (la levée) ; ré2 + ré1 sur le logo."""
    _COUCHE[0] = "basse"
    p = piste()
    # entrée délicate au décroché : sol2 (le décroché), attaque 0,6 s, tenu jusqu'au si de la mesure 3
    notes = [(T_DEC, 43, tb(12) - T_DEC, 0.45, "sol : le décroché (attaque 0,6 s)")]
    for n0, m, d in ((12, 47, 4), (16, 40, 4), (20, 45, 4), (24, 43, 4)):
        notes.append((tb(n0), m, d * BEAT, 0.55 + 0.05 * (n0 - 12) / 4, "longue"))
    # dès « dix » : motif rythmique
    # 4e temps : fa#2 sous si mineur, si2 sous sol (sol · si · mi : la basse marche, et aucun ré avant le logo), si2 sous mi
    for n0, m, quinte in ((28, 47, 42), (32, 43, 47), (36, 40, 47)):
        if n0 == 32:
            # mesure 8 : la plume (la 25,40 · sol 25,64) passe seule ; le 1er temps s'éteint à 25,31 (0,9 temps + 0,12 s
            # de relâche) et le « et du 2 » (25,65, dont l'harmonique 4, 392 Hz, doublait le sol) n'est pas joué
            notes += [(tb(n0), m, 0.9 * BEAT, 0.8, "1er temps, court : la plume passe seule")]
        else:
            notes += [(tb(n0), m, 1.5 * BEAT, 0.8, "1er temps"), (tb(n0 + 1.5), m, 0.5 * BEAT, 0.6, "et du 2")]
        notes.append((tb(n0 + 3), quinte, 0.95 * BEAT, 0.65, "4e temps"))
    notes += [(tb(40), 45, 1.5 * BEAT, 0.85, "1er temps"), (tb(41.5), 45, 0.5 * BEAT, 0.65, "et du 2"),
              (tb(42), 45, 0.95 * BEAT, 0.7, "3e temps"),
              (tb(43), 43, T_RAC - tb(43) + 0.02, 0.8, "« -tion » : sol, tenu jusqu'au raccroché")]
    notes.append((tb(48), 45, 4 * BEAT, 0.7, "mesure 12 : la (le SMS)"))
    for k in range(6):
        notes.append((tb(52 + 0.5 * k), 43, 0.45 * BEAT, 0.62 + 0.05 * k, "mesure 13 : croches de sol (la levée)"))
    notes.append((tb(56), 38, FIN_SON - tb(56), 0.75, "logo : ré2"))
    # la basse est MONOPHONIQUE (une corde, un doigt) : une note qui déborderait sur la suivante s'éteint en 25 ms,
    # finie 12 ms après l'attaque de la suivante (avant : 120 ms de chevauchement, deux notes à la fois)
    notes.sort(key=lambda n_: n_[0])
    for j, (t, m, d, vel, quoi) in enumerate(notes):
        duree, rel = d + 0.12, (110 if d > 1 else 60)
        if j + 1 < len(notes) and t + duree > notes[j + 1][0]:
            duree, rel = notes[j + 1][0] - t + 0.012, 25
        y = I.basse(m, duree, attaque_ms=600 if t == T_DEC else 10, relache_ms=rel)
        poser(p, y * vel, t)
        cue("basse", t, f"{quoi} · MIDI {m}", "evenements.decroche" if t == T_DEC else "grille")
    # sous-basse du logo : ré1 36,7 Hz, sinus pur, attaque 15 ms, τ 1,6 s
    tt = np.arange(int((FIN_SON - tb(56)) * SR)) / SR
    sub = np.sin(2 * np.pi * float(I.hz(26)) * tt) * np.exp(-tt / 1.6)
    sub[:int(0.015 * SR)] *= S.rampe_cos(int(0.015 * SR))
    poser(p, sub * 0.06, tb(56))           # 0,35 → 0,06 (défauts 3 et 4) : moins d'énergie sous 60 Hz, moins de crête au ré
    cue("basse", tb(56), "sous-basse ré1 36,7 Hz", "evenements.signature_re_contact")
    return p


def marimba():
    """Le pouls. Entre avec « neuf » (temps 27) : son premier coup est ré5, l'octave sous le toucher ré6 ; croches sur
    les accords jusqu'à « -tion » ; « dix » plus léger (0,35 : la voix y est la plus serrée) ; arrêt composé sur le
    premier temps de la mesure 8 (croches 32 à 33,5 : « c'est parfait », puis le la · sol de la plume) ; noires qui descendent ré · si · la · sol
    sur « Super, merci » (l'appel se pose sur la · sol, sans ré) ; croches de retour pendant le SMS (dès le temps 49),
    SAUF 50 à 51 (le verre y joue le motif seul), ré5 remplacés par si4 dans la mesure 13, coupées dès le temps 54."""
    _COUCHE[0] = "marimba"
    p = piste()
    k = 0

    def coup(n, m, vel, exact=False, pan=None, quoi=""):
        nonlocal k
        t = tb(n) if exact else humain(tb(n), 2.5)
        if not exact and sous_un_mot(t):
            vel *= VEL_SOUS_MOT
        y = I.marimba(m, 1.1, vel, graine=k)
        pan_ = pan if pan is not None else (0.22 if m >= 72 else -0.18)
        poser(p, y * vel, t, pan=pan_)
        if quoi:
            cue("marimba", t, f"{quoi} · MIDI {m}", "grille")
        k += 1

    coup(27, 74, 0.62, exact=True, quoi="entre avec « neuf » : ré5 sous le toucher ré6")
    coup(27.5, 67, 0.45)
    for n0 in range(28, 43, 4):
        nom = accord_a(tb(n0) + 0.01)[1]
        notes = MARIMBA[nom]
        for e in range(8):
            n = n0 + 0.5 * e
            if n >= 43:
                break
            nm = accord_a(tb(n) + 0.01)[1]
            notes = MARIMBA[nm]
            m = notes[MOTIF_CROCHES[e]]
            vel = (0.62 if e % 2 == 0 else 0.46) * (1 + 0.10 * (n0 - 28) / 12)
            exact = n in (28, 29)
            if n in (32, 32.5, 33, 33.5):
                continue                        # arrêt composé : « c'est parfait » (24,41-24,95), puis la plume (25,40 ·
                                                # 25,64) passent seuls ; le marimba reprend au temps 34 (26,03)
            if n == 28:
                vel = 0.35
            coup(n, m, vel, exact=exact, quoi=("« dix » : ré5" if n == 28 else ("« onze » : ré5" if n == 29 else "")))
    for i, (n, m) in enumerate(((43, 74), (44, 71), (45, 69), (46, 67))):
        coup(n, m, 0.55 - 0.05 * i, exact=True, quoi=["« -tion » : ré5", "si4", "la4", "sol4 (l'appel se pose sans ré)"][i])
    for n0 in (48, 52):
        for e in range(8):
            n = n0 + 0.5 * e
            if n < 49 or n >= 54 or 50 <= n < 51.5:
                continue
            nom = accord_a(tb(n) + 0.01)[1]
            m = MARIMBA[nom][MOTIF_CROCHES[e]]
            if n >= 52 and m == 74:
                m = 71                          # mesure 13 : aucun ré frappé avant celui de la signature
            vel = (0.5 + 0.3 * (n - 49) / 6) * (1.0 if e % 2 == 0 else 0.78)
            coup(n, m, vel, quoi=("retour du pouls (SMS)" if n == 49 else ""))
    return p


def harpe():
    """L'agenda qui monte (temps 24, quatre notes) ; une réponse dans la pause après « confirmation. » (temps 43,5) ; la levée : double-croches qui montent sur sol · la · si · mi · fa#
    (sol4 → la6, sans ré : la note que le motif cherche n'arrive qu'avec la signature) pendant les temps 52-54,75 ;
    sur le logo, arpège de ré majeur sans ré (la3 → fa#6) qui part une double-croche APRÈS le ré (le ré garde son
    attaque, et sa résonance)."""
    _COUCHE[0] = "harpe"
    p = piste()
    # l'agenda monte (18,37 → 19,07, temps 24 → 24,9) dans le silence de l'outil : quatre doubles-croches de sol
    # majeur qui montent avec lui, douces
    for i, m in enumerate((67, 71, 74, 79)):
        vel = 0.42 + 0.06 * i
        poser(p, I.harpe(m, 1.8, vel, graine=80 + i) * vel, humain(tb(24 + 0.25 * i), 1.5), pan=-0.3 + 0.2 * i)
    cue("harpe", tb(24), "sol4 · si4 · ré5 · sol5 en doubles-croches : l'agenda monte", "evenements.agenda_monte = temps 24")
    # la réponse (relecture 27/09, défaut 3) : après « confirmation. » (temps 43,5, 33,32 s), si5 · sol5 · ré5 · si4 qui
    # redescendent se poser. Après « c'est parfait. », il n'y en a plus (deuxième relecture, défaut 1) : la réponse, c'est
    # le la · sol de la plume (25,40 · 25,64), que la harpe encadrait et complétait d'un ré5 10 ms après le sol
    for i, m in enumerate((83, 79, 74, 71)):
        vel = 0.50 - 0.04 * i
        poser(p, I.harpe(m, 2.0, vel, graine=95 + i) * vel, humain(tb(43.5 + 0.25 * i), 1.5), pan=0.35 - 0.2 * i)
    cue("harpe", tb(43.5), "réponse : si5 · sol5 · ré5 · si4 (après « -tion »)", "pause 33,05-34,03 (donnees/mots.json), temps 43,5")
    montee = [67, 69, 71, 76, 78, 79, 81, 83, 88, 90, 91, 93]
    for i, m in enumerate(montee):
        n = 52 + 0.25 * i
        vel = 0.45 + 0.4 * i / (len(montee) - 1)
        y = I.harpe(m, 1.6, vel, graine=i)
        poser(p, y * vel, humain(tb(n), 2.0), pan=-0.45 + 0.9 * i / (len(montee) - 1))
    cue("harpe", tb(52), "montée sol4 → la6 en double-croches (12 notes, sans ré)", "grille, temps 52 → 54,75")
    # sans aucun ré (deuxième relecture 27/09, défaut 3 : ré5 à 43,67 et ré6 à 44,24 refrappaient le ré de la signature
    # et son octave dans un autre timbre) : la3 · fa#4 · la4 · fa#5 · la5 · fa#6, la tierce et la quinte AUTOUR du ré ;
    # la fondamentale du logo, c'est la signature (et la basse)
    arp = [57, 66, 69, 78, 81, 90]
    for i, m in enumerate(arp):
        n = 56.25 + 0.25 * i
        vel = 0.7 - 0.04 * i
        y = I.harpe(m, 2.6, vel, graine=40 + i)
        poser(p, y * vel, humain(tb(n), 1.5), pan=-0.35 + 0.7 * i / (len(arp) - 1))
    cue("harpe", tb(56.25), "arpège la3 · fa#4 · la4 · fa#5 · la5 · fa#6 (sans ré), une double-croche après le ré",
        "grille, temps 56,25 → 57,5")
    return p


def verre_motif():
    """Pendant le SMS (mesure 12, temps 50) : le verre rejoue le motif avec le rythme exact de la signature (0 · 0,24 ·
    0,60 s) mais une mauvaise fin : la5 · sol5 · MI5. La vraie fin (ré) n'arrive qu'avec la signature, 4 s plus tard.
    Il joue SEUL : ni marimba ni grosse caisse du temps 50 au temps 51,5 (relecture 27/09, défaut 5)."""
    _COUCHE[0] = "verre"
    p = piste()
    t0 = tb(50)
    d_sol, d_re = T["sol_sig"] - T["la"], T["re"] - T["la"]
    for m, dt, vel, pan in ((81, 0.0, 0.7, 0.25), (79, d_sol, 0.62, 0.15), (76, d_re, 0.66, -0.05)):
        y = I.verre(m, 2.0, vel, graine=m)
        poser(p, y * vel, t0 + dt, pan=pan)
    cue("verre", t0, "la5 · sol5 · mi5, rythme de la signature (0 · 0,24 · 0,60)", "grille temps 50 ; écarts = signature_sol − signature_la, signature_re_contact − signature_la")
    return p


def batterie():
    """Grosse caisse feutrée (dès « dix », 1er et 3e temps ; « -tion » ; mesure 13 sur 1-2-3 ; logo, grave) et shaker
    (dès « onze », contretemps de croche, puis doubles-croches mesures 9-10 ; retour au SMS), cymbales inversées vers
    « -tion » et vers le ré, miroitements après. Chaque grosse caisse pose son corps sur la basse de l'accord
    (note_du_corps)."""
    gc, sh, cy = piste(), piste(), piste()
    # « dix » plus léger (0,45) ; pas de grosse caisse au temps 32 (arrêt composé sous « c'est parfait ») ; celle du
    # temps 50 avancée au temps 49 (le verre joue seul au temps 50) ; celle du ré à 0,5 (le ré garde sa crête)
    kicks = [(28, 0.45, False)] + [(n, 0.62, False) for n in (30, 34, 36, 38, 40, 42)] + [(43, 0.75, True)]
    kicks += [(49, 0.55, False), (52, 0.7, False), (53, 0.72, False), (54, 0.76, False), (56, 0.5, True)]
    _COUCHE[0] = "grosse_caisse"
    for i, (n, vel, grave) in enumerate(kicks):
        exact = n in (28, 43, 56)
        t = tb(n) if exact else humain(tb(n), 1.5)
        if not exact and sous_un_mot(t):
            vel *= VEL_SOUS_MOT
        m_corps = note_du_corps(tb(n))
        poser(gc, I.grosse_caisse(vel, grave=grave, graine=i, f_fin=float(I.hz(m_corps))) * vel, t)
        cue("grosse caisse", t, f"temps {n}" + (" (grave)" if grave else "") + f", corps sur MIDI {m_corps}", "grille",
            f_fin=round(float(I.hz(m_corps)), 2))
    k = 0
    # contretemps, dès « onze » ; sans celui du temps 33,5 (25,65 : le sol de la plume)
    coups = [(29 + 0.5 + i, 0.5) for i in range(0, 7) if 29.5 + i != 33.5]
    coups += [(36 + 0.25 * i, (0.62, 0.40, 0.30, 0.40)[(i + 2) % 4]) for i in range(0, 28)]   # doubles 36 → 42,75, accent sur les « et »
    coups += [(50.5, 0.4), (51.5, 0.45)] + [(52 + 0.25 * i, (0.45 + 0.35 * i / 11) * (1.0 if i % 2 else 0.7)) for i in range(12)]
    _COUCHE[0] = "shaker"
    for n, vel in coups:
        if n >= 43 and n < 50:
            continue
        t = humain(tb(n), 3.0)
        if sous_un_mot(t):
            vel *= VEL_SOUS_MOT
        poser(sh, I.shaker(vel, graine=k) * vel, t, pan=0.38)
        k += 1
    cue("shaker", tb(29.5), "contretemps dès « onze » ; doubles-croches mesures 9-10 ; retour mesure 12-13", "grille")
    # vers le ré : 0,35 s seulement (elle part après le sol de la signature, 42,54) et finie 30 ms avant le contact
    _COUCHE[0] = "cymbales"
    for (fin, d, vel, g) in ((tb(43), 1.4, 0.4, 1), (tb(56) - 0.030, 0.35, 0.75, 2)):
        poser(cy, I.cymbale_inverse(d, graine=g) * vel, fin - d, pan=0.0)
        cue("cymbale inversée", fin - d, f"monte jusqu'à {fin:.3f}", "grille")
    for (t, d, vel, g) in ((tb(43), 1.6, 0.30, 3), (tb(56), 2.6, 0.45, 4)):
        poser(cy, I.miroitement(d, graine=g) * vel, t, pan=0.1)
        cue("miroitement", t, f"{d} s", "grille")
    return gc, sh, cy


SOUFFLE_S = 0.35


def souffle_vers_le_re():
    """Le souffle avant le ré : l'accord de ré majeur, rendu 0,8 s, sa réverbe SEULE, lue à l'envers sur 0,35 s, finit
    sur le contact du ré : il part APRÈS le sol de la signature (42,55), dans la clairière (relecture 27/09, défaut 2 : sur
    1,4 s, il montait sous le la · sol)."""
    d = 0.8
    t = np.arange(int(d * SR)) / SR
    y = np.zeros((len(t), 2))
    for m in (50, 57, 62, 66, 69):
        v = I.voix_corde(float(I.hz(m)), t, graine=[m, 9], vibrato=False)
        y += S.panner(v, np.clip((m - 60) / 18, -0.5, 0.5))
    y *= np.hanning(len(t))[:, None]
    hum = MX.reverbe_nappe(y, 2.4, graine=77)
    L = int(SOUFFLE_S * SR)
    queue = hum[:L][::-1]
    k = int(0.006 * SR)
    queue[-k:] *= S.rampe_cos(k)[::-1, None]
    queue /= np.max(np.abs(queue))
    p = piste()
    S.ajouter(p, queue, int(round(tb(56) * SR)) - L)
    cue("souffle", tb(56) - SOUFFLE_S, "réverbe de ré majeur à l'envers, finit au contact du ré", "evenements.signature_re_contact")
    return p


# ── 2. voix : présence, ducking, creux 1-4 kHz ──────────────────────────────
def presence_voix(voix, seuil_db=-34.0, attaque=0.030, relache=0.260, anticipation=0.080, tenue=0.120):
    """0 → 1 : la voix parle. Même détecteur que mix.gain_ducking (RMS 10 ms, anticipation, tenue, puis un pôle
    d'attaque et un de relâche), à l'échelle du stem au gain du master (seuil −40 dBFS avant master + 7,84 dB ≈ −32 ;
    −34 pour attraper les fins de mots). Les réglages de chaque groupe sont dans DETECTEURS."""
    w = 480
    c = np.concatenate([[0.0], np.cumsum(voix ** 2)])
    idx = np.clip(np.arange(N) + w // 2, 0, N); jdx = np.clip(np.arange(N) - w // 2, 0, N)
    rms = np.sqrt(np.maximum(c[idx] - c[jdx], 0) / w)
    au_dessus = 20 * np.log10(rms + 1e-12) > seuil_db
    # cadence 1 ms (blocs de 48) ; un film dont la durée n'est pas un nombre entier de ms (50,066667 s = 2 403 200 éch.,
    # 28/09) garde son dernier bloc, partiel : aucun effet quand N est un multiple de 48 (film de 47 s)
    dessus = np.concatenate([au_dessus, np.zeros(-len(au_dessus) % 48, bool)]).reshape(-1, 48).any(axis=1)
    m = len(dessus)
    la, te = int(anticipation * 1000), int(tenue * 1000)
    cs = np.concatenate([[0], np.cumsum(dessus)])
    a = np.arange(m)
    anticipe = (cs[np.clip(a + la + 1, 0, m)] - cs[a]) > 0
    cs2 = np.concatenate([[0], np.cumsum(anticipe)])
    tenu = (cs2[a + 1] - cs2[np.clip(a - te, 0, m)]) > 0
    cible = tenu.astype(float)
    ka, kr = 1 - np.exp(-1 / (attaque * 1000)), 1 - np.exp(-1 / (relache * 1000))
    g = np.zeros(m); x = 0.0
    for i in range(m):
        x += (cible[i] - x) * (ka if cible[i] > x else kr)
        g[i] = x
    return np.interp(np.arange(N) / SR, (np.arange(m) + 0.5) / 1000, g)


def creuser(x, g_bande, f1=1000.0, f2=4000.0):
    """Égaliseur dynamique : gain g_bande(t) sur [f1 ; f2], raccords en cosinus sur une demi-octave de chaque côté
    (700 → 1 000 Hz, 4 000 → 5 700 Hz), 1 ailleurs. STFT Hann 2 048 / pas 512 (reconstruction exacte à gain 1)."""
    Nf, H = 2048, 512
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(Nf) / Nf)
    f = np.fft.rfftfreq(Nf, 1 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    w = np.zeros_like(f)
    w[(f >= f1) & (f <= f2)] = 1
    b = (lf > np.log2(f1) - 0.5) & (f < f1)
    w[b] = 0.5 - 0.5 * np.cos(np.pi * (lf[b] - (np.log2(f1) - 0.5)) / 0.5)
    b = (f > f2) & (lf < np.log2(f2) + 0.5)
    w[b] = 0.5 + 0.5 * np.cos(np.pi * (lf[b] - np.log2(f2)) / 0.5)
    n = len(x)
    xp = np.vstack([np.zeros((Nf, 2)), x, np.zeros((2 * Nf, 2))])
    nb = (len(xp) - Nf) // H + 1
    centres = np.clip(np.arange(nb) * H + Nf // 2 - Nf, 0, n - 1)
    gb = g_bande[centres]
    M = 1 - (1 - gb[:, None]) * w[None, :]
    y = np.zeros_like(xp)
    for c in range(2):
        fr = np.lib.stride_tricks.sliding_window_view(xp[:, c], Nf)[::H][:nb] * win
        Y = np.fft.irfft(np.fft.rfft(fr, axis=1) * M, Nf, axis=1) * win
        for j in range(nb):
            y[j * H:j * H + Nf, c] += Y[j]
    return y[Nf:Nf + n] / 1.5


# ── 3. niveaux (dB appliqués au rendu de chaque couche, avant le bus) et arc du bus ──
NIV = {
    "drone": -23.5, "coeur": -18.0, "cordes": -29.0, "pedale": -40.0, "basse": -24.0, "marimba": -22.0,
    "harpe": -24.0, "verre": -18.0, "grosse_caisse": -20.0, "shaker": -14.0, "cymbales": -25.0, "souffle": -19.0,
}
# relecture 27/09 : verre −22 → −18 (le motif du SMS doit sortir), shaker −17 → −14 (le pouls sur un téléphone ; −12
# coûtait 1 LU à la voix sur « pour » : 5-13 kHz compte en sonie K) ; et sur le logo seulement, cordes +2 et harpe +0,5 dB
# (plus d'énergie au-dessus de 250 Hz, moins de sous-basse)
LOGO_DB = {"cordes": 2.5, "harpe": 1.5}
REVERBE = {"cordes": 0.30, "pedale": 0.35, "marimba": 0.22, "harpe": 0.35, "verre": 0.40, "shaker": 0.10,
           "grosse_caisse": 0.04, "cymbales": 0.25}
LIT = ("cordes", "pedale", "reverbe")        # ce qui tient : s'efface sous la voix, et seul à subir les rattrapages
ARRIVEE = ("souffle", "cymbales")            # ce qui monte vers le ré : hors de la clairière
DUCK = {"large_db": -3.0, "bande_db": -10.0, "grave_db": -6.0}  # sous la voix : −3 dB partout, −10 dB sur 1-4 kHz,
GRAVE_HZ = 160.0                              # et, sur le pouls, −6 dB sous 160 Hz (raccord jusqu'à 225 Hz)
DUCK_LIT_DB = -4.0                            # et −4 dB de plus sur le lit : on garde le rythme, on retire le tapis
# détecteurs de présence (défaut 8 : la tenue de 0,12 s relâchait le tapis de +5 dB dans chaque blanc de 0,3 s) :
#   lit          tenue 0,60 s : ne relâche que dans les pauses de plus de 0,7 s (18,4-19,8 ; 24,9-26,2 ; 33,0-34,0)
#   pouls        attaque τ 0,20 s, anticipation 0,30 s : −3 dB en ≤ 0,75 dB par 50 ms, déjà à −2,3 dB quand la voix entre
#   pouls_bande  τ 0,55 s, anticipation 0,80 s : le creux 1-4 kHz du rythme ne bouge jamais de plus de 1 dB en 50 ms
DETECTEURS = {
    "lit": {"attaque": 0.030, "relache": 0.40, "anticipation": 0.080, "tenue": 0.60},
    "pouls": {"attaque": 0.20, "relache": 0.40, "anticipation": 0.30, "tenue": 0.60},
    "pouls_bande": {"attaque": 0.55, "relache": 0.55, "anticipation": 0.80, "tenue": 0.60},
}
CLAIRIERE_DB = -14.0     # le bus (sauf ARRIVEE) tombe de 14 dB en 0,12 s au temps 55, remonte en 0,06 s au contact du ré
# Deuxième relecture 27/09, défaut 2 : avec son attaque de 30 ms, le lit replongeait de 5 à 6 dB en 50 ms, dans le
# silence, 80 ms avant chaque reprise de la voix (et −13,7 dB cumulés sur 1-4 kHz avant « Bonjour ») : un pompage sur
# un accord tenu. La partie du gain du lit qui suit la voix (ducking, réponses, rattrapages) ne DESCEND plus qu'à pente
# bornée, en anticipant : le lit est déjà au fond quand le mot commence, il y est allé en fondu. Montées libres.
PENTE_LIT = {"large": 0.55, "bande": 0.80}   # dB par 50 ms au plus (1,35 cumulés sur 1-4 kHz, + l'arc ≤ 0,1)


def limiter_descente(g, db_par_50ms):
    """Courbe de gain (dB, à l'échantillon) dont aucune descente ne dépasse db_par_50ms par 50 ms, et qui ne dépasse
    jamais g : sortie(i) = min sur j ≥ i de g(j) + pente·(j − i). Chaque baisse est anticipée en rampe linéaire (en dB),
    qui arrive au fond à l'instant où g y arrivait ; les montées suivent g. Le lit n'est donc jamais moins bas sous la
    voix qu'avant : les marges de la voix ne peuvent qu'y gagner."""
    c = db_par_50ms / (0.05 * SR)
    idx = np.arange(len(g), dtype=np.float64)
    h = g + c * idx
    return np.minimum.accumulate(h[::-1])[::-1] - c * idx


def arc_bus(t):
    """Fader du bus musique (dB) : l'appel sous la voix, la pulsation qui monte, la levée du SMS, le plein du logo.
    Lu à travers CHRONO.vers_base : pendant une mesure insérée, l'arc est TENU (la montée de « neuf » à « -tion » attend
    que le rendez-vous soit pris) ; avant et après, il redonne ses valeurs d'avant, décalées."""
    ancres = [0, T_DEC, tb(12), tb(24), tb(43), tb(43) + 0.8, T_RAC, T_VIB, tb(52), tb(55), tb(56), FIN_SON]
    return np.interp(CHRONO.vers_base(t), CHRONO.vers_base(np.array(ancres, dtype=np.float64)),
                     [0, 0, 1.0, -1.0, 3.0, 1.5, -1.5, -4.0, 0.5, 4.0, 8.5, 11.0])


PAUSE_MIN = 0.90        # une « vraie pause » du dialogue : au moins 0,9 s entre deux mots (donnees/mots.json)
REPONSE_DB = 5.0        # la musique s'avance de 5 dB dans chaque vraie pause (elle répond à la voix)
RAMPE_REPONSE = 0.45    # rampes cosinus de 0,45 s (5 dB : 0,87 dB par 50 ms au plus raide)


def pauses_du_dialogue():
    """Les vraies pauses de l'appel : [fin d'un mot ; début du suivant] quand l'écart atteint PAUSE_MIN."""
    mots = sorted(MX.MOTS["mots"], key=lambda w: w["debut"])
    return [(a["fin"], b["debut"]) for a, b in zip(mots, mots[1:]) if b["debut"] - a["fin"] >= PAUSE_MIN]


REPONSE_PLUME_DB = 2.0  # … sauf dans la pause où la plume écrit (24,95-26,24) : c'est la signature qui répond (la · sol)
# … et dans toute pause qui commence pendant l'ARRÊT COMPOSÉ (temps 32 → 34 de la grille : ni grosse caisse ni marimba,
# le lit seul, de « c'est parfait » à « Parfait, ») : depuis l'échange du prénom (28/09), l'arrêt dure une mesure de plus et
# sa vraie pause est celle de l'appelant qui réfléchit (« prénom ? » → « C'est pour Florian. ») ; la plume y attend,
# suspendue : la musique ne s'avance pas plus que pour elle. Dans le film de 47 s, la seule pause de l'arrêt est déjà
# celle de la plume : rien ne change.
ARRET_TEMPS = (32, 34)


def reponses(t):
    """dB : +REPONSE_DB dans chaque vraie pause, montée qui part 0,05 s après le dernier mot, descente finie 0,30 s
    avant le mot suivant (le pouls anticipe la voix de 0,30 s) ; +REPONSE_PLUME_DB seulement dans la pause de la plume
    et dans les pauses de l'arrêt composé (ARRET_TEMPS)."""
    arret = (tb(ARRET_TEMPS[0]), tb(ARRET_TEMPS[1]))
    g = np.zeros_like(t)
    for a, b in pauses_du_dialogue():
        t0, t1 = a + 0.05, b - 0.30 - RAMPE_REPONSE
        if t1 <= t0:
            continue
        r = min(RAMPE_REPONSE, (t1 - t0))
        A = min(REPONSE_DB, 11.0 * r)           # pente ≤ 0,86 dB par 50 ms, même dans une pause courte
        if a <= T_PLUME_LA <= b or arret[0] <= a < arret[1]:
            A = min(A, REPONSE_PLUME_DB)
        g = np.maximum(g, A * fondu_cos(t, t0, r) * (1 - fondu_cos(t, t1, RAMPE_REPONSE)))
    return g


def clairiere(t):
    """Défaut 2 : le temps 55 (42,13) est une vraie clairière. Le bus tombe de CLAIRIERE_DB en 0,12 s (fini à 42,25,
    avant le la de 42,30) et ne remonte qu'au contact du ré, en 0,06 s, sous l'attaque du ré qui le masque."""
    return CLAIRIERE_DB * (fondu_cos(t, tb(55), 0.12) - fondu_cos(t, T["re"], 0.06))


MARGE_MOT = 11.0        # la voix ≥ 11 LU au-dessus de TOUT le reste, mot par mot (contrôle F du master : ≥ 10)
MARGE_PLANCHER = 10.2   # … sauf si les touchers seuls en prennent déjà l'essentiel : alors marge sans musique − 1, ≥ 10,2
MARGE_BANDE = 12.0      # et dans la bande 1-4 kHz (consonnes, formants hauts) : voix ≥ musique + 12 dB, mot par mot
RAMPE_RAT = 0.15        # rattrapages : érosion ±0,15 s puis moyenne glissante ±0,15 s (rampes de 0,30 s en tout)
FUSION_RAT = 0.40       # deux creux séparés de moins de 0,4 s n'en font qu'un (le lit ne remonte pas entre deux mots)
TENUE_RAT = 0.80        # un creux suivi d'un blanc de moins de 0,8 s est tenu jusqu'au mot suivant (contrôle L)


def bande_1_4k(x):
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = ((f >= 1000) & (f <= 4000)).astype(float)
    return np.fft.irfft(X * m[:, None], len(x), axis=0)


def fenetres_mots():
    return [(w["debut"] - 0.09, max(w["fin"], w["debut"] + 0.12) + 0.05, w) for w in MX.MOTS["mots"]]


def courbe_rattrapage(profondeurs, fen):
    """Courbe (dB, à l'échantillon) : chaque mot à sa profondeur sur [début − 0,09 ; fin + 0,05] ; entre deux creux
    séparés de moins de FUSION_RAT, on tient la moins profonde des deux (pas de remontée entre deux mots) ; puis érosion
    (minimum glissant ±RAMPE_RAT) et moyenne glissante ±RAMPE_RAT : la profondeur demandée est tenue sur toute la fenêtre
    du mot, et le gain ne bouge qu'en rampes de 2 × RAMPE_RAT."""
    m = int(np.ceil(N / SR * 1000)) + 1
    g = np.zeros(m)
    creux = sorted((a, b, d) for (a, b, _), d in zip(fen, profondeurs) if d < -0.01)
    for a, b, d in creux:
        i0, i1 = max(0, int(a * 1000)), min(m, int(np.ceil(b * 1000)))
        g[i0:i1] = np.minimum(g[i0:i1], d)
    for (a0, b0, d0), (a1, b1, d1) in zip(creux, creux[1:]):
        if 0 < a1 - b0 < FUSION_RAT:
            i0, i1 = int(b0 * 1000), int(np.ceil(a1 * 1000))
            g[i0:i1] = np.minimum(g[i0:i1], max(d0, d1))
    # deuxième relecture 27/09 : un creux suivi d'un blanc court (< TENUE_RAT entre la fin du mot et le début du suivant)
    # est tenu jusqu'à la fenêtre du mot suivant ; le lit ne remonte pas dans le blanc (contrôle L : « heures. » → « Vous »
    # remontait de 1,52 dB dans 0,49 s), il remonte sous le mot suivant, que la voix masque
    debuts = sorted(a for (a, _, _) in fen)
    mots_ = {round(a, 6): w for (a, _, w) in fen}
    for a, b, d in creux:
        w = mots_[round(a, 6)]
        suivants = [x for x in debuts if x > a + 1e-6]
        if suivants:
            a_n = suivants[0]
            if mots_[round(a_n, 6)]["debut"] - w["fin"] < TENUE_RAT:
                i0, i1 = int(b * 1000), int(np.ceil(a_n * 1000))
                if i1 > i0:
                    g[i0:i1] = np.minimum(g[i0:i1], d)
    r = int(RAMPE_RAT * 1000)
    e = MX.filtre_min(g, 2 * r + 1)
    c = np.concatenate([[0.0], np.cumsum(np.concatenate([np.zeros(r), e, np.zeros(r)]))])
    lisse = (c[2 * r + 1:] - c[:-(2 * r + 1)]) / (2 * r + 1)
    return np.interp(np.arange(N) / SR, np.arange(m) / 1000, lisse[:m])


def rattrapages(lit, pouls, st, iterations=10):
    """Le geste de l'ingénieur du son, mesuré, mot par mot (donnees/mots.json), SUR LE LIT SEUL (défaut 1 : appliqués au
    bus, ils faisaient pomper le rythme précisément sur les accents composés). Deux automations qui ne font que baisser :
      - LARGE : la voix doit passer MARGE_MOT LU au-dessus de tout le reste (pondération K, la fenêtre du contrôle F) ;
        cible abaissée à (marge sans musique − 1), plancher MARGE_PLANCHER, quand les touchers en prennent déjà
        l'essentiel (« dix ») ;
      - BANDE (1-4 kHz, par creuser()) : la voix doit passer MARGE_BANDE dB au-dessus de la musique.
    Si le lit à −12 dB ne suffit pas, le mot est noté dans « manques » : c'est l'arrangement du pouls qu'il faut alléger.
    Itéré (les sommes de sonie ne sont pas linéaires). Renvoie (gain large dB, gain bande dB, journal, manques)."""
    dk = MX.ponderer_k(st["dialogue"])
    autres = MX.ponderer_k(st["sfx"] + st["signature"])
    lk, pk = MX.ponderer_k(lit), MX.ponderer_k(pouls)
    vb, lb, pb = bande_1_4k(st["dialogue"]), bande_1_4k(lit), bande_1_4k(pouls)
    fen = fenetres_mots()
    prof_l, prof_b = np.zeros(len(fen)), np.zeros(len(fen))
    journal, manques = {}, {}
    P = lambda xk, a, b: np.sum(np.mean(xk[a:b] ** 2, axis=0)) + 1e-20  # noqa: E731
    gl, gb = np.zeros(N), np.zeros(N)
    for it in range(iterations):
        gl, gb = courbe_rattrapage(prof_l, fen), courbe_rattrapage(prof_b, fen)
        L_, B_ = S.gain(gl)[:, None], S.gain(gb)[:, None]
        change = False
        for j, (_, _, w) in enumerate(fen):
            a, b = int(w["debut"] * SR), int(max(w["fin"], w["debut"] + 0.12) * SR)
            Pv, Pa, Pl, Pp = P(dk, a, b), P(autres, a, b), P(lk * L_, a, b), P(pk, a, b)
            # la marge est mesurée sur la SOMME des signaux, comme le contrôle F (deuxième relecture 27/09 : la somme des
            # puissances oubliait ce qui est corrélé entre le lit et le pouls, la harpe et sa réverbe, et laissait
            # « vous » à 11,4 dB sur 1-4 kHz pour 12,2 visés) ; la profondeur se déduit des puissances, puis on itère
            Ptot = P(autres + lk * L_ + pk, a, b)
            marge = 10 * np.log10(Pv / Ptot)
            cible = max(MARGE_PLANCHER, min(MARGE_MOT, 10 * np.log10(Pv / Pa) - 1.0))
            bl = 0.0
            if marge < cible:
                # part « effective » du lit : sa puissance plus les termes croisés (ce que la somme lui doit)
                eff = max(Ptot - Pa - Pp, 1e-3 * Pl)
                reste = Pv / 10 ** ((cible + 0.2) / 10) - Pa - Pp
                if reste <= 0:
                    # (28/09) le lit ne peut PAS sauver ce mot : les sons voulus (touchers, signature) et le pouls prennent
                    # déjà la marge (l'échange du prénom : le la · sol de la plume sous « Très bien. », 8,4 LU sans
                    # musique). Plutôt que de creuser le lit de 12 dB pour rien, il ne coûte pas plus de 1 LU au mot
                    # (même règle que la garde de la voix du mixeur, perte_max_db) ; jamais atteint dans le film de 47 s
                    reste = Pv / 10 ** ((10 * np.log10(Pv / Pa) - 1.0 + 0.2) / 10) - Pa - Pp
                bl = -12.0 if reste <= 0 else min(0.0, 10 * np.log10(reste / eff))
            Pvb, Plb, Ppb = P(vb, a, b), P(lb * L_ * B_, a, b), P(pb, a, b)
            Pmb = P(lb * L_ * B_ + pb, a, b)
            eb = 10 * np.log10(Pvb / Pmb)
            bb = 0.0
            if eb < MARGE_BANDE:
                eff_b = max(Pmb - Ppb, 1e-3 * Plb)
                reste_b = Pvb / 10 ** ((MARGE_BANDE + 0.2) / 10) - Ppb
                bb = -12.0 if reste_b <= 0 else min(0.0, 10 * np.log10(reste_b / eff_b))
            cle = f"{w['debut']:.3f} {w['texte']}"
            if bl < -0.01 or bb < -0.01:
                nl, nb = max(-12.0, prof_l[j] + bl), max(-12.0, prof_b[j] + bb)
                if nl < prof_l[j] - 0.01 or nb < prof_b[j] - 0.01:
                    change = True
                elif marge < cible - 0.05 or eb < MARGE_BANDE - 0.05:
                    manques[cle] = {"marge_LU": round(float(marge), 2), "cible_LU": round(float(cible), 2),
                                    "voix_moins_musique_1-4k_db": round(float(eb), 1)}
                prof_l[j], prof_b[j] = nl, nb
                journal.setdefault(cle, []).append(
                    {"iteration": it, "marge_LU": round(float(marge), 2), "cible_LU": round(float(cible), 2),
                     "voix_moins_musique_1-4k_db": round(float(eb), 1), "profondeur_lit_db": round(float(nl), 2),
                     "profondeur_lit_bande_db": round(float(nb), 2)})
        if not change:
            break
    return gl, gb, journal, manques


PROFONDEUR_SIGNATURE = -11.0    # défaut 4 : −5 → −11 dB ; la musique a déjà reculé 8 ms avant chaque attaque
AVANCE_SIGNATURE = 0.008
RELACHE_SIGNATURE = {"la": 0.20, "sol_sig": 0.20, "re": 0.60}   # τ de la relâche après chaque note (s)


def place_a_la_signature(sig=None):
    """Gain (dB) du bus musique sous les trois notes de la signature (instants de donnees/evenements.json : la, sol,
    ré) : PROFONDEUR_SIGNATURE, atteinte en 6 ms et AVANCE_SIGNATURE avant l'attaque (la musique a déjà reculé quand la
    note frappe : c'était la seconde cause du limiteur au ré), tenue 30 ms, puis relâche exponentielle de τ
    RELACHE_SIGNATURE ; le plus profond des trois l'emporte ; retour à 0 en cosinus de ré + 1,6 à ré + 1,9 s.
    Relecture 27/09 : un suiveur d'enveloppe du stem signature suivait la longue queue du ré, restait à −6 dB jusqu'à
    43,8 s puis lâchait +6 dB en 0,3 s (une poussée tardive de l'accord, plus forte à 44,4 s que le ré lui-même)."""
    t = np.arange(N) / SR
    g = np.zeros(N)
    for cle, tau in RELACHE_SIGNATURE.items():
        u = t - T[cle]
        h = np.where(u < 0.03, fondu_cos(u, -(AVANCE_SIGNATURE + 0.006), 0.006), np.exp(-(u - 0.03) / tau))
        g = np.minimum(g, PROFONDEUR_SIGNATURE * h)
    return g * (1 - fondu_cos(t, T["re"] + 1.6, 0.3))


def controle_plume(marge=0.10):
    """Le la · sol de la plume (stem signature, evenements.ecriture_debut) doit tomber dans l'ARRÊT COMPOSÉ (ARRET_TEMPS),
    sans note de la musique à moins de `marge` s. Depuis l'échange du prénom, l'image fait écrire « Florian » sous la voix
    de l'appelant : l'arrêt (temps 32 → 34 de la grille du film d'avant, 24,50 → 29,10 dans le film de 50,07 s) le couvre
    tant que l'écriture reste entre la fin de « c'est parfait. » et « Parfait, ». À lire après composer()."""
    arret = (tb(ARRET_TEMPS[0]), tb(ARRET_TEMPS[1]))
    proches = sorted((round(abs(a_["t"] - x), 4), a_["couche"], a_["t"]) for a_ in ATTAQUES for x in (T_PLUME_LA, T_PLUME_SOL))
    d = proches[0] if proches else (None, None, None)
    return {"la": round(T_PLUME_LA, 6), "sol": round(T_PLUME_SOL, 6), "arret": [round(arret[0], 6), round(arret[1], 6)],
            "dans_l_arret": bool(arret[0] <= T_PLUME_LA and T_PLUME_SOL < arret[1]),
            "attaque_la_plus_proche": {"ecart_s": d[0], "couche": d[1], "t": d[2]},
            "ok": bool(arret[0] <= T_PLUME_LA and T_PLUME_SOL < arret[1] and (d[0] is None or d[0] >= marge))}


def fondu_final(t):
    f0 = FIN_SON - MX.DEC["fin_fondu"]
    return 1 - fondu_cos(t, f0, FIN_SON - f0)


# ── 4. assemblage ───────────────────────────────────────────────────────────
def composer():
    ATTAQUES.clear()
    print("   couches…")
    C = {
        "drone": drone_sonnerie(), "coeur": coeur_sonnerie(), "cordes": cordes(), "pedale": pedale_la(),
        "basse": ligne_de_basse(), "marimba": marimba(), "harpe": harpe(), "verre": verre_motif(),
        "souffle": souffle_vers_le_re(),
    }
    gc, sh, cy = batterie()
    _COUCHE[0] = None
    C["grosse_caisse"], C["shaker"], C["cymbales"] = gc, sh, cy
    t = np.arange(N) / SR
    logo = fondu_cos(t, tb(56) - 0.03, 0.03)
    for k in C:
        C[k] *= S.gain(NIV[k] + LOGO_DB.get(k, 0.0) * logo)[:, None]
    envoi = sum(C[k] * REVERBE[k] for k in REVERBE)
    print("   réverbe…")
    # deux réverbes : avant le raccroché (sa queue est coupée avec tout le reste) et après le silence (elle part de
    # zéro) ; une seule réverbe ferait ressortir, à 36,67, la queue de ce qui sonnait avant la coupe
    i_rac, i_s1 = int(round(T_RAC * SR)), int(round(S1 * SR))
    avant, apres = envoi.copy(), envoi.copy()
    avant[i_rac:] = 0
    apres[:i_s1] = 0
    r_av = MX.reverbe_nappe(avant, 2.6, graine=2709)[:N]
    k = int(0.005 * SR)
    r_av[i_rac:i_rac + k] *= S.rampe_cos(k)[::-1, None]
    r_av[i_rac + k:] = 0
    C["reverbe"] = r_av + MX.reverbe_nappe(apres, 2.6, graine=2710)[:N]
    return C


def ecrire_couches(C, t):
    """Pour l'analyse : chaque couche seule (niveau de couche et arc du bus, sans ducking ni clairière), 16 bits."""
    d = ICI / "couches"
    d.mkdir(exist_ok=True)
    for k, v in C.items():
        labo.ecrire(d / f"{k}.wav", v * S.gain(arc_bus(t))[:, None])


def activite_limiteur(g_lim):
    """Où le limiteur travaille : réduction max, part du temps au-delà de 0,5 / 1 / 2 dB, intervalles > 1 dB."""
    r = -20 * np.log10(np.maximum(g_lim, 1e-9))
    au_dela = r > 1.0
    bords = np.flatnonzero(np.diff(np.concatenate([[0], au_dela.astype(int), [0]])))
    inter = [(round(a / SR, 3), round(b / SR, 3), round(float(r[a:b].max()), 2)) for a, b in zip(bords[::2], bords[1::2])]
    return {"reduction_max_db": round(float(r.max()), 2), "t_max": round(float(np.argmax(r) / SR), 3),
            "part_sup_0.5_db": round(float(np.mean(r > 0.5)), 4), "part_sup_1_db": round(float(np.mean(r > 1)), 4),
            "part_sup_2_db": round(float(np.mean(r > 2)), 5), "intervalles_sup_1_db": inter[:40]}


def charger_stems():
    """Les stems du master validé au gain du master, SANS sa courbe de limiteur (stems_avant_limiteur.py)."""
    noms = ("dialogue", "sfx", "signature")
    if not all((STEMS_AV / f"{k}.npy").exists() for k in noms):
        import stems_avant_limiteur
        stems_avant_limiteur.main()
    st = {k: np.load(STEMS_AV / f"{k}.npy") for k in noms}
    for k, v in st.items():
        assert v.shape == (N, 2), (k, v.shape)
    return st


def fabriquer(st, couches=False):
    """Toute la chaîne, en mémoire : couches, lit et pouls, ducking, clairière, rattrapages, coupe, master."""
    print("2. musique")
    C = composer()
    t = np.arange(N) / SR
    if couches:
        ecrire_couches(C, t)
    print("3. voix : ducking lent, creux 1-4 kHz, rattrapages sur le lit")
    voix = st["dialogue"][:, 0]
    pv = {k: presence_voix(voix, **v) for k, v in DETECTEURS.items()}
    rep = reponses(t)
    arc, clr = arc_bus(t) + rep, clairiere(t)
    gsig = place_a_la_signature(st["signature"])
    hp = lambda x: MX.ffmpeg_filtre(x, "highpass=f=28")          # noqa: E731  rien sous le ré1 : pas de grondement
    # le lit : une part composée (arc, clairière, place à la signature : jamais bornée) et une part qui suit la voix
    # (réponses, ducking, puis rattrapages), dont les descentes sont bornées (défaut 2 de la deuxième relecture)
    fixe_lit = arc_bus(t) + clr + gsig
    dyn_l0 = rep + (DUCK["large_db"] + DUCK_LIT_DB) * pv["lit"]
    dyn_b0 = DUCK["bande_db"] * pv["lit"]
    lit_brut = hp(sum(C[k] for k in LIT))

    def faire_lit(d_l, d_b):
        return creuser(lit_brut * S.gain(fixe_lit + d_l)[:, None], S.gain(d_b))

    dyn_l1, dyn_b1 = limiter_descente(dyn_l0, PENTE_LIT["large"]), limiter_descente(dyn_b0, PENTE_LIT["bande"])
    lit = faire_lit(dyn_l1, dyn_b1)
    g_pouls_dyn = DUCK["large_db"] * pv["pouls"]
    pouls = hp(sum(v for k, v in C.items() if k not in LIT and k not in ARRIVEE)) * S.gain(arc + clr + g_pouls_dyn + gsig)[:, None]
    pouls += hp(sum(C[k] for k in ARRIVEE)) * S.gain(arc + g_pouls_dyn + gsig)[:, None]
    pouls = creuser(pouls, S.gain(DUCK["bande_db"] * pv["pouls_bande"]))
    # sous la voix, le grave du pouls (fondamentales de basse, corps de grosse caisse) recule : il coûte à la voix en
    # sonie sans s'entendre sur un téléphone ; en pleine bande, les harmoniques de la basse restent
    pouls = creuser(pouls, S.gain(DUCK["grave_db"] * pv["pouls_bande"]), f1=20.0, f2=GRAVE_HZ)
    g_rat, g_rat_b, journal_rat, manques = rattrapages(lit, pouls, st)
    # courbes finales : (bornée + rattrapages) de nouveau bornée ; elles restent partout ≤ celles sur lesquelles les
    # rattrapages ont été mesurés, donc les marges de la voix tiennent
    dyn_l, dyn_b = limiter_descente(dyn_l1 + g_rat, PENTE_LIT["large"]), limiter_descente(dyn_b1 + g_rat_b, PENTE_LIT["bande"])
    lit = faire_lit(dyn_l, dyn_b)
    print(f"   rattrapages sur le lit : {len(journal_rat)} mots, large max {g_rat.min():.1f} dB, bande 1-4 kHz max "
          f"{g_rat_b.min():.1f} dB ; mots que le lit seul ne sauve pas : {list(manques) or 'aucun'}")
    musique = lit + pouls
    # raccroché : la musique est coupée au même échantillon que tout le reste (5 ms), zéros jusqu'au vibreur
    i_rac, i_s1 = int(round(T_RAC * SR)), int(round(S1 * SR))
    k = int(0.005 * SR)
    musique[i_rac:i_rac + k] *= S.rampe_cos(k)[::-1, None]
    musique[i_rac + k:i_s1] = 0
    # rien de ce qui a commencé avant le raccroché ne doit sonner après le silence
    musique *= fondu_final(t)[:, None]
    musique[int(round(FIN_SON * SR)):] = 0
    somme = st["dialogue"] + st["sfx"] + st["signature"] + musique
    print("4. master (un gain, UN limiteur à crête vraie −1,7 dBTP)")
    mix, G, g_lim, red = MX.masteriser(somme)
    finals = {k: v * S.gain(G) * g_lim[:, None] for k, v in st.items()}
    finals["musique"] = musique * S.gain(G) * g_lim[:, None]
    gains = {"pv_lit": pv["lit"], "pv_pouls": pv["pouls"], "pv_pouls_bande": pv["pouls_bande"], "arc_db": arc,
             "reponses_db": reponses(t),
             "clairiere_db": clr, "signature_db": gsig, "pouls_dyn_db": g_pouls_dyn,
             "pouls_bande_db": DUCK["bande_db"] * pv["pouls_bande"], "pouls_grave_db": DUCK["grave_db"] * pv["pouls_bande"],
             "lit_rattrapage_db": g_rat,
             "lit_rattrapage_bande_db": g_rat_b, "lit_db": fixe_lit + dyn_l, "lit_bande_db": dyn_b,
             "lit_dyn_avant_borne_db": dyn_l0 + g_rat, "lit_bande_avant_borne_db": dyn_b0 + g_rat_b, "g_lim": g_lim}
    return {"C": C, "lit": lit, "pouls": pouls, "musique": musique, "mix": mix, "G": G, "g_lim": g_lim, "red": red, "finals": finals,
            "gains": gains, "journal_rat": journal_rat, "manques": manques}


def main(essai=False, couches=True):
    STEMS_OUT.mkdir(exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    print("1. stems du master validé, avant son limiteur")
    st = charger_stems()
    R_ = fabriquer(st, couches=couches)
    for k, v in R_["finals"].items():
        S.ecrire24(STEMS_OUT / f"{k}.wav", v)
    S.ecrire24(ICI / "mix-musique.wav", R_["mix"])
    np.savez_compressed(ICI / "gains-musique.npz", **{k: v[::48].astype(np.float32) for k, v in R_["gains"].items()})
    rapport = {"version": "musique-270926-relue-2", "grille": {"temps_s": BEAT, "bpm": 60 / BEAT, "t0": T0, "re": tb(56)},
               "insertions": [dict(i) for i in CHRONO.ins],
               "stems_entree": "stems-avant-limiteur/ (master validé au gain de 7,84 dB, sans sa courbe de limiteur)",
               "gain_master_db": round(float(R_["G"]), 3), "reduction_limiteur_max_db": round(float(R_["red"]), 2),
               "niveaux_couches_db": NIV, "logo_db": LOGO_DB, "reverbe_envois": REVERBE, "ducking": DUCK,
               "ducking_lit_db": DUCK_LIT_DB, "detecteurs": DETECTEURS, "clairiere_db": CLAIRIERE_DB,
               "profondeur_signature_db": PROFONDEUR_SIGNATURE, "avance_signature_s": AVANCE_SIGNATURE,
               "relache_signature_tau_s": RELACHE_SIGNATURE, "pente_lit_db_par_50ms": PENTE_LIT,
               "reponse_plume_db": REPONSE_PLUME_DB, "plume": {"la": T_PLUME_LA, "sol": T_PLUME_SOL},
               "rattrapages_mot_par_mot_sur_le_lit": R_["journal_rat"], "manques": R_["manques"], "marge_mot_LU": MARGE_MOT,
               "limiteur": activite_limiteur(R_["g_lim"]),
               "cues": sorted(CUES, key=lambda c: c["t"]), "attaques": sorted(ATTAQUES, key=lambda c: c["t"])}
    (ICI / "cues-musique.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=float))
    if essai:
        print(f"   essai : {ICI / 'mix-musique.wav'} {labo.mesurer(ICI / 'mix-musique.wav')} (rien hors de riche-musique/)")
        return R_
    shutil.copyfile(ICI / "mix-musique.wav", SORTIE_WAV)
    print("5. MP4 : vidéo copiée, nouvelle piste AAC 256k 48 kHz")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VIDEO), "-i", str(SORTIE_WAV), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart",
                    "-shortest", str(SORTIE_MP4)], check=True)
    print(f"   {SORTIE_WAV} {labo.mesurer(SORTIE_WAV)}")
    return R_


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true", help="n'écrit rien hors de riche-musique/ (ni WAV livré ni MP4)")
    ap.add_argument("--sans-couches", action="store_true", help="n'écrit pas couches/ (le contrôle D et le verre en ont besoin)")
    a = ap.parse_args()
    main(essai=a.essai, couches=not a.sans_couches)
