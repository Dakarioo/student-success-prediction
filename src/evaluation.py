"""Calcul des métriques et comparaison des modèles — Mission 5.

Squelette documenté : aucune fonction n'est encore implémentée.

Responsabilités prévues
-----------------------
- Métriques : Accuracy, Precision, Recall, F1-score par classe, F1 macro,
  F1 pondéré, matrice de confusion (ordre des classes : ``config.TARGET_CLASSES``).
- Tableau de synthèse des scores de validation croisée (moyenne ± écart-type)
  pour la référence élémentaire et les quatre algorithmes.
- Évaluation finale UNIQUE du modèle retenu sur le jeu de test.

Règles
------
- La métrique principale est choisie et justifiée AVANT l'ajustement des
  hyperparamètres (voir ``docs/methodology.md``).
- Une Accuracy élevée ne suffit pas : toujours examiner les scores par classe.
"""
