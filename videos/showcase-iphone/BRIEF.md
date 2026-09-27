# Showcase Vokio · brief commun (26/09/2026)

Demande de Florian, fondateur de Vokio : « Tu ferais quoi pour Vokio ? Jusqu'où tu pourrais
aller en motion design ET en sound design ? Utilise toutes les ressources possibles, montre-moi
quelque chose d'époustouflant, épate-moi. » Carte blanche. On livre un film FINI, sonorisé.

## Vokio en une phrase
Un assistant téléphonique IA (agent vocal) qui décroche à la place des artisans, commerçants et
praticiens (plombier, restaurant, institut de beauté, vétérinaire, garage, coiffure…) quand ils
ne peuvent pas répondre : il prend le rendez-vous dans leur agenda, envoie un SMS de
confirmation, résume l'appel dans leur espace (app.vokio.fr). 59 €/mois, sans engagement.
Promesse : « Votre ligne répond même quand vous ne pouvez pas. » Concurrent réel : le répondeur
et l'appel manqué (le client appelle le suivant sur la liste).

## Format
9:16, 1080×1920, 30 i/s, 30 à 45 s, pour Instagram Reels / TikTok / pub Meta. AVEC SA BANDE
SON (c'est tout l'enjeu ici, contrairement aux autres vidéos livrées muettes). Pas de voix off
synthétique de narrateur : Florian a banni la voix off synthétique (doublage humain en attente).
Les voix autorisées : les VRAIS appels enregistrés sur nos lignes de démo (voir Ressources),
et la voix réelle de l'agent (c'est le produit). Tout le reste passe par la typographie, le
mouvement et le son.

## DA « Plein Jour » (non négociable)
- Papier #F4F1E8 · encre #262019 · solaire #EFA424 (l'accent, « l'agent agit », UNE fois par
  plan) · terracotta #C0452C (la seule couleur négative) · vert #6E9C74 (validé) · gris texte
  #6F695F. Fond sombre possible seulement s'il est motivé (la nuit) et reste chaud, jamais noir pur.
- Polices (woff2 dans /opt/vokio-ads/videos/ux-retravail/repondeur-ou-vokio/assets/fonts/) :
  Instrument Serif (récit, titres, italique pour la chute), Geist (interface, texte courant),
  Geist Mono (un seul usage en capitales par écran, maximum).
- Wordmark « Vokıo » : ı sans point + point solaire rond, left:63.5 % du ı, margin-left -.055em,
  top .13em, taille .11em (voir #mot dans repondeur-ou-vokio/index.html, masque de départ
  inset(-30% 114% -30% -14%) pour ne pas laisser dépasser l'empattement du V).
- Mouvement : décélération power3 (power4 pour les heures), aucun rebond élastique, sorties plus
  courtes que les entrées, masques de ligne (le mot monte de sa ligne de base).

## Règles de Florian (chacune a coûté un aller-retour)
1. Trois éléments simultanés à l'écran, pas plus. Une info à la fois, quitte à rallonger.
2. Aucun chrome d'interface factice (faux boutons, compteurs, barres d'OS). Un OBJET vrai qui
   porte l'info est bienvenu (vraie capture de app.vokio.fr, silhouette d'iPhone pour un SMS).
3. Mono capitales : un seul usage par écran. Qui parle = typographie, pas des étiquettes.
4. Aucun numéro de téléphone à l'écran. Établissements fictifs, mention « Établissement fictif »
   si on montre l'app.
5. Texte ≥ 36 px (sur 1080 de large), contraste WCAG AA, rien d'important sous y = 1500
   (interface Reels/TikTok), marges latérales ≥ 70 px.
6. Jamais de tiret cadratin « — » dans un texte publié. Prénom seul, jamais « Alauzet ».
7. Pas de vidéo générative (Veo…) : la physique est fausse, notre public le voit.
8. Le texte montré doit être une sous-suite du texte dit quand il y a une voix.
9. Une carte d'app ne zoome pas (le texte sautille à chaque image) : elle se déplie, glisse,
   mais son échelle reste constante.
10. Le rythme ne doit pas être trop rapide : on doit avoir le temps de remarquer les détails.
    Florian a trouvé 4 s par appel « un peu rapide », 6 s « bien ».
11. Rien de « généré par IA » : pas d'accumulation, pas d'effets gratuits, pas de glow partout.

## Ressources
### Image
- HyperFrames 0.8.62 (HTML seekable + GSAP → MP4) : lanceur `/opt/vokio-ads/bin/hf`
  (`hf check .`, `hf render . --fps 30 -o out.mp4 --quiet`). Rendus sérialisés :
  `flock /tmp/hf-rendu.lock …`. Skills : /root/.claude/skills/hyperframes*/ (core : composition,
  sub-compositions ; animation : blueprints, transitions ; audio : data-fx-chain, automation ;
  registry : blocs prêts). NE JAMAIS lancer `skills update` ni `audio.mjs sync-durations`.
- Vraies captures de app.vokio.fr (établissements fictifs, sans numéro) :
  /opt/vokio-ads/videos/ux-retravail/24h-chez-vokio/assets/captures/ (lignes d'appel repliées,
  en-têtes, volets vides + résumé à réécrire en calque HTML Geist 42/68,25 rgb(78,73,66) :
  voir index.html de ce projet pour la méthode exacte, qui est validée) ;
  /opt/vokio-ads/videos/ux-retravail/film-demo/assets/<metier>/ (agenda-jour, impact-rdv,
  impact-nuit, appels) ; /opt/vokio-ads/videos/ux-retravail/appel-reel-plombier/assets/plans/.
- Films existants à ne pas refaire à l'identique (on doit les dépasser) : « 24 h chez Vokio »
  (horloge qui roule, 4 métiers, cartes qui se déplient, résumé qui s'écrit), « Le répondeur,
  ou Vokio » (messagerie doublée, bip, deux issues), « appel manqué » (montant perdu),
  « L'appel réel » plombier (vrai appel + résumé au curseur).
### Son
- Vrais appels montés (voix de l'agent + de l'appelant, VRAIS, c'est la preuve) :
  /root/vokio-audios-metiers-180926/montes/<metier>.wav (19 métiers, ~45-90 s chacun),
  transcriptions horodatées dans /root/vokio-audios-metiers-180926/originaux/<metier>.json
  (champ transcript : t, role, message) et design/audios/extraits.json du site
  (/opt/vokio-site-repo/design/audios/extraits.json). /opt/vokio-site/assets/appel-*.mp3 (22).
- ElevenLabs, clé pub dédiée `/root/.secrets/vokio-ads-elevenlabs` (jamais la clé de prod) :
  bruitages `POST /v1/sound-generation` {text, duration_seconds 0.5-22, prompt_influence} ✔ testé ;
  musique `POST /v1/music/plan` ✔ et composition `POST /v1/music` (composition_plan ou prompt,
  music_length_ms) ; TTS interdit ici pour un narrateur.
- Synthèse maison : python3 + numpy 1.26 (pas de scipy), ffmpeg complet (afir, aecho,
  sidechaincompress, loudnorm, stereotools, extrastereo, apulsator, aphaser, flanger, chorus,
  firequalizer, showwaves/showcqt pour des visuels audio-réactifs pré-calculés).
- Chaîne d'effets HyperFrames (`data-fx-chain`, `data-automation`, `<hf-audio-group>`).
- Tonalité de retour d'appel française : 440 Hz, 1,5 s on / 3,5 s off. Sonnerie de
  combiné : libre. Signature sonore Vokio : n'existe pas encore (à inventer).
- Livraison son : -14 LUFS intégré (réseaux sociaux), crête -1 dBTP, stéréo 48 kHz AAC.

## Où travailler
Projet : /opt/vokio-ads/videos/showcase/ (dépôt git vokio-ads). Sorties :
/root/vokio-uploads/videos/showcase/. Ne rien écrire en production (pas de base, pas de
n8n, pas de site, pas d'app). Pas de git push depuis un sous-agent.
