"""Anomalies statistiques univariées et modalités rares.

Méthodes complémentaires, toutes à seuils configurables :

- **IQR (Tukey)** : robuste, adaptée aux distributions asymétriques ;
  moustaches à 1,5·IQR (atypique) et 3·IQR (extrême).
- **Z-score** : n'est appliqué que si la distribution est approximativement
  symétrique (|asymétrie| ≤ seuil), car moyenne et écart-type sont
  eux-mêmes sensibles aux valeurs extrêmes.
- **Z-score modifié (MAD)** : M = 0,6745·(x − médiane)/MAD, seuil 3,5
  (Iglewicz & Hoaglin, 1993).

Distributions asymétriques (asymétrie > 1, valeurs ≥ 0 : âge, comptages) :
les trois méthodes sont appliquées sur l'échelle ``log1p`` puis les bornes
sont reconverties dans l'unité d'origine (transformation monotone). Un
Comptages (UE, évaluations, âges) : seule la queue HAUTE est examinée, la
borne basse étant fixée par le domaine (0) et les petites valeurs étant
normales. Un signalement individuel exige l'accord d'au moins deux méthodes applicables
(ou de l'unique méthode applicable) ; le nombre de valeurs signalées par
chaque méthode reste disponible dans le tableau de synthèse.

Précautions :

- calculs sur les seules valeurs du domaine métier (``valid_numeric``) : les
  valeurs impossibles sont déjà signalées et fausseraient les seuils ;
- zéros structurels exclus pour les variables concentrées en zéro (une note
  nulle est légitime d'après le dictionnaire) ;
- dispersion robuste nulle (IQR ou MAD = 0) : méthode déclarée non applicable
  plutôt que de signaler toute valeur différente du mode ;
- une valeur atypique n'est jamais une erreur confirmée.

Comparaison avant/après nettoyage : si ``ctx.reference_thresholds`` est
fourni, les bornes d'une audit précédent sont réutilisées (seuils constants)
au lieu d'être recalculées sur les nouvelles données.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_quality.config import CONTINUOUS, COUNT, VARIABLE_SPECS
from src.data_quality.context import AuditContext, normalize_key
from src.data_quality.detectors.formats import canonical_forms
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput

MAD_CONSTANT = 0.6745


def univariate_columns(ctx: AuditContext) -> list[str]:
    """Variables numériques individuelles soumises à l'analyse univariée."""
    excluded = set(ctx.config.univariate_excluded_columns)
    return [
        c
        for c in ctx.valid_numeric.columns
        if VARIABLE_SPECS[c].kind in {CONTINUOUS, COUNT} and c not in excluded
    ]


def compute_thresholds(values: pd.Series, column: str, ctx: AuditContext) -> dict:
    """Statistiques descriptives et bornes de détection d'une variable."""
    cfg = ctx.config
    zero_excluded = column in cfg.zero_inflated_columns
    base = values.dropna()
    analysed = base[base != 0] if zero_excluded else base
    n = int(analysed.size)
    row: dict = {
        "variable": column,
        "queue_examinee": "haute" if VARIABLE_SPECS[column].kind == COUNT else "deux",
        "n_valides": int(base.size),
        "n_analyses": n,
        "zeros_exclus": zero_excluded,
        "part_zeros": round(float((base == 0).mean()), 4) if base.size else np.nan,
    }
    if n < cfg.min_non_missing_for_stats:
        row["methodes_applicables"] = "aucune (effectif insuffisant)"
        return row

    raw_skew = float(analysed.skew())
    use_log = cfg.log_transform_skewed and raw_skew > cfg.zscore_max_abs_skew
    use_log = use_log and float(analysed.min()) >= 0
    scaled = np.log1p(analysed) if use_log else analysed
    back = np.expm1 if use_log else (lambda x: x)

    q = analysed.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    qs = scaled.quantile([0.25, 0.5, 0.75])
    iqr = float(qs[0.75] - qs[0.25])
    median = float(qs[0.5])
    mad = float((scaled - median).abs().median())
    skew = float(scaled.skew())
    mean, std = float(scaled.mean()), float(scaled.std(ddof=1))
    methods = []
    row.update(
        echelle="log1p" if use_log else "identite",
        moyenne=round(float(analysed.mean()), 4),
        ecart_type=round(float(analysed.std(ddof=1)), 4),
        min=float(analysed.min()),
        q01=float(q[0.01]),
        q05=float(q[0.05]),
        q1=float(q[0.25]),
        mediane=float(q[0.5]),
        q3=float(q[0.75]),
        q95=float(q[0.95]),
        q99=float(q[0.99]),
        max=float(analysed.max()),
        asymetrie=round(raw_skew, 4),
        asymetrie_echelle_analyse=round(skew, 4),
        aplatissement=round(float(analysed.kurt()), 4),
        iqr=iqr,
        mad=mad,
    )
    if iqr > 0:
        row.update(
            borne_basse_iqr=float(back(qs[0.25] - cfg.iqr_factor * iqr)),
            borne_haute_iqr=float(back(qs[0.75] + cfg.iqr_factor * iqr)),
            borne_basse_extreme=float(back(qs[0.25] - cfg.iqr_extreme_factor * iqr)),
            borne_haute_extreme=float(back(qs[0.75] + cfg.iqr_extreme_factor * iqr)),
        )
        methods.append("IQR")
    if abs(skew) <= cfg.zscore_max_abs_skew and std > 0:
        row.update(
            borne_basse_z=float(back(mean - cfg.zscore_threshold * std)),
            borne_haute_z=float(back(mean + cfg.zscore_threshold * std)),
        )
        methods.append("Z-score")
    if mad > 0:
        half_width = cfg.modified_zscore_threshold * mad / MAD_CONSTANT
        row.update(
            borne_basse_mad=float(back(median - half_width)),
            borne_haute_mad=float(back(median + half_width)),
        )
        methods.append("Z-score modifié")
    row["methodes_applicables"] = ", ".join(methods) or "aucune (dispersion nulle)"
    return row


def detect_statistical(ctx: AuditContext) -> DetectorOutput:
    """Détecte les valeurs atypiques univariées et les modalités rares."""
    out = DetectorOutput()
    rows = []
    reference = _reference(ctx)
    for column in univariate_columns(ctx):
        values = ctx.valid_numeric[column]
        thresholds = reference.get(column) or compute_thresholds(values, column, ctx)
        thresholds["seuils"] = "reference" if column in reference else "recalcules"
        counts = _flag_outliers(ctx, column, values, thresholds, out)
        thresholds.update(counts)
        rows.append(thresholds)
        if thresholds.get("methodes_applicables", "").startswith("aucune (dispersion"):
            out.anomalies.append(
                Anomaly(
                    get_rule("UNI_ZERO_DISPERSION"),
                    f"« {column} » : IQR et MAD nuls sur les valeurs analysées ; détection "
                    "univariée non applicable.",
                    column=column,
                )
            )
    out.tables["valeurs_atypiques"] = pd.DataFrame(rows)
    out.tables["modalites_rares"] = _rare_categories(ctx, out)
    return out


def _reference(ctx: AuditContext) -> dict[str, dict]:
    ref = ctx.reference_thresholds
    if ref is None or ref.empty or "variable" not in ref.columns:
        return {}
    keep = [c for c in ref.columns if not c.startswith("n_atypiques")]
    return {r["variable"]: dict(r) for r in ref[keep].to_dict("records")}


def _outside(
    values: pd.Series, low: float | None, high: float | None, upper_only: bool = False
) -> pd.Series:
    """Valeurs hors de l'intervalle [low ; high] (ou au-dessus de ``high`` seulement)."""
    if low is None or high is None or pd.isna(low) or pd.isna(high):
        return pd.Series(False, index=values.index)
    above = values > high
    return above if upper_only else above | (values < low)


def _flag_outliers(
    ctx: AuditContext, column: str, values: pd.Series, t: dict, out: DetectorOutput
) -> dict[str, int]:
    analysed = values.copy()
    if t.get("zeros_exclus"):
        analysed = analysed.where(analysed != 0)
    up = VARIABLE_SPECS[column].kind == COUNT
    iqr = _outside(analysed, t.get("borne_basse_iqr"), t.get("borne_haute_iqr"), up)
    z = _outside(analysed, t.get("borne_basse_z"), t.get("borne_haute_z"), up)
    mad = _outside(analysed, t.get("borne_basse_mad"), t.get("borne_haute_mad"), up)
    extreme_iqr = _outside(analysed, t.get("borne_basse_extreme"), t.get("borne_haute_extreme"), up)
    extreme = extreme_iqr & mad
    votes = iqr.astype(int) + z.astype(int) + mad.astype(int)
    n_methods = len([m for m in str(t.get("methodes_applicables", "")).split(", ") if m])
    required = min(ctx.config.min_methods_agreement, max(n_methods, 1))
    any_flag = (votes >= required) | extreme
    ids = ctx.student_ids()

    for row in analysed.index[any_flag.fillna(False)]:
        methods = [
            name
            for name, mask in (("IQR", iqr), ("Z-score", z), ("Z-score modifié", mad))
            if mask.at[row]
        ]
        is_extreme = bool(extreme.at[row])
        rule = get_rule("UNI_EXTREME_OUTLIER" if is_extreme else "UNI_OUTLIER")
        out.anomalies.append(
            Anomaly(
                rule,
                f"Valeur {ctx.raw.at[row, column]} atypique pour « {column} » "
                f"(médiane {t.get('mediane'):g}, échelle {t.get('echelle', 'identite')}, "
                f"méthodes : {', '.join(methods)}).",
                row_index=int(row),
                id_etudiant=ids.at[row],
                column=column,
                observed_value=ctx.raw.at[row, column],
                expected_value=_interval(t),
                detection_method=" + ".join(methods),
            )
        )
    return {
        "n_atypiques_iqr": int(iqr.sum()),
        "n_atypiques_z": int(z.sum()),
        "n_atypiques_mad": int(mad.sum()),
        "n_atypiques_extremes": int(extreme.sum()),
        "n_signalements_consensus": int(any_flag.sum()),
    }


def _interval(t: dict) -> str:
    low, high = t.get("borne_basse_iqr"), t.get("borne_haute_iqr")
    if low is None or pd.isna(low):
        low, high = t.get("borne_basse_mad"), t.get("borne_haute_mad")
    if low is None or pd.isna(low):
        return "non défini"
    return f"[{low:.4g} ; {high:.4g}]"


def _rare_categories(ctx: AuditContext, out: DetectorOutput) -> pd.DataFrame:
    """Modalités (après normalisation) rares parmi les valeurs renseignées."""
    cfg = ctx.config
    rows = []
    for column in ctx.keys.columns:
        spec = VARIABLE_SPECS.get(column)
        if spec is None or not spec.is_categorical:
            continue
        keys = ctx.keys[column]
        if spec.modalities:
            canonical = canonical_forms(column, ctx.raw[column], keys)
            # Clé de la forme de référence (ex. « yes » → « oui ») : calcul une fois par modalité.
            ref_keys = normalize_key(pd.Series(list(canonical.values()), dtype=object))
            mapping = dict(zip(canonical.keys(), ref_keys, strict=True))
            keys = keys.map(mapping).fillna(keys)
        counts = keys.value_counts()
        total = int(counts.sum())
        if total == 0:
            continue
        for key, count in counts.items():
            share = count / total
            if share < cfg.rare_category_share and count <= cfg.rare_category_max_count:
                rows.append(
                    {
                        "variable": column,
                        "modalite_normalisee": key,
                        "n": int(count),
                        "part": round(share, 5),
                    }
                )
                out.anomalies.append(
                    Anomaly(
                        get_rule("UNI_RARE_CATEGORY"),
                        f"Modalité « {key} » de « {column} » : {count} observations ({share:.2%}).",
                        column=column,
                        observed_value=key,
                        expected_value=f"part ≥ {cfg.rare_category_share:.0%}",
                        n_affected=int(count),
                        extra_key=key,
                    )
                )
    return pd.DataFrame(rows, columns=["variable", "modalite_normalisee", "n", "part"])
