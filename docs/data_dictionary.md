# Dictionnaire des variables

> Construit à partir du dictionnaire officiel (`Dictionnaire_variables.pdf`, ressource pédagogique non
> redistribuée) et d'une **inspection structurelle** du fichier réalisée à l'initialisation du projet.
>
> - Les colonnes *Description*, *Domaine attendu* et *Unité* reprennent le dictionnaire officiel.
> - La colonne *Type lu* indique le type attribué par `pandas` 3.0.1 à la lecture du CSV : c'est un
>   **constat**, pas un diagnostic. Un écart entre le type lu et le type métier est un point à
>   expliquer pendant l'audit (mission 1).
> - Le *Type métier* et le *Rôle potentiel* sont des **propositions** à confirmer pendant l'audit.
> - Aucune décision de conservation ou de suppression n'est prise ici.

## Fichier source

| Élément | Valeur |
|---|---|
| Fichier | `parcours_etudiants.csv` |
| Format | CSV, séparateur virgule, décimales représentées « normalement » par un point |
| Encodage | UTF-8 avec BOM |
| Dimensions constatées | 4 504 lignes × 33 colonnes (en-tête exclu) |
| Contexte de prédiction | Informations disponibles à l'inscription et jusqu'à la fin du semestre 2 |

## 1. Identification et inscription

| Variable | Description | Type métier (proposé) | Domaine attendu | Unité | Type lu | Rôle potentiel | Points de vigilance |
|---|---|---|---|---|---|---|---|
| `id_etudiant` | Identifiant administratif fictif attribué à un étudiant | Identifiant | Unique par étudiant (à vérifier) | — | `str` | **Identifiant** — exclu des variables explicatives | Doublons et identifiants répétés à rechercher ; base des contrôles de non-chevauchement |
| `mode_admission` | Voie d'admission | Qualitative nominale | Candidature générale, transfert, dispositifs particuliers, etc. (liste non exhaustive) | — | `str` | Explicative candidate | Modalités rares ou orthographes variables possibles |
| `rang_voeu` | Ordre de préférence de la candidature | Qualitative ordinale | De « Rang 0 » à « Rang 9 », du plus au moins prioritaire selon la convention de la source | — | `str` | Explicative candidate | Format des valeurs à vérifier ; encodage ordinal à discuter |
| `filiere` | Formation suivie par l'étudiant | Qualitative nominale | Non précisé | — | `str` | Explicative candidate | Nombre de modalités à mesurer |
| `regime_cours` | Horaire des enseignements | Qualitative binaire | Jour, Soir | — | `str` | Explicative candidate | Modalités hors domaine à rechercher |
| `diplome_anterieur` | Type de formation ou de qualification antérieure | Qualitative nominale | Non précisé | — | `str` | Explicative candidate | Parcours généraux, techniques et universitaires pas tous directement comparables (dictionnaire) |
| `note_diplome_anterieur` | Note de la qualification antérieure | Quantitative continue | Sur 200 | points / 200 | `str` | Explicative candidate | Lue comme texte alors qu'attendue numérique : cause à identifier |
| `note_admission` | Note utilisée lors de l'admission | Quantitative continue | Sur 200 | points / 200 | `str` | Explicative candidate | Lue comme texte alors qu'attendue numérique ; redondance possible avec `note_admission_archive` |
| `note_admission_archive` | Note d'admission figurant dans un second export (simulé pour l'exercice) | Quantitative continue | Sur 200 | points / 200 | `float64` | À évaluer | Second export de la même information : redondance et cohérence avec `note_admission` à étudier |
| `niveau_dossier` | Appréciation du dossier dérivée de la note antérieure | Qualitative ordinale | Fragile, Moyen, Bon, Très bon | — | `str` | À évaluer | Dérivée de `note_diplome_anterieur` (dictionnaire) : redondance |
| `dette_inscription` | Dette déclarée lors de l'inscription | Qualitative binaire | Oui, Non | — | `str` | Explicative candidate | Variable socio-économique sensible (éthique) |
| `frais_scolarite_a_jour` | Frais de scolarité à jour | Qualitative binaire | Oui, Non | — | `str` | Explicative candidate | Variable socio-économique sensible (éthique) |
| `boursier` | Bénéficie d'une bourse | Qualitative binaire | Oui, Non | — | `str` | Explicative candidate | Variable socio-économique sensible (éthique) |
| `age_inscription` | Âge à l'inscription | Quantitative discrète | Années révolues | années | `str` | Explicative candidate | Lue comme texte alors qu'attendue numérique : cause à identifier |
| `age_inscription_mois` | Âge à l'inscription en mois, simulé à partir de l'âge en années | Quantitative | — | mois | `float64` | À évaluer | Simulée à partir de `age_inscription` (dictionnaire) : redondance, cohérence à vérifier |

## 2. Contexte économique

| Variable | Description | Type métier (proposé) | Domaine attendu | Unité | Type lu | Rôle potentiel | Points de vigilance |
|---|---|---|---|---|---|---|---|
| `taux_chomage` | Taux de chômage | Quantitative continue | Non précisé | % | `float64` | Explicative candidate | Indicateur de contexte, probablement commun à de nombreux étudiants (à vérifier) |
| `taux_inflation` | Taux d'inflation | Quantitative continue | Peut être négatif | % | `float64` | Explicative candidate | Une valeur négative n'est pas automatiquement une anomalie (dictionnaire) |
| `indicateur_pib` | Indicateur économique de PIB tel que fourni par la source | Quantitative continue | Peut être négatif | Non précisée | `float64` | Explicative candidate | Unité non documentée ; valeur négative légitime possible (dictionnaire) |

## 3. Résultats des deux semestres

Suffixes `_s1` / `_s2` : premier / deuxième semestre. UE = unité d'enseignement. Les nombres d'UE et
d'évaluations sont des **entiers non négatifs** ; les relations entre variables doivent être examinées
(dictionnaire).

| Variable | Description | Type métier (proposé) | Domaine attendu | Unité | Type lu | Rôle potentiel | Points de vigilance |
|---|---|---|---|---|---|---|---|
| `ue_creditees_s1` | Nombre d'UE créditées (S1) | Quantitative discrète | Entier ≥ 0 | UE | `int64` | Explicative candidate | Cohérence avec les UE inscrites |
| `ue_inscrites_s1` | Nombre d'UE auxquelles l'étudiant est inscrit (S1) | Quantitative discrète | Entier ≥ 0 | UE | `float64` | Explicative candidate | Lue en flottant alors qu'attendue entière : valeurs manquantes ou non entières à rechercher |
| `nb_evaluations_s1` | Nombre d'évaluations effectuées (S1) | Quantitative discrète | Entier ≥ 0 | évaluations | `float64` | Explicative candidate | Lue en flottant : idem ; plusieurs évaluations possibles par UE |
| `ue_validees_s1` | Nombre d'UE validées (S1) | Quantitative discrète | Entier ≥ 0 | UE | `int64` | Explicative candidate | Cohérence avec les UE inscrites |
| `note_moyenne_s1` | Note moyenne du semestre (S1) | Quantitative continue | Sur 20 | points / 20 | `str` | Explicative candidate | Lue comme texte : cause à identifier ; une valeur nulle peut être légitime (aucune UE validée) |
| `ue_sans_evaluation_s1` | Nombre d'UE sans évaluation (S1) | Quantitative discrète | Entier ≥ 0 | UE | `int64` | Explicative candidate | Cohérence avec les UE inscrites |
| `ue_creditees_s2` | Nombre d'UE créditées (S2) | Quantitative discrète | Entier ≥ 0 | UE | `int64` | Explicative candidate | Cohérence avec les UE inscrites |
| `ue_inscrites_s2` | Nombre d'UE auxquelles l'étudiant est inscrit (S2) | Quantitative discrète | Entier ≥ 0 | UE | `int64` | Explicative candidate | — |
| `nb_evaluations_s2` | Nombre d'évaluations effectuées (S2) | Quantitative discrète | Entier ≥ 0 | évaluations | `int64` | Explicative candidate | — |
| `ue_validees_s2` | Nombre d'UE validées (S2) | Quantitative discrète | Entier ≥ 0 | UE | `float64` | Explicative candidate | Lue en flottant alors qu'attendue entière : valeurs manquantes ou non entières à rechercher |
| `note_moyenne_s2` | Note moyenne du semestre (S2) | Quantitative continue | Sur 20 | points / 20 | `str` | Explicative candidate | Lue comme texte : cause à identifier ; une valeur nulle peut être légitime |
| `ue_sans_evaluation_s2` | Nombre d'UE sans évaluation (S2) | Quantitative discrète | Entier ≥ 0 | UE | `int64` | Explicative candidate | Cohérence avec les UE inscrites |

## 4. Métadonnées et cible

| Variable | Description | Type métier (proposé) | Domaine attendu | Unité | Type lu | Rôle potentiel | Points de vigilance |
|---|---|---|---|---|---|---|---|
| `version_export` | Version du système d'export (métadonnée simulée) | Qualitative nominale | Non précisé | — | `str` | **Métadonnée** — pertinence à évaluer | Information technique sans sens métier : risque de corrélation artificielle avec la cible |
| `code_campagne` | Code administratif d'export simulé ; ce n'est pas l'année réelle de collecte | Code (qualitatif) | Non précisé | — | `int64` | **Métadonnée** — pertinence à évaluer | Lu comme entier mais ne doit pas être traité comme une grandeur numérique ni comme une année |
| `statut_academique` | Statut observé à l'échéance normale de la formation | Qualitative nominale (3 classes) | Abandon, En cours, Diplômé | — | `str` | **Cible** | « En cours » = encore inscrit à l'échéance normale ; modalités réelles et déséquilibre à vérifier |

## Relations à examiner (suggérées par le dictionnaire)

- `note_admission` ↔ `note_admission_archive` : même information issue de deux exports.
- `age_inscription` ↔ `age_inscription_mois` : la seconde est simulée à partir de la première.
- `note_diplome_anterieur` ↔ `niveau_dossier` : la seconde est dérivée de la première.
- UE inscrites, créditées, validées, sans évaluation et nombre d'évaluations, pour chaque semestre.

## Constats de l'audit automatique (mission 1)

> Établis par `python -m src.data_quality` sur le fichier reçu (SHA-256 `707360BC…DFC2`). Détail :
> [`reports/audit_qualite.md`](../reports/audit_qualite.md) ; règles :
> [`audit_rules_catalog.md`](audit_rules_catalog.md). Aucune décision de traitement n'est prise ici.

| Variable(s) | Cause de l'écart entre type lu et type métier, ou constat principal |
|---|---|
| `note_admission`, `note_diplome_anterieur`, `note_moyenne_s1` | Lues comme texte : virgules décimales (`120,0`) et/ou marqueurs `ND`, `?`, `Non renseigné` ; valeurs hors échelle (ex. 450, 999, −15, 25, 99) |
| `note_moyenne_s2`, `age_inscription` | Lues comme texte : marqueurs `ND`, `?`, `Non renseigné` ; âges impossibles (−3, 0, 145, 220) |
| `ue_inscrites_s1`, `nb_evaluations_s1`, `ue_validees_s2`, `age_inscription_mois` | Lues en flottant à cause de champs vides ; `nb_evaluations_s1` et `ue_inscrites_s2` contiennent des valeurs négatives et le code 999 |
| Variables qualitatives et binaires | Variantes de casse, d'espaces et d'accents ; `YES` / `NO` dans les binaires ; valeurs déguisées `ND`, `?`, `Non renseigné` |
| `id_etudiant` | 80 identifiants présents deux fois, tous en doublons exacts de ligne |
| `version_export`, `code_campagne` | Constantes (`V1`, `2026`) |
| `age_inscription_mois`, `niveau_dossier`, `note_admission_archive` | Redondances confirmées (dérivation exacte / corrélation 0,996 avec `note_admission`) |
| `filiere` → `regime_cours` ; `taux_chomage` ↔ `indicateur_pib` → `taux_inflation` | Dépendances déterministes constatées |

