"""Contrôles de structure : dimensions, colonnes, types, colonnes vides ou constantes."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from src.data_quality.config import EXPECTED_COLUMNS, VARIABLE_SPECS
from src.data_quality.context import NATIVE, AuditContext
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput, Severity


def infer_observed_type(series: pd.Series) -> str:
    """Type que pandas attribuerait à la lecture par défaut du CSV.

    Reproduit la logique de ``read_csv`` : champ vide → NaN, puis entier si
    toutes les valeurs sont entières, flottant si numériques (point décimal
    uniquement), texte sinon.
    """
    values = series[series.astype(str) != ""].astype(str)
    if values.empty:
        return "vide"
    numbers = pd.to_numeric(values, errors="coerce")
    if numbers.isna().any():
        return "texte"
    has_missing = len(values) < len(series)
    if (numbers % 1 == 0).all() and not has_missing and not values.str.contains(r"\.").any():
        return "entier"
    return "decimal"


_EXPECTED_LABEL = {"text": "texte", "float": "decimal", "int": "entier"}


def detect_structure(ctx: AuditContext) -> DetectorOutput:
    """Contrôle la structure générale et la conformité au dictionnaire."""
    out = DetectorOutput()
    n_rows, n_cols = ctx.raw.shape
    out.summary.update(n_rows=int(n_rows), n_columns=int(n_cols), source=ctx.source)

    out.anomalies.append(
        Anomaly(
            get_rule("STR_SHAPE"),
            f"{n_rows} observations × {n_cols} colonnes "
            f"({len(EXPECTED_COLUMNS)} colonnes attendues par le dictionnaire).",
            observed_value=f"{n_rows} x {n_cols}",
            expected_value=f"? x {len(EXPECTED_COLUMNS)}",
            n_affected=int(n_rows),
        )
    )
    if n_rows == 0:
        out.anomalies.append(
            Anomaly(get_rule("STR_EMPTY_DATASET"), "Le fichier ne contient aucune observation.")
        )

    _check_columns(ctx, out)
    out.tables["structure_variables"] = _variable_table(ctx, out)
    return out


def _check_columns(ctx: AuditContext, out: DetectorOutput) -> None:
    present = set(ctx.columns)
    for name in EXPECTED_COLUMNS:
        if name not in present:
            out.anomalies.append(
                Anomaly(
                    get_rule("STR_MISSING_COLUMN"),
                    f"La colonne « {name} » décrite dans le dictionnaire est absente.",
                    column=name,
                    expected_value="présente",
                    observed_value="absente",
                )
            )
    for name in ctx.columns:
        if name not in VARIABLE_SPECS:
            out.anomalies.append(
                Anomaly(
                    get_rule("STR_UNEXPECTED_COLUMN"),
                    f"La colonne « {name} » n'est pas décrite dans le dictionnaire.",
                    column=name,
                )
            )
    for name, count in Counter(ctx.header).items():
        if count > 1:
            out.anomalies.append(
                Anomaly(
                    get_rule("STR_DUPLICATE_COLUMN_NAME"),
                    f"Le nom « {name} » apparaît {count} fois dans l'en-tête.",
                    column=name,
                    observed_value=count,
                    expected_value=1,
                )
            )


def _variable_table(ctx: AuditContext, out: DetectorOutput) -> pd.DataFrame:
    """Tableau de conformité par variable (type attendu / observé, modalités…)."""
    rows = []
    cfg = ctx.config
    for name in ctx.columns:
        series = ctx.raw[name]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        spec = VARIABLE_SPECS.get(name)
        observed = infer_observed_type(series)
        expected = _EXPECTED_LABEL[spec.expected_dtype] if spec else "non documenté"
        n_missing = int(ctx.is_missing[name].sum())
        n_present = len(series) - n_missing
        present_values = series[~ctx.is_missing[name]]
        n_unique = int(present_values.nunique())
        top_share = float(present_values.value_counts(normalize=True).iloc[0]) if n_present else 0.0
        rows.append(
            {
                "variable": name,
                "documentee": spec is not None,
                "role": spec.kind if spec else "inconnu",
                "disponibilite": spec.availability if spec else "inconnue",
                "type_attendu": expected,
                "type_observe": observed,
                "n_valeurs_renseignees": n_present,
                "n_modalites_distinctes": n_unique,
                "part_modalite_dominante": round(top_share, 4),
            }
        )
        if spec is not None:
            _type_anomaly(name, expected, observed, out)
        if len(series) and int(ctx.missing_kind[name].eq(NATIVE).sum()) == len(series):
            out.anomalies.append(
                Anomaly(
                    get_rule("STR_EMPTY_COLUMN"),
                    f"La colonne « {name} » ne contient aucune valeur.",
                    column=name,
                    n_affected=len(series),
                )
            )
        elif n_present and n_unique == 1:
            out.anomalies.append(
                Anomaly(
                    get_rule("STR_CONSTANT_COLUMN"),
                    f"« {name} » ne prend qu'une valeur ({present_values.iloc[0]!r}) sur "
                    f"{n_present} observations renseignées.",
                    column=name,
                    observed_value=present_values.iloc[0],
                    n_affected=n_present,
                )
            )
        elif n_present and top_share >= cfg.quasi_constant_share:
            out.anomalies.append(
                Anomaly(
                    get_rule("STR_QUASI_CONSTANT_COLUMN"),
                    f"« {name} » : la modalité dominante représente {top_share:.1%} des valeurs "
                    f"(seuil {cfg.quasi_constant_share:.0%}).",
                    column=name,
                    observed_value=f"{top_share:.4f}",
                    expected_value=f"< {cfg.quasi_constant_share}",
                    n_affected=n_present,
                )
            )
    return pd.DataFrame(rows)


def _type_anomaly(name: str, expected: str, observed: str, out: DetectorOutput) -> None:
    """Signale l'écart entre type attendu (dictionnaire) et type lu par pandas."""
    if observed in {expected, "vide"}:
        return
    if expected == "decimal" and observed == "entier":
        return  # un entier est un décimal valide
    severity = Severity.HIGH
    detail = "des valeurs non numériques empêchent la lecture numérique"
    if expected == "entier" and observed == "decimal":
        severity = Severity.LOW
        detail = "valeurs manquantes ou non entières : pandas lit la colonne en flottant"
    elif expected == "texte":
        severity = Severity.INFO
        detail = "code lu comme un nombre : il ne doit pas être traité comme une grandeur"
    out.anomalies.append(
        Anomaly(
            get_rule("STR_TYPE_MISMATCH"),
            f"« {name} » : type attendu {expected}, type lu {observed} ({detail}).",
            column=name,
            observed_value=observed,
            expected_value=expected,
            severity=severity,
        )
    )
