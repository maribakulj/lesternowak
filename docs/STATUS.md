# État courant

Mis à jour à chaque fin de lot. Une nouvelle session commence par lire `CLAUDE.md`, ce fichier
et `docs/PLAN.md`.

- **Lot C3–C5 (2026-11-17)** : pipeline générique volume -> slice (`lesternowak build --catalogue
  config/catalogues/<id>.yaml --out data/slices/<id>/`, client `gallica.py`, `alto.py`,
  `catalogue.py`), exécuté sur les 5 volumes de développement Gallica (120 pages ALTO max chacun, liens
  E1 `machine_proposed`, aucune résolution externe : `unresolved` partout). File de revue combinée
  `data/review/queue-c5.jsonl` (Terracottas + Gallica). Ribes-Christofle 1928 exclu (experts nommés sans
  dates : `excluded_reason`, `build` refuse avant tout téléchargement) ; trous de numérotation
  signalés (`segmentation_uncertain`, liens `unresolved`). Quotas : `docs/sources/inventory/gallica-probe.md`.
- **Dernier lot terminé avant C3–C5** : L1.2 + L1.3 (feuille d'annotation, import gold, banc d'évaluation,
  accord) ; B0 non mesuré faute de gold réel (H1b).
- **Prochain lot** : H1b (annotation par le porteur de `data/annotation/sheet-dev-v1.csv`),
  puis mesure de B0.
- **En attente du porteur** : H1a (relire `docs/annotation-guide.md`) puis H1b (annoter la
  feuille). Revue indépendante de J1 faite, 5 défauts corrigés (c896274).
- **Corpus dev** : *Ancient Terracottas*, cats. 1–4 (48 paragraphes, 122 liens
  `machine_proposed`, aucun validé).
- **Tenus à l'écart (ne pas regarder)** : *Roman Mosaics* (J4), *Mummy Portraits* (J5).
- **Commandes** : `uv run lesternowak slice getty-terracottas --entries 1 2 3 4` ;
  `uv run pytest -m "not live"`.
- **Plan corpus élargi** : `docs/PLAN_CORPUS.md` (lots C0–C7, avant J2) ; décisions du
  porteur consignées (§8 : labo BnF, non commercial, EN/FR, datasets d'entraînement, exclusion de
  tout texte sous droits) ; 5 h/semaine de vérification, accès Gallica
  via `openapi.bnf.fr` (quotas §2.3), dépôt = logiciel générique (§0) ; prochain lot : C0.
