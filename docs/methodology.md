# Méthodologie — protocole scientifique

> Ce document décrit le protocole **attendu** et les règles à respecter. Les décisions qui dépendent des
> données (traitement des doublons, variables retenues, métrique principale…) restent **ouvertes** jusqu'à
> l'audit et sont consignées dans [`decision_log.md`](decision_log.md) au moment où elles sont prises.

## 1. Problématique

Prédire, pour chaque étudiant, son statut académique à l'échéance normale de sa formation, à partir des
informations disponibles **à l'inscription et jusqu'à la fin du deuxième semestre**.

Question directrice de la SAÉ : *comment construire, à partir de données imparfaites et de classes
déséquilibrées, un modèle de classification fiable, interprétable et évalué selon une démarche
scientifique rigoureuse ?*

## 2. Cible

| Élément | Valeur |
|---|---|
| Variable | `statut_academique` |
| Type de tâche | Classification supervisée multiclasse (3 classes) |
| Classes | `Abandon`, `En cours`, `Diplômé` |
| Point de vigilance | Le déséquilibre éventuel des classes est à mesurer pendant l'audit (mission 1) |

Les modalités réellement présentes dans le fichier doivent être comparées aux trois classes attendues
(orthographe, accents, espaces, casse).

## 3. Unité statistique et identifiants

- L'unité statistique est l'**étudiant**, identifié par `id_etudiant` (identifiant administratif fictif).
- `id_etudiant` n'est **jamais** une variable explicative : il sert uniquement aux contrôles.
- L'audit doit déterminer s'il existe des **doublons exacts** et des **identifiants répétés** avec des
  valeurs différentes. La stratégie retenue doit être justifiée :
  - dédoublonnage (si les répétitions sont des copies d'un même enregistrement) ;
  - ou découpage groupé stratifié (par exemple `StratifiedGroupKFold`) si plusieurs lignes légitimes
    concernent un même étudiant.
- Contrôle obligatoire : aucun `id_etudiant` commun entre apprentissage et test, ni entre apprentissage
  et validation dans chacun des 5 plis.

## 4. Séparation apprentissage / test

| Paramètre | Valeur | Source |
|---|---|---|
| Proportions | 80 % apprentissage / 20 % test | Imposé |
| Stratification | Sur `statut_academique` | Imposé |
| Graine | `random_state = 42` | Imposé |
| Moment | Après le traitement des identifiants, **avant** tout traitement appris | Imposé |

Le jeu de test est mis de côté immédiatement. Il ne sert qu'**une seule fois**, pour évaluer le modèle final.

## 5. Prévention des fuites de données

| Type de fuite | Exemple | Prévention |
|---|---|---|
| Fuite par prétraitement | Imputation par la médiane calculée sur tout le jeu | Transformations dans un `Pipeline`, ajustées sur l'apprentissage du pli |
| Fuite par chevauchement | Un étudiant en apprentissage et en test | Contrôle des identifiants (section 3) |
| Fuite par sélection | Choix des hyperparamètres sur le test | Sélection uniquement sur les scores de validation croisée |
| Fuite temporelle / cible | Variable connue après la fin du S2 ou dérivée de la cible | Vérification de la disponibilité de chaque variable (dictionnaire) |
| Fuite par sélection de variables | Sélection fondée sur la corrélation à la cible calculée sur tout le jeu | Sélection justifiée métier, ou réalisée dans les plis |

## 6. Prétraitement

Deux catégories de traitements, à ne pas confondre :

1. **Nettoyage déterministe** (aucun paramètre estimé) : conversion de types, harmonisation des modalités,
   corrections d'incohérences justifiées. Applicable de façon identique à tous les ensembles.
2. **Transformations apprises** (paramètres estimés sur les données) : imputation, mise à l'échelle,
   encodage, sélection automatique. Intégrées à un `ColumnTransformer` / `Pipeline`, ajustées
   uniquement sur la partie apprentissage de chaque pli.

Exigences par algorithme (à confirmer et justifier en mission 3) :

| Algorithme | Mise à l'échelle | Encodage des catégorielles | Valeurs manquantes |
|---|---|---|---|
| KNN | Indispensable (distances) | Nécessaire | À imputer |
| CART | Inutile | Nécessaire dans scikit-learn | À vérifier selon la version |
| Random Forest | Inutile | Nécessaire dans scikit-learn | À vérifier selon la version |
| XGBoost | Inutile | Nécessaire (ou support natif à justifier) | Gérées nativement |

Chaque décision importante précise : **pourquoi** le traitement est nécessaire, **pourquoi** il a été
retenu, **quelles conséquences** il a sur les données.

## 7. Modèles

| Modèle | Rôle | Hyperparamètre obligatoire |
|---|---|---|
| Référence élémentaire (`DummyClassifier`, classe majoritaire du jeu d'apprentissage) | Plancher de performance | — |
| K-Nearest Neighbors | Méthode à base de distances | Nombre de voisins |
| Arbre de décision (CART) | Modèle interprétable | Profondeur maximale |
| Random Forest | Ensemble par bagging | Nombre d'arbres |
| XGBoost | Ensemble par boosting | Nombre d'itérations de boosting |

Tous les modèles stochastiques utilisent `random_state = 42`. XGBoost attend une cible encodée en
entiers : l'encodage doit être reproductible et réversible.

## 8. Validation croisée

- `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)` sur le **jeu d'apprentissage uniquement**
  (ou équivalent groupé si la décision de la section 3 l'exige).
- Les plis sont générés **une seule fois** et réutilisés pour **toutes** les configurations.
- Pour chaque configuration : score de chaque pli, moyenne, écart-type, et score d'apprentissage pour
  diagnostiquer le sur-apprentissage.

## 9. Optimisation des hyperparamètres

- **Boucles explicites** sur les valeurs testées ; `GridSearchCV` est interdit.
- Les grilles sont justifiées (ordre de grandeur, taille du jeu, coût de calcul).
- Pour chaque hyperparamètre : tableau des valeurs, scores moyens, variabilité entre plis, graphique,
  interprétation.

## 10. Métrique principale et sélection du modèle

Métriques calculées : Accuracy, Precision, Recall, F1-score par classe, F1 macro, F1 pondéré, matrice
de confusion.

La métrique principale est **choisie et justifiée avant l'optimisation**, en tenant compte du
déséquilibre des classes. Le **F1-score macro** est une candidate envisageable (poids égal pour chaque
classe), mais la décision définitive dépend de l'audit et du coût des erreurs dans le contexte étudié.

Sélection : modèle dont le score moyen de validation est le meilleur selon la métrique principale,
en tenant compte de la variabilité entre plis (deux scores dont l'écart est inférieur à la dispersion
ne sont pas réellement distinguables). Le modèle retenu est ensuite **réentraîné sur l'intégralité du
jeu d'apprentissage**.

## 11. Évaluation finale

- Une **seule** évaluation du modèle retenu sur le jeu de test, en fin de projet.
- Aucune décision (modèle, hyperparamètre, variable, seuil) ne doit être prise après avoir vu ce score.
- Analyse par classe et matrice de confusion ; réponse aux cinq questions de la mission 5.

## 12. Interprétation

- Importance des variables d'au moins un modèle à arbres ; comparaison entre modèles si plusieurs.
- L'importance par impureté favorise les variables continues ou à nombreuses modalités : la compléter
  si possible par l'importance par permutation calculée sur des données non utilisées pour l'entraînement.
- **Importance prédictive ≠ causalité** : une variable importante est associée à la prédiction, elle n'en
  est pas la cause.

## 13. Limites et précautions éthiques

- Données partiellement **simulées** pour l'exercice (dictionnaire des variables) : les conclusions ne se
  transposent pas à une population réelle.
- Variables socio-économiques (bourse, dette, frais de scolarité) : risque de reproduire ou d'amplifier
  des inégalités ; risque de stigmatisation.
- Un modèle prédictif ne doit pas fonder seul une décision individuelle concernant un étudiant.
- Le modèle est réalisé dans un **cadre pédagogique** et ne constitue **pas** un outil de décision
  opérationnel.
