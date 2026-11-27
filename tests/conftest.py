"""Fixtures partagées : jeu de données SYNTHÉTIQUE conforme au dictionnaire.

Le jeu réel n'est pas redistribuable : les tests unitaires construisent un
petit jeu valide (aucune anomalie de domaine ni de cohérence), dans lequel
chaque test injecte l'anomalie qu'il veut vérifier.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data_quality.config import EXPECTED_COLUMNS

_MACRO = [("10.8", "1.4", "1.74"), ("13.9", "-0.3", "0.79"), ("7.6", "2.6", "0.32")]
_CLASSES = ["Diplômé", "Abandon", "En cours"]


def _niveau(note: float) -> str:
    if note < 120:
        return "Fragile"
    if note < 140:
        return "Moyen"
    if note < 160:
        return "Bon"
    return "Très bon"


def make_valid_frame(n: int = 80, seed: int = 42) -> pd.DataFrame:
    """Jeu synthétique valide, en texte, aux 33 colonnes du dictionnaire."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        evening = i % 5 == 0
        age = int(rng.integers(18, 30))
        note_prev = round(float(rng.uniform(112, 165)), 1)
        note_adm = round(float(rng.uniform(110, 150)), 1)
        validated = int(rng.integers(0, 7))
        grade = 0.0 if validated == 0 else round(float(rng.uniform(10.5, 15.5)), 2)
        validated2 = int(rng.integers(0, 7))
        grade2 = 0.0 if validated2 == 0 else round(float(rng.uniform(10.5, 15.5)), 2)
        chomage, inflation, pib = _MACRO[i % 3]
        rows.append(
            {
                "id_etudiant": f"ET{100000 + i}",
                "mode_admission": "Phase 1 - général" if i % 4 else "Transfert",
                "rang_voeu": f"Rang {1 + i % 3}",
                "filiere": "Gestion (soir)" if evening else "Gestion",
                "regime_cours": "Soir" if evening else "Jour",
                "diplome_anterieur": "Secondaire achevé",
                "note_diplome_anterieur": f"{note_prev}",
                "note_admission": f"{note_adm}",
                "dette_inscription": "Non" if i % 6 else "Oui",
                "frais_scolarite_a_jour": "Oui" if i % 7 else "Non",
                "boursier": "Non" if i % 3 else "Oui",
                "age_inscription": str(age),
                "taux_chomage": chomage,
                "taux_inflation": inflation,
                "indicateur_pib": pib,
                "ue_creditees_s1": "0",
                "ue_inscrites_s1": "6",
                "nb_evaluations_s1": str(6 + int(rng.integers(0, 5))),
                "ue_validees_s1": str(validated),
                "note_moyenne_s1": str(grade),
                "ue_sans_evaluation_s1": "0",
                "ue_creditees_s2": "0",
                "ue_inscrites_s2": "6",
                "nb_evaluations_s2": str(6 + int(rng.integers(0, 5))),
                "ue_validees_s2": str(validated2),
                "note_moyenne_s2": str(grade2),
                "ue_sans_evaluation_s2": "0",
                "niveau_dossier": _niveau(note_prev),
                "note_admission_archive": f"{note_adm + float(rng.uniform(-2, 2)):.2f}",
                "age_inscription_mois": str(12 * age + int(rng.integers(0, 12))),
                "version_export": "V1",
                "code_campagne": "2026",
                "statut_academique": _CLASSES[i % 3],
            }
        )
    frame = pd.DataFrame(rows, columns=list(EXPECTED_COLUMNS))
    return frame.astype(str)


def write_csv(frame: pd.DataFrame, path: Path) -> Path:
    """Écrit au format de la source : virgule, UTF-8 avec BOM."""
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


@pytest.fixture
def valid_frame() -> pd.DataFrame:
    return make_valid_frame()


@pytest.fixture
def valid_csv(tmp_path: Path, valid_frame: pd.DataFrame) -> Path:
    return write_csv(valid_frame, tmp_path / "parcours_test.csv")
