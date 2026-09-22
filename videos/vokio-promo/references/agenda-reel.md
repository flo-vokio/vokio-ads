# L'agenda du plan 04 — relevé du vrai écran

Florian a tranché : on n'est pas obligé de capturer app.vokio.fr. On reconstruit.
Mais « reconstruire » ne veut pas dire « inventer » : un agenda dessiné au jugé
se voit, et c'est exactement ce que la règle « aucun chrome d'interface factice »
cherche à éviter. Les valeurs ci-dessous sont relevées dans
`/opt/vokio-client/src/components/AgendaPro.tsx`, l'écran que voient les clients.

Source relevée le 22/09/2026. Si l'agenda change, ce fichier ment : le relever
à nouveau avant de retoucher le plan 04.

## Grille

| Élément | Valeur réelle |
| --- | --- |
| Hauteur d'une heure | `52 px` (`HOUR_PX`) |
| Colonne des heures | largeur `44 px`, étiquette mono `10 px`, centrée sur le trait |
| En-tête de jour | mono `10 px`, capitales, interlettrage élargi ; le jour courant en encre solaire |
| Colonne d'un jour | coins `8 px`, fond encre à 2 % ; le jour courant en solaire à 5 % |
| Traits d'heure | filet haut `1 px`, encre à **6 %** |

Tout est en filets et en aplats très pâles : aucune bordure franche, aucune
ombre. C'est ce qui fait que l'écran réel a l'air calme, et c'est ce qu'une
reconstruction ratée alourdit toujours.

## La carte d'un rendez-vous

C'est l'objet qui se pose à l'écran dans le plan 04, donc le seul qui doit être
juste au pixel près.

| Propriété | Valeur réelle |
| --- | --- |
| Fond | solaire à **20 %** (`rgba(239,164,36,0.20)`) |
| Filet | `1 px` solaire à **55 %** (`rgba(239,164,36,0.55)`) |
| Coins | `6 px` |
| Marges | `6 px` horizontal, `4 px` vertical |
| Texte | encre pleine, `11 px`, interligne serré |
| Ligne 1 | le nom du client, graisse moyenne |
| Ligne 2 | `08:30 · Prestation`, opacité `0.70` |
| Sous `34 px` de haut | les deux lignes se replient en une seule |

La carte est donc **du solaire pâle cerné d'un filet solaire**, sur papier. Elle
tombe dans le vocabulaire de `frame.md` sans rien forcer : c'est la même DA.

## Le mouvement

L'écran réel pose un rendez-vous avec `transition: top .18s ease`. C'est court,
et c'est le bon repère : dans le film, le créneau ne doit pas flotter ni rebondir.
Il se pose. Un ressort cartoon sur cet objet trahirait immédiatement la
reconstruction.

## Ce qu'on ne montre pas

- Aucun numéro de téléphone, même tronqué.
- Aucun nom de client réel. Le plan 04 réutilise la fiction déjà publique du
  site : Plomberie Azur, et une demande de fuite sous évier.
- Pas de barre de navigation, pas d'onglets, pas de fenêtre de navigateur. On
  montre la grille et la carte, rien autour. Trois éléments simultanés au
  maximum, la règle tient aussi ici.
