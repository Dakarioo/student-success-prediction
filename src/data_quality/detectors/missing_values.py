"""Valeurs manquantes : natives, espaces seuls, NULL textuels, déguisées.

Distingue les manques reconnus nativement par pandas (champ vide) de ceux
représentés par des chaînes (« ND », « ? », « Non renseigné »…), calcule les
taux par variable et par observation, et mesure l'association des manques
entre variables.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import config as project_config
from src.data_quality.context import (
    DISGUISED,
    MISSING_KINDS,
    NATIVE,
    NULL_TOKEN,
    WHITESPACE,
    AuditContext,
)
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput

_RULE_BY_KIND = {
    NATIVE: "MIS_NATIVE",
    WHITESPACE: "MIS_WHITESPACE_ONLY",
    NULL_TOKEN: "MIS_NULL_TOKEN",
    DISGUISED: "MIS_DISGUISED",
}
_LABEL_BY_KIND = {
    NATIVE: "champ vide (NaN natif)",
    WHITESPACE: "espaces seuls",
    NULL_TOKEN: "mot-clé NULL textuel",
    DISGUISED: "valeur manquante déguisée",
}
_KEY_FIELDS = (project_config.STUDENT_ID, project_config.TARGET)


def detect_missing_values(ctx: AuditContext) -> DetectorOutput:
    """Détecte et quantifie toutes les formes de valeurs manquantes."""
    out = DetectorOutput()
    kinds = ctx.missing_kind
    ids = ctx.student_ids()

    for column in kinds.columns:
        missing_rows = kinds.index[kinds[column].ne("present")]
        for row in missing_rows:
            kind = kinds.at[row, column]
            rule_id = "MIS_KEY_FIELD" if column in _KEY_FIELDS else _RULE_BY_KIND[kind]
            original = ctx.raw.at[row, column]
            out.anomalies.append(
                Anomaly(
                    get_rule(rule_id),
                    f"Valeur manquante dans « {column} » : {_LABEL_BY_KIND[kind]}"
                    + (f" ({original!r})." if original != "" else "."),
                    row_index=int(row),
                    id_etudiant=ids.at[row],
                    column=column,
                    observed_value=repr(original),
                    expected_value="valeur renseignée",
                )
            )

    per_row = ctx.is_missing.sum(axis=1)
    _row_concentration(ctx, per_row, ids, out)

    out.tables["valeurs_manquantes"] = _per_variable_table(ctx)
    out.tables["manquants_par_observation"] = (
        per_row.value_counts()
        .sort_index()
        .rename_axis("n_valeurs_manquantes")
        .rename("n_observations")
        .reset_index()
    )
    out.tables["associations_manquants"] = _association_table(ctx, out)
    by_class = _missing_by_class(ctx)
    if by_class is not None:
        out.tables["manquants_par_classe"] = by_class

    total_cells = int(ctx.is_missing.size)
    out.summary.update(
        n_cellules_manquantes=int(ctx.is_missing.values.sum()),
        taux_cellules_manquantes=(
            round(float(ctx.is_missing.values.sum()) / total_cells, 4) if total_cells else 0.0
        ),
        n_observations_avec_manquant=int((per_row > 0).sum()),
        par_nature={k: int(kinds.eq(k).values.sum()) for k in MISSING_KINDS},
    )
    return out


def _per_variable_table(ctx: AuditContext) -> pd.DataFrame:
    kinds = ctx.missing_kind
    n = max(ctx.n_rows, 1)
    rows = []
    for column in kinds.columns:
        counts = kinds[column].value_counts()
        tokens = ctx.raw.loc[kinds[column].isin([NULL_TOKEN, DISGUISED]), column]
        n_total = int(sum(counts.get(k, 0) for k in MISSING_KINDS))
        rows.append(
            {
                "variable": column,
                "n_natifs": int(counts.get(NATIVE, 0)),
                "n_espaces_seuls": int(counts.get(WHITESPACE, 0)),
                "n_null_textuels": int(counts.get(NULL_TOKEN, 0)),
                "n_deguises": int(counts.get(DISGUISED, 0)),
                "n_total": n_total,
                "pct_total": round(100 * n_total / n, 2),
                "pct_natifs": round(100 * int(counts.get(NATIVE, 0)) / n, 2),
                "marqueurs_observes": " | ".join(
                    f"{tok!r}×{cnt}" for tok, cnt in tokens.value_counts().items()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("n_total", ascending=False, kind="stable")


def _row_concentration(
    ctx: AuditContext, per_row: pd.Series, ids: pd.Series, out: DetectorOutput
) -> None:
    threshold = ctx.config.row_missing_alert
    for row in per_row.index[per_row >= threshold]:
        columns = list(ctx.is_missing.columns[ctx.is_missing.loc[row]])
        out.anomalies.append(
            Anomaly(
                get_rule("MIS_ROW_CONCENTRATION"),
                f"{int(per_row[row])} valeurs manquantes sur cette observation "
                f"(seuil {threshold}).",
                row_index=int(row),
                id_etudiant=ids.at[row],
                related_columns=tuple(columns),
                observed_value=int(per_row[row]),
                expected_value=f"< {threshold}",
            )
        )


def _association_table(ctx: AuditContext, out: DetectorOutput) -> pd.DataFrame:
    """Coefficient phi (corrélation de Pearson entre indicateurs binaires de manque)."""
    indicators = ctx.is_missing.loc[:, ctx.is_missing.sum() > 0].astype(float)
    columns = ["variable_1", "variable_2", "phi", "n_manquants_communs"]
    if indicators.shape[1] < 2:
        return pd.DataFrame(columns=columns)
    phi = indicators.corr()
    rows = []
    names = list(phi.columns)
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            value = phi.at[first, second]
            if np.isnan(value):
                continue
            both = int((indicators[first].astype(bool) & indicators[second].astype(bool)).sum())
            rows.append((first, second, round(float(value), 4), both))
    table = pd.DataFrame(rows, columns=columns).sort_values("phi", ascending=False)
    threshold = ctx.config.missing_association_min_phi
    for first, second, value, both in table.itertuples(index=False):
        if value >= threshold:
            out.anomalies.append(
                Anomaly(
                    get_rule("MIS_ASSOCIATION"),
                    f"Manques associés entre « {first} » et « {second} » (phi = {value:.2f}, "
                    f"{both} observations concernées simultanément).",
                    column=first,
                    related_columns=(first, second),
                    observed_value=f"phi={value:.3f}",
                    expected_value=f"phi < {threshold}",
                    n_affected=both,
                    extra_key=second,
                )
            )
    return table.reset_index(drop=True)


def _missing_by_class(ctx: AuditContext) -> pd.DataFrame | None:
    """Taux de manque par variable et par classe cible (lecture descriptive)."""
    target = ctx.target_keys()
    if target is None or target.notna().sum() == 0:
        return None
    rates = ctx.is_missing.groupby(target).mean().T * 100
    rates = rates.loc[ctx.is_missing.sum() > 0]
    ordered = [c for c in project_config.TARGET_CLASSES if c in rates.columns]
    return rates[ordered].round(2).rename_axis("variable").reset_index()
