"""Risques de fuite de données et d'apprentissage artificiel.

Rappel du protocole : la prédiction utilise les informations disponibles
jusqu'à la FIN DU SEMESTRE 2. Une forte association avec la cible n'est donc
pas, en soi, une fuite : les résultats de S1/S2 sont légitimement très
prédictifs. Une suspicion est émise lorsque :

- la variable n'a pas de sens métier (identifiant, métadonnée d'export) ;
- une variable connue dès l'inscription (ou non documentée) est associée de
  façon anormalement forte à la cible, ou possède une modalité « pure » ;
- le fait qu'une valeur soit manquante dépend fortement de la classe ;
- un même étudiant apparaît plusieurs fois (risque de chevauchement).

Les associations sont calculées sur l'ensemble du fichier à titre
DESCRIPTIF : elles ne doivent pas servir à sélectionner des variables
(cela constituerait une fuite par sélection).
"""

from __future__ import annotations

import pandas as pd
from scipy.stats import chi2_contingency

from src import config as project_config
from src.data_quality.config import IDENTIFIER, METADATA, TARGET, VARIABLE_SPECS
from src.data_quality.context import AuditContext
from src.data_quality.detectors.redundancy import correlation_ratio, cramers_v
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput, Severity

_LEGITIMATE_AVAILABILITY = {"s1", "s2"}
_MISSINGNESS_P_VALUE = 0.001
_MISSINGNESS_MIN_V = 0.10
_MISSINGNESS_MIN_COUNT = 20


def detect_leakage(ctx: AuditContext) -> DetectorOutput:
    """Recense les risques de fuite de données et d'apprentissage artificiel."""
    out = DetectorOutput()
    _identifier_risks(ctx, out)
    _metadata_risks(ctx, out)
    target = ctx.target_keys()
    if target is not None and target.notna().sum() > 0:
        out.tables["association_cible"] = _target_associations(ctx, target, out)
        out.tables["manquants_informatifs"] = _informative_missingness(ctx, target, out)
    out.anomalies.append(
        Anomaly(
            get_rule("LEA_AUDIT_STATISTICS"),
            "Seuils d'audit (quantiles, IQR, corrélations, associations) calculés sur "
            "l'ensemble du fichier : usage descriptif uniquement, à ne pas réutiliser pour un "
            "traitement appris.",
        )
    )
    return out


def _identifier_risks(ctx: AuditContext, out: DetectorOutput) -> None:
    id_col = project_config.STUDENT_ID
    if not ctx.has(id_col):
        return
    out.anomalies.append(
        Anomaly(
            get_rule("LEA_IDENTIFIER"),
            f"« {id_col} » est un identifiant : à exclure des variables explicatives.",
            column=id_col,
        )
    )
    ids = ctx.student_ids().dropna()
    repeated = ids[ids.duplicated(keep=False)]
    if not repeated.empty:
        out.anomalies.append(
            Anomaly(
                get_rule("LEA_DUPLICATE_SPLIT"),
                f"{repeated.nunique()} identifiants apparaissent plusieurs fois "
                f"({len(repeated)} lignes) : sans dédoublonnage ou découpage groupé, un même "
                "étudiant peut se retrouver en apprentissage et en test.",
                column=id_col,
                observed_value=f"{repeated.nunique()} identifiants répétés",
                expected_value="identifiant unique par ligne, ou découpage groupé",
                n_affected=len(repeated),
            )
        )


def _metadata_risks(ctx: AuditContext, out: DetectorOutput) -> None:
    for column in ctx.columns:
        spec = VARIABLE_SPECS.get(column)
        if spec is None or spec.kind != METADATA:
            continue
        values = ctx.raw.loc[~ctx.is_missing[column], column]
        constant = values.nunique() <= 1
        detail = (
            "constante dans ce fichier : aucun signal possible ici, mais aucune utilité "
            "prédictive et risque si de nouvelles versions apparaissent"
            if constant
            else f"{values.nunique()} valeurs : peut refléter le mode de constitution du fichier"
        )
        out.anomalies.append(
            Anomaly(
                get_rule("LEA_TECHNICAL_METADATA"),
                f"« {column} » est une métadonnée technique ({detail}).",
                column=column,
                observed_value=f"{values.nunique()} valeur(s) distincte(s)",
                severity=Severity.INFO if constant else None,
            )
        )


def _explanatory_columns(ctx: AuditContext) -> list[str]:
    excluded = {IDENTIFIER, METADATA, TARGET}
    return [
        c
        for c in ctx.columns
        if VARIABLE_SPECS.get(c) is None or VARIABLE_SPECS[c].kind not in excluded
    ]


def _target_associations(ctx: AuditContext, target: pd.Series, out: DetectorOutput) -> pd.DataFrame:
    cfg = ctx.config
    rows = []
    for column in _explanatory_columns(ctx):
        spec = VARIABLE_SPECS.get(column)
        availability = spec.availability if spec else "inconnue"
        if column in ctx.valid_numeric.columns:
            measure, value = "eta", correlation_ratio(target, ctx.valid_numeric[column])
            pure = []
        elif column in ctx.keys.columns:
            measure, value = "V de Cramér", cramers_v(ctx.keys[column], target)
            pure = _pure_modalities(ctx.keys[column], target, cfg.pure_modality_min_count)
        else:
            continue
        legit = availability in _LEGITIMATE_AVAILABILITY
        strong = value >= cfg.target_association_threshold
        rows.append(
            {
                "variable": column,
                "disponibilite": availability,
                "disponible_fin_s2": availability != "apres_s2",
                "mesure": measure,
                "valeur": round(value, 4),
                "modalites_pures": " | ".join(pure),
                "lecture": _reading(strong, legit, bool(pure)),
            }
        )
        if strong and legit:
            out.anomalies.append(
                Anomaly(
                    get_rule("LEA_STRONG_PREDICTOR"),
                    f"« {column} » ({availability.upper()}) fortement associée à la cible "
                    f"({measure} = {value:.2f}) : attendu et légitime en fin de S2.",
                    column=column,
                    observed_value=f"{measure}={value:.4f}",
                )
            )
        elif (strong or pure) and not legit:
            reason = f"{measure} = {value:.2f}" if strong else f"modalité(s) pure(s) : {pure}"
            out.anomalies.append(
                Anomaly(
                    get_rule("LEA_TARGET_ASSOCIATION"),
                    f"« {column} » (disponibilité : {availability}) associée à la cible de façon "
                    f"suspecte ({reason}) : vérifier son mode de calcul et sa date de "
                    "disponibilité.",
                    column=column,
                    observed_value=reason,
                    expected_value=f"association < {cfg.target_association_threshold}",
                )
            )
    return pd.DataFrame(rows).sort_values("valeur", ascending=False, kind="stable")


def _reading(strong: bool, legit: bool, pure: bool) -> str:
    if strong and legit:
        return "forte association légitime (information disponible en fin de S2)"
    if strong or pure:
        return "association suspecte à vérifier"
    return "association modérée ou faible"


def _pure_modalities(keys: pd.Series, target: pd.Series, min_count: int) -> list[str]:
    """Modalités d'effectif ≥ ``min_count`` associées à une seule classe."""
    table = pd.crosstab(keys, target)
    totals = table.sum(axis=1)
    pure = table[(totals >= min_count) & (table.max(axis=1) == totals)]
    return [f"{idx}→{row.idxmax()}" for idx, row in pure.iterrows()]


def _informative_missingness(
    ctx: AuditContext, target: pd.Series, out: DetectorOutput
) -> pd.DataFrame:
    rows = []
    known = target.notna()
    for column in _explanatory_columns(ctx):
        indicator = ctx.is_missing.loc[known, column]
        if indicator.sum() < _MISSINGNESS_MIN_COUNT or indicator.all():
            continue
        table = pd.crosstab(indicator, target[known])
        if table.shape[0] < 2 or table.shape[1] < 2:
            continue
        _, p_value, _, _ = chi2_contingency(table)
        v = cramers_v(indicator, target[known])
        rates = (ctx.is_missing.loc[known, column].groupby(target[known]).mean() * 100).round(2)
        rows.append(
            {
                "variable": column,
                "n_manquants": int(indicator.sum()),
                "p_value_khi2": p_value,
                "v_cramer": round(v, 4),
                **{f"pct_manquants_{cls}": rates.get(cls) for cls in project_config.TARGET_CLASSES},
            }
        )
        if p_value < _MISSINGNESS_P_VALUE and v >= _MISSINGNESS_MIN_V:
            detail = ", ".join(f"{cls} {rate:.1f} %" for cls, rate in rates.items())
            out.anomalies.append(
                Anomaly(
                    get_rule("LEA_INFORMATIVE_MISSINGNESS"),
                    f"Le manque de « {column} » dépend de la classe ({detail} ; V = {v:.2f}, "
                    f"p = {p_value:.1e}).",
                    column=column,
                    observed_value=detail,
                    n_affected=int(indicator.sum()),
                )
            )
    columns = ["variable", "n_manquants", "p_value_khi2", "v_cramer"]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=columns)
