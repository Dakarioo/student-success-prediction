## Description des modifications

<!-- Ce que cette Pull Request apporte, en quelques phrases. -->

## Issue associée

Closes #<!-- numéro -->

## Mission concernée

<!-- Mission 1 à 6, sous-partie, ou « Transverse ». -->

## Fichiers modifiés

<!-- Liste des fichiers principaux et de leur rôle. -->

- 

## Justification des décisions

<!-- Pourquoi ces choix ? Lien vers les entrées de docs/decision_log.md. -->

## Tests effectués

- [ ] `python -m pytest`
- [ ] `python -m ruff check .`
- [ ] *Restart Kernel and Run All Cells* sur les notebooks modifiés
- [ ] Autre : 

## Impact méthodologique

<!-- Les résultats précédents changent-ils ? Faut-il mettre à jour le notebook final ? -->

## Vérification des risques de fuite de données

- [ ] Aucune transformation apprise n'est ajustée avant la séparation apprentissage / test.
- [ ] En validation croisée, les transformations sont ajustées sur la partie apprentissage de chaque pli (pipeline).
- [ ] Aucun étudiant commun entre les ensembles ni entre apprentissage et validation d'un pli.
- [ ] Le jeu de test n'a servi à aucune décision (modèle, hyperparamètre, variable).
- [ ] Aucune variable indisponible à la fin du semestre 2 ou dérivée de la cible.

## Vérification des données sensibles

- [ ] Aucun fichier de données, PDF pédagogique ou modèle entraîné n'est commité.
- [ ] Aucune ligne individuelle d'étudiant dans les sorties des notebooks.
- [ ] Aucun secret ni chemin absolu personnel.

## Checklist de relecture

- [ ] Le code est lisible, documenté et respecte les conventions du projet.
- [ ] Les fonctions réutilisables sont dans `src/`.
- [ ] Les interprétations correspondent aux sorties réellement affichées.
- [ ] Le relecteur est capable d'expliquer l'ensemble des modifications.
