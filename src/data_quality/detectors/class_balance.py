"""Déséquilibre des classes de la cible : un RISQUE MÉTHODOLOGIQUE, pas une erreur.

Aucun rééquilibrage n'est réalisé ici (il relèverait de la modélisation et
devrait être évalué en validation croisée).
"""

from __future__ import annotations

import pandas as pd

from src import config as project_config
from src.data_quality.context import AuditContext
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput, Severity


def detect_class_balance(ctx: AuditContext) -> DetectorOutput:
    """Effectifs, proportions et ratio de déséquilibre de ``statut_academique``."""
    out = DetectorOutput()
    target = ctx.target_keys()
    if target is None:
        out.summary["statut"] = "cible absente"
        return out
    counts = target.value_counts().reindex(project_config.TARGET_CLASSES, fill_value=0)
    total = int(counts.sum())
    table = pd.DataFrame(
        {
            "classe": counts.index,
            "effectif": counts.to_numpy(),
            "proportion": (counts / total).round(4).to_numpy() if total else 0.0,
        }
    )
    out.tables["repartition_classes"] = table
    if total == 0 or (counts > 0).sum() < 2:
        out.summary["statut"] = "moins de deux classes observées"
        return out

    present = counts[counts > 0]
    majority, minority = present.idxmax(), present.idxmin()
    ratio = float(present.max() / present.min())
    out.summary.update(
        classe_majoritaire=majority,
        classe_minoritaire=minority,
        ratio_desequilibre=round(ratio, 3),
        effectifs={k: int(v) for k, v in counts.items()},
        baseline_accuracy=round(float(present.max() / total), 4),
    )
    alert = ratio >= ctx.config.class_imbalance_ratio_alert
    out.anomalies.append(
        Anomaly(
            get_rule("IMB_CLASS_IMBALANCE"),
            f"Classe majoritaire « {majority} » ({present.max()} ; {present.max() / total:.1%}), "
            f"classe minoritaire « {minority} » ({present.min()} ; {present.min() / total:.1%}) : "
            f"ratio {ratio:.2f}. Un modèle prédisant toujours « {majority} » obtiendrait une "
            f"Accuracy de {present.max() / total:.1%}.",
            column=project_config.TARGET,
            observed_value=f"ratio={ratio:.3f}",
            expected_value=f"ratio < {ctx.config.class_imbalance_ratio_alert}",
            severity=None if alert else Severity.INFO,
            n_affected=total,
        )
    )
    return out
