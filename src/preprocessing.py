"""Nettoyage et transformations — Mission 2.

Squelette documenté : aucune fonction n'est encore implémentée.

Responsabilités prévues
-----------------------
1. Nettoyage déterministe, sans paramètre appris (applicable avant la séparation
   apprentissage / test) : conversion de types, harmonisation des modalités,
   correction d'incohérences justifiées, traitement des doublons.
2. Transformations apprises (imputation, mise à l'échelle, encodage) :
   construites sous forme de ``ColumnTransformer`` / ``Pipeline`` scikit-learn,
   ajustées UNIQUEMENT sur la partie apprentissage de chaque pli, puis sur
   l'intégralité du jeu d'apprentissage pour le modèle final.
3. Sélection des variables explicatives, justifiée par le sens métier et
   l'audit (et non uniquement par des critères statistiques).

Règles
------
- Ne jamais écraser ``data/raw/`` ; les sorties éventuelles vont dans
  ``data/interim/`` ou ``data/processed/``.
- Aucun ``fit`` sur l'ensemble des données avant la séparation.
- Chaque décision importante est justifiée dans ``docs/decision_log.md``.
"""
