# Rapport d'audit de qualité des données

> Rapport généré automatiquement le 2026-11-26 à 17:32 par `src/data_quality` à partir des résultats réels de l'audit. Il ne contient aucun identifiant étudiant : le détail par observation est dans `outputs/audit/anomalies_detail.csv` (non versionné). L'audit **ne modifie aucune donnée**.

## 1. Présentation du jeu de données

| Élément | Valeur |
|---|---|
| Fichier | parcours_etudiants.csv |
| Empreinte SHA-256 | `707360BCC39CE4F85FD36CC4516B8601B3322E3CCAB62D0E690F3FBC5F0DDFC2` |
| Observations | 4 504 |
| Colonnes | 33 |
| Variable cible | `statut_academique` |
| Contrôles exécutés | structure, missing_values, duplicates, formats, business_rules, consistency, statistical, multivariate, redundancy, leakage, class_balance |

Rôles des variables (dictionnaire officiel) :

| rôle | variables |
|---|---|
| quantitative_discrete | 12 |
| quantitative_continue | 8 |
| binaire | 4 |
| qualitative_nominale | 3 |
| qualitative_ordinale | 2 |
| metadonnee | 2 |
| identifiant | 1 |
| cible | 1 |

La prédiction porte sur le statut observé à l'échéance normale de la formation, à partir des informations disponibles **jusqu'à la fin du semestre 2**.

## 2. Résumé exécutif

- **3 716 signalements** au total, dont 3 665 portant sur une observation et 51 globaux (variables, jeu de données).
- **2 216 observations distinctes** concernées (49,2 %), dont **1 984** (44,0 %) par au moins un signalement de gravité supérieure à INFO, et **296** par un signalement CRITICAL ou HIGH.
- Un nombre de signalements n'est pas un nombre d'observations : une observation peut cumuler plusieurs anomalies.

Problèmes prioritaires (gravité CRITICAL / HIGH) :

- **Valeur hors des bornes du dictionnaire** (`DOM_OUT_OF_RANGE`, CRITICAL) : 97 signalement(s), 96 observation(s) — note_admission, note_diplome_anterieur, note_moyenne_s1, note_moyenne_s2.
- **Âge impossible (≤ 0 ou > 120 ans)** (`DOM_AGE_IMPOSSIBLE`, CRITICAL) : 40 signalement(s), 40 observation(s) — age_inscription, age_inscription_mois.
- **Nombre d'UE ou d'évaluations négatif** (`DOM_NEGATIVE_COUNT`, CRITICAL) : 23 signalement(s), 23 observation(s) — nb_evaluations_s1, ue_inscrites_s2.
- **Doublon exact d'une observation** (`DUP_EXACT_ROW`, HIGH) : 80 signalement(s), 80 observation(s) — toutes.
- **UE validées supérieures aux UE inscrites** (`CON_VALIDATED_GT_ENROLLED`, HIGH) : 49 signalement(s), 49 observation(s) — ue_validees_s1, ue_validees_s2.
- **Note moyenne nulle malgré des UE validées** (`CON_ZERO_GRADE_WITH_VALIDATED`, HIGH) : 12 signalement(s), 12 observation(s) — note_moyenne_s1, note_moyenne_s2.
- **Code sentinelle probable (999)** (`DOM_SENTINEL_VALUE`, HIGH) : 10 signalement(s), 10 observation(s) — nb_evaluations_s1, ue_inscrites_s2.
- **Type lu différent du type attendu** (`STR_TYPE_MISMATCH`, HIGH) : 5 signalement(s), 0 observation(s) — age_inscription, note_admission, note_diplome_anterieur, note_moyenne_s1, note_moyenne_s2.

- Cible déséquilibrée : classe majoritaire « Diplômé », minoritaire « En cours », ratio 2.78 (Accuracy d'un modèle constant : 49,9 %).

## 3. Méthodologie de détection

Principes : lecture du CSV **en texte brut** (aucune conversion implicite), valeurs originales conservées dans chaque signalement, aucun nettoyage, aucune imputation, aucune suppression. Les contrôles croisés et statistiques portent sur les seules valeurs du domaine métier, pour ne pas re-signaler une valeur impossible déjà détectée. Gravité (impact) et diagnostic (certitude) sont deux axes distincts.

| Famille | Méthodes | Seuils |
|---|---|---|
| Structure | Colonnes attendues/inattendues, types, colonnes vides ou constantes | quasi constante ≥ 95% |
| Valeurs manquantes | Natives, espaces, NULL textuels, déguisées ; par ligne ; phi | ligne ≥ 3 manques ; phi ≥ 0.3 |
| Doublons | Exacts, identifiants divergents, contenu identique, après normalisation | — |
| Format | Variantes de modalités, synonymes, virgule décimale, texte, caractères | similarité ≥ 0.85 |
| Domaine métier | Bornes du dictionnaire, entiers ≥ 0, modalités, âges | âge plausible [16 ; 70] (hypothèse) |
| Cohérence | UE, évaluations, notes, âges, exports, niveau, filière, admission | tolérance exports 10 pts ; validation 10/20 (hypothèse) |
| Atypiques univariés | IQR, Z-score (si \|asymétrie\| ≤ 1), Z-score modifié (MAD) | IQR × 1.5 / × 3.0 ; \|z\| > 3.0 ; \|M\| > 3.5 ; consensus ≥ 2 méthodes ; log1p si asymétrie > 1 |
| Modalités rares | Fréquence après normalisation | < 1% et ≤ 20 obs. |
| Atypiques multivariés | Isolation Forest, LOF (facultatif) | contamination 0.01 ; graine 42 |
| Redondances | Égalité, corrélations, dépendances fonctionnelles, V de Cramér | \|ρ\| ≥ 0.8 / ≥ 0.98 ; V ≥ 0.5 |
| Fuite de données | Rôle, disponibilité, association à la cible, manques informatifs | η ou V ≥ 0.5 |
| Déséquilibre | Effectifs, proportions, ratio | ratio ≥ 2.0 |

Le catalogue complet des règles (identifiant, justification, gravité) est dans `docs/audit_rules_catalog.md`.

## 4. Résultats globaux

| Gravité | Signalements | Observations distinctes |
|---|---|---|
| Critique (CRITICAL) | 160 | 159 |
| Élevée (HIGH) | 160 | 141 |
| Modérée (MEDIUM) | 1797 | 1426 |
| Faible (LOW) | 577 | 538 |
| Information (INFO) | 1022 | 522 |

Par nature du diagnostic :

| Diagnostic | Signalements | Observations distinctes |
|---|---|---|
| Erreur confirmée | 2196 | 1752 |
| Valeur statistiquement atypique | 1178 | 554 |
| Anomalie potentielle | 301 | 274 |
| Information descriptive | 26 | 0 |
| Risque méthodologique | 15 | 0 |

## 5. Analyse par catégorie d'anomalies

| Catégorie | Signalements | Observations distinctes | Gravité maximale | Règles déclenchées |
|---|---|---|---|---|
| Valeurs manquantes | 1334 | 1156 | MEDIUM | 3 |
| Atypiques univariés | 1122 | 530 | MEDIUM | 3 |
| Format et saisie | 573 | 538 | LOW | 3 |
| Cohérence entre variables | 330 | 292 | HIGH | 6 |
| Domaine métier | 170 | 168 | CRITICAL | 4 |
| Doublons | 80 | 80 | HIGH | 1 |
| Atypiques multivariés | 74 | 74 | INFO | 1 |
| Structure | 13 | 0 | HIGH | 3 |
| Redondances | 11 | 0 | MEDIUM | 3 |
| Fuite de données | 8 | 0 | HIGH | 5 |
| Déséquilibre des classes | 1 | 0 | MEDIUM | 1 |

![Signalements par catégorie et gravité](../outputs/audit/figures/04_signalements_par_categorie.png)

*Figure — Signalements par catégorie et gravité.*

Détail par règle :

| Règle | Intitulé | Catégorie | Gravité | Diagnostic | Signalements | Observations |
|---|---|---|---|---|---|---|
| DOM_OUT_OF_RANGE | Valeur hors des bornes du dictionnaire | domaine_metier | CRITICAL | erreur_confirmee | 97 | 96 |
| DOM_AGE_IMPOSSIBLE | Âge impossible (≤ 0 ou > 120 ans) | domaine_metier | CRITICAL | erreur_confirmee | 40 | 40 |
| DOM_NEGATIVE_COUNT | Nombre d'UE ou d'évaluations négatif | domaine_metier | CRITICAL | erreur_confirmee | 23 | 23 |
| DUP_EXACT_ROW | Doublon exact d'une observation | doublons | HIGH | erreur_confirmee | 80 | 80 |
| CON_VALIDATED_GT_ENROLLED | UE validées supérieures aux UE inscrites | coherence_variables | HIGH | erreur_confirmee | 49 | 49 |
| CON_ZERO_GRADE_WITH_VALIDATED | Note moyenne nulle malgré des UE validées | coherence_variables | HIGH | anomalie_potentielle | 12 | 12 |
| DOM_SENTINEL_VALUE | Code sentinelle probable (999) | domaine_metier | HIGH | anomalie_potentielle | 10 | 10 |
| STR_TYPE_MISMATCH | Type lu différent du type attendu | structure | HIGH | erreur_confirmee | 5 | 0 |
| CON_NO_EVAL_GT_ENROLLED | UE sans évaluation supérieures aux UE inscrites | coherence_variables | HIGH | erreur_confirmee | 3 | 3 |
| LEA_DUPLICATE_SPLIT | Même étudiant présent plusieurs fois : risque de chevauchement | fuite_donnees | HIGH | risque_methodologique | 1 | 0 |
| MIS_NATIVE | Valeur manquante native (champ vide) | valeurs_manquantes | MEDIUM | erreur_confirmee | 1186 | 1054 |
| UNI_EXTREME_OUTLIER | Valeur extrêmement atypique (consensus de méthodes robustes) | atypique_univarie | MEDIUM | valeur_atypique | 186 | 141 |
| CON_VALIDATED_PLUS_NO_EVAL_GT_ENROLLED | UE validées + UE sans évaluation > UE inscrites | coherence_variables | MEDIUM | anomalie_potentielle | 175 | 153 |
| MIS_DISGUISED | Valeur manquante déguisée (ND, ?, Non renseigné…) | valeurs_manquantes | MEDIUM | erreur_confirmee | 135 | 133 |
| CON_GRADUATE_WITHOUT_UE | Diplômé sans aucune UE inscrite en S1 et en S2 | coherence_variables | MEDIUM | anomalie_potentielle | 76 | 76 |
| CON_CREDITED_GT_VALIDATED | UE créditées supérieures aux UE validées | coherence_variables | MEDIUM | anomalie_potentielle | 15 | 11 |
| MIS_ROW_CONCENTRATION | Observation concentrant plusieurs valeurs manquantes | valeurs_manquantes | MEDIUM | anomalie_potentielle | 13 | 13 |
| RED_DETERMINISTIC | Dépendance déterministe entre variables | redondance | MEDIUM | risque_methodologique | 6 | 0 |
| STR_CONSTANT_COLUMN | Colonne constante | structure | MEDIUM | risque_methodologique | 2 | 0 |
| IMB_CLASS_IMBALANCE | Déséquilibre des classes de la cible | desequilibre_classes | MEDIUM | risque_methodologique | 1 | 0 |
| LEA_IDENTIFIER | Identifiant utilisable comme variable | fuite_donnees | MEDIUM | risque_methodologique | 1 | 0 |
| RED_NEAR_DUPLICATE | Colonnes quasi identiques | redondance | MEDIUM | risque_methodologique | 1 | 0 |
| FMT_CATEGORY_VARIANT | Variante de saisie d'une modalité (espaces, casse, accents) | format_saisie | LOW | erreur_confirmee | 430 | 409 |
| FMT_NUMERIC_REPRESENTATION | Représentation numérique non standard (virgule décimale, espaces) | format_saisie | LOW | erreur_confirmee | 80 | 78 |
| FMT_FOREIGN_SYNONYM | Synonyme dans une autre langue (YES / NO) | format_saisie | LOW | erreur_confirmee | 63 | 62 |
| STR_TYPE_MISMATCH | Type lu différent du type attendu | structure | LOW | erreur_confirmee | 4 | 0 |
| UNI_OUTLIER | Valeur statistiquement atypique | atypique_univarie | INFO | valeur_atypique | 918 | 495 |
| MUL_OUTLIER | Observation atypique en plusieurs dimensions | atypique_multivarie | INFO | valeur_atypique | 74 | 74 |
| UNI_RARE_CATEGORY | Modalité rare | atypique_univarie | INFO | information_descriptive | 18 | 0 |
| RED_HIGH_CORRELATION | Forte corrélation entre variables numériques | redondance | INFO | information_descriptive | 4 | 0 |
| LEA_STRONG_PREDICTOR | Forte association avec la cible d'une variable disponible en fin de S2 | fuite_donnees | INFO | information_descriptive | 3 | 0 |
| LEA_TECHNICAL_METADATA | Métadonnée technique sans sens métier | fuite_donnees | INFO | risque_methodologique | 2 | 0 |
| LEA_AUDIT_STATISTICS | Statistiques d'audit calculées sur l'ensemble des données | fuite_donnees | INFO | risque_methodologique | 1 | 0 |
| STR_SHAPE | Dimensions du jeu de données | structure | INFO | information_descriptive | 1 | 0 |
| STR_TYPE_MISMATCH | Type lu différent du type attendu | structure | INFO | erreur_confirmee | 1 | 0 |

## 6. Analyse par variable

Variables classées par nombre d'observations concernées par un signalement de gravité supérieure à INFO (15 premières ; tableau complet : `qualite_variables.csv`) :

| variable | type_attendu | type_observe | pct_manquants | n_critical | n_high | n_medium | n_low | n_observations_concernees_hors_info | pct_observations_concernees_hors_info |
|---|---|---|---|---|---|---|---|---|---|
| note_moyenne_s2 | decimal | texte | 3.44 | 22 | 5 | 155 | 0 | 182 | 4.04 |
| note_admission | decimal | texte | 2.69 | 30 | 0 | 123 | 28 | 181 | 4.02 |
| boursier | texte | texte | 2.22 | 0 | 0 | 100 | 78 | 178 | 3.95 |
| ue_validees_s2 | entier | decimal | 1.24 | 0 | 24 | 151 | 0 | 175 | 3.89 |
| note_moyenne_s1 | decimal | texte | 2.49 | 22 | 7 | 112 | 26 | 167 | 3.71 |
| note_diplome_anterieur | decimal | texte | 2.51 | 23 | 0 | 115 | 26 | 164 | 3.64 |
| ue_inscrites_s1 | entier | decimal | 0.78 | 0 | 0 | 162 | 0 | 162 | 3.6 |
| diplome_anterieur | texte | texte | 2.53 | 0 | 0 | 114 | 45 | 159 | 3.53 |
| mode_admission | texte | texte | 1.95 | 0 | 0 | 88 | 46 | 134 | 2.98 |
| age_inscription | entier | texte | 1.91 | 25 | 0 | 99 | 0 | 124 | 2.75 |
| ue_validees_s1 | entier | entier | 0 | 0 | 25 | 95 | 0 | 120 | 2.66 |
| niveau_dossier | texte | texte | 1.53 | 0 | 0 | 69 | 45 | 114 | 2.53 |
| frais_scolarite_a_jour | texte | texte | 1.04 | 0 | 0 | 47 | 65 | 112 | 2.49 |
| filiere | texte | texte | 0.98 | 0 | 0 | 44 | 55 | 99 | 2.2 |
| rang_voeu | texte | texte | 1.02 | 0 | 0 | 46 | 52 | 98 | 2.18 |

_… 18 ligne(s) supplémentaire(s) dans les CSV._

![Variables les plus concernées](../outputs/audit/figures/05_signalements_par_variable.png)

*Figure — Variables les plus concernées.*

![Valeurs manquantes par variable](../outputs/audit/figures/01_valeurs_manquantes_par_variable.png)

*Figure — Valeurs manquantes par variable.*

![Carte des valeurs manquantes](../outputs/audit/figures/02_carte_valeurs_manquantes.png)

*Figure — Carte des valeurs manquantes.*

Valeurs manquantes : 1 321 cellules (0,9 %), 1 156 observations avec au moins une valeur manquante. Nature : 1186 natives, 135 déguisées, 0 espaces seuls, 0 NULL textuels. Les valeurs déguisées expliquent la lecture en texte de plusieurs colonnes numériques.

## 7. Répartition par gravité

| Catégorie | CRITICAL | HIGH | MEDIUM | LOW | INFO |
|---|---|---|---|---|---|
| Atypiques multivariés | 0 | 0 | 0 | 0 | 74 |
| Atypiques univariés | 0 | 0 | 186 | 0 | 936 |
| Cohérence entre variables | 0 | 64 | 266 | 0 | 0 |
| Domaine métier | 160 | 10 | 0 | 0 | 0 |
| Doublons | 0 | 80 | 0 | 0 | 0 |
| Déséquilibre des classes | 0 | 0 | 1 | 0 | 0 |
| Format et saisie | 0 | 0 | 0 | 573 | 0 |
| Fuite de données | 0 | 1 | 1 | 0 | 6 |
| Redondances | 0 | 0 | 7 | 0 | 4 |
| Structure | 0 | 5 | 2 | 4 | 2 |
| Valeurs manquantes | 0 | 0 | 1334 | 0 | 0 |

![Répartition par gravité](../outputs/audit/figures/03_signalements_par_gravite.png)

*Figure — Répartition par gravité.*

![Nombre de signalements (≥ LOW) par observation](../outputs/audit/figures/06_signalements_par_observation.png)

*Figure — Nombre de signalements (≥ LOW) par observation.*

## 8. Principales incohérences métier

| rule_id | titre | gravite | diagnostic | n_signalements | n_observations_distinctes | variables | justification |
|---|---|---|---|---|---|---|---|
| DOM_OUT_OF_RANGE | Valeur hors des bornes du dictionnaire | CRITICAL | erreur_confirmee | 97 | 96 | note_admission, note_diplome_anterieur, note_moyenne_s1, note_moyenne_s2 | Le dictionnaire fixe les échelles : notes d'admission et antérieures sur 200, notes semestrielles sur 20. |
| DOM_AGE_IMPOSSIBLE | Âge impossible (≤ 0 ou > 120 ans) | CRITICAL | erreur_confirmee | 40 | 40 | age_inscription, age_inscription_mois | Un âge nul, négatif ou supérieur à 120 ans est biologiquement impossible. |
| DOM_NEGATIVE_COUNT | Nombre d'UE ou d'évaluations négatif | CRITICAL | erreur_confirmee | 23 | 23 | nb_evaluations_s1, ue_inscrites_s2 | Le dictionnaire impose des entiers non négatifs. |
| CON_VALIDATED_GT_ENROLLED | UE validées supérieures aux UE inscrites | HIGH | erreur_confirmee | 49 | 49 | ue_validees_s1, ue_validees_s2 | Une UE validée est une UE suivie. Les UE créditées ne dépassent jamais les UE inscrites dans le fichier, ce qui indique qu'elles y sont comptées. |
| CON_ZERO_GRADE_WITH_VALIDATED | Note moyenne nulle malgré des UE validées | HIGH | anomalie_potentielle | 12 | 12 | note_moyenne_s1, note_moyenne_s2 | Le dictionnaire justifie une note nulle par l'absence d'UE validée ; avec des UE validées, le 0 ressemble à un code de valeur manquante. |
| DOM_SENTINEL_VALUE | Code sentinelle probable (999) | HIGH | anomalie_potentielle | 10 | 10 | nb_evaluations_s1, ue_inscrites_s2 | 999 est un code conventionnel de valeur inconnue ; aucune borne haute n'est fixée par le dictionnaire, d'où un diagnostic potentiel. |
| CON_NO_EVAL_GT_ENROLLED | UE sans évaluation supérieures aux UE inscrites | HIGH | erreur_confirmee | 3 | 3 | ue_sans_evaluation_s2 | Une UE sans évaluation est une UE inscrite. |
| CON_VALIDATED_PLUS_NO_EVAL_GT_ENROLLED | UE validées + UE sans évaluation > UE inscrites | MEDIUM | anomalie_potentielle | 175 | 153 | ue_validees_s1, ue_validees_s2 | Si une UE validée a été évaluée, les deux ensembles sont disjoints. Une UE créditée peut toutefois être validée sans évaluation : diagnostic à confirmer. |
| CON_GRADUATE_WITHOUT_UE | Diplômé sans aucune UE inscrite en S1 et en S2 | MEDIUM | anomalie_potentielle | 76 | 76 | statut_academique | Un diplômé sans UE inscrite la première année est surprenant ; des parcours particuliers (équivalences, reprises) restent possibles. |
| CON_CREDITED_GT_VALIDATED | UE créditées supérieures aux UE validées | MEDIUM | anomalie_potentielle | 15 | 11 | ue_creditees_s1, ue_creditees_s2 | Hypothèse : une UE créditée (équivalence) est comptée comme validée. Non confirmé par le dictionnaire. |

![Violations de domaine et incohérences](../outputs/audit/figures/12_incoherences_metier.png)

*Figure — Violations de domaine et incohérences.*

![UE validées vs inscrites (S1)](../outputs/audit/figures/13_ue_validees_vs_inscrites_s1.png)

*Figure — UE validées vs inscrites (S1).*

Contrôles exécutés sans aucune incohérence détectée (sur les valeurs du domaine) : `CON_ACTIVITY_WITHOUT_ENROLMENT_s1`, `CON_ACTIVITY_WITHOUT_ENROLMENT_s2`, `CON_ADMISSION_ARCHIVE`, `CON_ADMISSION_MODE_AGE`, `CON_AGE_MONTHS`, `CON_CREDITED_GT_ENROLLED_s1`, `CON_CREDITED_GT_ENROLLED_s2`, `CON_EVALUATIONS_LT_VALIDATED_s1`, `CON_EVALUATIONS_LT_VALIDATED_s2`, `CON_FILIERE_REGIME`, `CON_GRADE_WITHOUT_EVALUATION_s1`, `CON_GRADE_WITHOUT_EVALUATION_s2`, `CON_NIVEAU_DOSSIER`, `CON_NO_EVAL_GT_ENROLLED_s1`, `CON_PASSING_GRADE_NO_VALIDATED_s1`, `CON_PASSING_GRADE_NO_VALIDATED_s2`.

## 9. Analyse des doublons

| Indicateur | Valeur |
|---|---|
| Lignes en double exact (occurrences supplémentaires) | 80 |
| Groupes de doublons exacts | 80 |
| Lignes partageant un identifiant | 160 |
| Identifiants répétés | 80 |
| Groupes d'identifiants aux informations divergentes | 0 |
| Groupes de contenu identique sous des identifiants différents | 0 |
| Groupes de doublons révélés après normalisation | 0 |

Tous les identifiants répétés correspondent à des copies strictement identiques : il s'agit de doubles exports d'un même enregistrement, sans conflit d'information. Ils doivent être traités **avant** la séparation apprentissage/test (décision D-005), faute de quoi un même étudiant pourrait figurer dans les deux ensembles.

## 10. Analyse des valeurs atypiques

| variable | echelle | queue_examinee | n_analyses | mediane | borne_basse_iqr | borne_haute_iqr | methodes_applicables | n_atypiques_iqr | n_atypiques_z | n_atypiques_mad | n_atypiques_extremes | n_signalements_consensus |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| note_diplome_anterieur | identite | deux | 4368 | 133 | 100 | 164 | IQR, Z-score, Z-score modifié | 78 | 20 | 55 | 2 | 55 |
| note_admission | identite | deux | 4353 | 126 | 92.9 | 160 | IQR, Z-score, Z-score modifié | 131 | 21 | 37 | 2 | 37 |
| age_inscription | log1p | haute | 4393 | 20 | 12.5 | 37.5 | IQR, Z-score modifié | 314 | 0 | 436 | 13 | 314 |
| ue_creditees_s1 | log1p | haute | 590 | 4 | -0.423 | 45.8 | IQR, Z-score, Z-score modifié | 0 | 0 | 0 | 0 | 0 |
| ue_inscrites_s1 | log1p | haute | 4288 | 6 | 4.2 | 9.36 | IQR, Z-score modifié | 295 | 0 | 127 | 127 | 127 |
| nb_evaluations_s1 | log1p | haute | 4099 | 8 | 3.96 | 16.7 | IQR, Z-score, Z-score modifié | 159 | 24 | 18 | 9 | 24 |
| ue_validees_s1 | log1p | haute | 3782 | 6 | 2.02 | 10.6 | IQR, Z-score, Z-score modifié | 183 | 10 | 48 | 10 | 48 |
| note_moyenne_s1 | identite | deux | 3657 | 12.7 | 9.01 | 16.3 | IQR, Z-score, Z-score modifié | 29 | 16 | 3 | 0 | 16 |
| ue_sans_evaluation_s1 | log1p | haute | 299 | 1 | 0.0887 | 4.51 | IQR | 24 | 0 | 0 | 0 | 24 |
| ue_creditees_s2 | log1p | haute | 542 | 4 | -0.158 | 23.9 | IQR, Z-score, Z-score modifié | 0 | 0 | 0 | 0 | 0 |
| ue_inscrites_s2 | log1p | haute | 4306 | 6 | 2.9 | 11.3 | IQR, Z-score modifié | 128 | 0 | 82 | 8 | 82 |
| nb_evaluations_s2 | log1p | haute | 4097 | 8 | 3.96 | 16.7 | IQR, Z-score, Z-score modifié | 111 | 25 | 8 | 2 | 25 |
| ue_validees_s2 | log1p | haute | 3578 | 6 | 2.02 | 10.6 | IQR, Z-score, Z-score modifié | 129 | 5 | 18 | 5 | 18 |
| note_moyenne_s2 | identite | deux | 3469 | 12.7 | 8.79 | 16.6 | IQR, Z-score, Z-score modifié | 16 | 11 | 3 | 0 | 11 |
| ue_sans_evaluation_s2 | log1p | haute | 288 | 1.5 | -0.293 | 10.3 | IQR, Z-score, Z-score modifié | 2 | 2 | 13 | 0 | 2 |
| note_admission_archive | identite | deux | 4449 | 126 | 92.1 | 161 | IQR, Z-score, Z-score modifié | 96 | 28 | 32 | 3 | 32 |
| age_inscription_mois | log1p | haute | 4444 | 245 | 148 | 468 | IQR, Z-score modifié | 289 | 0 | 573 | 5 | 289 |

Lecture : une valeur atypique est **rare**, pas **fausse**. Les âges élevés (reprises d'études, voie « Plus de 23 ans ») ou les nombres d'UE élevés (parcours avec équivalences) sont plausibles. Les zéros structurels (note nulle sans UE validée, aucune UE inscrite) sont exclus des calculs ; pour les comptages, seule la queue haute est examinée. Les valeurs impossibles sont traitées par le domaine métier, pas ici.

![Boxplots des variables numériques](../outputs/audit/figures/07_boxplots_variables_numeriques.png)

*Figure — Boxplots des variables numériques.*

![Histogrammes et valeurs signalées](../outputs/audit/figures/08_histogrammes_atypiques.png)

*Figure — Histogrammes et valeurs signalées.*

Modalités rares (après harmonisation) :

| variable | modalite_normalisee | n | part |
|---|---|---|---|
| mode_admission | phase 1 - acores | 16 | 0.00362 |
| mode_admission | dispositif 854-b/99 | 10 | 0.00226 |
| mode_admission | dispositif 612/93 | 3 | 0.00068 |
| mode_admission | changement international etablissement/filiere | 1 | 0.00023 |
| mode_admission | dispositif 533-a/99 b3 | 1 | 0.00023 |
| mode_admission | dispositif 533-a/99 b2 | 1 | 0.00023 |
| rang_voeu | rang 0 | 1 | 0.00022 |
| rang_voeu | rang 9 | 1 | 0.00022 |
| filiere | technologies des biocarburants | 12 | 0.00269 |
| diplome_anterieur | superieur frequente | 16 | 0.00364 |
| diplome_anterieur | 12e annee non achevee | 11 | 0.00251 |
| diplome_anterieur | superieur - master | 8 | 0.00182 |
| diplome_anterieur | education de base - cycle 2 | 7 | 0.00159 |
| diplome_anterieur | superieur - deuxieme cycle | 6 | 0.00137 |
| diplome_anterieur | 11e annee non achevee | 5 | 0.00114 |
| diplome_anterieur | 10e annee non achevee | 2 | 0.00046 |
| diplome_anterieur | superieur - doctorat | 1 | 0.00023 |
| diplome_anterieur | 10e annee | 1 | 0.00023 |

Analyse multivariée (périmètre d'ajustement : `all`) sur 15 variables : 46 observations signalées par Isolation Forest, 31 par LOF, **3 par les deux**. Les scores sont des rangs d'atypicité relatifs ; la part signalée est fixée par le paramètre de contamination.

## 11. Analyse des redondances

| variable_1 | variable_2 | type | mesure | valeur | commentaire |
|---|---|---|---|---|---|
| age_inscription | age_inscription_mois | RED_DETERMINISTIC | part coherente | 1 | variable dérivée de la précédente (dictionnaire), confirmée par les données |
| note_diplome_anterieur | niveau_dossier | RED_DETERMINISTIC | part coherente | 1 | variable dérivée de la précédente (dictionnaire), confirmée par les données |
| note_admission | note_admission_archive | RED_NEAR_DUPLICATE | max(\|Pearson\|,\|Spearman\|) | 0.996 | variables quasi identiques : l'une n'apporte presque rien de plus |
| ue_creditees_s1 | ue_creditees_s2 | RED_HIGH_CORRELATION | max(\|Pearson\|,\|Spearman\|) | 0.944 | forte corrélation (association statistique, pas forcément redondance) |
| ue_inscrites_s1 | ue_inscrites_s2 | RED_HIGH_CORRELATION | max(\|Pearson\|,\|Spearman\|) | 0.962 | forte corrélation (association statistique, pas forcément redondance) |
| ue_validees_s1 | ue_validees_s2 | RED_HIGH_CORRELATION | max(\|Pearson\|,\|Spearman\|) | 0.886 | forte corrélation (association statistique, pas forcément redondance) |
| note_moyenne_s1 | note_moyenne_s2 | RED_HIGH_CORRELATION | max(\|Pearson\|,\|Spearman\|) | 0.84 | forte corrélation (association statistique, pas forcément redondance) |
| filiere | regime_cours | RED_DETERMINISTIC | part déterminée | 1 | la valeur de « filiere » détermine celle de « regime_cours » |
| taux_chomage | taux_inflation | RED_DETERMINISTIC | part déterminée | 1 | la valeur de « taux_chomage » détermine celle de « taux_inflation » |
| taux_chomage | indicateur_pib | RED_DETERMINISTIC | part déterminée | 1 | la valeur de « taux_chomage » détermine celle de « indicateur_pib » |
| indicateur_pib | taux_inflation | RED_DETERMINISTIC | part déterminée | 1 | la valeur de « indicateur_pib » détermine celle de « taux_inflation » |

Paires documentées par le dictionnaire :

| paire | n_comparables | correlation_pearson | part_egalite_exacte | part_coherente | ecart_absolu_median | ecart_absolu_q99 | lecture | rapport_correlation_eta |
|---|---|---|---|---|---|---|---|---|
| note_admission / note_admission_archive | 4299 | 0.996 | 0.0037 | 1 | 0.87 | 3.21 | même information issue de deux exports (léger bruit systématique) |  |
| age_inscription / age_inscription_mois | 4333 | 0.999 |  | 1 |  |  | âge en mois simulé à partir de l'âge en années (dérivation documentée) |  |
| note_diplome_anterieur / niveau_dossier | 4301 |  |  | 1 |  |  | niveau dérivé de la note par seuils (dérivation documentée) | 0.91 |

Distinction : `RED_DETERMINISTIC`, `RED_NEAR_DUPLICATE` et `RED_IDENTICAL_COLUMNS` signalent une **redondance réelle** (information dupliquée) ; `RED_HIGH_CORRELATION` et `RED_CATEGORICAL_ASSOCIATION` une **association** statistique, qui ne justifie pas seule une exclusion. Aucune variable n'est supprimée par l'audit.

![Redondances documentées](../outputs/audit/figures/10_redondances_documentees.png)

*Figure — Redondances documentées.*

![Matrice de corrélation de Spearman](../outputs/audit/figures/09_matrice_correlation.png)

*Figure — Matrice de corrélation de Spearman.*

## 12. Risques méthodologiques pour le Machine Learning

| rule_id | severity | column | description |
|---|---|---|---|
| LEA_DUPLICATE_SPLIT | HIGH | id_etudiant | 80 identifiants apparaissent plusieurs fois (160 lignes) : sans dédoublonnage ou découpage groupé, un même étudiant peut se retrouver en apprentissage et en test. |
| IMB_CLASS_IMBALANCE | MEDIUM | statut_academique | Classe majoritaire « Diplômé » (2249 ; 49.9%), classe minoritaire « En cours » (808 ; 17.9%) : ratio 2.78. Un modèle prédisant toujours « Diplômé » obtiendrait une Accuracy de 49.9%. |
| LEA_IDENTIFIER | MEDIUM | id_etudiant | « id_etudiant » est un identifiant : à exclure des variables explicatives. |
| LEA_AUDIT_STATISTICS | INFO |  | Seuils d'audit (quantiles, IQR, corrélations, associations) calculés sur l'ensemble du fichier : usage descriptif uniquement, à ne pas réutiliser pour un traitement appris. |
| LEA_STRONG_PREDICTOR | INFO | note_moyenne_s2 | « note_moyenne_s2 » (S2) fortement associée à la cible (eta = 0.58) : attendu et légitime en fin de S2. |
| LEA_STRONG_PREDICTOR | INFO | ue_validees_s1 | « ue_validees_s1 » (S1) fortement associée à la cible (eta = 0.52) : attendu et légitime en fin de S2. |
| LEA_STRONG_PREDICTOR | INFO | ue_validees_s2 | « ue_validees_s2 » (S2) fortement associée à la cible (eta = 0.62) : attendu et légitime en fin de S2. |
| LEA_TECHNICAL_METADATA | INFO | code_campagne | « code_campagne » est une métadonnée technique (constante dans ce fichier : aucun signal possible ici, mais aucune utilité prédictive et risque si de nouvelles versions apparaissent). |
| LEA_TECHNICAL_METADATA | INFO | version_export | « version_export » est une métadonnée technique (constante dans ce fichier : aucun signal possible ici, mais aucune utilité prédictive et risque si de nouvelles versions apparaissent). |

Répartition de la cible :

| classe | effectif | proportion |
|---|---|---|
| Abandon | 1447 | 0.321 |
| En cours | 808 | 0.179 |
| Diplômé | 2249 | 0.499 |

![Répartition des classes](../outputs/audit/figures/11_repartition_classes.png)

*Figure — Répartition des classes.*

Association des variables avec la cible (10 plus fortes, usage descriptif) :

| variable | disponibilite | mesure | valeur | lecture |
|---|---|---|---|---|
| ue_validees_s2 | s2 | eta | 0.619 | forte association légitime (information disponible en fin de S2) |
| note_moyenne_s2 | s2 | eta | 0.58 | forte association légitime (information disponible en fin de S2) |
| ue_validees_s1 | s1 | eta | 0.523 | forte association légitime (information disponible en fin de S2) |
| note_moyenne_s1 | s1 | eta | 0.493 | association modérée ou faible |
| frais_scolarite_a_jour | inscription | V de Cramér | 0.304 | association modérée ou faible |
| age_inscription_mois | inscription | eta | 0.257 | association modérée ou faible |
| filiere | inscription | V de Cramér | 0.252 | association modérée ou faible |
| age_inscription | inscription | eta | 0.25 | association modérée ou faible |
| mode_admission | inscription | V de Cramér | 0.232 | association modérée ou faible |
| boursier | inscription | V de Cramér | 0.214 | association modérée ou faible |

_… 19 ligne(s) supplémentaire(s) dans les CSV._

Rappels de protocole : séparation stratifiée 80/20 (graine 42) **après** le traitement des doublons et **avant** tout traitement appris ; aucun étudiant commun entre ensembles ni entre plis ; transformations apprises dans des pipelines ajustés sur l'apprentissage de chaque pli ; les seuils de cet audit ne doivent pas être réutilisés comme paramètres de prétraitement.

## 13. Recommandations de nettoyage

Synthèse au format attendu par la SAÉ (problème, variables, diagnostic, conséquences, solution envisagée). Ces propositions sont à **valider et consigner** dans `docs/decision_log.md` ; l'audit n'en applique aucune.

| Problème | Variables | Diagnostic | Conséquences potentielles | Solution envisagée |
|---|---|---|---|---|
| Valeur hors des bornes du dictionnaire (`DOM_OUT_OF_RANGE`) | note_admission, note_diplome_anterieur, note_moyenne_s1, note_moyenne_s2 | CRITICAL · Erreur confirmée · 97 signalement(s) | Valeurs impossibles qui faussent moyennes, échelles (KNN) et seuils des arbres. | Considérer comme manquante (recodage déterministe), puis imputer dans le pipeline ; ne jamais « corriger » par une valeur supposée. |
| Âge impossible (≤ 0 ou > 120 ans) (`DOM_AGE_IMPOSSIBLE`) | age_inscription, age_inscription_mois | CRITICAL · Erreur confirmée · 40 signalement(s) | Valeur aberrante qui fausse les échelles et les distances. | Recoder en manquante ; age_inscription_mois peut aider à vérifier (sans arbitrage automatique). |
| Nombre d'UE ou d'évaluations négatif (`DOM_NEGATIVE_COUNT`) | nb_evaluations_s1, ue_inscrites_s2 | CRITICAL · Erreur confirmée · 23 signalement(s) | Valeurs impossibles, contrôles croisés faussés. | Recoder en manquante lors du nettoyage. |
| Doublon exact d'une observation (`DUP_EXACT_ROW`) | toutes | HIGH · Erreur confirmée · 80 signalement(s) | Surpondération ; même étudiant possible en apprentissage ET en test (fuite, score optimiste). | Conserver une seule occurrence avant la séparation apprentissage/test (décision D-005). |
| UE validées supérieures aux UE inscrites (`CON_VALIDATED_GT_ENROLLED`) | ue_validees_s1, ue_validees_s2 | HIGH · Erreur confirmée · 49 signalement(s) | Profil de réussite impossible, signal trompeur pour le modèle. | Arbitrer avec la source ; à défaut, rendre les deux valeurs manquantes. |
| Note moyenne nulle malgré des UE validées (`CON_ZERO_GRADE_WITH_VALIDATED`) | note_moyenne_s1, note_moyenne_s2 | HIGH · Anomalie potentielle · 12 signalement(s) | Note artificiellement basse, confusion avec les abandons. | Traiter le 0 comme manquant dans ce cas, après validation. |
| Code sentinelle probable (999) (`DOM_SENTINEL_VALUE`) | nb_evaluations_s1, ue_inscrites_s2 | HIGH · Anomalie potentielle · 10 signalement(s) | Valeur extrême artificielle (moyennes, écarts-types et distances écrasés). | Traiter comme valeur manquante déguisée après confirmation. |
| Type lu différent du type attendu (`STR_TYPE_MISMATCH`) | age_inscription, note_admission, note_diplome_anterieur, note_moyenne_s1, note_moyenne_s2 | HIGH · Erreur confirmée · 5 signalement(s) | Calculs impossibles ou faux, encodage catégoriel accidentel de variables numériques. | Identifier les valeurs responsables (voir FMT_* et MIS_*), puis convertir explicitement lors du nettoyage déterministe. |
| UE sans évaluation supérieures aux UE inscrites (`CON_NO_EVAL_GT_ENROLLED`) | ue_sans_evaluation_s2 | HIGH · Erreur confirmée · 3 signalement(s) | Incohérence de comptage. | Vérifier la source. |
| Même étudiant présent plusieurs fois : risque de chevauchement (`LEA_DUPLICATE_SPLIT`) | id_etudiant | HIGH · Risque méthodologique · 1 signalement(s) | Score de test optimiste (le modèle a vu l'étudiant à l'apprentissage). | Dédoublonner avant la séparation ou découper par groupe d'identifiant. |
| Valeur manquante native (champ vide) (`MIS_NATIVE`) | age_inscription, age_inscription_mois, boursier, diplome_anterieur, filiere, frais_scolarite_a_jour, mode_admission, nb_evaluations_s1, niveau_dossier, note_admission, note_admission_archive, note_diplome_anterieur, note_moyenne_s1, note_moyenne_s2, rang_voeu, ue_inscrites_s1, ue_validees_s2 | MEDIUM · Erreur confirmée · 1 186 signalement(s) | Modèles scikit-learn en échec sans imputation ; biais si le manque est informatif. | Imputer dans un pipeline ajusté sur l'apprentissage, ou exclure après analyse. |
| Valeur extrêmement atypique (consensus de méthodes robustes) (`UNI_EXTREME_OUTLIER`) | age_inscription, age_inscription_mois, nb_evaluations_s1, nb_evaluations_s2, note_admission, note_admission_archive, note_diplome_anterieur, ue_inscrites_s1, ue_inscrites_s2, ue_validees_s1, ue_validees_s2 | MEDIUM · Valeur statistiquement atypique · 186 signalement(s) | Forte influence sur les méthodes à distances. | Vérifier la vraisemblance ; conserver si plausible. |
| UE validées + UE sans évaluation > UE inscrites (`CON_VALIDATED_PLUS_NO_EVAL_GT_ENROLLED`) | ue_validees_s1, ue_validees_s2 | MEDIUM · Anomalie potentielle · 175 signalement(s) | Comptages potentiellement incohérents. | Examiner avec la définition exacte des UE créditées. |
| Valeur manquante déguisée (ND, ?, Non renseigné…) (`MIS_DISGUISED`) | age_inscription, boursier, diplome_anterieur, mode_admission, note_admission, note_moyenne_s2 | MEDIUM · Erreur confirmée · 135 signalement(s) | Modalité artificielle « ND » apprise par le modèle ; colonne numérique lue comme texte ; sous-estimation du taux de valeurs manquantes. | Recoder en valeur manquante (nettoyage déterministe), puis traiter avec les autres manques. |
| Diplômé sans aucune UE inscrite en S1 et en S2 (`CON_GRADUATE_WITHOUT_UE`) | statut_academique | MEDIUM · Anomalie potentielle · 76 signalement(s) | Profil atypique difficile à apprendre ; possible erreur d'export. | Examiner ces profils ; ne pas supprimer sans justification. |
| UE créditées supérieures aux UE validées (`CON_CREDITED_GT_VALIDATED`) | ue_creditees_s1, ue_creditees_s2 | MEDIUM · Anomalie potentielle · 15 signalement(s) | Possible incohérence de comptage. | Confirmer la définition des UE créditées avant tout traitement. |
| Observation concentrant plusieurs valeurs manquantes (`MIS_ROW_CONCENTRATION`) | toutes | MEDIUM · Anomalie potentielle · 13 signalement(s) | Imputations multiples sur une même ligne : information largement artificielle. | Examiner ces observations ; envisager leur exclusion si l'information restante est faible. |
| Dépendance déterministe entre variables (`RED_DETERMINISTIC`) | age_inscription, filiere, indicateur_pib, note_diplome_anterieur, taux_chomage | MEDIUM · Risque méthodologique · 6 signalement(s) | Information dupliquée ; risque d'incohérence entre les deux versions. | Conserver la variable source ; exclure la variable dérivée sauf justification. |
| Colonne constante (`STR_CONSTANT_COLUMN`) | code_campagne, version_export | MEDIUM · Risque méthodologique · 2 signalement(s) | Aucun pouvoir prédictif ; bruit inutile pour KNN ; risque si la constante change à l'avenir (dérive). | Exclure des variables explicatives (décision à consigner dans le registre). |
| Déséquilibre des classes de la cible (`IMB_CLASS_IMBALANCE`) | statut_academique | MEDIUM · Risque méthodologique · 1 signalement(s) | Accuracy trompeuse ; classe minoritaire mal reconnue. | Stratifier séparation et plis ; métrique adaptée (F1 macro) ; pondération éventuelle évaluée en validation croisée — aucun rééquilibrage dans l'audit. |
| Identifiant utilisable comme variable (`LEA_IDENTIFIER`) | id_etudiant | MEDIUM · Risque méthodologique · 1 signalement(s) | Apprentissage artificiel, sur-apprentissage. | Exclure des variables explicatives ; le réserver aux contrôles de chevauchement. |
| Colonnes quasi identiques (`RED_NEAR_DUPLICATE`) | note_admission | MEDIUM · Risque méthodologique · 1 signalement(s) | Redondance, importances diluées, incohérences possibles entre versions. | Choisir une version de référence (justification métier). |
| Variante de saisie d'une modalité (espaces, casse, accents) (`FMT_CATEGORY_VARIANT`) | boursier, dette_inscription, diplome_anterieur, filiere, frais_scolarite_a_jour, mode_admission, niveau_dossier, rang_voeu, regime_cours | LOW · Erreur confirmée · 430 signalement(s) | Modalités artificiellement multipliées : encodage one-hot gonflé, effectifs dispersés. | Harmoniser vers la forme de référence (nettoyage déterministe, sans paramètre appris). |
| Représentation numérique non standard (virgule décimale, espaces) (`FMT_NUMERIC_REPRESENTATION`) | note_admission, note_diplome_anterieur, note_moyenne_s1 | LOW · Erreur confirmée · 80 signalement(s) | Colonne entière lue comme texte. | Remplacer la virgule par un point avant conversion. |
| Synonyme dans une autre langue (YES / NO) (`FMT_FOREIGN_SYNONYM`) | boursier, dette_inscription, frais_scolarite_a_jour | LOW · Erreur confirmée · 63 signalement(s) | Modalités supplémentaires dans une variable binaire. | Recoder vers Oui / Non (table de correspondance documentée). |
| Type lu différent du type attendu (`STR_TYPE_MISMATCH`) | age_inscription_mois, nb_evaluations_s1, ue_inscrites_s1, ue_validees_s2 | LOW · Erreur confirmée · 4 signalement(s) | Calculs impossibles ou faux, encodage catégoriel accidentel de variables numériques. | Identifier les valeurs responsables (voir FMT_* et MIS_*), puis convertir explicitement lors du nettoyage déterministe. |

Ordre de traitement suggéré (nettoyage déterministe, sans paramètre appris, applicable avant la séparation) : (1) doublons exacts ; (2) harmonisation des modalités et des formats numériques ; (3) recodage des valeurs manquantes déguisées et des codes sentinelles en valeurs manquantes ; (4) recodage des valeurs impossibles en valeurs manquantes ; (5) décision sur les incohérences certaines ; (6) choix des variables redondantes et métadonnées à exclure. L'imputation, la mise à l'échelle et l'encodage relèvent des pipelines appris.

## 14. Limites du système

- Les seuils de `niveau_dossier` (120/140/160) et le format d'identifiant sont **inférés du fichier**, non documentés au dictionnaire.
- Plusieurs règles reposent sur des **hypothèses** signalées comme telles (plage d'âge plausible, validation à 10/20, UE créditées comptées comme validées) et produisent des anomalies potentielles, jamais des erreurs confirmées.
- Une divergence entre deux variables ne dit pas laquelle est fausse ; l'audit n'arbitre pas.
- Les méthodes statistiques signalent la rareté, pas l'erreur ; leurs résultats dépendent des seuils (configurables) et sont calculés sur l'ensemble du fichier (usage descriptif).
- Les méthodes multivariées dépendent du choix des variables, de la préparation (imputation médiane, échelle robuste) et du taux de contamination fixé.
- Le rapprochement avant/après nettoyage repose sur `id_etudiant` : il est fragile si les identifiants sont modifiés ou dupliqués.
- Les variantes orthographiques non triviales (hors casse, accents, espaces, synonymes connus) ne sont que suggérées (`FMT_SIMILAR_CATEGORIES`).

## 15. Conclusion

L'audit recense 3 716 signalements portant sur 2 216 observations distinctes ; 296 observations portent au moins une anomalie CRITICAL ou HIGH. 577 anomalies de représentation (formats, modalités) relèvent d'un nettoyage déterministe documenté. Des redondances réelles sont confirmées : une seule version de chaque information devrait être conservée. Les colonnes constantes n'ont aucune valeur prédictive. Le déséquilibre des classes impose une séparation et des plis stratifiés et une métrique adaptée. Ces constats alimentent les décisions D-005 à D-009 du registre ; aucune correction n'a été appliquée par l'audit.
