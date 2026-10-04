# Pub « Cette secrétaire n'existe pas » (9:16, 04/10/2026)

Pub Meta (Reels / Stories) bâtie sur le VRAI appel plombier de la démo (Camille, Plomberie Azur, fuite sous l'évier).
Accroche composée dès l'image 0 (« Cette secrétaire n'existe pas. », le point final est le point solaire) sur la voix de
Camille ; preuve en 18 s (urgence, plombier prévenu, adresse, conseil, SMS) ; révélation « Camille est une IA. » ;
fin : Vokıo, « Essayez-la : laissez votre numéro, elle vous rappelle en 10 secondes. », vokio.fr, 59 €/mois.

| Besoin | Commande (depuis ce dossier) |
|---|---|
| Changer les coupes de l'appel ou les instants de la fin | éditer `SEGMENTS` / `temps` dans `son/monter.py`, puis `python3 son/monter.py && python3 construire.py` |
| Changer la mise en page, un texte | éditer `gabarit.html` (jamais `index.html`, généré), puis `python3 construire.py` |
| Regarder sans rendre (erreurs internes + planche, zones Meta 250 / 1250 en rouge) | `/root/.pwtest/bin/python3 apercu.py [--instants 0,2.5,…] [-o /dev/shm/a.png]` |
| Rendre avec le son | `cd ../showcase-iphone && python3 outils/rendre.py ../pub-secretaire -o /root/vokio-uploads/videos/pub-secretaire/cette-secretaire-9x16.mp4 --son ../pub-secretaire/son/mix.wav` |

- Tout le minutage vient de `donnees/montage.json` (écrit par `son/monter.py`) : mots en temps film, coches de la fiche,
  instants de la fin. Le texte montré est exactement le texte dit (règle 8).
- Son : coupes + gain sur la voix (aucun traitement), nappe du showcase baissée sous la voix, battement 100 BPM doux,
  toc à chaque ligne cochée, signature courte la · sol · ré au point sur le ı ; -14 LUFS.
- Zones Meta 9:16 : rien d'important au-dessus de 250 ni sous 1250 (contrôlé par `exiger` dans le gabarit).
- Réutilise : situation « évier » et iPhone Messages du relais, wordmark et signature du showcase.
- Une autre déclinaison métier = un autre appel dans `APPEL`/`ALIGN` + d'autres `SEGMENTS` et coches.
