"""Tests unitaires des détecteurs d'anomalies (``src.data_quality``).

Chaque test part du jeu synthétique VALIDE (``conftest.py``), injecte une
anomalie précise et vérifie qu'elle est détectée — et seulement elle.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data_quality import (
    AuditConfig,
    compare_audits,
    filter_anomalies,
    get_rule,
    rules_frame,
    run_audit,
    severities_at_least,
)
from src.data_quality.context import (
    AuditInputError,
    build_context,
    classify_missing,
    normalize_key,
    parse_numeric,
)
from src.data_quality.detectors.statistical import compute_thresholds
from src.data_quality.schemas import ANOMALY_COLUMNS
from tests.conftest import make_valid_frame, write_csv

CORE_CHECKS = [
    "structure",
    "missing_values",
    "duplicates",
    "formats",
    "business_rules",
    "consistency",
]


def rule_counts(frame: pd.DataFrame, checks=None) -> Counter:
    result = run_audit(frame, checks=checks or CORE_CHECKS)
    assert result.errors == {}
    return Counter(result.anomalies["rule_id"])


def rows_of(frame: pd.DataFrame, rule_id: str, checks=None) -> pd.DataFrame:
    result = run_audit(frame, checks=checks or CORE_CHECKS)
    return result.anomalies[result.anomalies["rule_id"] == rule_id]


# ------------------------------------------------------------------- jeu de référence
def test_valid_frame_has_no_error_level_anomaly(valid_frame: pd.DataFrame) -> None:
    result = run_audit(valid_frame, checks=CORE_CHECKS)
    serious = result.filter(min_severity="LOW")
    # Seules les métadonnées constantes (attendues) sont signalées.
    assert set(serious["rule_id"]) <= {"STR_CONSTANT_COLUMN"}


def test_anomaly_table_has_traceability_columns(valid_frame: pd.DataFrame) -> None:
    result = run_audit(valid_frame)
    assert list(result.anomalies.columns) == list(ANOMALY_COLUMNS)
    assert result.anomalies["anomaly_id"].is_unique


# ------------------------------------------------------------------ valeurs manquantes
def test_missing_values_native_and_disguised_are_distinguished(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "note_admission"] = ""
    frame.loc[1, "note_admission"] = "ND"
    frame.loc[2, "boursier"] = "Non renseigné"
    frame.loc[3, "filiere"] = "   "
    frame.loc[4, "mode_admission"] = "NULL"
    frame.loc[5, "age_inscription"] = "?"
    counts = rule_counts(frame)
    assert counts["MIS_NATIVE"] == 1
    assert counts["MIS_DISGUISED"] == 3
    assert counts["MIS_WHITESPACE_ONLY"] == 1
    assert counts["MIS_NULL_TOKEN"] == 1


def test_missing_target_is_critical(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[7, "statut_academique"] = ""
    flagged = rows_of(frame, "MIS_KEY_FIELD")
    assert len(flagged) == 1
    assert flagged.iloc[0]["severity"] == "CRITICAL"


def test_classify_missing_kinds() -> None:
    kinds = classify_missing(pd.Series(["", "  ", "NA", "nd", " ? ", "12", "Non renseigné"]))
    assert kinds.tolist() == [
        "native",
        "espaces_seuls",
        "null_textuel",
        "deguisee",
        "deguisee",
        "present",
        "deguisee",
    ]


def test_missing_per_row_concentration(valid_frame) -> None:
    frame = valid_frame.copy()
    for column in ("note_admission", "boursier", "filiere", "rang_voeu"):
        frame.loc[10, column] = ""
    flagged = rows_of(frame, "MIS_ROW_CONCENTRATION")
    assert flagged["row_index"].tolist() == [10]


# ---------------------------------------------------------------------------- doublons
def test_exact_duplicates_are_detected_once(valid_frame) -> None:
    frame = pd.concat([valid_frame, valid_frame.iloc[[3]]], ignore_index=True)
    counts = rule_counts(frame)
    assert counts["DUP_EXACT_ROW"] == 1
    assert counts["DUP_ID_CONFLICT"] == 0  # pas de double signalement du même groupe


def test_duplicated_identifier_with_divergent_information(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[5, "id_etudiant"] = frame.loc[4, "id_etudiant"]
    flagged = rows_of(frame, "DUP_ID_CONFLICT")
    assert sorted(flagged["row_index"].tolist()) == [4, 5]


def test_same_content_with_different_identifiers(valid_frame) -> None:
    clone = valid_frame.iloc[[2]].copy()
    clone["id_etudiant"] = "ET999999"
    frame = pd.concat([valid_frame, clone], ignore_index=True)
    assert rule_counts(frame)["DUP_CONTENT_DIFFERENT_ID"] == 1


def test_duplicates_after_normalisation(valid_frame) -> None:
    clone = valid_frame.iloc[[2]].copy()
    clone["regime_cours"] = clone["regime_cours"].str.upper()
    frame = pd.concat([valid_frame, clone], ignore_index=True)
    counts = rule_counts(frame)
    assert counts["DUP_NORMALIZED"] == 1
    assert counts["DUP_EXACT_ROW"] == 0


# ------------------------------------------------------------------------ domaine métier
@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("note_admission", "250"),
        ("note_diplome_anterieur", "-10"),
        ("note_moyenne_s1", "25"),
        ("note_moyenne_s2", "-3"),
    ],
)
def test_grades_out_of_range(valid_frame, column: str, value: str) -> None:
    frame = valid_frame.copy()
    frame.loc[0, column] = value
    flagged = rows_of(frame, "DOM_OUT_OF_RANGE")
    assert flagged["column"].tolist() == [column]
    assert flagged.iloc[0]["observed_value"] == value  # valeur ORIGINALE conservée
    assert flagged.iloc[0]["severity"] == "CRITICAL"


def test_negative_and_non_integer_counts(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "ue_inscrites_s2"] = "-3"
    frame.loc[1, "nb_evaluations_s1"] = "7.5"
    frame.loc[2, "nb_evaluations_s1"] = "999"
    counts = rule_counts(frame)
    assert counts["DOM_NEGATIVE_COUNT"] == 1
    assert counts["DOM_NON_INTEGER"] == 1
    assert counts["DOM_SENTINEL_VALUE"] == 1


def test_categories_out_of_domain_and_invalid_target(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "regime_cours"] = "Nuit"
    frame.loc[1, "rang_voeu"] = "Rang 12"
    frame.loc[2, "statut_academique"] = "Exclu"
    counts = rule_counts(frame)
    assert counts["DOM_CATEGORY_OUT_OF_DOMAIN"] == 2
    assert counts["DOM_TARGET_INVALID"] == 1


def test_impossible_and_implausible_ages(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "age_inscription"] = "0"
    frame.loc[1, "age_inscription"] = "145"
    frame.loc[2, "age_inscription"] = "75"
    counts = rule_counts(frame)
    assert counts["DOM_AGE_IMPOSSIBLE"] == 2
    assert counts["DOM_AGE_IMPLAUSIBLE"] == 1


def test_negative_economic_indicator_is_not_an_anomaly(valid_frame) -> None:
    frame = valid_frame.copy()
    frame["taux_inflation"] = "-0.8"
    frame["indicateur_pib"] = "-4.06"
    flagged = rule_counts(frame)
    assert not any(rule.startswith("DOM_") for rule in flagged)


def test_invalid_identifier_format(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "id_etudiant"] = "XX12"
    assert rule_counts(frame)["DOM_ID_FORMAT"] == 1


# ---------------------------------------------------------------- cohérence entre variables
def test_validated_greater_than_enrolled(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, ["ue_inscrites_s1", "ue_validees_s1", "note_moyenne_s1"]] = ["5", "9", "12.0"]
    flagged = rows_of(frame, "CON_VALIDATED_GT_ENROLLED")
    assert flagged["row_index"].tolist() == [0]
    assert "ue_validees_s1='9'" in flagged.iloc[0]["observed_value"]


def test_zero_grade_is_legitimate_without_validated_ue(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, ["ue_validees_s1", "note_moyenne_s1"]] = ["0", "0.0"]
    frame.loc[1, ["ue_validees_s1", "note_moyenne_s1"]] = ["4", "0.0"]
    flagged = rows_of(frame, "CON_ZERO_GRADE_WITH_VALIDATED")
    assert flagged["row_index"].tolist() == [1]


def test_age_months_consistency(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, ["age_inscription", "age_inscription_mois"]] = ["20", "240"]  # cohérent
    frame.loc[1, ["age_inscription", "age_inscription_mois"]] = ["20", "300"]  # incohérent
    flagged = rows_of(frame, "CON_AGE_MONTHS")
    assert flagged["row_index"].tolist() == [1]


def test_admission_archive_divergence_and_niveau(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, ["note_admission", "note_admission_archive"]] = ["120.0", "160.0"]
    frame.loc[1, ["note_diplome_anterieur", "niveau_dossier"]] = ["165.0", "Fragile"]
    counts = rule_counts(frame)
    assert counts["CON_ADMISSION_ARCHIVE"] == 1
    assert counts["CON_NIVEAU_DOSSIER"] == 1


def test_consistency_ignores_values_outside_domain(valid_frame) -> None:
    """Une valeur impossible n'entraîne pas de signalements en cascade."""
    frame = valid_frame.copy()
    frame.loc[0, ["ue_inscrites_s2", "ue_validees_s2"]] = ["-3", "2"]
    counts = rule_counts(frame)
    assert counts["DOM_NEGATIVE_COUNT"] == 1
    assert counts["CON_VALIDATED_GT_ENROLLED"] == 0


def test_filiere_regime_inconsistency(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, ["filiere", "regime_cours"]] = ["Gestion (soir)", "Jour"]
    assert rule_counts(frame)["CON_FILIERE_REGIME"] == 1


# ----------------------------------------------------------------------- format / saisie
def test_format_variants_keep_original_values(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "regime_cours"] = " Jour "
    frame.loc[1, "regime_cours"] = "JOUR"
    frame.loc[2, "boursier"] = "YES"
    frame.loc[3, "note_admission"] = "125,5"
    frame.loc[4, "niveau_dossier"] = (
        "tres bon"
        if frame.loc[4, "niveau_dossier"] == "Très bon"
        else frame.loc[4, "niveau_dossier"].lower()
    )
    result = run_audit(frame, checks=["formats"])
    a = result.anomalies
    variants = a[a["rule_id"] == "FMT_CATEGORY_VARIANT"]
    assert {"' Jour '", "'JOUR'"} <= set(variants["observed_value"])
    assert (a["rule_id"] == "FMT_FOREIGN_SYNONYM").sum() == 1
    numeric = a[a["rule_id"] == "FMT_NUMERIC_REPRESENTATION"]
    assert numeric.iloc[0]["expected_value"] == "125.5"
    # Les données d'entrée ne sont pas modifiées.
    assert frame.loc[0, "regime_cours"] == " Jour "


def test_text_in_numeric_and_parasite_characters(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "note_admission"] = "douze"
    frame.loc[1, "filiere"] = "Gestion "
    counts = rule_counts(frame, checks=["formats"])
    assert counts["FMT_TEXT_IN_NUMERIC"] == 1
    assert counts["FMT_PARASITE_CHARACTERS"] == 1


def test_normalize_key_and_parse_numeric() -> None:
    assert normalize_key(pd.Series([" PHASE 1 - GÉNÉRAL "])).iloc[0] == "phase 1 - general"
    parsed = parse_numeric(pd.Series(["12,5", " 7 ", "ND", "-3"]))
    assert parsed.iloc[0] == 12.5 and parsed.iloc[1] == 7 and np.isnan(parsed.iloc[2])
    assert parsed.iloc[3] == -3


# ------------------------------------------------------------------- atypiques statistiques
def test_statistical_outlier_is_flagged_but_not_an_error(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "note_admission"] = "199.0"  # dans le domaine [0 ; 200] mais très rare
    result = run_audit(frame, checks=["business_rules", "statistical"])
    a = result.anomalies
    flagged = a[(a["column"] == "note_admission") & (a["row_index"] == 0)]
    assert set(flagged["rule_id"]) <= {"UNI_OUTLIER", "UNI_EXTREME_OUTLIER"}
    assert not flagged.empty
    assert (flagged["diagnostic_status"] == "valeur_atypique").all()
    assert not a["rule_id"].str.startswith("DOM_").any()


def test_zero_dispersion_disables_robust_methods() -> None:
    ctx = build_context(make_valid_frame(), AuditConfig())
    constant = pd.Series([6.0] * 80)
    thresholds = compute_thresholds(constant, "ue_inscrites_s1", ctx)
    assert thresholds["methodes_applicables"] == "aucune (dispersion nulle)"
    assert "borne_haute_iqr" not in thresholds


def test_zero_dispersion_column_produces_info_and_no_outlier(valid_frame) -> None:
    result = run_audit(valid_frame, checks=["statistical"])
    a = result.anomalies
    assert "UNI_ZERO_DISPERSION" in set(a["rule_id"])  # ue_inscrites_* constantes (6)
    assert a[a["column"] == "ue_inscrites_s1"]["rule_id"].eq("UNI_ZERO_DISPERSION").all()


def test_constant_reference_thresholds_are_reused(valid_frame) -> None:
    before = run_audit(valid_frame, checks=["statistical"])
    after = run_audit(valid_frame, checks=["statistical"], reference_thresholds=before.thresholds)
    assert (after.thresholds["seuils"] == "reference").all()


# ----------------------------------------------------------------------------- structure
def test_missing_unexpected_and_constant_columns(valid_frame) -> None:
    frame = valid_frame.drop(columns=["boursier"]).assign(colonne_inconnue="x")
    counts = rule_counts(frame, checks=["structure"])
    assert counts["STR_MISSING_COLUMN"] == 1
    assert counts["STR_UNEXPECTED_COLUMN"] == 1
    assert counts["STR_CONSTANT_COLUMN"] >= 3  # version_export, code_campagne, colonne_inconnue


def test_empty_column_and_type_mismatch(valid_frame) -> None:
    frame = valid_frame.copy()
    frame["boursier"] = ""
    frame.loc[0, "note_admission"] = "ND"
    counts = rule_counts(frame, checks=["structure"])
    assert counts["STR_EMPTY_COLUMN"] == 1
    assert counts["STR_TYPE_MISMATCH"] >= 1


def test_duplicate_column_names_in_header(tmp_path: Path, valid_frame) -> None:
    path = write_csv(valid_frame, tmp_path / "dup.csv")
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    lines[0] = lines[0].replace("boursier", "dette_inscription")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    result = run_audit(path, checks=["structure"])
    assert "STR_DUPLICATE_COLUMN_NAME" in set(result.anomalies["rule_id"])


def test_empty_file_raises_explicit_error(tmp_path: Path) -> None:
    path = tmp_path / "vide.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(AuditInputError, match="vide"):
        run_audit(path)


def test_header_only_file_is_reported_as_empty_dataset(tmp_path: Path, valid_frame) -> None:
    path = write_csv(valid_frame.iloc[0:0], tmp_path / "entete.csv")
    result = run_audit(path)
    assert result.n_rows == 0
    assert "STR_EMPTY_DATASET" in set(result.anomalies["rule_id"])
    assert result.errors == {}


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_audit(tmp_path / "absent.csv")


# ------------------------------------------------------------- fuite, déséquilibre, redondance
def test_class_imbalance_and_leakage_risks(valid_frame) -> None:
    frame = pd.concat(
        [valid_frame, valid_frame[valid_frame["statut_academique"] == "Diplômé"]], ignore_index=True
    )
    result = run_audit(frame, checks=["class_balance", "leakage"])
    rules = set(result.anomalies["rule_id"])
    assert {
        "IMB_CLASS_IMBALANCE",
        "LEA_IDENTIFIER",
        "LEA_DUPLICATE_SPLIT",
        "LEA_TECHNICAL_METADATA",
    } <= rules
    assert result.summaries["class_balance"]["classe_majoritaire"] == "Diplômé"


def test_documented_redundancies_are_confirmed(valid_frame) -> None:
    result = run_audit(valid_frame, checks=["redundancy"])
    table = result.tables["redondances"]
    pairs = set(zip(table["variable_1"], table["variable_2"], table["type"], strict=True))
    assert ("age_inscription", "age_inscription_mois", "RED_DETERMINISTIC") in pairs
    assert ("note_diplome_anterieur", "niveau_dossier", "RED_DETERMINISTIC") in pairs
    assert ("filiere", "regime_cours", "RED_DETERMINISTIC") in pairs


# ------------------------------------------------------------- conservation et utilitaires
def test_input_dataframe_is_never_modified(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "note_admission"] = " 12,5 "
    frame.loc[1, "boursier"] = "ND"
    snapshot = frame.copy(deep=True)
    run_audit(frame, multivariate=True)
    pd.testing.assert_frame_equal(frame, snapshot)


def test_filter_and_severity_order(valid_frame) -> None:
    frame = valid_frame.copy()
    frame.loc[0, "note_admission"] = "250"
    result = run_audit(frame, checks=CORE_CHECKS)
    critical = result.filter(severity="critical")
    assert set(critical["severity"]) == {"CRITICAL"}
    assert severities_at_least("HIGH") == ["CRITICAL", "HIGH"]
    assert len(filter_anomalies(result.anomalies, column="note_admission")) >= 1
    with pytest.raises(ValueError, match="Gravité inconnue"):
        severities_at_least("URGENT")


def test_unknown_check_raises(valid_frame) -> None:
    with pytest.raises(ValueError, match="inconnu"):
        run_audit(valid_frame, checks=["inexistant"])


def test_rule_registry_is_complete() -> None:
    catalog = rules_frame()
    assert catalog["rule_id"].is_unique
    assert catalog[["justification", "impact_ml", "action_envisagee"]].ne("").all().all()
    with pytest.raises(KeyError):
        get_rule("REGLE_INEXISTANTE")


def test_compare_audits_tracks_resolved_and_new(valid_frame) -> None:
    dirty = pd.concat([valid_frame, valid_frame.iloc[[1]]], ignore_index=True)
    dirty.loc[0, "note_admission"] = "250"
    cleaned = valid_frame.copy()
    cleaned.loc[2, "boursier"] = "ND"  # anomalie introduite par un « nettoyage »
    before = run_audit(dirty, checks=CORE_CHECKS)
    after = run_audit(cleaned, checks=CORE_CHECKS)
    comparison = compare_audits(before, after)
    resolved = set(comparison.resolved["rule_id"])
    assert {"DUP_EXACT_ROW", "DOM_OUT_OF_RANGE"} <= resolved
    assert set(comparison.new["rule_id"]) == {"MIS_DISGUISED"}
    status = comparison.status_counts().set_index("rule_id")
    assert status.loc["DOM_OUT_OF_RANGE", "resolu"] == 1
    totals = comparison.totals.set_index("indicateur")
    assert totals.loc["Observations", "evolution"] == -1
