# État courant

Mis à jour à chaque fin de lot. Une nouvelle session commence par lire `CLAUDE.md`, ce fichier,
`docs/PLAN_CORPUS.md` et `docs/PLAN.md`.

## Où on en est (2026-11-17)

- **Lots C0–C7 du plan corpus faits**, en exécution autonome. Chiffres : `reports/corpus/2026-11-17.md`.
- **File de vérification unique** : `data/review/queue-all.jsonl`, 5 351 éléments dont 803 présentés à
  l'aveugle, sur 7 volumes de développement : Terracottas, Berthomieu 1923, Villot 1849, Villot 1875,
  Met 1926, Rococo, Mummy Portraits. (La *Gazette* 1910 n'a aucun lien proposé : abstention.)
- **Aucun lien `validated`** : tout attend le porteur. Précision et temps de vérification non mesurés.
- **Prochain pas** : sessions de vérification du porteur (5 h/semaine), puis mesure de la précision par
  corpus (`lesternowak eval` sur l'export du pilote), puis J2 (`docs/PLAN.md`).

Lancer le pilote :

```bash
uv run lesternowak review-serve --queue data/review/queue-all.jsonl --events data/review/events.jsonl --annotator NOM
```

(127.0.0.1:8765.) Les sorties sous `data/` ne sont pas dans Git ; elles se régénèrent avec les commandes
`build`, `ia-build`, `slice` et `review-queue` (voir `docs/PLAN_CORPUS.md` et `--help`).

## Sélection et volumes tenus à l'écart

- Sélection : `docs/sources/inventory/selection.yaml`. Droits : `docs/sources/rights/`.
- **Tenus à l'écart, gelés** (`gold/heldout-volumes.yaml`, sha256 9370…ca7, ne jamais ouvrir avant le
  gel des règles) : Durrieu–Benoît 1903, Met 1922 (même famille que Met 1926 : test « même famille »
  seulement), vente Luminais 1898, *Conserving Canvas*.
- Les mentions de *Roman Mosaics* et *Mummy Portraits* comme tenus à l'écart dans `docs/PLAN.md`
  (J4/J5) sont **remplacées** par ce gel (`docs/PLAN_CORPUS.md` §6) : *Mummy Portraits* est un volume
  de développement.
- Exclus : Ribes-Christofle 1928 (droits du texte inconnus), Cariatide et Heidelberg (contrôle
  anti-robot, non contourné), textes sous droits, corpus en allemand.

## Décisions prises par l'orchestrateur pendant l'exécution autonome (à relire par le porteur)

1. CC BY-NC accepté (usage de recherche non commercial) : *Rococo*, *Conserving Canvas* ; drapeau NC
   dans les exports.
2. Œuvres anonymes ou collectives : domaine public si publiées au plus tard en 1955 (CPI L123-3).
3. Identification en deux niveaux (ADR 0003) : passage ↔ œuvre de la notice (E1), puis œuvre locale ↔
   référentiel (E0 ou E2 composite, crédit et année = un seul signal).
4. Notice à numérotation trouée → liens `unresolved` plutôt que proposés.
5. Vague 3 Cariatide/Heidelberg remplacée par des catalogues de vente Gallica.

## Limites connues

- OCR dégradé : Berthomieu (38 % de numéros manquants), Villot 1849 (33 %, 617 spans de faible qualité).
- Louvre : aucune source ouverte des anciens numéros → aucune résolution externe pour les catalogues
  français.
- Met 1926 : 135 résolutions sur 1 511 notices ; le référentiel ne couvre que les peintures européennes
  (les peintures américaines manquent).
- Périodiques : un seul article de la *Gazette* dont l'auteur est vérifié dans le domaine public
  (Wikidata a limité les requêtes) ; seconde passe à faire lentement.
- Incident : après un 403 du Met, un agent a tenté une requête avec un autre User-Agent ; elle a été
  bloquée et abandonnée. La règle de non-contournement est rappelée dans tous les briefs.

## Historique

- J1 (guide d'annotation, feuille, import, banc d'évaluation, accord) : fait ; B0 non mesuré.
- Étape 2 : tranche verticale Terracottas.
