# ADR 0002 — Une seule liste de relations et une seule liste de fonctions

- Statut : accepté (2026-11-14), sous réserve de la relecture du guide par le porteur (H1a)
- Remplace : l'énumération `PassageRole` de l'étape 2 ; les listes concurrentes du cadrage
  (§13 rôles, §28 taxonomie) pour le MVP.

## Contexte

Le cadrage proposait trois listes qui se recouvrent (13 rôles, 16 classes + 5 axes, « fonction » de
la note produit). Elles sont inannotables par une seule personne et non mesurables sur un petit
corpus. La lecture des 37 paragraphes de la discussion partagée (cats. 1–3) montre en outre que
beaucoup de paragraphes sont de l'arrière-plan (tradition iconographique, comparanda) sans
affirmation sur l'objet.

## Décision

Deux axes indépendants :

1. **Relation** paragraphe ↔ œuvre : `about`, `group`, `context`, `mentions`, `not_about`, `unsure`.
   Positif strict = `about` ; tolérant = `about` ∪ `group`.
2. **Fonction** du paragraphe (une valeur) : `visual_description`, `technical_material`,
   `iconography_interpretation`, `comparison`, `attribution_dating`, `provenance_context`, `other` ;
   `unclassified` réservé aux prédictions (abstention).

Définitions et cas limites : `docs/annotation-guide.md`.

## Conséquences

- La règle structurelle B0 (« tout paragraphe d'une discussion de groupe concerne chaque membre »)
  devient mesurable et sera vraisemblablement peu précise en strict : c'est attendu.
- Les catégories du cadrage (assertions, controverses, rôles fins) restent possibles plus tard,
  comme raffinements d'une valeur existante, après mesure.
- Fusionner des classes si leur F1 reste faible (plan §6) plutôt qu'en ajouter.
