"""Harmonisation des visualisations — toutes missions.

Squelette documenté : aucune fonction n'est encore implémentée.

Responsabilités prévues
-----------------------
- Thème graphique commun (taille, police, grille) appliqué une fois en début
  de notebook.
- Palette constante pour les trois classes, dans l'ordre
  ``config.TARGET_CLASSES``, lisible par les personnes daltoniennes.
- Graphiques récurrents : distribution par classe, courbes de validation
  (moyenne ± écart-type par valeur d'hyperparamètre), matrice de confusion,
  importance des variables.
- Sauvegarde des figures destinées au rapport dans ``config.FIGURES_DIR``.

Règles
------
- Une figure répond à une question ; titre, axes et unités sont explicites.
- Aucune figure ne doit exposer de données individuelles d'étudiants.
"""
