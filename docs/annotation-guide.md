# Guide d'annotation — rattachement œuvre ↔ paragraphe et fonction du paragraphe

Version 1 — 2026-11-14. Corpus dev : *Ancient Terracottas*, cats. 1–4.
Annotateur : le porteur, en lisant chaque paragraphe **sur la page en ligne du catalogue**
(colonne `source_url`), avec son contexte (paragraphes voisins, titre de la discussion, figures).

## 1. Ce que l'on annote

Pour chaque **paragraphe** (une ligne de la feuille) :

1. pour chaque œuvre candidate (colonnes `relation_cat1` … `relation_cat4`) : **la relation** entre
   le paragraphe et cette œuvre ;
2. une seule fois par paragraphe : **la fonction principale** du paragraphe ;
3. facultatif : une `note` libre pour un doute, une erreur de texte ou un cas intéressant.

On juge ce que **l'auteur écrit**, jamais si c'est vrai. On ne corrige pas le texte.

## 2. Relation paragraphe ↔ œuvre (une valeur par œuvre candidate)

| Valeur | Quand l'utiliser |
|---|---|
| `about` | Le paragraphe **affirme quelque chose sur cette œuvre précise** : son aspect, sa technique, son identification, son interprétation, sa datation, son attribution, sa provenance, ou une comparaison où elle est le terme comparé. La référence peut être explicite (« cat. 2 », « Siren B ») ou sans ambiguïté (« the seated figure » = cat. 1 ; « the two sirens » = cats. 2 et 3). |
| `group` | Le paragraphe parle **du groupe comme ensemble** sans distinguer cette œuvre (« the Getty group was created for a purely religious context »). Chaque membre du groupe reçoit `group`. |
| `context` | Arrière-plan **sans affirmation sur l'œuvre** : histoire d'un type iconographique, d'une doctrine, d'un site, comparanda décrits pour eux-mêmes. Le paragraphe sert l'argument mais ne dit rien de l'objet. |
| `mentions` | L'œuvre est **citée en passant** (renvoi, liste, inventaire) sans rien en dire. |
| `not_about` | Le paragraphe ne concerne pas cette œuvre (il porte sur un autre membre du groupe ou sur autre chose). |
| `unsure` | Impossible de trancher même avec le contexte. Écrire la raison dans `note`. |

Règles de décision :

- **Un paragraphe peut être `about` pour plusieurs œuvres** (« the two sirens… » → cats. 2 et 3).
- Si un paragraphe parle d'abord du groupe puis précise une œuvre, l'œuvre précisée est `about`,
  les autres `group`.
- **Sirène A / Sirène B** : « the siren » au singulier sans précision → `about` pour les deux seulement
  si l'énoncé vaut manifestement pour les deux ; sinon `unsure`. « Siren B » explicite → `about`
  pour cat. 3, `not_about` pour cat. 2, sauf comparaison explicite des deux.
- Un comparandum externe (le Pindare du Serapeion, un vase apulien) n'est pas une œuvre du corpus :
  le paragraphe est `about` l'œuvre du corpus **si** la comparaison porte sur elle (« The Getty figure
  is closely comparable with… ») ; s'il décrit seulement le comparandum ou la tradition, `context`.
- L'héritage du sujet n'est pas automatique : un paragraphe sur les sirènes en général (« Sirens were
  portrayed in the Archaic period with birds' bodies… ») est `context`, même dans la discussion du
  groupe.
- Les cases « - » (œuvre non candidate) peuvent être remplacées si le paragraphe la concerne
  vraiment : c'est une information utile (candidat manqué).

## 3. Fonction principale du paragraphe (une valeur par ligne)

| Valeur | Contenu dominant |
|---|---|
| `visual_description` | Ce qui se voit : pose, vêtement, attributs, forme, état visible. |
| `technical_material` | Fabrication, argile, moulage, cuisson, polychromie, analyses scientifiques, restaurations. |
| `iconography_interpretation` | Identification du sujet, sens, fonction religieuse ou funéraire, lecture symbolique. |
| `comparison` | Mise en rapport avec d'autres œuvres (parallèles, prototypes, ateliers). |
| `attribution_dating` | Attribution à un atelier, un coroplathe, un cercle ; datation et ses arguments. |
| `provenance_context` | Provenance, acquisition, collection, contexte de découverte ou de destination. |
| `other` | Rien de ce qui précède ne domine (transition, généralités, historiographie pure). |

Si plusieurs fonctions coexistent, choisir **celle qui occupe le plus de texte** ; en cas d'égalité,
celle qui porte la conclusion du paragraphe. Noter la seconde dans `note` si elle est importante
(ex. « aussi attribution_dating »).

## 4. Exemples tirés du corpus dev

| Paragraphe (début) | Relations | Fonction |
|---|---|---|
| Description cat. 1 : « The male figure is shown sitting on a klismos (seat)… » | cat. 1 `about` | `visual_description` |
| Discussion §0 : « An investigation conducted with endoscopic instruments revealed… this sculptural group » | cats. 1–3 `group` (sauf mention précise d'une figure) | `technical_material` |
| Discussion §3 : « The seated figure has been identified as Orpheus… » | cat. 1 `about` ; cats. 2–3 `not_about` | `iconography_interpretation` |
| Discussion §17 : « Sirens were portrayed in the Archaic period with birds' bodies… » | cats. 2–3 `context` ; cat. 1 `not_about` | `iconography_interpretation` ou `comparison` selon le texte complet |
| Discussion §19 : « …attested by both the pose of Siren B and a copious literary tradition… » | cat. 3 `about` ; cat. 2 selon la suite | `iconography_interpretation` |
| Discussion §36 : « …the group can only be generally dated to the last thirty years of the fourth century BC… » | cats. 1–3 `group` | `attribution_dating` |
| Discussion cat. 4, §1 : « In the documentation about this acquisition… Jacob Hirsch… » | cat. 4 `group` (discussion des cats. 4–23) | `provenance_context` |

Ces exemples sont des indications pour fixer la règle, pas des réponses : le porteur tranche sur le
texte complet.

## 5. Procédure

1. Ouvrir la feuille `data/annotation/sheet-dev-v1.csv` dans un tableur (UTF-8).
2. Remplir ligne par ligne en ouvrant `source_url`. Ne pas modifier les colonnes `span_id` et `text`
   (l'import vérifie que le texte est identique au passage extrait).
3. Importer : `uv run lesternowak annotation-import --sheet data/annotation/sheet-dev-v1.csv --annotator NOM --out gold/terracottas/dev-v1.jsonl`.
4. Au moins une semaine plus tard : feuille à l'aveugle de 20 paragraphes tirés au hasard
   (`annotation-sheet --sample 20 --seed …`), import dans `dev-v1-reannot.jsonl`, puis
   `lesternowak agreement`. Si l'accord (kappa) est inférieur à 0,8 sur les relations, le guide est
   revu avant toute mesure.

## 6. Ce que le gold sert à mesurer

- Rattachement strict : `about` = positif. Tolérant : `about` ∪ `group`.
- Fonction : exactitude et F1 par classe.
- Les couples `unsure` sont exclus des métriques et comptés à part.

## 7. Pilote de vérification

Interface locale (lot C6) pour vérifier les liens un à un, sans feuille CSV. Les décisions sont
ajoutées à `events.jsonl` (append-only) ; rien n'est jamais réécrit.

```bash
uv run lesternowak review-queue --slice data/slice --out data/review/queue.jsonl --blind-rate 0.15 --seed 7
uv run lesternowak review-serve --queue data/review/queue.jsonl --events data/review/events.jsonl --port 8765 --annotator NOM
# ouvrir http://127.0.0.1:8765/ ; Ctrl+C pour arrêter, relancer la même commande pour reprendre
uv run lesternowak review-export --queue data/review/queue.jsonl --events data/review/events.jsonl --out gold/<corpus>/review-v1.jsonl
```

La file alterne sections, types de preuve et œuvres. 15 % des éléments sont **à l'aveugle** : aucune
proposition n'est affichée, on choisit relation et fonction ; ces éléments servent à mesurer la
précision des propositions. Au démarrage, les éléments déjà décidés sont sautés. Le serveur écoute
sur 127.0.0.1 ; l'image de l'œuvre n'est affichée que si ses droits le permettent (sinon, lien).

| Touche | Action |
|---|---|
| `1` à `6` | relation : about, group, context, mentions, not_about, unsure |
| `q w e r t y u` | fonction : visual_description, technical_material, iconography_interpretation, comparison, attribution_dating, provenance_context, other |
| `v` / `x` / `n` | décision (éléments non aveugles) : valider / rejeter / non résolu |
| `Tab` (`Échap`) | aller à la note (revenir aux raccourcis) |
| `Entrée` | enregistrer et passer au suivant |
| `←` | élément précédent (une nouvelle décision s'ajoute, la dernière fait foi) |

Valider exige relation et fonction (préremplies depuis la proposition quand elle existe). Pour un
élément à l'aveugle, `unsure` donne `unresolved`, toute autre relation est enregistrée telle quelle.
