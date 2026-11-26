"""Configuration centralisée de l'audit : schéma du dictionnaire et seuils.

Deux familles de paramètres, volontairement séparées :

1. ``VARIABLES`` : traduction FIDÈLE du dictionnaire officiel des variables
   (``docs/references/Dictionnaire_variables.pdf``). Les domaines métier
   viennent du dictionnaire ; lorsqu'une valeur repose sur une hypothèse
   (absente du dictionnaire), elle est signalée par ``hypothesis`` et les
   règles correspondantes produisent des alertes à examiner, jamais des
   erreurs confirmées.
2. ``AuditConfig`` : seuils statistiques et options d'exécution, tous
   modifiables (ligne de commande, notebook) et documentés dans
   ``docs/data_quality_audit.md``.

Aucun paramètre métier n'est codé en dur dans les détecteurs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from src import config as project_config

# --- Rôles des variables ------------------------------------------------------
IDENTIFIER = "identifiant"
CATEGORICAL = "qualitative_nominale"
ORDINAL = "qualitative_ordinale"
BINARY = "binaire"
CONTINUOUS = "quantitative_continue"
COUNT = "quantitative_discrete"
METADATA = "metadonnee"
TARGET = "cible"

#: Moment où l'information est disponible (protocole : prédiction en fin de S2).
AVAILABILITY_ORDER: Final[tuple[str, ...]] = (
    "inscription",
    "contexte",
    "s1",
    "s2",
    "technique",
    "apres_s2",
)


@dataclass(frozen=True)
class VariableSpec:
    """Description d'une variable issue du dictionnaire officiel."""

    name: str
    kind: str
    expected_dtype: str  # "text", "float" ou "int"
    availability: str
    description: str
    min_value: float | None = None
    max_value: float | None = None
    modalities: tuple[str, ...] = ()
    unit: str = ""
    hypothesis: str = ""

    @property
    def is_numeric(self) -> bool:
        return self.expected_dtype in {"float", "int"}

    @property
    def is_categorical(self) -> bool:
        return self.kind in {CATEGORICAL, ORDINAL, BINARY, TARGET}


_OUI_NON = ("Oui", "Non")
_RANGS = tuple(f"Rang {i}" for i in range(10))


def _note(name: str, desc: str, availability: str = "inscription") -> VariableSpec:
    return VariableSpec(name, CONTINUOUS, "float", availability, desc, 0, 200, unit="points / 200")


def _note20(name: str, sem: str) -> VariableSpec:
    return VariableSpec(
        name,
        CONTINUOUS,
        "float",
        sem,
        f"Note moyenne du semestre ({sem.upper()}), sur 20 ; 0 légitime sans UE validée",
        0,
        20,
        unit="points / 20",
    )


def _count(name: str, desc: str, sem: str) -> VariableSpec:
    return VariableSpec(name, COUNT, "int", sem, desc, 0, None, unit="nombre entier")


VARIABLES: Final[tuple[VariableSpec, ...]] = (
    VariableSpec(
        "id_etudiant",
        IDENTIFIER,
        "text",
        "technique",
        "Identifiant administratif fictif attribué à un étudiant",
    ),
    VariableSpec(
        "mode_admission",
        CATEGORICAL,
        "text",
        "inscription",
        "Voie d'admission (liste ouverte dans le dictionnaire)",
    ),
    VariableSpec(
        "rang_voeu",
        ORDINAL,
        "text",
        "inscription",
        "Ordre de préférence de la candidature, de Rang 0 à Rang 9",
        modalities=_RANGS,
    ),
    VariableSpec("filiere", CATEGORICAL, "text", "inscription", "Formation suivie"),
    VariableSpec(
        "regime_cours",
        BINARY,
        "text",
        "inscription",
        "Horaire des enseignements",
        modalities=("Jour", "Soir"),
    ),
    VariableSpec(
        "diplome_anterieur",
        CATEGORICAL,
        "text",
        "inscription",
        "Type de formation ou de qualification antérieure",
    ),
    _note("note_diplome_anterieur", "Note de la qualification antérieure, sur 200"),
    _note("note_admission", "Note utilisée lors de l'admission, sur 200"),
    VariableSpec(
        "dette_inscription",
        BINARY,
        "text",
        "inscription",
        "Dette déclarée lors de l'inscription",
        modalities=_OUI_NON,
    ),
    VariableSpec(
        "frais_scolarite_a_jour",
        BINARY,
        "text",
        "inscription",
        "Frais de scolarité à jour",
        modalities=_OUI_NON,
    ),
    VariableSpec(
        "boursier", BINARY, "text", "inscription", "Bénéficie d'une bourse", modalities=_OUI_NON
    ),
    VariableSpec(
        "age_inscription",
        COUNT,
        "int",
        "inscription",
        "Âge à l'inscription en années révolues",
        min_value=0,
        unit="années",
        hypothesis="Plage plausible [16 ; 70] ans : hypothèse d'audit, absente du dictionnaire",
    ),
    VariableSpec(
        "taux_chomage",
        CONTINUOUS,
        "float",
        "contexte",
        "Taux de chômage, en %",
        min_value=0,
        max_value=100,
        unit="%",
        hypothesis="Bornes [0 ; 100] déduites de la définition d'un taux, pas du dictionnaire",
    ),
    VariableSpec(
        "taux_inflation",
        CONTINUOUS,
        "float",
        "contexte",
        "Taux d'inflation, en % (peut être négatif)",
        unit="%",
    ),
    VariableSpec(
        "indicateur_pib",
        CONTINUOUS,
        "float",
        "contexte",
        "Indicateur économique de PIB (peut être négatif)",
    ),
    _count("ue_creditees_s1", "Nombre d'UE créditées (S1)", "s1"),
    _count("ue_inscrites_s1", "Nombre d'UE inscrites (S1)", "s1"),
    _count("nb_evaluations_s1", "Nombre d'évaluations effectuées (S1)", "s1"),
    _count("ue_validees_s1", "Nombre d'UE validées (S1)", "s1"),
    _note20("note_moyenne_s1", "s1"),
    _count("ue_sans_evaluation_s1", "Nombre d'UE sans évaluation (S1)", "s1"),
    _count("ue_creditees_s2", "Nombre d'UE créditées (S2)", "s2"),
    _count("ue_inscrites_s2", "Nombre d'UE inscrites (S2)", "s2"),
    _count("nb_evaluations_s2", "Nombre d'évaluations effectuées (S2)", "s2"),
    _count("ue_validees_s2", "Nombre d'UE validées (S2)", "s2"),
    _note20("note_moyenne_s2", "s2"),
    _count("ue_sans_evaluation_s2", "Nombre d'UE sans évaluation (S2)", "s2"),
    VariableSpec(
        "niveau_dossier",
        ORDINAL,
        "text",
        "inscription",
        "Appréciation du dossier dérivée de la note antérieure",
        modalities=("Fragile", "Moyen", "Bon", "Très bon"),
    ),
    _note(
        "note_admission_archive",
        "Note d'admission figurant dans un second export (simulé), sur 200",
    ),
    VariableSpec(
        "age_inscription_mois",
        COUNT,
        "int",
        "inscription",
        "Âge à l'inscription en mois, simulé à partir de l'âge en années",
        min_value=0,
        unit="mois",
    ),
    VariableSpec(
        "version_export",
        METADATA,
        "text",
        "technique",
        "Version du système d'export (métadonnée simulée)",
    ),
    VariableSpec(
        "code_campagne",
        METADATA,
        "text",
        "technique",
        "Code administratif d'export simulé ; ce n'est pas l'année de collecte",
    ),
    VariableSpec(
        project_config.TARGET,
        TARGET,
        "text",
        "apres_s2",
        "Statut observé à l'échéance normale de la formation (variable cible)",
        modalities=project_config.TARGET_CLASSES,
    ),
)

VARIABLE_SPECS: Final[dict[str, VariableSpec]] = {v.name: v for v in VARIABLES}
EXPECTED_COLUMNS: Final[tuple[str, ...]] = tuple(v.name for v in VARIABLES)
NUMERIC_COLUMNS: Final[tuple[str, ...]] = tuple(v.name for v in VARIABLES if v.is_numeric)
CLOSED_DOMAIN_COLUMNS: Final[tuple[str, ...]] = tuple(v.name for v in VARIABLES if v.modalities)
OPEN_CATEGORICAL_COLUMNS: Final[tuple[str, ...]] = tuple(
    v.name for v in VARIABLES if v.kind == CATEGORICAL
)

# --- Représentations des valeurs manquantes -----------------------------------
#: Chaînes que pandas reconnaît par défaut comme NaN (``read_csv``) : « NULL textuels ».
PANDAS_NULL_TOKENS: Final[frozenset[str]] = frozenset(
    {"NA", "N/A", "n/a", "NULL", "null", "NaN", "nan", "-NaN", "-nan", "None", "<NA>", "#N/A"}
)
#: Valeurs manquantes déguisées, comparées après suppression des espaces et en minuscules.
#: Liste construite à partir des valeurs RÉELLEMENT observées dans le CSV (ND, ?,
#: Non renseigné) complétée de formes usuelles.
DISGUISED_MISSING_TOKENS: Final[frozenset[str]] = frozenset(
    {"nd", "n.d.", "?", "??", "non renseigné", "non renseigne", "inconnu", "-", "--"}
)
#: Codes numériques sentinelles suspectés (999 observé dans plusieurs colonnes).
SENTINEL_VALUES: Final[tuple[float, ...]] = (999.0, 9999.0)

#: Synonymes d'autres langues pour les variables binaires (YES/NO observés).
BINARY_SYNONYMS: Final[dict[str, str]] = {"yes": "oui", "no": "non", "y": "oui", "n": "non"}

#: Format observé des identifiants (convention constatée, non décrite au dictionnaire).
STUDENT_ID_PATTERN: Final[str] = r"ET\d{6}"


@dataclass
class AuditConfig:
    """Seuils et options de l'audit (valeurs par défaut documentées).

    Chaque seuil est un compromis explicite ; modifier un seuil modifie le
    nombre de signalements, pas les données.
    """

    # Structure
    quasi_constant_share: float = 0.95  # modalité dominante ≥ 95 % → quasi constante

    # Valeurs manquantes
    row_missing_alert: int = 3  # ≥ 3 valeurs manquantes sur une observation
    missing_association_min_phi: float = 0.30  # corrélation entre indicateurs de manque

    # Plausibilité de l'âge (hypothèse documentée, absente du dictionnaire)
    age_plausible_min: int = 16
    age_plausible_max: int = 70
    age_impossible_max: int = 120  # au-delà : biologiquement impossible

    # Cohérences
    admission_archive_tolerance: float = 10.0  # écart toléré entre les deux exports (/200)
    passing_grade: float = 10.0  # hypothèse : seuil de validation d'une UE sur 20
    #: Seuils de niveau_dossier INFÉRÉS des données (séparation parfaite observée) :
    #: Fragile < 120 ≤ Moyen < 140 ≤ Bon < 160 ≤ Très bon.
    niveau_dossier_thresholds: tuple[tuple[str, float, float], ...] = (
        ("fragile", float("-inf"), 120.0),
        ("moyen", 120.0, 140.0),
        ("bon", 140.0, 160.0),
        ("tres bon", 160.0, float("inf")),
    )

    # Atypiques univariés
    iqr_factor: float = 1.5  # moustaches de Tukey
    iqr_extreme_factor: float = 3.0  # « far out » de Tukey
    zscore_threshold: float = 3.0
    zscore_max_abs_skew: float = 1.0  # Z-score appliqué seulement si |asymétrie| ≤ 1
    modified_zscore_threshold: float = 3.5  # Iglewicz & Hoaglin (1993)
    log_transform_skewed: bool = True  # échelle log1p si asymétrie > zscore_max_abs_skew
    min_methods_agreement: int = 2  # consensus requis pour un signalement individuel
    min_non_missing_for_stats: int = 30
    #: Variables dont les zéros sont STRUCTURELS (exclus du calcul des seuils et de la
    #: détection) : note nulle légitime sans UE validée (dictionnaire), absence d'UE
    #: inscrite, validée, créditée ou d'évaluation (abandon, parcours particuliers).
    #: Les zéros incohérents sont traités par les contrôles croisés (consistency).
    zero_inflated_columns: tuple[str, ...] = tuple(
        f"{prefix}_{semester}"
        for semester in ("s1", "s2")
        for prefix in (
            "note_moyenne",
            "ue_creditees",
            "ue_inscrites",
            "ue_validees",
            "nb_evaluations",
            "ue_sans_evaluation",
        )
    )
    #: Indicateurs de contexte (10 valeurs distinctes) : non individuels, exclus.
    univariate_excluded_columns: tuple[str, ...] = (
        "taux_chomage",
        "taux_inflation",
        "indicateur_pib",
        "code_campagne",
    )
    rare_category_share: float = 0.01  # modalité < 1 % des valeurs renseignées
    rare_category_max_count: int = 20  # … et au plus 20 observations
    similar_category_ratio: float = 0.85  # similarité de chaînes (difflib)

    # Atypiques multivariés (facultatif)
    multivariate_enabled: bool = False
    multivariate_contamination: float = 0.01
    multivariate_fit_scope: str = "all"  # "all" (audit descriptif) ou "train"
    isolation_forest_estimators: int = 300
    lof_neighbors: int = 20
    multivariate_max_missing_share: float = 0.5
    multivariate_columns: tuple[str, ...] = (
        "note_diplome_anterieur",
        "note_admission",
        "age_inscription",
        "ue_creditees_s1",
        "ue_inscrites_s1",
        "nb_evaluations_s1",
        "ue_validees_s1",
        "note_moyenne_s1",
        "ue_sans_evaluation_s1",
        "ue_creditees_s2",
        "ue_inscrites_s2",
        "nb_evaluations_s2",
        "ue_validees_s2",
        "note_moyenne_s2",
        "ue_sans_evaluation_s2",
    )

    # Redondances
    high_correlation: float = 0.80
    near_identical_correlation: float = 0.98
    cramers_v_threshold: float = 0.50
    functional_dependency_share: float = 0.99

    # Fuite de données / cible
    target_association_threshold: float = 0.50  # V de Cramér ou rapport de corrélation η
    pure_modality_min_count: int = 20
    class_imbalance_ratio_alert: float = 2.0  # classe majoritaire / minoritaire

    # Protocole (repris de src/config.py, jamais redéfini ailleurs)
    random_state: int = project_config.RANDOM_STATE
    test_size: float = project_config.TEST_SIZE

    # Exécution
    output_dir: Path = field(default_factory=lambda: project_config.OUTPUTS_DIR / "audit")
    report_path: Path = field(
        default_factory=lambda: project_config.REPORTS_DIR / "audit_qualite.md"
    )


DEFAULT_CONFIG: Final[AuditConfig] = AuditConfig()
