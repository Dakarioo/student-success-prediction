"""Figures de l'audit de qualité (affichage Jupyter et export).

Chaque fonction reçoit un ``AuditResult`` et retourne une ``Figure`` (ou
``None`` si la figure n'apporterait aucune information, par exemple aucune
valeur manquante). ``save_audit_figures`` exporte l'ensemble pertinent.

Aucune figure n'affiche d'identifiant étudiant.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from src import config as project_config
from src.data_quality.schemas import SEVERITY_LABELS_FR, SEVERITY_ORDER, Severity
from src.visualization import (
    CLASS_COLORS,
    DIVERGING_CMAP,
    HIGHLIGHT_COLOR,
    NEUTRAL_COLOR,
    TEXT_SECONDARY,
    apply_theme,
    save_figure,
)

if TYPE_CHECKING:
    from src.data_quality.audit import AuditResult

logger = logging.getLogger(__name__)

#: Couleurs de gravité (réservées à cet usage, toujours accompagnées d'un libellé).
SEVERITY_COLORS: dict[str, str] = {
    Severity.CRITICAL.value: "#dc3c3d",
    Severity.HIGH.value: "#f18a59",
    Severity.MEDIUM.value: "#fbb315",
    Severity.LOW.value: "#84b9f3",
    Severity.INFO.value: "#b8b8b8",
}
_MISSING_COLORS = {"natifs": "#257de0", "deguises": "#f47230"}

#: Variables numériques montrées dans les boxplots / histogrammes.
KEY_NUMERIC = (
    "note_diplome_anterieur",
    "note_admission",
    "age_inscription",
    "note_moyenne_s1",
    "note_moyenne_s2",
    "ue_inscrites_s1",
    "nb_evaluations_s1",
    "ue_validees_s1",
    "ue_validees_s2",
)


def _label_bars(ax, values, fmt="{:,.0f}") -> None:
    for patch, value in zip(ax.patches, values, strict=False):
        ax.annotate(
            fmt.format(value).replace(",", " "),
            (patch.get_width(), patch.get_y() + patch.get_height() / 2),
            xytext=(3, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=TEXT_SECONDARY,
        )


# ------------------------------------------------------------------ valeurs manquantes
def plot_missing_rates(result: AuditResult) -> Figure | None:
    """Pourcentage de valeurs manquantes par variable (natives / déguisées)."""
    table = result.tables.get("valeurs_manquantes")
    if table is None or table["n_total"].sum() == 0:
        return None
    data = table[table["n_total"] > 0].sort_values("pct_total")
    n = max(result.n_rows, 1)
    native = data["n_natifs"] / n * 100
    disguised = (data["n_total"] - data["n_natifs"]) / n * 100
    fig, ax = plt.subplots(figsize=(9, 0.35 * len(data) + 1.5))
    ax.barh(data["variable"], native, color=_MISSING_COLORS["natifs"], label="Natives (champ vide)")
    ax.barh(
        data["variable"],
        disguised,
        left=native,
        color=_MISSING_COLORS["deguises"],
        label="Déguisées / textuelles (ND, ?, Non renseigné…)",
        edgecolor="white",
        linewidth=1,
    )
    _label_bars_total(ax, data["pct_total"].to_numpy(), (native + disguised).to_numpy())
    ax.set_xlabel("Part des observations (%)")
    ax.set_title("Valeurs manquantes par variable")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    return fig


def _label_bars_total(ax, labels, positions) -> None:
    for y, (label, x) in enumerate(zip(labels, positions, strict=True)):
        ax.annotate(
            f"{label:.1f} %",
            (x, y),
            xytext=(3, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=TEXT_SECONDARY,
        )


def plot_missing_map(result: AuditResult) -> Figure | None:
    """Carte des valeurs manquantes (observations triées par nombre de manques)."""
    ctx = result.context
    if ctx is None or not ctx.is_missing.values.any():
        return None
    columns = ctx.is_missing.columns[ctx.is_missing.any()]
    matrix = ctx.is_missing[columns]
    order = matrix.sum(axis=1).sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(
        matrix.loc[order].T.astype(int),
        cmap=["#f2f2f2", NEUTRAL_COLOR],
        cbar=False,
        ax=ax,
        xticklabels=False,
    )
    ax.set_xlabel(f"Observations ({len(order)}), triées par nombre de valeurs manquantes")
    ax.set_ylabel("")
    ax.set_title("Carte des valeurs manquantes (bleu = manquante, natives et déguisées)")
    return fig


# -------------------------------------------------------------------------- anomalies
def plot_severity_distribution(result: AuditResult) -> Figure | None:
    """Signalements et observations distinctes par niveau de gravité."""
    a = result.anomalies
    if a.empty:
        return None
    levels = [s.value for s in SEVERITY_ORDER]
    reports = a["severity"].value_counts().reindex(levels, fill_value=0)
    rows = (
        a[a["scope"] == "observation"]
        .groupby("severity")["row_index"]
        .nunique()
        .reindex(levels, fill_value=0)
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    labels = [f"{SEVERITY_LABELS_FR[Severity(lv)]}\n({lv})" for lv in levels]
    colors = [SEVERITY_COLORS[lv] for lv in levels]
    for ax, values, title in (
        (axes[0], reports, "Nombre de signalements"),
        (axes[1], rows, "Observations distinctes concernées"),
    ):
        ax.barh(labels, values.to_numpy(), color=colors)
        _label_bars(ax, values.to_numpy())
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
    fig.suptitle("Répartition par gravité", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    return fig


def plot_anomalies_by_category(result: AuditResult) -> Figure | None:
    """Signalements par catégorie, empilés par gravité."""
    a = result.anomalies
    if a.empty:
        return None
    levels = [s.value for s in SEVERITY_ORDER]
    pivot = pd.crosstab(a["category"], a["severity"]).reindex(columns=levels, fill_value=0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(pivot) + 1.5))
    left = np.zeros(len(pivot))
    for level in levels:
        ax.barh(
            pivot.index,
            pivot[level],
            left=left,
            color=SEVERITY_COLORS[level],
            label=level,
            edgecolor="white",
            linewidth=1,
        )
        left += pivot[level].to_numpy()
    for y, total in enumerate(left):
        ax.annotate(
            f"{int(total):,}".replace(",", " "),
            (total, y),
            xytext=(3, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=TEXT_SECONDARY,
        )
    ax.set_xlabel("Nombre de signalements")
    ax.set_title("Signalements par catégorie et gravité")
    ax.legend(title="Gravité", loc="lower right")
    ax.grid(axis="y", visible=False)
    return fig


def plot_anomalies_by_variable(
    result: AuditResult, top: int = 20, min_severity: str = "LOW"
) -> Figure | None:
    """Variables les plus concernées (signalements individuels hors INFO par défaut)."""
    from src.data_quality.audit import severities_at_least

    a = result.anomalies
    subset = a[
        (a["scope"] == "observation") & a["severity"].isin(severities_at_least(min_severity))
    ]
    if subset.empty:
        return None
    levels = severities_at_least(min_severity)
    pivot = pd.crosstab(subset["column"], subset["severity"]).reindex(columns=levels, fill_value=0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index[:top]][::-1]
    fig, ax = plt.subplots(figsize=(9, 0.35 * len(pivot) + 1.5))
    left = np.zeros(len(pivot))
    for level in levels:
        ax.barh(
            pivot.index,
            pivot[level],
            left=left,
            color=SEVERITY_COLORS[level],
            label=level,
            edgecolor="white",
            linewidth=1,
        )
        left += pivot[level].to_numpy()
    ax.set_xlabel("Nombre de signalements individuels")
    ax.set_title(f"Variables les plus concernées (gravité ≥ {min_severity})")
    ax.legend(title="Gravité", loc="lower right")
    ax.grid(axis="y", visible=False)
    return fig


def plot_anomalies_per_observation(result: AuditResult, min_severity: str = "LOW") -> Figure | None:
    """Distribution du nombre de signalements par observation."""
    from src.data_quality.audit import severities_at_least

    a = result.anomalies
    subset = a[
        (a["scope"] == "observation") & a["severity"].isin(severities_at_least(min_severity))
    ]
    if subset.empty:
        return None
    per_row = subset.groupby("row_index").size().reindex(range(result.n_rows), fill_value=0)
    counts = per_row.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(9, 4))
    positions = np.arange(len(counts))
    ax.bar(positions, counts.to_numpy(), color=NEUTRAL_COLOR)
    ax.set_xticks(positions, [str(i) for i in counts.index])
    for x, value in enumerate(counts.to_numpy()):
        ax.annotate(
            f"{value}",
            (x, value),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=TEXT_SECONDARY,
        )
    ax.set_xlabel(f"Nombre de signalements (gravité ≥ {min_severity}) sur l'observation")
    ax.set_ylabel("Nombre d'observations")
    ax.set_title("Concentration des anomalies par observation")
    ax.grid(axis="x", visible=False)
    return fig


# ------------------------------------------------------------------ distributions
def _numeric_columns(result: AuditResult, columns) -> list[str]:
    ctx = result.context
    if ctx is None:
        return []
    return [c for c in (columns or KEY_NUMERIC) if c in ctx.valid_numeric.columns]


def plot_numeric_boxplots(result: AuditResult, columns=None) -> Figure | None:
    """Boxplots des variables numériques (valeurs du domaine uniquement)."""
    cols = _numeric_columns(result, columns)
    if not cols:
        return None
    ctx = result.context
    ncols = 3
    nrows = int(np.ceil(len(cols) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.6 * nrows))
    for ax, column in zip(np.ravel(axes), cols, strict=False):
        values = ctx.valid_numeric[column].dropna()
        ax.boxplot(
            values,
            orientation="horizontal",
            widths=0.5,
            patch_artist=True,
            boxprops={"facecolor": "#cce3fd", "edgecolor": NEUTRAL_COLOR},
            medianprops={"color": NEUTRAL_COLOR, "linewidth": 2},
            flierprops={
                "marker": "o",
                "markersize": 3,
                "markerfacecolor": HIGHLIGHT_COLOR,
                "markeredgecolor": "none",
                "alpha": 0.5,
            },
        )
        ax.set_title(column, fontsize=10)
        ax.set_yticks([])
    for ax in np.ravel(axes)[len(cols) :]:
        ax.set_visible(False)
    fig.suptitle(
        "Distributions des variables numériques (valeurs hors domaine exclues ; "
        "points = au-delà de 1,5·IQR)",
        x=0.01,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig


def plot_outlier_histograms(result: AuditResult, columns=None) -> Figure | None:
    """Histogrammes avec bornes de détection et valeurs signalées."""
    cols = _numeric_columns(result, columns)
    thresholds = result.tables.get("valeurs_atypiques")
    if not cols or thresholds is None or thresholds.empty:
        return None
    ctx = result.context
    t = thresholds.set_index("variable")
    flagged = result.anomalies[
        result.anomalies["rule_id"].isin(["UNI_OUTLIER", "UNI_EXTREME_OUTLIER"])
    ]
    ncols = 3
    nrows = int(np.ceil(len(cols) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.8 * nrows))
    for ax, column in zip(np.ravel(axes), cols, strict=False):
        values = ctx.valid_numeric[column].dropna()
        rows = flagged.loc[flagged["column"] == column, "row_index"].dropna().astype(int)
        ax.hist(values, bins=40, color="#9dc8f7", edgecolor="white", linewidth=0.5)
        if len(rows):
            ax.hist(
                ctx.valid_numeric.loc[rows, column].dropna(),
                bins=40,
                range=(values.min(), values.max()),
                color=HIGHLIGHT_COLOR,
                label="signalées",
            )
        if column in t.index:
            upper_only = (
                t.at[column, "queue_examinee"] == "haute" if "queue_examinee" in t else False
            )
            bounds = ("borne_haute_iqr",) if upper_only else ("borne_basse_iqr", "borne_haute_iqr")
            for bound in bounds:
                value = t.at[column, bound] if bound in t.columns else np.nan
                if pd.notna(value) and values.min() <= value <= values.max():
                    ax.axvline(value, color=TEXT_SECONDARY, linestyle="--", linewidth=1)
        ax.set_title(f"{column} ({len(rows)} signalées)", fontsize=10)
    for ax in np.ravel(axes)[len(cols) :]:
        ax.set_visible(False)
    fig.suptitle(
        "Histogrammes : valeurs atypiques signalées (rouge) et bornes IQR (tirets)",
        x=0.01,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig


# ------------------------------------------------------------- relations / redondances
def plot_correlation_matrix(result: AuditResult) -> Figure | None:
    """Matrice de corrélation de Spearman (variables numériques, valeurs du domaine)."""
    corr = result.tables.get("matrice_correlation_spearman")
    if corr is None or corr.empty:
        return None
    fig, ax = plt.subplots(figsize=(11, 9))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr,
        mask=mask,
        cmap=DIVERGING_CMAP,
        vmin=-1,
        vmax=1,
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.7, "label": "ρ de Spearman"},
        ax=ax,
    )
    ax.set_title("Corrélations de Spearman entre variables numériques")
    return fig


def plot_redundancy_pairs(result: AuditResult) -> Figure | None:
    """Les trois paires redondantes documentées par le dictionnaire."""
    ctx = result.context
    if ctx is None:
        return None
    v = ctx.valid_numeric
    panels = []
    if {"note_admission", "note_admission_archive"} <= set(v.columns):
        panels.append("admission")
    if {"age_inscription", "age_inscription_mois"} <= set(v.columns):
        panels.append("age")
    if "note_diplome_anterieur" in v.columns and "niveau_dossier" in ctx.keys.columns:
        panels.append("niveau")
    if not panels:
        return None
    fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels), 4))
    for ax, panel in zip(np.atleast_1d(axes), panels, strict=True):
        if panel == "admission":
            ax.scatter(
                v["note_admission"],
                v["note_admission_archive"],
                s=6,
                alpha=0.4,
                color=NEUTRAL_COLOR,
            )
            ax.plot([90, 200], [90, 200], color=TEXT_SECONDARY, linewidth=1, linestyle="--")
            ax.set(
                xlabel="note_admission",
                ylabel="note_admission_archive",
                title="Admission : deux exports",
            )
        elif panel == "age":
            ax.scatter(
                v["age_inscription"], v["age_inscription_mois"], s=6, alpha=0.4, color=NEUTRAL_COLOR
            )
            ax.set(
                xlabel="age_inscription (années)",
                ylabel="age_inscription_mois",
                title="Âge : années / mois",
            )
        else:
            order = ["fragile", "moyen", "bon", "tres bon"]
            frame = pd.DataFrame(
                {"niveau": ctx.keys["niveau_dossier"], "note": v["note_diplome_anterieur"]}
            ).dropna()
            frame = frame[frame["niveau"].isin(order)]
            sns.stripplot(
                data=frame,
                x="niveau",
                y="note",
                order=order,
                size=2,
                alpha=0.4,
                color=NEUTRAL_COLOR,
                ax=ax,
                jitter=0.3,
            )
            for bound in (120, 140, 160):
                ax.axhline(bound, color=TEXT_SECONDARY, linestyle="--", linewidth=1)
            ax.set(
                xlabel="niveau_dossier",
                ylabel="note_diplome_anterieur",
                title="Niveau dérivé de la note",
            )
    fig.suptitle(
        "Redondances documentées (valeurs du domaine uniquement)",
        x=0.01,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig


def plot_class_distribution(result: AuditResult) -> Figure | None:
    """Répartition des classes de la cible (effectifs et proportions)."""
    table = result.tables.get("repartition_classes")
    if table is None or table["effectif"].sum() == 0:
        return None
    fig, ax = plt.subplots(figsize=(7, 3.2))
    colors = [CLASS_COLORS.get(c, NEUTRAL_COLOR) for c in table["classe"]]
    ax.barh(table["classe"], table["effectif"], color=colors)
    for y, (count, share) in enumerate(zip(table["effectif"], table["proportion"], strict=True)):
        ax.annotate(
            f"{count} ({share:.1%})",
            (count, y),
            xytext=(4, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )
    ax.invert_yaxis()
    ax.set_xlabel("Nombre d'observations")
    ax.set_title(f"Répartition de la cible « {project_config.TARGET} »")
    ax.grid(axis="y", visible=False)
    return fig


def plot_business_issues(result: AuditResult) -> Figure | None:
    """Incohérences métier et violations de domaine par règle."""
    a = result.anomalies
    subset = a[a["category"].isin(["domaine_metier", "coherence_variables"])]
    if subset.empty:
        return None
    counts = subset.groupby(["rule_id", "severity"]).size().reset_index(name="n")
    counts = counts.sort_values("n")
    fig, ax = plt.subplots(figsize=(9, 0.38 * len(counts) + 1.5))
    ax.barh(counts["rule_id"], counts["n"], color=counts["severity"].map(SEVERITY_COLORS))
    _label_bars(ax, counts["n"].to_numpy())
    ax.set_xlabel("Nombre de signalements")
    ax.set_title("Violations de domaine et incohérences entre variables (couleur = gravité)")
    present = [s.value for s in SEVERITY_ORDER if s.value in set(counts["severity"])]
    handles = [plt.Rectangle((0, 0), 1, 1, color=SEVERITY_COLORS[s]) for s in present]
    ax.legend(handles, present, title="Gravité", loc="lower right")
    ax.grid(axis="y", visible=False)
    return fig


def plot_enrolled_vs_validated(result: AuditResult, semester: str = "s1") -> Figure | None:
    """UE validées vs UE inscrites, incohérences mises en évidence."""
    ctx = result.context
    ins, val = f"ue_inscrites_{semester}", f"ue_validees_{semester}"
    if ctx is None or not {ins, val} <= set(ctx.valid_numeric.columns):
        return None
    data = ctx.valid_numeric[[ins, val]].dropna()
    bad = data[val] > data[ins]
    jitter = np.random.default_rng(project_config.RANDOM_STATE).uniform(-0.25, 0.25, (len(data), 2))
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(
        data[ins] + jitter[:, 0],
        data[val] + jitter[:, 1],
        s=5,
        alpha=0.3,
        color=NEUTRAL_COLOR,
        label="cohérent",
    )
    ax.scatter(
        data.loc[bad, ins] + jitter[bad.to_numpy(), 0],
        data.loc[bad, val] + jitter[bad.to_numpy(), 1],
        s=14,
        color=HIGHLIGHT_COLOR,
        label=f"validées > inscrites ({int(bad.sum())})",
    )
    top = float(data.max().max()) + 1
    ax.plot([0, top], [0, top], color=TEXT_SECONDARY, linestyle="--", linewidth=1)
    ax.set(xlabel=ins, ylabel=val, title=f"UE validées vs inscrites ({semester.upper()})")
    ax.legend(loc="upper left")
    return fig


#: Figures exportées par ``save_audit_figures`` (nom de fichier → fonction).
FIGURES: dict[str, Callable[[AuditResult], Figure | None]] = {
    "01_valeurs_manquantes_par_variable": plot_missing_rates,
    "02_carte_valeurs_manquantes": plot_missing_map,
    "03_signalements_par_gravite": plot_severity_distribution,
    "04_signalements_par_categorie": plot_anomalies_by_category,
    "05_signalements_par_variable": plot_anomalies_by_variable,
    "06_signalements_par_observation": plot_anomalies_per_observation,
    "07_boxplots_variables_numeriques": plot_numeric_boxplots,
    "08_histogrammes_atypiques": plot_outlier_histograms,
    "09_matrice_correlation": plot_correlation_matrix,
    "10_redondances_documentees": plot_redundancy_pairs,
    "11_repartition_classes": plot_class_distribution,
    "12_incoherences_metier": plot_business_issues,
    "13_ue_validees_vs_inscrites_s1": plot_enrolled_vs_validated,
}


def save_audit_figures(result: AuditResult, directory: Path | str) -> dict[str, Path]:
    """Exporte les figures pertinentes (PNG) et retourne leurs chemins."""
    apply_theme()
    paths: dict[str, Path] = {}
    for name, plot in FIGURES.items():
        try:
            fig = plot(result)
        except Exception:  # une figure défaillante ne doit pas bloquer l'export
            logger.exception("Figure « %s » non générée", name)
            continue
        if fig is None:
            logger.info("Figure « %s » sans objet : non générée", name)
            continue
        paths[name] = save_figure(fig, Path(directory) / f"{name}.png")
        plt.close(fig)
    return paths
