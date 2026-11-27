# Fonctionnement des programmes Python de l'audit de qualité

> Public visé : les deux membres du binôme, pour comprendre et expliquer le code en soutenance.
> Pour **utiliser** l'outil (commandes, options), voir [`data_quality_audit.md`](../data_quality_audit.md).

## Sommaire

1. [Vue d'ensemble](#1-vue-densemble)
2. [Le trajet d'un audit, étape par étape](#2-le-trajet-dun-audit-étape-par-étape)
3. [Fichiers existants modifiés](#3-fichiers-existants-modifiés)
4. [Les fondations : schemas, config, rules, context](#4-les-fondations)
5. [L'orchestrateur : `audit.py`](#5-lorchestrateur--auditpy)
6. [Les onze détecteurs](#6-les-onze-détecteurs)
7. [Les sorties : reporting, visualization, comparison, CLI](#7-les-sorties)
8. [Les tests](#8-les-tests)
9. [Notions statistiques utilisées](#9-notions-statistiques-utilisées)
10. [Questions probables en soutenance](#10-questions-probables-en-soutenance)

---

## 1. Vue d'ensemble

Le paquet `src/data_quality/` lit `parcours_etudiants.csv`, applique **69 règles** réparties
dans **11 détecteurs**, et produit une liste de signalements (« anomalies ») accompagnée de
tableaux, de figures et d'un rapport. Il **ne modifie jamais** les données : il diagnostique,
il ne corrige pas.

```text
src/
├── audit.py                 façade : « from src.audit import run_audit »
├── data_loader.py           lecture du CSV (ajout : lecture en texte brut)
├── visualization.py         thème graphique commun du projet
└── data_quality/
    ├── __init__.py          ce qu'on peut importer
    ├── __main__.py          commande terminal
    ├── schemas.py           le vocabulaire : gravité, diagnostic, catégorie, anomalie
    ├── config.py            le dictionnaire des variables + les seuils
    ├── rules.py             le registre des 69 règles
    ├── context.py           les « vues » des données partagées par les détecteurs
    ├── audit.py             l'orchestrateur : run_audit()
    ├── detectors/           11 fichiers, un par famille de contrôles
    ├── reporting.py         tableaux de synthèse, CSV, JSON, rapport Markdown
    ├── visualization.py     les 13 figures
    └── comparison.py        comparaison de deux audits (avant / après nettoyage)
```

Trois idées structurent tout le code :

| Idée | Où | Pourquoi |
|---|---|---|
| **Une règle est déclarée une seule fois** | `rules.py` | Le détecteur, le rapport et le catalogue lisent la même description : pas de divergence possible |
| **Les données sont préparées une seule fois** | `context.py` | Les 11 détecteurs lisent les mêmes vues (texte, numérique, clés normalisées) : cohérence et rapidité |
| **Chaque détecteur est indépendant** | `detectors/` | On peut en lancer un seul, en ajouter un, ou en désactiver un sans toucher aux autres |

---

## 2. Le trajet d'un audit, étape par étape

Quand on exécute `run_audit()` (ou `python -m src.data_quality`) :

```text
 parcours_etudiants.csv
          │  1. lecture en TEXTE BRUT (aucune conversion)            data_loader.load_raw_text_data
          ▼
   AuditContext                                                      context.build_context
   ├─ raw            valeurs originales (chaînes)
   ├─ missing_kind   nature de chaque manque (vide, espaces, NULL, ND…)
   ├─ numeric        conversion numérique tolérante (virgule acceptée)
   ├─ valid_numeric  numeric, sans les valeurs impossibles
   └─ keys           modalités normalisées (casse, accents, espaces)
          │  2. chaque détecteur lit le contexte                     detectors/*.py
          ▼
   DetectorOutput × 11  (liste d'Anomaly + tableaux + résumé)
          │  3. assemblage, tri, identifiants A000001…              schemas.anomalies_to_frame
          ▼
   AuditResult  (anomalies, tables, summaries)                      audit.run_audit
          │  4. exports                                              reporting.export_results
          ▼
 outputs/audit/*.csv, audit_resume.json, figures/*.png, reports/audit_qualite.md
```

---

## 3. Fichiers existants modifiés

### `src/data_loader.py`

Ajout de `load_raw_text_data(path=None)`. Différence avec `load_raw_data()` :

| | `load_raw_data()` (existante) | `load_raw_text_data()` (ajoutée) |
|---|---|---|
| Types | pandas devine (int, float, texte) | tout en texte (`dtype=str`) |
| Champ vide | devient `NaN` | reste `""` |
| `"NA"`, `"NULL"` | deviennent `NaN` | restent du texte (`keep_default_na=False`) |
| Usage | modélisation | audit : voir le fichier **tel quel** |

Pourquoi : si pandas convertit automatiquement, on perd l'information « cette valeur était
`120,0` avec une virgule » ou « ce champ contenait `NA` en toutes lettres ». La vérification
d'existence du fichier est factorisée dans `_resolve_existing_path()`, utilisée par les deux
fonctions (même message d'erreur explicite).

### `src/visualization.py`

Le squelette prévoyait un thème commun et une palette des classes ; ils sont implémentés :

- `apply_theme()` : réglages Matplotlib communs (taille, police, grille discrète, pas de cadre
  haut/droit) ;
- `CLASS_COLORS` : une couleur fixe par classe (Abandon, En cours, Diplômé), choisie lisible
  par les personnes daltoniennes ;
- `save_figure(fig, path)` : crée le dossier si besoin et enregistre la figure.

### `src/audit.py`

Ce fichier était un squelette réservé à la mission 1. Il **ré-exporte** les fonctions du paquet
(`run_audit`, `export_results`…) pour que les notebooks puissent écrire
`from src.audit import run_audit`. Il ne contient aucune logique.

---

## 4. Les fondations

### `schemas.py` — le vocabulaire commun

Trois **énumérations** (`StrEnum` : des constantes qui se comportent comme des chaînes) :

| Énumération | Valeurs | Rôle |
|---|---|---|
| `Severity` | CRITICAL, HIGH, MEDIUM, LOW, INFO | **Impact** du problème |
| `DiagnosticStatus` | erreur_confirmee, anomalie_potentielle, valeur_atypique, risque_methodologique, information_descriptive | **Certitude** du diagnostic |
| `Category` | structure, valeurs_manquantes, doublons, … | Famille de contrôle |

Gravité et certitude sont **deux axes séparés** : un doublon exact est une *erreur confirmée*
de gravité HIGH ; une note moyenne nulle avec des UE validées est une *anomalie potentielle* de
gravité HIGH (grave si c'est une erreur, mais pas certain).

Deux **dataclasses** :

- `Rule` : la description complète d'une règle (identifiant, détecteur, catégorie, gravité,
  statut, titre, variables, justification, impact ML, action envisagée, méthode).
- `Anomaly` : un signalement. Il pointe vers sa `Rule` et ajoute le cas concret : ligne,
  identifiant étudiant, colonne, valeur observée (**originale**), valeur attendue, description.
  Sa méthode `to_record()` le transforme en ligne de tableau et calcule la **clé stable**
  `anomaly_key = règle | identifiant | colonne | complément`, utilisée pour comparer deux audits.

`anomalies_to_frame()` assemble tous les signalements en un DataFrame : suppression des
doublons stricts (même clé, même ligne), tri par gravité puis par règle, puis numérotation
`A000001`, `A000002`…

### `config.py` — le dictionnaire et les seuils

**1. `VARIABLES`** : les 33 colonnes du dictionnaire officiel, chacune décrite par un
`VariableSpec` :

```python
VariableSpec("note_admission", CONTINUOUS, "float", "inscription",
             "Note utilisée lors de l'admission, sur 200", 0, 200)
```

| Champ | Exemple | Utilisé par |
|---|---|---|
| `kind` (rôle) | identifiant, binaire, quantitative_discrete, cible… | structure, fuite, statistiques |
| `expected_dtype` | text / float / int | structure (type attendu), domaine (entiers) |
| `availability` | inscription, contexte, s1, s2, technique, apres_s2 | fuite de données |
| `min_value` / `max_value` | 0 / 200 | domaine métier |
| `modalities` | ("Oui", "Non") | domaine, formats |
| `hypothesis` | « plage plausible [16 ; 70] » | documentation : limite NON présente dans le dictionnaire |

Les fonctions d'aide `_note`, `_note20`, `_count` évitent de répéter les mêmes paramètres.

**2. Constantes de détection** : marqueurs de manque reconnus par pandas
(`PANDAS_NULL_TOKENS`), marqueurs déguisés réellement observés (`ND`, `?`, `Non renseigné`…),
codes sentinelles (`999`), synonymes anglais (`YES → oui`), motif d'identifiant (`ET` + 6 chiffres).

**3. `AuditConfig`** : une dataclass qui regroupe **tous les seuils** (IQR 1,5, Z-score 3,
tolérance entre exports 10 points…). Aucun seuil n'est écrit dans les détecteurs : on les
change en un seul endroit, par exemple `run_audit(config=AuditConfig(iqr_factor=2.0))`.

### `rules.py` — le registre des règles

Une liste de 69 objets `Rule`, groupés par détecteur. Exemple :

```python
Rule("CON_VALIDATED_GT_ENROLLED", "consistency", C.CONSISTENCY, S.HIGH, D.CONFIRMED_ERROR,
     "UE validées supérieures aux UE inscrites",            # titre
     "ue_validees_s*, ue_inscrites_s*",                     # variables
     "Une UE validée est une UE suivie. …",                 # justification métier
     "Profil de réussite impossible, …",                    # impact ML
     "Arbitrer avec la source ; …",                         # action envisagée
     "Comparaison ligne à ligne …")                         # méthode
```

- `RULES` : dictionnaire `identifiant → Rule` (un contrôle vérifie qu'aucun identifiant n'est dupliqué).
- `get_rule("ID")` : utilisé par les détecteurs ; erreur explicite si l'identifiant n'existe pas
  (une faute de frappe est détectée immédiatement).
- `rules_frame()` : le registre sous forme de DataFrame, utilisé pour générer le catalogue.

| Détecteur | Règles | Détecteur | Règles |
|---|---|---|---|
| consistency | 16 | formats | 6 |
| structure | 9 | redundancy | 5 |
| business_rules | 9 | duplicates | 4 |
| missing_values | 7 | statistical | 4 |
| leakage | 7 | multivariate, class_balance | 1 + 1 |

### `context.py` — préparer les données une seule fois

**Fonctions de base** (chacune testée séparément) :

| Fonction | Ce qu'elle fait | Exemple |
|---|---|---|
| `classify_missing(series)` | Nature de chaque valeur | `""` → native ; `"  "` → espaces_seuls ; `"NA"` → null_textuel ; `" nd "` → deguisee ; `"12"` → present |
| `parse_numeric(series)` | Conversion tolérante | `"12,5"` → 12.5 ; `" 7 "` → 7 ; `"ND"` → NaN |
| `normalize_key(series)` | Clé de comparaison | `" PHASE 1 - GÉNÉRAL "` → `"phase 1 - general"` |
| `strip_accents(text)` | Retire les accents (décomposition Unicode NFKD) | `"é"` → `"e"` |
| `domain_violation_mask(spec, values, cfg)` | Valeurs **impossibles** d'après le dictionnaire | note 450, âge −3, comptage 7,5 ou 999 |
| `to_text_frame(df)` | Convertit un DataFrame quelconque en texte (NaN → `""`) | audit de données nettoyées |

**La classe `AuditContext`** calcule, dans `__post_init__`, les cinq vues décrites au §2. Point
essentiel : `valid_numeric` est `numeric` **dont on a retiré les valeurs impossibles**.

> Pourquoi ? Si `ue_inscrites_s2 = -3` et `ue_validees_s2 = 2`, le détecteur de domaine signale
> « comptage négatif ». Sans `valid_numeric`, le contrôle croisé signalerait **aussi**
> « validées > inscrites » : deux signalements pour une seule erreur. Avec `valid_numeric`, la
> valeur −3 devient NaN pour les contrôles croisés, qui l'ignorent.

**`build_context(data, cfg)`** accepte un chemin de CSV **ou** un DataFrame, vérifie que le
fichier existe et n'est pas vide (`AuditInputError` sinon) et lit l'en-tête brut avec le module
`csv` (pandas renommerait silencieusement deux colonnes de même nom en `x` et `x.1`).

---

## 5. L'orchestrateur : `audit.py`

### `run_audit(data, config, checks, exclude, multivariate, reference_thresholds, strict)`

1. `resolve_detectors()` choisit les détecteurs à lancer (tous sauf `multivariate` par défaut ;
   erreur explicite si un nom est inconnu).
2. `build_context()` prépare les données.
3. Boucle sur les détecteurs : chacun est appelé dans un `try/except`. Si l'un plante, l'erreur
   est journalisée et enregistrée dans `result.errors`, et **les autres continuent** (sauf si
   `strict=True`).
4. `anomalies_to_frame()` assemble les signalements.
5. Calcul de l'empreinte SHA-256 du fichier (preuve qu'on a audité le bon fichier).
6. Retourne un `AuditResult`.

### `AuditResult`

| Attribut / méthode | Contenu |
|---|---|
| `anomalies` | DataFrame : un signalement par ligne |
| `tables` | dictionnaire de tableaux nommés (`"valeurs_manquantes"`, `"doublons"`…) |
| `summaries` | résumé chiffré de chaque détecteur |
| `filter(...)` | filtrage par gravité, gravité minimale, catégorie, règle, colonne, statut, portée |
| `counts()` | signalements **vs** observations distinctes, par gravité, catégorie, statut |
| `summary_by_rule()` | une ligne par règle |
| `thresholds` | seuils statistiques calculés (réutilisables pour une comparaison) |
| `affected_rows()` | lignes ayant au moins un signalement d'une gravité donnée |

Autres fonctions : `run_detector("duplicates")` (un seul contrôle), `severities_at_least("HIGH")`
(→ `["CRITICAL", "HIGH"]`), `available_checks()`, `file_sha256()`.

---

## 6. Les onze détecteurs

Tous ont la même signature : `detect_xxx(ctx: AuditContext) -> DetectorOutput`. Ils sont
enregistrés dans le dictionnaire `DETECTORS` de `detectors/__init__.py`, dans l'ordre
d'exécution.

### 6.1 `structure.py` — la forme du fichier

1. **Dimensions** (`STR_SHAPE`) et fichier sans ligne (`STR_EMPTY_DATASET`).
2. **Colonnes** comparées au dictionnaire : absentes (`STR_MISSING_COLUMN`), inattendues
   (`STR_UNEXPECTED_COLUMN`), noms en double dans l'en-tête brut (`STR_DUPLICATE_COLUMN_NAME`).
3. **Type** : `infer_observed_type()` reproduit le raisonnement de `pd.read_csv` (une seule
   valeur non numérique → la colonne est lue comme texte). Si le type lu diffère du type
   attendu → `STR_TYPE_MISMATCH`, avec une gravité adaptée : HIGH (numérique lu comme texte),
   LOW (entier lu en flottant à cause d'un vide), INFO (code lu comme nombre).
4. **Colonnes vides, constantes ou quasi constantes** (modalité dominante ≥ 95 %).

Produit le tableau `structure_variables` (une ligne par variable).

### 6.2 `missing_values.py` — les valeurs manquantes

- Parcourt `ctx.missing_kind` : **un signalement par cellule manquante**, avec une règle selon
  la nature (`MIS_NATIVE`, `MIS_WHITESPACE_ONLY`, `MIS_NULL_TOKEN`, `MIS_DISGUISED`). Si la
  cellule est dans `id_etudiant` ou dans la cible → `MIS_KEY_FIELD` (CRITICAL).
- **Par observation** : une ligne avec au moins 3 manques → `MIS_ROW_CONCENTRATION`.
- **Associations** : chaque variable devient un indicateur 0/1 « manquant » ; la corrélation
  entre deux indicateurs (coefficient **phi**) mesure si elles manquent ensemble
  (`MIS_ASSOCIATION` si phi ≥ 0,30).
- Tableaux : manques par variable et par nature (avec les marqueurs réellement observés),
  distribution par observation, taux par classe de la cible.

### 6.3 `duplicates.py` — les doublons

Quatre recherches, de la **plus précise à la plus large** ; une ligne déjà signalée n'est pas
re-signalée par une recherche suivante (ensemble `already_flagged`) :

| Ordre | Recherche | Règle | Méthode |
|---|---|---|---|
| 1 | Lignes strictement identiques | `DUP_EXACT_ROW` | `DataFrame.duplicated` sur le texte brut |
| 2 | Identiques après normalisation | `DUP_NORMALIZED` | même chose sur les clés normalisées |
| 3 | Même identifiant, informations différentes | `DUP_ID_CONFLICT` | groupes d'`id_etudiant`, comparés après normalisation |
| 4 | Même contenu, identifiants différents | `DUP_CONTENT_DIFFERENT_ID` | `duplicated` sur toutes les colonnes sauf l'identifiant |

`_groups()` renvoie les groupes de lignes identiques ; `_emit_groups()` enregistre chaque groupe
dans le tableau `doublons` (avec les variables divergentes) et signale les lignes : la première
sert de référence, les suivantes sont signalées.

### 6.4 `formats.py` — la saisie

- **Variantes de modalités** : `canonical_forms()` construit, pour chaque clé normalisée, la
  **forme de référence** : celle du dictionnaire quand il fixe le domaine (`Jour`, `Oui`…),
  sinon la variante la plus fréquente dans le fichier. Toute valeur dont la clé est connue mais
  dont l'écriture diffère est une variante (`FMT_CATEGORY_VARIANT`) ; `describe_differences()`
  précise lesquelles (espaces superflus, casse, accentuation). `YES`/`NO` → `FMT_FOREIGN_SYNONYM`.
- **Formats numériques** : on compare une conversion **stricte** (`pd.to_numeric`) et une
  conversion **tolérante**. Si seule la tolérante réussit (`"120,0"`, `" 12"`) →
  `FMT_NUMERIC_REPRESENTATION`, avec la forme attendue (`"120.0"`). Si aucune ne réussit et
  que ce n'est pas un marqueur de manque → `FMT_TEXT_IN_NUMERIC`.
- **Caractères parasites** (tabulation, espace insécable, caractères de contrôle) : expression
  régulière → `FMT_PARASITE_CHARACTERS`.
- **Modalités proches** : similarité de chaînes (`difflib.SequenceMatcher`) ≥ 0,85 entre
  modalités d'une variable à liste ouverte → `FMT_SIMILAR_CATEGORIES` (INFO). Les paires qui ne
  diffèrent que par un nombre (« Phase 1 » / « Phase 2 », « b2 » / « b3 ») sont ignorées : ce
  sont de vraies catégories différentes.

Rien n'est modifié : la valeur originale est conservée, la forme de référence est seulement
proposée.

### 6.5 `business_rules.py` — le domaine du dictionnaire

Pour chaque variable numérique, dans cet ordre (une valeur n'est signalée qu'une fois, grâce au
masque `flagged`) :

1. **Âges** : ≤ 0 ou > 120 ans → `DOM_AGE_IMPOSSIBLE` (CRITICAL) ; hors [16 ; 70] →
   `DOM_AGE_IMPLAUSIBLE` (MEDIUM, **hypothèse**).
2. **Comptages négatifs** → `DOM_NEGATIVE_COUNT`.
3. **Hors bornes** (notes sur 200 ou sur 20, taux de chômage [0 ; 100]) → `DOM_OUT_OF_RANGE` ;
   le message précise « probable code sentinelle » si la valeur vaut 999.
4. **Comptage non entier** (7,5 UE) → `DOM_NON_INTEGER`.
5. **999 dans un comptage sans borne haute** → `DOM_SENTINEL_VALUE` (anomalie potentielle : le
   dictionnaire n'interdit pas 999 évaluations, mais c'est un code « inconnu » classique).

Pour les variables à modalités fixées : clé normalisée hors du domaine →
`DOM_CATEGORY_OUT_OF_DOMAIN` (ou `DOM_TARGET_INVALID` pour la cible). Enfin, identifiant ne
respectant pas `ET` + 6 chiffres → `DOM_ID_FORMAT`.

> Un indicateur économique négatif n'est **jamais** signalé : le dictionnaire précise que c'est
> légitime (déflation, récession).

### 6.6 `consistency.py` — la cohérence entre variables

Travaille uniquement sur `valid_numeric`. La fonction `_flag()` signale chaque ligne d'un
masque booléen en conservant **toutes les valeurs originales impliquées**
(`ue_validees_s1='9'; ue_inscrites_s1='6'`).

**Par semestre** (`_semester_rules`, appelée pour S1 puis S2) :

| Contrôle | Statut |
|---|---|
| validées > inscrites ; créditées > inscrites ; sans évaluation > inscrites | erreur confirmée |
| validées + sans évaluation > inscrites | potentielle |
| créditées > validées | potentielle (hypothèse) |
| évaluations < validées − créditées | potentielle |
| aucune UE inscrite mais évaluations ou note > 0 | potentielle |
| note = 0 avec des UE validées | potentielle |
| note ≥ 10 sans UE validée | potentielle (hypothèse 10/20) |
| note > 0 sans évaluation | potentielle |

Les contrôles « potentiels » ne sont faits que sur les lignes qui respectent les contrôles
certains (`certain_ok`) : pas de double signalement.

**Transversaux** : âge en mois hors de [12 × âge ; 12 × âge + 11] ; écart > 10 points entre les
deux exports de la note d'admission ; niveau du dossier différent du niveau attendu
(`expected_niveau()` applique les seuils 120 / 140 / 160) ; filière « (soir) » et régime Jour ;
voie « Plus de 23 ans » et âge < 23 ; diplômé sans aucune UE inscrite en S1 et S2.

Le tableau `controles_coherence` indique le nombre de cas de **chaque** contrôle, y compris
ceux à 0 : un contrôle sans résultat est aussi une information.

### 6.7 `statistical.py` — les valeurs atypiques univariées

**`compute_thresholds(values, column, ctx)`** calcule, pour une variable :

1. On part des valeurs du domaine ; on retire les **zéros structurels** pour les notes et les
   comptages semestriels (un 0 y signifie « abandon » ou « aucune UE », pas une valeur rare).
2. Moins de 30 valeurs → pas d'analyse.
3. Si la distribution est très **asymétrique** (asymétrie > 1, valeurs ≥ 0, ex. l'âge), on
   travaille sur `log1p(x) = ln(1 + x)`, qui la rend plus symétrique.
4. Trois méthodes, chacune seulement si elle a un sens :
   - **IQR** : bornes Q1 − 1,5·IQR et Q3 + 1,5·IQR (et 3·IQR pour « extrême ») — si IQR > 0 ;
   - **Z-score** : moyenne ± 3 écarts-types — seulement si la distribution est à peu près
     symétrique (|asymétrie| ≤ 1) ;
   - **Z-score modifié** : médiane ± 3,5·MAD/0,6745 — si MAD > 0.
5. Les bornes sont reconverties dans l'unité d'origine (`expm1`) pour être lisibles.

**`_flag_outliers()`** : pour les comptages, seule la **queue haute** est examinée. Chaque
méthode « vote » ; une valeur est signalée si **au moins 2 méthodes** sont d'accord (ou la
seule méthode applicable), ou si elle est extrême (au-delà de 3·IQR **et** du Z-score modifié)
→ `UNI_OUTLIER` (INFO) ou `UNI_EXTREME_OUTLIER` (MEDIUM). Statut toujours
« valeur atypique », jamais « erreur ».

Si aucune méthode n'est applicable (IQR et MAD nuls) → `UNI_ZERO_DISPERSION` au lieu de
signaler toutes les valeurs différentes du mode.

**Modalités rares** (`_rare_categories`) : modalité < 1 % des valeurs et ≤ 20 observations,
comptée **après** harmonisation (sinon `yes` paraîtrait rare alors que c'est `Oui`).

**Seuils constants** : si `ctx.reference_thresholds` est fourni (seuils d'un audit précédent),
ils sont réutilisés au lieu d'être recalculés ; la colonne `seuils` vaut alors `reference`.

### 6.8 `multivariate.py` — les observations atypiques en plusieurs dimensions (facultatif)

1. `prepare_matrix()` : 15 variables individuelles (notes, âge, comptages) ; on exclut
   l'identifiant, la cible, les métadonnées, les indicateurs de contexte et les variables
   redondantes ; on écarte les lignes avec plus de 50 % de manques.
2. Préparation : imputation par la médiane puis mise à l'échelle robuste (médiane / IQR).
3. **Isolation Forest** (300 arbres, `random_state=42`) et **LOF** (20 voisins), contamination
   1 % : chacune signale environ 1 % des observations.
4. Scores inversés pour que « plus grand = plus atypique » ; colonne `consensus` = signalé par
   les deux méthodes.
5. Chaque observation signalée → `MUL_OUTLIER` (INFO), avec les 3 variables les plus éloignées
   de la médiane pour aider à l'interpréter.

Avec `multivariate_fit_scope="train"`, `train_mask()` constitue un jeu d'apprentissage d'environ
80 % avec `StratifiedGroupKFold` (5 plis, graine 42, stratifié sur la cible, groupé par
`id_etudiant`) : le modèle est ajusté sur ces lignes seulement, puis toutes sont scorées.

### 6.9 `redundancy.py` — les redondances

Dans l'ordre (une paire déjà signalée n'est pas re-signalée) :

1. **Paires documentées** (`_documented_pairs`) : admission / archive (corrélation, écarts),
   âge / âge en mois (part cohérente avec la formule), note antérieure / niveau (part cohérente,
   rapport de corrélation η). Si ≥ 95 % des lignes respectent la dérivation →
   `RED_DETERMINISTIC`.
2. **Colonnes identiques** → `RED_IDENTICAL_COLUMNS`.
3. **Corrélations** de Pearson et de Spearman : ≥ 0,98 → `RED_NEAR_DUPLICATE` (redondance
   réelle) ; ≥ 0,80 → `RED_HIGH_CORRELATION` (simple association).
4. **Dépendances fonctionnelles** : `functional_dependency_share(a, b)` = part des lignes où
   `b` prend la valeur la plus fréquente de son groupe `a`. Si ≥ 99 % → « a détermine b »
   (`RED_DETERMINISTIC`). Garde-fous : variables à 2–60 modalités, au moins 20 lignes par groupe
   en moyenne, et `b` non quasi constante (sinon la dépendance serait triviale).
5. **V de Cramér** entre qualitatives ≥ 0,5 → `RED_CATEGORICAL_ASSOCIATION`.

### 6.10 `leakage.py` — les risques de fuite de données

- `id_etudiant` → `LEA_IDENTIFIER` ; identifiants répétés → `LEA_DUPLICATE_SPLIT` (un même
  étudiant pourrait tomber en apprentissage **et** en test).
- Métadonnées (`version_export`, `code_campagne`) → `LEA_TECHNICAL_METADATA` (INFO si constantes).
- **Association avec la cible** : η pour une variable numérique, V de Cramér pour une
  qualitative, plus les modalités « pures » (≥ 20 observations, toutes dans la même classe).
  Décision selon la **disponibilité** de la variable :
  - association forte d'une variable de S1/S2 → `LEA_STRONG_PREDICTOR` (INFO : attendu et
    légitime, l'information existe en fin de S2) ;
  - association forte ou modalité pure d'une variable d'inscription ou non documentée →
    `LEA_TARGET_ASSOCIATION` (à vérifier).
- **Manques informatifs** : test du khi-deux entre « manquant oui/non » et la cible ; si
  p < 0,001 et V ≥ 0,1 → `LEA_INFORMATIVE_MISSINGNESS`.
- Rappel systématique `LEA_AUDIT_STATISTICS` : les statistiques de l'audit sont calculées sur
  tout le fichier et ne doivent pas servir au prétraitement.

### 6.11 `class_balance.py` — le déséquilibre des classes

Effectifs et proportions des trois classes (ordre de `config.TARGET_CLASSES`), classe
majoritaire et minoritaire, **ratio** majoritaire / minoritaire et Accuracy d'un modèle qui
prédirait toujours la classe majoritaire. Ratio ≥ 2 → `IMB_CLASS_IMBALANCE` en MEDIUM, sinon
INFO. C'est un **risque méthodologique**, pas une erreur dans les données ; aucun rééquilibrage
n'est fait.

---

## 7. Les sorties

### `reporting.py`

| Fonction | Produit |
|---|---|
| `synthesis_by_rule()` | une ligne par règle : nombre de signalements et d'**observations distinctes** |
| `summary_counts()` | totaux (signalements, observations, hors INFO, CRITICAL/HIGH), par gravité, catégorie, statut |
| `quality_by_variable()` | une ligne par variable : types, manques, signalements par gravité |
| `methodological_risks()` | signalements de fuite, de déséquilibre et de redondance |
| `export_results()` | écrit tous les CSV, le JSON, les figures et le rapport |
| `build_summary()` | contenu de `audit_resume.json` (SHA-256, comptages, configuration) |
| `md_table()` | convertit un DataFrame en tableau Markdown (sans dépendance externe) |
| `write_report()` | rapport en 15 sections via la classe `_ReportBuilder` (une méthode par section) |
| `write_rules_catalog()` | génère `docs/audit_rules_catalog.md` à partir du registre |

Le rapport ne contient **que des agrégats** : aucun identifiant étudiant (vérifié par un test),
car `reports/` est versionné dans un dépôt public.

### `visualization.py` (de l'audit)

Une fonction par figure, qui reçoit l'`AuditResult` et retourne une figure Matplotlib — ou
`None` si elle n'apporterait rien (par exemple aucune valeur manquante). Le dictionnaire
`FIGURES` liste les 13 figures ; `save_audit_figures()` les exporte en PNG. Les couleurs de
gravité sont fixes (rouge = CRITICAL… gris = INFO) et toujours accompagnées d'un libellé.

### `comparison.py`

`compare_audits(avant, apres)` rapproche les signalements par **clé stable + rang
d'occurrence** (deux doublons exacts ont la même clé : le rang les distingue), jamais par numéro
de ligne (qui change dès qu'on supprime une ligne). Une fusion `outer` avec `indicator=True`
classe chaque signalement en **résolu** (seulement avant), **persistant** (des deux côtés) ou
**nouveau** (seulement après). Tableaux d'évolution : totaux, catégories, règles, variables,
manques, doublons, incohérences métier.

### `__main__.py` — la commande terminal

`build_parser()` définit les options avec `argparse` ; `main()` configure la journalisation,
choisit le moteur Matplotlib `Agg` (export sans fenêtre), lance l'audit, exporte et affiche une
synthèse filtrée par `--min-severity`. Codes de retour : `0` succès, `1` un détecteur en
échec, `2` fichier absent ou illisible.

---

## 8. Les tests

| Fichier | Tests | Contenu |
|---|---|---|
| `tests/conftest.py` | — | `make_valid_frame()` : jeu **synthétique** de 80 lignes conforme au dictionnaire, sans aucune anomalie ; `write_csv()` l'écrit au format de la source |
| `tests/test_data_quality.py` | 45 | Un test par comportement : on part du jeu valide, on **injecte** une anomalie, on vérifie qu'elle est détectée — et elle seule |
| `tests/test_data_quality_integration.py` | 5 | Pipeline complet (audit → exports → rapport), CLI, catalogue, et un test sur le vrai fichier (ignoré s'il est absent) |

Exemples de vérifications : valeurs manquantes natives et déguisées distinguées, doublons exacts
signalés une seule fois, note 250 → CRITICAL avec la valeur originale conservée, inflation
négative **non** signalée, note nulle sans UE validée **non** signalée, valeur atypique mais
dans le domaine → « valeur atypique » et non erreur, dispersion nulle gérée, fichier vide →
erreur explicite, DataFrame d'entrée **inchangé** après l'audit, fichier source **inchangé**
(empreinte SHA-256 comparée), rapport sans identifiant.

Le vrai CSV n'est pas utilisé par les tests unitaires : il n'est pas redistribuable, et un jeu
synthétique permet de savoir exactement quelles anomalies on attend.

---

## 9. Notions statistiques utilisées

| Notion | Définition simple | Utilisée dans |
|---|---|---|
| **IQR** (écart interquartile) | Q3 − Q1 : largeur des 50 % centraux ; robuste aux extrêmes | atypiques univariés |
| **Z-score** | (x − moyenne) / écart-type ; sensible aux extrêmes, pensé pour des distributions symétriques | atypiques (si asymétrie ≤ 1) |
| **MAD** | médiane des écarts absolus à la médiane ; version robuste de l'écart-type | Z-score modifié |
| **Z-score modifié** | 0,6745 × (x − médiane) / MAD ; seuil 3,5 (Iglewicz & Hoaglin) | atypiques univariés |
| **Asymétrie** (skewness) | > 0 : longue queue à droite (ex. âge) | choix de la méthode, échelle log |
| **log1p** | ln(1 + x) : resserre la queue droite, accepte 0 | variables asymétriques |
| **Coefficient phi** | corrélation entre deux variables 0/1 | manques associés |
| **Pearson / Spearman** | corrélation linéaire / corrélation des rangs (monotone) | redondances |
| **V de Cramér** | association entre qualitatives, de 0 à 1 | redondances, fuite |
| **Rapport de corrélation η** | part de la variance d'une numérique expliquée par une qualitative (racine) | niveau du dossier, fuite |
| **Khi-deux** | test d'indépendance entre deux qualitatives | manques informatifs |
| **Dépendance fonctionnelle** | la valeur de A suffit à connaître B | redondances |
| **Isolation Forest** | isole les points par coupures aléatoires ; un point isolé vite est atypique | multivarié |
| **LOF** | compare la densité autour d'un point à celle de ses voisins | multivarié |

---

## 10. Questions probables en soutenance

**Pourquoi lire le CSV en texte et pas directement avec `pd.read_csv` ?**
Pour voir les valeurs exactement comme dans le fichier. Une lecture typée transforme `NA` en
NaN, fait disparaître la différence entre `120,0` et `120.0`, et lit toute une colonne en texte
à cause d'un seul `ND`.

**Pourquoi un registre de règles séparé des détecteurs ?**
La justification, la gravité et l'action d'une règle sont écrites une seule fois ; le
rapport et le catalogue les lisent au même endroit. Ajouter une règle = la déclarer, puis
l'utiliser.

**Pourquoi la gravité et le diagnostic sont-ils séparés ?**
Parce qu'un problème peut être grave mais incertain (note nulle avec des UE validées) ou certain
mais mineur (une majuscule en trop). Les mélanger ferait perdre l'une des deux informations.

**Pourquoi exclure les valeurs impossibles des contrôles croisés et statistiques ?**
Pour signaler une seule fois une même erreur, et pour que des valeurs comme 999 ne faussent pas
les quartiles ni les corrélations.

**Une valeur atypique est-elle une erreur ?**
Non. Un étudiant de 50 ans est rare mais plausible (voie « Plus de 23 ans »). C'est pour cela
que ces signalements sont en INFO ou MEDIUM avec le statut « valeur atypique », et que deux
méthodes doivent être d'accord.

**Pourquoi le Z-score n'est-il pas toujours appliqué ?**
Il suppose une distribution à peu près symétrique ; sur une variable asymétrique (âge), la
moyenne et l'écart-type sont tirés par la queue et les seuils n'ont plus de sens.

**Les statistiques de l'audit créent-elles une fuite de données ?**
Non, tant qu'elles restent descriptives. Elles sont calculées sur tout le fichier, donc elles ne
doivent pas servir de paramètres au prétraitement (imputation, bornage) : ceux-ci seront appris
dans des pipelines, sur la partie apprentissage de chaque pli. Le mode
`multivariate_fit_scope="train"` montre comment respecter la séparation quand une méthode
apprend des paramètres.

**Pourquoi une forte association avec la cible n'est-elle pas forcément une fuite ?**
La prédiction se fait en fin de S2 : les UE validées et les notes de S1/S2 sont connues à ce
moment-là. Leur lien fort avec le statut final est attendu. Une fuite, ce serait une information
connue seulement **après** la prédiction, ou calculée à partir de la cible.

**Que se passe-t-il si un détecteur plante ?**
L'erreur est journalisée et enregistrée dans `result.errors` ; les autres détecteurs continuent.
En ligne de commande, le code de retour est alors 1.

**Comment vérifier que l'audit ne modifie rien ?**
Deux tests le prouvent : le DataFrame passé à `run_audit` est comparé à une copie faite avant,
et l'empreinte SHA-256 du fichier source est comparée avant et après.
