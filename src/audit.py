"""Audit et qualité des données — Mission 1 (façade).

L'implémentation se trouve dans le paquet ``src.data_quality`` (un module par
famille de contrôles). Ce module conserve le point d'import historique prévu
à l'initialisation du projet, pour les notebooks ::

    from src.audit import run_audit, export_results
    result = run_audit()

Responsabilités couvertes
-------------------------
- Structure générale : dimensions, types lus, conformité au dictionnaire.
- Typage : colonnes numériques lues comme texte et valeurs responsables.
- Valeurs manquantes : natives, déguisées, par variable, par observation, par classe.
- Doublons : lignes identiques et identifiants ``id_etudiant`` répétés.
- Domaines : valeurs hors du domaine décrit dans le dictionnaire.
- Cohérence entre variables (UE validées ≤ UE inscrites, âges, exports…).
- Valeurs atypiques univariées et (optionnellement) multivariées.
- Redondances (``note_admission`` / ``note_admission_archive``,
  ``age_inscription`` / ``age_inscription_mois``, ``niveau_dossier``).
- Risques de fuite et répartition des classes de la cible.

Règles
------
- Les fonctions retournent des diagnostics (DataFrame, dictionnaires) et ne
  modifient jamais le DataFrame reçu.
- Les décisions qui découlent de l'audit sont consignées dans
  ``docs/decision_log.md``.
"""

from src.data_quality import (
    AuditConfig,
    AuditResult,
    available_checks,
    compare_audits,
    export_results,
    rules_frame,
    run_audit,
    run_detector,
)

__all__ = [
    "AuditConfig",
    "AuditResult",
    "available_checks",
    "compare_audits",
    "export_results",
    "rules_frame",
    "run_audit",
    "run_detector",
]
