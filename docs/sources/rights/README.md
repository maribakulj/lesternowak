# Droits : domaine public par auteur et par volume (lot C1)

Date : 2026-11-17 (deux passes). Fichier de données : `authors.yaml` ; statuts finaux par volume dans
`../inventory/gallica.yaml` et `../inventory/met-getty.yaml` (champs `pd_status`, `pd_basis`, et
`articles[].pd` pour les fascicules). Ce n'est pas un avis juridique.

## Règles appliquées

1. **Œuvre d'auteurs nommés** : règle par décès. `pd = yes` si décès ≤ 1955 (70 ans révolus au
   1er janvier 2026) ; `no` si décès ≥ 1956 ; `unknown` si date introuvable ou identité incertaine.
   Un auteur nommé à date inconnue **bloque le volume** (ou l'article) : `unknown` donc exclu.
2. **Règle complémentaire (décision de l'orchestrateur, 2026-11-17)** : œuvre **anonyme ou
   collective** (auteur personne morale, musée, « catalogue » sans auteur nommé) : domaine public
   si publiée **au plus tard en 1955** (CPI L123-3 : 70 ans après la publication). Pour les
   personnes morales, `authors.yaml` porte `pd: by_publication_year` et le statut est apprécié volume
   par volume. Pour un volume sans auteur nommé dans les métadonnées (Besançon, Abbeville, Bordeaux,
   catalogues de vente Luminais et Ribes-Christofle), la page de titre reste à contrôler en C3 :
   un auteur ou un expert nommé sans date fait basculer le volume en `unknown`.
3. **Licences ouvertes** (Quire) : `pd_status: yes` avec `pd_basis` « licence CC BY » ou
   « CC BY-NC [NC] ». Les images tierces ne sont pas couvertes par ces statuts.
4. **Fascicules de périodiques** : statut **par article** (`articles[].pd`). `pd_status: partial` si
   certains articles seulement sont `yes` ; seuls ces articles seront traités.

## Sources et limites

- Wikidata (P570, description ; `wbsearchentities`, `wbgetentities`), puis les dates figurant dans la
  notice BnF du volume (marquées `identity_confidence: medium`, « notice BnF seule » quand elles ne
  sont pas recoupées). IdRef et VIAF n'ont pas été joignables.
- Passe 1 : 16 noms. Passe 2 : Wikidata a répondu 429 deux fois (requêtes à 2 s d'intervalle,
  User-Agent générique) ; **arrêt des requêtes** conformément à la consigne. Les auteurs d'articles
  des fascicules (42 noms) et les experts des catalogues de vente (Georges Petit, Haro) n'ont donc
  pas de date : `unknown`, sauf Paul Durrieu (passe 1). À relancer plus tard par petits lots.
- Décisions à confirmer par l'orchestrateur : Biais, Berthomieu et Masson passent à `yes` sur la
  date de la notice BnF (décès 1932, 1928, 1931), identité `medium` ; Benoît reste `medium`.
- Les volumes Met 1905 et 1905-1911 passent à `yes` par la règle collective (publiés avant 1956) ;
  George H. Story, cité par une notice non consultée, est à vérifier.
