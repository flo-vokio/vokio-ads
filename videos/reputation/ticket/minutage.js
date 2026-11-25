/* « Le ticket » (Vokio Réputation n° 3, 25/11/2026) · LA source unique du minutage.
 * Lu par index.html (animation) ET par outils/salon.py (sons du salon posés sur les mêmes instants).
 * Tout est exprimé en TEMPS de musique : 96 BPM, un temps = 0,625 s, une mesure = 4 temps = 2,5 s ; film = 50 temps.
 * Ne rien écrire en secondes ailleurs : changer un instant ici déplace l'image ET le son.
 */
window.MINUTAGE = {
  bpm: 96,
  duree_temps: 50,
  plans: {                        // début de chaque plan, en temps
    accroche: 0, google: 5, geste: 10, sms: 19, semaine: 25, chute: 36, fin: 42
  },
  // Ticket 1 : les rangées 0 à 2 (en-tête double + ville) sont déjà sorties à l'image 0 ; avance = [temps, rangées]
  // la première avance tombe à 0 : le bruit de l'imprimante est le premier temps de la musique
  ticket1: { visibles: 3, avances: [[0, 1], [0.5, 1], [1, 1], [1.5, 1], [2, 1], [2.25, 1], [3, 1]], coupe: 4, retire: 4.25 },
  ticket2: { avances: [[5, 1], [5.5, 1], [5.75, 1], [6.5, 1], [6.75, 1], [7.5, 1]], sortie: 9.5 },
  geste: {
    legende: 10.25, carte: 10.75,
    numero: 11.5, pas: 0.25,      // 14 caractères du numéro, à la double croche
    prenom: 15.25,                // 6 caractères du prénom
    pleine: 16.75, presse: 17, note: 17.25, sortie: 18.75
  },
  sms: { legende: 19.25, telephone: 19.25, bulle: 20.5, sortie: 24.5 },
  semaine: {
    compteur: 25.25,
    tickets: [25.5, 27.5, 29.25, 31, 32.5, 34],     // chaque ticket se pose (accélère avec la musique)
    paliers: [[26.5, 48], [30.25, 50], [33.25, 53], [35, 56]],
    sortie: 35.75
  },
  chute: { imprimante: 36, avances: [[37, 1], [37.5, 1], [38, 1], [38.5, 1], [39, 1], [39.25, 1], [39.5, 1]],
           coupe: 40, retire: 41.5, sechoir: [36.25, 40] },
  fin: { halo: 42, mot: 42.4, sous: 43.4, phrase: 44.4, cta: 46.4, site: 47.4, mention: 46.4 }
};
