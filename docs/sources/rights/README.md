# Droits : domaine public par auteur (lot C1)

Date : 2026-11-17. Fichier de données : `authors.yaml`.

**Règle appliquée** : pd = yes si décès ≤ 1955 (70 ans révolus au 1er janvier 2026) ; pd = no si
décès ≥ 1956 ; pd = unknown si date introuvable ou identité incertaine. Une personne morale
(musée, collectivité) n'a pas de date de décès : pd = unknown, règle à trancher par le porteur.

**Sources** : Wikidata (P570 et description ; api `wbsearchentities` puis `wbgetentities`).
IdRef a été injoignable (connexion réinitialisée) : aucune date ne vient d'IdRef ni de VIAF. Wikidata
a répondu 429 à plusieurs requêtes ; deux noms restent à relancer (Collet, et P570 de Benoît).

**Résultat** (16 noms de `authors_for_pd_check`, gallica.yaml et met-getty.yaml) :
- yes : 5 (Villot, Durrieu, Benoît, Demonts, Burroughs)
- no : 0
- unknown : 11 (5 personnes : Huteau, Collet, Biais, Berthomieu, Masson ; 6 personnes morales)

**Décisions consignées dans `docs/sources/inventory/met-getty.yaml`** : Conserving Canvas et Rococo
(CC BY-NC) incluses avec `license_flags: [NC]`, décision du porteur ; deux volumes Met (1922, 1926)
en `pd_status: yes` ; les autres volumes Met restent exclus, avec `pd_blocking_author`.

Limites : Biais, Berthomieu et Huteau ont un candidat Wikidata qui ne concorde pas (dates ou
profession) ; Demonts et Benoît n'ont qu'un candidat concordant, rattachement au Louvre non vérifié.
Ce fichier n'est pas un avis juridique.
