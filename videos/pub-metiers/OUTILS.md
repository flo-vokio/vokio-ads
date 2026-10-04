# Pub multi-métiers « Ils ont tous la même assistante » (9:16, 04/10/2026)

Accroche : quatre VRAIS décrochés de nos lignes de démo (Plomberie Azur, Salon Marchand, Garage du Rond-Point,
La Table des Halles) sous « Ils ont tous la même assistante. », puis voix off (ElevenLabs, Sébastien) qui déroule les
fonctionnalités : rendez-vous dans l'agenda Google, SMS de confirmation + rappel la veille, commandes, urgences,
résumé dans l'espace client (vraies captures), le mur des 22 métiers ; signature du film long (le point écrit Vokıo
et se pose sur le ı), promesse, « Créez votre espace gratuitement, sur vokio.fr », 59 €/mois sans engagement.

| Besoin | Commande (depuis ce dossier) |
|---|---|
| Changer le texte de la voix off ou la voix | `REPLIQUES` / `VOIX` dans `son/voix.py`, puis `python3 son/voix.py` (cache : seules les répliques changées sont refacturées) |
| Changer les décrochés, les écarts, la musique | `son/monter.py`, puis `python3 son/monter.py && python3 construire.py` |
| Mise en page, textes à l'écran | `gabarit.src.html` (les pièces iPhone viennent de `../pub-secretaire/gabarit.html`), puis `python3 construire.py` |
| Regarder sans rendre | `/root/.pwtest/bin/python3 apercu.py --instants 0,3,6.5 -o /dev/shm/a.png` |
| Rendre | `cd ../showcase-iphone && python3 outils/rendre.py ../pub-metiers -o /root/vokio-uploads/videos/pub-metiers/meme-assistante-9x16.mp4 --son ../pub-metiers/son/mix.wav` |

- Chaque réplique de voix off part sur un temps de la musique (120 BPM, grosse caisse calée sur l'image 0) ; le la de
  la signature aussi ; la musique est coupée net au la puis revient doucement sous la promesse.
- Voix off : compression douce + limiteur (voix de pub). Les VRAIS appels : coupes + gain seulement.
- Piège : la classe `.pt` est celle des éléments de l'iPhone ; le point final des titres est `.ptf`.
