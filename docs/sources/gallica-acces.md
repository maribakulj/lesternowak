# Gallica — points d'accès et quotas utilisés par LesterNowak

Source : information transmise par le porteur (laboratoire de recherche de la BnF), 2026-11-17.
Les accès historiques `gallica.bnf.fr` sont bloqués (Cloudflare) ; la passerelle
`https://openapi.bnf.fr` les remplace. Quotas « anonymes » **par IP**, en cours de validation ; ils
peuvent baisser ou monter. Documentation de référence : portail https://api.bnf.fr (mise à jour en
cours). Seuls les services utiles au projet sont listés ici.

**Plafond global : 75 requêtes par minute et par IP, toutes API Gallica confondues.**

| Besoin | Point d'accès (passerelle) | Quota / IP | Usage prévu |
|---|---|---|---|
| Recherche de documents | `/recherche/sru/gallica/1.0.0/sru` | 10 req/min | constitution de l'inventaire (C0) |
| Notice OAI-DC | `/document/oaidc/gallica/1.0.0/OAIRecord` | aucun spécifique | métadonnées, droits affichés |
| Pagination (folios ↔ vues) | `/document/pagination/gallica/1.0.0/Pagination` | aucun spécifique | correspondance pages imprimées / vues |
| Table des matières | `/document/tdm/gallica/1.0.0/Toc` | aucun spécifique | structure, repérage des notices |
| Fascicules de périodiques | `/date/periodique/gallica/1.0.0/Issues` | aucun spécifique | *Gazette des Beaux-Arts*, revues |
| Texte brut du document entier | `/texte/brut/gallica/1.0.0/ark:/{repo}/{id}.texteBrut` | 6 req/min | **une requête par volume** : repérage des pages utiles |
| Texte brut d'une page | `/texte/brut/gallica/1.0.0/ark:/{repo}/{id}/f{n}.texteBrut` | 20 req/min | contrôle ponctuel |
| Recherche plein texte (occurrences / positions) | `/occurence/texte/…/ContentSearch` ; `/position/texte/…/ContentSearch` (avec `page`) | aucun spécifique | trouver identifiants et noms sans télécharger l'OCR |
| OCR ALTO d'une page | `/texte/ocr/gallica/1.0.0/RequestDigitalElement?O={id}&E=ALTO&Deb={n}` (6 req/min ; syntaxe vérifiée au lot C3, répond là où le v3 renvoie 404) ou IIIF v3 `…/presentation/v3/ark:/{repo}/{id}/f{n}/alto.xml` (5 req/min) | 5–6 req/min | **pages utiles seulement** (coordonnées, illustrations) |
| Structure logique (OLR, METS) | IIIF v3 `…/presentation/v3/ark:/{repo}/{id}/olr.xml` | 5 req/min | sections, articles, illustrations |
| Manifeste IIIF | v2 `/presentation/iiifv2/gallica/1.0.0/ark:/{repo}/{id}/manifest.json` ; v3 `…/presentation/v3/ark:/{repo}/{id}/manifest.json` | 5 req/min | liste des vues, dimensions |
| Image précalculée | `/image/gallica/1.0.0/{ark}/f{n}.{thumbnail,lowres,medres,highres}` | 50 req/min | **affichage dans le pilote** (lowres/medres) |
| Image IIIF (région, taille) | v2 `/image/iiifv2/gallica/1.0.0/ark:/{repo}/{id}/f{n}/{region}/{size}/{rotation}/{quality}.{format}` ; v3 `/image/iiif/gallica/1.0.0/image/v3/…` | 10 Mo/min (à confirmer) | recadrage des figures seulement |

Chemins préfixés par `https://openapi.bnf.fr`. Le préfixe IIIF v3 complet est
`https://openapi.bnf.fr/presentation/iiif/gallica/1.0.0/presentation/v3/`.

## Stratégie d'acquisition sous quotas (lot C3)

1. Par volume, en requêtes uniques : notice OAI, pagination, table des matières, OLR, manifeste,
   texte brut entier.
2. Repérage des pages utiles par le texte brut ou `ContentSearch` (numéros, noms, « fig. », « pl. »).
3. ALTO **uniquement** pour ces pages ; images précalculées `medres` pour la revue ; IIIF Image
   seulement pour recadrer une figure.
4. Limiteur par service (requêtes/minute), par volume transféré (octets/minute) et plafond global
   partagé ; `Retry-After` respecté ; arrêt après 403 ou 429 répétés ; cache permanent.

Ordre de grandeur pour un volume de 400 vues dont 60 pages utiles : environ 6 requêtes de
structure, 60 ALTO (environ 12 min à 5–6 req/min), 60 images `medres` (environ 1–2 min), soit
**environ 15 minutes par volume**. Le banc C3 mesurera les durées réelles et les refus, ce qui
fournira aussi un retour chiffré sur l'adéquation des quotas anonymes.
