"""Audit et qualité des données — Mission 1.

Squelette documenté : aucune fonction n'est encore implémentée.

Responsabilités prévues
-----------------------
- Structure générale : dimensions, types lus, mémoire.
- Typage : détection des colonnes numériques lues comme texte et de leur cause.
- Valeurs manquantes : volume par variable et par classe.
- Doublons : lignes identiques et identifiants ``id_etudiant`` répétés.
- Domaines : valeurs hors du domaine décrit dans le dictionnaire des variables
  (notes sur 200 ou sur 20, entiers non négatifs, modalités attendues).
- Cohérence entre variables (ex. UE validées <= UE inscrites, S1 / S2).
- Redondances (ex. ``note_admission`` / ``note_admission_archive``,
  ``age_inscription`` / ``age_inscription_mois``).
- Répartition des classes de la cible.

Règles
------
- Les fonctions retournent des diagnostics (DataFrame, dictionnaires) et ne
  modifient jamais le DataFrame reçu.
- Les décisions qui découlent de l'audit sont consignées dans
  ``docs/decision_log.md``.
"""
