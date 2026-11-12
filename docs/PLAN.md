# Plan d'exécution v2 — LesterNowak

Version 2026-11-12. Remplace le plan v1 (étapes 0–5). Les exigences scientifiques et juridiques
du cadrage (`docs/reference/`) restent valables ; elles entrent dans le code quand un lot en a
besoin. L'état courant est tenu à jour dans `docs/STATUS.md`.

---

## 1. Principes de développement agentique appliqués

### 1.1 Boucle d'un lot

Chaque lot suit la même boucle, sans raccourci :

1. **Spécifier** : objectif en une phrase, entrées, sorties, critères de sortie *exécutables*
   (commande + seuil), interdits.
2. **Tests d'acceptation d'abord** : écrits ou mis à jour avant l'implémentation.
3. **Implémenter** par petits commits verts (lint + tests passent à chaque commit).
4. **Vérifier** : lancer les critères de sortie ; distinguer réel / fixture.
5. **Revue indépendante** : un agent frais reçoit le diff et la spécification, pas la conclusion
   de l'implémenteur ; il cherche les erreurs et les écarts aux règles de `CLAUDE.md`.
6. **Rapport** de fin de lot (gabarit §5.2) et mise à jour de `docs/STATUS.md`.
7. **Point de contrôle humain** lorsque le lot en prévoit un (marqué **H**).

### 1.2 Règles de conduite

- **Une question par lot.** Un lot fait avancer une seule capacité mesurable ; diff visé
  ≤ ~400 lignes hors fixtures.
- **Mesurer avant d'améliorer.** Aucune règle ni aucun modèle n'est ajouté sans une référence
  humaine pour le mesurer et une baseline mesurée avant lui.
- **Pas de réglage sur le test.** Les ensembles de test sont gelés (fichier de partition + empreinte
  sha256) *avant* d'être regardés. Les règles sont figées par un tag Git avant chaque évaluation
  tenue à l'écart.
- **Ablation obligatoire** pour tout ajout de méthode (B0 → B1 → B2 → …), sur le même jeu gelé.
- **Rapporter l'abstention** à côté de la précision ; un gain de précision obtenu en abstenant
  davantage est rapporté comme tel.
- **Pas de faux succès.** Un test non exécuté est déclaré non exécuté ; une fixture ne valide pas
  une source distante ; un échec est rapporté avec sa sortie.
- **Reprise sans mémoire.** Une nouvelle session doit pouvoir repartir de `CLAUDE.md`,
  `docs/STATUS.md` et ce plan, sans relire l'historique de conversation.
- **Décisions tracées.** Toute décision d'architecture ou de méthode non triviale → ADR dans
  `docs/adr/`.
- **Réversibilité.** Sorties append-only ; les décisions humaines (événements) ne sont jamais
  écrasées par une réexécution ; identifiants déterministes.
- **Budget.** Chaque lot a un budget indicatif ; dépassement → arrêt et rapport plutôt que fuite
  en avant.

### 1.3 Répartition des rôles et des modèles

| Rôle | Qui | Tâches |
|---|---|---|
| Porteur (vérité terrain) | humain | choix, annotations, validation, arbitrages |
| Orchestrateur | modèle principal | spécification, briefs, revue finale, décisions, rapports au porteur |
| Implémenteur | sous-agent Sonnet | code, tests, exécution des critères de sortie, commit |
| Tâches mécaniques | sous-agent Haiku | inventaires de pages, vérification de licences et de liens, mise en forme de fixtures, rapports tirés de JSON de métriques, contrôles de cohérence |
| Relecteur | sous-agent frais (Sonnet) | revue du diff contre la spec et `CLAUDE.md`, sans la conclusion de l'implémenteur |

Règles de délégation :
- l'orchestrateur ne refait pas ce qu'il a délégué ; il vérifie par échantillonnage
  (une commande, un fichier, un exemple) ;
- un brief = la seule mémoire de l'agent : il suit le gabarit §5.1 ;
- tâches indépendantes lancées en parallèle ; tâches dépendantes en séquence ;
- rapports d'agents courts (≤ 15–25 lignes), sans copie de fichiers.

---

## 2. État de départ (fait)

| Étape | Résultat |
|---|---|
| 0 — Dépôt minimal | package, CLI, tests, CI hors réseau, `CLAUDE.md`, docs |
| 1 — Choix du catalogue | *Ancient Terracottas* (Getty/Quire, CC BY 4.0) ; fiche `docs/sources/terracottas-rights.md` |
| 2 — Tranche verticale | `lesternowak slice getty-terracottas` : 48 paragraphes, 122 liens `machine_proposed` (cats. 1–4), offsets vérifiés, droits par action, `validate` append-only, `inspect.html` |

Limite connue : la règle actuelle (B0) relie chaque paragraphe d'une discussion de groupe à toutes
les œuvres du groupe. C'est la baseline à battre.

---

## 3. Jalons et lots

Légende : **H** = point de contrôle humain ; *agent* = modèle conseillé pour l'exécution.

### Jalon J1 — Référence humaine et banc de mesure

But : rendre la qualité mesurable. Rien d'autre n'est amélioré tant que J1 n'est pas terminé.

**L1.1 — Guide d'annotation** (*orchestrateur*)
- Sortie : `docs/annotation-guide.md` : question posée par paragraphe, valeurs permises,
  cas limites, exemples tirés des cats. 1–4.
- Étiquettes par (paragraphe, œuvre candidate) : `about` (le paragraphe analyse cette œuvre),
  `mentions` (citée sans analyse), `group` (porte sur le groupe sans viser cette œuvre),
  `not_about`, `unsure`.
- Étiquette par paragraphe — fonction (liste unique, 6 valeurs) : `visual_description`,
  `technical_material`, `iconography_interpretation`, `attribution_dating`,
  `provenance_context`, `other`.
- Sortie : un ADR remplaçant `PassageRole` par cette liste.
- Critère : relu et accepté par le porteur (**H1a**).

**L1.2 — Feuille d'annotation** (*Sonnet*)
- `lesternowak annotation-sheet` → CSV (ou HTML formulaire local) : un rang par
  (paragraphe, œuvre candidate), texte du paragraphe, lien vers la page source, colonnes vides.
- `lesternowak annotation-import` → `AnnotationEvent` + `gold/<corpus>/<version>.jsonl`
  (identifiants de spans + étiquettes ; texte non dupliqué).
- Critères : aller-retour CSV → gold testé ; import refusé si colonnes invalides ; aucun texte
  inventé possible (le texte vient des spans).

**H1b — Annotation de référence par le porteur** (~1 h 30)
- Corpus dev : cats. 1–4, soit 48 paragraphes, environ 120 couples. Le porteur annote en lisant
  le catalogue en ligne.
- Une semaine plus tard ou plus : ré-annotation à l'aveugle de 20 couples tirés au hasard
  (accord intra-annotateur).

**L1.3 — Banc d'évaluation** (*Sonnet*)
- `lesternowak eval --gold … --pred …` → `metrics.json` + rapport Markdown : précision, rappel,
  F1, couverture/abstention, intervalles de Wilson, matrice de confusion des fonctions, liste
  des erreurs avec liens vers l'inspection.
- Mesure de **B0** (règle structurelle actuelle) sur le gold dev.
- Gold dev committé (CC BY, identifiants + étiquettes) et test CI de non-régression.
- Critère : chiffres B0 publiés dans `docs/reports/J1-baseline.md`.

### Jalon J2 — Rattachement par mentions (règles + TAL)

But : relier chaque paragraphe à la bonne œuvre plutôt qu'au groupe entier.

**L2.1 — Lexique d'alias** (*Haiku pour l'extraction, porteur pour la relecture*)
- Alias issus des données éditeur (titres, groupes, numéros de catalogue et d'inventaire) et des
  titres de sections. Exemple : « Statue of a Siren » → *siren*, *sirens*.
- Sortie : `config/aliases/terracottas.yaml` versionné, relu par le porteur (**H2a**, ~15 min).

**L2.2 — Détection de mentions** (*Sonnet*)
- Expressions régulières : `cat. n`, `cats. n–m`, `fig. n`, numéros d'inventaire.
- spaCy (`en_core_web_sm`, version épinglée) : segmentation en phrases, groupes nominaux,
  `PhraseMatcher` sur le lexique d'alias.
- Chaque mention = span vérifié (offsets) + alias reconnu + œuvre(s) visée(s).
- Critère : tests unitaires sur des phrases réelles des cats. 1–4 ; rappel des mentions mesuré
  sur 30 paragraphes annotés (**H2b**, ~20 min : marquer les mentions manquées).

**L2.3 — Règles de rattachement et ablation** (*Sonnet ; revue par relecteur*)
- **B1** : mentions explicites (numéros, titres) → lien `about`/`mentions` vers l'œuvre visée.
- **B2** : B1 + alias génériques (*the seated figure*, *the sirens*) + continuité avec le
  paragraphe précédent (preuve plus faible, marquée E3) ; aucun référent → `unresolved`.
- Chaque lien porte ses signaux séparés (E0/E1/E2/E3) ; le rang n'est pas une probabilité.
- Critère : rapport d'ablation B0/B1/B2 sur le gold dev. Cible indicative : précision ≥ 0,90
  avec borne basse de Wilson et taux d'abstention rapportés.
- **Stop** : si B2 ne bat pas B0 en précision à couverture comparable, analyser les erreurs
  avant toute autre méthode.

### Jalon J3 — Fonction du passage

**L3.1 — Baseline lexicale** (*Sonnet*)
- Marqueurs lexicaux (« attributed to », « dated », « provenance », « pigment », « composition »…)
  + petit classifieur scikit-learn, entraîné et évalué en validation croisée *par œuvre* sur
  le gold dev.
- Critère : F1 par classe et matrice de confusion publiés ; la plus fréquente des classes sert de
  baseline triviale.

**L3.2 — Comparateur LLM (optionnel)** (*Sonnet pour le code*)
- Uniquement si L3.1 est insuffisant sur au moins une classe utile.
- Liste d'étiquettes fermée, sortie JSON sous schéma, justification par citation vérifiée
  automatiquement ; statut `model_suggested` ; droits `remote_llm` vérifiés avant envoi.
- Coût et latence mesurés ; gardé seulement s'il gagne à l'ablation (ADR 0001).

### Jalon J4 — Généralisation sur document tenu à l'écart

**L4.1 — Généraliser le lecteur Quire** (*Sonnet*)
- `getty_quire.py` paramétré par configuration de publication (URL, fichier de données,
  sections analytiques) au lieu d'un code propre à Terracottas.
- Ajout de *Roman Mosaics* sans réglage des règles : seulement la configuration.
- Critère : tests de contrat communs aux deux publications ; fiche de droits Roman Mosaics
  (exclusions de figures consignées) produite par *Haiku* et relue.

**L4.2 — Gel et annotation à l'aveugle**
- Tag Git `rules-frozen-J4` avant tout regard sur les sorties Roman Mosaics.
- Échantillon de ~60 couples tiré par script (graine fixée, stratifié par section).
- **H4** : le porteur annote sans voir les prédictions (~1 h).

**L4.3 — Évaluation tenue à l'écart** (*Sonnet ; rapport rédigé par Haiku depuis metrics.json,
relu par l'orchestrateur*)
- Précision, abstention, faux liens ; comparaison au dev ; analyse d'erreurs.
- Sortie : `docs/reports/J4-heldout-romanmosaics.md`.
- **Décision (H4b)** : poursuivre, corriger la conception, ou restreindre le périmètre.

### Jalon J5 — Deuxième nature de source (PDF, puis hors structure)

**L5.1 — Benchmark d'extraction PDF à vérité automatique** (*Sonnet*)
- Le PDF de *Terracottas* a le même contenu que le HTML natif : le HTML sert de vérité terrain
  automatique pour le texte, l'ordre de lecture, les notes et les appels de figures.
- Adaptateurs Xberg et Docling (versions épinglées, configurations consignées, ADR).
- Mesures : CER sur paragraphes, conservation des notes et numéros, ordre, appels de figure,
  secondes/page, mémoire.
- Critère : `docs/reports/J5-extraction-benchmark.md` et choix du moteur *par type de document*.

**L5.2 — Rattachement depuis PDF**
- Le pipeline J2 exécuté sur l'extraction PDF de Terracottas, comparé au résultat natif sur le
  même gold : mesure de la perte due à l'extraction.

**L5.3 — Hors structure de catalogue : *Mummy Portraits*** (essais)
- Pas de fiche par objet : le rattachement repose sur les mentions (J2) et les appels de figures.
- **H5** : annotation à l'aveugle d'environ 60 couples ; rapport tenu à l'écart.
- Champ `text_fidelity` étendu dès l'arrivée d'OCR.

### Jalon J6 — Dataset v0.1

**L6.1 — Exports filtrés par droits** (*Sonnet*)
- Export standoff (identifiants, offsets, URI) par défaut ; export avec texte seulement si la
  décision de droits de l'action correspondante est `allow` ; JSONL + Parquet.
- Tests : une action `unknown` ou `deny` bloque l'export du contenu concerné.

**L6.2 — Dataset card et publication** (*Haiku pour le gabarit, orchestrateur pour la relecture*)
- Sélection, exclusions, biais (antiquités, anglais, Getty), métriques J2–J5, accord
  intra-annotateur, droits, versions du pipeline.
- **H6** : relecture du porteur avant toute publication.

### Après J6 (conditionnel, selon les métriques)

Sources patrimoniales ALTO/IIIF (Gallica, Heidelberg) ; MetPublications ; interface de revue plus
riche ; assertions historiographiques ; graphes/RDF. Chacun ouvert par un ADR qui justifie la
valeur attendue avec des chiffres.

---

## 4. Points de contrôle humains (récapitulatif)

| Point | Objet | Charge estimée |
|---|---|---|
| H1a | accepter le guide d'annotation | 15 min |
| H1b | annoter le gold dev (≈120 couples) + ré-annotation différée (20) | 1 h 30 + 15 min |
| H2a | relire le lexique d'alias | 15 min |
| H2b | marquer les mentions manquées (30 paragraphes) | 20 min |
| H4 | annotation à l'aveugle Roman Mosaics (~60 couples) | 1 h |
| H4b | décision de poursuite | 15 min |
| H5 | annotation à l'aveugle Mummy Portraits (~60 couples) | 1 h |
| H6 | relecture de la dataset card | 30 min |

---

## 5. Gabarits

### 5.1 Brief d'agent

```
Contexte : dépôt, branche, fichiers à lire (CLAUDE.md toujours), ce qui est déjà établi.
Objectif : une phrase.
À faire : étapes numérotées, fichiers concernés.
Interdits : ce qui ne doit pas être touché ou ajouté.
Critères de sortie : commandes exactes + résultats attendus.
Commit/push : message en français, lignes d'attribution, branche.
Rapport : ≤ 15–25 lignes ; chiffres, échantillon vérifiable, ce qui n'a pas marché.
```

### 5.2 Rapport de fin de lot

```
Fichiers modifiés · commandes exécutées et résultats · réel vs fixture · métriques ·
limites · décisions (ADR) · prochain lot.
Trois vérifications :
1. progrès observable vers le dataset œuvre↔analyse ?
2. puis-je ouvrir la source d'un exemple et vérifier passage, œuvre, lien ?
3. preuve directe / suggestion de modèle / non résolu / interdiction d'usage distingués ?
```

---

## 6. Risques et critères d'arrêt

| Risque | Signal | Réponse |
|---|---|---|
| Règles sur-ajustées à Terracottas | écart dev → tenu à l'écart > 15 points de précision | analyse d'erreurs, simplification, nouvel échantillon gelé |
| Annotation par une seule personne | accord intra-annotateur < 0,8 | revoir le guide avant toute mesure |
| Fonction du passage mal définie | F1 baseline < 0,5 sur les classes utiles | fusionner des classes plutôt qu'ajouter un modèle |
| Dépendance à la structure Quire | effondrement sur Mummy Portraits | assumer le périmètre « catalogues structurés » (cadrage §59.10) |
| Dérive des sources en ligne | changement d'empreinte des pages en cache | nouvelle capture datée, pas d'écrasement |
| Coût LLM | coût par lien validé non justifié | rester sans LLM |
