"""Chargement des données brutes.

Ce module lit le fichier CSV original sans jamais le modifier. Aucun
nettoyage ni conversion de type n'est effectué ici : ces opérations relèvent
de l'audit (mission 1) et du prétraitement (mission 2), et doivent être
justifiées.
"""

from pathlib import Path

import pandas as pd

from src import config


def get_raw_data_path() -> Path:
    """Retourne le chemin attendu du fichier CSV brut (``data/raw/``)."""
    return config.RAW_DATA_PATH


def load_raw_data(path: Path | str | None = None) -> pd.DataFrame:
    """Charge le jeu de données brut dans un DataFrame.

    Parameters
    ----------
    path:
        Chemin du fichier CSV. Par défaut, ``data/raw/parcours_etudiants.csv``.

    Returns
    -------
    pandas.DataFrame
        Données telles qu'elles figurent dans le fichier, BOM UTF-8 retiré.

    Raises
    ------
    FileNotFoundError
        Si le fichier est absent, avec la procédure de récupération.
    """
    csv_path = _resolve_existing_path(path)
    return pd.read_csv(csv_path, sep=config.CSV_SEPARATOR, encoding=config.CSV_ENCODING)


def load_raw_text_data(path: Path | str | None = None) -> pd.DataFrame:
    """Charge le jeu de données brut en TEXTE, sans aucune interprétation.

    Toutes les cellules sont lues comme des chaînes ; aucune valeur n'est
    convertie en NaN (un champ vide reste une chaîne vide). Cette lecture sert
    à l'audit de qualité, qui doit voir les valeurs exactement telles qu'elles
    figurent dans le fichier (espaces, virgules décimales, « ND », etc.).

    Parameters
    ----------
    path:
        Chemin du fichier CSV. Par défaut, ``data/raw/parcours_etudiants.csv``.

    Raises
    ------
    FileNotFoundError
        Si le fichier est absent, avec la procédure de récupération.
    """
    csv_path = _resolve_existing_path(path)
    return pd.read_csv(
        csv_path,
        sep=config.CSV_SEPARATOR,
        encoding=config.CSV_ENCODING,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
    )


def _resolve_existing_path(path: Path | str | None) -> Path:
    """Résout le chemin du CSV et vérifie son existence (message explicite)."""
    csv_path = Path(path) if path is not None else get_raw_data_path()
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Fichier de données introuvable : {csv_path}\n"
            f"Téléchargez '{config.RAW_DATA_FILENAME}' depuis Moodle et placez-le dans "
            f"'data/raw/' (voir data/README.md). Le fichier n'est pas versionné."
        )
    return csv_path
