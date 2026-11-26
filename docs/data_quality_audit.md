# Système d'audit et de détection des anomalies (`src/data_quality`)

> Outil de la **Mission 1** : il **détecte, documente et signale** les anomalies de
> `parcours_etudiants.csv`. Il ne corrige, n'impute et ne supprime **jamais** rien : ni
> observation, ni valeur, ni variable. Les décisions de nettoyage restent humaines et sont
> consignées dans [`decision_log.md`](decision_log.md).

## Sommaire

1. [Installation et dépendances](#1-installation-et-dépendances)
2. [Utilisation en terminal](#2-utilisation-en-terminal)
3. [Utilisation dans un notebook](#3-utilisation-dans-un-notebook)
4. [Architecture du module](#4-architecture-du-module)
5. [Principes de détection](#5-principes-de-détection)
6. [Règles de détection](#6-règles-de-détection)
7. [Seuils et justifications](#7-seuils-et-justifications)
8. [Fichiers générés](#8-fichiers-générés)
9. [Interpréter les résultats](#9-interpréter-les-résultats)
10. [Comparer avant / après nettoyage](#10-comparer-avant--après-nettoyage)
11. [Respect du protocole de Machine Learning](#11-respect-du-protocole-de-machine-learning)
12. [Ajouter une règle](#12-ajouter-une-règle)
13. [Tests](#13-tests)
14. [Limites](#14-limites)

## 1. Installation et dépendances

Aucune dépendance supplémentaire : le module utilise uniquement des bibliothèques déjà
déclarées dans [`requirements.txt`](../requirements.txt).

| Bibliothèque | Usage dans l'audit |
|---|---|
| pandas, NumPy | Lecture en texte brut, contrôles vectorisés |
| SciPy | V de Cramér, test du khi-deux (manques informatifs) |
| scikit-learn | Isolation Forest, LOF, découpage groupé stratifié (facultatif) |
| Matplotlib, seaborn | Figures |
| pytest, Ruff | Tests et qualité du code |

Installation : voir le [README](../README.md#installation) (`python -m venv .venv`, puis
`python -m pip install -r requirements.txt`). Le CSV doit être placé dans `data/raw/`.

## 2. Utilisation en terminal

Depuis la racine du projet :

```powershell
# Audit complet (fichier brut), exports dans outputs/audit/, rapport dans reports/
python -m src.data_quality

# Avec les méthodes multivariées (facultatives) et affichage des seules gravités ≥ HIGH
python -m src.data_quality --multivariate --min-severity HIGH

# Quelques contrôles seulement, sans figures
python -m src.data_quality --checks duplicates business_rules consistency --no-figures

# Auditer un autre fichier (ex. données nettoyées) vers un autre dossier
python -m src.data_quality --input data/processed/parcours_nettoye.csv --output-dir outputs/audit_nettoye --report reports/audit_qualite_nettoye.md

# Régénérer le catalogue des règles (docs/audit_rules_catalog.md)
python -m src.data_quality --catalog

# Aide complète
python -m src.data_quality --help
```

| Option | Rôle | Défaut |
|---|---|---|
| `--input` | Fichier source | `data/raw/parcours_etudiants.csv` |
| `--output-dir` | Dossier de destination | `outputs/audit` |
| `--report` / `--no-report` | Rapport Markdown | `reports/audit_qualite.md` |
| `--checks` / `--exclude` | Contrôles à exécuter / exclure | tous sauf `multivariate` |
| `--min-severity` | Gravité minimale affichée dans le terminal (les exports restent complets) | `INFO` |
| `--multivariate` | Active Isolation Forest + LOF | désactivé |
| `--multivariate-scope` | `all` (descriptif) ou `train` (80 %, graine 42) | `all` |
| `--no-figures` | Désactive les figures | figures générées |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |

Contrôles disponibles : `structure`, `missing_values`, `duplicates`, `formats`,
`business_rules`, `consistency`, `statistical`, `multivariate`, `redundancy`, `leakage`,
`class_balance`.

Codes de sortie : `0` succès, `1` au moins un contrôle en échec (journalisé), `2` fichier
absent ou illisible.

## 3. Utilisation dans un notebook

La cellule de localisation de la racine du projet (déjà présente dans les notebooks de
`notebooks/development/`) suffit ; ensuite :

```python
from src.data_quality import run_audit, run_detector, export_results, compare_audits
from src.data_quality import visualization as dqv
from src.visualization import apply_theme

apply_theme()
result = run_audit()                              # fichier brut, contrôles par défaut
result = run_audit(multivariate=True)             # + Isolation Forest / LOF

result.anomalies                                  # 1 ligne = 1 signalement (DataFrame)
result.counts()                                   # signalements vs observations distinctes
result.summary_by_rule()                          # synthèse par règle
result.filter(min_severity="HIGH")                # filtrage par gravité
result.filter(category="coherence_variables", column="ue_validees_s1")
result.tables["valeurs_manquantes"]               # tableaux de synthèse nommés
result.tables["valeurs_atypiques"]                # seuils statistiques par variable

run_detector("duplicates").anomalies              # un seul détecteur

dqv.plot_missing_rates(result)                    # affichage direct dans Jupyter
dqv.plot_severity_distribution(result)
dqv.plot_redundancy_pairs(result)

export_results(result)                            # mêmes fichiers que le terminal
```

`run_audit` accepte aussi un **DataFrame** (par exemple des données nettoyées) : il est
converti en texte sur une copie, l'objet d'origine n'est pas modifié.

Tableaux disponibles dans `result.tables` : `structure_variables`, `valeurs_manquantes`,
`manquants_par_observation`, `manquants_par_classe`, `associations_manquants`, `doublons`,
`variantes_modalites`, `controles_coherence`, `valeurs_atypiques`, `modalites_rares`,
`scores_multivaries` (si activé), `redondances`, `paires_documentees`,
`matrice_correlation_spearman`, `association_cible`, `manquants_informatifs`,
`repartition_classes`.

## 4. Architecture du module

```text
src/
├── audit.py                 Façade historique : from src.audit import run_audit
├── data_loader.py           + load_raw_text_data() : lecture en texte brut, sans conversion
├── visualization.py         Thème graphique commun, palette des classes, save_figure()
└── data_quality/
    ├── __init__.py          API publique
    ├── __main__.py          Interface en ligne de commande (python -m src.data_quality)
    ├── config.py            Schéma du dictionnaire (VARIABLES) + seuils (AuditConfig)
    ├── schemas.py           Severity, DiagnosticStatus, Category, Rule, Anomaly
    ├── rules.py             Registre centralisé des règles (source du catalogue)
    ├── context.py           Vues partagées : texte brut, manquants, numérique, clés normalisées
    ├── audit.py             run_audit(), run_detector(), AuditResult, filtres
    ├── reporting.py         Synthèses, exports CSV/JSON, rapport Markdown, catalogue
    ├── visualization.py     Figures de l'audit
    ├── comparison.py        Comparaison de deux audits (avant / après nettoyage)
    └── detectors/
        ├── structure.py        Dimensions, colonnes, types, colonnes vides / constantes
        ├── missing_values.py   Manques natifs, déguisés, par ligne, associations
        ├── duplicates.py       Doublons exacts, normalisés, identifiants, contenus
        ├── formats.py          Variantes de modalités, synonymes, formats numériques
        ├── business_rules.py   Domaines du dictionnaire, âges, identifiants
        ├── consistency.py      Contrôles croisés entre variables
        ├── statistical.py      IQR, Z-score, Z-score modifié, quantiles, modalités rares
        ├── multivariate.py     Isolation Forest, LOF (facultatif)
        ├── redundancy.py       Colonnes identiques, corrélations, dépendances
        ├── leakage.py          Risques de fuite de données
        └── class_balance.py    Déséquilibre des classes
```

Flux : `run_audit()` → `build_context()` (lecture texte, vues partagées) → chaque détecteur
renvoie un `DetectorOutput` (signalements + tableaux) → `anomalies_to_frame()` (identifiants,
tri, suppression des doublons stricts) → `AuditResult` → `export_results()`.

Un détecteur en échec est journalisé et consigné dans `result.errors` sans interrompre les
autres (`strict=True` pour lever l'erreur).

## 5. Principes de détection

- **Lecture en texte brut** (`dtype=str`, aucune valeur convertie en NaN) : l'audit voit les
  valeurs exactement comme dans le fichier (espaces, virgules, « ND »…).
- **Valeur originale conservée** dans `observed_value` ; pour un contrôle multivariable, toutes
  les valeurs impliquées (`ue_validees_s1='9'; ue_inscrites_s1='6'`).
- **Pas de cascade** : les contrôles croisés, statistiques et multivariés n'utilisent que les
  valeurs du **domaine métier** (`valid_numeric`). Une valeur impossible est signalée une fois,
  par le détecteur de domaine.
- **Un signalement par cellule et par règle** : les variantes d'une même valeur (espaces + casse)
  sont décrites dans un seul signalement ; une ligne déjà signalée comme doublon exact n'est pas
  re-signalée comme « identifiant répété ».
- **Gravité ≠ certitude** : la gravité mesure l'impact (CRITICAL → INFO), le diagnostic la
  certitude (`erreur_confirmee`, `anomalie_potentielle`, `valeur_atypique`,
  `risque_methodologique`, `information_descriptive`).
- **Hypothèses explicites** : toute limite absente du dictionnaire est marquée comme hypothèse et
  produit au plus une `anomalie_potentielle`.

| Gravité | Signification |
|---|---|
| CRITICAL | Règle métier confirmée violée ou exploitation compromise |
| HIGH | Incohérence importante, conflit entre observations, problème majeur |
| MEDIUM | Problème potentiel nécessitant une analyse complémentaire |
| LOW | Problème mineur de représentation, de format ou de normalisation |
| INFO | Observation statistique ou méthodologique, sans erreur confirmée |

Structure d'un signalement : `anomaly_id`, `anomaly_key` (clé stable pour les comparaisons),
`rule_id`, `scope` (`observation` / `global`), `row_index` (ligne 0-indexée ; ligne du CSV =
`row_index + 2`), `id_etudiant`, `column`, `related_columns`, `observed_value`,
`expected_value`, `category`, `severity`, `diagnostic_status`, `description`,
`potential_impact`, `suggested_action`, `detection_method`, `n_affected`. Les signalements
globaux n'ont ni `row_index` ni `id_etudiant`.

## 6. Règles de détection

Le **catalogue complet** (identifiant, description, variables, justification, gravité, impact,
action) est généré depuis le registre : [`audit_rules_catalog.md`](audit_rules_catalog.md).

Contrôles croisés retenus et leur justification :

| Règle | Contrôle | Statut | Justification |
|---|---|---|---|
| `CON_VALIDATED_GT_ENROLLED` | UE validées ≤ UE inscrites | Erreur confirmée | Une UE validée est suivie ; les UE créditées ne dépassent jamais les UE inscrites dans le fichier, elles y sont donc comptées |
| `CON_CREDITED_GT_ENROLLED` | UE créditées ≤ UE inscrites | Erreur confirmée | Idem |
| `CON_NO_EVAL_GT_ENROLLED` | UE sans évaluation ≤ UE inscrites | Erreur confirmée | Sous-ensemble des UE inscrites |
| `CON_VALIDATED_PLUS_NO_EVAL_GT_ENROLLED` | validées + sans évaluation ≤ inscrites | Potentielle | Une UE créditée peut être validée sans évaluation |
| `CON_CREDITED_GT_VALIDATED` | créditées ≤ validées | Potentielle | Hypothèse non confirmée par le dictionnaire |
| `CON_EVALUATIONS_LT_VALIDATED` | évaluations ≥ validées − créditées | Potentielle | Plusieurs évaluations par UE : seule la borne basse est contrôlée |
| `CON_ACTIVITY_WITHOUT_ENROLMENT` | aucune évaluation / note sans UE inscrite | Potentielle | — |
| `CON_ZERO_GRADE_WITH_VALIDATED` | note = 0 avec UE validées | Potentielle | Le 0 n'est légitime qu'en l'absence d'UE validée (dictionnaire) |
| `CON_PASSING_GRADE_NO_VALIDATED` | note ≥ 10 sans UE validée | Potentielle | Hypothèse : validation à 10/20 |
| `CON_GRADE_WITHOUT_EVALUATION` | note > 0 sans évaluation | Potentielle | — |
| `CON_AGE_MONTHS` | 12·âge ≤ âge_mois ≤ 12·âge + 11 | Potentielle | Années révolues ; on ne sait pas laquelle est fausse |
| `CON_ADMISSION_ARCHIVE` | écart entre les deux exports ≤ 10 points | Potentielle | Écart systématique ≈ ±3 points observé ; aucun export n'est arbitré |
| `CON_NIVEAU_DOSSIER` | niveau cohérent avec la note antérieure | Potentielle | Seuils inférés du fichier |
| `CON_FILIERE_REGIME` | filière « (soir) » ⇔ régime Soir | Potentielle | Dépendance observée |
| `CON_ADMISSION_MODE_AGE` | « Plus de 23 ans » ⇒ âge ≥ 23 | Potentielle | Date d'appréciation de l'âge inconnue |
| `CON_GRADUATE_WITHOUT_UE` | Diplômé sans UE inscrite en S1 et S2 | Potentielle | Parcours particuliers possibles |

Une note semestrielle nulle n'est **jamais** signalée seule (légitime selon le dictionnaire),
et un indicateur économique négatif n'est **jamais** une anomalie.

## 7. Seuils et justifications

Tous les seuils sont dans `AuditConfig` ([`src/data_quality/config.py`](../src/data_quality/config.py))
et modifiables : `run_audit(config=AuditConfig(iqr_factor=2.0))`.

| Paramètre | Valeur | Justification |
|---|---|---|
| `quasi_constant_share` | 0,95 | Modalité dominante laissant < 5 % de variabilité |
| `row_missing_alert` | 3 | Au-delà, l'imputation d'une même ligne devient importante |
| `missing_association_min_phi` | 0,30 | Corrélation modérée entre indicateurs de manque |
| `age_plausible_min/max` | 16 / 70 | **Hypothèse** : âge usuel d'une inscription dans le supérieur |
| `age_impossible_max` | 120 | Limite biologique |
| `admission_archive_tolerance` | 10 points | Bien au-delà du bruit systématique observé (99 % des écarts ≤ 3,2) |
| `passing_grade` | 10/20 | **Hypothèse** : seuil de validation usuel |
| `niveau_dossier_thresholds` | 120 / 140 / 160 | **Inférés** : séparation parfaite des valeurs du domaine |
| `iqr_factor` / `iqr_extreme_factor` | 1,5 / 3 | Moustaches et « far out » de Tukey |
| `zscore_threshold` | 3 | Convention ; appliqué seulement si \|asymétrie\| ≤ 1 |
| `modified_zscore_threshold` | 3,5 | Iglewicz & Hoaglin (1993) |
| `log_transform_skewed` | oui | Asymétrie > 1 : méthodes sur `log1p`, bornes reconverties |
| `min_methods_agreement` | 2 | Un signalement individuel exige l'accord de deux méthodes |
| `zero_inflated_columns` | notes et comptages semestriels | Zéros structurels (abandon, aucune UE) exclus des seuils |
| `rare_category_share` / `max_count` | 1 % / 20 | Modalité trop rare pour être apprise de façon stable |
| `similar_category_ratio` | 0,85 | Similarité difflib suggérant une variante orthographique |
| `multivariate_contamination` | 0,01 | Part arbitraire d'observations signalées (1 %) |
| `lof_neighbors` / `isolation_forest_estimators` | 20 / 300 | Valeurs usuelles, stables sur ~4 500 lignes |
| `high_correlation` / `near_identical_correlation` | 0,80 / 0,98 | Forte association / quasi-duplication |
| `cramers_v_threshold` | 0,50 | Association forte entre qualitatives |
| `functional_dependency_share` | 0,99 | Une valeur en détermine une autre dans ≥ 99 % des cas |
| `target_association_threshold` | 0,50 | η ou V de Cramér élevé avec la cible |
| `class_imbalance_ratio_alert` | 2,0 | Classe majoritaire au moins deux fois plus fréquente |

Atypiques univariés : pour les **comptages** (UE, évaluations, âges), seule la queue **haute**
est examinée (la borne basse est fixée par le domaine, 0). Lorsque l'IQR ou la MAD est nul,
la méthode est déclarée non applicable (`UNI_ZERO_DISPERSION`) au lieu de signaler toute
valeur différente du mode.

## 8. Fichiers générés

| Fichier | Contenu | Versionné |
|---|---|---|
| `outputs/audit/anomalies_detail.csv` | Tous les signalements (avec identifiants) | Non |
| `outputs/audit/anomalies_synthese.csv` | Une ligne par règle : signalements, observations distinctes | Non |
| `outputs/audit/qualite_variables.csv` | Par variable : types attendu/lu, manquants, signalements par gravité | Non |
| `outputs/audit/doublons.csv` | Groupes de doublons, lignes et variables divergentes | Non |
| `outputs/audit/valeurs_manquantes.csv` | Manques par variable et par nature, marqueurs observés, taux par classe | Non |
| `outputs/audit/incoherences_metier.csv` | Signalements de domaine et de cohérence | Non |
| `outputs/audit/valeurs_atypiques.csv` | Statistiques, quantiles, bornes et comptes par méthode | Non |
| `outputs/audit/scores_multivaries.csv` | Scores Isolation Forest / LOF (si activé) | Non |
| `outputs/audit/redondances.csv` | Redondances détectées et mesures des paires documentées | Non |
| `outputs/audit/risques_methodologiques.csv` | Fuite, déséquilibre, redondances | Non |
| `outputs/audit/association_cible.csv` | Association de chaque variable avec la cible (descriptif) | Non |
| `outputs/audit/audit_resume.json` | Métadonnées, SHA-256 de la source, comptages, configuration | Non |
| `outputs/audit/figures/*.png` | 13 figures (générées seulement si elles apportent une information) | Non |
| `reports/audit_qualite.md` | Rapport en 15 sections, **sans aucun identifiant étudiant** | Oui, après relecture |

## 9. Interpréter les résultats

- **Signalements ≠ observations** : une observation peut cumuler plusieurs anomalies. Le
  rapport donne les deux comptes, ainsi que les observations concernées hors INFO et par une
  anomalie CRITICAL/HIGH.
- **Lire par règle, pas par total** : `anomalies_synthese.csv` est le point d'entrée.
- **`erreur_confirmee`** : le nettoyage doit traiter le cas (recodage, dédoublonnage…).
  **`anomalie_potentielle`** : à examiner, la décision dépend d'une hypothèse.
  **`valeur_atypique`** : rare n'est pas faux ; à conserver par défaut.
  **`risque_methodologique`** : à prendre en compte dans le protocole, pas dans les données.
- **Scores multivariés** : rangs d'atypicité relatifs ; prioriser les observations signalées
  par les **deux** méthodes (`consensus`).

## 10. Comparer avant / après nettoyage

```python
before = run_audit()                                         # données brutes
after = run_audit(df_nettoye, reference_thresholds=before.thresholds)  # seuils constants
comparison = compare_audits(before, after)
comparison.totals            # évolution globale
comparison.by_rule           # par règle
comparison.by_variable       # qualité par variable (hors INFO)
comparison.missing           # valeurs manquantes par variable
comparison.duplicates        # indicateurs de doublons
comparison.business          # incohérences métier
comparison.status_counts()   # résolues / persistantes / nouvelles par règle
comparison.new               # anomalies introduites par le nettoyage
comparison.notes             # mode des seuils, limites du rapprochement
```

- **Seuils constants** (`reference_thresholds=before.thresholds`) : les écarts d'atypiques
  reflètent uniquement l'évolution des données.
- **Seuils recalculés** (par défaut) : les bornes sont réestimées ; une valeur peut changer de
  statut parce que la distribution a changé (ex. après suppression de valeurs extrêmes).
- Le rapprochement utilise une clé stable (règle | identifiant | variable) et le rang
  d'occurrence, jamais le numéro de ligne. Il devient approximatif si les identifiants sont
  modifiés ou absents.

## 11. Respect du protocole de Machine Learning

| Type de traitement | Exemples dans l'audit | Ajustement |
|---|---|---|
| Contrôles déterministes (dictionnaire) | Bornes, entiers, modalités, contrôles croisés | Aucun paramètre appris : applicables à tout ensemble |
| Statistiques descriptives d'audit | Quantiles, IQR, MAD, corrélations, associations avec la cible | Calculées sur tout le fichier, **usage descriptif uniquement** |
| Méthodes apprenant des paramètres | Isolation Forest, LOF, imputation médiane et échelle robuste internes | `--multivariate-scope train` : ajustement sur ~80 % (stratifié, graine 42, groupé par `id_etudiant`), score de toutes les lignes |

Règle : aucun seuil, score ou statistique de cet audit ne doit être réutilisé comme paramètre de
prétraitement ou de sélection de variables. Les traitements appris de la mission 2 seront
estimés dans des pipelines, sur la seule partie apprentissage de chaque pli, après une
séparation stratifiée 80/20 (graine 42) réalisée une fois les doublons traités.

## 12. Ajouter une règle

1. Déclarer la règle dans [`src/data_quality/rules.py`](../src/data_quality/rules.py) :
   identifiant unique, détecteur, catégorie, gravité, diagnostic, intitulé, variables,
   **justification métier**, impact ML, action envisagée, méthode.
2. Ajouter les éventuels seuils dans `AuditConfig` (jamais de valeur codée dans le détecteur).
3. Implémenter le contrôle dans le détecteur concerné, par exemple dans `consistency.py` :

   ```python
   _flag(ctx, out, counts, "CON_MA_REGLE", masque_booleen, ("col_a", "col_b"),
         "Description lisible.", "relation attendue")
   ```

   ou, pour un signalement global : `out.anomalies.append(Anomaly(get_rule("ID"), "texte"))`.
4. Ajouter un test dans [`tests/test_data_quality.py`](../tests/test_data_quality.py)
   (injection de l'anomalie dans le jeu synthétique valide).
5. Régénérer le catalogue : `python -m src.data_quality --catalog`.

Pour un nouveau **détecteur** : créer `detectors/mon_detecteur.py` exposant
`detect_xxx(ctx) -> DetectorOutput`, puis l'enregistrer dans `DETECTORS`
([`detectors/__init__.py`](../src/data_quality/detectors/__init__.py)).

## 13. Tests

```powershell
python -m pytest tests/test_data_quality.py tests/test_data_quality_integration.py
```

Les tests unitaires utilisent un **jeu synthétique** conforme au dictionnaire
([`tests/conftest.py`](../tests/conftest.py)) ; le test sur le fichier réel est ignoré si
`data/raw/parcours_etudiants.csv` est absent.

## 14. Limites

- Seuils de `niveau_dossier` et format d'identifiant **inférés** du fichier.
- Règles fondées sur des **hypothèses** (âge plausible, validation à 10/20, UE créditées) :
  diagnostics potentiels uniquement.
- Une divergence entre deux variables n'indique pas laquelle est fausse.
- Les méthodes statistiques signalent la rareté ; leurs volumes dépendent des seuils.
- Les méthodes multivariées dépendent des variables retenues, de la préparation et du taux de
  contamination ; elles restent facultatives.
- Les variantes orthographiques non triviales sont seulement suggérées.
- Le rapprochement avant/après repose sur `id_etudiant`.
