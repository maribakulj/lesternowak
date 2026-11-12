# Évaluation du cadrage LesterNowak (v1.1) — 2026-11-09, mise à jour 2026-11-12

Évaluation critique de `docs/reference/OBJECTIF_PRODUIT.md` et
`docs/reference/LESTERNOWAK_CADRAGE_V1_1.md` avant tout développement.

## Verdict

- **Thèse produit solide et différenciante.** Les datasets existants (SemArt, Explain Me the
  Painting…) associent images et textes sans auteur attribué, sans preuve du lien et sans droits
  par usage. Le créneau « passage authentique, attribué, prouvé, avec droits » est réel.
- **Cadrage scientifique excellent** : figure ≠ œuvre, mention ≠ analyse, assertion attribuée ≠
  fait, abstention valorisée.
- **Plan d'exécution en contradiction avec sa propre note** : sur-architecturé, infrastructure
  avant données (premier lien œuvre↔passage au lot 6).
- **Risques principaux non techniques** : droits sur les textes, capacité d'annotation, choix du
  premier catalogue.

## Affirmations vérifiées (2026-11-09)

| Affirmation | Résultat |
|---|---|
| API Met : `/public/collection/v1.1/search` paginé, migration depuis v1 demandée | confirmé (metmuseum.github.io) |
| Xberg : `reading_order` désactivé par défaut ; migration depuis Kreuzberg | confirmé (docs.xberg.io) |
| Dépôt GitHub Xberg | non vérifié (403 depuis l'environnement) |
| API Met joignable, `isPublicDomain` exposé | confirmé |

## Points forts à conserver

1. Définition opérationnelle du livrable (œuvre + passage exact + page + justification + droits).
2. Hiérarchie des preuves E0–E5 ; interdiction du score visuel comme preuve unique.
3. Droits par actif × action ; `unknown` ≠ `allow`.
4. Valeurs nulles typées (`access_denied` ≠ `not_observed`).
5. Évaluation par document tenu à l'écart et bootstrap par volume.
6. Section « ce que le projet n'est pas ».

## Problèmes et corrections

1. **Ordre du plan** (critique) — le plan 0–9 inverse la priorité de la note ; « Lot 2A » non
   défini ; v1.0/v1.1 incohérents ; `CLAUDE.md` et `PLAN_EXECUTION.md` cités mais absents.
   → `docs/PLAN.md` réordonné autour de la tranche verticale ; `CLAUDE.md` court.
2. **Premier catalogue non choisi.** → Catalogue Getty Quire sous CC BY (voir
   `docs/sources/getty-quire.md`). Cas facile assumé ; le document tenu à l'écart devra ensuite
   être de nature différente (PDF ou ALTO).
3. **Droits vs promesse « IA »** — les catalogues les plus analytiques sont modernes et protégés ;
   les fonds anciens ont un OCR sale. → Mesurer tôt droits × densité analytique ; export
   **standoff** (identifiants + offsets) par défaut.
4. **« Texte original exact » vs OCR non corrigé.** → Champ `text_fidelity` obligatoire.
5. **Trois taxonomies concurrentes** (rôles §13, taxonomie §28, « fonction » de la note).
   → Une liste unique de 5 à 7 valeurs pour la tranche, avec guide court.
6. **Schéma trop large** (18 entités, Alembic au lot 0). → ~8 objets Pydantic + JSONL ; base de
   données quand un besoin mesuré l'impose.
7. **Benchmark Xberg/Docling trop tôt.** → Sur les pages du premier PDF réellement retenu.
8. **Capacité humaine non dimensionnée.** → Voir décisions ci-dessous.
9. **Supervision faible sous-exploitée** : listes d'œuvres par volume (MetPublications, données
   Quire) = candidats fermés, levier principal de précision.

## Décisions du porteur (2026-11-12)

- Recommandations acceptées.
- **Aucun annotateur** : le porteur vérifie seul sur le catalogue original. Conséquences :
  cibles réduites (≈ 100–150 liens jugés pour la première mesure), accord intra-annotateur par
  ré-annotation à l'aveugle différée, limite documentée dans la dataset card.
- **Statut : chercheur.** L'exception TDM de l'art. 3 de la directive 2019/790 (L122-5-3 CPI)
  vise les organismes de recherche et institutions patrimoniales : elle s'applique si le travail
  est mené dans le cadre d'un tel organisme ; sinon régime de l'art. 4 (opt-out possible). Sans
  objet pour les sources sous CC BY.
- **LLM distant autorisé**, dans le cadre de `docs/adr/0001-regles-avant-modeles.md` : règles et
  TAL d'abord ; LLM comme comparateur ou assistant d'annotation, gardé seulement s'il gagne à
  l'ablation.
