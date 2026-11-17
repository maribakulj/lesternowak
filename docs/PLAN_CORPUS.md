# Plan « Corpus élargi » — récolte maximale, preuve forte, vérification humaine seule

Version 2026-11-17. Complète `docs/PLAN.md` : ce plan s'insère **avant le jalon J2** et remplace
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

## 2. Corpus candidats, par vague

Critères de pertinence (notés au lot C0, grille §4) : densité analytique, identifiabilité des
œuvres (identifiants dans le texte), droits image, droits texte et TDM, qualité du texte (natif /
OCR), langue, effort technique.

### Vague 1 — peinture, identification forte, images ouvertes (priorité)

| Corpus | Plateforme | Pourquoi | Identifiants | Images | Texte |
|---|---|---|---|---|---|
| Catalogues de peintures du Met en PDF gratuits (ex. catalogues systématiques de peinture hollandaise, flamande, italienne, française ; catalogue sommaire des peintures européennes) | MetPublications | notices longues et savantes ; liste « œuvres du Met dans cette publication » = candidats fermés | numéros d'accession (`29.100.6`) dans chaque notice → E0 | API Collection, `isPublicDomain` (vérifié sur un objet) | © Met : lecture et TDM de recherche à qualifier ; export standoff |
| Bulletins et journaux du Met (*Metropolitan Museum Journal*, *Bulletin*) | MetPublications | articles analytiques avec figures | numéros d'accession fréquents | idem | idem |
| Catalogues de peintures du Getty et *J. Paul Getty Museum Journal* (bibliothèque virtuelle Getty) | Getty Publications | notices et articles sur les peintures du musée | numéros `78.PA.1` (PA = peinture) → E0 | Getty Open Content | © Getty, téléchargement libre : droits de réutilisation à qualifier |
| *Mummy Portraits of Roman Egypt* | Getty (Quire) | portraits peints ; texte CC BY (vérifié) | mentions et numéros de musées | majorité des images exclues de la CC BY (vérifié) ; images des musées à résoudre | CC BY 4.0 (vérifié) |

### Vague 2 — patrimonial, domaine public, français et allemand

| Corpus | Plateforme | Pourquoi | Identifiants | Images | Texte |
|---|---|---|---|---|---|
| Notices des peintures du Louvre du XIXᵉ siècle (ex. *Notice des tableaux* de Villot) | Gallica | notices numérotées, descriptions et attributions historiques | anciens numéros → concordance à établir avec les inventaires actuels | planches éventuelles ; images actuelles via les collections du Louvre (conditions à vérifier) | domaine public ; conditions Gallica (réutilisation non commerciale libre) |
| *Gazette des Beaux-Arts*, sélection d'articles sur la peinture (auteurs morts depuis plus de 70 ans) | Gallica | articles très analytiques, planches | mentions, collections citées | planches gravées/photographiques du domaine public, coordonnées ALTO | domaine public selon l'auteur ; OCR à qualifier |
| Catalogues savants de galeries allemandes (ex. Berlin, Munich, Dresde, fin XIXᵉ–début XXᵉ) | Heidelberg | notices de peintures, attributions argumentées | numéros de catalogue historiques | planches, IIIF | domaine public ; licence des numérisations à vérifier ; OCR « sale » |
| *Zeitschrift für bildende Kunst*, *Kunstchronik* (sélection peinture) | Heidelberg | articles analytiques illustrés | mentions | planches, IIIF | idem |

### Vague 3 — contrastif et extension

| Corpus | Plateforme | Usage |
|---|---|---|
| Catalogues de vente illustrés (peintures) | Cariatide/INHA, Heidelberg | notices courtes : cas négatifs, histoire des attributions, beaucoup de `unresolved` |
| Autres catalogues Quire (*Terracottas* actuel, *Roman Mosaics*, *Ancient Lamps*) | Getty | corpus non pictural, déjà outillé ; dev et contrôle |
| Getty Research Portal | Getty | découverte d'exemplaires et dédoublonnage, pas de stockage |

Hors des cinq plateformes, à envisager seulement si C0 montre un manque (non retenu ici) :
catalogues systématiques de la National Gallery of Art (Washington), données ouvertes du
Rijksmuseum.

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
- Règle d'export par défaut : **standoff** (identifiants, pages, offsets, URI, image par URL quand
  la licence le permet) ; texte intégral exporté seulement si `allow`.
- Critère : aucun volume n'entre en C3 sans fiche de droits.

### C2 — Référentiels d'œuvres et images (Sonnet)
- Cache local des fiches de collection pour les départements concernés : Met (peintures
  européennes, via l'API v1.1), Getty (données de collection), puis concordances patrimoniales
  (Louvre, galeries allemandes) et Wikidata en appoint, avec provenance de chaque attribut.
- Pour chaque œuvre : identifiants externes, numéro d'accession, titre, artiste, date,
  département, URL et licence de l'image, statut domaine public.
- Sert de **liste fermée de candidats** et de source d'images. Aucune fusion d'œuvres automatique.

### C3 — Acquisition des volumes sélectionnés (Sonnet)
- Un lecteur par voie, pas par plateforme : HTML Quire (existant), PDF (Met, Getty), IIIF + ALTO
  (Gallica, Heidelberg, Cariatide).
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
- Critère : session d'essai de 20 éléments sur *Terracottas* et un premier volume du Met, sans
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

Vague 1 traverse C2 → C5 en entier avant le démarrage de la vague 2.

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
| Textes du Met et du Getty sous droits : pas de redistribution | export standoff ; texte intégral seulement si `allow` ; usage d'entraînement soumis à qualification |
| Volume supérieur à la capacité de vérification d'une seule personne | file priorisée, échantillon aveugle, précision mesurée par corpus plutôt que vérification exhaustive |
| Ancrage sur les propositions | 15 % à l'aveugle, accord mesuré entre vérification et aveugle |
| Identifiants mal lus (OCR, coupures de ligne) | proposition seulement si l'identifiant se résout dans le référentiel ; sinon `unresolved` |
| Concordances patrimoniales (anciens numéros) incertaines | vague 2 sans lien automatique tant que la concordance n'est pas sourcée |
| Dispersion technique (cinq plateformes à la fois) | lecteurs par voie, vagues successives, une vague terminée avant la suivante |

## 8. Questions au porteur avant C0

1. Êtes-vous rattaché à un organisme de recherche (université, laboratoire, institution
   patrimoniale) ? Cela décide de l'exception de TDM applicable (art. 3 ou art. 4 de la directive).
2. Un usage commercial est-il envisagé, même plus tard ? (Les conditions de Gallica distinguent
   réutilisation non commerciale et commerciale.)
3. Langues acceptées pour la vérification : anglais, français, allemand, italien ?
4. Temps de vérification disponible par semaine ?
