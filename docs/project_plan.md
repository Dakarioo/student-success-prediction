# Plan de projet — SAÉ 5.03 Data Mining

> Document de pilotage du binôme. Les noms sont remplacés par `Membre 1` et `Membre 2` tant qu'ils ne
> sont pas renseignés. Aucune échéance n'est inventée : les dates seront ajoutées à partir du calendrier
> officiel communiqué par l'établissement.

## 1. Présentation générale

**Student Success Prediction** vise à prédire le statut académique d'un étudiant (`Abandon`, `En cours`,
`Diplômé`) à l'échéance normale de sa formation, à partir des informations disponibles à l'inscription
et jusqu'à la fin du deuxième semestre. Le projet suit un processus de Data Mining complet, de l'audit
des données à la recommandation, dans un cadre pédagogique.

## 2. Périmètre

| Inclus | Exclu |
|---|---|
| Audit, prétraitement, classification supervisée multiclasse | Mise en production, API, application web, dashboard |
| Référence élémentaire + KNN, CART, Random Forest, XGBoost | Algorithmes supplémentaires non justifiés |
| Validation croisée stratifiée, boucles explicites d'optimisation | `GridSearchCV`, recherche automatique non demandée |
| Interprétation (importance des variables), recommandations | Inférence causale |
| Notebook final unique + synthèse décisionnelle | Outillage MLOps (MLflow, DVC, Docker, CI/CD complexe) |

## 3. Objectifs

1. Garantir et documenter la qualité des données exploitées.
2. Construire un protocole de validation sans fuite de données, respectant les contraintes imposées.
3. Comparer rigoureusement les modèles selon une métrique principale choisie et justifiée à l'avance.
4. Interpréter les résultats sans confondre importance prédictive et causalité.
5. Communiquer clairement auprès d'un public technique (notebook) et non technique (synthèse).
6. Permettre à chaque membre de justifier et de modifier n'importe quelle partie du code (évaluation individuelle).

## 4. Livrables officiels

| Livrable | Fichier | Public |
|---|---|---|
| 1 — Notebook Jupyter unique, documenté, entièrement exécutable | `notebooks/SAE5_03_Data_Mining.ipynb` | Personne extérieure au projet |
| 2 — Synthèse décisionnelle | `reports/executive_summary.md` (export au format demandé à la remise) | Responsable non spécialiste du Machine Learning |

Les notebooks de `notebooks/development/` sont des espaces de travail et **ne sont pas** des livrables.

## 5. Les six missions

| Mission | Intitulé | Notebook de développement | Module principal |
|---|---|---|---|
| 1 | Exploration et audit de la qualité des données | `01_data_audit.ipynb` | `src/audit.py` |
| 2 | Prétraitement et préparation des données | `02_preprocessing.ipynb` | `src/preprocessing.py` |
| 3 | Construction des modèles de classification | `03_modeling.ipynb` | `src/modeling.py` |
| 4 | Validation croisée et ajustement des hyperparamètres | `04_cross_validation.ipynb` | `src/validation.py` |
| 5 | Évaluation et interprétation des performances | `05_evaluation.ipynb` | `src/evaluation.py` |
| 6 | Interprétation du modèle et recommandations | `06_interpretation.ipynb` | `src/interpretation.py` |

**Ordre logique.** Le protocole de validation (métrique principale, séparation, plis, contrôle des
identifiants) est défini **après l'audit et avant tout traitement appris**, même s'il est rattaché
officiellement à la mission 4.

## 6. Décomposition en tâches et dépendances

Les charges horaires ne sont pas estimées à ce stade : elles seront renseignées par le binôme si besoin.
La répartition est une **proposition** à valider ensemble ; chaque tâche est relue par l'autre membre.

| ID | Tâche | Milestone | Priorité | Dépend de | Responsable proposé | Relecteur | Critère d'acceptation | Statut |
|---|---|---|---|---|---|---|---|---|
| T00 | Valider la structure, premier commit, dépôt GitHub public | M0 Initialisation | Haute | — | Membre 1 | Membre 2 | Dépôt public créé sans données ni PDF, les deux membres ont accès en écriture | À faire |
| T01 | Structure générale et rôle des variables (1.1, 1.2) | M1 Audit | Haute | T00 | Membre 1 | Membre 2 | Tableau variable / type / rôle confronté au dictionnaire | À faire |
| T02 | Distributions et répartition des classes (1.3, 1.4) | M1 Audit | Haute | T00 | Membre 2 | Membre 1 | Graphiques et effectifs par classe commentés | À faire |
| T03 | Qualité : manquants, doublons, identifiants, domaines, cohérence (1.5) | M1 Audit | Haute | T01 | Membre 1 | Membre 2 | Chaque anomalie chiffrée et localisée | À faire |
| T04 | Relations et redondances (1.6) | M1 Audit | Moyenne | T01 | Membre 2 | Membre 1 | Redondances identifiées et justifiées | À faire |
| T05 | Difficultés et rapport d'audit synthétique (1.7, 1.8) | M1 Audit | Haute | T02, T03, T04 | Membre 1 et 2 | Les deux | Tableau problème / diagnostic / conséquence / solution | À faire |
| T06 | Choix et justification de la métrique principale | M2 Protocole | Haute | T02 | Membre 1 et 2 | Les deux | Décision consignée dans `decision_log.md` | À faire |
| T07 | Protocole : identifiants, séparation 80/20, 5 plis, contrôles (`src/validation.py`) | M2 Protocole | Haute | T03, T06 | Membre 2 | Membre 1 | Assertions de non-chevauchement réussies | À faire |
| T08 | Nettoyage déterministe (2.1) | M3 Prétraitement | Haute | T05 | Membre 1 | Membre 2 | Chaque correction justifiée | À faire |
| T09 | Sélection des variables (2.2) | M3 Prétraitement | Haute | T05 | Membre 2 | Membre 1 | Liste justifiée (métier, redondance, fuite) | À faire |
| T10 | Pipelines de transformation et bilan avant/après (2.3, 2.4) | M3 Prétraitement | Haute | T07, T08, T09 | Membre 1 | Membre 2 | Aucun `fit` hors apprentissage | À faire |
| T11 | Principe des algorithmes (3.1) | M4 Modélisation | Moyenne | T00 | Membre 2 | Membre 1 | Tableau principe / traitements / avantages / limites | À faire |
| T12 | Référence élémentaire et modèles simples sur les mêmes plis (3.2 à 3.4) | M4 Modélisation | Haute | T10 | Membre 2 | Membre 1 | Tableau moyenne ± écart-type | À faire |
| T13 | Optimisation KNN et CART par boucles explicites (4.1, 4.2) | M5 Optimisation | Haute | T12 | Membre 1 | Membre 2 | Grilles justifiées, courbes, interprétation | À faire |
| T14 | Optimisation Random Forest et XGBoost (4.3, 4.4) | M5 Optimisation | Haute | T12 | Membre 2 | Membre 1 | Grilles justifiées, courbes, interprétation | À faire |
| T15 | Sélection et réentraînement du modèle final (4.5) | M5 Optimisation | Haute | T13, T14 | Membre 1 et 2 | Les deux | Choix argumenté selon la métrique principale | À faire |
| T16 | Synthèse de validation croisée et sensibilité à la métrique (5.1, 5.2) | M6 Évaluation | Haute | T15 | Membre 1 | Membre 2 | Tableau de synthèse complet | À faire |
| T17 | Évaluation finale sur le test, matrice de confusion, questions (5.3 à 5.5) | M6 Évaluation | Haute | T15 | Membre 2 | Membre 1 | Test utilisé une seule fois ; 5 questions traitées | À faire |
| T18 | Importance des variables et interprétation (6.1 à 6.3) | M7 Interprétation | Haute | T17 | Membre 1 | Membre 2 | Distinction prédiction / causalité explicite | À faire |
| T19 | Recommandation, limites, conclusion (6.4) | M7 Interprétation | Haute | T18 | Membre 2 | Membre 1 | Recommandation argumentée et prudente | À faire |
| T20 | Intégration et réexécution complète du notebook final | M8 Livraison | Haute | T05, T10, T16, T17, T19 | Intégrateur désigné | Autre membre | *Restart & Run All* sans erreur | À faire |
| T21 | Synthèse décisionnelle | M8 Livraison | Haute | T19 | Membre 1 et 2 | Les deux | Compréhensible par un non-spécialiste | À faire |
| T22 | Vérifications finales et remise sur Moodle | M8 Livraison | Haute | T20, T21 | Membre 1 et 2 | Les deux | Checklist finale (section 11) cochée | À faire |

**Chemin critique :** T00 → T01 → T03 → T05 → T08/T09 → T10 → T12 → T13/T14 → T15 → T17 → T18 → T19 → T20 → T22.

## 7. Responsabilités proposées

| Rôle | Membre 1 | Membre 2 |
|---|---|---|
| Missions principales | Audit qualité, nettoyage, pipelines, KNN / CART, interprétation | Distributions, protocole, sélection des variables, modélisation, RF / XGBoost, évaluation finale |
| Intégration dans le notebook final | En alternance, par mission (voir `docs/collaboration.md`) | En alternance, par mission |
| Relecture | Tout le travail de Membre 2 | Tout le travail de Membre 1 |

Les deux membres doivent maîtriser **toutes** les étapes : l'évaluation est individuelle (écrit, oral
et/ou soutenance).

## 8. Critères de validation par mission

| Mission | Critère de validation |
|---|---|
| 1 | Rapport d'audit synthétique complet ; toute modification envisagée est justifiée |
| 2 | Bilan avant / après ; transformations apprises intégrées à des pipelines |
| 3 | Référence élémentaire + 4 algorithmes comparés sur les mêmes plis |
| 4 | Hyperparamètres obligatoires étudiés par boucles explicites ; moyenne et variabilité présentées |
| 5 | Toutes les métriques demandées ; tableau de synthèse ; évaluation unique sur le test ; 5 questions traitées |
| 6 | Importance des variables d'au moins un modèle à arbres ; recommandation argumentée ; limites |

## 9. Risques techniques et méthodologiques

| Risque | Impact | Prévention |
|---|---|---|
| Fuite de données (transformation ajustée avant la séparation) | Scores surestimés | Pipelines scikit-learn ; revue systématique (checklist PR) |
| Même étudiant dans plusieurs ensembles | Scores surestimés | Contrôle des `id_etudiant` avant et après séparation, et dans chaque pli |
| Utilisation du test pour choisir un modèle | Évaluation biaisée | Test isolé ; une seule évaluation, en fin de projet |
| Optimisation de l'Accuracy malgré le déséquilibre | Classes minoritaires mal reconnues | Métrique principale choisie et justifiée avant l'optimisation |
| Colonnes numériques lues comme texte (constaté à l'initialisation) | Erreurs de typage, analyses faussées | Diagnostic à l'audit, conversion justifiée |
| Variables redondantes signalées par le dictionnaire | Importances diluées, interprétation trompeuse | Analyse des redondances (mission 1) |
| Conflits Git sur le notebook final | Perte de travail | Notebooks de développement séparés, intégrateur unique |
| Écart d'environnement entre les deux ordinateurs | Résultats non reproductibles | `.venv` + `requirements.txt` ; graine fixée |
| Publication de données non autorisées | Problème juridique et éthique | Données exclues par `.gitignore` ; `publication_checklist.md` |
| Un membre ne maîtrise pas une partie | Note individuelle pénalisée | Relecture croisée obligatoire ; explication orale mutuelle |

## 10. Definition of Done

Une tâche est terminée lorsque :

- [ ] le code s'exécute de haut en bas dans un noyau neuf ;
- [ ] les fonctions réutilisables sont dans `src/`, documentées ;
- [ ] les paramètres proviennent de `src/config.py` ;
- [ ] aucune fuite de données n'est possible (vérifié par le relecteur) ;
- [ ] chaque résultat est accompagné d'une interprétation fondée sur les sorties réelles ;
- [ ] les décisions importantes sont consignées dans `docs/decision_log.md` ;
- [ ] `python -m pytest` et `python -m ruff check .` passent ;
- [ ] la Pull Request a été relue et approuvée par l'autre membre.

## 11. Checklist finale de livraison

- [ ] Notebook final exécuté intégralement (*Restart Kernel and Run All Cells*) sans erreur.
- [ ] Aucun chemin absolu ; seules les ressources prévues sont nécessaires.
- [ ] Les six missions sont traitées, y compris les questions de la mission 5.
- [ ] Toutes les interprétations correspondent aux sorties affichées.
- [ ] Le jeu de test n'a été utilisé qu'une seule fois.
- [ ] La synthèse décisionnelle est complète et compréhensible par un non-spécialiste.
- [ ] Les deux membres savent expliquer et modifier chaque partie du code.
- [ ] Les livrables sont déposés sur Moodle au format demandé.

## 12. Organisation du GitHub Project (à créer manuellement)

**Vue Kanban — colonnes :** `Backlog` → `Ready` → `In Progress` → `In Review` → `Done`.

| Colonne | Signification |
|---|---|
| Backlog | Tâche identifiée, pas encore prête |
| Ready | Dépendances satisfaites, critères d'acceptation clairs |
| In Progress | Branche créée, travail en cours |
| In Review | Pull Request ouverte, relecture par l'autre membre |
| Done | PR fusionnée dans `main`, branche supprimée |

**Champs personnalisés recommandés :**

| Champ | Type | Valeurs |
|---|---|---|
| Mission | Single select | 01-audit, 02-preprocessing, 03-modeling, 04-validation, 05-evaluation, 06-interpretation |
| Responsable | Assignees | Membre 1, Membre 2 |
| Relecteur | Text ou Single select | Membre 1, Membre 2 |
| Priorité | Single select | high, medium, low |
| Statut | Status (natif) | Colonnes du Kanban |

**Labels proposés :**

| Label | Couleur suggérée | Usage |
|---|---|---|
| `mission:01-audit` | `#1D76DB` | Mission 1 |
| `mission:02-preprocessing` | `#1D76DB` | Mission 2 |
| `mission:03-modeling` | `#1D76DB` | Mission 3 |
| `mission:04-validation` | `#1D76DB` | Mission 4 |
| `mission:05-evaluation` | `#1D76DB` | Mission 5 |
| `mission:06-interpretation` | `#1D76DB` | Mission 6 |
| `type:feature` | `#0E8A16` | Nouvelle analyse ou fonctionnalité |
| `type:bug` | `#D73A4A` | Erreur à corriger |
| `type:documentation` | `#0075CA` | Documentation |
| `type:research` | `#5319E7` | Recherche méthodologique, comparaison d'options |
| `priority:high` | `#B60205` | Bloquant pour la suite |
| `priority:medium` | `#FBCA04` | Important |
| `priority:low` | `#C2E0C6` | Amélioration facultative |
