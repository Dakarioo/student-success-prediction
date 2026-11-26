"""Protocole de validation et optimisation des hyperparamètres — Mission 4.

Squelette documenté : aucune fonction n'est encore implémentée.

Responsabilités prévues
-----------------------
- Séparation stratifiée 80 / 20 (``config.TEST_SIZE``, ``config.RANDOM_STATE``),
  réalisée avant tout traitement appris.
- Contrôle d'absence de chevauchement d'étudiants (``config.STUDENT_ID``) entre
  apprentissage et test, et entre apprentissage et validation de chaque pli.
- Définition UNIQUE des 5 plis stratifiés (``config.N_SPLITS``) sur le jeu
  d'apprentissage, réutilisés pour toutes les configurations.
- Boucles explicites sur les hyperparamètres (``GridSearchCV`` interdit) :
  nombre de voisins (KNN), profondeur maximale (CART), nombre d'arbres
  (Random Forest), nombre d'itérations de boosting (XGBoost).
- Collecte des scores par pli (apprentissage et validation) pour calculer
  moyenne et écart-type.

Règles
------
- Le jeu de test n'intervient ni dans le prétraitement appris, ni dans la
  sélection des modèles ou des hyperparamètres.
- Si un même étudiant apparaît plusieurs fois, la stratégie (dédoublonnage ou
  découpage groupé stratifié) est décidée après l'audit et consignée dans
  ``docs/decision_log.md``.
"""
