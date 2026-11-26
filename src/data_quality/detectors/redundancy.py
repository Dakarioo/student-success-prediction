"""Redondances entre variables.

Distingue :

- les redondances RÉELLES : colonnes identiques, quasi identiques
  (corrélation ≥ 0,98) et dépendances déterministes (une variable fixe
  l'autre) ;
- les simples ASSOCIATIONS statistiques : fortes corrélations, V de Cramér
  élevé, qui ne justifient pas à elles seules une exclusion.

Trois paires documentées par le dictionnaire sont étudiées en détail :
``note_admission`` / ``note_admission_archive``, ``age_inscription`` /
``age_inscription_mois`` et ``note_diplome_anterieur`` / ``niveau_dossier``.
Aucune variable n'est supprimée.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats.contingency import association

from src.data_quality.config import IDENTIFIER, METADATA, TARGET, VARIABLE_SPECS
from src.data_quality.context import AuditContext
from src.data_quality.detectors.consistency import expected_niveau
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput

_EXCLUDED_KINDS = {IDENTIFIER, METADATA, TARGET}
_MAX_LEVELS = 60  # au-delà, une « dépendance » est triviale (groupes minuscules)
_MIN_GROUP_SIZE = 20


def _analysable(name: str) -> bool:
    spec = VARIABLE_SPECS.get(name)
    return spec is not None and spec.kind not in _EXCLUDED_KINDS


def detect_redundancy(ctx: AuditContext) -> DetectorOutput:
    """Recherche les redondances et associations fortes entre variables."""
    out = DetectorOutput()
    flagged_pairs: set[frozenset[str]] = set()
    rows: list[dict] = []
    documented = _documented_pairs(ctx)
    _documented_derivations(documented, out, flagged_pairs, rows)
    _identical_columns(ctx, out, flagged_pairs, rows)
    corr = _correlations(ctx, out, flagged_pairs, rows)
    _functional_dependencies(ctx, out, flagged_pairs, rows)
    _categorical_associations(ctx, out, flagged_pairs, rows)
    out.tables["redondances"] = pd.DataFrame(
        rows, columns=["variable_1", "variable_2", "type", "mesure", "valeur", "commentaire"]
    )
    out.tables["paires_documentees"] = documented
    if corr is not None:
        out.tables["matrice_correlation_spearman"] = corr
    return out


def _record(
    out: DetectorOutput,
    rows: list[dict],
    flagged: set[frozenset[str]],
    rule_id: str,
    first: str,
    second: str,
    measure: str,
    value: float,
    comment: str,
) -> None:
    flagged.add(frozenset((first, second)))
    rows.append(
        {
            "variable_1": first,
            "variable_2": second,
            "type": rule_id,
            "mesure": measure,
            "valeur": round(float(value), 4),
            "commentaire": comment,
        }
    )
    out.anomalies.append(
        Anomaly(
            get_rule(rule_id),
            f"« {first} » / « {second} » : {comment} ({measure} = {value:.3f}).",
            column=first,
            related_columns=(first, second),
            observed_value=f"{measure}={value:.4f}",
            extra_key=second,
        )
    )


#: Dérivations documentées par le dictionnaire : (paire, variable source, variable dérivée).
_DERIVATIONS = (
    ("age_inscription / age_inscription_mois", "age_inscription", "age_inscription_mois"),
    ("note_diplome_anterieur / niveau_dossier", "note_diplome_anterieur", "niveau_dossier"),
)
_DERIVATION_MIN_SHARE = 0.95


def _documented_derivations(documented, out, flagged, rows) -> None:
    """Signale les dérivations documentées confirmées par les données."""
    if documented.empty:
        return
    shares = documented.set_index("paire")["part_coherente"]
    for pair, source, derived in _DERIVATIONS:
        share = shares.get(pair)
        if share is not None and not pd.isna(share) and share >= _DERIVATION_MIN_SHARE:
            _record(
                out,
                rows,
                flagged,
                "RED_DETERMINISTIC",
                source,
                derived,
                "part coherente",
                share,
                "variable dérivée de la précédente (dictionnaire), confirmée par les données",
            )


def _identical_columns(ctx, out, flagged, rows) -> None:
    names = [c for c in ctx.columns if _analysable(c)]
    raw = ctx.raw.loc[:, ~ctx.raw.columns.duplicated()]
    for first, second in combinations(names, 2):
        if raw[first].equals(raw[second]):
            _record(
                out,
                rows,
                flagged,
                "RED_IDENTICAL_COLUMNS",
                first,
                second,
                "egalite",
                1.0,
                "colonnes strictement identiques",
            )


def _correlations(ctx, out, flagged, rows) -> pd.DataFrame | None:
    cfg = ctx.config
    numeric = ctx.valid_numeric[[c for c in ctx.valid_numeric.columns if _analysable(c)]]
    numeric = numeric.loc[:, numeric.nunique() > 1]
    if numeric.shape[1] < 2 or len(numeric) < 3:
        return None
    pearson = numeric.corr(method="pearson")
    spearman = numeric.corr(method="spearman")
    for first, second in combinations(numeric.columns, 2):
        if frozenset((first, second)) in flagged:
            continue
        r_p, r_s = pearson.at[first, second], spearman.at[first, second]
        strongest = max(abs(r_p), abs(r_s)) if not (np.isnan(r_p) and np.isnan(r_s)) else 0
        if strongest >= cfg.near_identical_correlation:
            _record(
                out,
                rows,
                flagged,
                "RED_NEAR_DUPLICATE",
                first,
                second,
                "max(|Pearson|,|Spearman|)",
                strongest,
                "variables quasi identiques : l'une n'apporte presque rien de plus",
            )
        elif strongest >= cfg.high_correlation:
            _record(
                out,
                rows,
                flagged,
                "RED_HIGH_CORRELATION",
                first,
                second,
                "max(|Pearson|,|Spearman|)",
                strongest,
                "forte corrélation (association statistique, pas forcément redondance)",
            )
    return spearman.round(4)


def _candidate_levels(ctx: AuditContext) -> dict[str, pd.Series]:
    """Variables à peu de modalités (qualitatives normalisées ou numériques discrètes)."""
    candidates: dict[str, pd.Series] = {}
    for column in ctx.columns:
        if not _analysable(column):
            continue
        series = ctx.keys[column] if column in ctx.keys.columns else ctx.valid_numeric[column]
        n_levels = series.nunique()
        if 2 <= n_levels <= _MAX_LEVELS:
            candidates[column] = series
    return candidates


def functional_dependency_share(source: pd.Series, target: pd.Series) -> float:
    """Part des observations dont ``target`` est la valeur modale de son groupe ``source``."""
    frame = pd.DataFrame({"a": source, "b": target}).dropna()
    if frame.empty:
        return float("nan")
    modal = frame.groupby("a")["b"].agg(lambda s: s.value_counts().iloc[0])
    return float(modal.sum() / len(frame))


def _functional_dependencies(ctx, out, flagged, rows) -> None:
    cfg = ctx.config
    candidates = _candidate_levels(ctx)
    for source, target in ((a, b) for a in candidates for b in candidates if a != b):
        if frozenset((source, target)) in flagged:
            continue
        a, b = candidates[source], candidates[target]
        both = a.notna() & b.notna()
        if both.sum() == 0 or both.sum() / a[both].nunique() < _MIN_GROUP_SIZE:
            continue
        baseline = float(b[both].value_counts(normalize=True).iloc[0])
        if baseline >= 0.9:
            continue  # cible quasi constante : la dépendance serait triviale
        share = functional_dependency_share(a, b)
        if share >= cfg.functional_dependency_share:
            _record(
                out,
                rows,
                flagged,
                "RED_DETERMINISTIC",
                source,
                target,
                "part déterminée",
                share,
                f"la valeur de « {source} » détermine celle de « {target} »",
            )


def _categorical_associations(ctx, out, flagged, rows) -> None:
    cfg = ctx.config
    names = [
        c
        for c in ctx.keys.columns
        if _analysable(c) and VARIABLE_SPECS[c].is_categorical and ctx.keys[c].nunique() > 1
    ]
    for first, second in combinations(names, 2):
        if frozenset((first, second)) in flagged:
            continue
        value = cramers_v(ctx.keys[first], ctx.keys[second])
        if value >= cfg.cramers_v_threshold:
            _record(
                out,
                rows,
                flagged,
                "RED_CATEGORICAL_ASSOCIATION",
                first,
                second,
                "V de Cramér",
                value,
                "forte association entre variables qualitatives",
            )


def cramers_v(first: pd.Series, second: pd.Series) -> float:
    """V de Cramér entre deux variables qualitatives (lignes complètes)."""
    table = pd.crosstab(first, second)
    if table.shape[0] < 2 or table.shape[1] < 2:
        return 0.0
    return float(association(table.to_numpy(), method="cramer"))


def correlation_ratio(categories: pd.Series, values: pd.Series) -> float:
    """Rapport de corrélation η (part de variance expliquée par les modalités, racine)."""
    frame = pd.DataFrame({"c": categories, "v": values}).dropna()
    if frame["c"].nunique() < 2 or frame["v"].var() == 0 or len(frame) < 3:
        return 0.0
    grand = frame["v"].mean()
    groups = frame.groupby("c")["v"]
    between = float((groups.count() * (groups.mean() - grand) ** 2).sum())
    total = float(((frame["v"] - grand) ** 2).sum())
    return float(np.sqrt(between / total)) if total > 0 else 0.0


def _documented_pairs(ctx: AuditContext) -> pd.DataFrame:
    """Analyse détaillée des trois paires signalées par le dictionnaire."""
    cfg = ctx.config
    v = ctx.valid_numeric
    rows = []
    if {"note_admission", "note_admission_archive"} <= set(v.columns):
        a, b = v["note_admission"], v["note_admission_archive"]
        both = a.notna() & b.notna()
        gap = (a - b)[both]
        rows.append(
            {
                "paire": "note_admission / note_admission_archive",
                "n_comparables": int(both.sum()),
                "correlation_pearson": round(float(a[both].corr(b[both])), 4)
                if both.sum() > 2
                else None,
                "part_egalite_exacte": round(float((gap == 0).mean()), 4) if both.any() else None,
                "part_coherente": round(
                    float((gap.abs() <= cfg.admission_archive_tolerance).mean()), 4
                )
                if both.any()
                else None,
                "ecart_absolu_median": round(float(gap.abs().median()), 4) if both.any() else None,
                "ecart_absolu_q99": round(float(gap.abs().quantile(0.99)), 4)
                if both.any()
                else None,
                "lecture": "même information issue de deux exports (léger bruit systématique)",
            }
        )
    if {"age_inscription", "age_inscription_mois"} <= set(v.columns):
        years, months = v["age_inscription"], v["age_inscription_mois"]
        both = years.notna() & months.notna()
        ok = (months >= 12 * years) & (months <= 12 * years + 11)
        rows.append(
            {
                "paire": "age_inscription / age_inscription_mois",
                "n_comparables": int(both.sum()),
                "correlation_pearson": round(float(years[both].corr(months[both])), 4)
                if both.sum() > 2
                else None,
                "part_coherente": round(float(ok[both].mean()), 4) if both.any() else None,
                "lecture": "âge en mois simulé à partir de l'âge en années (dérivation documentée)",
            }
        )
    if "note_diplome_anterieur" in v.columns and "niveau_dossier" in ctx.keys.columns:
        note, level = v["note_diplome_anterieur"], ctx.keys["niveau_dossier"]
        expected = expected_niveau(note, cfg.niveau_dossier_thresholds)
        both = note.notna() & level.notna()
        rows.append(
            {
                "paire": "note_diplome_anterieur / niveau_dossier",
                "n_comparables": int(both.sum()),
                "rapport_correlation_eta": round(correlation_ratio(level, note), 4),
                "part_coherente": round(float((expected[both] == level[both]).mean()), 4)
                if both.any()
                else None,
                "lecture": "niveau dérivé de la note par seuils (dérivation documentée)",
            }
        )
    return pd.DataFrame(rows)
