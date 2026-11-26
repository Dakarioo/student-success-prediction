"""Préparation des vues de travail partagées par les détecteurs.

Principe de conservation : le DataFrame reçu n'est JAMAIS modifié. Toutes les
vues (texte, numérique, clés normalisées) sont des copies calculées une seule
fois, puis lues par les détecteurs.

- ``raw`` : valeurs originales en texte (champ vide = chaîne vide).
- ``missing_kind`` : nature de chaque valeur manquante (native, espaces,
  NULL textuel, déguisée) ou ``present``.
- ``numeric`` : conversion numérique TOLÉRANTE (espaces retirés, virgule
  décimale acceptée) des colonnes numériques ; NaN si manquante ou illisible.
- ``valid_numeric`` : ``numeric`` restreint aux valeurs du domaine métier
  (les valeurs impossibles deviennent NaN). Les contrôles croisés et
  statistiques s'appuient sur cette vue pour ne pas signaler deux fois une
  même valeur impossible.
- ``keys`` : clés normalisées des colonnes qualitatives (casse, accents,
  espaces), servant à rapprocher les variantes d'une même modalité.
"""

from __future__ import annotations

import csv
import logging
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src import config as project_config
from src.data_quality.config import (
    DISGUISED_MISSING_TOKENS,
    PANDAS_NULL_TOKENS,
    SENTINEL_VALUES,
    VARIABLE_SPECS,
    AuditConfig,
    VariableSpec,
)

logger = logging.getLogger(__name__)

PRESENT = "present"
NATIVE = "native"
WHITESPACE = "espaces_seuls"
NULL_TOKEN = "null_textuel"
DISGUISED = "deguisee"
MISSING_KINDS: tuple[str, ...] = (NATIVE, WHITESPACE, NULL_TOKEN, DISGUISED)


class AuditInputError(ValueError):
    """Erreur explicite sur les données d'entrée de l'audit."""


# ----------------------------------------------------------------------------- lecture
def read_header(path: Path) -> list[str]:
    """Lit l'en-tête brut du CSV (sans le renommage automatique de pandas)."""
    with path.open(encoding=project_config.CSV_ENCODING, newline="") as handle:
        reader = csv.reader(handle, delimiter=project_config.CSV_SEPARATOR)
        return next(reader, [])


def load_text_frame(path: Path | str) -> tuple[pd.DataFrame, list[str]]:
    """Charge le CSV en texte brut, sans aucune conversion ni interprétation.

    Returns
    -------
    (DataFrame de chaînes, en-tête brut)
    """
    from src.data_loader import load_raw_text_data

    csv_path = Path(path)
    frame = load_raw_text_data(csv_path)
    return frame, read_header(csv_path)


def to_text_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit un DataFrame quelconque (ex. données nettoyées) en texte.

    Les valeurs manquantes natives deviennent des chaînes vides, comme dans le
    CSV brut ; les autres valeurs sont converties par ``str``. Le DataFrame
    d'origine n'est pas modifié.
    """
    text = pd.DataFrame(index=df.index)
    for position in range(df.shape[1]):
        column = df.iloc[:, position]
        as_text = column.astype(object).where(column.notna(), "")
        text[f"__col{position}"] = as_text.map(str)
    text.columns = list(df.columns)
    return text


# ------------------------------------------------------------------------- normalisation
def strip_accents(text: str) -> str:
    """Supprime les accents (é → e) sans modifier les autres caractères."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_key(series: pd.Series) -> pd.Series:
    """Clé de comparaison : espaces superflus, casse et accents neutralisés."""
    cleaned = (
        series.astype(str)
        .str.replace(" ", " ", regex=False)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.casefold()
    )
    return cleaned.map(strip_accents)


def classify_missing(series: pd.Series) -> pd.Series:
    """Nature de chaque valeur : présente ou type de valeur manquante."""
    text = series.astype(str)
    stripped = text.str.strip()
    lowered = stripped.str.casefold()

    kind = pd.Series(PRESENT, index=series.index, dtype=object)
    kind[lowered.isin(DISGUISED_MISSING_TOKENS)] = DISGUISED
    kind[stripped.isin(PANDAS_NULL_TOKENS)] = NULL_TOKEN
    kind[(text != "") & (stripped == "")] = WHITESPACE
    kind[text == ""] = NATIVE
    return kind


def parse_numeric(series: pd.Series) -> pd.Series:
    """Conversion numérique tolérante : espaces retirés, virgule décimale acceptée.

    Les chaînes non numériques (dont les marqueurs de manque) deviennent NaN.
    """
    cleaned = (
        series.astype(str)
        .str.replace(" ", "", regex=False)
        .str.strip()
        .str.replace(r"^(-?\d+),(\d+)$", r"\1.\2", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce").astype(float)


# ------------------------------------------------------------------- domaine métier
def domain_violation_mask(spec: VariableSpec, values: pd.Series, cfg: AuditConfig) -> pd.Series:
    """Valeurs numériques présentes mais incompatibles avec le domaine métier.

    Utilisé pour construire ``valid_numeric`` : une valeur impossible est
    signalée par le détecteur de domaine et exclue des autres contrôles.
    """
    present = values.notna()
    invalid = pd.Series(False, index=values.index)
    if spec.min_value is not None:
        invalid |= values < spec.min_value
    if spec.max_value is not None:
        invalid |= values > spec.max_value
    if spec.expected_dtype == "int":
        invalid |= (values % 1) != 0
        invalid |= values.isin(SENTINEL_VALUES)
    if spec.name in {"age_inscription"}:
        invalid |= (values <= 0) | (values > cfg.age_impossible_max)
    if spec.name == "age_inscription_mois":
        invalid |= (values <= 0) | (values > 12 * (cfg.age_impossible_max + 1))
    return invalid & present


# ---------------------------------------------------------------------------- contexte
@dataclass
class AuditContext:
    """Vues de travail en lecture seule partagées par tous les détecteurs."""

    raw: pd.DataFrame
    header: list[str]
    config: AuditConfig
    source: str
    missing_kind: pd.DataFrame = field(init=False)
    is_missing: pd.DataFrame = field(init=False)
    numeric: pd.DataFrame = field(init=False)
    valid_numeric: pd.DataFrame = field(init=False)
    keys: pd.DataFrame = field(init=False)
    reference_thresholds: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        unique_columns = list(dict.fromkeys(self.raw.columns))
        raw_unique = self.raw.loc[:, ~self.raw.columns.duplicated()]

        self.missing_kind = raw_unique.apply(classify_missing)
        self.is_missing = self.missing_kind.ne(PRESENT)

        numeric_cols = [
            c for c in unique_columns if c in VARIABLE_SPECS and VARIABLE_SPECS[c].is_numeric
        ]
        self.numeric = pd.DataFrame(
            {c: parse_numeric(raw_unique[c]) for c in numeric_cols}, index=self.raw.index
        )
        self.numeric = self.numeric.where(~self.is_missing[numeric_cols])

        valid = self.numeric.copy()
        for name in numeric_cols:
            mask = domain_violation_mask(VARIABLE_SPECS[name], self.numeric[name], self.config)
            valid.loc[mask, name] = np.nan
        self.valid_numeric = valid

        categorical = [c for c in unique_columns if c not in numeric_cols]
        self.keys = pd.DataFrame(
            {c: normalize_key(raw_unique[c]) for c in categorical}, index=self.raw.index
        )
        self.keys = self.keys.where(~self.is_missing[categorical])
        logger.debug("Contexte préparé : %d lignes, %d colonnes", *self.raw.shape)

    # -- accès pratiques ----------------------------------------------------------
    @property
    def n_rows(self) -> int:
        return int(self.raw.shape[0])

    @property
    def columns(self) -> list[str]:
        return list(dict.fromkeys(self.raw.columns))

    def has(self, *columns: str) -> bool:
        """Vrai si toutes les colonnes sont présentes (contrôle sautable sinon)."""
        return all(c in self.raw.columns for c in columns)

    def student_ids(self) -> pd.Series:
        """Identifiants bruts (ou série vide si la colonne est absente)."""
        if project_config.STUDENT_ID in self.raw.columns:
            ids = self.raw[project_config.STUDENT_ID]
            if isinstance(ids, pd.DataFrame):
                ids = ids.iloc[:, 0]
            return ids.where(~self.is_missing[project_config.STUDENT_ID], None)
        return pd.Series(None, index=self.raw.index, dtype=object)

    def target_keys(self) -> pd.Series | None:
        """Classe cible harmonisée (forme du dictionnaire) ou None si absente."""
        target = project_config.TARGET
        if target not in self.keys.columns:
            return None
        canonical = {normalize_key(pd.Series([c]))[0]: c for c in project_config.TARGET_CLASSES}
        return self.keys[target].map(canonical)


def build_context(
    data: pd.DataFrame | Path | str,
    cfg: AuditConfig,
    reference_thresholds: pd.DataFrame | None = None,
) -> AuditContext:
    """Construit le contexte d'audit à partir d'un chemin CSV ou d'un DataFrame."""
    if isinstance(data, pd.DataFrame):
        header = [str(c) for c in data.columns]
        raw = to_text_frame(data)
        source = "DataFrame fourni en mémoire"
    else:
        path = Path(data)
        if not path.is_file():
            raise FileNotFoundError(
                f"Fichier à auditer introuvable : {path}. Voir data/README.md pour la "
                "procédure de récupération."
            )
        try:
            raw, header = load_text_frame(path)
        except pd.errors.EmptyDataError as exc:
            raise AuditInputError(
                f"Le fichier {path.name} est vide (aucun en-tête) : audit impossible."
            ) from exc
        source = path.name
    if raw.shape[1] == 0:
        raise AuditInputError("Aucune colonne lue : audit impossible.")
    if not raw.index.is_unique:
        logger.warning("Index non unique : les observations sont renumérotées 0..n-1.")
        raw = raw.reset_index(drop=True)
    return AuditContext(
        raw=raw,
        header=header,
        config=cfg,
        source=source,
        reference_thresholds=reference_thresholds,
    )
