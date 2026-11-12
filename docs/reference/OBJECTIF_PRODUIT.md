# NOTE D’ORIENTATION PRODUIT — LESTERNOWAK v1.1

**Cette note est normative et prime, pour l’ordre des priorités, sur les formulations plus générales de la spécification v1.0. Elle n’annule ni ses exigences scientifiques ni ses contraintes juridiques.**

## En une phrase

**LesterNowak extrait automatiquement de véritables analyses d’histoire de l’art contenues dans des publications numérisées, les rattache à la bonne œuvre et constitue des datasets multimodaux vérifiables pour la recherche et l’IA.**

## Les entrées

Des livres et catalogues d’art numérisés (PDF, pages IIIF, ALTO, METS, textes éditoriaux structurés), provenant d’abord de MetPublications, Getty, Heidelberg, Cariatide et Gallica, lorsque l’accès et les usages visés sont autorisés.

## La sortie principale, non négociable

Un jeu de **liaisons œuvre ↔ passage analytique authentique**, exportable en JSONL/Parquet, contenant au minimum :

- l’identifiant stable de l’œuvre et, si autorisé, sa reproduction ou son URI ;
- l’identifiant de la figure éditoriale lorsqu’elle existe (une œuvre peut être mentionnée sans illustration) ;
- le **texte original exact** d’un passage qui analyse l’œuvre, distinct de la simple légende et de simples métadonnées ;
- sa fonction (description formelle, iconographie, interprétation, attribution, provenance, comparaison, etc.), avec catégories révisables ;
- la publication, l’auteur du passage si connu, l’édition/numérisation, la ou les pages, la citation/zone source ;
- le type et la force de preuve du rattachement, son état de validation et la possibilité `unresolved` ;
- les droits et restrictions d’usage **distincts pour image, texte, TDM/entraînement, publication et redistribution** ;
- les versions du pipeline et la trace de toute correction humaine.

Les commentaires sont des textes d’historiens ou d’auteurs identifiables, **pas des légendes inventées par un LLM**. Le système n’a pas à affirmer que l’interprétation est vraie : il attribue la proposition à sa source.

## Démonstration minimale attendue avant de développer une grosse architecture

Sur **un catalogue réel accessible et autorisé**, LesterNowak doit produire un enregistrement inspectable reliant : (1) une œuvre/figure identifiée, (2) un passage d’analyse réellement extrait et non fabriqué, (3) sa page et son passage exact, (4) une justification du lien, (5) un état des droits. Pour la toute première démonstration, une partie du rattachement peut être validée manuellement ; elle sert ensuite de fixture de référence. Les tests synthétiques n’équivalent pas à cette preuve en conditions réelles.

Ensuite, démontrer au moins un rattachement automatique sur un document tenu à l’écart du réglage des règles ; mesurer aussi les faux rattachements et les abstentions. **Le succès du projet se mesure en exemples utilisables et vérifiables, pas en nombre de classes, de connecteurs déclarés ou de lignes de code.**

## Priorités et ordre des arbitrages

1. Produire une *vertical slice* réelle bout en bout sur une publication et un exemple d’analyse.
2. Mesurer extraction des figures, qualité des passages, et précision des liens œuvre-passage ; améliorer le rappel à précision maîtrisée.
3. Étendre à d’autres catalogues, langues, mises en page et sources.
4. Produire des exports adaptés aux droits et des jeux d’évaluation non contaminés.
5. Ajouter seulement ensuite les assertions historiographiques fines, contradictions, graphes ou enrichissements RDF lorsqu’ils apportent une valeur démontrable.

## Décisions techniques

Xberg est un candidat prioritaire pour les PDF ; Docling est le comparateur. L’usage des fichiers natifs IIIF/ALTO/METS prévaut lorsqu’il fournit une meilleure fidélité. Le backend est choisi après benchmark sur les figures, légendes, coordonnées, notes, ordre de lecture et texte, **pas sur le débit seul**. Le schéma doit permettre de distinguer le document et sa numérisation, l’illustration imprimée et l’œuvre, la mention et le commentaire, le fait établi et la thèse attribuée.

## Ce que LesterNowak n’est pas

Ce n’est ni un VLM qui analyse des tableaux de manière autonome, ni un simple OCR, ni un moteur de légendes, ni un agent qui produit des dissertations, ni un remplaçant de Palomar ou Lermolieff. L’usage ML est un objectif de valorisation du corpus, **pas un droit automatique d’entraînement sur tout document accessible**.

## Trois vérifications de fin de lot pour Claude Code

1. **Quel progrès observable ce lot apporte-t-il vers un dataset œuvre↔analyse authentique ?** Si aucun, il faut justifier précisément le blocage levé.
2. **Puis-je ouvrir la source d’un exemple et vérifier le passage, l’œuvre et le lien ?** Si non, l’extraction n’est pas démontrée.
3. **Ai-je distingué preuve directe, suggestion de modèle, hypothèse non résolue et interdiction d’usage ?** Si non, le lot n’est pas validé.
