# Référentiels d'œuvres locaux (lot C2)

Caches JSONL sous `data/ref/<source>.jsonl` (ignorés par Git), modèle `ReferenceArtwork`
(`src/lesternowak/referentials.py`). Ils servent de **liste fermée de candidats** au résolveur
E0 / E2 composite (ADR 0003) et de source d'images quand la licence le permet. Aucune fusion
automatique entre sources : `ref_id = <source>:<id externe>`.

Commandes : `lesternowak ref-build met --department "European Paintings"` (reprise incrémentale :
les `external_id` déjà en cache sont sautés) ; `lesternowak ref-build louvre --limit 500`.

## Met (European Paintings)

- Source : API Collection du Met, `GET /public/collection/v1/departments`, puis
  `/v1/objects?departmentIds=11` (liste d'identifiants), puis `/v1/objects/{id}`.
  La recherche `/v1/search` n'est pas utilisée ; la page https://metmuseum.github.io/ (consultée le
  2026-11-17) signale un nouveau point `/public/collection/v1.1/search` paginé, non nécessaire ici.
- Réutilisation (même page, 2026-11-17) : « we do not require API users to register or obtain an API
  key » ; « Please limit request rate to 80 requests per second ». Nous restons à 2,5 req/s,
  backoff exponentiel sur 429/5xx, `Retry-After` respecté, 403 = arrêt (jamais contourné).
- Images : `primaryImage` est conservée **seulement** si `isPublicDomain` (Open Access du Met,
  CC0) → `image_license = cc0`. Sinon `image_url` vide (`restricted` si une image existe).
- Champs disponibles : accession, titre, artiste et dates, date, médium, dimensions (texte en
  pouces et cm ; `dimensions_cm` en repli sur `measurements`), `creditLine`, `accessionYear`,
  département, URL de fiche. **Pas d'anciens numéros de catalogue** dans l'API (`other_numbers`
  vide) : les concordances anciens numéros ↔ Met ne sont donc pas possibles par cette source.
- Volumes, durées, taux de présence : voir la section « Résultats mesurés » ci-dessous.

## Louvre : impasse partielle, échantillon Joconde

Investigation du 2026-11-17.

1. **collections.louvre.fr** : chaque fiche existe en JSON (`/ark:/53355/cl0100xxxxx.json`) avec
   `objectNumber` typés (« Numéro principal », « Autre numéro d'inventaire », ex. INV 779 + MR 316),
   `collection`, `dimension`, `acquisitionDetails`, `image` (avec mention © GrandPalaisRmn).
   Mais : aucune liste ouverte ni export en masse ; la recherche (`/recherche?...`) renvoie une page de
   vérification anti-robot (« I am not a robot ») et la page de conditions d'utilisation n'est
   rendue que par JavaScript (non lue). Énumérer les identifiants ark à l'aveugle serait du
   moissonnage non autorisé : **non fait**. Les images du Louvre portent un © : droits `unknown`.
2. **Base Joconde** (POP, data.gouv.fr, jeu `5b448216a3a729752eb11d6f`, licence « lov2 » =
   Licence Ouverte 2.0, vérifié par l'API data.gouv.fr le 2026-11-17) : CSV de 1,25 Go
   (`ministere-culture.s3.sbg.io.cloud.ovh.net/POP/joconde.csv`, séparateur `|`, 206 colonnes, mis à
   jour chaque mercredi). L'API Explore de data.culture.gouv.fr n'est plus exposée (redirection 301
   vers une application JavaScript). Le Louvre y figure : 5 446 fiches « peinture » (référence
   `000PE…`), 4 885 avec image signalée, 5 236 avec mesures, 3 644 avec date d'acquisition.
   `Numero_inventaire`, `Date_d_acquisition`, `Mesures` (cm, « 41 H ; 52 L »), `Ancienne_appartenance`
   (provenance, **pas** une ligne de crédit) existent.
3. **Anciens numéros** : pas de champ structuré. Seuls cas sourçables : numéros multiples dans
   `Numero_inventaire` (49 fiches sur 5 446, ex. « MV 3678 ; INV 3229 ; MR 1576 ») et renvois de
   `Bibliographie` (« Villot II 365 », « Suppl. Tauzia 809 », ≈ 10 fiches). Les numéros Villot / Both de
   Tauzia ne sont donc **pas** disponibles en volume en open data. Sur l'échantillon de 500 fiches
   construit par `ref-build louvre`, une seule fiche porte un ancien numéro. Aucune concordance n'est
   inférée du texte libre.
4. `ref-build louvre` : lecture en flux (une seule requête, fichier non conservé), arrêt à 500 fiches
   (ici 31 612 lignes lues, ≈ 3 s). Pas d'URL d'image dans Joconde : `image_url` vide, licence
   d'image `unknown`. `credit_line` = `Ancienne_appartenance` (provenance) : à ne pas apparier comme une
   ligne de crédit de musée.

Pistes restantes : demander au Louvre un export / accord pour sa base ; numériser les tables de
concordance Villot ↔ INV depuis les catalogues eux-mêmes (corpus C0, sourcées) ; Joconde ne couvre pas
les anciens numéros.

## Limites générales

- `credit_line` et `accession_year` du Met ne sont pas totalement indépendants (l'année figure dans
  la ligne de crédit) : le résolveur les compte comme deux signaux selon l'ADR 0003 ; à réexaminer à la
  mesure (C7).
- La tolérance dimensionnelle (± 2 cm) donne des collisions sur les séries (ex. les allégories de
  Tiepolo : dimensions et crédit identiques) ; le résolveur refuse alors (≥ 2 candidats).
- Getty et Wikidata ne sont pas encore construits (hors périmètre de ce lot).

## Résultats mesurés (2026-11-17)

- Met, département « European Paintings » (id 11) : **2 650 objets** listés et récupérés
  (0 × 404), en deux passes à 2,5 req/s max (une première interrompue par un 403 après 400 objets,
  consigné comme statut et non contourné ; reprise ensuite sans incident : 2 250 objets en 1 067 s,
  soit ≈ 18 min ; ≈ 2 req/s effectifs). Cache : `data/ref/met.jsonl`.
- Images : 2 367 objets avec `image_license = cc0` (89,3 %) ; les autres sans URL d'image.
- Présence des champs : numéro d'accession 100 %, ligne de crédit 100 %, année d'accession 100 %,
  `dimensions_cm` exploitables 99,9 %.
- Louvre (Joconde) : échantillon de 500 fiches, dimensions 227/500 (le reste en formats non
  « H ; L »), un seul ancien numéro.
