# Plan d'exécution réordonné

Ce plan remplace l'ordre des lots 0–9 du cadrage (§47–56), qui plaçait le premier lien
œuvre↔passage au lot 6. Il applique la note `docs/reference/OBJECTIF_PRODUIT.md` : une tranche
verticale réelle d'abord, l'architecture ensuite. Les exigences scientifiques et juridiques du
cadrage restent valables ; elles sont introduites quand une étape en a besoin.

Contraintes connues : un seul vérificateur (le porteur, chercheur), pas d'annotateurs ; LLM distant
autorisé (voir `docs/adr/0001-regles-avant-modeles.md`).

## Étape 0 — Dépôt minimal ✅

Package installable, CLI `--help`/`--version`, pytest, ruff, CI hors réseau, `CLAUDE.md`, docs.
Pas de base de données, pas de connecteur, pas de dépendance lourde.

## Étape 1 — Choix du premier catalogue et fiche de droits

Entrée : `docs/sources/getty-quire.md` (candidats vérifiés le 2026-11-12).
Sortie : choix du porteur ; fiche de droits par actif et par action (texte, images, données,
TDM, LLM distant, publication, redistribution) avec preuves (URL + date de consultation).

## Étape 2 — Tranche verticale (démonstration minimale)

Sur le catalogue choisi :
1. récupérer licitement les pages HTML et les données structurées de quelques entrées (cache local
   dans `data/`, empreintes sha256, date de capture) ;
2. extraire les sections d'entrée (Description, Discussion/Commentary, Provenance, Bibliography)
   avec leurs offsets dans le texte source ;
3. modèle minimal Pydantic : `Surrogate`, `Page`, `Span`, `Figure`, `ArtworkRef`, `Link`,
   `RightsDecision`, `Run` ; export JSONL ;
4. **3 à 5 enregistrements validés à la main** par le porteur, dont au moins un cas difficile
   (discussion partagée par plusieurs œuvres, comparaison avec une œuvre non reproduite) ;
5. page HTML statique d'inspection : passage surligné, œuvre (lien collection), justification,
   droits, lien vers la page source.

Critère de sortie : le porteur ouvre la source d'un exemple et vérifie passage, œuvre et lien.
Ces enregistrements deviennent la fixture de référence (texte CC BY : versionnable).

## Étape 3 — Rattachement automatique par règles, document tenu à l'écart

- Règles E0 (appels explicites) et E1 (structure de notice), candidats fermés par volume ;
  abstention sinon.
- Classement de la fonction du passage : baseline lexicale, liste unique de 5 à 7 valeurs avec
  guide d'annotation court (`docs/annotation-guide.md`).
- Évaluation sur une **2ᵉ publication jamais regardée pendant le réglage** : 50 à 100 candidats
  jugés par le porteur (positifs, négatifs, incertains) ; précision, abstentions, faux liens,
  intervalle de Wilson.
- Ré-annotation à l'aveugle de 15–20 % des cas quelques semaines plus tard (accord intra-annotateur,
  substitut documenté à la double annotation).

## Étape 4 — Deuxième famille de sources et benchmark d'extraction

- Une source de nature différente : PDF (MetPublications, ou le PDF du catalogue de l'étape 2,
  qui permet de comparer natif et PDF sur un contenu identique) ou ALTO (Gallica/Heidelberg).
- Benchmark Xberg / Docling / natif sur les pages de cette source uniquement, versions épinglées,
  configurations consignées.
- Champ `text_fidelity` (né numérique / OCR brut / corrigé) obligatoire dès l'arrivée d'OCR.

## Étape 5 et suivantes — selon les métriques

Dans l'ordre de la note produit : mesurer et améliorer le rappel à précision maîtrisée ; étendre
(sources, langues, mises en page) ; interface de revue et journal d'événements ; exports filtrés
par droits (export standoff d'abord : identifiants et offsets, sans texte) ; dataset card.
Assertions historiographiques, coréférence fine, graphes et RDF seulement ensuite, s'ils apportent
une valeur démontrée.

SQLite/Alembic, connecteurs multiples, petit modèle entraîné et LLM : introduits chacun quand une
étape en démontre le besoin, avec ablation pour les modèles.
