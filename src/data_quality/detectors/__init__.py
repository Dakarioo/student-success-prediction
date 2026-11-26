"""Détecteurs indépendants : chacun reçoit le contexte et renvoie un ``DetectorOutput``.

L'ordre du registre est l'ordre d'exécution par défaut. Le détecteur
multivarié est facultatif (activé par ``AuditConfig.multivariate_enabled``
ou en le demandant explicitement).
"""

from __future__ import annotations

from collections.abc import Callable

from src.data_quality.context import AuditContext
from src.data_quality.detectors.business_rules import detect_business_rules
from src.data_quality.detectors.class_balance import detect_class_balance
from src.data_quality.detectors.consistency import detect_consistency
from src.data_quality.detectors.duplicates import detect_duplicates
from src.data_quality.detectors.formats import detect_formats
from src.data_quality.detectors.leakage import detect_leakage
from src.data_quality.detectors.missing_values import detect_missing_values
from src.data_quality.detectors.multivariate import detect_multivariate
from src.data_quality.detectors.redundancy import detect_redundancy
from src.data_quality.detectors.statistical import detect_statistical
from src.data_quality.detectors.structure import detect_structure
from src.data_quality.schemas import DetectorOutput

Detector = Callable[[AuditContext], DetectorOutput]

DETECTORS: dict[str, Detector] = {
    "structure": detect_structure,
    "missing_values": detect_missing_values,
    "duplicates": detect_duplicates,
    "formats": detect_formats,
    "business_rules": detect_business_rules,
    "consistency": detect_consistency,
    "statistical": detect_statistical,
    "multivariate": detect_multivariate,
    "redundancy": detect_redundancy,
    "leakage": detect_leakage,
    "class_balance": detect_class_balance,
}

#: Détecteurs non exécutés par défaut.
OPTIONAL_DETECTORS: frozenset[str] = frozenset({"multivariate"})

__all__ = ["DETECTORS", "OPTIONAL_DETECTORS", "Detector"]
