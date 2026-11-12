# LesterNowak

LesterNowak extrait de publications d'histoire de l'art numérisées de **véritables passages
d'analyse**, écrits par des auteurs identifiables, les rattache à la bonne œuvre avec une preuve
vérifiable, et constitue des jeux de données dont la provenance et les droits par usage sont
explicites.

Il ne génère aucun commentaire, n'analyse pas les images de manière autonome et n'affirme pas que
les interprétations sont vraies : il les attribue à leur source.

Le nom vient de Lester K. Nowak, critique fictif d'*Un cabinet d'amateur* (Georges Perec, 1979).

## État

Étape 0 : squelette du dépôt. Aucune extraction n'est encore implémentée.
Voir [`docs/PLAN.md`](docs/PLAN.md) pour la suite et [`docs/EVALUATION.md`](docs/EVALUATION.md)
pour l'évaluation critique du cadrage initial.

## Développement

```bash
uv sync
uv run pytest -m "not live"
uv run lesternowak --help
```

## Documents

- [`docs/reference/OBJECTIF_PRODUIT.md`](docs/reference/OBJECTIF_PRODUIT.md) — note d'orientation produit (normative)
- [`docs/reference/LESTERNOWAK_CADRAGE_V1_1.md`](docs/reference/LESTERNOWAK_CADRAGE_V1_1.md) — cadrage scientifique et technique
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — évaluation du cadrage
- [`docs/PLAN.md`](docs/PLAN.md) — plan d'exécution réordonné
- [`docs/adr/`](docs/adr/) — décisions d'architecture
- [`docs/sources/`](docs/sources/) — fiches de sources et de droits
