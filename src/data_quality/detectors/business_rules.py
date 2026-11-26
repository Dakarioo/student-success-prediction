"""Règles de domaine métier construites à partir du dictionnaire des variables.

- Bornes des notes (sur 200, sur 20) et des taux.
- Comptages entiers et non négatifs, codes sentinelles.
- Modalités admises (rang de vœu, régime, binaires, niveau, cible).
- Validité des identifiants et plausibilité des âges.

Les valeurs manquantes et les problèmes de format sont traités par leurs
propres détecteurs : ce module ne contrôle que les valeurs lisibles.
"""

from __future__ import annotations

import pandas as pd

from src import config as project_config
from src.data_quality.config import (
    BINARY_SYNONYMS,
    SENTINEL_VALUES,
    STUDENT_ID_PATTERN,
    VARIABLE_SPECS,
    VariableSpec,
)
from src.data_quality.context import AuditContext, normalize_key
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput, Rule

_AGE_COLUMNS = {"age_inscription", "age_inscription_mois"}


def detect_business_rules(ctx: AuditContext) -> DetectorOutput:
    """Applique les règles de domaine de chaque variable documentée."""
    out = DetectorOutput()
    ids = ctx.student_ids()
    for column in ctx.columns:
        spec = VARIABLE_SPECS.get(column)
        if spec is None:
            continue
        if spec.is_numeric and column in ctx.numeric.columns:
            _numeric_domain(ctx, spec, ids, out)
        elif spec.modalities and column in ctx.keys.columns:
            _categorical_domain(ctx, spec, ids, out)
    if ctx.has(project_config.STUDENT_ID):
        _identifier_format(ctx, ids, out)
    return out


def _emit(
    out: DetectorOutput,
    rule: Rule,
    rows: pd.Index,
    ctx: AuditContext,
    ids: pd.Series,
    column: str,
    expected: str,
    message: str,
) -> None:
    for row in rows:
        original = ctx.raw.at[row, column]
        out.anomalies.append(
            Anomaly(
                rule,
                message.format(value=original),
                row_index=int(row),
                id_etudiant=ids.at[row],
                column=column,
                observed_value=original,
                expected_value=expected,
            )
        )


def _numeric_domain(
    ctx: AuditContext, spec: VariableSpec, ids: pd.Series, out: DetectorOutput
) -> None:
    values = ctx.numeric[spec.name]
    present = values.notna()
    flagged = pd.Series(False, index=values.index)
    cfg = ctx.config

    if spec.name in _AGE_COLUMNS:
        limit = cfg.age_impossible_max * (12 if spec.name.endswith("mois") else 1)
        impossible = present & ((values <= 0) | (values > limit))
        _emit(
            out,
            get_rule("DOM_AGE_IMPOSSIBLE"),
            values.index[impossible],
            ctx,
            ids,
            spec.name,
            f"]0 ; {limit}]",
            "Âge impossible : {value}.",
        )
        flagged |= impossible
        if spec.name == "age_inscription":
            implausible = (
                present
                & ~flagged
                & ((values < cfg.age_plausible_min) | (values > cfg.age_plausible_max))
            )
            _emit(
                out,
                get_rule("DOM_AGE_IMPLAUSIBLE"),
                values.index[implausible],
                ctx,
                ids,
                spec.name,
                f"[{cfg.age_plausible_min} ; {cfg.age_plausible_max}] (hypothèse)",
                "Âge peu plausible pour une inscription : {value} ans (plage d'hypothèse).",
            )
    elif spec.expected_dtype == "int":
        negative = present & (values < 0)
        _emit(
            out,
            get_rule("DOM_NEGATIVE_COUNT"),
            values.index[negative],
            ctx,
            ids,
            spec.name,
            "entier ≥ 0",
            "Comptage négatif : {value}.",
        )
        flagged |= negative

    lower, upper = spec.min_value, spec.max_value
    if upper is not None or (lower is not None and spec.expected_dtype != "int"):
        out_of_range = present & ~flagged
        bound = pd.Series(False, index=values.index)
        if lower is not None:
            bound |= values < lower
        if upper is not None:
            bound |= values > upper
        out_of_range &= bound
        expected = f"[{_fmt(lower, '-inf')} ; {_fmt(upper, '+inf')}]"
        is_sentinel = values.isin(SENTINEL_VALUES)
        message = "Valeur {value} hors de l'échelle du dictionnaire " + expected
        _emit(
            out,
            get_rule("DOM_OUT_OF_RANGE"),
            values.index[out_of_range & ~is_sentinel],
            ctx,
            ids,
            spec.name,
            expected,
            message + ".",
        )
        _emit(
            out,
            get_rule("DOM_OUT_OF_RANGE"),
            values.index[out_of_range & is_sentinel],
            ctx,
            ids,
            spec.name,
            expected,
            message + " (probable code sentinelle de valeur inconnue).",
        )
        flagged |= out_of_range

    if spec.expected_dtype == "int":
        non_integer = present & ~flagged & ((values % 1) != 0)
        _emit(
            out,
            get_rule("DOM_NON_INTEGER"),
            values.index[non_integer],
            ctx,
            ids,
            spec.name,
            "entier",
            "Valeur non entière {value} pour un comptage.",
        )
        flagged |= non_integer
        sentinel = present & ~flagged & values.isin(SENTINEL_VALUES)
        _emit(
            out,
            get_rule("DOM_SENTINEL_VALUE"),
            values.index[sentinel],
            ctx,
            ids,
            spec.name,
            "valeur réelle ou manquante explicite",
            "Valeur {value} : code sentinelle probable (valeur inconnue), sans borne haute au "
            "dictionnaire.",
        )


def _fmt(bound: float | None, default: str) -> str:
    """Borne lisible (``default`` si la borne n'existe pas)."""
    return default if bound is None else f"{bound:g}"


def _categorical_domain(
    ctx: AuditContext, spec: VariableSpec, ids: pd.Series, out: DetectorOutput
) -> None:
    keys = ctx.keys[spec.name]
    allowed = {normalize_key(pd.Series([m]))[0] for m in spec.modalities}
    if spec.kind == "binaire":
        allowed |= {syn for syn, tgt in BINARY_SYNONYMS.items() if tgt in allowed}
    invalid = keys.notna() & ~keys.isin(allowed)
    is_target = spec.name == project_config.TARGET
    rule = get_rule("DOM_TARGET_INVALID" if is_target else "DOM_CATEGORY_OUT_OF_DOMAIN")
    _emit(
        out,
        rule,
        keys.index[invalid],
        ctx,
        ids,
        spec.name,
        " | ".join(spec.modalities),
        "Modalité {value!r} absente du domaine du dictionnaire.",
    )


def _identifier_format(ctx: AuditContext, ids: pd.Series, out: DetectorOutput) -> None:
    column = project_config.STUDENT_ID
    present = ids.notna()
    valid = ids.astype(str).str.fullmatch(STUDENT_ID_PATTERN)
    invalid = present & ~valid.fillna(False).astype(bool)
    _emit(
        out,
        get_rule("DOM_ID_FORMAT"),
        ids.index[invalid],
        ctx,
        ids,
        column,
        f"motif {STUDENT_ID_PATTERN} (convention observée)",
        "Identifiant {value!r} au format inhabituel.",
    )
