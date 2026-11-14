# État courant

Mis à jour à chaque fin de lot. Une nouvelle session commence par lire `CLAUDE.md`, ce fichier
et `docs/PLAN.md`.

- **Dernier lot terminé** : L1.2 + L1.3 (feuille d'annotation, import gold, banc d'évaluation,
  accord) ; B0 non mesuré faute de gold réel (H1b).
- **Prochain lot** : H1b (annotation par le porteur de `data/annotation/sheet-dev-v1.csv`),
  puis mesure de B0.
- **En attente du porteur** : rien pour le moment ; H1a après L1.1.
- **Corpus dev** : *Ancient Terracottas*, cats. 1–4 (48 paragraphes, 122 liens
  `machine_proposed`, aucun validé).
- **Tenus à l'écart (ne pas regarder)** : *Roman Mosaics* (J4), *Mummy Portraits* (J5).
- **Commandes** : `uv run lesternowak slice getty-terracottas --entries 1 2 3 4` ;
  `uv run pytest -m "not live"`.
