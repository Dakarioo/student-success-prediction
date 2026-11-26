"""Tests de cohérence de la configuration (indépendants du jeu de données)."""

from pathlib import Path

from src import config


def test_protocol_parameters_match_sae_requirements() -> None:
    assert config.RANDOM_STATE == 42
    assert config.TEST_SIZE == 0.20
    assert config.N_SPLITS == 5


def test_target_classes_are_the_three_expected_statuses() -> None:
    assert config.TARGET_CLASSES == ("Abandon", "En cours", "Diplômé")
    assert len(set(config.TARGET_CLASSES)) == len(config.TARGET_CLASSES)


def test_target_and_student_id_are_distinct_columns() -> None:
    assert config.TARGET == "statut_academique"
    assert config.STUDENT_ID == "id_etudiant"
    assert config.TARGET != config.STUDENT_ID


def test_project_root_is_derived_from_package_location() -> None:
    expected_root = Path(config.__file__).resolve().parents[1]
    assert config.PROJECT_ROOT == expected_root
    assert (config.PROJECT_ROOT / "pyproject.toml").is_file()
    assert (config.PROJECT_ROOT / "src" / "config.py").is_file()


def test_all_project_paths_are_inside_project_root() -> None:
    paths = [
        config.DATA_DIR,
        config.DATA_RAW_DIR,
        config.DATA_INTERIM_DIR,
        config.DATA_PROCESSED_DIR,
        config.NOTEBOOKS_DIR,
        config.MODELS_DIR,
        config.OUTPUTS_DIR,
        config.REPORTS_DIR,
        config.FIGURES_DIR,
        config.TABLES_DIR,
        config.RAW_DATA_PATH,
    ]
    for path in paths:
        assert path.is_relative_to(config.PROJECT_ROOT), path


def test_raw_data_path_points_to_raw_folder() -> None:
    assert config.RAW_DATA_PATH.parent == config.DATA_RAW_DIR
    assert config.RAW_DATA_PATH.name == config.RAW_DATA_FILENAME == "parcours_etudiants.csv"


def test_csv_format_matches_data_dictionary() -> None:
    assert config.CSV_SEPARATOR == ","
    assert config.CSV_ENCODING == "utf-8-sig"
