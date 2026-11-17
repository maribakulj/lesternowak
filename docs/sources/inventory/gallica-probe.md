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
