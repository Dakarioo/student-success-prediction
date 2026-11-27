"""Incohérences entre variables (contrôles croisés).

Tous les contrôles portent sur ``ctx.valid_numeric`` : une valeur déjà
signalée comme impossible (hors domaine) est exclue, afin de ne pas produire
de signalements en cascade. Chaque règle précise dans le registre si
l'incohérence est certaine (erreur confirmée) ou à vérifier (anomalie
potentielle), et sur quelle hypothèse elle repose.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import config as project_config
from src.data_quality.context import AuditContext, normalize_key
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput

SEMESTERS: tuple[str, ...] = ("s1", "s2")


def detect_consistency(ctx: AuditContext) -> DetectorOutput:
    """Applique l'ensemble des contrôles croisés disponibles."""
    out = DetectorOutput()
    counts: dict[str, int] = {}
    for semester in SEMESTERS:
        _semester_rules(ctx, semester, out, counts)
    _age_months(ctx, out, counts)
    _admission_archive(ctx, out, counts)
    _niveau_dossier(ctx, out, counts)
    _filiere_regime(ctx, out, counts)
    _admission_mode_age(ctx, out, counts)
    _graduate_without_ue(ctx, out, counts)
    out.tables["controles_coherence"] = pd.DataFrame(
        sorted(counts.items()), columns=["controle", "n_observations"]
    )
    out.summary["controles"] = counts
    return out


# ----------------------------------------------------------------------- utilitaires
def _flag(
    ctx: AuditContext,
    out: DetectorOutput,
    counts: dict[str, int],
    rule_id: str,
    mask: pd.Series,
    columns: tuple[str, ...],
    description: str,
    expected: str,
    label: str | None = None,
) -> None:
    """Signale chaque ligne de ``mask`` en conservant les valeurs ORIGINALES impliquées."""
    mask = mask.fillna(False).astype(bool)
    ids = ctx.student_ids()
    counts[label or rule_id] = counts.get(label or rule_id, 0) + int(mask.sum())
    for row in mask.index[mask]:
        observed = "; ".join(f"{c}={ctx.raw.at[row, c]!r}" for c in columns)
        out.anomalies.append(
            Anomaly(
                get_rule(rule_id),
                description,
                row_index=int(row),
                id_etudiant=ids.at[row],
                column=columns[0],
                related_columns=columns,
                observed_value=observed,
                expected_value=expected,
            )
        )


def _cols(ctx: AuditContext, *names: str) -> list[pd.Series] | None:
    """Séries valides (domaine respecté) ou None si une colonne manque."""
    if not all(n in ctx.valid_numeric.columns for n in names):
        return None
    return [ctx.valid_numeric[n] for n in names]


# ---------------------------------------------------------------- règles par semestre
def _semester_rules(ctx: AuditContext, s: str, out: DetectorOutput, counts: dict[str, int]) -> None:
    names = (
        f"ue_inscrites_{s}",
        f"ue_validees_{s}",
        f"ue_creditees_{s}",
        f"ue_sans_evaluation_{s}",
        f"nb_evaluations_{s}",
        f"note_moyenne_{s}",
    )
    series = _cols(ctx, *names)
    if series is None:
        return
    ins, val, cre, sev, nev, moy = series
    sem = s.upper()
    ins_n, val_n, cre_n, sev_n, nev_n, moy_n = names
    passing = ctx.config.passing_grade

    _flag(
        ctx,
        out,
        counts,
        "CON_VALIDATED_GT_ENROLLED",
        val > ins,
        (val_n, ins_n),
        f"{sem} : plus d'UE validées que d'UE inscrites.",
        f"{val_n} ≤ {ins_n}",
        f"CON_VALIDATED_GT_ENROLLED_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_CREDITED_GT_ENROLLED",
        cre > ins,
        (cre_n, ins_n),
        f"{sem} : plus d'UE créditées que d'UE inscrites.",
        f"{cre_n} ≤ {ins_n}",
        f"CON_CREDITED_GT_ENROLLED_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_NO_EVAL_GT_ENROLLED",
        sev > ins,
        (sev_n, ins_n),
        f"{sem} : plus d'UE sans évaluation que d'UE inscrites.",
        f"{sev_n} ≤ {ins_n}",
        f"CON_NO_EVAL_GT_ENROLLED_{s}",
    )
    # Contrôles « potentiels » : uniquement si les contrôles certains sont respectés.
    certain_ok = (val <= ins) & (sev <= ins) & (cre <= ins)
    _flag(
        ctx,
        out,
        counts,
        "CON_VALIDATED_PLUS_NO_EVAL_GT_ENROLLED",
        certain_ok & (val + sev > ins),
        (val_n, sev_n, ins_n),
        f"{sem} : UE validées + UE sans évaluation dépassent les UE inscrites.",
        f"{val_n} + {sev_n} ≤ {ins_n}",
        f"CON_VALIDATED_PLUS_NO_EVAL_GT_ENROLLED_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_CREDITED_GT_VALIDATED",
        certain_ok & (cre > val),
        (cre_n, val_n),
        f"{sem} : plus d'UE créditées que d'UE validées (hypothèse : une UE "
        "créditée est comptée comme validée).",
        f"{cre_n} ≤ {val_n}",
        f"CON_CREDITED_GT_VALIDATED_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_EVALUATIONS_LT_VALIDATED",
        certain_ok & (nev < (val - cre)),
        (nev_n, val_n, cre_n),
        f"{sem} : moins d'évaluations que d'UE validées hors crédits.",
        f"{nev_n} ≥ {val_n} − {cre_n}",
        f"CON_EVALUATIONS_LT_VALIDATED_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_ACTIVITY_WITHOUT_ENROLMENT",
        (ins == 0) & ((nev > 0) | (moy > 0)),
        (ins_n, nev_n, moy_n),
        f"{sem} : évaluations ou note sans aucune UE inscrite.",
        f"{nev_n} = 0 et {moy_n} = 0 si {ins_n} = 0",
        f"CON_ACTIVITY_WITHOUT_ENROLMENT_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_ZERO_GRADE_WITH_VALIDATED",
        (moy == 0) & (val > 0),
        (moy_n, val_n),
        f"{sem} : note moyenne nulle alors que des UE sont validées.",
        f"{moy_n} > 0 si {val_n} > 0",
        f"CON_ZERO_GRADE_WITH_VALIDATED_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_PASSING_GRADE_NO_VALIDATED",
        (moy >= passing) & (val == 0) & (ins > 0),
        (moy_n, val_n, ins_n),
        f"{sem} : moyenne ≥ {passing:g}/20 sans aucune UE validée (seuil supposé).",
        f"{val_n} > 0 si {moy_n} ≥ {passing:g}",
        f"CON_PASSING_GRADE_NO_VALIDATED_{s}",
    )
    _flag(
        ctx,
        out,
        counts,
        "CON_GRADE_WITHOUT_EVALUATION",
        (moy > 0) & (nev == 0),
        (moy_n, nev_n),
        f"{sem} : note moyenne positive sans aucune évaluation.",
        f"{nev_n} > 0 si {moy_n} > 0",
        f"CON_GRADE_WITHOUT_EVALUATION_{s}",
    )


# --------------------------------------------------------------- règles transversales
def _age_months(ctx: AuditContext, out: DetectorOutput, counts: dict[str, int]) -> None:
    series = _cols(ctx, "age_inscription", "age_inscription_mois")
    if series is None:
        return
    years, months = series
    mismatch = (months < 12 * years) | (months > 12 * years + 11)
    _flag(
        ctx,
        out,
        counts,
        "CON_AGE_MONTHS",
        mismatch,
        ("age_inscription_mois", "age_inscription"),
        "Âge en mois hors de l'intervalle [12 × âge ; 12 × âge + 11].",
        "12·age ≤ age_mois ≤ 12·age + 11",
    )


def _admission_archive(ctx: AuditContext, out: DetectorOutput, counts: dict[str, int]) -> None:
    series = _cols(ctx, "note_admission", "note_admission_archive")
    if series is None:
        return
    current, archive = series
    tolerance = ctx.config.admission_archive_tolerance
    gap = (current - archive).abs()
    _flag(
        ctx,
        out,
        counts,
        "CON_ADMISSION_ARCHIVE",
        gap > tolerance,
        ("note_admission", "note_admission_archive"),
        f"Écart supérieur à {tolerance:g} points entre les deux exports de la note "
        "d'admission ; impossible de déterminer la valeur correcte.",
        f"|écart| ≤ {tolerance:g}",
    )


def expected_niveau(note: pd.Series, thresholds: tuple[tuple[str, float, float], ...]) -> pd.Series:
    """Niveau attendu (clé normalisée) d'après la note antérieure et les seuils."""
    result = pd.Series(np.nan, index=note.index, dtype=object)
    for label, low, high in thresholds:
        result[(note >= low) & (note < high)] = label
    return result


def _niveau_dossier(ctx: AuditContext, out: DetectorOutput, counts: dict[str, int]) -> None:
    if "niveau_dossier" not in ctx.keys.columns or "note_diplome_anterieur" not in (
        ctx.valid_numeric.columns
    ):
        return
    note = ctx.valid_numeric["note_diplome_anterieur"]
    observed = ctx.keys["niveau_dossier"]
    expected = expected_niveau(note, ctx.config.niveau_dossier_thresholds)
    known = observed.isin([t[0] for t in ctx.config.niveau_dossier_thresholds])
    mismatch = note.notna() & known & expected.notna() & (observed != expected)
    _flag(
        ctx,
        out,
        counts,
        "CON_NIVEAU_DOSSIER",
        mismatch,
        ("niveau_dossier", "note_diplome_anterieur"),
        "Niveau du dossier différent du niveau attendu d'après la note antérieure (seuils "
        "120/140/160 inférés du fichier).",
        "Fragile <120 ≤ Moyen <140 ≤ Bon <160 ≤ Très bon",
    )


def _filiere_regime(ctx: AuditContext, out: DetectorOutput, counts: dict[str, int]) -> None:
    if not all(c in ctx.keys.columns for c in ("filiere", "regime_cours")):
        return
    filiere, regime = ctx.keys["filiere"], ctx.keys["regime_cours"]
    evening_label = filiere.str.contains("(soir)", regex=False)
    known = filiere.notna() & regime.isin(["jour", "soir"])
    mismatch = known & (evening_label != (regime == "soir"))
    _flag(
        ctx,
        out,
        counts,
        "CON_FILIERE_REGIME",
        mismatch,
        ("filiere", "regime_cours"),
        "Mention « (soir) » de la filière incohérente avec le régime des cours.",
        "filière « (soir) » ⇔ régime Soir",
    )


def _admission_mode_age(ctx: AuditContext, out: DetectorOutput, counts: dict[str, int]) -> None:
    if "mode_admission" not in ctx.keys.columns or "age_inscription" not in (
        ctx.valid_numeric.columns
    ):
        return
    key = normalize_key(pd.Series(["Plus de 23 ans"]))[0]
    mode = ctx.keys["mode_admission"]
    age = ctx.valid_numeric["age_inscription"]
    _flag(
        ctx,
        out,
        counts,
        "CON_ADMISSION_MODE_AGE",
        (mode == key) & (age < 23),
        ("mode_admission", "age_inscription"),
        "Voie « Plus de 23 ans » avec un âge à l'inscription inférieur à 23 ans.",
        "age_inscription ≥ 23",
    )


def _graduate_without_ue(ctx: AuditContext, out: DetectorOutput, counts: dict[str, int]) -> None:
    target = ctx.target_keys()
    series = _cols(ctx, "ue_inscrites_s1", "ue_inscrites_s2")
    if target is None or series is None:
        return
    ins1, ins2 = series
    mask = (target == "Diplômé") & (ins1 == 0) & (ins2 == 0)
    _flag(
        ctx,
        out,
        counts,
        "CON_GRADUATE_WITHOUT_UE",
        mask,
        (project_config.TARGET, "ue_inscrites_s1", "ue_inscrites_s2"),
        "Étudiant diplômé sans aucune UE inscrite en S1 ni en S2 (parcours à vérifier).",
        "au moins une UE inscrite, ou parcours particulier documenté",
    )
