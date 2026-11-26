"""Anomalies multivariées (FACULTATIF, désactivé par défaut).

Deux méthodes complémentaires, et seulement deux :

- **Isolation Forest** : isole les observations par partitions aléatoires ;
  une observation isolée en peu de coupures est atypique. Insensible à
  l'échelle, adaptée aux distributions asymétriques.
- **Local Outlier Factor (LOF)** : compare la densité locale d'une
  observation à celle de ses voisins ; détecte les profils atypiques
  localement (incohérents avec des observations semblables).

Choix et limites (détaillés dans docs/data_quality_audit.md) :

- variables : notes et comptages individuels (identifiant, cible,
  métadonnées, indicateurs de contexte et variables redondantes exclus) ;
- préparation : valeurs hors domaine → NaN, imputation par la médiane,
  mise à l'échelle robuste (médiane / IQR) — préparation propre à l'audit,
  qui NE doit PAS être réutilisée pour la modélisation ;
- ``fit_scope="all"`` : ajustement descriptif sur tout le fichier ;
  ``fit_scope="train"`` : ajustement sur un jeu d'apprentissage stratifié
  (~80 %, graine 42, groupé par identifiant) et score de toutes les lignes,
  pour rester compatible avec le protocole si les scores étaient réutilisés ;
- les scores sont relatifs (rang d'atypicité), sans seuil « vrai » : le taux
  de contamination fixe arbitrairement la part d'observations signalées.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.data_quality.context import AuditContext
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput

logger = logging.getLogger(__name__)


def prepare_matrix(ctx: AuditContext) -> tuple[pd.DataFrame, pd.Index]:
    """Matrice numérique préparée pour l'audit et index des lignes scorées."""
    columns = [c for c in ctx.config.multivariate_columns if c in ctx.valid_numeric.columns]
    data = ctx.valid_numeric[columns]
    keep = data.isna().mean(axis=1) <= ctx.config.multivariate_max_missing_share
    return data.loc[keep], data.index[keep]


def train_mask(ctx: AuditContext, index: pd.Index) -> pd.Series:
    """Lignes d'apprentissage (≈ 80 %, stratifié sur la cible, groupé par étudiant)."""
    from sklearn.model_selection import StratifiedGroupKFold

    target = ctx.target_keys()
    if target is None:
        raise ValueError("fit_scope='train' exige la variable cible.")
    ids = ctx.student_ids().loc[index].fillna(pd.Series(index.astype(str), index=index))
    y = target.loc[index].fillna("__manquante__")
    n_splits = round(1 / ctx.config.test_size)
    splitter = StratifiedGroupKFold(
        n_splits=n_splits, shuffle=True, random_state=ctx.config.random_state
    )
    _, test_positions = next(splitter.split(np.zeros(len(index)), y, groups=ids))
    mask = pd.Series(True, index=index)
    mask.iloc[test_positions] = False
    return mask


def detect_multivariate(ctx: AuditContext) -> DetectorOutput:
    """Scores d'atypicité multivariés (Isolation Forest et LOF)."""
    from sklearn.ensemble import IsolationForest
    from sklearn.impute import SimpleImputer
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import RobustScaler

    out = DetectorOutput()
    cfg = ctx.config
    data, index = prepare_matrix(ctx)
    if len(index) < max(cfg.lof_neighbors + 1, 50) or data.shape[1] < 2:
        logger.warning("Analyse multivariée ignorée : données insuffisantes.")
        out.summary["statut"] = "ignoree (donnees insuffisantes)"
        return out

    fit_rows = train_mask(ctx, index) if cfg.multivariate_fit_scope == "train" else None
    fit_data = data if fit_rows is None else data.loc[fit_rows]

    prep = make_pipeline(SimpleImputer(strategy="median"), RobustScaler())
    prep.fit(fit_data)
    matrix = prep.transform(data)
    fit_matrix = prep.transform(fit_data)

    forest = IsolationForest(
        n_estimators=cfg.isolation_forest_estimators,
        contamination=cfg.multivariate_contamination,
        random_state=cfg.random_state,
    ).fit(fit_matrix)
    lof = LocalOutlierFactor(
        n_neighbors=cfg.lof_neighbors, contamination=cfg.multivariate_contamination, novelty=True
    ).fit(fit_matrix)

    scores = pd.DataFrame(
        {
            "row_index": index,
            "id_etudiant": ctx.student_ids().loc[index].to_numpy(),
            # Plus le score est élevé, plus l'observation est atypique.
            "score_isolation_forest": -forest.score_samples(matrix),
            "score_lof": -lof.score_samples(matrix),
            "atypique_isolation_forest": forest.predict(matrix) == -1,
            "atypique_lof": lof.predict(matrix) == -1,
        }
    )
    if fit_rows is not None:
        scores["ensemble_ajustement"] = np.where(fit_rows.to_numpy(), "apprentissage", "test")
    scores["consensus"] = scores["atypique_isolation_forest"] & scores["atypique_lof"]
    _emit(ctx, data, scores, out)

    out.tables["scores_multivaries"] = scores.sort_values("score_isolation_forest", ascending=False)
    out.summary.update(
        statut="executee",
        perimetre_ajustement=cfg.multivariate_fit_scope,
        variables=list(data.columns),
        n_observations_scorees=int(len(index)),
        n_isolation_forest=int(scores["atypique_isolation_forest"].sum()),
        n_lof=int(scores["atypique_lof"].sum()),
        n_consensus=int(scores["consensus"].sum()),
    )
    return out


def _emit(ctx: AuditContext, data: pd.DataFrame, scores: pd.DataFrame, out: DetectorOutput) -> None:
    medians = data.median()
    spread = (data.quantile(0.75) - data.quantile(0.25)).replace(0, np.nan)
    flagged = scores[scores["atypique_isolation_forest"] | scores["atypique_lof"]]
    for record in flagged.itertuples(index=False):
        row = int(record.row_index)
        deviation = ((data.loc[row] - medians).abs() / spread).dropna()
        top = list(deviation.sort_values(ascending=False).index[:3])
        methods = [
            name
            for name, flag in (
                ("Isolation Forest", record.atypique_isolation_forest),
                ("LOF", record.atypique_lof),
            )
            if flag
        ]
        values = "; ".join(f"{c}={ctx.raw.at[row, c]!r}" for c in top)
        out.anomalies.append(
            Anomaly(
                get_rule("MUL_OUTLIER"),
                f"Combinaison atypique ({' et '.join(methods)}) ; variables les plus éloignées de "
                f"la médiane : {', '.join(top)}.",
                row_index=row,
                id_etudiant=record.id_etudiant,
                column=top[0] if top else None,
                related_columns=tuple(top),
                observed_value=values,
                expected_value="profil proche de la majorité",
                detection_method=" + ".join(methods),
            )
        )
