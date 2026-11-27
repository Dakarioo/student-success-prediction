# Student Success Prediction — SAÉ 5.03 Data Mining

**Prédire le statut académique d'un étudiant (Abandon, En cours, Diplômé) à l'échéance normale de sa
formation, à partir des informations disponibles jusqu'à la fin du deuxième semestre.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.x-150458?logo=pandas&logoColor=white)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.8%2B-F7931E?logo=scikitlearn&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-3.x-189FDD)
![Statut](https://img.shields.io/badge/statut-en%20cours-lightgrey)

> **Projet pédagogique en cours de réalisation.** Aucun résultat n'est encore disponible. Le modèle
> produit ne constitue pas un outil de décision académique opérationnel.

---

## Sommaire

- [Contexte universitaire](#contexte-universitaire)
- [Problématique](#problématique)
- [Objectifs](#objectifs)
- [Jeu de données](#jeu-de-données)
- [Démarche Data Mining](#démarche-data-mining)
- [Protocole de validation](#protocole-de-validation)
- [Architecture du projet](#architecture-du-projet)
- [Installation](#installation)
- [Exécution du notebook](#exécution-du-notebook)
- [Audit automatique de la qualité des données](#audit-automatique-de-la-qualité-des-données)
- [Reproductibilité](#reproductibilité)
- [Organisation collaborative](#organisation-collaborative)
- [Avancement](#avancement)
- [Résultats](#résultats)
- [Limites et précautions éthiques](#limites-et-précautions-éthiques)
- [Auteurs](#auteurs)
- [Conditions de publication et d'utilisation](#conditions-de-publication-et-dutilisation)

## Contexte universitaire

Projet réalisé en binôme dans le cadre de la **SAÉ 5.03 — Mise en œuvre d'un processus de Data Mining**
du **BUT 3 Sciences des Données** (année universitaire 2026–2027). L'évaluation est individuelle
(écrit, oral et/ou soutenance) : chaque membre maîtrise l'ensemble du code et des choix méthodologiques.

## Problématique

Un établissement d'enseignement supérieur souhaite mieux comprendre les parcours académiques de ses
étudiants afin d'améliorer ses dispositifs d'accompagnement et d'aide à la réussite.

> *Comment construire, à partir de données imparfaites et de classes déséquilibrées, un modèle de
> classification fiable, interprétable et évalué selon une démarche scientifique rigoureuse ?*

## Objectifs

- Auditer et garantir la qualité des données exploitées.
- Construire un protocole de validation rigoureux, sans fuite de données.
- Comparer une référence élémentaire et quatre algorithmes de classification.
- Évaluer la reconnaissance de **chaque** classe, au-delà de l'Accuracy.
- Interpréter les facteurs associés au parcours académique, sans conclure à une causalité.
- Formuler une recommandation argumentée à destination de l'établissement.

## Jeu de données

| Élément | Description |
|---|---|
| Fichier | `parcours_etudiants.csv` — export administratif et pédagogique préparé pour l'exercice |
| Dimensions | 4 504 lignes × 33 colonnes |
| Format | CSV, séparateur virgule, UTF-8 avec BOM |
| Familles de variables | Inscription et parcours antérieur, situation administrative, contexte économique, résultats des semestres 1 et 2, métadonnées d'export |
| Accès | Fourni sur Moodle ; **non redistribué** dans ce dépôt (voir [`data/README.md`](data/README.md)) |

Documentation détaillée : [`docs/data_dictionary.md`](docs/data_dictionary.md).

### Variable cible

`statut_academique`, classification multiclasse :

| Classe | Signification |
|---|---|
| Abandon | L'étudiant a interrompu sa formation |
| En cours | L'étudiant est encore inscrit à l'échéance normale de la formation |
| Diplômé | L'étudiant a obtenu son diplôme |

## Démarche Data Mining

| Mission | Contenu |
|---|---|
| 1. Exploration et audit | Structure, distributions, classes, qualité, cohérence, redondances, rapport d'audit |
| 2. Prétraitement | Nettoyage justifié, sélection des variables, transformations en pipelines |
| 3. Modélisation | Référence élémentaire et quatre algorithmes en configuration simple |
| 4. Validation croisée et optimisation | Boucles explicites sur les hyperparamètres, sélection du modèle final |
| 5. Évaluation | Métriques par classe, matrice de confusion, évaluation unique sur le test |
| 6. Interprétation et recommandations | Importance des variables, limites, recommandation |

### Algorithmes étudiés

| Algorithme | Hyperparamètre étudié |
|---|---|
| Référence élémentaire (classe majoritaire) | — |
| K-Nearest Neighbors | Nombre de voisins |
| Arbre de décision (CART) | Profondeur maximale |
| Random Forest | Nombre d'arbres |
| XGBoost | Nombre d'itérations de boosting |

## Protocole de validation

- Séparation **stratifiée 80 % / 20 %**, graine **42**, réalisée avant tout traitement appris.
- Aucun étudiant commun entre apprentissage et test, ni entre apprentissage et validation d'un pli.
- **Validation croisée stratifiée à 5 plis** sur le jeu d'apprentissage, plis identiques pour toutes les configurations.
- Transformations apprises intégrées à des **pipelines**, ajustées sur la partie apprentissage de chaque pli.
- Optimisation par **boucles explicites** (sans `GridSearchCV`).
- Métrique principale choisie et justifiée **avant** l'optimisation (le F1-score macro est une candidate).
- Jeu de test utilisé **une seule fois**, pour le modèle final.

Détails : [`docs/methodology.md`](docs/methodology.md).

## Architecture du projet

```text
.
├── .github/                  Modèles d'issues et de Pull Request
├── data/
│   ├── raw/                  Données originales, immuables (non versionnées)
│   ├── interim/              Données intermédiaires (non versionnées)
│   └── processed/            Données préparées (non versionnées)
├── notebooks/
│   ├── SAE5_03_Data_Mining.ipynb   Livrable 1 — notebook final unique
│   └── development/          Notebooks de travail par mission (non livrés)
├── src/                      Code réutilisable : config, chargement, audit, modèles…
│   └── data_quality/         Système d'audit et de détection des anomalies (mission 1)
├── tests/                    Tests unitaires (pytest)
├── docs/                     Plan, méthodologie, dictionnaire, décisions, collaboration
├── reports/
│   ├── figures/              Figures destinées au rapport
│   ├── tables/               Tableaux destinés au rapport
│   └── executive_summary.md  Livrable 2 — synthèse décisionnelle
├── models/                   Modèles entraînés (non versionnés)
├── outputs/                  Sorties temporaires (non versionnées)
├── requirements.txt          Dépendances
└── pyproject.toml            Configuration de Ruff et Pytest
```

### Stack technique

| Usage | Outils |
|---|---|
| Langage | Python ≥ 3.11 |
| Données | pandas, NumPy, SciPy |
| Visualisation | Matplotlib, seaborn |
| Machine Learning | scikit-learn, XGBoost |
| Notebooks | JupyterLab, Notebook, ipykernel, nbformat |
| Qualité | pytest, Ruff |
| Versionnement | Git, GitHub |

## Installation

Prérequis : Python 3.11 ou plus récent, Git. Commandes PowerShell (Windows), depuis la racine du dépôt :

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

```powershell
python -m pip install -r requirements.txt
```

> Si PowerShell refuse d'activer l'environnement (politique d'exécution), utilisez directement
> `.\.venv\Scripts\python.exe` à la place de `python`, sans modifier la configuration globale.

Placez ensuite `parcours_etudiants.csv` dans `data/raw/` (procédure : [`data/README.md`](data/README.md)).

## Exécution du notebook

```powershell
python -m jupyterlab
```

Ouvrez `notebooks/SAE5_03_Data_Mining.ipynb`, puis exécutez *Restart Kernel and Run All Cells*.
Les chemins sont relatifs à la racine du projet : aucune adaptation n'est nécessaire d'un ordinateur à l'autre.

Contrôles qualité :

```powershell
python -m pytest
python -m ruff check .
```

## Audit automatique de la qualité des données

Le paquet [`src/data_quality`](src/data_quality) audite le fichier brut et **signale** les
anomalies (structure, valeurs manquantes, doublons, formats, domaine métier, cohérence entre
variables, atypiques, redondances, fuite de données, déséquilibre des classes). Il ne corrige,
n'impute et ne supprime rien.

```powershell
python -m src.data_quality                      # audit complet
python -m src.data_quality --multivariate       # + Isolation Forest / LOF (facultatif)
python -m src.data_quality --help               # toutes les options
```

```python
from src.data_quality import run_audit, export_results
result = run_audit()
result.filter(min_severity="HIGH")
export_results(result)
```

Sorties : `outputs/audit/` (détail par observation, non versionné) et
[`reports/audit_qualite.md`](reports/audit_qualite.md) (rapport agrégé, sans identifiant).
Documentation : [`docs/data_quality_audit.md`](docs/data_quality_audit.md) · catalogue des
règles : [`docs/audit_rules_catalog.md`](docs/audit_rules_catalog.md).
Fonctionnement détaillé du code : [`docs/fonctionnement/`](docs/fonctionnement/).

## Reproductibilité

- Graine aléatoire unique (`42`) définie dans [`src/config.py`](src/config.py).
- Paramètres du protocole centralisés dans `src/config.py`.
- Dépendances bornées dans [`requirements.txt`](requirements.txt), environnement local `.venv`.
- Données brutes jamais modifiées ; transformations reproductibles par le code.
- Notebook final exécutable de haut en bas dans un noyau neuf.

## Organisation collaborative

- Branche `main` protégée, branches temporaires par tâche (`feature/…`, `fix/…`, `docs/…`).
- Pull Request relue par l'autre membre avant chaque fusion.
- Commits inspirés de Conventional Commits.
- Un notebook de développement par mission ; un intégrateur unique pour le notebook final.

Voir [`CONTRIBUTING.md`](CONTRIBUTING.md), [`docs/collaboration.md`](docs/collaboration.md) et
[`docs/project_plan.md`](docs/project_plan.md).

## Avancement

| Mission | Statut |
|---|---|
| Initialisation du projet | Structure créée |
| 1. Exploration et audit | En cours — système d'audit automatique implémenté et testé ; analyse et interprétation dans le notebook à réaliser |
| 2. Prétraitement | À démarrer |
| 3. Modélisation | À démarrer |
| 4. Validation croisée et optimisation | À démarrer |
| 5. Évaluation | À démarrer |
| 6. Interprétation et recommandations | À démarrer |
| Synthèse décisionnelle | À démarrer |

## Résultats

> **À compléter** après l'évaluation finale. Cette section présentera uniquement des résultats
> réellement obtenus : tableau de validation croisée (moyenne ± écart-type), performances du modèle
> retenu sur le jeu de test, matrice de confusion, principales variables associées aux prédictions.

## Limites et précautions éthiques

- Données en partie **simulées** pour l'exercice : les conclusions ne se transposent pas à une population réelle.
- Une variable importante pour le modèle est **associée** à la prédiction, elle n'en est pas la **cause**.
- Les variables socio-économiques (bourse, dette, frais de scolarité) exposent à un risque de
  reproduction d'inégalités et de stigmatisation.
- Une prédiction ne doit jamais fonder seule une décision concernant un étudiant.

## Auteurs

| Membre | Rôle | Contact |
|---|---|---|
| Membre 1 | *À compléter* | *À compléter* |
| Membre 2 | *À compléter* | *À compléter* |

## Conditions de publication et d'utilisation

- Travail **pédagogique**, réalisé dans le cadre du BUT Sciences des Données.
- Les données et les documents pédagogiques fournis par l'établissement **ne sont pas redistribués**.
- Aucune licence n'a encore été choisie : sauf mention contraire ultérieure, tous droits réservés aux auteurs.
  Le choix éventuel d'une licence se fera d'un commun accord, après vérification des droits applicables
  (voir [`docs/publication_checklist.md`](docs/publication_checklist.md)).
