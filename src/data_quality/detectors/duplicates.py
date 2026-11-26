"""Doublons : exacts, identifiants répétés, contenus identiques, après normalisation.

Chaque type est détecté séparément et n'est signalé qu'une fois par ligne :
une ligne déjà signalée comme doublon exact n'est pas re-signalée comme
« identifiant répété » ou « doublon après normalisation ». Une similarité
n'est jamais considérée automatiquement comme un doublon confirmé.
"""

from __future__ import annotations

import pandas as pd

from src import config as project_config
from src.data_quality.context import AuditContext, normalize_key
from src.data_quality.rules import get_rule
from src.data_quality.schemas import Anomaly, DetectorOutput

_GROUP_COLUMNS = ["type_doublon", "groupe", "row_index", "id_etudiant", "variables_divergentes"]


def detect_duplicates(ctx: AuditContext) -> DetectorOutput:
    """Détecte les quatre familles de doublons et liste leurs groupes.

    Ordre (du diagnostic le plus précis au plus large) : doublons exacts,
    doublons après normalisation, identifiants aux informations réellement
    divergentes, contenus identiques sous des identifiants différents.
    """
    out = DetectorOutput()
    raw = ctx.raw.loc[:, ~ctx.raw.columns.duplicated()]
    ids = ctx.student_ids()
    records: list[dict] = []
    already_flagged: set[int] = set()

    exact = _groups(raw, list(raw.columns))
    _emit_groups(
        exact,
        "exact",
        "DUP_EXACT_ROW",
        raw,
        ids,
        records,
        out,
        already_flagged,
        "Ligne strictement identique à la ligne {first} (identifiant compris).",
    )

    # Après normalisation : diagnostic plus précis qu'un « conflit d'identifiant »
    # lorsque les lignes ne diffèrent que par la casse, les accents ou les espaces.
    normalized = raw.apply(normalize_key)
    norm_groups = [
        g for g in _groups(normalized, list(raw.columns)) if not set(g) <= already_flagged
    ]
    _emit_groups(
        norm_groups,
        "apres_normalisation",
        "DUP_NORMALIZED",
        raw,
        ids,
        records,
        out,
        already_flagged,
        "Identique à la ligne {first} après normalisation (casse, accents, espaces) ; "
        "différences : {diff}.",
    )

    id_col = project_config.STUDENT_ID
    id_groups: list[list[int]] = []
    content: list[list[int]] = []
    if id_col in raw.columns:
        id_groups = [
            g for g in _id_conflict_groups(normalized, ctx) if not set(g) <= already_flagged
        ]
        _emit_groups(
            id_groups,
            "identifiant_diverge",
            "DUP_ID_CONFLICT",
            raw,
            ids,
            records,
            out,
            already_flagged,
            "Identifiant partagé avec la ligne {first}, informations divergentes : {diff}.",
            flag_first=True,
        )
        others = [c for c in raw.columns if c != id_col]
        content = [g for g in _groups(raw, others) if not set(g) <= already_flagged]
        _emit_groups(
            content,
            "contenu_identique_id_differents",
            "DUP_CONTENT_DIFFERENT_ID",
            raw,
            ids,
            records,
            out,
            already_flagged,
            "Contenu identique à la ligne {first} sous un identifiant différent.",
        )

    out.tables["doublons"] = pd.DataFrame(records, columns=_GROUP_COLUMNS)
    repeated_ids = int(ids.dropna().duplicated(keep=False).sum()) if id_col in raw else 0
    out.summary.update(
        n_lignes_doublons_exacts=int(raw.duplicated(keep="first").sum()),
        n_groupes_doublons_exacts=len(exact),
        n_lignes_identifiant_repete=repeated_ids,
        n_identifiants_repetes=int(ids.dropna()[ids.dropna().duplicated()].nunique()),
        n_groupes_identifiant_divergent=len(id_groups),
        n_groupes_contenu_identique_id_differents=len(content),
        n_groupes_doublons_normalises=len(norm_groups),
    )
    return out


def _groups(frame: pd.DataFrame, subset: list[str]) -> list[list[int]]:
    """Groupes de lignes identiques sur ``subset`` (listes d'index, taille ≥ 2)."""
    if frame.empty or not subset:
        return []
    mask = frame.duplicated(subset=subset, keep=False)
    if not mask.any():
        return []
    dup = frame.loc[mask, subset]
    grouped = dup.groupby(list(subset), sort=False, dropna=False).groups
    return [sorted(int(i) for i in idx) for idx in grouped.values()]


def _id_conflict_groups(normalized: pd.DataFrame, ctx: AuditContext) -> list[list[int]]:
    """Identifiants répétés dont les lignes diffèrent même après normalisation."""
    id_col = project_config.STUDENT_ID
    present = normalized[~ctx.is_missing[id_col]]
    repeated = present[present[id_col].duplicated(keep=False)]
    groups = []
    for _, block in repeated.groupby(id_col, sort=False):
        if len(block.drop_duplicates()) > 1:
            groups.append(sorted(int(i) for i in block.index))
    return groups


def _diverging_columns(raw: pd.DataFrame, rows: list[int]) -> list[str]:
    block = raw.loc[rows]
    return [c for c in raw.columns if block[c].nunique(dropna=False) > 1]


def _emit_groups(
    groups: list[list[int]],
    kind: str,
    rule_id: str,
    raw: pd.DataFrame,
    ids: pd.Series,
    records: list[dict],
    out: DetectorOutput,
    already_flagged: set[int],
    template: str,
    flag_first: bool = False,
) -> None:
    """Enregistre chaque groupe et signale ses lignes (la 1re sert de référence)."""
    for number, rows in enumerate(groups, start=1):
        diff_cols = _diverging_columns(raw, rows)
        group_label = f"{kind}-{number:04d}"
        for row in rows:
            records.append(
                {
                    "type_doublon": kind,
                    "groupe": group_label,
                    "row_index": row,
                    "id_etudiant": ids.at[row],
                    "variables_divergentes": ";".join(diff_cols),
                }
            )
        flagged_rows = rows if flag_first else rows[1:]
        for row in flagged_rows:
            if row in already_flagged:
                continue
            already_flagged.add(row)
            values = "; ".join(f"{c}={raw.at[row, c]!r}" for c in diff_cols[:8])
            out.anomalies.append(
                Anomaly(
                    get_rule(rule_id),
                    template.format(first=rows[0], diff=", ".join(diff_cols) or "aucune"),
                    row_index=row,
                    id_etudiant=ids.at[row],
                    column=project_config.STUDENT_ID if kind == "identifiant_diverge" else None,
                    related_columns=tuple(diff_cols),
                    observed_value=values or f"lignes {rows}",
                    expected_value="observation unique",
                    detection_method=f"{get_rule(rule_id).detection_method} (groupe {group_label})",
                    extra_key=f"occ{rows.index(row)}",
                )
            )
        already_flagged.update(rows)
