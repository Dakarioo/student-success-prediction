# Guide de contribution

Ce guide décrit le fonctionnement collaboratif du binôme. Il reste volontairement simple.
Les rôles, la revue et l'intégration dans le notebook final sont détaillés dans
[`docs/collaboration.md`](docs/collaboration.md).

## 1. Branches

### Branche principale : `main`

`main` contient **uniquement des versions validées** : code exécutable, relu par l'autre membre.
On ne travaille jamais directement sur `main`.

### Branches de travail : une branche par tâche

Les branches sont **temporaires et liées à une tâche**, pas à une personne. Elles sont supprimées après fusion.

| Préfixe | Usage | Exemples |
|---|---|---|
| `feature/` | Nouvelle analyse ou fonctionnalité | `feature/data-audit`, `feature/data-cleaning`, `feature/preprocessing`, `feature/knn`, `feature/cart`, `feature/random-forest`, `feature/xgboost`, `feature/cross-validation`, `feature/model-evaluation`, `feature/model-interpretation` |
| `fix/` | Correction d'un problème | `fix/data-leakage` |
| `docs/` | Documentation, intégration au notebook final | `docs/executive-summary` |

Noms en anglais, en minuscules, avec des tirets.

## 2. Workflow

```powershell
# 1. Récupérer la dernière version de main
git switch main
git pull origin main

# 2. Créer une branche dédiée à la tâche
git switch -c feature/data-audit

# 3. Réaliser les modifications (notebook de développement, src/, docs/)

# 4. Vérifier leur fonctionnement
python -m pytest
python -m ruff check .
#    + Restart Kernel and Run All Cells sur les notebooks modifiés

# 5. Créer des commits explicites
git add src/audit.py notebooks/development/01_data_audit.ipynb
git commit -m "feat: add missing values analysis"

# 6. Pousser la branche sur GitHub
git push -u origin feature/data-audit
```

7. Créer une **Pull Request** vers `main` sur GitHub (le modèle se remplit automatiquement).
8. Faire **relire** le travail par le second membre.
9. **Corriger** les éventuels problèmes par de nouveaux commits sur la même branche.
10. **Fusionner** dans `main` après approbation.
11. **Supprimer** la branche devenue inutile :

```powershell
git switch main
git pull origin main
git branch -d feature/data-audit
```

> Utiliser `git add <fichiers>` plutôt que `git add .` pour éviter de commiter un fichier non prévu.

## 3. Convention de commits

Format inspiré de [Conventional Commits](https://www.conventionalcommits.org/) : `type: description`
(description courte, en anglais, à l'impératif, sans point final).

| Type | Usage | Exemple |
|---|---|---|
| `feat` | Nouvelle analyse, fonction ou fonctionnalité | `feat: add missing values analysis` |
| `fix` | Correction d'un bug ou d'une erreur méthodologique | `fix: prevent data leakage` |
| `docs` | Documentation, Markdown, interprétations | `docs: document preprocessing choices` |
| `refactor` | Restructuration du code sans changement de résultat | `refactor: simplify validation pipeline` |
| `test` | Ajout ou modification de tests | `test: verify student identifiers` |
| `chore` | Maintenance, configuration, dépendances | `chore: initialize project structure` |

Un commit = une modification cohérente. Éviter les messages vagues (`update`, `wip`, `modifs`).

## 4. Règles pour les notebooks Jupyter

- **Ne jamais modifier simultanément** le notebook final `notebooks/SAE5_03_Data_Mining.ipynb`.
- Développer chaque mission dans son notebook de `notebooks/development/`.
- Centraliser les fonctions réutilisables dans `src/` (un module par responsabilité).
- Un **responsable temporaire de l'intégration** reporte le travail validé dans le notebook final.
- Chaque mission est **relue par l'autre membre** avant intégration.
- Éviter les commits contenant des sorties volumineuses ou inutiles (tableaux complets, lignes
  individuelles d'étudiants, longs logs).
- Conserver les résultats utiles (tableaux de synthèse, figures commentées) dans la version finale
  destinée à la présentation.
- Avant de commiter un notebook : *Restart Kernel and Run All Cells*, pour vérifier l'exécution de haut en bas.

## 5. Règles sur les données

- Ne **jamais** modifier ni écraser `data/raw/`.
- Ne **jamais** commiter de données, de PDF pédagogiques ou de modèles entraînés (exclus par `.gitignore`).
- Toujours charger les données via `src.data_loader.load_raw_data()` et utiliser les chemins de `src/config.py`.

## 6. Qualité du code

- PEP 8, vérifié par `python -m ruff check .`.
- Noms de fichiers, modules et fonctions en anglais ; commentaires et documentation en français ;
  noms originaux des variables du jeu de données conservés.
- Docstrings claires, typage lorsqu'il clarifie, erreurs explicites.
- Toute décision méthodologique est consignée dans [`docs/decision_log.md`](docs/decision_log.md).

## 7. Maîtrise partagée

L'évaluation est **individuelle**. Les deux membres doivent comprendre l'ensemble du code et des décisions,
même si les tâches sont réparties. Une Pull Request n'est approuvée que si le relecteur peut expliquer
le travail.
