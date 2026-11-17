# Sonde Gallica via openapi.bnf.fr — lot C0 (2026-11-17)

Volume sondé : `bpt6k73772x` (Villot, *Notice des tableaux…*, 1849, 221 vues). Aucun contenu de
document n'est copié ici ; les réponses brutes restent hors dépôt (scratchpad de session).

## Requêtes de la sonde

| Besoin | URL (préfixe `https://openapi.bnf.fr`) | HTTP | Taille | Content-Type | Résultat |
|---|---|---|---|---|---|
| Manifeste IIIF v2 | `/presentation/iiifv2/gallica/1.0.0/ark:/12148/bpt6k73772x/manifest.json` | 200 | 226 675 o | application/json;charset=UTF-8 | 221 canvases, cohérent avec « Nombre total de vues : 221 » |
| ALTO IIIF v3, vue f10 | `/presentation/iiif/gallica/1.0.0/presentation/v3/ark:/12148/bpt6k73772x/f10/alto.xml` | **404** | 175 o | application/json | « Cannot find ALTO XML associated with image » |
| Image précalculée | `/image/gallica/1.0.0/ark:/12148/bpt6k73772x/f10.lowres` | 200 | 14 133 o | image/jpeg;charset=UTF-8 | image lowres obtenue |
| ALTO `RequestDigitalElement`, vue f10 (paramètre `ark=` deviné, non documenté) | `/texte/ocr/gallica/1.0.0/RequestDigitalElement?ark=ark:/12148/bpt6k73772x/f10` | 500 | 95 o | application/json | erreur générique ; **test non concluant** (syntaxe non établie) |

Sonde complémentaire (une requête de plus, volume `bpt6k97965685`, 1855, « Avec mode texte ») :

| Besoin | URL | HTTP | Taille | Content-Type | Résultat |
|---|---|---|---|---|---|
| ALTO IIIF v3, vue f10 | `/presentation/iiif/gallica/1.0.0/presentation/v3/ark:/12148/bpt6k97965685/f10/alto.xml` | 200 | 65 806 o | application/xml; charset=UTF-8 | XML ALTO reçu (contenu non examiné au-delà de sa validité d'en-tête) |

## Constats

- **ALTO accessible par la passerelle** pour le volume 1855 (IIIF v3 `alto.xml`, 200). Le 404 sur
  le volume 1849 est une réponse de l'API (« ALTO introuvable pour cette image ») : cohérent avec une
  notice qui ne mentionne pas « mode texte », mais **une seule vue testée** ; ne pas généraliser.
- **Images précalculées** accessibles (lowres, 200).
- **Manifeste** accessible et cohérent avec la notice SRU.
- **Quotas** : aucun en-tête `Retry-After`, `X-RateLimit-*` ou équivalent dans les réponses. Les
  quotas de `gallica-acces.md` ne sont donc pas vérifiables par en-têtes ; ils ont été respectés
  par espacement des requêtes.
- Le préfixe IIIF v3 réel est `…/presentation/iiif/gallica/1.0.0/presentation/v3/` (et non
  `…/presentation/v3/` seul).

## Requêtes faites pendant le lot C0 (total : 15)

- SRU (recherche) : 10 au total, dont 1 requête « sonde » et 9 de recherche. Une requête SRU a
  retourné `Connection reset by peer` (curl 35) et n'a pas été relancée.
- Sonde : 5 (manifeste, ALTO f10 du 1849, lowres f10, `RequestDigitalElement` testé sans succès,
  ALTO f10 du 1855).
- Espacement SRU : 7,5 s minimum entre deux requêtes SRU à partir de la 2e (`sru2` à `sru9`).
  **Écart connu** : les deux premières requêtes SRU (exécutées en tout début de lot) ont été
  espacées d'environ 5 s seulement, sans mesure précise ; à signaler.

## Limites

- Les formes `RequestDigitalElement` et ses paramètres ne sont pas établies : à vérifier dans la
  nouvelle documentation api.bnf.fr avant toute utilisation.
- Aucune requête `Pagination`, `Issues` ou `Toc` ; aucune requête OAIRecord (les notices SRU
  contiennent déjà les champs `dc:*`).

## Usage des quotas, lot C0 complément (2026-11-17)

Appelant unique d'`openapi.bnf.fr` pendant ce complément ; limiteur local (espacement minimal par
service : SRU 7 s, texteBrut document entier 11,5 s, autres 2,5 s ; script hors dépôt). Aucun texte
de document n'est conservé dans le dépôt, seulement des comptages (`sample:`) et des métadonnées.

| Service (passerelle) | Requêtes | Réponses non 200 |
|---|---|---|
| SRU (`/recherche/sru`) | 4 | aucune |
| Issues (`/date/periodique/.../Issues`) | 6 | aucune |
| Toc (`/document/tdm/.../Toc`) | 6 | aucune |
| OAIRecord (`/document/oaidc/.../OAIRecord`) | 6 | aucune |
| texteBrut, document entier | 33 (29 volumes ; 4 relances) | 2 × `Connection reset by peer` (curl 35), 2 × HTTP 500 |
| Pagination, ALTO, manifestes, images | 0 | sans objet |
| **Total openapi.bnf.fr** | **55** | 4 échecs transitoires, tous réussis à la relance unique |

- **Aucun 429, aucun 403.** Pic mesuré : 12 requêtes dans une fenêtre de 60 s (toutes API
  confondues, plafond 75) ; texteBrut : 4 par fenêtre de 60 s au maximum (quota 6), écart minimal
  13,5 s ; SRU : 4 par fenêtre de 60 s (quota 10), écart minimal 9,2 s.
- **Échecs transitoires de texteBrut** (volumes `bpt6k97965685`, `bpt6k6234712c` : connexion
  réinitialisée ; `bpt6k1253202g`, `bpt6k1249980p` : HTTP 500 sans corps utile). Réessayés une fois
  après le délai d'espacement habituel, tous ont réussi. Pas de `Retry-After` dans les réponses
  d'erreur. Les 500 et resets semblent liés au service plutôt qu'aux quotas (plus de marge sous
  les plafonds) ; à signaler à l'équipe BnF : le client doit prévoir une relance unique espacée.
- **Format texteBrut document entier** : texte brut avec `<br/>` ; le séparateur `</BR>` marque les
  sauts de page (nombre de pages = vues pour le volume 1849 : 220 séparateurs, 221 vues). Pour
  certains volumes le nombre de pages du texteBrut diffère des « Nombre total de vues » de la
  notice (ex. catalogue de vente 1928 : 110 pages pour 158 vues) : à vérifier en C3.
- Taille : 20 Ko à 1,1 Mo de texte par volume ; la durée dominante est le délai d'espacement
  (≈ 14 s par volume en pratique) : 29 volumes en environ 7 minutes.
- Issues renvoie des **volumes semestriels** pour la *Gazette des Beaux-Arts* (2 arks par année) et
  parfois des doublons d'arks (ex. 1875, 1910 pour la *Revue de l'art ancien et moderne*) ; la
  Toc est en XML TEI, encodage déclaré ISO-8859-1 mais contenu UTF-8 pour la *Revue* : décoder
  d'abord en UTF-8.
- IA : 2 téléchargements `djvu.txt` (Internet Archive, hors BnF) pour les catalogues Met retenus.
