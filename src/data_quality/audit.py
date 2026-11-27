"""Point d'entrée Python de l'audit : ``run_audit`` et ``AuditResult``.

Exemple (notebook)::

    from src.data_quality import run_audit
    result = run_audit()                       # fichier brut par défaut
    result.anomalies                           # un signalement par ligne
    result.filter(min_severity="HIGH")         # filtrage
    result.summary_by_rule()                   # synthèse par règle

L'audit ne modifie jamais les données : il lit, diagnostique et documente.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import pandas as pd

from src import config as project_config
from src.data_quality.config import DEFAULT_CONFIG, AuditConfig
from src.data_quality.context import AuditContext, build_context
from src.data_quality.detectors import DETECTORS, OPTIONAL_DETECTORS
from src.data_quality.rules import RULES
from src.data_quality.schemas import (
    SEVERITY_ORDER,
    Anomaly,
    DetectorOutput,
    Severity,
    anomalies_to_frame,
)

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Résultat complet d'un audit (signalements, tableaux, synthèses)."""

    anomalies: pd.DataFrame
    tables: dict[str, pd.DataFrame]
    summaries: dict[str, dict[str, Any]]
    config: AuditConfig
    source: str
    n_rows: int
    n_columns: int
    detectors_run: list[str]
    errors: dict[str, str] = field(default_factory=dict)
    duration_s: float = 0.0
    source_sha256: str | None = None
    context: AuditContext | None = field(default=None, repr=False)

    # ------------------------------------------------------------------ filtrage
    def filter(
        self,
        severity: str | Iterable[str] | None = None,
        min_severity: str | None = None,
        category: str | Iterable[str] | None = None,
        rule_id: str | Iterable[str] | None = None,
        column: str | Iterable[str] | None = None,
        status: str | Iterable[str] | None = None,
        scope: str | None = None,
    ) -> pd.DataFrame:
        """Sous-ensemble des signalements selon un ou plusieurs critères."""
        return filter_anomalies(
            self.anomalies, severity, min_severity, category, rule_id, column, status, scope
        )

    # ------------------------------------------------------------------ synthèses
    def summary_by_rule(self) -> pd.DataFrame:
        """Nombre de signalements et d'observations distinctes par règle."""
        from src.data_quality.reporting import synthesis_by_rule

        return synthesis_by_rule(self.anomalies)

    def counts(self) -> dict[str, Any]:
        """Totaux : signalements, observations distinctes, gravité, catégorie."""
        from src.data_quality.reporting import summary_counts

        return summary_counts(self.anomalies, self.n_rows)

    @property
    def thresholds(self) -> pd.DataFrame:
        """Seuils statistiques calculés (réutilisables pour une comparaison à seuils constants)."""
        return self.tables.get("valeurs_atypiques", pd.DataFrame())

    def affected_rows(self, min_severity: str = "INFO") -> pd.Index:
        """Index des observations ayant au moins un signalement de gravité suffisante."""
        subset = self.filter(min_severity=min_severity, scope="observation")
        return pd.Index(subset["row_index"].dropna().astype(int).unique()).sort_values()


def filter_anomalies(
    anomalies: pd.DataFrame,
    severity: str | Iterable[str] | None = None,
    min_severity: str | None = None,
    category: str | Iterable[str] | None = None,
    rule_id: str | Iterable[str] | None = None,
    column: str | Iterable[str] | None = None,
    status: str | Iterable[str] | None = None,
    scope: str | None = None,
) -> pd.DataFrame:
    """Filtre un tableau de signalements (utilisable aussi sur un CSV rechargé)."""
    mask = pd.Series(True, index=anomalies.index)
    for name, wanted in (
        ("severity", severity),
        ("category", category),
        ("rule_id", rule_id),
        ("column", column),
        ("diagnostic_status", status),
        ("scope", scope),
    ):
        if wanted is not None:
            values = [wanted] if isinstance(wanted, str) else list(wanted)
            if name == "severity":
                values = [v.upper() for v in values]
            mask &= anomalies[name].isin(values)
    if min_severity is not None:
        allowed = severities_at_least(min_severity)
        mask &= anomalies["severity"].isin(allowed)
    return anomalies.loc[mask]


def severities_at_least(level: str) -> list[str]:
    """Niveaux de gravité supérieurs ou égaux à ``level``."""
    try:
        threshold = Severity(level.upper())
    except ValueError as exc:
        valid = ", ".join(s.value for s in SEVERITY_ORDER)
        raise ValueError(f"Gravité inconnue : {level!r} (attendu : {valid}).") from exc
    position = SEVERITY_ORDER.index(threshold)
    return [s.value for s in SEVERITY_ORDER[: position + 1]]


def resolve_detectors(
    checks: Iterable[str] | None, exclude: Iterable[str] | None, multivariate: bool
) -> list[str]:
    """Liste ordonnée des détecteurs à exécuter (erreur explicite si nom inconnu)."""
    requested = list(checks) if checks else None
    unknown = [c for c in (requested or []) + list(exclude or []) if c not in DETECTORS]
    if unknown:
        raise ValueError(
            f"Contrôle(s) inconnu(s) : {unknown}. Disponibles : {', '.join(DETECTORS)}."
        )
    if requested is None:
        selected = [n for n in DETECTORS if n not in OPTIONAL_DETECTORS or multivariate]
    else:
        selected = [n for n in DETECTORS if n in requested]
    return [n for n in selected if n not in set(exclude or [])]


def run_audit(
    data: pd.DataFrame | Path | str | None = None,
    config: AuditConfig | None = None,
    checks: Iterable[str] | None = None,
    exclude: Iterable[str] | None = None,
    multivariate: bool | None = None,
    reference_thresholds: pd.DataFrame | None = None,
    strict: bool = False,
) -> AuditResult:
    """Lance l'audit complet (ou une sélection de contrôles).

    Parameters
    ----------
    data:
        Chemin d'un CSV, DataFrame (ex. données nettoyées) ou ``None`` pour le
        fichier brut ``data/raw/parcours_etudiants.csv``. Jamais modifié.
    config:
        Seuils et options ; ``AuditConfig()`` par défaut.
    checks / exclude:
        Noms de détecteurs à exécuter / à exclure (voir ``DETECTORS``).
    multivariate:
        Active le détecteur multivarié (sinon : valeur de la configuration).
    reference_thresholds:
        Seuils statistiques d'un audit précédent (``result.thresholds``) pour
        une comparaison à seuils constants.
    strict:
        Si vrai, une erreur dans un détecteur interrompt l'audit ; sinon elle
        est journalisée et consignée dans ``result.errors``.
    """
    started = time.perf_counter()
    cfg = config or replace(DEFAULT_CONFIG)
    use_multivariate = cfg.multivariate_enabled if multivariate is None else multivariate
    names = resolve_detectors(checks, exclude, use_multivariate)
    source = project_config.RAW_DATA_PATH if data is None else data

    ctx = build_context(source, cfg, reference_thresholds)
    logger.info("Audit de %s : %d lignes × %d colonnes", ctx.source, *ctx.raw.shape)

    anomalies: list[Anomaly] = []
    tables: dict[str, pd.DataFrame] = {}
    summaries: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for name in names:
        step = time.perf_counter()
        try:
            output: DetectorOutput = DETECTORS[name](ctx)
        except Exception as exc:  # un détecteur défaillant n'arrête pas l'audit
            if strict:
                raise
            logger.exception("Détecteur « %s » en échec", name)
            errors[name] = f"{type(exc).__name__}: {exc}"
            continue
        anomalies.extend(output.anomalies)
        tables.update(output.tables)
        summaries[name] = output.summary
        logger.info(
            "  %-15s %6d signalement(s) en %.2f s",
            name,
            len(output.anomalies),
            time.perf_counter() - step,
        )

    frame = anomalies_to_frame(anomalies)
    duration = time.perf_counter() - started
    logger.info("Audit terminé : %d signalements en %.1f s", len(frame), duration)
    return AuditResult(
        anomalies=frame,
        tables=tables,
        summaries=summaries,
        config=cfg,
        source=ctx.source,
        n_rows=ctx.n_rows,
        n_columns=int(ctx.raw.shape[1]),
        detectors_run=[n for n in names if n not in errors],
        errors=errors,
        duration_s=round(duration, 2),
        source_sha256=None if isinstance(source, pd.DataFrame) else file_sha256(source),
        context=ctx,
    )


def file_sha256(path: Path | str) -> str:
    """Empreinte SHA-256 d'un fichier (vérifie que le fichier audité est le bon)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def run_detector(
    name: str,
    data: pd.DataFrame | Path | str | None = None,
    config: AuditConfig | None = None,
) -> AuditResult:
    """Exécute un seul détecteur (ex. ``run_detector("duplicates")``)."""
    return run_audit(data, config=config, checks=[name], multivariate=name == "multivariate")


def available_checks() -> pd.DataFrame:
    """Détecteurs disponibles et nombre de règles associées."""
    return pd.DataFrame(
        [
            {
                "controle": name,
                "facultatif": name in OPTIONAL_DETECTORS,
                "n_regles": sum(r.detector == name for r in RULES.values()),
            }
            for name in DETECTORS
        ]
    )
