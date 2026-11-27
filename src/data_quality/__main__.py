"""Interface en ligne de commande de l'audit.

Exemples (depuis la racine du projet) ::

    python -m src.data_quality
    python -m src.data_quality --multivariate --min-severity HIGH
    python -m src.data_quality --checks duplicates business_rules --no-figures
    python -m src.data_quality --input data/processed/clean.csv --output-dir outputs/audit_clean
    python -m src.data_quality --catalog
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib

from src import config as project_config
from src.data_quality.audit import run_audit, severities_at_least
from src.data_quality.config import DEFAULT_CONFIG
from src.data_quality.context import AuditInputError
from src.data_quality.detectors import DETECTORS
from src.data_quality.reporting import export_results, synthesis_by_rule, write_rules_catalog
from src.data_quality.schemas import Severity

CATALOG_PATH = project_config.PROJECT_ROOT / "docs" / "audit_rules_catalog.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.data_quality",
        description="Audit de qualité de parcours_etudiants.csv (détection uniquement, aucune "
        "correction).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=project_config.RAW_DATA_PATH,
        help="CSV à auditer (défaut : data/raw/parcours_etudiants.csv).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_CONFIG.output_dir,
        help="Dossier des sorties (défaut : outputs/audit).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_CONFIG.report_path,
        help="Rapport Markdown (défaut : reports/audit_qualite.md).",
    )
    parser.add_argument("--no-report", action="store_true", help="Ne pas générer le rapport.")
    parser.add_argument(
        "--checks",
        nargs="+",
        choices=list(DETECTORS),
        metavar="CHECK",
        help=f"Contrôles à exécuter parmi : {', '.join(DETECTORS)}.",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        choices=list(DETECTORS),
        metavar="CHECK",
        help="Contrôles à exclure.",
    )
    parser.add_argument(
        "--min-severity",
        default="INFO",
        type=str.upper,
        choices=[s.value for s in Severity],
        help="Gravité minimale affichée dans le terminal (exports complets).",
    )
    parser.add_argument(
        "--multivariate", action="store_true", help="Active Isolation Forest et LOF (facultatif)."
    )
    parser.add_argument(
        "--multivariate-scope",
        choices=["all", "train"],
        default="all",
        help="Ajustement multivarié sur tout le fichier ou sur l'apprentissage (80 %%, graine 42).",
    )
    parser.add_argument("--no-figures", action="store_true", help="Ne pas générer les figures.")
    parser.add_argument(
        "--catalog", action="store_true", help="Régénère docs/audit_rules_catalog.md puis quitte."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Niveau de journalisation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)-7s %(name)s — %(message)s")
    log = logging.getLogger("src.data_quality")

    if args.catalog:
        path = write_rules_catalog(CATALOG_PATH)
        log.info("Catalogue des règles écrit : %s", path)
        return 0

    matplotlib.use("Agg")  # export sans affichage
    cfg = replace(
        DEFAULT_CONFIG,
        output_dir=args.output_dir,
        report_path=args.report,
        multivariate_enabled=args.multivariate,
        multivariate_fit_scope=args.multivariate_scope,
    )
    try:
        result = run_audit(args.input, config=cfg, checks=args.checks, exclude=args.exclude)
    except (FileNotFoundError, AuditInputError, ValueError) as exc:
        log.error("%s", exc)
        return 2

    written = export_results(
        result, figures=not args.no_figures, report_path=False if args.no_report else args.report
    )
    _print_summary(result, args.min_severity)
    print(f"\n{len(written)} fichiers écrits ; détail : {args.output_dir}")
    if not args.no_report:
        print(f"Rapport : {args.report}")
    return 1 if result.errors else 0


def _print_summary(result, min_severity: str) -> None:
    counts = result.counts()
    print(f"\nAudit de {result.source} — {result.n_rows} lignes × {result.n_columns} colonnes")
    print(
        f"Signalements : {counts['n_signalements']} "
        f"(individuels {counts['n_signalements_individuels']}, "
        f"globaux {counts['n_signalements_globaux']})"
    )
    print(
        f"Observations distinctes concernées : {counts['n_observations_distinctes']} "
        f"(hors INFO : {counts['n_observations_distinctes_hors_info']} ; "
        f"CRITICAL/HIGH : {counts['n_observations_critique_ou_elevee']})"
    )
    table = synthesis_by_rule(result.anomalies)
    table = table[table["gravite"].isin(severities_at_least(min_severity))]
    if table.empty:
        print(f"Aucun signalement de gravité ≥ {min_severity}.")
        return
    print(f"\nSynthèse par règle (gravité ≥ {min_severity}) :")
    print(
        table[["rule_id", "gravite", "n_signalements", "n_observations_distinctes"]].to_string(
            index=False
        )
    )
    if result.errors:
        print(f"\nContrôles en échec : {result.errors}")


if __name__ == "__main__":
    sys.exit(main())
