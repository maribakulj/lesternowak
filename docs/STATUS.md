# État courant

Mis à jour à chaque fin de lot. Une nouvelle session commence par lire `CLAUDE.md`, ce fichier
et `docs/PLAN.md`.

- **Dernier lot terminé** : étape 2, tranche verticale (paragraphes, exclusion des tableaux,
  marqueurs de note).
- **Prochain lot** : L1.1, guide d'annotation (J1).
- **En attente du porteur** : rien pour le moment ; H1a après L1.1.
- **Corpus dev** : *Ancient Terracottas*, cats. 1–4 (48 paragraphes, 122 liens
  `machine_proposed`, aucun validé).
- **Tenus à l'écart (ne pas regarder)** : *Roman Mosaics* (J4), *Mummy Portraits* (J5).
- **Commandes** : `uv run lesternowak slice getty-terracottas --entries 1 2 3 4` ;
  `uv run pytest -m "not live"`.
