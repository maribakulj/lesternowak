# ADR 0003 — Identification des œuvres en deux niveaux

- Statut : accepté (2026-11-17), décision prise par l'orchestrateur en exécution autonome
- Contexte mesuré : lot C0 (`docs/sources/inventory/`)

## Contexte

L'échantillonnage C0 montre que les catalogues anciens retenus ne citent presque jamais les
identifiants actuels des musées :
- catalogues du Met de 1922 et 1926 : aucun numéro d'accession, mais des lignes de dimensions
  (« H. … W. … ») et des lignes de crédit avec année d'entrée pour la plupart des notices ;
- catalogues Gallica (Louvre, musées de province) : notices numérotées (médiane de 578 par volume),
  numéros d'inventaire rares (« inv. » présent dans 4 volumes sur 29) ;
- catalogues de vente : numéros de lot.

La preuve E0 par numéro d'accession, prévue dans `docs/PLAN_CORPUS.md`, ne s'applique donc pas à ces
volumes.

## Décision

Séparer deux problèmes, mesurés séparément (cadrage §25) :

1. **Passage ↔ œuvre de la notice (niveau document).** Chaque notice numérotée définit une œuvre
   *locale* au volume (`artwork_local_id` = volume + numéro de notice). Le rattachement d'un passage
   de la notice à cette œuvre est une preuve E1 (structure de notice). C'est la sortie principale, et
   elle vaut même sans identifiant externe.
2. **Œuvre locale ↔ référentiel externe (niveau identité).** Proposée seulement :
   - par E0 : identifiant actuel cité et résolu dans le référentiel ;
   - ou par **E2 composite** : au moins **deux attributs indépendants** concordants (ligne de crédit,
     année d'entrée, dimensions à tolérance fixée, ancien numéro de catalogue sourcé dans le
     référentiel), avec l'artiste ou le titre en appui, et **un seul candidat** restant. Sinon
     `unresolved`.
   - Aucune résolution sur le seul titre ou le seul artiste.
   - Correction (lot C3–C5) : la ligne de crédit et l'année d'accession ne sont pas indépendantes (le
     crédit porte l'année d'entrée) ; elles comptent pour **un seul** signal, les autres étant
     les dimensions et l'ancien numéro sourcé.

Images :
- œuvre résolue : image du référentiel si sa licence le permet (Met Open Access, etc.) ;
- sinon, planche du volume lui-même (domaine public) lorsque la figure est rattachée à la notice
  par son numéro ou sa légende ;
- sinon, aucune image : le lien texte reste valide.

## Conséquences

- Le dataset distingue `artwork_local_id` (toujours présent) et `external_ids` (souvent vides au
  début), avec la preuve de chaque résolution.
- Deux mesures distinctes dans le pilote et le rapport C7 : précision du rattachement passage ↔
  notice ; précision et couverture de la résolution externe.
- La concordance des anciens numéros du Louvre devient une tâche de référentiel (C2), alimentée par
  les sources qui la documentent ; elle n'est jamais inférée.
