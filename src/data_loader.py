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
    csv_path = Path(path) if path is not None else get_raw_data_path()

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Fichier de données introuvable : {csv_path}\n"
            f"Téléchargez '{config.RAW_DATA_FILENAME}' depuis Moodle et placez-le dans "
            f"'data/raw/' (voir data/README.md). Le fichier n'est pas versionné."
        )

    return pd.read_csv(csv_path, sep=config.CSV_SEPARATOR, encoding=config.CSV_ENCODING)
