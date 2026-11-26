"""Système d'audit et de détection des anomalies (Mission 1).

Le module détecte, documente et signale les anomalies : il ne corrige,
n'impute et ne supprime JAMAIS rien.

Utilisation rapide (notebook)::

    from src.data_quality import run_audit, export_results
    result = run_audit()                         # data/raw/parcours_etudiants.csv
    result.filter(min_severity="HIGH")           # signalements graves
    result.summary_by_rule()                     # synthèse par règle
    export_results(result)                       # outputs/audit/ + reports/audit_qualite.md

Terminal : ``python -m src.data_quality --help``.
"""

from src.data_quality.audit import (
    AuditResult,
    available_checks,
    filter_anomalies,
    run_audit,
    run_detector,
    severities_at_least,
)
from src.data_quality.comparison import AuditComparison, compare_audits
from src.data_quality.config import DEFAULT_CONFIG, VARIABLE_SPECS, AuditConfig
from src.data_quality.reporting import (
    export_results,
    quality_by_variable,
    summary_counts,
    synthesis_by_rule,
    write_report,
    write_rules_catalog,
)
from src.data_quality.rules import RULES, get_rule, rules_frame
from src.data_quality.schemas import Category, DiagnosticStatus, Severity

__all__ = [
    "DEFAULT_CONFIG",
    "RULES",
    "VARIABLE_SPECS",
    "AuditComparison",
    "AuditConfig",
    "AuditResult",
    "Category",
    "DiagnosticStatus",
    "Severity",
    "available_checks",
    "compare_audits",
    "export_results",
    "filter_anomalies",
    "get_rule",
    "quality_by_variable",
    "rules_frame",
    "run_audit",
    "run_detector",
    "severities_at_least",
    "summary_counts",
    "synthesis_by_rule",
    "write_report",
    "write_rules_catalog",
]
