"""Anomalies de format et de saisie.

Les variantes d'une même modalité (espaces, casse, accents, synonymes) sont
rapprochées grâce à une clé normalisée, SANS modifier les valeurs d'origine.
La forme de référence est celle du dictionnaire lorsqu'il fixe le domaine,
sinon la variante la plus fréquente dans le fichier.
"""

from __future__ import annotations

import difflib
import re
from itertools import combinations

import pandas as pd

from src.data_quality.config import BINARY, BINARY_SYNONYMS, VARIABLE_SPECS
from src.data_quality.context import AuditContext, normalize_key, strip_accents
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput

_PARASITE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f ​﻿\t\r\n]")
_DIGITS = re.compile(r"\d+")


def detect_formats(ctx: AuditContext) -> DetectorOutput:
    """Détecte variantes de saisie, formats numériques non standard et caractères parasites."""
    out = DetectorOutput()
    ids = ctx.student_ids()
    variant_rows: list[dict] = []

    for column in ctx.columns:
        spec = VARIABLE_SPECS.get(column)
        values = ctx.raw[column]
        present = ~ctx.is_missing[column]
        _parasites(column, values, present, ids, out)
        if spec is not None and spec.is_numeric:
            _numeric_format(column, values, present, ids, out)
        elif column in ctx.keys.columns and spec is not None and spec.kind != "identifiant":
            canonical = canonical_forms(column, values[present], ctx.keys[column][present])
            _category_variants(column, values, ctx.keys[column], canonical, ids, out, variant_rows)
            if not spec.modalities:
                _similar_categories(column, ctx.keys[column][present], ctx, out)

    out.tables["variantes_modalites"] = pd.DataFrame(
        variant_rows,
        columns=["variable", "forme_reference", "variante", "n_observations", "differences"],
    )
    out.summary["n_variantes_distinctes"] = len(variant_rows)
    return out


def canonical_forms(column: str, values: pd.Series, keys: pd.Series) -> dict[str, str]:
    """Clé normalisée → forme de référence de la modalité."""
    spec = VARIABLE_SPECS.get(column)
    if spec is not None and spec.modalities:
        mapping = {normalize_key(pd.Series([m]))[0]: m for m in spec.modalities}
        if spec.kind == BINARY:
            for synonym, target in BINARY_SYNONYMS.items():
                target_form = mapping.get(target)
                if target_form is not None:
                    mapping.setdefault(synonym, target_form)
        return mapping
    frame = pd.DataFrame({"value": values, "key": keys})
    counts = frame.groupby(["key", "value"]).size().reset_index(name="n")
    counts = counts.sort_values(["key", "n"], ascending=[True, False], kind="stable")
    return dict(counts.drop_duplicates("key")[["key", "value"]].itertuples(index=False))


def describe_differences(value: str, reference: str) -> list[str]:
    """Liste les différences entre une variante et sa forme de référence."""
    issues = []
    stripped = value.strip()
    if stripped != value or "  " in value:
        issues.append("espaces superflus")
    if strip_accents(stripped.casefold()) != strip_accents(reference.casefold()):
        issues.append("synonyme/autre langue")
        return issues
    if stripped.casefold() != reference.casefold():
        issues.append("accentuation")
    if strip_accents(stripped) != strip_accents(reference) and (
        strip_accents(stripped).casefold() == strip_accents(reference).casefold()
    ):
        issues.append("casse")
    return issues


def _category_variants(
    column: str,
    values: pd.Series,
    keys: pd.Series,
    canonical: dict[str, str],
    ids: pd.Series,
    out: DetectorOutput,
    variant_rows: list[dict],
) -> None:
    expected = keys.map(canonical)
    mask = expected.notna() & (values != expected)
    if not mask.any():
        return
    for (value, reference), block in values[mask].groupby(
        [values[mask], expected[mask]], sort=True
    ):
        issues = describe_differences(str(value), str(reference))
        is_synonym = "synonyme/autre langue" in issues
        rule = get_rule("FMT_FOREIGN_SYNONYM" if is_synonym else "FMT_CATEGORY_VARIANT")
        variant_rows.append(
            {
                "variable": column,
                "forme_reference": reference,
                "variante": value,
                "n_observations": len(block),
                "differences": ", ".join(issues),
            }
        )
        for row in block.index:
            out.anomalies.append(
                Anomaly(
                    rule,
                    f"« {value} » est une variante de « {reference} » ({', '.join(issues)}).",
                    row_index=int(row),
                    id_etudiant=ids.at[row],
                    column=column,
                    observed_value=repr(value),
                    expected_value=reference,
                )
            )


def _numeric_format(
    column: str, values: pd.Series, present: pd.Series, ids: pd.Series, out: DetectorOutput
) -> None:
    candidates = values[present]
    strict = pd.to_numeric(candidates, errors="coerce")
    tolerant_text = (
        candidates.str.replace(" ", "", regex=False)
        .str.strip()
        .str.replace(r"^(-?\d+),(\d+)$", r"\1.\2", regex=True)
    )
    tolerant = pd.to_numeric(tolerant_text, errors="coerce")
    has_space = candidates != candidates.str.strip()
    has_comma = candidates.str.contains(",", regex=False)

    representation = tolerant.notna() & (strict.isna() | has_space | has_comma)
    for row in candidates.index[representation]:
        reasons = []
        if has_comma.at[row]:
            reasons.append("virgule décimale")
        if has_space.at[row]:
            reasons.append("espaces superflus")
        out.anomalies.append(
            Anomaly(
                get_rule("FMT_NUMERIC_REPRESENTATION"),
                f"Format numérique non standard ({', '.join(reasons) or 'représentation'}).",
                row_index=int(row),
                id_etudiant=ids.at[row],
                column=column,
                observed_value=repr(candidates.at[row]),
                expected_value=tolerant_text.at[row],
            )
        )
    for row in candidates.index[tolerant.isna()]:
        out.anomalies.append(
            Anomaly(
                get_rule("FMT_TEXT_IN_NUMERIC"),
                f"Valeur textuelle {candidates.at[row]!r} dans une variable numérique.",
                row_index=int(row),
                id_etudiant=ids.at[row],
                column=column,
                observed_value=repr(candidates.at[row]),
                expected_value="nombre",
            )
        )


def _parasites(
    column: str, values: pd.Series, present: pd.Series, ids: pd.Series, out: DetectorOutput
) -> None:
    mask = present & values.str.contains(_PARASITE, regex=True)
    for row in values.index[mask]:
        out.anomalies.append(
            Anomaly(
                get_rule("FMT_PARASITE_CHARACTERS"),
                "Caractère invisible ou non imprimable dans la valeur.",
                row_index=int(row),
                id_etudiant=ids.at[row],
                column=column,
                observed_value=repr(values.at[row]),
            )
        )


def _similar_categories(
    column: str, keys: pd.Series, ctx: AuditContext, out: DetectorOutput
) -> None:
    """Paires de modalités proches (hors différences purement numériques)."""
    counts = keys.value_counts()
    threshold = ctx.config.similar_category_ratio
    for first, second in combinations(sorted(counts.index), 2):
        if _DIGITS.sub("#", first) == _DIGITS.sub("#", second):
            continue  # « Phase 1 » / « Phase 2 », « b2 » / « b3 » : catégories distinctes
        ratio = difflib.SequenceMatcher(None, first, second).ratio()
        if ratio >= threshold:
            out.anomalies.append(
                Anomaly(
                    get_rule("FMT_SIMILAR_CATEGORIES"),
                    f"Modalités proches dans « {column} » : « {first} » ({counts[first]}) et "
                    f"« {second} » ({counts[second]}), similarité {ratio:.2f}.",
                    column=column,
                    observed_value=f"{first} | {second}",
                    expected_value="catégories distinctes ou à regrouper (à vérifier)",
                    n_affected=int(counts[first] + counts[second]),
                    extra_key=f"{first}|{second}",
                )
            )
