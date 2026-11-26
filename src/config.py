"""Configuration centrale du projet.

Toutes les constantes partagées (chemins, cible, paramètres du protocole) sont
définies ici, une seule fois. Les chemins sont construits à partir de
l'emplacement de ce fichier : aucun chemin absolu propre à un ordinateur
n'est versionné, ce qui garantit la portabilité entre les membres du binôme.
"""

from pathlib import Path
from typing import Final

# --- Chemins du projet ------------------------------------------------------
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
DATA_RAW_DIR: Final[Path] = DATA_DIR / "raw"
DATA_INTERIM_DIR: Final[Path] = DATA_DIR / "interim"
DATA_PROCESSED_DIR: Final[Path] = DATA_DIR / "processed"

NOTEBOOKS_DIR: Final[Path] = PROJECT_ROOT / "notebooks"
MODELS_DIR: Final[Path] = PROJECT_ROOT / "models"
OUTPUTS_DIR: Final[Path] = PROJECT_ROOT / "outputs"
REPORTS_DIR: Final[Path] = PROJECT_ROOT / "reports"
FIGURES_DIR: Final[Path] = REPORTS_DIR / "figures"
TABLES_DIR: Final[Path] = REPORTS_DIR / "tables"

# --- Fichier source ---------------------------------------------------------
RAW_DATA_FILENAME: Final[str] = "parcours_etudiants.csv"
RAW_DATA_PATH: Final[Path] = DATA_RAW_DIR / RAW_DATA_FILENAME

# Format documenté dans le dictionnaire des variables :
# séparateur virgule, encodage UTF-8 avec BOM ("utf-8-sig" retire le BOM).
CSV_SEPARATOR: Final[str] = ","
CSV_ENCODING: Final[str] = "utf-8-sig"

# --- Variables clés ---------------------------------------------------------
TARGET: Final[str] = "statut_academique"
STUDENT_ID: Final[str] = "id_etudiant"

# Classes attendues de la variable cible (dictionnaire des variables).
# L'ordre est utilisé pour l'affichage des matrices de confusion et rapports.
TARGET_CLASSES: Final[tuple[str, ...]] = ("Abandon", "En cours", "Diplômé")

# --- Protocole de validation (imposé par la SAÉ, mission 4) -----------------
RANDOM_STATE: Final[int] = 42
TEST_SIZE: Final[float] = 0.20
N_SPLITS: Final[int] = 5
