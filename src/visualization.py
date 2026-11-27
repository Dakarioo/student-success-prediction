"""Harmonisation des visualisations — toutes missions.

Responsabilités
---------------
- Thème graphique commun (taille, police, grille) appliqué une fois en début
  de notebook : ``apply_theme()``.
- Palette constante pour les trois classes, dans l'ordre
  ``config.TARGET_CLASSES``, lisible par les personnes daltoniennes
  (``CLASS_COLORS``).
- Sauvegarde homogène des figures : ``save_figure()``.

Graphiques prévus pour les missions suivantes (à implémenter le moment venu) :
courbes de validation (moyenne ± écart-type par valeur d'hyperparamètre),
matrice de confusion, importance des variables.

Règles
------
- Une figure répond à une question ; titre, axes et unités sont explicites.
- Aucune figure ne doit exposer de données individuelles d'étudiants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from src import config

# Palette catégorielle validée pour les daltonismes (3 premières teintes :
# séparation suffisante même lorsque toutes les paires sont comparées).
CATEGORICAL_COLORS: Final[tuple[str, ...]] = ("#257de0", "#f47230", "#00b894")
CLASS_COLORS: Final[dict[str, str]] = dict(
    zip(config.TARGET_CLASSES, CATEGORICAL_COLORS, strict=True)
)
#: Couleur neutre (séries uniques) et encres de texte.
NEUTRAL_COLOR: Final[str] = "#257de0"
HIGHLIGHT_COLOR: Final[str] = "#dc3c3d"
TEXT_PRIMARY: Final[str] = "#191919"
TEXT_SECONDARY: Final[str] = "#666666"
GRID_COLOR: Final[str] = "#e6e6e6"
#: Rampe séquentielle (une teinte, du clair au foncé) et divergente (bleu ↔ rouge).
SEQUENTIAL_CMAP: Final[str] = "Blues"
DIVERGING_CMAP: Final[str] = "RdBu_r"


def apply_theme() -> None:
    """Applique le thème graphique commun du projet (à appeler une fois)."""
    plt.rcParams.update(
        {
            "figure.figsize": (9, 5),
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 10,
            "axes.labelcolor": TEXT_PRIMARY,
            "axes.edgecolor": "#bdbdbd",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID_COLOR,
            "grid.linewidth": 0.8,
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            "text.color": TEXT_PRIMARY,
            "legend.frameon": False,
            "lines.linewidth": 2,
        }
    )


def save_figure(fig: Figure, path: Path | str) -> Path:
    """Enregistre une figure (dossier créé si besoin) et retourne son chemin."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target)
    return target
