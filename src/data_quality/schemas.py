"""Structures de données de l'audit : gravité, statut, catégorie, anomalie.

Ce module ne contient aucune logique de détection. Il définit le vocabulaire
commun à tous les détecteurs, afin que chaque signalement ait exactement la
même structure (traçabilité, section 7 de la mission).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import pandas as pd


class Severity(StrEnum):
    """Gravité d'un signalement (de la plus forte à la plus faible)."""

    CRITICAL = "CRITICAL"  # règle métier confirmée violée / exploitation compromise
    HIGH = "HIGH"  # incohérence importante, conflit entre observations
    MEDIUM = "MEDIUM"  # problème potentiel nécessitant une analyse complémentaire
    LOW = "LOW"  # problème mineur de représentation, de format ou de normalisation
    INFO = "INFO"  # observation statistique ou méthodologique, sans erreur confirmée


SEVERITY_ORDER: tuple[Severity, ...] = tuple(Severity)
SEVERITY_LABELS_FR: dict[Severity, str] = {
    Severity.CRITICAL: "Critique",
    Severity.HIGH: "Élevée",
    Severity.MEDIUM: "Modérée",
    Severity.LOW: "Faible",
    Severity.INFO: "Information",
}


class DiagnosticStatus(StrEnum):
    """Nature du diagnostic, indépendante de la gravité (certitude ≠ gravité)."""

    CONFIRMED_ERROR = "erreur_confirmee"
    POTENTIAL_ANOMALY = "anomalie_potentielle"
    STATISTICAL_OUTLIER = "valeur_atypique"
    METHODOLOGICAL_RISK = "risque_methodologique"
    DESCRIPTIVE_INFO = "information_descriptive"


STATUS_LABELS_FR: dict[DiagnosticStatus, str] = {
    DiagnosticStatus.CONFIRMED_ERROR: "Erreur confirmée",
    DiagnosticStatus.POTENTIAL_ANOMALY: "Anomalie potentielle",
    DiagnosticStatus.STATISTICAL_OUTLIER: "Valeur statistiquement atypique",
    DiagnosticStatus.METHODOLOGICAL_RISK: "Risque méthodologique",
    DiagnosticStatus.DESCRIPTIVE_INFO: "Information descriptive",
}


class Category(StrEnum):
    """Famille de contrôle à l'origine du signalement."""

    STRUCTURE = "structure"
    MISSING = "valeurs_manquantes"
    DUPLICATES = "doublons"
    FORMAT = "format_saisie"
    DOMAIN = "domaine_metier"
    CONSISTENCY = "coherence_variables"
    UNIVARIATE = "atypique_univarie"
    MULTIVARIATE = "atypique_multivarie"
    REDUNDANCY = "redondance"
    LEAKAGE = "fuite_donnees"
    IMBALANCE = "desequilibre_classes"


#: Colonnes du tableau détaillé des anomalies, dans l'ordre d'export.
ANOMALY_COLUMNS: tuple[str, ...] = (
    "anomaly_id",
    "anomaly_key",
    "rule_id",
    "scope",
    "row_index",
    "id_etudiant",
    "column",
    "related_columns",
    "observed_value",
    "expected_value",
    "category",
    "severity",
    "diagnostic_status",
    "description",
    "potential_impact",
    "suggested_action",
    "detection_method",
    "n_affected",
)


@dataclass(frozen=True)
class Rule:
    """Règle d'audit déclarée dans le registre central (``rules.py``)."""

    rule_id: str
    detector: str
    category: Category
    severity: Severity
    status: DiagnosticStatus
    title: str
    columns: str
    justification: str
    potential_impact: str
    suggested_action: str
    detection_method: str


@dataclass
class Anomaly:
    """Un signalement individuel (une observation) ou global (``row_index`` absent).

    ``observed_value`` conserve toujours la valeur ORIGINALE (texte brut du CSV) ;
    pour un contrôle multivariable, elle liste les valeurs impliquées.
    """

    rule: Rule
    description: str
    row_index: int | None = None
    id_etudiant: str | None = None
    column: str | None = None
    related_columns: tuple[str, ...] = ()
    observed_value: Any = None
    expected_value: Any = None
    severity: Severity | None = None  # surcharge éventuelle de la gravité de la règle
    detection_method: str | None = None
    n_affected: int | None = None
    extra_key: str = ""

    def to_record(self) -> dict[str, Any]:
        """Convertit le signalement en ligne de tableau (sans ``anomaly_id``)."""
        scope = "observation" if self.row_index is not None else "global"
        key_parts = [
            self.rule.rule_id,
            self.id_etudiant or "-",
            self.column or "-",
            self.extra_key or "-",
        ]
        return {
            "anomaly_key": "|".join(key_parts),
            "rule_id": self.rule.rule_id,
            "scope": scope,
            "row_index": self.row_index,
            "id_etudiant": self.id_etudiant,
            "column": self.column,
            "related_columns": ";".join(self.related_columns),
            "observed_value": _to_text(self.observed_value),
            "expected_value": _to_text(self.expected_value),
            "category": self.rule.category.value,
            "severity": (self.severity or self.rule.severity).value,
            "diagnostic_status": self.rule.status.value,
            "description": self.description,
            "potential_impact": self.rule.potential_impact,
            "suggested_action": self.rule.suggested_action,
            "detection_method": self.detection_method or self.rule.detection_method,
            "n_affected": self.n_affected if self.n_affected is not None else 1,
        }


@dataclass
class DetectorOutput:
    """Résultat d'un détecteur : signalements + tableaux de synthèse nommés."""

    anomalies: list[Anomaly] = field(default_factory=list)
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


def _to_text(value: Any) -> str | None:
    """Représentation texte stable d'une valeur observée/attendue."""
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    return str(value)


def anomalies_to_frame(anomalies: list[Anomaly]) -> pd.DataFrame:
    """Assemble les signalements en DataFrame trié, avec identifiants séquentiels.

    Les doublons stricts (même clé) sont éliminés : une même règle ne signale
    qu'une fois une même cellule.
    """
    if not anomalies:
        return pd.DataFrame(columns=list(ANOMALY_COLUMNS))

    frame = pd.DataFrame([a.to_record() for a in anomalies])
    frame = frame.drop_duplicates(subset=["anomaly_key", "row_index"], keep="first")

    severity_rank = {s.value: i for i, s in enumerate(SEVERITY_ORDER)}
    frame["_sev"] = frame["severity"].map(severity_rank)
    frame["_row"] = frame["row_index"].fillna(-1)
    frame = frame.sort_values(["_sev", "rule_id", "_row", "column"], kind="stable")
    frame = frame.drop(columns=["_sev", "_row"]).reset_index(drop=True)

    frame["row_index"] = frame["row_index"].astype("Int64")
    frame["n_affected"] = frame["n_affected"].astype("Int64")
    frame.insert(0, "anomaly_id", [f"A{i:06d}" for i in range(1, len(frame) + 1)])
    return frame[list(ANOMALY_COLUMNS)]
