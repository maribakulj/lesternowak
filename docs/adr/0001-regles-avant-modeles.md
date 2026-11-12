# ADR 0001 — Règles et structure d'abord, modèles seulement s'ils gagnent à l'ablation

- Statut : accepté
- Date : 2026-11-12

## Contexte

Le produit exige des liens œuvre ↔ passage dont la preuve est localisable et vérifiable. Un LLM
distant est autorisé, mais ses sorties ne sont ni calibrées ni des preuves. Le projet dispose d'un
seul vérificateur humain (le porteur, chercheur) et pas d'annotateurs.

## Décision

Chaque sous-problème utilise la méthode la plus simple et la plus explicable qui suffit :

| Sous-problème | Méthode par défaut | Escalade possible |
|---|---|---|
| Structure (pages, notices, figures, légendes) | Lecture de la structure native (Quire, IIIF, ALTO/METS), sinon PDF via adapter | Benchmark Xberg / Docling (étape 4) |
| Appels explicites (fig., pl., cat. no., Abb., Taf., n° d'inventaire) | Expressions régulières par langue + graphe de renvois | — |
| Héritage du sujet d'une notice | Règles sur la structure éditoriale | — |
| Résolution de l'œuvre citée | Liste **fermée** de candidats par volume (données de l'éditeur) + spaCy/rapidfuzz | Reranker entraîné |
| Coréférence (« ce tableau », « l'autre version ») | Règles locales simples ; sinon `unresolved` | Modèle, après mesure |
| Fonction du passage (description, iconographie, attribution…) | Indices lexicaux + petit classifieur (scikit-learn) | Petit encodeur affiné sur données validées ; LLM comme comparateur |

Usage du LLM, quand il est employé :
- entrée : passage exact, contexte borné, liste fermée de candidats avec identifiants ;
- sortie : JSON sous schéma versionné, avec citations par identifiant de span ;
- vérification automatique que toute citation existe dans le texte source ; sinon rejet ;
- statut `model_suggested`, jamais `validated` sans action humaine tracée ;
- conservé dans le pipeline uniquement s'il améliore la couverture **à précision fixée** sur un
  document tenu à l'écart ;
- comme assistant d'annotation : une partie de l'échantillon est d'abord annotée à l'aveugle pour
  mesurer le biais d'ancrage ;
- aucun texte dont la décision de droits pour l'action `remote_llm` n'est pas `allow` n'est envoyé.

## Conséquences

- Les premiers résultats seront à forte précision et couverture modeste, ce qui est voulu.
- Les dépendances lourdes (spaCy, modèles, Xberg, Docling) n'entrent qu'à l'étape qui les exige.
- Chaque signal de preuve (E0–E5 du cadrage) est conservé séparément dans l'enregistrement.
