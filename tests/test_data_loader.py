"""Tests du chargement des données, sur un petit CSV temporaire.

Le jeu de données réel n'est jamais utilisé : il n'est pas redistribuable.
"""

from pathlib import Path

import pytest

from src import config
from src.data_loader import get_raw_data_path, load_raw_data

SAMPLE_CSV = (
    "id_etudiant,note_moyenne_s1,statut_academique\n"
    "E001,12.5,Diplômé\n"
    "E002,0.0,Abandon\n"
    "E003,10.25,En cours\n"
)


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Écrit un CSV au format de la source : virgule, UTF-8 avec BOM."""
    path = tmp_path / "sample.csv"
    path.write_text(SAMPLE_CSV, encoding="utf-8-sig")
    return path


def test_default_path_is_raw_data_path() -> None:
    assert get_raw_data_path() == config.RAW_DATA_PATH


def test_load_removes_bom_from_first_column(sample_csv: Path) -> None:
    df = load_raw_data(sample_csv)
    assert list(df.columns) == ["id_etudiant", "note_moyenne_s1", "statut_academique"]


def test_load_preserves_rows_accents_and_decimals(sample_csv: Path) -> None:
    df = load_raw_data(sample_csv)
    assert df.shape == (3, 3)
    assert df["statut_academique"].tolist() == ["Diplômé", "Abandon", "En cours"]
    assert df["note_moyenne_s1"].tolist() == [12.5, 0.0, 10.25]


def test_load_accepts_string_path(sample_csv: Path) -> None:
    assert load_raw_data(str(sample_csv)).shape == (3, 3)


def test_missing_file_raises_explicit_error(tmp_path: Path) -> None:
    missing = tmp_path / "absent.csv"
    with pytest.raises(FileNotFoundError, match="introuvable") as excinfo:
        load_raw_data(missing)
    message = str(excinfo.value)
    assert str(missing) in message
    assert "data/raw/" in message
