## Finalité : fabriquer des datasets multimodaux d’analyses d’œuvres réelles, sourcées et exploitables

Cette note est prioritaire pour l’ordre d’exécution. Elle complète, sans
remplacer, la spécification scientifique v1.0.

## Mission principale

À partir de catalogues et de publications numérisées, retrouver les
reproductions et identifiants d’œuvres, extraire des passages
analytiques effectivement écrits par des auteurs, puis établir des liens
entre œuvres et passages, justifiés, vérifiables et révisables. Exporter
ces associations comme corpus pour la recherche et, seulement lorsque
les droits le permettent, pour l’entraînement et l’évaluation de modèles
d’IA.

## Résultat minimal vérifiable

Une véritable œuvre identifiée + un passage analytique original (pas une
simple légende) + une publication et ses pages + la preuve du
rattachement + un statut de validation + des droits par usage. Le tout
inspectable par un chercheur et exportable en JSONL ou Parquet. Une
œuvre peut être commentée sans figurer dans l’ouvrage.

## Jalon obligatoire

Avant de construire une infrastructure complète, démontrer un exemple
réel vérifié humainement sur une source accessible et autorisée (Lot
2A). Ensuite, automatiser le rattachement, mesurer sa précision et sa
couverture, puis étendre à plusieurs sources. L’extraction d’assertions
fines et les graphes sont des enrichissements conditionnels, pas les
conditions initiales de succès.

## Critères de réussite

Qualité des couples œuvre-passage authentiques ; fidélité du texte et
des coordonnées ; précision/couverture des liens ; provenance et droits
vérifiables ; abstention sur les cas non résolus ; capacité à réexporter
un corpus utilisable. Aucun score de vitesse d’OCR ou nombre de
connecteurs ne remplace ces critères.

## Choix technique

Xberg est testé en priorité sur les PDF ; Docling sert de comparaison
indépendante. La structure native IIIF, METS, ALTO et éditoriale est
utilisée lorsqu’elle préserve mieux les informations. Le choix des
extracteurs dépend d’un benchmark sur catalogues réels, pas des annonces
de performance.

## Ne pas confondre

LesterNowak ne rédige pas de nouveaux commentaires sur les œuvres. Il
n’est pas un VLM d’identification, un simple moteur OCR, ni un outil
d’attribution automatique. Il reconstitue des relations entre œuvres et
discours humains documentés ; les hypothèses de modèles et les
affirmations des auteurs restent distinctes.

# LESTERNOWAK

## De catalogues d’art numérisés à des corpus de discours historiens ancrés dans leurs sources

**Cahier des charges scientifique et technique, revue critique de la
version ArtCommentary 0.1, architecture et plan d’exécution pour Claude
Code**  
**Version 1.0 \| 9 novembre 2026 \| Statut : spécification de recherche,
non prototype validé**

> **Principe fondateur.** LesterNowak ne « lit » pas une œuvre pour
> inventer un commentaire. Il analyse des publications existantes et
> reconstitue, avec leurs preuves, les relations entre les œuvres d’art,
> leurs reproductions, les textes qui en parlent, les auteurs de ces
> textes et les propositions qu’ils formulent. Tout ce qui ne peut pas
> être rattaché à une source identifiable doit rester hypothétique,
> révisable ou non résolu.

**Sources initiales.** MetPublications, Getty Publications et
publications Quire quand les données sont effectivement accessibles,
Getty Research Portal comme outil de découverte, bibliothèque numérique
de Heidelberg, Cariatide (INHA) et Gallica (BnF). Cariatide apparaît une
seule fois : cinq institutions/plateformes principales, avec plusieurs
sous-sources.

**Lecteurs visés.** Développeur utilisant Claude Code ; chercheur en
histoire de l’art / humanités numériques ; annotateurs ; responsable de
corpus ; évaluateur ML ; responsable des droits et de la provenance.

**Documents compagnons.** CLAUDE.md (instructions d’agent),
PLAN_EXECUTION.md (lots et critères de réception). Les exemples de
données du présent document sont synthétiques sauf indication expresse.

# I. Décision scientifique et périmètre

## 1. Résumé exécutif

LesterNowak est un **moteur d’extraction documentaire, d’alignement
multimodal et de constitution de corpus**. Il identifie dans des
catalogues, monographies et publications d’histoire de l’art les figures
imprimées, légendes, notices, passages analytiques, mentions d’œuvres,
citations, arguments, références et controverses. Il les relie dans un
modèle interrogeable et réversible, puis produit des jeux de données
dont le statut scientifique, l’origine et les droits sont explicites.

La difficulté principale n’est ni l’OCR ni la reconnaissance générale
des tableaux. C’est la **résolution des référents dans un discours
historiographique distribué** : l’œuvre illustrée page 12 peut être
discutée page 27, comparée à une œuvre non reproduite page 29 et
réattribuée en note page 138. Une légende peut nommer une œuvre tandis
que le texte analyse une copie, un état, un détail, une radiographie ou
un autre objet. Une mention n’est pas automatiquement une analyse ; une
interprétation n’est pas un fait objectif ; un livre consultable n’est
pas automatiquement réutilisable pour l’entraînement ou la
redistribution.

Le système conservera distincts : (1) la **publication bibliographique**
; (2) son **édition**, sa numérisation et ses pages ; (3) la **figure
reproduite** ; (4) l’**œuvre historique** à laquelle la figure renvoie,
si elle est identifiable ; (5) le **passage** de texte et ses mentions ;
(6) la **proposition** formulée ; (7) la **preuve** et le **statut
épistémique** ; (8) l’**historique des hypothèses et validations**. Les
objets et textes non résolus restent de première classe.

LesterNowak ne dépendra pas d’un seul fournisseur de données, d’un seul
parseur PDF ou d’un seul LLM. **Xberg est la première option à tester
pour l’extraction des PDF ; Docling est la baseline indépendante et peut
devenir le moteur retenu sur certains documents.** Pour les documents
patrimoniaux, les structures natives IIIF/METS/ALTO et les données
éditoriales accessibles restent prioritaires sur la réextraction par
machine.

**Livrables du prototype :** connecteurs de découverte et d’ingestion
vérifiés ; registre de droits ; représentation documentaire canonique ;
benchmark Xberg/Docling ; détecteur de figures/légendes et de structure
; résolveur de références et de liens œuvre-passage ; registre des
assertions sourcées ; interface de révision ; jeu de référence ; exports
filtrés ; rapport de résultats, erreurs, coûts, biais et limites. La
réalisation de ces composants n’implique pas que le benchmark a réussi :
chaque étape comporte une condition d’acceptation et une possibilité
d’arrêt.

## 2. Le nom et sa fonction

Le projet s’appelle **LesterNowak**, d’après Lester K. Nowak, critique
d’art fictif d’*Un cabinet d’amateur. Histoire d’un tableau* (Georges
Perec, 1979). Dans le roman, le langage du connaisseur, les catalogues,
les études attribuées, les descriptions et les provenances participent à
une construction persuasive mais potentiellement fallacieuse de
l’histoire des tableaux. Le nom n’est donc pas une simple référence à la
peinture. Il désigne la **fabrique documentaire de l’autorité**,
précisément ce qu’un système d’extraction doit analyser sans y adhérer
aveuglément.

La leçon méthodologique est nette : citer un catalogue ne rend pas toute
assertion vraie. Le logiciel attribue les propositions à un auteur, date
leur formulation et conserve leurs fondements et contradictions. Il ne
remplace pas l’historien par une « vérité de corpus » synthétique.

Le nom technique retenu est lesternowak pour le dépôt GitHub, le package
Python et la CLI. Le nom éditorial est « LesterNowak ». La disponibilité
GitHub/registre de package doit être recontrôlée avant publication : la
recherche préalable n’est pas une réservation.

## 3. Ce qu’est et ce que n’est pas le projet

**Produit cœur.** Un pipeline *publication → objets documentaires →
liens justifiés → corpus évalué*. La fonctionnalité la plus importante
est l’obtention de relations **œuvre ↔ passage**, avec rôle, preuve,
attribution et possibilité d’abstention.

**Usages aval possibles mais indépendants.** Recherche historienne dans
les corpus ; entraînement de modèles image-texte ; évaluation de VLM ;
supervision pour l’iconographie ; extraction de graphes de connaissances
; études de l’histoire des attributions et du langage descriptif ;
comparaison de commentaires sur une même œuvre.

**Exclusions initiales.** Générer de faux commentaires « d’étudiants » ;
produire de la critique d’art originale ; créer une encyclopédie de
l’art ; faire un moteur de reconnaissance visuelle généraliste ;
reproduire les fonctions de Palomar ou de Lermolieff ; publier des
ouvrages et images sans contrôle de droits ; faire de RDF/CIDOC CRM une
dépendance du MVP ; télécharger l’intégralité de toutes les plateformes
; ouvrir une plateforme SaaS.

**Frontières avec les autres dépôts.** Palomar peut fournir
ultérieurement une résolution d’entités patrimoniales ; Lermolieff peut
fournir des indices de sujets Iconclass ; Porkyevitch peut consommer les
exports pour l’entraînement/benchmark ; Fregex peut expérimenter le
raisonnement sur des représentations. LesterNowak reste autonome, ne
copie pas ces moteurs et expose des interfaces optionnelles versionnées.

## 4. Questions scientifiques et hypothèses falsifiables

**RQ1.** Quel type de preuve permet d’identifier qu’un passage commente
une œuvre donnée, et à quelle distance spatiale, textuelle ou
bibliographique ?

**RQ2.** Les métadonnées éditoriales (objets du Met ; structures Quire),
bibliographiques (METS) et spatiales (ALTO/IIIF) améliorent-elles le
*rappel à précision d’appariement fixée* par rapport à la seule
proximité image-texte ?

**RQ3.** Les systèmes d’extraction généralistes conservent-ils mieux les
figures, légendes, notes, numéros et ordre de lecture qu’un pipeline
historique fondé sur des fichiers natifs ? Les différences varient-elles
selon époque, langue et mise en page ?

**RQ4.** Comment conserver, mesurer et interroger les assertions
opposées d’ouvrages différents, sans choisir arbitrairement une
attribution unique ?

**RQ5.** Les images de détails, gravures d’après, variantes,
photographies de conservation et multiples numérisations peuvent-elles
être reliées à l’œuvre appropriée sans fusion abusive ?

**RQ6.** Une évaluation VLM peut-elle distinguer correctement
reconnaissance visuelle, connaissance récupérée, mémorisation d’un texte
célèbre et inférence historique ?

**Hypothèses à enregistrer avant les tests.** H1 : les références
explicites à des figures/notices sont plus précises que la proximité. H2
: l’ajout contrôlé d’un modèle pour les cas ambigus augmente la
couverture à précision fixée. H3 : les structures natives réduisent les
pertes de provenance. H4 : une stratégie de revue humaine fondée sur la
diversité des erreurs et l’incertitude améliore davantage la qualité
qu’une sélection uniforme au même coût. Chaque hypothèse nécessite un
critère de rejet, un jeu gelé et des résultats publiés même négatifs.

# II. Audit de la spécification ArtCommentary 0.1

## 5. Diagnostic : ce qui était juste, insuffisant ou faux

La version 0.1 posait les bonnes bases : séparation figure/œuvre,
priorité au texte humain, provenance, abstention, connecteurs, droits,
évaluations par volume et refus du « PDF → Markdown → dataset ». Elle
doit cependant être refondue sur plusieurs points importants.

**Nom et finalité**. **Gravité :** Moyenne. **Défaut de la version 0.1
:** Nom générique et tension entre extraction, graphe et benchmark sans
définition d’un produit cœur. **Correction obligatoire dans LesterNowak
:** Nom stable ; produit cœur = liens œuvre-passage vérifiables ; usages
aval séparés.

**Choix de moteur**. **Gravité :** Élevée. **Défaut de la version 0.1
:** Docling/Surya cités mais comparaison avec Xberg absente.
**Correction obligatoire dans LesterNowak :** Benchmark
Xberg–Docling–natif, mêmes pages et métriques ; décision empirique.

**API Met**. **Gravité :** Élevée. **Défaut de la version 0.1 :**
Documentation générique sans version de l’API. **Correction obligatoire
dans LesterNowak :** Endpoint de recherche Met
/public/collection/v1.1/search depuis 2026 ; pagination et limites
vérifiées ; pas de /v1/search périmé.

**Structure de la publication**. **Gravité :** Élevée. **Défaut de la
version 0.1 :** documents / editions trop peu définis. **Correction
obligatoire dans LesterNowak :** Séparer œuvre bibliographique, édition,
exemplaire numérisé, actif numérique, édition redoublée.

**Analyse du texte**. **Gravité :** Critique. **Défaut de la version 0.1
:** « Passage » directement lié à l’œuvre sans niveau explicite de
mention et de coréférence. **Correction obligatoire dans LesterNowak :**
Ajouter mentions, chaînes de coréférence, portée de discours et statut
*mention/comparison/analysis*.

**Modèle des figures**. **Gravité :** Élevée. **Défaut de la version 0.1
:** Figure et œuvre séparées, mais copie, détail, radiographie, planche
et représentation de plusieurs œuvres sous-spécifiés. **Correction
obligatoire dans LesterNowak :** Occurrence d’illustration, région,
relation d’illustration à une entité, rôle de la reproduction.

**Assertions**. **Gravité :** Critique. **Défaut de la version 0.1 :**
Modèle de claim trop sommaire, notamment pour les hypothèses et
désaccords. **Correction obligatoire dans LesterNowak :** Assertion
attribuée, datée, modalisée, reliée à plusieurs éléments de preuve et à
des contre-assertions.

**Disponibilité des sources**. **Gravité :** Élevée. **Défaut de la
version 0.1 :** Risque d’assimiler portail, plateforme et format de
téléchargement. **Correction obligatoire dans LesterNowak :** Manifeste
de capacités vérifiées pour chaque item ; mode unknown, essai de
récupération licite et retour d’erreur honnête.

**Datasets et droits**. **Gravité :** Critique. **Défaut de la version
0.1 :** « exports public/interne » sans matrice détaillée d’usages.
**Correction obligatoire dans LesterNowak :** Décisions distinctes
*acquisition*, TDM, stockage, entraînement, partage, affichage et
diffusion.

**Jeu de référence**. **Gravité :** Élevée. **Défaut de la version 0.1
:** « ~300 passages » ne caractérise pas la difficulté ni la puissance
statistique. **Correction obligatoire dans LesterNowak :** Gold
multidimensionnel, sélection stratifiée, double annotation, intervalles,
courbes risque-couverture.

**Déduplication**. **Gravité :** Élevée. **Défaut de la version 0.1 :**
Cluster d’édition sans politique d’éclatement. **Correction obligatoire
dans LesterNowak :** Déduplication par niveaux, identifiants persistants
et liens d’équivalence conservant les sources.

**Conception logicielle**. **Gravité :** Moyenne. **Défaut de la version
0.1 :** Liste de nombreux modules mais contrats et versionnage
implicites. **Correction obligatoire dans LesterNowak :** Schémas,
invariants, journal d’événements, jobs idempotents, stockage immuable,
tests de migration.

**Coût et performance**. **Gravité :** Moyenne. **Défaut de la version
0.1 :** Aucun budget opératoire ni gardes-fous d’exécution. **Correction
obligatoire dans LesterNowak :** Mesure par page et lien validé, file
d’attente, politique de recours aux modèles et plafonds configurables.

**Risques ML**. **Gravité :** Élevée. **Défaut de la version 0.1 :**
Contamination évoquée mais usages d’entraînement peu spécifiés.
**Correction obligatoire dans LesterNowak :** Exports par tâche, modèle
d’évidence, familles d’images et de publications, fuite
document/œuvre/prompt.

**Agent Claude Code**. **Gravité :** Élevée. **Défaut de la version 0.1
:** « phases » pertinentes mais trop ouvertes, provoquant une
implémentation massive sans preuve. **Correction obligatoire dans
LesterNowak :** Lots atomiques avec fichiers, entrées, commandes, tests,
métriques, conditions de sortie et interdits.

**Bilan.** La version 0.1 est un cadrage conceptuel crédible mais ne
constitue pas encore une spécification d’implémentation assez
contraignante. Elle peut conduire à un système qui « a beaucoup de
composants » sans démontrer que les associations sont correctes. La
version 1.0 rend la qualité de la preuve, l’analyse de l’erreur et la
responsabilité des données structurantes dans l’architecture.

## 6. Décisions abandonnées et décisions conservées

**Abandonné :** Docling par défaut sans test ; traitement uniforme de
toute source comme PDF ; sélection de catalogues par quantité disponible
; label textuel unique « analyse » ; confiance autoproclamée par LLM ;
lien œuvre-paragraphe sans preuve localisable ; score brut présenté
comme probabilité ; 95 % de précision comme condition de succès
déconnectée d’un intervalle et de la couverture ; lancement d’un grand
crawl avant le jeu de référence.

**Conservé :** sources institutionnelles ; cinq connecteurs ; hiérarchie
d’extraction native d’abord ; traces originales et versions dérivées ;
règles documentaires avant embeddings ; possibilité de non-résolution ;
revue humaine ; évaluation en aveugle par volumes et familles ; sorties
JSONL/Parquet et base relationnelle ; licences et politiques
d’acquisition explicites.

# III. Stratégie documentaire et corpus

## 7. Ne pas confondre les types de catalogues

Un « catalogue d’exposition » peut contenir un essai scientifique de 40
pages, des notices argumentées, une liste sommaire d’œuvres ou un index.
Les cinq plateformes ne produiront donc pas le même signal
d’apprentissage. Le modèle de sélection doit distinguer au minimum :

**Catalogue d’exposition à notices développées**. **Potentiel analytique
:** Très élevé. **Risque principal :** Illustrations et passages
éloignés ; droits modernes. **Position dans le pilote :** Priorité A.

**Catalogue de collection savant**. **Potentiel analytique :** Très
élevé. **Risque principal :** Métadonnées techniques et bibliographie
hétérogènes. **Position dans le pilote :** Priorité A.

**Catalogue raisonné**. **Potentiel analytique :** Très élevé. **Risque
principal :** Numérotation complexe ; variantes et états ; droits.
**Position dans le pilote :** Priorité A, petit échantillon.

**Monographie illustrée**. **Potentiel analytique :** Élevé. **Risque
principal :** Comparaisons diffuses, références multiples. **Position
dans le pilote :** Priorité B.

**Essai de revue ou bulletin de musée**. **Potentiel analytique :**
Élevé. **Risque principal :** Figures et légendes transversales ; OCR.
**Position dans le pilote :** Priorité B.

**Catalogue de vente ancien**. **Potentiel analytique :** Variable.
**Risque principal :** Très nombreuses notices pauvres. **Position dans
le pilote :** Corpus contrastif et historique, pas vérité de «
commentaire ».

**Catalogue de salon ancien**. **Potentiel analytique :** Variable.
**Risque principal :** Listes et numéros sans analyse. **Position dans
le pilote :** Cas négatifs, histoire des classifications.

**Livre d’artiste / publication expérimentale**. **Potentiel analytique
:** Variable. **Risque principal :** Ordre de lecture non linéaire.
**Position dans le pilote :** Défi méthodologique, hors MVP automatique.

**Sélection selon la richesse scientifique, pas le nombre de PDF.**
Après un contrôle manuel de 10 à 20 pages par volume : densité de
passages analytiques ; proportion de reproductions identifiables ;
disponibilité du texte spatial ; langues ; droits ; complexité des
références ; valeur pour la diversité du corpus. Conserver aussi des
volumes peu productifs dans le jeu d’évaluation pour ne pas surestimer
le pipeline.

## 8. La matrice des cinq sources

**MetPublications**. **Signal documentaire exploitable :** Notices
éditoriales et œuvres reliées à certains livres ; PDF d’une partie des
titres épuisés ; API Collection. **Stratégie :** Métadonnées de livre →
liens connus aux œuvres → PDF autorisé → passages. **Ce qui ne doit pas
être présumé :** Que le lien livre-œuvre désigne une page ; que PDF et
contenu soient en libre redistribution.

**Getty Publications**. **Signal documentaire exploitable :** PDF ; site
de publication numérique ; parfois structure Quire. **Stratégie :**
Vérifier PDF/HTML/source éditorial accessible avant extraction. **Ce qui
ne doit pas être présumé :** Que chaque livre ait son dépôt Quire public
; que tout Getty soit dans les collections du musée.

**Getty Research Portal**. **Signal documentaire exploitable :**
Catalogue fédéré et renvoi vers collections partenaires. **Stratégie :**
Découverte et canonicalisation ; suivre l’institution détentrice. **Ce
qui ne doit pas être présumé :** Qu’il héberge les fichiers ou octroie
les droits ; que les notices ne dupliquent pas INHA/Heidelberg.

**Heidelberg**. **Signal documentaire exploitable :** IIIF (v2/v3 selon
volume), METS, OCR ou texte selon fonds, identifiants. **Stratégie :**
METS/structure → manifeste → OCR → pages ; PDF si utile. **Ce qui ne
doit pas être présumé :** Que l’OCR soit corrigé ou suffisant pour une
citation scientifique.

**Cariatide / INHA**. **Signal documentaire exploitable :** Notices,
manifestes IIIF selon item, réutilisation indiquée sur notices.
**Stratégie :** Identification de l’item et de la licence → manifeste →
OCR/PDF s’ils existent. **Ce qui ne doit pas être présumé :** Un ALTO
universel ; homogénéité des droits ; indépendance vis-à-vis de Gallica.

**Gallica / BnF**. **Signal documentaire exploitable :** ARK, OCR/ALTO
parfois, structure de document, IIIF. **Stratégie :** Metadonnées →
texte/ALTO natif → figures géométriques → images autorisées. **Ce qui ne
doit pas être présumé :** Accessibilité constante des anciennes URLs ;
quotas fixes ; droit d’extraction confondu avec droit de republication.

### 8.1 MetPublications : ne pas ignorer les liens déjà établis

MetPublications décrit dans ses notices les œuvres du Met présentées
dans un ouvrage. C’est de la **supervision faible au niveau du volume**,
pas une vérité de terrain pour le passage. Ces liens doivent être
enregistrés avec scope=publication et ne devenir scope=passage qu’après
une preuve spécifique. La Collection API a annoncé en septembre 2026
/public/collection/v1.1/search avec pagination ; l’ancienne recherche
/v1/search a été annoncée comme retirée au 1er octobre 2026. Éviter tout
code figé sur l’ancien endpoint. La documentation fixe aussi des
conditions de débit et distingue données ouvertes de publications
\[S1–S2\].

### 8.2 Getty : deux familles de données

Le site des publications et le Research Portal n’ont pas la même
fonction. Pour les ouvrages fabriqués avec Quire, les structures
objects.yaml, figures.yaml et references.yaml sont importantes : si les
fichiers sources sont accessibles pour une publication donnée, ils
peuvent donner des liens éditoriaux beaucoup plus fiables qu’un OCR.
Cette accessibilité doit être testée et enregistrée par ouvrage. Le
Research Portal sert à découvrir des exemplaires numériques conservés
ailleurs, pas à imposer une copie redondante du document \[S3–S4\].

### 8.3 Heidelberg : l’OCR ne constitue pas une édition critique

Heidelberg propose des interfaces de données ouvertes, des manifestes
IIIF et des notices contenant METS selon les collections. La
bibliothèque précise elle-même que l’OCR automatique est « sale » et
doit être contrôlé sur les images. Une recherche infructueuse dans l’OCR
n’est pas la preuve que le terme est absent du livre. Cette asymétrie
doit entrer dans les métriques de rappel et l’interface de validation
\[S5–S6\].

### 8.4 Cariatide : données ouvertes ≠ même accès pour tous les actifs

L’INHA affirme l’interopérabilité IIIF de Cariatide, qui est également
reliée au Getty Research Portal et moissonnée par Gallica pour certains
contenus. Cela crée de vrais doublons possibles. Les droits de
réutilisation sont à lire au niveau de chaque notice et chaque
ressource, sans déduire des droits du manifeste ceux des photographies
ou textes indépendants \[S7–S8\].

### 8.5 Gallica : exploitation intelligente et prudente d’ALTO

La documentation API Document de Gallica décrit les éléments
Illustration et des blocs ComposedBlock associant parfois illustration
et légende, ainsi que des coordonnées utilisables pour une requête IIIF
Image. C’est un signal de structure très pertinent. Il n’est cependant
ni garanti sur chaque page, ni synonyme d’une segmentation parfaite. Les
anciennes et nouvelles passerelles, protections et quotas doivent être
testés avec les autorisations adéquates ; un 403 est un statut d’accès,
pas une invitation à contourner la protection \[S9\].

## 9. Inventaire et échantillonnage

**Pilote de découverte : 15 volumes**, trois par source, avec
représentation d’au moins un ouvrage à notices, un ouvrage à essais et
un ouvrage difficile. **Pilote d’évaluation : 10 volumes supplémentaires
tenus à l’écart**, deux par source, choisis sans adapter les règles à
leurs erreurs. **Extension éventuelle : 120 volumes**, uniquement si les
critères de qualité et les droits sont satisfaits. Ces effectifs sont
des budgets de travail et non des estimations de taille de dataset.

Pour chaque volume, conserver : URI canonique, titre, contributeurs,
année, type de publication, langue(s), identifiants de collection,
édition, numérisation, présence PDF/IIIF/OCR/METS/HTML, statut
juridique, nombre de pages, pages analysées, nombre de figures et de
passages *réellement* exploitables, raisons d’exclusion. Ne pas choisir
exclusivement des beaux exemples.

**Strates de contrôle :** siècle de publication, siècle des œuvres,
langue, médium (peinture, gravure, photographie, sculpture, dessin,
objet décoratif), format page, qualité OCR, position des figures, type
d’analyse, nombre de référents, présence d’un index, provenance des
documents. La taille des strates sera rapportée explicitement pour
éviter les généralités factices.

## 10. Catalogue, édition, exemplaire, numérisation : un modèle documentaire rigoureux

Une **publication intellectuelle** peut avoir différentes éditions. Une
**édition** peut exister en plusieurs exemplaires physiques, dont
plusieurs **numérisations** produites par des institutions différentes.
Ces numérisations ont des cadrages, OCR et paginations numériques
différents. La même œuvre peut être représentée plusieurs fois, avec des
détails, états ou photographies différents.

Il faut donc trois niveaux au minimum : bibliographic_work (identité
intellectuelle), edition (manifestation publiée), digital_surrogate
(numérisation ou représentation numérique datée). Ajouter si connu
physical_exemplar. Les équivalences doivent être explicites, datées et
révisables, sans effacer les originaux. Si la nature bibliographique
d’une ressource est inconnue, ne pas forcer une équivalence FRBR.

**Exemple de doublon à éviter :** un catalogue numérisé par l’INHA peut
être exposé sur Cariatide, découvert par le Getty Research Portal et
moissonné par Gallica. Trois points d’accès ne correspondent pas
nécessairement à trois livres. Inversement, deux éditions du même
catalogue peuvent différer par une nouvelle notice ou une planche
corrigée : elles ne doivent pas être fusionnées automatiquement.

# IV. Architecture et modèle d’information

## 11. Architecture logique : de l’actif brut au savoir attribué

Le système est organisé en **couches immuables ou révisables
explicitement** :

1.  **Découverte et droit** : identifier ressources et capacités ;
    statuer sur les actions permises ; ne rien collecter sans trace.

2.  **Acquisition** : obtenir légalement les actifs et métadonnées,
    conserver les octets bruts ou leurs références lorsqu’un stockage
    local n’est pas permis ; produire un manifeste de provenance.

3.  **Extraction documentaire** : lire PDF, HTML, ALTO, METS, IIIF ;
    conserver textes, géométrie, ordre et structures natives ; faire
    figurer la version exacte de chaque extraction.

4.  **Structuration éditoriale** : pages, sections, notices, chapitres,
    planches, index, bibliographies, renvois et références ; relier
    figures et légendes.

5.  **Analyse des mentions** : retrouver les noms et désignateurs
    d’œuvres, d’auteurs, de collections, de numéros, de figures ;
    résoudre les chaînes de référence dans le texte.

6.  **Appariement** : proposer une ou plusieurs œuvres candidates pour
    chaque mention, puis des relations explicites entre passages, œuvres
    et figures, avec rôle et preuve.

7.  **Argumentation** : optionnellement extraire des propositions
    attribuées, modalités, arguments invoqués, contre-arguments et
    relations entre œuvres.

8.  **Revue et publication** : interfaces de correction, séries
    d’évaluations, exports filtrés selon usage et droits.

La circulation se fait dans un sens, sans altérer les sources. Les
composants aval peuvent être recalculés à partir des états amont. Un
mauvais appariement corrigé ne doit jamais imposer le remplacement d’une
édition entière ni la perte de l’OCR brut.

## 12. Modèle de données canonique

La base relationnelle ne sera pas un stockage plat de légendes. Voici
les entités fondamentales et leur responsabilité.

**bibliographic_work**. **Fonction :** Ouvrage intellectuel. **Points
essentiels :** titre, auteurs, sujet, identifiants bibliographiques.

**edition**. **Fonction :** Réalisation éditoriale. **Points essentiels
:** date, éditeur, langue, pagination, ISBN, différences entre éditions.

**digital_surrogate**. **Fonction :** Numérisation concrète. **Points
essentiels :** institution, URI, version, empreintes, présence d’actifs.

**asset**. **Fonction :** Fichier ou flux numérique. **Points essentiels
:** MIME, hash, droit, ETag, provenance, format, statut.

**page**. **Fonction :** Feuillet/canevas/face dans un substitut.
**Points essentiels :** ordre physique, label imprimé, taille, rotation,
URL IIIF.

**zone**. **Fonction :** Région documentaire. **Points essentiels :**
géométrie, type, provenance d’extraction, texte original, qualité.

**section**. **Fonction :** Structure logique. **Points essentiels :**
chapitre, essai, notice, table, note, index, légende.

**figure_occurrence**. **Fonction :** Illustration particulière dans un
volume. **Points essentiels :** zone, recadrage, légende, type (détail,
planche, photo).

**artwork**. **Fonction :** Œuvre d’art distincte du document. **Points
essentiels :** identifiants et désignations externes non imposés.

**artwork_description**. **Fonction :** Attribut rapporté à une œuvre.
**Points essentiels :** titre, attribution, datation, provenance et
source de cette information.

**artwork_candidate**. **Fonction :** Hypothèse de résolution. **Points
essentiels :** score, signaux, alternatives et décision, sans fusion
implicite.

**text_span**. **Fonction :** Segment ancré dans texte original.
**Points essentiels :** offsets et plages de pages/zones ; chevauchement
autorisé.

**mention**. **Fonction :** Référence textuelle à une œuvre, personne,
figure, objet, lieu. **Points essentiels :** surface textuelle,
coréférence, cible candidate.

**passage**. **Fonction :** Unité éditoriale ou analytique. **Points
essentiels :** plusieurs text_span, langue, type et auteur local.

**passage_artwork_link**. **Fonction :** Relation sémantique. **Points
essentiels :** rôle et portée, preuve, statut et validateur.

**claim**. **Fonction :** Assertion historienne. **Points essentiels :**
proposition, attributaire, temporalité, modalité, position épistémique.

**evidence**. **Fonction :** Fragment de preuve. **Points essentiels :**
source, offsets/boîte, citation, mécanisme d’inférence.

**annotation_event**. **Fonction :** Action de relecture. **Points
essentiels :** avant/après, annotateur, motif, horodatage.

**extraction_run**. **Fonction :** Provenance algorithmique. **Points
essentiels :** code, modèle, paramètres, version, seed, coût, statut.

**rights_assertion**. **Fonction :** Constat juridique. **Points
essentiels :** titulaire ou source, finalité, licence, statut et date.

Le schéma n’est pas une ontologie générale de l’histoire de l’art. Il
formalise les exigences du **rattachement vérifiable**. Les entités
additionnelles (person, institution, event, place) pourront venir par
migrations, mais la relation est toujours sourcée et la création ne
suppose pas qu’un nom propre soit résolu.

## 13. Typologie fondamentale des relations

**Rôles d’un passage vis-à-vis d’une œuvre.** primary_subject (objet
principal de la discussion), formal_analysis, iconographic_analysis,
technical_analysis, attribution_discussion, provenance_discussion,
comparison_target, comparison_source, visual_source, example,
bibliographic_mention, caption_reference, uncertain_reference. Un même
passage peut avoir plusieurs rôles et plusieurs œuvres.

**Relations entre objets.** depicts, shows_detail_of, reproduces,
copy_after, variant_of, state_of_print, influenced_by, compared_with,
probably_same_as, same_as_validated, related_but_distinct. Garder
distincts les relations décrites par la source et les liens techniques
calculés. copy_after n’implique pas identité de l’œuvre ;
shows_detail_of n’implique pas que le détail corresponde à une
reproduction intégrale.

**Relations d’assertions.** supports, contradicts, qualifies, revises,
cites_as_evidence, reports_view_of. Une assertion de 1890 indiquant une
attribution à Titien et une assertion de 2020 indiquant une attribution
à un atelier ne se remplacent pas : elles coexistent et sont attribuées
à des sources et à des moments distincts.

**Valeurs nulles.** not_observed, not_available, not_checked,
not_applicable, conflicting et access_denied ne sont pas synonymes. Dans
la version minimum, conserver une valeur et un reason_code explicites.
Une image non récupérée à cause d’un 403 n’est pas une « image absente
du catalogue ».

## 14. Le passage, la mention et la coréférence

La version 0.1 liait rapidement un passage à une œuvre. Cela fonctionne
pour une notice monographique explicite, mais s’effondre dans les essais
où le référent est implicite : « Le tableau », « cette composition », «
l’exemple précédent », « sa gravure », « l’autre version », « l’œuvre de
la page suivante ». Il faut introduire une **chaîne documentaire de
coréférence** qui s’appuie sur les titres, les sous-titres, la
numérotation, les notes et le discours précédant.

Chaque mention reçoit : texte original, ancrage, type de référent,
candidat(s), source de la résolution, rôle discursif, degré de
résolution, lien à d’autres mentions. Une mention dans un index peut
être une entrée bibliographique, tandis que la même expression dans le
corps du livre peut désigner l’œuvre étudiée. Les stratégies de
coréférence doivent donc intégrer la **structure éditoriale**, pas
seulement les phrases.

Il faut également représenter les **œuvres non reproduites**. Sinon, le
système force toute mention à l’image la plus proche. Exemple typique :
un article reproduit le tableau A et le compare à la gravure B absente
des planches ; le bon résultat est deux entités distinctes, dont une
sans figure dans le volume.

## 15. Géométrie, offsets et préservation des sources

Un bbox est interprétable uniquement avec son repère : unité,
dimensions, origine, orientation et version d’image. PDF utilise
fréquemment des points avec des repères variables ; ALTO peut utiliser
une unité propre documentée par MeasurementUnit ; IIIF opère sur les
dimensions du canevas ou du service d’image ; une image rendue à 150 dpi
ne possède pas les mêmes coordonnées que la numérisation originale.

**Contrat géométrique.** Chaque zone conserve : source_bbox,
source_coordinate_system, page_dimensions, rotation,
transform_to_canonical, canonical_bbox et éventuellement un
iiif_selector. Le format canonique de travail sera un rectangle relatif
top-left \[x0,y0,x1,y1\] en coordonnées normalisées \[0,1\] (avec
précision suffisante), mais les valeurs sources ne sont jamais écrasées.
Le retour au fichier doit être testé à tolérance explicite.

Le texte est conservé sous trois formes : raw_text (tel que livré ou
reconnu, sans correction), display_text (normalisation non destructive
lisible) et search_text (formé pour l’index, avec lemmatisation
facultative). Une table d’alignement préserve les offsets entre raw_text
et les versions dérivées. Toute citation dans une décision doit pointer
le texte **original** et non une paraphrase ou une traduction.

**Attention ALTO.** Les unités, espaces et niveaux de segmentation
varient selon les sources et les versions. Les heuristiques
Illustration/ComposedBlock de Gallica sont utiles mais non universelles.
Conserver le XML original et l’identifiant du bloc avant toute
conversion \[S9–S10\].

## 16. Proposition historiographique : du texte à l’argument

La couche claim ne doit pas donner l’illusion qu’une phrase est une
vérité atomique. Distinguer trois niveaux :

- **Formulation citée** : séquence exacte du texte, avec auteur,
  édition, page et éventuellement note.

- **Paraphrase technique contrôlée** : structuration de l’énoncé («
  l’auteur attribue X à Y ») révisable, versionnée et explicitement
  dérivée.

- **Interprétation de l’extracteur** : le logiciel pense que l’énoncé
  est une hypothèse, une objection, une description ou une comparaison ;
  cette analyse n’est pas une affirmation de l’historien.

Une assertion structurée peut comporter subject, predicate, object,
qualifiers, modality, negation, temporal_scope, claimant, source_span,
evidence_refs et extraction_confidence. Le claimant est un chercheur, un
rédacteur de catalogue ou une source rapportée, pas systématiquement
l’auteur bibliographique du volume. Les notes et citations introduisent
parfois des voix différentes.

**Exemple synthétique.** Un catalogue dit : « Selon X, la figure reprend
une estampe de Y ; Z conteste cette filiation. » Le système produit deux
assertions attribuées à X et Z, avec le catalogue comme **source qui
rapporte**, et non une vérité non qualifiée selon laquelle l’estampe
aurait servi de modèle. Une même relation peut faire l’objet d’une date,
d’un degré de certitude, d’un argument visuel et d’un contre-argument.

## 17. Identifiants, versionnement et correction

Les identifiants de source (ARK, ID Heidelberg, ID IIIF, Met Object ID,
DOI) sont des **identifiants externes**, pas les clés primaires uniques
du modèle. Les identifiants internes doivent survivre aux changements
d’URL, de segmentation, de modèle OCR et de prestataire. Une zone
calculée garde la référence au run_id et au fichier/repère ; une
resegmentation crée une nouvelle version de zone et un tableau de
correspondance plutôt qu’un écrasement.

**Principe d’écriture.** Sources brutes et sorties algorithmiques
horodatées et append-only ; vues courantes calculées ; annotations
humaines gérées comme événements réversibles ; corrections enregistrées
avec motif et auteur ; migrations Alembic explicites. Les fusions
d’œuvres ne sont jamais destructrices. Les empreintes (sha256) servent à
l’intégrité et à la déduplication technique, pas à démontrer l’identité
intellectuelle de deux documents.

## 18. Exemple de contrat d’appariement (fictif)

    {
      "schema_version": "1.0",
      "decision_id": "ln:link:example:001",
      "source_document_id": "ln:surrogate:example",
      "passage_id": "ln:passage:42",
      "artwork_candidates": [
        {"artwork_id": "ln:artwork:A", "status": "selected"},
        {"artwork_id": "ln:artwork:B", "status": "rejected"}
      ],
      "relations": [{
        "artwork_id": "ln:artwork:A",
        "role": "iconographic_analysis",
        "scope": "paragraph",
        "evidence": [{
          "source_span_id": "ln:span:99",
          "mechanism": "explicit_figure_reference",
          "quoted_text": "as shown in figure 12",
          "original_page_index": 38,
          "figure_id": "ln:figure:12"
        }]
      }],
      "status": "machine_proposed",
      "abstention_reason": null,
      "review_status": "pending",
      "pipeline_run_id": "ln:run:0007",
      "rights_decision_id": "ln:rights:005"
    }

Dans le stockage réel, les chaînes de citations seront de préférence des
références à des spans immuables, pour éviter la duplication de texte
protégé dans les tables et exports. Le JSON ci-dessus est un contrat de
sortie conceptuel, non le schéma SQL final.

# V. Extraction : Xberg, Docling et structures patrimoniales

## 19. Décision de principe : trois voies, pas un monoculture PDF

1.  **Voie native structurée**, quand possible : XML ALTO, METS,
    manifestes IIIF, annotations, HTML éditorial/Quire, tables des
    matières et index institutionnels. Priorité pour les relations et la
    géométrie fournies par l’institution ; validation de leur fiabilité.

2.  **Voie PDF à couche texte** : extraction avec Xberg ou Docling,
    enrichissement géométrique si nécessaire avec PyMuPDF ; conserver
    les images et le texte originaux.

3.  **Voie PDF scanné/image patrimoniale** : utiliser OCR existant si
    exploitable, sinon OCR local sélectionné après analyse de qualité ;
    détecter les pages difficiles et les revisiter. Il ne faut pas
    réocériser par défaut un volume entier s’il possède déjà un texte
    correct.

Le choix est **par type de document, parfois par page**, et jamais
seulement par plateforme. Un document Cariatide peut fournir un PDF
natif, un autre uniquement une image IIIF ; un volume Met peut être un
PDF à couche texte ou une numérisation ancienne.

## 20. Xberg : bénéfices et points de vigilance avérés

Le projet Xberg succède à Kreuzberg et fournit un cœur Rust, des
bindings Python, de l’extraction multimodale, du PDF, des images et des
options OCR/layout \[S11–S12\]. Pour LesterNowak, ses qualités
potentielles sont le débit, la gestion de nombreux formats, la
production de pages et d’éléments, et une chaîne paramétrable. **Mais
les annonces générales « le plus rapide » ou « meilleur PDF » ne
constituent pas un résultat sur catalogues d’art.**

Points techniques importants dans la documentation consultée :

- La **détection de mise en page** exige les fonctionnalités et modèles
  activés dans la construction Xberg ; elle n’est pas nécessairement
  dans l’installation par défaut \[S13\].

- La réparation de **l’ordre de lecture** est désactivée par défaut
  (reading_order=false) et ne fonctionne que si des indices de mise en
  page ont réellement été produits ; activer un drapeau sans modèle de
  layout peut ne rien changer \[S14\].

- Les **en-têtes, pieds et répétitions** peuvent être filtrés par défaut
  : dangereuse perte si un numéro de planche, une cote ou une annotation
  de page y figure. LesterNowak doit conserver une extraction
  brute/complète et une vue filtrée séparée \[S14\].

- Les positions des **images embarquées** peuvent être absentes ou
  partielles ; un PDF peut représenter une planche par plusieurs images,
  masques ou objets graphiques. Une image embarquée n’est pas toujours
  égale à la figure telle qu’elle apparaît sur la page. Un rendu de page
  et un recadrage géométrique peuvent être indispensables \[S15\].

- Les paramètres, modèles, poids et version exacte doivent être
  consignés, en particulier dans un logiciel dont la documentation et
  les releases évoluent rapidement.

**Conséquence :** pour le benchmark, enregistrer *explicitement*
configuration d’extraction, OCR, activation layout, ordre de lecture,
filtrage, images, pages, version du paquet et construction. Une
implémentation qui lit uniquement content Markdown est non conforme.

## 21. Docling : pourquoi le conserver

Docling propose un modèle DoclingDocument avec hiérarchie, zones de
texte, figures, tables, ordre de lecture et éléments de provenance, dont
des boîtes et des pages lorsque l’information existe \[S16\]. Il fournit
un **point de comparaison utile pour la fidélité structurale**, et non
une simple alternative de conversion Markdown.

LesterNowak doit adapter Xberg et Docling vers une interface canonique
commune sans les forcer à déclarer des informations absentes. Un type
bbox nul doit rester nul. Le pipeline doit évaluer séparément la qualité
du contenu (texte juste) et du **rattachement source** (page et zone
juste). Le choix final peut être hybride : Xberg rapide sur PDF
modernes, Docling sur documents particuliers, ALTO/METS pour
numérisations patrimoniales. Ce scénario reste une hypothèse de travail,
pas un verdict.

## 22. Benchmark d’extraction réellement décisif

**Échantillon initial : 30 pages**, stratifié par source et par
difficulté (au moins six par source), pour tester la faisabilité.
**Élargissement : 100 à 150 pages indépendantes** si les premiers
résultats ne discriminent pas les moteurs. Choisir des pages avec :
figures et texte sur une page ; planches isolées ; plusieurs images ;
doubles colonnes ; notes ; légendes partagées ; images sans légende ;
numérotation éloignée ; index ; scans anciens ; épreuves altérées ;
figures vectorielles et détails.

Comparer quatre conditions selon les capacités : **N** = source native ;
**X** = Xberg configuré (avec variantes layout/OCR) ; **D** = Docling
configuré ; **H** = hybride natif puis extraction complémentaire. Chaque
condition reçoit les mêmes pages et mêmes droits ; les différences
d’exigences (GPU, modèles à télécharger) sont rapportées.

**Zones texte**. **Métrique principale :** CER/WER sur passages
annotés + conservation des notes. **Critère de contrôle :** Différencier
erreurs OCR et erreurs d’ordre.

**Structure**. **Métrique principale :** Exactitude ordre de lecture,
titres/sections, séparation colonnes. **Critère de contrôle :** Éviter
la concaténation erronée.

**Figures**. **Métrique principale :** Précision, rappel, IoU et classe
de figure. **Critère de contrôle :** Reconnaître planches, détails et
objets non artistiques.

**Légendes**. **Métrique principale :** Précision/F1 figure↔légende.
**Critère de contrôle :** Inclure N:1 et 1:N.

**Références**. **Métrique principale :** Rappel des numéros et renvois.
**Critère de contrôle :** Les numéros sont critiques pour les liens
distants.

**Ancrage**. **Métrique principale :** Taux de passages localisables et
erreur des coordonnées. **Critère de contrôle :** Revenir à la page
d’origine.

**Ressources**. **Métrique principale :** secondes/page, RAM max,
disque, coût OCR/modèles. **Critère de contrôle :** Mesurer à qualité
comparable.

**Règle de décision :** donner priorité à la fidélité des preuves et des
figures, puis à la vitesse et aux ressources. Un moteur qui produit du
texte plus lisible mais supprime les notes et numéros de figure est
moins utile au cœur du projet. Ne pas changer le backend par défaut
après avoir regardé le test final ; réserver les décisions à un ensemble
de développement.

## 23. Normalisation et reconstructions prudentes

- Conservation d’une **image de page** et du **texte d’origine** lorsque
  les droits le permettent ; sinon identifiants et dérivés autorisés.

- Reconstruction de l’ordre de lecture avec des alternatives pour les
  mises en page incertaines ; journaliser ce qui a été déplacé.

- Extraction de césures, colonnes, titres, sous-titres, notes,
  appendices et bibliographies sans modifier les citations sources.

- Extraction des figures avec boîtes et classes : œuvre entière, détail,
  schéma, radiographie, photographie d’objet en situation, graphique,
  décor, publicité, logo, artefact non pertinent.

- Association figure-légende par numérotation, typographie, voisinage,
  séquence et structure, avec exceptions 1:N, N:1 et sans légende.

- Détection des **plates/planche/cat. no./Abb./Tafel/fig.** et de leurs
  variantes en anglais, français, allemand, italien et langues
  d’extension, sans prétendre couvrir toutes les conventions par regex.

- Table des matières et index comme structures d’aide à la localisation,
  sans leur attribuer d’emblée le statut de commentaire d’œuvre.

# VI. Du document à la relation œuvre-commentaire

## 24. Génération des candidats : privilégier la preuve forte

Ne jamais proposer toutes les figures d’un volume à tous ses
paragraphes. Construire un graphe de renvois internes et une liste de
candidats limitée, structurée par preuves :

**E0 : indication explicite et vérifiable.** Numéro de figure, planche,
catalogue, inventaire ou URI dans le passage ; résolution de l’appel et
de sa cible. La preuve porte sur l’identité référée, non automatiquement
sur le rôle analytique.

**E1 : structure éditoriale.** Rubrique de notice à entrée unique, titre
de section, numérotation de catalogue, lien objet/entrée Quire,
structure METS et tableaux de contenu ; héritage du sujet de la notice
jusqu’à changement explicite.

**E2 : identité documentaire.** Nom de l’artiste, ancien titre, date,
collection, numéro d’inventaire, bibliographie et alias ; comparaison
avec les descriptions d’œuvres et catalogues d’autorité.

**E3 : continuité discursive.** Coréférence, démonstratifs, continuité
de section, références au paragraphe précédent, passage multi-pages ;
les transitions introduisant une autre œuvre doivent rompre la chaîne.

**E4 : proximité sémantique.** Similarité texte-légende, description de
motifs et indexation lexicale. Utile pour augmenter le rappel, mais
exposée aux homonymies, copies et clichés stylistiques.

**E5 : indices visuels.** Correspondance figure/candidat connu, image de
détail, gravure source ou photographie de l’œuvre. En aucun cas un score
visuel seul ne prouve qu’un historien commente cette œuvre dans une page
donnée.

Chaque candidat conserve ses signaux séparément. Un rang n’est pas une
probabilité. Les éléments qui ne contiennent pas une référence
vérifiable reçoivent needs_review ou unresolved selon la politique. Un
système robuste ne doit pas systématiquement « choisir le moins mauvais
».

## 25. Séparer trois problèmes souvent mélangés

1.  **Identification d’illustration :** quel objet est visible dans le
    rectangle de la page ? Cela peut être indéterminé ou plusieurs
    œuvres.

2.  **Résolution de mention :** quelle œuvre est visée par l’expression
    « cette Madone », « le n° 48 », « une gravure de Marcantonio » ? Il
    peut n’exister aucune image de cette œuvre dans le livre.

3.  **Relation d’analyse :** que fait précisément le passage avec cette
    œuvre : l’analyse-t-il, la mentionne-t-il, la compare-t-il,
    attribue-t-il une propriété ou discute-t-il l’opinion d’un autre
    auteur ?

Une erreur au premier niveau contamine les deux suivants, mais le
système doit les **mesurer indépendamment**. Les utilisateurs pourront
examiner un passage juste mais une identité d’œuvre douteuse sans devoir
rejeter tout l’extrait.

## 26. Résolution d’œuvres et variantes matérielles

L’identification s’appuie sur des candidats issus des catalogues et
référentiels officiels (Met Collection API, Getty Collection Data et
liens de collections accessibles), et éventuellement Wikidata/URI
patrimoniales en appoint. Ne pas transformer les données d’autorité en
vérité universelle : une attribution de musée peut être incertaine, une
œuvre perdue n’avoir aucune fiche, un titre historique être différent.

Combiner identité textuelle, période, technique, dimensions, collection,
cotes, provenance, numéros d’inventaire, anciens titres, signatures et
parentés visuelles. Les noms et dates ne suffisent pas toujours ; les
entités work, physical_object, representation, copy, detail, print_state
pourront être spécifiées si l’échantillon les exige. Les fusions restent
manuelles ou exigent une preuve forte auditée.

**Tests adversariaux obligatoires :** deux Madones au même titre ; une
estampe d’après un tableau ; deux états d’une gravure ; un tableau dont
l’attribution a changé ; une œuvre détruite citée sans reproduction ;
détail inversé ; plusieurs figures sur une planche ; couverture de livre
représentant un tableau ; légende erronée dans l’édition.

## 27. LLM : arbitre limité, jamais auteur de la preuve

Le modèle est appelé après les règles et la génération de candidats. Son
entrée contient le passage exact, le contexte local contrôlé, la
structure de section, les mentions, la liste fermée des candidats et des
indices avec leurs IDs. Il doit sortir un **JSON sous schéma versionné**
contenant : candidat(s), rôle, extraits de preuve identifiés par span,
éventuelle chaîne de coréférence, causes d’incertitude et abstention.

**Deux contrôles impératifs :**

- Vérification automatique que chaque citation et ID de preuve renvoie à
  un contenu réellement présent ; interdiction d’inventer un titre, une
  page ou une figure. Les références produites par un modèle doivent
  être résolues dans le manifeste des sources.

- Instructions trouvées dans un catalogue numérisé, une légende, un PDF
  ou une page web traitées **comme des données non fiables**. Elles ne
  peuvent pas piloter la collecte ni modifier les consignes du système
  (résistance aux prompt injections documentaires).

Les scores de vraisemblance du modèle et son « confidence: 0.98 »
éventuel ne sont pas des probabilités calibrées. Pour l’acceptation
automatique, utiliser au besoin un classifieur ou reranker sur signaux
observables, calibré sur des exemples annotés indépendants. La réponse
abstain doit être valide et valorisée.

## 28. Passage analytique ou simple occurrence ?

Les textes à garder ne sont pas seulement ceux contenant des « adjectifs
artistiques ». On cherchera notamment des raisonnements du type **indice
→ inférence → comparaison → interprétation**, des questions de
datation/attribution, des références à des sources, des démonstrations
techniques, des comparaisons formelles. Un passage peut relever de
plusieurs classes.

Proposition de taxonomie multi-étiquette : visual_description,
formal_analysis, material_technical, iconography, attribution, dating,
provenance, commission, reception, source_relation,
comparative_analysis, historiography, interpretive_argument,
bibliographic_context, administrative_record, unclassified.
Orthogonalement, distinguer visual_evidence, documentary_evidence,
inference, reported_opinion et not_determinable.

L’extraction d’une phrase courte sur une œuvre ne suffit pas à garantir
un « commentaire savant ». On conservera des unités de passage
contextuelles, pouvant inclure deux paragraphes, une note et son appel,
voire plusieurs pages. Les résumés générés sont facultatifs et ne
remplacent pas l’original.

## 29. Extraction des assertions et des arguments : une voie de recherche spécifique

La couche des propositions sera développée **après** la validation d’un
appariement œuvre-passage. Sinon, une segmentation sémantique
sophistiquée ne ferait que rationaliser de faux liens. Un sous-ensemble
manuel doit distinguer : assertion factuelle, hypothèse, interprétation,
citation d’un auteur, objection, comparaison, argument probatoire,
modalité et négation.

Une proposition peut avoir plusieurs éléments de preuve, et la preuve
peut être purement textuelle (document d’archive) ou visuelle (détail
d’image). **Ne pas créer de correspondance pixel/argument
artificielle.** Une interprétation de commanditaire n’a souvent aucune
région visuelle propre. Si la référence à un objet visible est
explicite, associer un selector de région ; sinon rester au niveau de
l’œuvre ou du passage.

Cette séparation rend possible un futur corpus de relations telles que
engraving_source_of, borrowed_motif_from, reinterpreted_by,
attributed_to_by, dated_by, mais n’impose pas une ontologie exhaustive
avant d’avoir observé les textes.

# VII. Évaluation scientifique, données de référence et usages ML

## 30. Le benchmark doit mesurer des composantes causales, pas un score global

**Volets distincts :** (A) acquisition/capacités ; (B) OCR/layout ; (C)
détection de figures ; (D) association figure-légende ; (E) extraction
de mentions ; (F) résolution d’identité d’œuvre ; (G) lien passage-œuvre
et rôle ; (H) classification analytique ; (I) assertions et preuves ;
(J) droits et export. Une erreur dans (G) ne peut pas être compensée par
un bon score de (B).

Comparer explicitement :

- **B0** proximité page, sans structure.

- **B1** règles documentaires, appels de figures, notices et sources
  natives.

- **B2** B1 + alias/réconciliation documentaire et coréférence.

- **B3** B2 + reranker sémantique ou LLM contraint.

- **B4** B3 + indice visuel uniquement sur les ambiguïtés qui le
  justifient.

Les ajouts seront évalués par *ablation* sur le même jeu gelé. Le
système ne doit pas annoncer « meilleure qualité » si la performance
vient simplement d’un plus faible taux d’abstention au prix d’erreurs
supplémentaires.

## 31. Plan d’annotation de référence

**Étape pilote.** Sur les 15 volumes de développement, produire 30 pages
de référence extraction, puis annoter des séquences complètes de
notices/essais. Ensuite, sur les 10 volumes de test indépendants,
constituer une série de **500 à 800 jugements de liens candidats**
(positifs, négatifs et incertains) ainsi qu’un inventaire des vrais
liens pertinents pour estimer le rappel. Il s’agit d’une proposition de
charge de travail, pas d’un échantillon statistiquement garanti. La
taille finale dépendra du rendement observé et de l’incertitude des
métriques.

**Deux niveaux d’annotation :** délimitation physique (région, figure,
légende, passage, section) et interprétation documentaire (identité
d’œuvre, rôle, preuve, modalité). Au moins 15 à 20 % des exemples
critiques doivent être annotés indépendamment par deux personnes, avec
arbitrage et journal des désaccords. Les experts doivent voir les pages,
les notes et les index ; ne pas leur demander de juger une phrase privée
de son contexte.

**Les cas négatifs sont structurants.** Il faut un échantillon de
simples mentions, tableaux absents du livre, figures seulement
comparées, légendes ambiguës, références erronées, œuvres très
semblables et identités impossibles à établir. Sinon les métriques de
précision seront artificiellement élevées. Ne pas sélectionner seulement
les liens proposés avec confiance par le logiciel.

## 32. Guide d’annotation : décisions non triviales

1.  Un passage « figure 8 » est positif pour la **référence** à la
    figure 8 ; le rôle est mention tant qu’il n’existe pas d’analyse
    effective.

2.  Un paragraphe compare A à B : deux liens distincts,
    primary_subject/comparison_target selon la syntaxe et la structure,
    non un seul « œuvre principale ».

3.  Un auteur cite une attribution antérieure qu’il rejette : assertion
    reported_opinion et assertion de rejet ; ne pas donner au passage
    une attribution affirmative non nuancée.

4.  Une planche montre une reproduction inversée : même œuvre possible,
    orientation notée sur l’occurrence ; si une copie matérielle
    distincte, relation copy_after, pas same_as.

5.  Une page traite de « l’artiste » sans nom : si aucune antécédence
    sûre, annoter unresolved.

6.  Si l’OCR remplace un numéro de figure par une autre valeur, la
    correction manuelle doit préserver la transcription OCR initiale.

7.  Si un catalogue affirme un fait contesté par un ouvrage ultérieur,
    les deux propositions sont enregistrées ; le label « vérité » n’est
    pas attribué par l’annotateur du lien.

8.  Si une figure illustre une exposition historique et non une œuvre
    particulière, éviter l’identification forcée.

Les règles complètes seront publiées dans docs/annotation-guide.md, avec
exemples réellement annotés et cas litigieux. Ce guide doit précéder
l’annotation massive.

## 33. Mesures : métriques, incertitude et couverture

**Figures**. **Métriques :** précision/rappel, IoU, taux de faux objets.
**Lecture :** Qualité de la localisation et de la classe.

**OCR**. **Métriques :** CER/WER sur passages choisis, préservation des
noms/numéros. **Lecture :** La perte d’un chiffre peut être pire qu’une
faute de ponctuation.

**Ordre et structure**. **Métriques :** exactitude des parcours et
sections. **Lecture :** Empêche les transferts erronés entre colonnes.

**Figure-légende**. **Métriques :** précision/rappel/F1 avec
cardinalité. **Lecture :** Lier les bonnes figures aux bons textes.

**Œuvre candidate**. **Métriques :** Hits@k, MRR et exactitude de l’ID
validé. **Lecture :** Mesurer la recherche puis la décision.

**Passage-œuvre**. **Métriques :** précision/rappel/F1 par relation,
micro et macro. **Lecture :** Estimer les liens corrects et ceux
manqués.

**Abstention**. **Métriques :** couverture ; précision-couverture ;
courbe risque-couverture. **Lecture :** Voir ce qui est accepté et ce
qui reste à relire.

**Assertions**. **Métriques :** F1 par type/acteur/modulation ; fidélité
des preuves. **Lecture :** Vérifier les contenus d’argument et
l’attribution.

**Revue**. **Métriques :** secondes par correction, désaccord,
amélioration après correction. **Lecture :** Coût humain réel.

**Efficience**. **Métriques :** secondes/page, RAM, coût/volume,
coût/lien validé. **Lecture :** Calcul économique pertinent.

Rapporter les intervalles de confiance (par exemple Wilson pour des
proportions, bootstrap **par volume** pour réduire la dépendance
intra-livre), les nombres d’exemples et une analyse des cas d’erreur. À
300 ou 500 liens très corrélés issus de trois livres, un intervalle naïf
trop étroit est trompeur.

**Cible proposée, non promesse.** Pour autoriser un lien sans revue,
viser une précision observée au moins égale à 95 % avec une borne
inférieure d’intervalle de confiance satisfaisante **et un taux de
couverture documenté**. Le seuil exact dépend du risque et de l’usage.
Un export d’entraînement à fort enjeu exige davantage de prudence qu’une
interface exploratoire.

## 34. Partition et fuite des données

Les découpages doivent se faire par **famille éditoriale et édition**,
avec contrôle des duplications entre plateformes, mais aussi par
familles d’œuvres reproduites dans plusieurs catalogues. Sinon une même
figure ou un même commentaire peut être présent dans l’entraînement et
l’évaluation. Pour les essais VLM, il faut distinguer au minimum :

- *Document-held-out* : ouvrages jamais vus par le système de liens.

- *Artwork-held-out* : œuvres et dérivés visuels absents de
  l’entraînement supervisé spécifique.

- *Source-held-out* : tests sur une plateforme ou un type de mise en
  page non utilisé au développement.

- *Temporal/edition-held-out* : attribution ou version plus récente
  d’une œuvre, pour tester la robustesse historiographique.

L’absence de présence dans le dataset supervisé ne prouve pas l’absence
dans le préentraînement d’un grand VLM. Documenter cette limite au lieu
de présenter le test comme preuve absolue de « raisonnement visuel ».

## 35. Quatre familles d’exports, avec degrés d’exigence distincts

**E1. Index de découverte.** Identifiants, URL sources, métadonnées
autorisées, identifiants de figures et de passages, pages et liens
vérifiés. Utile sans republier de livres protégés.

**E2. Dataset d’alignement.** Figures autorisées, textes originaux
autorisés, rôles, ancrages, preuves, niveau de contrôle et alternatives,
dans un JSONL/Parquet documenté. Le cas « œuvre non reproduite » reste
licite comme exemple de lien documentaire non visuel.

**E3. Dataset de propositions.** Assertions attribuées et modalisées,
références aux preuves, graphes de relations, désaccords. Séparer
l’extrait source de la normalisation interprétative.

**E4. Benchmark de vision-langage.** Tâches distinctes : description
visuelle seule ; reconnaissance iconographique ; question documentée
avec récupération ; identification d’une preuve ; comparaison d’œuvres
et critique d’une attribution. Ne pas transformer toute annotation de
catalogue en réponse nécessairement visible.

Le système de droits doit accepter l’export de références sans export du
texte/images. Toute production synthétique en aval porte un drapeau
generated=true et ne peut jamais se substituer à un passage historique
d’auteur.

## 36. Place d’Iconclass dans LesterNowak

Iconclass est **une couche optionnelle de classement**, pas le modèle de
données ontologique principal. Une œuvre peut recevoir plusieurs
notations valides, des notations composites, des motifs, des relations
et des lectures historiographiques qui ne coïncident pas avec une
étiquette canonique unique. Une annotation iconographique doit conserver
la notation exacte, sa version/source, la personne ou modèle qui l’a
attribuée, et le type de preuve.

Des données Iconclass récurrentes dans un corpus supervisé peuvent être
mémorisées sans maîtrise de leur composition. LesterNowak peut produire
des contextes analytiques pour étudier la généralisation, mais il ne
doit pas présumer que la présence d’un code dans un catalogue prouve son
applicabilité visuelle ni qu’une notation composée absente du
dictionnaire est syntaxiquement invalide. Les évaluations sépareront
labels complets, constituants et justification textuelle/visuelle.

# VIII. Droits, sécurité, exploitation durable

## 37. Matrice des droits par action et par actif

Une licence d’une fiche descriptive peut différer de celle du scan, du
texte de l’ouvrage, de la photographie et de l’œuvre représentée. La
gratuité de consultation et le fait qu’une API expose une URL ne donnent
pas automatiquement le droit de republier ou d’entraîner.

**Découvrir et indexer les notices**. **Vérification spécifique :**
Conditions API et régime des métadonnées. **Défaut prudent :** Conserver
URI et provenance.

**Télécharger fichier**. **Vérification spécifique :** Droit d’accès
licite et contraintes techniques. **Défaut prudent :** Ne pas
télécharger si non autorisé.

**Stocker copie durable**. **Vérification spécifique :** Licence,
exceptions applicables, sécurité. **Défaut prudent :** Stockage limité /
référence distante.

**Extraire/OCR/TDM**. **Vérification spécifique :** Finalité de
recherche, statut de l’organisme, réserves de droits, juridiction.
**Défaut prudent :** legal_review_required si incertain.

**Utiliser pour entraînement ML**. **Vérification spécifique :**
Finalité, bases juridiques, éventuelles réserves et contrats. **Défaut
prudent :** Non autorisé tant que non qualifié.

**Afficher page/extrait dans l’UI**. **Vérification spécifique :**
Droits d’affichage, accès des annotateurs. **Défaut prudent :**
Interface restreinte ou liens source.

**Publier corpus texte/image**. **Vérification spécifique :** Licence de
chaque contenu et conditions de réutilisation. **Défaut prudent :**
Metadata-only.

**Publier prompts ou exemples**. **Vérification spécifique :** Droit de
citation/accès et règles de partage. **Défaut prudent :** Exemples
synthétiques.

Le droit européen prévoit une exception de fouille scientifique pour des
organismes et institutions éligibles et un régime plus général soumis à
certaines réserves ; en France, voir l’article L122-5-3 du CPI. **Ce
n’est pas une autorisation universelle de redistribution ni un avis
juridique**. Le statut du projet, la localisation des traitements, les
contrats des sources et les éventuelles réserves doivent être examinés
avant l’extension \[S17–S18\].

Modèle de décision : rights_assertion(asset_id, action, jurisdiction,
basis, evidence_url, checked_at, reviewer, decision) avec décision
allow, deny, unknown ou conditional. Tout export vérifie cette table
**par actif et par action**. unknown ne devient jamais allow
automatiquement.

## 38. Accès et sécurité des plateformes

Les connecteurs doivent respecter les conditions d’utilisation, robots
lorsqu’applicables, quotas publiés, Retry-After, temporisation,
concurrence bornée et backoff. Un 429 suspend l’accès selon la politique
; un 403 se consigne et arrête les tentatives non autorisées. Aucune
rotation de proxy, contournement Cloudflare ou travestissement des
requêtes ne fait partie du projet.

Prévoir une **ingestion hors ligne de fichiers obtenus licitement**,
utile quand les API documentées sont inaccessibles depuis
l’environnement de test. Les API changeantes sont des dépendances
observées, non des invariants. Stocker les journaux HTTP sans secrets ni
jetons. Configurer des budgets maximaux de pages, octets, requêtes et
temps par job.

## 39. Intégrité, prompt injection, vie privée et pollution documentaire

Les textes extraits sont du contenu extérieur non fiable. Les appels de
modèle séparent instructions système et citations documentaires ; tout
lien externe ou commande incluse dans le document est une donnée à
interpréter, jamais une instruction à exécuter. Empêcher SSRF, accès aux
adresses locales, archives démesurées et chemins de traversal par
validation des URLs/chemins et par limites de
téléchargement/décompression.

Éviter toute exposition accidentelle de clés, fichiers temporaires ou
textes sous droits dans CI, logs, captures UI et rapports. Les
annotations humaines peuvent contenir des informations nominatives
d’annotateurs : définir une politique de conservation et de publication.
Les documents modernes peuvent contenir des données personnelles, à
minimiser selon le contexte.

## 40. Reproductibilité scientifique

Chaque run conserve : commit Git, paramètres, version de Xberg/Docling,
modèle OCR/layout, poids et checksum lorsque possible, langue, système,
droits constatés, état des requêtes, version des modèles de classement,
version du prompt, sortie brute du modèle, coût et durée. Une décision
de validation humaine ne disparaît pas lors d’une réexécution. Produire
des manifests JSON et un dataset card documentant la sélection, les
exclusions, les biais, les droits et les métriques.

Les sources peuvent changer : les dates de capture et les versions sont
indispensables. Le document doit signaler explicitement si l’on n’a pas
pu vérifier un endpoint en condition réelle ; un résultat simulé avec
fixture ne sera jamais déclaré « connecteur fonctionnel en production ».

# IX. Conception logicielle pour un vrai prototype maintenable

## 41. Stack proposée et décisions d’ingénierie

**Langage.** Python 3.12 comme base testée, gestion via uv, typage
Pydantic v2 pour schémas API et modèles d’échange ; ruff, mypy ou
pyright, pytest, tests avec fixtures et sans réseau par défaut.
Sélectionner une version reproductible des outils.

**Parsing.** lxml pour ALTO/METS ; client IIIF validant v2/v3 ; httpx +
tenacity sous politique de débit ; Xberg et Docling comme adapters
interchangeables ; PyMuPDF pour diagnostic géométrique et rendu des
pages quand autorisé. Pas de dépendance Xberg dans la couche métier :
interface abstraite et schéma canonique.

**Données.** SQLAlchemy 2 et Alembic. SQLite peut permettre le bootstrap
local et les tests, avec PostgreSQL comme cible si la concurrence, la
recherche textuelle et le volume le justifient. Écrire dès le début des
migrations et des requêtes compatibles avec la cible déclarée ; ne pas
utiliser des fonctionnalités PostgreSQL non couvertes par les tests
SQLite sans un test d’intégration Postgres. Fichiers bruts dans un
stockage content-addressable local configurable ; abstraction S3
seulement à l’extension.

**Traitement.** CLI déterministe (Typer ou argparse), orchestrateur
simple avec jobs reprenables et stages invalidables. Pas de
microservices, Kubernetes, message broker ou GPU obligatoire. Recherche
plein texte/FTS d’abord, vecteurs optionnels seulement après ablation
démontrant un gain.

**Interface.** Streamlit pour vérifier le prototype, avec affichage de
la page et des régions, listes de candidats, spans source, motifs de
décision, statut de droits et corrections persistées. Si le dessin
interactif de polygones devient central, passer à une interface web
spécialisée plutôt que surcharger Streamlit.

**Modèles.** LLM via provider interchangeable ; le fournisseur, le mode
local/remote et les politiques de confidentialité sont explicitement
configurés. Aucun texte sous droits ne part vers une API distante sans
décision appropriée. Similarité d’image DINO/SigLIP à envisager plus
tard, non exigée par les phases d’ingestion.

## 42. API des connecteurs et schéma de capacités

    from typing import Protocol, Literal
    from pydantic import BaseModel

    Status = Literal["yes", "no", "unknown", "blocked"]

    class Capabilities(BaseModel):
        pdf: Status = "unknown"
        iiif: Status = "unknown"
        mets: Status = "unknown"
        alto: Status = "unknown"
        native_text: Status = "unknown"
        editorial_structure: Status = "unknown"
        lawful_download: Status = "unknown"

    class SourceConnector(Protocol):
        async def discover(self, query: str, limit: int): ...
        async def describe(self, source_id: str): ...
        async def list_assets(self, source_id: str): ...
        async def probe_capabilities(self, source_id: str) -> Capabilities: ...
        async def fetch_authorized(self, asset_id: str, policy): ...

Le code ci-dessus décrit un contrat conceptuel. Les vraies signatures
devront être typées avec des classes métier de retour, des identifiants
stables, des erreurs structurées et des paramètres de limitation. Un
connecteur de découverte peut fonctionner même lorsqu’aucun
téléchargement n’est autorisé. Chaque source possède ses tests de
contrat et ses exemples d’erreurs 403/429, timeout, 404, XML invalide,
manifeste partiel et conditions inconnues.

## 43. Architecture des adapters PDF

    class DocumentExtractor(Protocol):
        def extract(self, asset, config) -> "ExtractedDocument": ...

    # Adapters indépendants :
    # NativeAltoMetsExtractor / XbergExtractor / DoclingExtractor
    # PDFGeometryHelper n'est pas un substitut au parsing structuré.

Le ExtractedDocument canonique comprend pages, zones, figures
candidates, blocs textuels, ordre(s), provenance et capacités. Il
comporte **des booléens de disponibilité distincts des résultats
vides**. Chaque adapter documente les informations perdues et son
paramétrage. Un test de sérialisation et un test de réextraction sur les
mêmes octets doivent être identiques à configuration figée ou expliquer
toute variation.

## 44. Pipeline de jobs versionnés

Chaque étape est identifiée par une clé de cache dépendant de
sha256(input_assets), de la version logicielle et des paramètres du
stage. Les sorties sont écrites dans un répertoire temporaire, validées
puis publiées atomiquement avec un manifeste. Les erreurs sont classées
retryable, permanent, policy_denied, quality_review ; la reprise ne
modifie pas les sorties déjà validées et garde une limite de tentatives.

**Schéma d’un job :** discovered → eligible → acquired → extracted →
structured → figure_caption_linked → mentions_extracted →
artwork_candidates → passage_links → reviewed → exportable. Les états
failed, blocked et insufficient_evidence ne sont pas des succès
silencieux. Un document peut progresser pour ses métadonnées alors que
les images restent bloquées.

## 45. Répertoire recommandé

    lesternowak/
      README.md
      CLAUDE.md
      pyproject.toml
      uv.lock
      .env.example
      docs/
        LESTERNOWAK_CADRAGE_V1.md
        PLAN_EXECUTION.md
        architecture/adr/
        sources/{met,getty,heidelberg,cariatide,gallica}.md
        annotation-guide.md
        data-rights-policy.md
        evaluation-protocol.md
        dataset-card.md
      config/{sources.example.yaml,pipeline.example.yaml}
      src/lesternowak/
        domain/{bibliography,documents,artworks,passages,claims,rights}.py
        sources/{base,met,getty,heidelberg,cariatide,gallica}.py
        acquisition/{manifest,fetch,throttle,storage}.py
        parsers/{alto,mets,iiif,quire}.py
        extractors/{base,xberg_adapter,docling_adapter,pymupdf_helper}.py
        layout/{pages,figures,captions,sections,reading_order}.py
        discourse/{mentions,coreference,passages,claims}.py
        identity/{candidates,features,decisions}.py
        linking/{rules,retrieval,rerank,validation}.py
        review/{events,queue}.py
        evaluation/{gold,metrics,ablation,reports}.py
        exports/{policies,jsonl,parquet}.py
        db/{models,migrations,repositories}.py
        cli.py
      app/review.py
      tests/{unit,contract,integration,golden,live_optional}/
      benchmarks/extraction/
      fixtures/README.md
      data/  # gitignored ; pas de documents sous droits dans le dépôt

Les modules ne doivent pas être créés vides « pour faire joli ».
L’arborescence est un objectif architectural ; seules les parties utiles
à la phase active sont implémentées.

# X. Plan Claude Code : 10 lots démontrables

## 46. Principes de collaboration avec Claude Code

Claude Code doit commencer par lire les documents et **inspecter le
dépôt existant**. Ne pas écraser fichiers, branches ni données. Chaque
lot se termine par : résumé, fichiers modifiés, commandes/tests exécutés
avec leur statut, limitations, décisions d’architecture, rapport d’accès
live vs fixture, métriques, risques et prochain lot. Un test non exécuté
est explicitement déclaré non exécuté ; une fixture ne vaut pas
validation d’une API distante.

Ne pas utiliser un agent pour installer simultanément cinq dépendances
lourdes, changer la base et entraîner un modèle : les décisions sont
séquentielles, motivées et réversibles. L’agent demande une décision
uniquement si elle bloque effectivement le code ; pour le reste, il
choisit une option conservatrice, documente son hypothèse et maintient
un changement petit.

## 47. Lot 0. Dépôt, audit et environnement

**Entrée :** cahier des charges et éventuel dépôt existant. **Travail
:** état des lieux Git et dépendances, pyproject.toml, package
installable, CLI lesternowak --help, tests, lint, CI hors réseau, règles
de secrets, stockage local minimal, répertoire docs/architecture/adr,
matrice d’hypothèses et liste des endpoints à vérifier.

**Sortie :** dépôt exécutable sur une machine CPU, sans téléchargement
de modèles au premier démarrage. **Tests :** import, pytest, lint, cli,
migration de test. **Stop :** aucune collecte réelle tant que la
politique de provenance et droits n’existe pas.

## 48. Lot 1. Catalogue de sources et droits, d’abord métadonnées

**Travail :** contrat de connecteur ; un connecteur vertical initial
Met, puis les autres ; modèle SourceRecord, Asset, Capabilities,
RightsDecision ; découverte, pagination, désambiguïsation des notices et
tests de statut ; identité canonique des ressources ; enregistrement des
doublons candidats. Pour Met, utiliser les API documentées v1.1,
enregistrer la version des endpoints.

**Définition de fini :** trois notices réelles par source dans un
inventaire contrôlé, statuts de capacité et de droit explicites, sans
affirmer que les PDF/IIIF/ALTO sont disponibles si non testés. Tous les
connecteurs passent le même test de contrat sur des fixtures. Les tests
live sont séparés, étiquetés, désactivés par défaut.

## 49. Lot 2. Modèle documentaire et fichiers natifs

**Travail :** migrations
bibliographie/édition/numérisation/asset/page/zone ; parser IIIF v2/v3,
ALTO avec unités, METS avec liens structuraux, HTML/Quire seulement
lorsque données effectivement récupérables. Tables de transformation de
coordonnées ; texte brut et dérivé ; manifestes de jobs.

**Définition de fini :** fixtures vérifiées, test de pages dans le bon
ordre, transformation géométrique aller-retour, idempotence de
l’ingestion, exemple de même édition en deux numérisations distinctes,
distinction unknown/none/blocked, jamais de bloc OCR remplacé
silencieusement.

## 50. Lot 3. Benchmark Xberg / Docling / natif

**Travail :** adapters indépendants ; versions épinglées ; configs Xberg
avec options de layout, reading-order et filtrage explicites ; profils
Docling correspondants ; 30 pages annotées multi-source ; rendu
d’overlays ; mesures qualité/vitesse/mémoire ; cas scans/figures
vectorielles et notes.

**Définition de fini :** tableau comparatif, exemples visuels d’erreurs,
scores par document et type de page, fichiers de sortie normalisés,
rapport d’environnement. **Décision :** sélectionner par défaut une
politique de choix de backend par type de document, sans promettre un
vainqueur universel.

## 51. Lot 4. Figures, légendes et structure éditoriale

**Travail :** distinguer figures artistiques des décorations et
graphiques, segmentation des sections et notices, extraction de renvois,
association figures↔légendes, gestion 1:N/N:1, planches et figures sur
pages voisines, index et titres.

**Définition de fini :** jeu de tests multi-figure et légende partagée ;
mesures de figure-légende séparées des mesures OCR ; visualisation des
boîtes et cas d’échec ; chaque figure pointe vers une page et une zone
vérifiables.

## 52. Lot 5. Mentions et identité des œuvres

**Travail :** parser artistes, titres, variantes, dates, numéros
d’inventaire, identifiants et alias ; modèle de mentions et coréférences
; résolution de candidats avec provenance ; traitement des œuvres
absentes des images ; distinction copies/états/détails et attribution
changeante. Interopérabilité Palomar seulement en option, via adapter
sans import circulaire.

**Définition de fini :** tests adversariaux de titres identiques, œuvres
non reproduites, gravure/copie et attribution controversée ; candidats
non fusionnés par similarité seule ; métriques de ranking sur exemples
annotés.

## 53. Lot 6. Rattachement passage-œuvre et rôles

**Travail :** implémenter B0/B1/B2, puis B3 uniquement si le jeu
d’évaluation et le budget existent ; validation des références
explicites ; héritage de section et coréférences ; classification des
rôles ; abstention ; LLM avec sorties JSON, liste de candidats fermée et
citations vérifiées.

**Définition de fini :** précision, rappel, couverture, exemples de
plusieurs œuvres par passage, erreurs et coûts. Toute association
retenue a un span source, une méthode de justification et une version de
décision ; pas de liens automatiques dépourvus de preuve localisable.

## 54. Lot 7. Revue humaine, journal d’événements et désaccords

**Travail :** interface : page, figure, bbox, légende, extrait original,
contexte avant/après, candidats, preuves, statut du lien, statut de
droits ; valider/rejeter/modifier/créer ; historique complet ; file
priorisée par incertitude et diversité des erreurs.

**Définition de fini :** 25 cas tests corrigés et persistés avec
restitution exacte après redémarrage, export d’événements et relecture ;
aucune correction ne détruit l’annotation d’origine ; tests
d’autorisations et de droits d’affichage.

## 55. Lot 8. Extraction prudente d’assertions et exports

**Travail :** sur liens validés, extraire une première taxonomie
d’assertions avec auteurs/modalité/négation et source ; constituer un
jeu limité de cas contradictoires ; export JSONL/Parquet, métadonnées
seules, corpus à droits compatibles, dataset card, identifiants
persistants et manifestes de versions.

**Définition de fini :** chaque assertion retourne à son texte et à son
auteur ; les contradictions ne sont pas écrasées ; une action d’export
deny/unknown est refusée ; les textes restreints ne sont pas contenus
dans les exemples publics.

## 56. Lot 9. Évaluation indépendante et décision d’extension

**Travail :** test sur dix volumes gelés ; métriques par source, type,
langue et qualité OCR ; bootstrap par volume ; ablations B0/B1/B2/B3/B4
quand disponibles ; coût par lien accepté et validé ; erreurs et cas
négatifs ; rapport scientifique et tests de fuite d’images/document.

**Définition de fini :** un rapport ne prétendant pas que les cas non
évalués ont été réussis ; scénarios d’échec ; décisions documentées de
poursuivre, restreindre à certaines classes documentaires ou changer la
conception. Passer à 120 volumes seulement si la précision, la
couverture, les droits et le coût justifient l’extension.

## 57. Définition globale de « terminé »

Le prototype n’est pas terminé lorsqu’une page s’affiche et qu’un modèle
retourne un titre d’œuvre. Il est terminé lorsque l’on peut **reproduire
de bout en bout** : découvrir un volume autorisé, accéder à ses pages,
extraire les éléments, relier au moins un passage à une œuvre avec
preuve, rejeter un lien ambigu, afficher les sources, corriger la
décision, réexécuter sans perdre les données, exporter selon les droits,
et produire une évaluation indépendante montrant à la fois résultats et
échecs.

**Critère négatif non négociable :** aucune tâche automatisée ne peut
promouvoir une hypothèse de machine au statut de lien validé sans règle
explicite de politique et preuve traçable.

# XI. Démarrage concret

## 58. Premier sprint minimal

Pour limiter les dépenses et éviter d’introduire de fausses certitudes,
la première livraison peut être modeste mais réelle : cinq fiches de
source et quinze notices ; un volume PDF moderne et un volume
patrimonial IIIF/ALTO effectivement accessibles ; un schéma
Page/Zone/Figure/Passage ; les deux extracteurs sur quelques pages ; un
tableau des divergences documentaires ; aucun LLM appelé. Le résultat
utile est le **diagnostic empirique des matériaux**, pas le nombre de
classes Python.

## 59. Questions ouvertes et critères d’arrêt

1.  Quelle proportion de catalogues offre de véritables analyses
    développées plutôt que des inventaires ? Mesurer avant l’extension.

2.  Quelles sources offrent légalement un export de texte/image utile à
    un dataset entraînable ? Décision par asset et finalité.

3.  Les index et renvois permettent-ils une récupération efficace de
    commentaires distants ? Mesure sur livres complets.

4.  Les moteurs conservent-ils les notes et les légendes au niveau
    requis ? Benchmark réel Xberg–Docling–natif.

5.  Faut-il une base documentaire plus puissante que SQLite au pilote ?
    Déclencher seulement par charge mesurée.

6.  Les indices visuels améliorent-ils la résolution des détails sans
    augmenter les confusions copies/originaux ? Tester après baseline
    documentaire.

7.  Quelles langues et quels siècles sont réellement couverts par un jeu
    fiable ? Rapporter les strates, y compris les lacunes.

8.  Les assertions peuvent-elles être structurées sans déformer la
    position de l’auteur ? Contrôle expert, sinon rester au passage
    sourcé.

9.  Quels documents et modèles peuvent être partagés publiquement ?
    Filtrer et expliciter les restrictions.

10. Si les performances ne sont bonnes que sur notices à structure
    forte, faut-il assumer ce périmètre plutôt que prétendre lire tout
    ouvrage illustré ? Oui, si les données le démontrent.

## 60. Commande de démarrage à donner à Claude Code

> Lis intégralement docs/LESTERNOWAK_CADRAGE_V1.md, CLAUDE.md et
> docs/PLAN_EXECUTION.md. Inspecte le dépôt Git existant avant toute
> action. Présente en cinq à dix lignes l’état du dépôt, les risques et
> les décisions déjà fixées, puis exécute **uniquement le Lot 0**.
> Respecte les contrats, les tests, les droits et la provenance. Ne
> télécharge aucun corpus sans autorisation explicite. N’installe pas
> Xberg/Docling ni de modèles lourds avant le Lot 3, sauf si nécessaire
> à un test minimal approuvé. À la fin : affiche fichiers modifiés,
> commandes réellement exécutées, résultats de tests, éléments non
> vérifiés et proposition du prochain lot. Ne prétends pas qu’un
> connecteur sur fixtures a été validé en ligne.

# XII. Références vérifiées et traçabilité des décisions

Les sources ci-dessous ont été consultées le **9 novembre 2026**. Elles
documentent les fonctionnalités et interfaces **annoncées** au moment de
la consultation. L’accessibilité réelle des actifs, la présence des
formats et les conditions juridiques restent à tester ressource par
ressource.

- **\[S1\] MetPublications**, présentation des collections éditoriales
  et des liens œuvres–publications :
  <https://www.metmuseum.org/it/met-publications>

- **\[S2\] Metropolitan Museum Collection API**, notes du 4 septembre
  2026, recherche /public/collection/v1.1/search, retrait annoncé de la
  recherche v1, pagination et conditions :
  <https://metmuseum.github.io/>

- **\[S3\] Quire, Getting Started**, publication.yaml, objects.yaml,
  figures.yaml, references.yaml :
  <https://quire.getty.edu/docs-v1/getting-started/>

- **\[S4\] Getty Open Data and APIs**, description des structures
  patrimoniales et de l’écosystème :
  <https://www.getty.edu/projects/open-data-apis/>

- **\[S5\] Heidelberg, interfaces de données ouvertes** :
  <https://www.ub.uni-heidelberg.de/helios/kataloge/datenschnittstellen.html>

- **\[S6\] Heidelberg, notice sur les limites de l’OCR non corrigé** :
  <https://www.ub.uni-heidelberg.de/helios/digi/ocr.html>

- **\[S7\] INHA, Cariatide, interopérabilité et partenariats
  Getty/Gallica** :
  <https://www.inha.fr/actualites/institut-national-histoire-art-rejoint-francearchives/>

- **\[S8\] Exemple Cariatide montrant licence et manifeste IIIF au
  niveau de la notice** :
  <https://bibliotheque-numerique.inha.fr/it/collection/item/64725-vente-au-chateau-d-hautefort-dordogne-vente-du-28-novembre-au-4-decembre-1926>

- **\[S9\] BnF, API Document de Gallica**, extraction ALTO,
  illustrations et ComposedBlock :
  <https://api.bnf.fr/fr/api-document-de-gallica>

- **\[S10\] Library of Congress, ALTO**, principes, coordonnées et
  articulation METS :
  <https://www.loc.gov/standards/alto/description.html>

- **\[S11\] Xberg**, dépôt source, fonctionnalités et installation :
  <https://github.com/xberg-io/xberg>

- **\[S12\] Xberg, documentation de l’architecture et de la migration
  Kreuzberg** : <https://docs.xberg.io/concepts/architecture/> et
  <https://docs.xberg.io/changelog/>

- **\[S13\] Xberg, layout detection et feature gate** :
  <https://docs.xberg.io/guides/layout-detection/>

- **\[S14\] Xberg, extraction**, reading-order désactivé par défaut et
  filtres d’en-tête/pied : <https://docs.xberg.io/guides/extraction/>

- **\[S15\] Xberg, API Python**, pages, images, positions optionnelles :
  <https://docs.xberg.io/reference/api-python/>

- **\[S16\] Docling, modèle documentaire et provenance** :
  <https://docling-project.github.io/docling/concepts/docling_document/>

- **\[S17\] Directive (UE) 2019/790**, articles 3 et 4, fouille de
  textes et de données :
  <https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=oj%3AJOL_2019_130_R_0004>

- **\[S18\] Code de la propriété intellectuelle, article L122-5-3**,
  Légifrance :
  <https://www.legifrance.gouv.fr/loda/id/LEGISCTA000023092377>

- **\[S19\] IIIF Presentation API 3.0**, structure
  Manifest/Canvas/AnnotationPage :
  <https://iiif.io/api/presentation/3.0/>

- **\[S20\] Getty Research Portal**, accès aux publications numérisées
  fédérées :
  <https://www.getty.edu/research-conservation/tools-databases/research-portal/>

- **\[S21\] SemArt**, dataset de référence pour la comparaison
  historique :
  <https://research.aston.ac.uk/en/datasets/semart-dataset/>

- **\[S22\] Explain Me the Painting**, catégorisation
  Form/Content/Context :
  <https://github.com/noagarcia/explain-paintings>

**Conclusion.** LesterNowak doit être évalué non sur sa capacité à
produire un texte vraisemblable à propos d’une image, mais sur sa
capacité à **rendre inspectable la chaîne qui mène d’un ouvrage à une
œuvre, d’une œuvre à une description, d’une description à une
proposition et d’une proposition à une preuve**. L’enjeu est autant
historiographique que technique : rendre les documents utilisables par
des machines sans effacer la singularité, la diversité et l’incertitude
des savoirs qu’ils portent.
