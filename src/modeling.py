"""Construction des modèles de classification — Mission 3.

Squelette documenté : aucune fonction n'est encore implémentée.

Responsabilités prévues
-----------------------
- Référence élémentaire : classe majoritaire du jeu d'apprentissage
  (``DummyClassifier(strategy="most_frequent")``).
- Modèles de référence en configuration simple :
  KNN, arbre de décision (CART), Random Forest, XGBoost.
- Assemblage de chaque modèle avec le prétraitement adapté dans un ``Pipeline``
  (ex. mise à l'échelle indispensable pour KNN, inutile pour les arbres).
- ``random_state = config.RANDOM_STATE`` pour tous les modèles stochastiques.

Points d'attention
------------------
- XGBoost attend des étiquettes entières : encoder la cible de façon
  reproductible (ordre ``config.TARGET_CLASSES``) et décoder les prédictions.
"""
