# Getty — catalogues en ligne (Quire) candidats pour la tranche verticale

Vérifié le **2026-11-12** par consultation des pages publiques (pages `about/`, `copyright/`,
page de catalogue et fichiers de données). Aucun fichier n'est versionné dans ce dépôt.
Ceci n'est pas un avis juridique ; les décisions de droits par action seront consignées à
l'étape 1.

## Candidat recommandé : *Ancient Terracottas from South Italy and Sicily in the J. Paul Getty Museum*

- Auteure : Maria Lucia Ferruzza. Éditeur : J. Paul Getty Museum, 2016.
- URL : https://www.getty.edu/publications/terracottas/
- Licence déclarée (page `about/`, section Copyright) : « Copyright © 2016 J. Paul Getty Trust.
  Except where otherwise noted, this work is licensed under a Creative Commons Attribution 4.0
  International License. » Aucune liste d'exclusion de figures relevée sur cette page (seules les
  tuiles de carte sont attribuées à l'Ancient World Mapping Center). Les crédits par légende
  restent à contrôler figure par figure avant tout usage d'image (« except where otherwise noted »).
- Formats observés : HTML par entrée (`catalogue/<n>/`), PDF (~18,9 Mo), EPUB, MOBI, données
  `AncientTerracottas_Ferruzza_Data.json` / `.csv` (et version `Extended`), archive d'images.
- Données structurées : 60 objets. Champs observés : `Catalogue/Guide Number` (« cat. 1 »),
  `DOR ID` (13144), `Inventory Number` (« 76.AD.11.1 »), `Title`, `Group`, `Date`, `Medium`,
  liens TGN/AAT/Pleiades, `Collection Page URL` (https://www.getty.edu/art/collection/objects/13144).
- Structure d'une entrée (cat. 1) : métadonnées, Fabric, Condition, Provenance, Bibliography,
  **Description**, **Discussion**.
- Intérêt :
  - liste fermée de candidats et identifiants d'œuvre stables fournis par l'éditeur ;
  - texte né numérique (pas d'OCR) ;
  - passages réellement analytiques (description formelle, technique, interprétation) ;
  - cas difficile réel : la discussion « Group of a Seated Poet (Orpheus?) and Sirens (cats. 1–3) »
    est « reproduced on each of the individual object pages » → un passage, plusieurs œuvres ;
  - le PDF du même ouvrage permet plus tard de comparer extraction native et PDF à contenu égal.
- Limites : antiquités (pas de peinture), une seule langue (anglais), structure très régulière —
  cas facile pour le rattachement, qui démontre la chaîne mais pas la difficulté scientifique.

## Autres candidats vérifiés

### *Roman Mosaics in the J. Paul Getty Museum* (Alexis Belis, 2016)
- https://www.getty.edu/publications/romanmosaics/ — licence déclarée CC BY 4.0 (page `about/`),
  avec exclusions explicites : figs. 2–5, 8, 10, 11, 15, 16, 17, 19, 20 (droits réservés).
- PDF, EPUB, données JSON/CSV (21 objets, mêmes champs que ci-dessus), archive d'images.
- Entrée : section **Commentary**, Provenance, Bibliography. Riche en iconographie.
- Bon candidat de **document tenu à l'écart** pour l'étape 3 (même famille éditoriale : à
  traiter comme test « même structure », pas comme test de généralisation).

### *Ancient Lamps in the J. Paul Getty Museum* (Jean Bussière, Birgitta Lindros Wohl, 2017)
- https://www.getty.edu/publications/ancientlamps/ — licence déclarée CC BY 4.0 (page `about/`).
- PDF, EPUB, données JSON/CSV, archive d'images. Environ 630 lampes : beaucoup d'entrées courtes,
  utile comme **cas contrastif** (notices pauvres, mentions sans analyse).

### *Mummy Portraits of Roman Egypt* (dir. Marie Svoboda, Caroline R. Cartwright, 2020)
- https://www.getty.edu/publications/mummyportraits/
- Page `copyright/` : « The text of this work and figs. 4.2–3, 4.10, 4.13, 8.3–4, 11.2–5, and 17.4a
  are licensed under a Creative Commons Attribution 4.0 International License. All other images
  are … expressly excluded from the CC BY license ».
- Actes de colloque (essais) : le référent est distribué dans le discours, sans notice par objet.
  Candidat pour tester le rattachement **hors structure de catalogue**. Images majoritairement
  exclues : export texte/références seulement.

### *Ancient Carved Ambers in the J. Paul Getty Museum* (Faya Causey, 2012, rév. 2019)
- https://www.getty.edu/publications/ambers/
- Page `copyright/` : CC BY 4.0 sauf figures 3, 9–17, 22–24, 28, 32, 33, 36, 38, 40, 51 et 54,
  exclues. Exemple concret de droits différents pour le texte et pour certaines images.

## Points à trancher à l'étape 1

- Choix du catalogue de la tranche (recommandation : Terracottas) et du document tenu à l'écart.
- Droits des images d'objets : licence de la publication vs conditions Getty Open Content de la
  page collection — à consigner séparément.
- Envoi du texte à un LLM distant : compatible avec CC BY (attribution conservée), à consigner
  comme action distincte.
