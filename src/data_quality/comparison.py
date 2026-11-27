"""Comparaison de deux audits (ex. avant / après nettoyage).

Rapprochement des signalements
------------------------------
Un signalement est identifié de façon stable par ``anomaly_key`` =
règle | identifiant étudiant | variable | complément, puis par son rang
d'occurrence (deux doublons exacts partagent la même clé). Les numéros de
ligne ne sont PAS utilisés : ils changent dès qu'une ligne est supprimée.

Limites : si le nettoyage modifie ou supprime des identifiants, les
signalements correspondants apparaissent « résolus » puis « nouveaux » ; une
observation sans identifiant ne peut pas être suivie individuellement.

Contrôles statistiques
----------------------
- **Seuils constants** : auditer les données nettoyées avec
  ``run_audit(after_df, reference_thresholds=before.thresholds)`` ; les
  variations reflètent alors uniquement les changements de données.
- **Seuils recalculés** (par défaut) : les bornes sont réestimées sur les
  nouvelles données ; une valeur peut devenir (ou cesser d'être) atypique
  simplement parce que la distribution a changé.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pandas as pd

from src.data_quality.schemas import SEVERITY_ORDER, Category, Severity

if TYPE_CHECKING:
    from src.data_quality.audit import AuditResult


@dataclass
class AuditComparison:
    """Tableaux de comparaison entre deux audits."""

    totals: pd.DataFrame
    by_category: pd.DataFrame
    by_rule: pd.DataFrame
    by_variable: pd.DataFrame
    missing: pd.DataFrame
    duplicates: pd.DataFrame
    business: pd.DataFrame
    resolved: pd.DataFrame
    persistent: pd.DataFrame
    new: pd.DataFrame
    notes: list[str] = field(default_factory=list)

    def status_counts(self) -> pd.DataFrame:
        """Nombre de signalements résolus, persistants et nouveaux par règle."""
        frames = []
        for label, frame in (
            ("resolu", self.resolved),
            ("persistant", self.persistent),
            ("nouveau", self.new),
        ):
            counts = frame.groupby("rule_id").size().rename(label)
            frames.append(counts)
        return pd.concat(frames, axis=1).fillna(0).astype(int).reset_index()


def _with_occurrence(anomalies: pd.DataFrame) -> pd.DataFrame:
    frame = anomalies.sort_values(["anomaly_key", "row_index"], kind="stable").copy()
    frame["occurrence"] = frame.groupby("anomaly_key").cumcount()
    return frame


def _delta(before: pd.Series, after: pd.Series, name: str) -> pd.DataFrame:
    table = pd.concat([before.rename("avant"), after.rename("apres")], axis=1).fillna(0)
    table = table.astype(int)
    table["evolution"] = table["apres"] - table["avant"]
    return table.rename_axis(name).reset_index()


def compare_audits(before: AuditResult, after: AuditResult) -> AuditComparison:
    """Compare deux ``AuditResult`` (même configuration recommandée)."""
    a, b = before.anomalies, after.anomalies
    notes = []

    totals_rows = [
        ("Observations", before.n_rows, after.n_rows),
        ("Colonnes", before.n_columns, after.n_columns),
        ("Signalements", len(a), len(b)),
        (
            "Signalements hors INFO",
            int((a["severity"] != "INFO").sum()),
            int((b["severity"] != "INFO").sum()),
        ),
        ("Observations distinctes concernées", a["row_index"].nunique(), b["row_index"].nunique()),
    ]
    for level in SEVERITY_ORDER:
        totals_rows.append(
            (
                f"Signalements {level.value}",
                int((a["severity"] == level).sum()),
                int((b["severity"] == level).sum()),
            )
        )
    totals = pd.DataFrame(totals_rows, columns=["indicateur", "avant", "apres"])
    totals["evolution"] = totals["apres"] - totals["avant"]

    by_category = _delta(a["category"].value_counts(), b["category"].value_counts(), "categorie")
    by_rule = _delta(a["rule_id"].value_counts(), b["rule_id"].value_counts(), "rule_id")
    non_info_a = a[(a["severity"] != Severity.INFO.value) & a["column"].notna()]
    non_info_b = b[(b["severity"] != Severity.INFO.value) & b["column"].notna()]
    by_variable = _delta(
        non_info_a["column"].value_counts(), non_info_b["column"].value_counts(), "variable"
    )

    missing = _missing_delta(before, after)
    duplicates = _summary_delta(
        before.summaries.get("duplicates", {}), after.summaries.get("duplicates", {})
    )
    business_rules = {Category.DOMAIN.value, Category.CONSISTENCY.value}
    business = _delta(
        a.loc[a["category"].isin(business_rules), "rule_id"].value_counts(),
        b.loc[b["category"].isin(business_rules), "rule_id"].value_counts(),
        "rule_id",
    )

    ka, kb = _with_occurrence(a), _with_occurrence(b)
    keys = ["anomaly_key", "occurrence"]
    merged = ka.merge(
        kb[keys + ["row_index"]], on=keys, how="outer", indicator=True, suffixes=("", "_apres")
    )
    resolved = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])
    persistent = merged[merged["_merge"] == "both"].drop(columns=["_merge"])
    new = kb.merge(ka[keys], on=keys, how="left", indicator=True)
    new = new[new["_merge"] == "left_only"].drop(columns=["_merge"])

    if a["id_etudiant"].isna().all() or b["id_etudiant"].isna().all():
        notes.append("Identifiants absents : rapprochement individuel impossible.")
    ref = after.thresholds
    if not ref.empty and "seuils" in ref.columns and (ref["seuils"] == "reference").all():
        notes.append("Contrôles statistiques à seuils constants (seuils de l'audit de référence).")
    else:
        notes.append(
            "Contrôles statistiques à seuils recalculés : une partie des écarts d'atypiques "
            "vient de l'évolution des distributions."
        )
    return AuditComparison(
        totals,
        by_category,
        by_rule,
        by_variable,
        missing,
        duplicates,
        business,
        resolved,
        persistent,
        new,
        notes,
    )


def _missing_delta(before: AuditResult, after: AuditResult) -> pd.DataFrame:
    tb = before.tables.get("valeurs_manquantes")
    ta = after.tables.get("valeurs_manquantes")
    if tb is None or ta is None:
        return pd.DataFrame(columns=["variable", "avant", "apres", "evolution"])
    return _delta(
        tb.set_index("variable")["n_total"], ta.set_index("variable")["n_total"], "variable"
    )


def _summary_delta(before: dict, after: dict) -> pd.DataFrame:
    keys = sorted(set(before) | set(after))
    rows = [
        (k, before.get(k, 0), after.get(k, 0))
        for k in keys
        if isinstance(before.get(k, 0), (int, float)) and isinstance(after.get(k, 0), (int, float))
    ]
    table = pd.DataFrame(rows, columns=["indicateur", "avant", "apres"])
    table["evolution"] = table["apres"] - table["avant"]
    return table
