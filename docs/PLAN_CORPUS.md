# Plan « Corpus élargi » — récolte maximale, preuve forte, vérification humaine seule

Version 2026-11-17, révisée après les décisions du porteur (§8). Complète `docs/PLAN.md` : ce plan s'insère **avant le jalon J2** et remplace
les corpus tenus à l'écart prévus en J4/J5 par des volumes gelés issus de ce plan. Statut : plan,
rien n'est implémenté. Les disponibilités et licences citées ci-dessous sont des **hypothèses à
vérifier au lot C0**, sauf mention « vérifié ».

## 1. Objectif et principe

Obtenir le plus grand nombre possible de couples **œuvre identifiée ↔ passage d'auteur ↔ image
exploitable**, en peinture d'abord, sur les cinq plateformes déjà retenues (Met, Getty, Gallica,
Heidelberg, Cariatide/INHA), de sorte que le porteur n'ait plus qu'à **vérifier** des propositions
dans un pilote d'annotation prêt à l'emploi.

Trois idées structurent le plan :

1. **Récolte large, preuve forte uniquement.** À grande échelle, la machine ne propose un lien que
   sur preuve explicite (E0 : numéro d'inventaire ou d'accession, numéro de catalogue résolu ;
   E1 : structure de notice). Tout le reste est conservé comme `unresolved`. On maximise le volume
   sans dégrader la précision ; les méthodes plus fines (J2–J3) viendront ensuite sur ces mêmes
   données.
2. **Les images viennent des référentiels des musées, pas des PDF.** Les numéros d'accession
   cités dans les catalogues renvoient aux fiches des collections (Met Open Access, Getty Open
   Content…), dont les images d'œuvres du domaine public sont réutilisables. Extraire les figures
   imprimées est secondaire et réservé aux sources patrimoniales.
3. **Le porteur vérifie, il n'annote pas de zéro.** Chaque proposition arrive avec sa preuve
   surlignée ; une fraction tirée au hasard est présentée **à l'aveugle** (sans proposition) pour
   mesurer honnêtement la précision et le biais d'ancrage.

## 2. Filtre d'entrée et corpus candidats

### 2.1 Filtre d'entrée (décision du porteur, 2026-11-17)

Finalité : **datasets d'entraînement de modèles**, usage de recherche, aucun usage commercial,
porteur rattaché à un laboratoire de recherche de la BnF. Un volume n'est **traité** que s'il passe
les trois conditions suivantes ; sinon il n'est ni téléchargé ni extrait (il peut figurer dans
l'inventaire avec le motif d'exclusion).

1. **Texte réutilisable pour l'entraînement et le partage** : domaine public (auteurs morts depuis
   plus de 70 ans, vérifié par auteur ou par article) ou licence ouverte (CC0, CC BY, CC BY-SA,
   Licence Ouverte Etalab, conditions Gallica pour la réutilisation non commerciale). Une œuvre
   sous droits, même lisible gratuitement et même couverte par l'exception de fouille de l'art. 3,
   est exclue, car le dataset ne pourrait pas être partagé.
2. **Image d'œuvre exploitable** pour au moins une partie des notices : œuvre du domaine public et
   reproduction libre (CC0, domaine public, licence ouverte ; en droit de l'UE, l'art. 14 de la
   directive 2019/790 exclut tout droit nouveau sur la reproduction fidèle d'une œuvre d'art du
   domaine public, sous réserve des conditions d'utilisation des sites, à consigner).
3. **Langue** : anglais ou français.

Obligations à propager dans les exports : attribution (CC BY), partage à l'identique (CC BY-SA :
le dataset dérivé hérite de la licence), mention de source Gallica. Voir C1.

Conséquences sur la première version : les catalogues récents du Met et du Getty (texte sous droits)
sont **exclus du traitement** ; le Met et le Getty restent utiles comme **référentiels d'œuvres et
sources d'images** (Met Open Access CC0, Getty Open Content) et pour leurs publications anciennes du
domaine public ou sous licence ouverte. Les corpus en allemand sont exclus.

### 2.2 Corpus candidats, par vague

Critères de pertinence (notés au lot C0, grille §4) : densité analytique, identifiabilité des
œuvres, droits image, qualité du texte, effort technique.

#### Vague 1 — peinture, français, domaine public (Gallica / BnF)

| Corpus | Pourquoi | Identification | Images |
|---|---|---|---|
| Notices et catalogues des peintures du Louvre du XIXᵉ siècle (ex. Villot ; éditions successives) | notices numérotées, descriptions, attributions historiques ; plusieurs éditions = histoire des attributions | anciens numéros → concordance avec les inventaires actuels (base des collections du Louvre, POP/Joconde), à sourcer | collections nationales et Wikimedia Commons (domaine public), conditions à consigner |
| *Gazette des Beaux-Arts*, articles sur la peinture dont les auteurs sont morts depuis plus de 70 ans | articles très analytiques, planches | mentions + collections citées ; résolution plus difficile (E2) | planches du domaine public (coordonnées ALTO) + images des musées |
| Catalogues de musées de province du XIXᵉ–début XXᵉ siècle | notices de peintures, souvent numérotées | numéros de catalogue → concordance Joconde | idem |
| Autres revues d'art du domaine public (ex. *Revue de l'art ancien et moderne*) | articles analytiques illustrés | mentions | planches |

Atout : rattachement du porteur à la BnF. **Question** : un accès en masse (ALTO, IIIF, API Gallica,
services du BnF DataLab) est-il possible ? Cela réduirait fortement C3.

#### Vague 2 — peinture, anglais, identification forte

| Corpus | Pourquoi | Identification | Images |
|---|---|---|---|
| Publications anciennes du Met dans le domaine public (premiers catalogues de peintures, *Bulletin* des premières décennies ; auteur par auteur) | notices et articles sur des œuvres toujours au Met | numéros d'accession ou titres → résolution par l'API Collection v1.1 | **Met Open Access CC0** (`isPublicDomain`, vérifié sur un objet) |
| Publications Getty sous licence ouverte portant sur la peinture (ex. *Mummy Portraits of Roman Egypt*, texte CC BY vérifié) et autres titres Quire à identifier en C0 | texte CC BY, structure native | numéros de musées, mentions | Getty Open Content ; images de tiers souvent exclues de la licence (vérifié pour *Mummy Portraits*) |

#### Vague 3 — contrastif (français / anglais)

| Corpus | Plateforme | Usage |
|---|---|---|
| Catalogues de vente illustrés de peintures du domaine public | Cariatide/INHA (Licence Ouverte à vérifier par notice), Heidelberg (titres français et anglais seulement ; licence des numérisations à vérifier, CC BY-SA probable) | notices courtes : cas négatifs, histoire des attributions et des provenances, beaucoup de `unresolved` |
| Catalogues Quire non picturaux déjà outillés (*Terracottas*, *Roman Mosaics*, *Ancient Lamps*, CC BY) | Getty | corpus de développement et de contrôle |

## 3. Lots

Légende : **H** = point de contrôle du porteur ; agent conseillé entre parenthèses.

### C0 — Inventaire et notation des volumes (Haiku ×5 en parallèle, consolidation Sonnet)
- Un agent par plateforme : lister 10 à 30 volumes candidats (peinture prioritaire), et pour chacun
  vérifier en ligne : URL, type, période, langue, formats (PDF texte, IIIF, ALTO, METS, HTML),
  présence d'identifiants d'œuvres dans un échantillon de pages, nombre estimé de notices, licence
  du texte, des images, conditions de TDM et réserve éventuelle, date de consultation.
- Sorties : `docs/sources/inventory.yaml` (un enregistrement par volume) et une fiche par
  plateforme `docs/sources/<plateforme>.md`.
- Notation automatique par la grille §4, sans lecture des textes au-delà de l'échantillon
  nécessaire au comptage d'identifiants.
- Tirage **gelé** des volumes tenus à l'écart : environ 20 % par vague, graine fixée, empreinte dans
  `gold/heldout-volumes.yaml`. Ces volumes ne servent jamais au réglage.
- **H-C0** (~30 min) : le porteur approuve la sélection et la liste des volumes tenus à l'écart.

### C1 — Fiches de droits par plateforme et par action (Haiku, relecture orchestrateur)
- Pour chaque plateforme : décisions `allow / deny / unknown / conditional` par actif (texte,
  image de page, image d'œuvre, métadonnées) et par action (téléchargement, stockage, TDM,
  LLM distant, affichage dans le pilote, publication, redistribution, entraînement), avec preuve.
- Statut de domaine public établi **par auteur** (dates de décès sourcées : BnF data, IdRef, VIAF) et
  consigné ; à défaut, `unknown` → volume ou article exclu (filtre §2.1).
- Règle d'export par défaut : **standoff** (identifiants, pages, offsets, URI, image par URL quand
  la licence le permet) ; texte intégral exporté seulement si `allow`.
- Critère : aucun volume n'entre en C3 sans fiche de droits.

### C2 — Référentiels d'œuvres et images (Sonnet)
- Cache local des fiches de collection pour les départements concernés : Met (peintures
  européennes, via l'API v1.1), Getty (données de collection), collections nationales françaises
  (base des collections du Louvre, POP/Joconde) avec concordances des anciens numéros, et Wikidata en
  appoint, avec provenance de chaque attribut.
- Pour chaque œuvre : identifiants externes, numéro d'accession, titre, artiste, date,
  département, URL et licence de l'image, statut domaine public.
- Sert de **liste fermée de candidats** et de source d'images. Aucune fusion d'œuvres automatique.

### C3 — Acquisition des volumes sélectionnés (Sonnet)
- Un lecteur par voie, pas par plateforme : HTML Quire (existant), PDF (publications anciennes du Met,
  Getty sous licence ouverte), IIIF + ALTO (Gallica, Heidelberg, Cariatide).
- Cache `data/raw/` avec empreinte, date de capture, budgets (pages, octets, requêtes par job),
  politesse réseau ; 403 consigné et arrêt.

### C4 — Extraction minimale (Sonnet)
- PDF : texte et coordonnées des mots via PyMuPDF (suffisant pour détecter les identifiants et
  ancrer les passages) ; le benchmark Xberg / Docling reste en J5.
- ALTO : blocs, lignes et illustrations avec leurs coordonnées ; `text_fidelity = ocr_raw`.
- Segmentation en notices et paragraphes ; table d'ancrage page ↔ offsets.

### C5 — Propositions à preuve forte (Sonnet ; revue par agent frais)
- Détecteurs E0 par institution : formats de numéros d'accession (Met, Getty), numéros de
  catalogue internes, appels `fig. / pl. / cat. / Abb. / Taf.`.
- E1 : héritage du sujet dans une notice à entrée unique.
- Un lien n'est proposé que si l'identifiant **se résout** dans le référentiel C2 ; sinon
  `unresolved` avec la raison.
- Fonction du passage : `unclassified` à ce stade (J3 viendra plus tard).

### C6 — Pilote d'annotation (Sonnet ; préparé en parallèle de C2–C5)
- Application locale (page web servie depuis le conteneur) :
  - à gauche : image de l'œuvre (si l'affichage est permis), métadonnées, lien vers la fiche du
    musée ;
  - au centre : passage exact, identifiant surligné, lien vers la page source (PDF à la page,
    visionneuse IIIF) ;
  - à droite : boutons valider / rejeter / non résolu, relation (`about`, `group`, `context`,
    `mentions`), fonction, note ;
  - raccourcis clavier ; reprise exacte après interruption.
- File priorisée : diversité des volumes et des types de preuve d'abord ; **15 % des éléments
  présentés à l'aveugle** (sans proposition) pour la mesure.
- Chaque décision = `AnnotationEvent` append-only ; export vers `gold/`.
- Critère : session d'essai de 20 éléments sur *Terracottas* et un premier volume Gallica, sans
  perte après redémarrage.

### C7 — Contrôle qualité et tableau de bord (Haiku sur les JSON de métriques)
- Par volume et par vague : notices, passages, liens proposés par type de preuve, `unresolved`,
  œuvres avec image exploitable, liens vérifiés, précision mesurée sur l'échantillon aveugle,
  temps de vérification par élément.
- Sortie : `reports/corpus/<date>.md`.

### Sessions de vérification (H)
- Par blocs d'environ 1 h ; cible indicative 200 à 400 éléments E0 à l'heure (à mesurer en C6).
- Après la première session : mesure de la précision E0 par corpus ; si elle est inférieure à
  0,95 sur un corpus, arrêt de la récolte sur ce corpus et analyse d'erreurs.

## 4. Grille de notation des volumes (C0)

| Critère | 0 | 1 | 2 |
|---|---|---|---|
| Densité analytique (échantillon de pages) | listes, inventaire | notices descriptives | notices argumentées, essais |
| Identifiabilité | aucun identifiant | numéros internes seulement | numéros d'accession ou d'inventaire actuels |
| Images d'œuvres | aucune réutilisable | affichage seulement | réutilisation ouverte (CC0, domaine public) |
| Texte | droits inconnus | TDM de recherche seulement | licence ouverte ou domaine public |
| Qualité du texte | OCR inutilisable | OCR brut correct | natif ou corrigé |
| Effort | nouvelle voie technique | voie existante + adaptation | voie existante |

Sélection : peinture d'abord, score total ≥ 8 sur 12, en gardant quelques volumes faibles pour ne
pas surestimer le pipeline.

## 5. Ordre d'exécution et parallélisme

```
C0 ──► H-C0 ──► C1 ──┬─► C2 (par vague) ──┐
                     └─► C3 ─► C4 ─► C5 ──┼─► sessions H ─► C7 ─► J2 (règles fines)
C6 (pilote) ──────────────────────────────┘   (démarre dès maintenant, en parallèle)
```

La vague 1 traverse C2 → C5 en entier avant le démarrage de la vague 2. C0 et C1 portent sur les trois vagues à la fois.

## 6. Articulation avec `docs/PLAN.md`

- **J1** reste valable : le guide d'annotation est étendu à la peinture (cas : copie, atelier,
  « attribué à », pendants, détails) avant la première session ; le pilote C6 remplace la feuille
  CSV pour les gros volumes.
- **J2–J3** (mentions, coréférence, fonction) se développeront sur les volumes de développement de
  ce plan, et leur rappel se mesurera sur les liens `unresolved` collectés ici.
- **J4–J5** utilisent les volumes gelés de C0 au lieu de *Roman Mosaics* et *Mummy Portraits* seuls.
- **J6** (dataset) exporte selon les fiches C1.

## 7. Risques

| Risque | Réponse |
|---|---|
| Domaine public incertain (auteur inconnu, date de décès introuvable, article collectif) | exclusion par défaut ; `unknown` n'est jamais traité comme domaine public |
| Licence CC BY-SA d'une source | le dataset dérivé est publié sous CC BY-SA ; séparer les sources par licence dans les exports |
| Volume supérieur à la capacité de vérification d'une seule personne | file priorisée, échantillon aveugle, précision mesurée par corpus plutôt que vérification exhaustive |
| Ancrage sur les propositions | 15 % à l'aveugle, accord mesuré entre vérification et aveugle |
| Identifiants mal lus (OCR, coupures de ligne) | proposition seulement si l'identifiant se résout dans le référentiel ; sinon `unresolved` |
| Concordances patrimoniales (anciens numéros) incertaines | vague 1 sans lien automatique tant que la concordance n'est pas sourcée ; la construction de la concordance est elle-même une tâche vérifiée |
| Moins d'identifiants explicites dans les textes anciens | E0 plus rare : prévoir plus de `unresolved` et une part plus grande de vérification ; mesurer en C0 avant de s'engager |
| Dispersion technique (cinq plateformes à la fois) | lecteurs par voie, vagues successives, une vague terminée avant la suivante |

## 8. Décisions du porteur (2026-11-17) et questions restantes

Décisions :
- rattachement à un laboratoire de recherche de la BnF ; aucun usage commercial ;
- vérification en anglais et en français ;
- ne pas traiter ce qui serait inutilisable pour des raisons de droit d'auteur ;
- finalité : datasets d'entraînement de modèles.

Questions restantes :
1. Accès en masse aux données Gallica (ALTO, IIIF, API, BnF DataLab) possible via le laboratoire ?
2. Temps de vérification disponible par semaine ?
3. Les datasets seront-ils publiés hors du laboratoire ? (Détermine la gestion des licences
   CC BY-SA et des conditions Gallica dans les exports.)
