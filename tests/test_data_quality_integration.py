"""Tests d'intégration : pipeline complet (audit → exports → rapport → CLI).

Le test sur le fichier réel est ignoré si ``data/raw/parcours_etudiants.csv``
est absent (données non versionnées).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import matplotlib
import pandas as pd
import pytest

from src import config
from src.data_quality import AuditConfig, export_results, run_audit, write_rules_catalog
from src.data_quality.__main__ import main
from tests.conftest import make_valid_frame, write_csv

matplotlib.use("Agg")

EXPECTED_FILES = {
    "anomalies_detail.csv",
    "anomalies_synthese.csv",
    "qualite_variables.csv",
    "doublons.csv",
    "valeurs_manquantes.csv",
    "incoherences_metier.csv",
    "valeurs_atypiques.csv",
    "redondances.csv",
    "risques_methodologiques.csv",
    "audit_resume.json",
}
ID_PATTERN = re.compile(r"ET\d{6}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dirty_csv(tmp_path: Path) -> Path:
    frame = make_valid_frame(n=120)
    frame.loc[0, "note_admission"] = "450"
    frame.loc[1, "boursier"] = "ND"
    frame.loc[2, "regime_cours"] = " JOUR "
    frame.loc[3, ["ue_inscrites_s1", "ue_validees_s1"]] = ["5", "9"]
    frame.loc[4, "note_moyenne_s1"] = "13,5"
    frame = pd.concat([frame, frame.iloc[[5]]], ignore_index=True)  # doublon exact
    return write_csv(frame, tmp_path / "parcours_sale.csv")


def test_full_pipeline_exports_all_outputs(tmp_path: Path) -> None:
    source = _dirty_csv(tmp_path)
    fingerprint = _sha256(source)
    out_dir = tmp_path / "audit"
    report = tmp_path / "rapport.md"

    result = run_audit(source, multivariate=True)
    written = export_results(result, output_dir=out_dir, report_path=report, figures=True)

    assert result.errors == {}
    assert EXPECTED_FILES <= {p.name for p in out_dir.iterdir()}
    assert any((out_dir / "figures").glob("*.png"))
    assert {
        "DOM_OUT_OF_RANGE",
        "MIS_DISGUISED",
        "FMT_CATEGORY_VARIANT",
        "CON_VALIDATED_GT_ENROLLED",
        "FMT_NUMERIC_REPRESENTATION",
        "DUP_EXACT_ROW",
    } <= set(result.anomalies["rule_id"])

    summary = json.loads((out_dir / "audit_resume.json").read_text(encoding="utf-8"))
    assert summary["dimensions"] == {"lignes": 121, "colonnes": 33}
    assert summary["comptages"]["n_signalements"] == len(result.anomalies)

    text = report.read_text(encoding="utf-8")
    for section in range(1, 16):
        assert f"## {section}. " in text
    assert not ID_PATTERN.search(text), "le rapport ne doit contenir aucun identifiant"
    assert written["rapport"] == report
    assert _sha256(source) == fingerprint, "le fichier source ne doit jamais être modifié"


def test_cli_runs_selected_checks(tmp_path: Path) -> None:
    source = _dirty_csv(tmp_path)
    code = main(
        [
            "--input",
            str(source),
            "--output-dir",
            str(tmp_path / "out"),
            "--report",
            str(tmp_path / "r.md"),
            "--checks",
            "duplicates",
            "business_rules",
            "--no-figures",
            "--min-severity",
            "HIGH",
            "--log-level",
            "WARNING",
        ]
    )
    assert code == 0
    assert (tmp_path / "out" / "anomalies_detail.csv").is_file()
    assert not (tmp_path / "out" / "figures").exists()


def test_cli_reports_missing_file(tmp_path: Path) -> None:
    assert main(["--input", str(tmp_path / "absent.csv"), "--log-level", "ERROR"]) == 2


def test_rules_catalog_generation(tmp_path: Path) -> None:
    path = write_rules_catalog(tmp_path / "catalogue.md")
    text = path.read_text(encoding="utf-8")
    assert "DOM_OUT_OF_RANGE" in text and "Justification" in text


@pytest.mark.skipif(not config.RAW_DATA_PATH.is_file(), reason="fichier réel absent")
def test_real_dataset_audit(tmp_path: Path) -> None:
    fingerprint = _sha256(config.RAW_DATA_PATH)
    result = run_audit(config=AuditConfig(output_dir=tmp_path))
    assert result.errors == {}
    assert (result.n_rows, result.n_columns) == (4504, 33)
    assert result.summaries["duplicates"]["n_lignes_doublons_exacts"] == 80
    assert result.summaries["class_balance"]["classe_majoritaire"] == "Diplômé"
    assert _sha256(config.RAW_DATA_PATH) == fingerprint
